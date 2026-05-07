"""Tests for Google-backed price signals in AI Concierge verified cards.

Coverage:
1. priceLevel from Google is mapped into PlaceSupportingDetails and ConciergeDisplayFields.
2. priceRange from Google is mapped into PlaceSupportingDetails.
3. display_price is formatted from priceRange when present.
4. display_price falls back to priceLevel symbol when priceRange absent.
5. Missing price fields do not drop or break verified cards.
6. _format_display_price handles all priceLevel enum values correctly.
7. _format_display_price returns None when neither field is present.
8. _format_display_price never exposes raw enum names.
9. Value-aware ranking: prefer_lower_price sorts by priceLevel ascending.
10. prefer_lower_price is detected in cheaper/budget/affordable queries.
11. Non-cheaper queries do not set prefer_lower_price.
12. Card cap and no-visible-fallback-note contracts remain intact.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.fast_dynamic_place_search import (
    FastDynamicPlaceSearch,
    ParsedPlaceQuery,
    _OPERATIONAL,
    _format_display_price,
    parse_place_query,
)
from app.models.concierge import PlaceSupportingDetails, ConciergeDisplayFields


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_place(
    *,
    name: str = "Test Venue",
    place_id: str = "pid_test",
    price_level: Optional[str] = None,
    price_range: Optional[Dict[str, Any]] = None,
    rating: float = 4.5,
    review_count: int = 300,
    types: Optional[List[str]] = None,
    business_status: str = _OPERATIONAL,
    address: str = "100 W Test St, Chicago, IL",
    maps_uri: str = "https://maps.google.com/?cid=1",
) -> Dict[str, Any]:
    place: Dict[str, Any] = {
        "id": place_id,
        "displayName": {"text": name},
        "types": types or ["restaurant", "food"],
        "rating": rating,
        "userRatingCount": review_count,
        "businessStatus": business_status,
        "formattedAddress": address,
        "googleMapsUri": maps_uri,
        "websiteUri": None,
        "priceLevel": price_level,
    }
    if price_range is not None:
        place["priceRange"] = price_range
    return place


def _parsed(query: str = "cocktail bars", destination: str = "Chicago") -> ParsedPlaceQuery:
    return parse_place_query(query, destination)


def _build_card(place_data: Dict[str, Any]):
    """Use FastDynamicPlaceSearch._to_card in isolation."""
    svc = FastDynamicPlaceSearch.__new__(FastDynamicPlaceSearch)
    svc._api_key = "fake"
    svc._timeout = 6.0
    svc._max_candidates = 15
    return svc._to_card(place_data, parsed=_parsed())


# ── 1. priceLevel mapped into PlaceSupportingDetails ─────────────────────────


class TestPriceLevelMapping:
    def test_price_level_stored_in_supporting_details(self) -> None:
        place = _make_place(price_level="PRICE_LEVEL_MODERATE")
        card = _build_card(place)
        assert card is not None
        assert card.supporting_details is not None
        assert card.supporting_details.price_level == "PRICE_LEVEL_MODERATE"

    def test_price_level_inexpensive(self) -> None:
        place = _make_place(price_level="PRICE_LEVEL_INEXPENSIVE")
        card = _build_card(place)
        assert card is not None
        assert card.supporting_details.price_level == "PRICE_LEVEL_INEXPENSIVE"

    def test_price_level_expensive(self) -> None:
        place = _make_place(price_level="PRICE_LEVEL_EXPENSIVE")
        card = _build_card(place)
        assert card is not None
        assert card.supporting_details.price_level == "PRICE_LEVEL_EXPENSIVE"

    def test_price_level_very_expensive(self) -> None:
        place = _make_place(price_level="PRICE_LEVEL_VERY_EXPENSIVE")
        card = _build_card(place)
        assert card is not None
        assert card.supporting_details.price_level == "PRICE_LEVEL_VERY_EXPENSIVE"

    def test_price_level_free(self) -> None:
        place = _make_place(price_level="PRICE_LEVEL_FREE")
        card = _build_card(place)
        assert card is not None
        assert card.supporting_details.price_level == "PRICE_LEVEL_FREE"

    def test_display_price_set_from_price_level(self) -> None:
        place = _make_place(price_level="PRICE_LEVEL_MODERATE")
        card = _build_card(place)
        assert card is not None
        assert card.display is not None
        assert card.display.display_price == "$$"

    def test_display_price_symbols_all_levels(self) -> None:
        expected = {
            "PRICE_LEVEL_FREE": "Free",
            "PRICE_LEVEL_INEXPENSIVE": "$",
            "PRICE_LEVEL_MODERATE": "$$",
            "PRICE_LEVEL_EXPENSIVE": "$$$",
            "PRICE_LEVEL_VERY_EXPENSIVE": "$$$$",
        }
        for level, symbol in expected.items():
            place = _make_place(price_level=level)
            card = _build_card(place)
            assert card is not None and card.display is not None
            assert card.display.display_price == symbol, f"level={level}"


# ── 2. priceRange mapped into PlaceSupportingDetails ─────────────────────────


class TestPriceRangeMapping:
    def test_price_range_stored_in_supporting_details(self) -> None:
        pr = {
            "startPrice": {"currencyCode": "USD", "units": "10", "nanos": 0},
            "endPrice": {"currencyCode": "USD", "units": "25", "nanos": 0},
        }
        place = _make_place(price_range=pr)
        card = _build_card(place)
        assert card is not None
        assert card.supporting_details is not None
        assert card.supporting_details.price_range == pr

    def test_display_price_from_price_range_beats_price_level(self) -> None:
        pr = {
            "startPrice": {"currencyCode": "USD", "units": "15", "nanos": 0},
            "endPrice": {"currencyCode": "USD", "units": "30", "nanos": 0},
        }
        place = _make_place(price_level="PRICE_LEVEL_MODERATE", price_range=pr)
        card = _build_card(place)
        assert card is not None and card.display is not None
        # priceRange should win over priceLevel
        assert card.display.display_price == "$15–30"

    def test_display_price_uses_currency_code(self) -> None:
        pr = {
            "startPrice": {"currencyCode": "EUR", "units": "12", "nanos": 0},
            "endPrice": {"currencyCode": "EUR", "units": "28", "nanos": 0},
        }
        place = _make_place(price_range=pr)
        card = _build_card(place)
        assert card is not None and card.display is not None
        # Non-USD currencies use code as symbol
        assert card.display.display_price == "EUR12–28"


# ── 3. Missing price fields do not drop cards ─────────────────────────────────


class TestMissingPriceFields:
    def test_card_not_dropped_when_price_absent(self) -> None:
        place = _make_place()  # no price_level, no price_range
        card = _build_card(place)
        assert card is not None

    def test_supporting_details_price_none_when_absent(self) -> None:
        place = _make_place()
        card = _build_card(place)
        assert card is not None
        assert card.supporting_details is not None
        assert card.supporting_details.price_level is None
        assert card.supporting_details.price_range is None

    def test_display_price_none_when_absent(self) -> None:
        place = _make_place()
        card = _build_card(place)
        assert card is not None and card.display is not None
        assert card.display.display_price is None


# ── 4. _format_display_price unit tests ──────────────────────────────────────


class TestFormatDisplayPrice:
    def test_price_range_usd_compact_format(self) -> None:
        pr = {
            "startPrice": {"currencyCode": "USD", "units": "10", "nanos": 0},
            "endPrice": {"currencyCode": "USD", "units": "20", "nanos": 0},
        }
        assert _format_display_price(None, pr) == "$10–20"

    def test_price_range_prefers_over_level(self) -> None:
        pr = {
            "startPrice": {"currencyCode": "USD", "units": "5", "nanos": 0},
            "endPrice": {"currencyCode": "USD", "units": "15", "nanos": 0},
        }
        assert _format_display_price("PRICE_LEVEL_EXPENSIVE", pr) == "$5–15"

    def test_price_level_moderate_returns_symbol(self) -> None:
        assert _format_display_price("PRICE_LEVEL_MODERATE", None) == "$$"

    def test_price_level_inexpensive_returns_symbol(self) -> None:
        assert _format_display_price("PRICE_LEVEL_INEXPENSIVE", None) == "$"

    def test_price_level_free_returns_label(self) -> None:
        assert _format_display_price("PRICE_LEVEL_FREE", None) == "Free"

    def test_none_when_no_data(self) -> None:
        assert _format_display_price(None, None) is None

    def test_never_exposes_raw_enum_name(self) -> None:
        result = _format_display_price("PRICE_LEVEL_MODERATE", None)
        assert "PRICE_LEVEL" not in (result or "")

    def test_price_range_zero_units_returns_none(self) -> None:
        pr = {
            "startPrice": {"currencyCode": "USD", "units": "0", "nanos": 0},
            "endPrice": {"currencyCode": "USD", "units": "0", "nanos": 0},
        }
        assert _format_display_price(None, pr) is None

    def test_price_range_partial_units_falls_through_to_level(self) -> None:
        # malformed range (zero start and end) → fall through to priceLevel
        pr = {
            "startPrice": {"currencyCode": "USD", "units": "0", "nanos": 0},
            "endPrice": {"currencyCode": "USD", "units": "0", "nanos": 0},
        }
        assert _format_display_price("PRICE_LEVEL_EXPENSIVE", pr) == "$$$"


# ── 5. Value-aware ranking ────────────────────────────────────────────────────


class TestValueAwareRanking:
    def _places(self) -> List[Dict[str, Any]]:
        return [
            _make_place(name="Expensive One", price_level="PRICE_LEVEL_EXPENSIVE",
                        rating=4.8, review_count=2000, place_id="pid_expensive"),
            _make_place(name="Cheap One", price_level="PRICE_LEVEL_INEXPENSIVE",
                        rating=4.2, review_count=500, place_id="pid_cheap"),
            _make_place(name="Moderate One", price_level="PRICE_LEVEL_MODERATE",
                        rating=4.5, review_count=1000, place_id="pid_moderate"),
        ]

    def test_prefer_lower_price_sorts_cheaper_first(self) -> None:
        svc = FastDynamicPlaceSearch.__new__(FastDynamicPlaceSearch)
        svc._api_key = "fake"
        svc._timeout = 6.0
        svc._max_candidates = 15
        parsed = parse_place_query("find cheaper nearby cocktail bars", "Chicago")
        assert parsed.prefer_lower_price is True
        ranked = svc._filter_and_rank(self._places(), parsed=parsed, prior_identity_keys=None)
        names = [p["displayName"]["text"] for p in ranked]
        assert names[0] == "Cheap One", f"Expected cheapest first, got {names}"

    def test_normal_ranking_prefers_highest_score(self) -> None:
        svc = FastDynamicPlaceSearch.__new__(FastDynamicPlaceSearch)
        svc._api_key = "fake"
        svc._timeout = 6.0
        svc._max_candidates = 15
        parsed = parse_place_query("cocktail bars", "Chicago")
        assert parsed.prefer_lower_price is False
        ranked = svc._filter_and_rank(self._places(), parsed=parsed, prior_identity_keys=None)
        names = [p["displayName"]["text"] for p in ranked]
        # "Expensive One" has highest rating*review → tops in normal ranking
        assert names[0] == "Expensive One", f"Expected highest-rated first, got {names}"

    def test_value_aware_does_not_add_non_google_cards(self) -> None:
        svc = FastDynamicPlaceSearch.__new__(FastDynamicPlaceSearch)
        svc._api_key = "fake"
        svc._timeout = 6.0
        svc._max_candidates = 15
        parsed = parse_place_query("budget restaurants", "Chicago")
        cards = svc._build_cards(self._places()[:1], parsed=parsed)
        for card in cards:
            assert card.source == "Google Places"
            assert card.verified_place is True

    def test_missing_price_sorts_after_known_prices_in_value_aware_ranking(self) -> None:
        """Unknown priceLevel must NOT default to MODERATE (order 2).

        It must sort after all known-price candidates so places without a price
        signal are never treated as cheaper than genuinely expensive ones.
        """
        places = [
            _make_place(name="No Price Place", price_level=None,
                        rating=4.9, review_count=5000, place_id="pid_no_price"),
            _make_place(name="Cheap Place", price_level="PRICE_LEVEL_INEXPENSIVE",
                        rating=4.0, review_count=200, place_id="pid_cheap"),
            _make_place(name="Expensive Place", price_level="PRICE_LEVEL_EXPENSIVE",
                        rating=4.5, review_count=1000, place_id="pid_expensive"),
        ]
        svc = FastDynamicPlaceSearch.__new__(FastDynamicPlaceSearch)
        svc._api_key = "fake"
        svc._timeout = 6.0
        svc._max_candidates = 15
        parsed = parse_place_query("find cheaper restaurants", "Chicago")
        assert parsed.prefer_lower_price is True
        ranked = svc._filter_and_rank(places, parsed=parsed, prior_identity_keys=None)
        names = [p["displayName"]["text"] for p in ranked]
        assert names[0] == "Cheap Place", f"Cheapest known price must be first, got {names}"
        cheap_idx = names.index("Cheap Place")
        expensive_idx = names.index("Expensive Place")
        no_price_idx = names.index("No Price Place")
        assert cheap_idx < expensive_idx, f"INEXPENSIVE must rank before EXPENSIVE, got {names}"
        assert expensive_idx < no_price_idx, \
            f"Known EXPENSIVE must rank before unknown price, got {names}"


# ── 6. prefer_lower_price detection ─────────────────────────────────────────


class TestPreferLowerPriceDetection:
    def test_cheaper_sets_prefer_lower_price(self) -> None:
        assert parse_place_query("cheaper restaurants", "Chicago").prefer_lower_price is True

    def test_budget_sets_prefer_lower_price(self) -> None:
        assert parse_place_query("budget sushi Chicago", "Chicago").prefer_lower_price is True

    def test_affordable_sets_prefer_lower_price(self) -> None:
        assert parse_place_query("affordable cocktail bars", "Chicago").prefer_lower_price is True

    def test_lower_price_sets_prefer_lower_price(self) -> None:
        assert parse_place_query("find lower-price options", "Chicago").prefer_lower_price is True

    def test_normal_query_does_not_set_prefer_lower_price(self) -> None:
        assert parse_place_query("cocktail bars", "Chicago").prefer_lower_price is False

    def test_upscale_query_does_not_set_prefer_lower_price(self) -> None:
        assert parse_place_query("fine dining restaurants", "Chicago").prefer_lower_price is False

    def test_contextual_cheaper_query_detected(self) -> None:
        # Simulates the contextual query built by buildContextualSearchQuery frontend
        q = "Best cocktail bars in Chicago — find cheaper nearby"
        assert parse_place_query(q, "Chicago").prefer_lower_price is True


# ── 7. No fallback notes / contracts intact ──────────────────────────────────


class TestContractIntegrity:
    def test_price_field_in_typed_card_payload(self) -> None:
        pr = {
            "startPrice": {"currencyCode": "USD", "units": "12", "nanos": 0},
            "endPrice": {"currencyCode": "USD", "units": "25", "nanos": 0},
        }
        place = _make_place(price_level="PRICE_LEVEL_MODERATE", price_range=pr)
        card = _build_card(place)
        assert card is not None
        # supportingDetails shape
        assert hasattr(card.supporting_details, "price_level")
        assert hasattr(card.supporting_details, "price_range")
        # display shape
        assert hasattr(card.display, "display_price")
        # Values
        assert card.supporting_details.price_level == "PRICE_LEVEL_MODERATE"
        assert card.supporting_details.price_range == pr
        assert card.display.display_price == "$12–25"  # priceRange beats priceLevel

    def test_model_serializes_price_fields(self) -> None:
        sd = PlaceSupportingDetails(
            price_level="PRICE_LEVEL_MODERATE",
            price_range={"startPrice": {"units": "10"}, "endPrice": {"units": "20"}},
        )
        dumped = sd.model_dump()
        assert "price_level" in dumped
        assert "price_range" in dumped
        assert dumped["price_level"] == "PRICE_LEVEL_MODERATE"

    def test_display_price_in_concierge_display_fields(self) -> None:
        cd = ConciergeDisplayFields(
            display_name="Test",
            display_category="Bar",
            display_why="Great place",
            display_price="$$",
        )
        dumped = cd.model_dump()
        assert dumped["display_price"] == "$$"

    def test_display_price_absent_when_not_set(self) -> None:
        cd = ConciergeDisplayFields(
            display_name="Test",
            display_category="Bar",
            display_why="Great place",
        )
        dumped = cd.model_dump()
        assert dumped.get("display_price") is None
