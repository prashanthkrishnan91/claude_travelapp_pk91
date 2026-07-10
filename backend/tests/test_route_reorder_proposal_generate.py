"""Route reorder-proposal generation service tests — AI Route Planning v1.

Governed by docs/ai/AI_ROUTE_PLANNING_V1_ADR.md.

Proves:
- Feature flag default False -> disabled status, no items fetched.
- Fewer than two routeable stops -> unavailable, no route-estimate call, no
  LLM call.
- Stale current_order (does not match actual persisted order) is rejected,
  no route-estimate call, no LLM call.
- Route data unavailable -> unavailable, no LLM call.
- A generated proposal missing/adding/duplicating an eligible item ID is
  rejected (fail-closed), not silently repaired.
- A generated proposal that violates the relative order of two fixed-time
  (start_time) stops is rejected.
- A generated rationale/move-reason claiming "optimal"/"perfect" is
  rejected.
- Non-movable items (wrong type, or eligible but missing coordinates) keep
  their exact original slot in the returned proposed_order.
- A valid generation returns success with the full day's item set preserved
  in proposed_order.
- This module never calls itinerary.update_item — generation never writes.
"""
from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

import app.services.route_reorder_proposal_generate as svc
from app.models.route_reorder_proposal import RouteReorderProposalGenerateRequest


def _settings(enabled: bool) -> MagicMock:
    s = MagicMock()
    s.ai_route_reorder_proposal_v1_enabled = enabled
    return s


def _item(item_id, item_type="activity", lat=1.0, lng=2.0, title="Stop", start_time=None):
    details = {} if lat is None else {"lat": lat, "lng": lng}
    return SimpleNamespace(
        id=item_id,
        item_type=item_type,
        title=title,
        details=details,
        start_time=start_time,
    )


class _FakeItineraryService:
    calls = []
    updates = []

    def __init__(self, db):
        self.db = db

    def list_items(self, day_id, user_id=None):
        _FakeItineraryService.calls.append((day_id, user_id))
        return _FakeItineraryService.items

    def update_item(self, item_id, payload, user_id=None):
        _FakeItineraryService.updates.append((item_id, payload, user_id))
        raise AssertionError("generation must never write")


def _patch_itinerary_service(monkeypatch, items):
    import sys
    import types

    _FakeItineraryService.items = items
    _FakeItineraryService.calls = []
    _FakeItineraryService.updates = []
    fake_mod = types.ModuleType("app.services.itinerary")
    fake_mod.ItineraryService = _FakeItineraryService
    monkeypatch.setitem(sys.modules, "app.services.itinerary", fake_mod)


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
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
    def __init__(self, trips=(), days=()):
        self._trips = list(trips)
        self._days = list(days)

    def table(self, name):
        if name == "trips":
            return _FakeQuery(self._trips)
        if name == "itinerary_days":
            return _FakeQuery(self._days)
        raise AssertionError(f"unexpected table: {name}")


def _owned_db(user_id, trip_id, day_id):
    return _FakeDB(
        trips=[{"id": str(trip_id), "user_id": str(user_id)}],
        days=[{"id": str(day_id), "trip_id": str(trip_id)}],
    )


def _success_route_response(estimates):
    return SimpleNamespace(status="success", estimates=estimates)


def _leg(from_id, to_id, duration=600, distance=2000):
    return {
        "from_item_id": from_id,
        "to_item_id": to_id,
        "duration_seconds": duration,
        "distance_meters": distance,
    }


def _no_route_call(*_a, **_k):
    raise AssertionError("route-estimate must not be called")


def _no_llm_call(*_a, **_k):
    raise AssertionError("LLM must not be called")


# ── feature flag disabled ─────────────────────────────────────────────────


class TestFeatureFlagDisabled:
    def test_flag_false_returns_disabled_status(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        resp = svc.generate_route_reorder_proposal(
            uuid4(), uuid4(), uuid4(), RouteReorderProposalGenerateRequest(), db=MagicMock()
        )
        assert resp.status == "disabled"
        assert resp.proposed_order == []


# ── insufficient stops ────────────────────────────────────────────────────


class TestInsufficientStops:
    def test_fewer_than_two_routeable_stops_is_unavailable_no_calls(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        monkeypatch.setattr(svc, "compute_route_estimate", _no_route_call)
        monkeypatch.setattr(svc, "_call_llm", _no_llm_call)
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a = uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a)])
        resp = svc.generate_route_reorder_proposal(
            trip_id,
            day_id,
            user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a)]),
            db=db,
        )
        assert resp.status == "unavailable"
        assert resp.reason == "insufficient_stops"
        assert resp.proposed_order == []

    def test_one_located_stop_plus_one_unlocated_is_insufficient(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        monkeypatch.setattr(svc, "compute_route_estimate", _no_route_call)
        monkeypatch.setattr(svc, "_call_llm", _no_llm_call)
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b = uuid4(), uuid4()
        _patch_itinerary_service(
            monkeypatch, [_item(a), _item(b, lat=None, lng=None)]
        )
        resp = svc.generate_route_reorder_proposal(
            trip_id,
            day_id,
            user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]),
            db=db,
        )
        assert resp.status == "unavailable"
        assert resp.reason == "insufficient_stops"


# ── stale current_order ───────────────────────────────────────────────────


class TestStaleCurrentOrder:
    def test_stale_current_order_rejected_before_any_route_or_llm_call(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        monkeypatch.setattr(svc, "compute_route_estimate", _no_route_call)
        monkeypatch.setattr(svc, "_call_llm", _no_llm_call)
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b = uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a), _item(b)])
        resp = svc.generate_route_reorder_proposal(
            trip_id,
            day_id,
            user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(b), str(a)]),
            db=db,
        )
        assert resp.status == "unavailable"
        assert resp.reason == "stale_current_order"


# ── ownership ──────────────────────────────────────────────────────────────


class TestOwnership:
    def test_trip_not_owned_is_rejected(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _FakeDB(trips=[], days=[{"id": str(day_id), "trip_id": str(trip_id)}])
        _patch_itinerary_service(monkeypatch, [])
        with pytest.raises(HTTPException):
            svc.generate_route_reorder_proposal(
                trip_id, day_id, user_id, RouteReorderProposalGenerateRequest(), db=db
            )
        assert _FakeItineraryService.calls == []


# ── route data unavailable ────────────────────────────────────────────────


class TestRouteDataUnavailable:
    def test_route_estimate_failure_is_unavailable_no_llm_call(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        monkeypatch.setattr(
            svc, "compute_route_estimate", lambda *a, **k: SimpleNamespace(status="provider_error", estimates=[])
        )
        monkeypatch.setattr(svc, "_call_llm", _no_llm_call)
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b = uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a), _item(b)])
        resp = svc.generate_route_reorder_proposal(
            trip_id,
            day_id,
            user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]),
            db=db,
        )
        assert resp.status == "unavailable"
        assert resp.reason == "route_data_unavailable"


# ── generation validation ─────────────────────────────────────────────────


class TestGenerationValidation:
    def _base(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b = uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a), _item(b)])
        monkeypatch.setattr(
            svc,
            "compute_route_estimate",
            lambda *a2, **k: _success_route_response([_leg(str(a), str(b))]),
        )
        return user_id, trip_id, day_id, db, a, b

    def test_rejects_generation_missing_an_id(self, monkeypatch):
        user_id, trip_id, day_id, db, a, b = self._base(monkeypatch)
        monkeypatch.setattr(
            svc,
            "_call_llm",
            lambda *_a, **_k: '{"proposed_order": ["%s"], "rationale": "Shorter walk."}' % str(a),
        )
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]), db=db,
        )
        assert resp.status == "unavailable"
        assert resp.reason == "generation_invalid"

    def test_rejects_generation_with_duplicate_id(self, monkeypatch):
        user_id, trip_id, day_id, db, a, b = self._base(monkeypatch)
        monkeypatch.setattr(
            svc,
            "_call_llm",
            lambda *_a, **_k: '{"proposed_order": ["%s", "%s"], "rationale": "Shorter walk."}'
            % (str(a), str(a)),
        )
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]), db=db,
        )
        assert resp.status == "unavailable"
        assert resp.reason == "generation_invalid"

    def test_rejects_generation_with_foreign_id(self, monkeypatch):
        user_id, trip_id, day_id, db, a, b = self._base(monkeypatch)
        foreign = str(uuid4())
        monkeypatch.setattr(
            svc,
            "_call_llm",
            lambda *_a, **_k: '{"proposed_order": ["%s", "%s"], "rationale": "Shorter walk."}'
            % (str(a), foreign),
        )
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]), db=db,
        )
        assert resp.status == "unavailable"
        assert resp.reason == "generation_invalid"

    def test_rejects_rationale_claiming_optimality(self, monkeypatch):
        user_id, trip_id, day_id, db, a, b = self._base(monkeypatch)
        monkeypatch.setattr(
            svc,
            "_call_llm",
            lambda *_a, **_k: '{"proposed_order": ["%s", "%s"], "rationale": "This is the optimal order."}'
            % (str(b), str(a)),
        )
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]), db=db,
        )
        assert resp.status == "unavailable"
        assert resp.reason == "generation_invalid"

    def test_rejects_llm_unavailable(self, monkeypatch):
        user_id, trip_id, day_id, db, a, b = self._base(monkeypatch)
        monkeypatch.setattr(svc, "_call_llm", lambda *_a, **_k: None)
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]), db=db,
        )
        assert resp.status == "unavailable"
        assert resp.reason == "llm_unavailable"

    def test_accepts_valid_generation(self, monkeypatch):
        user_id, trip_id, day_id, db, a, b = self._base(monkeypatch)
        monkeypatch.setattr(
            svc,
            "_call_llm",
            lambda *_a, **_k: '{"proposed_order": ["%s", "%s"], "rationale": "Groups nearby stops together.", "move_reasons": {"%s": "Closer to the next stop"}}'
            % (str(b), str(a), str(b)),
        )
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]), db=db,
        )
        assert resp.status == "success"
        assert resp.current_order == [str(a), str(b)]
        assert resp.proposed_order == [str(b), str(a)]
        assert resp.rationale == "Groups nearby stops together."
        assert resp.move_reasons == {str(b): "Closer to the next stop"}


# ── fixed-time constraint ─────────────────────────────────────────────────


class TestFixedTimeConstraint:
    def test_rejects_proposal_that_violates_fixed_time_order(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b = uuid4(), uuid4()
        early = datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc)
        late = early + timedelta(hours=3)
        # a has an earlier fixed time than b.
        _patch_itinerary_service(
            monkeypatch, [_item(a, start_time=early), _item(b, start_time=late)]
        )
        monkeypatch.setattr(
            svc,
            "compute_route_estimate",
            lambda *a2, **k: _success_route_response([_leg(str(a), str(b))]),
        )
        # Model proposes b before a — violates fixed chronological order.
        monkeypatch.setattr(
            svc,
            "_call_llm",
            lambda *_a, **_k: '{"proposed_order": ["%s", "%s"], "rationale": "Reordered for convenience."}'
            % (str(b), str(a)),
        )
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]), db=db,
        )
        assert resp.status == "unavailable"
        assert resp.reason == "generation_invalid"


# ── non-movable items keep their exact slot ───────────────────────────────


class TestNonMovableItemsPreserved:
    def test_flight_and_unlocated_stop_keep_original_positions(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        flight, a, unlocated, b = uuid4(), uuid4(), uuid4(), uuid4()
        _patch_itinerary_service(
            monkeypatch,
            [
                _item(flight, item_type="flight"),
                _item(a),
                _item(unlocated, lat=None, lng=None),
                _item(b),
            ],
        )
        monkeypatch.setattr(
            svc,
            "compute_route_estimate",
            lambda *a2, **k: _success_route_response([_leg(str(a), str(b))]),
        )
        monkeypatch.setattr(
            svc,
            "_call_llm",
            lambda *_a, **_k: '{"proposed_order": ["%s", "%s"], "rationale": "Groups nearby stops together."}'
            % (str(b), str(a)),
        )
        current = [str(flight), str(a), str(unlocated), str(b)]
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=current), db=db,
        )
        assert resp.status == "success"
        # flight (index 0) and unlocated (index 2) keep their exact slots;
        # only the movable a/b pair (indices 1, 3) is reordered.
        assert resp.proposed_order == [str(flight), str(b), str(unlocated), str(a)]
        assert set(resp.proposed_order) == set(current)


# ── no writes ──────────────────────────────────────────────────────────────


class TestNoWrites:
    def test_module_never_calls_update_item(self):
        source = inspect.getsource(svc)
        assert "update_item(" not in source
