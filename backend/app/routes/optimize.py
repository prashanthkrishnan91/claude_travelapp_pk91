"""Trip optimization route — POST /optimize/trip."""

from fastapi import APIRouter

from app.models.optimization import TripOptimizationRequest, TripOptimizationResponse
from app.services.optimization import TripOptimizationEngine

router = APIRouter(prefix="/optimize", tags=["optimize"])


@router.post("/trip", response_model=TripOptimizationResponse)
def optimize_trip(req: TripOptimizationRequest) -> TripOptimizationResponse:
    """Score every flight × hotel combination and return the top 3 ranked options."""
    return TripOptimizationEngine().optimize(req)
