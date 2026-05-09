"""SearchService → HotelProvider wiring (Hotels v1).

Proves:

- ``SearchService.search_hotels`` does NOT call ``_mock_hotels`` anymore.
- It delegates to ``get_hotel_provider()`` and returns provider rows.
- When the provider is ``UNAVAILABLE`` / ``EMPTY`` / ``ERROR`` the route
  returns zero rows (fail-closed) instead of fabricated mocks.
"""
from __future__ import annotations

from datetime import date
from typing import List
from unittest.mock import MagicMock, patch

from app.contracts.hotels import HotelSourceStatus
from app.models.search import HotelResult, HotelSearchRequest
from app.services import search as search_service
from app.services.hotels_provider import (
    HotelProviderResult,
    NullHotelProvider,
)
from app.services.search import SearchService


def _gp_hotel(idx: int = 1) -> HotelResult:
    return HotelResult(
        id=f"gp-{idx}",
        location="Paris, FR",
        booking_url=f"https://maps.google.com/?cid={idx}",
        source="google_places",
        booking_options=[],
        name=f"Hotel {idx}",
        check_in=date(2026, 6, 1),
        check_out=date(2026, 6, 5),
        nights=4,
        amenities=[],
        price_per_night=0.0,
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
    def __init__(self, result: HotelProviderResult):
        self.result = result
        self.calls: List[HotelSearchRequest] = []

    def search_hotels(self, req: HotelSearchRequest) -> HotelProviderResult:
        self.calls.append(req)
        return self.result


def _req():
    return HotelSearchRequest(
        location="Paris", check_in=date(2026, 6, 1), check_out=date(2026, 6, 5)
    )


def test_search_hotels_uses_provider_and_does_not_call_mock():
    provider = _StaticProvider(
        HotelProviderResult(status=HotelSourceStatus.OK, rows=[_gp_hotel(1)])
    )
    svc = SearchService(_empty_db())
    with patch.object(search_service, "_mock_hotels",
                      side_effect=AssertionError("must not be called")) as mock_call:
        with patch("app.services.hotels_provider.get_hotel_provider",
                   return_value=provider):
            results = svc.search_hotels(_req())
        assert mock_call.called is False
    assert len(results) == 1
    assert results[0].source == "google_places"
    assert len(provider.calls) == 1


def test_search_hotels_unavailable_returns_zero_rows():
    provider = _StaticProvider(
        HotelProviderResult(
            status=HotelSourceStatus.UNAVAILABLE,
            rows=[],
            reason="no provider configured",
        )
    )
    svc = SearchService(_empty_db())
    with patch.object(search_service, "_mock_hotels",
                      side_effect=AssertionError("must not be called")):
        with patch("app.services.hotels_provider.get_hotel_provider",
                   return_value=provider):
            out = svc.search_hotels(_req())
    assert out == []


def test_search_hotels_error_returns_zero_rows():
    provider = _StaticProvider(
        HotelProviderResult(status=HotelSourceStatus.ERROR, rows=[], reason="500")
    )
    svc = SearchService(_empty_db())
    with patch.object(search_service, "_mock_hotels",
                      side_effect=AssertionError("must not be called")):
        with patch("app.services.hotels_provider.get_hotel_provider",
                   return_value=provider):
            out = svc.search_hotels(_req())
    assert out == []


def test_search_hotels_empty_returns_zero_rows():
    provider = _StaticProvider(
        HotelProviderResult(status=HotelSourceStatus.EMPTY, rows=[], reason="zero")
    )
    svc = SearchService(_empty_db())
    with patch.object(search_service, "_mock_hotels",
                      side_effect=AssertionError("must not be called")):
        with patch("app.services.hotels_provider.get_hotel_provider",
                   return_value=provider):
            out = svc.search_hotels(_req())
    assert out == []


def test_default_null_provider_results_in_zero_rows(monkeypatch):
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_HOTELS_ENABLED", raising=False)
    from app.services.hotels_provider import reset_hotel_provider_cache
    reset_hotel_provider_cache()
    svc = SearchService(_empty_db())
    with patch.object(search_service, "_mock_hotels",
                      side_effect=AssertionError("must not be called")):
        out = svc.search_hotels(_req())
    assert out == []
