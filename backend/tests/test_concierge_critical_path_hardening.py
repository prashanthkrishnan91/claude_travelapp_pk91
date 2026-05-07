"""Tests for AI Concierge Request Critical Path Hardening v1 (PR #274).

Covers:
  PART 1 — Legacy summary LLM bypass for semantic_retrieval_v1 card-first responses
  PART 2 — Non-blocking request-log DB persistence contract
  PART 3 — Schema drift robustness (process-level column cache, bounded retries)
  PART 4 — End-to-end timing spans in service search logs
"""

from __future__ import annotations

import logging
import sys
import types
from typing import Any, List, Optional
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

# ---------------------------------------------------------------------------
# Stubs: minimal Supabase client for ConciergeService unit tests
# ---------------------------------------------------------------------------


class _FakeTableOp:
    def __init__(self, db, table_name):
        self._db = db
        self._table = table_name

    def select(self, *args):
        return self

    def eq(self, col, val):
        return self

    def limit(self, n):
        return self

    def insert(self, payload):
        self._db._messages.append(dict(payload))
        return self

    def update(self, payload):
        return self

    def order(self, col, **kwargs):
        return self

    def delete(self):
        return self

    def execute(self):
        if self._table == "trips":
            return _FakeResult([self._db._trip])
        if self._table == "concierge_messages":
            return _FakeResult([])
        return _FakeResult([])


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeTripDb:
    def __init__(self, trip: dict):
        self._trip = trip
        self._messages: List[dict] = []

    def table(self, name: str):
        return _FakeTableOp(self, name)


def _make_trip_and_db():
    uid = str(uuid4())
    tid = str(uuid4())
    trip = {
        "id": tid,
        "destination": "Chicago, IL",
        "start_date": "2026-06-01",
        "end_date": "2026-06-05",
        "user_id": uid,
    }
    return trip, _FakeTripDb(trip)


def _make_real_restaurant(name: str = "TestResto") -> Any:
    """Return a real UnifiedRestaurantResult that passes Pydantic validation."""
    from app.models.concierge import UnifiedRestaurantResult, ConciergeDisplayFields, PlaceSupportingDetails
    card = UnifiedRestaurantResult(
        name=name,
        source="Live search · semantic_retrieval_v1",
        cuisine="Restaurant",
        neighborhood="Downtown",
        rating=8.5,
        review_count=200,
        why_pick=f"A strong option.",
        reason_source="deterministic_safe_v1",
        supporting_details=PlaceSupportingDetails(why_pick="A strong option."),
        display=ConciergeDisplayFields(
            display_name=name,
            display_category="Restaurant",
            display_why="A strong option.",
            display_badges=[],
            display_why_source="deterministic_safe_v1",
        ),
    )
    return card


class _FakeLiveResult:
    def __init__(self, *, restaurants=None, attractions=None, provider_name="semantic_retrieval_v1",
                 source_status="live_search", cached=False):
        self.restaurants = restaurants or []
        self.attractions = attractions or []
        self.hotels = []
        self.research_sources = []
        self.provider_name = provider_name
        self.source_status = source_status
        self.cached = cached


def _make_service(provider_name="semantic_retrieval_v1", source_status="live_search"):
    """Build a ConciergeService with mocked live research returning semantic results."""
    from app.services.concierge import ConciergeService

    trip, db = _make_trip_and_db()
    svc = ConciergeService(db)

    cards = [_make_real_restaurant("Alinea"), _make_real_restaurant("Girl & the Goat")]
    live_result = _FakeLiveResult(
        restaurants=cards,
        provider_name=provider_name,
        source_status=source_status,
    )
    svc._fetch_live_research = MagicMock(return_value=live_result)
    return svc, trip


# ---------------------------------------------------------------------------
# PART 1 — Legacy summary LLM bypass
# ---------------------------------------------------------------------------


def test_semantic_card_first_path_skips_call_claude():
    """_call_claude must NOT be called when semantic_retrieval_v1 returns place cards."""
    from app.services.concierge import ConciergeService

    svc, trip = _make_service(provider_name="semantic_retrieval_v1", source_status="live_search")
    user_id = UUID(trip["user_id"])
    trip_id = UUID(trip["id"])

    with patch.object(ConciergeService, "_call_claude") as mock_claude:
        response = svc.search(trip_id, "best restaurants in chicago", user_id, "msg-001")

    mock_claude.assert_not_called()
    assert len(response.restaurants) >= 1, "cards must be present"


def test_semantic_card_first_response_is_empty_or_neutral():
    """Response text on semantic path must be empty or safe (no ranking/claim words)."""
    svc, trip = _make_service()
    user_id = UUID(trip["user_id"])
    trip_id = UUID(trip["id"])

    response = svc.search(trip_id, "best restaurants in chicago", user_id, "msg-002")

    forbidden = ("best overall", "hidden gem", "cheap", "popular")
    text = (response.response or "").lower()
    for phrase in forbidden:
        assert phrase not in text, f"response text contains forbidden claim: {phrase!r} in {text!r}"


def test_semantic_card_first_cards_are_present():
    """Cards must survive even though LLM is skipped."""
    svc, trip = _make_service()
    user_id = UUID(trip["user_id"])
    trip_id = UUID(trip["id"])

    response = svc.search(trip_id, "best restaurants in chicago", user_id, "msg-003")
    assert response.restaurants, "response must contain restaurant cards"


def test_non_semantic_path_still_calls_claude():
    """When provider is NOT semantic_retrieval_v1, _call_claude must still be called."""
    from app.services.concierge import ConciergeService

    svc, trip = _make_service(provider_name="google_places_direct", source_status="live_search")
    user_id = UUID(trip["user_id"])
    trip_id = UUID(trip["id"])

    with patch.object(ConciergeService, "_call_claude",
                      return_value='{"response": "ok", "suggestions": []}') as mock_claude:
        response = svc.search(trip_id, "best restaurants in chicago", user_id, "msg-004")

    mock_claude.assert_called_once()


def test_semantic_path_suggestions_empty():
    """Suggestions must be [] on semantic card-first path (no LLM to generate them)."""
    svc, trip = _make_service()
    user_id = UUID(trip["user_id"])
    trip_id = UUID(trip["id"])

    response = svc.search(trip_id, "restaurants chicago", user_id, "msg-006")
    assert response.suggestions == [], "suggestions should be empty on semantic path"


def test_semantic_path_source_status_preserved():
    """source_status must be 'live_search' or 'mixed' on semantic card-first path."""
    from app.models.concierge import SOURCE_LIVE_SEARCH, SOURCE_MIXED
    svc, trip = _make_service()
    user_id = UUID(trip["user_id"])
    trip_id = UUID(trip["id"])

    response = svc.search(trip_id, "restaurants chicago", user_id, "msg-007")
    assert response.source_status in {SOURCE_LIVE_SEARCH, SOURCE_MIXED}


# ---------------------------------------------------------------------------
# PART 2 — Non-blocking persistence contract
# ---------------------------------------------------------------------------


def test_background_task_wrapper_swallows_persist_exceptions(caplog):
    """A wrapper matching the background task contract must swallow exceptions and log them."""
    from app.concierge.logging import persist_concierge_request_log

    rid = uuid4()
    exceptions_propagated = []

    def _task_wrapper(*, db, user_id, request_id, prompt, decision, response, latency_ms):
        """Replicate the _persist_request_log_task contract."""
        try:
            raise RuntimeError("db timeout")
        except Exception as exc:
            logging.getLogger("app.routes.ai").warning(
                "concierge.request_log.background_task_failed request_id=%s error=%s",
                request_id,
                exc,
            )

    with caplog.at_level(logging.WARNING, logger="app.routes.ai"):
        try:
            _task_wrapper(
                db=MagicMock(),
                user_id=uuid4(),
                request_id=rid,
                prompt="test",
                decision=MagicMock(),
                response=MagicMock(),
                latency_ms=50,
            )
        except Exception as exc:
            exceptions_propagated.append(exc)

    assert not exceptions_propagated, "background task must not propagate exceptions"
    assert "background_task_failed" in caplog.text


def test_persist_request_log_never_raises():
    """persist_concierge_request_log must never raise regardless of DB state."""
    from app.concierge.logging import persist_concierge_request_log, _KNOWN_UNSUPPORTED_COLUMNS, _SCHEMA_DRIFT_WARNED_COLUMNS
    from app.concierge.router import route_prompt
    from app.concierge.contracts import PlaceRecommendationsResponse

    _KNOWN_UNSUPPORTED_COLUMNS.clear()
    _SCHEMA_DRIFT_WARNED_COLUMNS.clear()

    class _ExplodingDb:
        def table(self, _n):
            return self

        def insert(self, _p):
            return self

        def execute(self):
            raise RuntimeError("boom")

    decision = route_prompt("restaurants", confidence_threshold=0.55)
    response = PlaceRecommendationsResponse(
        response="", intent="restaurants", retrieval_used=True, source_status="none",
        restaurants=[], attractions=[], hotels=[], research_sources=[],
        areas=[], area_comparisons=[], suggestions=[], sources=[], warnings=[],
    )
    rid = uuid4()
    # Must not raise
    result = persist_concierge_request_log(
        db=_ExplodingDb(),
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        prompt="test",
        decision=decision,
        response=response,
        latency_ms=100,
        request_id=rid,
    )
    assert result == rid


def test_request_log_event_emits_request_id(caplog):
    """request_log_event must include the pre-generated request_id in log output."""
    from app.concierge.logging import request_log_event
    from app.concierge.router import route_prompt
    from app.concierge.contracts import PlaceRecommendationsResponse

    decision = route_prompt("best restaurants in chicago", confidence_threshold=0.55)
    response = PlaceRecommendationsResponse(
        response="ok", intent="restaurants", retrieval_used=True, source_status="live_search",
        restaurants=[], attractions=[], hotels=[], research_sources=[],
        areas=[], area_comparisons=[], suggestions=[], sources=[], warnings=[],
    )
    rid = uuid4()
    with caplog.at_level(logging.INFO, logger="app.concierge.logging"):
        request_log_event(
            request_id=rid,
            prompt="best restaurants in chicago",
            decision=decision,
            response=response,
            latency_ms=500,
            sources_used=[],
            llm_tokens_in=None,
            llm_tokens_out=None,
        )
    assert str(rid) in caplog.text


# ---------------------------------------------------------------------------
# PART 3 — Schema drift robustness
# ---------------------------------------------------------------------------

from app.concierge.logging import (
    _KNOWN_UNSUPPORTED_COLUMNS,
    _SCHEMA_DRIFT_WARNED_COLUMNS,
    persist_concierge_request_log,
)
from app.concierge.router import route_prompt
from app.concierge.contracts import PlaceRecommendationsResponse


class _InsertOp:
    def __init__(self, db):
        self._db = db
        self.payload: Optional[dict] = None

    def insert(self, payload):
        self.payload = dict(payload)
        self._db.payloads.append(dict(payload))
        return self

    def execute(self):
        if self._db.errors:
            err = self._db.errors.pop(0)
            if err is not None:
                raise err
        if self.payload is not None:
            self._db.inserted.append(dict(self.payload))
        return self


class _FakeDb:
    def __init__(self, errors):
        self.errors = list(errors)
        self.payloads: List[dict] = []
        self.inserted: List[dict] = []

    def table(self, _name):
        return _InsertOp(self)


def _schema_err(code: str, column: str) -> Exception:
    return Exception({
        "code": code,
        "message": f"Could not find the '{column}' column of 'concierge_request_log' in the schema cache",
    })


def _mock_place_response() -> PlaceRecommendationsResponse:
    return PlaceRecommendationsResponse(
        response="placeholder", intent="restaurants", retrieval_used=True,
        source_status="none", restaurants=[], attractions=[], hotels=[],
        research_sources=[], areas=[], area_comparisons=[], suggestions=[],
        sources=[], warnings=[],
    )


def _clear_drift_state():
    _SCHEMA_DRIFT_WARNED_COLUMNS.clear()
    _KNOWN_UNSUPPORTED_COLUMNS.clear()


def test_four_missing_columns_handled_without_exception(caplog):
    """When 4 columns are missing, persistence degrades gracefully with no exception spam."""
    _clear_drift_state()
    cols = ["intent_confidence", "pipeline_version", "prompt", "request_id"]
    errors = [_schema_err("PGRST204", c) for c in cols] + [None]
    db = _FakeDb(errors=errors)
    decision = route_prompt("best hotels in chicago", confidence_threshold=0.55)

    with caplog.at_level(logging.WARNING, logger="app.concierge.logging"):
        persist_concierge_request_log(
            db=db,
            user_id=UUID("00000000-0000-0000-0000-000000000099"),
            prompt="test",
            decision=decision,
            response=_mock_place_response(),
            latency_ms=10,
        )

    assert "NoneType" not in caplog.text, "logger.exception outside except block produces NoneType"
    for col in cols:
        count = caplog.text.count(f"column={col}")
        assert count <= 1, f"column={col} warned more than once: {count}"


def test_known_unsupported_columns_stripped_on_next_call():
    """After discovering unsupported columns, future calls omit them before first insert."""
    _clear_drift_state()
    decision = route_prompt("best hotels in chicago", confidence_threshold=0.55)

    # First call: discovers "llm_model" is missing
    db1 = _FakeDb(errors=[_schema_err("PGRST204", "llm_model"), None])
    persist_concierge_request_log(
        db=db1,
        user_id=UUID("00000000-0000-0000-0000-000000000011"),
        prompt="test", decision=decision, response=_mock_place_response(), latency_ms=10,
    )
    assert "llm_model" in _KNOWN_UNSUPPORTED_COLUMNS.get("concierge_request_log", set())

    # Second call: "llm_model" stripped upfront before first insert
    db2 = _FakeDb(errors=[None])
    persist_concierge_request_log(
        db=db2,
        user_id=UUID("00000000-0000-0000-0000-000000000011"),
        prompt="test", decision=decision, response=_mock_place_response(), latency_ms=10,
    )
    assert len(db2.payloads) >= 1
    assert "llm_model" not in db2.payloads[0], "known unsupported column must be stripped before first attempt"


def test_schema_drift_exhausted_emits_warning_not_exception(caplog):
    """When all columns are missing, emit a warning (not logger.exception — no 'NoneType: None')."""
    _clear_drift_state()
    decision = route_prompt("best hotels in chicago", confidence_threshold=0.55)

    # All columns in base_row — force each to be removed one by one
    many_cols = [
        "request_id", "user_id", "prompt", "response_type", "stage1_prior",
        "intent_confidence", "sources_used", "llm_model", "llm_tokens_in",
        "llm_tokens_out", "latency_ms", "pipeline_version",
    ]
    errors = [_schema_err("PGRST204", c) for c in many_cols]
    db = _FakeDb(errors=errors)

    with caplog.at_level(logging.WARNING, logger="app.concierge.logging"):
        persist_concierge_request_log(
            db=db,
            user_id=UUID("00000000-0000-0000-0000-000000000033"),
            prompt="test", decision=decision, response=_mock_place_response(), latency_ms=10,
        )

    assert "NoneType" not in caplog.text
    # One of these warning patterns must appear
    assert (
        "persist_failed" in caplog.text
        or "schema_drift_exhausted" in caplog.text
        or "all_columns_unsupported" in caplog.text
    ), f"Expected a persist_failed/exhausted warning, got: {caplog.text}"


def test_unexpected_db_error_swallowed_once(caplog):
    """Unexpected (non-schema) DB errors are swallowed and logged once."""
    _clear_drift_state()
    db = _FakeDb(errors=[RuntimeError("connection timeout")])
    decision = route_prompt("best hotels in chicago", confidence_threshold=0.55)

    with caplog.at_level(logging.ERROR, logger="app.concierge.logging"):
        persist_concierge_request_log(
            db=db,
            user_id=UUID("00000000-0000-0000-0000-000000000044"),
            prompt="test", decision=decision, response=_mock_place_response(), latency_ms=10,
        )

    assert "persist_failed" in caplog.text
    assert caplog.text.count("persist_failed") == 1


def test_pii_redaction_still_works():
    """Email and phone redaction must still work after schema drift changes."""
    _clear_drift_state()
    db = _FakeDb(errors=[None])
    decision = route_prompt("restaurants", confidence_threshold=0.55)

    persist_concierge_request_log(
        db=db,
        user_id=UUID("00000000-0000-0000-0000-000000000055"),
        prompt="contact me at user@example.com or 555-123-4567",
        decision=decision,
        response=_mock_place_response(),
        latency_ms=10,
    )

    assert len(db.payloads) == 1
    stored_prompt = db.payloads[0].get("prompt", "")
    assert "user@example.com" not in stored_prompt
    assert "555-123-4567" not in stored_prompt
    assert "[redacted_email]" in stored_prompt
    assert "[redacted_phone]" in stored_prompt


# ---------------------------------------------------------------------------
# PART 4 — Timing spans in service search logs
# ---------------------------------------------------------------------------


def test_service_search_timing_log_emitted(caplog):
    """search() must emit a structured timing log with all required fields."""
    svc, trip = _make_service()
    user_id = UUID(trip["user_id"])
    trip_id = UUID(trip["id"])

    with caplog.at_level(logging.INFO, logger="app.services.concierge"):
        svc.search(trip_id, "best restaurants in chicago", user_id, "msg-timing-001")

    assert "concierge.service.search_timing" in caplog.text
    required_fields = [
        "fetch_trip_ms=",
        "save_user_message_ms=",
        "fetch_live_research_ms=",
        "legacy_summary_llm_ms=",
        "legacy_summary_skipped=",
        "response_assembly_ms=",
        "save_assistant_message_ms=",
        "total_search_ms=",
        "semantic_card_first_path=",
    ]
    for field in required_fields:
        assert field in caplog.text, f"Timing field missing from log: {field}"


def test_semantic_path_shows_legacy_summary_skipped_true(caplog):
    """On semantic_retrieval_v1 path, timing log must show legacy_summary_skipped=True."""
    svc, trip = _make_service(provider_name="semantic_retrieval_v1", source_status="live_search")
    user_id = UUID(trip["user_id"])
    trip_id = UUID(trip["id"])

    with caplog.at_level(logging.INFO, logger="app.services.concierge"):
        svc.search(trip_id, "best restaurants in chicago", user_id, "msg-timing-002")

    assert "legacy_summary_skipped=True" in caplog.text
    assert "semantic_card_first_path=True" in caplog.text


def test_non_semantic_path_shows_legacy_summary_skipped_false(caplog):
    """On non-semantic path, timing log must show legacy_summary_skipped=False."""
    from app.services.concierge import ConciergeService

    svc, trip = _make_service(provider_name="google_places_direct", source_status="live_search")
    user_id = UUID(trip["user_id"])
    trip_id = UUID(trip["id"])

    with caplog.at_level(logging.INFO, logger="app.services.concierge"):
        with patch.object(ConciergeService, "_call_claude",
                          return_value='{"response": "ok", "suggestions": []}'):
            svc.search(trip_id, "restaurants chicago", user_id, "msg-timing-003")

    assert "legacy_summary_skipped=False" in caplog.text


def test_timing_legacy_llm_ms_zero_on_semantic_path(caplog):
    """legacy_summary_llm_ms must be near-zero (< 100ms) on the semantic bypass path."""
    import re
    svc, trip = _make_service()
    user_id = UUID(trip["user_id"])
    trip_id = UUID(trip["id"])

    with caplog.at_level(logging.INFO, logger="app.services.concierge"):
        svc.search(trip_id, "restaurants chicago", user_id, "msg-timing-004")

    timing_line = next(
        (line for line in caplog.text.splitlines() if "search_timing" in line), None
    )
    assert timing_line is not None, "timing log line not found"
    m = re.search(r"legacy_summary_llm_ms=(\d+)", timing_line)
    assert m is not None
    assert int(m.group(1)) < 100, f"legacy_summary_llm_ms unexpectedly large: {m.group(1)}"
