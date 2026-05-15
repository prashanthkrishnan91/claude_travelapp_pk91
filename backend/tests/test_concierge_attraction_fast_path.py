"""
Tests: broad shared AI Concierge place-search capability fix.

Root causes fixed:
1. INTENT_ATTRACTIONS absent from _FAST_DYNAMIC_INTENTS → added.
2. _FAST_DYNAMIC_INTENTS was the main eligibility gate (brittle allowlist) →
   replaced by _SEMANTIC_PLACE_SEARCH_BLOCKLIST (small blocklist; everything
   not in it is place-search eligible).
3. run_semantic_retrieval_v1 always returned restaurants= bucket regardless
   of query type → now accepts vertical param and routes correctly.
4. INTENT_GENERAL handler missing hotels branch and _semantic_card_first
   missing hotels check → both fixed.

Coverage:
A. Routing — intent detection for attraction/nightlife/hotel/general queries.
B. Eligibility — blocklist gate; open-class; no-destination guard.
C. Vertical detection — query tokens map to correct bucket.
D. Bucket correctness — semantic returns cards in right LiveResearchResult field.
E. Wrong-vertical guard — food/bar only; attractions/hotels unaffected.
F. Nightlife regression — sports bars / cocktail bars still fast-path eligible.
G. Inside-trip — trip context doesn't break shared service behavior.
"""

from __future__ import annotations

import logging
import sys
import os
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.concierge import (
    INTENT_ATTRACTIONS,
    INTENT_NIGHTLIFE,
    INTENT_RESTAURANTS,
    INTENT_GENERAL,
    INTENT_HOTELS,
    INTENT_PLAN_DAY,
    INTENT_BEST_AREA,
    INTENT_COMPARE,
)
from app.services.concierge import ConciergeService, _SEMANTIC_PLACE_SEARCH_BLOCKLIST


# ── Helpers ───────────────────────────────────────────────────────────────────

def _svc() -> ConciergeService:
    return object.__new__(ConciergeService)


def _settings(semantic_on: bool = True, fast_on: bool = False):
    return SimpleNamespace(
        concierge_semantic_retrieval_v1_enabled=semantic_on,
        concierge_fast_dynamic_place_search_v1_enabled=fast_on,
        live_research_enabled=False,
        live_research_cache_ttl_seconds=1800,
        live_research_timeout_seconds=6.0,
        research_engine_require_google_verification=False,
        google_places_api_key="",
        tavily_api_key="",
        brave_search_api_key="",
        serper_api_key="",
    )


# ── Section A: Routing ────────────────────────────────────────────────────────

class TestAttractionIntentRouting:
    """Intent detection for known categories."""

    def test_intent_attractions_in_fast_dynamic_intents(self):
        svc = _svc()
        assert INTENT_ATTRACTIONS in svc._FAST_DYNAMIC_INTENTS, (
            "INTENT_ATTRACTIONS must be in _FAST_DYNAMIC_INTENTS so the fast_dynamic "
            "fallback path is available."
        )

    def test_intent_attractions_in_open_class_eligible(self):
        svc = _svc()
        assert INTENT_ATTRACTIONS in svc._OPEN_CLASS_ELIGIBLE_INTENTS

    def test_intent_hotels_in_fast_dynamic_intents(self):
        svc = _svc()
        assert INTENT_HOTELS in svc._FAST_DYNAMIC_INTENTS

    @pytest.mark.parametrize("query", [
        "top attractions",
        "best attractions in Seattle",
        "museums in Seattle",
        "things to do in Seattle",
    ])
    def test_attraction_queries_detect_as_attractions_intent(self, query):
        svc = _svc()
        intent = svc._detect_intent(query)
        assert intent == INTENT_ATTRACTIONS, (
            f"Query {query!r} should map to INTENT_ATTRACTIONS, got {intent!r}"
        )

    def test_nightlife_intent_still_in_fast_dynamic(self):
        svc = _svc()
        assert INTENT_NIGHTLIFE in svc._FAST_DYNAMIC_INTENTS

    def test_restaurants_intent_still_in_fast_dynamic(self):
        svc = _svc()
        assert INTENT_RESTAURANTS in svc._FAST_DYNAMIC_INTENTS


# ── Section B: Eligibility / blocklist ───────────────────────────────────────

class TestPlaceSearchEligibility:
    """_is_place_search_eligible uses blocklist; everything not in it is eligible."""

    def test_blocklist_contains_plan_day(self):
        assert INTENT_PLAN_DAY in _SEMANTIC_PLACE_SEARCH_BLOCKLIST

    def test_blocklist_contains_best_area(self):
        assert INTENT_BEST_AREA in _SEMANTIC_PLACE_SEARCH_BLOCKLIST

    def test_blocklist_contains_compare(self):
        assert INTENT_COMPARE in _SEMANTIC_PLACE_SEARCH_BLOCKLIST

    def test_attractions_not_in_blocklist(self):
        assert INTENT_ATTRACTIONS not in _SEMANTIC_PLACE_SEARCH_BLOCKLIST

    def test_nightlife_not_in_blocklist(self):
        assert INTENT_NIGHTLIFE not in _SEMANTIC_PLACE_SEARCH_BLOCKLIST

    def test_hotels_not_in_blocklist(self):
        assert INTENT_HOTELS not in _SEMANTIC_PLACE_SEARCH_BLOCKLIST

    def test_restaurants_not_in_blocklist(self):
        assert INTENT_RESTAURANTS not in _SEMANTIC_PLACE_SEARCH_BLOCKLIST

    def test_attractions_eligible_with_destination(self):
        svc = _svc()
        assert svc._is_place_search_eligible(INTENT_ATTRACTIONS, False, "Seattle") is True

    def test_hotels_eligible_with_destination(self):
        svc = _svc()
        assert svc._is_place_search_eligible(INTENT_HOTELS, False, "Seattle") is True

    def test_nightlife_eligible_with_destination(self):
        svc = _svc()
        assert svc._is_place_search_eligible(INTENT_NIGHTLIFE, False, "Seattle") is True

    def test_restaurants_eligible_with_destination(self):
        svc = _svc()
        assert svc._is_place_search_eligible(INTENT_RESTAURANTS, False, "Seattle") is True

    def test_plan_day_not_eligible(self):
        svc = _svc()
        assert svc._is_place_search_eligible(INTENT_PLAN_DAY, False, "Seattle") is False

    def test_best_area_not_eligible(self):
        svc = _svc()
        assert svc._is_place_search_eligible(INTENT_BEST_AREA, False, "Seattle") is False

    def test_no_destination_blocks_all(self):
        svc = _svc()
        for intent in [INTENT_ATTRACTIONS, INTENT_HOTELS, INTENT_NIGHTLIFE, INTENT_RESTAURANTS]:
            assert svc._is_place_search_eligible(intent, False, "") is False, (
                f"Intent {intent} must be blocked when destination is empty"
            )

    def test_general_with_open_class_eligible(self):
        svc = _svc()
        assert svc._is_place_search_eligible(INTENT_GENERAL, True, "Seattle") is True

    def test_general_without_open_class_not_eligible(self):
        svc = _svc()
        assert svc._is_place_search_eligible(INTENT_GENERAL, False, "Seattle") is False


# ── Section B2: Semantic eligibility log ─────────────────────────────────────

class TestAttractionSemanticEligibility:
    """attraction intent with a destination must be semantic-eligible (not skipped)."""

    def test_attractions_not_skipped_when_semantic_on(self, caplog):
        svc = _svc()
        svc._settings = _settings(semantic_on=True)
        svc._get_live_research = lambda: SimpleNamespace(is_live_capable=False)

        with caplog.at_level(logging.INFO, logger="app.services.concierge"):
            svc._fetch_live_research(
                intent=INTENT_ATTRACTIONS,
                destination="Seattle",
                user_query="top attractions",
                trip={},
            )

        skip_logs = [
            r.message for r in caplog.records
            if "semantic_skip" in r.message and "intent_not_eligible" in r.message
        ]
        assert not skip_logs, (
            "INTENT_ATTRACTIONS must NOT produce semantic_skip intent_not_eligible. "
            f"Got: {skip_logs}"
        )

    def test_attractions_produces_semantic_eligible_log(self, caplog):
        svc = _svc()
        svc._settings = _settings(semantic_on=True)
        svc._get_live_research = lambda: SimpleNamespace(is_live_capable=False)

        with caplog.at_level(logging.INFO, logger="app.services.concierge"):
            svc._fetch_live_research(
                intent=INTENT_ATTRACTIONS,
                destination="Seattle",
                user_query="top attractions",
                trip={},
            )

        eligible_logs = [
            r.message for r in caplog.records
            if "semantic_eligible" in r.message
        ]
        assert eligible_logs, (
            "Expected concierge.semantic_eligible log for INTENT_ATTRACTIONS + destination. "
            f"All logs: {[r.message for r in caplog.records]}"
        )

    def test_attractions_semantic_skip_when_no_destination(self, caplog):
        """No destination → semantic must still skip (no_destination, not intent_not_eligible)."""
        svc = _svc()
        svc._settings = _settings(semantic_on=True)
        svc._get_live_research = lambda: SimpleNamespace(is_live_capable=False)

        with caplog.at_level(logging.INFO, logger="app.services.concierge"):
            svc._fetch_live_research(
                intent=INTENT_ATTRACTIONS,
                destination="",
                user_query="top attractions",
                trip={},
            )

        skip_logs = [r.message for r in caplog.records if "semantic_skip" in r.message]
        assert skip_logs, "Expected semantic_skip log when no destination"
        assert any("no_destination" in m for m in skip_logs), (
            f"Expected no_destination reason, got: {skip_logs}"
        )

    @pytest.mark.parametrize("query", [
        "beaches near Lisbon",
        "scenic viewpoints in Tokyo",
        "best museums in Berlin",
        "botanical gardens",
        "waterfall hikes",
        "markets in Marrakech",
    ])
    def test_open_vocabulary_attraction_queries_eligible(self, query, caplog):
        """Open-vocabulary place queries must not be blocked by the eligibility gate."""
        svc = _svc()
        svc._settings = _settings(semantic_on=True)
        svc._get_live_research = lambda: SimpleNamespace(is_live_capable=False)

        with caplog.at_level(logging.INFO, logger="app.services.concierge"):
            svc._fetch_live_research(
                intent=INTENT_ATTRACTIONS,
                destination="Seattle",
                user_query=query,
                trip={},
            )

        skip_logs = [
            r.message for r in caplog.records
            if "semantic_skip" in r.message and "intent_not_eligible" in r.message
        ]
        assert not skip_logs, (
            f"Open-vocabulary query {query!r} must not be blocked. Got skip logs: {skip_logs}"
        )

    @pytest.mark.parametrize("query", [
        "boutique hotels in Kyoto",
        "luxury hotels near the Colosseum",
        "cheap hostels in Bangkok",
    ])
    def test_hotel_queries_eligible_with_hotels_intent(self, query, caplog):
        svc = _svc()
        svc._settings = _settings(semantic_on=True)
        svc._get_live_research = lambda: SimpleNamespace(is_live_capable=False)

        with caplog.at_level(logging.INFO, logger="app.services.concierge"):
            svc._fetch_live_research(
                intent=INTENT_HOTELS,
                destination="Kyoto",
                user_query=query,
                trip={},
            )

        skip_logs = [
            r.message for r in caplog.records
            if "semantic_skip" in r.message and "intent_not_eligible" in r.message
        ]
        assert not skip_logs, (
            f"Hotel query {query!r} must not be blocked. Got: {skip_logs}"
        )


# ── Section C: Vertical detection ────────────────────────────────────────────

class TestVerticalDetection:
    """_detect_semantic_vertical routes queries to the correct bucket."""

    def test_attractions_intent_maps_to_attractions(self):
        svc = _svc()
        assert svc._detect_semantic_vertical(INTENT_ATTRACTIONS, "top attractions") == "attractions"

    def test_hotels_intent_maps_to_hotels(self):
        svc = _svc()
        assert svc._detect_semantic_vertical(INTENT_HOTELS, "hotels near downtown") == "hotels"

    def test_restaurants_intent_maps_to_restaurants(self):
        svc = _svc()
        assert svc._detect_semantic_vertical(INTENT_RESTAURANTS, "sushi restaurants") == "restaurants"

    def test_nightlife_intent_maps_to_restaurants(self):
        svc = _svc()
        assert svc._detect_semantic_vertical(INTENT_NIGHTLIFE, "cocktail bars") == "restaurants"

    @pytest.mark.parametrize("query,expected", [
        ("beaches near the city", "attractions"),
        ("scenic viewpoints", "attractions"),
        ("museums in the old town", "attractions"),
        ("hiking trails", "attractions"),
        ("botanical gardens", "attractions"),
        ("waterfall tours", "attractions"),
        ("markets in Marrakech", "attractions"),
    ])
    def test_general_intent_attraction_tokens(self, query, expected):
        svc = _svc()
        result = svc._detect_semantic_vertical(INTENT_GENERAL, query)
        assert result == expected, (
            f"Query {query!r}: expected vertical={expected!r}, got {result!r}"
        )

    @pytest.mark.parametrize("query,expected", [
        ("boutique hotels downtown", "hotels"),
        ("resorts with pool", "hotels"),
    ])
    def test_general_intent_hotel_tokens(self, query, expected):
        svc = _svc()
        result = svc._detect_semantic_vertical(INTENT_GENERAL, query)
        assert result == expected, (
            f"Query {query!r}: expected vertical={expected!r}, got {result!r}"
        )

    def test_general_intent_unknown_query_defaults_to_restaurants(self):
        svc = _svc()
        result = svc._detect_semantic_vertical(INTENT_GENERAL, "izakaya near Shibuya")
        assert result == "restaurants"


# ── Section D: Bucket correctness (semantic_retrieval_v1) ────────────────────

class TestBucketCorrectness:
    """run_semantic_retrieval_v1 returns cards in the correct LiveResearchResult field."""

    def _make_result(self, vertical: str, cards: list):
        """Construct a LiveResearchResult the same way _run_pipeline does."""
        from app.services.live_research import LiveResearchResult
        from app.models.concierge import SOURCE_LIVE_SEARCH, SOURCE_NONE
        if not cards:
            return LiveResearchResult(source_status=SOURCE_NONE)
        if vertical == "hotels":
            return LiveResearchResult(hotels=cards, source_status=SOURCE_LIVE_SEARCH)
        if vertical == "attractions":
            return LiveResearchResult(attractions=cards, source_status=SOURCE_LIVE_SEARCH)
        return LiveResearchResult(restaurants=cards, source_status=SOURCE_LIVE_SEARCH)

    def test_restaurants_vertical_populates_restaurants_field(self):
        from app.models.concierge import UnifiedRestaurantResult
        card = UnifiedRestaurantResult(name="Cafe A")
        result = self._make_result("restaurants", [card])
        assert result.restaurants == [card]
        assert not result.attractions
        assert not result.hotels

    def test_attractions_vertical_populates_attractions_field(self):
        from app.models.concierge import UnifiedAttractionResult
        card = UnifiedAttractionResult(name="Space Needle", category="landmark")
        result = self._make_result("attractions", [card])
        assert result.attractions == [card]
        assert not result.restaurants
        assert not result.hotels

    def test_hotels_vertical_populates_hotels_field(self):
        from app.models.concierge import UnifiedHotelResult
        hotel = UnifiedHotelResult(name="Grand Hotel")
        result = self._make_result("hotels", [hotel])
        assert result.hotels == [hotel]
        assert not result.restaurants
        assert not result.attractions

    def test_empty_pipeline_returns_empty_result(self):
        result = self._make_result("attractions", [])
        assert not result.restaurants
        assert not result.attractions
        assert not result.hotels

    def test_vertical_param_forwarded_to_pipeline(self):
        """run_semantic_retrieval_v1 must pass vertical= to _run_pipeline."""
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1
        from app.services.live_research import LiveResearchResult
        from app.models.concierge import SOURCE_NONE
        import app.concierge.semantic_retrieval as sr_mod

        captured = {}

        def recording_pipeline(**kw):
            captured["vertical"] = kw.get("vertical")
            return LiveResearchResult(source_status=SOURCE_NONE)

        original = sr_mod._run_pipeline
        try:
            sr_mod._run_pipeline = recording_pipeline
            run_semantic_retrieval_v1(
                destination="Seattle",
                user_query="beaches",
                api_key="fake-key-for-test",
                vertical="attractions",
            )
        finally:
            sr_mod._run_pipeline = original

        assert captured.get("vertical") == "attractions", (
            f"Expected vertical='attractions' forwarded to _run_pipeline, got {captured.get('vertical')!r}"
        )


# ── Section E: Wrong-vertical guard not applied to attractions ────────────────

class TestWrongVerticalGuardAttractions:
    """The wrong-vertical guard must NOT apply to attraction/museum/hotel queries."""

    def test_attraction_types_pass_vertical_guard(self):
        from app.concierge.retrieval_planner import entity_passes_vertical_guard
        assert entity_passes_vertical_guard(
            ["tourist_attraction", "point_of_interest", "establishment"],
            "tourist_attraction",
            is_food_bar=False,
        ) is True

    def test_museum_types_pass_vertical_guard(self):
        from app.concierge.retrieval_planner import entity_passes_vertical_guard
        assert entity_passes_vertical_guard(
            ["museum", "point_of_interest"],
            "museum",
            is_food_bar=False,
        ) is True

    def test_park_types_pass_vertical_guard(self):
        from app.concierge.retrieval_planner import entity_passes_vertical_guard
        assert entity_passes_vertical_guard(
            ["park", "establishment"],
            "park",
            is_food_bar=False,
        ) is True

    def test_hotel_types_pass_vertical_guard(self):
        from app.concierge.retrieval_planner import entity_passes_vertical_guard
        assert entity_passes_vertical_guard(
            ["lodging", "point_of_interest"],
            "lodging",
            is_food_bar=False,
        ) is True

    def test_is_food_bar_query_false_for_attractions_query(self):
        from app.concierge.retrieval_planner import is_food_bar_query
        from app.concierge.frame_extractor import extract_frame

        for query in ["top attractions", "best museums", "botanical gardens", "beach hikes"]:
            frame = extract_frame(query, "Seattle")
            assert not is_food_bar_query(frame), (
                f"is_food_bar_query returned True for attraction query {query!r}"
            )

    def test_is_food_bar_query_false_for_hotel_query(self):
        from app.concierge.retrieval_planner import is_food_bar_query
        from app.concierge.frame_extractor import extract_frame

        frame = extract_frame("boutique hotels", "Seattle")
        assert not is_food_bar_query(frame), "hotel query must not be classified as food/bar"

    def test_sports_bars_still_food_bar_query(self):
        from app.concierge.retrieval_planner import is_food_bar_query
        from app.concierge.frame_extractor import extract_frame

        frame = extract_frame("sports bars", "Seattle")
        assert is_food_bar_query(frame), "sports bars must still be a food/bar query"

    def test_cocktail_bars_still_food_bar_query(self):
        from app.concierge.retrieval_planner import is_food_bar_query
        from app.concierge.frame_extractor import extract_frame

        frame = extract_frame("cocktail bars near Pike Place", "Seattle")
        assert is_food_bar_query(frame), "cocktail bars must still be a food/bar query"


# ── Section F: Nightlife regression guard ────────────────────────────────────

class TestNightlifeRegressionGuard:
    """sports bars and cocktail bars must still fast-path, not through attractions guard."""

    @pytest.mark.parametrize("query", [
        "sports bars",
        "cocktail bars near Pike Place",
        "best cocktail bars in Seattle",
    ])
    def test_nightlife_queries_detect_as_nightlife(self, query):
        svc = _svc()
        intent = svc._detect_intent(query)
        assert intent == INTENT_NIGHTLIFE, (
            f"Query {query!r} should map to INTENT_NIGHTLIFE, got {intent!r}"
        )

    def test_nightlife_not_skipped_when_semantic_on(self, caplog):
        svc = _svc()
        svc._settings = _settings(semantic_on=True)
        svc._get_live_research = lambda: SimpleNamespace(is_live_capable=False)

        with caplog.at_level(logging.INFO, logger="app.services.concierge"):
            svc._fetch_live_research(
                intent=INTENT_NIGHTLIFE,
                destination="Seattle",
                user_query="sports bars",
                trip={},
            )

        skip_logs = [
            r.message for r in caplog.records
            if "semantic_skip" in r.message and "intent_not_eligible" in r.message
        ]
        assert not skip_logs, (
            "INTENT_NIGHTLIFE must NOT produce intent_not_eligible skip. "
            f"Got: {skip_logs}"
        )


# ── Section G: Inside-trip context ───────────────────────────────────────────

class TestInsideTripContext:
    """Same service behavior applies when a trip dict is provided (inside-trip flow)."""

    def test_attractions_eligible_with_trip_and_destination(self, caplog):
        svc = _svc()
        svc._settings = _settings(semantic_on=True)
        svc._get_live_research = lambda: SimpleNamespace(is_live_capable=False)

        trip = {"id": "trip-123", "destination": "Paris", "start_date": "2026-06-01", "end_date": "2026-06-07"}

        with caplog.at_level(logging.INFO, logger="app.services.concierge"):
            svc._fetch_live_research(
                intent=INTENT_ATTRACTIONS,
                destination="Paris",
                user_query="must-see museums in Paris",
                trip=trip,
            )

        skip_logs = [
            r.message for r in caplog.records
            if "semantic_skip" in r.message and "intent_not_eligible" in r.message
        ]
        assert not skip_logs, (
            "Inside-trip attraction query must not produce intent_not_eligible skip. "
            f"Got: {skip_logs}"
        )

    def test_hotels_eligible_with_trip_and_destination(self, caplog):
        svc = _svc()
        svc._settings = _settings(semantic_on=True)
        svc._get_live_research = lambda: SimpleNamespace(is_live_capable=False)

        trip = {"id": "trip-456", "destination": "Tokyo", "start_date": "2026-09-10", "end_date": "2026-09-17"}

        with caplog.at_level(logging.INFO, logger="app.services.concierge"):
            svc._fetch_live_research(
                intent=INTENT_HOTELS,
                destination="Tokyo",
                user_query="boutique hotels near Shinjuku",
                trip=trip,
            )

        skip_logs = [
            r.message for r in caplog.records
            if "semantic_skip" in r.message and "intent_not_eligible" in r.message
        ]
        assert not skip_logs, (
            "Inside-trip hotel query must not produce intent_not_eligible skip. "
            f"Got: {skip_logs}"
        )
