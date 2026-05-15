"""
Tests: attraction/category queries must use the fast Google-verified card-first path.

Root cause that was fixed: INTENT_ATTRACTIONS was absent from _FAST_DYNAMIC_INTENTS,
causing "top attractions", "museums", etc. to fall into the legacy Tavily/live_research
path (~123s).  After the fix, INTENT_ATTRACTIONS is in _FAST_DYNAMIC_INTENTS and the
semantic_retrieval_v1 pipeline runs.

Coverage:
A. Routing — INTENT_ATTRACTIONS is in _FAST_DYNAMIC_INTENTS and semantic-eligible.
B. Semantic path — attraction queries enter semantic_retrieval_v1, not Tavily.
C. Vertical guard — wrong-vertical guard (food/bar only) does not block attractions/museums.
D. Nightlife regression — "sports bars" / "cocktail bars" still fast-path and guard-free.
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
)
from app.services.concierge import ConciergeService


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
    """INTENT_ATTRACTIONS must be in _FAST_DYNAMIC_INTENTS after the fix."""

    def test_intent_attractions_in_fast_dynamic_intents(self):
        svc = _svc()
        assert INTENT_ATTRACTIONS in svc._FAST_DYNAMIC_INTENTS, (
            "INTENT_ATTRACTIONS must be in _FAST_DYNAMIC_INTENTS so semantic "
            "retrieval v1 runs for attraction queries instead of Tavily/live_research."
        )

    def test_intent_attractions_in_open_class_eligible(self):
        svc = _svc()
        assert INTENT_ATTRACTIONS in svc._OPEN_CLASS_ELIGIBLE_INTENTS

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
        """Regression: nightlife must still be fast-path eligible."""
        svc = _svc()
        assert INTENT_NIGHTLIFE in svc._FAST_DYNAMIC_INTENTS

    def test_restaurants_intent_still_in_fast_dynamic(self):
        svc = _svc()
        assert INTENT_RESTAURANTS in svc._FAST_DYNAMIC_INTENTS


# ── Section B: Semantic eligibility log ──────────────────────────────────────

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


# ── Section C: Wrong-vertical guard not applied to attractions ────────────────

class TestWrongVerticalGuardAttractions:
    """The wrong-vertical guard must NOT apply to attraction/museum/hotel queries."""

    def test_attraction_types_pass_vertical_guard(self):
        from app.concierge.retrieval_planner import entity_passes_vertical_guard
        # tourist_attraction + point_of_interest — must pass
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
        """Attraction queries must not be classified as food/bar."""
        from app.concierge.retrieval_planner import is_food_bar_query
        from app.concierge.frame_extractor import extract_frame

        for query in ["top attractions", "best museums", "parks with views"]:
            frame = extract_frame(query, "Seattle")
            assert not is_food_bar_query(frame), (
                f"is_food_bar_query returned True for attraction query {query!r}"
            )

    def test_sports_bars_still_food_bar_query(self):
        """Regression: sports bars must still be classified as food/bar."""
        from app.concierge.retrieval_planner import is_food_bar_query
        from app.concierge.frame_extractor import extract_frame

        frame = extract_frame("sports bars", "Seattle")
        assert is_food_bar_query(frame), "sports bars must still be a food/bar query"

    def test_cocktail_bars_still_food_bar_query(self):
        from app.concierge.retrieval_planner import is_food_bar_query
        from app.concierge.frame_extractor import extract_frame

        frame = extract_frame("cocktail bars near Pike Place", "Seattle")
        assert is_food_bar_query(frame), "cocktail bars must still be a food/bar query"


# ── Section D: Nightlife regression guard ────────────────────────────────────

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
