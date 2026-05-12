"""Ignav Flights adapter shell — disabled-promotion-scaffold.

Ignav is the provisional paid/self-serve backup flight provider candidate.
This module ships DISABLED: the adapter makes no live network calls, returns
no rows, and cannot be activated without:

  1. A ``ignav_flights`` entry in ``provider_registry.py`` with
     ``production_allowed=True`` and an active role (currently EVALUATION).
  2. ``IGNAV_API_KEY`` set in the backend environment (server-side only;
     never exposed as a NEXT_PUBLIC_ frontend variable).
  3. ``IGNAV_FLIGHTS_ENABLED=1`` set in the backend environment.
  4. Ignav passing the validation gate (see docs/product/DECISION_LOG.md).
  5. A real implementation of ``IgnavFlightProvider.search_flights``
     replacing the stub below.

Ignav must NOT be promoted to visible production behavior until it has
passed provider validation testing.  The evaluation/disabled status in the
registry enforces this.
"""

from __future__ import annotations

import os
from typing import Optional

from app.contracts.flights import FlightSourceStatus
from app.contracts.flight_offer import FlightAdapterDisabledResult
from app.services.flights_provider import FlightProvider, FlightProviderResult
from app.models.search import FlightSearchRequest


def ignav_enabled_from_env() -> bool:
    """True only when both the feature flag AND API key are present in env."""
    flag = os.environ.get("IGNAV_FLIGHTS_ENABLED", "").strip()
    key = os.environ.get("IGNAV_API_KEY", "").strip()
    return bool(flag and flag not in ("0", "false", "no") and key)


class IgnavFlightProvider:
    """Scaffold adapter for Ignav Flights (evaluation/backup candidate).

    Returns ``FlightProviderResult(status=UNAVAILABLE, rows=[])`` in all cases
    until the live implementation replaces the stub body of ``search_flights``.
    Must pass provider validation before promotion.
    """

    def search_flights(self, req: FlightSearchRequest) -> FlightProviderResult:
        disabled = FlightAdapterDisabledResult(
            provider_id="ignav_flights",
            reason=(
                "Ignav Flights adapter is not yet implemented; "
                "evaluation scaffold only — must pass validation before promotion"
            ),
        )
        return FlightProviderResult(
            status=FlightSourceStatus.UNAVAILABLE,
            rows=[],
            reason=disabled.reason,
        )


def build_ignav_provider_from_env() -> Optional[FlightProvider]:
    """Factory: returns an ``IgnavFlightProvider`` only when fully enabled.

    Returns ``None`` when env vars are absent.  Even when it returns an
    instance today, ``search_flights`` still returns UNAVAILABLE because the
    live implementation and validation are not yet complete.
    """
    if not ignav_enabled_from_env():
        return None
    return IgnavFlightProvider()


__all__ = [
    "IgnavFlightProvider",
    "build_ignav_provider_from_env",
    "ignav_enabled_from_env",
]
