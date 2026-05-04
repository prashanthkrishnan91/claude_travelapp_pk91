"""AI concierge endpoint — contextual travel recommendations powered by Claude."""

import json
import logging
import re
import time
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, TypeAdapter, ValidationError

from app.concierge.contracts import (
    ConciergeTypedResponse,
    PlaceRecommendationsResponse,
    TripAdviceResponse,
    UnsupportedResponse,
)
from app.concierge.builders.trip_advice import build_trip_advice_payload
from app.concierge.context import build_context_window, classify_turn, log_context_turn
from app.concierge.logging import persist_concierge_request_log, request_log_event
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


def build_typed_concierge_response(
    service: ConciergeService,
    payload: ConciergeSearchRequest,
    user_id: UUID,
) -> tuple[ConciergeTypedResponse, RouteDecision]:
    """Build and validate the typed concierge response contract."""
    settings = get_settings()

    # Dark context classification — PR 1 foundation. Classifies and logs only.
    # No behavior change: existing search flow runs unconditionally after this block.
    try:
        ctx = build_context_window(service._db, payload.trip_id)
        turn_mode, rerank_rule = classify_turn(payload.user_query, ctx)
        log_context_turn(
            trip_id=payload.trip_id,
            turn_mode=turn_mode,
            rerank_rule=rerank_rule,
            card_pool_size=ctx.card_pool_size,
            has_prior_cards=ctx.has_prior_cards,
            source_message_id=ctx.source_message_id,
            reset_reason=ctx.reset_reason,
            # In PR 1 we always make a provider call; future PRs will skip it for
            # refine_previous and anchor_new modes.
            provider_call_expected_for_future_mode=turn_mode in ("new_search", "reset"),
        )
    except Exception:
        logger.exception(
            "concierge.context.classify_failed trip_id=%s", payload.trip_id
        )

    if not settings.concierge_router_v2:
        legacy = service.search(payload.trip_id, payload.user_query, user_id, payload.client_message_id)
        typed_payload = PlaceRecommendationsResponse(**legacy.model_dump())
        decision = RouteDecision(
            response_type="place_recommendations",
            stage1_prior={"place_recommendations": 1.0, "trip_advice": 0.0, "unsupported": 0.0},
            stage2_confidence=1.0,
            code="router_v2_disabled",
        )
    else:
        decision = route_prompt(
            payload.user_query,
            confidence_threshold=settings.concierge_router_v2_confidence_threshold,
        )
        logger.info(
            "concierge.router.stage2 decision=%s confidence=%.4f code=%s",
            decision.response_type,
            decision.stage2_confidence,
            decision.code,
        )

        if decision.response_type == "place_recommendations":
            legacy = service.search(payload.trip_id, payload.user_query, user_id, payload.client_message_id)
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

    try:
        validated = _typed_response_adapter.validate_python(typed_payload)
        return validated, decision
    except ValidationError as exc:
        logger.exception("concierge.typed_response_validation_failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Concierge typed response validation failed",
        ) from exc


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


@router.post("/concierge/search", response_model=ConciergeTypedResponse)
def concierge_search(payload: ConciergeSearchRequest, db: DB, user_id: CurrentUserID) -> ConciergeTypedResponse:
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
    service = ConciergeService(db)
    start = time.perf_counter()
    response, decision = build_typed_concierge_response(service, payload, user_id)
    latency_ms = int((time.perf_counter() - start) * 1000)

    request_id = persist_concierge_request_log(
        db=db,
        user_id=user_id,
        prompt=payload.user_query,
        decision=decision,
        response=response,
        latency_ms=latency_ms,
    )

    llm_usage = getattr(response, "metadata", {}).get("llm_usage", {}) if hasattr(response, "metadata") else {}
    tokens_in = llm_usage.get("tokens_in") if isinstance(llm_usage, dict) else None
    tokens_out = llm_usage.get("tokens_out") if isinstance(llm_usage, dict) else None
    sources_used = response.sources if hasattr(response, "sources") else [c.url for c in getattr(response, "citations", [])]

    request_log_event(
        request_id=request_id,
        prompt=payload.user_query,
        decision=decision,
        response=response,
        latency_ms=latency_ms,
        sources_used=sources_used,
        llm_tokens_in=tokens_in,
        llm_tokens_out=tokens_out,
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
