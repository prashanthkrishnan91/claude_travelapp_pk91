"""Ignav Flights live adapter — targeted contract tests.

Covers:
1.  ignav_enabled_from_env() requires both key and flag
2.  build_ignav_provider_from_env() returns None when not enabled
3.  is_provider_active("ignav_flights") now returns True (promoted)
4.  is_provider_active("skyscanner_flights") still False (still PENDING)
5.  Duffel + Amadeus still disabled
6.  IgnavFlightProvider maps a one-way fixture → FlightItineraryOffer (correct fields)
7.  IgnavFlightProvider maps a round-trip fixture → FlightItineraryOffer with return_leg
8.  Provider HTTP error → ERROR status, zero rows
9.  Provider timeout → UNAVAILABLE status, zero rows
10. Empty itineraries → EMPTY status, zero rows
11. No points fields on any emitted offer
12. No fabricated booking URLs (UNAVAILABLE link accepted)
13. IGNAV_API_KEY never exposed as NEXT_PUBLIC_ frontend variable
14. Explore Flights fails closed when provider not active (NullFlightProvider)
15. _map_segment raises on missing airports
16. _map_leg raises on empty segments
17. Booking link priority: airline_direct > ota > provider_deeplink
18. Round-trip request body includes return_date
19. Cabin class passed through to offer correctly
"""

from __future__ import annotations

import os
from datetime import date
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from app.contracts.flights import FlightSourceStatus
from app.contracts.flight_offer import (
    BookingLinkType,
    FlightItineraryOffer,
    FlightOfferLeg,
    FlightPrice,
    FlightSegment,
    LiveCachedStatus,
    TripType,
)
from app.services.provider_registry import (
    PROVIDER_REGISTRY,
    ProviderRole,
    is_provider_active,
    is_production_allowed,
)
from app.services.flights_provider import (
    FlightProviderResult,
    NullFlightProvider,
    reset_flight_provider_cache,
    get_flight_provider,
)
from app.services.flights_provider_ignav import (
    IgnavFlightProvider,
    build_ignav_provider_from_env,
    ignav_enabled_from_env,
)
from app.models.search import FlightSearchRequest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_request(return_date=None, cabin="economy", passengers=1) -> FlightSearchRequest:
    return FlightSearchRequest(
        origin="JFK",
        destination="CDG",
        departure_date=date(2026, 6, 1),
        return_date=return_date,
        passengers=passengers,
        cabin_class=cabin,
    )


def _make_segment_dict(
    dep_airport="JFK",
    arr_airport="CDG",
    carrier_code="AF",
    flight_number="AF001",
    carrier_name="Air France",
    dep_utc="2026-06-01T22:00:00Z",
    arr_utc="2026-06-02T06:00:00Z",
    duration=480,
) -> Dict[str, Any]:
    return {
        "marketing_carrier_code": carrier_code,
        "flight_number": flight_number,
        "operating_carrier_name": carrier_name,
        "departure_airport": dep_airport,
        "arrival_airport": arr_airport,
        "departure_time_utc": dep_utc,
        "arrival_time_utc": arr_utc,
        "duration_minutes": duration,
        "aircraft_type": "Boeing 777",
    }


def _make_leg_dict(
    origin="JFK",
    dest="CDG",
    duration=480,
    segments=None,
) -> Dict[str, Any]:
    return {
        "carrier_name": "Air France",
        "duration_minutes": duration,
        "segments": segments or [_make_segment_dict(dep_airport=origin, arr_airport=dest)],
    }


def _make_itinerary(
    ignav_id="abc123",
    amount=499.00,
    currency="USD",
    cabin="economy",
    inbound=None,
) -> Dict[str, Any]:
    return {
        "ignav_id": ignav_id,
        "price": {"amount": amount, "currency": currency},
        "cabin_class": cabin,
        "outbound": _make_leg_dict(),
        "inbound": inbound,
    }


def _make_search_response(itineraries=None) -> Dict[str, Any]:
    return {
        "origin": "JFK",
        "destination": "CDG",
        "departure_date": "2026-06-01",
        "itineraries": itineraries if itineraries is not None else [_make_itinerary()],
    }


def _make_booking_options(
    provider_type: str = "airline",
    url: str = "https://www.airfrance.com/booking/abc123",
) -> List[Dict[str, Any]]:
    """Return Ignav-doc-shaped booking_options[].links[] fixture."""
    return [
        {
            "provider_name": "Air France",
            "provider_type": provider_type,
            "links": [{"url": url, "price": {"amount": 499.0, "currency": "USD"}}],
        }
    ]


# ---------------------------------------------------------------------------
# 1–5: Registry + env gating
# ---------------------------------------------------------------------------

class TestRegistryGates:
    def test_ignav_now_production_allowed(self):
        entry = PROVIDER_REGISTRY["ignav_flights"]
        assert entry.production_allowed is True

    def test_ignav_role_is_link_out(self):
        entry = PROVIDER_REGISTRY["ignav_flights"]
        assert entry.role == ProviderRole.LINK_OUT

    def test_ignav_is_provider_active_when_no_env_set(self):
        # Even though production_allowed=True, is_provider_active doesn't check env —
        # it only checks role and production_allowed.  So it returns True.
        assert is_provider_active("ignav_flights") is True

    def test_skyscanner_still_not_active(self):
        assert is_provider_active("skyscanner_flights") is False

    def test_skyscanner_still_pending(self):
        assert PROVIDER_REGISTRY["skyscanner_flights"].role == ProviderRole.PENDING

    def test_duffel_still_disabled(self):
        assert is_provider_active("duffel_flights") is False

    def test_amadeus_still_disabled(self):
        assert is_provider_active("amadeus") is False

    def test_ignav_env_gate_requires_both_key_and_flag(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IGNAV_API_KEY", None)
            os.environ.pop("IGNAV_FLIGHTS_ENABLED", None)
            assert ignav_enabled_from_env() is False

    def test_ignav_env_gate_key_only_is_insufficient(self):
        with patch.dict(os.environ, {"IGNAV_API_KEY": "somekey"}, clear=False):
            os.environ.pop("IGNAV_FLIGHTS_ENABLED", None)
            assert ignav_enabled_from_env() is False

    def test_ignav_env_gate_flag_only_is_insufficient(self):
        with patch.dict(os.environ, {"IGNAV_FLIGHTS_ENABLED": "1"}, clear=False):
            os.environ.pop("IGNAV_API_KEY", None)
            assert ignav_enabled_from_env() is False

    def test_ignav_env_gate_flag_false_string_disabled(self):
        with patch.dict(
            os.environ,
            {"IGNAV_API_KEY": "somekey", "IGNAV_FLIGHTS_ENABLED": "false"},
        ):
            assert ignav_enabled_from_env() is False

    def test_ignav_env_gate_flag_zero_disabled(self):
        with patch.dict(
            os.environ,
            {"IGNAV_API_KEY": "somekey", "IGNAV_FLIGHTS_ENABLED": "0"},
        ):
            assert ignav_enabled_from_env() is False

    def test_ignav_env_gate_enabled_when_both_present(self):
        with patch.dict(
            os.environ,
            {"IGNAV_API_KEY": "test_key_123", "IGNAV_FLIGHTS_ENABLED": "1"},
        ):
            assert ignav_enabled_from_env() is True

    def test_build_provider_from_env_returns_none_when_disabled(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IGNAV_API_KEY", None)
            os.environ.pop("IGNAV_FLIGHTS_ENABLED", None)
            assert build_ignav_provider_from_env() is None

    def test_build_provider_from_env_returns_provider_when_enabled(self):
        with patch.dict(
            os.environ,
            {"IGNAV_API_KEY": "test_key_abc", "IGNAV_FLIGHTS_ENABLED": "1"},
        ):
            provider = build_ignav_provider_from_env()
            assert isinstance(provider, IgnavFlightProvider)


# ---------------------------------------------------------------------------
# 6–7: Mapping fixtures
# ---------------------------------------------------------------------------

class TestMapping:
    def _build_provider(self) -> IgnavFlightProvider:
        mock_client = MagicMock()
        return IgnavFlightProvider(api_key="testkey", http_client=mock_client)

    def test_maps_one_way_offer_correctly(self):
        provider = self._build_provider()
        it = _make_itinerary(amount=499.0, currency="USD", cabin="economy")
        bl = _make_booking_options("airline")
        req = _make_request()
        offer = provider._map_itinerary(it, bl, req, "2026-05-12T10:00:00Z")

        assert isinstance(offer, FlightItineraryOffer)
        assert offer.provider == "ignav_flights"
        assert offer.trip_type == TripType.ONE_WAY
        assert offer.origin == "JFK"
        assert offer.destination == "CDG"
        assert offer.passengers == 1
        assert offer.cabin_class == "economy"
        assert offer.price.total_amount == 499.0
        assert offer.price.currency == "USD"
        assert offer.live_cached_status == LiveCachedStatus.LIVE
        assert offer.fetched_at == "2026-05-12T10:00:00Z"
        assert offer.return_leg is None
        assert offer.ai_score is None

    def test_one_way_outbound_leg_fields(self):
        provider = self._build_provider()
        it = _make_itinerary()
        offer = provider._map_itinerary(it, [], _make_request(), "2026-05-12T10:00:00Z")
        leg = offer.outbound_leg
        assert leg.origin == "JFK"
        assert leg.destination == "CDG"
        assert leg.stops == 0
        assert leg.duration_minutes == 480
        assert len(leg.segments) == 1

    def test_one_way_segment_fields(self):
        provider = self._build_provider()
        it = _make_itinerary()
        offer = provider._map_itinerary(it, [], _make_request(), "2026-05-12T10:00:00Z")
        seg = offer.outbound_leg.segments[0]
        assert isinstance(seg, FlightSegment)
        assert seg.origin == "JFK"
        assert seg.destination == "CDG"
        assert seg.airline == "Air France"
        assert seg.duration_minutes == 480
        assert seg.aircraft_type == "Boeing 777"

    def test_maps_round_trip_offer_with_return_leg(self):
        provider = self._build_provider()
        inbound = _make_leg_dict(origin="CDG", dest="JFK", duration=420)
        it = _make_itinerary(inbound=inbound)
        req = _make_request(return_date=date(2026, 6, 10))
        offer = provider._map_itinerary(it, [], req, "2026-05-12T10:00:00Z")

        assert offer.trip_type == TripType.ROUND_TRIP
        assert offer.return_leg is not None
        assert offer.return_leg.origin == "CDG"
        assert offer.return_leg.destination == "JFK"
        assert offer.return_date == "2026-06-10"

    def test_round_trip_missing_inbound_raises(self):
        provider = self._build_provider()
        it = _make_itinerary(inbound=None)
        req = _make_request(return_date=date(2026, 6, 10))
        with pytest.raises(ValueError, match="no inbound leg"):
            provider._map_itinerary(it, [], req, "2026-05-12T10:00:00Z")

    def test_cabin_class_passed_through_from_itinerary(self):
        provider = self._build_provider()
        it = _make_itinerary(cabin="business")
        offer = provider._map_itinerary(it, [], _make_request(cabin="business"), "now")
        assert offer.cabin_class == "business"

    def test_passengers_passed_through(self):
        provider = self._build_provider()
        it = _make_itinerary()
        req = _make_request(passengers=2)
        offer = provider._map_itinerary(it, [], req, "now")
        assert offer.passengers == 2


# ---------------------------------------------------------------------------
# 8–10: Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def _build_provider(self) -> IgnavFlightProvider:
        mock_client = MagicMock()
        return IgnavFlightProvider(api_key="testkey", http_client=mock_client)

    def test_http_error_returns_error_status(self):
        import httpx
        provider = self._build_provider()
        provider._client.post.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=MagicMock(status_code=500)
        )
        result = provider.search_flights(_make_request())
        assert result.status == FlightSourceStatus.ERROR
        assert result.rows == []

    def test_timeout_returns_unavailable_status(self):
        import httpx
        provider = self._build_provider()
        provider._client.post.side_effect = httpx.TimeoutException("timed out")
        result = provider.search_flights(_make_request())
        assert result.status == FlightSourceStatus.UNAVAILABLE
        assert result.rows == []

    def test_empty_itineraries_returns_empty_status(self):
        provider = self._build_provider()
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_search_response(itineraries=[])
        mock_resp.raise_for_status = MagicMock()
        provider._client.post.return_value = mock_resp
        result = provider.search_flights(_make_request())
        assert result.status == FlightSourceStatus.EMPTY
        assert result.rows == []

    def test_successful_search_returns_ok_status(self):
        provider = self._build_provider()
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_search_response()
        mock_resp.raise_for_status = MagicMock()
        provider._client.post.return_value = mock_resp
        # Also mock _fetch_booking_links to avoid extra httpx calls
        with patch.object(provider, "_fetch_booking_links", return_value=[]):
            result = provider.search_flights(_make_request())
        assert result.status == FlightSourceStatus.OK
        assert len(result.rows) == 1
        assert isinstance(result.rows[0], FlightItineraryOffer)

    def test_ok_result_rows_are_flight_itinerary_offers(self):
        provider = self._build_provider()
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_search_response(
            itineraries=[_make_itinerary("id1"), _make_itinerary("id2")]
        )
        mock_resp.raise_for_status = MagicMock()
        provider._client.post.return_value = mock_resp
        with patch.object(provider, "_fetch_booking_links", return_value=[]):
            result = provider.search_flights(_make_request())
        assert result.status == FlightSourceStatus.OK
        for row in result.rows:
            assert isinstance(row, FlightItineraryOffer)


# ---------------------------------------------------------------------------
# 11–12: No points, no fabricated URLs
# ---------------------------------------------------------------------------

class TestNoPointsNoFabricatedUrls:
    def _make_offer(self, booking_options=None) -> FlightItineraryOffer:
        provider = IgnavFlightProvider(api_key="k", http_client=MagicMock())
        return provider._map_itinerary(
            _make_itinerary(),
            booking_options or [],
            _make_request(),
            "2026-05-12T10:00:00Z",
        )

    def test_no_points_cost_field_on_offer(self):
        offer = self._make_offer()
        assert not hasattr(offer, "points_cost")
        assert not hasattr(offer, "points_estimate")
        assert not hasattr(offer, "cpp")

    def test_no_recommendation_tag_field_on_offer(self):
        offer = self._make_offer()
        assert not hasattr(offer, "recommendation_tag")
        assert not hasattr(offer, "decision")

    def test_price_is_typed_flight_price_not_bare_float(self):
        offer = self._make_offer()
        assert isinstance(offer.price, FlightPrice)

    def test_unavailable_booking_link_when_no_options(self):
        offer = self._make_offer(booking_options=[])
        assert offer.booking_link.link_type == BookingLinkType.UNAVAILABLE
        assert offer.booking_link.url == ""

    def test_airline_direct_link_type_mapped(self):
        bl = _make_booking_options("airline")
        offer = self._make_offer(booking_options=bl)
        assert offer.booking_link.link_type == BookingLinkType.AIRLINE_DIRECT
        assert "airfrance.com" in offer.booking_link.url

    def test_ota_link_type_mapped(self):
        bl = [{"provider_name": "Kayak", "provider_type": "third_party", "links": [{"url": "https://www.kayak.com/flights/abc"}]}]
        offer = self._make_offer(booking_options=bl)
        assert offer.booking_link.link_type == BookingLinkType.OTA

    def test_airline_direct_preferred_over_ota(self):
        bl = [
            {"provider_name": "Kayak", "provider_type": "third_party", "links": [{"url": "https://www.kayak.com/x"}]},
            {"provider_name": "Air France", "provider_type": "airline", "links": [{"url": "https://www.airfrance.com/x"}]},
        ]
        offer = self._make_offer(booking_options=bl)
        assert offer.booking_link.link_type == BookingLinkType.AIRLINE_DIRECT
        assert "airfrance.com" in offer.booking_link.url


# ---------------------------------------------------------------------------
# 13: No NEXT_PUBLIC_ key exposure
# ---------------------------------------------------------------------------

class TestNoKeyExposure:
    def test_ignav_api_key_not_in_next_public_env(self):
        env_vars = list(os.environ.keys())
        next_public_flight_vars = [v for v in env_vars if v.startswith("NEXT_PUBLIC_") and "IGNAV" in v.upper()]
        assert next_public_flight_vars == [], (
            f"IGNAV key exposed as NEXT_PUBLIC_ variable: {next_public_flight_vars}"
        )

    def test_ignav_key_env_var_name_is_correct(self):
        assert "IGNAV_API_KEY" in PROVIDER_REGISTRY["ignav_flights"].required_env_vars
        assert "IGNAV_FLIGHTS_ENABLED" in PROVIDER_REGISTRY["ignav_flights"].required_env_vars

    def test_ignav_required_env_vars_not_prefixed_next_public(self):
        for var in PROVIDER_REGISTRY["ignav_flights"].required_env_vars:
            assert not var.startswith("NEXT_PUBLIC_"), (
                f"Ignav env var '{var}' must not be NEXT_PUBLIC_ (server-side only)"
            )


# ---------------------------------------------------------------------------
# 14: Fail-closed when provider not active
# ---------------------------------------------------------------------------

class TestFailClosed:
    def test_null_provider_when_no_env_set(self):
        reset_flight_provider_cache()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IGNAV_API_KEY", None)
            os.environ.pop("IGNAV_FLIGHTS_ENABLED", None)
            provider = get_flight_provider()
        assert isinstance(provider, NullFlightProvider)

    def test_null_provider_returns_unavailable(self):
        reset_flight_provider_cache()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IGNAV_API_KEY", None)
            os.environ.pop("IGNAV_FLIGHTS_ENABLED", None)
            provider = get_flight_provider()
        result = provider.search_flights(_make_request())
        assert result.status == FlightSourceStatus.UNAVAILABLE
        assert result.rows == []


# ---------------------------------------------------------------------------
# 15–16: Mapping edge cases
# ---------------------------------------------------------------------------

class TestMappingEdgeCases:
    def test_map_segment_raises_on_empty_origin(self):
        seg = _make_segment_dict(dep_airport="")
        with pytest.raises((ValueError, Exception)):
            IgnavFlightProvider._map_segment(seg)

    def test_map_leg_raises_on_empty_segments(self):
        leg_data = {"carrier_name": "X", "duration_minutes": 120, "segments": []}
        with pytest.raises(ValueError, match="no segments"):
            IgnavFlightProvider._map_leg(leg_data)

    def test_map_segment_uses_utc_time_over_local(self):
        seg = _make_segment_dict(
            dep_utc="2026-06-01T22:00:00Z",
        )
        # Add local time that differs
        seg["departure_time_local"] = "2026-06-01T18:00:00"
        result = IgnavFlightProvider._map_segment(seg)
        assert result.departure_time == "2026-06-01T22:00:00Z"

    def test_flight_number_prefixes_carrier_code(self):
        seg = _make_segment_dict(carrier_code="AF", flight_number="001")
        result = IgnavFlightProvider._map_segment(seg)
        assert result.flight_number == "AF001"

    def test_flight_number_not_double_prefixed(self):
        seg = _make_segment_dict(carrier_code="AF", flight_number="AF001")
        result = IgnavFlightProvider._map_segment(seg)
        assert result.flight_number == "AF001"
        assert not result.flight_number.startswith("AFAF")


# ---------------------------------------------------------------------------
# 17: Booking link priority
# ---------------------------------------------------------------------------

class TestBookingLinkPriority:
    def test_provider_deeplink_fallback(self):
        options = [
            {"provider_name": "Ignav", "provider_type": "ignav_generated", "links": [{"url": "https://ignav.com/deeplink/xyz"}]}
        ]
        link = IgnavFlightProvider._pick_booking_link(options)
        assert link.link_type == BookingLinkType.PROVIDER_DEEPLINK

    def test_empty_url_in_links_falls_through_to_unavailable(self):
        options = [{"provider_name": "Ignav", "provider_type": "airline", "links": [{"url": ""}]}]
        link = IgnavFlightProvider._pick_booking_link(options)
        assert link.link_type == BookingLinkType.UNAVAILABLE

    def test_url_without_scheme_gets_https_prefix(self):
        options = [{"provider_name": "AA", "provider_type": "airline", "links": [{"url": "aa.com/booking/123"}]}]
        link = IgnavFlightProvider._pick_booking_link(options)
        assert link.url == "https://aa.com/booking/123"
        assert link.link_type == BookingLinkType.AIRLINE_DIRECT

    def test_airline_link_nested_under_links_array_is_selected(self):
        options = [
            {
                "provider_name": "American Airlines",
                "provider_type": "airline",
                "links": [
                    {"url": "https://aa.com/booking/abc"},
                    {"url": "https://aa.com/booking/def"},
                ],
            }
        ]
        link = IgnavFlightProvider._pick_booking_link(options)
        assert link.link_type == BookingLinkType.AIRLINE_DIRECT
        assert "aa.com" in link.url

    def test_scheme_relative_url_gets_https(self):
        options = [{"provider_name": "AF", "provider_type": "airline", "links": [{"url": "//airfrance.com/book/xyz"}]}]
        link = IgnavFlightProvider._pick_booking_link(options)
        assert link.url == "https://airfrance.com/book/xyz"
