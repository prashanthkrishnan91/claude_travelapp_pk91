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
    INTENT_NIGHTLIFE,
    INTENT_PLAN_DAY,
    INTENT_RESTAURANTS,
    INTENT_REWARDS_HELP,
    INTENT_ROMANTIC,
    SOURCE_CURATED_STATIC,
    SOURCE_NONE,
    SOURCE_SAMPLE_DATA,
    SOURCE_UNAVAILABLE,
    UnifiedRestaurantResult,
)
from app.services.concierge import ConciergeService
from app.services.live_research import LiveResearchResult
from app.services.michelin_retriever import MichelinRetriever
from app.concierge.router import route_prompt

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

    def test_nearby_drinks_intent_routes_to_restaurants(self):
        svc = self._svc()
        assert svc._detect_intent("Add nearby drinks") == INTENT_NIGHTLIFE

    @pytest.mark.parametrize(
        "query",
        [
            "Nearby cocktail bars",
            "Best rooftop bars",
            "Wine bars near dinner",
            "Speakeasy recommendations",
            "Nightlife after dinner",
        ],
    )
    def test_nightlife_queries_route_to_nightlife_intent(self, query):
        svc = self._svc()
        assert svc._detect_intent(query) == INTENT_NIGHTLIFE

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

    @pytest.mark.parametrize(
        ("prompt", "expected_response_type", "expected_intent", "expected_category"),
        [
            ("Best cocktail bars", "place_recommendations", INTENT_NIGHTLIFE, "bar"),
            ("Nearby cocktail bars", "place_recommendations", INTENT_NIGHTLIFE, "bar"),
            ("Best brunch cafes", "place_recommendations", INTENT_RESTAURANTS, "cafe"),
            ("Michelin restaurants", "place_recommendations", INTENT_MICHELIN_RESTAURANTS, "restaurant"),
            ("Hidden gem restaurants", "place_recommendations", INTENT_HIDDEN_GEMS, "restaurant"),
            ("Best hotels", "place_recommendations", INTENT_HOTELS, "hotel"),
            ("Things to do on Day 2", "place_recommendations", INTENT_PLAN_DAY, "attraction"),
            ("Compare River North vs West Loop", "place_recommendations", INTENT_COMPARE, "comparison"),
            ("Points vs cash ideas", "trip_advice", INTENT_REWARDS_HELP, "advice"),
        ],
    )
    def test_qa_prompt_matrix_routes_to_expected_response_and_legacy_intent(
        self,
        prompt: str,
        expected_response_type: str,
        expected_intent: str,
        expected_category: str,
    ):
        svc = self._svc()
        decision = route_prompt(prompt, confidence_threshold=0.5)
        assert decision.response_type == expected_response_type
        detected_intent = svc._detect_intent(prompt)
        assert detected_intent == expected_intent
        category_by_intent = {
            INTENT_NIGHTLIFE: "bar",
            INTENT_RESTAURANTS: "cafe",
            INTENT_MICHELIN_RESTAURANTS: "restaurant",
            INTENT_HIDDEN_GEMS: "restaurant",
            INTENT_HOTELS: "hotel",
            INTENT_PLAN_DAY: "attraction",
            INTENT_COMPARE: "comparison",
            INTENT_REWARDS_HELP: "advice",
        }
        assert category_by_intent[detected_intent] == expected_category


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

    def test_summary_best_overall_is_aligned_to_first_ranked_card(self):
        svc = self._svc("Chicago")
        live_result = LiveResearchResult(
            restaurants=[
                UnifiedRestaurantResult(
                    name="Lula Cafe",
                    cuisine="Cafe",
                    neighborhood="Logan Square",
                    rating=4.6,
                    summary="Brunch-focused cafe.",
                ),
                UnifiedRestaurantResult(
                    name="Aba",
                    cuisine="Restaurant",
                    neighborhood="Fulton Market",
                    rating=4.7,
                    summary="Mediterranean restaurant.",
                ),
            ],
            source_status="live_search",
            provider_name="Stub",
        )
        bad_llm = json.dumps({"response": "Best overall: Aba. Great brunch options.", "suggestions": []})
        with patch.object(svc, "_fetch_live_research", return_value=live_result), \
             patch.object(svc, "_call_claude", return_value=bad_llm):
            result = svc.search(FAKE_TRIP_ID, "brunch cafes near my hotel", FAKE_USER_ID)
        assert result.restaurants[0].name == "Lula Cafe"
        assert "best overall: lula cafe" in result.response.lower()

    def test_add_nearby_drinks_returns_structured_cards(self):
        svc = self._svc("Chicago")
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            MockSearch.return_value = self._mock_search_svc()
            result = svc.search(FAKE_TRIP_ID, "Add nearby drinks", FAKE_USER_ID)
        assert result.intent == INTENT_NIGHTLIFE
        assert result.retrieval_used is True
        assert len(result.restaurants) >= 4
        assert all(r.name != "The Violet Hour" for r in result.restaurants)
        assert result.restaurants[0].cuisine in {
            "Bar", "Cocktail Bar", "Rooftop Bar", "Speakeasy", "Wine Bar", "Brewery"
        }
        assert all("verify hours and current status before booking" in (r.summary or "").lower() for r in result.restaurants)
        assert result.source_status == SOURCE_SAMPLE_DATA
        assert result.restaurants[0].summary

    def test_search_does_not_crash_when_messages_table_missing(self):
        db = _make_mock_db("Chicago")
        messages_query = MagicMock()
        missing_table_error = Exception(
            "PGRST205: Could not find the table 'public.concierge_messages' in the schema cache"
        )
        missing_table_error.code = "PGRST205"
        messages_query.select.return_value.eq.return_value.limit.return_value.execute.side_effect = missing_table_error

        def table_side_effect(name):
            if name == "concierge_messages":
                return messages_query
            return db.table.return_value

        db.table.side_effect = table_side_effect
        svc = ConciergeService(db)
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            mock_svc = self._mock_search_svc()
            mock_svc.search_restaurants.return_value = [
                SimpleNamespace(name="Test Bar", cuisine="Bar", location="Loop", rating=4.3, ai_score=80.0, tags=[])
            ]
            MockSearch.return_value = mock_svc
            result = svc.search(FAKE_TRIP_ID, "Add nearby drinks", FAKE_USER_ID)
        assert result.intent == INTENT_NIGHTLIFE
        assert result.restaurants

    def test_search_continues_when_message_persistence_insert_fails(self):
        db = _make_mock_db("Chicago")
        messages_query = MagicMock()
        messages_query.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        messages_query.insert.return_value.execute.side_effect = Exception("network hiccup")

        def table_side_effect(name):
            if name == "concierge_messages":
                return messages_query
            return db.table.return_value

        db.table.side_effect = table_side_effect
        svc = ConciergeService(db)
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            MockSearch.return_value = self._mock_search_svc()
            result = svc.search(FAKE_TRIP_ID, "Nearby cocktail bars", FAKE_USER_ID)
        assert result.intent == INTENT_NIGHTLIFE
        assert result.retrieval_used is True

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
        if expected_intent == INTENT_COMPARE:
            assert result.restaurants == []
            assert result.attractions == []
            assert len(result.area_comparisons) >= 2

    def test_compare_specific_neighborhoods_returns_comparison_data(self):
        svc = self._svc("Chicago")
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            MockSearch.return_value = self._mock_search_svc()
            result = svc.search(FAKE_TRIP_ID, "Compare River North vs West Loop", FAKE_USER_ID)
        assert result.intent == INTENT_COMPARE
        assert result.restaurants == []
        assert result.attractions == []
        names = [item.area for item in result.area_comparisons]
        assert names == ["River North", "West Loop"]

    def test_nightlife_non_supported_city_returns_clear_note_not_restaurants(self):
        svc = self._svc("Paris")
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            MockSearch.return_value = self._mock_search_svc()
            result = svc.search(FAKE_TRIP_ID, "Nearby cocktail bars", FAKE_USER_ID)
        assert result.intent == INTENT_NIGHTLIFE
        assert result.restaurants == []
        assert result.source_status == SOURCE_UNAVAILABLE
        assert result.warnings


class _FakeMessagesQuery:
    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def execute(self):
        exc = Exception(
            "Could not find the table 'public.concierge_messages' in the schema cache"
        )
        exc.code = "PGRST205"
        raise exc


class _FakeTripsQuery:
    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(
            data=[
                {
                    "id": str(FAKE_TRIP_ID),
                    "destination": "Paris",
                    "start_date": "2026-06-01",
                    "end_date": "2026-06-07",
                    "title": "Test Trip",
                    "user_id": str(FAKE_USER_ID),
                }
            ]
        )


class _FakeDBForMissingMessages:
    def table(self, name: str):
        if name == "trips":
            return _FakeTripsQuery()
        if name == "concierge_messages":
            return _FakeMessagesQuery()
        raise AssertionError(f"Unexpected table requested: {name}")


def test_list_messages_returns_empty_when_messages_table_missing():
    svc = ConciergeService(_FakeDBForMissingMessages())
    rows = svc.list_messages(FAKE_TRIP_ID, FAKE_USER_ID)
    assert rows == []


class _SaveMessageQuery:
    def __init__(self, db):
        self.db = db
        self._mode = None
        self._eq_value = None
        self._payload = None

    def select(self, *_args, **_kwargs):
        self._mode = "select"
        return self

    def eq(self, _field, value):
        self._eq_value = value
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def insert(self, payload):
        self._mode = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._mode = "update"
        self._payload = payload
        return self

    def upsert(self, *_args, **_kwargs):
        raise AssertionError("_save_message should not call upsert")

    def execute(self):
        if self._mode == "select":
            if self._eq_value in self.db.messages_by_client_id:
                row = self.db.messages_by_client_id[self._eq_value]
                return SimpleNamespace(data=[{"id": row["id"]}])
            return SimpleNamespace(data=[])
        if self._mode == "insert":
            client_id = self._payload.get("client_message_id")
            if client_id and client_id in self.db.messages_by_client_id:
                exc = Exception("duplicate key value violates unique constraint")
                exc.code = "23505"
                raise exc
            row_id = f"row-{len(self.db.messages_by_client_id) + 1}"
            if client_id:
                self.db.messages_by_client_id[client_id] = {"id": row_id, **self._payload}
            self.db.insert_calls += 1
            return SimpleNamespace(data=[{"id": row_id}])
        if self._mode == "update":
            self.db.update_calls += 1
            return SimpleNamespace(data=[])
        raise AssertionError(f"Unsupported mode {self._mode}")


class _SaveMessageDB:
    def __init__(self):
        self.messages_by_client_id = {}
        self.insert_calls = 0
        self.update_calls = 0

    def table(self, name: str):
        if name != "concierge_messages":
            raise AssertionError(f"Unexpected table requested: {name}")
        return _SaveMessageQuery(self)


def test_save_message_dedupes_without_upsert():
    svc = object.__new__(ConciergeService)
    svc._db = _SaveMessageDB()
    svc._settings = None

    svc._save_message(FAKE_TRIP_ID, "user", "hello", client_message_id="abc")
    svc._save_message(FAKE_TRIP_ID, "user", "hello again", client_message_id="abc")

    assert svc._db.insert_calls == 1
    assert svc._db.update_calls == 1


def test_save_message_duplicate_race_is_ignored():
    svc = object.__new__(ConciergeService)
    db = _SaveMessageDB()
    svc._db = db
    svc._settings = None

    db.messages_by_client_id["abc"] = {"id": "existing-row", "client_message_id": "abc"}
    svc._save_message(FAKE_TRIP_ID, "user", "hello", client_message_id="abc")
    assert db.update_calls == 1


class _ClearCacheMessagesQuery:
    def __init__(self, db):
        self.db = db
        self._trip_id = None

    def delete(self):
        return self

    def eq(self, field, value):
        assert field == "trip_id"
        self._trip_id = value
        return self

    def execute(self):
        self.db.deleted_trip_ids.append(self._trip_id)
        return SimpleNamespace(data=[])


class _ClearCacheDB:
    def __init__(self):
        self.deleted_trip_ids = []

    def table(self, name: str):
        if name != "concierge_messages":
            raise AssertionError(f"Unexpected table requested: {name}")
        return _ClearCacheMessagesQuery(self)


class _StubLiveResearch:
    def __init__(self):
        self.calls = []

    def clear_cache_for_context(self, destination: str, dates: str):
        self.calls.append((destination, dates))
        return 3


def test_clear_cache_removes_persisted_messages_and_invalidates_live_cache():
    svc = object.__new__(ConciergeService)
    svc._db = _ClearCacheDB()
    svc._settings = None
    live = _StubLiveResearch()
    svc._get_live_research = lambda: live
    svc._fetch_trip = lambda _trip_id, _user_id: {
        "destination": "Chicago",
        "start_date": "2026-06-01",
        "end_date": "2026-06-04",
    }

    svc.clear_cache(FAKE_TRIP_ID, FAKE_USER_ID)

    assert svc._db.deleted_trip_ids == [str(FAKE_TRIP_ID)]
    assert live.calls == [("Chicago", "2026-06-01|2026-06-04")]
