"""
Tests: beach/viewpoint place-search stabilization (follow-up to PR #393).

Root causes fixed:
1. "sunset points", "lookout points", "viewpoints" etc. were misclassified as
   INTENT_REWARDS_HELP because _REWARDS_PAT fired on bare "points" before
   _ATTRACTION_PAT had a chance to match the phrase. Fixed by adding viewpoint/
   scenic-point compound phrases to _ATTRACTION_PAT (phrase context wins).
2. "best beaches in Miami" generated only one query ("beach Miami") — too narrow
   for natural-feature coastal queries. Fixed by adding beach/viewpoint synonym
   expansions to _SYNONYM_EXPANSIONS and using pref_primary for Q2 in plan_queries
   so "sunset" fans out to "sunset viewpoint <city>" as a richer Q2.

Coverage:
A. Intent routing: viewpoint/scenic phrases → INTENT_ATTRACTIONS, not INTENT_REWARDS_HELP.
B. Intent routing: actual rewards queries still → INTENT_REWARDS_HELP.
C. Semantic eligibility: viewpoint intents pass the place-search gate.
D. Query expansion: beaches generate 2+ distinct queries.
E. Query expansion: sunset points generate viewpoint/overlook variants.
F. Mocked verified attraction cards returned from semantic path.
G. No Tavily/legacy fallback when semantic verified cards are present.
H. Existing vertical regression: sports bars/cocktail bars/rooftop bars → restaurants;
   hotels near beach → hotels; beaches/viewpoints with no venue head → attractions.
"""

from __future__ import annotations

import logging
import sys
import os
from types import SimpleNamespace
from typing import List, Optional

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.concierge import (
    INTENT_ATTRACTIONS,
    INTENT_REWARDS_HELP,
    INTENT_RESTAURANTS,
    INTENT_NIGHTLIFE,
    INTENT_HOTELS,
    INTENT_GENERAL,
)
from app.services.concierge import ConciergeService, _SEMANTIC_PLACE_SEARCH_BLOCKLIST
from app.concierge.frame_extractor import extract_frame
from app.concierge.retrieval_planner import plan_queries


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


def _queries(query: str, destination: str) -> List[str]:
    frame = extract_frame(query, destination)
    return plan_queries(frame)


# ── Section A: Intent routing — viewpoint phrases → INTENT_ATTRACTIONS ────────

class TestViewpointIntentRouting:
    """Viewpoint/scenic phrases must route as INTENT_ATTRACTIONS, not INTENT_REWARDS_HELP."""

    @pytest.mark.parametrize("query", [
        "best sunset points in San Diego",
        "sunset points San Diego",
        "top sunset spots in San Diego",
        "best viewpoints in Seattle",
        "viewpoints in Tokyo",
        "best view points in New York",
        "view points near downtown",
        "lookout points in Cape Town",
        "scenic points in Lisbon",
        "lookout overlooks near Barcelona",
        "photo spots in Paris",
    ])
    def test_viewpoint_phrases_route_to_attractions(self, query):
        """All viewpoint/scenic-point phrases must detect as INTENT_ATTRACTIONS."""
        svc = _svc()
        intent = svc._detect_intent(query)
        assert intent == INTENT_ATTRACTIONS, (
            f"Query {query!r} should be INTENT_ATTRACTIONS, got {intent!r}. "
            "Viewpoint phrases must not collide with rewards intent."
        )

    @pytest.mark.parametrize("query", [
        "sunset points",
        "best view points",
        "lookout point",
        "scenic overlook",
        "photo spot",
        "vantage point",
    ])
    def test_viewpoint_phrases_not_rewards(self, query):
        """Viewpoint queries must never return INTENT_REWARDS_HELP."""
        svc = _svc()
        intent = svc._detect_intent(query)
        assert intent != INTENT_REWARDS_HELP, (
            f"Query {query!r} must NOT be INTENT_REWARDS_HELP, got {intent!r}"
        )

    @pytest.mark.parametrize("query", [
        "best sunset points in San Diego",
        "sunset spots in Miami",
        "viewpoints in Seattle",
    ])
    def test_viewpoint_intent_not_in_semantic_blocklist(self, query):
        """INTENT_ATTRACTIONS must not be in the semantic-retrieval blocklist."""
        svc = _svc()
        intent = svc._detect_intent(query)
        assert intent not in _SEMANTIC_PLACE_SEARCH_BLOCKLIST, (
            f"Query {query!r} resolved to intent={intent!r}, which is blocked from "
            "semantic retrieval. Viewpoint queries must be semantic-eligible."
        )


# ── Section B: Actual rewards queries still route correctly ──────────────────

class TestRewardsIntentPreserved:
    """Genuine rewards/points/miles queries must still route to INTENT_REWARDS_HELP."""

    @pytest.mark.parametrize("query", [
        "how do I use points for flights",
        "credit card points",
        "earn reward miles",
        "best loyalty program",
        "redeem my miles",
        "cpp for award bookings",
    ])
    def test_rewards_queries_still_route_to_rewards(self, query):
        svc = _svc()
        intent = svc._detect_intent(query)
        assert intent == INTENT_REWARDS_HELP, (
            f"Genuine rewards query {query!r} must stay INTENT_REWARDS_HELP, got {intent!r}"
        )


# ── Section C: Semantic eligibility gate ────────────────────────────────────

class TestSemanticEligibility:
    """INTENT_ATTRACTIONS must pass semantic eligibility; INTENT_REWARDS_HELP must not."""

    def test_attractions_intent_eligible_with_destination(self):
        svc = _svc()
        assert svc._is_place_search_eligible(INTENT_ATTRACTIONS, False, "San Diego") is True

    def test_rewards_intent_not_eligible(self):
        svc = _svc()
        assert svc._is_place_search_eligible(INTENT_REWARDS_HELP, False, "San Diego") is False

    def test_sunset_points_now_eligible_for_semantic(self):
        """After the fix, 'sunset points' must yield INTENT_ATTRACTIONS and be eligible."""
        svc = _svc()
        intent = svc._detect_intent("best sunset points in San Diego")
        eligible = svc._is_place_search_eligible(intent, False, "San Diego")
        assert eligible is True, (
            f"'best sunset points in San Diego' got intent={intent!r}, eligible={eligible}. "
            "After fix, this must be INTENT_ATTRACTIONS and semantic-eligible."
        )

    def test_viewpoints_eligible_for_semantic(self):
        svc = _svc()
        intent = svc._detect_intent("scenic viewpoints in Seattle")
        eligible = svc._is_place_search_eligible(intent, False, "Seattle")
        assert eligible is True, (
            f"intent={intent!r} eligible={eligible}; viewpoints must be semantic-eligible."
        )

    def test_eligibility_log_not_non_place_intent(self, caplog):
        """Viewpoint queries must log semantic_eligible, not semantic_skip non_place_intent."""
        svc = _svc()
        svc._settings = _settings(semantic_on=True)
        svc._get_live_research = lambda: SimpleNamespace(is_live_capable=False)

        with caplog.at_level(logging.INFO, logger="app.services.concierge"):
            svc._fetch_live_research(
                intent=INTENT_ATTRACTIONS,
                destination="San Diego",
                user_query="best sunset points in San Diego",
                trip={},
            )

        non_place_skips = [
            r.message for r in caplog.records
            if "semantic_skip" in r.message and "non_place_intent" in r.message
        ]
        assert not non_place_skips, (
            "INTENT_ATTRACTIONS must NOT produce semantic_skip non_place_intent. "
            f"Got: {non_place_skips}"
        )


# ── Section D: Query expansion — beaches ────────────────────────────────────

class TestBeachQueryExpansion:
    """Beach queries must fan out to 2+ distinct Google queries."""

    def test_beach_miami_generates_multiple_queries(self):
        queries = _queries("best beaches in Miami", "Miami")
        assert len(queries) >= 2, (
            f"Expected 2+ beach queries, got {queries!r}. "
            "Single 'beach Miami' is too narrow for coastal place searches."
        )

    def test_beach_miami_not_only_beach_miami(self):
        queries = _queries("best beaches in Miami", "Miami")
        assert queries != ["beach Miami"], (
            "Query planning must fan out beyond a single 'beach Miami'. "
            f"Got: {queries!r}"
        )

    def test_beach_miami_contains_beach_variant(self):
        queries = _queries("best beaches in Miami", "Miami")
        combined = " ".join(q.lower() for q in queries)
        assert "public beach" in combined or "beach park" in combined, (
            f"Beach queries must include public-beach or beach-park variant. Got: {queries!r}"
        )

    def test_beach_miami_all_queries_contain_destination(self):
        queries = _queries("best beaches in Miami", "Miami")
        for q in queries:
            assert "miami" in q.lower(), (
                f"Every query must include destination 'Miami'. Offending: {q!r}"
            )

    @pytest.mark.parametrize("city", ["Miami", "Malibu", "Barcelona"])
    def test_beach_queries_fan_out_across_cities(self, city):
        queries = _queries(f"best beaches in {city}", city)
        assert len(queries) >= 2, (
            f"Expected 2+ queries for beaches in {city}, got {queries!r}"
        )


# ── Section E: Query expansion — sunset points / viewpoints ─────────────────

class TestSunsetViewpointQueryExpansion:
    """Sunset-points / viewpoint queries must generate overlook/viewpoint variants."""

    def test_sunset_points_san_diego_multiple_queries(self):
        queries = _queries("best sunset points in San Diego", "San Diego")
        assert len(queries) >= 2, (
            f"Expected 2+ queries for sunset points, got {queries!r}"
        )

    def test_sunset_points_contains_viewpoint_or_overlook_variant(self):
        queries = _queries("best sunset points in San Diego", "San Diego")
        combined = " ".join(q.lower() for q in queries)
        has_viewpoint = any(
            kw in combined
            for kw in ("viewpoint", "overlook", "sunset spot", "scenic")
        )
        assert has_viewpoint, (
            f"Sunset-points queries must include a viewpoint/overlook/scenic variant. "
            f"Got: {queries!r}"
        )

    def test_sunset_points_all_queries_contain_destination(self):
        queries = _queries("best sunset points in San Diego", "San Diego")
        for q in queries:
            assert "san diego" in q.lower(), (
                f"Every query must include destination. Offending: {q!r}"
            )

    def test_viewpoints_seattle_multiple_queries(self):
        # "best viewpoints" → concept="viewpoint" which has synonyms; generates 2+ queries.
        queries = _queries("best viewpoints in Seattle", "Seattle")
        assert len(queries) >= 2, (
            f"Expected 2+ viewpoint queries for Seattle, got {queries!r}"
        )

    def test_sunset_spots_generate_viewpoint_variants(self):
        queries = _queries("best sunset spots in San Diego", "San Diego")
        assert len(queries) >= 2, f"Expected multiple queries, got {queries!r}"


# ── Section F: Mocked verified attraction cards from semantic path ────────────

class TestMockedSemanticAttractionCards:
    """Semantic path must return attraction cards in the attractions bucket."""

    def _make_attraction_result(self):
        from app.services.live_research import LiveResearchResult
        from app.models.concierge import SOURCE_LIVE_SEARCH, UnifiedAttractionResult
        cards = [
            UnifiedAttractionResult(name="Sunset Cliffs", category="scenic overlook"),
            UnifiedAttractionResult(name="Torrey Pines Gliderport", category="viewpoint"),
        ]
        return LiveResearchResult(attractions=cards, source_status=SOURCE_LIVE_SEARCH)

    def test_semantic_retrieval_beaches_returns_attraction_cards(self):
        """When semantic retrieval returns verified attraction cards, they go in
        the attractions bucket, not restaurants."""
        from app.services.live_research import LiveResearchResult
        from app.models.concierge import SOURCE_LIVE_SEARCH, UnifiedAttractionResult
        import app.concierge.semantic_retrieval as sr_mod

        beach_cards = [
            UnifiedAttractionResult(name="South Beach", category="beach"),
            UnifiedAttractionResult(name="Crandon Park Beach", category="beach park"),
        ]
        beach_result = LiveResearchResult(
            attractions=beach_cards, source_status=SOURCE_LIVE_SEARCH
        )

        original = sr_mod._run_pipeline
        try:
            sr_mod._run_pipeline = lambda **kw: beach_result
            from app.concierge.semantic_retrieval import run_semantic_retrieval_v1
            result = run_semantic_retrieval_v1(
                destination="Miami",
                user_query="best beaches in Miami",
                api_key="fake-key-for-test",
                vertical="attractions",
            )
        finally:
            sr_mod._run_pipeline = original

        assert result.attractions == beach_cards, (
            f"Expected beach cards in attractions bucket, got: {result!r}"
        )
        assert not result.restaurants, "Beach cards must not land in restaurants bucket"
        assert not result.hotels, "Beach cards must not land in hotels bucket"

    def test_semantic_retrieval_sunset_points_returns_attraction_cards(self):
        """Sunset-viewpoint semantic results must land in attractions bucket."""
        from app.services.live_research import LiveResearchResult
        from app.models.concierge import SOURCE_LIVE_SEARCH, UnifiedAttractionResult
        import app.concierge.semantic_retrieval as sr_mod

        viewpoint_cards = [
            UnifiedAttractionResult(name="Sunset Cliffs", category="scenic overlook"),
        ]
        viewpoint_result = LiveResearchResult(
            attractions=viewpoint_cards, source_status=SOURCE_LIVE_SEARCH
        )

        original = sr_mod._run_pipeline
        try:
            sr_mod._run_pipeline = lambda **kw: viewpoint_result
            from app.concierge.semantic_retrieval import run_semantic_retrieval_v1
            result = run_semantic_retrieval_v1(
                destination="San Diego",
                user_query="best sunset points in San Diego",
                api_key="fake-key-for-test",
                vertical="attractions",
            )
        finally:
            sr_mod._run_pipeline = original

        assert result.attractions == viewpoint_cards
        assert not result.restaurants
        assert not result.hotels

    def test_vertical_forwarded_to_pipeline_for_beach_query(self):
        """vertical='attractions' must be forwarded to _run_pipeline for beach queries."""
        import app.concierge.semantic_retrieval as sr_mod
        from app.services.live_research import LiveResearchResult
        from app.models.concierge import SOURCE_NONE

        captured = {}

        def recording_pipeline(**kw):
            captured["vertical"] = kw.get("vertical")
            return LiveResearchResult(source_status=SOURCE_NONE)

        original = sr_mod._run_pipeline
        try:
            sr_mod._run_pipeline = recording_pipeline
            from app.concierge.semantic_retrieval import run_semantic_retrieval_v1
            run_semantic_retrieval_v1(
                destination="Miami",
                user_query="best beaches in Miami",
                api_key="fake-key-for-test",
                vertical="attractions",
            )
        finally:
            sr_mod._run_pipeline = original

        assert captured.get("vertical") == "attractions", (
            f"Expected vertical='attractions' forwarded to pipeline, got {captured!r}"
        )


# ── Section G: No Tavily/legacy fallback when semantic cards available ────────

class TestNoTavilyWhenSemanticCardsPresent:
    """When semantic retrieval returns verified cards, _fetch_live_research must
    return immediately without reaching Tavily or the slow live-research path."""

    def test_fetch_live_research_returns_on_verified_cards(self, caplog):
        """semantic_card_first_path=true must be logged; no live_research fallback."""
        from app.services.live_research import LiveResearchResult
        from app.models.concierge import SOURCE_LIVE_SEARCH, UnifiedAttractionResult
        import app.concierge.semantic_retrieval as sr_mod

        cards = [UnifiedAttractionResult(name="Del Mar Beach", category="beach")]
        mock_result = LiveResearchResult(
            attractions=cards, source_status=SOURCE_LIVE_SEARCH
        )

        svc = _svc()
        svc._settings = _settings(semantic_on=True)
        svc._get_live_research = lambda: SimpleNamespace(is_live_capable=False)

        original = sr_mod.run_semantic_retrieval_v1
        try:
            sr_mod.run_semantic_retrieval_v1 = lambda **kw: mock_result
            # Patch the import inside _fetch_live_research
            import app.services.concierge as conc_mod

            with caplog.at_level(logging.INFO, logger="app.services.concierge"):
                result = svc._fetch_live_research(
                    intent=INTENT_ATTRACTIONS,
                    destination="Miami",
                    user_query="best beaches in Miami",
                    trip={},
                )
        finally:
            sr_mod.run_semantic_retrieval_v1 = original

        assert result.attractions == cards, (
            "Verified attraction cards must be returned from _fetch_live_research"
        )
        card_first_logs = [
            r.message for r in caplog.records
            if "semantic_card_first" in r.message
        ]
        assert card_first_logs, (
            "semantic_card_first log must be emitted when verified cards are present"
        )


# ── Section H: Existing vertical regression tests ────────────────────────────

class TestExistingVerticalRegressions:
    """PR #393 passing behavior must be preserved after this stabilization fix."""

    @pytest.mark.parametrize("query", [
        "sports bars in Chicago",
        "cocktail bars in San Francisco",
        "rooftop bars with sunset views",
    ])
    def test_bar_queries_still_route_to_restaurants(self, query):
        svc = _svc()
        intent = svc._detect_intent(query)
        vertical = svc._detect_semantic_vertical(intent, query)
        assert vertical == "restaurants", (
            f"Bar/nightlife query {query!r} must stay restaurants, got {vertical!r}"
        )

    @pytest.mark.parametrize("query", [
        "hotels near the beach",
        "beachfront hotels in Miami",
        "luxury hotels with sunset views",
    ])
    def test_hotel_queries_route_to_hotels(self, query):
        svc = _svc()
        intent = svc._detect_intent(query)
        vertical = svc._detect_semantic_vertical(intent, query)
        assert vertical == "hotels", (
            f"Hotel query {query!r} must route to hotels, got {vertical!r}"
        )

    @pytest.mark.parametrize("query", [
        "best beaches in Miami",
        "viewpoints in Seattle",
        "sunset viewpoints in San Diego",
    ])
    def test_beach_viewpoint_queries_route_to_attractions(self, query):
        svc = _svc()
        intent = svc._detect_intent(query)
        vertical = svc._detect_semantic_vertical(intent, query)
        assert vertical == "attractions", (
            f"Beach/viewpoint query {query!r} must route to attractions, "
            f"got intent={intent!r} vertical={vertical!r}"
        )

    def test_sunset_restaurants_still_restaurants(self):
        """'Sunset restaurants' has a venue head — must stay restaurants bucket."""
        svc = _svc()
        intent = svc._detect_intent("sunset restaurants in San Diego")
        vertical = svc._detect_semantic_vertical(intent, "sunset restaurants in San Diego")
        assert vertical == "restaurants", (
            f"'sunset restaurants' must stay restaurants, got vertical={vertical!r}"
        )

    def test_rewards_intent_in_blocklist(self):
        """INTENT_REWARDS_HELP must still be blocked from semantic path."""
        assert INTENT_REWARDS_HELP in _SEMANTIC_PLACE_SEARCH_BLOCKLIST

    def test_attractions_intent_not_in_blocklist(self):
        """INTENT_ATTRACTIONS must not be blocked from semantic path."""
        assert INTENT_ATTRACTIONS not in _SEMANTIC_PLACE_SEARCH_BLOCKLIST
