"""Vertical-search architecture — Explore is not backed by the AI Concierge.

Durable replacement for the PR #368 ``allow_live_research`` flag tests.  The
flag was a patch around wrong routing; the durable fix is canonical vertical
search endpoints (``/search/hotels``, ``/search/attractions``) shared by
Explore and trip creation.  This file proves:

- ``ConciergeSearchRequest`` no longer carries an ``allow_live_research`` flag.
- ``ConciergeService.search`` / ``_fetch_live_research`` no longer accept an
  ``allow_live_research`` parameter.
- The AI Concierge live-research path still reaches the provider (Tavily) when
  a live-capable provider is configured — explicit AI Concierge / deep-research
  behaviour is unchanged and not gated by any per-request boolean.
- The canonical ``/search/attractions`` route and
  ``SearchService.search_attraction_results`` exist and are Google-Places
  backed (fail-closed, no Concierge, no live research).
"""

from __future__ import annotations

import inspect
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch
from uuid import UUID

from app.models.concierge import ConciergeSearchRequest
from app.services.concierge import ConciergeService
from app.services.live_research import LiveResearchResult

FAKE_USER_ID = UUID("00000000-0000-0000-0000-000000000099")


def _make_service():
    svc = object.__new__(ConciergeService)
    svc._db = MagicMock()
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
# allow_live_research flag is fully removed
# ---------------------------------------------------------------------------

class TestAllowLiveResearchFlagRemoved:
    def test_request_model_has_no_allow_live_research_field(self):
        assert "allow_live_research" not in ConciergeSearchRequest.model_fields
        req = ConciergeSearchRequest(destination="Boise", user_query="hotels in boise")
        assert not hasattr(req, "allow_live_research")

    def test_search_signature_has_no_allow_live_research_param(self):
        params = inspect.signature(ConciergeService.search).parameters
        assert "allow_live_research" not in params

    def test_fetch_live_research_signature_has_no_allow_live_research_param(self):
        params = inspect.signature(ConciergeService._fetch_live_research).parameters
        assert "allow_live_research" not in params


# ---------------------------------------------------------------------------
# AI Concierge live research still reaches the provider when configured
# ---------------------------------------------------------------------------

class TestConciergeLiveResearchStillReachesProvider:
    def test_enabled_provider_path_is_reached(self):
        """The explicit AI Concierge path still uses live research (Tavily) when
        a live-capable provider is configured — there is no per-request flag
        that can disable it."""
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
            )
        mock_get_provider.assert_called_once()
        fake_provider.fetch.assert_called_once()
        assert result is sentinel


# ---------------------------------------------------------------------------
# Canonical /search/attractions vertical-search service
# ---------------------------------------------------------------------------

class TestCanonicalAttractionsSearch:
    def test_search_attraction_results_exists(self):
        from app.services.search import SearchService
        assert hasattr(SearchService, "search_attraction_results")

    def test_search_attraction_results_fails_closed_without_api_key(self):
        """Canonical attractions search is Google Places only — it must fail
        closed (empty list) when no API key is configured and never fall back
        to the Concierge / live research / Tavily path."""
        from app.models.search import AttractionSearchRequest
        from app.services.search import SearchService

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GOOGLE_PLACES_API_KEY", None)
            svc = SearchService(db=MagicMock())
            out = svc.search_attraction_results(
                AttractionSearchRequest(location="Boise")
            )
        assert out == []

    def test_search_attractions_route_is_mounted(self):
        """The canonical /search/attractions route exists in the route source."""
        import pathlib

        repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
        src = (repo_root / "backend" / "app" / "routes" / "search.py").read_text(encoding="utf-8")
        assert '@router.post("/attractions"' in src
