"""Route reorder-proposal apply router — AI Route Planning v1 PR C.

POST /itinerary/{trip_id}/days/{day_id}/route-reorder-proposal/apply

Flag-gated (default off). Writes only on explicit confirmation, only the
exact order the caller supplied, only after ownership + item-set +
stale-order validation. No LLM call, no AI-generated suggestion, no
auto-reorder. Governed by ``docs/ai/AI_ROUTE_PLANNING_V1_ADR.md``
(Section 9, PR C).
"""
from uuid import UUID

from fastapi import APIRouter

from app.core.deps import DB, CurrentUserID
from app.models.route_reorder_proposal import (
    RouteReorderApplyRequest,
    RouteReorderApplyResponse,
)
from app.services.route_reorder_proposal import apply_route_reorder_proposal

router = APIRouter(prefix="/itinerary", tags=["route-reorder-proposal"])


@router.post(
    "/{trip_id}/days/{day_id}/route-reorder-proposal/apply",
    response_model=RouteReorderApplyResponse,
)
def route_reorder_proposal_apply(
    trip_id: UUID,
    day_id: UUID,
    payload: RouteReorderApplyRequest,
    user_id: CurrentUserID,
    db: DB,
) -> RouteReorderApplyResponse:
    """Apply an explicit, user-confirmed one-day reorder.

    The caller must supply both the previewed ``current_order`` and
    ``proposed_order``; the server verifies ownership, exact item-set
    equality, and that the current order has not gone stale before writing
    anything. Nothing changes unless every check passes.
    """
    return apply_route_reorder_proposal(trip_id, day_id, user_id, payload, db)
