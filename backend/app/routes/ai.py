"""AI concierge endpoint — contextual travel recommendations powered by Claude."""

import logging

from fastapi import APIRouter

from app.core.deps import DB, CurrentUserID
from app.models.concierge import ConciergeRequest, ConciergeResponse
from app.services.concierge import ConciergeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/concierge", response_model=ConciergeResponse)
def concierge(payload: ConciergeRequest, db: DB, user_id: CurrentUserID) -> ConciergeResponse:
    """Generate contextual travel recommendations for a trip using Claude."""
    return ConciergeService(db).answer(payload.trip_id, payload.user_query, user_id)
