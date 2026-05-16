"""Semantic Retrieval v1 — end-to-end verified-card pipeline.

Feature flag: CONCIERGE_SEMANTIC_RETRIEVAL_V1_ENABLED (default False)

Pipeline (when flag ON, new_search, place-recommendation asks):
  1. ExperienceFrame extraction (open-vocabulary, deterministic)
  2. RetrievalPlanner → 1–3 Google Text Search queries
  3. Provider fanout (parallel, per-call deadlines)
  4. Verified Place Entity Layer (Google place id + OPERATIONAL + maps URI gates)
  5. SemanticRanker v1 (subtype_fit dominates, no hard category gate)
  6. MinimalEvidenceBundle per entity
  7. SafeReasonBuilder v1 (honest, ask-anchored, no hallucinated facts)
  8. TrustGate final pass (redundant safety check before card return)
  9. Structured observability log (one line, debuggable in one pass)
  10. Return LiveResearchResult with verified UnifiedRestaurantResult cards

When flag OFF: this module is never called. Existing pipeline is unchanged.
Yelp/Foursquare (Step 5.55) and Tavily/Serper editorial (Step 5.56) enrichment
run only when this module is active and API keys are present.
No SQL. No frontend changes. No personalization. No vector search.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Dict, FrozenSet, List, Optional, Set

logger = logging.getLogger(__name__)

PROVIDER_NAME = "semantic_retrieval_v1"
PIPELINE_VERSION = "semantic_retrieval_v1"
_MAX_CARDS = 8  # pool/ranking size; first response is capped separately by SLA config
# Minimum remaining budget (seconds) required to attempt LLM note generation.
# Below this threshold, skip the writer before calling it rather than submitting
# a call that cannot complete usefully within the remaining window.
_MIN_NOTE_GENERATION_BUDGET_S = 0.5

# Google type tokens that are incompatible with food/restaurant responses.
# An entity whose types contain ONLY these tokens (none of the food-compatible
# tokens below) is rejected from restaurant/place_recommendations results.
# This gate blocks "Only One Boutique" (womens_clothing_store) from appearing
# in restaurant responses.
_FOOD_INCOMPATIBLE_TYPES: frozenset = frozenset({
    "clothing_store", "womens_clothing_store", "mens_clothing_store",
    "shoe_store", "department_store", "shopping_mall", "boutique",
    "jewelry_store", "accessories_store", "sporting_goods_store",
    "home_goods_store", "furniture_store", "hardware_store",
    "electronics_store", "book_store", "toy_store", "pet_store",
    "florist", "art_gallery", "gift_shop",
    "gym", "fitness_center", "health_club", "yoga_studio", "spa",
    "beauty_salon", "hair_salon", "nail_salon", "barber_shop",
    "laundry", "dry_cleaning",
    "car_dealer", "car_rental", "auto_parts_store",
    "real_estate_agency", "insurance_agency", "travel_agency",
    "lawyer", "accountant",
})

# Food/restaurant-compatible Google type tokens. An entity with at least one of
# these tokens is eligible for restaurant responses regardless of other types.
_FOOD_COMPATIBLE_TYPES: frozenset = frozenset({
    "restaurant", "food", "cafe", "coffee_shop", "bakery", "bar",
    "meal_takeaway", "meal_delivery", "night_club",
    "brewery", "winery", "distillery",
    "ice_cream_shop", "donut_shop", "pizza_delivery",
    "sandwich_shop", "hamburger_restaurant", "fast_food_restaurant",
    "sushi_restaurant", "japanese_restaurant", "ramen_restaurant",
    "spanish_restaurant", "mexican_restaurant", "italian_restaurant",
    "french_restaurant", "chinese_restaurant", "thai_restaurant",
    "indian_restaurant", "korean_restaurant", "vietnamese_restaurant",
    "mediterranean_restaurant", "greek_restaurant", "american_restaurant",
    "steak_house", "seafood_restaurant", "pizza_restaurant",
    "brunch_restaurant", "breakfast_restaurant", "dessert_shop",
    "wine_bar", "cocktail_bar", "gastropub", "pub",
})

# Concept-label words that must never be used as category label prefixes.
# These are modifier/refinement words that can become the concept label when the
# query is a modifier-only phrase (e.g., "casual Mediterranean"). Using them as a
# category label prefix produces nonsense like "Only Restaurant" or "Casual Restaurant".
_CONCEPT_LABEL_BLOCKLIST: frozenset = frozenset({
    "only", "just", "more", "less", "make", "filter", "show", "get",
    "casual", "fancy", "cheap", "cheaper", "expensive", "affordable",
    "nearby", "closer", "outdoor", "outside",
})

# Google priceLevel → UI symbol (mirrors fast_dynamic_place_search._PRICE_LEVEL_SYMBOL)
_PRICE_LEVEL_SYMBOL: Dict[str, str] = {
    "PRICE_LEVEL_FREE": "Free",
    "PRICE_LEVEL_INEXPENSIVE": "$",
    "PRICE_LEVEL_MODERATE": "$$",
    "PRICE_LEVEL_EXPENSIVE": "$$$",
    "PRICE_LEVEL_VERY_EXPENSIVE": "$$$$",
}

# ── Natural-feature precision gate (Step 4.7) ─────────────────────────────────
# Concept labels (from frame extractor, after singularization) that indicate the
# user is searching for a natural geographic feature, not a named venue.
# For these concepts, candidate entities must have Google type/category evidence
# confirming they are natural features — not lexical name matches.
_NATURAL_FEATURE_CONCEPT_LABELS: frozenset = frozenset({
    "beach", "beaches",
    "sunset", "sunsets",
    "sunrise", "sunrises",
    "viewpoint", "viewpoints",
    "lookout", "lookouts",
    "scenic", "overlook",
    "vista", "vistas",
    "panorama",
    "waterfall", "waterfalls",
    "trail", "trails",
    "garden", "gardens",
    # Compound labels the frame extractor may produce
    "sunset point", "sunset spot", "sunset viewpoint",
    "lookout point", "scenic overlook", "scenic viewpoint",
    "scenic point",
})

# Google type tokens that confirm beach/coastal natural feature evidence.
_BEACH_NATURAL_FEATURE_TYPES: frozenset = frozenset({
    "beach", "public_beach", "beach_park", "natural_feature",
    "park", "swimming_area", "water_park",
})

# Google type tokens that confirm viewpoint/scenic/sightseeing evidence.
_VIEWPOINT_NATURAL_FEATURE_TYPES: frozenset = frozenset({
    "scenic_viewpoint", "viewpoint", "observation_deck",
    "tourist_attraction", "natural_feature",
    "park", "national_park", "state_park",
    "landmark",
})

# Google type tokens that unambiguously reject an entity for natural-feature queries.
# An entity whose specific types are exclusively from this set (no natural-feature
# type present) is rejected by the precision gate.
_NATURAL_FEATURE_HARD_REJECTED_TYPES: frozenset = frozenset({
    "restaurant", "food", "cafe", "coffee_shop", "bakery",
    "bar", "night_club", "nightclub", "pub", "lounge",
    "meal_takeaway", "meal_delivery",
    "hotel", "lodging",
    "cocktail_bar", "wine_bar", "gastropub",
})

# Strong name tokens that unambiguously confirm a viewpoint/observation place.
# "tower", "terrace", "panorama" are intentionally excluded — too common in venue
# names ("Sunset Tower Bar", "Panorama Lounge", "Terrace Restaurant") to be safe
# as confirmation signals. Only tokens that cannot reasonably appear in a food/bar
# venue name are included.
_STRONG_VIEWPOINT_NAME_TOKENS: frozenset = frozenset({
    "viewpoint", "overlook", "lookout", "observation",
    "belvedere", "mirador", "belvédère",
})

# Name tokens that confirm beach/coastal evidence for generic-typed entities.
_BEACH_CONFIRMING_NAME_TOKENS: frozenset = frozenset({
    "beach", "coast", "coastal", "oceanfront", "ocean", "shore",
    "shoreline", "beachfront", "seaside",
})

# Minimum candidates required after precision gate to proceed.
# If fewer pass, return honest empty state rather than falling back to Tavily.
_MIN_NATURAL_FEATURE_GATE_CANDIDATES: int = 1


_VENUE_HEAD_TOKENS: frozenset = frozenset({
    "bar", "bars", "pub", "pubs", "club", "clubs", "nightclub", "nightclubs",
    "restaurant", "restaurants", "cafe", "cafes", "lounge", "lounges",
    "hotel", "hotels", "hostel", "hostels",
    "brewery", "breweries", "winery", "wineries", "distillery",
})


def _is_natural_feature_query(frame: Any) -> "tuple[bool, str]":
    """Return (is_natural_feature, concept_category) for this query frame.

    concept_category: "beach" | "viewpoint" | other label | "" when not applicable.
    The gate runs only when is_natural_feature=True.

    Returns False when the query has an explicit venue head (e.g. "beach bars",
    "sunset cocktail bars") — those are venue-type queries, not feature searches.
    """
    if not frame or not getattr(frame, "subtype_concepts", None):
        return False, ""

    primary_label = (frame.subtype_concepts[0].label or "").lower()
    if primary_label not in _NATURAL_FEATURE_CONCEPT_LABELS:
        return False, ""

    # If the query contains an explicit venue-type head ("bars", "clubs",
    # "restaurants", "hotels"), the user wants venues near a feature, not the
    # feature itself — do not apply the natural-feature gate.
    ask = (getattr(frame, "literal_ask", None) or getattr(frame, "normalized_ask", None) or "").lower()
    import re as _re
    ask_tokens = set(_re.findall(r"\b[a-z]+\b", ask))
    if ask_tokens & _VENUE_HEAD_TOKENS:
        return False, ""

    beach_tokens = {"beach", "beaches"}
    viewpoint_tokens = {
        "sunset", "sunsets", "sunrise", "sunrises",
        "viewpoint", "viewpoints", "lookout", "lookouts",
        "scenic", "overlook", "vista", "vistas", "panorama",
        "sunset point", "sunset spot", "sunset viewpoint",
        "lookout point", "scenic overlook", "scenic viewpoint", "scenic point",
    }
    if primary_label in beach_tokens:
        return True, "beach"
    if primary_label in viewpoint_tokens:
        return True, "viewpoint"
    return True, primary_label


def _entity_passes_natural_feature_gate(entity: Any, concept_category: str) -> bool:
    """Return True when entity is plausible for a natural-feature query.

    Order of checks — designed so hard rejections cannot be overridden by name tokens:

    1. HARD REJECT first: if specific types are exclusively food/bar/nightlife/hotel,
       reject immediately — entity name ("Sunset Tower Bar", "Panorama Lounge") cannot
       override this decision.
    2. ACCEPT: confirmed natural-feature Google type present.
    3. GENERIC-ONLY: no specific types — accept only with supporting name evidence
       (beach/coast tokens for beach; strong viewpoint vocabulary for viewpoint).
    4. REJECT: any other specific types outside the confirmed set — for this
       containment, wrong cards are worse than empty cards.

    concept_category: "beach" | "viewpoint" | other
    """
    all_types = {t.lower().replace("-", "_") for t in (getattr(entity, "types", None) or [])}
    primary = getattr(entity, "primary_type", None)
    if primary:
        all_types.add(primary.lower().replace("-", "_"))

    _generic = {"establishment", "point_of_interest", "premise", "local_business", "place"}
    non_generic = all_types - _generic

    # Step 1 — HARD REJECT: exclusively food/bar/nightlife/hotel types.
    # This runs before any name-token check so venue names ("Sunset Tower Bar",
    # "Panorama Lounge", "Terrace Restaurant") cannot override typed rejection.
    if non_generic and non_generic <= _NATURAL_FEATURE_HARD_REJECTED_TYPES:
        return False

    # Step 2 — ACCEPT: at least one confirmed natural-feature type.
    confirmed_types = (
        _BEACH_NATURAL_FEATURE_TYPES
        if concept_category == "beach"
        else _VIEWPOINT_NATURAL_FEATURE_TYPES
    )
    if all_types & confirmed_types:
        return True

    # Step 3 — GENERIC-ONLY: no specific types — use name evidence conservatively.
    if not non_generic:
        name_lower = (getattr(entity, "name", "") or "").lower()
        if concept_category == "beach":
            return any(tok in name_lower for tok in _BEACH_CONFIRMING_NAME_TOKENS)
        # viewpoint: only accept with strong, unambiguous viewpoint vocabulary.
        # "tower"/"terrace"/"panorama" are excluded — too common in venue names.
        return any(tok in name_lower for tok in _STRONG_VIEWPOINT_NAME_TOKENS)

    # Step 4 — REJECT: specific types present but outside confirmed AND rejected sets
    # (museum, shop, transit, etc.). For this containment fix, wrong cards worse than
    # empty cards.
    return False


def _normalize_brand_name(name: str) -> str:
    """Lowercase, apostrophe-stripped name for same-brand detection.

    Used only to detect identical chains/locations (e.g. two "Sinya Mediterranean"
    entries). Does NOT collapse genuinely different named places.
    """
    if not name:
        return ""
    normalized = name.lower().strip()
    # Remove apostrophes/curly-quotes that don't change identity
    normalized = re.sub(r"['''‘’]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _deduplicate_brand_names(
    ranked: List[Any],
) -> tuple:
    """Remove same-brand duplicates keeping the highest-ranked card per brand.

    Takes list of (PlaceEntity, RankScore) tuples — already sorted by rank score.
    For identical normalized names (same brand, different locations), keeps only
    the first occurrence (best-fit card). Returns (deduplicated_list, count_suppressed).

    Conservative: only collapses entities with IDENTICAL normalized names.
    Different names are never collapsed regardless of similarity.
    """
    seen_brands: Dict[str, str] = {}  # brand_name → place_id of kept entity
    result = []
    suppressed = 0
    for entity, rs in ranked:
        brand = _normalize_brand_name(entity.name)
        if brand in seen_brands:
            suppressed += 1
            logger.info(
                "semantic_retrieval_v1.brand_dedup: suppressed name=%r place_id=%s "
                "kept_place_id=%s",
                entity.name,
                entity.place_id,
                seen_brands[brand],
            )
        else:
            seen_brands[brand] = entity.place_id
            result.append((entity, rs))
    return result, suppressed


def _is_food_incompatible_entity(types: List[str]) -> bool:
    """Return True when this entity's Google types are incompatible with food/restaurant results.

    Blocks retail/clothing/services entities (e.g. "Only One Boutique") from
    appearing in restaurant responses. An entity is food-incompatible when:
    1. It has no food-compatible type tokens at all, AND
    2. At least one food-incompatible type token is present.

    An entity with only generic types like ["establishment", "point_of_interest"]
    is NOT rejected (no incompatible marker). This keeps the gate conservative
    so borderline or uncategorized venues still pass through.
    """
    if not types:
        return False
    types_lower = {t.lower() for t in types}
    # Pass if ANY food-compatible type token present
    if types_lower & _FOOD_COMPATIBLE_TYPES:
        return False
    # Reject if ANY food-incompatible type token present (and no food-compatible one)
    return bool(types_lower & _FOOD_INCOMPATIBLE_TYPES)


def _format_display_price(
    price_level: Optional[str],
    price_range: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Compact UI price string from Google price fields, or None. Mirrors fast_dynamic path."""
    if price_range and isinstance(price_range, dict):
        start = price_range.get("startPrice") or {}
        end = price_range.get("endPrice") or {}
        if isinstance(start, dict) and isinstance(end, dict):
            try:
                start_units = int(start.get("units") or 0)
                end_units = int(end.get("units") or 0)
                currency = start.get("currencyCode") or end.get("currencyCode") or "USD"
                symbol = "$" if currency == "USD" else currency
                if start_units > 0 and end_units > 0:
                    return f"{symbol}{start_units}–{end_units}"
                elif start_units > 0:
                    return f"From {symbol}{start_units}"
                elif end_units > 0:
                    return f"Up to {symbol}{end_units}"
            except (TypeError, ValueError):
                pass
    if price_level:
        return _PRICE_LEVEL_SYMBOL.get(price_level)
    return None

# SLA contract (v2 amendment §4 and §6); Latency Architecture v1 constants
from app.concierge.deadline_manager import (
    RequestDeadline,
    DEFAULT_SLA,
    SET_WRITER_MIN_BUDGET_MS,
    clamp_first_card_limit,
)


def _assemble_card_reasons(
    cards_data: list,
    set_writer_result: Any,
    note_generation_timed_out: bool,
    note_generation_low_budget: bool,
    note_generation_budget_s: float,
    frame: Any = None,
    user_query: str = "",
    deadline: Any = None,
    remaining_budget_before_reasoning_ms: int = 0,
    note_decision: Any = None,
) -> tuple:
    """Step 7: Assemble card reasons from set-writer output or fallback cascade.

    Set-writer primary path is checked FIRST — before SLA timeout and low-budget
    guards — because set-writer notes are already computed at Step 5.8 and cost
    zero additional LLM calls.  Without this ordering, the note_generation_timed_out
    branch fires first and discards validated notes that were already computed when
    enrichment steps (Yelp/FSQ, editorial) consumed budget past the 4000ms soft ceiling.

    note_decision: NoteDecision from make_note_decision() — the single shared
    authority for whether any LLM note path may run. When provided and
    note_decision.should_run_legacy_batched_reasoning is False, legacy batched
    reasoning is skipped even when set_writer_result is None. This prevents the
    production failure where the set-writer is correctly skipped for no editorial
    evidence but legacy batched reasoning still runs and collapses card count.

    Returns (card_reasons, set_writer_primary_active, reasoning_result, legacy_batched_attempted).
    cards_data must be a list of (entity, evidence, rank_score, det_reason) 4-tuples.
    """
    from app.concierge.batched_reason_builder import (
        build_reasons_with_retry,
        CardReason,
        ReasoningResultV2,
    )

    set_writer_primary_active = False
    _legacy_batched_attempted = False
    if (
        set_writer_result is not None
        and not set_writer_result.timed_out
        and set_writer_result.visible_note_count > 0
    ):
        # ── Set-writer primary path — checked FIRST (before SLA timeout check) ─
        # The set-writer LLM already ran at Step 5.8.  Assembling its pre-computed
        # notes costs zero additional LLM calls.  Cards with hidden notes
        # (validated=False) are also added so Step 8 can include them without a
        # note block — preserving the contract:
        # "hide invalid notes, not valid Google-verified cards."
        set_writer_primary_active = True
        card_reasons: Dict[str, Any] = {}
        for idx, (entity, _ev, _rs, _det) in enumerate(cards_data, 1):
            pid = getattr(entity, "place_id", None)
            sw_note = set_writer_result.notes_by_place_id.get(pid) if pid else None
            if sw_note and sw_note.validated:
                card_reasons[str(idx)] = CardReason(
                    note=sw_note.note,
                    source=sw_note.source,
                    validated=True,
                    attempt_count=1,
                    model_used="set_level_writer_v1",
                )
            else:
                # Note hidden but card is still Google-verified — keep the slot
                # so Step 8 can include the card without a note rather than
                # dropping it from the response.
                card_reasons[str(idx)] = CardReason(
                    note="",
                    source="set_level_writer_v1",
                    validated=False,
                    attempt_count=1,
                    model_used="set_level_writer_v1",
                )

        n = len(cards_data)
        accepted = sum(1 for cr in card_reasons.values() if cr.validated)
        src_counts: Dict[str, int] = {}
        for cr in card_reasons.values():
            if cr.validated:
                src_counts[cr.source] = src_counts.get(cr.source, 0) + 1

        reasoning_result = ReasoningResultV2(
            attempted=True,
            success=(accepted == n),
            accepted_count=accepted,
            final_card_count=n,
            final_note_omitted_count=n - accepted,
            deterministic_visible_count=0,  # invariant: always 0
            failure_reason=(
                None if accepted == n
                else f"set_writer_partial:{n - accepted}_missing"
            ),
            model="set_level_writer_v1",
            fallback_model="",
            visible_note_source_counts=src_counts,
        )
        logger.info(
            "semantic_retrieval_v1: set_writer_primary accepted=%d/%d",
            accepted, n,
        )
    elif set_writer_result is not None and (
        set_writer_result.timed_out
        or (
            set_writer_result.visible_note_count == 0
            and len(set_writer_result.notes_by_place_id) > 0
        )
    ):
        # Set-writer was invoked at Step 5.8 but produced no validated visible notes
        # (either timed out against the SET_WRITER_LLM_MAX_S cap, or all notes failed
        # validation). Do NOT fall through to build_reasons_with_retry — that would
        # spend another LLM budget on the same request and undo the latency benefit of
        # the cap. Return verified Google cards without notes instead.
        logger.info(
            "semantic_retrieval_v1: set_writer_attempted_no_fallback "
            "query=%r timed_out=%s visible_notes=%d",
            user_query,
            set_writer_result.timed_out,
            set_writer_result.visible_note_count,
        )
        card_reasons = {}
        n_cards = len(cards_data)
        reasoning_result = ReasoningResultV2(
            attempted=False,
            failure_reason="set_writer_attempted_no_fallback",
            final_card_count=n_cards,
            final_note_omitted_count=n_cards,
        )
    elif note_generation_timed_out:
        # Only fires when set-writer was NOT attempted (set_writer_result is None)
        # and we are past the SLA soft ceiling.
        # Cards will be assembled without notes; the frontend must not render a
        # Concierge Note block when display_why_validated=False.
        if deadline is not None:
            logger.warning(
                "semantic_retrieval_v1: note_generation_skipped_past_soft_ceiling "
                "query=%r elapsed_ms=%d soft_ceiling_ms=%d",
                user_query, deadline.elapsed_ms(), deadline.sla.soft_ceiling_ms,
            )
        card_reasons = {}
        n_cards = len(cards_data)
        reasoning_result = ReasoningResultV2(
            attempted=False,
            failure_reason="skipped_past_soft_ceiling",
            final_card_count=n_cards,
            final_note_omitted_count=n_cards,
        )
    elif note_generation_low_budget:
        # Budget positive but below the minimum useful threshold — skip before
        # calling the writer so we don't waste a marginal LLM call.
        if deadline is not None:
            logger.info(
                "semantic_retrieval_v1: note_generation_skipped_low_budget "
                "query=%r remaining_ms=%d budget_s=%.2f",
                user_query, remaining_budget_before_reasoning_ms, note_generation_budget_s,
            )
        card_reasons = {}
        n_cards = len(cards_data)
        reasoning_result = ReasoningResultV2(
            attempted=False,
            failure_reason="skipped_low_budget",
            final_card_count=n_cards,
            final_note_omitted_count=n_cards,
        )
    elif not cards_data:
        # No verified cards reached note assembly — skip LLM cascade entirely.
        if deadline is not None:
            logger.info(
                "semantic_retrieval_v1: note_writer_skipped_no_valid_cards query=%r",
                user_query,
            )
        card_reasons = {}
        reasoning_result = ReasoningResultV2(
            attempted=False,
            failure_reason="skipped_no_valid_cards",
            final_card_count=0,
            final_note_omitted_count=0,
        )
    elif note_decision is not None and not note_decision.should_run_legacy_batched_reasoning:
        # NoteDecision gate: no accepted editorial evidence and no cached notes —
        # skip legacy batched reasoning entirely.  The three-pass cascade would
        # spend Haiku credits and produce generic/empty notes that fail validation,
        # yielding the same empty card_reasons with wasted latency.
        # _assemble_card_set will include all verified Google cards without notes.
        logger.info(
            "semantic_retrieval_v1: legacy_batched_reason_skipped_note_decision "
            "reason=%s query=%r",
            note_decision.legacy_batched_reasoning_skip_reason, user_query,
        )
        card_reasons = {}
        n_cards = len(cards_data)
        reasoning_result = ReasoningResultV2(
            attempted=False,
            failure_reason="note_paths_skipped_no_editorial_evidence",
            final_card_count=n_cards,
            final_note_omitted_count=n_cards,
        )
    else:
        # ── Fallback: existing three-pass cascade ─────────────────────────────
        _legacy_batched_attempted = True
        card_reasons, reasoning_result = build_reasons_with_retry(
            cards_data, frame, timeout_s=note_generation_budget_s
        )

    return card_reasons, set_writer_primary_active, reasoning_result, _legacy_batched_attempted


def run_semantic_retrieval_v1(
    user_query: str,
    destination: str,
    prior_identity_keys: Optional[FrozenSet[str]] = None,
    api_key: Optional[str] = None,
    timeout: float = 5.0,
    max_cards: int = _MAX_CARDS,
    vertical: str = "restaurants",
) -> "LiveResearchResult":  # type: ignore[name-defined]
    """Run the full Semantic Retrieval v1 pipeline for one concierge turn.

    Args:
        user_query: User's natural-language place ask.
        destination: Trip destination city.
        prior_identity_keys: Already-shown card keys (for dedup).
        api_key: Google Places API key (falls back to env var).
        timeout: Per-provider-call deadline in seconds.
        max_cards: Maximum cards to return.
        vertical: Target result bucket — "restaurants", "attractions", or "hotels".
            Caller must pass the detected vertical so cards reach the correct bucket
            in the response. Defaults to "restaurants" for backward compatibility.

    Returns:
        LiveResearchResult with verified place cards in the bucket matching ``vertical``,
        or empty result if the pipeline fails or returns no verified entities.
        Never raises — falls back to empty on any unhandled error.
    """
    from app.services.live_research import LiveResearchResult
    from app.models.concierge import SOURCE_LIVE_SEARCH, SOURCE_NONE, SOURCE_UNAVAILABLE

    t_pipeline_start = time.monotonic()

    if not destination:
        logger.warning("semantic_retrieval_v1: empty destination, skipping")
        return LiveResearchResult(source_status=SOURCE_NONE, provider_name=PROVIDER_NAME)

    _api_key = api_key or os.getenv("GOOGLE_PLACES_API_KEY", "")
    if not _api_key:
        logger.warning("semantic_retrieval_v1: no GOOGLE_PLACES_API_KEY configured")
        return LiveResearchResult(source_status=SOURCE_UNAVAILABLE, provider_name=PROVIDER_NAME)

    try:
        return _run_pipeline(
            user_query=user_query,
            destination=destination,
            prior_identity_keys=prior_identity_keys or frozenset(),
            api_key=_api_key,
            timeout=timeout,
            max_cards=max_cards,
            t_pipeline_start=t_pipeline_start,
            vertical=vertical,
        )
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - t_pipeline_start) * 1000)
        logger.exception(
            "semantic_retrieval_v1: unhandled pipeline error "
            "query=%r destination=%r elapsed_ms=%d error=%s",
            user_query, destination, elapsed_ms, exc,
        )
        from app.services.live_research import LiveResearchResult
        from app.models.concierge import SOURCE_NONE
        return LiveResearchResult(source_status=SOURCE_NONE, provider_name=PROVIDER_NAME)


def _run_pipeline(
    *,
    user_query: str,
    destination: str,
    prior_identity_keys: FrozenSet[str],
    api_key: str,
    timeout: float,
    max_cards: int,
    t_pipeline_start: float,
    vertical: str = "restaurants",
) -> "LiveResearchResult":  # type: ignore[name-defined]
    from app.services.live_research import LiveResearchResult
    from app.models.concierge import SOURCE_LIVE_SEARCH, SOURCE_NONE, SOURCE_UNAVAILABLE

    # ── SLA deadline: governs all remaining stages ───────────────────────────
    deadline = RequestDeadline(sla=DEFAULT_SLA, t_start=t_pipeline_start)
    first_card_limit = clamp_first_card_limit(DEFAULT_SLA.first_card_limit)

    latency: Dict[str, int] = {}

    # ── Credit ROI telemetry tracker ─────────────────────────────────────────
    from app.concierge.evidence_cache import (
        CreditROITelemetry,
        EvidenceCacheEntry,
        NoteDecision,
        _EVIDENCE_ATOM_CACHE,
        _NOTE_CACHE,
        _SUPABASE_EVIDENCE_CACHE,
        _SUPABASE_NOTE_CACHE,
        build_evidence_fingerprint,
        make_note_decision,
        should_run_editorial,
        should_skip_writer_no_evidence,
    )
    roi_tel = CreditROITelemetry()

    # ── Step 1: ExperienceFrame extraction ───────────────────────────────────
    t0 = time.monotonic()
    from app.concierge.frame_extractor import extract_frame
    frame = extract_frame(user_query, destination)
    latency["frame_ms"] = int((time.monotonic() - t0) * 1000)

    # Build evidence fingerprint now that we have the frame.
    # Used for evidence cache and note cache lookups throughout the pipeline.
    evidence_fingerprint = build_evidence_fingerprint(
        destination=destination,
        subtype_concepts=[c.label for c in (frame.subtype_concepts or [])],
        location_modifiers=list(getattr(frame, "location_modifiers", []) or []),
        geography_hints=list(getattr(frame, "geography_hints", []) or []),
        normalized_soft_preferences=list(
            getattr(frame, "normalized_soft_preferences", []) or []
        ),
    )

    logger.debug(
        "semantic_retrieval_v1.frame query=%r concepts=%r geo=%r locs=%r prefs=%r neg=%r open_class=%s",
        user_query,
        [(c.label, round(c.confidence, 2)) for c in frame.subtype_concepts],
        frame.geography_hints,
        getattr(frame, "location_modifiers", []),
        frame.soft_preferences,
        frame.negative_constraints,
        getattr(frame, "open_class_place_detected", False),
    )

    # ── Step 2: RetrievalPlanner ─────────────────────────────────────────────
    t0 = time.monotonic()
    from app.concierge.retrieval_planner import plan_queries
    queries = plan_queries(frame)
    latency["plan_ms"] = int((time.monotonic() - t0) * 1000)

    # ── Step 3: Critical path — Google Text Search fanout (deadline-bounded) ──
    # Uses remaining deadline budget to bound per-call timeout so the critical
    # path cannot overrun the SLA hard cutoff.
    from app.concierge.parallel_retrieval import (
        run_critical_google_fanout,
        run_non_critical_enrichment,
    )
    critical_result = run_critical_google_fanout(
        queries, api_key=api_key, deadline=deadline, timeout=timeout
    )
    provider_results = critical_result.provider_results
    latency["provider_ms"] = critical_result.elapsed_ms

    provider_call_count = len(provider_results)
    provider_success_count = sum(1 for r in provider_results if r.succeeded)
    per_query_latencies = {r.query: r.latency_ms for r in provider_results}
    google_critical_candidate_count = sum(
        len(r.places) for r in provider_results if r.succeeded
    )

    # If all providers failed: return honest no-card result
    if provider_success_count == 0:
        logger.warning(
            "semantic_retrieval_v1: all_provider_queries_failed "
            "query=%r destination=%r queries=%r",
            user_query, destination, queries,
        )
        _log_semantic_turn(
            user_query=user_query,
            frame=frame,
            queries=queries,
            latency=latency,
            provider_call_count=provider_call_count,
            provider_success_count=0,
            raw_candidate_count=0,
            deduped_candidate_count=0,
            verified_entity_count=0,
            rejection_stats={},
            final_card_count=0,
            t_pipeline_start=t_pipeline_start,
            outcome="all_providers_failed",
        )
        return LiveResearchResult(source_status=SOURCE_UNAVAILABLE, provider_name=PROVIDER_NAME)

    # ── Step 4: Verified Place Entity Layer ──────────────────────────────────
    t0 = time.monotonic()
    from app.concierge.place_entity_layer import build_entity_layer
    entities, entity_stats = build_entity_layer(provider_results, prior_identity_keys)
    latency["entity_ms"] = int((time.monotonic() - t0) * 1000)

    raw_count = entity_stats.raw_candidate_count
    verified_count = entity_stats.verified_entity_count

    # ── Step 4.5: Food/restaurant entity type gate ────────────────────────────
    # Reject entities whose Google types are exclusively non-food (clothing stores,
    # retail, services, etc.) from restaurant/place_recommendations responses.
    # "Only One Boutique" (womens_clothing_store) is blocked here.
    # Entities with only generic types (establishment, point_of_interest) pass through.
    _entity_type_gate_rejected = 0
    if entities:
        _entities_before_gate = len(entities)
        entities = [e for e in entities if not _is_food_incompatible_entity(e.types)]
        _entity_type_gate_rejected = _entities_before_gate - len(entities)
        if _entity_type_gate_rejected > 0:
            logger.info(
                "semantic_retrieval_v1: entity_type_gate_rejected=%d query=%r "
                "entities_remaining=%d",
                _entity_type_gate_rejected, user_query, len(entities),
            )

    # ── Step 4.6: Wrong-vertical guard for food/bar/nightlife queries ───────────
    # Rejects entities whose Google types are clearly wrong-vertical (rehab, gym,
    # stadium, arena, sports complex, medical) when the query is food/bar/nightlife.
    # Guard is off for attractions, museums, hotels, parks — those verticals pass
    # through unchanged. Uses helpers defined in retrieval_planner.py.
    from app.concierge.retrieval_planner import is_food_bar_query, entity_passes_vertical_guard
    _is_food_bar = is_food_bar_query(frame)
    wrong_vertical_rejected_count = 0
    if _is_food_bar and entities:
        _before_vg = len(entities)
        entities = [
            e for e in entities
            if entity_passes_vertical_guard(e.types, e.primary_type, _is_food_bar)
        ]
        wrong_vertical_rejected_count = _before_vg - len(entities)
        if wrong_vertical_rejected_count > 0:
            logger.info(
                "semantic_retrieval_v1: wrong_vertical_rejected=%d query=%r "
                "is_food_bar=%s entities_remaining=%d",
                wrong_vertical_rejected_count, user_query, _is_food_bar, len(entities),
            )

    if not entities:
        logger.warning(
            "semantic_retrieval_v1: no_verified_entities "
            "query=%r destination=%r raw=%d stats=%s",
            user_query, destination, raw_count, vars(entity_stats),
        )
        _log_semantic_turn(
            user_query=user_query,
            frame=frame,
            queries=queries,
            latency=latency,
            provider_call_count=provider_call_count,
            provider_success_count=provider_success_count,
            raw_candidate_count=raw_count,
            deduped_candidate_count=verified_count,
            verified_entity_count=0,
            rejection_stats=vars(entity_stats),
            final_card_count=0,
            t_pipeline_start=t_pipeline_start,
            outcome="no_verified_entities",
        )
        return LiveResearchResult(source_status=SOURCE_NONE, provider_name=PROVIDER_NAME)

    # ── Step 4.7: Natural-feature precision gate ─────────────────────────────
    # For queries targeting natural geographic features (beach, sunset viewpoint,
    # scenic overlook, lookout, waterfall, garden), require Google type evidence
    # confirming the entity belongs to the right category. Rejects food/bar/hotel
    # entities whose names happen to contain the natural-feature word (e.g.
    # "Sunset Boulevard" bar for "sunset points", "The Beach Club" restaurant for
    # "best beaches"). Honest empty state: if no candidates pass, return no cards
    # rather than falling back to Tavily/editorial or fabricating results.
    _is_natural_feature, _natural_feature_category = _is_natural_feature_query(frame)
    natural_feature_gate_rejected_count = 0
    if _is_natural_feature and entities:
        _before_nf_gate = len(entities)
        entities = [
            e for e in entities
            if _entity_passes_natural_feature_gate(e, _natural_feature_category)
        ]
        natural_feature_gate_rejected_count = _before_nf_gate - len(entities)
        if natural_feature_gate_rejected_count > 0:
            logger.info(
                "semantic_retrieval_v1: natural_feature_gate_rejected=%d "
                "concept_category=%r query=%r entities_remaining=%d",
                natural_feature_gate_rejected_count, _natural_feature_category,
                user_query, len(entities),
            )
        if len(entities) < _MIN_NATURAL_FEATURE_GATE_CANDIDATES:
            logger.info(
                "semantic_retrieval_v1: natural_feature_gate_no_candidates "
                "concept_category=%r query=%r gate_rejected=%d returning_honest_empty=true",
                _natural_feature_category, user_query, natural_feature_gate_rejected_count,
            )
            _log_semantic_turn(
                user_query=user_query,
                frame=frame,
                queries=queries,
                latency=latency,
                provider_call_count=provider_call_count,
                provider_success_count=provider_success_count,
                raw_candidate_count=raw_count,
                deduped_candidate_count=verified_count,
                verified_entity_count=0,
                rejection_stats={"natural_feature_gate_rejected": natural_feature_gate_rejected_count},
                final_card_count=0,
                t_pipeline_start=t_pipeline_start,
                outcome="natural_feature_gate_no_candidates",
            )
            return LiveResearchResult(source_status=SOURCE_NONE, provider_name=PROVIDER_NAME)

    # ── Step 5: SemanticRanker v1 ────────────────────────────────────────────
    t0 = time.monotonic()
    from app.concierge.ranker import rank_entities_with_stats, build_evidence_bundle
    ranked, ranker_stats = rank_entities_with_stats(entities, frame, top_n=max_cards)
    latency["rank_ms"] = int((time.monotonic() - t0) * 1000)

    # Critical path ends here — capture total time through Google + entity + rank.
    critical_path_ms = deadline.elapsed_ms()

    # ── Step 5.05: Brand-name diversity dedup ────────────────────────────────
    # After ranking, suppress duplicate-chain entries that share an identical
    # normalized brand name (e.g. two "Sinya Mediterranean" locations). The
    # highest-ranked entry for each brand is kept; the rest are suppressed.
    # This is conservative: only identical names are collapsed.
    ranked, _brand_dedup_suppressed = _deduplicate_brand_names(ranked)
    if _brand_dedup_suppressed > 0:
        logger.info(
            "semantic_retrieval_v1: brand_dedup_suppressed=%d query=%r "
            "ranked_after=%d",
            _brand_dedup_suppressed, user_query, len(ranked),
        )

    # ── Step 5.5: Non-critical enrichment (deadline-bounded, skipped if low budget) ─
    # Google Place Details enrichment improves note reasoning evidence only.
    # Skipped when remaining deadline budget is insufficient (< 500 ms reserve).
    # Cannot change card identity or addable status — those are critical-path only.
    # Fixes prior silent bug: enrich_top_cards was never called due to _api_key NameError.
    t0 = time.monotonic()
    remaining_budget_before_enrichment_ms = deadline.remaining_ms()
    enrich_result = run_non_critical_enrichment(
        [e for e, _ in ranked],
        api_key=api_key,
        deadline=deadline,
        budget_n=4,
    )
    enrichment_map = enrich_result.enrichment_map
    latency["enrich_ms"] = enrich_result.elapsed_ms

    # ── Step 5.55: Cross-source evidence enrichment v1 (PR #275) ────────────
    # Yelp + Foursquare enrichment for already Google-verified cards only.
    # Deadline-bounded and parallel. Never blocks card return.
    # Yelp/Foursquare cannot mint cards, override Google identity/addability/
    # operational status, or directly create visible prose.
    # Keys gracefully absent → no enrichment, cards still returned.
    from app.concierge.cross_source_enrichment import (
        CrossSourceEnrichmentResult,
        CrossSourceTelemetry,
        get_foursquare_key,
        get_yelp_key,
        run_cross_source_enrichment,
    )
    t0 = time.monotonic()
    cross_source_result: CrossSourceEnrichmentResult
    cross_source_tel: Dict[str, Any] = {}
    try:
        _yelp_key = get_yelp_key()
        _fsq_key = get_foursquare_key()
        cross_source_result = run_cross_source_enrichment(
            [e for e, _ in ranked],
            deadline=deadline,
            yelp_key=_yelp_key,
            fsq_key=_fsq_key,
            budget_n=first_card_limit,
        )
        cross_source_tel = cross_source_result.telemetry.as_log_dict()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "semantic_retrieval_v1: cross_source_enrichment_failed query=%r error=%s",
            user_query, exc,
        )
        cross_source_result = CrossSourceEnrichmentResult(
            atoms_by_place_id={},
            telemetry=CrossSourceTelemetry(enrichment_enabled=True, enrichment_attempted=False),
            elapsed_ms=0,
        )
        cross_source_tel = cross_source_result.telemetry.as_log_dict()
    latency["cross_source_ms"] = cross_source_result.elapsed_ms

    # ── Step 5.56: Editorial Corroboration v1 (cache-aware) ──────────────────
    # Tavily + Serper editorial enrichment for already Google-verified cards only.
    # Now credit-efficient:
    #   1. Evidence cache is checked first — cache hit skips Tavily entirely.
    #   2. Selectivity gate decides if Tavily is worth calling for this query.
    #   3. Accepted atoms are cached even if the LLM note writer later times out.
    # Deadline-bounded and parallel (non-blocking executor lifecycle).
    # Never blocks card return. Atoms merged into cross_source_result.atoms_by_place_id.
    # Tavily/Serper cannot mint cards, override Google identity/addability/
    # operational status, or directly create visible prose.
    from app.concierge.editorial_enrichment import (
        EDITORIAL_POST_CROSS_SOURCE_MIN_MS,
        EditorialEnrichmentResult,
        EditorialEnrichmentTelemetry,
        get_serper_key,
        get_tavily_key,
        run_editorial_enrichment,
    )
    t0 = time.monotonic()
    editorial_result: EditorialEnrichmentResult
    editorial_tel: Dict[str, Any] = {}
    _remaining_after_cross_source_ms = deadline.remaining_ms()
    try:
        # ── Kill switch: ALLOW_LIVE_RESEARCH_CALLS ────────────────────────────
        # Global hard gate: when ALLOW_LIVE_RESEARCH_CALLS is false (production
        # default), no Tavily/Serper/Brave/editorial call may happen from any
        # Concierge path. Checked before key reads so no provider path is entered.
        # Google Places fanout (Steps 1–5.5) is unaffected — it is the verified
        # card provider, not the editorial/live-research path.
        from app.services.live_research import _live_research_calls_allowed
        if not _live_research_calls_allowed():
            roi_tel.tavily_skipped_reason = "allow_live_research_calls_false"
            logger.info(
                "semantic_retrieval_v1: editorial_skipped "
                "editorial_skipped_reason=allow_live_research_calls_false "
                "tavily_attempted=0 serper_attempted=0 brave_attempted=0 query=%r",
                user_query,
            )
            editorial_result = EditorialEnrichmentResult(
                atoms_by_place_id={},
                telemetry=EditorialEnrichmentTelemetry(
                    enrichment_attempted=False,
                    skipped_reason="allow_live_research_calls_false",
                ),
                elapsed_ms=0,
            )
        else:
            _tavily_key = get_tavily_key()
            _serper_key = get_serper_key()

            # ── Evidence cache check (skips Tavily on hit) ────────────────────────
            # Read order: 1. in-memory hot layer, 2. Supabase durable layer, 3. live path.
            _evidence_cache_entry = _EVIDENCE_ATOM_CACHE.get(evidence_fingerprint)
            if _evidence_cache_entry is None:
                # Memory miss — check durable Supabase layer before running Tavily.
                _durable_ev_entry = _SUPABASE_EVIDENCE_CACHE.get(evidence_fingerprint)
                if _durable_ev_entry is not None:
                    # Warm in-memory cache so the next request on this worker is free.
                    _EVIDENCE_ATOM_CACHE.set(
                        evidence_fingerprint,
                        _durable_ev_entry.atoms_by_place_id,
                        _durable_ev_entry.accepted_count,
                    )
                    _evidence_cache_entry = _durable_ev_entry
                    roi_tel.durable_evidence_cache_hit = True
                    logger.info(
                        "semantic_retrieval_v1: durable_evidence_cache_hit "
                        "fingerprint=%s accepted_count=%d query=%r",
                        evidence_fingerprint,
                        _durable_ev_entry.accepted_count,
                        user_query,
                    )
            if _evidence_cache_entry is not None:
                # Cache hit (memory or durable) — reuse accepted atoms, skip Tavily entirely.
                roi_tel.evidence_cache_hit = True
                roi_tel.accepted_editorial_evidence_count = _evidence_cache_entry.accepted_count
                editorial_result = EditorialEnrichmentResult(
                    atoms_by_place_id=dict(_evidence_cache_entry.atoms_by_place_id),
                    telemetry=EditorialEnrichmentTelemetry(
                        enrichment_attempted=False,
                        skipped_reason="evidence_cache_hit",
                    ),
                    elapsed_ms=0,
                )
                logger.info(
                    "semantic_retrieval_v1: editorial_evidence_cache_hit "
                    "fingerprint=%s accepted_count=%d query=%r durable=%s",
                    evidence_fingerprint,
                    _evidence_cache_entry.accepted_count,
                    user_query,
                    roi_tel.durable_evidence_cache_hit,
                )
            elif _remaining_after_cross_source_ms < EDITORIAL_POST_CROSS_SOURCE_MIN_MS:
                # Opportunistic budget gate: Step 5.55 (Yelp/FSQ) consumed too much
                # budget — skip editorial to protect dossier/writer latency.
                roi_tel.tavily_skipped_reason = "budget_after_cross_source_too_low"
                logger.info(
                    "semantic_retrieval_v1: editorial_skipped "
                    "reason=budget_after_cross_source_too_low remaining_ms=%d",
                    _remaining_after_cross_source_ms,
                )
                editorial_result = EditorialEnrichmentResult(
                    atoms_by_place_id={},
                    telemetry=EditorialEnrichmentTelemetry(
                        enrichment_attempted=False,
                        skipped_reason="budget_after_cross_source_too_low",
                    ),
                    elapsed_ms=0,
                )
            else:
                # ── Selectivity gate ──────────────────────────────────────────────
                _editorial_should_run, _editorial_selectivity_reason = should_run_editorial(frame)
                if not _editorial_should_run:
                    # Simple category search — Tavily adds marginal value; skip.
                    roi_tel.tavily_skipped_reason = f"selectivity:{_editorial_selectivity_reason}"
                    logger.info(
                        "semantic_retrieval_v1: editorial_skipped "
                        "reason=selectivity selectivity_reason=%s query=%r",
                        _editorial_selectivity_reason, user_query,
                    )
                    editorial_result = EditorialEnrichmentResult(
                        atoms_by_place_id={},
                        telemetry=EditorialEnrichmentTelemetry(
                            enrichment_attempted=False,
                            skipped_reason=f"selectivity:{_editorial_selectivity_reason}",
                        ),
                        elapsed_ms=0,
                    )
                else:
                    # ── Run Tavily/Serper ─────────────────────────────────────────
                    roi_tel.tavily_attempted = bool(_tavily_key or _serper_key)
                    editorial_result = run_editorial_enrichment(
                        [e for e, _ in ranked],
                        deadline=deadline,
                        tavily_key=_tavily_key,
                        serper_key=_serper_key,
                        destination=destination,
                        budget_n=first_card_limit,
                    )

                    # ── Store accepted atoms to evidence cache ────────────────────
                    # Cache even when notes later fail/time out — prevents re-spending
                    # Tavily credits on the same query when notes eventually succeed.
                    _total_accepted = sum(
                        len(atoms)
                        for atoms in editorial_result.atoms_by_place_id.values()
                    )
                    if _total_accepted > 0:
                        try:
                            _EVIDENCE_ATOM_CACHE.set(
                                evidence_fingerprint,
                                editorial_result.atoms_by_place_id,
                                _total_accepted,
                            )
                            roi_tel.evidence_cache_write = True
                            roi_tel.accepted_editorial_evidence_count = _total_accepted
                            logger.info(
                                "semantic_retrieval_v1: editorial_evidence_cached "
                                "fingerprint=%s accepted=%d query=%r",
                                evidence_fingerprint, _total_accepted, user_query,
                            )
                        except Exception as _cache_exc:  # noqa: BLE001
                            logger.debug(
                                "semantic_retrieval_v1: editorial_cache_write_failed "
                                "error=%s", _cache_exc,
                            )
                        # Also write to durable Supabase layer.
                        _durable_ok = _SUPABASE_EVIDENCE_CACHE.set(
                            evidence_fingerprint,
                            editorial_result.atoms_by_place_id,
                            _total_accepted,
                            destination=destination,
                        )
                        if _durable_ok:
                            roi_tel.durable_evidence_cache_write = True
                            logger.info(
                                "semantic_retrieval_v1: durable_evidence_cache_write "
                                "fingerprint=%s accepted=%d query=%r",
                                evidence_fingerprint, _total_accepted, user_query,
                            )
                        else:
                            roi_tel.durable_cache_error_count += 1

        editorial_tel = editorial_result.telemetry.as_log_dict()
        # Merge editorial atoms into cross_source atoms_by_place_id so the
        # existing dossier builder sees all enrichment in one pass.
        for pid, atoms in editorial_result.atoms_by_place_id.items():
            existing = cross_source_result.atoms_by_place_id.get(pid, [])
            cross_source_result.atoms_by_place_id[pid] = existing + atoms
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "semantic_retrieval_v1: editorial_enrichment_failed query=%r error=%s",
            user_query, exc,
        )
        editorial_result = EditorialEnrichmentResult(
            atoms_by_place_id={},
            telemetry=EditorialEnrichmentTelemetry(enrichment_attempted=False),
            elapsed_ms=0,
        )
        editorial_tel = editorial_result.telemetry.as_log_dict()
    latency["editorial_ms"] = editorial_result.elapsed_ms

    # ── Step 5.6: Evidence Dossier v1 (PR #259) ─────────────────────────────
    # Build structured dossiers for top cards using critical + enrichment data.
    # Does not block card return. Minimal dossiers built if budget is too low.
    t0 = time.monotonic()
    from app.concierge.evidence_dossier import (
        DOSSIER_BUDGET_RESERVE_MS,
        EvidenceDossierTelemetry,
        build_dossiers_for_ranked_cards,
        get_dossier_telemetry,
    )
    dossiers = []
    try:
        _primary_concept = (
            frame.subtype_concepts[0].label if frame.subtype_concepts else ""
        )
        low_budget = deadline.remaining_ms() < DOSSIER_BUDGET_RESERVE_MS
        skipped_due_to_budget = 0
        if low_budget:
            for entity, _ in ranked[:first_card_limit]:
                if enrichment_map.get(entity.place_id) is not None:
                    skipped_due_to_budget += 1
        dossiers = build_dossiers_for_ranked_cards(
            ranked=ranked,
            frame=frame,
            enrichment_map=enrichment_map,
            deadline=deadline,
            top_n=first_card_limit,
            category_fn=lambda e: _derive_display_category(
                e.types, e.primary_type, _primary_concept
            ),
            cross_source_map=cross_source_result.atoms_by_place_id,
        )
        dossier_tel = get_dossier_telemetry(
            dossiers,
            skipped_due_to_budget=skipped_due_to_budget,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "semantic_retrieval_v1: dossier_build_failed query=%r error=%s",
            user_query,
            exc,
        )
        dossier_tel = EvidenceDossierTelemetry()
    latency["dossier_ms"] = int((time.monotonic() - t0) * 1000)

    # ── Step 5.7: Card Role + Curated Set Ranker v1 (PR #260) ───────────────
    # Assigns internal roles and computes curation scores using dossier data.
    # Optionally reorders the first-response set within conservative bounds.
    # Does not change visible card payload, note generation, or card cap.
    # Failure is fully isolated: original ranked order is preserved on error.
    t0 = time.monotonic()
    from app.concierge.card_curator import (
        CuratedSetResult,
        curate_cards,
    )
    curator_tel: dict = {"curated_fallback_to_original_order": True, "curated_ms": 0}
    curated_result: Optional[CuratedSetResult] = None
    try:
        curated_result = curate_cards(
            ranked=ranked,
            dossiers=dossiers,
            first_card_limit=first_card_limit,
        )
        if curated_result.reordered_count > 0:
            # Rebuild ranked: curated order for the dossier-covered cap, original
            # order for the rest (entries beyond dossier coverage are unchanged).
            n_curated = curated_result.output_count
            curated_entities = [
                (cc.entity, cc.rank_score) for cc in curated_result.curated_cards
            ]
            ranked = curated_entities + ranked[n_curated:]
        curator_tel = curated_result.as_telemetry_dict(
            elapsed_ms=int((time.monotonic() - t0) * 1000)
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "semantic_retrieval_v1: curator_failed query=%r error=%s — "
            "falling back to original ranked order",
            user_query,
            exc,
        )
    latency["curator_ms"] = int((time.monotonic() - t0) * 1000)

    # ── Step 5.8: Set-Level Writer v1 (cache-aware) ───────────────────────────
    # Uses CuratedSetResult + PlaceEvidenceDossier to generate evidence-grounded,
    # set-aware notes. Credit-efficient:
    #   1. Note cache is checked first — cache hit skips the LLM call entirely.
    #   2. Approved notes from the LLM writer are stored to note cache for reuse.
    # Falls back to the existing batched_reason_builder path on any failure.
    # Never blocks card return.
    #
    # Latency Architecture v1: budget gate added. If remaining budget when we
    # reach this step is below SET_WRITER_MIN_BUDGET_MS, the writer is skipped
    # entirely before any LLM call is made. Inside write_set_notes, the LLM
    # timeout is capped at SET_WRITER_LLM_MAX_S so it cannot consume the full
    # remaining note-gen budget even when budget appears large.
    t0 = time.monotonic()
    from app.concierge.set_level_writer import (
        SetWriterResult,
        make_cached_note_result,
        write_set_notes,
    )
    set_writer_result: Optional[SetWriterResult] = None
    set_writer_tel: Dict[str, Any] = {"set_writer_fallback_to_existing_path": True}
    _set_writer_remaining_ms = deadline.remaining_ms()
    _set_writer_skipped_budget = _set_writer_remaining_ms < SET_WRITER_MIN_BUDGET_MS

    # ── Note cache check ──────────────────────────────────────────────────────
    # Read order: 1. in-memory hot layer, 2. Supabase durable layer.
    # Cache key: (place_id, evidence_fingerprint) — prevents cross-context bleed.
    _cached_notes: Dict[str, str] = {}
    _durable_note_hits = 0
    if curated_result is not None and curated_result.output_count > 0:
        for _cc in (getattr(curated_result, "curated_cards", []) or [])[:first_card_limit]:
            _pid = getattr(_cc.entity, "place_id", None)
            if _pid:
                _note_entry = _NOTE_CACHE.get(_pid, evidence_fingerprint)
                if _note_entry is not None:
                    _cached_notes[_pid] = _note_entry.note
                else:
                    # Memory miss — check durable layer.
                    _dn = _SUPABASE_NOTE_CACHE.get(_pid, evidence_fingerprint)
                    if _dn is not None:
                        # Warm in-memory cache.
                        _NOTE_CACHE.set(_pid, evidence_fingerprint, _dn.note, _dn.source)
                        _cached_notes[_pid] = _dn.note
                        _durable_note_hits += 1
        roi_tel.note_cache_hit_count = len(_cached_notes)
        roi_tel.durable_note_cache_hit_count = _durable_note_hits

    _n_curated = curated_result.output_count if curated_result is not None else 0
    _all_notes_cached = (
        _n_curated > 0
        and len(_cached_notes) >= min(_n_curated, first_card_limit)
    )

    # ── Shared note/evidence decision (single source of truth) ────────────────
    # Computed once from frame signals and actual editorial/cache outcomes.
    # This decision gates ALL optional LLM note paths (set_level_writer,
    # batched_reason_builder). No note path may run without approval here.
    _note_decision = make_note_decision(
        frame=frame,
        cached_notes=_cached_notes,
        accepted_editorial_evidence_count=roi_tel.accepted_editorial_evidence_count,
    )
    logger.debug(
        "semantic_retrieval_v1: note_decision "
        "should_run_set_writer=%s should_run_legacy=%s "
        "has_editorial=%s has_cached=%s plain_category=%s query=%r",
        _note_decision.should_run_set_writer,
        _note_decision.should_run_legacy_batched_reasoning,
        _note_decision.has_accepted_editorial_evidence,
        _note_decision.has_cached_approved_notes,
        _note_decision.is_plain_category_query,
        user_query,
    )

    if _all_notes_cached:
        # All cards have cached approved notes — skip LLM writer entirely.
        logger.info(
            "semantic_retrieval_v1: note_cache_full_hit "
            "count=%d fingerprint=%s query=%r",
            len(_cached_notes), evidence_fingerprint, user_query,
        )
        set_writer_result = make_cached_note_result(
            curated_result=curated_result,
            cached_notes=_cached_notes,
            first_card_limit=first_card_limit,
        )
        set_writer_tel = set_writer_result.as_telemetry_dict(
            elapsed_ms=int((time.monotonic() - t0) * 1000)
        )
        set_writer_tel["set_writer_fallback_to_existing_path"] = False
        set_writer_tel["source"] = "note_cache"
        _set_writer_skipped_budget = False  # note: cache hit, not budget skip
    elif _set_writer_skipped_budget:
        logger.info(
            "semantic_retrieval_v1: set_writer_skipped_budget "
            "remaining_ms=%d threshold_ms=%d query=%r",
            _set_writer_remaining_ms, SET_WRITER_MIN_BUDGET_MS, user_query,
        )
        set_writer_tel = {
            "set_writer_fallback_to_existing_path": True,
            "set_writer_skipped_budget": True,
            "set_writer_remaining_ms_at_skip": _set_writer_remaining_ms,
        }
    elif not _note_decision.should_run_set_writer:
        # Shared note decision says skip set-writer: no accepted editorial evidence
        # AND no cached approved notes. The writer has no editorial grounding —
        # it would produce generic or empty notes that fail the quality gate,
        # wasting Haiku credits with nothing visible or cacheable as the result.
        # The same decision will also gate legacy batched reasoning in _assemble_card_reasons.
        logger.info(
            "semantic_retrieval_v1: set_writer_skipped_note_decision "
            "reason=%s accepted_editorial=%d cached_notes=%d query=%r",
            _note_decision.set_writer_skip_reason,
            roi_tel.accepted_editorial_evidence_count,
            len(_cached_notes), user_query,
        )
        roi_tel.set_writer_skipped_reason = _note_decision.set_writer_skip_reason
        set_writer_tel = {
            "set_writer_fallback_to_existing_path": True,
            "set_writer_skipped_no_editorial_evidence": True,
            "set_writer_skipped_reason": _note_decision.set_writer_skip_reason,
        }
    elif curated_result is not None and curated_result.output_count > 0:
        try:
            roi_tel.note_writer_attempted = True
            set_writer_result = write_set_notes(
                curated_result=curated_result,
                frame=frame,
                deadline=deadline,
                first_card_limit=first_card_limit,
            )
            set_writer_tel = set_writer_result.as_telemetry_dict(
                elapsed_ms=int((time.monotonic() - t0) * 1000)
            )
            set_writer_tel["set_writer_fallback_to_existing_path"] = (
                set_writer_result.timed_out
                or set_writer_result.visible_note_count == 0
            )

            # Track timeout for ROI telemetry
            if set_writer_result.timed_out:
                roi_tel.note_writer_timed_out = True
                # Evidence is already cached (Step 5.56) — the next matching
                # search can reuse atoms without re-calling Tavily.
                logger.info(
                    "semantic_retrieval_v1: note_writer_timed_out_evidence_cached "
                    "evidence_cache_written=%s fingerprint=%s query=%r",
                    roi_tel.evidence_cache_write or roi_tel.evidence_cache_hit,
                    evidence_fingerprint, user_query,
                )
            else:
                # ── Store approved notes to note cache ────────────────────────
                # Only validated, non-empty notes are stored. Failed/generic/
                # timeout notes are never cached.
                _write_count = 0
                _durable_note_writes = 0
                for _pid, _note_obj in (
                    set_writer_result.notes_by_place_id or {}
                ).items():
                    if _note_obj.validated and _note_obj.note:
                        try:
                            _NOTE_CACHE.set(
                                _pid,
                                evidence_fingerprint,
                                _note_obj.note,
                                _note_obj.source,
                            )
                            _write_count += 1
                        except Exception as _nc_exc:  # noqa: BLE001
                            logger.debug(
                                "semantic_retrieval_v1: note_cache_write_failed "
                                "place_id=%s error=%s", _pid, _nc_exc,
                            )
                        # Also write to durable Supabase layer.
                        _dn_ok = _SUPABASE_NOTE_CACHE.set(
                            _pid,
                            evidence_fingerprint,
                            _note_obj.note,
                            _note_obj.source,
                        )
                        if _dn_ok:
                            _durable_note_writes += 1
                        else:
                            roi_tel.durable_cache_error_count += 1
                roi_tel.note_cache_write_count = _write_count
                roi_tel.durable_note_cache_write_count = _durable_note_writes
                if _write_count > 0:
                    logger.info(
                        "semantic_retrieval_v1: note_cache_written "
                        "count=%d durable_writes=%d fingerprint=%s query=%r",
                        _write_count, _durable_note_writes,
                        evidence_fingerprint, user_query,
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "semantic_retrieval_v1: set_writer_failed query=%r error=%s — "
                "falling back to existing note path",
                user_query,
                exc,
            )
            set_writer_result = None
            set_writer_tel = {"set_writer_fallback_to_existing_path": True}
    latency["set_writer_ms"] = int((time.monotonic() - t0) * 1000)

    # ── Step 5.8.1: Partial note cache merge ─────────────────────────────────
    # Overlay approved cached notes for cards that the LLM writer did not cover
    # (partial cache hit + LLM timeout, or partial hit + LLM produced 0 notes).
    # Only place IDs that have NO validated note in set_writer_result receive a
    # cached note. LLM-validated notes are never overwritten by cache.
    # Cards with no cached entry and no LLM note remain note-less — no generic
    # fallback is created.
    if _cached_notes:
        if set_writer_result is None:
            # Writer was skipped (budget/exception) but we have some cached notes.
            set_writer_result = make_cached_note_result(
                curated_result=curated_result,
                cached_notes=_cached_notes,
                first_card_limit=first_card_limit,
            )
            set_writer_tel["set_writer_fallback_to_existing_path"] = False
            set_writer_tel["source"] = "note_cache_partial"
        else:
            # Writer ran (or timed out): overlay cached notes for uncovered cards.
            from app.concierge.set_level_writer import SetWriterNote
            _cache_overlaid = 0
            for _pid, _cached_text in _cached_notes.items():
                _existing = set_writer_result.notes_by_place_id.get(_pid)
                if _existing is None or not _existing.validated:
                    set_writer_result.notes_by_place_id[_pid] = SetWriterNote(
                        place_id=_pid,
                        note=_cached_text,
                        validated=True,
                        rejection_reason="",
                        source="note_cache",
                        role_used_internal="",
                        evidence_terms_used=[],
                        caveat_type="",
                    )
                    _cache_overlaid += 1
            if _cache_overlaid > 0:
                _merged_visible = sum(
                    1 for n in set_writer_result.notes_by_place_id.values() if n.validated
                )
                _merged_hidden = sum(
                    1 for n in set_writer_result.notes_by_place_id.values() if not n.validated
                )
                set_writer_result.visible_note_count = _merged_visible
                set_writer_result.hidden_note_count = _merged_hidden
                if _merged_visible > 0:
                    set_writer_result.timed_out = False
                logger.info(
                    "semantic_retrieval_v1: partial_note_cache_merge "
                    "overlaid=%d total_visible=%d fingerprint=%s query=%r",
                    _cache_overlaid, _merged_visible, evidence_fingerprint, user_query,
                )

    # ── Step 6: Evidence bundles + deterministic SafeReasonBuilder ───────────
    t0 = time.monotonic()
    from app.concierge.safe_reason_builder import build_safe_reason
    from app.concierge.reason_validator import validate_reason

    # Build evidence bundles, deterministic reasons, and validate each one.
    # A deterministic reason that fails validation (e.g., pure name+rating template)
    # is replaced with "" — no note is better than a template. The LLM path will
    # attempt to produce a better note; if it also fails, the card gets no note.
    cards_data: List[Any] = []  # (entity, evidence, rank_score, det_reason)
    det_reason_rejected_count = 0

    for entity, rank_score in ranked:
        enrichment = enrichment_map.get(entity.place_id)
        evidence = build_evidence_bundle(entity, frame, rank_score, enrichment=enrichment)
        det_reason = build_safe_reason(entity, evidence, frame, rank_score)

        # Validate the deterministic reason using the same validator applied to
        # LLM output. If rejected (e.g., pure name+rating template), use ""
        # so the card assembles with no note rather than a template.
        is_valid, rejection = validate_reason(det_reason, frame, evidence)
        if not is_valid:
            logger.warning(
                "semantic_retrieval_v1: det_reason_rejected "
                "name=%s rejection=%s reason=%r",
                entity.name, rejection, det_reason,
            )
            det_reason = ""  # absent note > template
            det_reason_rejected_count += 1

        cards_data.append((entity, evidence, rank_score, det_reason))

    latency["det_reason_ms"] = int((time.monotonic() - t0) * 1000)

    # ── Step 7: Note generation — set-level writer (primary) or three-pass LLM ─
    t0 = time.monotonic()

    # Check SLA before committing to LLM note generation.
    remaining_budget_before_reasoning_ms = deadline.remaining_ms()
    note_generation_budget_s = deadline.budget_for_note_generation_s()
    note_generation_timed_out = note_generation_budget_s <= 0.0
    # Pre-skip when budget is positive but below the minimum useful window.
    note_generation_low_budget = (
        not note_generation_timed_out
        and note_generation_budget_s < _MIN_NOTE_GENERATION_BUDGET_S
    )

    card_reasons, set_writer_primary_active, reasoning_result, _legacy_batched_attempted = (
        _assemble_card_reasons(
            cards_data=cards_data,
            set_writer_result=set_writer_result,
            note_generation_timed_out=note_generation_timed_out,
            note_generation_low_budget=note_generation_low_budget,
            note_generation_budget_s=note_generation_budget_s,
            frame=frame,
            user_query=user_query,
            deadline=deadline,
            remaining_budget_before_reasoning_ms=remaining_budget_before_reasoning_ms,
            note_decision=_note_decision,
        )
    )
    latency["batched_reason_ms"] = int((time.monotonic() - t0) * 1000)
    # optional_reasoning_ms covers all non-critical optional work (dossier, curator,
    # set-writer, batched-reason). Tracked for latency profiling only.
    latency["optional_reasoning_ms"] = (
        latency.get("dossier_ms", 0)
        + latency.get("curator_ms", 0)
        + latency.get("set_writer_ms", 0)
        + latency["batched_reason_ms"]
    )

    # ── Step 8: Assemble final cards ─────────────────────────────────────────
    # set_writer_attempted_no_fallback means: set-writer ran but produced nothing,
    # no LLM fallback will be attempted. Treat it the same as note_generation_timed_out
    # so _assemble_card_set includes Google-verified cards without notes instead of
    # dropping them via the excluded_unvalidated path.
    _effective_note_gen_skipped = (
        note_generation_timed_out
        or reasoning_result.failure_reason == "set_writer_attempted_no_fallback"
        or reasoning_result.failure_reason == "note_paths_skipped_no_editorial_evidence"
    )
    cards, rank_debug, excluded_unvalidated, visible_note_count, cards_without_notes_count = (
        _assemble_card_set(
            cards_data=cards_data,
            card_reasons=card_reasons,
            frame=frame,
            note_generation_timed_out=_effective_note_gen_skipped,
            set_writer_primary_active=set_writer_primary_active,
            vertical=vertical,
        )
    )

    latency["reason_ms"] = latency["det_reason_ms"] + latency["batched_reason_ms"]

    # ── Step 8.5: Per-card observability log ─────────────────────────────────
    _log_per_card_notes(user_query, cards_data, card_reasons, frame)

    # ── Step 9: TrustGate final pass ─────────────────────────────────────────
    t0 = time.monotonic()
    cards, trust_rejected = _trust_gate(cards)
    latency["trust_gate_ms"] = int((time.monotonic() - t0) * 1000)

    # ── Step 9.5: First-response card cap (v2 amendment §4 invariant 3) ──────
    # Cap at first_card_limit (default 6, range 5–7) for the first response.
    # The upstream ranked pool of up to _MAX_CARDS remains available for
    # continuation/more-options turns via the result pool (managed by router).
    # fallback_note_visible_count is always 0 — enforced structurally because
    # reason_validated=False hides the note block; no deterministic text is
    # ever written with reason_validated=True.
    pre_cap_count = len(cards)
    cards = cards[:first_card_limit]
    final_card_count = len(cards)

    # Recount note counts post-cap to match returned card set.
    # When set_writer_primary_active=True, set-writer notes survived into the cards
    # even if the SLA budget was exceeded — so we must re-scan the actual card objects
    # rather than assuming all notes are absent.
    if _effective_note_gen_skipped and not set_writer_primary_active:
        visible_note_count = 0
        cards_without_notes_count = final_card_count
    else:
        # Recalculate for the capped set (cards with validated notes only).
        visible_note_count = sum(
            1 for c in cards
            if getattr(getattr(c, "display", None), "display_why_validated", False)
        )
        cards_without_notes_count = final_card_count - visible_note_count

    # ── Step 10: Structured observability ────────────────────────────────────
    # Wrong-category fit diagnostics: count entities whose subtype_fit fell
    # below the wrong-category threshold (used for visibility into ranker
    # behavior, not for any hard gate). off_concept_dropped reports the
    # entities removed by the post-rank venue-head filter — i.e., modifier-only
    # matches discarded so a brewery ask doesn't surface parks or riverwalk
    # attractions that just happen to satisfy the geo modifier.
    wrong_category_count = sum(
        1 for _, rs in ranked if rs.subtype_fit < 0.30
    )
    top_card_name = cards[0].name if cards else ""
    top_card_city = ""
    if cards:
        # Extract city/area from the top card's formatted address.
        # Filter out building fragments (Lower Level, Suite, Floor, etc.) so that
        # "Lower Level, Chicago, IL" returns "Chicago", not "Lower Level".
        from app.concierge.safe_reason_builder import _NON_NEIGHBORHOOD_FRAGMENTS
        addr = getattr(cards[0], "neighborhood", "") or ""
        addr_parts = [p.strip() for p in addr.split(",")]
        _ADDR_SKIP = frozenset({"usa", "us", "il", "ny", "ca", "tx", "fl", "wa"})
        for part in addr_parts:
            p_lower = part.strip().lower()
            if not part or any(c.isdigit() for c in part) or len(part) <= 2:
                continue
            if p_lower in _ADDR_SKIP:
                continue
            # Skip building fragments — never report them as city
            if p_lower in _NON_NEIGHBORHOOD_FRAGMENTS:
                continue
            if any(p_lower.startswith(frag) for frag in _NON_NEIGHBORHOOD_FRAGMENTS if len(frag) > 4):
                continue
            top_card_city = part.strip()
            break

    rejection_stats = {
        **vars(entity_stats),
        "trust_gate_rejected": trust_rejected,
        "wrong_category_low_subtype_fit": wrong_category_count,
        "off_concept_dropped": ranker_stats.off_concept_dropped,
        "on_concept_count": ranker_stats.on_concept_count,
        "venue_head_recognized": ranker_stats.concept_is_recognized,
        "destination_penalized_count": ranker_stats.destination_penalized_count,
        "modifier_intent": ranker_stats.modifier_intent,
        "modifier_filter_applied": ranker_stats.modifier_filter_applied,
        "casual_downranked_count": ranker_stats.casual_downranked_count,
        "casual_excluded_count": ranker_stats.casual_excluded_count,
        "det_reason_rejected_count": det_reason_rejected_count,
        # Truthful telemetry: Reasoning Reliability v2 fields.
        "reasoning_attempted": reasoning_result.attempted,
        "reasoning_model": reasoning_result.model,
        "reasoning_success": reasoning_result.success,
        "reasoning_failure_reason": reasoning_result.failure_reason,
        "llm_accepted_count": reasoning_result.accepted_count,
        "retry_recovered_count": reasoning_result.retry_recovered_count,
        "fallback_model_used_count": reasoning_result.fallback_model_used_count,
        "deterministic_visible_count": 0,  # invariant: always 0
        "final_note_omitted_count": reasoning_result.final_note_omitted_count,
        "excluded_unvalidated_count": excluded_unvalidated,
        "prompt_builder_error": reasoning_result.prompt_error,
        "diversity_flagged": reasoning_result.diversity_flagged,
        "visible_note_source_counts": reasoning_result.visible_note_source_counts,
        # Legacy fields for compatibility with existing log parsers
        "grounded_reason_attempted": reasoning_result.attempted,
        "grounded_reason_success": reasoning_result.success,
        # PR #261 set-level writer
        "set_writer_used": (
            set_writer_result is not None
            and not set_writer_result.timed_out
            and set_writer_result.visible_note_count > 0
        ),
        "set_writer_visible_note_count": (
            set_writer_result.visible_note_count
            if set_writer_result is not None else 0
        ),
        # Entity type gate telemetry (Step 4.5)
        "entity_type_gate_rejected": _entity_type_gate_rejected,
        "brand_duplicate_suppressed_count": _brand_dedup_suppressed,
        # Honest card-count telemetry (split into distinct signals):
        # - insufficient_verified_candidates: true when Google returned too few
        #   verified places before note assembly — genuinely not enough supply.
        # - below_first_card_limit: true when the returned set is smaller than
        #   the configured default (may be caused by note validation, cap, or
        #   trust gate — not necessarily insufficient Google supply).
        "insufficient_verified_candidates": verified_count < 5,
        "below_first_card_limit": final_card_count < first_card_limit,
        "pre_assembly_verified_count": verified_count,
        # Note-writer skip telemetry (E — latency regression fix)
        "note_writer_skipped_no_valid_cards": (
            reasoning_result.failure_reason == "skipped_no_valid_cards"
        ),
        # True only when budget was positive but below the minimum useful window
        # (pre-skip before calling the LLM writer).
        "note_writer_skipped_low_budget": note_generation_low_budget,
        # True when past the SLA soft ceiling (budget already exhausted).
        "note_writer_skipped_past_soft_ceiling": note_generation_timed_out,
        "note_writer_skipped_below_card_threshold": (
            not note_generation_timed_out
            and not note_generation_low_budget
            and not cards_data
        ),
        "optional_reasoning_ms": latency.get("optional_reasoning_ms", 0),
        # Semantic price signal telemetry (internal only, never surfaced in UI)
        "semantic_cards_with_price_level": sum(
            1 for c in cards
            if getattr(getattr(c, "supporting_details", None), "price_level", None)
        ),
        "semantic_cards_with_price_range": sum(
            1 for c in cards
            if getattr(getattr(c, "supporting_details", None), "price_range", None)
        ),
        "semantic_cards_without_price_signal": sum(
            1 for c in cards
            if not getattr(getattr(c, "supporting_details", None), "price_level", None)
            and not getattr(getattr(c, "supporting_details", None), "price_range", None)
        ),
        "semantic_price_signal_path": "semantic_retrieval_v1",
        # Synthesized note-absence diagnostic. Inspect this field when
        # display_why_source=="timed_out" or display_why_validated==False.
        # Possible values:
        #   "wall_clock_timeout"    → set_writer thread cap fired (set_writer_timed_out=True)
        #   "no_budget"             → writer skipped before attempt (set_writer_skipped_budget=True)
        #   "all_notes_rejected"    → writer ran, all notes failed validation
        #   "past_soft_ceiling"     → SLA soft ceiling exceeded before writer ran
        #   "low_budget"            → budget positive but below minimum useful threshold
        #   "no_valid_cards"        → no verified cards reached note assembly
        #   "ok"                    → notes present
        "note_absent_reason": (
            "ok" if visible_note_count > 0
            else "no_budget" if _set_writer_skipped_budget
            else "wall_clock_timeout" if (
                set_writer_result is not None and set_writer_result.timed_out
            )
            else "all_notes_rejected" if (
                set_writer_result is not None
                and not set_writer_result.timed_out
                and set_writer_result.visible_note_count == 0
            )
            else "past_soft_ceiling" if note_generation_timed_out
            else "low_budget" if note_generation_low_budget
            else "no_valid_cards" if not cards_data
            else "unknown"
        ),
    }

    # ── Finalise credit ROI telemetry ─────────────────────────────────────────
    roi_tel.approved_note_count = reasoning_result.accepted_count if reasoning_result else 0
    roi_tel.visible_note_count = visible_note_count
    roi_tel.credits_spent_but_no_visible_notes = (
        roi_tel.tavily_attempted and visible_note_count == 0
    )
    # Control-plane ROI fields
    roi_tel.legacy_batched_reason_attempted = _legacy_batched_attempted
    if not _legacy_batched_attempted and reasoning_result.failure_reason:
        roi_tel.legacy_batched_reason_skipped_reason = reasoning_result.failure_reason
    roi_tel.final_card_count_before_notes = len(cards_data)
    roi_tel.final_card_count_after_notes = final_card_count
    roi_tel.card_count_collapsed_due_to_notes = False  # structural invariant: never true
    # Collect omission reasons from card reasons for ROI log
    for cr_val in card_reasons.values():
        if not cr_val.validated:
            _omit_reason = getattr(cr_val, "source", "unknown") or "unknown"
            roi_tel.record_omission(_omit_reason)

    # ── Latency summary fields ────────────────────────────────────────────────
    _elapsed_ms_final = int((time.monotonic() - t_pipeline_start) * 1000)
    _timeout_budget_consumed_pct = min(100, int(_elapsed_ms_final * 100 / DEFAULT_SLA.hard_cutoff_ms))
    _timeout_branches_triggered: List[str] = []
    if _set_writer_skipped_budget:
        _timeout_branches_triggered.append("set_writer_skipped_budget")
    if reasoning_result.failure_reason == "set_writer_attempted_no_fallback":
        _timeout_branches_triggered.append("set_writer_attempted_no_fallback")
    if note_generation_timed_out:
        _timeout_branches_triggered.append("note_generation_timed_out")
    if note_generation_low_budget:
        _timeout_branches_triggered.append("note_generation_low_budget")
    _editorial_skip = getattr(getattr(editorial_result, "telemetry", None), "skipped_reason", None)
    if _editorial_skip:
        _timeout_branches_triggered.append(f"editorial_skipped:{_editorial_skip}")
    _cross_source_skip = getattr(getattr(cross_source_result, "telemetry", None), "skipped_reason", None)
    if _cross_source_skip:
        _timeout_branches_triggered.append(f"cross_source_skipped:{_cross_source_skip}")

    _log_semantic_turn(
        user_query=user_query,
        frame=frame,
        queries=queries,
        latency=latency,
        provider_call_count=provider_call_count,
        provider_success_count=provider_success_count,
        raw_candidate_count=raw_count,
        deduped_candidate_count=verified_count,
        verified_entity_count=verified_count,
        rejection_stats=rejection_stats,
        final_card_count=final_card_count,
        t_pipeline_start=t_pipeline_start,
        outcome="ok" if final_card_count > 0 else "no_cards_after_trust_gate",
        rank_top3=rank_debug[:3],
        reason_source=reasoning_result.visible_note_source_counts and "llm_evidence_pack_v2" or "none",
        top_card_name=top_card_name,
        top_card_city=top_card_city,
        # SLA telemetry (v2 amendment §12)
        target_response_ms=DEFAULT_SLA.target_ms,
        soft_ceiling_ms=DEFAULT_SLA.soft_ceiling_ms,
        hard_cutoff_ms=DEFAULT_SLA.hard_cutoff_ms,
        first_return_card_limit=first_card_limit,
        pre_cap_card_count=pre_cap_count,
        visible_note_count=visible_note_count,
        hidden_note_count=cards_without_notes_count,
        fallback_note_visible_count=0,  # structural invariant: always 0
        note_generation_timed_out=note_generation_timed_out,
        cards_without_notes=cards_without_notes_count,
        more_options_cursor_present=False,  # cursor lives in router layer
        # PR #258 parallel retrieval telemetry
        critical_path_ms=critical_path_ms,
        non_critical_enrichment_ms=enrich_result.elapsed_ms,
        provider_fanout_ms=latency["provider_ms"],
        provider_timeout_counts=critical_result.timeout_count,
        provider_skipped_due_to_budget_counts=enrich_result.skipped_count if enrich_result.skip_reason else 0,
        google_critical_success=critical_result.success,
        google_critical_candidate_count=google_critical_candidate_count,
        google_verified_count=verified_count,
        non_critical_enrichment_used_count=enrich_result.used_count,
        non_critical_enrichment_skipped_count=enrich_result.skipped_count,
        remaining_budget_before_reasoning_ms=remaining_budget_before_reasoning_ms,
        # PR #259 evidence dossier telemetry
        dossier_telemetry=dossier_tel,
        # PR #275 cross-source enrichment telemetry
        cross_source_enrichment_telemetry=cross_source_tel,
        # PR #276 editorial enrichment telemetry
        editorial_enrichment_telemetry=editorial_tel,
        # PR #260 curator telemetry
        curator_telemetry=curator_tel,
        # PR #261 set-level writer telemetry
        set_writer_telemetry=set_writer_tel,
        # PR this: semantic frame finalization telemetry
        frame_finalization_telemetry={
            "raw_concepts": [(c.label, round(c.confidence, 2)) for c in frame.subtype_concepts],
            "finalized_venue_head": frame.subtype_concepts[0].label if frame.subtype_concepts else "",
            "suppressed_preference_nouns": getattr(frame, "suppressed_preference_nouns", []),
            "soft_preferences": getattr(frame, "soft_preferences", []),
            "normalized_soft_preferences": getattr(frame, "normalized_soft_preferences", []),
            "hidden_gem_preference_active": "hidden_gem" in getattr(frame, "normalized_soft_preferences", []),
            "temporal_constraints": getattr(frame, "temporal_constraints", []),
            "geography_hints": getattr(frame, "geography_hints", []),
            "retrieval_queries": queries,
            "insufficient_verified_candidates": verified_count < 5,
            "below_first_card_limit": final_card_count < first_card_limit,
            "pre_assembly_verified_count": verified_count,
            "final_card_count": final_card_count,
        },
        # Latency Observability v1: consolidated budget/timeout/note-preservation telemetry
        timeout_budget_consumed_pct=_timeout_budget_consumed_pct,
        timeout_branches_triggered=_timeout_branches_triggered,
        set_writer_primary_active=set_writer_primary_active,
    )

    # ── Credit ROI log (separate line for easy grep) ──────────────────────────
    logger.info(
        "semantic_retrieval_v1.credit_roi %r",
        roi_tel.as_log_dict(),
    )

    if not cards:
        return LiveResearchResult(source_status=SOURCE_NONE, provider_name=PROVIDER_NAME)

    # Route cards to the correct typed bucket so the concierge service can place
    # them under restaurants/attractions/hotels without any re-inspection.
    if vertical == "hotels":
        return LiveResearchResult(
            hotels=cards,
            source_status=SOURCE_LIVE_SEARCH,
            provider_name=PROVIDER_NAME,
        )
    if vertical == "attractions":
        return LiveResearchResult(
            attractions=cards,
            source_status=SOURCE_LIVE_SEARCH,
            provider_name=PROVIDER_NAME,
        )
    return LiveResearchResult(
        restaurants=cards,
        source_status=SOURCE_LIVE_SEARCH,
        provider_name=PROVIDER_NAME,
    )


def _minimal_safe_note(entity: Any) -> str:
    """Previously used as a last-resort fallback. Now returns "" (no note).

    The format "Name — rating★ from N reviews." is rejected by the validator
    (name_rating_only_template) because it repeats only visible card fields.
    An absent note is better than a generic template.

    This function is retained for API compatibility but must not be called
    for visible output. The caller in _run_pipeline now uses "" directly.
    """
    return ""


def _trust_gate(cards: List[Any]) -> tuple:
    """Final trust validation: assert every card has place_id, OPERATIONAL, maps URI."""
    passed = []
    rejected = 0
    for card in cards:
        gv = getattr(card, "google_verification", None)
        if gv is None:
            logger.warning("semantic_retrieval_v1.trust_gate: rejected no_google_verification name=%s",
                           getattr(card, "name", "?"))
            rejected += 1
            continue
        if not getattr(gv, "provider_place_id", None):
            logger.warning("semantic_retrieval_v1.trust_gate: rejected missing_place_id name=%s",
                           getattr(card, "name", "?"))
            rejected += 1
            continue
        status = (getattr(gv, "business_status", None) or "").upper()
        if status and status != "OPERATIONAL":
            logger.warning("semantic_retrieval_v1.trust_gate: rejected non_operational name=%s status=%s",
                           getattr(card, "name", "?"), status)
            rejected += 1
            continue
        if not getattr(gv, "google_maps_uri", None):
            logger.warning("semantic_retrieval_v1.trust_gate: rejected missing_maps_uri name=%s",
                           getattr(card, "name", "?"))
            rejected += 1
            continue
        passed.append(card)
    return passed, rejected


def _assemble_card_set(
    cards_data: List[Any],
    card_reasons: Dict[str, Any],
    frame: Any,
    note_generation_timed_out: bool,
    set_writer_primary_active: bool,
    vertical: str = "restaurants",
) -> tuple:
    """Assemble the final ordered card list from ranked entities and note reasons.

    Extracted from Step 8 so it can be unit-tested independently.

    Rules:
    - All paths: NEVER exclude a Google-verified card because its note failed
      validation or no note path ran.  Hide the note block (reason_validated=False)
      but keep the card.  "Hide invalid notes, not valid cards."
    - Deadline-exceeded path: include all entities without a note block.
    - Set-writer primary path: include all entities; hide note block for any
      card whose set-writer note failed validation.
    - Note-paths-skipped path (NoteDecision gate or budget skip): include all
      entities without a note block.
    - LLM fallback path: include all entities; cards without a validated note
      are included without a note block (reason_validated=False).

    Returns:
        (cards, rank_debug, excluded_unvalidated, visible_note_count,
         cards_without_notes_count)
    """
    from app.concierge.batched_reason_builder import CardReason
    cards: List[Any] = []
    rank_debug: List[Dict[str, Any]] = []
    excluded_unvalidated = 0
    visible_note_count = 0
    cards_without_notes_count = 0
    for i, (entity, _evidence, rank_score, _det_reason) in enumerate(cards_data, 1):
        if note_generation_timed_out and not set_writer_primary_active:
            # SLA exceeded AND no set-writer notes available — include card without note.
            # When set_writer_primary_active=True the set-writer already ran at Step 5.8
            # and card_reasons holds its pre-computed notes; skip this branch so those
            # notes are used in the else path below.
            card = _entity_to_card(
                entity, "", frame,
                reason_source="timed_out",
                reason_validated=False,
                vertical=vertical,
            )
            cards_without_notes_count += 1
        else:
            cr = card_reasons.get(str(i), CardReason())
            if not cr.validated:
                # Card is Google-verified but note failed validation or no note path ran.
                # Include the card without a note — never drop a verified card because of
                # note status.  The note block is hidden on the frontend when
                # reason_validated=False.  This holds for both set_writer_primary_active
                # and legacy batched paths.
                _note_src = cr.source if cr.source else (
                    "set_level_writer_v1" if set_writer_primary_active else "no_note"
                )
                card = _entity_to_card(
                    entity, "", frame,
                    reason_source=_note_src,
                    reason_validated=False,
                    vertical=vertical,
                )
                cards_without_notes_count += 1
            else:
                card = _entity_to_card(
                    entity, cr.note, frame,
                    reason_source=cr.source,
                    reason_validated=True,
                    vertical=vertical,
                )
                if card is not None:
                    visible_note_count += 1
        if card is not None:
            cards.append(card)
            rank_debug.append({
                "name": entity.name,
                "score": rank_score.as_dict(),
            })
    return cards, rank_debug, excluded_unvalidated, visible_note_count, cards_without_notes_count


def _entity_to_card(
    entity: "PlaceEntity",  # type: ignore[name-defined]
    reason: str,
    frame: "ExperienceFrame",  # type: ignore[name-defined]
    reason_source: str = "deterministic_safe_v1",
    reason_validated: bool = False,
    vertical: str = "restaurants",
) -> Optional[Any]:
    """Convert a verified PlaceEntity to the correct card type for the given vertical."""
    try:
        from app.models.concierge import (
            ConciergeDisplayFields,
            GoogleVerification,
            PlaceSupportingDetails,
            UnifiedAttractionResult,
            UnifiedHotelResult,
            UnifiedRestaurantResult,
        )

        # Derive display category from types + frame concept
        primary_concept = frame.subtype_concepts[0].label if frame.subtype_concepts else ""
        display_category = _derive_display_category(entity.types, entity.primary_type, primary_concept)

        # Preserve Google native rating scale (0–5) for display.
        rating_display = float(entity.rating) if entity.rating is not None else None
        meta_line: Optional[str] = None
        if rating_display is not None and entity.user_rating_count:
            meta_line = f"★ {rating_display:.1f} ({entity.user_rating_count:,} reviews)"
        elif rating_display is not None:
            meta_line = f"★ {rating_display:.1f}"

        gv = GoogleVerification(
            provider="google_places",
            provider_place_id=entity.place_id,
            name=entity.name,
            formatted_address=entity.formatted_address,
            lat=entity.lat,
            lng=entity.lng,
            business_status=entity.business_status,
            google_maps_uri=entity.google_maps_uri,
            website_uri=entity.website_uri,
            rating=entity.rating,
            user_rating_count=entity.user_rating_count,
            types=entity.types,
            confidence="high",
            score=1.0,
        )

        fallback_map = (
            f"https://maps.google.com/?q="
            f"{entity.name.replace(' ', '+')}+"
            f"{frame.destination.replace(' ', '+')}"
        )

        entity_price_level: Optional[str] = getattr(entity, "price_level", None) or None
        entity_price_range: Optional[Dict[str, Any]] = getattr(entity, "price_range", None) or None
        display_price = _format_display_price(entity_price_level, entity_price_range)

        _supporting = PlaceSupportingDetails(
            why_pick=reason,
            meta_line=meta_line,
            address=entity.formatted_address,
            category_label=display_category,
            price_level=entity_price_level,
            price_range=entity_price_range,
        )
        _display = ConciergeDisplayFields(
            display_name=entity.name,
            display_category=display_category,
            display_meta_line=meta_line,
            display_why=reason,
            display_price=display_price,
            display_badges=[],
            addability="addable",
            display_why_source=reason_source,
            display_why_validated=reason_validated,
        )
        _maps = entity.google_maps_uri or fallback_map

        if vertical == "attractions":
            return UnifiedAttractionResult(
                name=entity.name,
                source="Google Places",
                category=display_category or "Attraction",
                description=reason,
                neighborhood=entity.formatted_address,
                address=entity.formatted_address,
                rating=rating_display,
                review_count=entity.user_rating_count,
                maps_link=_maps,
                source_url=entity.website_uri,
                verified_place=True,
                google_verification=gv,
                primary_reason=reason,
                reason_source=reason_source,
                why_pick=reason,
                confidence="high",
                supporting_details=_supporting,
                display=_display,
                tags=[],
            )

        if vertical == "hotels":
            return UnifiedHotelResult(
                name=entity.name,
                source="Google Places",
                area_label=entity.formatted_address,
                rating=rating_display,
                maps_link=_maps,
                booking_url=entity.website_uri,
                source_url=entity.website_uri,
                verified_place=True,
                google_verification=gv,
                reason=reason,
                primary_reason=reason,
                reason_source=reason_source,
                why_pick=reason,
                confidence="high",
                supporting_details=_supporting,
                display=_display,
                tags=[],
            )

        return UnifiedRestaurantResult(
            name=entity.name,
            source="Google Places",
            cuisine=display_category,
            neighborhood=entity.formatted_address,
            rating=rating_display,
            review_count=entity.user_rating_count,
            summary=reason,
            primary_reason=reason,
            reason_source=reason_source,
            why_pick=reason,
            verified_place=True,
            google_verification=gv,
            supporting_details=_supporting,
            display=_display,
            maps_link=_maps,
            booking_link=entity.website_uri,
            tags=[],
        )
    except Exception as exc:
        logger.warning("semantic_retrieval_v1: card_build_failed name=%s error=%s", entity.name, exc)
        return None


def _derive_display_category(
    types: List[str],
    primary_type: Optional[str],
    concept_label: str,
) -> str:
    """Derive a user-facing category label from Google types and extracted concept."""
    _TYPE_LABELS = {
        "brewery": "Brewery / Taproom",
        "bar": "Bar",
        "cocktail_bar": "Cocktail Bar",
        "wine_bar": "Wine Bar",
        "night_club": "Nightclub",
        "restaurant": "Restaurant",
        "cafe": "Café",
        "coffee_shop": "Coffee Shop",
        "bakery": "Bakery",
        "sushi_restaurant": "Sushi Restaurant",
        "japanese_restaurant": "Japanese Restaurant",
        "ramen_restaurant": "Ramen Restaurant",
        "spanish_restaurant": "Spanish Restaurant",
        "mexican_restaurant": "Mexican Restaurant",
        "italian_restaurant": "Italian Restaurant",
        "french_restaurant": "French Restaurant",
        "chinese_restaurant": "Chinese Restaurant",
        "thai_restaurant": "Thai Restaurant",
        "indian_restaurant": "Indian Restaurant",
        "korean_restaurant": "Korean Restaurant",
        "vietnamese_restaurant": "Vietnamese Restaurant",
        "mediterranean_restaurant": "Mediterranean Restaurant",
        "greek_restaurant": "Greek Restaurant",
        "steak_house": "Steakhouse",
        "seafood_restaurant": "Seafood Restaurant",
        "pizza_restaurant": "Pizza Restaurant",
        "brunch_restaurant": "Brunch Spot",
        "breakfast_restaurant": "Breakfast Spot",
        "american_restaurant": "American Restaurant",
    }

    # First try primary_type
    if primary_type:
        label = _TYPE_LABELS.get((primary_type or "").lower())
        if label:
            return label

    # Then try types list
    for t in (types or []):
        label = _TYPE_LABELS.get((t or "").lower())
        if label:
            return label

    # Fall back to concept label if meaningful and not a modifier word.
    # "only", "casual", "cheap" etc. must never become a category label prefix
    # (prevents "Only Restaurant", "Casual Restaurant" fabrication).
    if (
        concept_label
        and len(concept_label) >= 3
        and concept_label.lower() not in _CONCEPT_LABEL_BLOCKLIST
    ):
        # Capitalise and add a suffix
        c = concept_label.strip().title()
        # If it's a drink-type concept (brewery, bar, etc.)
        drink_concepts = {"brewery", "taproom", "brewpub", "bar", "pub", "winery", "distillery"}
        if concept_label.lower() in drink_concepts:
            return c
        return f"{c} Restaurant"

    return "Restaurant"


def _log_per_card_notes(
    user_query: str,
    cards_data: List[Any],
    card_reasons: Dict[str, Any],
    frame: Any,
) -> None:
    """Emit one structured log line per card with exact visible note and evidence quality.

    Log key: semantic_retrieval_v1.per_card_notes
    Fields per card:
      - card_index (1-based)
      - card_name
      - evidence_adequacy (STRONG/OK/THIN)
      - modifier_status (confirmed/not_confirmed/none)
      - display_why_validated (bool)
      - display_why_source (str)
      - visible_note (first 220 chars of the accepted note, or "" if omitted)
    """
    location_modifiers = getattr(frame, "location_modifiers", []) or []
    geo_hints = getattr(frame, "geography_hints", []) or []
    # Use location_modifiers first; fall back to geography_hints (e.g. "river" from geo)
    primary_modifier = location_modifiers[0] if location_modifiers else (geo_hints[0] if geo_hints else "")

    # Generic modifier evidence term sets — used ONLY for telemetry/observability.
    # These are NOT retrieval eligibility gates, candidate inclusion filters, or ranking
    # signals. They simply expand the listing-context check for known geographic/setting
    # synonym clusters so per-card modifier_status telemetry is accurate.
    # New clusters can be added here without touching retrieval, routing, or ranking.
    _WATER_GEO_MODIFIER_TERMS = frozenset({
        "river", "riverwalk", "riverfront", "riverbank", "riverside",
        "waterfront", "lakefront", "waterside",
    })
    _SCENIC_VIEW_MODIFIER_TERMS = frozenset({
        "view", "rooftop", "panoramic", "scenic", "terrace", "overlook",
    })
    _GARDEN_MODIFIER_TERMS = frozenset({
        "garden", "courtyard", "patio", "terrace", "outdoor",
    })
    mod_lower = primary_modifier.lower()
    # Map modifier → synonym cluster for listing-context evidence check.
    # This is a generic pattern: modifier → related terms that might appear in
    # the venue's verified listing name or address.
    if any(r in mod_lower for r in ("river", "waterfront", "riverwalk", "waterside")):
        _geo_check_terms = _WATER_GEO_MODIFIER_TERMS
    elif any(r in mod_lower for r in ("view", "scenic", "rooftop", "panoramic", "overlook")):
        _geo_check_terms = _SCENIC_VIEW_MODIFIER_TERMS
    elif any(r in mod_lower for r in ("garden", "courtyard", "terrace", "patio")):
        _geo_check_terms = _GARDEN_MODIFIER_TERMS
    else:
        # For any other modifier, do a simple word-token match against the modifier itself
        _geo_check_terms = frozenset(w for w in mod_lower.split() if len(w) >= 3)

    per_card_entries = []
    for i, (entity, evidence, _rank_score, _det_reason) in enumerate(cards_data, 1):
        cr = card_reasons.get(str(i))
        if cr is None:
            continue

        # Modifier status for this card — distinguishes listing-context from unknown
        modifier_status = "none"
        if primary_modifier:
            # Check structured_facts first (explicit location_modifier_confirmed)
            loc_confirmed = any(
                "confirms" in f and primary_modifier.lower() in f.lower()
                for f in (evidence.structured_facts or [])
            )
            loc_not_confirmed = any(
                f.startswith(f"location_modifier_not_confirmed:{primary_modifier}")
                for f in (evidence.uncertainty_flags or [])
            )
            if loc_confirmed:
                modifier_status = "confirmed"
            elif loc_not_confirmed:
                modifier_status = "not_confirmed"
            elif _geo_check_terms:
                # For geo hints (river, view, etc.), check entity name/address
                name_lower = (getattr(entity, "name", "") or "").lower()
                addr_lower = (getattr(entity, "formatted_address", "") or "").lower()
                if any(term in name_lower for term in _geo_check_terms):
                    modifier_status = "confirmed_listing_context"
                elif any(term in addr_lower for term in _geo_check_terms):
                    modifier_status = "confirmed_address_context"
                else:
                    modifier_status = "unknown"
            else:
                modifier_status = "unknown"

        per_card_entries.append({
            "i": i,
            "name": entity.name,
            "adequacy": getattr(evidence, "evidence_adequacy", "THIN"),
            "modifier_status": modifier_status,
            "validated": cr.validated,
            "source": cr.source,
            "note": cr.note[:220] if cr.note else "",
        })

    logger.info(
        "semantic_retrieval_v1.per_card_notes "
        "query=%r cards=%r",
        user_query,
        per_card_entries,
    )


def _log_semantic_turn(
    *,
    user_query: str,
    frame: Any,
    queries: List[str],
    latency: Dict[str, int],
    provider_call_count: int,
    provider_success_count: int,
    raw_candidate_count: int,
    deduped_candidate_count: int,
    verified_entity_count: int,
    rejection_stats: Dict[str, Any],
    final_card_count: int,
    t_pipeline_start: float,
    outcome: str,
    rank_top3: Optional[List[Dict]] = None,
    reason_source: str = "deterministic_safe_v1",
    top_card_name: str = "",
    top_card_city: str = "",
    # SLA telemetry (v2 amendment §12)
    target_response_ms: int = DEFAULT_SLA.target_ms,
    soft_ceiling_ms: int = DEFAULT_SLA.soft_ceiling_ms,
    hard_cutoff_ms: int = DEFAULT_SLA.hard_cutoff_ms,
    first_return_card_limit: int = DEFAULT_SLA.first_card_limit,
    pre_cap_card_count: int = 0,
    visible_note_count: int = 0,
    hidden_note_count: int = 0,
    fallback_note_visible_count: int = 0,  # must always be 0
    note_generation_timed_out: bool = False,
    cards_without_notes: int = 0,
    more_options_cursor_present: bool = False,
    # PR #258 parallel retrieval telemetry
    critical_path_ms: int = 0,
    non_critical_enrichment_ms: int = 0,
    provider_fanout_ms: int = 0,
    provider_timeout_counts: int = 0,
    provider_skipped_due_to_budget_counts: int = 0,
    google_critical_success: bool = True,
    google_critical_candidate_count: int = 0,
    google_verified_count: int = 0,
    non_critical_enrichment_used_count: int = 0,
    non_critical_enrichment_skipped_count: int = 0,
    remaining_budget_before_reasoning_ms: int = 0,
    # PR #259 evidence dossier telemetry
    dossier_telemetry: Optional[Any] = None,  # Optional[EvidenceDossierTelemetry]
    # PR #275 cross-source enrichment telemetry
    cross_source_enrichment_telemetry: Optional[Dict[str, Any]] = None,
    # PR #276 editorial enrichment telemetry
    editorial_enrichment_telemetry: Optional[Dict[str, Any]] = None,
    # PR #260 curator telemetry
    curator_telemetry: Optional[Dict[str, Any]] = None,
    # PR #261 set-level writer telemetry
    set_writer_telemetry: Optional[Dict[str, Any]] = None,
    # PR this: semantic frame finalization telemetry
    frame_finalization_telemetry: Optional[Dict[str, Any]] = None,
    # Latency Architecture v1: consolidated budget/timeout telemetry
    timeout_budget_consumed_pct: int = 0,
    timeout_branches_triggered: Optional[List[str]] = None,
    # Latency Observability: set_writer_notes_in_final_cards is True only when
    # the set-writer ran as primary AND at least one post-cap card has a
    # validated note with source="set_level_writer_v1".  Derived from
    # set_writer_primary_active (path gate) + visible_note_count (final state).
    set_writer_primary_active: bool = False,
) -> None:
    """Log one structured semantic turn line for zero-card failure debugging."""
    total_ms = int((time.monotonic() - t_pipeline_start) * 1000)
    concepts_summary = (
        [(c.label, round(c.confidence, 2)) for c in frame.subtype_concepts]
        if hasattr(frame, "subtype_concepts") else []
    )
    venue_concept = (
        frame.subtype_concepts[0].label
        if getattr(frame, "subtype_concepts", None)
        else ""
    )
    logger.info(
        "semantic_retrieval_v1.turn "
        "pipeline_version=%s "
        "flag=on "
        "turn_mode=new_search "
        "query=%r "
        "destination=%r "
        "open_class_place_detected=%s "
        "venue_concept=%r "
        "concepts=%r "
        "geo_hints=%r "
        "location_modifiers=%r "
        "soft_preferences=%r "
        "negative_constraints=%r "
        "use_cases=%r "
        "value_signals=%r "
        "ambiguity_flags=%r "
        "retrieval_queries=%r "
        "provider_calls=%d "
        "provider_success=%d "
        "raw_candidates=%d "
        "deduped_candidates=%d "
        "verified_entities=%d "
        "rejection_stats=%r "
        "final_card_count=%d "
        "reason_source=%s "
        "grounded_reason_attempted=%s "
        "grounded_reason_success=%s "
        "destination_penalized=%d "
        "det_reason_rejected=%d "
        "top_card_name=%r "
        "top_card_city=%r "
        "latency_by_stage=%r "
        "total_ms=%d "
        "rank_top3=%r "
        "outcome=%s "
        "turn_total_ms=%d "
        "target_response_ms=%d "
        "soft_ceiling_ms=%d "
        "hard_cutoff_ms=%d "
        "first_return_card_limit=%d "
        "pre_cap_card_count=%d "
        "visible_note_count=%d "
        "hidden_note_count=%d "
        "fallback_note_visible_count=%d "
        "note_generation_timed_out=%s "
        "cards_without_notes=%d "
        "more_options_cursor_present=%s "
        "critical_path_ms=%d "
        "non_critical_enrichment_ms=%d "
        "provider_fanout_ms=%d "
        "provider_timeout_counts=%d "
        "provider_skipped_due_to_budget_counts=%d "
        "google_critical_success=%s "
        "google_critical_candidate_count=%d "
        "google_verified_count=%d "
        "non_critical_enrichment_used_count=%d "
        "non_critical_enrichment_skipped_count=%d "
        "remaining_budget_before_reasoning_ms=%d "
        "timeout_budget_consumed_pct=%d "
        "timeout_branches_triggered=%r",
        PIPELINE_VERSION,
        user_query,
        getattr(frame, "destination", ""),
        getattr(frame, "open_class_place_detected", False),
        venue_concept,
        concepts_summary,
        getattr(frame, "geography_hints", []),
        getattr(frame, "location_modifiers", []),
        getattr(frame, "soft_preferences", []),
        getattr(frame, "negative_constraints", []),
        getattr(frame, "use_cases", []),
        getattr(frame, "value_signals", []),
        getattr(frame, "ambiguity_flags", []),
        queries,
        provider_call_count,
        provider_success_count,
        raw_candidate_count,
        deduped_candidate_count,
        verified_entity_count,
        rejection_stats,
        final_card_count,
        reason_source,
        rejection_stats.get("grounded_reason_attempted", False),
        rejection_stats.get("grounded_reason_success", False),
        rejection_stats.get("destination_penalized_count", 0),
        rejection_stats.get("det_reason_rejected_count", 0),
        top_card_name,
        top_card_city,
        latency,
        total_ms,
        rank_top3 or [],
        outcome,
        # SLA telemetry — appended last for backwards-compatible log parsing
        total_ms,
        target_response_ms,
        soft_ceiling_ms,
        hard_cutoff_ms,
        first_return_card_limit,
        pre_cap_card_count,
        visible_note_count,
        hidden_note_count,
        fallback_note_visible_count,
        note_generation_timed_out,
        cards_without_notes,
        more_options_cursor_present,
        # PR #258 parallel retrieval telemetry values
        critical_path_ms,
        non_critical_enrichment_ms,
        provider_fanout_ms,
        provider_timeout_counts,
        provider_skipped_due_to_budget_counts,
        google_critical_success,
        google_critical_candidate_count,
        google_verified_count,
        non_critical_enrichment_used_count,
        non_critical_enrichment_skipped_count,
        remaining_budget_before_reasoning_ms,
        # Latency Architecture v1 values
        timeout_budget_consumed_pct,
        timeout_branches_triggered or [],
    )
    # Latency Architecture v1: single-line latency summary for easy grep diagnosis.
    # Key: semantic_retrieval_v1.latency_summary
    logger.info(
        "semantic_retrieval_v1.latency_summary "
        "total_ms=%d "
        "google_retrieval_ms=%d "
        "entity_rank_ms=%d "
        "google_place_details_ms=%d "
        "cross_source_enrichment_ms=%d "
        "editorial_enrichment_ms=%d "
        "dossier_ms=%d "
        "curator_ms=%d "
        "set_writer_ms=%d "
        "note_assembly_ms=%d "
        "trust_gate_ms=%d "
        "optional_reasoning_ms=%d "
        "timeout_budget_consumed_pct=%d "
        "timeout_branches=%r "
        "cards_returned=%d "
        "cards_with_notes=%d "
        "cards_without_notes=%d "
        "set_writer_notes_in_final_cards=%s",
        total_ms,
        latency.get("provider_ms", 0),
        latency.get("entity_ms", 0) + latency.get("rank_ms", 0),
        latency.get("enrich_ms", 0),
        latency.get("cross_source_ms", 0),
        latency.get("editorial_ms", 0),
        latency.get("dossier_ms", 0),
        latency.get("curator_ms", 0),
        latency.get("set_writer_ms", 0),
        latency.get("batched_reason_ms", 0),
        latency.get("trust_gate_ms", 0),
        latency.get("optional_reasoning_ms", 0),
        timeout_budget_consumed_pct,
        timeout_branches_triggered or [],
        final_card_count,
        visible_note_count,
        hidden_note_count,
        # True only when set-writer was primary AND at least one post-cap card
        # has a validated note (visible_note_count derived from actual card objects).
        set_writer_primary_active and visible_note_count > 0,
    )
    # PR #259 dossier telemetry — separate log line to preserve turn-line parsers.
    if dossier_telemetry is not None:
        logger.info(
            "semantic_retrieval_v1.dossier_telemetry %r",
            dossier_telemetry.as_log_dict(),
        )
    # PR #275 cross-source enrichment telemetry — separate log line.
    if cross_source_enrichment_telemetry:
        logger.info(
            "semantic_retrieval_v1.cross_source_enrichment_telemetry %r",
            cross_source_enrichment_telemetry,
        )
    # PR #276 editorial enrichment telemetry — separate log line.
    if editorial_enrichment_telemetry:
        logger.info(
            "semantic_retrieval_v1.editorial_enrichment_telemetry %r",
            editorial_enrichment_telemetry,
        )
    # PR #260 curator telemetry — separate log line.
    if curator_telemetry is not None:
        logger.info(
            "semantic_retrieval_v1.curated_set_telemetry %r",
            curator_telemetry,
        )
    # PR #261 set-level writer telemetry — separate log line.
    if set_writer_telemetry is not None:
        logger.info(
            "semantic_retrieval_v1.set_writer_telemetry %r",
            set_writer_telemetry,
        )
        # PR #267 reviewer telemetry — emitted as sub-key of set_writer_telemetry
        # if the reviewer ran this turn. Backend-only; never surfaced to users.
        reviewer_tel = set_writer_telemetry.get("reviewer_telemetry")
        if reviewer_tel:
            logger.info(
                "semantic_retrieval_v1.reviewer_telemetry %r",
                reviewer_tel,
            )
    # PR this: frame finalization telemetry — separate log line (backend-only).
    if frame_finalization_telemetry is not None:
        logger.info(
            "semantic_retrieval_v1.frame_finalization_telemetry %r",
            frame_finalization_telemetry,
        )
