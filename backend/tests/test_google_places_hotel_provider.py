"""Google Places lodging provider — Hotels v1 unit tests.

Mocked HTTP only — no real network calls.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import pytest

from app.contracts.hotels import (
    HotelSourceStatus,
    is_persistable_hotel,
)
from app.models.search import HotelSearchRequest
from app.services.hotels_provider import (
    HotelProviderResult,
    NullHotelProvider,
    get_hotel_provider,
    reset_hotel_provider_cache,
)
from app.services.hotels_provider_google_places import (
    GooglePlacesHotelProvider,
    build_google_places_hotel_provider_from_env,
    google_places_hotels_enabled_from_env,
    _map_place_to_hotel,
)


# ---------------------------------------------------------------------------
# Fakes
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


class _FakeHttp:
    def __init__(self) -> None:
        self.calls: List[Tuple[str, Dict[str, Any]]] = []
        self.responses: List[_FakeResponse] = []
        self.raise_on_post = False

    def post(self, url: str, headers: Optional[Dict[str, str]] = None,
             json: Optional[Dict[str, Any]] = None) -> _FakeResponse:
        if self.raise_on_post:
            raise RuntimeError("boom")
        self.calls.append((url, {"headers": dict(headers or {}), "json": dict(json or {})}))
        if not self.responses:
            return _FakeResponse(500, text="no scripted response")
        return self.responses.pop(0)


def _req(location: str = "Paris") -> HotelSearchRequest:
    return HotelSearchRequest(
        location=location,
        check_in=date(2026, 6, 1),
        check_out=date(2026, 6, 5),
        guests=1,
    )


def _operational_lodging(idx: int = 1) -> Dict[str, Any]:
    return {
        "id": f"place-{idx}",
        "displayName": {"text": f"Hotel {idx}"},
        "formattedAddress": f"{idx} Rue de Test, Paris",
        "location": {"latitude": 48.8566, "longitude": 2.3522},
        "businessStatus": "OPERATIONAL",
        "types": ["lodging", "establishment"],
        "primaryType": "lodging",
        "rating": 4.4,
        "userRatingCount": 1200,
        "googleMapsUri": f"https://maps.google.com/?cid={idx}",
        "priceLevel": "PRICE_LEVEL_MODERATE",
    }


# ---------------------------------------------------------------------------
# Env gating
# ---------------------------------------------------------------------------


def test_enabled_requires_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_HOTELS_ENABLED", "1")
    assert google_places_hotels_enabled_from_env() is False


def test_default_enabled_when_key_present_and_flag_unset(monkeypatch):
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "k")
    monkeypatch.delenv("GOOGLE_HOTELS_ENABLED", raising=False)
    assert google_places_hotels_enabled_from_env() is True


def test_explicit_disable(monkeypatch):
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "k")
    monkeypatch.setenv("GOOGLE_HOTELS_ENABLED", "0")
    assert google_places_hotels_enabled_from_env() is False


def test_get_hotel_provider_falls_back_to_null_when_unconfigured(monkeypatch):
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_HOTELS_ENABLED", raising=False)
    reset_hotel_provider_cache()
    provider = get_hotel_provider()
    assert isinstance(provider, NullHotelProvider)
    out = provider.search_hotels(_req())
    assert out.status is HotelSourceStatus.UNAVAILABLE
    assert out.rows == []


def test_get_hotel_provider_returns_google_places_when_configured(monkeypatch):
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "k")
    monkeypatch.delenv("GOOGLE_HOTELS_ENABLED", raising=False)
    reset_hotel_provider_cache()
    provider = get_hotel_provider()
    assert isinstance(provider, GooglePlacesHotelProvider)


# ---------------------------------------------------------------------------
# Provider behavior
# ---------------------------------------------------------------------------


def test_happy_path_emits_persistable_rows():
    http = _FakeHttp()
    http.responses.append(_FakeResponse(200, {"places": [_operational_lodging(1), _operational_lodging(2)]}))
    provider = GooglePlacesHotelProvider(api_key="k", http_client=http)
    out = provider.search_hotels(_req())
    assert out.status is HotelSourceStatus.OK
    assert len(out.rows) == 2
    for row in out.rows:
        assert is_persistable_hotel(row)
        assert row.source == "google_places"
        assert "book.example.com" not in row.booking_url
        assert row.price_per_night == 0.0  # no fabricated nightly rate
        assert row.stars is None  # no fabricated star rating
        assert row.amenities == []  # no fabricated amenities


def test_request_uses_lodging_query_and_field_mask():
    http = _FakeHttp()
    http.responses.append(_FakeResponse(200, {"places": [_operational_lodging(1)]}))
    provider = GooglePlacesHotelProvider(api_key="my-key", http_client=http)
    provider.search_hotels(_req("Tokyo"))
    assert len(http.calls) == 1
    url, info = http.calls[0]
    assert "places:searchText" in url
    assert info["headers"]["X-Goog-Api-Key"] == "my-key"
    field_mask = info["headers"]["X-Goog-FieldMask"]
    for required in ("places.id", "places.displayName", "places.formattedAddress",
                     "places.businessStatus", "places.types", "places.rating",
                     "places.googleMapsUri"):
        assert required in field_mask
    body = info["json"]
    assert "hotels" in body["textQuery"].lower()
    assert "tokyo" in body["textQuery"].lower()
    assert body["includedType"] == "lodging"


def test_non_operational_skipped():
    http = _FakeHttp()
    closed = _operational_lodging(1)
    closed["businessStatus"] = "CLOSED_PERMANENTLY"
    http.responses.append(_FakeResponse(200, {"places": [closed, _operational_lodging(2)]}))
    provider = GooglePlacesHotelProvider(api_key="k", http_client=http)
    out = provider.search_hotels(_req())
    assert out.status is HotelSourceStatus.OK
    assert len(out.rows) == 1
    assert out.rows[0].id == "gp-place-2"


def test_non_lodging_skipped():
    http = _FakeHttp()
    restaurant = _operational_lodging(1)
    restaurant["primaryType"] = "restaurant"
    restaurant["types"] = ["restaurant", "establishment"]
    http.responses.append(_FakeResponse(200, {"places": [restaurant, _operational_lodging(2)]}))
    provider = GooglePlacesHotelProvider(api_key="k", http_client=http)
    out = provider.search_hotels(_req())
    assert out.status is HotelSourceStatus.OK
    assert len(out.rows) == 1
    assert out.rows[0].id == "gp-place-2"


def test_empty_response_maps_to_empty():
    http = _FakeHttp()
    http.responses.append(_FakeResponse(200, {"places": []}))
    provider = GooglePlacesHotelProvider(api_key="k", http_client=http)
    out = provider.search_hotels(_req())
    assert out.status is HotelSourceStatus.EMPTY
    assert out.rows == []


def test_all_skipped_maps_to_empty():
    http = _FakeHttp()
    closed = _operational_lodging(1)
    closed["businessStatus"] = "CLOSED_PERMANENTLY"
    http.responses.append(_FakeResponse(200, {"places": [closed]}))
    provider = GooglePlacesHotelProvider(api_key="k", http_client=http)
    out = provider.search_hotels(_req())
    assert out.status is HotelSourceStatus.EMPTY
    assert out.rows == []


def test_non_200_maps_to_error():
    http = _FakeHttp()
    http.responses.append(_FakeResponse(500, text="upstream"))
    provider = GooglePlacesHotelProvider(api_key="k", http_client=http)
    out = provider.search_hotels(_req())
    assert out.status is HotelSourceStatus.ERROR
    assert out.rows == []


def test_transport_exception_maps_to_error():
    http = _FakeHttp()
    http.raise_on_post = True
    provider = GooglePlacesHotelProvider(api_key="k", http_client=http)
    out = provider.search_hotels(_req())
    assert out.status is HotelSourceStatus.ERROR
    assert out.rows == []


def test_parse_error_maps_to_error():
    http = _FakeHttp()
    http.responses.append(_FakeResponse(200, payload=None, text="not json"))
    provider = GooglePlacesHotelProvider(api_key="k", http_client=http)
    out = provider.search_hotels(_req())
    assert out.status is HotelSourceStatus.ERROR


def test_whitespace_location_maps_to_empty():
    """``HotelSearchRequest`` validates non-empty location at the API
    edge, but the provider must still fail closed if a whitespace-only
    location somehow reaches it (defense in depth)."""
    http = _FakeHttp()
    provider = GooglePlacesHotelProvider(api_key="k", http_client=http)
    req = HotelSearchRequest.model_construct(
        location="   ",
        check_in=date(2026, 6, 1),
        check_out=date(2026, 6, 5),
        guests=1,
    )
    out = provider.search_hotels(req)
    assert out.status is HotelSourceStatus.EMPTY
    assert http.calls == []


def test_mapping_uses_request_dates_for_check_in_out_and_nights():
    place = _operational_lodging(1)
    req = HotelSearchRequest(
        location="Paris",
        check_in=date(2026, 6, 1),
        check_out=date(2026, 6, 8),
    )
    row = _map_place_to_hotel(place, req)
    assert row is not None
    assert row.check_in == date(2026, 6, 1)
    assert row.check_out == date(2026, 6, 8)
    assert row.nights == 7


def test_mapping_falls_back_to_place_id_url_when_no_maps_uri():
    place = _operational_lodging(1)
    place["googleMapsUri"] = ""
    row = _map_place_to_hotel(place, _req())
    assert row is not None
    assert row.booking_url.startswith("https://www.google.com/maps/place/?q=place_id:")
    # No fabricated host
    assert "book.example.com" not in row.booking_url
    assert "example.com" not in row.booking_url.lower().replace("google.com", "")


def test_provider_result_rejects_mock_rows_at_post_init():
    """A bug in a future adapter that emits ``source='mock'`` must be
    blocked by ``HotelProviderResult.__post_init__`` rather than reach
    the route."""
    from app.models.search import HotelResult
    bad = HotelResult(
        id="x",
        location="Paris",
        booking_url="https://book.example.com/x",
        source="mock",
        booking_options=[],
        name="Fake",
        check_in=date(2026, 6, 1),
        check_out=date(2026, 6, 5),
        nights=4,
        amenities=[],
        price_per_night=0.0,
    )
    with pytest.raises(ValueError):
        HotelProviderResult(status=HotelSourceStatus.OK, rows=[bad])


def test_ok_with_empty_rows_rejected():
    with pytest.raises(ValueError):
        HotelProviderResult(status=HotelSourceStatus.OK, rows=[])


def test_non_ok_with_rows_rejected():
    from app.models.search import HotelResult
    row = HotelResult(
        id="ok",
        location="Paris",
        booking_url="https://maps.google.com/x",
        source="google_places",
        booking_options=[],
        name="Test Hotel",
        check_in=date(2026, 6, 1),
        check_out=date(2026, 6, 5),
        nights=4,
        amenities=[],
        price_per_night=0.0,
    )
    with pytest.raises(ValueError):
        HotelProviderResult(status=HotelSourceStatus.UNAVAILABLE, rows=[row])
