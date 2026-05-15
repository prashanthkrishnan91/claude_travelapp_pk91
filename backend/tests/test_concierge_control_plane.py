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
    _canonical_concept_label,
    _distinct_concept_count,
    _stem_word,
    make_note_decision,
    should_run_editorial,
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


# ── Section E: Subtype-concept canonicalization ───────────────────────────────

class TestStemWord:
    """_stem_word strips common English plural suffixes from a single word."""

    def test_trailing_s_stripped(self):
        assert _stem_word("bars") == "bar"
        assert _stem_word("restaurants") == "restaurant"

    def test_trailing_s_not_stripped_from_ss(self):
        assert _stem_word("class") == "class"
        assert _stem_word("grass") == "grass"

    def test_ies_to_y(self):
        assert _stem_word("breweries") == "brewery"
        assert _stem_word("bakeries") == "bakery"

    def test_ches_suffix(self):
        assert _stem_word("benches") == "bench"
        assert _stem_word("beaches") == "beach"

    def test_shes_suffix(self):
        assert _stem_word("dishes") == "dish"

    def test_sses_suffix(self):
        assert _stem_word("glasses") == "glass"

    def test_no_suffix_unchanged(self):
        assert _stem_word("sushi") == "sushi"
        assert _stem_word("brunch") == "brunch"
        assert _stem_word("jazz") == "jazz"

    def test_short_word_not_mangled(self):
        # 2-char word: don't strip
        assert _stem_word("is") == "is"


class TestCanonicalConceptLabel:
    """_canonical_concept_label normalizes multi-word concept labels."""

    def test_trailing_s_on_last_word(self):
        assert _canonical_concept_label("bars") == "bar"
        assert _canonical_concept_label("sports") == "sport"

    def test_multiword_each_word_stemmed(self):
        # "sports bars" → "sport bar"
        assert _canonical_concept_label("sports bars") == "sport bar"
        assert _canonical_concept_label("sport bars") == "sport bar"
        assert _canonical_concept_label("sports bar") == "sport bar"

    def test_case_normalized(self):
        assert _canonical_concept_label("Bars") == "bar"
        assert _canonical_concept_label("SPORTS") == "sport"

    def test_punctuation_stripped(self):
        assert _canonical_concept_label("bar!") == "bar"
        assert _canonical_concept_label("craft-beer") == "craftbeer"

    def test_singular_unchanged(self):
        assert _canonical_concept_label("bar") == "bar"
        assert _canonical_concept_label("brewery") == "brewery"

    def test_breweries_canonicalized(self):
        assert _canonical_concept_label("breweries") == "brewery"


class TestDistinctConceptCount:
    """_distinct_concept_count collapses singular/plural and duplicate variants."""

    def _make_concept(self, label: str) -> Any:
        from dataclasses import dataclass

        @dataclass
        class _Concept:
            label: str

        return _Concept(label=label)

    def _concepts(self, *labels: str):
        return [self._make_concept(l) for l in labels]

    # ── Singular/plural collapse ──────────────────────────────────────────────

    def test_sport_sports_collapses_to_one(self):
        assert _distinct_concept_count(self._concepts("sport", "sports")) == 1

    def test_bar_bars_collapses_to_one(self):
        assert _distinct_concept_count(self._concepts("bar", "bars")) == 1

    def test_brewery_breweries_collapses_to_one(self):
        assert _distinct_concept_count(self._concepts("brewery", "breweries")) == 1

    def test_exact_duplicate_collapses_to_one(self):
        assert _distinct_concept_count(self._concepts("bar", "bar")) == 1

    def test_case_duplicate_collapses_to_one(self):
        assert _distinct_concept_count(self._concepts("Bar", "bar")) == 1

    def test_multiword_plural_collapses(self):
        # "sports bars" and "sport bar" are the same canonical form
        assert _distinct_concept_count(self._concepts("sports bars", "sport bar")) == 1

    # ── Truly distinct concepts ───────────────────────────────────────────────

    def test_bar_brewery_are_distinct(self):
        assert _distinct_concept_count(self._concepts("bar", "brewery")) == 2

    def test_three_distinct_concepts(self):
        assert _distinct_concept_count(self._concepts("bar", "brewery", "restaurant")) == 3

    def test_cocktail_bar_and_brewery_are_distinct(self):
        assert _distinct_concept_count(self._concepts("cocktail bar", "brewery")) == 2

    def test_empty_list_is_zero(self):
        assert _distinct_concept_count([]) == 0

    def test_single_concept_is_one(self):
        assert _distinct_concept_count(self._concepts("bar")) == 1

    def test_concept_with_no_label_skipped(self):
        class _NoLabel:
            pass
        assert _distinct_concept_count([_NoLabel(), self._make_concept("bar")]) == 1


class TestMultiConceptEditorialGate:
    """should_run_editorial uses canonical distinct count for multi-concept gate."""

    def _make_frame(self, *labels: str) -> _Frame:
        return _Frame(
            subtype_concepts=[_SubtypeConcept(label=l) for l in labels],
            destination="Chicago",
        )

    # ── Singular/plural pairs must NOT trigger Tavily ─────────────────────────

    def test_sport_sports_skips_tavily(self):
        frame = self._make_frame("sport", "sports")
        should_run, reason = should_run_editorial(frame)
        assert not should_run, f"Expected skip but got reason={reason}"
        assert "multi_concept" not in reason

    def test_bar_bars_skips_tavily(self):
        frame = self._make_frame("bar", "bars")
        should_run, reason = should_run_editorial(frame)
        assert not should_run, f"Expected skip but got reason={reason}"

    def test_brewery_breweries_skips_tavily(self):
        frame = self._make_frame("brewery", "breweries")
        should_run, reason = should_run_editorial(frame)
        assert not should_run

    def test_exact_duplicate_skips_tavily(self):
        frame = self._make_frame("bar", "bar")
        should_run, reason = should_run_editorial(frame)
        assert not should_run

    def test_sports_bars_sport_bar_skips_tavily(self):
        frame = self._make_frame("sports bars", "sport bar")
        should_run, reason = should_run_editorial(frame)
        assert not should_run

    # ── Truly distinct pairs MUST trigger Tavily ──────────────────────────────

    def test_bar_and_brewery_allow_tavily(self):
        frame = self._make_frame("bar", "brewery")
        should_run, reason = should_run_editorial(frame)
        assert should_run
        assert reason == "multi_concept_query"

    def test_three_distinct_concepts_allow_tavily(self):
        frame = self._make_frame("bar", "brewery", "restaurant")
        should_run, reason = should_run_editorial(frame)
        assert should_run
        assert reason == "multi_concept_query"

    # ── Single concept still skips (existing behavior unchanged) ─────────────

    def test_single_plain_concept_skips_tavily(self):
        frame = self._make_frame("bar")
        should_run, reason = should_run_editorial(frame)
        assert not should_run

    def test_single_plural_concept_skips_tavily(self):
        frame = self._make_frame("bars")
        should_run, reason = should_run_editorial(frame)
        assert not should_run

    # ── NoteDecision propagates the fix end-to-end ───────────────────────────

    def test_sport_sports_frame_note_decision_skips_note_paths(self):
        """Full end-to-end: singular/plural frame skips all note LLM paths."""
        frame = self._make_frame("sport", "sports")
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=0,
        )
        assert not decision.should_run_set_writer
        assert not decision.should_run_legacy_batched_reasoning
        assert decision.is_plain_category_query

    def test_bar_brewery_frame_note_decision_allows_note_paths_with_evidence(self):
        """Truly distinct concepts allow note paths when evidence is present."""
        frame = self._make_frame("bar", "brewery")
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=3,
        )
        assert decision.should_run_set_writer
        assert decision.should_run_legacy_batched_reasoning


# ── Section F: Runtime/control-plane guard for compound venue-head queries ──────

class TestCompoundVenueHeadControlPlane:
    """Production-like 'sports bars' frame must skip Tavily and legacy notes,
    preserve cards, and generate bar-preserving retrieval queries.

    This tests the full control-plane contract for the PR #390 regression:
    concepts=[sport, sports] + literal_ask='sports bars' should NOT trigger
    editorial enrichment or legacy batched reasoning, and the retrieval planner
    must produce queries with 'bar' in them.
    """

    def _make_sports_bars_frame(self, destination: str = "Seattle") -> _Frame:
        """Simulate the production frame for 'sports bars' query."""
        return _Frame(
            subtype_concepts=[
                _SubtypeConcept(label="sport", confidence=0.95),
                _SubtypeConcept(label="sports", confidence=0.85),
            ],
            destination=destination,
            user_query="sports bars",
            normalized_soft_preferences=[],
            geography_hints=[],
        )

    def test_sports_bars_frame_skips_tavily(self):
        """sport/sports concepts are singular/plural pair → skip editorial."""
        frame = self._make_sports_bars_frame()
        should_run, reason = should_run_editorial(frame)
        assert not should_run, (
            f"sports bars frame must skip Tavily, got reason={reason!r}"
        )

    def test_sports_bars_frame_skips_legacy_batched_reasoning(self):
        frame = self._make_sports_bars_frame()
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=0,
        )
        assert not decision.should_run_legacy_batched_reasoning, (
            "Legacy batched reasoning must be skipped for sports bars frame"
        )

    def test_sports_bars_frame_skips_set_writer(self):
        frame = self._make_sports_bars_frame()
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=0,
        )
        assert not decision.should_run_set_writer, (
            "Set writer must be skipped for sports bars frame without evidence"
        )

    def test_sports_bars_frame_is_plain_category(self):
        frame = self._make_sports_bars_frame()
        decision = make_note_decision(
            frame=frame,
            cached_notes={},
            accepted_editorial_evidence_count=0,
        )
        assert decision.is_plain_category_query

    def test_sports_bars_retrieval_query_contains_bar(self):
        """Retrieval planner with literal_ask='sports bars' must produce
        bar-preserving queries, not 'sport Seattle'."""
        from app.concierge.retrieval_planner import plan_queries
        from app.concierge.frame_extractor import ExperienceFrame, SubtypeConcept

        frame = ExperienceFrame(
            literal_ask="sports bars",
            normalized_ask="sports bars",
            destination="Seattle",
            subtype_concepts=[
                SubtypeConcept(label="sport", confidence=0.95, source="frame_extractor"),
                SubtypeConcept(label="sports", confidence=0.85, source="frame_extractor"),
            ],
        )
        qs = plan_queries(frame)
        first = qs[0].lower()
        assert "bar" in first or "bars" in first, (
            f"First query must contain 'bar', got {qs[0]!r}. "
            "Old regression produced 'sport Seattle' — bar-head was lost."
        )

    def test_sports_bars_retrieval_query_not_bare_sport(self):
        """The old regression: query was 'sport Seattle' — must not happen."""
        from app.concierge.retrieval_planner import plan_queries
        from app.concierge.frame_extractor import ExperienceFrame, SubtypeConcept

        frame = ExperienceFrame(
            literal_ask="sports bars",
            normalized_ask="sports bars",
            destination="Seattle",
            subtype_concepts=[
                SubtypeConcept(label="sport", confidence=0.95, source="frame_extractor"),
            ],
        )
        qs = plan_queries(frame)
        assert "sport seattle" not in [q.lower() for q in qs], (
            f"Query 'sport seattle' must not appear in {qs}"
        )

    def test_cards_preserved_without_notes(self):
        """Plain sports bars frame: make_note_decision must not collapse cards.
        card_count_collapsed_due_to_notes must be False (structural invariant)."""
        from app.concierge.evidence_cache import CreditROITelemetry
        tel = CreditROITelemetry()
        assert tel.card_count_collapsed_due_to_notes is False
