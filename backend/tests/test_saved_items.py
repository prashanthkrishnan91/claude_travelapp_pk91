"""Tests for SavedItemsService — Stage 2A Slice 2.

Covers: create (new), create (idempotent dedup), list (active only),
list (vertical filter), soft-delete, cross-user isolation.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from uuid import uuid4

import pytest

from app.models.saved_items import SavedItemCreate
from app.services.saved_items import SavedItemsService


# ---------------------------------------------------------------------------
# Minimal in-memory Supabase client stub
# ---------------------------------------------------------------------------

class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows):
        self.rows = rows
        self.filters: list = []
        self.mode = "select"
        self.payload = None
        self.limit_n = None
        self._desc = False

    def select(self, _ = "*"):
        return self

    def eq(self, field, value):
        self.filters.append((field, str(value)))
        return self

    def order(self, _, desc=False):
        self._desc = desc
        return self

    def limit(self, n):
        self.limit_n = n
        return self

    def insert(self, payload):
        self.mode = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.mode = "update"
        self.payload = payload
        return self

    def _match(self, row):
        return all(str(row.get(f)) == v for f, v in self.filters)

    def execute(self):
        if self.mode == "select":
            rows = [dict(r) for r in self.rows if self._match(r)]
            if self.limit_n is not None:
                rows = rows[: self.limit_n]
            return _Result(rows)
        if self.mode == "insert":
            row = dict(self.payload)
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", "2026-01-01T00:00:00+00:00")
            row.setdefault("updated_at", "2026-01-01T00:00:00+00:00")
            self.rows.append(row)
            return _Result([dict(row)])
        if self.mode == "update":
            out = []
            for r in self.rows:
                if self._match(r):
                    r.update(dict(self.payload))
                    out.append(dict(r))
            return _Result(out)
        return _Result([])


class _DB:
    def __init__(self):
        self.tables: dict = {"saved_items": []}

    def table(self, name):
        return _Query(self.tables[name])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_payload(vertical="restaurant", name="Le Bistro") -> SavedItemCreate:
    return SavedItemCreate(
        vertical=vertical,
        display_name=name,
        provider="google_places",
        provider_place_id="ChIJplace123",
        display_snapshot={"name": name, "rating": 4.5},
        search_context={"destination": "Paris"},
        provenance={"source": "explore_shell"},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_returns_saved_item():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    payload = _make_payload()
    item = svc.create(payload, user)
    assert item.vertical == "restaurant"
    assert item.display_name == "Le Bistro"
    assert item.status == "active"
    assert item.provider == "google_places"
    assert item.provider_place_id == "ChIJplace123"


def test_create_idempotent_same_provider_identity():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    payload = _make_payload()
    first = svc.create(payload, user)
    second = svc.create(payload, user)
    # No duplicate rows; second call returns the same id
    assert first.id == second.id
    assert len(db.tables["saved_items"]) == 1


def test_create_no_dedup_without_provider_place_id():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    payload = SavedItemCreate(
        vertical="flight",
        display_name="NYC → LAX",
        display_snapshot={},
        search_context={"origin": "JFK", "destination": "LAX"},
    )
    svc.create(payload, user)
    svc.create(payload, user)
    # Flights without provider_place_id should not dedup
    assert len(db.tables["saved_items"]) == 2


def test_list_returns_only_active():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    item = svc.create(_make_payload(), user)
    svc.delete(item.id, user)
    items = svc.list_active(user)
    assert items == []


def test_list_all_active_for_user():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    svc.create(_make_payload("restaurant", "A"), user)
    svc.create(_make_payload("attraction", "B"), user)
    items = svc.list_active(user)
    assert len(items) == 2


def test_list_vertical_filter():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    svc.create(_make_payload("restaurant", "A"), user)
    svc.create(
        SavedItemCreate(
            vertical="hotel",
            display_name="Grand Hotel",
            provider="google_places",
            provider_place_id="ChIJhotel",
            display_snapshot={},
            search_context={"destination": "Paris", "guests": 2},
        ),
        user,
    )
    restaurants = svc.list_active(user, vertical="restaurant")
    assert len(restaurants) == 1
    assert restaurants[0].vertical == "restaurant"


def test_delete_soft_deletes():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    item = svc.create(_make_payload(), user)
    svc.delete(item.id, user)
    row = db.tables["saved_items"][0]
    assert row["status"] == "deleted"


def test_delete_raises_for_nonexistent():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    import fastapi
    with pytest.raises((fastapi.HTTPException, Exception)):
        svc.delete(uuid4(), user)


def test_cross_user_isolation_list():
    db = _DB()
    svc = SavedItemsService(db)
    user_a = uuid4()
    user_b = uuid4()
    svc.create(_make_payload("restaurant", "A's place"), user_a)
    items_b = svc.list_active(user_b)
    assert items_b == []


def test_cross_user_cannot_delete():
    db = _DB()
    svc = SavedItemsService(db)
    owner = uuid4()
    intruder = uuid4()
    item = svc.create(_make_payload(), owner)
    import fastapi
    with pytest.raises((fastapi.HTTPException, Exception)):
        svc.delete(item.id, intruder)


def test_hotel_search_context_preserved():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    payload = SavedItemCreate(
        vertical="hotel",
        display_name="Grand Palais",
        provider="google_places",
        provider_place_id="ChIJhotel456",
        display_snapshot={"name": "Grand Palais"},
        search_context={
            "destination": "Paris",
            "check_in": "2026-06-01",
            "check_out": "2026-06-05",
            "guests": 2,
            "rooms": 1,
        },
        provenance={"source": "explore_shell"},
    )
    item = svc.create(payload, user)
    assert item.search_context["guests"] == 2
    assert "passengers" not in item.search_context


def test_flight_search_context_preserved():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    payload = SavedItemCreate(
        vertical="flight",
        display_name="JFK → CDG",
        display_snapshot={"name": "JFK → CDG"},
        search_context={
            "origin": "JFK",
            "destination": "CDG",
            "departure_date": "2026-06-01",
            "passengers": 2,
            "cabin_class": "economy",
        },
        provenance={"source": "explore_shell"},
    )
    item = svc.create(payload, user)
    assert item.search_context["passengers"] == 2
    assert "guests" not in item.search_context


def test_display_name_blank_rejected():
    with pytest.raises(Exception):
        SavedItemCreate(vertical="restaurant", display_name="   ")
