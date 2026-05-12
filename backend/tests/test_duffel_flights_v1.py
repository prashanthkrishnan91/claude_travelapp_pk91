"""Duffel Flights v1 — search-only provider tests.

Covers the full task spec:
  - env disabled → no provider / fail closed
  - one-way valid offer maps correctly
  - round-trip valid offer maps correctly
  - missing segment flight identity rejects (no carrier / flight number)
  - missing price rejects
  - malformed route / date rejects
  - no booking / order API is called
  - provider selection prefers Duffel when enabled
  - Ignav remains non-visible (DISABLED in registry)
  - booking_link is always UNAVAILABLE
  - trust gate: unmappable segment fails entire offer

All tests use synthetic Duffel-shaped fixtures; no live API calls.

Tests that require pydantic (FlightSearchRequest, FlightItineraryOffer) are
guarded with ``@requires_full_stack`` so they skip gracefully in the minimal
CI harness and run in the full Railway/Docker environment.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Full-stack guard (pydantic + app contracts require full install)
# ---------------------------------------------------------------------------
_full_stack = True
try:
    from app.contracts.flights import FlightSourceStatus
    from app.contracts.flight_offer import (
        BookingLinkType,
        FlightItineraryOffer,
        TripType,
    )
    from app.models.search import FlightSearchRequest
    from app.services.flights_provider import (
        NullFlightProvider,
        get_flight_provider,
        reset_flight_provider_cache,
    )
    from app.services.flights_provider_duffel import (
        DuffelFlightProvider,
        build_duffel_provider_from_env,
        duffel_certified_from_env,
        duffel_enabled_from_env,
    )
except (ImportError, ModuleNotFoundError):
    _full_stack = False
    FlightSourceStatus = None  # type: ignore[assignment,misc]
    BookingLinkType = None  # type: ignore[assignment,misc]
    FlightItineraryOffer = None  # type: ignore[assignment,misc]
    TripType = None  # type: ignore[assignment,misc]
    FlightSearchRequest = None  # type: ignore[assignment,misc]
    NullFlightProvider = None  # type: ignore[assignment,misc]
    get_flight_provider = None  # type: ignore[assignment]
    reset_flight_provider_cache = None  # type: ignore[assignment]
    DuffelFlightProvider = None  # type: ignore[assignment,misc]
    build_duffel_provider_from_env = None  # type: ignore[assignment]
    duffel_certified_from_env = None  # type: ignore[assignment]
    duffel_enabled_from_env = None  # type: ignore[assignment]

from app.services.provider_registry import (
    PROVIDER_REGISTRY,
    ProviderRole,
    is_production_allowed,
    is_provider_active,
)

requires_full_stack = pytest.mark.skipif(
    not _full_stack,
    reason="Skipped in minimal test harness (pydantic not installed); "
           "run in full Railway/Docker stack.",
)


# ── Fake HTTP plumbing ────────────────────────────────────────────────────────

class _FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload


class _FakeHttp:
    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self._responses: List[_FakeResponse] = []

    def enqueue(self, resp: _FakeResponse) -> None:
        self._responses.append(resp)

    def post(self, url: str, *, params=None, json=None, headers=None):
        self.calls.append({"url": url, "params": params, "json": json, "headers": headers})
        return self._responses.pop(0)


def _build(api_key: str = "test-key", certified: bool = True) -> tuple[DuffelFlightProvider, _FakeHttp]:
    http = _FakeHttp()
    return DuffelFlightProvider(
        api_key=api_key, base_url="https://duffel.test", http_client=http, certified=certified
    ), http


# ── Fixture helpers ───────────────────────────────────────────────────────────

def _seg(
    origin: str = "SEA",
    destination: str = "LAX",
    dep: str = "2026-06-17T08:00:00Z",
    arr: str = "2026-06-17T10:30:00Z",
    carrier_iata: str = "AS",
    carrier_name: str = "Alaska Airlines",
    flight_num: str = "7",
    duration: str = "PT2H30M",
) -> Dict[str, Any]:
    return {
        "origin": {"iata_code": origin},
        "destination": {"iata_code": destination},
        "departing_at": dep,
        "arriving_at": arr,
        "marketing_carrier": {"iata_code": carrier_iata, "name": carrier_name},
        "marketing_carrier_flight_number": flight_num,
        "duration": duration,
    }


def _offer_one_way(
    offer_id: str = "off1",
    amount: str = "189.50",
    currency: str = "USD",
    seg_kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    s = _seg(**(seg_kwargs or {}))
    return {
        "id": offer_id,
        "total_amount": amount,
        "total_currency": currency,
        "slices": [
            {
                "duration": "PT2H30M",
                "segments": [s],
            }
        ],
    }


def _offer_round_trip(
    offer_id: str = "off_rt",
    amount: str = "320.00",
    currency: str = "USD",
) -> Dict[str, Any]:
    outbound_seg = _seg(
        origin="SEA", destination="LAX",
        dep="2026-06-17T08:00:00Z", arr="2026-06-17T10:30:00Z",
    )
    return_seg = _seg(
        origin="LAX", destination="SEA",
        dep="2026-06-24T15:00:00Z", arr="2026-06-24T17:30:00Z",
        carrier_iata="AS", flight_num="8",
    )
    return {
        "id": offer_id,
        "total_amount": amount,
        "total_currency": currency,
        "slices": [
            {"duration": "PT2H30M", "segments": [outbound_seg]},
            {"duration": "PT2H30M", "segments": [return_seg]},
        ],
    }


def _duffel_response(offers: List[Dict[str, Any]]) -> _FakeResponse:
    return _FakeResponse(200, payload={"data": {"offers": offers}})


def _one_way_req(
    origin: str = "SEA",
    destination: str = "LAX",
    departure_date: str = "2026-06-17",
) -> FlightSearchRequest:
    return FlightSearchRequest(
        origin=origin,
        destination=destination,
        departure_date=date.fromisoformat(departure_date),
        passengers=1,
        cabin_class="economy",
    )


def _round_trip_req() -> FlightSearchRequest:
    return FlightSearchRequest(
        origin="SEA",
        destination="LAX",
        departure_date=date(2026, 6, 17),
        return_date=date(2026, 6, 24),
        passengers=1,
        cabin_class="economy",
    )


# ── 1. Env gating ─────────────────────────────────────────────────────────────

@requires_full_stack
class TestEnvGating:
    def test_disabled_when_no_key(self):
        assert duffel_enabled_from_env({"DUFFEL_FLIGHTS_ENABLED": "1"}) is False

    def test_disabled_when_no_flag(self):
        assert duffel_enabled_from_env({"DUFFEL_API_KEY": "x"}) is False

    def test_disabled_when_flag_is_zero(self):
        assert duffel_enabled_from_env({"DUFFEL_API_KEY": "x", "DUFFEL_FLIGHTS_ENABLED": "0"}) is False

    def test_enabled_when_both_set(self):
        assert duffel_enabled_from_env({"DUFFEL_API_KEY": "x", "DUFFEL_FLIGHTS_ENABLED": "1"}) is True

    def test_enabled_with_true_string(self):
        assert duffel_enabled_from_env({"DUFFEL_API_KEY": "x", "DUFFEL_FLIGHTS_ENABLED": "true"}) is True

    def test_build_returns_none_when_disabled(self):
        assert build_duffel_provider_from_env({"DUFFEL_FLIGHTS_ENABLED": "0"}) is None

    def test_build_returns_provider_when_enabled(self):
        p = build_duffel_provider_from_env({"DUFFEL_API_KEY": "k", "DUFFEL_FLIGHTS_ENABLED": "1"})
        assert isinstance(p, DuffelFlightProvider)


# ── 2. Provider selection ──────────────────────────────────────────────────────

@requires_full_stack
class TestProviderSelection:
    def test_get_flight_provider_returns_duffel_when_enabled(self, monkeypatch):
        monkeypatch.setenv("DUFFEL_API_KEY", "test-key")
        monkeypatch.setenv("DUFFEL_FLIGHTS_ENABLED", "1")
        reset_flight_provider_cache()
        p = get_flight_provider()
        assert isinstance(p, DuffelFlightProvider)

    def test_get_flight_provider_caches_instance(self, monkeypatch):
        monkeypatch.setenv("DUFFEL_API_KEY", "test-key")
        monkeypatch.setenv("DUFFEL_FLIGHTS_ENABLED", "1")
        reset_flight_provider_cache()
        p1 = get_flight_provider()
        p2 = get_flight_provider()
        assert p1 is p2

    def test_get_flight_provider_returns_null_when_key_absent(self, monkeypatch):
        monkeypatch.delenv("DUFFEL_API_KEY", raising=False)
        monkeypatch.delenv("DUFFEL_FLIGHTS_ENABLED", raising=False)
        reset_flight_provider_cache()
        assert isinstance(get_flight_provider(), NullFlightProvider)

    def test_get_flight_provider_returns_null_when_flag_off(self, monkeypatch):
        monkeypatch.setenv("DUFFEL_API_KEY", "test-key")
        monkeypatch.setenv("DUFFEL_FLIGHTS_ENABLED", "0")
        reset_flight_provider_cache()
        assert isinstance(get_flight_provider(), NullFlightProvider)


# ── 3. Registry state ──────────────────────────────────────────────────────────

class TestRegistryState:
    def test_duffel_is_production_allowed(self):
        assert is_production_allowed("duffel_flights") is True

    def test_duffel_is_active(self):
        assert is_provider_active("duffel_flights") is True

    def test_duffel_role_is_link_out(self):
        assert PROVIDER_REGISTRY["duffel_flights"].role is ProviderRole.LINK_OUT

    def test_duffel_required_env_vars(self):
        entry = PROVIDER_REGISTRY["duffel_flights"]
        assert "DUFFEL_API_KEY" in entry.required_env_vars
        assert "DUFFEL_FLIGHTS_ENABLED" in entry.required_env_vars

    def test_ignav_is_disabled(self):
        assert is_provider_active("ignav_flights") is False
        assert is_production_allowed("ignav_flights") is False

    def test_ignav_role_is_disabled(self):
        assert PROVIDER_REGISTRY["ignav_flights"].role is ProviderRole.DISABLED

    def test_ignav_cannot_serve_visible_cards(self):
        # Registry-level check: Ignav is DISABLED → is_provider_active returns False.
        # No env manipulation needed; this is a pure registry assertion.
        assert not is_provider_active("ignav_flights"), \
            "Ignav must not be active in the registry"


# ── 4. One-way offer mapping ───────────────────────────────────────────────────

@requires_full_stack
class TestOneWayMapping:
    def test_valid_one_way_maps_to_flight_itinerary_offer(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_one_way()]))
        result = p.search_flights(_one_way_req())
        assert result.status is FlightSourceStatus.OK
        assert len(result.rows) == 1
        offer = result.rows[0]
        assert isinstance(offer, FlightItineraryOffer)

    def test_one_way_offer_fields(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_one_way()]))
        offer = p.search_flights(_one_way_req()).rows[0]
        assert offer.provider == "duffel_flights"
        assert offer.trip_type is TripType.ONE_WAY
        assert offer.origin == "SEA"
        assert offer.destination == "LAX"
        assert offer.departure_date == "2026-06-17"
        assert offer.return_leg is None

    def test_one_way_offer_price(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_one_way(amount="189.50")]))
        offer = p.search_flights(_one_way_req()).rows[0]
        assert offer.price.total_amount == 189.50
        assert offer.price.currency == "USD"

    def test_one_way_outbound_leg_segment(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_one_way()]))
        offer = p.search_flights(_one_way_req()).rows[0]
        leg = offer.outbound_leg
        assert leg.origin == "SEA"
        assert leg.destination == "LAX"
        assert leg.stops == 0
        assert len(leg.segments) == 1
        seg = leg.segments[0]
        assert seg.flight_number == "AS7"
        assert seg.airline == "Alaska Airlines"
        assert seg.origin == "SEA"
        assert seg.destination == "LAX"
        assert seg.duration_minutes == 150

    def test_one_way_booking_link_is_unavailable(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_one_way()]))
        offer = p.search_flights(_one_way_req()).rows[0]
        assert offer.booking_link.link_type is BookingLinkType.UNAVAILABLE
        assert offer.booking_link.url == ""

    def test_one_way_live_cached_status_is_live(self):
        from app.contracts.flight_offer import LiveCachedStatus
        p, http = _build()
        http.enqueue(_duffel_response([_offer_one_way()]))
        offer = p.search_flights(_one_way_req()).rows[0]
        assert offer.live_cached_status is LiveCachedStatus.LIVE


# ── 5. Round-trip offer mapping ────────────────────────────────────────────────

@requires_full_stack
class TestRoundTripMapping:
    def test_valid_round_trip_maps_both_legs(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_round_trip()]))
        result = p.search_flights(_round_trip_req())
        assert result.status is FlightSourceStatus.OK
        offer = result.rows[0]
        assert offer.trip_type is TripType.ROUND_TRIP
        assert offer.return_leg is not None

    def test_round_trip_return_leg_fields(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_round_trip()]))
        offer = p.search_flights(_round_trip_req()).rows[0]
        ret_leg = offer.return_leg
        assert ret_leg.origin == "LAX"
        assert ret_leg.destination == "SEA"
        assert ret_leg.stops == 0

    def test_round_trip_with_only_one_slice_rejected(self):
        p, http = _build()
        one_slice_offer = _offer_one_way()  # only 1 slice
        http.enqueue(_duffel_response([one_slice_offer]))
        result = p.search_flights(_round_trip_req())
        assert result.status in (FlightSourceStatus.UNAVAILABLE, FlightSourceStatus.EMPTY)

    def test_round_trip_request_sends_two_slices(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_round_trip()]))
        p.search_flights(_round_trip_req())
        body = http.calls[0]["json"]
        assert len(body["data"]["slices"]) == 2
        assert body["data"]["slices"][0]["origin"] == "SEA"
        assert body["data"]["slices"][0]["destination"] == "LAX"
        assert body["data"]["slices"][1]["origin"] == "LAX"
        assert body["data"]["slices"][1]["destination"] == "SEA"


# ── 6. Trust gate — missing flight identity ────────────────────────────────────

@requires_full_stack
class TestMissingFlightIdentityRejected:
    def _offer_with_seg_patch(self, **patch_kwargs) -> Dict[str, Any]:
        seg = _seg(**{k: v for k, v in patch_kwargs.items()
                     if k in ("origin", "destination", "dep", "arr",
                               "carrier_iata", "carrier_name", "flight_num", "duration")})
        for k, v in patch_kwargs.items():
            if k.startswith("_raw_"):
                seg[k[5:]] = v
        return {
            "id": "off_bad",
            "total_amount": "150.00",
            "total_currency": "USD",
            "slices": [{"duration": "PT2H30M", "segments": [seg]}],
        }

    def test_missing_carrier_iata_rejects_offer(self):
        p, http = _build()
        seg = _seg()
        seg["marketing_carrier"]["iata_code"] = ""
        offer = {"id": "x", "total_amount": "100", "total_currency": "USD",
                 "slices": [{"duration": "PT2H", "segments": [seg]}]}
        http.enqueue(_duffel_response([offer]))
        result = p.search_flights(_one_way_req())
        assert result.status in (FlightSourceStatus.UNAVAILABLE, FlightSourceStatus.EMPTY)

    def test_missing_flight_number_rejects_offer(self):
        p, http = _build()
        seg = _seg()
        seg["marketing_carrier_flight_number"] = ""
        offer = {"id": "x", "total_amount": "100", "total_currency": "USD",
                 "slices": [{"duration": "PT2H", "segments": [seg]}]}
        http.enqueue(_duffel_response([offer]))
        result = p.search_flights(_one_way_req())
        assert result.status in (FlightSourceStatus.UNAVAILABLE, FlightSourceStatus.EMPTY)

    def test_missing_both_carrier_and_number_rejects(self):
        p, http = _build()
        seg = _seg()
        seg["marketing_carrier"]["iata_code"] = ""
        seg["marketing_carrier_flight_number"] = None
        offer = {"id": "x", "total_amount": "100", "total_currency": "USD",
                 "slices": [{"duration": "PT2H", "segments": [seg]}]}
        http.enqueue(_duffel_response([offer]))
        result = p.search_flights(_one_way_req())
        assert result.status in (FlightSourceStatus.UNAVAILABLE, FlightSourceStatus.EMPTY)

    def test_invalid_iata_origin_rejects_segment(self):
        p, http = _build()
        seg = _seg()
        seg["origin"]["iata_code"] = "XX"  # 2-letter, not 3
        offer = {"id": "x", "total_amount": "100", "total_currency": "USD",
                 "slices": [{"duration": "PT2H", "segments": [seg]}]}
        http.enqueue(_duffel_response([offer]))
        result = p.search_flights(_one_way_req())
        assert result.status in (FlightSourceStatus.UNAVAILABLE, FlightSourceStatus.EMPTY)

    def test_missing_departing_at_rejects_segment(self):
        p, http = _build()
        seg = _seg()
        seg["departing_at"] = ""
        offer = {"id": "x", "total_amount": "100", "total_currency": "USD",
                 "slices": [{"duration": "PT2H", "segments": [seg]}]}
        http.enqueue(_duffel_response([offer]))
        result = p.search_flights(_one_way_req())
        assert result.status in (FlightSourceStatus.UNAVAILABLE, FlightSourceStatus.EMPTY)

    def test_missing_arriving_at_rejects_segment(self):
        p, http = _build()
        seg = _seg()
        seg["arriving_at"] = None
        offer = {"id": "x", "total_amount": "100", "total_currency": "USD",
                 "slices": [{"duration": "PT2H", "segments": [seg]}]}
        http.enqueue(_duffel_response([offer]))
        result = p.search_flights(_one_way_req())
        assert result.status in (FlightSourceStatus.UNAVAILABLE, FlightSourceStatus.EMPTY)


# ── 7. Trust gate — missing price ─────────────────────────────────────────────

@requires_full_stack
class TestMissingPriceRejected:
    def test_null_total_amount_rejects(self):
        p, http = _build()
        offer = _offer_one_way()
        offer["total_amount"] = None
        http.enqueue(_duffel_response([offer]))
        result = p.search_flights(_one_way_req())
        assert result.status in (FlightSourceStatus.UNAVAILABLE, FlightSourceStatus.EMPTY)

    def test_zero_total_amount_rejects(self):
        p, http = _build()
        offer = _offer_one_way(amount="0")
        http.enqueue(_duffel_response([offer]))
        result = p.search_flights(_one_way_req())
        assert result.status in (FlightSourceStatus.UNAVAILABLE, FlightSourceStatus.EMPTY)

    def test_negative_total_amount_rejects(self):
        p, http = _build()
        offer = _offer_one_way(amount="-50")
        http.enqueue(_duffel_response([offer]))
        result = p.search_flights(_one_way_req())
        assert result.status in (FlightSourceStatus.UNAVAILABLE, FlightSourceStatus.EMPTY)

    def test_non_numeric_total_amount_rejects(self):
        p, http = _build()
        offer = _offer_one_way(amount="not-a-price")
        http.enqueue(_duffel_response([offer]))
        result = p.search_flights(_one_way_req())
        assert result.status in (FlightSourceStatus.UNAVAILABLE, FlightSourceStatus.EMPTY)


# ── 8. Malformed route / date inputs ──────────────────────────────────────────

@requires_full_stack
class TestMalformedInputs:
    def test_missing_origin_returns_empty(self):
        p, http = _build()
        req = FlightSearchRequest(
            origin=None,
            destination="LAX",
            departure_date=date(2026, 6, 17),
        )
        result = p.search_flights(req)
        assert result.status is FlightSourceStatus.EMPTY
        assert not http.calls  # no HTTP call made

    def test_missing_destination_returns_empty(self):
        p, http = _build()
        req = FlightSearchRequest(
            origin="SEA",
            destination=None,
            departure_date=date(2026, 6, 17),
        )
        result = p.search_flights(req)
        assert result.status is FlightSourceStatus.EMPTY
        assert not http.calls


# ── 9. No booking / order API called ──────────────────────────────────────────

@requires_full_stack
class TestNoBookingOrderCalled:
    def test_no_duffel_orders_endpoint_called(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_one_way()]))
        p.search_flights(_one_way_req())
        for call in http.calls:
            assert "/air/orders" not in call["url"], \
                f"Orders endpoint must never be called; got: {call['url']}"

    def test_booking_link_type_is_always_unavailable(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_one_way(), _offer_one_way(offer_id="off2")]))
        result = p.search_flights(_one_way_req())
        for offer in result.rows:
            assert offer.booking_link.link_type is BookingLinkType.UNAVAILABLE

    def test_only_one_http_call_per_search(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_one_way()]))
        p.search_flights(_one_way_req())
        assert len(http.calls) == 1


# ── 10. HTTP error handling ────────────────────────────────────────────────────

@requires_full_stack
class TestHttpErrorHandling:
    def test_5xx_returns_error(self):
        p, http = _build()
        http.enqueue(_FakeResponse(500))
        result = p.search_flights(_one_way_req())
        assert result.status is FlightSourceStatus.ERROR

    def test_401_returns_error(self):
        p, http = _build()
        http.enqueue(_FakeResponse(401))
        result = p.search_flights(_one_way_req())
        assert result.status is FlightSourceStatus.ERROR

    def test_empty_offers_list_returns_empty(self):
        p, http = _build()
        http.enqueue(_FakeResponse(200, payload={"data": {"offers": []}}))
        result = p.search_flights(_one_way_req())
        assert result.status is FlightSourceStatus.EMPTY

    def test_transport_error_returns_error(self):
        p, http = _build()

        class _ExplodingHttp:
            def post(self, *args, **kwargs):
                raise ConnectionError("network down")

        p2 = DuffelFlightProvider(
            api_key="test-key",
            base_url="https://duffel.test",
            http_client=_ExplodingHttp(),
        )
        result = p2.search_flights(_one_way_req())
        assert result.status is FlightSourceStatus.ERROR

    def test_all_offers_fail_trust_gate_returns_unavailable(self):
        p, http = _build()
        bad_offer = _offer_one_way()
        bad_offer["total_amount"] = None  # will fail trust gate
        http.enqueue(_duffel_response([bad_offer]))
        result = p.search_flights(_one_way_req())
        assert result.status is FlightSourceStatus.UNAVAILABLE


# ── 11. Request structure ─────────────────────────────────────────────────────

@requires_full_stack
class TestRequestStructure:
    def test_one_way_request_sends_single_slice(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_one_way()]))
        p.search_flights(_one_way_req())
        body = http.calls[0]["json"]
        assert len(body["data"]["slices"]) == 1

    def test_passengers_count_in_request(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_one_way()]))
        req = FlightSearchRequest(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17),
            passengers=2,
        )
        p.search_flights(req)
        body = http.calls[0]["json"]
        passengers = body["data"]["passengers"]
        assert len(passengers) == 2
        assert all(p["type"] == "adult" for p in passengers)

    def test_cabin_class_in_request(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_one_way()]))
        p.search_flights(_one_way_req())
        body = http.calls[0]["json"]
        assert body["data"]["cabin_class"] == "economy"

    def test_authorization_header_uses_bearer_token(self):
        p, http = _build(api_key="my-duffel-key")
        http.enqueue(_duffel_response([_offer_one_way()]))
        p.search_flights(_one_way_req())
        headers = http.calls[0]["headers"]
        assert headers["Authorization"] == "Bearer my-duffel-key"

    def test_duffel_version_header_set(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_one_way()]))
        p.search_flights(_one_way_req())
        headers = http.calls[0]["headers"]
        assert "Duffel-Version" in headers

    def test_one_way_slice_includes_max_connections_zero(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_one_way()]))
        p.search_flights(_one_way_req())
        slices = http.calls[0]["json"]["data"]["slices"]
        assert slices[0]["max_connections"] == 0

    def test_round_trip_both_slices_include_max_connections_zero(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_round_trip()]))
        p.search_flights(_round_trip_req())
        slices = http.calls[0]["json"]["data"]["slices"]
        assert all(sl["max_connections"] == 0 for sl in slices)


# ── 12. Multi-offer response ───────────────────────────────────────────────────

@requires_full_stack
class TestMultiOfferResponse:
    def test_multiple_valid_offers_all_mapped(self):
        p, http = _build()
        offers = [
            _offer_one_way(offer_id="off1", amount="189.50"),
            _offer_one_way(offer_id="off2", amount="229.00"),
            _offer_one_way(offer_id="off3", amount="310.00"),
        ]
        http.enqueue(_duffel_response(offers))
        result = p.search_flights(_one_way_req())
        assert result.status is FlightSourceStatus.OK
        assert len(result.rows) == 3

    def test_mix_of_valid_and_invalid_partial_success(self):
        p, http = _build()
        good = _offer_one_way(offer_id="good")
        bad = _offer_one_way(offer_id="bad", amount="0")  # zero price
        http.enqueue(_duffel_response([bad, good]))
        result = p.search_flights(_one_way_req())
        assert result.status is FlightSourceStatus.OK
        assert len(result.rows) == 1
        assert result.rows[0].price.total_amount == 189.50


# ── 13. Route/date validation ─────────────────────────────────────────────────

@requires_full_stack
class TestRouteDateValidation:
    """Offers whose segment data doesn't match the requested route/date are rejected."""

    def _offer_with_seg_route(
        self,
        origin: str = "SEA",
        destination: str = "LAX",
        dep: str = "2026-06-17T08:00:00Z",
    ) -> Dict[str, Any]:
        s = _seg(origin=origin, destination=destination, dep=dep)
        return {
            "id": "off_route",
            "total_amount": "189.50",
            "total_currency": "USD",
            "slices": [{"duration": "PT2H30M", "segments": [s]}],
        }

    # ── One-way route/date mismatches ─────────────────────────────────────────

    def test_wrong_outbound_origin_rejects(self):
        p, http = _build()
        http.enqueue(_duffel_response([self._offer_with_seg_route(origin="SFO")]))
        result = p.search_flights(_one_way_req(origin="SEA", destination="LAX"))
        assert result.status in (FlightSourceStatus.UNAVAILABLE, FlightSourceStatus.EMPTY)

    def test_wrong_outbound_destination_rejects(self):
        p, http = _build()
        http.enqueue(_duffel_response([self._offer_with_seg_route(destination="SFO")]))
        result = p.search_flights(_one_way_req(origin="SEA", destination="LAX"))
        assert result.status in (FlightSourceStatus.UNAVAILABLE, FlightSourceStatus.EMPTY)

    def test_wrong_outbound_departure_date_rejects(self):
        p, http = _build()
        # Same route but wrong date (June 18 instead of June 17)
        http.enqueue(_duffel_response([
            self._offer_with_seg_route(dep="2026-06-18T08:00:00Z")
        ]))
        result = p.search_flights(_one_way_req(departure_date="2026-06-17"))
        assert result.status in (FlightSourceStatus.UNAVAILABLE, FlightSourceStatus.EMPTY)

    def test_valid_one_way_route_and_date_accepted(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_one_way()]))
        result = p.search_flights(_one_way_req(origin="SEA", destination="LAX"))
        assert result.status is FlightSourceStatus.OK
        assert result.rows[0].outbound_leg.origin == "SEA"
        assert result.rows[0].outbound_leg.destination == "LAX"

    # ── Round-trip return leg mismatches ──────────────────────────────────────

    def _offer_rt_with_return_route(
        self,
        ret_origin: str = "LAX",
        ret_dest: str = "SEA",
        ret_dep: str = "2026-06-24T15:00:00Z",
    ) -> Dict[str, Any]:
        outbound_seg = _seg(
            origin="SEA", destination="LAX",
            dep="2026-06-17T08:00:00Z", arr="2026-06-17T10:30:00Z",
        )
        return_seg = _seg(
            origin=ret_origin, destination=ret_dest,
            dep=ret_dep, arr="2026-06-24T17:30:00Z",
            carrier_iata="AS", flight_num="8",
        )
        return {
            "id": "off_rt_route",
            "total_amount": "320.00",
            "total_currency": "USD",
            "slices": [
                {"duration": "PT2H30M", "segments": [outbound_seg]},
                {"duration": "PT2H30M", "segments": [return_seg]},
            ],
        }

    def test_round_trip_wrong_return_origin_rejects(self):
        p, http = _build()
        http.enqueue(_duffel_response([self._offer_rt_with_return_route(ret_origin="SFO")]))
        result = p.search_flights(_round_trip_req())
        assert result.status in (FlightSourceStatus.UNAVAILABLE, FlightSourceStatus.EMPTY)

    def test_round_trip_wrong_return_destination_rejects(self):
        p, http = _build()
        http.enqueue(_duffel_response([self._offer_rt_with_return_route(ret_dest="SFO")]))
        result = p.search_flights(_round_trip_req())
        assert result.status in (FlightSourceStatus.UNAVAILABLE, FlightSourceStatus.EMPTY)

    def test_round_trip_wrong_return_date_rejects(self):
        p, http = _build()
        # Return on June 25 instead of June 24
        http.enqueue(_duffel_response([
            self._offer_rt_with_return_route(ret_dep="2026-06-25T15:00:00Z")
        ]))
        result = p.search_flights(_round_trip_req())
        assert result.status in (FlightSourceStatus.UNAVAILABLE, FlightSourceStatus.EMPTY)

    def test_valid_round_trip_route_and_dates_accepted(self):
        p, http = _build()
        http.enqueue(_duffel_response([_offer_round_trip()]))
        result = p.search_flights(_round_trip_req())
        assert result.status is FlightSourceStatus.OK
        offer = result.rows[0]
        assert offer.outbound_leg.origin == "SEA"
        assert offer.outbound_leg.destination == "LAX"
        assert offer.return_leg.origin == "LAX"
        assert offer.return_leg.destination == "SEA"


# ── 14. Certification gate ────────────────────────────────────────────────────

@requires_full_stack
class TestCertificationGate:
    """DUFFEL_SCHEDULE_TRUST_CERTIFIED must be truthy before cards are returned."""

    def test_uncertified_returns_unavailable_even_with_valid_offers(self):
        # certified=False (default); valid offer maps but gate suppresses cards
        p, http = _build(certified=False)
        http.enqueue(_duffel_response([_offer_one_way()]))
        result = p.search_flights(_one_way_req())
        assert result.status is FlightSourceStatus.UNAVAILABLE
        assert result.rows == []
        assert "certification" in (result.reason or "").lower()

    def test_uncertified_rows_are_empty_not_partial(self):
        # Multiple valid offers, still no rows when not certified
        p, http = _build(certified=False)
        http.enqueue(_duffel_response([
            _offer_one_way(offer_id="off1"),
            _offer_one_way(offer_id="off2"),
        ]))
        result = p.search_flights(_one_way_req())
        assert result.rows == []

    def test_certified_allows_valid_offers(self):
        p, http = _build(certified=True)
        http.enqueue(_duffel_response([_offer_one_way()]))
        result = p.search_flights(_one_way_req())
        assert result.status is FlightSourceStatus.OK
        assert len(result.rows) == 1

    def test_certified_round_trip_allowed(self):
        p, http = _build(certified=True)
        http.enqueue(_duffel_response([_offer_round_trip()]))
        result = p.search_flights(_round_trip_req())
        assert result.status is FlightSourceStatus.OK

    def test_trust_gate_failures_still_unavailable_when_uncertified(self):
        # Trust gate failure path returns UNAVAILABLE for a different reason
        # (all offers failed trust gate), not the certification reason.
        # Either way: no visible cards.
        p, http = _build(certified=False)
        bad_offer = _offer_one_way()
        bad_offer["total_amount"] = None
        http.enqueue(_duffel_response([bad_offer]))
        result = p.search_flights(_one_way_req())
        assert result.status is FlightSourceStatus.UNAVAILABLE
        assert result.rows == []

    def test_duffel_certified_from_env_returns_false_by_default(self):
        assert duffel_certified_from_env({}) is False
        assert duffel_certified_from_env({"DUFFEL_SCHEDULE_TRUST_CERTIFIED": "0"}) is False
        assert duffel_certified_from_env({"DUFFEL_SCHEDULE_TRUST_CERTIFIED": "false"}) is False

    def test_duffel_certified_from_env_returns_true_when_set(self):
        assert duffel_certified_from_env({"DUFFEL_SCHEDULE_TRUST_CERTIFIED": "1"}) is True
        assert duffel_certified_from_env({"DUFFEL_SCHEDULE_TRUST_CERTIFIED": "true"}) is True
        assert duffel_certified_from_env({"DUFFEL_SCHEDULE_TRUST_CERTIFIED": "yes"}) is True

    def test_build_from_env_uncertified_by_default(self):
        env = {"DUFFEL_API_KEY": "k", "DUFFEL_FLIGHTS_ENABLED": "1"}
        p = build_duffel_provider_from_env(env)
        assert p is not None
        assert p._certified is False

    def test_build_from_env_certified_when_flag_set(self):
        env = {
            "DUFFEL_API_KEY": "k",
            "DUFFEL_FLIGHTS_ENABLED": "1",
            "DUFFEL_SCHEDULE_TRUST_CERTIFIED": "1",
        }
        p = build_duffel_provider_from_env(env)
        assert p is not None
        assert p._certified is True


# ── 15. Debug logging ─────────────────────────────────────────────────────────

@requires_full_stack
class TestDebugLogging:
    """DUFFEL_DEBUG=true logs compact non-sensitive summaries; off by default."""

    def test_no_debug_log_when_flag_absent(self, monkeypatch, caplog):
        monkeypatch.delenv("DUFFEL_DEBUG", raising=False)
        import logging
        with caplog.at_level(logging.DEBUG, logger="app.services.flights_provider_duffel"):
            p, http = _build(certified=True)
            http.enqueue(_duffel_response([_offer_one_way()]))
            p.search_flights(_one_way_req())
        debug_msgs = [r for r in caplog.records if "[duffel.accepted]" in r.message]
        assert debug_msgs == []

    def test_debug_log_emitted_when_flag_set(self, monkeypatch, caplog):
        monkeypatch.setenv("DUFFEL_DEBUG", "true")
        import logging
        with caplog.at_level(logging.DEBUG, logger="app.services.flights_provider_duffel"):
            p, http = _build(certified=True)
            http.enqueue(_duffel_response([_offer_one_way()]))
            p.search_flights(_one_way_req())
        debug_msgs = [r for r in caplog.records if "[duffel.accepted]" in r.message]
        assert len(debug_msgs) >= 1

    def test_debug_log_contains_route_and_price(self, monkeypatch, caplog):
        monkeypatch.setenv("DUFFEL_DEBUG", "true")
        import logging
        with caplog.at_level(logging.DEBUG, logger="app.services.flights_provider_duffel"):
            p, http = _build(certified=True)
            http.enqueue(_duffel_response([_offer_one_way()]))
            p.search_flights(_one_way_req())
        debug_msgs = [r for r in caplog.records if "[duffel.accepted]" in r.message]
        assert debug_msgs, "Expected at least one accepted-offer debug log"
        msg = debug_msgs[0].message
        assert "SEA" in msg
        assert "LAX" in msg
        assert "189.5" in msg or "189" in msg

    def test_debug_log_does_not_contain_api_key(self, monkeypatch, caplog):
        monkeypatch.setenv("DUFFEL_DEBUG", "true")
        import logging
        with caplog.at_level(logging.DEBUG, logger="app.services.flights_provider_duffel"):
            p, http = _build(api_key="SUPERSECRET-KEY", certified=True)
            http.enqueue(_duffel_response([_offer_one_way()]))
            p.search_flights(_one_way_req())
        all_messages = " ".join(r.message for r in caplog.records)
        assert "SUPERSECRET-KEY" not in all_messages
