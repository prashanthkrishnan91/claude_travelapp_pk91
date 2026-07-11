"""Route reorder-proposal generation service — AI Route Planning v1.

Read-only. Triggered only by an explicit "Plan My Day" click on a day that
already has at least two routeable (activity/meal, located) stops. Never
called on render, day switch, or refresh. Governed by
``docs/ai/AI_ROUTE_PLANNING_V1_ADR.md``.

Hard safety guarantees enforced here:
- No itinerary write of any kind — this module only reads and reasons.
  Applying a proposal is a separate explicit action via the existing
  ``apply_route_reorder_proposal`` (PR C) endpoint.
- Both the generation flag (``ai_route_reorder_proposal_v1_enabled``) and the
  apply flag (``route_reorder_proposal_v1_enabled``) must be on before any
  Google Routes or LLM call happens — a proposal is never generated for a
  day where applying it would be impossible.
- Only activity/meal stops with canonical coordinates are eligible to move;
  every other item (flight/hotel/note/transit, or an eligible stop missing
  coordinates) keeps its exact existing position in the returned order.
- The eligible item IDs in ``proposed_order`` are always exactly the eligible
  item IDs in ``current_order`` — validated before the response is built, not
  trusted from the model.
- The LLM only *proposes*; Google Routes *verifies*. The current order is
  routed once, the LLM's proposed order is routed a second time (only if it
  actually changed and passed structural/fixed-time validation), and the
  proposal is surfaced as a change only when the routed comparison shows a
  deterministic, material improvement (see ``_is_material_improvement``).
  Otherwise the unchanged current order is returned with
  ``reason="current_order_already_practical"`` and no Apply action is
  offered (``proposed_order == current_order``). No fabricated travel time,
  distance, or location is ever passed to the model or returned to the
  caller — every duration/distance figure in the response comes from real
  Google Routes legs.
- No hidden provider calls: both Google Routes calls this module makes reuse
  the existing registered route-estimate service (at most two calls total —
  current order, then proposed order only if it changed), and only run
  after the explicit generate request. No matrix API, no new provider.
- No new provider/model authority: the LLM call reuses the existing
  Anthropic REASONING provider, following the same lazy-import /
  fail-closed / env-key pattern already used by
  ``app.concierge.batched_reason_builder``.
- Fixed-time anchors: every movable stop with an explicit ``start_time`` is
  a fixed anchor — it must stay in its exact current slot, and no other
  stop may cross it. Untimed movable stops may only be reordered within the
  contiguous segment (before/between/after anchors) they already occupy. A
  generated order that crosses an anchor is rejected, not silently fixed.
- No claim of mathematical optimality: a generated rationale/move-reason
  containing "optimal" or "perfect" is treated as an invalid generation and
  rejected, rather than shown to the user.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException

from app.core.config import get_settings
from app.models.route_estimate import RouteableStop, RouteEstimateRequest
from app.models.route_quality_diagnostic import ELIGIBLE_ITEM_TYPES
from app.models.route_reorder_proposal import (
    RouteReorderProposalGenerateRequest,
    RouteReorderProposalGenerateResponse,
)
from app.services.google_routes_adapter import MAX_ROUTABLE_STOPS
from app.services.route_estimate import compute_route_estimate
from app.services.route_quality_diagnostic import _read_canonical_lat, _read_canonical_lng

logger = logging.getLogger(__name__)

# Reasoning-only call, single attempt, no fan-out — matches the Latency
# Budget Pack. Override via Railway env: AI_ROUTE_REORDER_PROPOSAL_MODEL.
_MODEL = os.getenv("AI_ROUTE_REORDER_PROPOSAL_MODEL", "claude-sonnet-4-6")
_TIMEOUT_SECONDS = 12.0
_CLAIM_UNSAFE_WORDS = ("optimal", "perfect")

# Conservative acceptance thresholds for surfacing a changed order — see
# module docstring. A proposal is accepted only when the routed comparison
# clears one of these two bars.
_DURATION_IMPROVEMENT_ABS_SECONDS = 300  # 5 minutes
_DURATION_IMPROVEMENT_PCT = 0.10
_DURATION_SIMILAR_WINDOW_SECONDS = 120  # 2 minutes
_DISTANCE_IMPROVEMENT_ABS_METERS = 1000  # 1 km
_DISTANCE_IMPROVEMENT_PCT = 0.10

_ALREADY_PRACTICAL_MESSAGE = (
    "This day's order already looks practical — the suggested change "
    "didn't meaningfully reduce travel time or distance, so nothing is "
    "proposed."
)


def _verify_trip_ownership(db: Any, trip_id: UUID, user_id: UUID) -> None:
    """Mirrors route_reorder_proposal._verify_trip_ownership."""
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
    """Mirrors route_reorder_proposal._verify_day_ownership."""
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


def _item_type_str(item_type: Any) -> str:
    return item_type.value if hasattr(item_type, "value") else str(item_type)


def _disabled_response(day_id: UUID) -> RouteReorderProposalGenerateResponse:
    return RouteReorderProposalGenerateResponse(
        status="disabled",
        reason="feature_flag_disabled",
        message="AI route planning is not yet available. This feature is coming soon.",
        day_id=str(day_id),
    )


def _unavailable(
    day_id: UUID, current_order: List[str], reason: str, message: str
) -> RouteReorderProposalGenerateResponse:
    return RouteReorderProposalGenerateResponse(
        status="unavailable",
        reason=reason,
        message=message,
        day_id=str(day_id),
        current_order=current_order,
    )


def _already_practical_response(
    day_id: UUID,
    actual_current_order: List[str],
    current_duration_seconds: int,
    current_distance_meters: int,
    proposed_duration_seconds: Optional[int] = None,
    proposed_distance_meters: Optional[int] = None,
    route_call_count: int = 1,
    movable_stop_count: int = 0,
) -> RouteReorderProposalGenerateResponse:
    final_duration = (
        proposed_duration_seconds if proposed_duration_seconds is not None else current_duration_seconds
    )
    final_distance = (
        proposed_distance_meters if proposed_distance_meters is not None else current_distance_meters
    )
    return RouteReorderProposalGenerateResponse(
        status="success",
        reason="current_order_already_practical",
        message=_ALREADY_PRACTICAL_MESSAGE,
        day_id=str(day_id),
        current_order=actual_current_order,
        proposed_order=actual_current_order,
        rationale="",
        move_reasons={},
        current_duration_seconds=current_duration_seconds,
        proposed_duration_seconds=final_duration,
        estimated_savings_seconds=current_duration_seconds - final_duration,
        current_distance_meters=current_distance_meters,
        proposed_distance_meters=final_distance,
        estimated_distance_savings_meters=current_distance_meters - final_distance,
        metadata={
            "movable_stop_count": movable_stop_count,
            "model": _MODEL,
            "route_call_count": route_call_count,
        },
    )


def _build_movable_stops(items: List[Any]) -> Tuple[List[RouteableStop], Dict[str, Any]]:
    """Eligible = activity/meal with canonical coordinates already persisted,
    in the day's current position order. Everything else (flights, hotels,
    notes, transit, or an eligible stop missing coordinates) is excluded and
    keeps its exact current slot in the returned order."""
    movable_stops: List[RouteableStop] = []
    movable_items_by_id: Dict[str, Any] = {}
    for item in items:
        item_type = _item_type_str(item.item_type)
        if item_type not in ELIGIBLE_ITEM_TYPES:
            continue
        details = item.details if isinstance(item.details, dict) else {}
        lat = _read_canonical_lat(details)
        lng = _read_canonical_lng(details)
        if lat is None or lng is None:
            continue
        stop = RouteableStop(
            item_id=str(item.id),
            title=item.title,
            item_type=item_type,
            lat=lat,
            lng=lng,
            place_id=details.get("placeId") if isinstance(details.get("placeId"), str) else None,
            provider_place_id=(
                details.get("providerPlaceId")
                if isinstance(details.get("providerPlaceId"), str)
                else None
            ),
        )
        movable_stops.append(stop)
        movable_items_by_id[str(item.id)] = item
    return movable_stops, movable_items_by_id


def generate_route_reorder_proposal(
    trip_id: UUID,
    day_id: UUID,
    user_id: UUID,
    payload: RouteReorderProposalGenerateRequest,
    db: Any,
) -> RouteReorderProposalGenerateResponse:
    """Generate a suggested stop order for one day, or an honest unavailable
    result. Never writes anything.
    """
    settings = get_settings()

    if not settings.ai_route_reorder_proposal_v1_enabled or not settings.route_reorder_proposal_v1_enabled:
        return _disabled_response(day_id)

    _verify_trip_ownership(db, trip_id, user_id)
    _verify_day_ownership(db, trip_id, day_id)

    from app.services.itinerary import ItineraryService

    itinerary = ItineraryService(db)
    items = itinerary.list_items(day_id, user_id=user_id)
    actual_current_order = [str(item.id) for item in items]

    if payload.current_order != actual_current_order:
        return _unavailable(
            day_id,
            actual_current_order,
            reason="stale_current_order",
            message=(
                "This day's order changed since it was last loaded. Refresh "
                "and try Plan My Day again."
            ),
        )

    movable_stops, movable_items_by_id = _build_movable_stops(items)

    if len(movable_stops) < 2:
        return _unavailable(
            day_id,
            actual_current_order,
            reason="insufficient_stops",
            message=(
                "This day needs at least 2 activity or meal stops with "
                "locations before AI route planning can suggest an order."
            ),
        )

    if len(movable_stops) > MAX_ROUTABLE_STOPS:
        return _unavailable(
            day_id,
            actual_current_order,
            reason="too_many_stops",
            message=(
                f"AI route planning supports at most {MAX_ROUTABLE_STOPS} "
                "located stops per day in v1."
            ),
        )

    # First Google Routes call: the day's current order. Reuses the existing
    # registered route-estimate service — same provider client, order
    # preserved, no matrix/optimization.
    current_route_response = compute_route_estimate(
        RouteEstimateRequest(stops=movable_stops),
        trip_id,
        day_id,
        user_id=user_id,
        db=db,
    )
    if current_route_response.status != "success" or not current_route_response.estimates:
        return _unavailable(
            day_id,
            actual_current_order,
            reason="route_data_unavailable",
            message=(
                "Travel-time data isn't available for this day right now, "
                "so AI route planning can't make an honest suggestion."
            ),
        )

    current_duration, current_distance = _sum_route_totals(current_route_response.estimates)

    prompt = _build_prompt(movable_stops, movable_items_by_id, current_route_response.estimates)
    raw_response = _call_llm(prompt)
    if raw_response is None:
        return _unavailable(
            day_id,
            actual_current_order,
            reason="llm_unavailable",
            message="AI route planning isn't available right now. Please try again.",
        )

    parsed = _parse_llm_response(raw_response)
    movable_ids = {stop.item_id for stop in movable_stops}
    validated = _validate_generation(parsed, movable_ids, movable_items_by_id)
    if validated is None:
        return _unavailable(
            day_id,
            actual_current_order,
            reason="generation_invalid",
            message=(
                "AI route planning couldn't produce a trustworthy suggestion "
                "for this day. Please try again."
            ),
        )
    proposed_movable_order, rationale, move_reasons = validated

    current_movable_order = [stop.item_id for stop in movable_stops]

    if not _fixed_time_segments_respected(current_movable_order, proposed_movable_order, movable_items_by_id):
        return _unavailable(
            day_id,
            actual_current_order,
            reason="fixed_time_anchor_violated",
            message=(
                "AI route planning couldn't produce a suggestion that "
                "honors this day's fixed times. Please try again."
            ),
        )

    if proposed_movable_order == current_movable_order:
        # The model itself judged the current order best — no need to spend
        # a second Google Routes call to confirm that.
        return _already_practical_response(
            day_id,
            actual_current_order,
            current_duration,
            current_distance,
            route_call_count=1,
            movable_stop_count=len(movable_stops),
        )

    # Second Google Routes call: the proposed order, only reachable once the
    # generation passed structural + fixed-time validation and actually
    # differs from the current order.
    stop_by_id = {stop.item_id: stop for stop in movable_stops}
    proposed_stops_ordered = [stop_by_id[item_id] for item_id in proposed_movable_order]
    proposed_route_response = compute_route_estimate(
        RouteEstimateRequest(stops=proposed_stops_ordered),
        trip_id,
        day_id,
        user_id=user_id,
        db=db,
    )
    if proposed_route_response.status != "success" or not proposed_route_response.estimates:
        return _unavailable(
            day_id,
            actual_current_order,
            reason="route_data_unavailable",
            message=(
                "Travel-time data isn't available for this day right now, "
                "so AI route planning can't make an honest suggestion."
            ),
        )

    proposed_duration, proposed_distance = _sum_route_totals(proposed_route_response.estimates)

    if not _is_material_improvement(current_duration, proposed_duration, current_distance, proposed_distance):
        return _already_practical_response(
            day_id,
            actual_current_order,
            current_duration,
            current_distance,
            proposed_duration_seconds=proposed_duration,
            proposed_distance_meters=proposed_distance,
            route_call_count=2,
            movable_stop_count=len(movable_stops),
        )

    full_proposed_order = _splice_movable_order(actual_current_order, movable_ids, proposed_movable_order)

    return RouteReorderProposalGenerateResponse(
        status="success",
        reason="proposal_generated",
        message="Here is a suggested order for this day.",
        day_id=str(day_id),
        current_order=actual_current_order,
        proposed_order=full_proposed_order,
        rationale=rationale,
        move_reasons=move_reasons,
        current_duration_seconds=current_duration,
        proposed_duration_seconds=proposed_duration,
        estimated_savings_seconds=current_duration - proposed_duration,
        current_distance_meters=current_distance,
        proposed_distance_meters=proposed_distance,
        estimated_distance_savings_meters=current_distance - proposed_distance,
        metadata={
            "movable_stop_count": len(movable_stops),
            "model": _MODEL,
            "route_call_count": 2,
        },
    )


def _sum_route_totals(estimates: List[Dict[str, Any]]) -> Tuple[int, int]:
    """Sum duration/distance across every leg. Both figures come only from
    the provider's own returned legs — never estimated or interpolated."""
    duration = sum(int(leg.get("duration_seconds", 0)) for leg in estimates)
    distance = sum(int(leg.get("distance_meters", 0)) for leg in estimates)
    return duration, distance


def _is_material_improvement(
    current_duration_seconds: int,
    proposed_duration_seconds: int,
    current_distance_meters: int,
    proposed_distance_meters: int,
) -> bool:
    """Conservative acceptance rule — see module docstring. A proposal is
    surfaced as a change only when it clears one of two bars: a real
    duration improvement, or (when duration is essentially unchanged) a
    real distance improvement. Never accepts a proposal that worsens
    duration just because distance improved."""
    duration_savings = current_duration_seconds - proposed_duration_seconds
    duration_threshold = min(
        _DURATION_IMPROVEMENT_ABS_SECONDS, current_duration_seconds * _DURATION_IMPROVEMENT_PCT
    )
    if duration_threshold > 0 and duration_savings >= duration_threshold:
        return True

    duration_diff = abs(current_duration_seconds - proposed_duration_seconds)
    if duration_diff <= _DURATION_SIMILAR_WINDOW_SECONDS:
        distance_savings = current_distance_meters - proposed_distance_meters
        distance_threshold = min(
            _DISTANCE_IMPROVEMENT_ABS_METERS, current_distance_meters * _DISTANCE_IMPROVEMENT_PCT
        )
        if distance_threshold > 0 and distance_savings >= distance_threshold:
            return True

    return False


def _fixed_time_segments_respected(
    current_movable_order: List[str],
    proposed_movable_order: List[str],
    items_by_id: Dict[str, Any],
) -> bool:
    """Every movable stop with an explicit ``start_time`` is a fixed anchor:
    it must stay in its exact current slot, and nothing may cross it.
    Untimed stops may only be reordered within the contiguous segment
    (before the first anchor, between two anchors, or after the last
    anchor) they already occupy — never across an anchor."""
    anchor_indices = {
        i for i, item_id in enumerate(current_movable_order) if getattr(items_by_id[item_id], "start_time", None)
    }
    for i in anchor_indices:
        if proposed_movable_order[i] != current_movable_order[i]:
            return False

    n = len(current_movable_order)
    i = 0
    while i < n:
        if i in anchor_indices:
            i += 1
            continue
        start = i
        while i < n and i not in anchor_indices:
            i += 1
        if set(proposed_movable_order[start:i]) != set(current_movable_order[start:i]):
            return False
    return True


def _splice_movable_order(
    full_current_order: List[str], movable_ids: set, proposed_movable_order: List[str]
) -> List[str]:
    """Rebuild the full day order, replacing only the movable-item slots (in
    their original absolute positions) with the model's new sequence for
    those slots. Every non-movable item stays at its exact current index."""
    it = iter(proposed_movable_order)
    return [next(it) if item_id in movable_ids else item_id for item_id in full_current_order]


def _build_prompt(
    stops: List[RouteableStop],
    items_by_id: Dict[str, Any],
    estimates: List[Dict[str, Any]],
) -> str:
    stop_lines = []
    for stop in stops:
        item = items_by_id[stop.item_id]
        parts = [f'id="{stop.item_id}"', f'title="{stop.title}"', f"type={stop.item_type}"]
        if item.start_time:
            parts.append(f'fixed_time="{item.start_time.isoformat()}"')
        details = item.details if isinstance(item.details, dict) else {}
        day_part = details.get("dayPart")
        if isinstance(day_part, str) and day_part:
            parts.append(f'day_part="{day_part}"')
        parts.append(f"lat={stop.lat}")
        parts.append(f"lng={stop.lng}")
        stop_lines.append(" ".join(parts))

    title_by_id = {stop.item_id: stop.title for stop in stops}
    leg_lines = []
    for leg in estimates:
        from_title = title_by_id.get(leg.get("from_item_id"), leg.get("from_item_id"))
        to_title = title_by_id.get(leg.get("to_item_id"), leg.get("to_item_id"))
        duration_min = round(int(leg.get("duration_seconds", 0)) / 60)
        distance_km = round(int(leg.get("distance_meters", 0)) / 1000, 1)
        leg_lines.append(f'"{from_title}" -> "{to_title}": {duration_min} min, {distance_km} km')

    return f"""You are helping arrange stops already added to one day of a trip itinerary into a more practical order. These stops are already in the itinerary — you are only suggesting a better sequence for them, never adding, removing, or inventing a stop.

Stops in this day's current order:
{chr(10).join(stop_lines)}

Real travel time between consecutive stops in the CURRENT order, from the app's route provider — do not invent any figure not listed here:
{chr(10).join(leg_lines) if leg_lines else "(no leg data)"}

Task: suggest a more practical order for these stops that reduces unnecessary backtracking, honors any fixed_time or day_part shown above, keeps sensible meal placement, and preserves the traveler's intent. Any stop with a fixed_time is a hard anchor — it cannot move from its position, and other stops cannot be reordered across it; you may only reorder untimed stops among themselves, within the stretch of stops between the same two fixed_time anchors (or before the first / after the last). If the current order is already reasonable, keep it unchanged — prefer minimal changes over churn. Never invent a location, travel time, or opening hour beyond what is given above. This is a suggested order, not a mathematically optimal one — do not use the words "optimal" or "perfect" anywhere in your response.

Return ONLY a JSON object with exactly this shape (ids must be exactly the ids listed above, each exactly once):
{{"proposed_order": ["id1", "id2", ...], "rationale": "one or two plain-English sentences", "move_reasons": {{"id": "short reason", "...": "only include an entry if it materially helps"}}}}"""


def _call_llm(prompt: str) -> Optional[str]:
    """Call the Claude API with a timeout. Returns raw response text or None.

    Mirrors the lazy-import / env-key / fail-closed pattern in
    ``app.concierge.batched_reason_builder._call_llm``.
    """
    try:
        import anthropic  # type: ignore[import]
    except ImportError:
        logger.warning("route_reorder_proposal_generate: anthropic SDK not installed, skipping LLM")
        return None

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("route_reorder_proposal_generate: ANTHROPIC_API_KEY not set, skipping LLM")
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            timeout=_TIMEOUT_SECONDS,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text if message.content else None
    except Exception as exc:
        logger.warning("route_reorder_proposal_generate: llm_call_failed error=%s", exc)
        return None


def _parse_llm_response(response_text: str) -> Dict[str, Any]:
    if not response_text:
        return {}
    try:
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if not json_match:
            return {}
        return json.loads(json_match.group(0))
    except (json.JSONDecodeError, ValueError):
        return {}


def _contains_claim_unsafe_words(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in _CLAIM_UNSAFE_WORDS)


def _validate_generation(
    parsed: Dict[str, Any],
    movable_ids: set,
    items_by_id: Dict[str, Any],
) -> Optional[Tuple[List[str], str, Dict[str, str]]]:
    """Validate an LLM-generated proposal's structure and copy safety.
    Returns None (fail-closed) on any mismatch — never silently repairs a
    malformed generation. Fixed-time anchor/segment validation happens
    separately in ``_fixed_time_segments_respected`` once the current
    movable order is available."""
    proposed = parsed.get("proposed_order")
    if not isinstance(proposed, list) or not all(isinstance(x, str) for x in proposed):
        return None
    proposed_set = set(proposed)
    if len(proposed) != len(movable_ids) or len(proposed) != len(proposed_set) or proposed_set != movable_ids:
        return None

    rationale = parsed.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        return None
    rationale = rationale.strip()
    if _contains_claim_unsafe_words(rationale):
        return None

    move_reasons: Dict[str, str] = {}
    raw_reasons = parsed.get("move_reasons")
    if isinstance(raw_reasons, dict):
        for item_id, reason in raw_reasons.items():
            if item_id not in movable_ids or not isinstance(reason, str) or not reason.strip():
                continue
            reason = reason.strip()
            if _contains_claim_unsafe_words(reason):
                return None
            move_reasons[item_id] = reason

    return proposed, rationale, move_reasons
