"""Flights provider seam — Flights Product Contract v1.

The runtime seam the future provider-backed Flights v1 PR will plug into.
This module deliberately ships **no** real provider, **no** API key, and
**no** fabricated fallback rows.  Its only job is to define the interface
boundary so the next PR is a drop-in adapter, not a refactor of
``TripBuilder`` / ``OptimizeTripModal`` / ``/trips/create-with-search``.

Row type policy
---------------
``FlightProviderResult.rows`` accepts two row shapes:

- **Canonical (new adapters):** ``FlightItineraryOffer`` from
  ``app.contracts.flight_offer``.  Skyscanner, Ignav, and any future
  approved adapter MUST return this type.  Its invariants (positive price,
  no fabricated booking URLs, IATA code lengths, etc.) are enforced in its
  own ``__post_init__``.

- **Legacy (SearchService consumer layer):** ``FlightResult`` from
  ``app.models.search``.  This shape is used by the existing
  ``SearchService.search_flights`` / ``search_round_trip_flights`` /
  ``curate_flight_results`` stack that pre-dates the normalized offer
  contract.  ``FlightResult`` rows are validated via the legacy
  ``assert_persistable_flight`` predicate.  New provider adapters MUST NOT
  produce ``FlightResult`` rows; this path exists only to avoid a breaking
  change on the SearchService consumer while the promotion PR is pending.

Default binding (``DefaultFlightProvider``) is the ``NullFlightProvider``
which always returns ``UNAVAILABLE``.  The legacy ``_mock_flights`` helper
in ``backend/app/services/search.py`` is intentionally NOT wired into this
seam: it remains a quarantined legacy fixture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Protocol, Union

from app.contracts.flights import (
    FlightProviderUnavailable,
    FlightSourceStatus,
    assert_persistable_flight,
)
from app.contracts.flight_offer import FlightItineraryOffer
from app.models.search import FlightResult, FlightSearchRequest

# Canonical row type for new provider adapters.
# Legacy type (FlightResult) is accepted for backward compat with the
# SearchService consumer layer; it is not the canonical live-provider shape.
ProviderBoundRow = Union[FlightItineraryOffer, FlightResult]


@dataclass(frozen=True)
class FlightProviderResult:
    """Typed response for any flight provider adapter.

    Row contract:
    - **Canonical:** ``FlightItineraryOffer`` — new adapters (Skyscanner,
      Ignav) MUST use this.  Invariants enforced in ``FlightItineraryOffer``
      itself; no fabricated prices, no placeholder booking URLs.
    - **Legacy:** ``FlightResult`` — accepted for backward compat with the
      SearchService consumer layer (``curate_flight_results`` etc.) that
      pre-dates the normalized contract.  Validated via
      ``assert_persistable_flight``.  NOT the canonical live-provider shape.

    Structural invariants (enforced in ``__post_init__``):
    - ``rows`` MUST be empty whenever ``status`` is not ``OK``.
    - ``OK`` with zero rows is a contract bug; use ``EMPTY`` instead.
    - Adapters never raise on transport errors; translate to ``ERROR``.
    """

    status: FlightSourceStatus
    rows: List[ProviderBoundRow] = field(default_factory=list)
    reason: str = ""

    def __post_init__(self) -> None:
        if self.status is FlightSourceStatus.OK:
            if not self.rows:
                raise ValueError(
                    "FlightProviderResult(status=OK) must carry at least one "
                    "row; use FlightSourceStatus.EMPTY for zero-result queries"
                )
            for idx, row in enumerate(self.rows):
                if isinstance(row, FlightItineraryOffer):
                    # Canonical path: invariants already enforced in __post_init__.
                    pass
                elif isinstance(row, FlightResult):
                    # LEGACY path: validate via pre-contract persistability predicate.
                    try:
                        assert_persistable_flight(row)
                    except Exception as exc:
                        raise ValueError(
                            f"FlightProviderResult(status=OK).rows[{idx}] failed "
                            f"the Flights Product Contract v1: {exc}"
                        ) from exc
                else:
                    raise ValueError(
                        f"FlightProviderResult(status=OK).rows[{idx}] is not a "
                        f"FlightItineraryOffer (canonical) or FlightResult (legacy); "
                        f"got {type(row).__name__}"
                    )
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

    Flights v1 — registry-gated then env-gated.  Provider priority order:

    1. Duffel (``duffel_flights``) — active search-only provider.  LINK_OUT +
       ``production_allowed=True`` in the registry.  Gates:
       registry ``is_provider_active("duffel_flights")`` then
       ``DUFFEL_API_KEY`` + ``DUFFEL_FLIGHTS_ENABLED`` env vars.
       BOOKING DISABLED: never creates Duffel orders; v1 is search-only.

    2. Skyscanner (``skyscanner_flights``) — PENDING; access rejected; stays
       off even if env vars are present.

    3. Ignav (``ignav_flights``) — DISABLED; schedule trust not certified;
       must not serve visible flight cards.

    When no provider is active, falls back to ``NullFlightProvider``
    (``UNAVAILABLE``, zero rows — polished fail-closed state in UI).
    """
    from app.services.provider_registry import is_provider_active
    import os

    # ── 1. Duffel (active search-only provider) ──────────────────────────────
    try:
        from app.services.flights_provider_duffel import (
            duffel_enabled_from_env,
            build_duffel_provider_from_env,
        )
        if is_provider_active("duffel_flights"):
            if duffel_enabled_from_env():
                env_key = ("duffel", os.environ.get("DUFFEL_API_KEY", ""))
                cached = _PROVIDER_CACHE.get(env_key)
                if cached is not None:
                    return cached
                provider = build_duffel_provider_from_env()
                if provider is not None:
                    _PROVIDER_CACHE[env_key] = provider
                    return provider
    except Exception:
        pass

    # ── 2. Skyscanner (PENDING — stays off) ──────────────────────────────────
    try:
        from app.services.flights_provider_skyscanner import (
            skyscanner_enabled_from_env,
            build_skyscanner_provider_from_env,
        )
        if is_provider_active("skyscanner_flights"):
            if skyscanner_enabled_from_env():
                env_key = ("skyscanner", os.environ.get("SKYSCANNER_API_KEY", ""))
                cached = _PROVIDER_CACHE.get(env_key)
                if cached is not None:
                    return cached
                provider = build_skyscanner_provider_from_env()
                if provider is not None:
                    _PROVIDER_CACHE[env_key] = provider
                    return provider
    except Exception:
        pass

    # ── 3. Ignav (DISABLED — schedule trust not certified) ───────────────────
    try:
        from app.services.flights_provider_ignav import (
            ignav_enabled_from_env,
            build_ignav_provider_from_env,
        )
        if is_provider_active("ignav_flights"):
            if ignav_enabled_from_env():
                env_key = ("ignav", os.environ.get("IGNAV_API_KEY", ""))
                cached = _PROVIDER_CACHE.get(env_key)
                if cached is not None:
                    return cached
                provider = build_ignav_provider_from_env()
                if provider is not None:
                    _PROVIDER_CACHE[env_key] = provider
                    return provider
    except Exception:
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
