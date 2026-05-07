"""AI concierge endpoint — contextual travel recommendations powered by Claude."""

import json
import logging
import re
import time
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, TypeAdapter, ValidationError

from app.concierge.contracts import (
    ConciergeTypedResponse,
    PlaceRecommendationsResponse,
    TripAdviceResponse,
    UnsupportedResponse,
)
from app.concierge.builders.trip_advice import build_trip_advice_payload
from app.concierge.context import (
    build_context_window,
    classify_turn,
    derive_category_hint,
    is_more_options_continuation,
    log_context_turn,
)
from app.concierge.result_pool import _GLOBAL_CONTINUATION_POOL
from app.concierge.context_resolver import resolve_refine_previous
from app.concierge.logging import persist_concierge_request_log, request_log_event
from app.models.concierge import (
    UnifiedAttractionResult,
    UnifiedHotelResult,
    UnifiedRestaurantResult,
)
from app.concierge.router import RouteDecision, route_prompt
from app.core.config import get_settings
from app.core.deps import DB, CurrentUserID
from app.core.cost_guardrails import GuardrailRule, guardrails
from app.models.concierge import (
    ConciergeCacheClearRequest,
    ConciergeCacheClearResponse,
    ConciergeDebugRequest,
    ConciergeMessage,
    ConciergeRequest,
    ConciergeResponse,
    ConciergeSearchRequest,
)
from app.services.concierge import ConciergeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])
_typed_response_adapter = TypeAdapter(ConciergeTypedResponse)


def _validate_reused_cards(raw_cards: List[Any], model_cls: Any) -> List[Any]:
    """Deserialize raw card dicts into typed Pydantic models; drop any that fail."""
    result = []
    for card in raw_cards:
        try:
            result.append(model_cls.model_validate(card))
        except Exception:
            logger.warning(
                "concierge.context_resolver.card_validation_failed model=%s",
                model_cls.__name__,
            )
    return result


def _build_reuse_summary(rerank_rule: str, n: int) -> str:
    if rerank_rule == "best_one":
        return "Here is the top pick from your previous search results."
    if rerank_rule == "compare":
        return "Here are your previous search results for comparison."
    # top_n
    return f"Here are the top {n} picks from your previous search results."


def _normalize_free_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"\s+", " ", text)


def _get_value(source: Any, key: str) -> Any:
    if isinstance(source, dict):
        return source.get(key)
    return getattr(source, key, None)


def _normalize_identity_text(value: Any) -> str:
    text = _normalize_free_text(value)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _card_identity_keys(card: Any) -> set[str]:
    """Build stable identity keys for safe duplicate exclusion."""
    keys: set[str] = set()
    gv = _get_value(card, "google_verification")
    id_candidates = [
        _get_value(card, "provider_place_id"),
        _get_value(card, "google_place_id"),
        _get_value(card, "place_id"),
        _get_value(gv, "provider_place_id"),
        _get_value(gv, "google_place_id"),
        _get_value(gv, "place_id"),
    ]
    for candidate in id_candidates:
        if candidate:
            keys.add(f"pid:{_normalize_free_text(candidate)}")
    for uri_candidate in (
        _get_value(card, "google_maps_uri"),
        _get_value(gv, "google_maps_uri"),
    ):
        if uri_candidate:
            keys.add(f"gmaps:{_normalize_free_text(uri_candidate)}")
    name = _get_value(card, "name") or _get_value(gv, "name")
    address = (
        _get_value(card, "address")
        or _get_value(card, "formatted_address")
        or _get_value(gv, "formatted_address")
    )
    if name and address:
        keys.add(f"name_addr:{_normalize_identity_text(name)}|{_normalize_identity_text(address)}")
    return keys


def _exclude_prior_verified_cards(
    response: PlaceRecommendationsResponse,
    prior_pool: Optional[Dict[str, Any]],
) -> tuple[PlaceRecommendationsResponse, Dict[str, int]]:
    stats = {
        "prior_exclusion_count": 0,
        "raw_candidate_count": len(response.restaurants) + len(response.attractions) + len(response.hotels),
        "verified_candidate_count": len(response.restaurants) + len(response.attractions) + len(response.hotels),
        "excluded_prior_duplicate_count": 0,
        "final_unique_count": 0,
    }
    if not isinstance(prior_pool, dict):
        stats["final_unique_count"] = stats["raw_candidate_count"]
        return response, stats
    prior_keys: set[str] = set()
    for bucket in ("restaurants", "attractions", "hotels"):
        for raw_card in (prior_pool.get(bucket) or []):
            if not isinstance(raw_card, dict):
                continue
            prior_keys.update(_card_identity_keys(raw_card))
    stats["prior_exclusion_count"] = len(prior_keys)
    if not prior_keys:
        stats["final_unique_count"] = stats["raw_candidate_count"]
        return response, stats

    before = stats["raw_candidate_count"]
    response.restaurants = [c for c in response.restaurants if _card_identity_keys(c).isdisjoint(prior_keys)]
    response.attractions = [c for c in response.attractions if _card_identity_keys(c).isdisjoint(prior_keys)]
    response.hotels = [c for c in response.hotels if _card_identity_keys(c).isdisjoint(prior_keys)]
    after = len(response.restaurants) + len(response.attractions) + len(response.hotels)
    stats["final_unique_count"] = after
    stats["excluded_prior_duplicate_count"] = max(0, before - after)
    return response, stats


def _build_prior_identity_keys_set(prior_card_pool: Optional[Dict[str, Any]]) -> frozenset:
    """Build a frozenset of stable identity keys from a prior card pool dict."""
    if not isinstance(prior_card_pool, dict):
        return frozenset()
    keys: set = set()
    for bucket in ("restaurants", "attractions", "hotels"):
        for raw_card in (prior_card_pool.get(bucket) or []):
            if isinstance(raw_card, dict):
                keys.update(_card_identity_keys(raw_card))
    return frozenset(keys)


def _filter_pool_buckets_by_identity(
    buckets: Dict[str, Any],
    prior_keys: frozenset,
) -> tuple[Dict[str, List], int]:
    """Filter pool card dicts against prior identity keys. Returns (filtered_buckets, unique_count)."""
    result: Dict[str, List] = {}
    for bucket in ("restaurants", "attractions", "hotels"):
        cards = buckets.get(bucket) or []
        result[bucket] = [c for c in cards if _card_identity_keys(c).isdisjoint(prior_keys)]
    unique_count = sum(len(v) for v in result.values())
    return result, unique_count


def _build_place_response_from_pool(
    buckets: Dict[str, Any],
    query_hint: str,
) -> PlaceRecommendationsResponse:
    """Build a PlaceRecommendationsResponse from raw pool card dicts."""
    from app.models.concierge import (
        UnifiedAttractionResult,
        UnifiedHotelResult,
        UnifiedRestaurantResult,
    )

    def _load_cards(raw_list: List, model_cls: Any) -> List[Any]:
        result = []
        for raw in (raw_list or []):
            try:
                result.append(model_cls.model_validate(raw) if isinstance(raw, dict) else raw)
            except Exception:
                pass
        return result

    restaurants = _load_cards(buckets.get("restaurants"), UnifiedRestaurantResult)
    attractions = _load_cards(buckets.get("attractions"), UnifiedAttractionResult)
    hotels = _load_cards(buckets.get("hotels"), UnifiedHotelResult)
    n = len(restaurants) + len(attractions) + len(hotels)
    return PlaceRecommendationsResponse(
        response=f"Here are more {query_hint} from your search.",
        intent="restaurants" if restaurants else ("attractions" if attractions else "hotels"),
        retrieval_used=True,
        source_status="pool",
        cached=False,
        restaurants=restaurants,
        attractions=attractions,
        hotels=hotels,
        turn_mode="new_search",
    )


def _refill_variant_queries(query_hint: str) -> List[str]:
    """Return bounded variant queries for a refill attempt when pool is empty."""
    base = (query_hint or "").strip().lower()
    if not base:
        return []
    return [
        f"best {base}",
        f"popular {base}",
    ]


def _response_identity_keys(response: PlaceRecommendationsResponse) -> frozenset:
    """Build identity keys from cards already in a PlaceRecommendationsResponse."""
    keys: set = set()
    for card in list(response.restaurants) + list(response.attractions) + list(response.hotels):
        keys.update(_card_identity_keys(card))
    return frozenset(keys)


def build_typed_concierge_response(
    service: ConciergeService,
    payload: ConciergeSearchRequest,
    user_id: UUID,
) -> tuple[ConciergeTypedResponse, RouteDecision]:
    """Build and validate the typed concierge response contract."""
    settings = get_settings()
    _t_btcr_start = time.perf_counter()
    _ctx_ms = 0
    _route_prompt_ms = 0
    _service_search_ms = 0
    _typed_val_ms = 0

    # Context classification — classifies and logs. PR 2: may skip provider call.
    turn_mode = "new_search"
    rerank_rule = "none"
    ctx = None
    _t_ctx = time.perf_counter()
    try:
        ctx = build_context_window(service._db, payload.trip_id)
        turn_mode, rerank_rule = classify_turn(payload.user_query, ctx)
        provider_call_expected = not (
            getattr(settings, "concierge_context_v1_enabled", False)
            and turn_mode == "refine_previous"
            and rerank_rule in ("top_n", "best_one", "compare")
            and ctx.has_prior_cards
        )
        log_context_turn(
            trip_id=payload.trip_id,
            turn_mode=turn_mode,
            rerank_rule=rerank_rule,
            card_pool_size=ctx.card_pool_size,
            has_prior_cards=ctx.has_prior_cards,
            source_message_id=ctx.source_message_id,
            reset_reason=ctx.reset_reason,
            provider_call_expected_for_future_mode=provider_call_expected,
        )
    except Exception:
        logger.exception(
            "concierge.context.classify_failed trip_id=%s", payload.trip_id
        )
    _ctx_ms = int((time.perf_counter() - _t_ctx) * 1000)

    # PR 2: attempt card reuse when flag is ON and turn qualifies.
    # getattr guard: safe when settings is a SimpleNamespace/stub without the field.
    _flag_on = getattr(settings, "concierge_context_v1_enabled", False)
    if (
        _flag_on
        and turn_mode == "refine_previous"
        and ctx is not None
    ):
        try:
            resolved = resolve_refine_previous(ctx, rerank_rule, payload.user_query)
            if resolved is not None:
                restaurants = _validate_reused_cards(resolved.restaurants, UnifiedRestaurantResult)
                attractions = _validate_reused_cards(resolved.attractions, UnifiedAttractionResult)
                hotels = _validate_reused_cards(resolved.hotels, UnifiedHotelResult)

                n_after = len(restaurants) + len(attractions) + len(hotels)
                if n_after > 0:
                    summary = _build_reuse_summary(rerank_rule, n_after)
                    typed_payload = PlaceRecommendationsResponse(
                        response=summary,
                        intent=resolved.prior_intent or "general",
                        retrieval_used=True,
                        source_status="reused_context",
                        cached=False,
                        restaurants=restaurants,
                        attractions=attractions,
                        hotels=hotels,
                        turn_mode="refine_previous",
                        context_reuse={
                            "provider_call": False,
                            "card_pool_size": resolved.pool_size_before,
                            "cards_returned": n_after,
                            "source_message_id": resolved.source_message_id,
                            "rerank_rule": resolved.rerank_rule,
                            "filter_applied": None,
                        },
                    )
                    decision = RouteDecision(
                        response_type="place_recommendations",
                        stage1_prior={"place_recommendations": 1.0, "trip_advice": 0.0, "unsupported": 0.0},
                        stage2_confidence=1.0,
                        code="refine_previous_card_reuse",
                    )
                    try:
                        validated = _typed_response_adapter.validate_python(typed_payload)
                        return validated, decision
                    except ValidationError:
                        logger.warning(
                            "concierge.context_resolver.validation_failed trip_id=%s "
                            "falling_through=true",
                            payload.trip_id,
                        )
        except Exception:
            logger.exception(
                "concierge.context_resolver.error trip_id=%s falling_through=true",
                payload.trip_id,
            )

    # PR 2.5 / PR 3: more-options continuation — fast pagination through verified places.
    #
    # Algorithm:
    #   1. Canonicalize: use canonical subtype query (e.g. "mexican restaurants") not
    #      "more mexican restaurants" — better cache alignment and provider diversity.
    #   2. Pool check: if in-memory result pool has unused verified cards, return them
    #      immediately without a provider call (target < 2 s backend time).
    #   3. Provider search: if pool miss, call service.search() with canonical query +
    #      prior_identity_keys for early dedup (skips reason_generation for duplicates).
    #   4. Bounded refill: if < 2 unique cards remain, try up to 2 canonical variant
    #      queries ("best <subtype>", "popular <subtype>") to surface new candidates.
    #   5. Store: save final unique cards in pool keyed by (trip_id, canonical_query)
    #      for the next more-options call.
    if (
        _flag_on
        and turn_mode == "new_search"
        and ctx is not None
        and is_more_options_continuation(payload.user_query, ctx)
    ):
        _query_hint = ctx.prior_place_query_hint or derive_category_hint(ctx.prior_card_pool)
        if _query_hint:
            _t0_cont = time.perf_counter()
            # Canonical query: plain subtype phrase without "more " prefix.
            # This aligns with the initial search cache key, reducing redundant provider calls.
            _canonical_query = _query_hint

            _prior_keys = _build_prior_identity_keys_set(ctx.prior_card_pool)

            logger.info(
                "concierge.context.more_options_continuation trip_id=%s "
                "turn_mode=new_search canonical_query=%r original_user_query=%r "
                "prior_category_hint=%s source_message_id=%s card_pool_size=%d "
                "prior_identity_key_count=%d",
                payload.trip_id,
                _canonical_query,
                payload.user_query,
                _query_hint,
                ctx.source_message_id,
                ctx.card_pool_size,
                len(_prior_keys),
            )

            # ── Step 2: pool check ────────────────────────────────────────────
            _t_pool_start = time.perf_counter()
            _pool_entry = _GLOBAL_CONTINUATION_POOL.pop(str(payload.trip_id), _canonical_query)
            _pool_ms = int((time.perf_counter() - _t_pool_start) * 1000)
            _pool_hit = _pool_entry is not None
            _pool_size_before = _pool_entry[1] if _pool_entry is not None else 0

            if _pool_hit and _pool_entry is not None:
                _pool_unique, _pool_unique_count = _filter_pool_buckets_by_identity(
                    _pool_entry[0], _prior_keys
                )
                logger.info(
                    "concierge.more_options_continuation.pool trip_id=%s "
                    "pool_hit=true pool_size_before=%d pool_unique_count=%d pool_ms=%d",
                    payload.trip_id, _pool_size_before, _pool_unique_count, _pool_ms,
                )
                if _pool_unique_count >= 1:
                    try:
                        _typed_pool = _build_place_response_from_pool(_pool_unique, _canonical_query)
                        _decision_pool = RouteDecision(
                            response_type="place_recommendations",
                            stage1_prior={"place_recommendations": 1.0, "trip_advice": 0.0, "unsupported": 0.0},
                            stage2_confidence=1.0,
                            code="more_options_continuation",
                        )
                        logger.info(
                            "concierge.more_options_continuation.pool_fast_path trip_id=%s "
                            "unique_count=%d total_ms=%d",
                            payload.trip_id,
                            _pool_unique_count,
                            int((time.perf_counter() - _t0_cont) * 1000),
                        )
                        try:
                            validated = _typed_response_adapter.validate_python(_typed_pool)
                            return validated, _decision_pool
                        except ValidationError:
                            logger.warning(
                                "concierge.more_options_continuation.pool_validation_failed "
                                "trip_id=%s falling_through_to_provider=true",
                                payload.trip_id,
                            )
                    except Exception:
                        logger.exception(
                            "concierge.more_options_continuation.pool_build_failed "
                            "trip_id=%s falling_through_to_provider=true",
                            payload.trip_id,
                        )
            else:
                logger.info(
                    "concierge.more_options_continuation.pool trip_id=%s "
                    "pool_hit=false pool_ms=%d",
                    payload.trip_id, _pool_ms,
                )

            # ── Step 3: provider search (canonical query + early dedup) ───────
            try:
                _t_provider_start = time.perf_counter()
                legacy = service.search(
                    payload.trip_id,
                    _canonical_query,
                    user_id,
                    payload.client_message_id,
                    prior_identity_keys=_prior_keys,
                )
                _provider_ms = int((time.perf_counter() - _t_provider_start) * 1000)

                typed_payload = PlaceRecommendationsResponse(**legacy.model_dump())

                # Post-search dedup (catches any duplicates not covered by early dedup)
                _t_dedup_start = time.perf_counter()
                typed_payload, dedup_stats = _exclude_prior_verified_cards(typed_payload, ctx.prior_card_pool)
                _dedup_ms = int((time.perf_counter() - _t_dedup_start) * 1000)
                _final_count = dedup_stats["final_unique_count"]

                logger.info(
                    "concierge.more_options_continuation.dedup trip_id=%s "
                    "prior_exclusion_count=%d raw_candidate_count=%d "
                    "excluded_prior_duplicate_count=%d final_unique_count=%d "
                    "provider_ms=%d dedup_ms=%d",
                    payload.trip_id,
                    dedup_stats["prior_exclusion_count"],
                    dedup_stats["raw_candidate_count"],
                    dedup_stats["excluded_prior_duplicate_count"],
                    _final_count,
                    _provider_ms,
                    _dedup_ms,
                )

                # ── Step 4: bounded refill when < 2 unique cards ──────────────
                if _final_count < 2:
                    _combined_prior = _prior_keys | _response_identity_keys(typed_payload)
                    _refill_variants = _refill_variant_queries(_canonical_query)
                    _refill_added = 0
                    for _variant in _refill_variants:
                        if _final_count >= 2:
                            break
                        try:
                            _t_refill = time.perf_counter()
                            _refill_legacy = service.search(
                                payload.trip_id,
                                _variant,
                                user_id,
                                None,
                                prior_identity_keys=_combined_prior,
                            )
                            _refill_resp = PlaceRecommendationsResponse(**_refill_legacy.model_dump())
                            _refill_resp, _refill_dedup = _exclude_prior_verified_cards(
                                _refill_resp,
                                ctx.prior_card_pool,
                            )
                            # Also exclude cards already in current typed_payload
                            _current_keys = _response_identity_keys(typed_payload)
                            _refill_resp.restaurants = [
                                c for c in _refill_resp.restaurants
                                if _card_identity_keys(c).isdisjoint(_current_keys)
                            ]
                            _refill_resp.attractions = [
                                c for c in _refill_resp.attractions
                                if _card_identity_keys(c).isdisjoint(_current_keys)
                            ]
                            _refill_resp.hotels = [
                                c for c in _refill_resp.hotels
                                if _card_identity_keys(c).isdisjoint(_current_keys)
                            ]
                            _batch_added = (
                                len(_refill_resp.restaurants)
                                + len(_refill_resp.attractions)
                                + len(_refill_resp.hotels)
                            )
                            if _batch_added > 0:
                                typed_payload.restaurants += _refill_resp.restaurants
                                typed_payload.attractions += _refill_resp.attractions
                                typed_payload.hotels += _refill_resp.hotels
                                _refill_added += _batch_added
                                _final_count += _batch_added
                                _combined_prior = _combined_prior | _response_identity_keys(typed_payload)
                            logger.info(
                                "concierge.more_options_continuation.refill trip_id=%s "
                                "variant=%r batch_added=%d total_unique=%d refill_ms=%d",
                                payload.trip_id,
                                _variant,
                                _batch_added,
                                _final_count,
                                int((time.perf_counter() - _t_refill) * 1000),
                            )
                        except Exception:
                            logger.warning(
                                "concierge.more_options_continuation.refill_failed "
                                "trip_id=%s variant=%r",
                                payload.trip_id,
                                _variant,
                                exc_info=True,
                            )

                # ── Step 5: store results in pool for next more-options call ──
                _pool_cards = {
                    "restaurants": [c.model_dump() for c in typed_payload.restaurants],
                    "attractions": [c.model_dump() for c in typed_payload.attractions],
                    "hotels": [c.model_dump() for c in typed_payload.hotels],
                }
                if _final_count > 0:
                    _GLOBAL_CONTINUATION_POOL.store(
                        str(payload.trip_id), _canonical_query, _pool_cards
                    )

                logger.info(
                    "concierge.more_options_continuation.complete trip_id=%s "
                    "final_unique_count=%d total_ms=%d provider_cache_status=%s",
                    payload.trip_id,
                    _final_count,
                    int((time.perf_counter() - _t0_cont) * 1000),
                    getattr(legacy, "cached", False),
                )

                decision = RouteDecision(
                    response_type="place_recommendations",
                    stage1_prior={"place_recommendations": 1.0, "trip_advice": 0.0, "unsupported": 0.0},
                    stage2_confidence=1.0,
                    code="more_options_continuation",
                )
                try:
                    validated = _typed_response_adapter.validate_python(typed_payload)
                    return validated, decision
                except ValidationError:
                    logger.warning(
                        "concierge.more_options_continuation.validation_failed trip_id=%s "
                        "falling_through=true",
                        payload.trip_id,
                    )
            except Exception:
                logger.exception(
                    "concierge.more_options_continuation.search_failed trip_id=%s "
                    "falling_through=true",
                    payload.trip_id,
                )
        else:
            logger.info(
                "concierge.more_options_continuation.fall_through trip_id=%s "
                "fall_through_reason=no_prior_category_hint provider_call=true",
                payload.trip_id,
            )

    if not settings.concierge_router_v2:
        _t_ss = time.perf_counter()
        legacy = service.search(payload.trip_id, payload.user_query, user_id, payload.client_message_id)
        _service_search_ms = int((time.perf_counter() - _t_ss) * 1000)
        typed_payload = PlaceRecommendationsResponse(**legacy.model_dump())
        decision = RouteDecision(
            response_type="place_recommendations",
            stage1_prior={"place_recommendations": 1.0, "trip_advice": 0.0, "unsupported": 0.0},
            stage2_confidence=1.0,
            code="router_v2_disabled",
        )
    else:
        _t_rp = time.perf_counter()
        decision = route_prompt(
            payload.user_query,
            confidence_threshold=settings.concierge_router_v2_confidence_threshold,
        )
        _route_prompt_ms = int((time.perf_counter() - _t_rp) * 1000)
        logger.info(
            "concierge.router.stage2 decision=%s confidence=%.4f code=%s",
            decision.response_type,
            decision.stage2_confidence,
            decision.code,
        )

        if decision.response_type == "place_recommendations":
            _t_ss = time.perf_counter()
            legacy = service.search(payload.trip_id, payload.user_query, user_id, payload.client_message_id)
            _service_search_ms = int((time.perf_counter() - _t_ss) * 1000)
            typed_payload = PlaceRecommendationsResponse(**legacy.model_dump())
        elif decision.response_type == "trip_advice":
            if not getattr(settings, "trip_advice_builder_enabled", False):
                typed_payload = UnsupportedResponse(
                    code="trip_advice_disabled",
                    message="Trip advice mode is currently disabled.",
                )
            else:
                advice_payload = build_trip_advice_payload(payload.user_query)
                typed_payload = TripAdviceResponse(
                    response=advice_payload.response,
                    advice_sections=[section.model_dump() for section in advice_payload.advice_sections],
                    citations=[citation.model_dump() for citation in advice_payload.citations],
                    suggestions=advice_payload.suggestions,
                    metadata={
                        **advice_payload.metadata,
                        "router": {
                            "stage1_prior": decision.stage1_prior,
                            "stage2_confidence": decision.stage2_confidence,
                        },
                    },
                )
        else:
            typed_payload = UnsupportedResponse(
                code=decision.code or "unsupported_prompt",
                message="I couldn't confidently route this request yet. Please rephrase with more travel detail.",
            )

    _t_tv = time.perf_counter()
    try:
        validated = _typed_response_adapter.validate_python(typed_payload)
    except ValidationError as exc:
        logger.exception("concierge.typed_response_validation_failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Concierge typed response validation failed",
        ) from exc
    _typed_val_ms = int((time.perf_counter() - _t_tv) * 1000)
    _total_btcr_ms = int((time.perf_counter() - _t_btcr_start) * 1000)
    logger.info(
        "concierge.search.build_typed_timing trip_id=%s context_window_ms=%d "
        "route_prompt_ms=%d service_search_ms=%d typed_validation_ms=%d "
        "total_build_typed_ms=%d",
        payload.trip_id,
        _ctx_ms,
        _route_prompt_ms,
        _service_search_ms,
        _typed_val_ms,
        _total_btcr_ms,
    )
    return validated, decision


@router.post("/concierge", response_model=ConciergeResponse)
def concierge(payload: ConciergeRequest, db: DB, user_id: CurrentUserID) -> ConciergeResponse:
    """Generate contextual travel recommendations for a trip using Claude."""
    settings = get_settings()
    guardrails.enforce(
        endpoint_key="ai.concierge",
        user_id=user_id,
        rule=GuardrailRule(
            requests=settings.guardrail_ai_concierge_requests,
            window_seconds=settings.guardrail_ai_concierge_window_seconds,
            dedupe_seconds=settings.guardrail_ai_concierge_dedupe_seconds,
        ),
        dedupe_payload={"trip_id": payload.trip_id, "query": payload.user_query.strip().lower(), "day": payload.day_number},
    )
    return ConciergeService(db).answer(payload.trip_id, payload.user_query, user_id, payload.day_number)


def _persist_request_log_task(
    *,
    db: Any,
    user_id: UUID,
    request_id: UUID,
    prompt: str,
    decision: RouteDecision,
    response: Any,
    latency_ms: int,
) -> None:
    """Background task wrapper — persistence failures must never propagate."""
    try:
        persist_concierge_request_log(
            db=db,
            user_id=user_id,
            prompt=prompt,
            decision=decision,
            response=response,
            latency_ms=latency_ms,
            request_id=request_id,
        )
    except Exception as exc:
        logger.warning(
            "concierge.request_log.background_task_failed request_id=%s error=%s",
            request_id,
            exc,
        )


@router.post("/concierge/search", response_model=ConciergeTypedResponse)
def concierge_search(
    payload: ConciergeSearchRequest,
    db: DB,
    user_id: CurrentUserID,
    background_tasks: BackgroundTasks,
) -> ConciergeTypedResponse:
    """Retrieval-first concierge with typed response routing contract."""
    settings = get_settings()
    guardrails.enforce(
        endpoint_key="ai.concierge_search",
        user_id=user_id,
        rule=GuardrailRule(
            requests=settings.guardrail_ai_concierge_requests,
            window_seconds=settings.guardrail_ai_concierge_window_seconds,
            dedupe_seconds=settings.guardrail_ai_concierge_dedupe_seconds,
        ),
        dedupe_payload={"trip_id": payload.trip_id, "query": payload.user_query.strip().lower(), "client_message_id": payload.client_message_id},
    )
    # Generate request_id upfront so both the synchronous log event and the
    # background DB persistence share the same identifier.
    request_id = uuid4()
    service = ConciergeService(db)

    _t_route_start = time.perf_counter()
    response, decision = build_typed_concierge_response(service, payload, user_id)
    _build_typed_ms = int((time.perf_counter() - _t_route_start) * 1000)

    llm_usage = getattr(response, "metadata", {}).get("llm_usage", {}) if hasattr(response, "metadata") else {}
    tokens_in = llm_usage.get("tokens_in") if isinstance(llm_usage, dict) else None
    tokens_out = llm_usage.get("tokens_out") if isinstance(llm_usage, dict) else None
    sources_used = response.sources if hasattr(response, "sources") else [c.url for c in getattr(response, "citations", [])]

    # Synchronous: cheap structured app log — always emitted before response.
    _t_log_event = time.perf_counter()
    request_log_event(
        request_id=request_id,
        prompt=payload.user_query,
        decision=decision,
        response=response,
        latency_ms=_build_typed_ms,
        sources_used=sources_used,
        llm_tokens_in=tokens_in,
        llm_tokens_out=tokens_out,
    )
    _log_event_ms = int((time.perf_counter() - _t_log_event) * 1000)

    # Async: DB persistence is best-effort and must not delay the response.
    _t_sched = time.perf_counter()
    background_tasks.add_task(
        _persist_request_log_task,
        db=db,
        user_id=user_id,
        request_id=request_id,
        prompt=payload.user_query,
        decision=decision,
        response=response,
        latency_ms=_build_typed_ms,
    )
    _persist_sched_ms = int((time.perf_counter() - _t_sched) * 1000)

    _route_total_ms = int((time.perf_counter() - _t_route_start) * 1000)
    logger.info(
        "concierge.search.route_timing request_id=%s trip_id=%s "
        "build_typed_concierge_response_ms=%d request_log_event_ms=%d "
        "persist_scheduled_ms=%d route_total_before_return_ms=%d",
        request_id,
        payload.trip_id,
        _build_typed_ms,
        _log_event_ms,
        _persist_sched_ms,
        _route_total_ms,
    )

    return response


@router.post("/concierge/debug-trace")
def concierge_debug_trace(payload: ConciergeDebugRequest, db: DB, user_id: CurrentUserID) -> dict:
    """[DEV-ONLY] Run the live-research pipeline for a free-form query and return a full debug trace.

    Does NOT require a trip_id — use location directly. Safe: read-only, no side effects.
    """
    from app.services.live_research import LiveResearchService

    service = ConciergeService(db)
    intent = service._detect_intent(payload.user_query)

    debug_out: dict = {}
    live_svc = LiveResearchService(max_results=payload.limit)
    result = live_svc.fetch(
        intent=intent,
        destination=payload.location,
        user_query=payload.user_query,
        _debug_out=debug_out,
    )

    all_addable = result.restaurants + result.attractions + result.hotels

    why_pick_dist: dict = {}
    for card in all_addable:
        gv = getattr(card, "google_verification", None)
        types: list = getattr(gv, "types", []) if gv else []
        label = types[0] if types else "unknown"
        why_pick_dist[label] = why_pick_dist.get(label, 0) + 1

    def _card_dump(c: object) -> dict:
        try:
            return c.model_dump()  # type: ignore[attr-defined]
        except Exception:
            return {}

    return {
        "summary": {
            "raw_provider_candidate_count": debug_out.get("raw_provider_candidate_count", debug_out.get("raw_candidate_count", 0)),
            "extracted_candidate_count": debug_out.get("extracted_candidate_count", debug_out.get("raw_candidate_count", 0)),
            "google_direct_candidate_count": debug_out.get("google_direct_candidate_count", 0),
            "merged_candidate_count": debug_out.get("merged_candidate_count", debug_out.get("deduped_candidate_count", 0)),
            "deduped_candidate_count": debug_out.get("deduped_candidate_count", 0),
            "raw_candidate_count": debug_out.get("raw_candidate_count", 0),
            "google_matched_count": debug_out.get("google_matched_count", 0),
            "accepted_operational_count": debug_out.get("google_matched_count", 0),
            "rejected_count_by_reason": debug_out.get("rejection_reasons", {}),
            "final_addable_count": len(all_addable),
            "research_only_count": len(result.research_sources),
            "why_pick_source_distribution": why_pick_dist,
        },
        "parsed_intent": intent,
        "search_queries": debug_out.get("search_queries", []),
        "raw_candidates": debug_out.get("raw_candidates", []),
        "deduped_candidates": debug_out.get("deduped_candidates", []),
        "google_verification": debug_out.get("google_verification", {}),
        "rejection_reasons": debug_out.get("rejection_details", []),
        "final_addable_cards": [_card_dump(c) for c in all_addable],
        "final_display_payload": {
            "restaurants": [] if intent == "nightlife" else [_card_dump(c) for c in result.restaurants],
            "bars": [_card_dump(c) for c in result.restaurants] if intent == "nightlife" else [],
            "attractions": [_card_dump(c) for c in result.attractions],
            "hotels": [_card_dump(c) for c in result.hotels],
            "research_sources": [_card_dump(c) for c in result.research_sources],
            "source_status": result.source_status,
            "provider_name": result.provider_name,
        },
        "cache_status": {
            "hit": debug_out.get("cache_hit", False),
            "key": debug_out.get("cache_key"),
        },
    }


@router.get("/concierge/{trip_id}/messages", response_model=List[ConciergeMessage])
def concierge_messages(trip_id: UUID, db: DB, user_id: CurrentUserID) -> List[ConciergeMessage]:
    """Load persisted AI concierge messages for a trip, ordered by created_at."""
    return ConciergeService(db).list_messages(trip_id, user_id)


@router.delete("/concierge/cache", response_model=ConciergeCacheClearResponse)
def clear_concierge_cache(payload: ConciergeCacheClearRequest, db: DB, user_id: CurrentUserID) -> ConciergeCacheClearResponse:
    """Clear concierge cache for the authenticated user's trip context."""
    ConciergeService(db).clear_cache(payload.trip_id, user_id, payload.destination)
    return ConciergeCacheClearResponse(cleared=True)


# ─── Smart Day Timeline AI Planning ──────────────────────────────────────────

class _TimelineItem(BaseModel):
    id: str
    title: str
    item_type: str
    details: Dict[str, Any] = {}


class _TimelineSuggestion(BaseModel):
    item_id: str
    day_part: Literal["morning", "afternoon", "evening", "unscheduled"]
    time_label: Optional[str] = None


class _TimelineSuggestRequest(BaseModel):
    items: List[_TimelineItem]


class _TimelineSuggestResponse(BaseModel):
    suggestions: List[_TimelineSuggestion]
    provider: Literal["claude", "deterministic"]


_MORNING_RE = re.compile(
    r"breakfast|brunch|coffee|cafe|caf[eé]|bakery|patisserie|boulangerie|sunrise|morning tour",
    re.IGNORECASE,
)
_EVENING_RE = re.compile(
    r"dinner|supper|cocktail|nightlife|nightclub|\bbar\b|speakeasy|jazz\s+club|wine\s+bar|rooftop\s+bar|night\s+market",
    re.IGNORECASE,
)
_LUNCH_RE = re.compile(r"\blunch\b|midday|noon", re.IGNORECASE)


def _classify_deterministic(item: _TimelineItem) -> _TimelineSuggestion:
    """Rule-based dayPart classifier — always available, no API key needed."""
    # Conservative: flights/hotels stay unscheduled
    if item.item_type in ("flight", "hotel"):
        return _TimelineSuggestion(item_id=item.id, day_part="unscheduled")

    # Preserve explicitly set dayPart from prior manual saves
    explicit = item.details.get("dayPart") or item.details.get("day_part")
    if explicit in ("morning", "afternoon", "evening"):
        tl = item.details.get("timeLabel") or item.details.get("time_label")
        return _TimelineSuggestion(item_id=item.id, day_part=explicit, time_label=tl)  # type: ignore[arg-type]

    text = " ".join(
        filter(
            None,
            [
                item.title,
                item.details.get("category"),
                item.details.get("type"),
                item.details.get("cuisine"),
            ],
        )
    )

    if _MORNING_RE.search(text):
        label: Optional[str] = None
        if re.search(r"breakfast|brunch", text, re.IGNORECASE):
            label = "Breakfast"
        elif re.search(r"coffee|cafe|caf[eé]|bakery", text, re.IGNORECASE):
            label = "Morning coffee"
        return _TimelineSuggestion(item_id=item.id, day_part="morning", time_label=label)

    if _EVENING_RE.search(text):
        if re.search(r"dinner|supper", text, re.IGNORECASE):
            ev_label: Optional[str] = "Dinner"
        elif re.search(r"cocktail|\bbar\b|speakeasy|wine\s+bar", text, re.IGNORECASE):
            ev_label = "Evening drinks"
        else:
            ev_label = "Night out"
        return _TimelineSuggestion(item_id=item.id, day_part="evening", time_label=ev_label)

    if _LUNCH_RE.search(text):
        return _TimelineSuggestion(item_id=item.id, day_part="afternoon", time_label="Lunch")

    if item.item_type == "meal":
        return _TimelineSuggestion(item_id=item.id, day_part="afternoon", time_label="Lunch")

    if item.item_type == "activity":
        return _TimelineSuggestion(item_id=item.id, day_part="morning")

    return _TimelineSuggestion(item_id=item.id, day_part="unscheduled")


def _build_claude_prompt(items: List[_TimelineItem]) -> str:
    lines = []
    for i, item in enumerate(items, 1):
        parts = [f'{i}. id={item.id!r} title={item.title!r} type={item.item_type!r}']
        cat = item.details.get("category") or item.details.get("type")
        cuisine = item.details.get("cuisine")
        if cat:
            parts.append(f"category={cat!r}")
        if cuisine:
            parts.append(f"cuisine={cuisine!r}")
        lines.append(" ".join(parts))

    items_block = "\n".join(lines)
    return f"""You are a travel itinerary assistant. For each item, suggest the best time of day.

Rules:
- breakfast/brunch/coffee/cafe/bakery → morning; add timeLabel "Breakfast" or "Morning coffee" if obvious
- lunch/midday → afternoon; timeLabel "Lunch"
- dinner/supper/cocktail bar/nightlife → evening; timeLabel "Dinner" or "Evening drinks"
- attractions/museums/parks → morning (default) or afternoon if explicitly afternoon
- flights/hotels → unscheduled (always)
- if unsure → unscheduled
- keep timeLabel short and useful; omit if not clearly implied
- do NOT invent exact clock times unless strongly implied

Items:
{items_block}

Respond ONLY with a JSON array — no markdown, no explanation:
[{{"item_id": "<id>", "day_part": "morning|afternoon|evening|unscheduled", "time_label": "<short label or null>"}}]"""


def _parse_claude_suggestions(
    raw: str,
    items: List[_TimelineItem],
) -> List[_TimelineSuggestion]:
    """Parse Claude JSON output; fall back to deterministic for missing/invalid items."""
    item_map = {item.id: item for item in items}
    try:
        data = json.loads(raw.strip())
        if not isinstance(data, list):
            raise ValueError("not a list")
        suggestions: List[_TimelineSuggestion] = []
        covered: set[str] = set()
        for entry in data:
            iid = str(entry.get("item_id", ""))
            dp = str(entry.get("day_part", "unscheduled"))
            tl = entry.get("time_label") or None
            if iid not in item_map:
                continue
            if dp not in ("morning", "afternoon", "evening", "unscheduled"):
                dp = "unscheduled"
            suggestions.append(
                _TimelineSuggestion(item_id=iid, day_part=dp, time_label=tl)  # type: ignore[arg-type]
            )
            covered.add(iid)
        # Fill in any items Claude missed with deterministic fallback
        for item in items:
            if item.id not in covered:
                suggestions.append(_classify_deterministic(item))
        return suggestions
    except Exception:
        return [_classify_deterministic(item) for item in items]


@router.post("/timeline/suggest", response_model=_TimelineSuggestResponse)
def suggest_timeline(
    payload: _TimelineSuggestRequest,
    user_id: CurrentUserID,
) -> _TimelineSuggestResponse:
    """
    Suggest dayPart / timeLabel metadata for itinerary items already assigned
    to a day. Uses Claude if ANTHROPIC_API_KEY is configured; otherwise falls
    back to deterministic rule-based classification.

    No Supabase writes — callers persist suggestions via the existing
    PATCH /itinerary/items/{id} endpoint.
    """
    if not payload.items:
        return _TimelineSuggestResponse(suggestions=[], provider="deterministic")

    settings = get_settings()
    guardrails.enforce(
        endpoint_key="ai.timeline_suggest",
        user_id=user_id,
        rule=GuardrailRule(
            requests=settings.guardrail_ai_timeline_requests,
            window_seconds=settings.guardrail_ai_timeline_window_seconds,
            dedupe_seconds=settings.guardrail_ai_timeline_dedupe_seconds,
        ),
        dedupe_payload={"items": [{"id": i.id, "title": i.title, "type": i.item_type} for i in payload.items]},
    )
    api_key = settings.anthropic_api_key

    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            prompt = _build_claude_prompt(payload.items)
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text if message.content else "[]"
            suggestions = _parse_claude_suggestions(raw, payload.items)
            return _TimelineSuggestResponse(suggestions=suggestions, provider="claude")
        except Exception as exc:
            logger.warning("timeline/suggest: Claude call failed (%s), using deterministic fallback", exc)

    suggestions = [_classify_deterministic(item) for item in payload.items]
    return _TimelineSuggestResponse(suggestions=suggestions, provider="deterministic")
