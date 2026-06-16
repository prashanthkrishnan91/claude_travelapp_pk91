"""Route estimate request/response models — Route Planning v1 PR 2.

Governed by Route Planning v1 Contract ADR (PR #509).
Accepted stop types: activity and meal only. Flights, hotels, and notes are excluded.
No travel-time values, no fabricated coordinates, no reordering.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

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


class RouteEstimateResponse(BaseModel):
    """Fail-closed route estimate response.

    In this implementation estimates is always an empty list.
    No travel times, distances, or durations are computed or fabricated.
    """

    status: str  # "disabled" | "not_configured"
    reason: str  # machine-readable reason code
    message: str  # user-safe explanation
    provider: str  # "google_routes" — future candidate only, never called in this PR
    estimates: List[Any] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
