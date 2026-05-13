"""Explore routes — provider-backed vertical search.

These routes are the canonical, provider-neutral flight (and future hotel)
search surface for the Explore shell.  They differ from the legacy
``/search/flights`` route in that:

- They call ``get_flight_provider()`` which consults Provider Registry v1.
- They return ``FlightItineraryOffer`` (normalized contract), not the legacy
  mock-backed ``FlightResult``.
- They never generate mock/placeholder rows.  When no provider is active the
  response carries ``status=unavailable`` with an empty ``offers`` list, and
  the frontend renders the polished fail-closed state.

Routes:
  POST /explore/flights — live flight search via the active registered provider.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import Any, Dict, List

from fastapi import APIRouter

from app.contracts.flight_offer import FlightItineraryOffer
from app.core.config import get_settings
from app.core.cost_guardrails import GuardrailRule, guardrails
from app.core.deps import DB, CurrentUserID
from app.models.search import FlightSearchRequest
from app.services.canonical_flight_search import canonical_flight_search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/explore", tags=["explore"])


def _offer_to_dict(offer: FlightItineraryOffer) -> Dict[str, Any]:
    """Serialize FlightItineraryOffer to a plain dict for JSON response.

    Adds ``kind="flight_offer"`` discriminant for the frontend type system.
    ``dataclasses.asdict`` recursively converts nested dataclasses and tuples.
    All enums extend ``str`` so they serialize as their string values.
    """
    d = dataclasses.asdict(offer)
    d["kind"] = "flight_offer"
    # _FABRICATED_HOSTS is a class var (no annotation) so asdict skips it;
    # but remove any stray "_fabricated_hosts" key defensively.
    d.get("booking_link", {}).pop("_fabricated_hosts", None)
    return d


@router.post("/flights")
def explore_flights(
    payload: FlightSearchRequest,
    db: DB,
    user_id: CurrentUserID,
) -> Dict[str, Any]:
    """Live flight search via the active registered provider (Ignav v1).

    Returns a provider-neutral response envelope:
    ``{ status, offers: [...FlightItineraryOffer...], reason? }``

    ``status`` values:
    - ``ok``          — one or more offers returned.
    - ``empty``       — provider active but no itineraries found.
    - ``unavailable`` — no provider configured / provider not reachable.
    - ``error``       — provider returned an unexpected error.

    The frontend maps ``unavailable`` and ``error`` to the polished
    fail-closed state; it renders offer cards only when ``status=ok``.
    """
    settings = get_settings()
    guardrails.enforce(
        endpoint_key="explore.explore_flights",
        user_id=user_id,
        rule=GuardrailRule(
            requests=settings.guardrail_search_requests,
            window_seconds=settings.guardrail_search_window_seconds,
            dedupe_seconds=settings.guardrail_search_dedupe_seconds,
        ),
        dedupe_payload={
            "origin": payload.origin,
            "destination": payload.destination,
            "departure_date": str(payload.departure_date),
            "return_date": str(payload.return_date) if payload.return_date else None,
        },
    )

    logger.info(
        "[explore_flights] origin=%s dest=%s dep=%s ret=%s pax=%d cabin=%s",
        payload.origin,
        payload.destination,
        payload.departure_date,
        payload.return_date,
        payload.passengers,
        payload.cabin_class,
    )

    result = canonical_flight_search(payload)

    offers: List[Dict[str, Any]] = []
    for row in result.offers:
        try:
            offers.append(_offer_to_dict(row))
        except Exception as exc:
            logger.warning("[explore_flights] offer serialization error: %s", exc)

    return {
        "status": result.status.value,
        "offers": offers,
        "reason": result.reason or None,
    }
