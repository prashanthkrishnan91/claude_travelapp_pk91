"""Google Routes adapter — Route Planning v1 PR 3.

Calls the computeRoutes endpoint ONLY (v2 REST API). Hard safety constraints:
- Only calls routes.googleapis.com/directions/v2:computeRoutes.
- No matrix calls; no route optimization; no geocoding.
- No traffic-aware routing (uses TRAFFIC_UNAWARE in v1).
- No polylines, no tolls, no transit, no two-wheel, no alternatives.
- Tight field mask: per-leg duration and distance only.
- Single HTTP call per invocation; no retry loops.
- MAX_ROUTABLE_STOPS enforced at adapter boundary.
- Fail-closed: any missing or invalid leg field returns error, never silently uses 0.

Governed by Route Planning v1 Contract ADR (PR #509).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import httpx

from app.models.route_estimate import RouteableStop

_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
_TIMEOUT_SECONDS = 8.0

# Tight field mask: per-leg duration and distance only.
# No polylines, no headers, no route-level totals.
_FIELD_MASK = "routes.legs.duration,routes.legs.distanceMeters"

# Hard cap: max stops accepted by this adapter in v1.
# Caller (service layer) must enforce this and raise 422 before calling the adapter.
MAX_ROUTABLE_STOPS = 10


@dataclass
class LegEstimate:
    from_item_id: str
    to_item_id: str
    distance_meters: int
    duration_seconds: int
    order_index: int
    provider: str = "google_routes"
    source: str = "google_routes"
    estimated: bool = True


@dataclass
class AdapterResult:
    estimates: List[LegEstimate] = field(default_factory=list)
    provider_call_count: int = 0
    error_reason: Optional[str] = None


def _build_waypoint(stop: RouteableStop) -> dict:
    return {
        "location": {
            "latLng": {
                "latitude": stop.lat,
                "longitude": stop.lng,
            }
        }
    }


def _parse_duration_seconds(duration_str: str) -> Optional[int]:
    """Parse Google Duration string '300s' → 300. Returns None on any parse failure."""
    try:
        s = duration_str.strip()
        if s.endswith("s"):
            return int(s[:-1])
        return int(s)
    except (ValueError, AttributeError):
        return None


def call_compute_routes(
    valid_stops: List[RouteableStop],
    api_key: str,
    *,
    http_client: Optional[httpx.Client] = None,
) -> AdapterResult:
    """Call Google Routes ComputeRoutes for an ordered list of stops.

    Caller contract:
    - 2 ≤ len(valid_stops) ≤ MAX_ROUTABLE_STOPS (service layer enforces).
    - api_key is non-empty (service layer enforces).
    - Stops are in caller-supplied order; never reordered here.

    Returns AdapterResult with provider_call_count=1 on any HTTP attempt
    (success or error), 0 if the call is skipped due to invalid input.
    Fail-closed: any missing or invalid leg field returns an error result,
    never silently substituting 0 for missing provider data.
    """
    # Defensive boundary: service layer must enforce these, but reject here too.
    if len(valid_stops) < 2 or len(valid_stops) > MAX_ROUTABLE_STOPS:
        return AdapterResult(provider_call_count=0, error_reason="invalid_stop_count")

    origin = valid_stops[0]
    destination = valid_stops[-1]
    intermediates = valid_stops[1:-1]

    body: dict = {
        "origin": _build_waypoint(origin),
        "destination": _build_waypoint(destination),
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_UNAWARE",
        "computeAlternativeRoutes": False,
    }
    if intermediates:
        body["intermediates"] = [_build_waypoint(s) for s in intermediates]

    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": _FIELD_MASK,
        "Content-Type": "application/json",
    }

    should_close = http_client is None
    client = http_client or httpx.Client(timeout=_TIMEOUT_SECONDS)

    try:
        response = client.post(_ROUTES_URL, json=body, headers=headers)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return AdapterResult(
            provider_call_count=1,
            error_reason=f"http_error_{exc.response.status_code}",
        )
    except httpx.TimeoutException:
        return AdapterResult(provider_call_count=1, error_reason="timeout")
    except Exception as exc:  # noqa: BLE001
        return AdapterResult(provider_call_count=1, error_reason=f"provider_error: {type(exc).__name__}")
    finally:
        if should_close:
            client.close()

    data = response.json()
    routes = data.get("routes", [])
    if not routes:
        return AdapterResult(provider_call_count=1, error_reason="no_routes_returned")

    legs = routes[0].get("legs", [])
    if not legs:
        return AdapterResult(provider_call_count=1, error_reason="no_legs_returned")

    expected_leg_count = len(valid_stops) - 1
    if len(legs) != expected_leg_count:
        return AdapterResult(provider_call_count=1, error_reason="leg_count_mismatch")

    estimates: List[LegEstimate] = []
    for i, leg in enumerate(legs):
        raw_duration = leg.get("duration")
        if raw_duration is None:
            return AdapterResult(provider_call_count=1, error_reason="missing_leg_duration")
        duration_seconds = _parse_duration_seconds(raw_duration)
        if duration_seconds is None:
            return AdapterResult(provider_call_count=1, error_reason="invalid_leg_duration")

        raw_distance = leg.get("distanceMeters")
        if raw_distance is None:
            return AdapterResult(provider_call_count=1, error_reason="missing_leg_distance")
        try:
            distance_meters = int(raw_distance)
        except (ValueError, TypeError):
            return AdapterResult(provider_call_count=1, error_reason="invalid_leg_distance")

        estimates.append(
            LegEstimate(
                from_item_id=valid_stops[i].item_id,
                to_item_id=valid_stops[i + 1].item_id,
                distance_meters=distance_meters,
                duration_seconds=duration_seconds,
                order_index=i,
            )
        )

    return AdapterResult(estimates=estimates, provider_call_count=1)
