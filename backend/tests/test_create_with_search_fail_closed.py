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


def test_create_with_search_creates_trip_when_providers_return_empty(monkeypatch):
    """When all providers return empty (timeout / unavailable), the trip must
    still be created so the user can manually build their itinerary.  No
    itinerary items are persisted since there are no provider results to save.

    This replaces the old all-empty → 503 behaviour that caused a ~40-second
    hang while Duffel searched many origin-destination pairs sequentially.
    """
    from app.models import Trip  # noqa: WPS433
    from datetime import datetime as _dt
    from uuid import uuid4 as _uuid4

    user_uuid = _uuid4()
    fake_trip = Trip(
        id=_uuid4(),
        user_id=user_uuid,
        title="Paris Trip",
        destination="Paris",
        origin="New York",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="planned",
        created_at=_dt(2026, 5, 8, 0, 0, 0),
    )

    fake_search = MagicMock()
    fake_search.search_flights.return_value = []
    fake_search.search_round_trip_flights.return_value = []
    fake_search.search_hotels.return_value = []

    fake_trips = MagicMock()
    fake_trips.create_trip.return_value = fake_trip

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
        result = trips_route.create_trip_with_search(
            payload, db=MagicMock(), user_id=user_uuid
        )

    # 1. Trip was created — user gets a usable (empty) trip
    fake_trips.create_trip.assert_called_once()
    fake_itinerary.ensure_trip_days.assert_called_once()

    # 2. No itinerary items (no provider results to persist)
    fake_itinerary.create_trip_item.assert_not_called()

    # 3. Response has empty flights/hotels/pairs
    assert result.flights == []
    assert result.hotels == []
    assert result.round_trip_pairs == []


def test_create_with_search_does_not_block_after_budget_expiry(monkeypatch):
    """Provider calls that exceed the budget must NOT block the route.

    This test catches the context-manager bug: `with ThreadPoolExecutor(...) as
    pool:` calls shutdown(wait=True) on exit, holding the route until every
    thread finishes regardless of the per-future timeout.

    We simulate three slow providers that block until released, set a tiny
    budget (50 ms), and assert the route returns well within 500 ms — far
    below the time the slow providers would take if we waited for them.
    """
    import threading as _threading
    import time as _time
    from app.models import Trip  # noqa: WPS433
    from datetime import datetime as _dt
    from uuid import uuid4 as _uuid4

    # Event the slow-provider threads wait on.  We set it *after* asserting
    # so threads can exit cleanly rather than lingering for the full wait.
    _unblock = _threading.Event()

    def _slow_search(*_args, **_kwargs):
        # Block until released or 3s safety timeout.
        _unblock.wait(timeout=3.0)
        return []

    fake_search = MagicMock()
    fake_search.search_flights.side_effect = _slow_search
    fake_search.search_round_trip_flights.side_effect = _slow_search
    fake_search.search_hotels.side_effect = _slow_search

    user_uuid = _uuid4()
    fake_trip = Trip(
        id=_uuid4(),
        user_id=user_uuid,
        title="Paris Trip",
        destination="Paris",
        origin="New York",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="planned",
        created_at=_dt(2026, 5, 8, 0, 0, 0),
    )
    fake_trips = MagicMock()
    fake_trips.create_trip.return_value = fake_trip
    fake_itinerary = MagicMock()

    payload = trips_route.TripCreateWithSearch(
        origin_city="New York",
        destination_city="Paris",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
    )

    # Patch budget to 50 ms so _futures_wait times out quickly.
    monkeypatch.setattr(trips_route, "_SEARCH_BUDGET_SECONDS", 0.05)

    t_start = _time.perf_counter()
    with patch.object(trips_route, "SearchService", return_value=fake_search), \
         patch.object(trips_route, "TripsService", return_value=fake_trips), \
         patch.object(trips_route, "ItineraryService", return_value=fake_itinerary):
        result = trips_route.create_trip_with_search(
            payload, db=MagicMock(), user_id=user_uuid
        )
    elapsed = _time.perf_counter() - t_start

    # Release background threads now that we have the result.
    _unblock.set()

    # With context-manager shutdown(wait=True) the route would block until all
    # slow threads finish (3s each).  With shutdown(wait=False) it returns
    # near the 50ms budget.  Allow generous headroom for CI scheduling jitter.
    assert elapsed < 0.5, (
        f"Route took {elapsed:.3f}s — executor.shutdown(wait=True) likely still blocking "
        "after budget expiry.  Fix: use shutdown(wait=False, cancel_futures=True)."
    )

    # Trip is created and provider results are all empty (timed out).
    fake_trips.create_trip.assert_called_once()
    assert result.flights == []
    assert result.round_trip_pairs == []
    assert result.hotels == []


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


# ---- Mock-derived persistence guard ----------------------------------------


def _make_flight(*, source: str, booking_url: str, booking_options=None):
    from app.models.search import BookingOption, FlightResult  # noqa: WPS433
    from datetime import datetime as _dt
    return FlightResult(
        id="f1",
        price=499.0,
        rating=4.5,
        location="JFK→CDG",
        booking_url=booking_url,
        source=source,
        booking_options=booking_options or [],
        airline="Test Air",
        flight_number="TA100",
        origin="JFK",
        destination="CDG",
        departure_time=_dt(2026, 6, 1, 9, 0),
        arrival_time=_dt(2026, 6, 1, 21, 0),
        duration_minutes=720,
        stops=0,
        cabin_class="economy",
    )


def _make_hotel(*, source: str, booking_url: str, booking_options=None):
    from app.models.search import HotelResult  # noqa: WPS433
    return HotelResult(
        id="h1",
        price=900.0,
        rating=4.6,
        location="Paris, FR",
        booking_url=booking_url,
        source=source,
        booking_options=booking_options or [],
        name="Test Hotel",
        check_in=date(2026, 6, 1),
        check_out=date(2026, 6, 7),
        nights=6,
        amenities=[],
        price_per_night=150.0,
    )


def test_create_with_search_does_not_persist_mock_derived_flights_via_canonical_helper():
    """The canonical flight helper cannot return mock-derived rows.

    ``FlightItineraryOffer`` / ``FlightBookingLink`` reject fabricated hosts at
    construction time, so the legacy ``_mock_flights`` row path is structurally
    unreachable from ``/trips/create-with-search``.  This test pins that
    invariant by feeding the legacy SearchService a mock row and asserting it
    is never reached from this route.
    """
    mock_flight = _make_flight(
        source="mock",
        booking_url="https://book.example.com/flights/aa/jfk/cdg",
    )
    fake_search = MagicMock()
    fake_search.search_flights.return_value = [mock_flight]
    fake_search.search_round_trip_flights.return_value = []
    fake_search.search_hotels.return_value = []

    from app.models import Trip  # noqa: WPS433
    from datetime import datetime as _dt
    from uuid import uuid4 as _uuid4

    user_uuid = _uuid4()
    fake_trip = Trip(
        id=_uuid4(),
        user_id=user_uuid,
        title="Paris Trip",
        destination="Paris",
        origin="New York",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="planned",
        created_at=_dt(2026, 5, 8, 0, 0, 0),
    )
    fake_trips = MagicMock()
    fake_trips.create_trip.return_value = fake_trip
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
        result = trips_route.create_trip_with_search(
            payload, db=MagicMock(), user_id=user_uuid
        )

    # SearchService.search_flights is never invoked from create-with-search.
    fake_search.search_flights.assert_not_called()
    fake_search.search_round_trip_flights.assert_not_called()
    # Trip is created (no longer 503 just because flights are 0).
    fake_trips.create_trip.assert_called_once()
    # No flight items persisted (NullFlightProvider returns UNAVAILABLE in tests).
    from app.models.itinerary import ItineraryItemType  # noqa: WPS433
    flight_calls = [
        c for c in fake_itinerary.create_trip_item.call_args_list
        if c.args and getattr(c.args[0], "item_type", None) == ItineraryItemType.FLIGHT
    ]
    assert flight_calls == []
    assert result.flights == []


def test_create_with_search_blocks_mock_hotels_even_when_non_empty(monkeypatch):
    """Symmetric guard: a non-empty hotel row carrying ``book.example.com``
    booking URL must also fail closed, even if ``source`` claims otherwise."""

    from app.models.search import BookingOption  # noqa: WPS433

    sneaky_hotel = _make_hotel(
        source="booking_com",  # claim a real provider
        booking_url="https://hotels.example.com/legit",  # primary URL clean
        booking_options=[
            BookingOption(
                provider="hotels_com",
                # ...but a deep link still leaks the mock host
                url="https://book.example.com/hotels/booking/test-hotel",
            ),
        ],
    )
    fake_search = MagicMock()
    fake_search.search_flights.return_value = []
    fake_search.search_round_trip_flights.return_value = []
    fake_search.search_hotels.return_value = [sneaky_hotel]

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

    assert excinfo.value.status_code == 503
    fake_trips.create_trip.assert_not_called()
    fake_itinerary.create_trip_item.assert_not_called()


def test_legacy_round_trip_pair_search_is_not_invoked_from_create_with_search():
    """Round-trip flight seeding goes through canonical FlightItineraryOffer.

    The legacy ``search_round_trip_flights`` path is intentionally bypassed
    because it could diverge from Explore Flights.  This test pins that.
    """
    fake_search = MagicMock()
    fake_search.search_flights.return_value = []
    fake_search.search_round_trip_flights.return_value = []
    fake_search.search_hotels.return_value = []

    from app.models import Trip  # noqa: WPS433
    from datetime import datetime as _dt
    from uuid import uuid4 as _uuid4

    user_uuid = _uuid4()
    fake_trip = Trip(
        id=_uuid4(), user_id=user_uuid, title="Paris Trip", destination="Paris",
        origin="New York", start_date=date(2026, 6, 1), end_date=date(2026, 6, 7),
        status="planned", created_at=_dt(2026, 5, 8, 0, 0, 0),
    )
    fake_trips = MagicMock()
    fake_trips.create_trip.return_value = fake_trip
    fake_itinerary = MagicMock()

    payload = trips_route.TripCreateWithSearch(
        origin_city="New York", destination_city="Paris",
        start_date=date(2026, 6, 1), end_date=date(2026, 6, 7),
    )

    with patch.object(trips_route, "SearchService", return_value=fake_search), \
         patch.object(trips_route, "TripsService", return_value=fake_trips), \
         patch.object(trips_route, "ItineraryService", return_value=fake_itinerary):
        trips_route.create_trip_with_search(
            payload, db=MagicMock(), user_id=user_uuid,
        )

    fake_search.search_round_trip_flights.assert_not_called()
    fake_search.search_flights.assert_not_called()


def test_create_with_search_allows_clean_provider_rows(monkeypatch):
    """Negative control: clean hotel rows pass the mock guard and persist.

    Flights now come from the canonical FlightProvider, not SearchService,
    so this test focuses on the hotel persistence path remaining intact.
    """
    clean_hotel = _make_hotel(
        source="booking_com",
        booking_url="https://www.booking.com/hotel/fr/test-hotel",
    )

    fake_search = MagicMock()
    fake_search.search_flights.return_value = []
    fake_search.search_round_trip_flights.return_value = []
    fake_search.search_hotels.return_value = [clean_hotel]

    from app.models import Trip  # noqa: WPS433
    from datetime import datetime as _dt
    from uuid import uuid4 as _uuid4

    user_uuid = _uuid4()
    fake_trip = Trip(
        id=_uuid4(),
        user_id=user_uuid,
        title="Paris Trip",
        destination="Paris",
        origin="New York",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        status="planned",
        created_at=_dt(2026, 5, 8, 0, 0, 0),
    )
    fake_trips = MagicMock()
    fake_trips.create_trip.return_value = fake_trip

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
        result = trips_route.create_trip_with_search(
            payload, db=MagicMock(), user_id=user_uuid
        )

    fake_trips.create_trip.assert_called_once()
    fake_itinerary.ensure_trip_days.assert_called_once()
    # Hotel persisted.
    assert fake_itinerary.create_trip_item.call_count >= 1
    assert any(h is clean_hotel for h in result.hotels)


# ---- Helper-level unit tests on the detector ------------------------------


def test_is_mock_flight_detects_source_marker():
    f = _make_flight(source="mock", booking_url="https://legit.example.com/x")
    assert trips_route._is_mock_flight(f) is True


def test_is_mock_flight_detects_book_example_in_primary_url():
    f = _make_flight(source="amadeus", booking_url="https://book.example.com/x")
    assert trips_route._is_mock_flight(f) is True


def test_is_mock_flight_detects_book_example_in_options():
    from app.models.search import BookingOption  # noqa: WPS433
    f = _make_flight(
        source="amadeus",
        booking_url="https://amadeus.example/x",
        booking_options=[BookingOption(provider="kayak", url="https://book.example.com/y")],
    )
    assert trips_route._is_mock_flight(f) is True


def test_is_mock_flight_passes_clean_provider_rows():
    f = _make_flight(source="amadeus", booking_url="https://amadeus.example/x")
    assert trips_route._is_mock_flight(f) is False
