from __future__ import annotations

from uuid import UUID

from app.concierge.logging import persist_concierge_request_log, _SCHEMA_DRIFT_WARNED_COLUMNS, _KNOWN_UNSUPPORTED_COLUMNS
from app.concierge.router import route_prompt

from app.concierge.contracts import PlaceRecommendationsResponse


class _InsertOp:
    def __init__(self, db):
        self._db = db
        self.payload = None

    def insert(self, payload):
        self.payload = dict(payload)
        self._db.payloads.append(dict(payload))
        return self

    def execute(self):
        if self._db.errors:
            err = self._db.errors.pop(0)
            if err is not None:
                raise err
        self._db.inserted.append(dict(self.payload))
        return self


class _FakeDb:
    def __init__(self, errors):
        self.errors = list(errors)
        self.payloads = []
        self.inserted = []

    def table(self, _name):
        return _InsertOp(self)


def _schema_err(code: str, column: str) -> Exception:
    return Exception({"code": code, "message": f"Could not find the '{column}' column of 'concierge_request_log' in the schema cache"})




def _mock_place_response() -> PlaceRecommendationsResponse:
    return PlaceRecommendationsResponse(
        response="placeholder",
        intent="hotels",
        retrieval_used=True,
        source_status="none",
        restaurants=[],
        attractions=[],
        hotels=[],
        research_sources=[],
        areas=[],
        area_comparisons=[],
        suggestions=[],
        sources=["https://example.com/source"],
        warnings=[],
    )
def test_intent_classifier_version_never_in_insert_row(caplog):
    # intent_classifier_version was removed from base_row to avoid PGRST204;
    # its value is emitted in app logs via request_log_event instead.
    _SCHEMA_DRIFT_WARNED_COLUMNS.clear()
    _KNOWN_UNSUPPORTED_COLUMNS.clear()
    db = _FakeDb(errors=[])
    decision = route_prompt("best hotels in chicago", confidence_threshold=0.55)

    persist_concierge_request_log(
        db=db,
        user_id=UUID("00000000-0000-0000-0000-000000000012"),
        prompt="p",
        decision=decision,
        response=_mock_place_response(),
        latency_ms=10,
    )

    assert len(db.payloads) == 1
    assert "intent_classifier_version" not in db.payloads[0]


def test_two_missing_columns_are_dropped_across_retries():
    _SCHEMA_DRIFT_WARNED_COLUMNS.clear()
    _KNOWN_UNSUPPORTED_COLUMNS.clear()
    # Simulate two successive schema-drift errors on columns that ARE in base_row.
    db = _FakeDb(errors=[_schema_err("PGRST204", "llm_model"), _schema_err("PGRST116", "pipeline_version"), None])
    decision = route_prompt("best hotels in chicago", confidence_threshold=0.55)

    persist_concierge_request_log(
        db=db,
        user_id=UUID("00000000-0000-0000-0000-000000000012"),
        prompt="p",
        decision=decision,
        response=_mock_place_response(),
        latency_ms=10,
    )

    assert len(db.payloads) == 3
    assert "llm_model" not in db.payloads[1]
    assert "llm_model" not in db.payloads[2]
    assert "pipeline_version" not in db.payloads[2]


def test_warning_emitted_once_per_process_per_column(caplog):
    _SCHEMA_DRIFT_WARNED_COLUMNS.clear()
    _KNOWN_UNSUPPORTED_COLUMNS.clear()
    decision = route_prompt("best hotels in chicago", confidence_threshold=0.55)

    for _ in range(2):
        db = _FakeDb(errors=[_schema_err("PGRST204", "llm_model"), None])
        persist_concierge_request_log(
            db=db,
            user_id=UUID("00000000-0000-0000-0000-000000000012"),
            prompt="p",
            decision=decision,
            response=_mock_place_response(),
            latency_ms=10,
        )

    assert caplog.text.count("concierge.logging.schema_drift") == 1


def test_unexpected_exception_is_logged_and_not_raised(caplog):
    _SCHEMA_DRIFT_WARNED_COLUMNS.clear()
    _KNOWN_UNSUPPORTED_COLUMNS.clear()
    db = _FakeDb(errors=[RuntimeError("boom")])
    decision = route_prompt("best hotels in chicago", confidence_threshold=0.55)

    persist_concierge_request_log(
        db=db,
        user_id=UUID("00000000-0000-0000-0000-000000000012"),
        prompt="p",
        decision=decision,
        response=_mock_place_response(),
        latency_ms=10,
    )

    assert "concierge.request_log.persist_failed" in caplog.text
