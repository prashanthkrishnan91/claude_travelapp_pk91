from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional, Tuple

from app.contracts.flights import FlightSourceStatus
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
        self.calls = []
        self.offer_responses = []

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
            access_token="tok",
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


def _payload(*, with_operating: bool = False):
    seg = {
        "origin": {"iata_code": "JFK"},
        "destination": {"iata_code": "CDG"},
        "departing_at": "2026-06-01T09:00:00Z",
        "arriving_at": "2026-06-01T17:00:00Z",
        "marketing_carrier": {"iata_code": "AA", "name": "American Airlines"},
        "marketing_carrier_flight_number": "100",
    }
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
    assert duffel_enabled_from_env({"DUFFEL_FLIGHTS_ENABLED": "true"}) is False
    assert duffel_enabled_from_env({"DUFFEL_ACCESS_TOKEN": "x"}) is False
    assert (
        duffel_enabled_from_env(
            {"DUFFEL_FLIGHTS_ENABLED": "true", "DUFFEL_ACCESS_TOKEN": "x"}
        )
        is True
    )
    assert (
        build_duffel_provider_from_env(
            {"DUFFEL_FLIGHTS_ENABLED": "true", "DUFFEL_ACCESS_TOKEN": "x"}
        )
        is not None
    )


def test_get_flight_provider_uses_duffel(monkeypatch):
    monkeypatch.setenv("DUFFEL_FLIGHTS_ENABLED", "true")
    monkeypatch.setenv("DUFFEL_ACCESS_TOKEN", "abc")
    reset_flight_provider_cache()
    p = get_flight_provider()
    assert isinstance(p, DuffelFlightProvider)
    assert get_flight_provider() is p


def test_get_flight_provider_null_when_disabled(monkeypatch):
    monkeypatch.delenv("DUFFEL_FLIGHTS_ENABLED", raising=False)
    monkeypatch.delenv("DUFFEL_ACCESS_TOKEN", raising=False)
    reset_flight_provider_cache()
    assert isinstance(get_flight_provider(), NullFlightProvider)


def test_duffel_success_mapping_accepts_201():
    p, http = _build()
    http.offer_responses = [_FakeResponse(201, payload=_payload())]
    r = p.search_flights(_req())
    assert r.status is FlightSourceStatus.OK and len(r.rows) == 1
    row = r.rows[0]
    assert row.source == "duffel" and row.airline == "American Airlines" and row.origin == "JFK"


def test_duffel_prefers_operating_carrier_name_for_display():
    p, http = _build()
    http.offer_responses = [_FakeResponse(200, payload=_payload(with_operating=True))]
    row = p.search_flights(_req()).rows[0]
    assert row.airline == "British Airways"


def test_duffel_request_uses_offer_params_and_supplier_timeout():
    p, http = _build()
    http.offer_responses = [_FakeResponse(200, payload=_payload())]
    p.search_flights(_req())
    _url, params, _json, _headers = http.calls[0]
    assert params["return_offers"] == "true"
    assert params["view"] == "offers"
    assert params["supplier_timeout"] == "6000"


def test_duffel_non_2xx_and_empty_fail_closed():
    p, http = _build()
    http.offer_responses = [_FakeResponse(500, text="err")]
    assert p.search_flights(_req()).status is FlightSourceStatus.ERROR

    p, http = _build()
    http.offer_responses = [_FakeResponse(200, payload={"data": {"offers": []}})]
    assert p.search_flights(_req()).status is FlightSourceStatus.EMPTY
