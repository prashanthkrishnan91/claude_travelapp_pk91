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
No Tavily, editorial, Yelp, or Foursquare calls in this module.
No SQL. No frontend changes. No personalization. No vector search.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, FrozenSet, List, Optional, Set

logger = logging.getLogger(__name__)

PROVIDER_NAME = "semantic_retrieval_v1"
PIPELINE_VERSION = "semantic_retrieval_v1"
_MAX_CARDS = 8


def run_semantic_retrieval_v1(
    user_query: str,
    destination: str,
    prior_identity_keys: Optional[FrozenSet[str]] = None,
    api_key: Optional[str] = None,
    timeout: float = 5.0,
    max_cards: int = _MAX_CARDS,
) -> "LiveResearchResult":  # type: ignore[name-defined]
    """Run the full Semantic Retrieval v1 pipeline for one concierge turn.

    Args:
        user_query: User's natural-language place ask.
        destination: Trip destination city.
        prior_identity_keys: Already-shown card keys (for dedup).
        api_key: Google Places API key (falls back to env var).
        timeout: Per-provider-call deadline in seconds.
        max_cards: Maximum cards to return.

    Returns:
        LiveResearchResult with verified restaurant cards, or empty result
        if the pipeline fails or returns no verified entities.
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
) -> "LiveResearchResult":  # type: ignore[name-defined]
    from app.services.live_research import LiveResearchResult
    from app.models.concierge import SOURCE_LIVE_SEARCH, SOURCE_NONE, SOURCE_UNAVAILABLE

    latency: Dict[str, int] = {}

    # ── Step 1: ExperienceFrame extraction ───────────────────────────────────
    t0 = time.monotonic()
    from app.concierge.frame_extractor import extract_frame
    frame = extract_frame(user_query, destination)
    latency["frame_ms"] = int((time.monotonic() - t0) * 1000)

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

    # ── Step 3: Provider fanout (parallel Google Text Search) ────────────────
    t0 = time.monotonic()
    from app.concierge.provider_executor import execute_fanout
    provider_results = execute_fanout(queries, api_key=api_key, timeout=timeout)
    latency["provider_ms"] = int((time.monotonic() - t0) * 1000)

    provider_call_count = len(provider_results)
    provider_success_count = sum(1 for r in provider_results if r.succeeded)
    per_query_latencies = {r.query: r.latency_ms for r in provider_results}

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

    # ── Step 5: SemanticRanker v1 ────────────────────────────────────────────
    t0 = time.monotonic()
    from app.concierge.ranker import rank_entities_with_stats, build_evidence_bundle
    ranked, ranker_stats = rank_entities_with_stats(entities, frame, top_n=max_cards)
    latency["rank_ms"] = int((time.monotonic() - t0) * 1000)

    # ── Step 6: Evidence bundles + deterministic SafeReasonBuilder ───────────
    t0 = time.monotonic()
    from app.concierge.safe_reason_builder import build_safe_reason
    from app.concierge.reason_validator import validate_reason

    # Build evidence bundles, deterministic reasons, and validate each one.
    # A deterministic reason that fails validation falls back to a minimal
    # safe note built from verified facts only (rating + type label).
    cards_data: List[Any] = []  # (entity, evidence, rank_score, det_reason)
    det_reason_rejected_count = 0

    for entity, rank_score in ranked:
        evidence = build_evidence_bundle(entity, frame, rank_score)
        det_reason = build_safe_reason(entity, evidence, frame, rank_score)

        # Validate the deterministic reason using the same validator applied
        # to LLM output. If it fails, fall back to a minimal honest note.
        is_valid, rejection = validate_reason(det_reason, frame, evidence)
        if not is_valid:
            logger.warning(
                "semantic_retrieval_v1: det_reason_rejected "
                "name=%s rejection=%s reason=%r",
                entity.name, rejection, det_reason,
            )
            det_reason = _minimal_safe_note(entity)
            det_reason_rejected_count += 1

        cards_data.append((entity, evidence, rank_score, det_reason))

    latency["det_reason_ms"] = int((time.monotonic() - t0) * 1000)

    # ── Step 7: Batched grounded reasoning (LLM path, budget-gated) ─────────
    t0 = time.monotonic()
    from app.concierge.batched_reason_builder import build_batched_reasons, _flag_enabled as _batched_flag

    batched_reasons = build_batched_reasons(cards_data, frame)
    reason_source = "batched_grounded_v1" if _batched_flag() else "deterministic_safe_v1"
    latency["batched_reason_ms"] = int((time.monotonic() - t0) * 1000)

    # ── Step 8: Assemble final cards ─────────────────────────────────────────
    cards = []
    rank_debug: List[Dict[str, Any]] = []
    for i, (entity, evidence, rank_score, det_reason) in enumerate(cards_data, 1):
        reason = batched_reasons.get(str(i), det_reason)
        card = _entity_to_card(entity, reason, frame, reason_source=reason_source)
        if card is not None:
            cards.append(card)
            rank_debug.append({
                "name": entity.name,
                "score": rank_score.as_dict(),
            })

    latency["reason_ms"] = latency["det_reason_ms"] + latency["batched_reason_ms"]

    # ── Step 9: TrustGate final pass ─────────────────────────────────────────
    t0 = time.monotonic()
    cards, trust_rejected = _trust_gate(cards)
    latency["trust_gate_ms"] = int((time.monotonic() - t0) * 1000)

    final_card_count = len(cards)

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
        addr = getattr(cards[0], "neighborhood", "") or ""
        # Extract city segment from formatted address for observability
        addr_parts = [p.strip() for p in addr.split(",")]
        for part in addr_parts:
            if not any(c.isdigit() for c in part) and len(part) > 2:
                if part.strip().lower() not in {"usa", "us"}:
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
        "det_reason_rejected_count": det_reason_rejected_count,
        "grounded_reason_attempted": _batched_flag(),
        "grounded_reason_success": _batched_flag() and reason_source == "batched_grounded_v1",
    }
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
        reason_source=reason_source,
        top_card_name=top_card_name,
        top_card_city=top_card_city,
    )

    if not cards:
        return LiveResearchResult(source_status=SOURCE_NONE, provider_name=PROVIDER_NAME)

    return LiveResearchResult(
        restaurants=cards,
        source_status=SOURCE_LIVE_SEARCH,
        provider_name=PROVIDER_NAME,
    )


def _minimal_safe_note(entity: Any) -> str:
    """Ultra-safe fallback note when deterministic reason fails validation.

    Uses only verified structural fields: Google type and rating.
    Never emits city name, geo claims, or qualitative assertions.
    """
    parts = []
    if getattr(entity, "primary_type", None):
        type_label = entity.primary_type.replace("_", " ").title()
        parts.append(f"Verified {type_label}")
    elif getattr(entity, "types", None):
        type_label = entity.types[0].replace("_", " ").title()
        parts.append(f"Verified {type_label}")
    else:
        parts.append("Verified Google place")

    rating = getattr(entity, "rating", None)
    review_count = getattr(entity, "user_rating_count", None)
    if rating is not None and review_count:
        parts.append(f"{rating:.1f}★ ({review_count:,} reviews)")
    elif rating is not None:
        parts.append(f"{rating:.1f}★")

    return "; ".join(parts) + "."


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


def _entity_to_card(
    entity: "PlaceEntity",  # type: ignore[name-defined]
    reason: str,
    frame: "ExperienceFrame",  # type: ignore[name-defined]
    reason_source: str = "deterministic_safe_v1",
) -> Optional[Any]:
    """Convert a verified PlaceEntity to a UnifiedRestaurantResult card."""
    try:
        from app.models.concierge import (
            ConciergeDisplayFields,
            GoogleVerification,
            PlaceSupportingDetails,
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
            supporting_details=PlaceSupportingDetails(
                why_pick=reason,
                meta_line=meta_line,
                address=entity.formatted_address,
                category_label=display_category,
            ),
            display=ConciergeDisplayFields(
                display_name=entity.name,
                display_category=display_category,
                display_meta_line=meta_line,
                display_why=reason,
                display_badges=[],
                addability="addable",
                display_why_source=reason_source,
            ),
            maps_link=entity.google_maps_uri or fallback_map,
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

    # Fall back to concept label if meaningful
    if concept_label and len(concept_label) >= 3:
        # Capitalise and add a suffix
        c = concept_label.strip().title()
        # If it's a drink-type concept (brewery, bar, etc.)
        drink_concepts = {"brewery", "taproom", "brewpub", "bar", "pub", "winery", "distillery"}
        if concept_label.lower() in drink_concepts:
            return c
        return f"{c} Restaurant"

    return "Restaurant"


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
        "outcome=%s",
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
    )
