"""Route reorder-proposal apply service — AI Route Planning v1 PR C.

Governed by ``docs/ai/AI_ROUTE_PLANNING_V1_ADR.md`` (Section 9, PR C) and
Section 7 (Approval model). Turns an explicit, user-confirmed before/after
preview into a write — never before confirmation, never anything the
preview didn't show.

Hard safety guarantees enforced here:
- No LLM call, no AI-generated suggestion — this module only validates and
  applies an order the caller already supplied and the user already saw.
- No write without explicit confirmation — this function is only reachable
  from the apply endpoint; there is no read path that writes.
- Trip/day ownership is verified before any item is read or written.
- The proposed item set must be exactly the current day's item set: no
  item added, removed, duplicated, or moved across days. Any mismatch
  fails closed (``status="rejected"``) with no write.
- Stale-order detection: the caller's ``current_order`` must match the
  day's actual persisted order at apply time, or the request fails closed
  — the previewed before/after must match what will be written.
- Only the existing ``position`` field is written, via the existing
  ``ItineraryService.update_item`` ownership-checked path. No new table,
  no new column, no parallel data model.
"""
from __future__ import annotations

from typing import Any, List
from uuid import UUID

from fastapi import HTTPException

from app.core.config import get_settings
from app.models.route_reorder_proposal import (
    RouteReorderApplyRequest,
    RouteReorderApplyResponse,
)


def _verify_trip_ownership(db: Any, trip_id: UUID, user_id: UUID) -> None:
    """Mirrors ``route_quality_diagnostic._verify_trip_ownership``."""
    result = (
        db.table("trips")
        .select("id")
        .eq("id", str(trip_id))
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Trip not found")


def _verify_day_ownership(db: Any, trip_id: UUID, day_id: UUID) -> None:
    """Mirrors ``route_quality_diagnostic._verify_day_ownership`` — the
    path's ``trip_id`` must match the day's actual trip, not merely any
    trip the user owns."""
    result = (
        db.table("itinerary_days")
        .select("id")
        .eq("id", str(day_id))
        .eq("trip_id", str(trip_id))
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Day not found")


def _disabled_response(day_id: UUID) -> RouteReorderApplyResponse:
    return RouteReorderApplyResponse(
        status="disabled",
        reason="feature_flag_disabled",
        message="Reorder-proposal apply is not yet available. This feature is coming soon.",
        day_id=str(day_id),
        order=[],
    )


def _rejected_response(day_id: UUID, current_order: List[str], reason: str, message: str) -> RouteReorderApplyResponse:
    return RouteReorderApplyResponse(
        status="rejected",
        reason=reason,
        message=message,
        day_id=str(day_id),
        order=current_order,
    )


def apply_route_reorder_proposal(
    trip_id: UUID,
    day_id: UUID,
    user_id: UUID,
    payload: RouteReorderApplyRequest,
    db: Any,
) -> RouteReorderApplyResponse:
    """Apply an explicit, user-confirmed one-day reorder.

    Validation order: feature flag, ownership (trip, then day belongs to
    that exact trip), item-set equality, stale-order check. Nothing is
    written unless every check passes.
    """
    settings = get_settings()

    if not settings.route_reorder_proposal_v1_enabled:
        return _disabled_response(day_id)

    _verify_trip_ownership(db, trip_id, user_id)
    _verify_day_ownership(db, trip_id, day_id)

    # Imported lazily, only reached once the flag is on and ownership is
    # verified: reuses the existing ownership-checked item read/write path
    # rather than inventing a parallel data model.
    from app.models.itinerary import ItineraryItemUpdate
    from app.services.itinerary import ItineraryService

    itinerary = ItineraryService(db)
    items = itinerary.list_items(day_id, user_id=user_id)
    actual_current_order = [str(item.id) for item in items]
    position_by_id = {str(item.id): (item.position or 0) for item in items}

    if payload.current_order != actual_current_order:
        return _rejected_response(
            day_id,
            actual_current_order,
            reason="stale_current_order",
            message=(
                "This day's order changed since the proposal was previewed. "
                "Nothing was applied — refresh and review the current order "
                "before trying again."
            ),
        )

    actual_set = set(actual_current_order)
    proposed_set = set(payload.proposed_order)
    if (
        len(payload.proposed_order) != len(actual_current_order)
        or len(payload.proposed_order) != len(proposed_set)
        or proposed_set != actual_set
    ):
        return _rejected_response(
            day_id,
            actual_current_order,
            reason="item_set_mismatched",
            message=(
                "The proposed order does not match this day's current stops "
                "exactly. Nothing was applied — a reorder can only change the "
                "order of the stops shown, never add, remove, duplicate, or "
                "move a stop to another day."
            ),
        )

    for index, item_id in enumerate(payload.proposed_order):
        if position_by_id.get(item_id) == index:
            continue
        itinerary.update_item(
            UUID(item_id),
            ItineraryItemUpdate(position=index),
            user_id=user_id,
        )

    return RouteReorderApplyResponse(
        status="applied",
        reason="applied",
        message="This order was applied.",
        day_id=str(day_id),
        order=list(payload.proposed_order),
    )
