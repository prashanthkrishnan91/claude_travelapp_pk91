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
    """Stand-in for ItineraryService tracking list_items/update_item calls.

    ``fail_on_calls`` is a set of 1-indexed ``update_item`` call numbers that
    should raise, simulating a mid-apply write failure (e.g. a DB outage
    partway through the sequence of per-item PATCHes) — and, when it
    includes a call number that falls during rollback, a failing rollback
    write too.
    """

    calls = []
    updates = []
    fail_on_calls = frozenset()

    def __init__(self, db):
        self.db = db

    def list_items(self, day_id, user_id=None):
        _FakeItineraryService.calls.append((day_id, user_id))
        return _FakeItineraryService.items

    def update_item(self, item_id, payload, user_id=None):
        _FakeItineraryService.updates.append((item_id, payload.position, user_id))
        call_number = len(_FakeItineraryService.updates)
        if call_number in _FakeItineraryService.fail_on_calls:
            raise RuntimeError("simulated DB write failure")
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


def _patch_itinerary_service(monkeypatch, items, fail_on_calls=frozenset()):
    _FakeItineraryService.items = items
    _FakeItineraryService.calls = []
    _FakeItineraryService.updates = []
    _FakeItineraryService.fail_on_calls = fail_on_calls
    fake_mod = types.ModuleType("app.services.itinerary")
    fake_mod.ItineraryService = _FakeItineraryService
    monkeypatch.setitem(sys.modules, "app.services.itinerary", fake_mod)


def _owned_db(user_id, trip_id, day_id):
    return _FakeDB(
        trips=[{"id": str(trip_id), "user_id": str(user_id)}],
        days=[{"id": str(day_id), "trip_id": str(trip_id)}],
    )


class _StatusCodeHTTPException(Exception):
    """Local stand-in for fastapi.HTTPException that actually carries
    ``status_code``/``detail`` as instance attributes.

    ``tests/conftest.py`` stubs ``fastapi.HTTPException`` with a no-op
    ``__init__`` (for lightweight collection without the full fastapi
    stack), so ``svc``'s module-level ``HTTPException`` name does not carry
    a real ``status_code``. Tests that need to assert the actual status
    code monkeypatch ``svc.HTTPException`` to this class instead.
    """

    def __init__(self, status_code: int = 400, detail=None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


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


# ── partial-write / mid-apply failure ────────────────────────────────────────


class TestPartialWriteRollback:
    def test_mid_apply_failure_rolls_back_already_applied_items(self, monkeypatch):
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        monkeypatch.setattr(svc, "HTTPException", _StatusCodeHTTPException)
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b, c = uuid4(), uuid4(), uuid4()
        # Full rotation: a(0)->1, b(1)->2, c(2)->0 — every item's write call
        # fails on the 2nd update (the write for `a`), after `c`'s write
        # already succeeded.
        _patch_itinerary_service(
            monkeypatch, [_item(a, 0), _item(b, 1), _item(c, 2)], fail_on_calls={2}
        )
        current = [str(a), str(b), str(c)]
        proposed = [str(c), str(a), str(b)]
        with pytest.raises(_StatusCodeHTTPException) as exc_info:
            svc.apply_route_reorder_proposal(
                trip_id,
                day_id,
                user_id,
                RouteReorderApplyRequest(current_order=current, proposed_order=proposed),
                db=db,
            )
        assert exc_info.value.status_code == 502

        # Original positions are restored — no partial reorder survives.
        positions = {item.id: item.position for item in _FakeItineraryService.items}
        assert positions == {a: 0, b: 1, c: 2}

        # Call 1 applied c->0; call 2 (a->1) raised; call 3 is the rollback
        # of c back to its original position 2.
        assert len(_FakeItineraryService.updates) == 3
        assert _FakeItineraryService.updates[0] == (c, 0, user_id)
        assert _FakeItineraryService.updates[1] == (a, 1, user_id)
        assert _FakeItineraryService.updates[2] == (c, 2, user_id)

    def test_no_success_response_returned_on_mid_apply_failure(self, monkeypatch):
        # The function must never return a RouteReorderApplyResponse (with
        # status="applied" or otherwise) when a write in the sequence
        # failed — it must raise instead. pytest.raises below is itself the
        # proof: if apply_route_reorder_proposal returned anything, this
        # test would fail with "DID NOT RAISE".
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b = uuid4(), uuid4()
        _patch_itinerary_service(monkeypatch, [_item(a, 0), _item(b, 1)], fail_on_calls={1})
        current = [str(a), str(b)]
        proposed = [str(b), str(a)]
        with pytest.raises(HTTPException):
            svc.apply_route_reorder_proposal(
                trip_id,
                day_id,
                user_id,
                RouteReorderApplyRequest(current_order=current, proposed_order=proposed),
                db=db,
            )

    def test_rollback_write_failure_is_logged_and_still_fails_closed(self, monkeypatch):
        # If the rollback write itself fails (e.g. the same outage that
        # caused the original failure), the operation must still raise a
        # fail-closed error rather than silently succeeding or hanging.
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        user_id, trip_id, day_id = uuid4(), uuid4(), uuid4()
        db = _owned_db(user_id, trip_id, day_id)
        a, b, c = uuid4(), uuid4(), uuid4()
        # Call 2 (a's write) fails, triggering rollback of c (call 3), which
        # also fails.
        monkeypatch.setattr(svc, "HTTPException", _StatusCodeHTTPException)
        _patch_itinerary_service(
            monkeypatch, [_item(a, 0), _item(b, 1), _item(c, 2)], fail_on_calls={2, 3}
        )
        current = [str(a), str(b), str(c)]
        proposed = [str(c), str(a), str(b)]
        with pytest.raises(_StatusCodeHTTPException) as exc_info:
            svc.apply_route_reorder_proposal(
                trip_id,
                day_id,
                user_id,
                RouteReorderApplyRequest(current_order=current, proposed_order=proposed),
                db=db,
            )
        assert exc_info.value.status_code == 502
        # Rollback was attempted (recorded) even though it failed.
        assert len(_FakeItineraryService.updates) == 3
        assert _FakeItineraryService.updates[2] == (c, 2, user_id)


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
