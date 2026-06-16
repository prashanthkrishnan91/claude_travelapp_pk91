"""Route estimate service — Route Planning v1 PR 2.

Fail-closed shell: returns 'disabled' or 'not_configured'.
No live provider calls. No adapter. No fabricated travel times. No route computation.
Governed by Route Planning v1 Contract ADR (PR #509).
"""
from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import HTTPException

from app.core.config import get_settings
from app.models.route_estimate import (
    ACCEPTED_ITEM_TYPES,
    ExcludedStop,
    RouteableStop,
    RouteEstimateRequest,
    RouteEstimateResponse,
)
from app.services.provider_registry import get_provider, is_provider_active


def compute_route_estimate(
    request: RouteEstimateRequest,
    trip_id: UUID,
    day_id: UUID,
) -> RouteEstimateResponse:
    """Return a fail-closed route estimate.

    Behaviour by flag + provider state:
      flag=False → status='disabled', reason='feature_flag_disabled'
      flag=True, provider inactive → status='not_configured', reason='provider_not_implemented'
    No live provider calls are made in either path.
    Stop order is preserved exactly as supplied; caller-supplied order is final.
    """
    settings = get_settings()

    if not settings.route_estimate_v1_enabled:
        return RouteEstimateResponse(
            status="disabled",
            reason="feature_flag_disabled",
            message="Route estimates are not yet available. This feature is coming soon.",
            provider="google_routes",
            estimates=[],
        )

    # Filter stops — preserve caller order; order is never changed
    valid_stops: List[RouteableStop] = []
    excluded: List[ExcludedStop] = []

    for stop in request.stops:
        if stop.item_type not in ACCEPTED_ITEM_TYPES:
            excluded.append(
                ExcludedStop(
                    item_id=stop.item_id,
                    reason=(
                        f"item_type '{stop.item_type}' is not supported; "
                        "only activity and meal stops are accepted for route estimates"
                    ),
                )
            )
        else:
            valid_stops.append(stop)

    if len(valid_stops) < 2:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Route estimate requires at least 2 valid activity or meal stops. "
                f"Found {len(valid_stops)} after excluding unsupported item types "
                f"(flights, hotels, and notes are not routable)."
            ),
        )

    # Consult provider registry — confirm google_routes is inactive; never call it
    provider_entry = get_provider("google_routes")
    provider_active = provider_entry is not None and is_provider_active("google_routes")

    _metadata = {
        "valid_stop_count": len(valid_stops),
        "excluded_stop_count": len(excluded),
        "excluded_stops": [e.model_dump() for e in excluded],
        "stop_order_preserved": True,
    }

    if not provider_active:
        return RouteEstimateResponse(
            status="not_configured",
            reason="provider_not_implemented",
            message=(
                "Route time estimation is not yet configured. "
                "The Google Routes integration is coming soon."
            ),
            provider="google_routes",
            estimates=[],
            metadata=_metadata,
        )

    # Belt-and-suspenders: if production_allowed were ever set to True before
    # the adapter PR lands, still return fail-closed. Never call the provider here.
    return RouteEstimateResponse(
        status="not_configured",
        reason="provider_not_implemented",
        message="Route time estimation is not yet configured.",
        provider="google_routes",
        estimates=[],
        metadata=_metadata,
    )
