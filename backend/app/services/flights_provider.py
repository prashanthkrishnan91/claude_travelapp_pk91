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

from app.contracts.flights import (
    FlightProviderUnavailable,
    FlightSourceStatus,
    assert_persistable_flight,
)
from app.models.search import FlightResult, FlightSearchRequest


@dataclass(frozen=True)
class FlightProviderResult:
    """Typed response for any flight provider adapter.

    Invariants (enforced in ``__post_init__``):

    - ``rows`` MUST be empty whenever ``status`` is not ``OK``
      (``EMPTY``/``UNAVAILABLE``/``ERROR`` cannot carry rows).
    - When ``status == OK``, every row MUST satisfy
      ``app.contracts.flights.is_persistable_flight``.  Mock/demo/sample
      sources, fabricated booking hosts, and rows missing required fields
      are rejected via ``assert_persistable_flight``.
    - ``OK`` with zero rows is intentionally NOT allowed: callers should
      use ``EMPTY`` for the "valid query, no results" case so the typed
      status remains the single source of truth for UI fail-closed copy.
    - Adapters never raise on transport / API errors; they translate to
      ``status = ERROR`` with a non-empty ``reason``.
    """

    status: FlightSourceStatus
    rows: List[FlightResult] = field(default_factory=list)
    reason: str = ""

    def __post_init__(self) -> None:
        if self.status is FlightSourceStatus.OK:
            if not self.rows:
                raise ValueError(
                    "FlightProviderResult(status=OK) must carry at least one "
                    "row; use FlightSourceStatus.EMPTY for zero-result queries"
                )
            for idx, row in enumerate(self.rows):
                try:
                    assert_persistable_flight(row)
                except Exception as exc:
                    raise ValueError(
                        f"FlightProviderResult(status=OK).rows[{idx}] failed "
                        f"the Flights Product Contract v1: {exc}"
                    ) from exc
        else:
            if self.rows:
                raise ValueError(
                    f"FlightProviderResult(status={self.status.value}) must "
                    f"carry zero rows; got {len(self.rows)}"
                )


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

# Memoised real provider keyed by env tuple so the OAuth token cache survives
# across requests within a process while still picking up env changes.
_PROVIDER_CACHE: dict = {}


def reset_flight_provider_cache() -> None:
    """Clear the memoised provider — used by tests that monkeypatch env."""
    _PROVIDER_CACHE.clear()


def get_flight_provider() -> FlightProvider:
    """Return the active ``FlightProvider``.

    Flights v1 — env-gated registry:
    - When ``AMADEUS_FLIGHTS_ENABLED`` is truthy AND both
      ``AMADEUS_CLIENT_ID`` and ``AMADEUS_CLIENT_SECRET`` are set, returns
      a memoised ``AmadeusFlightProvider`` (its OAuth token cache is
      internal and survives across requests).
    - Otherwise falls back to ``NullFlightProvider`` so unconfigured
      deployments fail closed with ``UNAVAILABLE`` and zero rows.
    """
    try:
        import os  # local import keeps module pure when reading env
        from app.services.flights_provider_duffel import (
            duffel_enabled_from_env,
            build_duffel_provider_from_env,
        )
        if not duffel_enabled_from_env():
            return _DEFAULT_PROVIDER
        env_key = (
            os.environ.get("DUFFEL_ACCESS_TOKEN", ""),
            os.environ.get("DUFFEL_BASE_URL", ""),
        )
        cached = _PROVIDER_CACHE.get(env_key)
        if cached is not None:
            return cached
        duffel = build_duffel_provider_from_env()
        if duffel is not None:
            _PROVIDER_CACHE[env_key] = duffel
            return duffel
    except Exception:
        # Adapter import / construction must never break the seam.
        pass
    return _DEFAULT_PROVIDER


__all__ = [
    "DefaultFlightProvider",
    "FlightProvider",
    "FlightProviderResult",
    "NullFlightProvider",
    "get_flight_provider",
    "reset_flight_provider_cache",
]


# Legacy alias for direct test imports.
DefaultFlightProvider = NullFlightProvider
