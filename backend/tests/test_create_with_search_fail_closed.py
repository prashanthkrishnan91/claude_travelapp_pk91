"""Fail-Closed UX v1 — /trips/create-with-search must not persist anything
when provider-backed flight + hotel search returns empty results.

Regression contract:
- response is HTTP 503 (provider unavailable)
- TripsService.create_trip is NOT called
- ItineraryService.ensure_trip_days is NOT called
- ItineraryService.create_trip_item is NOT called

Mirrors the conftest stubbing pattern used by
``test_product_surface_pruning_v1a.py`` so this test imports the route
without booting the full FastAPI stack.
"""
from __future__ import annotations

import os
import sys
import types
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

# ---- Heavy-stack stubs (mirror conftest) ----------------------------------

for _mod in ["fastapi", "supabase", "anthropic"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import fastapi as _fa  # noqa: E402

class _StubHTTPException(Exception):
    def __init__(self, status_code: int = 400, detail=None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail

_fa.HTTPException = _StubHTTPException


# Provide a real router stub so route decorators preserve the underlying
# function (default MagicMock decorators replace the function with another
# MagicMock, which makes the handler uncallable in unit tests).
class _IdentityRouter:
    def __init__(self, *args, **kwargs):
        pass

    def _identity(self, *args, **kwargs):
        def decorator(fn):
            return fn
        return decorator

    post = _identity
    get = _identity
    put = _identity
    patch = _identity
    delete = _identity

_fa.APIRouter = _IdentityRouter
_fa.status = MagicMock()
_fa.status.HTTP_201_CREATED = 201
_fa.status.HTTP_204_NO_CONTENT = 204
_fa.status.HTTP_404_NOT_FOUND = 404
_fa.status.HTTP_422_UNPROCESSABLE_ENTITY = 422
_fa.status.HTTP_503_SERVICE_UNAVAILABLE = 503

_core_path = os.path.join(os.path.dirname(__file__), "..", "app", "core")
_core_mod = sys.modules.get("app.core")
if _core_mod is None:
    _core_mod = types.ModuleType("app.core")
    sys.modules["app.core"] = _core_mod
if not hasattr(_core_mod, "__path__"):
    _core_mod.__path__ = [_core_path]

_deps_mod = sys.modules.get("app.core.deps")
if _deps_mod is None:
    _deps_mod = types.ModuleType("app.core.deps")
    sys.modules["app.core.deps"] = _deps_mod
if not hasattr(_deps_mod, "DB"):
    setattr(_deps_mod, "DB", object)
if not hasattr(_deps_mod, "CurrentUserID"):
    setattr(_deps_mod, "CurrentUserID", object)

# Bypass app/routes/__init__.py (which imports every route's heavy deps).
if "app.routes" not in sys.modules:
    _routes_pkg = types.ModuleType("app.routes")
    _routes_pkg.__path__ = [
        os.path.join(os.path.dirname(__file__), "..", "app", "routes")
    ]
    sys.modules["app.routes"] = _routes_pkg

# trips.py does ``from app.services import TripsService``, which would
# normally trigger ``app/services/__init__.py``. The conftest stubs that
# package as an empty namespace — populate it from the submodules directly
# so the real route module imports cleanly.
import app.services.trips as _trips_svc_mod  # noqa: E402
import app.services.itinerary as _itin_svc_mod  # noqa: E402
import app.services.search as _search_svc_mod  # noqa: E402

_services_pkg = sys.modules["app.services"]
setattr(_services_pkg, "TripsService", _trips_svc_mod.TripsService)
setattr(_services_pkg, "ItineraryService", _itin_svc_mod.ItineraryService)
setattr(_services_pkg, "SearchService", _search_svc_mod.SearchService)

from app.routes import trips as trips_route  # noqa: E402


# ---- Test ------------------------------------------------------------------


def test_create_with_search_fails_closed_when_provider_unavailable(monkeypatch):
    """When both flights and hotels return empty (provider unavailable / flag-on),
    the route must raise 503 and not create or persist anything."""

    # Force search service to return empty for every search call (flights,
    # round-trip pairs, hotels) — simulates BLOCK_LEGACY_PRODUCT_MOCK=1 or any
    # provider-unavailable condition.
    fake_search = MagicMock()
    fake_search.search_flights.return_value = []
    fake_search.search_round_trip_flights.return_value = []
    fake_search.search_hotels.return_value = []

    fake_trips = MagicMock()
    fake_itinerary = MagicMock()

    payload = trips_route.TripCreateWithSearch(
        origin_city="New York",
        destination_city="Paris",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
    )

    with patch.object(trips_route, "SearchService", return_value=fake_search), \
         patch.object(trips_route, "TripsService", return_value=fake_trips), \
         patch.object(trips_route, "ItineraryService", return_value=fake_itinerary):
        with pytest.raises(_StubHTTPException) as excinfo:
            trips_route.create_trip_with_search(
                payload, db=MagicMock(), user_id="user-123"
            )

    # 1. Honest 503 with structured provider_unavailable detail
    assert excinfo.value.status_code == 503
    detail = excinfo.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "provider_unavailable"
    assert "provider-backed" in detail.get("message", "").lower() or \
           "provider" in detail.get("message", "").lower()

    # 2. No trip was created
    fake_trips.create_trip.assert_not_called()

    # 3. No itinerary days were ensured
    fake_itinerary.ensure_trip_days.assert_not_called()

    # 4. No itinerary items were persisted
    fake_itinerary.create_trip_item.assert_not_called()


def test_create_with_search_invalid_destination_still_returns_422(monkeypatch):
    """Sanity: an unresolvable destination is a request-validation error (422),
    not a provider-unavailable error (503). This guards against the new
    fail-closed branch swallowing the existing 422 path."""

    fake_search = MagicMock()
    fake_trips = MagicMock()
    fake_itinerary = MagicMock()

    payload = trips_route.TripCreateWithSearch(
        origin_city="New York",
        destination_city="Nowhereville-XYZ-not-a-real-city",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
    )

    with patch.object(trips_route, "SearchService", return_value=fake_search), \
         patch.object(trips_route, "TripsService", return_value=fake_trips), \
         patch.object(trips_route, "ItineraryService", return_value=fake_itinerary):
        with pytest.raises(_StubHTTPException) as excinfo:
            trips_route.create_trip_with_search(
                payload, db=MagicMock(), user_id="user-123"
            )

    assert excinfo.value.status_code == 422
    fake_trips.create_trip.assert_not_called()
    fake_itinerary.create_trip_item.assert_not_called()
