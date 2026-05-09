"""Amadeus Flight Provider — unit tests for Flights v1.

These tests exercise the adapter with mocked HTTP responses; no real
network calls are made.  They assert the Flights Product Contract v1
invariants:

- ``UNAVAILABLE`` with zero rows when disabled or credentials missing
- OAuth token cached and reused until near expiry
- Flight Offers Search params map correctly
- Happy-path offer maps to ``FlightProviderResult(status=OK, rows=[...])``
- Mapped rows satisfy ``assert_persistable_flight``
- Empty Amadeus result maps to ``EMPTY``
- Transport / parse / non-200 errors map to ``ERROR``
- Mock/fabricated candidate rows are rejected
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import pytest

from app.contracts.flights import (
    FlightSourceStatus,
    is_persistable_flight,
)
from app.models.search import FlightSearchRequest
from app.services.flights_provider import (
    FlightProviderResult,
    NullFlightProvider,
    get_flight_provider,
    reset_flight_provider_cache,
)
from app.services.flights_provider_amadeus import (
    AmadeusFlightProvider,
    amadeus_enabled_from_env,
    build_amadeus_provider_from_env,
    _map_offer_to_outbound,
    _parse_iso_duration,
)


# ---------------------------------------------------------------------------
# Fake HTTP client / clock
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code: int, payload: Optional[Dict[str, Any]] = None,
                 text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text or ""

    def json(self) -> Dict[str, Any]:
        if self._payload is None:
            raise ValueError("no json payload")
        return self._payload


class _FakeHttpClient:
    """Captures requests and replays scripted responses."""

    def __init__(self) -> None:
        self.calls: List[Tuple[str, str, Dict[str, Any]]] = []
        self.token_responses: List[_FakeResponse] = []
        self.offer_responses: List[_FakeResponse] = []

    def post(self, url: str, data: Optional[Dict[str, Any]] = None,
             headers: Optional[Dict[str, str]] = None) -> _FakeResponse:
        self.calls.append(("POST", url, {"data": dict(data or {}),
                                          "headers": dict(headers or {})}))
        if not self.token_responses:
            return _FakeResponse(500, text="no scripted token response")
        return self.token_responses.pop(0)

    def get(self, url: str, params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None) -> _FakeResponse:
        self.calls.append(("GET", url, {"params": dict(params or {}),
                                         "headers": dict(headers or {})}))
        if not self.offer_responses:
            return _FakeResponse(500, text="no scripted offer response")
        return self.offer_responses.pop(0)


class _FakeClock:
    def __init__(self, start: float = 1_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:  # behaves like time.time
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _build_provider() -> Tuple[AmadeusFlightProvider, _FakeHttpClient, _FakeClock]:
    http = _FakeHttpClient()
    clock = _FakeClock()
    provider = AmadeusFlightProvider(
        client_id="test-id",
        client_secret="test-secret",
        base_url="https://test.api.amadeus.example",
        http_client=http,
        clock=clock,
    )
    return provider, http, clock


def _token_response(access: str = "abc", expires_in: int = 1799) -> _FakeResponse:
    return _FakeResponse(200, payload={"access_token": access, "expires_in": expires_in})


def _offer_payload(*, carriers=None, offers=None) -> Dict[str, Any]:
    return {
        "data": offers or [],
        "dictionaries": {"carriers": carriers or {}},
    }


def _aa_offer(offer_id: str = "off1", price: str = "499.00") -> Dict[str, Any]:
    return {
        "id": offer_id,
        "itineraries": [
            {
                "duration": "PT12H0M",
                "segments": [
                    {
                        "departure": {"iataCode": "JFK", "at": "2026-06-01T09:00:00"},
                        "arrival": {"iataCode": "CDG", "at": "2026-06-01T21:00:00"},
                        "carrierCode": "AA",
                        "number": "100",
                    },
                ],
            },
        ],
        "price": {"grandTotal": price, "currency": "USD"},
    }


def _req() -> FlightSearchRequest:
    return FlightSearchRequest(
        origin="JFK",
        destination="CDG",
        departure_date=date(2026, 6, 1),
        passengers=1,
        cabin_class="economy",
    )


# ---------------------------------------------------------------------------
# Env gating
# ---------------------------------------------------------------------------


def test_amadeus_disabled_when_flag_off():
    env = {"AMADEUS_CLIENT_ID": "x", "AMADEUS_CLIENT_SECRET": "y"}
    assert amadeus_enabled_from_env(env) is False
    assert build_amadeus_provider_from_env(env) is None


def test_amadeus_disabled_when_creds_missing():
    env = {"AMADEUS_FLIGHTS_ENABLED": "true"}
    assert amadeus_enabled_from_env(env) is False
    assert build_amadeus_provider_from_env(env) is None


def test_amadeus_enabled_when_creds_and_flag_present():
    env = {
        "AMADEUS_CLIENT_ID": "x",
        "AMADEUS_CLIENT_SECRET": "y",
        "AMADEUS_FLIGHTS_ENABLED": "true",
    }
    assert amadeus_enabled_from_env(env) is True
    provider = build_amadeus_provider_from_env(env)
    assert isinstance(provider, AmadeusFlightProvider)


def test_default_get_flight_provider_is_null_without_env(monkeypatch):
    monkeypatch.delenv("AMADEUS_FLIGHTS_ENABLED", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_ID", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_SECRET", raising=False)
    reset_flight_provider_cache()
    assert isinstance(get_flight_provider(), NullFlightProvider)


def test_get_flight_provider_returns_amadeus_when_configured(monkeypatch):
    monkeypatch.setenv("AMADEUS_FLIGHTS_ENABLED", "true")
    monkeypatch.setenv("AMADEUS_CLIENT_ID", "abc")
    monkeypatch.setenv("AMADEUS_CLIENT_SECRET", "def")
    reset_flight_provider_cache()
    provider = get_flight_provider()
    assert isinstance(provider, AmadeusFlightProvider)
    # Memoisation: same instance on repeat
    assert get_flight_provider() is provider
    reset_flight_provider_cache()


# ---------------------------------------------------------------------------
# Token cache
# ---------------------------------------------------------------------------


def test_token_fetched_once_and_reused():
    provider, http, clock = _build_provider()
    http.token_responses = [_token_response("tok-1", expires_in=1800)]
    http.offer_responses = [
        _FakeResponse(200, payload=_offer_payload(
            carriers={"AA": "American Airlines"},
            offers=[_aa_offer("o1")],
        )),
        _FakeResponse(200, payload=_offer_payload(
            carriers={"AA": "American Airlines"},
            offers=[_aa_offer("o2")],
        )),
    ]

    r1 = provider.search_flights(_req())
    r2 = provider.search_flights(_req())
    assert r1.status is FlightSourceStatus.OK
    assert r2.status is FlightSourceStatus.OK

    posts = [c for c in http.calls if c[0] == "POST"]
    assert len(posts) == 1, "token must be fetched only once when still valid"


def test_token_refetched_after_expiry():
    provider, http, clock = _build_provider()
    http.token_responses = [
        _token_response("tok-1", expires_in=120),
        _token_response("tok-2", expires_in=1800),
    ]
    http.offer_responses = [
        _FakeResponse(200, payload=_offer_payload(offers=[_aa_offer("o1")],
                                                   carriers={"AA": "American"})),
        _FakeResponse(200, payload=_offer_payload(offers=[_aa_offer("o2")],
                                                   carriers={"AA": "American"})),
    ]

    provider.search_flights(_req())
    clock.advance(200)  # past 120 - 60 leeway
    provider.search_flights(_req())

    posts = [c for c in http.calls if c[0] == "POST"]
    assert len(posts) == 2


# ---------------------------------------------------------------------------
# Param mapping
# ---------------------------------------------------------------------------


def test_flight_offers_request_maps_params_correctly():
    provider, http, _clock = _build_provider()
    http.token_responses = [_token_response()]
    http.offer_responses = [
        _FakeResponse(200, payload=_offer_payload(
            offers=[_aa_offer("o1")], carriers={"AA": "American"},
        )),
    ]
    req = FlightSearchRequest(
        origin="jfk",
        destination="cdg",
        departure_date=date(2026, 6, 1),
        return_date=date(2026, 6, 7),
        passengers=2,
        cabin_class="business",
    )
    provider.search_flights(req)

    gets = [c for c in http.calls if c[0] == "GET"]
    assert len(gets) == 1
    _, _url, ctx = gets[0]
    p = ctx["params"]
    assert p["originLocationCode"] == "JFK"
    assert p["destinationLocationCode"] == "CDG"
    assert p["departureDate"] == "2026-06-01"
    assert p["returnDate"] == "2026-06-07"
    assert p["adults"] == 2
    assert p["currencyCode"] == "USD"
    assert p["travelClass"] == "BUSINESS"
    assert 1 <= p["max"] <= 10
    assert ctx["headers"].get("Authorization", "").startswith("Bearer ")


# ---------------------------------------------------------------------------
# Happy path / contract safety
# ---------------------------------------------------------------------------


def test_happy_path_offer_maps_to_persistable_row():
    provider, http, _clock = _build_provider()
    http.token_responses = [_token_response()]
    http.offer_responses = [
        _FakeResponse(200, payload=_offer_payload(
            offers=[_aa_offer("offer-A")],
            carriers={"AA": "American Airlines"},
        )),
    ]

    result = provider.search_flights(_req())
    assert isinstance(result, FlightProviderResult)
    assert result.status is FlightSourceStatus.OK
    assert len(result.rows) == 1
    row = result.rows[0]
    assert row.source == "amadeus"
    assert row.airline == "American Airlines"
    assert row.flight_number == "AA100"
    assert row.origin == "JFK"
    assert row.destination == "CDG"
    assert row.duration_minutes == 720
    assert row.stops == 0
    assert row.price == 499.0
    # No fabricated booking URL was invented.
    assert row.booking_url == ""
    assert row.booking_options == []
    assert is_persistable_flight(row) is True


def test_carrier_fallback_to_code_when_dictionary_missing():
    provider, http, _clock = _build_provider()
    http.token_responses = [_token_response()]
    http.offer_responses = [
        _FakeResponse(200, payload=_offer_payload(
            offers=[_aa_offer("offer-X")],
            carriers={},  # no carrier dictionary
        )),
    ]
    result = provider.search_flights(_req())
    assert result.status is FlightSourceStatus.OK
    assert result.rows[0].airline == "AA"
    assert is_persistable_flight(result.rows[0]) is True


def test_empty_amadeus_result_maps_to_empty():
    provider, http, _clock = _build_provider()
    http.token_responses = [_token_response()]
    http.offer_responses = [
        _FakeResponse(200, payload=_offer_payload(offers=[])),
    ]
    result = provider.search_flights(_req())
    assert result.status is FlightSourceStatus.EMPTY
    assert result.rows == []


def test_http_500_maps_to_error():
    provider, http, _clock = _build_provider()
    http.token_responses = [_token_response()]
    http.offer_responses = [_FakeResponse(500, text="upstream broken")]
    result = provider.search_flights(_req())
    assert result.status is FlightSourceStatus.ERROR
    assert result.rows == []
    assert "500" in result.reason


def test_transport_error_maps_to_error():
    provider, http, _clock = _build_provider()
    http.token_responses = [_token_response()]

    def boom(*args, **kwargs):
        raise RuntimeError("connection refused")

    http.get = boom  # type: ignore[assignment]
    result = provider.search_flights(_req())
    assert result.status is FlightSourceStatus.ERROR
    assert result.rows == []


def test_parse_error_maps_to_error():
    provider, http, _clock = _build_provider()
    http.token_responses = [_token_response()]

    bad = _FakeResponse(200, payload=None, text="not-json")
    http.offer_responses = [bad]
    result = provider.search_flights(_req())
    assert result.status is FlightSourceStatus.ERROR


def test_token_unavailable_maps_to_unavailable():
    provider, http, _clock = _build_provider()
    http.token_responses = [_FakeResponse(401, text="bad creds")]
    result = provider.search_flights(_req())
    assert result.status is FlightSourceStatus.UNAVAILABLE
    assert result.rows == []


def test_401_on_offers_triggers_single_token_retry():
    provider, http, _clock = _build_provider()
    http.token_responses = [
        _token_response("tok-1", expires_in=1800),
        _token_response("tok-2", expires_in=1800),
    ]
    http.offer_responses = [
        _FakeResponse(401, text="expired"),
        _FakeResponse(200, payload=_offer_payload(
            offers=[_aa_offer("o1")], carriers={"AA": "American"},
        )),
    ]
    result = provider.search_flights(_req())
    assert result.status is FlightSourceStatus.OK
    posts = [c for c in http.calls if c[0] == "POST"]
    gets = [c for c in http.calls if c[0] == "GET"]
    assert len(posts) == 2  # initial + refresh
    assert len(gets) == 2   # initial 401 + retry 200


def test_missing_iata_returns_empty():
    provider, http, _clock = _build_provider()
    req = FlightSearchRequest(
        origin_airports=[],
        destination_airports=[],
        departure_date=date(2026, 6, 1),
    )
    # all_origins/all_destinations are empty — but our guard for empty
    # origin/destination short-circuits before any HTTP call.
    result = provider.search_flights(req)
    assert result.status is FlightSourceStatus.EMPTY
    assert http.calls == []


# ---------------------------------------------------------------------------
# Contract guard: malformed offers must not slip through
# ---------------------------------------------------------------------------


def test_offer_missing_required_fields_is_skipped():
    bad = {"id": "x", "itineraries": [{"segments": []}]}
    out = _map_offer_to_outbound(bad, {}, "economy")
    assert out is None


def test_provider_skips_uncontract_safe_offer_and_returns_empty():
    provider, http, _clock = _build_provider()
    http.token_responses = [_token_response()]
    bad = {
        "id": "z",
        "itineraries": [{
            "segments": [{
                "departure": {"iataCode": "", "at": ""},
                "arrival": {"iataCode": "", "at": ""},
                "carrierCode": "",
                "number": "",
            }],
        }],
        "price": {"grandTotal": "100"},
    }
    http.offer_responses = [
        _FakeResponse(200, payload=_offer_payload(offers=[bad])),
    ]
    result = provider.search_flights(_req())
    assert result.status is FlightSourceStatus.EMPTY
    assert result.rows == []


def test_provider_result_rejects_mock_source_via_contract():
    """If a future bug ever produced a row with source=mock or a
    book.example.com URL, ``FlightProviderResult(status=OK, rows=[...])``
    would refuse it.  Cross-check via the contract directly."""
    from app.models.search import FlightResult
    from datetime import datetime
    bad = FlightResult(
        id="b1",
        location="JFK→CDG",
        booking_url="https://book.example.com/x",
        source="amadeus",
        booking_options=[],
        airline="American",
        flight_number="AA100",
        origin="JFK",
        destination="CDG",
        departure_time=datetime(2026, 6, 1, 9, 0),
        arrival_time=datetime(2026, 6, 1, 21, 0),
        duration_minutes=720,
        cabin_class="economy",
    )
    with pytest.raises(ValueError):
        FlightProviderResult(status=FlightSourceStatus.OK, rows=[bad])


# ---------------------------------------------------------------------------
# ISO duration parser
# ---------------------------------------------------------------------------


def test_parse_iso_duration():
    assert _parse_iso_duration("PT12H0M") == 720
    assert _parse_iso_duration("PT5H30M") == 330
    assert _parse_iso_duration("PT45M") == 45
    assert _parse_iso_duration("PT2H") == 120
    assert _parse_iso_duration(None) is None
    assert _parse_iso_duration("garbage") is None
