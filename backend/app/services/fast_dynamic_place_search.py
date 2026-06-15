"""Fast Dynamic Place Search v1 — natural-language search, fast verified cards.

Feature flag: CONCIERGE_FAST_DYNAMIC_PLACE_SEARCH_V1_ENABLED (default False)

Root causes addressed:
- "tapas bar" collapsing to cocktail bars: intent detection hits _NIGHTLIFE_PAT
  on "bar" and routes to the nightlife search query "best cocktail bars..." This
  service preserves the literal user query and routes it directly to Google Places.
- 126s latency: the old pipeline (Tavily article extraction → serial candidate
  verification → serial Google verification → reason generation per card) is
  replaced by a single bounded Google Places text_search call + deterministic
  reason building. Target: 3-8 seconds.

Architecture:
  1. Parse user query deterministically: preserve literal intent (tapas stays tapas).
  2. Direct Google Places text_search with canonical_query + destination.
  3. Filter and rank by OPERATIONAL + category fit score.
  4. Build dynamic evidence-grounded reasons deterministically (no per-card LLM).
  5. Return LiveResearchResult with verified cards.

Trust gates:
  - Only businessStatus == OPERATIONAL cards are addable.
  - category_score < 0.2 → excluded (intent mismatch).
  - Place ID dedup against prior shown cards via prior_identity_keys.
  - No fake/free-form cards. Every card comes from a Google Places result.
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

PROVIDER_NAME = "google_places_fast_dynamic"
MAX_CANDIDATES: int = 15
_GOOGLE_ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
_PLACES_FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.businessStatus",
        "places.types",
        "places.rating",
        "places.userRatingCount",
        "places.priceLevel",
        "places.priceRange",
        "places.googleMapsUri",
        "places.websiteUri",
    ]
)
# SKU note: priceLevel is Basic data (no extra cost). priceRange is Atmosphere
# data (higher SKU tier). Both are safe to request; absent fields are silently
# omitted by Google — no card is dropped when priceRange is unavailable.

# Google priceLevel → human label (used to prefix reasons when relevant)
_PRICE_LEVEL_LABEL: Dict[str, str] = {
    "PRICE_LEVEL_INEXPENSIVE": "budget-friendly",
    "PRICE_LEVEL_MODERATE": "mid-range",
    "PRICE_LEVEL_EXPENSIVE": "upscale",
    "PRICE_LEVEL_VERY_EXPENSIVE": "fine-dining",
}

# Google priceLevel → UI symbol (shown in card subheader)
_PRICE_LEVEL_SYMBOL: Dict[str, str] = {
    "PRICE_LEVEL_FREE": "Free",
    "PRICE_LEVEL_INEXPENSIVE": "$",
    "PRICE_LEVEL_MODERATE": "$$",
    "PRICE_LEVEL_EXPENSIVE": "$$$",
    "PRICE_LEVEL_VERY_EXPENSIVE": "$$$$",
}

# Numeric sort order for value-aware ranking (lower = cheaper)
_PRICE_LEVEL_ORDER: Dict[str, int] = {
    "PRICE_LEVEL_FREE": 0,
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
}
# Unknown / absent price sorts AFTER all known tiers so missing data is never
# treated as a cheaper signal (do not default to MODERATE = 2).
_UNKNOWN_PRICE_ORDER = len(_PRICE_LEVEL_ORDER)  # 5
_OPERATIONAL = "OPERATIONAL"

# Cuisine/subtype keywords that should be passed through literally to Google.
# These preserve fine-grained user intent that coarse intent detection loses.
_SUBTYPE_KEYWORDS: List[str] = [
    "tapas",
    "sushi",
    "ramen",
    "omakase",
    "dim sum",
    "pho",
    "pizza",
    "seafood",
    "steak",
    "steakhouse",
    "bbq",
    "barbecue",
    "brunch",
    "breakfast",
    "vegan",
    "vegetarian",
    "thai",
    "indian",
    "korean",
    "vietnamese",
    "french",
    "italian",
    "mexican",
    "greek",
    "mediterranean",
    "japanese",
    "chinese",
    "spanish",
    "taqueria",
    "izakaya",
    "bistro",
]

_VIBE_KEYWORDS: List[str] = [
    "romantic",
    "date night",
    "upscale",
    "casual",
    "cozy",
    "family",
    "trendy",
    "lively",
    "quiet",
    "intimate",
    "fancy",
]

_CONSTRAINT_KEYWORDS: List[str] = [
    "waterfront",
    "rooftop",
    "outdoor",
    "patio",
    "view",
    "lake view",
    "river view",
    "ocean view",
    "lake",
    "river",
    "ocean",
    "water",
    "skyline",
    "terrace",
]

_NEGATIVE_PATTERNS: List[str] = [
    "not too loud",
    "not loud",
    "not too crowded",
    "not crowded",
    "not touristy",
    "not expensive",
    "not too expensive",
]

# Google cuisine-specific place types → display label
_GOOGLE_TYPE_TO_CUISINE_LABEL: Dict[str, str] = {
    "mexican_restaurant": "Mexican Restaurant",
    "italian_restaurant": "Italian Restaurant",
    "japanese_restaurant": "Japanese Restaurant",
    "sushi_restaurant": "Sushi Restaurant",
    "ramen_restaurant": "Ramen Restaurant",
    "chinese_restaurant": "Chinese Restaurant",
    "thai_restaurant": "Thai Restaurant",
    "french_restaurant": "French Restaurant",
    "indian_restaurant": "Indian Restaurant",
    "korean_restaurant": "Korean Restaurant",
    "vietnamese_restaurant": "Vietnamese Restaurant",
    "mediterranean_restaurant": "Mediterranean Restaurant",
    "greek_restaurant": "Greek Restaurant",
    "spanish_restaurant": "Spanish Restaurant",
    "steak_house": "Steakhouse",
    "seafood_restaurant": "Seafood Restaurant",
    "pizza_restaurant": "Pizza Restaurant",
    "brunch_restaurant": "Brunch Restaurant",
    "breakfast_restaurant": "Breakfast Restaurant",
    "american_restaurant": "American Restaurant",
    "hamburger_restaurant": "Burger Restaurant",
    "cocktail_bar": "Cocktail Bar",
    "wine_bar": "Wine Bar",
    "bar": "Bar",
    "night_club": "Nightclub",
}

# Cuisine keyword → Google place types that confirm a match
_CUISINE_TO_GOOGLE_TYPES: Dict[str, Set[str]] = {
    "tapas": {"spanish_restaurant", "bar_and_grill"},
    "sushi": {"sushi_restaurant", "japanese_restaurant"},
    "ramen": {"ramen_restaurant", "japanese_restaurant"},
    "japanese": {"japanese_restaurant", "sushi_restaurant", "ramen_restaurant"},
    "italian": {"italian_restaurant"},
    "mexican": {"mexican_restaurant"},
    "french": {"french_restaurant"},
    "chinese": {"chinese_restaurant"},
    "thai": {"thai_restaurant"},
    "indian": {"indian_restaurant"},
    "mediterranean": {"mediterranean_restaurant", "greek_restaurant"},
    "greek": {"greek_restaurant"},
    "korean": {"korean_restaurant"},
    "vietnamese": {"vietnamese_restaurant"},
    "spanish": {"spanish_restaurant"},
    "steakhouse": {"steak_house"},
    "steak": {"steak_house"},
    "seafood": {"seafood_restaurant"},
    "pizza": {"pizza_restaurant"},
    "brunch": {"brunch_restaurant", "breakfast_restaurant"},
    "breakfast": {"breakfast_restaurant", "brunch_restaurant"},
    "bbq": {"american_restaurant"},
    "barbecue": {"american_restaurant"},
}


def _format_display_price(
    price_level: Optional[str],
    price_range: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Return a compact UI price string from Google price fields, or None.

    Prefers priceRange ("$10–20") over priceLevel ("$$").
    Never exposes raw enum names.
    """
    if price_range and isinstance(price_range, dict):
        start = price_range.get("startPrice") or {}
        end = price_range.get("endPrice") or {}
        if isinstance(start, dict) and isinstance(end, dict):
            try:
                start_units = int(start.get("units") or 0)
                end_units = int(end.get("units") or 0)
                if start_units > 0 or end_units > 0:
                    currency = start.get("currencyCode") or end.get("currencyCode") or "USD"
                    symbol = "$" if currency == "USD" else currency
                    return f"{symbol}{start_units}–{end_units}"
            except (TypeError, ValueError):
                pass
    if price_level:
        return _PRICE_LEVEL_SYMBOL.get(price_level)
    return None


@dataclass
class ParsedPlaceQuery:
    """Structured representation of a natural-language place query.

    Preserves the user's literal ask as canonical_query. Extra fields
    are used for reason building and category scoring only — they never
    override the literal Google search query.
    """

    canonical_query: str
    destination: str
    search_query: str = ""  # canonical_query + destination
    cuisine: Optional[str] = None  # detected subtype ("tapas", "sushi", ...)
    place_type: str = "restaurant"  # "restaurant" | "bar" | "restaurant_or_bar"
    vibe: Optional[str] = None
    constraint: Optional[str] = None
    negative_constraint: Optional[str] = None
    prefer_lower_price: bool = False  # True when query signals cheaper/budget/affordable intent


_WHITESPACE_RE = re.compile(r"\s+")


def parse_place_query(user_query: str, destination: str) -> ParsedPlaceQuery:
    """Parse a natural-language place query into a structured intent.

    Deterministic. The user's literal phrase is preserved as canonical_query
    and used directly as the Google Places search query. This ensures "tapas
    bar" → Google query "tapas bar Chicago", not "cocktail bars and nightlife".
    """
    q = (user_query or "").strip()
    q_low = q.lower()

    # Cuisine / subtype detection
    cuisine: Optional[str] = None
    for kw in _SUBTYPE_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", q_low):
            cuisine = kw
            break

    # Vibe detection
    vibe: Optional[str] = None
    for v in _VIBE_KEYWORDS:
        if v in q_low:
            vibe = v
            break

    # Constraint detection
    constraint: Optional[str] = None
    for c in _CONSTRAINT_KEYWORDS:
        if re.search(r"\b" + re.escape(c) + r"\b", q_low):
            constraint = c
            break

    # Negative constraint detection
    negative: Optional[str] = None
    for n in _NEGATIVE_PATTERNS:
        if n in q_low:
            negative = n
            break

    # Place type: preserve literal bar/restaurant signals
    is_cocktail_bar = bool(re.search(r"\bcocktail bar(s)?\b", q_low))
    is_wine_bar = bool(re.search(r"\bwine bar(s)?\b", q_low))
    is_bar_explicit = bool(re.search(r"\bbar(s)?\b", q_low)) and not cuisine
    has_restaurant_signal = bool(
        re.search(
            r"\b(restaurant(s)?|dining|dinner|lunch|breakfast|brunch|food|cuisine|eat)\b",
            q_low,
        )
    )

    if is_cocktail_bar or is_wine_bar:
        place_type = "bar"
    elif is_bar_explicit and cuisine:
        # "tapas bar" = restaurant-first with bar vibes, not generic nightlife
        place_type = "restaurant_or_bar"
    elif is_bar_explicit:
        place_type = "bar"
    elif has_restaurant_signal:
        place_type = "restaurant"
    else:
        place_type = "restaurant"

    # Build the final search query: preserve user's literal ask + destination
    # Strip negative qualifiers so they don't confuse Google
    core = q
    if negative:
        core = re.sub(re.escape(negative), "", core, flags=re.IGNORECASE).strip()
    core = _WHITESPACE_RE.sub(" ", core).strip()
    search_query = f"{core} {destination}".strip()

    prefer_lower_price = bool(
        re.search(r"\b(?:cheap(?:er)?|budget|affordable|lower[- ]price)\b", q_low)
    )

    return ParsedPlaceQuery(
        canonical_query=q,
        destination=destination,
        search_query=search_query,
        cuisine=cuisine,
        place_type=place_type,
        vibe=vibe,
        constraint=constraint,
        negative_constraint=negative,
        prefer_lower_price=prefer_lower_price,
    )


def _extract_area_from_address(address: str, destination: str) -> Optional[str]:
    """Extract a short neighborhood/area label from a full formatted address."""
    if not address:
        return None
    parts = [p.strip() for p in address.split(",")]
    dest_lower = (destination or "").lower()
    for part in parts:
        p = part.strip()
        # Skip parts with digits (street numbers), country codes, state abbreviations,
        # the destination city itself, and postal codes.
        if not p:
            continue
        if any(c.isdigit() for c in p):
            continue
        if len(p) <= 2:
            continue
        if p.lower() == dest_lower:
            continue
        if p.lower() in {"usa", "us", "il", "ny", "ca", "tx", "fl", "wa"}:
            continue
        return p
    return None


def _bayesian_score(rating: Optional[float], review_count: Optional[int]) -> float:
    if rating is None:
        return 0.0
    v = float(max(0, review_count or 0))
    m = 80.0
    c = 4.0
    r = float(rating)
    return ((v / (v + m)) * r) + ((m / (v + m)) * c)


def _category_score(
    place: Dict[str, Any],
    parsed: ParsedPlaceQuery,
) -> float:
    """Score 0.0-1.0 for how well a Google place matches the parsed query.

    Returns -1.0 when the place must be excluded (not OPERATIONAL).
    Returns < 0.2 for intent mismatches (filtered out by caller).
    """
    if place.get("businessStatus") != _OPERATIONAL:
        return -1.0

    types = [(t or "").lower() for t in (place.get("types") or [])]
    types_set = set(types)
    cuisine = (parsed.cuisine or "").lower()
    place_type = parsed.place_type

    # Hard match: cuisine keyword in the Google place name
    name = ((place.get("displayName") or {}).get("text") or "").lower()

    if cuisine:
        cuisine_types = _CUISINE_TO_GOOGLE_TYPES.get(cuisine, set())

        # "tapas" special: Spanish restaurant or restaurant with tapas in name
        if cuisine == "tapas":
            if "tapas" in name:
                return 1.0
            if "spanish_restaurant" in types_set:
                return 0.9
            if any(t in types_set for t in ("restaurant", "food", "bar_and_grill")):
                return 0.65
            if any(t in types_set for t in ("bar", "cocktail_bar", "night_club")):
                return 0.25  # Low but still searchable
            return 0.15

        # Standard cuisine type match via Google types
        if cuisine_types and any(t in types_set for t in cuisine_types):
            return 1.0

        # Name contains cuisine keyword with restaurant-compatible type
        restaurant_compat = {"restaurant", "food", "meal_takeaway", "meal_delivery"}
        if cuisine in name and any(t in types_set for t in restaurant_compat):
            return 0.8

        # Generic restaurant (no cuisine type match) — penalize
        if any(t in types_set for t in restaurant_compat):
            return 0.35

        # Bar/nightlife with no cuisine match
        if any(t in types_set for t in ("bar", "cocktail_bar", "night_club")):
            return 0.15

        return 0.2

    # No cuisine specified — score by place_type
    if place_type == "bar":
        if any(t in types_set for t in ("cocktail_bar", "bar", "night_club", "wine_bar")):
            return 1.0
        if any(t in types_set for t in ("bar_and_grill",)):
            return 0.7
        if any(t in types_set for t in ("restaurant", "food")):
            return 0.35
        return 0.2

    if place_type in ("restaurant", "restaurant_or_bar"):
        if any(t in types_set for t in ("restaurant", "food", "meal_takeaway", "bakery", "cafe", "coffee_shop")):
            return 0.9
        if any(t in types_set for t in ("bar_and_grill",)):
            return 0.75 if place_type == "restaurant_or_bar" else 0.5
        if any(t in types_set for t in ("bar", "cocktail_bar", "night_club")):
            return 0.4 if place_type == "restaurant_or_bar" else 0.2
        return 0.35

    return 0.5


def _derive_cuisine_label(types: List[str], cuisine_hint: Optional[str]) -> str:
    """Derive a user-facing cuisine label from Google types + parsed cuisine."""
    for gt in types:
        label = _GOOGLE_TYPE_TO_CUISINE_LABEL.get((gt or "").lower())
        if label:
            return label

    if cuisine_hint:
        c = cuisine_hint.strip().lower()
        if c == "tapas":
            return "Tapas / Spanish"
        if c in ("bbq", "barbecue"):
            return "BBQ Restaurant"
        if c == "brunch":
            return "Brunch Spot"
        return c.title() + " Restaurant"

    return "Restaurant"


def _review_tier(review_count: Optional[int]) -> str:
    """Translate review volume into a meaningful signal phrase."""
    if not review_count:
        return ""
    if review_count >= 1500:
        return "one of the most-reviewed"
    if review_count >= 400:
        return "consistently well-rated"
    if review_count >= 100:
        return "well-regarded"
    return ""


def _build_dynamic_why(
    *,
    place_name: str,
    types: List[str],
    cuisine_label: str,
    address: Optional[str],
    rating: Optional[float],
    review_count: Optional[int],
    price_level: Optional[str],
    parsed: ParsedPlaceQuery,
) -> str:
    """Build a concise, dynamic, evidence-grounded reason for this card.

    Rules:
    - Never repeat rating counts as the whole reason — use tier language instead.
    - Never invent vibes, awards, or attributes not present in the data.
    - Always reference the user's specific ask.
    - Use price level and review tier when available.
    - Max 160 chars, 1-2 sentences.
    """
    cuisine = (parsed.cuisine or "").lower()
    constraint = parsed.constraint
    vibe = parsed.vibe
    negative = parsed.negative_constraint
    dest = parsed.destination

    area = _extract_area_from_address(address or "", dest)
    loc_part = f" in {area}" if area else ""

    price_label = _PRICE_LEVEL_LABEL.get(price_level or "", "")
    tier = _review_tier(review_count)

    # Short rating badge appended only when it fits and adds signal
    rating_badge = ""
    if rating is not None:
        rating_badge = f" ({rating:.1f} ★)"

    def _clip(text: str) -> str:
        return text[:160]

    def _with_badge(base: str) -> str:
        if rating_badge and len(base) + len(rating_badge) <= 155:
            return _clip(base + rating_badge + ".")
        return _clip(base + ".")

    # ── Tapas-specific ────────────────────────────────────────────────────────
    if cuisine == "tapas":
        if vibe in ("romantic", "date night"):
            base = f"A romantic tapas/small-plates pick{loc_part}, well-suited for a dinner date"
        elif negative and "loud" in negative:
            base = f"A tapas/small-plates spot{loc_part} with a more relaxed atmosphere than a bar crawl"
        elif constraint:
            base = f"A tapas-focused spot{loc_part}; verify {constraint} seating when booking"
        else:
            prefix = f"{price_label} " if price_label else ""
            base = f"A {prefix}tapas/small-plates match{loc_part}, not a generic cocktail bar"
        return _with_badge(base)

    # ── Sushi/Japanese + location constraint ─────────────────────────────────
    if cuisine in ("sushi", "japanese") and constraint in (
        "waterfront", "water", "view", "lake", "river", "lake view", "river view",
    ):
        prefix = f"{price_label} " if price_label else ""
        base = f"A {prefix}sushi option{loc_part}; verify {constraint} seating directly when booking"
        return _with_badge(base)

    # ── Generic cuisine + constraint ─────────────────────────────────────────
    if cuisine and constraint:
        prefix = f"{price_label} " if price_label else ""
        base = f"A {prefix}{cuisine} pick{loc_part}; verify {constraint} setting when booking"
        return _with_badge(base)

    # ── Cuisine + vibe ────────────────────────────────────────────────────────
    if cuisine and vibe:
        prefix = f"{price_label} " if price_label else ""
        if vibe in ("romantic", "date night"):
            base = f"A {prefix}{cuisine} option{loc_part} suited for a special dinner"
        else:
            base = f"A {vibe}, {prefix}{cuisine} restaurant{loc_part}"
        return _with_badge(base)

    # ── Cuisine only ─────────────────────────────────────────────────────────
    if cuisine:
        prefix = f"{price_label} " if price_label else ""
        if tier:
            base = f"A {tier} {prefix}{cuisine} option{loc_part}"
        elif cuisine in place_name.lower():
            base = f"A {prefix}{cuisine} specialist{loc_part}"
        else:
            cat = cuisine_label.lower() if cuisine_label else cuisine
            base = f"A {prefix}{cat}{loc_part}"
        return _with_badge(base)

    # ── Bar (no cuisine) ─────────────────────────────────────────────────────
    types_set = {(t or "").lower() for t in types}
    if parsed.place_type == "bar" or any(t in types_set for t in ("cocktail_bar", "wine_bar", "bar", "night_club")):
        # Use the most specific type label available
        if "cocktail_bar" in types_set:
            cat = "craft cocktail bar"
        elif "wine_bar" in types_set:
            cat = "wine bar"
        elif "night_club" in types_set:
            cat = "nightclub"
        else:
            cat = cuisine_label.lower() or "bar"
        prefix = f"{price_label} " if price_label else ""
        if tier:
            base = f"A {tier} {prefix}{cat}{loc_part}"
        elif constraint:
            base = f"A {prefix}{cat}{loc_part} with {constraint} access"
        else:
            base = f"A {prefix}{cat}{loc_part}"
        return _with_badge(base)

    # ── Constraint without cuisine ────────────────────────────────────────────
    if constraint:
        cat = cuisine_label.lower() or "dining option"
        prefix = f"{price_label} " if price_label else ""
        base = f"A {prefix}{cat}{loc_part}; verify {constraint} setting when booking"
        return _with_badge(base)

    # ── Generic fallback — still evidence-grounded ────────────────────────────
    cat = cuisine_label.lower() or "restaurant"
    prefix = f"{price_label} " if price_label else ""
    if tier:
        base = f"A {tier} {prefix}{cat}{loc_part}"
    else:
        base = f"A {prefix}{cat}{loc_part}"
    return _with_badge(base)


class FastDynamicPlaceSearch:
    """Fast, direct Google Places pipeline for AI Concierge place searches.

    Bypasses Tavily article extraction and serial candidate verification.
    Uses a single bounded Google Places text_search call per request.
    Target latency: 3–8 seconds for a fresh search (vs 126s old pipeline).
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        timeout: float = 6.0,
        max_candidates: int = MAX_CANDIDATES,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.getenv("GOOGLE_PLACES_API_KEY", "")
        self._timeout = timeout
        self._max_candidates = max_candidates

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def search(
        self,
        *,
        user_query: str,
        destination: str,
        intent: str,
        prior_identity_keys: Optional[Set[str]] = None,
    ) -> "LiveResearchResult":  # type: ignore[name-defined]
        from app.services.live_research import LiveResearchResult
        from app.models.concierge import SOURCE_LIVE_SEARCH, SOURCE_UNAVAILABLE

        t_start = time.monotonic()

        if not self.available:
            logger.warning(
                "fast_dynamic_place_search: Google Places API key unavailable"
            )
            return LiveResearchResult(source_status=SOURCE_UNAVAILABLE)

        # Step 1: Parse query
        t_parse = time.monotonic()
        parsed = parse_place_query(user_query, destination)
        extraction_ms = int((time.monotonic() - t_parse) * 1000)

        logger.info(
            "fast_dynamic_place_search.parse query=%r destination=%r "
            "cuisine=%r place_type=%s vibe=%r constraint=%r negative=%r "
            "search_query=%r",
            user_query, destination,
            parsed.cuisine, parsed.place_type, parsed.vibe,
            parsed.constraint, parsed.negative_constraint,
            parsed.search_query,
        )

        # Step 2: Direct Google Places text_search
        t_search = time.monotonic()
        raw_places = self._google_text_search(parsed.search_query, self._max_candidates)
        google_search_ms = int((time.monotonic() - t_search) * 1000)
        candidate_count = len(raw_places)

        if not raw_places:
            logger.warning(
                "fast_dynamic_place_search: no Google results "
                "query=%r destination=%r google_search_ms=%d",
                user_query, destination, google_search_ms,
            )
            return LiveResearchResult(provider_name=PROVIDER_NAME)

        # Step 3: Filter and rank
        t_verify = time.monotonic()
        candidates = self._filter_and_rank(
            raw_places,
            parsed=parsed,
            prior_identity_keys=prior_identity_keys,
        )
        verify_ms = int((time.monotonic() - t_verify) * 1000)
        verified_count = len(candidates)

        # Step 4: Build cards with dynamic reasons
        t_reason = time.monotonic()
        restaurants = self._build_cards(candidates, parsed=parsed)
        reason_ms = int((time.monotonic() - t_reason) * 1000)
        filtered_count = len(restaurants)

        total_ms = int((time.monotonic() - t_start) * 1000)

        # Price signal telemetry — internal only, never surfaced in UI.
        cards_with_price_level = sum(
            1 for r in restaurants
            if getattr(getattr(r, "supporting_details", None), "price_level", None)
        )
        cards_with_price_range = sum(
            1 for r in restaurants
            if getattr(getattr(r, "supporting_details", None), "price_range", None)
        )
        cards_without_price_signal = filtered_count - cards_with_price_level

        logger.info(
            "fast_dynamic_place_search.timing "
            "fast_dynamic_enabled=true "
            "extraction_ms=%d "
            "google_search_ms=%d "
            "google_verify_or_details_ms=%d "
            "evidence_enrichment_ms=0 "
            "reason_generation_ms=%d "
            "total_ms=%d "
            "candidate_count=%d "
            "verified_count=%d "
            "filtered_count=%d "
            "final_unique_count=%d "
            "pool_hit=false "
            "provider_call=true "
            "reason_mode=deterministic "
            "cards_with_price_level=%d "
            "cards_with_price_range=%d "
            "cards_without_price_signal=%d "
            "prefer_lower_price=%s",
            extraction_ms, google_search_ms, verify_ms,
            reason_ms, total_ms,
            candidate_count, verified_count,
            filtered_count, filtered_count,
            cards_with_price_level, cards_with_price_range, cards_without_price_signal,
            parsed.prefer_lower_price,
        )

        return LiveResearchResult(
            restaurants=restaurants,
            source_status=SOURCE_LIVE_SEARCH,
            provider_name=PROVIDER_NAME,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _google_text_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Call Google Places text_search directly with a configurable result count."""
        if not self._api_key:
            return []
        try:
            import httpx
        except ImportError:
            logger.warning("fast_dynamic_place_search: httpx not installed")
            return []

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": _PLACES_FIELD_MASK,
        }
        body = {"textQuery": query, "maxResultCount": min(max_results, 20)}

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(_GOOGLE_ENDPOINT, headers=headers, json=body)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("fast_dynamic_place_search: Google API failed: %s", exc)
            return []

        return list(data.get("places") or [])

    def _filter_and_rank(
        self,
        raw_places: List[Dict[str, Any]],
        *,
        parsed: ParsedPlaceQuery,
        prior_identity_keys: Optional[Set[str]],
    ) -> List[Dict[str, Any]]:
        """Filter by OPERATIONAL + category fit ≥ 0.2, rank by combined score."""
        scored: List[tuple] = []
        for place in raw_places:
            place_id = place.get("id")

            # Dedup against prior shown cards
            if prior_identity_keys and place_id:
                if f"pid:{place_id}" in prior_identity_keys:
                    continue

            cat = _category_score(place, parsed)
            if cat < 0.0:  # not OPERATIONAL
                continue
            if cat < 0.2:  # intent mismatch
                continue

            rating = place.get("rating")
            review_count = place.get("userRatingCount")
            bayesian = _bayesian_score(rating, review_count)

            # Combined: category fit primary, bayesian secondary
            combined = (0.7 * cat) + (0.3 * min(1.0, bayesian / 5.0))
            scored.append((combined, place))

        if parsed.prefer_lower_price:
            # Post-retrieval value-aware sort: prefer lower price tier first,
            # then by combined quality score within the same tier.
            def _value_sort_key(item: tuple) -> tuple:
                combined, place = item
                pl = place.get("priceLevel")
                price_order = _PRICE_LEVEL_ORDER.get(pl, _UNKNOWN_PRICE_ORDER)
                return (price_order, -combined)
            scored.sort(key=_value_sort_key)
        else:
            scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored]

    def _build_cards(
        self,
        candidates: List[Dict[str, Any]],
        *,
        parsed: ParsedPlaceQuery,
    ) -> List["UnifiedRestaurantResult"]:  # type: ignore[name-defined]
        cards = []
        for place in candidates:
            card = self._to_card(place, parsed=parsed)
            if card is not None:
                cards.append(card)
        return cards

    def _to_card(
        self,
        place: Dict[str, Any],
        *,
        parsed: ParsedPlaceQuery,
    ) -> Optional["UnifiedRestaurantResult"]:  # type: ignore[name-defined]
        from app.models.concierge import (
            ConciergeDisplayFields,
            GoogleVerification,
            PlaceSupportingDetails,
            UnifiedRestaurantResult,
        )

        name_obj = place.get("displayName") or {}
        name = (
            name_obj.get("text") if isinstance(name_obj, dict) else str(name_obj or "")
        ).strip()
        if not name:
            return None

        place_id = place.get("id")
        types = [t for t in (place.get("types") or [])]
        rating = place.get("rating")
        review_count = place.get("userRatingCount")
        price_level: Optional[str] = place.get("priceLevel")
        price_range: Optional[Dict[str, Any]] = place.get("priceRange") or None
        address = (place.get("formattedAddress") or "").strip() or None
        maps_uri = place.get("googleMapsUri")
        website = place.get("websiteUri")
        _loc = place.get("location")
        lat: Optional[float] = _loc.get("latitude") if isinstance(_loc, dict) else None
        lng: Optional[float] = _loc.get("longitude") if isinstance(_loc, dict) else None

        cuisine_label = _derive_cuisine_label(types, parsed.cuisine)

        why = _build_dynamic_why(
            place_name=name,
            types=types,
            cuisine_label=cuisine_label,
            address=address,
            rating=rating,
            review_count=review_count,
            price_level=price_level,
            parsed=parsed,
        )

        rating_10 = round(rating * 2, 1) if rating is not None else None
        meta_line: Optional[str] = None
        if rating_10 is not None and review_count:
            meta_line = f"★ {rating_10:.1f} ({review_count:,} reviews)"
        elif rating_10 is not None:
            meta_line = f"★ {rating_10:.1f}"

        gv = GoogleVerification(
            provider="google_places",
            provider_place_id=place_id,
            name=name,
            formatted_address=address,
            lat=lat,
            lng=lng,
            business_status=_OPERATIONAL,
            google_maps_uri=maps_uri,
            website_uri=website,
            rating=rating,
            user_rating_count=review_count,
            types=types,
            confidence="high" if place_id else "medium",
            score=1.0,
        )

        dest = parsed.destination
        fallback_map = (
            f"https://maps.google.com/?q={name.replace(' ', '+')}+"
            f"{dest.replace(' ', '+')}"
        )

        display_price = _format_display_price(price_level, price_range)

        return UnifiedRestaurantResult(
            name=name,
            source="Google Places",
            cuisine=cuisine_label,
            neighborhood=address,
            rating=rating_10,
            review_count=review_count,
            summary=why,
            primary_reason=why,
            why_pick=why,
            verified_place=True,
            google_verification=gv,
            supporting_details=PlaceSupportingDetails(
                why_pick=why,
                meta_line=meta_line,
                address=address,
                category_label=cuisine_label,
                price_level=price_level or None,
                price_range=price_range or None,
            ),
            display=ConciergeDisplayFields(
                display_name=name,
                display_category=cuisine_label,
                display_meta_line=meta_line,
                display_why=why,
                display_price=display_price,
                display_badges=[],
                addability="addable",
                display_why_source="fast_dynamic_deterministic",
            ),
            maps_link=maps_uri or fallback_map,
            booking_link=website,
            tags=[],
        )


# ── Module-level singleton ────────────────────────────────────────────────────

_FAST_SEARCH_SINGLETON: Optional[FastDynamicPlaceSearch] = None


def get_fast_dynamic_search() -> FastDynamicPlaceSearch:
    """Return module-level FastDynamicPlaceSearch instance (process-local)."""
    global _FAST_SEARCH_SINGLETON
    if _FAST_SEARCH_SINGLETON is None:
        _FAST_SEARCH_SINGLETON = FastDynamicPlaceSearch()
    return _FAST_SEARCH_SINGLETON
