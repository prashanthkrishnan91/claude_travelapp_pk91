"""Route-quality diagnostic models — AI Route Planning v1 PR A.

Read-only, deterministic diagnostic substrate for a future AI advisor.
Governed by ``docs/ai/AI_ROUTE_PLANNING_V1_ADR.md`` (Section 9, PR A).

This module defines shapes only. No LLM calls, no AI text generation, no
provider calls, and no itinerary writes happen anywhere in this PR.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

# Only activity/meal stops are eligible for route-quality reasoning — mirrors
# the adjacency rule in travelHints.ts / computeRouteReadiness and the
# eligibility rule in ROUTE_PLANNING_V1_CONTRACT.md Section 2.
ELIGIBLE_ITEM_TYPES = frozenset({"activity", "meal"})

# Fewer than this many *located* eligible stops means a future AI pass must
# not reason about this day's route quality.
MIN_LOCATED_STOPS_FOR_AI = 2

# Documented, closed vocabulary — a future PR B consumer must not depend on
# an undocumented status string.
DiagnosticStatus = Literal["ready", "insufficient_stops", "missing_coordinates", "disabled"]
RouteDataStatus = Literal["unavailable"]


class DiagnosticStopSummary(BaseModel):
    """Safe, non-fabricated summary of one eligible stop.

    ``lat``/``lng`` are ``None`` when the item has no canonical coordinates —
    never fabricated, never geocoded, never interpolated. ``position`` is the
    item's existing manual order; this diagnostic never resequences it.
    """

    item_id: str
    title: str
    item_type: str
    position: int
    lat: Optional[float] = None
    lng: Optional[float] = None
    category: Optional[str] = None


class ExcludedStopSummary(BaseModel):
    """A non-eligible stop (flight/hotel/note/etc.) with an honest reason."""

    item_id: str
    title: str
    item_type: str
    reason: str


class RouteQualityDiagnosticResponse(BaseModel):
    """Deterministic, read-only route-quality diagnostic for a single day.

    ``status`` values: ``ready`` | ``insufficient_stops`` |
    ``missing_coordinates`` | ``disabled``.

    ``route_data_status`` reports whether already-computed route/connector
    data is available for this day. This PR never fetches or persists route
    data server-side, so it is always ``"unavailable"`` — an honest gap, not
    a fabricated figure. No ``duration``/``distance`` field exists anywhere
    on this response.
    """

    status: DiagnosticStatus
    eligible_stop_count: int
    located_stop_count: int
    missing_coordinate_count: int
    eligible_stops: List[DiagnosticStopSummary] = Field(default_factory=list)
    missing_coordinate_stops: List[DiagnosticStopSummary] = Field(default_factory=list)
    excluded_stops: List[ExcludedStopSummary] = Field(default_factory=list)
    route_data_status: RouteDataStatus = "unavailable"
    warnings: List[str] = Field(default_factory=list)
    safe_for_ai: bool
    ai_blockers: List[str] = Field(default_factory=list)
