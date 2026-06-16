"""Route estimate router — Route Planning v1 PR 2.

Endpoint shell: POST /itinerary/{trip_id}/days/{day_id}/route-estimate
Flag-gated; fail-closed; no live provider calls; no adapter; no frontend/UI.
"""
from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CurrentUserID
from app.models.route_estimate import RouteEstimateRequest, RouteEstimateResponse
from app.services.route_estimate import compute_route_estimate

router = APIRouter(prefix="/itinerary", tags=["route-estimate"])


@router.post(
    "/{trip_id}/days/{day_id}/route-estimate",
    response_model=RouteEstimateResponse,
)
def route_estimate(
    trip_id: UUID,
    day_id: UUID,
    payload: RouteEstimateRequest,
    user_id: CurrentUserID,
) -> RouteEstimateResponse:
    """Flag-gated route-estimate endpoint shell.

    Returns a fail-closed response (disabled or not_configured).
    No live provider calls are made in this implementation.
    Accepted stop types: activity and meal only.
    Stop order is preserved; never reordered.
    """
    return compute_route_estimate(payload, trip_id, day_id)
