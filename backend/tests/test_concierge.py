"""Tests for AI concierge service and retrieval layer."""

import sys
import os

# Allow imports from backend/app without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.models.concierge import (
    INTENT_AREA_ADVICE,
    INTENT_ATTRACTIONS,
    INTENT_BEST_AREA,
    INTENT_COMPARE,
    INTENT_FAMILY_FRIENDLY,
    INTENT_GENERAL,
    INTENT_HIDDEN_GEMS,
    INTENT_HOTELS,
    INTENT_LUXURY_VALUE,
    INTENT_MICHELIN_RESTAURANTS,
    INTENT_PLAN_DAY,
    INTENT_RESTAURANTS,
    INTENT_REWARDS_HELP,
    INTENT_ROMANTIC,
    SOURCE_CURATED_STATIC,
    SOURCE_NONE,
    SOURCE_UNAVAILABLE,
)
from app.services.concierge import ConciergeService
from app.services.michelin_retriever import MichelinRetriever

FAKE_TRIP_ID = UUID("00000000-0000-0000-0000-000000000001")
FAKE_USER_ID = UUID("00000000-0000-0000-0000-000000000002")

_FAKE_CLAUDE_JSON = json.dumps(
    {"response": "Great options here.", "suggestions": []}
)


# ── MichelinRetriever tests ───────────────────────────────────────────────────

class TestMichelinRetriever:
    def test_unsupported_destination_returns_empty_and_unavailable(self):
        results, status = MichelinRetriever().fetch("Reykjavik", "Michelin restaurants")
        assert results == [], "Should return no results for unsupported destination"
        assert status == SOURCE_UNAVAILABLE

    def test_honolulu_returns_results_and_curated_static(self):
        results, status = MichelinRetriever().fetch("Honolulu", "Michelin restaurants")
        assert len(results) > 0, "Honolulu should have curated Michelin data"
        assert status == SOURCE_CURATED_STATIC

    def test_honolulu_results_have_michelin_status(self):
        results, _ = MichelinRetriever().fetch("Honolulu")
        for r in results:
            assert r.michelin_status is not None, f"{r.name} is missing michelin_status"

    def test_no_fake_fallback_restaurants(self):
        """Restaurants like 'The Grand Table' or 'Maison Classique' must never appear."""
        fake_names = {"The Grand Table", "Maison Classique", "Ember & Oak", "Trattoria del Mercato"}
        for city in ["Paris", "Tokyo", "Sydney", "Cape Town", "Mumbai"]:
            results, _ = MichelinRetriever().fetch(city)
            result_names = {r.name for r in results}
            overlap = fake_names & result_names
            assert not overlap, f"Fake fallback data found for {city}: {overlap}"

    def test_unknown_city_never_returns_fake_michelin_data(self):
        results, status = MichelinRetriever().fetch("Nairobi")
        assert results == []
        assert status == SOURCE_UNAVAILABLE

    def test_bib_gourmand_filter(self):
        results, _ = MichelinRetriever().fetch("Paris", "Bib Gourmand restaurants")
        for r in results:
            assert r.michelin_status == "Bib Gourmand"

    def test_source_is_michelin_guide(self):
        results, _ = MichelinRetriever().fetch("Tokyo")
        for r in results:
            assert r.source == "Michelin Guide"

    def test_results_sorted_by_tier(self):
        results, _ = MichelinRetriever().fetch("Paris")
        tier_order = {"3 Stars": 5, "2 Stars": 4, "1 Star": 3, "Bib Gourmand": 2, "Selected": 1}
        scores = [tier_order.get(r.michelin_status, 0) for r in results]
        assert scores == sorted(scores, reverse=True), "Results should be sorted by Michelin tier"


# ── ConciergeService intent detection tests ───────────────────────────────────

class TestIntentDetection:
    """Tests for ConciergeService._detect_intent — no DB required."""

    def _svc(self) -> ConciergeService:
        svc = object.__new__(ConciergeService)
        return svc

    def test_michelin_intent(self):
        svc = self._svc()
        assert svc._detect_intent("Michelin restaurants in Honolulu") == INTENT_MICHELIN_RESTAURANTS

    def test_michelin_intent_bib_gourmand(self):
        svc = self._svc()
        assert svc._detect_intent("Bib Gourmand spots in Paris") == INTENT_MICHELIN_RESTAURANTS

    def test_michelin_intent_starred(self):
        svc = self._svc()
        assert svc._detect_intent("starred restaurants Tokyo") == INTENT_MICHELIN_RESTAURANTS

    def test_hidden_gems_intent(self):
        svc = self._svc()
        assert svc._detect_intent("hidden gem restaurants in Paris") == INTENT_HIDDEN_GEMS

    def test_hidden_gems_off_beaten(self):
        svc = self._svc()
        assert svc._detect_intent("off the beaten path dining in Berlin") == INTENT_HIDDEN_GEMS

    def test_romantic_intent(self):
        svc = self._svc()
        assert svc._detect_intent("romantic dinner in Paris for our anniversary") == INTENT_ROMANTIC

    def test_family_intent(self):
        svc = self._svc()
        assert svc._detect_intent("family-friendly restaurants in Rome") == INTENT_FAMILY_FRIENDLY

    def test_luxury_intent(self):
        svc = self._svc()
        assert svc._detect_intent("luxury dining in Singapore") == INTENT_LUXURY_VALUE

    def test_restaurants_intent(self):
        svc = self._svc()
        assert svc._detect_intent("best restaurants in Berlin") == INTENT_RESTAURANTS

    def test_attractions_intent(self):
        svc = self._svc()
        assert svc._detect_intent("best attractions in Rome") == INTENT_ATTRACTIONS

    def test_attractions_things_to_do(self):
        svc = self._svc()
        assert svc._detect_intent("things to do in Tokyo") == INTENT_ATTRACTIONS

    def test_hotels_intent(self):
        svc = self._svc()
        assert svc._detect_intent("best hotels near the city center") == INTENT_HOTELS

    def test_best_area_intent(self):
        svc = self._svc()
        assert svc._detect_intent("best area to stay in Tokyo") == INTENT_BEST_AREA

    def test_best_area_neighbourhood(self):
        svc = self._svc()
        assert svc._detect_intent("which neighbourhood is best in Paris") == INTENT_BEST_AREA

    def test_plan_day_intent(self):
        svc = self._svc()
        assert svc._detect_intent("plan my day in Barcelona") == INTENT_PLAN_DAY

    def test_compare_intent(self):
        svc = self._svc()
        assert svc._detect_intent("compare Septime vs Le Chateaubriand") == INTENT_COMPARE

    def test_rewards_intent(self):
        svc = self._svc()
        assert svc._detect_intent("best ways to use points in Tokyo") == INTENT_REWARDS_HELP

    def test_general_fallback(self):
        svc = self._svc()
        assert svc._detect_intent("what's the weather like?") == INTENT_GENERAL


# ── ConciergeService.search() integration tests (mocked) ─────────────────────

def _make_mock_db(destination: str = "Paris") -> MagicMock:
    """Build a mock Supabase client that returns a minimal trip row."""
    mock_db = MagicMock()
    chain = mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value
    chain.execute.return_value.data = [
        {
            "id": str(FAKE_TRIP_ID),
            "destination": destination,
            "start_date": "2026-06-01",
            "end_date": "2026-06-07",
            "title": "Test Trip",
            "user_id": str(FAKE_USER_ID),
        }
    ]
    return mock_db


class TestConciergeSearch:
    def _svc(self, destination: str = "Paris") -> ConciergeService:
        return ConciergeService(_make_mock_db(destination))

    def _mock_search_svc(self):
        """Return a SearchService mock with empty results."""
        m = MagicMock()
        m.search_restaurants.return_value = []
        m.search_attractions.return_value = []
        m.search_hotels.return_value = []
        return m

    def test_michelin_honolulu_uses_retrieval(self):
        svc = self._svc("Honolulu")
        with patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            result = svc.search(FAKE_TRIP_ID, "Michelin restaurants in Honolulu", FAKE_USER_ID)
        assert result.retrieval_used is True
        assert result.intent == INTENT_MICHELIN_RESTAURANTS
        assert len(result.restaurants) > 0
        assert result.source_status == SOURCE_CURATED_STATIC
        assert result.warnings == []

    def test_michelin_unsupported_destination_sets_warning(self):
        svc = self._svc("Reykjavik")
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            MockSearch.return_value = self._mock_search_svc()
            result = svc.search(FAKE_TRIP_ID, "Michelin restaurants in Reykjavik", FAKE_USER_ID)
        assert len(result.warnings) > 0
        assert "Michelin" in result.warnings[0]
        assert result.source_status == SOURCE_NONE

    def test_restaurants_query_uses_retrieval(self):
        svc = self._svc("Berlin")
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            mock_svc = self._mock_search_svc()
            MockSearch.return_value = mock_svc
            result = svc.search(FAKE_TRIP_ID, "best restaurants in Berlin", FAKE_USER_ID)
        assert result.retrieval_used is True
        assert result.intent == INTENT_RESTAURANTS
        assert result.source_status == SOURCE_NONE
        mock_svc.search_restaurants.assert_called_once()

    def test_attractions_query_uses_retrieval(self):
        svc = self._svc("Rome")
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            mock_svc = self._mock_search_svc()
            MockSearch.return_value = mock_svc
            result = svc.search(FAKE_TRIP_ID, "best attractions in Rome", FAKE_USER_ID)
        assert result.retrieval_used is True
        assert result.intent == INTENT_ATTRACTIONS
        assert result.source_status == SOURCE_NONE
        mock_svc.search_attractions.assert_called_once()

    def test_response_has_all_required_fields(self):
        svc = self._svc("Tokyo")
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            MockSearch.return_value = self._mock_search_svc()
            result = svc.search(FAKE_TRIP_ID, "things to do in Tokyo", FAKE_USER_ID)
        assert hasattr(result, "retrieval_used")
        assert hasattr(result, "source_status")
        assert hasattr(result, "warnings")
        assert hasattr(result, "sources")
        assert hasattr(result, "attractions")
        assert hasattr(result, "hotels")
        assert hasattr(result, "areas")
        assert isinstance(result.warnings, list)
        assert isinstance(result.sources, list)

    def test_michelin_restaurants_not_labeled_as_live_search(self):
        """Michelin curated data must not claim to be live search results."""
        svc = self._svc("Paris")
        with patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            result = svc.search(FAKE_TRIP_ID, "Michelin restaurants in Paris", FAKE_USER_ID)
        assert result.source_status != "live_search"
        assert result.source_status == SOURCE_CURATED_STATIC

    def test_restaurant_converter_handles_missing_optional_fields(self):
        svc = self._svc("Chicago")
        raw = SimpleNamespace(
            name="Lou's",
            cuisine="Pizza",
            location="River North",
            rating=4.6,
            ai_score=88.0,
            booking_url="https://book.example/lous",
            tags=["Local Favorite"],
            num_reviews=1200,
        )
        converted = svc._to_unified_restaurant(raw)
        assert converted.name == "Lou's"
        assert converted.cuisine == "Pizza"
        assert converted.michelin_status is None
        assert converted.booking_link == "https://book.example/lous"
        assert "Michelin status" not in (converted.summary or "")

    def test_best_restaurants_near_hotel_returns_structured_restaurants(self):
        svc = self._svc("Chicago")
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            mock_svc = self._mock_search_svc()
            mock_svc.search_restaurants.return_value = [
                SimpleNamespace(
                    name="Boka",
                    cuisine="American",
                    location="Lincoln Park",
                    rating=4.7,
                    ai_score=90.0,
                    booking_url="https://book.example/boka",
                    tags=["Fine Dining"],
                    num_reviews=2100,
                )
            ]
            MockSearch.return_value = mock_svc
            result = svc.search(FAKE_TRIP_ID, "Best restaurants near my hotel in Chicago", FAKE_USER_ID)
        assert result.intent == INTENT_RESTAURANTS
        assert result.restaurants
        assert result.restaurants[0].name == "Boka"
        assert result.source_status in {"sample_data", "app_database", "none"}

    @pytest.mark.parametrize(
        "query,expected_intent",
        [
            ("Compare neighborhoods", INTENT_COMPARE),
            ("Attractions for Day 2", INTENT_PLAN_DAY),
            ("Best restaurants near my hotel", INTENT_RESTAURANTS),
        ],
    )
    def test_chip_prompts_do_not_500(self, query, expected_intent):
        svc = self._svc("Chicago")
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            mock_svc = self._mock_search_svc()
            mock_svc.search_restaurants.return_value = [
                SimpleNamespace(
                    name="Test Restaurant",
                    cuisine="American",
                    location="Loop",
                    rating=4.4,
                    ai_score=82.0,
                    booking_url="https://book.example/test",
                    tags=["Local Favorite"],
                    num_reviews=500,
                )
            ]
            mock_svc.search_attractions.return_value = [
                SimpleNamespace(
                    name="Millennium Park",
                    category="landmark",
                    location="The Loop",
                    rating=4.7,
                    ai_score=89.0,
                    num_reviews=15000,
                    tags=["Must Visit"],
                    description="Iconic downtown park.",
                    duration_minutes=90,
                )
            ]
            MockSearch.return_value = mock_svc
            result = svc.search(FAKE_TRIP_ID, query, FAKE_USER_ID)
        assert result.intent == expected_intent
        assert isinstance(result.response, str)
