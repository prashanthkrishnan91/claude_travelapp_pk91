"""Route reorder-proposal router — AI Route Planning v1.

POST /itinerary/{trip_id}/days/{day_id}/route-reorder-proposal/generate
POST /itinerary/{trip_id}/days/{day_id}/route-reorder-proposal/apply

Both flag-gated (default off), independently. ``generate`` is read-only —
it never writes, only reasons about the day's already-persisted items and
route data and returns a suggested order. ``apply`` writes only on explicit
confirmation, only the exact order the caller supplied, only after
ownership + item-set + stale-order validation. No auto-reorder anywhere.
Governed by ``docs/ai/AI_ROUTE_PLANNING_V1_ADR.md``.
"""
from uuid import UUID

from fastapi import APIRouter

from app.core.deps import DB, CurrentUserID
from app.models.route_reorder_proposal import (
    RouteReorderApplyRequest,
    RouteReorderApplyResponse,
    RouteReorderProposalGenerateRequest,
    RouteReorderProposalGenerateResponse,
)
from app.services.route_reorder_proposal import apply_route_reorder_proposal
from app.services.route_reorder_proposal_generate import generate_route_reorder_proposal

router = APIRouter(prefix="/itinerary", tags=["route-reorder-proposal"])


@router.post(
    "/{trip_id}/days/{day_id}/route-reorder-proposal/generate",
    response_model=RouteReorderProposalGenerateResponse,
)
def route_reorder_proposal_generate(
    trip_id: UUID,
    day_id: UUID,
    payload: RouteReorderProposalGenerateRequest,
    user_id: CurrentUserID,
    db: DB,
) -> RouteReorderProposalGenerateResponse:
    """Generate a suggested stop order for one day. Read-only — never writes.

    Only reachable from an explicit user action (Plan My Day). The caller
    supplies the day's current order as it knows it so a stale request is
    rejected before any route-data or LLM work happens.
    """
    return generate_route_reorder_proposal(trip_id, day_id, user_id, payload, db)


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
