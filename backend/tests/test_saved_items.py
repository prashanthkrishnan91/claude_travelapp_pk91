"""Tests for SavedItemsService — Stage 2A Slice 2 (patched).

Covers: create (new), create (idempotent dedup by place id), create (idempotent
dedup by item/offer id), list (active only), list (vertical filter), list (invalid
vertical rejected), soft-delete, cross-user isolation, hotel context (guests + rooms,
no passengers), flight context (passengers, no guests), display_name blank rejected,
provider_item_id persisted on the row.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from uuid import uuid4

import pytest

from app.models.saved_items import SavedItemCreate, SavedItemNoteUpdate
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

def _place_payload(vertical="restaurant", name="Le Bistro") -> SavedItemCreate:
    return SavedItemCreate(
        vertical=vertical,
        display_name=name,
        provider="google_places",
        provider_place_id="ChIJplace123",
        display_snapshot={"name": name, "rating": 4.5},
        search_context={"destination": "Paris"},
        provenance={"source": "explore_shell"},
    )


def _flight_payload(offer_id: str = "offer-abc") -> SavedItemCreate:
    return SavedItemCreate(
        vertical="flight",
        display_name="JFK → CDG",
        provider="duffel",
        provider_item_id=offer_id,
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_returns_saved_item():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    item = svc.create(_place_payload(), user)
    assert item.vertical == "restaurant"
    assert item.display_name == "Le Bistro"
    assert item.status == "active"
    assert item.provider == "google_places"
    assert item.provider_place_id == "ChIJplace123"
    assert item.provider_item_id is None


def test_create_persists_provider_item_id():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    item = svc.create(_flight_payload("offer-xyz"), user)
    assert item.provider_item_id == "offer-xyz"
    assert item.provider_place_id is None


def test_create_idempotent_by_place_id():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    first = svc.create(_place_payload(), user)
    second = svc.create(_place_payload(), user)
    assert first.id == second.id
    assert len(db.tables["saved_items"]) == 1


def test_create_idempotent_by_item_id():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    first = svc.create(_flight_payload("offer-abc"), user)
    second = svc.create(_flight_payload("offer-abc"), user)
    assert first.id == second.id
    assert len(db.tables["saved_items"]) == 1


def test_create_no_dedup_without_any_identity():
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
    assert len(db.tables["saved_items"]) == 2


def test_create_different_item_ids_not_deduped():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    svc.create(_flight_payload("offer-1"), user)
    svc.create(_flight_payload("offer-2"), user)
    assert len(db.tables["saved_items"]) == 2


def test_create_resilient_to_unique_conflict_on_insert():
    """Simulate a concurrent insert race: insert raises a unique conflict after
    the pre-check passes.  create() must recover the existing row and return it
    rather than surfacing a 500 to the caller."""
    user = uuid4()
    # Seed an existing row directly into the table so the conflict is pre-existing
    existing_row = {
        "id": str(uuid4()),
        "user_id": str(user),
        "vertical": "restaurant",
        "display_name": "Le Bistro",
        "provider": "google_places",
        "provider_place_id": "ChIJrace",
        "provider_item_id": None,
        "display_snapshot": {},
        "search_context": {},
        "provenance": {},
        "status": "active",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }

    class _ConflictQuery(_Query):
        def execute(self):
            if self.mode == "insert":
                raise Exception("duplicate key value violates unique constraint (23505)")
            return super().execute()

    class _ConflictDB(_DB):
        def __init__(self, existing):
            super().__init__()
            self.tables["saved_items"].append(existing)

        def table(self, name):
            return _ConflictQuery(self.tables[name])

    db = _ConflictDB(existing_row)
    svc = SavedItemsService(db)
    payload = SavedItemCreate(
        vertical="restaurant",
        display_name="Le Bistro",
        provider="google_places",
        provider_place_id="ChIJrace",
        display_snapshot={},
        search_context={},
    )
    recovered = svc.create(payload, user)
    assert str(recovered.id) == existing_row["id"]
    assert recovered.display_name == "Le Bistro"


def test_create_non_conflict_error_propagates():
    """Unrelated insert errors must not be swallowed."""
    user = uuid4()

    class _ErrorQuery(_Query):
        def execute(self):
            if self.mode == "insert":
                raise RuntimeError("connection refused")
            return super().execute()

    class _ErrorDB(_DB):
        def table(self, name):
            return _ErrorQuery(self.tables[name])

    db = _ErrorDB()
    svc = SavedItemsService(db)
    payload = SavedItemCreate(
        vertical="restaurant",
        display_name="Le Bistro",
        display_snapshot={},
        search_context={},
    )
    with pytest.raises(RuntimeError):
        svc.create(payload, user)


def test_list_returns_only_active():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    item = svc.create(_place_payload(), user)
    svc.delete(item.id, user)
    assert svc.list_active(user) == []


def test_list_all_active_for_user():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    svc.create(_place_payload("restaurant", "A"), user)
    svc.create(_place_payload("attraction", "B"), user)
    assert len(svc.list_active(user)) == 2


def test_list_vertical_filter():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    svc.create(_place_payload("restaurant", "A"), user)
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


def test_list_invalid_vertical_rejected():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    import fastapi
    with pytest.raises((fastapi.HTTPException, Exception)):
        svc.list_active(user, vertical="cruise")


def test_delete_soft_deletes():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    item = svc.create(_place_payload(), user)
    svc.delete(item.id, user)
    assert db.tables["saved_items"][0]["status"] == "deleted"


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
    user_a, user_b = uuid4(), uuid4()
    svc.create(_place_payload("restaurant", "A's place"), user_a)
    assert svc.list_active(user_b) == []


def test_cross_user_cannot_delete():
    db = _DB()
    svc = SavedItemsService(db)
    owner, intruder = uuid4(), uuid4()
    item = svc.create(_place_payload(), owner)
    import fastapi
    with pytest.raises((fastapi.HTTPException, Exception)):
        svc.delete(item.id, intruder)


def test_hotel_search_context_has_guests_and_rooms():
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
    assert item.search_context["rooms"] == 1
    assert "passengers" not in item.search_context


def test_flight_search_context_has_passengers_not_guests():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    item = svc.create(_flight_payload(), user)
    assert item.search_context["passengers"] == 2
    assert "guests" not in item.search_context


def test_display_name_blank_rejected():
    with pytest.raises(Exception):
        SavedItemCreate(vertical="restaurant", display_name="   ")


# ---------------------------------------------------------------------------
# Saved Notes v1 — update_note tests
# ---------------------------------------------------------------------------

def test_update_note_sets_note():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    item = svc.create(_place_payload(), user)
    updated = svc.update_note(item.id, SavedItemNoteUpdate(note="great rooftop"), user)
    assert updated.note == "great rooftop"
    assert updated.id == item.id


def test_update_note_trims_whitespace():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    item = svc.create(_place_payload(), user)
    updated = svc.update_note(item.id, SavedItemNoteUpdate(note="  near hotel  "), user)
    assert updated.note == "near hotel"


def test_update_note_clear_with_empty_string():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    item = svc.create(_place_payload(), user)
    svc.update_note(item.id, SavedItemNoteUpdate(note="first note"), user)
    cleared = svc.update_note(item.id, SavedItemNoteUpdate(note=""), user)
    assert cleared.note is None


def test_update_note_clear_with_none():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    item = svc.create(_place_payload(), user)
    svc.update_note(item.id, SavedItemNoteUpdate(note="anniversary dinner"), user)
    cleared = svc.update_note(item.id, SavedItemNoteUpdate(note=None), user)
    assert cleared.note is None


def test_update_note_unauthorized_raises_404():
    db = _DB()
    svc = SavedItemsService(db)
    owner = uuid4()
    intruder = uuid4()
    item = svc.create(_place_payload(), owner)
    import fastapi
    with pytest.raises((fastapi.HTTPException, Exception)):
        svc.update_note(item.id, SavedItemNoteUpdate(note="intruder note"), intruder)


def test_update_note_not_found_raises_404():
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    import fastapi
    with pytest.raises((fastapi.HTTPException, Exception)):
        svc.update_note(uuid4(), SavedItemNoteUpdate(note="ghost note"), user)


def test_update_note_returns_updated_saved_item_shape():
    """update_note returns a full SavedItem (not just the note field)."""
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    item = svc.create(_place_payload(), user)
    updated = svc.update_note(item.id, SavedItemNoteUpdate(note="bar with a view"), user)
    assert updated.vertical == item.vertical
    assert updated.display_name == item.display_name
    assert updated.status == "active"
    assert updated.note == "bar with a view"


def test_note_field_present_on_newly_created_item():
    """Existing rows work with note=None — no schema error."""
    db = _DB()
    svc = SavedItemsService(db)
    user = uuid4()
    item = svc.create(_place_payload(), user)
    assert item.note is None
