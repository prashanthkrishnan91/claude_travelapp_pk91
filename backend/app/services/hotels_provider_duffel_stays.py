"""Duffel Stays hotel offer adapter — Slice 5C readiness scaffold.

DISABLED BY DEFAULT.

This module scaffolds the Duffel Stays provider behind the
``app.services.hotels_provider.HotelProvider`` seam.  It does NOT make
live API calls, does NOT fabricate rates, and does NOT return mock data.
When activated without credentials it returns ``UNAVAILABLE`` with no rows.

Activation requires:

1. ``DUFFEL_STAYS_API_KEY``   — Duffel Stays access token (required).
2. ``DUFFEL_STAYS_ENABLED``   — must be explicitly ``1``/``true``
                                (defaults to disabled).

The flag defaults to disabled so that deploying this module does not
accidentally activate a live provider.  Slice 5C will enable it once
Duffel Stays API access is confirmed and credentials are provisioned.

Do not add mock/fixture responses here.  If there is no real provider
credential, ``DuffelStaysProvider.search_hotels`` returns
``HotelSourceStatus.UNAVAILABLE`` and the UI shows its deferred state.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Optional

from app.contracts.hotels import HotelSourceStatus
from app.models.search import HotelSearchRequest
from app.services.hotels_provider import HotelProviderResult

logger = logging.getLogger(__name__)

_TRUTHY = {"1", "true", "yes", "on"}

# Env var names — no secrets stored here.
_ENV_API_KEY = "DUFFEL_STAYS_API_KEY"
_ENV_ENABLED = "DUFFEL_STAYS_ENABLED"

# Duffel Stays API base (not called until Slice 5C).
_DEFAULT_BASE_URL = "https://api.duffel.com"
_STAYS_PATH = "/stays/search"


def _truthy(value: Optional[str]) -> bool:
    return bool(value) and value.strip().lower() in _TRUTHY


def duffel_stays_enabled_from_env(env: Optional[Dict[str, str]] = None) -> bool:
    """True iff both the API key and the explicit opt-in flag are present.

    The flag defaults to disabled (``DUFFEL_STAYS_ENABLED`` absent or
    falsy) so the adapter never activates without explicit provisioning.
    """
    env = env if env is not None else os.environ  # type: ignore[assignment]
    api_key = (env.get(_ENV_API_KEY) or "").strip()
    if not api_key:
        return False
    return _truthy(env.get(_ENV_ENABLED))


class DuffelStaysProvider:
    """Duffel Stays hotel offer adapter.

    Currently a readiness scaffold: ``search_hotels`` returns
    ``UNAVAILABLE`` until Slice 5C implements the live offer request.
    The constructor requires a non-empty access token so the provider
    cannot be instantiated without credentials.

    Env-gated construction via
    ``build_duffel_stays_provider_from_env`` ensures disabled
    deployments never reach this class.
    """

    def __init__(
        self,
        *,
        access_token: str,
        base_url: str = _DEFAULT_BASE_URL,
    ) -> None:
        if not access_token:
            raise ValueError("DuffelStaysProvider requires a non-empty access token")
        self._access_token = access_token
        self._base_url = base_url.rstrip("/") or _DEFAULT_BASE_URL

    def search_hotels(self, req: HotelSearchRequest) -> HotelProviderResult:
        """Scaffold — returns UNAVAILABLE until Slice 5C live implementation.

        Slice 5C will replace this body with a real Duffel Stays offer
        request.  Until then the seam is wired but the provider is
        inert so the UI shows its deferred / unavailable state.
        """
        logger.info(
            "[duffel_stays.scaffold] search_hotels called but live "
            "implementation is deferred to Slice 5C; returning UNAVAILABLE. "
            "location=%s check_in=%s check_out=%s guests=%d",
            req.location, req.check_in, req.check_out, req.guests,
        )
        return HotelProviderResult(
            status=HotelSourceStatus.UNAVAILABLE,
            rows=[],
            reason=(
                "Duffel Stays live offer search not yet implemented; "
                "activate in Slice 5C once credentials are confirmed"
            ),
        )


def build_duffel_stays_provider_from_env(
    env: Optional[Dict[str, str]] = None,
) -> Optional[DuffelStaysProvider]:
    """Return a ``DuffelStaysProvider`` iff both the key and flag are set.

    Returns ``None`` (not an exception) when disabled so callers fall
    back to ``NullHotelProvider`` without noise.
    """
    env = env if env is not None else os.environ  # type: ignore[assignment]
    if not duffel_stays_enabled_from_env(env):
        return None
    api_key = (env.get(_ENV_API_KEY) or "").strip()
    if not api_key:
        return None
    return DuffelStaysProvider(access_token=api_key)


__all__ = [
    "DuffelStaysProvider",
    "build_duffel_stays_provider_from_env",
    "duffel_stays_enabled_from_env",
]
