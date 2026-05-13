"""Canonical provider-backed flight search.

Shared backend helper used by both ``/explore/flights`` and
``/trips/create-with-search`` so trip creation seeds the same canonical
``FlightItineraryOffer`` rows that Explore Flights surfaces.

The helper is a thin, well-typed pass-through over ``get_flight_provider()``.
It does not call ``/explore/flights`` over HTTP and does not introduce a
third flight pathway: the active ``FlightProvider`` (Duffel today) remains
the single source of truth for visible offers.

Returns a ``CanonicalFlightSearchResult`` with:

- ``status``  — provider status (``ok``/``empty``/``unavailable``/``error``).
- ``offers``  — canonical ``FlightItineraryOffer`` rows (empty when not OK).
- ``reason``  — optional provider reason string for logging.

Callers must treat ``status != OK`` (or zero offers) as fail-closed.  The
helper never fabricates rows and never raises — provider exceptions are
translated to ``status=ERROR`` with ``offers=[]``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from app.contracts.flight_offer import FlightItineraryOffer
from app.contracts.flights import FlightSourceStatus
from app.models.search import FlightSearchRequest
from app.services.flights_provider import get_flight_provider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CanonicalFlightSearchResult:
    status: FlightSourceStatus
    offers: List[FlightItineraryOffer] = field(default_factory=list)
    reason: str = ""


def canonical_flight_search(req: FlightSearchRequest) -> CanonicalFlightSearchResult:
    """Run the active FlightProvider and return canonical offers only.

    Round-trip is expressed by ``req.return_date`` on the same request; the
    Duffel adapter then sends two slices and returns each itinerary with a
    ``return_leg``.  We do not pair separate one-way searches here — that
    is the legacy SearchService path being retired from create-with-search.
    """
    provider = get_flight_provider()
    try:
        result = provider.search_flights(req)
    except Exception as exc:  # never propagate
        logger.warning("[canonical_flight_search] provider exception: %s", exc)
        return CanonicalFlightSearchResult(
            status=FlightSourceStatus.ERROR,
            offers=[],
            reason=f"provider exception: {exc}",
        )

    offers: List[FlightItineraryOffer] = []
    if result.status is FlightSourceStatus.OK:
        for row in result.rows:
            if isinstance(row, FlightItineraryOffer):
                offers.append(row)

    return CanonicalFlightSearchResult(
        status=result.status,
        offers=offers,
        reason=result.reason or "",
    )


__all__ = ["CanonicalFlightSearchResult", "canonical_flight_search"]
