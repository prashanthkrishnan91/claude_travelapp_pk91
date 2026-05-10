"""Concierge lifecycle guard — Level 3 Trip Data Contract Rescue.

If a user deletes a trip while an in-flight concierge search is still
completing, the late ``_save_message`` write hits a foreign-key violation
(code 23503) against ``trips.id``.  This is a benign lifecycle race and
must NOT emit a WARNING-level log — it should be downgraded to INFO and
silently dropped.

These tests pin that contract by exercising ``_save_message`` with a stub
supabase client that raises an FK-shaped error.
"""
from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

# ── Minimal stack stubs (mirror the patterns used by other test_concierge_* files)
for _mod in ["fastapi", "supabase", "anthropic"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import fastapi as _fa  # noqa: E402


class _StubHTTPException(Exception):
    def __init__(self, status_code: int = 400, detail=None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


_fa.HTTPException = _StubHTTPException
_fa.status = MagicMock()
_fa.status.HTTP_404_NOT_FOUND = 404


class _FKError(Exception):
    """Mimic Supabase / Postgres FK violation surface."""

    code = "23503"

    def __str__(self) -> str:
        return (
            'insert or update on table "concierge_messages" violates foreign '
            'key constraint "concierge_messages_trip_id_fkey" Key (trip_id)='
            "(deleted) is not present in table \"trips\"."
        )


class _DupKeyError(Exception):
    code = "23505"


def _import_service():
    """Import ConciergeService while shielding it from heavy app imports.

    ConciergeService lives in app.services.concierge.  The module-level
    imports pull in app.core.* / app.services.search etc.; those are
    expensive but already stubbable.  For these tests we only need the two
    helper methods on the instance, so we patch __init__ to skip the full
    dependency wiring.
    """
    from app.services import concierge as concierge_mod
    return concierge_mod


def _make_service(db: Any):
    mod = _import_service()
    svc = mod.ConciergeService.__new__(mod.ConciergeService)
    svc._db = db
    svc._settings = MagicMock()
    return svc, mod.logger


def test_save_message_quietly_skips_deleted_trip_fk_violation(monkeypatch, caplog):
    """FK violation from a deleted trip is logged at INFO, not WARNING."""
    svc, logger = _make_service(MagicMock())

    # Stub the supabase chain so insert().execute() raises an FK error.
    insert_call = MagicMock()
    insert_call.execute.side_effect = _FKError()
    table_call = MagicMock()
    table_call.insert.return_value = insert_call
    table_call.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
    svc._db.table.return_value = table_call

    import logging
    with caplog.at_level(logging.INFO, logger=logger.name):
        # Must not raise.
        svc._save_message(uuid4(), "user", "hello")

    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert warnings == [], f"FK violation must NOT log at WARNING; got {warnings}"

    infos = [r for r in caplog.records if r.levelno == logging.INFO and "no longer exists" in r.getMessage()]
    assert infos, "Lifecycle skip should be logged at INFO with a clear reason"


def test_is_deleted_trip_fk_error_detects_code_23503():
    svc, _ = _make_service(MagicMock())
    assert svc._is_deleted_trip_fk_error(_FKError()) is True


def test_is_deleted_trip_fk_error_detects_text_match_without_code():
    """Some Supabase error envelopes omit `.code`; fall back to text match."""
    svc, _ = _make_service(MagicMock())

    class _TextOnlyFK(Exception):
        def __str__(self) -> str:
            return "foreign key constraint failed on trip_id"

    assert svc._is_deleted_trip_fk_error(_TextOnlyFK()) is True


def test_is_deleted_trip_fk_error_ignores_unrelated_errors():
    svc, _ = _make_service(MagicMock())

    class _Unrelated(Exception):
        code = "PGRST500"

        def __str__(self) -> str:
            return "internal server error"

    assert svc._is_deleted_trip_fk_error(_Unrelated()) is False
    # Duplicate key should still go through the duplicate-detection branch,
    # not the FK branch.
    assert svc._is_deleted_trip_fk_error(_DupKeyError()) is False
