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
        with patch.object(provider, "_fetch_booking_links", return_value=[]):
            with patch.dict(os.environ, {"IGNAV_SCHEDULE_TRUST_CERTIFIED": "1"}):
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
            with patch.dict(os.environ, {"IGNAV_SCHEDULE_TRUST_CERTIFIED": "1"}):
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

    def test_map_segment_uses_local_time_over_utc(self):
        # Local is preferred for display correctness (airline departure boards show local)
        seg = _make_segment_dict(
            dep_utc="2026-06-01T22:00:00Z",
        )
        seg["departure_time_local"] = "2026-06-01T15:00:00"
        result = IgnavFlightProvider._map_segment(seg)
        assert result.departure_time == "2026-06-01T15:00:00"

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


# ---------------------------------------------------------------------------
# 18: Trust gate — _validate_itinerary_raw
# ---------------------------------------------------------------------------

def _make_sea_lax_request() -> FlightSearchRequest:
    return FlightSearchRequest(
        origin="SEA",
        destination="LAX",
        departure_date=date(2026, 6, 17),
        passengers=1,
        cabin_class="economy",
    )


def _make_sea_lax_rt_request() -> FlightSearchRequest:
    return FlightSearchRequest(
        origin="SEA",
        destination="LAX",
        departure_date=date(2026, 6, 17),
        return_date=date(2026, 6, 24),
        passengers=1,
        cabin_class="economy",
    )


def _make_lax_sea_inbound(
    dep_airport: str = "LAX",
    arr_airport: str = "SEA",
    dep_local: str = "2026-06-24T14:00:00",
    dep_utc: str = None,
    extra_segments: list = None,
) -> Dict[str, Any]:
    """Inbound leg dict for LAX→SEA return flight."""
    seg = {
        "marketing_carrier_code": "AS",
        "flight_number": "AS202",
        "operating_carrier_name": "Alaska Airlines",
        "departure_airport": dep_airport,
        "arrival_airport": arr_airport,
        "departure_time_local": dep_local,
        "arrival_time_local": "2026-06-24T16:30:00",
        "duration_minutes": 150,
    }
    if dep_utc is not None:
        seg["departure_time_utc"] = dep_utc
    segs = [seg] + (extra_segments or [])
    return {"duration_minutes": 150, "segments": segs}


def _make_sea_lax_rt_itinerary(
    inbound: Dict[str, Any] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Round-trip SEA↔LAX itinerary fixture."""
    it = _make_sea_lax_itinerary(**kwargs)
    it["inbound"] = inbound if inbound is not None else _make_lax_sea_inbound()
    return it


def _make_sea_lax_itinerary(
    dep_airport="SEA",
    arr_airport="LAX",
    dep_local="2026-06-17T08:00:00",
    dep_utc=None,
    extra_segments=None,
) -> Dict[str, Any]:
    """Build a minimal Ignav-shaped itinerary with configurable route/date."""
    seg = {
        "marketing_carrier_code": "AS",
        "flight_number": "AS101",
        "operating_carrier_name": "Alaska Airlines",
        "departure_airport": dep_airport,
        "arrival_airport": arr_airport,
        "departure_time_local": dep_local,
        "arrival_time_local": "2026-06-17T10:30:00",
        "duration_minutes": 150,
    }
    if dep_utc is not None:
        seg["departure_time_utc"] = dep_utc
    segments = [seg] + (extra_segments or [])
    return {
        "ignav_id": "sea_lax_abc123",
        "price": {"amount": 179.0, "currency": "USD"},
        "cabin_class": "economy",
        "outbound": {"duration_minutes": 150, "segments": segments},
    }


class TestTrustGate:
    """Covers _validate_itinerary_raw + search_flights integration with the gate."""

    # --- Unit: _validate_itinerary_raw ---

    def test_valid_sea_lax_offer_passes(self):
        req = _make_sea_lax_request()
        it = _make_sea_lax_itinerary()
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is True, f"Expected pass, got rejection: {reason}"

    def test_wrong_origin_is_rejected(self):
        req = _make_sea_lax_request()
        it = _make_sea_lax_itinerary(dep_airport="PDX")  # Portland, not SEA
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is False
        assert "origin mismatch" in reason
        assert "PDX" in reason

    def test_wrong_destination_is_rejected(self):
        req = _make_sea_lax_request()
        it = _make_sea_lax_itinerary(arr_airport="SFO")  # wrong route
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is False
        assert "dest mismatch" in reason
        assert "SFO" in reason

    def test_wrong_departure_date_rejected(self):
        req = _make_sea_lax_request()
        # Local date is June 16, but request is for June 17
        it = _make_sea_lax_itinerary(dep_local="2026-06-16T23:59:00")
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is False
        assert "date mismatch" in reason
        assert "2026-06-16" in reason

    def test_local_time_preferred_over_utc_for_date(self):
        req = _make_sea_lax_request()
        # Local date = June 17 (correct), UTC date = June 18 (due to UTC+offset)
        it = _make_sea_lax_itinerary(
            dep_local="2026-06-17T23:30:00",  # June 17 local — correct
            dep_utc="2026-06-18T06:30:00Z",   # June 18 UTC — would wrongly fail
        )
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is True, f"Local date should be used; rejection: {reason}"

    def test_broken_segment_chain_rejected(self):
        req = _make_sea_lax_request()
        # Two-segment itinerary where SEA→ORD and JFK→LAX (gap at ORD/JFK)
        extra = {
            "marketing_carrier_code": "AA",
            "flight_number": "AA456",
            "operating_carrier_name": "American",
            "departure_airport": "JFK",   # doesn't connect to ORD
            "arrival_airport": "LAX",
            "departure_time_local": "2026-06-17T14:00:00",
            "arrival_time_local": "2026-06-17T17:00:00",
            "duration_minutes": 180,
        }
        it = _make_sea_lax_itinerary(
            dep_airport="SEA",
            arr_airport="ORD",  # last segment of first leg, doesn't match
            extra_segments=[extra],
        )
        # With extra_segments, arr_airport of the itinerary is LAX (last segment),
        # but chain is broken: SEA→ORD then JFK→LAX
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is False
        assert "chain" in reason.lower() or "mismatch" in reason.lower()

    def test_no_segments_rejected(self):
        req = _make_sea_lax_request()
        it = _make_sea_lax_itinerary()
        it["outbound"]["segments"] = []
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is False
        assert "no segments" in reason

    # --- Integration: search_flights applies the gate ---

    def _build_provider(self) -> IgnavFlightProvider:
        return IgnavFlightProvider(api_key="testkey", http_client=MagicMock())

    def test_all_invalid_offers_return_unavailable(self):
        provider = self._build_provider()
        req = _make_sea_lax_request()
        # Ignav returns two itineraries with wrong routes
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "itineraries": [
                _make_sea_lax_itinerary(dep_airport="SFO", arr_airport="LAX"),  # wrong origin
                _make_sea_lax_itinerary(dep_airport="SEA", arr_airport="SFO"),  # wrong dest
            ]
        }
        provider._client.post.return_value = mock_resp
        result = provider.search_flights(req)
        assert result.status == FlightSourceStatus.UNAVAILABLE
        assert result.rows == []
        assert "validation" in (result.reason or "").lower()

    def test_valid_offers_pass_through(self):
        provider = self._build_provider()
        req = _make_sea_lax_request()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "itineraries": [_make_sea_lax_itinerary()]
        }
        provider._client.post.return_value = mock_resp
        with patch.object(provider, "_fetch_booking_links", return_value=[]):
            with patch.dict(os.environ, {"IGNAV_SCHEDULE_TRUST_CERTIFIED": "1"}):
                result = provider.search_flights(req)
        assert result.status == FlightSourceStatus.OK
        assert len(result.rows) == 1
        offer = result.rows[0]
        assert isinstance(offer, FlightItineraryOffer)
        assert offer.outbound_leg.segments[0].origin == "SEA"
        assert offer.outbound_leg.segments[0].destination == "LAX"

    def test_mixed_valid_invalid_returns_only_valid(self):
        provider = self._build_provider()
        req = _make_sea_lax_request()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "itineraries": [
                _make_sea_lax_itinerary(dep_airport="PDX"),  # invalid: wrong origin
                _make_sea_lax_itinerary(),                   # valid
            ]
        }
        provider._client.post.return_value = mock_resp
        with patch.object(provider, "_fetch_booking_links", return_value=[]):
            with patch.dict(os.environ, {"IGNAV_SCHEDULE_TRUST_CERTIFIED": "1"}):
                result = provider.search_flights(req)
        assert result.status == FlightSourceStatus.OK
        assert len(result.rows) == 1

    def test_missing_ignav_id_does_not_crash_booking_links(self):
        provider = self._build_provider()
        req = _make_sea_lax_request()
        it = _make_sea_lax_itinerary()
        del it["ignav_id"]  # missing ignav_id — should not crash; booking link unavailable
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"itineraries": [it]}
        provider._client.post.return_value = mock_resp
        with patch.dict(os.environ, {"IGNAV_SCHEDULE_TRUST_CERTIFIED": "1"}):
            result = provider.search_flights(req)
        assert result.status == FlightSourceStatus.OK
        assert result.rows[0].booking_link.link_type == BookingLinkType.UNAVAILABLE

    def test_missing_departure_time_rejected(self):
        req = _make_sea_lax_request()
        it = _make_sea_lax_itinerary(dep_local=None)  # dep_utc also absent (fixture default)
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is False
        assert "missing" in reason.lower()

    # --- Round-trip inbound validation ---

    def test_valid_round_trip_passes(self):
        req = _make_sea_lax_rt_request()
        it = _make_sea_lax_rt_itinerary()
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is True, f"Expected pass, got rejection: {reason}"

    def test_missing_inbound_rejected_for_round_trip(self):
        req = _make_sea_lax_rt_request()
        it = _make_sea_lax_itinerary()  # one-way fixture, no inbound key
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is False
        assert "inbound" in reason.lower()

    def test_inbound_wrong_route_rejected(self):
        req = _make_sea_lax_rt_request()
        # Inbound departs from SFO instead of LAX
        it = _make_sea_lax_rt_itinerary(inbound=_make_lax_sea_inbound(dep_airport="SFO"))
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is False
        assert "inbound origin mismatch" in reason
        assert "SFO" in reason

    def test_inbound_wrong_return_date_rejected(self):
        req = _make_sea_lax_rt_request()
        # Inbound departs June 23, but return_date is June 24
        it = _make_sea_lax_rt_itinerary(inbound=_make_lax_sea_inbound(dep_local="2026-06-23T14:00:00"))
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is False
        assert "inbound date mismatch" in reason
        assert "2026-06-23" in reason

    def test_inbound_broken_chain_rejected(self):
        req = _make_sea_lax_rt_request()
        # Two-segment inbound: LAX→ORD then JFK→SEA — ORD/JFK gap
        extra = {
            "marketing_carrier_code": "AA",
            "flight_number": "AA789",
            "operating_carrier_name": "American",
            "departure_airport": "JFK",  # doesn't connect from ORD
            "arrival_airport": "SEA",
            "departure_time_local": "2026-06-24T18:00:00",
            "arrival_time_local": "2026-06-24T20:30:00",
            "duration_minutes": 150,
        }
        it = _make_sea_lax_rt_itinerary(
            inbound=_make_lax_sea_inbound(arr_airport="ORD", extra_segments=[extra])
        )
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is False
        assert "inbound segment chain broken" in reason


# ---------------------------------------------------------------------------
# 19: Booking-link payload omits adults
# ---------------------------------------------------------------------------

class TestBookingLinkPayload:
    """booking-link ignav_id lookup must not include adults or market fields."""

    def _build_provider(self) -> IgnavFlightProvider:
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"booking_options": []}
        mock_client.post.return_value = mock_resp
        return IgnavFlightProvider(api_key="testkey", http_client=mock_client)

    def test_booking_link_payload_omits_adults(self):
        provider = self._build_provider()
        provider._fetch_booking_links("test-ignav-id-abc")
        _, kwargs = provider._client.post.call_args
        body = kwargs.get("json", {})
        assert "adults" not in body, (
            f"booking-link request must not contain 'adults'; got keys: {list(body.keys())}"
        )

    def test_booking_link_payload_includes_ignav_id(self):
        provider = self._build_provider()
        provider._fetch_booking_links("my-ignav-id-xyz")
        _, kwargs = provider._client.post.call_args
        body = kwargs.get("json", {})
        assert body.get("ignav_id") == "my-ignav-id-xyz"

    def test_booking_link_payload_has_no_extra_fields(self):
        provider = self._build_provider()
        provider._fetch_booking_links("abc123")
        _, kwargs = provider._client.post.call_args
        body = kwargs.get("json", {})
        assert set(body.keys()) == {"ignav_id"}, (
            f"booking-link body should only contain 'ignav_id'; got {set(body.keys())}"
        )

    def test_search_flights_booking_link_fetch_omits_adults(self):
        """Integration: search_flights parallel booking-link calls omit adults."""
        provider = IgnavFlightProvider(api_key="testkey", http_client=MagicMock())
        req = _make_sea_lax_request()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"itineraries": [_make_sea_lax_itinerary()]}
        provider._client.post.return_value = mock_resp

        mock_bl = MagicMock(return_value=[])
        with patch.object(provider, "_fetch_booking_links", mock_bl):
            with patch.dict(os.environ, {"IGNAV_SCHEDULE_TRUST_CERTIFIED": "1"}):
                result = provider.search_flights(req)
            assert result.status == FlightSourceStatus.OK
            # Verify each call used only ignav_id — no adults arg
            for call in mock_bl.call_args_list:
                args, kwargs = call
                assert len(args) == 1, "only ignav_id positional arg expected"
                assert "adults" not in kwargs


# ---------------------------------------------------------------------------
# 20: Per-segment field validation (_validate_segment_fields)
# ---------------------------------------------------------------------------

def _make_valid_segment(
    dep="SEA",
    arr="LAX",
    carrier_code="AS",
    flight_num="101",
    dep_local="2026-06-17T08:00:00",
    arr_local="2026-06-17T10:30:00",
    duration=150,
) -> Dict[str, Any]:
    return {
        "marketing_carrier_code": carrier_code,
        "flight_number": flight_num,
        "operating_carrier_name": "Alaska Airlines",
        "departure_airport": dep,
        "arrival_airport": arr,
        "departure_time_local": dep_local,
        "arrival_time_local": arr_local,
        "duration_minutes": duration,
    }


class TestSegmentFieldValidation:
    """Unit tests for _validate_segment_fields."""

    def test_valid_segment_passes(self):
        seg = _make_valid_segment()
        ok, reason = IgnavFlightProvider._validate_segment_fields(seg, 0, "outbound")
        assert ok is True, f"expected pass, got: {reason}"

    def test_missing_carrier_code_and_flight_number_rejected(self):
        seg = _make_valid_segment(carrier_code="", flight_num="")
        ok, reason = IgnavFlightProvider._validate_segment_fields(seg, 0, "outbound")
        assert ok is False
        assert "carrier code" in reason  # carrier check fires first

    def test_only_carrier_code_no_flight_number_rejected(self):
        seg = _make_valid_segment(flight_num="")
        ok, reason = IgnavFlightProvider._validate_segment_fields(seg, 0, "outbound")
        assert ok is False
        assert "flight number" in reason

    def test_only_flight_number_no_carrier_code_rejected(self):
        seg = _make_valid_segment(carrier_code="")
        ok, reason = IgnavFlightProvider._validate_segment_fields(seg, 0, "outbound")
        assert ok is False
        assert "carrier code" in reason

    def test_malformed_departure_airport_rejected(self):
        seg = _make_valid_segment(dep="SE")  # 2 chars, not 3
        ok, reason = IgnavFlightProvider._validate_segment_fields(seg, 0, "outbound")
        assert ok is False
        assert "departure_airport" in reason

    def test_malformed_arrival_airport_rejected(self):
        seg = _make_valid_segment(arr="LAXX")  # 4 chars
        ok, reason = IgnavFlightProvider._validate_segment_fields(seg, 0, "outbound")
        assert ok is False
        assert "arrival_airport" in reason

    def test_missing_departure_time_rejected(self):
        seg = _make_valid_segment()
        del seg["departure_time_local"]
        # no departure_time_utc either
        ok, reason = IgnavFlightProvider._validate_segment_fields(seg, 0, "outbound")
        assert ok is False
        assert "missing departure time" in reason

    def test_departure_utc_only_accepted(self):
        seg = _make_valid_segment()
        del seg["departure_time_local"]
        seg["departure_time_utc"] = "2026-06-17T15:00:00Z"
        ok, reason = IgnavFlightProvider._validate_segment_fields(seg, 0, "outbound")
        assert ok is True, f"UTC departure should suffice: {reason}"

    def test_missing_arrival_time_rejected(self):
        seg = _make_valid_segment()
        del seg["arrival_time_local"]
        # no arrival_time_utc either
        ok, reason = IgnavFlightProvider._validate_segment_fields(seg, 1, "outbound")
        assert ok is False
        assert "missing arrival time" in reason

    def test_arrival_utc_only_accepted(self):
        seg = _make_valid_segment()
        del seg["arrival_time_local"]
        seg["arrival_time_utc"] = "2026-06-17T17:30:00Z"
        ok, reason = IgnavFlightProvider._validate_segment_fields(seg, 0, "outbound")
        assert ok is True, f"UTC arrival should suffice: {reason}"

    def test_zero_duration_rejected(self):
        seg = _make_valid_segment(duration=0)
        ok, reason = IgnavFlightProvider._validate_segment_fields(seg, 0, "outbound")
        assert ok is False
        assert "non-positive duration_minutes" in reason

    def test_negative_duration_rejected(self):
        seg = _make_valid_segment(duration=-10)
        ok, reason = IgnavFlightProvider._validate_segment_fields(seg, 0, "outbound")
        assert ok is False
        assert "non-positive duration_minutes" in reason

    def test_absent_duration_accepted(self):
        seg = _make_valid_segment()
        del seg["duration_minutes"]
        ok, reason = IgnavFlightProvider._validate_segment_fields(seg, 0, "outbound")
        assert ok is True, f"absent duration should pass at this gate: {reason}"

    def test_inbound_leg_name_in_reason(self):
        seg = _make_valid_segment(carrier_code="", flight_num="")
        ok, reason = IgnavFlightProvider._validate_segment_fields(seg, 2, "inbound")
        assert ok is False
        assert "inbound seg[2]" in reason


# ---------------------------------------------------------------------------
# 21: Duplicate flight-number check (_check_duplicate_flight_numbers)
# ---------------------------------------------------------------------------

class TestDuplicateFlightNumbers:
    def test_no_duplicates_returns_empty_string(self):
        segs = [
            _make_valid_segment(dep="SEA", arr="PDX", carrier_code="AS", flight_num="101"),
            _make_valid_segment(dep="PDX", arr="LAX", carrier_code="AS", flight_num="202"),
        ]
        assert IgnavFlightProvider._check_duplicate_flight_numbers(segs, "outbound") == ""

    def test_same_flight_number_different_routes_rejected(self):
        segs = [
            _make_valid_segment(dep="SEA", arr="PDX", carrier_code="AS", flight_num="101"),
            _make_valid_segment(dep="PDX", arr="LAX", carrier_code="AS", flight_num="101"),
        ]
        reason = IgnavFlightProvider._check_duplicate_flight_numbers(segs, "outbound")
        assert reason != ""
        assert "duplicate" in reason.lower()
        assert "AS101" in reason

    def test_same_flight_number_same_route_not_rejected(self):
        # Through-flight: same flight number, same dep→arr is allowed
        segs = [
            _make_valid_segment(dep="SEA", arr="LAX", carrier_code="AS", flight_num="101"),
            _make_valid_segment(dep="SEA", arr="LAX", carrier_code="AS", flight_num="101"),
        ]
        reason = IgnavFlightProvider._check_duplicate_flight_numbers(segs, "outbound")
        assert reason == ""

    def test_missing_flight_number_segments_skipped(self):
        segs = [
            _make_valid_segment(dep="SEA", arr="LAX", carrier_code="AS", flight_num=""),
            _make_valid_segment(dep="SEA", arr="LAX", carrier_code="UA", flight_num=""),
        ]
        reason = IgnavFlightProvider._check_duplicate_flight_numbers(segs, "outbound")
        assert reason == ""

    def test_single_segment_never_duplicates(self):
        segs = [_make_valid_segment()]
        assert IgnavFlightProvider._check_duplicate_flight_numbers(segs, "outbound") == ""


# ---------------------------------------------------------------------------
# 22: Integration trust gate — new segment/consistency checks
# ---------------------------------------------------------------------------

def _make_full_sea_lax_segment(
    dep="SEA", arr="LAX", flight_num="101",
    dep_local="2026-06-17T08:00:00", arr_local="2026-06-17T10:30:00",
    duration=150,
) -> Dict[str, Any]:
    """Full-featured segment fixture with all required fields."""
    return {
        "marketing_carrier_code": "AS",
        "flight_number": flight_num,
        "operating_carrier_name": "Alaska Airlines",
        "departure_airport": dep,
        "arrival_airport": arr,
        "departure_time_local": dep_local,
        "arrival_time_local": arr_local,
        "duration_minutes": duration,
    }


def _make_full_sea_lax_itinerary(**kwargs) -> Dict[str, Any]:
    seg = _make_full_sea_lax_segment(**kwargs)
    return {
        "ignav_id": "full_sea_lax_test",
        "price": {"amount": 179.0, "currency": "USD"},
        "cabin_class": "economy",
        "outbound": {"duration_minutes": seg["duration_minutes"], "segments": [seg]},
    }


class TestTrustGateSegmentConsistency:
    """Integration tests for per-segment and consistency checks in _validate_itinerary_raw."""

    def test_valid_one_way_all_fields_passes(self):
        req = _make_sea_lax_request()
        it = _make_full_sea_lax_itinerary()
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is True, f"expected pass, got: {reason}"

    def test_valid_round_trip_all_fields_passes(self):
        req = _make_sea_lax_rt_request()
        it = _make_sea_lax_rt_itinerary()
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is True, f"expected pass, got: {reason}"

    def test_missing_arrival_time_in_segment_rejected(self):
        req = _make_sea_lax_request()
        it = _make_full_sea_lax_itinerary()
        seg = it["outbound"]["segments"][0]
        del seg["arrival_time_local"]
        # no arrival_time_utc either
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is False
        assert "missing arrival time" in reason

    def test_missing_carrier_and_flight_number_rejects_offer(self):
        req = _make_sea_lax_request()
        it = _make_full_sea_lax_itinerary()
        seg = it["outbound"]["segments"][0]
        seg["marketing_carrier_code"] = ""
        seg["flight_number"] = ""
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is False
        assert "carrier code" in reason  # carrier check fires first

    def test_non_positive_segment_duration_rejects_offer(self):
        req = _make_sea_lax_request()
        it = _make_full_sea_lax_itinerary(duration=0)
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is False
        assert "non-positive duration_minutes" in reason

    def test_inconsistent_leg_duration_rejects_offer(self):
        req = _make_sea_lax_request()
        it = _make_full_sea_lax_itinerary()
        # Segment duration=150, leg duration=50 — physically impossible
        it["outbound"]["duration_minutes"] = 50
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is False
        assert "duration" in reason.lower()
        assert "less than segment" in reason

    def test_leg_duration_exceeds_segment_sum_allowed(self):
        """Leg can be > segment sum (layover time); that is not an error."""
        req = _make_sea_lax_request()
        it = _make_full_sea_lax_itinerary()
        # Segment=150m but leg says 200m (50m layover). Acceptable.
        it["outbound"]["duration_minutes"] = 200
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is True, f"leg > segment sum should be valid: {reason}"

    def test_stop_count_mismatch_rejects_offer(self):
        req = _make_sea_lax_request()
        it = _make_full_sea_lax_itinerary()
        # 1 segment → 0 stops; raw says 2 — contradiction
        it["outbound"]["stops"] = 2
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is False
        assert "stop count mismatch" in reason

    def test_stop_count_match_passes(self):
        req = _make_sea_lax_request()
        it = _make_full_sea_lax_itinerary()
        it["outbound"]["stops"] = 0  # correct: 1 segment → 0 stops
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is True, f"stop count 0 for non-stop should pass: {reason}"

    def test_duplicate_flight_numbers_across_segments_rejected(self):
        req = _make_sea_lax_request()
        seg1 = _make_full_sea_lax_segment(
            dep="SEA", arr="PDX", flight_num="101",
            dep_local="2026-06-17T08:00:00", arr_local="2026-06-17T08:45:00",
            duration=45,
        )
        seg2 = _make_full_sea_lax_segment(
            dep="PDX", arr="LAX", flight_num="101",  # same flight number, different route
            dep_local="2026-06-17T10:00:00", arr_local="2026-06-17T12:30:00",
            duration=150,
        )
        it = {
            "ignav_id": "dup_fn_test",
            "price": {"amount": 179.0, "currency": "USD"},
            "cabin_class": "economy",
            "outbound": {"duration_minutes": 270, "segments": [seg1, seg2]},
        }
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is False
        assert "duplicate" in reason.lower()
        assert "AS101" in reason

    def test_connecting_flight_different_numbers_passes(self):
        req = _make_sea_lax_request()
        seg1 = _make_full_sea_lax_segment(
            dep="SEA", arr="PDX", flight_num="101",
            dep_local="2026-06-17T08:00:00", arr_local="2026-06-17T08:45:00",
            duration=45,
        )
        seg2 = _make_full_sea_lax_segment(
            dep="PDX", arr="LAX", flight_num="202",  # different flight number
            dep_local="2026-06-17T10:00:00", arr_local="2026-06-17T12:30:00",
            duration=150,
        )
        it = {
            "ignav_id": "conn_diff_fn",
            "price": {"amount": 179.0, "currency": "USD"},
            "cabin_class": "economy",
            "outbound": {"duration_minutes": 270, "segments": [seg1, seg2]},
        }
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is True, f"connecting flight with different numbers should pass: {reason}"

    def test_all_invalid_segment_offers_return_unavailable_from_search(self):
        """search_flights returns UNAVAILABLE when all offers fail segment validation."""
        provider = IgnavFlightProvider(api_key="testkey", http_client=MagicMock())
        req = _make_sea_lax_request()
        bad_seg = _make_full_sea_lax_segment()
        bad_seg["arrival_time_local"] = None
        # Remove all arrival time keys so segment fails
        bad_seg.pop("arrival_time_local", None)
        bad_it = {
            "ignav_id": "bad_it",
            "price": {"amount": 179.0, "currency": "USD"},
            "cabin_class": "economy",
            "outbound": {"duration_minutes": 150, "segments": [bad_seg]},
        }
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"itineraries": [bad_it]}
        provider._client.post.return_value = mock_resp
        result = provider.search_flights(req)
        assert result.status == FlightSourceStatus.UNAVAILABLE
        assert result.rows == []

    def test_inbound_missing_arrival_time_rejected_for_round_trip(self):
        req = _make_sea_lax_rt_request()
        it = _make_sea_lax_rt_itinerary()
        in_seg = it["inbound"]["segments"][0]
        in_seg.pop("arrival_time_local", None)
        # no arrival_time_utc either
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is False
        assert "missing arrival time" in reason
        assert "inbound" in reason

    def test_inbound_duplicate_flight_numbers_rejected(self):
        req = _make_sea_lax_rt_request()
        in_seg1 = {
            "marketing_carrier_code": "AS",
            "flight_number": "AS202",
            "operating_carrier_name": "Alaska Airlines",
            "departure_airport": "LAX",
            "arrival_airport": "PDX",
            "departure_time_local": "2026-06-24T14:00:00",
            "arrival_time_local": "2026-06-24T15:30:00",
            "duration_minutes": 90,
        }
        in_seg2 = {
            "marketing_carrier_code": "AS",
            "flight_number": "AS202",  # same number, different route
            "operating_carrier_name": "Alaska Airlines",
            "departure_airport": "PDX",
            "arrival_airport": "SEA",
            "departure_time_local": "2026-06-24T16:30:00",
            "arrival_time_local": "2026-06-24T17:15:00",
            "duration_minutes": 45,
        }
        it = _make_sea_lax_rt_itinerary(
            inbound={"duration_minutes": 225, "segments": [in_seg1, in_seg2]}
        )
        ok, reason = IgnavFlightProvider._validate_itinerary_raw(it, req)
        assert ok is False
        assert "duplicate" in reason.lower()
        assert "inbound" in reason


# ---------------------------------------------------------------------------
# 23: Schedule trust certification gate
# ---------------------------------------------------------------------------

def _make_certified_search_response() -> Dict[str, Any]:
    """One valid SEA→LAX itinerary with all required fields."""
    return {"itineraries": [_make_sea_lax_itinerary()]}


class TestScheduleTrustCertification:
    """Tests for the IGNAV_SCHEDULE_TRUST_CERTIFIED gate.

    Field completeness ≠ external correctness.  The gate prevents displaying
    offers whose schedule accuracy has not been manually confirmed.
    """

    def _build_provider(self) -> IgnavFlightProvider:
        provider = IgnavFlightProvider(api_key="testkey", http_client=MagicMock())
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = _make_certified_search_response()
        provider._client.post.return_value = mock_resp
        return provider

    def test_no_cert_env_returns_unavailable(self):
        """Default (no IGNAV_SCHEDULE_TRUST_CERTIFIED) → UNAVAILABLE."""
        provider = self._build_provider()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IGNAV_SCHEDULE_TRUST_CERTIFIED", None)
            with patch.object(provider, "_fetch_booking_links", return_value=[]):
                result = provider.search_flights(_make_sea_lax_request())
        assert result.status == FlightSourceStatus.UNAVAILABLE
        assert result.rows == []

    def test_cert_flag_zero_returns_unavailable(self):
        provider = self._build_provider()
        with patch.dict(os.environ, {"IGNAV_SCHEDULE_TRUST_CERTIFIED": "0"}):
            with patch.object(provider, "_fetch_booking_links", return_value=[]):
                result = provider.search_flights(_make_sea_lax_request())
        assert result.status == FlightSourceStatus.UNAVAILABLE
        assert result.rows == []

    def test_cert_flag_false_string_returns_unavailable(self):
        provider = self._build_provider()
        with patch.dict(os.environ, {"IGNAV_SCHEDULE_TRUST_CERTIFIED": "false"}):
            with patch.object(provider, "_fetch_booking_links", return_value=[]):
                result = provider.search_flights(_make_sea_lax_request())
        assert result.status == FlightSourceStatus.UNAVAILABLE
        assert result.rows == []

    def test_unavailable_reason_mentions_certification(self):
        provider = self._build_provider()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IGNAV_SCHEDULE_TRUST_CERTIFIED", None)
            with patch.object(provider, "_fetch_booking_links", return_value=[]):
                result = provider.search_flights(_make_sea_lax_request())
        assert result.reason is not None
        assert "certification" in (result.reason or "").lower()

    def test_cert_flag_one_allows_valid_offers(self):
        """IGNAV_SCHEDULE_TRUST_CERTIFIED=1 → OK with offers for valid payload."""
        provider = self._build_provider()
        with patch.dict(os.environ, {"IGNAV_SCHEDULE_TRUST_CERTIFIED": "1"}):
            with patch.object(provider, "_fetch_booking_links", return_value=[]):
                result = provider.search_flights(_make_sea_lax_request())
        assert result.status == FlightSourceStatus.OK
        assert len(result.rows) == 1
        assert isinstance(result.rows[0], FlightItineraryOffer)

    def test_cert_flag_true_string_allows_valid_offers(self):
        provider = self._build_provider()
        with patch.dict(os.environ, {"IGNAV_SCHEDULE_TRUST_CERTIFIED": "true"}):
            with patch.object(provider, "_fetch_booking_links", return_value=[]):
                result = provider.search_flights(_make_sea_lax_request())
        assert result.status == FlightSourceStatus.OK
        assert len(result.rows) >= 1

    def test_cert_on_but_trust_gate_still_rejects_invalid_offers(self):
        """Cert flag does not bypass trust gate — invalid offers still rejected."""
        provider = IgnavFlightProvider(api_key="testkey", http_client=MagicMock())
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        # Itinerary with wrong origin — should fail trust gate before cert check
        mock_resp.json.return_value = {
            "itineraries": [_make_sea_lax_itinerary(dep_airport="PDX")]
        }
        provider._client.post.return_value = mock_resp
        with patch.dict(os.environ, {"IGNAV_SCHEDULE_TRUST_CERTIFIED": "1"}):
            result = provider.search_flights(_make_sea_lax_request())
        assert result.status == FlightSourceStatus.UNAVAILABLE
        assert result.rows == []

    def test_cert_on_but_segment_missing_flight_number_rejects(self):
        """Cert flag does not bypass segment field validation."""
        provider = IgnavFlightProvider(api_key="testkey", http_client=MagicMock())
        it = _make_sea_lax_itinerary()
        it["outbound"]["segments"][0]["flight_number"] = ""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"itineraries": [it]}
        provider._client.post.return_value = mock_resp
        with patch.dict(os.environ, {"IGNAV_SCHEDULE_TRUST_CERTIFIED": "1"}):
            result = provider.search_flights(_make_sea_lax_request())
        assert result.status == FlightSourceStatus.UNAVAILABLE
        assert result.rows == []
