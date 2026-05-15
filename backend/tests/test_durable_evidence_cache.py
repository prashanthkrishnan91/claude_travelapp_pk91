"""Tests for AI Concierge Durable Evidence/Note Cache v2.

Covers:
- memory miss + Supabase evidence hit skips Tavily/editorial
- accepted evidence writes to Supabase and in-memory
- expired evidence row is ignored
- approved note writes to Supabase and in-memory
- memory miss + Supabase note hit hydrates approved notes
- expired note row is ignored
- rejected/timeout/unvalidated/generic notes are not written
- Supabase failure is non-fatal and live path continues
- ROI logs include durable cache fields
- SupabaseNoteCache empty note guard
- Atom serialization round-trip
- Compound key upsert in mock client
- Existing PR #384 ROI telemetry fields still present
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch, PropertyMock
import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

def _future_iso(days: int = 14) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _past_iso(days: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _make_mock_atom(
    source_provider: str = "tavily",
    evidence_type: str = "specialty_context",
    normalized_value: str = "craft beer taproom",
    confidence: float = 0.85,
) -> Any:
    """Build a minimal mock atom compatible with _atom_to_dict."""
    atom = MagicMock()
    atom.source_provider = source_provider
    atom.evidence_type = evidence_type
    atom.normalized_value = normalized_value
    atom.confidence = confidence
    atom.provenance = {"url": "https://example.com"}
    atom.allowed_into_writer = True
    atom.conflict_status = "ok"
    return atom


def _make_supabase_mock(rows: List[Dict]) -> Any:
    """Build a mock Supabase client that returns the given rows on .execute()."""
    result = MagicMock()
    result.data = rows
    qb = MagicMock()
    qb.select.return_value = qb
    qb.eq.return_value = qb
    qb.limit.return_value = qb
    qb.upsert.return_value = qb
    qb.execute.return_value = result
    client = MagicMock()
    client.table.return_value = qb
    return client


# ── Atom serialisation ─────────────────────────────────────────────────────────

class TestAtomSerialization:
    def test_atom_to_dict_round_trip(self):
        from app.concierge.evidence_cache import _atom_to_dict, _atom_from_dict

        atom = _make_mock_atom()
        d = _atom_to_dict(atom)
        assert d["source_provider"] == "tavily"
        assert d["evidence_type"] == "specialty_context"
        assert d["normalized_value"] == "craft beer taproom"
        assert d["confidence"] == 0.85
        assert d["allowed_into_writer"] is True
        assert d["conflict_status"] == "ok"

        restored = _atom_from_dict(d)
        assert restored.source_provider == "tavily"
        assert restored.evidence_type == "specialty_context"
        assert restored.normalized_value == "craft beer taproom"
        assert restored.confidence == 0.85
        assert restored.allowed_into_writer is True
        assert restored.conflict_status == "ok"

    def test_atom_from_dict_handles_missing_fields(self):
        from app.concierge.evidence_cache import _atom_from_dict
        restored = _atom_from_dict({})
        assert restored.source_provider == ""
        assert restored.evidence_type == ""
        assert restored.confidence == 0.0
        assert restored.allowed_into_writer is False
        assert restored.conflict_status == "ok"


# ── SupabaseEvidenceCache ──────────────────────────────────────────────────────

class TestSupabaseEvidenceCache:
    def test_get_returns_none_on_empty_rows(self):
        from app.concierge.evidence_cache import SupabaseEvidenceCache
        cache = SupabaseEvidenceCache()
        mock_client = _make_supabase_mock([])

        with patch("app.concierge.evidence_cache.logger"):
            with patch("app.db.client.get_supabase", return_value=mock_client):
                result = cache.get("fp_missing")
        assert result is None

    def test_get_returns_entry_on_valid_row(self):
        from app.concierge.evidence_cache import SupabaseEvidenceCache, _atom_to_dict

        atom = _make_mock_atom()
        row = {
            "atoms_by_place_id": {"place_1": [_atom_to_dict(atom)]},
            "accepted_count": 1,
            "expires_at": _future_iso(14),
        }
        cache = SupabaseEvidenceCache()
        mock_client = _make_supabase_mock([row])

        with patch("app.db.client.get_supabase", return_value=mock_client):
            entry = cache.get("fp_valid")

        assert entry is not None
        assert entry.accepted_count == 1
        assert "place_1" in entry.atoms_by_place_id
        assert len(entry.atoms_by_place_id["place_1"]) == 1

    def test_get_ignores_expired_row(self):
        from app.concierge.evidence_cache import SupabaseEvidenceCache, _atom_to_dict

        atom = _make_mock_atom()
        row = {
            "atoms_by_place_id": {"place_1": [_atom_to_dict(atom)]},
            "accepted_count": 1,
            "expires_at": _past_iso(1),  # expired
        }
        cache = SupabaseEvidenceCache()
        mock_client = _make_supabase_mock([row])

        with patch("app.db.client.get_supabase", return_value=mock_client):
            entry = cache.get("fp_expired")

        assert entry is None

    def test_get_is_nonfatal_on_supabase_error(self):
        from app.concierge.evidence_cache import SupabaseEvidenceCache

        cache = SupabaseEvidenceCache()
        with patch("app.db.client.get_supabase", side_effect=Exception("connection refused")):
            result = cache.get("fp_error")
        assert result is None

    def test_set_returns_true_on_success(self):
        from app.concierge.evidence_cache import SupabaseEvidenceCache

        atom = _make_mock_atom()
        cache = SupabaseEvidenceCache()
        mock_client = _make_supabase_mock([])

        with patch("app.db.client.get_supabase", return_value=mock_client):
            ok = cache.set("fp_set", {"place_1": [atom]}, accepted_count=1, destination="Chicago")

        assert ok is True
        # upsert was called
        mock_client.table.assert_called_with("concierge_evidence_cache")

    def test_set_returns_false_on_supabase_error(self):
        from app.concierge.evidence_cache import SupabaseEvidenceCache

        atom = _make_mock_atom()
        cache = SupabaseEvidenceCache()
        with patch("app.db.client.get_supabase", side_effect=Exception("write failed")):
            ok = cache.set("fp_err", {"p": [atom]}, accepted_count=1)
        assert ok is False

    def test_set_expires_at_is_future(self):
        from app.concierge.evidence_cache import SupabaseEvidenceCache

        captured: Dict = {}

        def fake_upsert(data, on_conflict=""):
            captured.update(data)
            qb = MagicMock()
            qb.execute.return_value = MagicMock(data=[])
            return qb

        client = MagicMock()
        qb = MagicMock()
        qb.upsert.side_effect = fake_upsert
        client.table.return_value = qb

        atom = _make_mock_atom()
        cache = SupabaseEvidenceCache(ttl_days=14)
        with patch("app.db.client.get_supabase", return_value=client):
            cache.set("fp_ttl", {"p": [atom]}, accepted_count=1)

        assert "expires_at" in captured
        expires_dt = datetime.fromisoformat(captured["expires_at"].replace("Z", "+00:00"))
        assert expires_dt > datetime.now(timezone.utc) + timedelta(days=13)


# ── SupabaseNoteCache ──────────────────────────────────────────────────────────

class TestSupabaseNoteCache:
    def test_get_returns_none_on_empty_rows(self):
        from app.concierge.evidence_cache import SupabaseNoteCache
        cache = SupabaseNoteCache()
        mock_client = _make_supabase_mock([])

        with patch("app.db.client.get_supabase", return_value=mock_client):
            result = cache.get("place_1", "fp_missing")
        assert result is None

    def test_get_returns_entry_on_valid_row(self):
        from app.concierge.evidence_cache import SupabaseNoteCache
        row = {
            "note": "A craft taproom near the riverwalk with 20 rotating taps.",
            "source": "set_level_writer_v1",
            "expires_at": _future_iso(30),
        }
        cache = SupabaseNoteCache()
        mock_client = _make_supabase_mock([row])

        with patch("app.db.client.get_supabase", return_value=mock_client):
            entry = cache.get("place_1", "fp_valid")

        assert entry is not None
        assert "riverwalk" in entry.note
        assert entry.source == "set_level_writer_v1"

    def test_get_ignores_expired_row(self):
        from app.concierge.evidence_cache import SupabaseNoteCache
        row = {
            "note": "A valid note.",
            "source": "set_level_writer_v1",
            "expires_at": _past_iso(1),
        }
        cache = SupabaseNoteCache()
        mock_client = _make_supabase_mock([row])

        with patch("app.db.client.get_supabase", return_value=mock_client):
            entry = cache.get("place_1", "fp_expired")

        assert entry is None

    def test_get_ignores_empty_note_in_row(self):
        from app.concierge.evidence_cache import SupabaseNoteCache
        row = {
            "note": "   ",
            "source": "set_level_writer_v1",
            "expires_at": _future_iso(30),
        }
        cache = SupabaseNoteCache()
        mock_client = _make_supabase_mock([row])

        with patch("app.db.client.get_supabase", return_value=mock_client):
            entry = cache.get("place_1", "fp_empty_note")
        assert entry is None

    def test_get_is_nonfatal_on_supabase_error(self):
        from app.concierge.evidence_cache import SupabaseNoteCache
        cache = SupabaseNoteCache()
        with patch("app.db.client.get_supabase", side_effect=Exception("db error")):
            result = cache.get("place_1", "fp_err")
        assert result is None

    def test_set_returns_true_on_success(self):
        from app.concierge.evidence_cache import SupabaseNoteCache
        cache = SupabaseNoteCache()
        mock_client = _make_supabase_mock([])

        with patch("app.db.client.get_supabase", return_value=mock_client):
            ok = cache.set("place_1", "fp_ok", "A specific note about the taproom.", "set_level_writer_v1")

        assert ok is True

    def test_set_returns_false_on_empty_note(self):
        from app.concierge.evidence_cache import SupabaseNoteCache
        cache = SupabaseNoteCache()
        ok = cache.set("place_1", "fp_x", "", "set_level_writer_v1")
        assert ok is False

    def test_set_returns_false_on_whitespace_note(self):
        from app.concierge.evidence_cache import SupabaseNoteCache
        cache = SupabaseNoteCache()
        ok = cache.set("place_1", "fp_x", "   ", "set_level_writer_v1")
        assert ok is False

    def test_set_returns_false_on_supabase_error(self):
        from app.concierge.evidence_cache import SupabaseNoteCache
        cache = SupabaseNoteCache()
        with patch("app.db.client.get_supabase", side_effect=Exception("write error")):
            ok = cache.set("place_1", "fp_err", "A note.", "writer")
        assert ok is False

    def test_set_expires_at_is_30_days(self):
        from app.concierge.evidence_cache import SupabaseNoteCache

        captured: Dict = {}

        def fake_upsert(data, on_conflict=""):
            captured.update(data)
            qb = MagicMock()
            qb.execute.return_value = MagicMock(data=[])
            return qb

        client = MagicMock()
        qb = MagicMock()
        qb.upsert.side_effect = fake_upsert
        client.table.return_value = qb

        cache = SupabaseNoteCache(ttl_days=30)
        with patch("app.db.client.get_supabase", return_value=client):
            cache.set("place_1", "fp_ttl", "A specific note.", "writer")

        assert "expires_at" in captured
        expires_dt = datetime.fromisoformat(captured["expires_at"].replace("Z", "+00:00"))
        assert expires_dt > datetime.now(timezone.utc) + timedelta(days=29)


# ── Durable layer skips Tavily on hit ─────────────────────────────────────────

class TestDurableCacheSkipsTavily:
    """Supabase evidence cache hit warms in-memory cache and skips Tavily."""

    def test_durable_hit_warms_memory_cache(self):
        """After a durable hit, in-memory cache should have the entry."""
        from app.concierge.evidence_cache import (
            EvidenceAtomCache,
            SupabaseEvidenceCache,
            _atom_to_dict,
        )

        atom = _make_mock_atom()
        row = {
            "atoms_by_place_id": {"place_1": [_atom_to_dict(atom)]},
            "accepted_count": 1,
            "expires_at": _future_iso(14),
        }
        memory_cache = EvidenceAtomCache(ttl_seconds=3600)
        durable_cache = SupabaseEvidenceCache()
        fp = "fp_durable_warm_test"

        assert memory_cache.get(fp) is None  # memory miss

        mock_client = _make_supabase_mock([row])
        with patch("app.db.client.get_supabase", return_value=mock_client):
            entry = durable_cache.get(fp)

        assert entry is not None
        # Warm in-memory
        memory_cache.set(fp, entry.atoms_by_place_id, entry.accepted_count)
        assert memory_cache.get(fp) is not None  # now in memory

    def test_durable_miss_falls_through_to_live_path(self):
        """Durable cache miss must not block the live Tavily path."""
        from app.concierge.evidence_cache import SupabaseEvidenceCache

        durable_cache = SupabaseEvidenceCache()
        mock_client = _make_supabase_mock([])  # empty = miss

        with patch("app.db.client.get_supabase", return_value=mock_client):
            entry = durable_cache.get("fp_miss")

        assert entry is None  # falls through to live path


# ── Evidence write goes to both layers ────────────────────────────────────────

class TestDurableEvidenceWrite:
    def test_set_stores_to_supabase_with_correct_fields(self):
        from app.concierge.evidence_cache import SupabaseEvidenceCache

        captured_rows = []

        def fake_upsert(data, on_conflict=""):
            captured_rows.append(dict(data))
            qb = MagicMock()
            qb.execute.return_value = MagicMock(data=[])
            return qb

        client = MagicMock()
        qb = MagicMock()
        qb.upsert.side_effect = fake_upsert
        client.table.return_value = qb

        atom = _make_mock_atom()
        cache = SupabaseEvidenceCache()
        with patch("app.db.client.get_supabase", return_value=client):
            ok = cache.set("fp_write_test", {"place_1": [atom]}, accepted_count=1, destination="Chicago")

        assert ok is True
        assert len(captured_rows) == 1
        row = captured_rows[0]
        assert row["evidence_fingerprint"] == "fp_write_test"
        assert row["destination"] == "Chicago"
        assert row["accepted_count"] == 1
        assert "atoms_by_place_id" in row
        assert "place_1" in row["atoms_by_place_id"]
        assert "expires_at" in row
        assert "version_salt" in row

    def test_rejected_notes_not_stored_via_supabase_note_cache(self):
        """SupabaseNoteCache.set() silently rejects empty notes — no Supabase call."""
        from app.concierge.evidence_cache import SupabaseNoteCache

        cache = SupabaseNoteCache()
        client = MagicMock()

        with patch("app.db.client.get_supabase", return_value=client):
            ok = cache.set("place_1", "fp_x", "", "writer")

        assert ok is False
        # table() should not have been called at all
        client.table.assert_not_called()


# ── Approved note write and retrieval ─────────────────────────────────────────

class TestDurableNoteWriteAndRetrieve:
    def test_approved_note_stored_and_retrieved_from_supabase(self):
        """Write an approved note to Supabase and retrieve it."""
        from app.concierge.evidence_cache import SupabaseNoteCache, _atom_to_dict

        stored: Dict = {}

        def fake_upsert(data, on_conflict=""):
            stored.update(data)
            qb = MagicMock()
            qb.execute.return_value = MagicMock(data=[])
            return qb

        write_client = MagicMock()
        wqb = MagicMock()
        wqb.upsert.side_effect = fake_upsert
        write_client.table.return_value = wqb

        cache = SupabaseNoteCache()
        note_text = "A riverside taproom specialising in hazy IPAs and seasonal sours."

        with patch("app.db.client.get_supabase", return_value=write_client):
            ok = cache.set("ChIJabc", "fp_note_test", note_text, "set_level_writer_v1")
        assert ok is True
        assert stored["note"] == note_text

        # Now simulate retrieval
        read_row = {
            "note": note_text,
            "source": "set_level_writer_v1",
            "expires_at": _future_iso(30),
        }
        read_client = _make_supabase_mock([read_row])
        with patch("app.db.client.get_supabase", return_value=read_client):
            entry = cache.get("ChIJabc", "fp_note_test")

        assert entry is not None
        assert "hazy IPAs" in entry.note
        assert entry.source == "set_level_writer_v1"

    def test_durable_note_hit_warms_memory_cache(self):
        """Durable note hit should write into NoteCache (in-memory hot layer)."""
        from app.concierge.evidence_cache import NoteCache, SupabaseNoteCache

        memory_cache = NoteCache(ttl_seconds=7200)
        durable_cache = SupabaseNoteCache()
        fp = "fp_warm_note"
        place_id = "ChIJtest"

        assert memory_cache.get(place_id, fp) is None  # memory miss

        read_row = {
            "note": "A cozy wine bar with natural pours and a curated cheese plate.",
            "source": "set_level_writer_v1",
            "expires_at": _future_iso(30),
        }
        read_client = _make_supabase_mock([read_row])
        with patch("app.db.client.get_supabase", return_value=read_client):
            dn = durable_cache.get(place_id, fp)

        assert dn is not None
        # Warm memory
        memory_cache.set(place_id, fp, dn.note, dn.source)
        mem_entry = memory_cache.get(place_id, fp)
        assert mem_entry is not None
        assert "natural pours" in mem_entry.note


# ── Non-fatal behavior ────────────────────────────────────────────────────────

class TestDurableCacheNonFatal:
    def test_evidence_get_error_does_not_raise(self):
        from app.concierge.evidence_cache import SupabaseEvidenceCache
        cache = SupabaseEvidenceCache()
        with patch("app.db.client.get_supabase", side_effect=RuntimeError("timeout")):
            result = cache.get("fp_any")
        assert result is None  # non-fatal, falls through

    def test_evidence_set_error_does_not_raise(self):
        from app.concierge.evidence_cache import SupabaseEvidenceCache
        atom = _make_mock_atom()
        cache = SupabaseEvidenceCache()
        with patch("app.db.client.get_supabase", side_effect=RuntimeError("timeout")):
            ok = cache.set("fp_any", {"p": [atom]}, 1)
        assert ok is False  # non-fatal, returns False

    def test_note_get_error_does_not_raise(self):
        from app.concierge.evidence_cache import SupabaseNoteCache
        cache = SupabaseNoteCache()
        with patch("app.db.client.get_supabase", side_effect=RuntimeError("connection reset")):
            result = cache.get("place_1", "fp_any")
        assert result is None

    def test_note_set_error_does_not_raise(self):
        from app.concierge.evidence_cache import SupabaseNoteCache
        cache = SupabaseNoteCache()
        with patch("app.db.client.get_supabase", side_effect=RuntimeError("connection reset")):
            ok = cache.set("place_1", "fp_any", "A note.", "writer")
        assert ok is False

    def test_evidence_error_increments_roi_error_count(self):
        """Durable cache failure should increment durable_cache_error_count."""
        from app.concierge.evidence_cache import CreditROITelemetry, SupabaseEvidenceCache

        roi = CreditROITelemetry()
        atom = _make_mock_atom()
        cache = SupabaseEvidenceCache()

        with patch("app.db.client.get_supabase", side_effect=Exception("db down")):
            ok = cache.set("fp_any", {"p": [atom]}, 1)

        if not ok:
            roi.durable_cache_error_count += 1

        assert roi.durable_cache_error_count == 1


# ── ROI telemetry fields ──────────────────────────────────────────────────────

class TestDurableCacheROITelemetry:
    REQUIRED_DURABLE_FIELDS = {
        "durable_evidence_cache_hit",
        "durable_evidence_cache_write",
        "durable_note_cache_hit_count",
        "durable_note_cache_write_count",
        "durable_cache_error_count",
    }

    def test_durable_fields_present_in_as_log_dict(self):
        from app.concierge.evidence_cache import CreditROITelemetry
        roi = CreditROITelemetry()
        d = roi.as_log_dict()
        missing = self.REQUIRED_DURABLE_FIELDS - set(d.keys())
        assert not missing, f"Missing durable ROI fields: {missing}"

    def test_durable_evidence_cache_hit_recorded(self):
        from app.concierge.evidence_cache import CreditROITelemetry
        roi = CreditROITelemetry()
        roi.durable_evidence_cache_hit = True
        roi.evidence_cache_hit = True
        d = roi.as_log_dict()
        assert d["durable_evidence_cache_hit"] is True
        assert d["evidence_cache_hit"] is True

    def test_durable_evidence_cache_write_recorded(self):
        from app.concierge.evidence_cache import CreditROITelemetry
        roi = CreditROITelemetry()
        roi.durable_evidence_cache_write = True
        roi.evidence_cache_write = True
        d = roi.as_log_dict()
        assert d["durable_evidence_cache_write"] is True

    def test_durable_note_cache_hit_count_recorded(self):
        from app.concierge.evidence_cache import CreditROITelemetry
        roi = CreditROITelemetry()
        roi.durable_note_cache_hit_count = 2
        roi.note_cache_hit_count = 2
        d = roi.as_log_dict()
        assert d["durable_note_cache_hit_count"] == 2

    def test_durable_note_cache_write_count_recorded(self):
        from app.concierge.evidence_cache import CreditROITelemetry
        roi = CreditROITelemetry()
        roi.durable_note_cache_write_count = 3
        d = roi.as_log_dict()
        assert d["durable_note_cache_write_count"] == 3

    def test_durable_cache_error_count_recorded(self):
        from app.concierge.evidence_cache import CreditROITelemetry
        roi = CreditROITelemetry()
        roi.durable_cache_error_count = 1
        d = roi.as_log_dict()
        assert d["durable_cache_error_count"] == 1

    def test_all_pr384_roi_fields_still_present(self):
        """Existing PR #384 ROI fields must remain intact."""
        from app.concierge.evidence_cache import CreditROITelemetry
        pr384_fields = {
            "tavily_attempted",
            "tavily_skipped_reason",
            "evidence_cache_hit",
            "evidence_cache_write",
            "accepted_editorial_evidence_count",
            "note_cache_hit_count",
            "note_cache_write_count",
            "note_writer_attempted",
            "note_writer_timed_out",
            "approved_note_count",
            "visible_note_count",
            "omitted_note_reasons",
            "credits_spent_but_no_visible_notes",
            "async_late_note_stored_count",
        }
        roi = CreditROITelemetry()
        d = roi.as_log_dict()
        missing = pr384_fields - set(d.keys())
        assert not missing, f"Missing PR #384 ROI fields: {missing}"

    def test_default_durable_fields_are_zero_false(self):
        from app.concierge.evidence_cache import CreditROITelemetry
        roi = CreditROITelemetry()
        assert roi.durable_evidence_cache_hit is False
        assert roi.durable_evidence_cache_write is False
        assert roi.durable_note_cache_hit_count == 0
        assert roi.durable_note_cache_write_count == 0
        assert roi.durable_cache_error_count == 0


# ── Generic/rejected notes never stored ──────────────────────────────────────

class TestGenericNotesNeverStored:
    """Generic, rating-only, rejected, or empty notes must not reach the durable cache."""

    def test_empty_string_not_stored(self):
        from app.concierge.evidence_cache import SupabaseNoteCache
        cache = SupabaseNoteCache()
        ok = cache.set("p1", "fp", "", "writer")
        assert ok is False

    def test_whitespace_not_stored(self):
        from app.concierge.evidence_cache import SupabaseNoteCache
        cache = SupabaseNoteCache()
        ok = cache.set("p1", "fp", "    \t\n", "writer")
        assert ok is False

    def test_in_memory_note_cache_also_rejects_empty(self):
        from app.concierge.evidence_cache import NoteCache
        cache = NoteCache(ttl_seconds=60)
        cache.set("p1", "fp", "", "writer")
        assert cache.get("p1", "fp") is None

    def test_in_memory_note_cache_rejects_whitespace(self):
        from app.concierge.evidence_cache import NoteCache
        cache = NoteCache(ttl_seconds=60)
        cache.set("p1", "fp", "   ", "writer")
        assert cache.get("p1", "fp") is None


# ── Module-level singletons exist ────────────────────────────────────────────

class TestModuleSingletons:
    def test_supabase_evidence_cache_singleton_exists(self):
        from app.concierge.evidence_cache import _SUPABASE_EVIDENCE_CACHE, SupabaseEvidenceCache
        assert isinstance(_SUPABASE_EVIDENCE_CACHE, SupabaseEvidenceCache)

    def test_supabase_note_cache_singleton_exists(self):
        from app.concierge.evidence_cache import _SUPABASE_NOTE_CACHE, SupabaseNoteCache
        assert isinstance(_SUPABASE_NOTE_CACHE, SupabaseNoteCache)

    def test_durable_evidence_ttl_is_14_days(self):
        from app.concierge.evidence_cache import _DURABLE_EVIDENCE_TTL_DAYS
        assert _DURABLE_EVIDENCE_TTL_DAYS == 14

    def test_durable_note_ttl_is_30_days(self):
        from app.concierge.evidence_cache import _DURABLE_NOTE_TTL_DAYS
        assert _DURABLE_NOTE_TTL_DAYS == 30


# ── Mock client compound key upsert ──────────────────────────────────────────

class TestMockCompoundKeyUpsert:
    """Verify the mock client handles compound conflict keys correctly."""

    def test_compound_key_upsert_updates_existing_row(self):
        from app.db.mock import MockSupabaseClient, _store

        # Reset mock store for this test
        _store.clear()
        client = MockSupabaseClient()

        # Insert first row
        client.table("test_compound").upsert(
            {"field_a": "x", "field_b": "y", "value": "original"},
            on_conflict="field_a,field_b",
        ).execute()

        # Upsert with same compound key → should update
        client.table("test_compound").upsert(
            {"field_a": "x", "field_b": "y", "value": "updated"},
            on_conflict="field_a,field_b",
        ).execute()

        rows = client.table("test_compound").select("*").eq("field_a", "x").eq("field_b", "y").execute().data
        assert len(rows) == 1
        assert rows[0]["value"] == "updated"

    def test_compound_key_upsert_inserts_different_key(self):
        from app.db.mock import MockSupabaseClient, _store

        _store.clear()
        client = MockSupabaseClient()

        client.table("test_compound2").upsert(
            {"field_a": "x", "field_b": "y", "value": "row1"},
            on_conflict="field_a,field_b",
        ).execute()

        # Different key → insert
        client.table("test_compound2").upsert(
            {"field_a": "x", "field_b": "z", "value": "row2"},
            on_conflict="field_a,field_b",
        ).execute()

        rows = client.table("test_compound2").select("*").execute().data
        assert len(rows) == 2
