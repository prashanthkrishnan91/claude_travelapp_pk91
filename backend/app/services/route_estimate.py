"""Route estimate service — Route Planning v1 PR 3.

Behaviour by flag + key + ownership + stop count:
  flag=False                           → status='disabled', reason='feature_flag_disabled'
  flag=True + key missing              → status='not_configured', reason='provider_key_missing'
  flag=True + key present + own fail   → HTTP 404 (trip not owned / not found)
  flag=True + key present + <2 stops   → HTTP 422
  flag=True + key present + >10 stops  → HTTP 422
  flag=True + key present + valid      → one ComputeRoutes call; estimates on success
  provider error                       → status='provider_error', estimates=[]

Hard safety guarantees enforced here:
- No automatic calls; only called on explicit manual request.
- Caller must supply lat/lng; no address lookups performed.
- Stop order is final as supplied; never changed.
- No ComputeRouteMatrix; no route optimization.
- Coordinates never sent to Google until ownership is verified.
- Max 10 routable stops (v1 hard cap).
- Adapter call count exposed in metadata.

Governed by Route Planning v1 Contract ADR (PR #509).
"""
from __future__ import annotations

from typing import Any, List, Optional
from uuid import UUID

from fastapi import HTTPException

from app.core.config import get_settings
from app.models.route_estimate import (
    ACCEPTED_ITEM_TYPES,
    ExcludedStop,
    RouteEstimate,
    RouteableStop,
    RouteEstimateRequest,
    RouteEstimateResponse,
)
from app.services.google_routes_adapter import MAX_ROUTABLE_STOPS, call_compute_routes


def _verify_trip_ownership(db: Any, trip_id: UUID, user_id: UUID) -> None:
    """Verify user owns trip_id; raises HTTP 404 if not.

    Mirrors ItineraryService._ensure_trip_owned using the same DB query pattern.
    Caller coordinates must not be sent to any provider before this check passes.
    """
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


def compute_route_estimate(
    request: RouteEstimateRequest,
    trip_id: UUID,
    day_id: UUID,
    user_id: Optional[UUID] = None,
    db: Optional[Any] = None,
) -> RouteEstimateResponse:
    """Return a route estimate, or a fail-closed response if prerequisites are unmet.

    user_id and db are required when the adapter path is reached (flag=True + key present).
    For early-return paths (flag=False, key missing) they are not consulted.
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

    # Filter stops — preserve caller order; order is never changed here
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

    _metadata: dict = {
        "valid_stop_count": len(valid_stops),
        "excluded_stop_count": len(excluded),
        "excluded_stops": [e.model_dump() for e in excluded],
        "stop_order_preserved": True,
        "provider_call_count": 0,
    }

    if len(valid_stops) < 2:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Route estimate requires at least 2 valid activity or meal stops. "
                f"Found {len(valid_stops)} after excluding unsupported item types "
                f"(flights, hotels, and notes are not routable)."
            ),
        )

    if len(valid_stops) > MAX_ROUTABLE_STOPS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Route estimate supports at most {MAX_ROUTABLE_STOPS} stops in v1. "
                f"Received {len(valid_stops)} valid stops after filtering. "
                "Split the route or reduce the number of stops."
            ),
        )

    api_key = settings.google_routes_api_key
    if not api_key:
        return RouteEstimateResponse(
            status="not_configured",
            reason="provider_key_missing",
            message=(
                "Route time estimation is not yet configured. "
                "The Google Routes integration is coming soon."
            ),
            provider="google_routes",
            estimates=[],
            metadata=_metadata,
        )

    # Ownership gate: verify the caller owns this trip before sending coordinates.
    # db and user_id are always provided by the endpoint when the flag is enabled.
    if db is None or user_id is None:
        return RouteEstimateResponse(
            status="not_configured",
            reason="internal_config_error",
            message="Route estimate is not available.",
            provider="google_routes",
            estimates=[],
            metadata=_metadata,
        )
    _verify_trip_ownership(db, trip_id, user_id)

    # Make exactly one ComputeRoutes call; never a matrix or optimization call.
    adapter_result = call_compute_routes(valid_stops, api_key)
    _metadata["provider_call_count"] = adapter_result.provider_call_count

    if adapter_result.error_reason or not adapter_result.estimates:
        _metadata["provider_error"] = adapter_result.error_reason or "no_estimates"
        return RouteEstimateResponse(
            status="provider_error",
            reason="provider_call_failed",
            message="Route estimate is temporarily unavailable. Please try again.",
            provider="google_routes",
            estimates=[],
            metadata=_metadata,
        )

    estimates = [
        RouteEstimate(
            from_item_id=leg.from_item_id,
            to_item_id=leg.to_item_id,
            distance_meters=leg.distance_meters,
            duration_seconds=leg.duration_seconds,
            order_index=leg.order_index,
        ).model_dump()
        for leg in adapter_result.estimates
    ]

    return RouteEstimateResponse(
        status="success",
        reason="route_estimate_success",
        message="Route estimate computed successfully.",
        provider="google_routes",
        estimates=estimates,
        metadata=_metadata,
    )
