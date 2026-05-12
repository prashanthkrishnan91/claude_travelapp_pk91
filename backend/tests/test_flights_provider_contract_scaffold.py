"""Flights Provider Contract Scaffold — fail-closed + registry gating tests.

Covers:
1.  No provider key/config => no flight results and no mock rows (get_flight_provider)
2.  Skyscanner registry entry is pending/disabled by default
3.  Ignav registry entry is evaluation/disabled by default
4.  Duffel cannot activate (registry disabled)
5.  Amadeus cannot activate (registry disabled)
6.  Skyscanner adapter shell fails closed (UNAVAILABLE, zero rows)
7.  Ignav adapter shell fails closed (UNAVAILABLE, zero rows)
8.  No cash price produced without a live provider
9.  No points price produced (points track is separately gated)
10. FlightItineraryOffer invariants: fabricated prices and URLs rejected
11. FlightPrice rejects zero/negative amounts
12. FlightBookingLink rejects placeholder/mock hosts
13. FlightSegment rejects invalid IATA codes or zero duration
14. FlightOfferLeg rejects empty segments
15. Provider keys are not in the approved frontend public env prefix (NEXT_PUBLIC_)
16. Existing get_flight_provider() returns NullFlightProvider (no real provider active)
"""

from __future__ import annotations

import os
from datetime import date
from typing import Any
from unittest.mock import patch

import pytest

from app.contracts.flights import FlightSourceStatus
from app.contracts.flight_offer import (
    BookingLinkType,
    FlightAdapterDisabledResult,
    FlightBookingLink,
    FlightItineraryOffer,
    FlightOfferLeg,
    FlightPrice,
    FlightSearchRequest,
    FlightSegment,
    LiveCachedStatus,
    TripType,
)
from app.services.provider_registry import (
    PROVIDER_REGISTRY,
    ProviderRole,
    is_production_allowed,
    is_provider_active,
)
from app.services.flights_provider import (
    FlightProviderResult,
    NullFlightProvider,
    reset_flight_provider_cache,
)
from app.services.flights_provider_skyscanner import (
    SkyscannerFlightProvider,
    skyscanner_enabled_from_env,
    build_skyscanner_provider_from_env,
)
from app.services.flights_provider_ignav import (
    IgnavFlightProvider,
    ignav_enabled_from_env,
    build_ignav_provider_from_env,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_segment() -> FlightSegment:
    return FlightSegment(
        airline="AA",
        flight_number="AA100",
        origin="JFK",
        destination="CDG",
        departure_time="2026-06-01T08:00:00Z",
        arrival_time="2026-06-01T20:00:00Z",
        duration_minutes=480,
    )


def _make_leg() -> FlightOfferLeg:
    return FlightOfferLeg(
        origin="JFK",
        destination="CDG",
        departure_time="2026-06-01T08:00:00Z",
        arrival_time="2026-06-01T20:00:00Z",
        duration_minutes=480,
        stops=0,
        segments=(_make_segment(),),
    )


def _make_price() -> FlightPrice:
    return FlightPrice(currency="USD", total_amount=450.00)


def _make_booking_link() -> FlightBookingLink:
    return FlightBookingLink(
        url="https://www.skyscanner.com/transport/flights/jfk/cdg/",
        link_type=BookingLinkType.PROVIDER_DEEPLINK,
        provider_name="skyscanner_flights",
    )


def _make_offer(**kwargs: Any) -> FlightItineraryOffer:
    defaults = dict(
        provider="skyscanner_flights",
        fetched_at="2026-06-01T00:00:00Z",
        live_cached_status=LiveCachedStatus.LIVE,
        trip_type=TripType.ONE_WAY,
        origin="JFK",
        destination="CDG",
        departure_date="2026-06-01",
        passengers=1,
        cabin_class="economy",
        outbound_leg=_make_leg(),
        price=_make_price(),
        booking_link=_make_booking_link(),
    )
    defaults.update(kwargs)
    return FlightItineraryOffer(**defaults)


# ---------------------------------------------------------------------------
# 1. No provider key => no flight results, no mock rows
# ---------------------------------------------------------------------------


class TestNoProviderKeyFailClosed:
    def test_no_skyscanner_key_no_results(self, monkeypatch):
        monkeypatch.delenv("SKYSCANNER_API_KEY", raising=False)
        monkeypatch.delenv("SKYSCANNER_FLIGHTS_ENABLED", raising=False)
        assert not skyscanner_enabled_from_env()
        assert build_skyscanner_provider_from_env() is None

    def test_no_ignav_key_no_results(self, monkeypatch):
        monkeypatch.delenv("IGNAV_API_KEY", raising=False)
        monkeypatch.delenv("IGNAV_FLIGHTS_ENABLED", raising=False)
        assert not ignav_enabled_from_env()
        assert build_ignav_provider_from_env() is None

    def test_flag_without_key_still_disabled_skyscanner(self, monkeypatch):
        monkeypatch.setenv("SKYSCANNER_FLIGHTS_ENABLED", "1")
        monkeypatch.delenv("SKYSCANNER_API_KEY", raising=False)
        assert not skyscanner_enabled_from_env()

    def test_flag_without_key_still_disabled_ignav(self, monkeypatch):
        monkeypatch.setenv("IGNAV_FLIGHTS_ENABLED", "1")
        monkeypatch.delenv("IGNAV_API_KEY", raising=False)
        assert not ignav_enabled_from_env()

    def test_key_without_flag_still_disabled_skyscanner(self, monkeypatch):
        monkeypatch.setenv("SKYSCANNER_API_KEY", "sk-live-key")
        monkeypatch.delenv("SKYSCANNER_FLIGHTS_ENABLED", raising=False)
        assert not skyscanner_enabled_from_env()

    def test_key_without_flag_still_disabled_ignav(self, monkeypatch):
        monkeypatch.setenv("IGNAV_API_KEY", "ignav-key")
        monkeypatch.delenv("IGNAV_FLIGHTS_ENABLED", raising=False)
        assert not ignav_enabled_from_env()


# ---------------------------------------------------------------------------
# 2–3. Registry entries: Skyscanner (PENDING) and Ignav (EVALUATION) disabled
# ---------------------------------------------------------------------------


class TestRegistryEntries:
    def test_skyscanner_in_registry(self):
        assert "skyscanner_flights" in PROVIDER_REGISTRY

    def test_ignav_in_registry(self):
        assert "ignav_flights" in PROVIDER_REGISTRY

    def test_skyscanner_role_is_pending(self):
        entry = PROVIDER_REGISTRY["skyscanner_flights"]
        assert entry.role is ProviderRole.PENDING

    def test_ignav_role_is_evaluation(self):
        entry = PROVIDER_REGISTRY["ignav_flights"]
        assert entry.role is ProviderRole.EVALUATION

    def test_skyscanner_not_production_allowed(self):
        assert not is_production_allowed("skyscanner_flights")

    def test_ignav_not_production_allowed(self):
        assert not is_production_allowed("ignav_flights")

    def test_skyscanner_not_active(self):
        assert not is_provider_active("skyscanner_flights")

    def test_ignav_not_active(self):
        assert not is_provider_active("ignav_flights")

    def test_skyscanner_required_env_vars(self):
        entry = PROVIDER_REGISTRY["skyscanner_flights"]
        assert "SKYSCANNER_API_KEY" in entry.required_env_vars
        assert "SKYSCANNER_FLIGHTS_ENABLED" in entry.required_env_vars

    def test_ignav_required_env_vars(self):
        entry = PROVIDER_REGISTRY["ignav_flights"]
        assert "IGNAV_API_KEY" in entry.required_env_vars
        assert "IGNAV_FLIGHTS_ENABLED" in entry.required_env_vars

    def test_skyscanner_supports_flight_vertical(self):
        entry = PROVIDER_REGISTRY["skyscanner_flights"]
        assert "flight" in entry.supported_verticals

    def test_ignav_supports_flight_vertical(self):
        entry = PROVIDER_REGISTRY["ignav_flights"]
        assert "flight" in entry.supported_verticals

    def test_skyscanner_cannot_create_addable_cards(self):
        entry = PROVIDER_REGISTRY["skyscanner_flights"]
        assert not entry.can_create_addable_cards

    def test_ignav_cannot_create_addable_cards(self):
        entry = PROVIDER_REGISTRY["ignav_flights"]
        assert not entry.can_create_addable_cards


# ---------------------------------------------------------------------------
# 4–5. Duffel and Amadeus cannot activate
# ---------------------------------------------------------------------------


class TestDisabledProvidersCannotActivate:
    def test_duffel_flights_disabled(self):
        assert not is_provider_active("duffel_flights")
        assert not is_production_allowed("duffel_flights")

    def test_amadeus_disabled(self):
        assert not is_provider_active("amadeus")
        assert not is_production_allowed("amadeus")

    def test_duffel_role_is_disabled(self):
        assert PROVIDER_REGISTRY["duffel_flights"].role is ProviderRole.DISABLED

    def test_amadeus_role_is_disabled(self):
        assert PROVIDER_REGISTRY["amadeus"].role is ProviderRole.DISABLED

    def test_duffel_stays_quarantined(self):
        assert not is_provider_active("duffel_stays")
        assert PROVIDER_REGISTRY["duffel_stays"].role is ProviderRole.QUARANTINED


# ---------------------------------------------------------------------------
# 6–7. Adapter shells fail closed
# ---------------------------------------------------------------------------


class TestAdapterShellsFailClosed:
    def _dummy_req(self) -> FlightSearchRequest:
        return FlightSearchRequest(
            origin="JFK",
            destination="CDG",
            departure_date=date(2026, 6, 1),
        )

    def test_skyscanner_shell_returns_unavailable(self):
        provider = SkyscannerFlightProvider()
        result = provider.search_flights(self._dummy_req())
        assert isinstance(result, FlightProviderResult)
        assert result.status is FlightSourceStatus.UNAVAILABLE
        assert result.rows == []

    def test_skyscanner_shell_zero_rows(self):
        provider = SkyscannerFlightProvider()
        result = provider.search_flights(self._dummy_req())
        assert len(result.rows) == 0

    def test_ignav_shell_returns_unavailable(self):
        provider = IgnavFlightProvider()
        result = provider.search_flights(self._dummy_req())
        assert result.status is FlightSourceStatus.UNAVAILABLE
        assert result.rows == []

    def test_ignav_shell_zero_rows(self):
        provider = IgnavFlightProvider()
        result = provider.search_flights(self._dummy_req())
        assert len(result.rows) == 0

    def test_skyscanner_shell_no_mock_rows(self):
        provider = SkyscannerFlightProvider()
        result = provider.search_flights(self._dummy_req())
        assert not any(
            getattr(r, "source", "").lower() in ("mock", "demo", "fixture", "sample")
            for r in result.rows
        )

    def test_ignav_shell_no_mock_rows(self):
        provider = IgnavFlightProvider()
        result = provider.search_flights(self._dummy_req())
        assert len(result.rows) == 0  # confirms no mock rows exist


# ---------------------------------------------------------------------------
# 8–9. No cash or points price without live provider
# ---------------------------------------------------------------------------


class TestNoPriceWithoutLiveProvider:
    def test_null_provider_no_cash_price(self):
        null = NullFlightProvider()
        req = FlightSearchRequest(
            origin="JFK", destination="CDG", departure_date=date(2026, 6, 1)
        )
        result = null.search_flights(req)
        assert result.rows == []
        # No row => no cash price
        prices = [getattr(r, "price", None) for r in result.rows]
        assert all(p is None for p in prices)

    def test_skyscanner_shell_no_cash_price(self):
        provider = SkyscannerFlightProvider()
        req = FlightSearchRequest(
            origin="JFK", destination="CDG", departure_date=date(2026, 6, 1)
        )
        result = provider.search_flights(req)
        assert result.rows == []

    def test_ignav_shell_no_cash_price(self):
        provider = IgnavFlightProvider()
        req = FlightSearchRequest(
            origin="JFK", destination="CDG", departure_date=date(2026, 6, 1)
        )
        result = provider.search_flights(req)
        assert result.rows == []

    def test_null_provider_no_points_price(self):
        null = NullFlightProvider()
        req = FlightSearchRequest(
            origin="JFK", destination="CDG", departure_date=date(2026, 6, 1)
        )
        result = null.search_flights(req)
        # Points track is separately gated; scaffold never returns points data
        assert result.rows == []


# ---------------------------------------------------------------------------
# 10. FlightItineraryOffer invariants
# ---------------------------------------------------------------------------


class TestFlightItineraryOfferInvariants:
    def test_valid_one_way_offer(self):
        offer = _make_offer()
        assert offer.trip_type is TripType.ONE_WAY
        assert offer.return_leg is None

    def test_valid_round_trip_offer(self):
        offer = _make_offer(
            trip_type=TripType.ROUND_TRIP,
            return_date="2026-06-08",
            return_leg=_make_leg(),
        )
        assert offer.return_leg is not None

    def test_round_trip_requires_return_leg(self):
        with pytest.raises(ValueError, match="return_leg"):
            _make_offer(trip_type=TripType.ROUND_TRIP, return_leg=None)

    def test_one_way_must_not_have_return_leg(self):
        with pytest.raises(ValueError, match="return_leg"):
            _make_offer(trip_type=TripType.ONE_WAY, return_leg=_make_leg())

    def test_empty_provider_rejected(self):
        with pytest.raises(ValueError, match="provider"):
            _make_offer(provider="")

    def test_empty_fetched_at_rejected(self):
        with pytest.raises(ValueError, match="fetched_at"):
            _make_offer(fetched_at="")

    def test_zero_passengers_rejected(self):
        with pytest.raises(ValueError, match="passengers"):
            _make_offer(passengers=0)

    def test_ai_score_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="ai_score"):
            _make_offer(ai_score=1.5)

    def test_ai_score_none_allowed(self):
        offer = _make_offer(ai_score=None)
        assert offer.ai_score is None


# ---------------------------------------------------------------------------
# 11. FlightPrice invariants
# ---------------------------------------------------------------------------


class TestFlightPriceInvariants:
    def test_valid_price(self):
        p = FlightPrice(currency="USD", total_amount=450.0)
        assert p.total_amount == 450.0

    def test_zero_price_rejected(self):
        with pytest.raises(ValueError, match="total_amount"):
            FlightPrice(currency="USD", total_amount=0.0)

    def test_negative_price_rejected(self):
        with pytest.raises(ValueError, match="total_amount"):
            FlightPrice(currency="USD", total_amount=-10.0)

    def test_empty_currency_rejected(self):
        with pytest.raises(ValueError, match="currency"):
            FlightPrice(currency="", total_amount=100.0)


# ---------------------------------------------------------------------------
# 12. FlightBookingLink rejects fabricated/placeholder hosts
# ---------------------------------------------------------------------------


class TestFlightBookingLinkInvariants:
    def test_valid_link(self):
        link = _make_booking_link()
        assert link.link_type is BookingLinkType.PROVIDER_DEEPLINK

    def test_mock_booking_host_rejected(self):
        with pytest.raises(ValueError, match="fabricated"):
            FlightBookingLink(
                url="https://book.example.com/flight/123",
                link_type=BookingLinkType.OTA,
                provider_name="fake",
            )

    def test_example_com_rejected(self):
        with pytest.raises(ValueError, match="fabricated"):
            FlightBookingLink(
                url="https://example.com/book",
                link_type=BookingLinkType.AIRLINE_DIRECT,
                provider_name="fake",
            )

    def test_unavailable_type_allows_empty_url(self):
        link = FlightBookingLink(
            url="",
            link_type=BookingLinkType.UNAVAILABLE,
            provider_name="skyscanner_flights",
        )
        assert link.url == ""

    def test_non_unavailable_type_requires_url(self):
        with pytest.raises(ValueError, match="url is required"):
            FlightBookingLink(
                url="",
                link_type=BookingLinkType.OTA,
                provider_name="some_ota",
            )


# ---------------------------------------------------------------------------
# 13. FlightSegment invariants
# ---------------------------------------------------------------------------


class TestFlightSegmentInvariants:
    def test_valid_segment(self):
        seg = _make_segment()
        assert seg.airline == "AA"

    def test_invalid_origin_iata(self):
        with pytest.raises(ValueError, match="3-letter IATA"):
            FlightSegment(
                airline="AA",
                flight_number="AA100",
                origin="JF",  # too short
                destination="CDG",
                departure_time="2026-06-01T08:00:00Z",
                arrival_time="2026-06-01T20:00:00Z",
                duration_minutes=480,
            )

    def test_zero_duration_rejected(self):
        with pytest.raises(ValueError, match="duration_minutes"):
            FlightSegment(
                airline="AA",
                flight_number="AA100",
                origin="JFK",
                destination="CDG",
                departure_time="2026-06-01T08:00:00Z",
                arrival_time="2026-06-01T20:00:00Z",
                duration_minutes=0,
            )

    def test_empty_airline_rejected(self):
        with pytest.raises(ValueError, match="airline"):
            FlightSegment(
                airline="",
                flight_number="AA100",
                origin="JFK",
                destination="CDG",
                departure_time="2026-06-01T08:00:00Z",
                arrival_time="2026-06-01T20:00:00Z",
                duration_minutes=480,
            )


# ---------------------------------------------------------------------------
# 14. FlightOfferLeg rejects empty segments
# ---------------------------------------------------------------------------


class TestFlightOfferLegInvariants:
    def test_valid_leg(self):
        leg = _make_leg()
        assert len(leg.segments) == 1

    def test_empty_segments_rejected(self):
        with pytest.raises(ValueError, match="segments"):
            FlightOfferLeg(
                origin="JFK",
                destination="CDG",
                departure_time="2026-06-01T08:00:00Z",
                arrival_time="2026-06-01T20:00:00Z",
                duration_minutes=480,
                stops=0,
                segments=(),
            )

    def test_invalid_origin_iata(self):
        with pytest.raises(ValueError, match="3-letter IATA"):
            FlightOfferLeg(
                origin="JF",
                destination="CDG",
                departure_time="2026-06-01T08:00:00Z",
                arrival_time="2026-06-01T20:00:00Z",
                duration_minutes=480,
                stops=0,
                segments=(_make_segment(),),
            )


# ---------------------------------------------------------------------------
# 15. Provider keys not in frontend public env prefix
# ---------------------------------------------------------------------------


class TestProviderKeysNotPublic:
    """Prove that provider key env var names do not use the NEXT_PUBLIC_ prefix.

    This is a static contract test: we verify that the names declared in the
    Provider Registry never start with NEXT_PUBLIC_, ensuring they cannot be
    inadvertently surfaced to the browser.
    """

    FLIGHT_PROVIDER_IDS = ("skyscanner_flights", "ignav_flights", "duffel_flights", "amadeus")

    def test_no_skyscanner_key_in_public_prefix(self):
        entry = PROVIDER_REGISTRY["skyscanner_flights"]
        for var in entry.required_env_vars:
            assert not var.startswith("NEXT_PUBLIC_"), (
                f"Provider key {var!r} must not use NEXT_PUBLIC_ prefix"
            )

    def test_no_ignav_key_in_public_prefix(self):
        entry = PROVIDER_REGISTRY["ignav_flights"]
        for var in entry.required_env_vars:
            assert not var.startswith("NEXT_PUBLIC_"), (
                f"Provider key {var!r} must not use NEXT_PUBLIC_ prefix"
            )

    def test_no_duffel_key_in_public_prefix(self):
        entry = PROVIDER_REGISTRY["duffel_flights"]
        for var in entry.required_env_vars:
            assert not var.startswith("NEXT_PUBLIC_")

    def test_all_flight_provider_keys_server_side(self):
        for pid in self.FLIGHT_PROVIDER_IDS:
            entry = PROVIDER_REGISTRY[pid]
            for var in entry.required_env_vars:
                assert not var.startswith("NEXT_PUBLIC_"), (
                    f"[{pid}] key {var!r} must be server-side only"
                )


# ---------------------------------------------------------------------------
# 16. get_flight_provider() returns NullFlightProvider with no active provider
# ---------------------------------------------------------------------------


class TestGetFlightProviderFailClosed:
    def test_returns_null_provider_by_default(self, monkeypatch):
        reset_flight_provider_cache()
        # Ensure no provider env vars are set
        for var in (
            "SKYSCANNER_API_KEY", "SKYSCANNER_FLIGHTS_ENABLED",
            "IGNAV_API_KEY", "IGNAV_FLIGHTS_ENABLED",
            "DUFFEL_ACCESS_TOKEN", "DUFFEL_FLIGHTS_ENABLED",
        ):
            monkeypatch.delenv(var, raising=False)

        from app.services.flights_provider import get_flight_provider
        provider = get_flight_provider()
        assert isinstance(provider, NullFlightProvider)

    def test_null_provider_result_unavailable(self, monkeypatch):
        reset_flight_provider_cache()
        for var in (
            "SKYSCANNER_API_KEY", "SKYSCANNER_FLIGHTS_ENABLED",
            "IGNAV_API_KEY", "IGNAV_FLIGHTS_ENABLED",
        ):
            monkeypatch.delenv(var, raising=False)

        from app.services.flights_provider import get_flight_provider
        provider = get_flight_provider()
        req = FlightSearchRequest(
            origin="JFK", destination="CDG", departure_date=date(2026, 6, 1)
        )
        result = provider.search_flights(req)
        assert result.status is FlightSourceStatus.UNAVAILABLE
        assert result.rows == []

    def test_registry_gate_blocks_skyscanner_even_with_env(self, monkeypatch):
        """Even with both env vars set, Skyscanner stays off (registry PENDING)."""
        reset_flight_provider_cache()
        monkeypatch.setenv("SKYSCANNER_API_KEY", "sk-live-test-key")
        monkeypatch.setenv("SKYSCANNER_FLIGHTS_ENABLED", "1")

        # Registry gate: skyscanner_flights is PENDING, so is_provider_active returns False.
        assert not is_provider_active("skyscanner_flights")

        from app.services.flights_provider import get_flight_provider
        provider = get_flight_provider()
        assert isinstance(provider, NullFlightProvider)

    def test_registry_gate_blocks_ignav_even_with_env(self, monkeypatch):
        """Even with both env vars set, Ignav stays off (registry EVALUATION)."""
        reset_flight_provider_cache()
        monkeypatch.setenv("IGNAV_API_KEY", "ignav-test-key")
        monkeypatch.setenv("IGNAV_FLIGHTS_ENABLED", "1")

        assert not is_provider_active("ignav_flights")

        from app.services.flights_provider import get_flight_provider
        provider = get_flight_provider()
        assert isinstance(provider, NullFlightProvider)


# ---------------------------------------------------------------------------
# Seam alignment — FlightProviderResult accepts FlightItineraryOffer (canonical)
# ---------------------------------------------------------------------------


class TestFlightProviderResultSeamAlignment:
    """Prove FlightProviderResult.rows accepts FlightItineraryOffer as the
    canonical row type, and isolates FlightResult as the legacy path.
    """

    def test_ok_accepts_valid_flight_itinerary_offer(self):
        result = FlightProviderResult(
            status=FlightSourceStatus.OK,
            rows=[_make_offer()],
        )
        assert result.status is FlightSourceStatus.OK
        assert len(result.rows) == 1
        assert isinstance(result.rows[0], FlightItineraryOffer)

    def test_ok_accepts_multiple_offers(self):
        offer1 = _make_offer()
        offer2 = _make_offer(
            trip_type=TripType.ROUND_TRIP,
            return_date="2026-06-08",
            return_leg=_make_leg(),
        )
        result = FlightProviderResult(
            status=FlightSourceStatus.OK,
            rows=[offer1, offer2],
        )
        assert len(result.rows) == 2

    def test_ok_rejects_zero_rows(self):
        with pytest.raises(ValueError, match="EMPTY"):
            FlightProviderResult(status=FlightSourceStatus.OK, rows=[])

    def test_unavailable_rejects_offer_rows(self):
        with pytest.raises(ValueError, match="must carry zero rows"):
            FlightProviderResult(
                status=FlightSourceStatus.UNAVAILABLE,
                rows=[_make_offer()],
                reason="bug",
            )

    def test_error_rejects_offer_rows(self):
        with pytest.raises(ValueError, match="must carry zero rows"):
            FlightProviderResult(
                status=FlightSourceStatus.ERROR,
                rows=[_make_offer()],
                reason="upstream 500",
            )

    def test_empty_rejects_offer_rows(self):
        with pytest.raises(ValueError, match="must carry zero rows"):
            FlightProviderResult(
                status=FlightSourceStatus.EMPTY,
                rows=[_make_offer()],
            )

    def test_ok_rejects_arbitrary_dict_row(self):
        with pytest.raises(ValueError, match="not a FlightItineraryOffer"):
            FlightProviderResult(
                status=FlightSourceStatus.OK,
                rows=[{"source": "mock", "price": 100}],  # type: ignore[list-item]
            )

    def test_canonical_offer_has_no_points_cost_field(self):
        """FlightItineraryOffer must not carry points_cost or points_estimate.

        Points/award prices are a separately gated track; the canonical offer
        type must not emit or require points fields.
        """
        offer = _make_offer()
        assert not hasattr(offer, "points_cost"), (
            "FlightItineraryOffer must not have points_cost field"
        )
        assert not hasattr(offer, "points_estimate"), (
            "FlightItineraryOffer must not have points_estimate field"
        )
        assert not hasattr(offer, "cpp"), (
            "FlightItineraryOffer must not have cpp (cents-per-point) field"
        )

    def test_canonical_offer_price_is_not_a_bare_float(self):
        """FlightPrice is the typed price wrapper — a bare float is not valid."""
        offer = _make_offer()
        assert isinstance(offer.price, FlightPrice)
        # The price amount is positive (invariant enforced in FlightPrice)
        assert offer.price.total_amount > 0

    def test_canonical_offer_has_no_recommendation_tag(self):
        """FlightItineraryOffer must not carry legacy FlightResult scoring tags."""
        offer = _make_offer()
        assert not hasattr(offer, "recommendation_tag"), (
            "FlightItineraryOffer must not have recommendation_tag (legacy FlightResult field)"
        )
        assert not hasattr(offer, "decision"), (
            "FlightItineraryOffer must not have decision (legacy FlightResult field)"
        )

    def test_skyscanner_shell_rows_are_empty_not_offers(self):
        """Skyscanner adapter shell returns UNAVAILABLE, not FlightItineraryOffer rows."""
        provider = SkyscannerFlightProvider()
        req = FlightSearchRequest(
            origin="JFK", destination="CDG", departure_date=date(2026, 6, 1)
        )
        result = provider.search_flights(req)
        assert result.status is FlightSourceStatus.UNAVAILABLE
        assert result.rows == []
        # No FlightItineraryOffer produced while disabled
        assert not any(isinstance(r, FlightItineraryOffer) for r in result.rows)

    def test_ignav_shell_rows_are_empty_not_offers(self):
        """Ignav adapter shell returns UNAVAILABLE, not FlightItineraryOffer rows."""
        provider = IgnavFlightProvider()
        req = FlightSearchRequest(
            origin="JFK", destination="CDG", departure_date=date(2026, 6, 1)
        )
        result = provider.search_flights(req)
        assert result.status is FlightSourceStatus.UNAVAILABLE
        assert result.rows == []
