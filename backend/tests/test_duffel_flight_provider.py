"""Duffel flight provider — legacy test suite updated for Duffel v1 (search-only).

Migrated from the pre-v1 adapter that returned FlightResult (legacy shape) to
the new adapter that returns FlightItineraryOffer (canonical shape).
Full coverage lives in test_duffel_flights_v1.py; this file retains the
original test IDs for backward compatibility.

Guarded with requires_full_stack; skips gracefully in the minimal harness
(pydantic not installed) and runs in the full Railway/Docker environment.
"""
from __future__ import annotations

import pytest
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

_full_stack = True
try:
    from app.contracts.flights import FlightSourceStatus
    from app.contracts.flight_offer import BookingLinkType, FlightItineraryOffer
    from app.models.search import FlightSearchRequest
    from app.services.flights_provider import (
        NullFlightProvider,
        get_flight_provider,
        reset_flight_provider_cache,
    )
    from app.services.flights_provider_duffel import (
        DuffelFlightProvider,
        build_duffel_provider_from_env,
        duffel_enabled_from_env,
    )
except (ImportError, ModuleNotFoundError):
    _full_stack = False
    FlightSourceStatus = None  # type: ignore[assignment,misc]
    BookingLinkType = None  # type: ignore[assignment,misc]
    FlightItineraryOffer = None  # type: ignore[assignment,misc]
    FlightSearchRequest = None  # type: ignore[assignment,misc]
    NullFlightProvider = None  # type: ignore[assignment,misc]
    get_flight_provider = None  # type: ignore[assignment]
    reset_flight_provider_cache = None  # type: ignore[assignment]
    DuffelFlightProvider = None  # type: ignore[assignment,misc]
    build_duffel_provider_from_env = None  # type: ignore[assignment]
    duffel_enabled_from_env = None  # type: ignore[assignment]

requires_full_stack = pytest.mark.skipif(
    not _full_stack,
    reason="Skipped in minimal test harness; run in full Railway/Docker stack.",
)

pytestmark = requires_full_stack


class _FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: Optional[Dict[str, Any]] = None,
        text: str = "",
    ):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class _FakeHttpClient:
    def __init__(self):
        self.calls: List[Tuple] = []
        self.offer_responses: List[_FakeResponse] = []

    def post(
        self,
        url: str,
        params: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.calls.append((url, params or {}, json or {}, headers or {}))
        return self.offer_responses.pop(0)


def _build() -> Tuple[DuffelFlightProvider, _FakeHttpClient]:
    http = _FakeHttpClient()
    return (
        DuffelFlightProvider(
            api_key="tok",
            base_url="https://duffel.test",
            http_client=http,
        ),
        http,
    )


def _req():
    return FlightSearchRequest(
        origin="JFK",
        destination="CDG",
        departure_date=date(2026, 6, 1),
        passengers=1,
        cabin_class="economy",
    )


def _seg(origin: str = "JFK", destination: str = "CDG",
         carrier_iata: str = "AA", carrier_name: str = "American Airlines",
         flight_num: str = "100") -> Dict[str, Any]:
    return {
        "origin": {"iata_code": origin},
        "destination": {"iata_code": destination},
        "departing_at": "2026-06-01T09:00:00Z",
        "arriving_at": "2026-06-01T17:00:00Z",
        "marketing_carrier": {"iata_code": carrier_iata, "name": carrier_name},
        "marketing_carrier_flight_number": flight_num,
        "duration": "PT8H0M",
    }


def _payload(*, with_operating: bool = False):
    seg = _seg()
    if with_operating:
        seg["operating_carrier"] = {"iata_code": "BA", "name": "British Airways"}
    return {
        "data": {
            "offers": [
                {
                    "id": "off1",
                    "total_amount": "455.50",
                    "total_currency": "USD",
                    "slices": [{"duration": "PT8H0M", "segments": [seg]}],
                }
            ]
        }
    }


def test_duffel_env_gating():
    # DUFFEL_API_KEY (not DUFFEL_ACCESS_TOKEN) is the required env var in v1.
    assert duffel_enabled_from_env({"DUFFEL_FLIGHTS_ENABLED": "true"}) is False
    assert duffel_enabled_from_env({"DUFFEL_API_KEY": "x"}) is False
    assert (
        duffel_enabled_from_env(
            {"DUFFEL_FLIGHTS_ENABLED": "true", "DUFFEL_API_KEY": "x"}
        )
        is True
    )
    assert (
        build_duffel_provider_from_env(
            {"DUFFEL_FLIGHTS_ENABLED": "true", "DUFFEL_API_KEY": "x"}
        )
        is not None
    )


def test_get_flight_provider_uses_duffel(monkeypatch):
    monkeypatch.setenv("DUFFEL_FLIGHTS_ENABLED", "true")
    monkeypatch.setenv("DUFFEL_API_KEY", "abc")
    reset_flight_provider_cache()
    p = get_flight_provider()
    assert isinstance(p, DuffelFlightProvider)
    assert get_flight_provider() is p


def test_get_flight_provider_null_when_disabled(monkeypatch):
    monkeypatch.delenv("DUFFEL_FLIGHTS_ENABLED", raising=False)
    monkeypatch.delenv("DUFFEL_API_KEY", raising=False)
    reset_flight_provider_cache()
    assert isinstance(get_flight_provider(), NullFlightProvider)


def test_duffel_success_mapping_accepts_201():
    p, http = _build()
    http.offer_responses = [_FakeResponse(201, payload=_payload())]
    r = p.search_flights(_req())
    assert r.status is FlightSourceStatus.OK and len(r.rows) == 1
    offer = r.rows[0]
    assert isinstance(offer, FlightItineraryOffer)
    assert offer.provider == "duffel_flights"
    assert offer.outbound_leg.origin == "JFK"
    assert offer.outbound_leg.segments[0].airline == "American Airlines"


def test_duffel_prefers_operating_carrier_name_for_display():
    p, http = _build()
    http.offer_responses = [_FakeResponse(200, payload=_payload(with_operating=True))]
    offer = p.search_flights(_req()).rows[0]
    # operating carrier name takes precedence for display
    assert offer.outbound_leg.segments[0].airline == "British Airways"


def test_duffel_request_uses_offer_params_and_supplier_timeout():
    p, http = _build()
    http.offer_responses = [_FakeResponse(200, payload=_payload())]
    p.search_flights(_req())
    _url, params, _json, _headers = http.calls[0]
    assert params["return_offers"] == "true"
    assert params["supplier_timeout"] == "9000"


def test_duffel_non_2xx_and_empty_fail_closed():
    p, http = _build()
    http.offer_responses = [_FakeResponse(500, text="err")]
    assert p.search_flights(_req()).status is FlightSourceStatus.ERROR

    p, http = _build()
    http.offer_responses = [_FakeResponse(200, payload={"data": {"offers": []}})]
    assert p.search_flights(_req()).status is FlightSourceStatus.EMPTY


def test_duffel_booking_link_always_unavailable():
    p, http = _build()
    http.offer_responses = [_FakeResponse(200, payload=_payload())]
    offer = p.search_flights(_req()).rows[0]
    assert offer.booking_link.link_type is BookingLinkType.UNAVAILABLE
    assert offer.booking_link.url == ""
