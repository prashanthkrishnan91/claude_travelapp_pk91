"""Route reorder-proposal apply service tests — AI Route Planning v1 PR C.

Governed by docs/ai/AI_ROUTE_PLANNING_V1_ADR.md (Section 9, PR C) and
Section 7 (Approval model).

Proves:
- Feature flag default False -> disabled status, no items fetched, no write.
- Rejects a day from another trip (day/trip binding mismatch), no write.
- Rejects a trip not owned by the caller, no write.
- Rejects a proposed order missing an item, no write.
- Rejects a proposed order with an extra item, no write.
- Rejects a proposed order with a duplicate item, no write.
- Rejects a stale current_order (does not match actual persisted order),
  no write.
- Writes only after every validation passes (explicit apply call).
- Preserves the item set exactly (writes touch position only, never
  add/remove).
- Only items whose position actually changed are written.
- No LLM/provider symbols reachable in the module source.
"""
from __future__ import annotations

import inspect
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

import app.services.route_reorder_proposal as svc
from app.models.route_reorder_proposal import RouteReorderApplyRequest


def _settings(enabled: bool) -> MagicMock:
    s = MagicMock()
    s.route_reorder_proposal_v1_enabled = enabled
    return s


def _item(item_id, position):
    return SimpleNamespace(id=item_id, position=position)


class _FakeItineraryService:
    """Stand-in for ItineraryService tracking list_items/update_item calls."""

    calls = []
    updates = []

    def __init__(self, db):
        self.db = db

    def list_items(self, day_id, user_id=None):
        _FakeItineraryService.calls.append((day_id, user_id))
        return _FakeItineraryService.items

    def update_item(self, item_id, payload, user_id=None):
        _FakeItineraryService.updates.append((item_id, payload.position, user_id))
        for item in _FakeItineraryService.items:
            if item.id == item_id:
                item.position = payload.position
        return SimpleNamespace(id=item_id, position=payload.position)


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


def _patch_itinerary_service(monkeypatch, items):
    _FakeItineraryService.items = items
    _FakeItineraryService.calls = []
    _FakeItineraryService.updates = []
    fake_mod = types.ModuleType("app.services.itinerary")
    fake_mod.ItineraryService = _FakeItineraryService
    monkeypatch.setitem(sys.modules, "app.services.itinerary", fake_mod)


def _owned_db(user_id, trip_id, day_id):
    return _FakeDB(
        trips=[{"id": str(trip_id), "user_id": str(user_id)}],
        days=[{"id": str(day_id), "trip_id": str(trip_id)}],
    )


# ── feature flag disabled (default) ──────────────────────────────────────────


class TestFeatureFlagDisabled:
    def test_flag_false_returns_disabled_status(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        resp = svc.apply_route_reorder_proposal(
            uuid4(), uuid4(), uuid4(), RouteReorderApplyRequest(), db=MagicMock()
        )
        assert resp.status == "disabled"
        assert resp.order == []

    def test_flag_false_does_not_import_itinerary_service(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        monkeypatch.delitem(sys.modules, "app.services.itinerary", raising=False)
        resp = svc.apply_route_reorder_proposal(
            uuid4(), uuid4(), uuid4(), RouteReorderApplyRequest(), db=MagicMock()
        )
        assert resp.status == "disabled"
        assert "app.services.itinerary" not in sys.modules


# ── ownership ─────────────────────────────────────────────────────────────────


class TestOwnership:
    def test_day_belonging_to_a_different_trip_is_rejected(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id = uuid4()
        owned_trip_id = uuid4()
        other_trip_id = uuid4()
        day_id = uuid4()
        db = _FakeDB(
            trips=[{"id": str(owned_trip_id), "user_id": str(user_id)}],
            days=[{"id": str(day_id), "trip_id": str(other_trip_id)}],
        )
        _patch_itinerary_service(monkeypatch, [])
        with pytest.raises(HTTPException):
            svc.apply_route_reorder_proposal(
                owned_trip_id, day_id, user_id, RouteReorderApplyRequest(), db=db
            )
        assert _FakeItineraryService.calls == []
        assert _FakeItineraryService.updates == []

    def test_trip_not_owned_by_user_is_rejected(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id = uuid4()
        trip_id = uuid4()
        day_id = uuid4()
        db = _FakeDB(trips=[], days=[{"id": str(day_id), "trip_id": str(trip_id)}])
        _patch_itinerary_service(monkeypatch, [])
        with pytest.raises(HTTPException):
            svc.apply_route_reorder_proposal(
                trip_id, day_id, user_id, RouteReorderApplyRequest(), db=db
            )
        assert _FakeItineraryService.calls == []
        assert _FakeItineraryService.updates == []


# ── item-set validation ───────────────────────────────────────────────────────


class TestItemSetValidation:
    def test_rejects_missing_item(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b = uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a, 0), _item(b, 1)])
        current = [str(a), str(b)]
        proposed = [str(a)]  # b missing
        resp = svc.apply_route_reorder_proposal(
            trip_id,
            day_id,
            user_id,
            RouteReorderApplyRequest(current_order=current, proposed_order=proposed),
            db=db,
        )
        assert resp.status == "rejected"
        assert resp.reason == "item_set_mismatched"
        assert _FakeItineraryService.updates == []

    def test_rejects_extra_item(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b, extra = uuid4(), uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a, 0), _item(b, 1)])
        current = [str(a), str(b)]
        proposed = [str(a), str(b), str(extra)]
        resp = svc.apply_route_reorder_proposal(
            trip_id,
            day_id,
            user_id,
            RouteReorderApplyRequest(current_order=current, proposed_order=proposed),
            db=db,
        )
        assert resp.status == "rejected"
        assert resp.reason == "item_set_mismatched"
        assert _FakeItineraryService.updates == []

    def test_rejects_duplicate_item(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b = uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a, 0), _item(b, 1)])
        current = [str(a), str(b)]
        proposed = [str(a), str(a)]  # duplicate, b dropped
        resp = svc.apply_route_reorder_proposal(
            trip_id,
            day_id,
            user_id,
            RouteReorderApplyRequest(current_order=current, proposed_order=proposed),
            db=db,
        )
        assert resp.status == "rejected"
        assert resp.reason == "item_set_mismatched"
        assert _FakeItineraryService.updates == []

    def test_rejects_cross_day_item(self, monkeypatch):
        # An item id from a different day (not present in this day's actual
        # current order) is indistinguishable from "extra item" once the
        # day-scoped current order is fetched — it must still be rejected.
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b, other_day_item = uuid4(), uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a, 0), _item(b, 1)])
        current = [str(a), str(b)]
        proposed = [str(a), str(other_day_item)]
        resp = svc.apply_route_reorder_proposal(
            trip_id,
            day_id,
            user_id,
            RouteReorderApplyRequest(current_order=current, proposed_order=proposed),
            db=db,
        )
        assert resp.status == "rejected"
        assert resp.reason == "item_set_mismatched"
        assert _FakeItineraryService.updates == []


# ── stale current_order ───────────────────────────────────────────────────────


class TestStaleCurrentOrder:
    def test_rejects_stale_current_order(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b = uuid4(), uuid4()
        # Actual persisted order is [a, b]; caller previewed [b, a] (stale).
        _patch_itinerary_service(monkeypatch, [_item(a, 0), _item(b, 1)])
        stale_current = [str(b), str(a)]
        proposed = [str(a), str(b)]
        resp = svc.apply_route_reorder_proposal(
            trip_id,
            day_id,
            user_id,
            RouteReorderApplyRequest(current_order=stale_current, proposed_order=proposed),
            db=db,
        )
        assert resp.status == "rejected"
        assert resp.reason == "stale_current_order"
        assert _FakeItineraryService.updates == []


# ── successful apply ──────────────────────────────────────────────────────────


class TestSuccessfulApply:
    def test_writes_only_after_explicit_confirmation_and_validation(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b, c = uuid4(), uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a, 0), _item(b, 1), _item(c, 2)])
        current = [str(a), str(b), str(c)]
        proposed = [str(c), str(a), str(b)]
        resp = svc.apply_route_reorder_proposal(
            trip_id,
            day_id,
            user_id,
            RouteReorderApplyRequest(current_order=current, proposed_order=proposed),
            db=db,
        )
        assert resp.status == "applied"
        assert resp.order == proposed

    def test_preserves_item_set_exactly(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b, c = uuid4(), uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a, 0), _item(b, 1), _item(c, 2)])
        current = [str(a), str(b), str(c)]
        proposed = [str(c), str(a), str(b)]
        svc.apply_route_reorder_proposal(
            trip_id,
            day_id,
            user_id,
            RouteReorderApplyRequest(current_order=current, proposed_order=proposed),
            db=db,
        )
        written_ids = {item_id for item_id, _pos, _uid in _FakeItineraryService.updates}
        assert written_ids <= {a, b, c}
        assert {item.id for item in _FakeItineraryService.items} == {a, b, c}

    def test_updates_only_position_and_only_changed_items(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b, c = uuid4(), uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a, 0), _item(b, 1), _item(c, 2)])
        current = [str(a), str(b), str(c)]
        # Only a and c swap; b stays at position 1.
        proposed = [str(c), str(b), str(a)]
        svc.apply_route_reorder_proposal(
            trip_id,
            day_id,
            user_id,
            RouteReorderApplyRequest(current_order=current, proposed_order=proposed),
            db=db,
        )
        updated_ids = {item_id for item_id, _pos, _uid in _FakeItineraryService.updates}
        assert b not in updated_ids
        assert a in updated_ids
        assert c in updated_ids
        for item_id, pos, uid in _FakeItineraryService.updates:
            assert uid == user_id

    def test_no_write_before_confirmation_call(self, monkeypatch):
        # Constructing a request object performs no write; only calling
        # apply_route_reorder_proposal can write.
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        a, b = uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a, 0), _item(b, 1)])
        RouteReorderApplyRequest(current_order=[str(a), str(b)], proposed_order=[str(b), str(a)])
        assert _FakeItineraryService.updates == []


# ── no LLM / provider symbols ──────────────────────────────────────────────────


class TestNoFabricationOrLlm:
    def test_no_llm_symbols_in_source(self):
        source = inspect.getsource(svc)
        for banned in ("import anthropic", "import openai", "anthropic.", "openai."):
            assert banned not in source

    def test_no_provider_call_symbols_in_source(self):
        source = inspect.getsource(svc)
        for banned in ("call_compute_routes", "google_routes", "httpx", "requests."):
            assert banned not in source
