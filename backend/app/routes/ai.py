"""AI concierge endpoint — contextual travel recommendations powered by Claude."""

import logging
import time
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import TypeAdapter, ValidationError

from app.concierge.contracts import (
    ConciergeTypedResponse,
    PlaceRecommendationsResponse,
    TripAdviceResponse,
    UnsupportedResponse,
)
from app.concierge.builders.trip_advice import build_trip_advice_payload
from app.concierge.logging import persist_concierge_request_log, request_log_event
from app.concierge.router import RouteDecision, route_prompt
from app.core.config import get_settings
from app.core.deps import DB, CurrentUserID
from app.models.concierge import (
    ConciergeCacheClearRequest,
    ConciergeCacheClearResponse,
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
    return ConciergeService(db).answer(payload.trip_id, payload.user_query, user_id, payload.day_number)


@router.post("/concierge/search", response_model=ConciergeTypedResponse)
def concierge_search(payload: ConciergeSearchRequest, db: DB, user_id: CurrentUserID) -> ConciergeTypedResponse:
    """Retrieval-first concierge with typed response routing contract."""
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


@router.get("/concierge/{trip_id}/messages", response_model=List[ConciergeMessage])
def concierge_messages(trip_id: UUID, db: DB, user_id: CurrentUserID) -> List[ConciergeMessage]:
    """Load persisted AI concierge messages for a trip, ordered by created_at."""
    return ConciergeService(db).list_messages(trip_id, user_id)


@router.delete("/concierge/cache", response_model=ConciergeCacheClearResponse)
def clear_concierge_cache(payload: ConciergeCacheClearRequest, db: DB, user_id: CurrentUserID) -> ConciergeCacheClearResponse:
    """Clear concierge cache for the authenticated user's trip context."""
    ConciergeService(db).clear_cache(payload.trip_id, user_id, payload.destination)
    return ConciergeCacheClearResponse(cleared=True)
