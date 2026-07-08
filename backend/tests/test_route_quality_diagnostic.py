"""Route-quality diagnostic service-level tests — AI Route Planning v1 PR A.

Governed by docs/ai/AI_ROUTE_PLANNING_V1_ADR.md (Section 9, PR A).

Proves:
- Feature flag default False → disabled response, no items fetched.
- 0 or 1 eligible stop → insufficient_stops, safe_for_ai False.
- 2+ eligible stops all with coords → status ready, safe_for_ai True.
- 2+ eligible stops with a missing-coordinate stop → missing_coordinates,
  safe_for_ai False, honest named missing list, nothing silently dropped.
- Flights/hotels/notes are excluded from eligible/missing lists with a
  reason, never treated as route stops.
- No provider call is made (no Google Routes / adapter symbols reachable).
- No itinerary write occurs (source contains no insert/update/delete calls).
- Current manual order (item.position) is preserved, never resequenced.
- Invalid/non-numeric/out-of-range/NaN/inf coordinates are treated as
  missing, never fabricated.
- A day that exists but belongs to a different trip than the URL's trip_id
  is rejected (404), never silently diagnosed under the wrong trip.
- The response never carries a duration/distance figure.
"""
from __future__ import annotations

import inspect
import math
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

import app.services.route_quality_diagnostic as svc


def _settings(enabled: bool) -> MagicMock:
    s = MagicMock()
    s.route_quality_diagnostic_v1_enabled = enabled
    return s


def _item(item_id, title, item_type, position, details=None):
    return SimpleNamespace(
        id=item_id,
        title=title,
        item_type=item_type,
        position=position,
        details=details or {},
    )


class _FakeItineraryService:
    """Stand-in for ItineraryService that returns a canned item list."""

    calls = []

    def __init__(self, db):
        self.db = db

    def list_items(self, day_id, user_id=None):
        _FakeItineraryService.calls.append((day_id, user_id))
        return _FakeItineraryService.items


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    """Minimal chainable stand-in for the Supabase query builder."""

    def __init__(self, rows):
        self._rows = list(rows)

    def select(self, *_a, **_k):
        return self

    def eq(self, field, value):
        self._rows = [r for r in self._rows if str(r.get(field)) == str(value)]
        return self

    def limit(self, n):
        self._rows = self._rows[:n]
        return self

    def execute(self):
        return _FakeResult(self._rows)


class _FakeDB:
    """Minimal stand-in for the Supabase client covering trips/itinerary_days."""

    def __init__(self, trips=(), days=()):
        self._trips = list(trips)
        self._days = list(days)

    def table(self, name):
        if name == "trips":
            return _FakeQuery(self._trips)
        if name == "itinerary_days":
            return _FakeQuery(self._days)
        raise AssertionError(f"unexpected table: {name}")


def _patch_itinerary_service(monkeypatch, items):
    """Inject a fake `app.services.itinerary` module before the service's
    lazy `from app.services.itinerary import ItineraryService` import runs,
    so the real module (which needs the full supabase/app.models stack) is
    never touched.
    """
    _FakeItineraryService.items = items
    _FakeItineraryService.calls = []
    fake_mod = types.ModuleType("app.services.itinerary")
    fake_mod.ItineraryService = _FakeItineraryService
    monkeypatch.setitem(sys.modules, "app.services.itinerary", fake_mod)


# ── feature flag disabled (default) ──────────────────────────────────────────


class TestFeatureFlagDisabled:
    def test_flag_false_returns_disabled_status(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        resp = svc.compute_route_quality_diagnostic(uuid4(), uuid4(), uuid4(), db=MagicMock())
        assert resp.status == "disabled"

    def test_flag_false_safe_for_ai_false(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        resp = svc.compute_route_quality_diagnostic(uuid4(), uuid4(), uuid4(), db=MagicMock())
        assert resp.safe_for_ai is False
        assert "feature_flag_disabled" in resp.ai_blockers

    def test_flag_false_does_not_import_itinerary_service(self, monkeypatch):
        # If the disabled path touched ItineraryService, this would try to
        # import the real app.services.itinerary module (which needs the
        # full supabase/app.models stack) and raise ImportError here.
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        monkeypatch.delitem(sys.modules, "app.services.itinerary", raising=False)
        resp = svc.compute_route_quality_diagnostic(uuid4(), uuid4(), uuid4(), db=MagicMock())
        assert resp.status == "disabled"
        assert "app.services.itinerary" not in sys.modules

    def test_flag_false_no_route_data_fabricated(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        resp = svc.compute_route_quality_diagnostic(uuid4(), uuid4(), uuid4(), db=MagicMock())
        assert resp.route_data_status == "unavailable"


# ── insufficient stops ───────────────────────────────────────────────────────


class TestInsufficientStops:
    def test_zero_eligible_stops(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        _patch_itinerary_service(monkeypatch, [])
        resp = svc.compute_route_quality_diagnostic(uuid4(), uuid4(), uuid4(), db=MagicMock())
        assert resp.status == "insufficient_stops"
        assert resp.eligible_stop_count == 0
        assert resp.safe_for_ai is False

    def test_one_eligible_stop(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        items = [_item(uuid4(), "Museum", "activity", 0, {"lat": 25.1, "lng": -80.1})]
        _patch_itinerary_service(monkeypatch, items)
        resp = svc.compute_route_quality_diagnostic(uuid4(), uuid4(), uuid4(), db=MagicMock())
        assert resp.status == "insufficient_stops"
        assert resp.eligible_stop_count == 1
        assert resp.safe_for_ai is False
        assert "insufficient_eligible_stops" in resp.ai_blockers


# ── ready / safe for AI ──────────────────────────────────────────────────────


class TestReadySafeForAi:
    def test_two_eligible_stops_with_coords_is_ready(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        items = [
            _item(uuid4(), "Museum", "activity", 0, {"lat": 25.1, "lng": -80.1}),
            _item(uuid4(), "Lunch", "meal", 1, {"lat": 25.2, "lng": -80.2}),
        ]
        _patch_itinerary_service(monkeypatch, items)
        resp = svc.compute_route_quality_diagnostic(uuid4(), uuid4(), uuid4(), db=MagicMock())
        assert resp.status == "ready"
        assert resp.safe_for_ai is True
        assert resp.missing_coordinate_count == 0
        assert resp.ai_blockers == []

    def test_manual_order_preserved(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        items = [
            _item(uuid4(), "Third", "activity", 2, {"lat": 25.3, "lng": -80.3}),
            _item(uuid4(), "First", "activity", 0, {"lat": 25.1, "lng": -80.1}),
            _item(uuid4(), "Second", "meal", 1, {"lat": 25.2, "lng": -80.2}),
        ]
        _patch_itinerary_service(monkeypatch, items)
        resp = svc.compute_route_quality_diagnostic(uuid4(), uuid4(), uuid4(), db=MagicMock())
        titles_in_order = [s.title for s in resp.eligible_stops]
        assert titles_in_order == ["Third", "First", "Second"]
        positions_in_order = [s.position for s in resp.eligible_stops]
        assert positions_in_order == [2, 0, 1]


# ── missing coordinates ───────────────────────────────────────────────────────


class TestMissingCoordinates:
    def test_missing_coordinate_stop_named_not_dropped(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        missing_id = uuid4()
        items = [
            _item(uuid4(), "Museum", "activity", 0, {"lat": 25.1, "lng": -80.1}),
            _item(missing_id, "Untracked Park", "activity", 1, {}),
        ]
        _patch_itinerary_service(monkeypatch, items)
        resp = svc.compute_route_quality_diagnostic(uuid4(), uuid4(), uuid4(), db=MagicMock())
        assert resp.status == "missing_coordinates"
        assert resp.safe_for_ai is False
        assert resp.eligible_stop_count == 2
        assert resp.missing_coordinate_count == 1
        assert len(resp.missing_coordinate_stops) == 1
        assert resp.missing_coordinate_stops[0].item_id == str(missing_id)
        # Not silently dropped: still present in the full eligible list too.
        eligible_ids = [s.item_id for s in resp.eligible_stops]
        assert str(missing_id) in eligible_ids
        assert "missing_stop_coordinates" in resp.ai_blockers

    def test_invalid_non_numeric_coordinates_rejected(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        items = [
            _item(uuid4(), "Museum", "activity", 0, {"lat": 25.1, "lng": -80.1}),
            _item(uuid4(), "Bad Coords", "activity", 1, {"lat": "not-a-number", "lng": None}),
        ]
        _patch_itinerary_service(monkeypatch, items)
        resp = svc.compute_route_quality_diagnostic(uuid4(), uuid4(), uuid4(), db=MagicMock())
        assert resp.status == "missing_coordinates"
        assert resp.missing_coordinate_count == 1
        assert resp.missing_coordinate_stops[0].lat is None
        assert resp.missing_coordinate_stops[0].lng is None

    @pytest.mark.parametrize(
        "bad_lat,bad_lng,expect_lat_none,expect_lng_none",
        [
            (91.0, -80.1, True, False),  # latitude out of range
            (25.1, 181.0, False, True),  # longitude out of range
            (math.nan, -80.1, True, False),
            (25.1, math.nan, False, True),
            (math.inf, -80.1, True, False),
            (25.1, -math.inf, False, True),
        ],
    )
    def test_out_of_range_and_non_finite_coordinates_rejected(
        self, monkeypatch, bad_lat, bad_lng, expect_lat_none, expect_lng_none
    ):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        items = [
            _item(uuid4(), "Museum", "activity", 0, {"lat": 25.1, "lng": -80.1}),
            _item(uuid4(), "Bad Coords", "activity", 1, {"lat": bad_lat, "lng": bad_lng}),
        ]
        _patch_itinerary_service(monkeypatch, items)
        resp = svc.compute_route_quality_diagnostic(uuid4(), uuid4(), uuid4(), db=MagicMock())
        # An out-of-range/non-finite axis makes the whole pair count as
        # missing — the diagnostic must never treat a bad coordinate as
        # located just because its sibling axis happened to be valid.
        assert resp.status == "missing_coordinates"
        assert resp.missing_coordinate_count == 1
        bad_stop = resp.missing_coordinate_stops[0]
        assert (bad_stop.lat is None) == expect_lat_none
        assert (bad_stop.lng is None) == expect_lng_none


# ── excluded stops ────────────────────────────────────────────────────────────


class TestExcludedStops:
    def test_flights_and_hotels_excluded_with_reason(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        items = [
            _item(uuid4(), "Flight AA100", "flight", 0, {"lat": 25.1, "lng": -80.1}),
            _item(uuid4(), "Hotel Stay", "hotel", 1, {"lat": 25.1, "lng": -80.1}),
            _item(uuid4(), "Note", "note", 2, {}),
            _item(uuid4(), "Museum", "activity", 3, {"lat": 25.1, "lng": -80.1}),
            _item(uuid4(), "Lunch", "meal", 4, {"lat": 25.2, "lng": -80.2}),
        ]
        _patch_itinerary_service(monkeypatch, items)
        resp = svc.compute_route_quality_diagnostic(uuid4(), uuid4(), uuid4(), db=MagicMock())
        assert resp.eligible_stop_count == 2
        excluded_types = {e.item_type for e in resp.excluded_stops}
        assert excluded_types == {"flight", "hotel", "note"}
        for excluded in resp.excluded_stops:
            assert excluded.reason
            assert "activity and meal" in excluded.reason


# ── trip/day ownership binding ───────────────────────────────────────────────


class TestTripDayOwnershipBinding:
    def test_day_belonging_to_a_different_trip_is_rejected(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id = uuid4()
        owned_trip_id = uuid4()
        other_trip_id = uuid4()
        day_id = uuid4()
        db = _FakeDB(
            trips=[{"id": str(owned_trip_id), "user_id": str(user_id)}],
            # The day exists, but belongs to a different trip than the URL's trip_id.
            days=[{"id": str(day_id), "trip_id": str(other_trip_id)}],
        )
        _patch_itinerary_service(monkeypatch, [])
        with pytest.raises(HTTPException):
            svc.compute_route_quality_diagnostic(owned_trip_id, day_id, user_id, db=db)
        # No items were read once the trip/day binding failed.
        assert _FakeItineraryService.calls == []

    def test_trip_not_owned_by_user_is_rejected(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id = uuid4()
        trip_id = uuid4()
        day_id = uuid4()
        db = _FakeDB(trips=[], days=[{"id": str(day_id), "trip_id": str(trip_id)}])
        _patch_itinerary_service(monkeypatch, [])
        with pytest.raises(HTTPException):
            svc.compute_route_quality_diagnostic(trip_id, day_id, user_id, db=db)
        assert _FakeItineraryService.calls == []

    def test_matching_trip_and_day_succeeds(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id = uuid4()
        trip_id = uuid4()
        day_id = uuid4()
        db = _FakeDB(
            trips=[{"id": str(trip_id), "user_id": str(user_id)}],
            days=[{"id": str(day_id), "trip_id": str(trip_id)}],
        )
        items = [
            _item(uuid4(), "Museum", "activity", 0, {"lat": 25.1, "lng": -80.1}),
            _item(uuid4(), "Lunch", "meal", 1, {"lat": 25.2, "lng": -80.2}),
        ]
        _patch_itinerary_service(monkeypatch, items)
        resp = svc.compute_route_quality_diagnostic(trip_id, day_id, user_id, db=db)
        assert resp.status == "ready"


# ── honest route data / no fabrication ───────────────────────────────────────


class TestNoFabrication:
    def test_route_data_status_always_unavailable(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        items = [
            _item(uuid4(), "Museum", "activity", 0, {"lat": 25.1, "lng": -80.1}),
            _item(uuid4(), "Lunch", "meal", 1, {"lat": 25.2, "lng": -80.2}),
        ]
        _patch_itinerary_service(monkeypatch, items)
        resp = svc.compute_route_quality_diagnostic(uuid4(), uuid4(), uuid4(), db=MagicMock())
        assert resp.route_data_status == "unavailable"

    def test_response_never_carries_duration_or_distance(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        items = [
            _item(uuid4(), "Museum", "activity", 0, {"lat": 25.1, "lng": -80.1}),
            _item(uuid4(), "Lunch", "meal", 1, {"lat": 25.2, "lng": -80.2}),
        ]
        _patch_itinerary_service(monkeypatch, items)
        resp = svc.compute_route_quality_diagnostic(uuid4(), uuid4(), uuid4(), db=MagicMock())
        dumped = resp.model_dump()
        # No structured duration/distance field exists anywhere on the model —
        # the only place either word may appear is inside the honest,
        # human-readable warning explaining that no such figure is available.
        assert "duration_seconds" not in dumped
        assert "distance_meters" not in dumped
        for stop in dumped["eligible_stops"] + dumped["missing_coordinate_stops"]:
            assert set(stop.keys()) == {"item_id", "title", "item_type", "position", "lat", "lng", "category"}

    def test_no_provider_call_symbols_in_source(self):
        source = inspect.getsource(svc)
        for banned in ("call_compute_routes", "google_routes", "httpx", "requests."):
            assert banned not in source

    def test_no_itinerary_write_symbols_in_source(self):
        source = inspect.getsource(svc)
        for banned in (".insert(", ".update(", ".delete(", ".upsert("):
            assert banned not in source

    def test_no_llm_symbols_in_source(self):
        # Import statements only — the docstrings intentionally document the
        # "no LLM call" invariant in plain English and legitimately contain
        # the word "LLM"/"AI", so scan for actual import/call symbols instead.
        source = inspect.getsource(svc)
        for banned in ("import anthropic", "import openai", "anthropic.", "openai."):
            assert banned not in source
