"""AI concierge endpoint — contextual travel recommendations powered by Claude."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter

from app.core.deps import DB, CurrentUserID
from app.models.concierge import (
    ConciergeMessage,
    ConciergeRequest,
    ConciergeResponse,
    ConciergeSearchRequest,
    ConciergeSearchResponse,
)
from app.services.concierge import ConciergeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/concierge", response_model=ConciergeResponse)
def concierge(payload: ConciergeRequest, db: DB, user_id: CurrentUserID) -> ConciergeResponse:
    """Generate contextual travel recommendations for a trip using Claude."""
    return ConciergeService(db).answer(payload.trip_id, payload.user_query, user_id, payload.day_number)


@router.post("/concierge/search", response_model=ConciergeSearchResponse)
def concierge_search(payload: ConciergeSearchRequest, db: DB, user_id: CurrentUserID) -> ConciergeSearchResponse:
    """Retrieval-first concierge: fetches live Michelin/restaurant data before generating a response."""
    return ConciergeService(db).search(payload.trip_id, payload.user_query, user_id)


@router.get("/concierge/{trip_id}/messages", response_model=List[ConciergeMessage])
def concierge_messages(trip_id: UUID, db: DB, user_id: CurrentUserID) -> List[ConciergeMessage]:
    """Load persisted AI concierge messages for a trip, ordered by created_at."""
    return ConciergeService(db).list_messages(trip_id, user_id)
