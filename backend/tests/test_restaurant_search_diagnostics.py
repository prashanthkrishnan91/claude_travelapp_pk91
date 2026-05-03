"""Tests for the restaurant search diagnostics path:
- Cache hit raw_count bug fix
- ExploreSnapshotRestaurant identity fields
- Verified identity on miss path
"""
import json
from unittest.mock import MagicMock, patch
from app.models.search import RestaurantSearchRequest, ExploreSnapshotRestaurant
from app.services.search import SearchService, _cache_key


class _EmptyDB:
    """Mock DB that always returns empty cache (simulates cold cache)."""
    def table(self, _):
        class _Q:
            def select(self, *a, **k): return self
            def eq(self, *a, **k): return self
            def gt(self, *a, **k): return self
            def limit(self, *a, **k): return self
            def upsert(self, *a, **k): return self
            def insert(self, *a, **k): return self
            def execute(self):
                class R:
                    data = []
                return R()
        return _Q()


class _CacheHitDB:
    """Mock DB that returns pre-populated cache data on _get_cache."""

    def __init__(self, cached_payload):
        self._cached_payload = cached_payload

    def table(self, _):
        cached = self._cached_payload

        class _Q:
            def select(self, *a, **k): return self
            def eq(self, *a, **k): return self
            def gt(self, *a, **k): return self
            def limit(self, *a, **k): return self
            def upsert(self, *a, **k): return self
            def insert(self, *a, **k): return self
            def execute(self_inner):
                class R:
                    data = [{"payload": {"results": cached}, "expires_at": None}]
                return R()
        return _Q()


def test_search_restaurants_miss_exposes_status_and_verified_identity_fields():
    """Cold cache (miss) path must return verified restaurants with identity fields."""
    svc = SearchService(_EmptyDB())
    out = svc.search_restaurants(RestaurantSearchRequest(location='Chicago'))
    assert out
    assert all(r.verification_status == 'verified' for r in out)
    assert all(r.source_status == 'ok' for r in out)
    assert all(r.cache_status == 'miss' for r in out)
    assert all(r.google_maps_uri or r.provider_place_id or r.place_id for r in out)


def test_search_restaurants_miss_returns_12_for_full_pool():
    """Cold cache returns all 12 restaurant pool entries (no cuisine filter)."""
    svc = SearchService(_EmptyDB())
    out = svc.search_restaurants(RestaurantSearchRequest(location='Chicago'))
    assert len(out) == 12, f"Expected 12 verified restaurants on miss, got {len(out)}"


def test_search_restaurants_cache_hit_does_not_raise_name_error():
    """Cache hit path previously used undefined raw_count -> NameError -> 500.

    Reproduce by using a DB mock that returns pre-cached restaurant data,
    then confirm search_restaurants completes without exception and returns results.
    """
    # Get a real miss result to seed the hit payload
    miss_svc = SearchService(_EmptyDB())
    miss_results = miss_svc.search_restaurants(RestaurantSearchRequest(location='Chicago'))
    cached_payload = [r.model_dump(mode="json") for r in miss_results]

    # Now simulate cache hit with a DB that returns this payload
    hit_svc = SearchService(_CacheHitDB(cached_payload))
    # This must NOT raise NameError: name 'raw_count' is not defined
    hit_results = hit_svc.search_restaurants(RestaurantSearchRequest(location='Chicago'))
    assert hit_results, "Cache hit path must return results (raw_count NameError fix)"
    assert all(r.cache_status == 'hit' for r in hit_results)


def test_search_restaurants_cache_hit_returns_verified_restaurants():
    """Cache hit results must still carry identity fields and verification_status=verified."""
    miss_svc = SearchService(_EmptyDB())
    cached_payload = [r.model_dump(mode="json") for r in
                      miss_svc.search_restaurants(RestaurantSearchRequest(location='Boston'))]

    hit_svc = SearchService(_CacheHitDB(cached_payload))
    out = hit_svc.search_restaurants(RestaurantSearchRequest(location='Boston'))
    assert out
    assert all(r.verification_status == 'verified' for r in out)
    assert all(r.google_maps_uri or r.provider_place_id or r.place_id for r in out)
    assert all(r.cache_status == 'hit' for r in out)
    assert all(r.source_status == 'ok' for r in out)


def test_search_restaurants_cache_hit_count_matches_miss_count():
    """Cache hit must return the same number of restaurants as the miss that seeded it."""
    miss_svc = SearchService(_EmptyDB())
    miss_results = miss_svc.search_restaurants(RestaurantSearchRequest(location='Seattle'))
    cached_payload = [r.model_dump(mode="json") for r in miss_results]

    hit_svc = SearchService(_CacheHitDB(cached_payload))
    hit_results = hit_svc.search_restaurants(RestaurantSearchRequest(location='Seattle'))
    assert len(miss_results) == len(hit_results), (
        f"Cache hit returned {len(hit_results)} but miss returned {len(miss_results)}"
    )


def test_search_restaurants_cache_hit_rescores_null_ai_score():
    """Cache hit path re-scores entries with ai_score=None using the deterministic formula."""
    miss_svc = SearchService(_EmptyDB())
    miss_results = miss_svc.search_restaurants(RestaurantSearchRequest(location='Denver'))
    # Null out ai_score in the cached payload to simulate stale pre-scoring cache
    cached_payload = [r.model_dump(mode="json") for r in miss_results]
    for item in cached_payload:
        item["ai_score"] = None

    hit_svc = SearchService(_CacheHitDB(cached_payload))
    hit_results = hit_svc.search_restaurants(RestaurantSearchRequest(location='Denver'))
    # All results should have ai_score re-computed (not None)
    assert all(r.ai_score is not None for r in hit_results), (
        "Cache hit must re-score restaurants with null ai_score"
    )


# ─── ExploreSnapshotRestaurant identity contract ─────────────────────────────

def test_explore_snapshot_restaurant_has_identity_fields():
    """ExploreSnapshotRestaurant must declare provider_place_id, google_maps_uri, place_id.

    These were missing — causing identity to be stripped by Pydantic on PUT, so snapshot
    restaurants always failed the frontend trust gate on next load, triggering perpetual
    self-heal which then hit the raw_count NameError on every warm-cache reload.
    """
    r = ExploreSnapshotRestaurant(
        id="rst-1",
        name="Test",
        cuisine="Italian",
        location="Chicago",
        address="123 Main St",
        provider_place_id="mock-test-chicago",
        google_maps_uri="https://www.google.com/maps/place/?q=place_id:mock-test-chicago",
        place_id="mock-test-chicago",
    )
    assert r.provider_place_id == "mock-test-chicago"
    assert r.google_maps_uri == "https://www.google.com/maps/place/?q=place_id:mock-test-chicago"
    assert r.place_id == "mock-test-chicago"


def test_explore_snapshot_restaurant_identity_fields_optional():
    """Identity fields must be optional (None by default) for backwards compat with old snapshots."""
    r = ExploreSnapshotRestaurant(
        id="rst-2",
        name="Test",
        cuisine="Mexican",
        location="Chicago",
        address="456 Oak Ave",
    )
    assert r.provider_place_id is None
    assert r.google_maps_uri is None
    assert r.place_id is None


def test_explore_snapshot_restaurant_serializes_identity_fields():
    """model_dump must include identity fields so they're stored in JSONB and survive GET."""
    r = ExploreSnapshotRestaurant(
        id="rst-3",
        name="Test",
        cuisine="Thai",
        location="Chicago",
        address="789 Elm St",
        provider_place_id="mock-place-123",
        google_maps_uri="https://maps.google.com/...",
        place_id="mock-place-123",
    )
    d = r.model_dump(mode="json")
    assert d["provider_place_id"] == "mock-place-123"
    assert d["google_maps_uri"] == "https://maps.google.com/..."
    assert d["place_id"] == "mock-place-123"


def test_unverified_restaurant_has_no_identity_in_miss():
    """Restaurants from mock data always have identity; no unverified ones returned."""
    svc = SearchService(_EmptyDB())
    out = svc.search_restaurants(RestaurantSearchRequest(location='Miami'))
    unverified = [r for r in out if r.verification_status != 'verified']
    assert not unverified, f"Found {len(unverified)} unverified restaurants — expected 0"
