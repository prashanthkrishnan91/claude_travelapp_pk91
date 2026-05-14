"""Stage 3 stabilization — default Explore surfaces must not call paid live research.

Covers Scope C of the Stage 3 stabilization patch (Explore Hotels + Attractions
tripless discovery):
- ConciergeSearchRequest defaults allow_live_research=True and accepts False.
- ConciergeService.search forwards allow_live_research to _fetch_live_research.
- _fetch_live_research short-circuits to an empty LiveResearchResult when
  allow_live_research is False — no provider (Tavily) is ever constructed or
  called, so default Explore Hotels never spends live-research credits.
- allow_live_research=True still reaches the provider path (explicit AI
  Concierge / deep-research behaviour is unchanged).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch
from uuid import UUID

from app.models.concierge import ConciergeSearchRequest
from app.services.concierge import ConciergeService
from app.services.live_research import LiveResearchResult

FAKE_USER_ID = UUID("00000000-0000-0000-0000-000000000099")


class _LiveResult:
    restaurants: list = []
    attractions: list = []
    hotels: list = []
    research_sources: list = []
    provider_name: str = "mock"
    source_status: str = "none"
    cached: bool = False


def _make_service():
    db = MagicMock()
    svc = object.__new__(ConciergeService)
    svc._db = db
    svc._live_research = None
    svc._settings = MagicMock(
        concierge_router_v2=False,
        concierge_context_v1_enabled=False,
        research_engine_require_google_verification=False,
        trip_advice_builder_enabled=False,
        concierge_semantic_retrieval_v1_enabled=False,
        concierge_fast_dynamic_place_search_v1_enabled=False,
    )
    return svc


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class TestConciergeSearchRequestLiveResearchFlag:
    def test_allow_live_research_defaults_true(self):
        req = ConciergeSearchRequest(destination="Boise", user_query="hotels in boise")
        assert req.allow_live_research is True

    def test_allow_live_research_can_be_disabled(self):
        req = ConciergeSearchRequest(
            destination="Boise",
            user_query="hotels in boise",
            allow_live_research=False,
        )
        assert req.allow_live_research is False


# ---------------------------------------------------------------------------
# search() forwards the flag
# ---------------------------------------------------------------------------

class TestSearchForwardsAllowLiveResearch:
    def test_search_forwards_allow_live_research_false(self):
        svc = _make_service()
        captured = {}

        def capture(intent, destination, user_query, trip, **kw):
            captured["allow_live_research"] = kw.get("allow_live_research")
            return _LiveResult()

        with patch.object(svc, "_fetch_trip"), \
             patch.object(svc, "_fetch_live_research", side_effect=capture), \
             patch.object(svc, "_save_message"), \
             patch.object(svc, "_call_claude", return_value='{"response":"ok","suggestions":[]}'), \
             patch.object(svc, "_detect_intent", return_value="restaurants"), \
             patch.object(svc, "_build_search_prompt", return_value="prompt"), \
             patch.object(svc, "_concise_response", return_value="ok"), \
             patch.object(svc, "_align_summary_with_ranked_cards", return_value="ok"), \
             patch.object(svc, "_derive_response_source_status", return_value="none"):
            svc.search(
                trip_id=None,
                user_query="hotels in boise",
                user_id=FAKE_USER_ID,
                destination="Boise",
                allow_live_research=False,
            )
        assert captured.get("allow_live_research") is False

    def test_search_defaults_allow_live_research_true(self):
        svc = _make_service()
        captured = {}

        def capture(intent, destination, user_query, trip, **kw):
            captured["allow_live_research"] = kw.get("allow_live_research")
            return _LiveResult()

        with patch.object(svc, "_fetch_trip"), \
             patch.object(svc, "_fetch_live_research", side_effect=capture), \
             patch.object(svc, "_save_message"), \
             patch.object(svc, "_call_claude", return_value='{"response":"ok","suggestions":[]}'), \
             patch.object(svc, "_detect_intent", return_value="restaurants"), \
             patch.object(svc, "_build_search_prompt", return_value="prompt"), \
             patch.object(svc, "_concise_response", return_value="ok"), \
             patch.object(svc, "_align_summary_with_ranked_cards", return_value="ok"), \
             patch.object(svc, "_derive_response_source_status", return_value="none"):
            svc.search(
                trip_id=None,
                user_query="hotels in boise",
                user_id=FAKE_USER_ID,
                destination="Boise",
            )
        assert captured.get("allow_live_research") is True


# ---------------------------------------------------------------------------
# _fetch_live_research enforcement — the actual no-Tavily gate
# ---------------------------------------------------------------------------

class TestFetchLiveResearchGate:
    def test_disabled_returns_empty_without_constructing_provider(self):
        """allow_live_research=False short-circuits before any provider call."""
        svc = _make_service()
        with patch.object(svc, "_get_live_research") as mock_get_provider:
            result = svc._fetch_live_research(
                intent="hotels",
                destination="Boise",
                user_query="hotels in boise",
                trip={"destination": "Boise"},
                allow_live_research=False,
            )
        # No provider (Tavily or otherwise) is ever constructed.
        mock_get_provider.assert_not_called()
        assert isinstance(result, LiveResearchResult)
        assert result.restaurants == []
        assert result.attractions == []
        assert result.hotels == []

    def test_disabled_blocks_provider_for_any_intent(self):
        """The gate is intent-agnostic — attractions, restaurants, etc. all skip
        live research when allow_live_research=False (default Explore surfaces)."""
        svc = _make_service()
        for intent in ("attractions", "restaurants", "hotels", "hidden_gems"):
            with patch.object(svc, "_get_live_research") as mock_get_provider:
                result = svc._fetch_live_research(
                    intent=intent,
                    destination="Boise",
                    user_query=f"{intent} in boise",
                    trip={"destination": "Boise"},
                    allow_live_research=False,
                )
            mock_get_provider.assert_not_called()
            assert isinstance(result, LiveResearchResult)
            assert result.attractions == []
            assert result.restaurants == []
            assert result.hotels == []

    def test_enabled_still_reaches_provider_path(self):
        """allow_live_research=True (default) still uses live research."""
        svc = _make_service()
        sentinel = LiveResearchResult()
        fake_provider = MagicMock()
        fake_provider.is_live_capable = True
        fake_provider.fetch.return_value = sentinel
        with patch.object(svc, "_get_live_research", return_value=fake_provider) as mock_get_provider:
            result = svc._fetch_live_research(
                intent="hotels",
                destination="Boise",
                user_query="hotels in boise",
                trip={"destination": "Boise"},
                allow_live_research=True,
            )
        mock_get_provider.assert_called_once()
        fake_provider.fetch.assert_called_once()
        assert result is sentinel
