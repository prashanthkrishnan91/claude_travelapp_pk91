"""Route reorder-proposal generation service tests — AI Route Planning v1.

Governed by docs/ai/AI_ROUTE_PLANNING_V1_ADR.md.

Proves:
- Both the generation flag and the apply flag must be on before any route
  or LLM call — a proposal is never actionable when apply is disabled.
- Fewer than two routeable stops -> unavailable, no route-estimate call, no
  LLM call.
- Stale current_order (does not match actual persisted order) is rejected,
  no route-estimate call, no LLM call.
- Route data unavailable for the CURRENT order -> unavailable, no LLM call.
- A changed LLM order is routed a second time before success is returned.
- The same order the LLM returned does not trigger a second route call.
- An improved proposed route returns success with provider-derived savings
  computed only from route legs, never LLM output.
- A proposed route that is equal or worse returns the unchanged current
  order with reason=current_order_already_practical.
- A proposed-route provider failure (second call) returns unavailable.
- A generated proposal missing/adding/duplicating an eligible item ID is
  rejected (fail-closed), not silently repaired.
- A movable stop cannot cross a fixed-time anchor; fixed-time stops stay in
  their exact routeable-order slot; reordering within the same segment is
  allowed.
- A generated rationale/move-reason claiming "optimal"/"perfect" is
  rejected.
- Non-movable items (wrong type, or eligible but missing coordinates) keep
  their exact original slot in the returned proposed_order.
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


def _settings(ai_enabled: bool, apply_enabled: bool = True) -> MagicMock:
    s = MagicMock()
    s.ai_route_reorder_proposal_v1_enabled = ai_enabled
    s.route_reorder_proposal_v1_enabled = apply_enabled
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


def _route_call_sequence(*responses):
    """Stateful stand-in for compute_route_estimate: returns each response
    in order, one per call, and records the item-id order each call was
    made with (so tests can assert call count / which stop order was
    routed)."""
    calls = []
    it = iter(responses)

    def _fn(request, *_a, **_k):
        calls.append([stop.item_id for stop in request.stops])
        try:
            return next(it)
        except StopIteration:
            raise AssertionError("compute_route_estimate called more times than expected")

    _fn.calls = calls
    return _fn


def _llm_response(order_ids, rationale="Groups nearby stops together.", move_reasons=None):
    import json

    payload = {"proposed_order": order_ids, "rationale": rationale}
    if move_reasons:
        payload["move_reasons"] = move_reasons
    return json.dumps(payload)


# ── feature flags ────────────────────────────────────────────────────────


class TestFeatureFlags:
    def test_generation_flag_off_returns_disabled_no_calls(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(ai_enabled=False, apply_enabled=True))
        monkeypatch.setattr(svc, "compute_route_estimate", _no_route_call)
        monkeypatch.setattr(svc, "_call_llm", _no_llm_call)
        resp = svc.generate_route_reorder_proposal(
            uuid4(), uuid4(), uuid4(), RouteReorderProposalGenerateRequest(), db=MagicMock()
        )
        assert resp.status == "disabled"
        assert resp.proposed_order == []

    def test_apply_flag_off_returns_disabled_before_any_route_or_llm_call(self, monkeypatch):
        # Generation flag on, apply flag off — a proposal would be
        # unactionable, so generation must fail closed before doing any
        # expensive work.
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(ai_enabled=True, apply_enabled=False))
        monkeypatch.setattr(svc, "compute_route_estimate", _no_route_call)
        monkeypatch.setattr(svc, "_call_llm", _no_llm_call)
        _patch_itinerary_service(monkeypatch, [])
        resp = svc.generate_route_reorder_proposal(
            uuid4(), uuid4(), uuid4(), RouteReorderProposalGenerateRequest(), db=MagicMock()
        )
        assert resp.status == "disabled"
        assert _FakeItineraryService.calls == []

    def test_both_flags_off_returns_disabled(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(ai_enabled=False, apply_enabled=False))
        monkeypatch.setattr(svc, "compute_route_estimate", _no_route_call)
        monkeypatch.setattr(svc, "_call_llm", _no_llm_call)
        resp = svc.generate_route_reorder_proposal(
            uuid4(), uuid4(), uuid4(), RouteReorderProposalGenerateRequest(), db=MagicMock()
        )
        assert resp.status == "disabled"


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


# ── route data unavailable (current order) ────────────────────────────────


class TestCurrentRouteDataUnavailable:
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


# ── structural generation validation ──────────────────────────────────────


class TestGenerationValidation:
    def _base(self, monkeypatch, route_fn=None):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b = uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a), _item(b)])
        fn = route_fn or _route_call_sequence(_success_route_response([_leg(str(a), str(b))]))
        monkeypatch.setattr(svc, "compute_route_estimate", fn)
        return user_id, trip_id, day_id, db, a, b

    def test_rejects_generation_missing_an_id(self, monkeypatch):
        user_id, trip_id, day_id, db, a, b = self._base(monkeypatch)
        monkeypatch.setattr(svc, "_call_llm", lambda *_a, **_k: _llm_response([str(a)]))
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]), db=db,
        )
        assert resp.status == "unavailable"
        assert resp.reason == "generation_invalid"

    def test_rejects_generation_with_duplicate_id(self, monkeypatch):
        user_id, trip_id, day_id, db, a, b = self._base(monkeypatch)
        monkeypatch.setattr(svc, "_call_llm", lambda *_a, **_k: _llm_response([str(a), str(a)]))
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]), db=db,
        )
        assert resp.status == "unavailable"
        assert resp.reason == "generation_invalid"

    def test_rejects_generation_with_foreign_id(self, monkeypatch):
        user_id, trip_id, day_id, db, a, b = self._base(monkeypatch)
        foreign = str(uuid4())
        monkeypatch.setattr(svc, "_call_llm", lambda *_a, **_k: _llm_response([str(a), foreign]))
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
            lambda *_a, **_k: _llm_response([str(b), str(a)], rationale="This is the optimal order."),
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


# ── route verification of a changed order ─────────────────────────────────


class TestRouteVerification:
    def test_changed_order_is_routed_a_second_time_before_success(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b = uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a), _item(b)])
        # Current order: 1800s/6000m. Proposed (swapped) order: 900s/3000m —
        # clears the duration-improvement bar.
        route_fn = _route_call_sequence(
            _success_route_response([_leg(str(a), str(b), duration=1800, distance=6000)]),
            _success_route_response([_leg(str(b), str(a), duration=900, distance=3000)]),
        )
        monkeypatch.setattr(svc, "compute_route_estimate", route_fn)
        monkeypatch.setattr(svc, "_call_llm", lambda *_a, **_k: _llm_response([str(b), str(a)]))
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]), db=db,
        )
        assert len(route_fn.calls) == 2
        assert route_fn.calls[0] == [str(a), str(b)]
        assert route_fn.calls[1] == [str(b), str(a)]
        assert resp.status == "success"
        assert resp.reason == "proposal_generated"

    def test_improved_route_returns_success_with_provider_derived_savings(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b = uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a), _item(b)])
        route_fn = _route_call_sequence(
            _success_route_response([_leg(str(a), str(b), duration=1800, distance=6000)]),
            _success_route_response([_leg(str(b), str(a), duration=900, distance=3000)]),
        )
        monkeypatch.setattr(svc, "compute_route_estimate", route_fn)
        monkeypatch.setattr(svc, "_call_llm", lambda *_a, **_k: _llm_response([str(b), str(a)]))
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]), db=db,
        )
        assert resp.status == "success"
        assert resp.proposed_order == [str(b), str(a)]
        assert resp.current_duration_seconds == 1800
        assert resp.proposed_duration_seconds == 900
        assert resp.estimated_savings_seconds == 900
        assert resp.current_distance_meters == 6000
        assert resp.proposed_distance_meters == 3000
        assert resp.estimated_distance_savings_meters == 3000

    def test_equal_or_worse_route_returns_unchanged_current_order(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b = uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a), _item(b)])
        # Proposed order is slightly worse — must not be surfaced as a change.
        route_fn = _route_call_sequence(
            _success_route_response([_leg(str(a), str(b), duration=1800, distance=6000)]),
            _success_route_response([_leg(str(b), str(a), duration=1850, distance=6100)]),
        )
        monkeypatch.setattr(svc, "compute_route_estimate", route_fn)
        monkeypatch.setattr(svc, "_call_llm", lambda *_a, **_k: _llm_response([str(b), str(a)]))
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]), db=db,
        )
        assert resp.status == "success"
        assert resp.reason == "current_order_already_practical"
        assert resp.proposed_order == resp.current_order == [str(a), str(b)]
        assert len(route_fn.calls) == 2

    def test_minor_improvement_below_threshold_returns_unchanged_current_order(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b = uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a), _item(b)])
        # 1800s -> 1750s: 50s savings, below min(300s, 10% of 1800=180s)=180s
        # threshold, and distance savings are also below the 1km/10% bar.
        route_fn = _route_call_sequence(
            _success_route_response([_leg(str(a), str(b), duration=1800, distance=6000)]),
            _success_route_response([_leg(str(b), str(a), duration=1750, distance=5950)]),
        )
        monkeypatch.setattr(svc, "compute_route_estimate", route_fn)
        monkeypatch.setattr(svc, "_call_llm", lambda *_a, **_k: _llm_response([str(b), str(a)]))
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]), db=db,
        )
        assert resp.status == "success"
        assert resp.reason == "current_order_already_practical"

    def test_similar_duration_but_material_distance_improvement_is_accepted(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b = uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a), _item(b)])
        # Duration within 2 min (1800 -> 1810), distance improves by 1.5km
        # (>= min(1km, 10% of 6000m=600m) threshold).
        route_fn = _route_call_sequence(
            _success_route_response([_leg(str(a), str(b), duration=1800, distance=6000)]),
            _success_route_response([_leg(str(b), str(a), duration=1810, distance=4500)]),
        )
        monkeypatch.setattr(svc, "compute_route_estimate", route_fn)
        monkeypatch.setattr(svc, "_call_llm", lambda *_a, **_k: _llm_response([str(b), str(a)]))
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]), db=db,
        )
        assert resp.status == "success"
        assert resp.reason == "proposal_generated"
        assert resp.estimated_distance_savings_meters == 1500

    def test_worse_duration_is_never_accepted_even_if_distance_improves(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b = uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a), _item(b)])
        # Duration materially worse (1800 -> 2400, +600s, outside the 2min
        # similarity window) even though distance improved a lot.
        route_fn = _route_call_sequence(
            _success_route_response([_leg(str(a), str(b), duration=1800, distance=6000)]),
            _success_route_response([_leg(str(b), str(a), duration=2400, distance=1000)]),
        )
        monkeypatch.setattr(svc, "compute_route_estimate", route_fn)
        monkeypatch.setattr(svc, "_call_llm", lambda *_a, **_k: _llm_response([str(b), str(a)]))
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]), db=db,
        )
        assert resp.status == "success"
        assert resp.reason == "current_order_already_practical"

    def test_proposed_route_provider_failure_is_unavailable(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b = uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a), _item(b)])
        route_fn = _route_call_sequence(
            _success_route_response([_leg(str(a), str(b), duration=1800, distance=6000)]),
            SimpleNamespace(status="provider_error", estimates=[]),
        )
        monkeypatch.setattr(svc, "compute_route_estimate", route_fn)
        monkeypatch.setattr(svc, "_call_llm", lambda *_a, **_k: _llm_response([str(b), str(a)]))
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]), db=db,
        )
        assert resp.status == "unavailable"
        assert resp.reason == "route_data_unavailable"
        assert resp.proposed_order == []

    def test_same_order_from_llm_does_not_trigger_second_route_call(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b = uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a), _item(b)])
        route_fn = _route_call_sequence(
            _success_route_response([_leg(str(a), str(b), duration=1800, distance=6000)]),
        )
        monkeypatch.setattr(svc, "compute_route_estimate", route_fn)
        monkeypatch.setattr(svc, "_call_llm", lambda *_a, **_k: _llm_response([str(a), str(b)]))
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b)]), db=db,
        )
        assert len(route_fn.calls) == 1
        assert resp.status == "success"
        assert resp.reason == "current_order_already_practical"
        assert resp.proposed_order == resp.current_order == [str(a), str(b)]


# ── fixed-time anchors and segments ───────────────────────────────────────


class TestFixedTimeAnchors:
    def _three_stop_day(self, monkeypatch, a, b, c, a_time=None, b_time=None, c_time=None):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        _patch_itinerary_service(
            monkeypatch,
            [
                _item(a, start_time=a_time),
                _item(b, start_time=b_time),
                _item(c, start_time=c_time),
            ],
        )
        return user_id, trip_id, day_id, db

    def test_movable_stop_cannot_cross_a_fixed_time_anchor(self, monkeypatch):
        a, b, c = uuid4(), uuid4(), uuid4()
        anchor_time = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
        # b is a fixed anchor between untimed a and untimed c.
        user_id, trip_id, day_id, db = self._three_stop_day(monkeypatch, a, b, c, b_time=anchor_time)
        route_fn = _route_call_sequence(
            _success_route_response([_leg(str(a), str(b)), _leg(str(b), str(c))]),
        )
        monkeypatch.setattr(svc, "compute_route_estimate", route_fn)
        # Model tries to move c before the b anchor — a segment-crossing move.
        monkeypatch.setattr(svc, "_call_llm", lambda *_a, **_k: _llm_response([str(c), str(a), str(b)]))
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b), str(c)]), db=db,
        )
        assert resp.status == "unavailable"
        assert resp.reason == "fixed_time_anchor_violated"
        assert len(route_fn.calls) == 1  # only the current-order call

    def test_fixed_time_stop_cannot_move_from_its_slot(self, monkeypatch):
        a, b, c = uuid4(), uuid4(), uuid4()
        anchor_time = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
        user_id, trip_id, day_id, db = self._three_stop_day(monkeypatch, a, b, c, b_time=anchor_time)
        route_fn = _route_call_sequence(
            _success_route_response([_leg(str(a), str(b)), _leg(str(b), str(c))]),
        )
        monkeypatch.setattr(svc, "compute_route_estimate", route_fn)
        # Model moves the anchor b itself out of its slot.
        monkeypatch.setattr(svc, "_call_llm", lambda *_a, **_k: _llm_response([str(b), str(a), str(c)]))
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b), str(c)]), db=db,
        )
        assert resp.status == "unavailable"
        assert resp.reason == "fixed_time_anchor_violated"

    def test_reordering_within_the_same_segment_is_allowed(self, monkeypatch):
        a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
        anchor_time = datetime(2026, 7, 10, 18, 0, tzinfo=timezone.utc)
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        # a, b untimed (segment before anchor); c anchor; d untimed (segment after).
        _patch_itinerary_service(
            monkeypatch,
            [_item(a), _item(b), _item(c, start_time=anchor_time), _item(d)],
        )
        route_fn = _route_call_sequence(
            _success_route_response(
                [_leg(str(a), str(b), duration=1800, distance=6000), _leg(str(b), str(c)), _leg(str(c), str(d))]
            ),
            _success_route_response(
                [_leg(str(b), str(a), duration=900, distance=3000), _leg(str(a), str(c)), _leg(str(c), str(d))]
            ),
        )
        monkeypatch.setattr(svc, "compute_route_estimate", route_fn)
        # Swap a/b (same pre-anchor segment); c and d stay put.
        monkeypatch.setattr(
            svc, "_call_llm", lambda *_a, **_k: _llm_response([str(b), str(a), str(c), str(d)])
        )
        resp = svc.generate_route_reorder_proposal(
            trip_id, day_id, user_id,
            RouteReorderProposalGenerateRequest(current_order=[str(a), str(b), str(c), str(d)]), db=db,
        )
        assert resp.status == "success"
        assert resp.reason == "proposal_generated"
        assert resp.proposed_order == [str(b), str(a), str(c), str(d)]
        assert len(route_fn.calls) == 2


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
        route_fn = _route_call_sequence(
            _success_route_response([_leg(str(a), str(b), duration=1800, distance=6000)]),
            _success_route_response([_leg(str(b), str(a), duration=900, distance=3000)]),
        )
        monkeypatch.setattr(svc, "compute_route_estimate", route_fn)
        monkeypatch.setattr(svc, "_call_llm", lambda *_a, **_k: _llm_response([str(b), str(a)]))
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

    def test_no_matrix_or_new_provider_symbols_in_source(self):
        source = inspect.getsource(svc)
        for banned in ("ComputeRouteMatrix", "openai", "openai.", "import googlemaps"):
            assert banned not in source
