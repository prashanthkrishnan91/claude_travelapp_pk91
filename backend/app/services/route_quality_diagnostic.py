"""Route-quality diagnostic service — AI Route Planning v1 PR A.

Deterministic, read-only diagnostic derived from a day's already-persisted
itinerary items. Governed by ``docs/ai/AI_ROUTE_PLANNING_V1_ADR.md``
(Section 9, PR A) — the read-only, flag-gated substrate a future AI advisor
may consume. This module never talks to an LLM and never mutates data.

Hard safety guarantees enforced here:
- No LLM call, no AI text generation.
- No external provider call of any kind (no Google Routes, no geocoding).
- No itinerary write — every code path in this module only reads.
- No fabricated travel time/distance — ``route_data_status`` is always
  reported as ``"unavailable"``; this diagnostic never computes, fetches, or
  caches a route figure. (No route-estimate result is persisted server-side
  today, so "unavailable" is the honest answer, not a placeholder.)
- Only activity/meal stops are eligible; flights/hotels/notes are excluded
  with a reason and are never treated as segment endpoints.
- Coordinates come only from canonical fields already persisted in
  ``item.details`` (never geocoded, never inferred). A stop missing
  coordinates is named, never silently dropped.
- Current manual order (``item.position``, as returned by
  ``ItineraryService.list_items`` ordered by position) is preserved.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.config import get_settings
from app.models.route_quality_diagnostic import (
    ELIGIBLE_ITEM_TYPES,
    MIN_LOCATED_STOPS_FOR_AI,
    DiagnosticStopSummary,
    ExcludedStopSummary,
    RouteQualityDiagnosticResponse,
)

# Same alternate-key contract as frontend tripItemMetadata.ts readCanonicalLat/
# readCanonicalLng: top-level lat/lng first, then latitude/longitude(/lon),
# then these nested shapes. Never geocodes; only reads what is already there.
_COORD_NESTED_KEYS = ("coordinates", "geo", "location", "coords", "position")


def _read_number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _read_canonical_lat(details: Dict[str, Any]) -> Optional[float]:
    direct = _read_number(details.get("lat"))
    if direct is None:
        direct = _read_number(details.get("latitude"))
    if direct is not None:
        return direct
    for key in _COORD_NESTED_KEYS:
        nested = details.get(key)
        if isinstance(nested, dict):
            v = _read_number(nested.get("lat"))
            if v is None:
                v = _read_number(nested.get("latitude"))
            if v is not None:
                return v
    return None


def _read_canonical_lng(details: Dict[str, Any]) -> Optional[float]:
    direct = _read_number(details.get("lng"))
    if direct is None:
        direct = _read_number(details.get("longitude"))
    if direct is None:
        direct = _read_number(details.get("lon"))
    if direct is not None:
        return direct
    for key in _COORD_NESTED_KEYS:
        nested = details.get(key)
        if isinstance(nested, dict):
            v = _read_number(nested.get("lng"))
            if v is None:
                v = _read_number(nested.get("longitude"))
            if v is None:
                v = _read_number(nested.get("lon"))
            if v is not None:
                return v
    return None


def _item_type_str(item_type: Any) -> str:
    return item_type.value if hasattr(item_type, "value") else str(item_type)


def _disabled_response() -> RouteQualityDiagnosticResponse:
    return RouteQualityDiagnosticResponse(
        status="disabled",
        eligible_stop_count=0,
        located_stop_count=0,
        missing_coordinate_count=0,
        route_data_status="unavailable",
        warnings=["Route-quality diagnostic is not yet available. This feature is coming soon."],
        safe_for_ai=False,
        ai_blockers=["feature_flag_disabled"],
    )


def compute_route_quality_diagnostic(
    trip_id: UUID,
    day_id: UUID,
    user_id: UUID,
    db: Any,
) -> RouteQualityDiagnosticResponse:
    """Return a deterministic route-quality diagnostic for a single day.

    Ownership of ``day_id`` (via its trip) is verified before any item is
    read, mirroring ``ItineraryService._ensure_day_owned``. No provider or
    LLM call is made on any path.
    """
    settings = get_settings()

    if not settings.route_quality_diagnostic_v1_enabled:
        return _disabled_response()

    # Imported lazily (only reached when the flag is on): keeps this module
    # importable in isolation and defers to the existing itinerary read path.
    from app.services.itinerary import ItineraryService

    itinerary = ItineraryService(db)
    items = itinerary.list_items(day_id, user_id=user_id)

    eligible: List[DiagnosticStopSummary] = []
    missing: List[DiagnosticStopSummary] = []
    excluded: List[ExcludedStopSummary] = []

    for item in items:
        item_type = _item_type_str(item.item_type)
        if item_type not in ELIGIBLE_ITEM_TYPES:
            excluded.append(
                ExcludedStopSummary(
                    item_id=str(item.id),
                    title=item.title,
                    item_type=item_type,
                    reason=(
                        f"item_type '{item_type}' is not a route stop in v1; "
                        "only activity and meal stops are eligible for route "
                        "quality reasoning"
                    ),
                )
            )
            continue

        details = item.details if isinstance(item.details, dict) else {}
        lat = _read_canonical_lat(details)
        lng = _read_canonical_lng(details)
        category = details.get("category")
        if not isinstance(category, str):
            category = None

        summary = DiagnosticStopSummary(
            item_id=str(item.id),
            title=item.title,
            item_type=item_type,
            position=item.position or 0,
            lat=lat,
            lng=lng,
            category=category,
        )
        eligible.append(summary)
        if lat is None or lng is None:
            missing.append(summary)

    eligible_count = len(eligible)
    missing_count = len(missing)
    located_count = eligible_count - missing_count

    warnings: List[str] = []
    ai_blockers: List[str] = []

    if eligible_count < 2:
        status = "insufficient_stops"
        warnings.append(
            f"This day has {eligible_count} eligible (activity/meal) stop"
            f"{'s' if eligible_count != 1 else ''}. Route-quality reasoning "
            "needs at least 2."
        )
        ai_blockers.append("insufficient_eligible_stops")
    elif missing_count > 0:
        status = "missing_coordinates"
        warnings.append(
            f"{located_count} of {eligible_count} stops have location data. "
            "Add locations before route planning."
        )
        ai_blockers.append("missing_stop_coordinates")
    else:
        status = "ready"

    safe_for_ai = status == "ready" and located_count >= MIN_LOCATED_STOPS_FOR_AI

    # Route/connector data is never fetched or persisted by this diagnostic —
    # honestly report the gap rather than imply a figure exists.
    warnings.append(
        "No previously computed route/connector data is available for this "
        "day; a future AI pass could describe stop order and location "
        "coverage only, never a travel time or distance it did not already "
        "have."
    )

    return RouteQualityDiagnosticResponse(
        status=status,
        eligible_stop_count=eligible_count,
        located_stop_count=located_count,
        missing_coordinate_count=missing_count,
        eligible_stops=eligible,
        missing_coordinate_stops=missing,
        excluded_stops=excluded,
        route_data_status="unavailable",
        warnings=warnings,
        safe_for_ai=safe_for_ai,
        ai_blockers=ai_blockers,
    )
