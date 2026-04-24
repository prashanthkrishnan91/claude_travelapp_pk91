from __future__ import annotations

from datetime import date
from uuid import uuid4

from app.models.itinerary import ItineraryDayCreate
from app.services.itinerary import ItineraryService


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, table_rows: list[dict]):
        self.table_rows = table_rows
        self.filters: list[tuple[str, str]] = []
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
        return all(str(row.get(field)) == value for field, value in self.filters)

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
        self.tables = {"itinerary_days": [], "itinerary_items": []}

    def table(self, name: str):
        return _Query(self.tables[name])


def _create_day(svc: ItineraryService, trip_id, day_number: int, d: date):
    return svc.create_day(ItineraryDayCreate(trip_id=trip_id, day_number=day_number, title=f"Day {day_number}", date=d))


def test_ensure_trip_days_same_start_end_creates_one_day():
    db = _FakeDB()
    svc = ItineraryService(db)
    trip_id = uuid4()

    days = svc.ensure_trip_days(trip_id, date(2026, 6, 5), date(2026, 6, 5))

    assert [d.day_number for d in days] == [1]
    assert [d.date.isoformat() for d in days if d.date] == ["2026-06-05"]


def test_ensure_trip_days_inclusive_range_creates_six_days():
    db = _FakeDB()
    svc = ItineraryService(db)
    trip_id = uuid4()

    days = svc.ensure_trip_days(trip_id, date(2026, 6, 5), date(2026, 6, 10))

    assert [d.day_number for d in days] == [1, 2, 3, 4, 5, 6]
    assert days[-1].date.isoformat() == "2026-06-10"


def test_ensure_trip_days_partial_existing_creates_missing_only():
    db = _FakeDB()
    svc = ItineraryService(db)
    trip_id = uuid4()

    _create_day(svc, trip_id, 1, date(2026, 6, 5))

    days = svc.ensure_trip_days(trip_id, date(2026, 6, 5), date(2026, 6, 7))

    assert [d.day_number for d in days] == [1, 2, 3]
    assert len(db.tables["itinerary_days"]) == 3


def test_ensure_trip_days_existing_full_range_no_duplicates():
    db = _FakeDB()
    svc = ItineraryService(db)
    trip_id = uuid4()

    _create_day(svc, trip_id, 1, date(2026, 6, 5))
    _create_day(svc, trip_id, 2, date(2026, 6, 6))
    _create_day(svc, trip_id, 3, date(2026, 6, 7))

    days = svc.ensure_trip_days(trip_id, date(2026, 6, 5), date(2026, 6, 7))

    assert [d.day_number for d in days] == [1, 2, 3]
    assert len(db.tables["itinerary_days"]) == 3
