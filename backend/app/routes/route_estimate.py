"""Route estimate router — Route Planning v1 PR 3.

POST /itinerary/{trip_id}/days/{day_id}/route-estimate
Flag-gated; ownership-verified; single ComputeRoutes call only.
No frontend/UI. No automatic calls. No geocoding. No reordering.
"""
from uuid import UUID

from fastapi import APIRouter

from app.core.deps import DB, CurrentUserID
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
    db: DB,
) -> RouteEstimateResponse:
    """Flag-gated route-estimate endpoint.

    Ownership is verified before any provider call.
    Stop order is preserved; never reordered.
    Accepted stop types: activity and meal only.
    """
    return compute_route_estimate(payload, trip_id, day_id, user_id=user_id, db=db)
