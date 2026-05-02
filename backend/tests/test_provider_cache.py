"""Tests for Provider Result Cache v1.

Coverage:
- ProviderResultCache fresh/stale/expired TTL tiers
- Quality gate rules: empty, error status, insufficient candidates, intent-aware
- Same normalized key → cache hit
- Stale reuse with quality gate pass/fail
- Provider errors are not cached
- Backward-compat with _TTLCache(0) injected in existing tests
- LiveResearchService integration: cache hit/stale/miss/weak_bypass log paths
- Existing endpoint behavior is backward-compatible (no regressions)
"""

import os
import sys
import time
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.services.provider_cache import (
    FRESH_SECONDS,
    STALE_SECONDS,
    ProviderResultCache,
    is_live_research_payload_quality_sufficient,
    reset_provider_cache,
)
from app.services.live_research import (
    LiveResearchResult,
    LiveResearchService,
    LiveSearchHit,
    StubLiveSearchProvider,
    _TTLCache,
    _make_cache_key,
    reset_global_cache,
)
from app.models.concierge import (
    INTENT_ATTRACTIONS,
    INTENT_HOTELS,
    INTENT_NIGHTLIFE,
    INTENT_PLAN_DAY,
    INTENT_RESTAURANTS,
    SOURCE_LIVE_SEARCH,
    SOURCE_NONE,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_payload(
    *,
    restaurants: int = 1,
    attractions: int = 0,
    hotels: int = 0,
    research_sources: int = 0,
    source_status: str = SOURCE_LIVE_SEARCH,
    cache_version: int = 7,
) -> Dict[str, Any]:
    return {
        "cache_version": cache_version,
        "restaurants": [{"id": str(i)} for i in range(restaurants)],
        "attractions": [{"id": str(i)} for i in range(attractions)],
        "hotels": [{"id": str(i)} for i in range(hotels)],
        "research_sources": [{"id": str(i)} for i in range(research_sources)],
        "source_status": source_status,
        "provider_name": "tavily",
        "source_url": None,
    }


# ---------------------------------------------------------------------------
# ProviderResultCache — TTL tiers
# ---------------------------------------------------------------------------

class TestProviderResultCacheTTL:
    def test_fresh_entry_returns_fresh_status(self):
        cache = ProviderResultCache(fresh_seconds=3600, stale_seconds=7200)
        payload = _make_payload()
        cache.set("k1", payload)
        result = cache.get_with_status("k1")
        assert result is not None
        status, got = result
        assert status == "fresh"
        assert got == payload

    def test_expired_entry_evicted_returns_none(self):
        cache = ProviderResultCache(fresh_seconds=0, stale_seconds=0)
        cache.set("k1", _make_payload())
        # With both tiers = 0, anything > 0s old is expired
        time.sleep(0.01)
        result = cache.get_with_status("k1")
        assert result is None

    def test_stale_entry_returns_stale_status(self):
        cache = ProviderResultCache(fresh_seconds=0, stale_seconds=3600)
        payload = _make_payload()
        cache.set("k1", payload)
        # age > fresh (0s) but <= stale (3600s) → stale
        time.sleep(0.01)
        result = cache.get_with_status("k1")
        assert result is not None
        status, got = result
        assert status == "stale"

    def test_get_returns_fresh_only(self):
        """get() (compat method) only returns FRESH entries, not stale."""
        cache = ProviderResultCache(fresh_seconds=0, stale_seconds=3600)
        cache.set("k1", _make_payload())
        time.sleep(0.01)
        # stale → get() returns None
        assert cache.get("k1") is None

    def test_get_returns_fresh_entry(self):
        cache = ProviderResultCache(fresh_seconds=3600, stale_seconds=7200)
        payload = _make_payload()
        cache.set("k1", payload)
        assert cache.get("k1") == payload

    def test_clear_empties_store(self):
        cache = ProviderResultCache()
        cache.set("k1", _make_payload())
        cache.set("k2", _make_payload())
        cache.clear()
        assert cache.size() == 0

    def test_clear_matching_removes_only_matching_keys(self):
        cache = ProviderResultCache()
        cache.set("dest_chicago::restaurants", _make_payload())
        cache.set("dest_paris::restaurants", _make_payload())
        cache.set("dest_chicago::attractions", _make_payload())
        removed = cache.clear_matching(lambda k: "chicago" in k)
        assert removed == 2
        assert cache.size() == 1

    def test_same_key_returns_same_payload(self):
        """Same normalized cache key must return the same payload (cache hit)."""
        cache = ProviderResultCache(fresh_seconds=3600, stale_seconds=7200)
        payload = _make_payload(restaurants=3)
        cache.set("normalized_key", payload)
        result = cache.get_with_status("normalized_key")
        assert result is not None
        assert result[1]["restaurants"] == payload["restaurants"]

    def test_different_keys_stored_independently(self):
        cache = ProviderResultCache(fresh_seconds=3600, stale_seconds=7200)
        p1 = _make_payload(restaurants=1)
        p2 = _make_payload(restaurants=5)
        cache.set("key_a", p1)
        cache.set("key_b", p2)
        assert cache.get("key_a")["restaurants"] != cache.get("key_b")["restaurants"]

    def test_missing_key_returns_none(self):
        cache = ProviderResultCache()
        assert cache.get_with_status("nonexistent") is None
        assert cache.get("nonexistent") is None


# ---------------------------------------------------------------------------
# Quality gate — is_live_research_payload_quality_sufficient
# ---------------------------------------------------------------------------

class TestQualityGate:
    def test_none_payload_fails(self):
        assert not is_live_research_payload_quality_sufficient(None)

    def test_empty_dict_fails(self):
        assert not is_live_research_payload_quality_sufficient({})

    def test_wrong_cache_version_fails(self):
        payload = _make_payload(cache_version=5)
        assert not is_live_research_payload_quality_sufficient(payload, cache_version=7)

    def test_matching_cache_version_passes(self):
        payload = _make_payload(cache_version=7)
        assert is_live_research_payload_quality_sufficient(payload, cache_version=7)

    def test_error_source_status_fails(self):
        payload = _make_payload(source_status="error")
        assert not is_live_research_payload_quality_sufficient(payload)

    def test_error_source_status_with_research_sources_still_fails(self):
        # source_status=error overrides non-empty research_sources — never cache errors
        payload = _make_payload(source_status="error", restaurants=0, research_sources=3)
        assert not is_live_research_payload_quality_sufficient(payload, intent=INTENT_NIGHTLIFE)

    def test_unavailable_source_status_fails(self):
        payload = _make_payload(source_status="unavailable")
        assert not is_live_research_payload_quality_sufficient(payload)

    def test_unavailable_source_status_with_research_sources_still_fails(self):
        # source_status=unavailable overrides non-empty research_sources
        payload = _make_payload(source_status="unavailable", restaurants=0, research_sources=2)
        assert not is_live_research_payload_quality_sufficient(payload, intent=INTENT_RESTAURANTS)

    def test_empty_source_status_fails(self):
        payload = _make_payload(source_status="none")
        assert not is_live_research_payload_quality_sufficient(payload)

    def test_live_search_source_status_passes(self):
        payload = _make_payload(source_status=SOURCE_LIVE_SEARCH)
        assert is_live_research_payload_quality_sufficient(payload)

    def test_restaurant_intent_no_restaurants_no_sources_fails(self):
        # no restaurants, no research_sources → fail for restaurant intents
        payload = _make_payload(restaurants=0, attractions=2, research_sources=0, source_status=SOURCE_LIVE_SEARCH)
        assert not is_live_research_payload_quality_sufficient(payload, intent=INTENT_RESTAURANTS)

    def test_restaurant_intent_with_restaurants_passes(self):
        payload = _make_payload(restaurants=2, source_status=SOURCE_LIVE_SEARCH)
        assert is_live_research_payload_quality_sufficient(payload, intent=INTENT_RESTAURANTS)

    def test_restaurant_intent_with_only_research_sources_passes(self):
        # research_sources are a valid partial result (articles found, no addable cards)
        payload = _make_payload(restaurants=0, research_sources=2, source_status=SOURCE_LIVE_SEARCH)
        assert is_live_research_payload_quality_sufficient(payload, intent=INTENT_RESTAURANTS)

    def test_nightlife_intent_no_restaurants_no_sources_fails(self):
        payload = _make_payload(restaurants=0, research_sources=0, source_status=SOURCE_LIVE_SEARCH)
        assert not is_live_research_payload_quality_sufficient(payload, intent=INTENT_NIGHTLIFE)

    def test_nightlife_intent_with_research_sources_passes(self):
        # nightlife result with articles but no addable cards is still valid
        payload = _make_payload(restaurants=0, research_sources=1, source_status=SOURCE_LIVE_SEARCH)
        assert is_live_research_payload_quality_sufficient(payload, intent=INTENT_NIGHTLIFE)

    def test_attraction_intent_requires_at_least_one_attraction_or_sources(self):
        # no attractions, no research_sources → fail
        payload = _make_payload(restaurants=3, attractions=0, research_sources=0, source_status=SOURCE_LIVE_SEARCH)
        assert not is_live_research_payload_quality_sufficient(payload, intent=INTENT_ATTRACTIONS)

    def test_attraction_intent_with_attractions_passes(self):
        payload = _make_payload(attractions=2, source_status=SOURCE_LIVE_SEARCH)
        assert is_live_research_payload_quality_sufficient(payload, intent=INTENT_ATTRACTIONS)

    def test_plan_day_intent_requires_attractions_or_sources(self):
        payload = _make_payload(restaurants=2, attractions=0, research_sources=0, source_status=SOURCE_LIVE_SEARCH)
        assert not is_live_research_payload_quality_sufficient(payload, intent=INTENT_PLAN_DAY)

    def test_hotels_intent_requires_hotels_or_sources(self):
        payload = _make_payload(restaurants=2, hotels=0, research_sources=0, source_status=SOURCE_LIVE_SEARCH)
        assert not is_live_research_payload_quality_sufficient(payload, intent=INTENT_HOTELS)

    def test_hotels_intent_with_hotels_passes(self):
        payload = _make_payload(hotels=1, source_status=SOURCE_LIVE_SEARCH)
        assert is_live_research_payload_quality_sufficient(payload, intent=INTENT_HOTELS)

    def test_general_intent_accepts_any_candidates(self):
        payload = _make_payload(restaurants=0, attractions=0, hotels=1, source_status=SOURCE_LIVE_SEARCH)
        assert is_live_research_payload_quality_sufficient(payload, intent="general")

    def test_general_intent_with_only_research_sources_passes(self):
        payload = _make_payload(restaurants=0, attractions=0, research_sources=2, source_status=SOURCE_LIVE_SEARCH)
        assert is_live_research_payload_quality_sufficient(payload, intent="general")

    def test_all_buckets_empty_fails(self):
        payload = _make_payload(restaurants=0, attractions=0, hotels=0, research_sources=0, source_status=SOURCE_LIVE_SEARCH)
        assert not is_live_research_payload_quality_sufficient(payload, intent="general")

    def test_all_buckets_empty_fails_for_place_intent(self):
        payload = _make_payload(restaurants=0, attractions=0, hotels=0, research_sources=0, source_status=SOURCE_LIVE_SEARCH)
        assert not is_live_research_payload_quality_sufficient(payload, intent=INTENT_RESTAURANTS)


# ---------------------------------------------------------------------------
# _TTLCache backward-compat shim
# ---------------------------------------------------------------------------

class TestTTLCacheShim:
    def test_ttl_cache_zero_get_with_status_returns_none(self):
        """_TTLCache(0) is effectively disabled — get_with_status returns None."""
        cache = _TTLCache(0)
        cache.set("k", {"data": 1})
        # TTL=0 means set is a no-op and get returns None
        assert cache.get_with_status("k") is None

    def test_ttl_cache_nonzero_get_with_status_returns_fresh(self):
        """_TTLCache with live TTL returns ("fresh", payload) via shim."""
        cache = _TTLCache(3600)
        payload = {"data": "ok"}
        cache.set("k", payload)
        result = cache.get_with_status("k")
        assert result is not None
        status, got = result
        assert status == "fresh"
        assert got == payload


# ---------------------------------------------------------------------------
# LiveResearchService integration — soft-TTL paths
# ---------------------------------------------------------------------------

class TestLiveResearchServiceCachePaths:
    """Integration tests that verify the soft-TTL logic in LiveResearchService.fetch()."""

    def _make_stub_provider(self, hits=None):
        if hits is None:
            hits = [
                LiveSearchHit(
                    title="Top restaurants in Chicago",
                    snippet="1. Alinea 2. Smyth",
                    url="http://example.com/chicago-restaurants",
                )
            ]
        return StubLiveSearchProvider(hits=hits)

    def test_same_normalized_query_reuses_cache(self):
        """Same destination + intent → second call returns cached result."""
        reset_global_cache()
        provider = self._make_stub_provider()
        cache = ProviderResultCache(fresh_seconds=3600, stale_seconds=7200)

        svc = LiveResearchService(provider=provider, cache=cache, enabled=True)
        r1 = svc.fetch(intent=INTENT_RESTAURANTS, destination="Chicago", user_query="best restaurants")

        # Manually store a known payload so we can verify it's reused
        from app.services.live_research import CONCIERGE_CACHE_VERSION
        key = _make_cache_key(INTENT_RESTAURANTS, "Chicago", "best restaurants")
        sentinel_payload = {
            "cache_version": CONCIERGE_CACHE_VERSION,
            "restaurants": [{"id": "sentinel", "name": "Sentinel Restaurant"}],
            "attractions": [],
            "hotels": [],
            "research_sources": [],
            "source_status": SOURCE_LIVE_SEARCH,
            "provider_name": "tavily",
            "source_url": None,
        }
        cache.set(key, sentinel_payload)

        r2 = svc.fetch(intent=INTENT_RESTAURANTS, destination="Chicago", user_query="best restaurants")
        assert r2.cached is True

    def test_provider_error_is_not_cached(self):
        """When provider raises an exception, nothing is stored in cache."""
        reset_global_cache()

        broken_provider = MagicMock()
        broken_provider.available = True
        broken_provider.name = "broken"
        broken_provider.search.side_effect = RuntimeError("provider down")

        cache = ProviderResultCache(fresh_seconds=3600, stale_seconds=7200)
        svc = LiveResearchService(provider=broken_provider, cache=cache, enabled=True)
        result = svc.fetch(intent=INTENT_RESTAURANTS, destination="Chicago", user_query="restaurants")

        # Nothing was stored
        assert cache.size() == 0
        # Result is an empty fallback, not an error
        assert isinstance(result, LiveResearchResult)

    def test_empty_provider_hits_not_cached(self):
        """When provider returns no hits, result is not stored in cache."""
        reset_global_cache()
        empty_provider = StubLiveSearchProvider(hits=[])
        cache = ProviderResultCache(fresh_seconds=3600, stale_seconds=7200)
        svc = LiveResearchService(provider=empty_provider, cache=cache, enabled=True)
        svc.fetch(intent=INTENT_RESTAURANTS, destination="Chicago", user_query="restaurants")
        assert cache.size() == 0

    def test_stale_weak_cache_forces_live_provider(self):
        """STALE + quality fail → live provider is called."""
        reset_global_cache()

        from app.services.live_research import CONCIERGE_CACHE_VERSION
        key = _make_cache_key(INTENT_RESTAURANTS, "Chicago", "best restaurants")

        # Build a stale-tier cache with a weak (empty restaurants) payload
        cache = ProviderResultCache(fresh_seconds=0, stale_seconds=3600)
        weak_payload = {
            "cache_version": CONCIERGE_CACHE_VERSION,
            "restaurants": [],           # fails restaurant intent quality gate
            "attractions": [],
            "hotels": [],
            "research_sources": [],
            "source_status": SOURCE_LIVE_SEARCH,
            "provider_name": "tavily",
            "source_url": None,
        }
        cache.set(key, weak_payload)
        time.sleep(0.01)  # push into stale tier

        live_called = []
        provider = MagicMock()
        provider.available = True
        provider.name = "tavily"
        provider.search.side_effect = lambda q, **kw: live_called.append(q) or []

        svc = LiveResearchService(provider=provider, cache=cache, enabled=True)
        svc.fetch(intent=INTENT_RESTAURANTS, destination="Chicago", user_query="best restaurants")

        assert len(live_called) == 1, "live provider should have been called on weak stale cache"

    def test_stale_good_quality_cache_reused_without_live_call(self):
        """STALE + quality ok → cached result is returned, live provider NOT called."""
        reset_global_cache()

        from app.services.live_research import CONCIERGE_CACHE_VERSION, _make_cache_key
        key = _make_cache_key(INTENT_RESTAURANTS, "Chicago", "best restaurants")

        cache = ProviderResultCache(fresh_seconds=0, stale_seconds=3600)
        good_payload = {
            "cache_version": CONCIERGE_CACHE_VERSION,
            "restaurants": [{"id": "r1", "name": "Good Place"}],
            "attractions": [],
            "hotels": [],
            "research_sources": [],
            "source_status": SOURCE_LIVE_SEARCH,
            "provider_name": "tavily",
            "source_url": None,
        }
        cache.set(key, good_payload)
        time.sleep(0.01)  # push into stale tier

        provider = MagicMock()
        provider.available = True
        provider.name = "tavily"
        provider.search.return_value = []  # should never be called

        svc = LiveResearchService(provider=provider, cache=cache, enabled=True)
        result = svc.fetch(intent=INTENT_RESTAURANTS, destination="Chicago", user_query="best restaurants")

        provider.search.assert_not_called()
        assert result.cached is True

    def test_expired_cache_forces_live_provider(self):
        """EXPIRED entry (age > stale) → live provider is called."""
        reset_global_cache()
        from app.services.live_research import CONCIERGE_CACHE_VERSION
        key = _make_cache_key(INTENT_RESTAURANTS, "Chicago", "best restaurants")

        # Use zero TTL so everything is immediately expired
        cache = ProviderResultCache(fresh_seconds=0, stale_seconds=0)
        cache.set(key, _make_payload(restaurants=2, source_status=SOURCE_LIVE_SEARCH, cache_version=CONCIERGE_CACHE_VERSION))
        time.sleep(0.01)

        live_called = []
        provider = MagicMock()
        provider.available = True
        provider.name = "tavily"
        provider.search.side_effect = lambda q, **kw: live_called.append(q) or []

        svc = LiveResearchService(provider=provider, cache=cache, enabled=True)
        svc.fetch(intent=INTENT_RESTAURANTS, destination="Chicago", user_query="best restaurants")

        assert len(live_called) == 1

    def test_cache_exception_does_not_fail_request(self):
        """If cache.get_with_status raises, the live provider is called and request succeeds."""
        reset_global_cache()

        broken_cache = MagicMock()
        broken_cache.get_with_status.side_effect = RuntimeError("cache exploded")
        broken_cache.set.return_value = None

        provider = StubLiveSearchProvider(hits=[])
        svc = LiveResearchService(provider=provider, cache=broken_cache, enabled=True)
        # Should not raise — falls through to live path
        try:
            result = svc.fetch(intent=INTENT_RESTAURANTS, destination="Chicago", user_query="restaurants")
        except RuntimeError:
            pytest.fail("cache exception should not propagate to caller")

    def test_ttl_cache_zero_injected_still_works(self):
        """_TTLCache(0) injected (existing test pattern) disables caching — no regression."""
        reset_global_cache()
        provider = StubLiveSearchProvider(hits=[])
        cache = _TTLCache(0)
        svc = LiveResearchService(provider=provider, cache=cache, enabled=True)
        result = svc.fetch(intent=INTENT_RESTAURANTS, destination="Chicago", user_query="restaurants")
        assert isinstance(result, LiveResearchResult)

    def test_normalized_equivalent_queries_hit_same_key(self):
        """Queries that differ only in whitespace/case produce the same cache key."""
        k1 = _make_cache_key(INTENT_RESTAURANTS, "chicago", "best restaurants in chicago")
        k2 = _make_cache_key(INTENT_RESTAURANTS, "Chicago", "best  restaurants in chicago")
        k3 = _make_cache_key(INTENT_RESTAURANTS, "CHICAGO", "Best Restaurants in Chicago")
        assert k1 == k2 == k3

    def test_different_intents_produce_different_keys(self):
        k_rest = _make_cache_key(INTENT_RESTAURANTS, "Chicago", "good spots")
        k_attr = _make_cache_key(INTENT_ATTRACTIONS, "Chicago", "good spots")
        assert k_rest != k_attr

    def test_different_destinations_produce_different_keys(self):
        k1 = _make_cache_key(INTENT_RESTAURANTS, "Chicago", "restaurants")
        k2 = _make_cache_key(INTENT_RESTAURANTS, "Paris", "restaurants")
        assert k1 != k2


# ---------------------------------------------------------------------------
# reset_provider_cache test helper
# ---------------------------------------------------------------------------

class TestResetHelper:
    def test_reset_provider_cache_clears_singleton(self):
        from app.services.provider_cache import get_provider_cache
        pc = get_provider_cache()
        pc.set("x", _make_payload())
        assert pc.size() >= 1
        reset_provider_cache()
        assert pc.size() == 0
