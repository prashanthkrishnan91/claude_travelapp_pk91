"""Route-quality diagnostic router — AI Route Planning v1 PR A.

GET /itinerary/{trip_id}/days/{day_id}/route-quality-diagnostic

Read-only, flag-gated (default off). No LLM call, no AI text generation, no
provider call, no itinerary write. Governed by
``docs/ai/AI_ROUTE_PLANNING_V1_ADR.md`` (Section 9, PR A).
"""
from uuid import UUID

from fastapi import APIRouter

from app.core.deps import DB, CurrentUserID
from app.models.route_quality_diagnostic import RouteQualityDiagnosticResponse
from app.services.route_quality_diagnostic import compute_route_quality_diagnostic

router = APIRouter(prefix="/itinerary", tags=["route-quality-diagnostic"])


@router.get(
    "/{trip_id}/days/{day_id}/route-quality-diagnostic",
    response_model=RouteQualityDiagnosticResponse,
)
def route_quality_diagnostic(
    trip_id: UUID,
    day_id: UUID,
    user_id: CurrentUserID,
    db: DB,
) -> RouteQualityDiagnosticResponse:
    """Deterministic route-quality diagnostic for a single day.

    Ownership is verified before any item is read (mirrors the existing
    itinerary read patterns). Read-only: no itinerary write, no provider
    call, no LLM call. The day's current manual order is preserved.
    """
    return compute_route_quality_diagnostic(trip_id, day_id, user_id, db)
