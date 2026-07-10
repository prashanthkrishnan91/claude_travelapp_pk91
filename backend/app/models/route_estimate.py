"""Route estimate request/response models — Route Planning v1.

Governed by Route Planning v1 Contract ADR (PR #509).
Accepted stop types: activity and meal only. Flights, hotels, and notes are excluded.
No fabricated coordinates, no reordering, no geocoding.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# Only these item types are accepted as routable stops.
ACCEPTED_ITEM_TYPES = frozenset({"activity", "meal"})


class RouteableStop(BaseModel):
    """A single routable stop supplied by the caller.

    Coordinates must be valid ranges; Pydantic rejects out-of-range values.
    Never geocoded — caller must supply pre-validated lat/lng.
    """

    item_id: str
    title: str
    item_type: str
    lat: float = Field(..., ge=-90.0, le=90.0)
    lng: float = Field(..., ge=-180.0, le=180.0)
    place_id: Optional[str] = None
    provider_place_id: Optional[str] = None


class RouteEstimateRequest(BaseModel):
    stops: List[RouteableStop]


class ExcludedStop(BaseModel):
    item_id: str
    reason: str


class RouteEstimate(BaseModel):
    """A single leg estimate from the Google Routes adapter.

    duration_seconds and distance_meters come from the provider only.
    No fabricated or haversine-derived values.
    """

    from_item_id: str
    to_item_id: str
    distance_meters: int
    duration_seconds: int
    provider: str = "google_routes"
    source: str = "google_routes"
    estimated: bool = True
    order_index: int


class RouteEstimateResponse(BaseModel):
    """Route estimate response.

    status values: "disabled" | "not_configured" | "success" | "provider_error"
    estimates is non-empty only when status == "success" and the provider returned data.
    """

    status: Literal["disabled", "not_configured", "success", "provider_error"]
    reason: str  # machine-readable reason code
    message: str  # user-safe explanation
    provider: str
    estimates: List[Any] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
