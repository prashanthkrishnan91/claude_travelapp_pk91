"""RetrievalPlanner v1 — generate provider-friendly Google Text Search queries.

Takes an ExperienceFrame and produces 1–3 short, targeted query strings for
Google Places text_search. Queries are designed to be provider-friendly (short,
direct) rather than preserving the full user sentence verbatim.

Rules:
- Always preserve the core subtype concept in each query.
- Use destination in every query.
- Add geo hints (waterfront, riverwalk) as modifiers where relevant.
- Generate synonym variants (brewery → taproom) to widen recall.
- Cap at 3 by default, hard cap at 4.
- Never add Tavily, editorial, or non-Google providers.
"""

from __future__ import annotations

import logging
import re
from typing import List

from app.concierge.frame_extractor import ExperienceFrame, SubtypeConcept

logger = logging.getLogger(__name__)

DEFAULT_MAX_QUERIES = 3
HARD_CAP_QUERIES = 4

# Near-synonym expansions for common concepts. These widen recall without
# hardcoding category membership. Not a closed enum — unknown concepts get
# no expansion and still work via direct name matching.
_SYNONYM_EXPANSIONS: dict = {
    "brewery": ["brewery", "taproom", "brewpub"],
    "breweries": ["breweries", "brewery", "taproom", "brewpub"],
    "brewing": ["brewing", "brewery", "taproom"],
    "brewpub": ["brewpub", "brewery", "taproom"],
    "brewpubs": ["brewpubs", "brewpub", "brewery"],
    "taproom": ["taproom", "brewery", "brewpub"],
    "taprooms": ["taprooms", "taproom", "brewery"],
    "craft beer": ["craft beer", "brewery", "taproom"],
    "beer": ["beer", "brewery", "craft beer"],
    "ale": ["ale", "brewery", "craft beer"],
    "winery": ["winery", "wine bar", "vineyard"],
    "wine": ["wine bar", "winery"],
    "distillery": ["distillery", "whiskey bar", "spirits"],
    "whiskey": ["whiskey bar", "distillery"],
    "whisky": ["whisky bar", "distillery"],
    "bourbon": ["bourbon bar", "whiskey bar"],
    "cocktail": ["cocktail bar", "craft cocktail"],
    "tapas": ["tapas", "spanish restaurant", "small plates"],
    "sushi": ["sushi", "sushi restaurant", "japanese restaurant"],
    "ramen": ["ramen", "ramen restaurant", "japanese restaurant"],
    "omakase": ["omakase", "sushi restaurant", "japanese fine dining"],
    "dim sum": ["dim sum", "chinese restaurant"],
    "pho": ["pho", "vietnamese restaurant"],
    "pizza": ["pizza", "pizzeria", "italian restaurant"],
    "steakhouse": ["steakhouse", "steak restaurant"],
    "steak": ["steak restaurant", "steakhouse"],
    "seafood": ["seafood restaurant", "seafood"],
    "brunch": ["brunch restaurant", "brunch spot"],
    "breakfast": ["breakfast restaurant", "breakfast spot"],
    "coffee": ["coffee shop", "cafe", "coffee"],
    "cafe": ["cafe", "coffee shop"],
    "bakery": ["bakery", "pastry shop"],
    "mediterranean": ["mediterranean restaurant"],
    "greek": ["greek restaurant"],
    "italian": ["italian restaurant"],
    "mexican": ["mexican restaurant", "taqueria"],
    "french": ["french restaurant", "bistro"],
    "indian": ["indian restaurant"],
    "thai": ["thai restaurant"],
    "chinese": ["chinese restaurant"],
    "korean": ["korean restaurant", "korean bbq"],
    "vietnamese": ["vietnamese restaurant"],
    "spanish": ["spanish restaurant", "tapas"],
}

# Preference query modifiers: canonical soft-preference label → list of query
# modifier phrases.  Each phrase is prepended to the venue head to generate a
# preference-aware, venue-anchored Google Text Search query.  Phrases are tried
# in order; the first cap-1 produce pref queries, the last cap slot is the broad
# venue-only fallback for recall.
#
# Design invariants:
# - Every entry is a natural-language phrase (not a single ambiguous word).
# - "gem" is intentionally absent: the word triggers gem-shop searches without
#   a strong venue noun.  Use "local favorite", "neighborhood", "underrated" instead.
# - "hidden gem" omitted for same reason.
_PREFERENCE_QUERY_MODIFIERS: dict = {
    "hidden_gem": ["local favorite", "neighborhood", "underrated"],
    "romantic": ["romantic", "date night", "intimate"],
    "intimate": ["intimate", "cozy"],
    "late_night": ["late night", "open late"],
    "view_or_geo": ["rooftop", "with a view", "outdoor"],
    # casual: generates queries that surface informal/neighbourhood options Google ranks
    # differently from the default popular-place ordering. Two modifiers + the plain
    # venue fallback = 3 queries; the third slot is always the broad recall query.
    "casual": ["casual dining", "neighborhood"],
}

# Geography anchors for Chicago — used when geo hints reference water features.
# This maps abstract geography hints to provider-query-friendly terms.
_GEO_QUERY_TERMS: dict = {
    "waterfront": ["waterfront", "riverwalk"],
    "riverwalk": ["riverwalk", "river"],
    "lakefront": ["lakefront", "lake michigan"],
    "lake view": ["lakefront", "lake michigan"],
    "ocean view": ["waterfront", "lakefront"],
    "sea view": ["waterfront"],
    "water view": ["waterfront", "riverwalk"],
    "harbour": ["harbour", "waterfront"],
    "river": ["river", "riverwalk"],
    "lake": ["lake", "lakefront"],
    "rooftop": ["rooftop"],
    "outdoor": ["outdoor", "patio"],
    "patio": ["patio", "outdoor seating"],
    "terrace": ["terrace"],
}


def _primary_label(frame: ExperienceFrame) -> str:
    """Return the most confident concept label from the frame."""
    if not frame.subtype_concepts:
        return (frame.normalized_ask or frame.literal_ask or "").strip()
    return frame.subtype_concepts[0].label


def _synonym_variants(concept: SubtypeConcept) -> List[str]:
    """Return synonym variants for a concept label, or just the label itself."""
    label = concept.label.lower()
    return list(_SYNONYM_EXPANSIONS.get(label, [label]))


def _clean_query(text: str) -> str:
    """Normalize whitespace and strip trailing punctuation from a query string."""
    return re.sub(r"\s+", " ", text).strip().rstrip(".,;:")


def plan_queries(
    frame: ExperienceFrame,
    max_queries: int = DEFAULT_MAX_QUERIES,
) -> List[str]:
    """Generate 1–max_queries provider-friendly Google Text Search queries.

    Query construction is venue-first: every query starts with the primary
    venue concept (or a near-synonym) and only then adds destination, location
    modifiers, and geo hints. This ensures "waterfront breweries" produces
    queries like "brewery Chicago waterfront" instead of "waterfront Chicago"
    that would surface arbitrary waterfront restaurants/parks.

    Preference-aware path: when frame.normalized_soft_preferences is non-empty
    (e.g., "hidden_gem", "romantic", "late_night") and no location anchor/geo
    hint is present, preference modifier phrases are prepended to the venue head
    so all queries carry the user's intent (e.g., "local favorite restaurant
    Chicago" instead of generic "restaurant Chicago").  A broad venue-only
    fallback query is always included for recall.

    Args:
        frame: Extracted ExperienceFrame from the user ask.
        max_queries: Soft cap. Hard capped at HARD_CAP_QUERIES.

    Returns:
        List of short, targeted query strings. Always at least 1 query.
        Each query includes the destination and the primary subtype concept.
    """
    cap = min(max_queries, HARD_CAP_QUERIES)
    destination = (frame.destination or "").strip()
    queries: List[str] = []
    seen: set = set()

    def _add(q: str) -> bool:
        q = _clean_query(q)
        if q and q not in seen and len(queries) < cap:
            queries.append(q)
            seen.add(q)
            return True
        return False

    primary = _primary_label(frame)
    geo_hints = frame.geography_hints
    location_modifiers = getattr(frame, "location_modifiers", []) or []
    geo_term = _geo_query_term(geo_hints[0], destination) if geo_hints else ""
    loc_anchor = location_modifiers[0] if location_modifiers else ""

    # Collect preference query modifiers from frame.normalized_soft_preferences.
    # Each modifier phrase is prepended to the venue head for targeted queries.
    normalized_soft_prefs: List[str] = getattr(frame, "normalized_soft_preferences", []) or []
    pref_modifiers: List[str] = []
    seen_pm: set = set()
    for pref in normalized_soft_prefs:
        for pm in _PREFERENCE_QUERY_MODIFIERS.get(pref, []):
            if pm not in seen_pm:
                pref_modifiers.append(pm)
                seen_pm.add(pm)

    # Use the first synonym as the "preference primary" for pref queries when it
    # is a more descriptive variant (e.g., "cocktail bar" for concept "cocktail").
    pref_primary = primary
    if frame.subtype_concepts:
        variants = _synonym_variants(frame.subtype_concepts[0])
        if variants and variants[0] and variants[0].lower() != primary.lower():
            pref_primary = variants[0]

    if pref_modifiers and not geo_term and not loc_anchor:
        # Preference-only path: generate preference-aware, venue-anchored queries.
        # Each is still venue-anchored so Google targets the right place type.
        for pm in pref_modifiers:
            if len(queries) >= cap:
                break
            _add(f"{pm} {pref_primary} {destination}")
        # Broad venue-only fallback for maximal recall (if cap not yet reached)
        _add(f"{primary} {destination}")

    elif pref_modifiers and (geo_term or loc_anchor):
        # Geo/location + preference path.
        # Q1: venue + destination + (loc or geo) — precision-targeted
        if loc_anchor:
            _add(f"{primary} {loc_anchor} {destination}".strip())
        elif geo_term:
            _add(f"{primary} {destination} {geo_term}")
        # Q2: preference-aware, venue-anchored
        _add(f"{pref_modifiers[0]} {pref_primary} {destination}")
        # Q3: broad fallback or synonym + geo
        _add(f"{primary} {destination}")
        if frame.subtype_concepts:
            variants = _synonym_variants(frame.subtype_concepts[0])
            for variant in variants[1:2]:
                if len(queries) >= cap:
                    break
                if geo_term:
                    _add(f"{variant} {destination} {geo_term}")
                else:
                    _add(f"{variant} {destination}")

    else:
        # Original path (no soft preferences): venue + destination + geo/loc + synonyms.
        # Query 1: venue + destination + (location modifier OR geo hint).
        if loc_anchor:
            _add(f"{primary} {loc_anchor} {destination}".strip())
        elif geo_term:
            _add(f"{primary} {destination} {geo_term}")
        else:
            _add(f"{primary} {destination}")

        # Query 2: pure venue + destination — broader recall.
        _add(f"{primary} {destination}")

        # Query 3: venue synonym variant + destination + (loc anchor or geo).
        if frame.subtype_concepts:
            variants = _synonym_variants(frame.subtype_concepts[0])
            for variant in variants[1:3]:
                if len(queries) >= cap:
                    break
                if loc_anchor:
                    _add(f"{variant} {loc_anchor} {destination}".strip())
                elif geo_term:
                    _add(f"{variant} {destination} {geo_term}")
                else:
                    _add(f"{variant} {destination}")

        # Query 4 (only if room): venue + location anchor + geo hint together.
        if len(queries) < cap and loc_anchor and geo_term:
            _add(f"{primary} {loc_anchor} {geo_term}")

    # Fallback: if nothing generated, use normalized ask + destination
    if not queries:
        fallback = f"{(frame.normalized_ask or frame.literal_ask).strip()} {destination}"
        queries.append(_clean_query(fallback))

    logger.debug(
        "retrieval_planner: query=%r destination=%r geo=%r locs=%r pref_modifiers=%r → queries=%r",
        frame.literal_ask, destination, geo_hints, location_modifiers, pref_modifiers, queries,
    )

    return queries[:cap]


def _geo_query_term(geo_hint: str, destination: str) -> str:
    """Map an abstract geo hint to a provider-query-friendly string."""
    terms = _GEO_QUERY_TERMS.get(geo_hint.lower(), [])
    if not terms:
        return geo_hint
    # Prefer the first term unless it matches the destination itself
    for term in terms:
        if term.lower() not in destination.lower():
            return term
    return terms[0]
