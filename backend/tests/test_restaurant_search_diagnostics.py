"""Tests for the restaurant search provider wiring and cache contract.

Covers:
1. /search/restaurants does not call or return mocks.
2. With Google Places provider configured + fake HTTP response → returns verified restaurants.
3. Missing provider config fails closed to [] with source_status=no_provider.
4. Provider failure fails closed to [] and does not write fake results.
5. Stale all-mock cache is bypassed/discarded.
6. Real provider results are cached safely.
7. Returned restaurant payload has canonical place_id/provider_place_id and google_maps_uri.
8. No loose name+city Maps URL fallback introduced.
9. Cuisine filter does not drop all valid provider results unless truly unmatched.
10. Logging contract: raw_candidates, verified_candidates, returned, cache_status,
    source_status, provider_configured all logged distinctly.
+ ExploreSnapshotRestaurant identity field contract (regression guards).
"""

import json
import os
from unittest.mock import MagicMock, patch, call
from app.models.search import RestaurantSearchRequest, RestaurantResult, ExploreSnapshotRestaurant
from app.services.search import (
    SearchService,
    _cache_key,
    _fetch_restaurants_google_places,
    _GOOGLE_TYPE_TO_CUISINE,
    _PRICE_LEVEL_MAP,
)




def _fetch_results(*args, **kwargs):
    return _fetch_restaurants_google_places(*args, **kwargs)[0]

# ---------------------------------------------------------------------------
# DB stubs
# ---------------------------------------------------------------------------

class _EmptyDB:
    """Mock DB that always returns empty cache (cold cache)."""
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
    """Mock DB that returns pre-populated cache payload."""

    def __init__(self, cached_payload):
        self._cached_payload = cached_payload
        self.upserted = []

    def table(self, _):
        cached = self._cached_payload
        store = self

        class _Q:
            def select(self, *a, **k): return self
            def eq(self, *a, **k): return self
            def gt(self, *a, **k): return self
            def limit(self, *a, **k): return self
            def upsert(self, record, **k):
                store.upserted.append(record)
                return self
            def insert(self, *a, **k): return self
            def execute(self_inner):
                class R:
                    data = [{"payload": {"results": cached}, "expires_at": None}]
                return R()
        return _Q()


class _EmptyThenWriteDB:
    """Cold cache that records cache writes — used to verify provider results are cached."""

    def __init__(self):
        self.written = []

    def table(self, _):
        store = self

        class _Q:
            def select(self, *a, **k): return self
            def eq(self, *a, **k): return self
            def gt(self, *a, **k): return self
            def limit(self, *a, **k): return self
            def upsert(self, record, **k):
                store.written.append(record)
                return self
            def insert(self, *a, **k): return self
            def execute(self_inner):
                class R:
                    data = []
                return R()
        return _Q()


# ---------------------------------------------------------------------------
# Fake Google Places response helpers
# ---------------------------------------------------------------------------

def _make_fake_place(
    place_id="ChIJabc123",
    name="Alinea",
    address="1723 N Halsted St, Chicago, IL 60614",
    lat=41.913817,
    lng=-87.648878,
    status="OPERATIONAL",
    rating=4.8,
    num_reviews=2500,
    google_maps_uri="https://maps.google.com/?cid=1234567890",
    price_level="PRICE_LEVEL_VERY_EXPENSIVE",
    primary_type="restaurant",
    types=None,
    opening_hours=None,
):
    place = {
        "id": place_id,
        "displayName": {"text": name},
        "formattedAddress": address,
        "location": {"latitude": lat, "longitude": lng},
        "businessStatus": status,
        "rating": rating,
        "userRatingCount": num_reviews,
        "googleMapsUri": google_maps_uri,
        "priceLevel": price_level,
        "primaryType": primary_type,
        "types": types or [primary_type, "food", "establishment", "point_of_interest"],
    }
    if opening_hours:
        place["regularOpeningHours"] = {"weekdayDescriptions": [opening_hours]}
    return place


def _fake_httpx_response(places):
    """Return a mock httpx response that yields a Google Places JSON payload."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"places": places}
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _patch_httpx(places):
    """Context manager: patches httpx.Client to return a fake Google Places response."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post = MagicMock(return_value=_fake_httpx_response(places))
    return patch("httpx.Client", return_value=mock_client), mock_client


# ---------------------------------------------------------------------------
# 1. /search/restaurants does NOT call or return mocks
# ---------------------------------------------------------------------------

def test_search_restaurants_no_provider_returns_empty():
    """Cold cache + no GOOGLE_PLACES_API_KEY → [] with source_status=no_provider, never mock data."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("GOOGLE_PLACES_API_KEY", None)
        svc = SearchService(_EmptyDB())
        out = svc.search_restaurants(RestaurantSearchRequest(location="Chicago"))
    assert out == [], "Must return [] when no provider is configured"


def test_search_restaurants_miss_never_returns_mock_source():
    """Results must never carry source='mock' on any path."""
    fake_place = _make_fake_place()
    ctx, _ = _patch_httpx([fake_place])
    with ctx, patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "fake-key"}):
        svc = SearchService(_EmptyDB())
        out = svc.search_restaurants(RestaurantSearchRequest(location="Chicago"))
    assert all(r.source != "mock" for r in out), "No result may carry source='mock'"


# ---------------------------------------------------------------------------
# 2. With Google Places provider configured → returns verified restaurants
# ---------------------------------------------------------------------------

def test_search_restaurants_calls_google_places_when_key_configured():
    """With key + fake HTTP response, search_restaurants returns non-empty verified results."""
    fake_place = _make_fake_place()
    ctx, mock_client = _patch_httpx([fake_place])
    with ctx, patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "fake-key"}):
        svc = SearchService(_EmptyDB())
        out = svc.search_restaurants(RestaurantSearchRequest(location="Chicago"))
    assert len(out) == 1
    r = out[0]
    assert r.source == "google_places"
    assert r.source_status == "ok"
    assert r.cache_status == "miss"
    assert r.verification_status == "verified"


def test_search_restaurants_provider_result_has_canonical_identity():
    """Provider results must carry provider_place_id, place_id, and google_maps_uri."""
    fake_place = _make_fake_place(
        place_id="ChIJabc999",
        google_maps_uri="https://maps.google.com/?cid=999",
    )
    ctx, _ = _patch_httpx([fake_place])
    with ctx, patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "fake-key"}):
        svc = SearchService(_EmptyDB())
        out = svc.search_restaurants(RestaurantSearchRequest(location="Chicago"))
    assert len(out) == 1
    r = out[0]
    assert r.provider_place_id == "ChIJabc999"
    assert r.place_id == "ChIJabc999"
    assert r.google_maps_uri == "https://maps.google.com/?cid=999"


# ---------------------------------------------------------------------------
# 3. Missing provider config → fail closed to []
# ---------------------------------------------------------------------------

def test_search_restaurants_no_key_does_not_call_http():
    """When GOOGLE_PLACES_API_KEY is absent, no HTTP call is made."""
    with patch("httpx.Client") as mock_httpx_client:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GOOGLE_PLACES_API_KEY", None)
            svc = SearchService(_EmptyDB())
            out = svc.search_restaurants(RestaurantSearchRequest(location="Chicago"))
    mock_httpx_client.assert_not_called()
    assert out == []


# ---------------------------------------------------------------------------
# 4. Provider HTTP failure → fail closed to []
# ---------------------------------------------------------------------------

def test_search_restaurants_provider_failure_fails_closed():
    """If httpx raises, search_restaurants returns [] and does not cache fake results."""
    import httpx as real_httpx

    db = _EmptyThenWriteDB()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post = MagicMock(side_effect=real_httpx.ConnectError("timeout"))

    with patch("httpx.Client", return_value=mock_client), \
         patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "fake-key"}):
        svc = SearchService(db)
        out = svc.search_restaurants(RestaurantSearchRequest(location="Chicago"))

    assert out == [], "Provider failure must return []"
    assert db.written == [], "Nothing must be written to cache on provider failure"


def test_fetch_restaurants_google_places_returns_empty_on_http_error():
    """_fetch_restaurants_google_places itself returns [] on any HTTP exception."""
    import httpx as real_httpx
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post = MagicMock(side_effect=real_httpx.ConnectError("refused"))

    with patch("httpx.Client", return_value=mock_client):
        out = _fetch_results(
            RestaurantSearchRequest(location="Chicago"), api_key="fake-key"
        )
    assert out == []


# ---------------------------------------------------------------------------
# 5. Stale all-mock cache is bypassed/discarded
# ---------------------------------------------------------------------------

def test_search_restaurants_stale_mock_cache_bypassed():
    """All-mock cache entries are discarded and the provider is called instead."""
    mock_cached = [
        {
            "id": "rst-mock-1", "name": "Bangkok Garden Chicago", "source": "mock",
            "cuisine": "Thai", "address": "715 Main St", "rating": 4.5,
            "location": "Chicago", "booking_url": "https://www.google.com/maps/place/?q=place_id:mock-1",
            "booking_options": [], "source_status": "ok", "cache_status": "miss",
            "verification_status": "verified", "provider_place_id": "mock-1",
            "google_maps_uri": "https://www.google.com/maps/place/?q=place_id:mock-1",
            "place_id": "mock-1",
        }
    ]
    fake_place = _make_fake_place(place_id="ChIJreal123", name="Real Restaurant")
    ctx, _ = _patch_httpx([fake_place])

    with ctx, patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "fake-key"}):
        svc = SearchService(_CacheHitDB(mock_cached))
        out = svc.search_restaurants(RestaurantSearchRequest(location="Chicago"))

    # Mock cache was bypassed → live provider was called → returned real result
    assert len(out) == 1
    assert out[0].source == "google_places"
    assert "mock" not in (out[0].provider_place_id or "")


# ---------------------------------------------------------------------------
# 6. Real provider results are cached safely
# ---------------------------------------------------------------------------

def test_search_restaurants_real_results_cached_with_google_places_source():
    """Provider results are written to cache with source='google_places'."""
    fake_place = _make_fake_place(place_id="ChIJcache1")
    ctx, _ = _patch_httpx([fake_place])
    db = _EmptyThenWriteDB()

    with ctx, patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "fake-key"}):
        svc = SearchService(db)
        out = svc.search_restaurants(RestaurantSearchRequest(location="Chicago"))

    assert out, "Provider should return results"
    assert db.written, "Results must be written to cache"
    assert db.written[0]["source"] == "google_places"
    cached_results = db.written[0]["payload"]["results"]
    assert all(r["source"] == "google_places" for r in cached_results)


def test_search_restaurants_empty_provider_not_cached():
    """Empty provider result must NOT be cached (no spurious cache pollution)."""
    db = _EmptyThenWriteDB()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post = MagicMock(return_value=_fake_httpx_response([]))  # empty places

    with patch("httpx.Client", return_value=mock_client), \
         patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "fake-key"}):
        svc = SearchService(db)
        out = svc.search_restaurants(RestaurantSearchRequest(location="Chicago"))

    assert out == []
    assert db.written == [], "Empty provider result must not be written to cache"


# ---------------------------------------------------------------------------
# 7. Returned payload includes canonical place_id/provider_place_id and google_maps_uri
# ---------------------------------------------------------------------------

def test_search_restaurants_booking_url_uses_canonical_maps_uri():
    """booking_url must be the canonical googleMapsUri, not a loose name+city query URL."""
    canonical_uri = "https://maps.google.com/?cid=9876543210"
    fake_place = _make_fake_place(google_maps_uri=canonical_uri)
    ctx, _ = _patch_httpx([fake_place])

    with ctx, patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "fake-key"}):
        svc = SearchService(_EmptyDB())
        out = svc.search_restaurants(RestaurantSearchRequest(location="Chicago"))

    assert len(out) == 1
    assert out[0].booking_url == canonical_uri, "booking_url must equal canonical googleMapsUri"
    assert "q=" not in out[0].booking_url or "place_id:" in out[0].booking_url, (
        "Loose name+city query URL must not appear when googleMapsUri is present"
    )


def test_search_restaurants_booking_url_fallback_uses_place_id():
    """When googleMapsUri is absent, booking_url falls back to canonical place_id URL."""
    fake_place = _make_fake_place(place_id="ChIJfallback", google_maps_uri=None)
    fake_place["googleMapsUri"] = None
    ctx, _ = _patch_httpx([fake_place])

    with ctx, patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "fake-key"}):
        svc = SearchService(_EmptyDB())
        out = svc.search_restaurants(RestaurantSearchRequest(location="Chicago"))

    assert len(out) == 1
    assert "place_id:ChIJfallback" in out[0].booking_url, (
        "Fallback booking_url must use canonical place_id, not loose name+city"
    )


# ---------------------------------------------------------------------------
# 8. No loose name+city Maps URL fallback
# ---------------------------------------------------------------------------

def test_fetch_restaurants_no_loose_name_city_url():
    """Mapping must never produce a Google Maps URL with q=<name>+<city> (non-canonical)."""
    fake_place = _make_fake_place(
        place_id="ChIJstrict", google_maps_uri="https://maps.google.com/?cid=111"
    )
    ctx, _ = _patch_httpx([fake_place])

    with ctx:
        out = _fetch_results(
            RestaurantSearchRequest(location="Chicago"), api_key="fake-key"
        )

    for r in out:
        # A loose name+city URL looks like maps.google.com/maps/search/Name+City
        # or maps.google.com/?q=Alinea+Chicago  (no place_id:)
        if r.booking_url and "q=" in r.booking_url:
            assert "place_id:" in r.booking_url, (
                f"Loose URL detected (no place_id:): {r.booking_url}"
            )


# ---------------------------------------------------------------------------
# 9. Cuisine filter does not drop all valid provider results
# ---------------------------------------------------------------------------

def test_cuisine_filter_does_not_drop_all_results():
    """If cuisine filter would drop all results, the full list is returned as fallback."""
    # Place with cuisine "Restaurant" — won't match "Italian" filter.
    fake_place = _make_fake_place(primary_type="restaurant", types=["restaurant", "food"])
    ctx, _ = _patch_httpx([fake_place])

    with ctx, patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "fake-key"}):
        svc = SearchService(_EmptyDB())
        out = svc.search_restaurants(RestaurantSearchRequest(location="Chicago", cuisine="Italian"))

    # Filter would drop the only result, so fallback keeps it.
    assert len(out) == 1, "Cuisine filter must not drop all results when none match"


def test_cuisine_filter_applied_when_match_exists():
    """Cuisine filter is applied when at least one result matches."""
    italian = _make_fake_place(place_id="ChIJit", name="Osteria", primary_type="italian_restaurant")
    japanese = _make_fake_place(place_id="ChIJjp", name="Nobu", primary_type="japanese_restaurant")
    ctx, _ = _patch_httpx([italian, japanese])

    with ctx, patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "fake-key"}):
        svc = SearchService(_EmptyDB())
        out = svc.search_restaurants(RestaurantSearchRequest(location="Chicago", cuisine="Italian"))

    assert len(out) == 1
    assert out[0].place_id == "ChIJit"


# ---------------------------------------------------------------------------
# 10. Logging contract
# ---------------------------------------------------------------------------

def test_search_restaurants_logs_provider_configured_false_on_miss(caplog):
    """Cache miss without key must log provider_configured=False and source_status=no_provider."""
    import logging
    with caplog.at_level(logging.INFO, logger="app.services.search"):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GOOGLE_PLACES_API_KEY", None)
            svc = SearchService(_EmptyDB())
            svc.search_restaurants(RestaurantSearchRequest(location="Chicago"))

    combined = " ".join(caplog.messages)
    assert "cache_status=miss" in combined
    assert "provider_configured=False" in combined
    assert "source_status=no_provider" in combined
    assert "raw_candidates=0" in combined
    assert "verified_candidates=0" in combined
    assert "returned=0" in combined


def test_search_restaurants_logs_full_counts_on_cache_hit(caplog):
    """Cache hit path must log raw_candidates, verified_candidates, returned, source_status=ok."""
    import logging
    cached_payload = [
        {
            "id": "gp-ChIJabc", "name": "Good Place", "source": "google_places",
            "cuisine": "Italian", "address": "123 Main St, Chicago", "rating": 4.5,
            "location": "Chicago", "booking_url": "https://maps.google.com/?cid=1",
            "booking_options": [], "source_status": "ok", "cache_status": "miss",
            "verification_status": "verified", "provider_place_id": "ChIJabc",
            "google_maps_uri": "https://maps.google.com/?cid=1", "place_id": "ChIJabc",
            "num_reviews": 1000, "ai_score": 85.0,
        }
    ]
    with caplog.at_level(logging.INFO, logger="app.services.search"):
        svc = SearchService(_CacheHitDB(cached_payload))
        svc.search_restaurants(RestaurantSearchRequest(location="Chicago"))

    combined = " ".join(caplog.messages)
    assert "cache_status=hit" in combined
    assert "raw_candidates=1" in combined
    assert "verified_candidates=1" in combined
    assert "returned=1" in combined
    assert "source_status=ok" in combined


def test_search_restaurants_logs_provider_call_counts(caplog):
    """Live provider call must log raw_candidates, verified_candidates, returned, source_status."""
    import logging
    fake_place = _make_fake_place()
    ctx, _ = _patch_httpx([fake_place])

    with ctx, caplog.at_level(logging.INFO, logger="app.services.search"), \
         patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "fake-key"}):
        svc = SearchService(_EmptyDB())
        out = svc.search_restaurants(RestaurantSearchRequest(location="Chicago"))

    combined = " ".join(caplog.messages)
    assert "provider_configured=True" in combined
    assert "raw_candidates=1" in combined
    assert "verified_candidates=1" in combined
    assert "returned=1" in combined
    assert "source_status=ok" in combined


# ---------------------------------------------------------------------------
# Cache hit path correctness (regression guards — not dependent on live provider)
# ---------------------------------------------------------------------------

def _make_google_places_cached_payload(count=3):
    """Build a realistic google_places-sourced cache payload for hit tests."""
    payload = []
    for i in range(count):
        payload.append({
            "id": f"gp-ChIJ{i:03d}",
            "name": f"Restaurant {i}",
            "source": "google_places",
            "cuisine": "Italian",
            "address": f"{i+1}00 N Halsted St, Chicago",
            "rating": 4.0 + i * 0.2,
            "num_reviews": 1000 * (i + 1),
            "location": "Chicago",
            "booking_url": f"https://maps.google.com/?cid={i}",
            "booking_options": [],
            "source_status": "ok",
            "cache_status": "miss",
            "verification_status": "verified",
            "provider_place_id": f"ChIJ{i:03d}",
            "google_maps_uri": f"https://maps.google.com/?cid={i}",
            "place_id": f"ChIJ{i:03d}",
            "ai_score": 70.0 + i * 5,
        })
    return payload


def test_search_restaurants_cache_hit_does_not_raise():
    """Cache hit path must complete without exception and return results."""
    payload = _make_google_places_cached_payload(3)
    svc = SearchService(_CacheHitDB(payload))
    out = svc.search_restaurants(RestaurantSearchRequest(location="Chicago"))
    assert out, "Cache hit must return results"
    assert all(r.cache_status == "hit" for r in out)


def test_search_restaurants_cache_hit_returns_verified_restaurants():
    """Cache hit results must carry identity fields and verification_status=verified."""
    payload = _make_google_places_cached_payload(2)
    svc = SearchService(_CacheHitDB(payload))
    out = svc.search_restaurants(RestaurantSearchRequest(location="Chicago"))
    assert out
    assert all(r.verification_status == "verified" for r in out)
    assert all(r.google_maps_uri or r.provider_place_id or r.place_id for r in out)
    assert all(r.cache_status == "hit" for r in out)
    assert all(r.source_status == "ok" for r in out)


def test_search_restaurants_cache_hit_count_matches_seeded():
    """Cache hit must return the same count as was seeded."""
    payload = _make_google_places_cached_payload(5)
    svc = SearchService(_CacheHitDB(payload))
    out = svc.search_restaurants(RestaurantSearchRequest(location="Chicago"))
    assert len(out) == 5


def test_search_restaurants_cache_hit_rescores_null_ai_score():
    """Cache hit path must re-score entries with ai_score=None."""
    payload = _make_google_places_cached_payload(2)
    for item in payload:
        item["ai_score"] = None

    svc = SearchService(_CacheHitDB(payload))
    out = svc.search_restaurants(RestaurantSearchRequest(location="Chicago"))
    assert all(r.ai_score is not None for r in out), "Cache hit must re-score null ai_score entries"


# ---------------------------------------------------------------------------
# _fetch_restaurants_google_places unit tests
# ---------------------------------------------------------------------------

def test_fetch_skips_non_operational_places():
    """Non-OPERATIONAL places (closed etc.) are excluded from results."""
    places = [
        _make_fake_place(place_id="ChIJopen", name="Open", status="OPERATIONAL"),
        _make_fake_place(place_id="ChIJclosed", name="Closed", status="CLOSED_PERMANENTLY"),
    ]
    ctx, _ = _patch_httpx(places)
    with ctx:
        out = _fetch_results(
            RestaurantSearchRequest(location="Chicago"), api_key="fake-key"
        )
    assert len(out) == 1
    assert out[0].place_id == "ChIJopen"


def test_fetch_skips_places_without_id():
    """Places missing an id field are excluded."""
    place_no_id = _make_fake_place()
    place_no_id.pop("id")
    ctx, _ = _patch_httpx([place_no_id])
    with ctx:
        out = _fetch_results(
            RestaurantSearchRequest(location="Chicago"), api_key="fake-key"
        )
    assert out == []


def test_fetch_price_level_string_enum_mapped():
    """priceLevel string enum from New API is mapped to integer 0–4."""
    for enum_str, expected_int in _PRICE_LEVEL_MAP.items():
        place = _make_fake_place(price_level=enum_str)
        ctx, _ = _patch_httpx([place])
        with ctx:
            out = _fetch_results(
                RestaurantSearchRequest(location="Chicago"), api_key="fake-key"
            )
        if out:
            assert out[0].price_level == expected_int, f"{enum_str} should map to {expected_int}"


def test_fetch_cuisine_from_primary_type():
    """Cuisine is resolved from primaryType before types list."""
    place = _make_fake_place(primary_type="italian_restaurant", types=["restaurant", "food"])
    ctx, _ = _patch_httpx([place])
    with ctx:
        out = _fetch_results(
            RestaurantSearchRequest(location="Chicago"), api_key="fake-key"
        )
    assert out
    assert out[0].cuisine == "Italian"


def test_fetch_cuisine_fallback_from_types():
    """When primaryType is generic, cuisine is resolved from the types list."""
    place = _make_fake_place(primary_type="restaurant", types=["japanese_restaurant", "food"])
    ctx, _ = _patch_httpx([place])
    with ctx:
        out = _fetch_results(
            RestaurantSearchRequest(location="Chicago"), api_key="fake-key"
        )
    assert out
    assert out[0].cuisine == "Japanese"


def test_fetch_returns_empty_when_api_key_missing():
    """_fetch_restaurants_google_places returns [] immediately when api_key is empty."""
    out = _fetch_results(
        RestaurantSearchRequest(location="Chicago"), api_key=""
    )
    assert out == []


# ---------------------------------------------------------------------------
# ExploreSnapshotRestaurant identity contract (regression guards)
# ---------------------------------------------------------------------------

def test_explore_snapshot_restaurant_has_identity_fields():
    """ExploreSnapshotRestaurant must declare provider_place_id, google_maps_uri, place_id."""
    r = ExploreSnapshotRestaurant(
        id="rst-1",
        name="Test",
        cuisine="Italian",
        location="Chicago",
        address="123 Main St",
        provider_place_id="ChIJabc",
        google_maps_uri="https://maps.google.com/?cid=1",
        place_id="ChIJabc",
    )
    assert r.provider_place_id == "ChIJabc"
    assert r.google_maps_uri == "https://maps.google.com/?cid=1"
    assert r.place_id == "ChIJabc"


def test_explore_snapshot_restaurant_identity_fields_optional():
    """Identity fields must be optional for backwards compat with old snapshots."""
    r = ExploreSnapshotRestaurant(
        id="rst-2", name="Test", cuisine="Mexican", location="Chicago", address="456 Oak Ave"
    )
    assert r.provider_place_id is None
    assert r.google_maps_uri is None
    assert r.place_id is None


def test_explore_snapshot_restaurant_serializes_identity_fields():
    """model_dump must include identity fields so they survive Pydantic round-trip."""
    r = ExploreSnapshotRestaurant(
        id="rst-3", name="Test", cuisine="Thai", location="Chicago", address="789 Elm St",
        provider_place_id="ChIJplace", google_maps_uri="https://maps.google.com/...", place_id="ChIJplace",
    )
    d = r.model_dump(mode="json")
    assert d["provider_place_id"] == "ChIJplace"
    assert d["google_maps_uri"] == "https://maps.google.com/..."
    assert d["place_id"] == "ChIJplace"
