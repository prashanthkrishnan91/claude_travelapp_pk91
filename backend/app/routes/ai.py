"""AI concierge endpoint — contextual travel recommendations powered by Claude."""

import logging
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
from app.concierge.router import route_prompt
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
) -> ConciergeTypedResponse:
    """Build and validate the typed concierge response contract."""
    settings = get_settings()

    if not settings.concierge_router_v2:
        legacy = service.search(payload.trip_id, payload.user_query, user_id, payload.client_message_id)
        typed_payload = PlaceRecommendationsResponse(**legacy.model_dump())
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
            typed_payload = TripAdviceResponse(
                response=(
                    "Trip advice mode is enabled. I can help with points vs cash tradeoffs, "
                    "award strategy, and booking timing."
                ),
                metadata={
                    "router": {
                        "stage1_prior": decision.stage1_prior,
                        "stage2_confidence": decision.stage2_confidence,
                    }
                },
            )
        else:
            typed_payload = UnsupportedResponse(
                code=decision.code or "unsupported_prompt",
                message="I couldn't confidently route this request yet. Please rephrase with more travel detail.",
            )

    try:
        return _typed_response_adapter.validate_python(typed_payload)
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
    return build_typed_concierge_response(service, payload, user_id)


@router.get("/concierge/{trip_id}/messages", response_model=List[ConciergeMessage])
def concierge_messages(trip_id: UUID, db: DB, user_id: CurrentUserID) -> List[ConciergeMessage]:
    """Load persisted AI concierge messages for a trip, ordered by created_at."""
    return ConciergeService(db).list_messages(trip_id, user_id)


@router.delete("/concierge/cache", response_model=ConciergeCacheClearResponse)
def clear_concierge_cache(payload: ConciergeCacheClearRequest, db: DB, user_id: CurrentUserID) -> ConciergeCacheClearResponse:
    """Clear concierge cache for the authenticated user's trip context."""
    ConciergeService(db).clear_cache(payload.trip_id, user_id, payload.destination)
    return ConciergeCacheClearResponse(cleared=True)
