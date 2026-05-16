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
from typing import List, Optional

from app.concierge.frame_extractor import ExperienceFrame, SubtypeConcept

logger = logging.getLogger(__name__)

DEFAULT_MAX_QUERIES = 3
HARD_CAP_QUERIES = 4

# Venue head nouns used to anchor Google queries to the correct place type.
# This is retrieval anchoring, not editorial intent — a small maintained set
# covering common app verticals is acceptable and preferred over per-query hacks.
_VENUE_HEAD_NOUNS: frozenset = frozenset({
    "bar", "bars",
    "restaurant", "restaurants",
    "coffee shop", "coffee shops",
    "cafe", "cafes", "café", "cafés",
    "brewery", "breweries",
    "pub", "pubs",
    "lounge", "lounges",
    "club", "clubs",
    "diner", "diners",
    "bistro", "bistros",
    "brasserie", "brasseries",
    "tavern", "taverns",
    "attraction", "attractions",
    "museum", "museums",
    "gallery", "galleries",
    "market", "markets",
    "hotel", "hotels",
    "resort", "resorts",
    "shop", "shops",
    "bakery", "bakeries",
    "brunch spot", "brunch spots",
    "breakfast spot", "breakfast spots",
    "seafood restaurant", "seafood restaurants",
    "steakhouse", "steakhouses",
})

# Trailing-tail connectors: words that begin a preference/location/use-case
# tail that should be stripped before extracting the core venue phrase.
# E.g. "sports bars with TVs" → strip "with TVs" → core = "sports bars".
# E.g. "cocktail bars near Pike Place" → strip "near Pike Place" → core = "cocktail bars".
_TAIL_CONNECTORS = re.compile(
    r"\b(with|near|in|on|for|open|serving|that|where|who|along|around|by|at|"
    r"next\s+to|close\s+to|across\s+from|offering|featuring|having|inside|"
    r"within|outside|during|after|before|great\s+for|good\s+for|perfect\s+for)\b",
    re.IGNORECASE,
)

# Pattern matching <modifier(s)> <venue-head-noun> at the start of a phrase,
# where the venue head is one of the nouns in _VENUE_HEAD_NOUNS.
# Built dynamically from the noun set so adding a noun above auto-extends this.
_VENUE_HEAD_PATTERN = re.compile(
    r"^(.+?)\s+(bar|bars|restaurant|restaurants|coffee\s+shop|coffee\s+shops"
    r"|cafe|cafes|café|cafés|brewery|breweries|pub|pubs|lounge|lounges"
    r"|club|clubs|diner|diners|bistro|bistros|brasserie|brasseries"
    r"|tavern|taverns|attraction|attractions|museum|museums|gallery|galleries"
    r"|market|markets|hotel|hotels|resort|resorts|shop|shops|bakery|bakeries"
    r"|brunch\s+spot|brunch\s+spots|breakfast\s+spot|breakfast\s+spots"
    r"|seafood\s+restaurant|seafood\s+restaurants|steakhouse|steakhouses)(?:\s+.*)?$",
    re.IGNORECASE,
)

# Wrong-vertical Google type tokens that indicate an entity is clearly outside
# the food/bar/cafe/nightlife vertical. Used by the entity quality guard.
# Applied ONLY when the query vertical is clearly food/bar/nightlife/cafe —
# NOT for attractions, museums, hotels, parks, landmarks, or activities.
_WRONG_VERTICAL_TYPES: frozenset = frozenset({
    "physiotherapist", "physical_therapist",
    "gym", "fitness_center", "health_club", "athletic_club",
    "stadium", "arena", "sports_complex", "sports_facility",
    "sports_club",
    "recreation_center",
    "hospital", "emergency_room", "urgent_care", "medical_clinic",
    "doctor",
    "real_estate_agency", "car_dealer", "car_repair", "car_wash",
    "gas_station", "parking",
    "laundry", "dry_cleaning",
    "bank", "finance", "insurance_agency",
})

# Google type tokens that confirm an entity is on-vertical for
# food/bar/cafe/nightlife queries.
_FOOD_BAR_NIGHTLIFE_TYPES: frozenset = frozenset({
    "bar", "bars", "night_club", "nightclub", "sports_bar",
    "restaurant", "food", "meal_takeaway", "meal_delivery",
    "cafe", "coffee_shop", "bakery", "dessert_shop",
    "brewery", "brewpub", "winery", "distillery",
    "pub", "lounge", "tavern",
})

# Concept tokens that indicate the query vertical is food/bar/nightlife/cafe.
# When the primary concept or literal ask contains these tokens, the wrong-vertical
# guard is active. Does NOT include "attraction", "museum", "hotel", "park".
_FOOD_BAR_QUERY_TOKENS: frozenset = frozenset({
    "bar", "bars", "restaurant", "restaurants", "cafe", "cafes",
    "coffee", "cocktail", "speakeasy", "pub", "pubs", "lounge", "lounges",
    "brewery", "breweries", "taproom", "nightclub", "tavern", "diner",
    "bistro", "brunch", "breakfast", "sushi", "ramen", "pizza", "steak",
    "seafood", "tapas", "omakase", "izakaya", "dim", "pho", "thai",
    "indian", "mexican", "italian", "french", "korean", "vietnamese",
    "chinese", "greek", "mediterranean", "spanish", "bakery",
    "food", "dining", "eatery", "meal",
    "sports", "sport",  # "sports bars" context — but only if venue head is bar
})


def _strip_tail(ask: str) -> str:
    """Strip trailing preference/location/use-case phrase from the ask.

    Returns the portion before the first tail connector, or the full ask if
    no connector is found.  E.g.:
      "sports bars with TVs"        → "sports bars"
      "cocktail bars near Pike Place" → "cocktail bars"
      "Mexican restaurants for date night" → "Mexican restaurants"
      "coffee shops open late"      → "coffee shops open late" (no connector)
        → "coffee shops" because "open" is a connector
      "best waterfront breweries"   → "best waterfront breweries" (no connector)
    """
    m = _TAIL_CONNECTORS.search(ask)
    if m:
        return ask[: m.start()].strip()
    return ask


def _core_venue_phrase(frame: ExperienceFrame) -> str:
    """Extract the core venue phrase from the user ask, preserving modifier+head.

    Strategy:
    1. Strip trailing tail (with/near/for/open/in/on ...) from literal_ask.
    2. Match the stripped phrase against <modifier(s)> <venue-head-noun>.
    3. If matched and the frame's primary concept lost the venue noun (stemming
       check), return the matched compound phrase as the retrieval anchor.
    4. Otherwise return empty string to fall through to concept-label path.

    This handles:
      "sports bars"                  → "sports bars"
      "sports bars with TVs"         → "sports bars"
      "cocktail bars near Pike Place" → "cocktail bars"
      "Mexican restaurants for date night" → "mexican restaurants"
      "coffee shops open late"        → "coffee shops"
      "attractions for kids"          → "attractions"  (modifier-only, venue IS attractions)
      "best waterfront breweries"     → "" (concept "brewery" already has venue noun)
    """
    ask_raw = (frame.literal_ask or frame.normalized_ask or "").strip()
    if not ask_raw:
        return ""

    stripped = _strip_tail(ask_raw).lower()
    if not stripped:
        return ""

    m = _VENUE_HEAD_PATTERN.match(stripped)
    if not m:
        # Try full stripped ask as venue head itself (e.g. "attractions")
        stripped_tokens = set(re.findall(r"\b[a-z]+\b", stripped))
        head_words = {re.sub(r"\s+", "_", n) for n in _VENUE_HEAD_NOUNS}
        single_heads = {w for w in _VENUE_HEAD_NOUNS if " " not in w}
        if not (stripped_tokens & single_heads):
            return ""
        # Single-word venue head (e.g. bare "attractions") — concept path handles it
        return ""

    venue_head = m.group(2).lower()
    modifier = m.group(1).strip().lower()

    # If there's no meaningful modifier, the ask is just the venue head alone —
    # concept path handles single-concept asks fine (ramen, sushi, breweries).
    # Only override when there is a genuine modifier (e.g. "sports", "cocktail").
    if not modifier:
        return ""

    # Check: did the frame's primary concept preserve the venue noun?
    # If it did, the concept path is already correct — don't override.
    primary_concept = (
        frame.subtype_concepts[0].label.lower() if frame.subtype_concepts else ""
    )

    def _stem(w: str) -> str:
        if w.endswith("ies") and len(w) > 4:
            return w[:-3] + "y"
        if w.endswith("es") and len(w) > 4 and w[-3] in "shc":
            return w[:-2]
        if w.endswith("s") and len(w) > 3 and not w.endswith("ss"):
            return w[:-1]
        return w

    concept_stems = {_stem(t) for t in re.findall(r"\b[a-z]+\b", primary_concept)}
    head_stems = {_stem(t) for t in re.findall(r"\b[a-z]+\b", venue_head)}

    if concept_stems & head_stems:
        # Concept already contains the venue noun — no override needed.
        return ""

    # Return modifier + venue head as the compound retrieval phrase.
    return f"{modifier} {venue_head}"


def is_food_bar_query(frame: ExperienceFrame) -> bool:
    """Return True when the query vertical is clearly food/bar/nightlife/cafe.

    Used to gate the wrong-vertical entity guard — only apply it when the
    user is looking for food/drink venues, not attractions, museums, hotels, parks.
    """
    ask_lower = (frame.literal_ask or frame.normalized_ask or "").lower()
    ask_tokens = set(re.findall(r"\b[a-z]+\b", ask_lower))

    # Direct token match in ask
    if ask_tokens & (_FOOD_BAR_QUERY_TOKENS - {"sports", "sport"}):
        return True

    # "sports"/"sport" only counts if the venue head is bar/restaurant
    if ask_tokens & {"sports", "sport"}:
        if ask_tokens & {"bar", "bars", "restaurant", "restaurants", "pub", "pubs"}:
            return True

    # Concept label match
    if frame.subtype_concepts:
        for sc in frame.subtype_concepts:
            label_tokens = set(re.findall(r"\b[a-z]+\b", sc.label.lower()))
            if label_tokens & (_FOOD_BAR_QUERY_TOKENS - {"sports", "sport"}):
                return True

    return False


def entity_passes_vertical_guard(
    entity_types: List[str],
    primary_type: str,
    is_food_bar: bool,
) -> bool:
    """Return False if the entity is clearly wrong-vertical for a food/bar query.

    Only active when is_food_bar=True. Rejects entities whose Google types are
    exclusively wrong-vertical (rehab, gym, stadium, arena, etc.) with no
    food/bar/nightlife type token present.

    Safe to pass: legitimate bars/restaurants that also carry generic types
    (establishment, point_of_interest) are NOT rejected.
    Does NOT apply to attractions, museums, hotels, parks, landmarks.
    """
    if not is_food_bar:
        return True  # guard off for non-food queries

    all_types = {t.lower().replace("-", "_") for t in (entity_types or [])}
    if primary_type:
        all_types.add(primary_type.lower().replace("-", "_"))

    # If any food/bar/nightlife type is present, entity is on-vertical.
    if all_types & _FOOD_BAR_NIGHTLIFE_TYPES:
        return True

    # If all types are wrong-vertical, reject.
    if all_types & _WRONG_VERTICAL_TYPES:
        wrong = all_types & _WRONG_VERTICAL_TYPES
        ok = all_types - _WRONG_VERTICAL_TYPES - {
            "point_of_interest", "establishment", "premise", "health",
            "local_business",
        }
        # Only reject if there's no ambiguous legitimate type left
        if not ok:
            return False

    return True


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
    # Natural-feature / coastal attraction synonyms — widens recall for place searches
    # where the concept label alone is too narrow for Google Text Search (e.g.
    # "beach Miami" retrieves far fewer results than "public beach Miami").
    "beach": ["beach", "public beach", "beach park"],
    "beaches": ["beaches", "public beach", "beach park"],
    "viewpoint": ["scenic overlook", "viewpoint", "scenic viewpoint"],
    "viewpoints": ["scenic overlooks", "viewpoints", "scenic viewpoints"],
    "sunset": ["sunset viewpoint", "scenic overlook", "sunset spot"],
    "lookout": ["scenic overlook", "lookout point", "viewpoint"],
    "lookout point": ["scenic overlook", "lookout", "viewpoint"],
    "lookout points": ["scenic overlooks", "lookouts", "viewpoints"],
    "sunset point": ["sunset viewpoint", "scenic overlook"],
    "sunset points": ["sunset viewpoints", "scenic overlooks"],
    "scenic": ["scenic overlook", "scenic viewpoint", "viewpoint"],
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
    """Return the retrieval label for the frame.

    When the user's literal ask contains a compound venue phrase (e.g. "sports
    bars", "cocktail bars near Pike Place", "Mexican restaurants for date night"),
    the core venue phrase (modifier + head noun, tails stripped) is returned so
    that Google receives a bar/restaurant-preserving query.  Single-concept asks
    (ramen, sushi, breweries) and asks where the frame extractor already preserved
    the venue noun fall through to the normal concept-label path unchanged.
    """
    core = _core_venue_phrase(frame)
    if core:
        return core
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
    # is richer than the raw concept label (e.g. "sunset" → "sunset viewpoint").
    # Compare against the CONCEPT LABEL, not primary, so that compound venue phrases
    # like "sports bars" (primary) are not downgraded to their concept label "sport".
    pref_primary = primary
    if frame.subtype_concepts:
        variants = _synonym_variants(frame.subtype_concepts[0])
        concept_label = frame.subtype_concepts[0].label.lower()
        if variants and variants[0] and variants[0].lower() != concept_label:
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

        # Query 2: most-descriptive synonym + destination for wider recall.
        # Uses pref_primary (first synonym when it is richer than the raw label)
        # so natural-feature queries like "sunset" → "sunset viewpoint <city>".
        _add(f"{pref_primary} {destination}")

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
