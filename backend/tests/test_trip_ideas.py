"""
Tests for Saved Trip Ideas / Unscheduled Items feature.

Covers:
1. Saving an idea does NOT assign it to Day 1 (day_id stays null).
2. list_unscheduled_items returns only day_id=null items.
3. Duplicate idea for the same trip/title is not created.
4. Existing Add-to-Day behavior still assigns to the correct day.
5. Assigning an idea to a day removes it from unscheduled results.
6. API data contract: unscheduled items have day_id=None.
"""
from __future__ import annotations

from uuid import uuid4

import pytest

from app.models.itinerary import ItineraryDayCreate, ItineraryItemDirectCreate, ItineraryItemUpdate
from app.services.itinerary import ItineraryService


# ---------------------------------------------------------------------------
# Minimal Supabase mock — supports eq, is_, order, limit, insert, update, delete
# ---------------------------------------------------------------------------

class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, table_rows: list[dict]):
        self.table_rows = table_rows
        self.filters: list[tuple[str, str]] = []
        self.null_checks: list[str] = []
        self.not_null_checks: list[str] = []
        self.order_field: str | None = None
        self.order_desc = False
        self.limit_n: int | None = None
        self._mode = "select"
        self._payload = None

    def select(self, _cols: str = "*"):
        return self

    def eq(self, field: str, value):
        self.filters.append((field, str(value)))
        return self

    def is_(self, field: str, value: str):
        if value.lower() == "null":
            self.null_checks.append(field)
        else:
            self.not_null_checks.append(field)
        return self

    def order(self, field: str, desc: bool = False):
        self.order_field = field
        self.order_desc = desc
        return self

    def limit(self, n: int):
        self.limit_n = n
        return self

    def insert(self, payload):
        self._mode = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._mode = "update"
        self._payload = payload
        return self

    def delete(self):
        self._mode = "delete"
        return self

    def _match(self, row: dict) -> bool:
        for field, value in self.filters:
            if str(row.get(field)) != value:
                return False
        for field in self.null_checks:
            if row.get(field) is not None:
                return False
        for field in self.not_null_checks:
            if row.get(field) is None:
                return False
        return True

    def execute(self):
        if self._mode == "select":
            rows = [dict(r) for r in self.table_rows if self._match(r)]
            if self.order_field:
                rows.sort(key=lambda r: r.get(self.order_field), reverse=self.order_desc)
            if self.limit_n is not None:
                rows = rows[: self.limit_n]
            return _Result(rows)

        if self._mode == "insert":
            row = dict(self._payload)
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", "2026-01-01T00:00:00+00:00")
            row.setdefault("updated_at", "2026-01-01T00:00:00+00:00")
            self.table_rows.append(row)
            return _Result([dict(row)])

        if self._mode == "update":
            updated = []
            for row in self.table_rows:
                if self._match(row):
                    row.update(dict(self._payload))
                    updated.append(dict(row))
            return _Result(updated)

        if self._mode == "delete":
            self.table_rows[:] = [r for r in self.table_rows if not self._match(r)]
            return _Result([])

        return _Result([])


class _FakeDB:
    def __init__(self):
        self.tables: dict[str, list[dict]] = {
            "itinerary_days": [],
            "itinerary_items": [],
        }

    def table(self, name: str):
        return _Query(self.tables[name])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_idea(trip_id, title: str = "Nobu Chicago", item_type: str = "meal") -> ItineraryItemDirectCreate:
    return ItineraryItemDirectCreate(
        trip_id=trip_id,
        item_type=item_type,
        title=title,
        location="River North",
        details={"source_kind": "concierge_idea"},
    )


def _make_day(svc: ItineraryService, trip_id, number: int = 1):
    from datetime import date as _date
    return svc.create_day(
        ItineraryDayCreate(
            trip_id=trip_id,
            day_number=number,
            title=f"Day {number}",
            date=_date(2026, 6, number),
        )
    )


# ---------------------------------------------------------------------------
# Test 1: Saving an idea does NOT assign it to Day 1 (day_id stays null)
# ---------------------------------------------------------------------------

def test_save_to_trip_ideas_does_not_assign_to_day():
    db = _FakeDB()
    svc = ItineraryService(db)
    trip_id = uuid4()
    _make_day(svc, trip_id, 1)  # Day 1 exists

    idea = svc.create_trip_item(_make_idea(trip_id))

    assert idea.day_id is None, "Saved trip idea must NOT be assigned to any day"
    assert idea.trip_id == trip_id


# ---------------------------------------------------------------------------
# Test 2: list_unscheduled_items returns only day_id=null items
# ---------------------------------------------------------------------------

def test_list_unscheduled_items_returns_only_null_day_items():
    db = _FakeDB()
    svc = ItineraryService(db)
    trip_id = uuid4()
    day = _make_day(svc, trip_id, 1)

    # Insert one scheduled item (with day_id) directly into the fake DB
    scheduled_id = str(uuid4())
    db.tables["itinerary_items"].append({
        "id": scheduled_id,
        "trip_id": str(trip_id),
        "day_id": str(day.id),
        "item_type": "meal",
        "title": "Scheduled Restaurant",
        "position": 0,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "details": {},
    })

    idea = svc.create_trip_item(_make_idea(trip_id, "Nobu Chicago"))
    assert idea.day_id is None

    unscheduled = svc.list_unscheduled_items(trip_id)

    ids = [it.id for it in unscheduled]
    assert idea.id in ids, "Saved idea should appear in unscheduled list"
    assert scheduled_id not in ids, "Scheduled item must NOT appear in unscheduled list"


# ---------------------------------------------------------------------------
# Test 2b: list_unscheduled_items includes creation_seed for supported item types
# ---------------------------------------------------------------------------

def test_list_unscheduled_items_includes_creation_seed_activity_and_meal():
    db = _FakeDB()
    svc = ItineraryService(db)
    trip_id = uuid4()

    idea = svc.create_trip_item(_make_idea(trip_id, "Lou Malnati's"))
    activity_id = str(uuid4())
    meal_id = str(uuid4())
    db.tables["itinerary_items"].extend([
        {
            "id": activity_id,
            "trip_id": str(trip_id),
            "day_id": None,
            "item_type": "activity",
            "title": "Tokyo Tower",
            "position": 1,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "details": {"source_kind": "creation_seed"},
        },
        {
            "id": meal_id,
            "trip_id": str(trip_id),
            "day_id": None,
            "item_type": "meal",
            "title": "Sushi Dai",
            "position": 2,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "details": {"source_kind": "creation_seed"},
        },
    ])

    unscheduled = svc.list_unscheduled_items(trip_id)
    ids = {str(it.id) for it in unscheduled}
    assert str(idea.id) in ids
    assert activity_id in ids
    assert meal_id in ids

# ---------------------------------------------------------------------------
# Test 3: Duplicate idea for the same trip/title is not created
# ---------------------------------------------------------------------------

def test_duplicate_idea_not_created():
    db = _FakeDB()
    svc = ItineraryService(db)
    trip_id = uuid4()

    first = svc.create_trip_item(_make_idea(trip_id, "Nobu Chicago"))
    second = svc.create_trip_item(_make_idea(trip_id, "Nobu Chicago"))

    assert first.id == second.id, "Second save should return the existing idea, not create a duplicate"
    unscheduled = svc.list_unscheduled_items(trip_id)
    assert len(unscheduled) == 1, "Only one idea should exist in the unscheduled list"


# ---------------------------------------------------------------------------
# Test 4: Add-to-Day still assigns to the correct day
# ---------------------------------------------------------------------------

def test_add_to_day_assigns_to_correct_day():
    db = _FakeDB()
    svc = ItineraryService(db)
    trip_id = uuid4()
    day = _make_day(svc, trip_id, 1)

    payload = ItineraryItemDirectCreate(
        trip_id=trip_id,
        day_id=day.id,
        item_type="activity",
        title="Art Institute of Chicago",
        location="Chicago Loop",
        details={},
    )
    item = svc.create_trip_item(payload)

    assert item.day_id == day.id, "Item added to a day must have that day's ID"
    assert item.day_id is not None

    unscheduled = svc.list_unscheduled_items(trip_id)
    assert all(it.id != item.id for it in unscheduled), "Day-assigned item must NOT appear in unscheduled list"


# ---------------------------------------------------------------------------
# Test 5: Assigning an idea to a day removes it from unscheduled results
# ---------------------------------------------------------------------------

def test_assigning_idea_to_day_removes_from_unscheduled():
    db = _FakeDB()
    svc = ItineraryService(db)
    trip_id = uuid4()
    day = _make_day(svc, trip_id, 1)

    idea = svc.create_trip_item(_make_idea(trip_id, "Girl & the Goat"))

    before = svc.list_unscheduled_items(trip_id)
    assert any(it.id == idea.id for it in before), "Idea should be in unscheduled list before assignment"

    # Assign to a day via update_item
    svc.update_item(idea.id, ItineraryItemUpdate(day_id=day.id))

    after = svc.list_unscheduled_items(trip_id)
    assert all(it.id != idea.id for it in after), "After assignment, idea must NOT appear in unscheduled list"


def test_assigning_idea_to_day_preserves_concierge_metadata():
    db = _FakeDB()
    svc = ItineraryService(db)
    trip_id = uuid4()
    day = _make_day(svc, trip_id, 2)

    idea = svc.create_trip_item(_make_idea(trip_id, "Arbella"))
    merged = dict(idea.details)
    merged["idea_status"] = "maybe"
    merged["user_note"] = "Try rooftop seating"
    idea = svc.update_item(idea.id, ItineraryItemUpdate(details=merged))

    assigned = svc.update_item(idea.id, ItineraryItemUpdate(day_id=day.id))
    assert assigned.day_id == day.id
    assert assigned.details.get("source_kind") == "concierge_idea"
    assert assigned.details.get("idea_status") == "maybe"
    assert assigned.details.get("user_note") == "Try rooftop seating"


# ---------------------------------------------------------------------------
# Test 6: API data contract — unscheduled items have day_id=None
# ---------------------------------------------------------------------------

def test_unscheduled_items_have_null_day_id():
    db = _FakeDB()
    svc = ItineraryService(db)
    trip_id = uuid4()

    svc.create_trip_item(_make_idea(trip_id, "Smyth"))
    svc.create_trip_item(_make_idea(trip_id, "Alinea"))

    unscheduled = svc.list_unscheduled_items(trip_id)

    assert len(unscheduled) == 2
    for item in unscheduled:
        assert item.day_id is None, f"Item {item.title} has unexpected day_id={item.day_id}"
        assert item.trip_id == trip_id


# ---------------------------------------------------------------------------
# Test 7: Different trips do not share unscheduled items
# ---------------------------------------------------------------------------

def test_unscheduled_items_scoped_to_trip():
    db = _FakeDB()
    svc = ItineraryService(db)
    trip_a = uuid4()
    trip_b = uuid4()

    svc.create_trip_item(_make_idea(trip_a, "Girl & the Goat"))
    svc.create_trip_item(_make_idea(trip_b, "Nobu Chicago"))

    ideas_a = svc.list_unscheduled_items(trip_a)
    ideas_b = svc.list_unscheduled_items(trip_b)

    assert len(ideas_a) == 1
    assert ideas_a[0].title == "Girl & the Goat"
    assert len(ideas_b) == 1
    assert ideas_b[0].title == "Nobu Chicago"


# ---------------------------------------------------------------------------
# Test 8: Updating idea_status via merged details preserves source_kind
# ---------------------------------------------------------------------------

def test_update_idea_status_preserves_source_kind():
    """Merging idea_status into details must not clobber source_kind."""
    db = _FakeDB()
    svc = ItineraryService(db)
    trip_id = uuid4()

    idea = svc.create_trip_item(_make_idea(trip_id, "Alinea"))
    assert idea.details.get("source_kind") == "concierge_idea"

    # Simulate the frontend merge: spread existing details + new fields
    merged = dict(idea.details)
    merged["idea_status"] = "must_do"
    merged["user_note"] = "Reserve three months out"

    updated = svc.update_item(idea.id, ItineraryItemUpdate(details=merged))

    assert updated.details.get("source_kind") == "concierge_idea", "source_kind must survive JSONB merge"
    assert updated.details.get("idea_status") == "must_do"
    assert updated.details.get("user_note") == "Reserve three months out"


# ---------------------------------------------------------------------------
# Test 9: Skipped ideas are still returned by list_unscheduled_items (backend
# does not filter by status — that is the frontend's responsibility)
# ---------------------------------------------------------------------------

def test_skipped_ideas_still_returned_by_backend_list():
    """Backend returns all concierge ideas regardless of idea_status.

    Filtering of 'skipped' ideas is the frontend's responsibility so that
    users can reveal skipped items via the show-skipped toggle without an
    extra API call.
    """
    db = _FakeDB()
    svc = ItineraryService(db)
    trip_id = uuid4()

    idea = svc.create_trip_item(_make_idea(trip_id, "Smyth"))

    # Mark as skipped via update
    merged = dict(idea.details)
    merged["idea_status"] = "skipped"
    svc.update_item(idea.id, ItineraryItemUpdate(details=merged))

    unscheduled = svc.list_unscheduled_items(trip_id)
    ids = [it.id for it in unscheduled]
    assert idea.id in ids, "Backend must return skipped ideas; frontend handles the hide-by-default logic"


def test_moving_assigned_idea_back_to_unscheduled_preserves_details():
    db = _FakeDB()
    svc = ItineraryService(db)
    trip_id = uuid4()
    day = _make_day(svc, trip_id, 1)

    idea = svc.create_trip_item(
        ItineraryItemDirectCreate(
            trip_id=trip_id,
            day_id=day.id,
            item_type="meal",
            title="Monteverde",
            location="West Loop",
            details={
                "source_kind": "concierge_idea",
                "idea_status": "must_do",
                "user_note": "Book early",
                "maps_link": "https://maps.example/abc",
            },
        )
    )

    moved = svc.update_item(idea.id, ItineraryItemUpdate(day_id=None))
    assert moved.day_id is None
    assert moved.details.get("source_kind") == "concierge_idea"
    assert moved.details.get("idea_status") == "must_do"
    assert moved.details.get("user_note") == "Book early"
    assert moved.details.get("maps_link") == "https://maps.example/abc"

    unscheduled = svc.list_unscheduled_items(trip_id)
    assert any(it.id == moved.id for it in unscheduled), "Moved idea should reappear in unscheduled list"
