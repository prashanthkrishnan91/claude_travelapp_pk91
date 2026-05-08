"""
Tests for Explore Candidate Snapshot persistence (per-trip, stored in trips.metadata).

Covers:
1. get_explore_snapshot returns None when no snapshot in metadata.
2. get_explore_snapshot returns snapshot dict when present.
3. save_explore_snapshot writes snapshot into metadata preserving other metadata keys.
4. save_explore_snapshot creates metadata when trip has empty metadata.
5. ExploreSnapshot model validates required fields and defaults.
6. ExploreSnapshotAttraction preserves ai_score field.
7. ExploreSnapshotRestaurant preserves ai_score field.
8. Snapshot round-trip: save then get returns same data.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.search import ExploreSnapshot, ExploreSnapshotAttraction, ExploreSnapshotRestaurant
from app.services.trips import TripsService


# ---------------------------------------------------------------------------
# Minimal DB mock that supports trips table operations
# ---------------------------------------------------------------------------

class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, table_rows: list[dict]):
        self.table_rows = table_rows
        self.filters: list[tuple[str, str]] = []
        self._mode = "select"
        self._payload = None

    def select(self, _cols: str = "*"):
        return self

    def eq(self, field: str, value):
        self.filters.append((field, str(value)))
        return self

    def order(self, field: str, desc: bool = False):
        return self

    def limit(self, n: int):
        return self

    def update(self, payload):
        self._mode = "update"
        self._payload = payload
        return self

    def insert(self, payload):
        self._mode = "insert"
        self._payload = payload
        return self

    def _match(self, row: dict) -> bool:
        for field, value in self.filters:
            if str(row.get(field)) != value:
                return False
        return True

    def execute(self):
        if self._mode == "select":
            rows = [dict(r) for r in self.table_rows if self._match(r)]
            return _Result(rows)

        if self._mode == "update":
            updated = []
            for row in self.table_rows:
                if self._match(row):
                    row.update(dict(self._payload))
                    updated.append(dict(row))
            return _Result(updated)

        if self._mode == "insert":
            row = dict(self._payload)
            row.setdefault("id", str(uuid4()))
            self.table_rows.append(row)
            return _Result([dict(row)])

        return _Result([])


class _FakeDB:
    def __init__(self, trips: list[dict] | None = None):
        self.tables: dict[str, list[dict]] = {
            "trips": trips or [],
        }

    def table(self, name: str):
        if name not in self.tables:
            self.tables[name] = []
        return _Query(self.tables[name])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trip(user_id, metadata: dict | None = None) -> dict:
    return {
        "id": str(uuid4()),
        "user_id": str(user_id),
        "title": "Test Trip",
        "destination": "Paris",
        "status": "draft",
        "metadata": metadata or {},
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }


def _sample_snapshot() -> dict:
    return {
        "destination": "Paris",
        "created_at": "2026-05-02T10:00:00Z",
        "attractions": [
            {
                "id": "attr-1",
                "name": "Eiffel Tower",
                "category": "landmark",
                "description": "Iconic iron tower",
                "location": "Paris",
                "address": "Champ de Mars, Paris",
                "rating": 4.7,
                "num_reviews": 120000,
                "ai_score": 92.5,
                "tags": ["Must Visit", "Iconic"],
                "lat": 48.8584,
                "lng": 2.2945,
            }
        ],
        "restaurants": [
            {
                "id": "rest-1",
                "name": "Le Jules Verne",
                "cuisine": "French",
                "location": "Paris",
                "address": "Eiffel Tower, Paris",
                "rating": 4.5,
                "num_reviews": 8000,
                "ai_score": 87.0,
                "tags": ["Fine Dining"],
                "lat": 48.8582,
                "lng": 2.2946,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Tests: TripsService snapshot methods
# ---------------------------------------------------------------------------

def test_get_explore_snapshot_returns_none_when_absent():
    user_id = uuid4()
    trip = _make_trip(user_id, metadata={})
    db = _FakeDB(trips=[trip])
    svc = TripsService(db)

    result = svc.get_explore_snapshot(trip["id"], user_id)

    assert result is None, "Should return None when trips.metadata has no explore_snapshot key"


def test_get_explore_snapshot_returns_snapshot_when_present():
    user_id = uuid4()
    snapshot = _sample_snapshot()
    trip = _make_trip(user_id, metadata={"explore_snapshot": snapshot})
    db = _FakeDB(trips=[trip])
    svc = TripsService(db)

    result = svc.get_explore_snapshot(trip["id"], user_id)

    assert result is not None
    assert result["destination"] == "Paris"
    assert len(result["attractions"]) == 1
    assert result["attractions"][0]["name"] == "Eiffel Tower"
    assert result["attractions"][0]["ai_score"] == 92.5


def test_save_explore_snapshot_writes_into_metadata():
    user_id = uuid4()
    trip = _make_trip(user_id, metadata={"existing_key": "existing_value"})
    db = _FakeDB(trips=[trip])
    svc = TripsService(db)

    snapshot = _sample_snapshot()
    svc.save_explore_snapshot(trip["id"], user_id, snapshot)

    result = svc.get_explore_snapshot(trip["id"], user_id)
    assert result is not None
    assert result["destination"] == "Paris"


def test_save_explore_snapshot_preserves_other_metadata_keys():
    user_id = uuid4()
    trip = _make_trip(user_id, metadata={"other_key": "preserve_me"})
    db = _FakeDB(trips=[trip])
    svc = TripsService(db)

    svc.save_explore_snapshot(trip["id"], user_id, _sample_snapshot())

    # Verify existing key is not clobbered in the in-memory representation
    trip_row = db.tables["trips"][0]
    assert trip_row["metadata"].get("other_key") == "preserve_me"
    assert "explore_snapshot" in trip_row["metadata"]


def test_save_explore_snapshot_works_with_empty_metadata():
    user_id = uuid4()
    trip = _make_trip(user_id, metadata={})
    db = _FakeDB(trips=[trip])
    svc = TripsService(db)

    svc.save_explore_snapshot(trip["id"], user_id, _sample_snapshot())

    result = svc.get_explore_snapshot(trip["id"], user_id)
    assert result is not None
    assert result["destination"] == "Paris"


# ---------------------------------------------------------------------------
# Tests: ExploreSnapshot Pydantic model validation
# ---------------------------------------------------------------------------

def test_explore_snapshot_model_roundtrip():
    attr = ExploreSnapshotAttraction(
        id="attr-1",
        name="Louvre",
        category="museum",
        description="World-renowned art museum",
        location="Paris",
        address="Rue de Rivoli, Paris",
        rating=4.8,
        num_reviews=200000,
        ai_score=95.0,
        tags=["Must Visit"],
        lat=48.8606,
        lng=2.3376,
    )
    rest = ExploreSnapshotRestaurant(
        id="rest-1",
        name="Café de Flore",
        cuisine="French Café",
        location="Paris",
        address="172 Bd Saint-Germain, Paris",
        rating=4.2,
        ai_score=78.5,
        tags=["Historic"],
    )
    snap = ExploreSnapshot(
        destination="Paris",
        created_at="2026-05-02T10:00:00Z",
        attractions=[attr],
        restaurants=[rest],
    )

    data = snap.model_dump(mode="json")
    assert data["destination"] == "Paris"
    assert len(data["attractions"]) == 1
    assert data["attractions"][0]["ai_score"] == 95.0
    assert len(data["restaurants"]) == 1
    assert data["restaurants"][0]["ai_score"] == 78.5


def test_explore_snapshot_attraction_ai_score_is_optional():
    attr = ExploreSnapshotAttraction(
        id="attr-2",
        name="Notre-Dame",
        category="landmark",
        location="Paris",
        address="6 Parvis Notre-Dame, Paris",
    )
    assert attr.ai_score is None, "ai_score must default to None when not provided"
    assert attr.description == "", "description must default to empty string"


def test_explore_snapshot_restaurant_ai_score_is_optional():
    rest = ExploreSnapshotRestaurant(
        id="rest-2",
        name="L'Ami Jean",
        cuisine="Basque",
        location="Paris",
        address="27 Rue Malar, Paris",
    )
    assert rest.ai_score is None, "ai_score must default to None when not provided"
    assert rest.sentiment is None


def test_explore_snapshot_empty_arrays_are_valid():
    snap = ExploreSnapshot(
        destination="Tokyo",
        created_at="2026-05-02T00:00:00Z",
    )
    assert snap.attractions == []
    assert snap.restaurants == []


def test_explore_snapshot_ownership_enforced_by_user_id():
    """get_explore_snapshot must not return data for a different user's trip."""
    owner_id = uuid4()
    other_id = uuid4()
    trip = _make_trip(owner_id, metadata={"explore_snapshot": _sample_snapshot()})
    db = _FakeDB(trips=[trip])
    svc = TripsService(db)

    # Requesting as a different user should raise (trip not found for that user)
    import fastapi
    with pytest.raises((fastapi.HTTPException, Exception)):
        svc.get_explore_snapshot(trip["id"], other_id)


# ---------------------------------------------------------------------------
# Tests: stale cache-hit re-scoring in search_restaurants
#
# v1D removed ``SearchService.search_attractions`` (mock-backed surface);
# the analogous attraction cache-rescoring tests have been deleted with it.
# ---------------------------------------------------------------------------

from app.services.search import SearchService, _compute_restaurant_ai_score
from app.models.search import RestaurantSearchRequest


class _FakeSupabase:
    """Minimal Supabase client mock for search service cache tests.

    Returns rows in the format _get_cache expects:
    [{"payload": {"results": [...]}, "expires_at": None}]
    """

    def __init__(self, cached_rows=None):
        self._cached_rows = cached_rows  # None = cache miss; list = cache hit

    def table(self, name):
        return self

    def select(self, *_):
        return self

    def eq(self, *_):
        return self

    def gt(self, *_):
        return self

    def order(self, *_):
        return self

    def limit(self, *_):
        return self

    def execute(self):
        class _R:
            def __init__(self, data):
                self.data = data
        if self._cached_rows is None:
            return _R([])
        return _R([{"payload": {"results": self._cached_rows}, "expires_at": None}])

    def insert(self, *_):
        return self

    def upsert(self, *_):
        return self


def test_search_restaurants_rescores_stale_cache_hit_with_null_ai_score():
    """Stale restaurant cache rows with ai_score=None are re-scored on cache hit."""
    stale_row = {
        "id": "rest-stale-1",
        "name": "Old Bistro",
        "cuisine": "French",
        "location": "Paris",
        "address": "12 Bistro Lane",
        "rating": 4.4,
        "num_reviews": 8000,
        "price_level": 2,
        "opening_hours": None,
        "ai_score": None,
        "sentiment": None,
        "tags": [],
        "booking_url": "https://maps.google.com/?cid=1",
        "source": "google_places",
        "provider_place_id": "ChIJbistro",
        "google_maps_uri": "https://maps.google.com/?cid=1",
        "place_id": "ChIJbistro",
        "lat": 48.85,
        "lng": 2.36,
    }
    db = _FakeSupabase(cached_rows=[stale_row])
    svc = SearchService(db)
    req = RestaurantSearchRequest(location="Paris")
    results = svc.search_restaurants(req)

    assert len(results) == 1
    result = results[0]
    assert result.ai_score is not None, "Cache-hit re-scoring must populate restaurant ai_score"
    assert result.ai_score > 0, "Re-scored restaurant ai_score must be positive"
    expected = _compute_restaurant_ai_score(4.4, 8000, 2, None)
    assert result.ai_score == expected, "Re-scored value must match _compute_restaurant_ai_score"


def test_search_restaurants_preserves_existing_positive_ai_score():
    """Restaurant cache rows that already have a positive ai_score must not be re-scored."""
    cached_row = {
        "id": "rest-scored-1",
        "name": "Le Gourmet",
        "cuisine": "French",
        "location": "Paris",
        "address": "5 Gourmet Place",
        "rating": 4.7,
        "num_reviews": 20000,
        "price_level": 3,
        "opening_hours": None,
        "ai_score": 85.0,
        "sentiment": 0.9,
        "tags": [],
        "booking_url": "https://maps.google.com/?cid=2",
        "source": "google_places",
        "provider_place_id": "ChIJgourmet",
        "google_maps_uri": "https://maps.google.com/?cid=2",
        "place_id": "ChIJgourmet",
        "lat": 48.84,
        "lng": 2.37,
    }
    db = _FakeSupabase(cached_rows=[cached_row])
    svc = SearchService(db)
    req = RestaurantSearchRequest(location="Paris")
    results = svc.search_restaurants(req)

    assert results[0].ai_score == 85.0, "Existing positive restaurant ai_score must be preserved"
