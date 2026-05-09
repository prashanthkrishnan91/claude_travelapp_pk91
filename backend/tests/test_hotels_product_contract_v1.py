"""Hotels Product Contract v1 — regression tests.

Mirrors ``test_flights_product_contract_v1.py`` for the lodging surface.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.contracts.hotels import (
    ALLOWED_SOURCE_VALUES,
    DISALLOWED_SOURCES,
    FABRICATED_BOOKING_HOSTS,
    HotelContractViolation,
    HotelOfferKind,
    HotelProviderUnavailable,
    HotelSourceStatus,
    MOCK_BOOKING_HOST,
    PROVIDER_BACKED_SOURCE_VALUES,
    USER_ENTERED_SOURCE_VALUES,
    assert_persistable_hotel,
    check_persistable_hotel,
    is_mock_derived_hotel,
    is_persistable_hotel,
)
from app.models.search import BookingOption, HotelResult


def _hotel(
    *,
    source: str = "google_places",
    booking_url: str = "https://www.google.com/maps/place/?q=place_id:abc",
    booking_options=None,
    name: str = "Test Hotel",
) -> HotelResult:
    return HotelResult(
        id="h1",
        price=None,
        location="Paris, FR",
        booking_url=booking_url,
        source=source,
        booking_options=booking_options or [],
        name=name,
        check_in=date(2026, 6, 1),
        check_out=date(2026, 6, 5),
        nights=4,
        amenities=[],
        price_per_night=0.0,
    )


def test_allowed_sources_partition():
    assert PROVIDER_BACKED_SOURCE_VALUES.isdisjoint(USER_ENTERED_SOURCE_VALUES)
    assert (
        PROVIDER_BACKED_SOURCE_VALUES | USER_ENTERED_SOURCE_VALUES
        == ALLOWED_SOURCE_VALUES
    )


def test_google_places_is_provider_backed():
    assert "google_places" in PROVIDER_BACKED_SOURCE_VALUES


def test_disallowed_sources_cover_legacy_mock_vocabulary():
    assert {"mock", "demo", "fixture", "sample", "placeholder"} <= DISALLOWED_SOURCES


def test_fabricated_hosts_include_legacy_book_example_com():
    assert MOCK_BOOKING_HOST == "book.example.com"
    assert "book.example.com" in FABRICATED_BOOKING_HOSTS
    assert "example.com" in FABRICATED_BOOKING_HOSTS


def test_offer_kind_partition_is_explicit():
    # Discovery vs bookable is the documented v1/v2 boundary.
    assert HotelOfferKind.DISCOVERY.value == "discovery"
    assert HotelOfferKind.BOOKABLE_OFFER.value == "bookable_offer"


def test_persistable_clean_provider_row():
    h = _hotel()
    assert is_persistable_hotel(h) is True
    assert check_persistable_hotel(h) is None
    assert is_mock_derived_hotel(h) is False


def test_mock_source_rejected():
    h = _hotel(source="mock")
    assert is_persistable_hotel(h) is False
    assert is_mock_derived_hotel(h) is True
    failure = check_persistable_hotel(h)
    assert failure is not None and failure.code == "disallowed_source"


def test_demo_fixture_sample_placeholder_rejected():
    for src in ("demo", "fixture", "sample", "placeholder"):
        h = _hotel(source=src)
        assert is_persistable_hotel(h) is False
        assert is_mock_derived_hotel(h) is True


def test_book_example_com_booking_url_rejected():
    h = _hotel(
        source="google_places",
        booking_url="https://book.example.com/hotels/foo",
    )
    assert is_persistable_hotel(h) is False
    assert is_mock_derived_hotel(h) is True


def test_book_example_com_booking_option_rejected():
    h = _hotel(
        source="google_places",
        booking_url="https://www.google.com/maps/place/?q=place_id:abc",
        booking_options=[
            BookingOption(provider="hotels_com", url="https://book.example.com/x"),
        ],
    )
    assert is_persistable_hotel(h) is False
    assert is_mock_derived_hotel(h) is True


def test_unknown_source_rejected():
    h = _hotel(source="random_provider")
    assert is_persistable_hotel(h) is False
    failure = check_persistable_hotel(h)
    assert failure is not None and failure.code == "unrecognised_source"


def test_assert_raises_typed_violation():
    h = _hotel(source="mock")
    with pytest.raises(HotelContractViolation) as exc:
        assert_persistable_hotel(h)
    assert exc.value.failure.code == "disallowed_source"


def test_provider_unavailable_must_carry_unavailable_or_error():
    HotelProviderUnavailable(status=HotelSourceStatus.UNAVAILABLE, reason="x")
    HotelProviderUnavailable(status=HotelSourceStatus.ERROR, reason="x")
    with pytest.raises(ValueError):
        HotelProviderUnavailable(status=HotelSourceStatus.OK, reason="x")
    with pytest.raises(ValueError):
        HotelProviderUnavailable(status=HotelSourceStatus.EMPTY, reason="x")
