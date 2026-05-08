"""Flights provider seam — Flights Product Contract v1.

The runtime seam the future provider-backed Flights v1 PR will plug into.
This module deliberately ships **no** real provider, **no** API key, and
**no** fabricated fallback rows.  Its only job is to define the interface
boundary so the next PR is a drop-in adapter, not a refactor of
``TripBuilder`` / ``OptimizeTripModal`` / ``/trips/create-with-search``.

The seam returns a typed ``FlightProviderResult`` containing a list of
real ``FlightResult`` rows and a ``FlightSourceStatus`` health marker.  An
unavailable / errored provider returns an empty ``rows`` list and a
non-``OK`` status — never a fake row.

Default binding (``DefaultFlightProvider``) is the ``NullFlightProvider``
which always returns ``UNAVAILABLE``.  The legacy ``_mock_flights`` helper
in ``backend/app/services/search.py`` is intentionally NOT wired into this
seam: it remains a quarantined legacy fixture, and binding it here would
re-open the persistence hole that PR #295 closed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Protocol

from app.contracts.flights import FlightProviderUnavailable, FlightSourceStatus
from app.models.search import FlightResult, FlightSearchRequest


@dataclass(frozen=True)
class FlightProviderResult:
    """Typed response for any flight provider adapter.

    Invariants:

    - ``rows`` is empty whenever ``status`` is not ``OK``.
    - Each row in ``rows`` MUST satisfy
      ``app.contracts.flights.is_persistable_flight``.
    - Adapters never raise on transport / API errors; they translate to
      ``status = ERROR`` with a non-empty ``reason``.
    """

    status: FlightSourceStatus
    rows: List[FlightResult] = field(default_factory=list)
    reason: str = ""


class FlightProvider(Protocol):
    """Adapter interface every Flights v1 provider must satisfy.

    Implementations live alongside this module (e.g.
    ``flights_provider_amadeus.py``) and must:

    - take a fully-formed ``FlightSearchRequest`` (no string parsing);
    - never call out to a fixture or fabricate data on failure;
    - never raise — translate every failure to
      ``FlightProviderResult(status=ERROR, ...)``.
    """

    def search_flights(self, req: FlightSearchRequest) -> FlightProviderResult: ...


class NullFlightProvider:
    """Default provider — always reports ``UNAVAILABLE`` with no rows.

    This is the binding ``app.services.flights_provider.get_flight_provider``
    returns until a real adapter is registered.  It is the typed equivalent
    of "no provider configured" and matches the fail-closed copy surfaced
    by ``OptimizeTripModal``.
    """

    def search_flights(self, req: FlightSearchRequest) -> FlightProviderResult:
        return FlightProviderResult(
            status=FlightSourceStatus.UNAVAILABLE,
            rows=[],
            reason="no flight provider configured",
        )

    def unavailable(self) -> FlightProviderUnavailable:
        return FlightProviderUnavailable(
            status=FlightSourceStatus.UNAVAILABLE,
            reason="no flight provider configured",
        )


_DEFAULT_PROVIDER: FlightProvider = NullFlightProvider()


def get_flight_provider() -> FlightProvider:
    """Return the active ``FlightProvider``.

    Until Flights v1 lands, this is always ``NullFlightProvider``.  The
    next PR is expected to add an env-gated registry that resolves a real
    adapter; until then, callers must treat the result as fail-closed.
    """
    return _DEFAULT_PROVIDER


__all__ = [
    "DefaultFlightProvider",
    "FlightProvider",
    "FlightProviderResult",
    "NullFlightProvider",
    "get_flight_provider",
]


# Legacy alias for direct test imports.
DefaultFlightProvider = NullFlightProvider
