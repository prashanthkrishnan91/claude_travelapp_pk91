"""Route reorder-proposal generation service — AI Route Planning v1.

Read-only. Triggered only by an explicit "Plan My Day" click on a day that
already has at least two routeable (activity/meal, located) stops. Never
called on render, day switch, or refresh. Governed by
``docs/ai/AI_ROUTE_PLANNING_V1_ADR.md``.

Hard safety guarantees enforced here:
- No itinerary write of any kind — this module only reads and reasons.
  Applying a proposal is a separate explicit action via the existing
  ``apply_route_reorder_proposal`` (PR C) endpoint.
- Only activity/meal stops with canonical coordinates are eligible to move;
  every other item (flight/hotel/note/transit, or an eligible stop missing
  coordinates) keeps its exact existing position in the returned order.
- The eligible item IDs in ``proposed_order`` are always exactly the eligible
  item IDs in ``current_order`` — validated before the response is built, not
  trusted from the model.
- No fabricated travel time, distance, or location: the LLM is given only
  route legs already computed by the existing Google Routes adapter for the
  day's current order, plus canonical coordinates already on each item. If
  that route data isn't available, this returns "unavailable" rather than
  asking the model to guess.
- No hidden provider calls: the Google Routes call this module makes reuses
  the existing registered route-estimate service, and only runs after the
  explicit generate request (itself only reachable from an explicit user
  click) — the same single-call, no-matrix, no-optimization contract as the
  existing route-estimate endpoint.
- No new provider/model authority: the LLM call reuses the existing
  Anthropic REASONING provider, following the same lazy-import /
  fail-closed / env-key pattern already used by
  ``app.concierge.batched_reason_builder``.
- Fixed-time stops: any two movable stops that both carry an explicit
  ``start_time`` must keep their chronological relative order in the
  proposal — a generated order that would silently violate this is rejected
  rather than surfaced.
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

    if not settings.ai_route_reorder_proposal_v1_enabled:
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

    # Eligible = activity/meal with canonical coordinates already persisted.
    # Everything else keeps its exact current slot in the returned order.
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

    # Reuses the existing registered route-estimate service — one call, the
    # same provider client, current order preserved, no matrix/optimization.
    route_response = compute_route_estimate(
        RouteEstimateRequest(stops=movable_stops),
        trip_id,
        day_id,
        user_id=user_id,
        db=db,
    )
    if route_response.status != "success" or not route_response.estimates:
        return _unavailable(
            day_id,
            actual_current_order,
            reason="route_data_unavailable",
            message=(
                "Travel-time data isn't available for this day right now, "
                "so AI route planning can't make an honest suggestion."
            ),
        )

    prompt = _build_prompt(movable_stops, movable_items_by_id, route_response.estimates)
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
        metadata={
            "movable_stop_count": len(movable_stops),
            "model": _MODEL,
        },
    )


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

Task: suggest a more practical order for these stops that reduces unnecessary backtracking, honors any fixed_time or day_part shown above, keeps sensible meal placement, and preserves the traveler's intent. If the current order is already reasonable, keep it unchanged — prefer minimal changes over churn. Never invent a location, travel time, or opening hour beyond what is given above. This is a suggested order, not a mathematically optimal one — do not use the words "optimal" or "perfect" anywhere in your response.

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
    """Validate an LLM-generated proposal. Returns None (fail-closed) on any
    mismatch — never silently repairs a malformed generation."""
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

    # Fixed-time constraint: two movable stops that both carry an explicit
    # start_time must keep their chronological relative order.
    timed_ids = [
        item_id for item_id in proposed if getattr(items_by_id[item_id], "start_time", None)
    ]
    for i in range(len(timed_ids)):
        for j in range(i + 1, len(timed_ids)):
            earlier_id, later_id = timed_ids[i], timed_ids[j]
            earlier_time = items_by_id[earlier_id].start_time
            later_time = items_by_id[later_id].start_time
            if earlier_time > later_time:
                return None

    return proposed, rationale, move_reasons
