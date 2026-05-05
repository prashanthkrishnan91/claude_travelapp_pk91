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

    # -- Query 1: primary concept + destination (+ most salient geo hint if present)
    if geo_hints:
        # First: concept + destination + first geo hint
        geo_term = geo_hints[0]
        q1_geo = _geo_query_term(geo_term, destination)
        _add(f"{primary} {destination} {q1_geo}" if q1_geo else f"{primary} {destination}")
    else:
        _add(f"{primary} {destination}")

    # -- Query 2: synonym variant + destination
    if frame.subtype_concepts:
        variants = _synonym_variants(frame.subtype_concepts[0])
        for variant in variants[1:3]:  # try up to 2 synonyms
            if len(queries) >= cap:
                break
            if geo_hints:
                geo_term = _geo_query_term(geo_hints[0], destination)
                _add(f"{variant} {destination} {geo_term}" if geo_term else f"{variant} {destination}")
            else:
                _add(f"{variant} {destination}")

    # -- Query 3: concept + destination (no geo modifier, broader fallback)
    if len(queries) < cap:
        _add(f"{primary} {destination}")

    # -- Fallback: if nothing generated, use normalized ask + destination
    if not queries:
        fallback = f"{(frame.normalized_ask or frame.literal_ask).strip()} {destination}"
        queries.append(_clean_query(fallback))

    logger.debug(
        "retrieval_planner: query=%r destination=%r geo=%r → queries=%r",
        frame.literal_ask, destination, geo_hints, queries,
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
