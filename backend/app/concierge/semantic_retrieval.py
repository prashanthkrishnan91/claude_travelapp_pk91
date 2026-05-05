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
    from app.models.concierge import SOURCE_LIVE_SEARCH, SOURCE_NONE

    latency: Dict[str, int] = {}

    # ── Step 1: ExperienceFrame extraction ───────────────────────────────────
    t0 = time.monotonic()
    from app.concierge.frame_extractor import extract_frame
    frame = extract_frame(user_query, destination)
    latency["frame_ms"] = int((time.monotonic() - t0) * 1000)

    logger.debug(
        "semantic_retrieval_v1.frame query=%r concepts=%r geo=%r prefs=%r neg=%r",
        user_query,
        [(c.label, round(c.confidence, 2)) for c in frame.subtype_concepts],
        frame.geography_hints,
        frame.soft_preferences,
        frame.negative_constraints,
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
        return LiveResearchResult(source_status=SOURCE_NONE, provider_name=PROVIDER_NAME)

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
    from app.concierge.ranker import rank_entities, build_evidence_bundle
    ranked = rank_entities(entities, frame, top_n=max_cards)
    latency["rank_ms"] = int((time.monotonic() - t0) * 1000)

    # ── Step 6+7: Evidence bundles + SafeReasonBuilder ───────────────────────
    t0 = time.monotonic()
    from app.concierge.safe_reason_builder import build_safe_reason

    cards = []
    rank_debug: List[Dict[str, Any]] = []
    for entity, rank_score in ranked:
        evidence = build_evidence_bundle(entity, frame, rank_score)
        reason = build_safe_reason(entity, evidence, frame, rank_score)
        card = _entity_to_card(entity, reason, frame)
        if card is not None:
            cards.append(card)
            rank_debug.append({
                "name": entity.name,
                "score": rank_score.as_dict(),
            })

    latency["reason_ms"] = int((time.monotonic() - t0) * 1000)

    # ── Step 8: TrustGate final pass ─────────────────────────────────────────
    t0 = time.monotonic()
    cards, trust_rejected = _trust_gate(cards)
    latency["trust_gate_ms"] = int((time.monotonic() - t0) * 1000)

    final_card_count = len(cards)

    # ── Step 9: Structured observability ─────────────────────────────────────
    rejection_stats = {**vars(entity_stats), "trust_gate_rejected": trust_rejected}
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
    )

    if not cards:
        return LiveResearchResult(source_status=SOURCE_NONE, provider_name=PROVIDER_NAME)

    return LiveResearchResult(
        restaurants=cards,
        source_status=SOURCE_LIVE_SEARCH,
        provider_name=PROVIDER_NAME,
    )


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

        # Rating display
        rating_10 = round(entity.rating * 2, 1) if entity.rating is not None else None
        meta_line: Optional[str] = None
        if rating_10 is not None and entity.user_rating_count:
            meta_line = f"★ {rating_10:.1f} ({entity.user_rating_count:,} reviews)"
        elif rating_10 is not None:
            meta_line = f"★ {rating_10:.1f}"

        gv = GoogleVerification(
            provider="google_places",
            provider_place_id=entity.place_id,
            name=entity.name,
            formatted_address=entity.formatted_address,
            lat=entity.lat,
            lng=entity.lng,
            business_status="OPERATIONAL",
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
            rating=rating_10,
            review_count=entity.user_rating_count,
            summary=reason,
            primary_reason=reason,
            reason_source="deterministic_safe_v1",
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
                display_why_source="deterministic_safe_v1",
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
) -> None:
    """Log one structured semantic turn line for zero-card failure debugging."""
    total_ms = int((time.monotonic() - t_pipeline_start) * 1000)
    concepts_summary = (
        [(c.label, round(c.confidence, 2)) for c in frame.subtype_concepts]
        if hasattr(frame, "subtype_concepts") else []
    )
    logger.info(
        "semantic_retrieval_v1.turn "
        "pipeline_version=%s "
        "flag=on "
        "turn_mode=new_search "
        "query=%r "
        "destination=%r "
        "concepts=%r "
        "geo_hints=%r "
        "retrieval_queries=%r "
        "provider_calls=%d "
        "provider_success=%d "
        "raw_candidates=%d "
        "deduped_candidates=%d "
        "verified_entities=%d "
        "rejection_stats=%r "
        "final_card_count=%d "
        "reason_source=deterministic_safe_v1 "
        "latency_by_stage=%r "
        "total_ms=%d "
        "rank_top3=%r "
        "outcome=%s",
        PIPELINE_VERSION,
        user_query,
        getattr(frame, "destination", ""),
        concepts_summary,
        getattr(frame, "geography_hints", []),
        queries,
        provider_call_count,
        provider_success_count,
        raw_candidate_count,
        deduped_candidate_count,
        verified_entity_count,
        rejection_stats,
        final_card_count,
        latency,
        total_ms,
        rank_top3 or [],
        outcome,
    )
