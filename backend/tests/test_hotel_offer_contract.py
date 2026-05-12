"""Hotel Offer Contract — Slice 5B regression tests.

Covers:
- HotelOffer construction and invariant enforcement.
- Discovery / offer partition is explicit and enforced by type.
- Disallowed provider names are rejected.
- provider_disclaimer is required and non-empty.
- total_price must be positive when is_available=True.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.contracts.hotels import HotelOffer, HotelOfferKind


def _offer(**kwargs) -> HotelOffer:
    defaults = dict(
        vertical="hotel_offer",
        provider="duffel_stays",
        provider_property_id="prop-001",
        provider_offer_id="offer-abc",
        destination="Paris, France",
        check_in=date(2026, 9, 1),
        check_out=date(2026, 9, 5),
        guests=2,
        rooms=1,
        currency="USD",
        total_price=850.00,
        taxes_fees_included=True,
        cancellation_summary="Free cancellation until Aug 28",
        booking_url="https://book.duffel.com/stays/offer-abc",
        rate_fetched_at="2026-05-12T00:00:00Z",
        provider_disclaimer="Rates from Duffel Stays. May change at checkout.",
        is_available=True,
        error_reason=None,
    )
    defaults.update(kwargs)
    return HotelOffer(**defaults)


class TestHotelOfferValidConstruction:
    def test_minimal_valid_offer(self):
        o = _offer()
        assert o.vertical == "hotel_offer"
        assert o.provider == "duffel_stays"
        assert o.total_price == 850.00
        assert o.is_available is True

    def test_taxes_unknown(self):
        o = _offer(taxes_fees_included=None)
        assert o.taxes_fees_included is None

    def test_unavailable_with_zero_price(self):
        o = _offer(is_available=False, total_price=0.0, error_reason="sold out")
        assert not o.is_available
        assert o.error_reason == "sold out"

    def test_no_offer_id(self):
        o = _offer(provider_offer_id=None)
        assert o.provider_offer_id is None

    def test_no_booking_url(self):
        o = _offer(booking_url=None)
        assert o.booking_url is None

    def test_no_cancellation_summary(self):
        o = _offer(cancellation_summary=None)
        assert o.cancellation_summary is None


class TestHotelOfferInvariants:
    def test_wrong_vertical_rejected(self):
        with pytest.raises(ValueError, match="vertical"):
            _offer(vertical="hotel_discovery")

    def test_empty_provider_rejected(self):
        with pytest.raises(ValueError, match="provider"):
            _offer(provider="")

    def test_mock_provider_rejected(self):
        with pytest.raises(ValueError, match="disallowed"):
            _offer(provider="mock")

    def test_demo_provider_rejected(self):
        with pytest.raises(ValueError, match="disallowed"):
            _offer(provider="demo")

    def test_fixture_provider_rejected(self):
        with pytest.raises(ValueError, match="disallowed"):
            _offer(provider="fixture")

    def test_empty_property_id_rejected(self):
        with pytest.raises(ValueError, match="provider_property_id"):
            _offer(provider_property_id="")

    def test_empty_destination_rejected(self):
        with pytest.raises(ValueError, match="destination"):
            _offer(destination="")

    def test_zero_guests_rejected(self):
        with pytest.raises(ValueError, match="guests"):
            _offer(guests=0)

    def test_zero_rooms_rejected(self):
        with pytest.raises(ValueError, match="rooms"):
            _offer(rooms=0)

    def test_empty_currency_rejected(self):
        with pytest.raises(ValueError, match="currency"):
            _offer(currency="")

    def test_zero_price_when_available_rejected(self):
        with pytest.raises(ValueError, match="total_price"):
            _offer(is_available=True, total_price=0.0)

    def test_negative_price_when_available_rejected(self):
        with pytest.raises(ValueError, match="total_price"):
            _offer(is_available=True, total_price=-1.0)

    def test_empty_rate_fetched_at_rejected(self):
        with pytest.raises(ValueError, match="rate_fetched_at"):
            _offer(rate_fetched_at="")

    def test_empty_provider_disclaimer_rejected(self):
        with pytest.raises(ValueError, match="provider_disclaimer"):
            _offer(provider_disclaimer="")


class TestOfferKindPartition:
    """Discovery and offer kinds remain distinct — cannot be confused."""

    def test_offer_kind_enum_values(self):
        assert HotelOfferKind.DISCOVERY.value == "discovery"
        assert HotelOfferKind.BOOKABLE_OFFER.value == "bookable_offer"

    def test_offer_kind_is_disjoint(self):
        assert HotelOfferKind.DISCOVERY != HotelOfferKind.BOOKABLE_OFFER

    def test_hotel_offer_vertical_differs_from_discovery_kind(self):
        """HotelOffer.vertical='hotel_offer' != HotelOfferKind.DISCOVERY='discovery'."""
        o = _offer()
        assert o.vertical == "hotel_offer"
        assert o.vertical != HotelOfferKind.DISCOVERY.value
