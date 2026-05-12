"""Hotels provider seam — Hotels Product Contract v1.

Mirrors ``backend/app/services/flights_provider.py``: defines a typed
``HotelProviderResult`` so adapters can return rows + a health marker
without raising, and a ``NullHotelProvider`` that fails closed when no
real provider is configured.

The legacy ``_mock_hotels`` helper in ``backend/app/services/search.py``
is intentionally NOT wired into this seam: binding it here would
re-open the persistence hole that PR #295 closed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Protocol

from app.contracts.hotels import (
    HotelProviderUnavailable,
    HotelSourceStatus,
    assert_persistable_hotel,
)
from app.models.search import HotelResult, HotelSearchRequest


@dataclass(frozen=True)
class HotelProviderResult:
    """Typed response for any hotel provider adapter.

    Invariants (enforced in ``__post_init__``):

    - ``rows`` MUST be empty whenever ``status`` is not ``OK``.
    - When ``status == OK``, every row MUST satisfy
      ``app.contracts.hotels.is_persistable_hotel`` — mock/demo/sample
      sources, fabricated booking hosts, and rows missing required
      fields are rejected via ``assert_persistable_hotel``.
    - ``OK`` with zero rows is intentionally NOT allowed: callers should
      use ``EMPTY`` for the "valid query, no results" case.
    - Adapters never raise on transport / API errors; they translate
      to ``status = ERROR`` with a non-empty ``reason``.
    """

    status: HotelSourceStatus
    rows: List[HotelResult] = field(default_factory=list)
    reason: str = ""

    def __post_init__(self) -> None:
        if self.status is HotelSourceStatus.OK:
            if not self.rows:
                raise ValueError(
                    "HotelProviderResult(status=OK) must carry at least one "
                    "row; use HotelSourceStatus.EMPTY for zero-result queries"
                )
            for idx, row in enumerate(self.rows):
                try:
                    assert_persistable_hotel(row)
                except Exception as exc:
                    raise ValueError(
                        f"HotelProviderResult(status=OK).rows[{idx}] failed "
                        f"the Hotels Product Contract v1: {exc}"
                    ) from exc
        else:
            if self.rows:
                raise ValueError(
                    f"HotelProviderResult(status={self.status.value}) must "
                    f"carry zero rows; got {len(self.rows)}"
                )


class HotelProvider(Protocol):
    """Adapter interface every Hotels v1 provider must satisfy.

    Implementations live alongside this module (e.g.
    ``hotels_provider_google_places.py``) and must:

    - take a fully-formed ``HotelSearchRequest`` (no string parsing);
    - never call out to a fixture or fabricate data on failure;
    - never raise — translate every failure to
      ``HotelProviderResult(status=ERROR, ...)``.
    """

    def search_hotels(self, req: HotelSearchRequest) -> HotelProviderResult: ...


class NullHotelProvider:
    """Default provider — always reports ``UNAVAILABLE`` with no rows."""

    def search_hotels(self, req: HotelSearchRequest) -> HotelProviderResult:
        return HotelProviderResult(
            status=HotelSourceStatus.UNAVAILABLE,
            rows=[],
            reason="no hotel provider configured",
        )

    def unavailable(self) -> HotelProviderUnavailable:
        return HotelProviderUnavailable(
            status=HotelSourceStatus.UNAVAILABLE,
            reason="no hotel provider configured",
        )


_DEFAULT_PROVIDER: HotelProvider = NullHotelProvider()

_PROVIDER_CACHE: dict = {}


def reset_hotel_provider_cache() -> None:
    """Clear the memoised provider — used by tests that monkeypatch env."""
    _PROVIDER_CACHE.clear()


def get_hotel_provider() -> HotelProvider:
    """Return the active ``HotelProvider``.

    Hotels v1 — registry-gated then env-gated:

    - Provider Registry v1 is the outer gate: ``google_places`` must be
      ``production_allowed`` and not ``DISABLED``/``QUARANTINED`` in
      ``app.services.provider_registry`` before the adapter is attempted.
    - When the registry allows it AND ``GOOGLE_PLACES_API_KEY`` is set AND
      ``GOOGLE_HOTELS_ENABLED`` is truthy, returns a memoised
      ``GooglePlacesHotelProvider``.
    - Otherwise falls back to ``NullHotelProvider`` so unconfigured
      deployments fail closed with ``UNAVAILABLE`` and zero rows.
    """
    try:
        import os  # local import keeps module pure when reading env
        from app.services.provider_registry import is_provider_active
        from app.services.hotels_provider_google_places import (
            build_google_places_hotel_provider_from_env,
            google_places_hotels_enabled_from_env,
        )
        # Registry gate: Google Places must be approved in Provider Policy v1.
        if not is_provider_active("google_places"):
            return _DEFAULT_PROVIDER
        if not google_places_hotels_enabled_from_env():
            return _DEFAULT_PROVIDER
        env_key = (
            os.environ.get("GOOGLE_PLACES_API_KEY", ""),
            os.environ.get("GOOGLE_HOTELS_ENABLED", ""),
        )
        cached = _PROVIDER_CACHE.get(env_key)
        if cached is not None:
            return cached
        provider = build_google_places_hotel_provider_from_env()
        if provider is not None:
            _PROVIDER_CACHE[env_key] = provider
            return provider
    except Exception:
        # Adapter import / construction must never break the seam.
        pass
    return _DEFAULT_PROVIDER


__all__ = [
    "DefaultHotelProvider",
    "HotelProvider",
    "HotelProviderResult",
    "NullHotelProvider",
    "get_hotel_provider",
    "reset_hotel_provider_cache",
]


# Legacy alias for direct test imports.
DefaultHotelProvider = NullHotelProvider
