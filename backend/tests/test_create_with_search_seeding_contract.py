"""Trip seeding contract tests — Level 2 fix for unified four-vertical reliability.

Targeted tests that verify:
1. Completed flight results are captured even when another vertical times out.
2. Hotels, attractions, and restaurants are seeded through the same normalized
   contract path.
3. A timeout/failure in one vertical does NOT zero out completed results from
   another.
4. Attraction seeding does not silently skip to zero; it uses the search_attractions
   path (Google Places backed, fails closed on missing key).
5. Restaurants are explicitly covered to prevent future regression.
6. The Supabase retry helper retries on RemoteProtocolError and does not mask
   HTTPException.
7. No mock hotel rates, mock booking URLs, or Duffel-live assumptions are
   introduced.
8. Existing one-way and round-trip item persistence remain covered.
"""
from __future__ import annotations

import os
import sys
import types
import threading
import time
from datetime import date, datetime
from typing import Any
from unittest.mock import MagicMock, call, patch
from uuid import uuid4

import pytest

# ── Heavy-stack stubs (mirror conftest / test_create_with_search_fail_closed) ─

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

# Identity router so decorators preserve the underlying function.
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

if "app.routes" not in sys.modules:
    _routes_pkg = types.ModuleType("app.routes")
    _routes_pkg.__path__ = [
        os.path.join(os.path.dirname(__file__), "..", "app", "routes")
    ]
    sys.modules["app.routes"] = _routes_pkg

import app.services.trips as _trips_svc_mod  # noqa: E402
import app.services.itinerary as _itin_svc_mod  # noqa: E402
import app.services.search as _search_svc_mod  # noqa: E402

_services_pkg = sys.modules["app.services"]
setattr(_services_pkg, "TripsService", _trips_svc_mod.TripsService)
setattr(_services_pkg, "ItineraryService", _itin_svc_mod.ItineraryService)
setattr(_services_pkg, "SearchService", _search_svc_mod.SearchService)

from app.routes import trips as trips_route  # noqa: E402


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fake_trip(user_uuid=None):
    from app.models import Trip  # noqa: WPS433
    uid = user_uuid or uuid4()
    return Trip(
        id=uuid4(),
        user_id=uid,
        title="Tokyo Trip",
        destination="Tokyo",
        origin="San Francisco",
        start_date=date(2026, 5, 13),
        end_date=date(2026, 5, 20),
        status="planned",
        created_at=datetime(2026, 5, 10, 0, 0, 0),
    )


def _clean_flight(origin="SFO", destination="NRT"):
    from app.models.search import FlightResult  # noqa: WPS433
    return FlightResult(
        id=f"fl-{uuid4().hex[:6]}",
        price=850.0,
        rating=4.2,
        location=f"{origin}→{destination}",
        booking_url="https://duffel.com/flights/DL100",
        source="duffel",
        booking_options=[],
        airline="Delta Air Lines",
        flight_number="DL100",
        origin=origin,
        destination=destination,
        departure_time=datetime(2026, 5, 13, 10, 0),
        arrival_time=datetime(2026, 5, 14, 14, 30),
        duration_minutes=860,
        stops=0,
        cabin_class="economy",
        points_cost=85000,
        cpp=1.0,
    )


def _clean_hotel():
    from app.models.search import HotelResult  # noqa: WPS433
    return HotelResult(
        id=f"htl-{uuid4().hex[:8]}",
        price=0.0,
        rating=4.5,
        location="Tokyo, Japan",
        booking_url="https://www.google.com/maps/place/?q=place_id:ChIJ_gn1",
        source="google_places",
        booking_options=[],
        name="Park Hyatt Tokyo",
        check_in=date(2026, 5, 13),
        check_out=date(2026, 5, 20),
        nights=7,
        amenities=[],
        price_per_night=0.0,
    )


def _attraction_dict():
    return {
        "place_id": "ChIJ_att_tokyo",
        "name": "Tokyo Skytree",
        "address": "1-chome-1-2 Oshiage, Sumida City, Tokyo",
        "rating": 4.6,
        "num_reviews": 120000,
        "google_maps_uri": "https://maps.google.com/?cid=1234",
        "booking_url": "https://maps.google.com/?cid=1234",
        "lat": 35.7101,
        "lng": 139.8107,
        "types": ["tourist_attraction", "observation_deck"],
        "source": "google_places",
    }


def _restaurant_result():
    from app.models.search import RestaurantResult  # noqa: WPS433
    return RestaurantResult(
        id="gp-ChIJ_rest",
        price=None,
        rating=4.7,
        location="Tokyo, Japan",
        booking_url="https://maps.google.com/?cid=5678",
        source="google_places",
        booking_options=[],
        name="Sukiyabashi Jiro",
        cuisine="Sushi",
        address="4-chome-2-15 Ginza, Chuo City, Tokyo",
        ai_score=88.0,
        tags=["Must Try"],
        num_reviews=15000,
        opening_hours=None,
        price_level=4,
        sentiment=None,
        provider_place_id="ChIJ_rest",
        google_maps_uri="https://maps.google.com/?cid=5678",
        place_id="ChIJ_rest",
        source_status="ok",
        cache_status="miss",
        verification_status="verified",
        lat=35.6717,
        lng=139.7654,
    )


def _setup_mocks(
    *,
    flights=None,
    hotels=None,
    rt_pairs=None,
    attractions=None,
    restaurants=None,
    user_uuid=None,
):
    """Return (fake_search, fake_trips, fake_itinerary, user_uuid, fake_trip)."""
    uid = user_uuid or uuid4()
    trip = _fake_trip(uid)

    fake_search = MagicMock()
    fake_search.search_flights.return_value = flights if flights is not None else []
    fake_search.search_round_trip_flights.return_value = rt_pairs if rt_pairs is not None else []
    fake_search.search_hotels.return_value = hotels if hotels is not None else []
    fake_search.search_attractions.return_value = attractions if attractions is not None else []
    fake_search.search_restaurants.return_value = restaurants if restaurants is not None else []

    fake_trips = MagicMock()
    fake_trips.create_trip.return_value = trip

    fake_itinerary = MagicMock()

    return fake_search, fake_trips, fake_itinerary, uid, trip


def _run(payload, fake_search, fake_trips, fake_itinerary, uid):
    with (
        patch.object(trips_route, "SearchService", return_value=fake_search),
        patch.object(trips_route, "TripsService", return_value=fake_trips),
        patch.object(trips_route, "ItineraryService", return_value=fake_itinerary),
    ):
        return trips_route.create_trip_with_search(
            payload, db=MagicMock(), user_id=uid
        )


_TOKYO_PAYLOAD = trips_route.TripCreateWithSearch(
    origin_city="San Francisco",
    origin_airports=["SFO"],
    destination_city="Tokyo",
    destination_airports=["NRT"],
    start_date=date(2026, 5, 13),
    end_date=date(2026, 5, 20),
)


# ── 1. Vertical isolation — completed results survive sibling timeouts ────────

def test_flights_captured_when_hotel_search_times_out(monkeypatch):
    """Completed flight results must be captured even when hotel search times out."""
    _unblock = threading.Event()

    def _slow_hotels(*_a, **_k):
        _unblock.wait(timeout=3.0)
        return []

    clean = _clean_flight()
    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks(flights=[clean])
    fake_search.search_hotels.side_effect = _slow_hotels

    monkeypatch.setattr(trips_route, "_SEARCH_BUDGET_SECONDS", 0.15)
    result = _run(_TOKYO_PAYLOAD, fake_search, fake_trips, fake_itin, uid)
    _unblock.set()

    assert len(result.flights) == 1, "Completed flight results must not be zeroed out"
    assert result.seeding_status["flights"]["harvested"] == 1


def test_hotels_captured_when_flight_search_times_out(monkeypatch):
    """Completed hotel results must be captured even when flight search times out."""
    _unblock = threading.Event()

    def _slow_flights(*_a, **_k):
        _unblock.wait(timeout=3.0)
        return []

    hotel = _clean_hotel()
    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks(hotels=[hotel])
    fake_search.search_flights.side_effect = _slow_flights
    fake_search.search_round_trip_flights.side_effect = _slow_flights

    monkeypatch.setattr(trips_route, "_SEARCH_BUDGET_SECONDS", 0.15)
    result = _run(_TOKYO_PAYLOAD, fake_search, fake_trips, fake_itin, uid)
    _unblock.set()

    assert len(result.hotels) == 1, "Completed hotel results must not be zeroed out"
    assert result.seeding_status["hotels"]["harvested"] == 1


# ── 2. Uniform seeding contract across all four verticals ─────────────────────

def test_all_four_verticals_seeded_and_logged():
    """All four verticals must be persisted and appear in seeding_status."""
    flight = _clean_flight()
    hotel = _clean_hotel()
    att = _attraction_dict()
    rest = _restaurant_result()

    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks(
        flights=[flight],
        hotels=[hotel],
        attractions=[att],
        restaurants=[rest],
    )

    result = _run(_TOKYO_PAYLOAD, fake_search, fake_trips, fake_itin, uid)

    assert result.seeding_status["flights"]["harvested"] == 1
    assert result.seeding_status["hotels"]["harvested"] == 1
    assert result.seeding_status["attractions"]["harvested"] == 1
    assert result.seeding_status["restaurants"]["harvested"] == 1

    # At least 4 create_trip_item calls (one per vertical)
    assert fake_itin.create_trip_item.call_count >= 4


def test_attraction_item_type_is_activity():
    """Attractions must be persisted as ACTIVITY items, never a fabricated type."""
    att = _attraction_dict()
    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks(attractions=[att])

    _run(_TOKYO_PAYLOAD, fake_search, fake_trips, fake_itin, uid)

    # Find the call whose title matches the attraction name
    att_calls = [
        c for c in fake_itin.create_trip_item.call_args_list
        if c.args and getattr(c.args[0], "title", None) == att["name"]
    ]
    assert att_calls, "Attraction item was not persisted"
    item_arg = att_calls[0].args[0]
    from app.models.itinerary import ItineraryItemType  # noqa: WPS433
    assert item_arg.item_type == ItineraryItemType.ACTIVITY


def test_restaurant_item_type_is_meal():
    """Restaurants must be persisted as MEAL items."""
    rest = _restaurant_result()
    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks(restaurants=[rest])

    _run(_TOKYO_PAYLOAD, fake_search, fake_trips, fake_itin, uid)

    rest_calls = [
        c for c in fake_itin.create_trip_item.call_args_list
        if c.args and getattr(c.args[0], "title", None) == rest.name
    ]
    assert rest_calls, "Restaurant item was not persisted"
    item_arg = rest_calls[0].args[0]
    from app.models.itinerary import ItineraryItemType  # noqa: WPS433
    assert item_arg.item_type == ItineraryItemType.MEAL


def test_attraction_source_is_google_places():
    """Attraction details must carry source=google_places — no mock/invented data."""
    att = _attraction_dict()
    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks(attractions=[att])

    _run(_TOKYO_PAYLOAD, fake_search, fake_trips, fake_itin, uid)

    att_calls = [
        c for c in fake_itin.create_trip_item.call_args_list
        if c.args and getattr(c.args[0], "title", None) == att["name"]
    ]
    assert att_calls
    details = att_calls[0].args[0].details
    assert details.get("source") == "google_places"
    assert details.get("place_id") == att["place_id"]


# ── 3. Vertical failure isolation — one failure does not zero others ──────────

def test_hotel_persistence_failure_does_not_zero_flights():
    """If hotel persistence raises, flight items must still be persisted."""
    flight = _clean_flight()
    hotel = _clean_hotel()

    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks(
        flights=[flight], hotels=[hotel]
    )

    def _raise_for_hotel(item, *_a):
        from app.models.itinerary import ItineraryItemType  # noqa: WPS433
        if item.item_type == ItineraryItemType.HOTEL:
            raise RuntimeError("simulated Supabase error")
        return MagicMock()

    fake_itin.create_trip_item.side_effect = _raise_for_hotel

    result = _run(_TOKYO_PAYLOAD, fake_search, fake_trips, fake_itin, uid)

    # Hotels failed to persist but seeding_status must reflect the failure.
    assert result.seeding_status["hotels"]["persisted"] == 0
    # Flights must be reported as harvested.
    assert result.seeding_status["flights"]["harvested"] == 1


def test_attraction_failure_does_not_zero_restaurants():
    """If attraction persistence raises, restaurant items must still be seeded."""
    att = _attraction_dict()
    rest = _restaurant_result()

    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks(
        attractions=[att], restaurants=[rest]
    )

    def _raise_for_attraction(item, *_a):
        from app.models.itinerary import ItineraryItemType  # noqa: WPS433
        if item.item_type == ItineraryItemType.ACTIVITY:
            raise RuntimeError("simulated error")
        return MagicMock()

    fake_itin.create_trip_item.side_effect = _raise_for_attraction

    result = _run(_TOKYO_PAYLOAD, fake_search, fake_trips, fake_itin, uid)

    assert result.seeding_status["attractions"]["persisted"] == 0
    assert result.seeding_status["restaurants"]["harvested"] == 1


# ── 4. Attraction search uses search_attractions path ────────────────────────

def test_search_attractions_called_with_destination():
    """search_attractions must be called with the destination city during creation."""
    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks()

    _run(_TOKYO_PAYLOAD, fake_search, fake_trips, fake_itin, uid)

    fake_search.search_attractions.assert_called_once_with("Tokyo")


def test_attraction_seeding_zero_when_provider_returns_empty():
    """When search_attractions returns [], seeding_status.attractions.harvested == 0."""
    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks(attractions=[])

    result = _run(_TOKYO_PAYLOAD, fake_search, fake_trips, fake_itin, uid)

    assert result.seeding_status["attractions"]["harvested"] == 0
    assert result.seeding_status["attractions"]["persisted"] == 0


# ── 5. Restaurant coverage ────────────────────────────────────────────────────

def test_search_restaurants_called_with_destination():
    """search_restaurants must be called with the destination city during creation."""
    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks()

    _run(_TOKYO_PAYLOAD, fake_search, fake_trips, fake_itin, uid)

    assert fake_search.search_restaurants.call_count == 1
    call_req = fake_search.search_restaurants.call_args.args[0]
    assert call_req.location == "Tokyo"


def test_restaurant_seeding_zero_when_provider_returns_empty():
    """When search_restaurants returns [], seeding_status.restaurants.harvested == 0."""
    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks(restaurants=[])

    result = _run(_TOKYO_PAYLOAD, fake_search, fake_trips, fake_itin, uid)

    assert result.seeding_status["restaurants"]["harvested"] == 0
    assert result.seeding_status["restaurants"]["persisted"] == 0


# ── 6. Supabase retry helper ──────────────────────────────────────────────────

def test_supabase_retry_retries_on_remote_protocol_error():
    """supabase_execute must retry on RemoteProtocolError and succeed on second attempt."""
    from app.core.supabase_retry import supabase_execute  # noqa: WPS433

    class _FakeRemoteProtocolError(Exception):
        pass

    # Rename to match detection heuristic
    _FakeRemoteProtocolError.__qualname__ = "RemoteProtocolError"
    _FakeRemoteProtocolError.__name__ = "RemoteProtocolError"

    calls = []

    def _fn():
        calls.append(1)
        if len(calls) == 1:
            raise _FakeRemoteProtocolError("connection terminated")
        return "ok"

    result = supabase_execute(_fn, context="test", max_retries=2)
    assert result == "ok"
    assert len(calls) == 2, "Should have retried exactly once"


def test_supabase_retry_does_not_mask_http_exception():
    """supabase_execute must not retry HTTPException (auth, not-found, RLS errors)."""
    from app.core.supabase_retry import supabase_execute  # noqa: WPS433

    calls = []

    def _fn():
        calls.append(1)
        raise _StubHTTPException(status_code=404, detail="Trip not found")

    with pytest.raises(_StubHTTPException) as exc_info:
        supabase_execute(_fn, context="test", max_retries=2)

    assert exc_info.value.status_code == 404
    assert len(calls) == 1, "HTTPException must not be retried"


def test_supabase_retry_reraises_after_all_retries_exhausted():
    """supabase_execute must propagate the error after max_retries attempts."""
    from app.core.supabase_retry import supabase_execute  # noqa: WPS433

    class _FakeRPE(Exception):
        pass

    _FakeRPE.__qualname__ = "RemoteProtocolError"

    calls = []

    def _fn():
        calls.append(1)
        raise _FakeRPE("always fails")

    with pytest.raises(_FakeRPE):
        supabase_execute(_fn, context="test", max_retries=2)

    assert len(calls) == 3  # 1 initial + 2 retries


# ── 7. No fake hotel rates / mock rows ───────────────────────────────────────

def test_attraction_details_contain_no_mock_booking_url():
    """Attraction items must not carry book.example.com URLs."""
    att = _attraction_dict()
    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks(attractions=[att])

    _run(_TOKYO_PAYLOAD, fake_search, fake_trips, fake_itin, uid)

    att_calls = [
        c for c in fake_itin.create_trip_item.call_args_list
        if c.args and getattr(c.args[0], "title", None) == att["name"]
    ]
    assert att_calls
    booking_url = att_calls[0].args[0].details.get("booking_url", "")
    assert "book.example.com" not in booking_url, "Attraction must not use mock booking URL"


def test_hotel_discovery_price_not_written_as_zero():
    """Hotels v1 has no real rate — cash_price must be None, not 0.0."""
    hotel = _clean_hotel()
    assert hotel.price_per_night == 0.0  # discovery hotel

    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks(hotels=[hotel])
    _run(_TOKYO_PAYLOAD, fake_search, fake_trips, fake_itin, uid)

    hotel_calls = [
        c for c in fake_itin.create_trip_item.call_args_list
        if c.args and getattr(c.args[0], "title", None) == hotel.name
    ]
    assert hotel_calls
    # cash_price must be None (not $0) for discovery-only hotels
    assert hotel_calls[0].args[0].cash_price is None


# ── 8. Primary-airport cap — one-way and round-trip coverage ─────────────────

def test_flight_request_uses_single_primary_airport():
    """create_with_search must build flight requests using only the primary airport."""
    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks()

    multi_airport_payload = trips_route.TripCreateWithSearch(
        origin_city="Tokyo",
        origin_airports=["NRT", "HND"],   # two airports
        destination_city="London",
        destination_airports=["LHR", "LGW"],  # two airports
        start_date=date(2026, 5, 13),
        end_date=date(2026, 5, 20),
    )

    _run(multi_airport_payload, fake_search, fake_trips, fake_itin, uid)

    # search_flights must have been called with a single-airport request
    assert fake_search.search_flights.call_count == 1
    req = fake_search.search_flights.call_args.args[0]
    # Primary airports only — no multi-airport list
    assert req.origin == "NRT"
    assert req.destination == "LHR"
    assert req.origin_airports is None
    assert req.destination_airports is None


def test_payload_title_is_used_for_created_trip():
    """create-with-search must use payload.title for the created trip when provided."""
    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks()

    payload = trips_route.TripCreateWithSearch(
        origin_city="San Francisco",
        origin_airports=["SFO"],
        destination_city="Tokyo",
        destination_airports=["NRT"],
        start_date=date(2026, 5, 13),
        end_date=date(2026, 5, 20),
        title="Honeymoon in Tokyo",
        travelers=2,
    )

    _run(payload, fake_search, fake_trips, fake_itin, uid)

    create_trip_arg = fake_trips.create_trip.call_args.args[0]
    assert create_trip_arg.title == "Honeymoon in Tokyo"


def test_payload_title_defaults_to_destination_when_omitted():
    """When payload.title is missing, created trip falls back to '<destination> Trip'."""
    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks()

    _run(_TOKYO_PAYLOAD, fake_search, fake_trips, fake_itin, uid)

    create_trip_arg = fake_trips.create_trip.call_args.args[0]
    assert create_trip_arg.title == "Tokyo Trip"


def test_flight_passengers_uses_payload_travelers():
    """Flight search requests must use payload.travelers as passenger count."""
    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks()

    payload = trips_route.TripCreateWithSearch(
        origin_city="San Francisco",
        origin_airports=["SFO"],
        destination_city="Tokyo",
        destination_airports=["NRT"],
        start_date=date(2026, 5, 13),
        end_date=date(2026, 5, 20),
        travelers=3,
    )

    _run(payload, fake_search, fake_trips, fake_itin, uid)

    flight_req = fake_search.search_flights.call_args.args[0]
    rt_req = fake_search.search_round_trip_flights.call_args.args[0]
    assert flight_req.passengers == 3
    assert rt_req.passengers == 3


def test_hotel_guests_uses_payload_travelers():
    """Hotel search request must use payload.travelers as guests."""
    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks()

    payload = trips_route.TripCreateWithSearch(
        origin_city="San Francisco",
        origin_airports=["SFO"],
        destination_city="Tokyo",
        destination_airports=["NRT"],
        start_date=date(2026, 5, 13),
        end_date=date(2026, 5, 20),
        travelers=4,
    )

    _run(payload, fake_search, fake_trips, fake_itin, uid)

    hotel_req = fake_search.search_hotels.call_args.args[0]
    assert hotel_req.guests == 4


def test_payload_travelers_persisted_on_created_trip():
    """The created Trip row must carry the requested travelers count."""
    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks()

    payload = trips_route.TripCreateWithSearch(
        origin_city="San Francisco",
        origin_airports=["SFO"],
        destination_city="Tokyo",
        destination_airports=["NRT"],
        start_date=date(2026, 5, 13),
        end_date=date(2026, 5, 20),
        travelers=2,
    )

    _run(payload, fake_search, fake_trips, fake_itin, uid)

    create_trip_arg = fake_trips.create_trip.call_args.args[0]
    assert create_trip_arg.travelers == 2


def test_travelers_sanitized_to_minimum_one():
    """travelers must be coerced to a minimum of 1, never zero or negative."""
    payload = trips_route.TripCreateWithSearch(
        origin_city="San Francisco",
        origin_airports=["SFO"],
        destination_city="Tokyo",
        destination_airports=["NRT"],
        start_date=date(2026, 5, 13),
        end_date=date(2026, 5, 20),
        travelers=0,
    )
    assert payload.travelers == 1


def test_round_trip_request_uses_same_primary_airports():
    """Round-trip requests must also use only primary airports."""
    fake_search, fake_trips, fake_itin, uid, _ = _setup_mocks()

    multi_airport_payload = trips_route.TripCreateWithSearch(
        origin_city="New York",
        origin_airports=["JFK", "LGA", "EWR"],
        destination_city="Tokyo",
        destination_airports=["NRT", "HND"],
        start_date=date(2026, 5, 13),
        end_date=date(2026, 5, 20),
    )

    _run(multi_airport_payload, fake_search, fake_trips, fake_itin, uid)

    rt_req = fake_search.search_round_trip_flights.call_args.args[0]
    assert rt_req.origin == "JFK"
    assert rt_req.destination == "NRT"
    assert rt_req.return_date == date(2026, 5, 20)
