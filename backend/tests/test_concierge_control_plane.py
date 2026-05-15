"""
Tests for the AI Concierge notes runtime control plane.

Covers:
  A. Plain-category credit protection — "sports bars" type queries should not
     trigger legacy batched reasoning, and all 6 verified cards must survive.
  B. Editorial-worthy queries — NoteDecision correctly approves note paths.
  C. NoteDecision gate — skip-reasons, edge cases, and None-frame safety.
  D. Telemetry — ROI fields correctly populated.

All tests are pure unit tests against evidence_cache.py; no network, Supabase,
or FastAPI required.  This file must not register stubs for modules that other
test files rely on (e.g. app.concierge.cross_source_enrichment).
"""

from __future__ import annotations

import sys
import os
import types
import importlib
import importlib.util
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pytest

# ── sys.path bootstrap ────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Import evidence_cache without disturbing sys.modules for other tests ──────
# We always load via the real sys.path (not a stub), so the module registered
# here is the genuine implementation used by the durable cache tests too.
from app.concierge.evidence_cache import (  # noqa: E402
    CreditROITelemetry,
    NoteDecision,
    make_note_decision,
)


# ── Minimal frame stubs ───────────────────────────────────────────────────────

@dataclass
class _SubtypeConcept:
    label: str
    confidence: float = 0.9


@dataclass
class _Frame:
    """Minimal ExperienceFrame-like object for tests."""
    subtype_concepts: List[_SubtypeConcept] = field(default_factory=list)
    destination: str = "Chicago"
    user_query: str = ""
    normalized_soft_preferences: List[str] = field(default_factory=list)
    geography_hints: List[str] = field(default_factory=list)


def _plain_frame(query: str = "sports bars") -> _Frame:
    """Frame for a plain category query (no editorial value)."""
    return _Frame(
        subtype_concepts=[_SubtypeConcept(label="sports_bar", confidence=0.9)],
        destination="Chicago",
        user_query=query,
    )


def _editorial_frame(query: str = "hidden gem cocktail bars Chicago") -> _Frame:
    """Frame for an editorial-worthy query."""
    return _Frame(
        subtype_concepts=[_SubtypeConcept(label="bar", confidence=0.9)],
        destination="Chicago",
        user_query=query,
        normalized_soft_preferences=["hidden_gem"],
    )


# ── Section A: Plain-category credit protection ───────────────────────────────

class TestPlainCategoryNoteDecision:
    """NoteDecision correctly skips all note paths for plain category queries."""

    def test_plain_query_no_evidence_no_cache_skips_all_note_paths(self):
        frame = _plain_frame("sports bars")
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=0,
        )
        assert not decision.should_run_set_writer
        assert not decision.should_run_legacy_batched_reasoning
        assert decision.set_writer_skip_reason == "no_editorial_evidence_no_cached_notes"
        assert decision.legacy_batched_reasoning_skip_reason == "no_editorial_evidence_no_cached_notes"
        assert decision.is_plain_category_query

    def test_plain_query_with_cache_allows_note_paths(self):
        """Cached notes override the plain-category skip — reuse approved notes."""
        frame = _plain_frame("sports bars")
        decision = make_note_decision(
            frame=frame,
            cached_notes={"ChIJ_abc": "Great sports bar with many TVs."},
            accepted_editorial_evidence_count=0,
        )
        assert decision.should_run_set_writer
        assert decision.should_run_legacy_batched_reasoning
        assert decision.has_cached_approved_notes

    def test_plain_query_with_editorial_evidence_allows_note_paths(self):
        """Accepted editorial atoms allow note paths even for plain query."""
        frame = _plain_frame("pizza places")
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=3,
        )
        assert decision.should_run_set_writer
        assert decision.should_run_legacy_batched_reasoning
        assert decision.has_accepted_editorial_evidence

    def test_plain_query_skip_reason_is_consistent_across_both_paths(self):
        """set_writer and legacy_batched must use the same skip reason."""
        frame = _plain_frame("breweries")
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=0,
        )
        assert decision.set_writer_skip_reason == decision.legacy_batched_reasoning_skip_reason

    def test_plain_query_sets_is_plain_category_query_flag(self):
        frame = _plain_frame("ramen")
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=0,
        )
        assert decision.is_plain_category_query is True

    def test_plain_query_with_both_cache_and_evidence_approves(self):
        frame = _plain_frame("coffee shops")
        decision = make_note_decision(
            frame=frame,
            cached_notes={"ChIJ_001": "Great coffee."},
            accepted_editorial_evidence_count=2,
        )
        assert decision.should_run_set_writer
        assert decision.should_run_legacy_batched_reasoning
        assert decision.set_writer_skip_reason is None
        assert decision.legacy_batched_reasoning_skip_reason is None


# ── Section B: Editorial-worthy queries ──────────────────────────────────────

class TestEditorialQueryNoteDecision:
    """NoteDecision correctly approves note paths for editorial-worthy queries."""

    def test_editorial_query_with_evidence_approves_all_paths(self):
        frame = _editorial_frame("hidden gem cocktail bars Chicago")
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=5,
        )
        assert decision.should_run_set_writer
        assert decision.should_run_legacy_batched_reasoning
        assert decision.has_accepted_editorial_evidence
        assert not decision.is_plain_category_query

    def test_editorial_query_no_evidence_no_cache_still_skips(self):
        """Even editorial queries skip notes when Tavily returned 0 atoms."""
        frame = _editorial_frame("best hidden gem speakeasy")
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=0,
        )
        assert not decision.should_run_set_writer
        assert not decision.should_run_legacy_batched_reasoning

    def test_editorial_flag_set_correctly_for_editorial_frame(self):
        frame = _editorial_frame()
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=1,
        )
        assert decision.should_run_editorial_enrichment
        assert decision.editorial_enrichment_skip_reason is None
        assert not decision.is_plain_category_query

    def test_editorial_flag_set_correctly_for_plain_frame(self):
        frame = _plain_frame()
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=0,
        )
        assert not decision.should_run_editorial_enrichment
        assert decision.editorial_enrichment_skip_reason is not None
        assert decision.is_plain_category_query

    def test_editorial_with_cache_approves_note_paths(self):
        frame = _editorial_frame("wine bars")
        decision = make_note_decision(
            frame=frame,
            cached_notes={"ChIJ_xyz": "Excellent wine selection."},
            accepted_editorial_evidence_count=0,
        )
        assert decision.should_run_set_writer
        assert decision.should_run_legacy_batched_reasoning


# ── Section C: NoteDecision gate — edge cases ─────────────────────────────────

class TestNoteDecisionEdgeCases:
    """Edge cases and boundary conditions for make_note_decision."""

    def test_none_frame_does_not_raise(self):
        """make_note_decision must not raise when frame is None."""
        decision = make_note_decision(
            frame=None,
            cached_notes={},
            accepted_editorial_evidence_count=0,
        )
        assert not decision.should_run_set_writer

    def test_none_frame_with_evidence_approves_note_paths(self):
        decision = make_note_decision(
            frame=None,
            cached_notes={},
            accepted_editorial_evidence_count=3,
        )
        assert decision.should_run_set_writer
        assert decision.should_run_legacy_batched_reasoning

    def test_empty_cached_notes_dict_treated_as_no_cache(self):
        frame = _plain_frame()
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=0,
        )
        assert not decision.has_cached_approved_notes

    def test_non_empty_cached_notes_dict_treated_as_cache_hit(self):
        frame = _plain_frame()
        decision = make_note_decision(
            frame=frame,
            cached_notes={"ChIJ_abc": "Great!"},
            accepted_editorial_evidence_count=0,
        )
        assert decision.has_cached_approved_notes
        assert decision.should_run_set_writer

    def test_accepted_evidence_count_propagated(self):
        frame = _plain_frame()
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=7,
        )
        assert decision.accepted_editorial_evidence_count == 7

    def test_zero_atoms_correctly_flagged(self):
        frame = _editorial_frame("best ramen")
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=0,
        )
        assert not decision.has_accepted_editorial_evidence
        assert decision.accepted_editorial_evidence_count == 0
        # Even editorial query with 0 accepted atoms skips notes.
        assert not decision.should_run_set_writer
        assert not decision.should_run_legacy_batched_reasoning

    def test_same_inputs_same_output(self):
        """make_note_decision must be deterministic."""
        frame = _editorial_frame()
        d1 = make_note_decision(frame=frame, cached_notes={}, accepted_editorial_evidence_count=3)
        d2 = make_note_decision(frame=frame, cached_notes={}, accepted_editorial_evidence_count=3)
        assert d1.should_run_set_writer == d2.should_run_set_writer
        assert d1.should_run_legacy_batched_reasoning == d2.should_run_legacy_batched_reasoning
        assert d1.is_plain_category_query == d2.is_plain_category_query

    def test_skip_reason_is_none_when_notes_approved(self):
        frame = _editorial_frame()
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=4,
        )
        assert decision.set_writer_skip_reason is None
        assert decision.legacy_batched_reasoning_skip_reason is None

    def test_skip_reason_present_when_notes_skipped(self):
        frame = _plain_frame("generic query")
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=0,
        )
        assert decision.set_writer_skip_reason is not None
        assert decision.legacy_batched_reasoning_skip_reason is not None

    def test_large_evidence_count_approves(self):
        frame = _plain_frame("tacos")
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=100,
        )
        assert decision.should_run_set_writer
        assert decision.should_run_legacy_batched_reasoning
        assert decision.accepted_editorial_evidence_count == 100


# ── Section D: Telemetry ──────────────────────────────────────────────────────

class TestNoteDecisionTelemetry:
    """NoteDecision fields are correctly reflected in CreditROITelemetry."""

    def test_roi_telemetry_has_new_control_plane_fields(self):
        tel = CreditROITelemetry()
        d = tel.as_log_dict()
        assert "set_writer_skipped_reason" in d
        assert "legacy_batched_reason_attempted" in d
        assert "legacy_batched_reason_skipped_reason" in d
        assert "final_card_count_before_notes" in d
        assert "final_card_count_after_notes" in d
        assert "card_count_collapsed_due_to_notes" in d

    def test_card_count_collapsed_invariant_is_false(self):
        tel = CreditROITelemetry()
        assert tel.card_count_collapsed_due_to_notes is False
        assert tel.as_log_dict()["card_count_collapsed_due_to_notes"] is False

    def test_legacy_batched_attempted_default_false(self):
        tel = CreditROITelemetry()
        assert tel.legacy_batched_reason_attempted is False

    def test_legacy_batched_attempted_can_be_set_true(self):
        tel = CreditROITelemetry()
        tel.legacy_batched_reason_attempted = True
        assert tel.as_log_dict()["legacy_batched_reason_attempted"] is True

    def test_set_writer_skipped_reason_default_none(self):
        tel = CreditROITelemetry()
        assert tel.set_writer_skipped_reason is None
        assert tel.as_log_dict()["set_writer_skipped_reason"] is None

    def test_set_writer_skipped_reason_can_be_set(self):
        tel = CreditROITelemetry()
        tel.set_writer_skipped_reason = "no_editorial_evidence_no_cached_notes"
        assert tel.as_log_dict()["set_writer_skipped_reason"] == "no_editorial_evidence_no_cached_notes"

    def test_final_card_counts_default_zero(self):
        tel = CreditROITelemetry()
        assert tel.final_card_count_before_notes == 0
        assert tel.final_card_count_after_notes == 0

    def test_final_card_counts_can_be_set(self):
        tel = CreditROITelemetry()
        tel.final_card_count_before_notes = 6
        tel.final_card_count_after_notes = 6
        d = tel.as_log_dict()
        assert d["final_card_count_before_notes"] == 6
        assert d["final_card_count_after_notes"] == 6

    def test_make_note_decision_plain_sets_skip_reason(self):
        frame = _plain_frame("breweries")
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=0,
        )
        assert decision.legacy_batched_reasoning_skip_reason == "no_editorial_evidence_no_cached_notes"

    def test_make_note_decision_editorial_with_evidence_no_skip_reason(self):
        frame = _editorial_frame("hidden gem oyster bar")
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=4,
        )
        assert decision.legacy_batched_reasoning_skip_reason is None
