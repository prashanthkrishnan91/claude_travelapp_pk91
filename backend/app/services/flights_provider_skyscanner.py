"""Skyscanner Flights adapter shell — disabled-promotion-scaffold.

This module is the scaffold for the Skyscanner Live Prices adapter.  It
ships DISABLED: the adapter makes no live network calls, returns no rows,
and cannot be activated without:

  1. A ``skyscanner_flights`` entry in ``provider_registry.py`` with
     ``production_allowed=True`` and an active role.
  2. ``SKYSCANNER_API_KEY`` set in the backend environment (server-side only;
     never exposed as a NEXT_PUBLIC_ frontend variable).
  3. ``SKYSCANNER_FLIGHTS_ENABLED=1`` set in the backend environment.
  4. A real implementation of ``SkyscannerFlightProvider.search_flights``
     replacing the stub below.

Until all four conditions are met, ``build_skyscanner_provider_from_env``
returns ``None`` and ``get_flight_provider`` falls back to
``NullFlightProvider``.

No mock data, no fabricated prices, no placeholder booking URLs are
ever returned by this adapter — disabled or active.
"""

from __future__ import annotations

import os
from typing import Optional

from app.contracts.flights import FlightSourceStatus
from app.contracts.flight_offer import FlightAdapterDisabledResult
from app.services.flights_provider import FlightProvider, FlightProviderResult
from app.models.search import FlightSearchRequest


def skyscanner_enabled_from_env() -> bool:
    """True only when both the feature flag AND API key are present in env.

    The provider registry is the outer gate; this is the inner env gate.
    Both must pass before the adapter is considered active.
    """
    flag = os.environ.get("SKYSCANNER_FLIGHTS_ENABLED", "").strip()
    key = os.environ.get("SKYSCANNER_API_KEY", "").strip()
    return bool(flag and flag not in ("0", "false", "no") and key)


class SkyscannerFlightProvider:
    """Scaffold adapter for Skyscanner Live Prices.

    This class satisfies the ``FlightProvider`` protocol but contains no
    live implementation.  When called it returns
    ``FlightProviderResult(status=UNAVAILABLE, rows=[])`` — the same
    fail-closed response as ``NullFlightProvider``.

    The implementation stub exists here so the adapter interface is
    drop-in-ready: the next PR replaces the body of ``search_flights``
    with real Skyscanner Live Prices API calls without touching
    TripBuilder / OptimizeTripModal / the frontend seam.
    """

    def search_flights(self, req: FlightSearchRequest) -> FlightProviderResult:
        disabled = FlightAdapterDisabledResult(
            provider_id="skyscanner_flights",
            reason="Skyscanner Live Prices adapter is not yet implemented; scaffold only",
        )
        return FlightProviderResult(
            status=FlightSourceStatus.UNAVAILABLE,
            rows=[],
            reason=disabled.reason,
        )


def build_skyscanner_provider_from_env() -> Optional[FlightProvider]:
    """Factory: returns a ``SkyscannerFlightProvider`` only when fully enabled.

    Called by ``get_flight_provider()`` after the registry gate passes.
    Returns ``None`` when env vars are absent so the caller falls back to
    ``NullFlightProvider``.

    Note: even when this factory returns a ``SkyscannerFlightProvider`` instance
    today, ``search_flights`` still returns UNAVAILABLE because the live
    implementation is not yet written.  This will change in the promotion PR.
    """
    if not skyscanner_enabled_from_env():
        return None
    return SkyscannerFlightProvider()


__all__ = [
    "SkyscannerFlightProvider",
    "build_skyscanner_provider_from_env",
    "skyscanner_enabled_from_env",
]
