"""SearchService → FlightProvider wiring (Flights v1).

Proves:

- ``SearchService.search_flights`` does NOT call ``_mock_flights`` anymore.
- It delegates to ``get_flight_provider()`` and returns provider rows.
- When the provider is ``UNAVAILABLE`` / ``EMPTY`` / ``ERROR`` the route
  returns zero rows (fail-closed) instead of fabricated mocks.
- ``search_round_trip_flights`` still pairs outbound + return rows.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from app.contracts.flights import FlightSourceStatus
from app.models.search import (
    BookingOption,
    FlightResult,
    FlightSearchRequest,
)
from app.services import search as search_service
from app.services.flights_provider import FlightProviderResult
from app.services.search import SearchService


def _provider_row(idx: int = 1, *, price: float = 499.0,
                  origin: str = "JFK", destination: str = "CDG") -> FlightResult:
    return FlightResult(
        id=f"amadeus-{idx}",
        price=price,
        location=f"{origin}→{destination}",
        booking_url="",
        source="duffel",
        booking_options=[],
        airline="American Airlines",
        flight_number=f"AA{100 + idx}",
        origin=origin,
        destination=destination,
        departure_time=datetime(2026, 6, 1, 9, 0),
        arrival_time=datetime(2026, 6, 1, 21, 0),
        duration_minutes=720,
        stops=0,
        cabin_class="economy",
    )


def _empty_db():
    db = MagicMock()
    table = MagicMock()
    chain = MagicMock()
    chain.execute.return_value = MagicMock(data=[])
    table.select.return_value = chain
    chain.eq.return_value = chain
    chain.gt.return_value = chain
    chain.limit.return_value = chain
    chain.order.return_value = chain
    chain.maybe_single.return_value = chain
    db.table.return_value = table
    table.insert.return_value = chain
    table.upsert.return_value = chain
    table.delete.return_value = chain
    return db


class _StaticProvider:
    def __init__(self, result: FlightProviderResult):
        self.result = result
        self.calls: List[FlightSearchRequest] = []

    def search_flights(self, req: FlightSearchRequest) -> FlightProviderResult:
        self.calls.append(req)
        return self.result


def test_search_flights_uses_provider_and_does_not_call_mock():
    provider = _StaticProvider(
        FlightProviderResult(status=FlightSourceStatus.OK, rows=[_provider_row(1)])
    )
    svc = SearchService(_empty_db())
    with patch.object(search_service, "_mock_flights",
                      side_effect=AssertionError("must not be called")) as mock_call:
        with patch("app.services.flights_provider.get_flight_provider",
                   return_value=provider):
            results = svc.search_flights(FlightSearchRequest(
                origin="JFK", destination="CDG",
                departure_date=date(2026, 6, 1),
            ))
        assert mock_call.called is False
    assert len(results) == 1
    assert results[0].source == "duffel"
    assert len(provider.calls) == 1


@pytest.mark.parametrize("status,reason", [
    (FlightSourceStatus.UNAVAILABLE, "no provider configured"),
    (FlightSourceStatus.ERROR, "500"),
])
def test_search_flights_non_ok_status_returns_zero_rows(status, reason):
    provider = _StaticProvider(
        FlightProviderResult(status=status, rows=[], reason=reason)
    )
    svc = SearchService(_empty_db())
    with patch.object(search_service, "_mock_flights",
                      side_effect=AssertionError("must not be called")):
        with patch("app.services.flights_provider.get_flight_provider",
                   return_value=provider):
            out = svc.search_flights(FlightSearchRequest(
                origin="JFK", destination="CDG",
                departure_date=date(2026, 6, 1),
            ))
    assert out == []


def test_default_null_provider_results_in_zero_rows(monkeypatch):
    monkeypatch.delenv("DUFFEL_FLIGHTS_ENABLED", raising=False)
    monkeypatch.delenv("DUFFEL_API_KEY", raising=False)
    monkeypatch.delenv("DUFFEL_BASE_URL", raising=False)
    monkeypatch.delenv("IGNAV_API_KEY", raising=False)
    monkeypatch.delenv("IGNAV_FLIGHTS_ENABLED", raising=False)
    from app.services.flights_provider import reset_flight_provider_cache
    reset_flight_provider_cache()
    svc = SearchService(_empty_db())
    with patch.object(search_service, "_mock_flights",
                      side_effect=AssertionError("must not be called")):
        out = svc.search_flights(FlightSearchRequest(
            origin="JFK", destination="CDG",
            departure_date=date(2026, 6, 1),
        ))
    assert out == []


def test_round_trip_pairs_preserved_with_provider_rows():
    outbound = _provider_row(1, origin="JFK", destination="CDG", price=500.0)
    ret = _provider_row(2, origin="CDG", destination="JFK", price=400.0)

    class _DirectionalProvider:
        def search_flights(self, req: FlightSearchRequest) -> FlightProviderResult:
            if req.origin == "JFK":
                return FlightProviderResult(
                    status=FlightSourceStatus.OK, rows=[outbound],
                )
            return FlightProviderResult(
                status=FlightSourceStatus.OK, rows=[ret],
            )

    svc = SearchService(_empty_db())
    with patch.object(search_service, "_mock_flights",
                      side_effect=AssertionError("must not be called")):
        with patch("app.services.flights_provider.get_flight_provider",
                   return_value=_DirectionalProvider()):
            pairs = svc.search_round_trip_flights(FlightSearchRequest(
                origin="JFK", destination="CDG",
                departure_date=date(2026, 6, 1),
                return_date=date(2026, 6, 7),
            ))
    assert len(pairs) == 1
    pair = pairs[0]
    assert pair.outbound.origin == "JFK" and pair.outbound.destination == "CDG"
    assert pair.return_flight.origin == "CDG" and pair.return_flight.destination == "JFK"
    assert pair.total_price == 900.0


def test_round_trip_pair_count_is_capped_and_shape_preserved():
    class _ManyProvider:
        def search_flights(self, req: FlightSearchRequest) -> FlightProviderResult:
            rows = [_provider_row(i, origin=req.origin or "JFK", destination=req.destination or "CDG", price=300.0 + i) for i in range(1, 20)]
            return FlightProviderResult(status=FlightSourceStatus.OK, rows=rows)

    svc = SearchService(_empty_db())
    with patch("app.services.flights_provider.get_flight_provider", return_value=_ManyProvider()):
        pairs = svc.search_round_trip_flights(FlightSearchRequest(
            origin="JFK", destination="CDG",
            departure_date=date(2026, 6, 1),
            return_date=date(2026, 6, 7),
        ))

    assert 1 <= len(pairs) <= 30
    sample = pairs[0]
    assert sample.outbound.origin == "JFK"
    assert sample.return_flight.destination == "JFK"
