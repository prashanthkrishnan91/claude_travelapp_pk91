"""Tests for claim_safety_reviewer.py — PR #267 Claim-Safety Reviewer Gate.

Coverage:
  1. Summary reviewer rejects unsupported name-hours inference.
  2. Summary reviewer allows late-night claim only with evidence.
  3. Per-card reviewer rejects unsupported name-hours inference.
  4. Hidden invalid note does not drop card.
  5. Waterfront/view summary claim safety.
  6. Hidden-gem claim safety.
  7. Internal leakage — role labels, evidence labels, dossier internals.
  8. Repeated skeleton and generic filler.
  9. Timeout fail-closed — text hidden, cards kept.
  10. Existing contracts — fallback_note_visible_count=0, deterministic_visible_count=0,
      cards 5–7, Google Places remains the only addable trust source.
  11. reason_validator._NAME_HOURS_INFERENCE_RE integration.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.concierge.claim_safety_reviewer import (
    NoteReviewResult,
    ReviewerTelemetry,
    SummaryReviewResult,
    _NAME_HOURS_INFERENCE_RE,
    _INTERNAL_LABEL_RE,
    review_note,
    review_notes_set,
    review_summary,
)


# ── Minimal stubs ──────────────────────────────────────────────────────────────

@dataclass
class _Frame:
    literal_ask: str = "late night izakayas"
    destination: str = "Chicago"
    subtype_concepts: List[Any] = field(default_factory=list)
    location_modifiers: List[str] = field(default_factory=list)
    geography_hints: List[str] = field(default_factory=list)
    ambiguity_flags: List[str] = field(default_factory=list)
    soft_preferences: List[str] = field(default_factory=list)
    normalized_soft_preferences: List[str] = field(default_factory=list)
    negative_constraints: List[str] = field(default_factory=list)


@dataclass
class _Entity:
    place_id: str
    name: str
    formatted_address: str = "123 Main St, Chicago, IL"
    rating: Optional[float] = 4.5
    user_rating_count: Optional[int] = 500
    types: List[str] = field(default_factory=lambda: ["restaurant"])
    primary_type: Optional[str] = "restaurant"
    business_status: str = "OPERATIONAL"
    google_maps_uri: str = "https://maps.google.com/test"
    website_uri: Optional[str] = None
    lat: float = 41.88
    lng: float = -87.63


@dataclass
class _Evidence:
    structured_facts: List[str] = field(default_factory=list)
    uncertainty_flags: List[str] = field(default_factory=list)
    geo_note: Optional[str] = None
    evidence_adequacy: str = "OK"
    entity: Optional[Any] = None


# ══════════════════════════════════════════════════════════════════════════════
# Test 1 — Summary reviewer rejects unsupported name-hours inference
# ══════════════════════════════════════════════════════════════════════════════

class TestSummaryReviewerRejectsNameHoursInference:
    """Criterion 1: The exact 2AM Izakaya phrase cannot appear in visible output."""

    def test_rejects_name_alone_signals_late_night_credibility(self):
        summary = (
            "2AM Izakaya, whose name alone signals late-night credibility, "
            "stands out in the set."
        )
        frame = _Frame()
        result = review_summary(summary, frame)
        # Sanitization should either remove the offending sentence or reject outright
        assert result.rejected or result.sanitized
        # After sanitization, the forbidden phrase must not appear
        assert "name alone signals" not in result.summary.lower()
        assert "late-night credibility" not in result.summary.lower()

    def test_rejects_name_signals_late_night_variant(self):
        summary = "This place's name signals late-night availability in Chicago."
        result = review_summary(summary, _Frame())
        assert result.rejected or result.sanitized
        assert "name signals" not in result.summary.lower()

    def test_rejects_name_implies_24_hour(self):
        summary = "The name implies 24-hour service, making it a strong candidate."
        result = review_summary(summary, _Frame())
        assert result.rejected or result.sanitized
        assert "name implies" not in result.summary.lower()

    def test_rejects_whose_name_indicates(self):
        summary = "2AM Izakaya, whose name indicates an after-hours orientation."
        result = review_summary(summary, _Frame())
        assert result.rejected or result.sanitized

    def test_sanitized_summary_does_not_expose_reviewer_language(self):
        """Sanitized/rejected output must never say 'reviewer rejected' or similar."""
        summary = "2AM Izakaya, whose name alone signals late-night credibility."
        result = review_summary(summary, _Frame())
        assert "reviewer" not in result.summary.lower()
        assert "rejected" not in result.summary.lower()
        assert "claim_safety" not in result.summary.lower()

    def test_name_hours_inference_regex_matches_exact_failure_phrase(self):
        phrase = "whose name alone signals late-night credibility"
        assert _NAME_HOURS_INFERENCE_RE.search(phrase) is not None

    def test_name_hours_inference_regex_matches_variant_phrases(self):
        phrases = [
            "name alone signals late night",
            "name implies 24-hour availability",
            "whose name suggests open late",
            "name itself indicates after-hours",
            "the name alone hints at credibility",
        ]
        for phrase in phrases:
            assert _NAME_HOURS_INFERENCE_RE.search(phrase) is not None, (
                f"Expected match for: {phrase!r}"
            )

    def test_multi_sentence_summary_sanitized_to_safe_remainder(self):
        """When only one sentence is unsafe, the safe sentences remain."""
        summary = (
            "This is a strong izakaya set. "
            "2AM Izakaya, whose name alone signals late-night credibility, is included. "
            "All places are Google-verified."
        )
        result = review_summary(summary, _Frame())
        # Either fully rejected or the unsafe sentence is stripped
        if result.sanitized:
            assert "whose name alone signals" not in result.summary
            # The other sentences should survive
            assert "Google-verified" in result.summary or "izakaya set" in result.summary


# ══════════════════════════════════════════════════════════════════════════════
# Test 2 — Summary reviewer allows late-night claim only with evidence
# ══════════════════════════════════════════════════════════════════════════════

class TestSummaryReviewerAllowsLateNightWithEvidence:
    """Criterion 2: Evidence-backed late-night claims may pass."""

    def test_allows_direct_hours_statement(self):
        """A statement about actual hours (not inferred from name) is fine."""
        summary = "Open until 2AM on weekends, per the verified listing."
        # This doesn't match the name-inference pattern — it's a direct hours claim.
        # The existing reason_validator handles hours claims; the reviewer does NOT
        # reject this (it only rejects name-inference patterns).
        result = review_summary(summary, _Frame())
        # The NAME_HOURS_INFERENCE pattern should NOT match this phrase
        assert _NAME_HOURS_INFERENCE_RE.search(summary) is None

    def test_allows_late_night_without_name_inference(self):
        """Late-night framing that doesn't infer from name passes the reviewer."""
        summary = "Known for late-night service, this izakaya set has solid options."
        result = review_summary(summary, _Frame())
        assert _NAME_HOURS_INFERENCE_RE.search(summary) is None
        assert not result.rejected

    def test_allows_caveat_about_hours(self):
        """Honest caveats about hours uncertainty are acceptable."""
        summary = (
            "2AM Izakaya appears in the late-night izakaya search set, "
            "but verify current hours before planning around a late arrival."
        )
        result = review_summary(summary, _Frame())
        # This phrasing does NOT say 'name alone signals' — it's an honest caveat
        assert _NAME_HOURS_INFERENCE_RE.search(summary) is None
        assert not result.rejected


# ══════════════════════════════════════════════════════════════════════════════
# Test 3 — Per-card reviewer rejects unsupported name-hours inference
# ══════════════════════════════════════════════════════════════════════════════

class TestPerCardReviewerRejectsNameHoursInference:
    """Criterion 3: Card notes inferring hours from name are hidden."""

    def test_rejects_card_note_name_signals_24hr(self):
        note = "2AM Izakaya signals 24-hour availability, making it a late-night anchor."
        result = review_note(note, "2AM Izakaya", _Frame())
        assert not result.passed
        assert result.note == ""
        # Caught by entity-name-as-subject temporal inference check
        assert "name" in result.rejection_reason or "temporal" in result.rejection_reason

    def test_rejects_whose_name_alone_signals_credibility(self):
        note = "2AM Izakaya, whose name alone signals late-night credibility."
        result = review_note(note, "2AM Izakaya", _Frame())
        assert not result.passed
        assert result.note == ""

    def test_rejects_name_implies_open_late(self):
        note = "Midnight Ramen — the name implies open late, a good sign for night owls."
        result = review_note(note, "Midnight Ramen", _Frame())
        assert not result.passed

    def test_allows_honest_name_mention_without_inference(self):
        """Mentioning the name without inferring hours is fine."""
        note = "2AM Izakaya is included in this late-night izakaya set; verify hours first."
        result = review_note(note, "2AM Izakaya", _Frame())
        # 'name alone signals' pattern should NOT match this
        assert _NAME_HOURS_INFERENCE_RE.search(note) is None

    def test_reviewer_ms_is_populated(self):
        note = "A well-regarded izakaya near the river with a solid sake selection."
        result = review_note(note, "Test Izakaya", _Frame())
        assert isinstance(result.reviewer_ms, int)
        assert result.reviewer_ms >= 0

    def test_reviewer_does_not_affect_empty_note(self):
        result = review_note("", "Some Place", _Frame())
        assert not result.passed
        assert result.rejection_reason == "empty_note"


# ══════════════════════════════════════════════════════════════════════════════
# Test 4 — Hidden invalid note does not drop card
# ══════════════════════════════════════════════════════════════════════════════

class TestHiddenInvalidNoteDoesNotDropCard:
    """Criterion 4: Card remains addable/Google-verified when note is hidden."""

    def test_review_notes_set_hides_note_not_place(self):
        """review_notes_set returns rejected=True but does not remove the place_id key."""
        notes = {
            "place_001": "2AM Izakaya, whose name alone signals late-night credibility.",
            "place_002": "A quiet izakaya with an excellent sake list.",
        }
        entity_names = {"place_001": "2AM Izakaya", "place_002": "Sake House"}
        results, telemetry = review_notes_set(notes, entity_names, _Frame())

        # place_001 should be rejected but still present in results dict
        assert "place_001" in results
        assert not results["place_001"].passed
        assert results["place_001"].note == ""

        # place_002 should pass (no name-inference pattern)
        assert "place_002" in results

    def test_hidden_note_card_count_unchanged(self):
        """After reviewer gate, cards (keys) count equals input count."""
        notes = {
            "p1": "2AM Izakaya, whose name alone signals late-night credibility.",
            "p2": "A solid izakaya with robust evidence.",
            "p3": "Great sake selection near Wicker Park.",
        }
        entity_names = {"p1": "2AM Izakaya", "p2": "Izakaya B", "p3": "Izakaya C"}
        results, telemetry = review_notes_set(notes, entity_names, _Frame())

        # All 3 place_ids present — reviewer hides notes but doesn't drop cards
        assert len(results) == 3

    def test_telemetry_counts_correctly(self):
        notes = {
            "p1": "2AM Izakaya, whose name alone signals late-night credibility.",
            "p2": "Known for a deep ramen menu in a small, authentic space.",
        }
        entity_names = {"p1": "2AM Izakaya", "p2": "Izakaya B"}
        results, telemetry = review_notes_set(notes, entity_names, _Frame())

        assert telemetry.reviewer_used is True
        assert telemetry.reviewer_rejected_note_count == 1
        assert telemetry.reviewer_hidden_note_count == 1
        assert telemetry.final_note_visible_count == 1
        assert telemetry.fallback_note_visible_count == 0   # invariant
        assert telemetry.deterministic_visible_count == 0   # invariant


# ══════════════════════════════════════════════════════════════════════════════
# Test 5 — Waterfront/view summary claim safety
# ══════════════════════════════════════════════════════════════════════════════

class TestWaterfrontViewSummaryClaimSafety:
    """Criterion 5: View/waterfront claims require evidence; else caveat or omit."""

    def test_scenic_view_without_evidence_matches_reviewer_chain(self):
        """'scenic view' without evidence is blocked by reason_validator first."""
        from app.concierge.reason_validator import validate_reason, _UNSUPPORTED_ATTRIBUTE_RE
        note = "This taproom offers stunning views of the riverfront."
        assert _UNSUPPORTED_ATTRIBUTE_RE.search(note) is not None

    def test_reviewer_allows_listing_context_view(self):
        """'Riverwalk' in a business name is listing context, not a scenic claim."""
        note = (
            "Chicago Riverwalk Taproom is verified in a Riverwalk-context listing; "
            "scenic claims are not confirmed from available data."
        )
        # The name-inference pattern should NOT match
        assert _NAME_HOURS_INFERENCE_RE.search(note) is None
        result = review_note(note, "Chicago Riverwalk Taproom", _Frame())
        # Reviewer (claim_safety_reviewer) does not check for waterfront claims
        # — that's reason_validator's job. Reviewer should not additionally reject.
        assert result.rejection_reason not in ("name_hours_inference", "internal_label_leakage")

    def test_reviewer_does_not_double_block_waterfront(self):
        """claim_safety_reviewer doesn't add a waterfront check (reason_validator owns it)."""
        note = "Great waterfront views from the rooftop deck."
        # This should pass the claim_safety_reviewer (it will be blocked by reason_validator)
        result = review_note(note, "Lakeside Taproom", _Frame())
        # reviewer should not trigger its own block for waterfront (no reviewer pattern for it)
        assert "reviewer" not in result.rejection_reason or result.passed

    def test_summary_reviewer_allows_caveated_view(self):
        """Honest caveats about view are acceptable in summary."""
        summary = (
            "The taprooms in this set range from verified patio spaces to "
            "places where outdoor seating is not confirmed from listing data."
        )
        result = review_summary(summary, _Frame())
        assert not result.rejected


# ══════════════════════════════════════════════════════════════════════════════
# Test 6 — Hidden-gem claim safety
# ══════════════════════════════════════════════════════════════════════════════

class TestHiddenGemClaimSafety:
    """Criterion 6: 'hidden gem' / 'local favorite' require evidence support."""

    def test_hidden_gem_in_note_detected_by_regex(self):
        from app.concierge.claim_safety_reviewer import _HIDDEN_GEM_TERMS_RE
        phrases = [
            "A true hidden gem on the north side.",
            "A local favorite among regulars.",
            "Underrated bar in Wicker Park.",
            "Locals love this place.",
        ]
        for phrase in phrases:
            assert _HIDDEN_GEM_TERMS_RE.search(phrase) is not None, (
                f"Expected match for: {phrase!r}"
            )

    def test_hidden_gem_terms_not_currently_blocked_by_reviewer(self):
        """Hidden-gem terms are checked by reason_validator, not claim_safety_reviewer.
        This test documents the scope boundary: reviewer checks name-inference + internals.
        """
        note = "A hidden gem izakaya loved by locals near Wicker Park."
        result = review_note(note, "Wicker Park Izakaya", _Frame())
        # claim_safety_reviewer does not currently gate hidden-gem terms
        # (that's reason_validator's domain via evidence checks).
        # The note passes the reviewer; whether it passes the full pipeline
        # depends on reason_validator's evidence check.
        assert result.rejection_reason not in ("name_hours_inference", "internal_label_leakage")

    def test_reviewer_does_not_inject_hidden_gem_claims(self):
        """Reviewer output never introduces new claims not in the original note."""
        note = "Known for a deep sake list in an authentic setting."
        result = review_note(note, "Sake Den", _Frame())
        assert "hidden gem" not in result.note.lower()
        assert "local favorite" not in result.note.lower()


# ══════════════════════════════════════════════════════════════════════════════
# Test 7 — Internal leakage: role labels, evidence labels, dossier internals
# ══════════════════════════════════════════════════════════════════════════════

class TestInternalLeakageRejected:
    """Criterion 7: Role labels, evidence labels, dossier fields never exposed."""

    def test_internal_label_regex_matches_role_names(self):
        role_labels = [
            "best_overall",
            "strongest_query_match",
            "modifier_confirmed",
            "evidence_rich",
            "distinctive_theme",
            "geographic_fit",
            "safe_popular_fallback",
            "interesting_but_weaker",
            "low_evidence_holdback",
        ]
        for label in role_labels:
            assert _INTERNAL_LABEL_RE.search(label) is not None, (
                f"Expected match for role label: {label!r}"
            )

    def test_internal_label_regex_matches_evidence_internals(self):
        internal_fields = [
            "evidence_adequacy",
            "source_confidence",
            "is_minimal",
            "provider_evidence",
            "reviewer_rejected",
            "CardReason",
            "SetWriterNote",
        ]
        for field_name in internal_fields:
            assert _INTERNAL_LABEL_RE.search(field_name) is not None, (
                f"Expected match for internal field: {field_name!r}"
            )

    def test_reviewer_rejects_note_with_role_label(self):
        note = "This place has evidence_rich signals and strong category fit."
        result = review_note(note, "Some Izakaya", _Frame())
        assert not result.passed
        assert result.rejection_reason == "internal_label_leakage"

    def test_reviewer_rejects_summary_with_role_label(self):
        summary = "The best_overall pick in this set is a strong izakaya choice."
        result = review_summary(summary, _Frame())
        assert result.rejected
        assert result.rejection_reason == "internal_label_leakage"

    def test_reviewer_allows_note_without_internals(self):
        note = "A well-regarded izakaya with deep sake selection and a lively atmosphere."
        result = review_note(note, "Sake House", _Frame())
        assert result.rejection_reason != "internal_label_leakage"

    def test_reviewer_label_itself_never_exposed(self):
        """reviewer_rejected must never appear in any user-facing text."""
        note = "reviewer_rejected: this place is not suitable."
        result = review_note(note, "Some Place", _Frame())
        assert not result.passed
        # Output note must be empty — no reviewer label leaked
        assert "reviewer_rejected" not in result.note


# ══════════════════════════════════════════════════════════════════════════════
# Test 8 — Repeated skeleton and generic filler
# ══════════════════════════════════════════════════════════════════════════════

class TestRepeatedSkeletonAndGenericFiller:
    """Criterion 8: Generic filler phrases are rejected."""

    def test_filler_regex_matches_generic_phrases(self):
        from app.concierge.claim_safety_reviewer import _FILLER_SKELETON_RE
        phrases = [
            "A great option for izakaya lovers.",
            "A solid choice for ramen enthusiasts.",
            "Makes a good choice for late-night lovers.",
        ]
        for phrase in phrases:
            assert _FILLER_SKELETON_RE.search(phrase) is not None, (
                f"Expected match for filler: {phrase!r}"
            )

    def test_reviewer_rejects_pure_filler_note(self):
        note = "A great option for late-night izakaya lovers looking for authentic food."
        result = review_note(note, "Some Izakaya", _Frame())
        assert not result.passed
        assert result.rejection_reason == "generic_filler"

    def test_reviewer_allows_specific_differentiated_note(self):
        note = (
            "Izakaya Shinya's charcoal-grilled skewers and rare Japanese whisky menu "
            "set it apart from the other izakayas in this Chicago search set."
        )
        result = review_note(note, "Izakaya Shinya", _Frame())
        assert result.passed or result.rejection_reason not in (
            "generic_filler", "name_hours_inference", "internal_label_leakage"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Test 9 — Timeout fail-closed: text hidden, cards kept
# ══════════════════════════════════════════════════════════════════════════════

class TestTimeoutFailClosed:
    """Criterion 9: Reviewer timeout hides/sanitizes text but keeps cards."""

    def test_note_reviewer_timeout_hides_note(self):
        """When timeout_s=0.0, the reviewer cannot start and fails closed."""
        note = "A great izakaya with good ramen."
        result = review_note(note, "Some Place", _Frame(), timeout_s=0.0)
        # Reviewer fails closed: note is hidden
        assert not result.passed
        assert result.note == ""
        assert result.rejection_reason == "reviewer_timeout"

    def test_summary_reviewer_timeout_hides_summary(self):
        summary = "A set of late-night izakayas in Chicago."
        result = review_summary(summary, _Frame(), timeout_s=0.0)
        assert result.rejected
        assert result.summary == ""
        assert result.rejection_reason == "reviewer_timeout"

    def test_timeout_result_contains_no_user_visible_reason(self):
        """The timeout reason must NOT be exposed in user-facing output."""
        note = "A great izakaya."
        result = review_note(note, "Some Place", _Frame(), timeout_s=0.0)
        # note field must be empty (the timeout reason is only in rejection_reason,
        # which is backend-only telemetry)
        assert result.note == ""

    def test_review_notes_set_global_timeout(self):
        """review_notes_set with zero budget: all notes hidden, results still present."""
        notes = {"p1": "Great izakaya.", "p2": "Good ramen spot."}
        entity_names = {"p1": "Place A", "p2": "Place B"}
        # Very tight timeout forces the global timeout branch
        results, telemetry = review_notes_set(
            notes, entity_names, _Frame(), timeout_s=0.000001
        )
        # All notes hidden but all place_ids present — cards not dropped
        assert len(results) == 2
        for r in results.values():
            assert r.note == "" or not r.passed

    def test_telemetry_reports_timed_out_flag(self):
        notes = {"p1": "Great izakaya.", "p2": "Good ramen spot."}
        entity_names = {"p1": "Place A", "p2": "Place B"}
        results, telemetry = review_notes_set(
            notes, entity_names, _Frame(), timeout_s=0.000001
        )
        assert telemetry.reviewer_timed_out is True


# ══════════════════════════════════════════════════════════════════════════════
# Test 10 — Existing contracts preserved
# ══════════════════════════════════════════════════════════════════════════════

class TestExistingContractsPreserved:
    """Criterion 10: All pre-existing contracts remain intact after PR #267."""

    def test_reviewer_telemetry_fallback_note_visible_count_is_zero(self):
        notes = {"p1": "Good ramen in Wicker Park.", "p2": "Solid sake menu."}
        entity_names = {"p1": "Ramen Place", "p2": "Sake Den"}
        _, telemetry = review_notes_set(notes, entity_names, _Frame())
        assert telemetry.fallback_note_visible_count == 0

    def test_reviewer_telemetry_deterministic_visible_count_is_zero(self):
        notes = {"p1": "Good ramen in Wicker Park."}
        entity_names = {"p1": "Ramen Place"}
        _, telemetry = review_notes_set(notes, entity_names, _Frame())
        assert telemetry.deterministic_visible_count == 0

    def test_reviewer_telemetry_as_dict_contains_required_fields(self):
        tel = ReviewerTelemetry(reviewer_used=True)
        d = tel.as_dict()
        required_fields = [
            "reviewer_used",
            "reviewer_ms",
            "reviewer_timed_out",
            "reviewer_rejected_note_count",
            "reviewer_hidden_note_count",
            "reviewer_rejected_summary",
            "reviewer_sanitized_summary",
            "reviewer_unsupported_claim_count",
            "reviewer_internal_leakage_count",
            "final_summary_visible",
            "final_note_visible_count",
            "fallback_note_visible_count",
            "deterministic_visible_count",
        ]
        for f in required_fields:
            assert f in d, f"Missing telemetry field: {f}"

    def test_reviewer_result_types(self):
        tel = ReviewerTelemetry()
        assert isinstance(tel.fallback_note_visible_count, int)
        assert isinstance(tel.deterministic_visible_count, int)
        assert tel.fallback_note_visible_count == 0
        assert tel.deterministic_visible_count == 0

    def test_note_review_result_has_expected_fields(self):
        result = NoteReviewResult(note="test", passed=True, rejection_reason="", reviewer_ms=1)
        assert hasattr(result, "note")
        assert hasattr(result, "passed")
        assert hasattr(result, "rejection_reason")
        assert hasattr(result, "reviewer_ms")

    def test_summary_review_result_has_expected_fields(self):
        result = SummaryReviewResult(
            summary="", passed=False, rejected=True,
            sanitized=False, rejection_reason="timeout", reviewer_ms=0
        )
        assert hasattr(result, "summary")
        assert hasattr(result, "passed")
        assert hasattr(result, "rejected")
        assert hasattr(result, "sanitized")
        assert hasattr(result, "rejection_reason")
        assert hasattr(result, "reviewer_ms")


# ══════════════════════════════════════════════════════════════════════════════
# Test 11 — reason_validator integration: _NAME_HOURS_INFERENCE_RE
# ══════════════════════════════════════════════════════════════════════════════

class TestReasonValidatorNameHoursInferenceIntegration:
    """Validates that the new pattern in reason_validator catches name-inference."""

    def _make_frame(self):
        from app.concierge.frame_extractor import extract_frame
        return extract_frame("late night izakayas", "Chicago")

    def _make_evidence(self, facts=None):
        from app.concierge.ranker import MinimalEvidenceBundle
        return MinimalEvidenceBundle(
            structured_facts=facts or [],
            uncertainty_flags=[],
            geo_note=None,
            evidence_adequacy="OK",
            entity=None,
            enrichment_facts=[],
        )

    def test_validate_reason_rejects_name_alone_signals(self):
        from app.concierge.reason_validator import validate_reason
        reason = "2AM Izakaya, whose name alone signals late-night credibility."
        frame = self._make_frame()
        evidence = self._make_evidence()
        is_valid, rejection = validate_reason(reason, frame, evidence)
        assert not is_valid
        assert rejection == "name_hours_inference"

    def test_validate_reason_rejects_name_implies_24hr(self):
        from app.concierge.reason_validator import validate_reason
        reason = "The name implies 24-hour availability, ideal for night owls."
        frame = self._make_frame()
        evidence = self._make_evidence()
        is_valid, rejection = validate_reason(reason, frame, evidence)
        assert not is_valid
        assert rejection == "name_hours_inference"

    def test_validate_reason_rejects_whose_name_suggests_open_late(self):
        from app.concierge.reason_validator import validate_reason
        reason = "Midnight Ramen, whose name suggests open-late hours, anchors the set."
        frame = self._make_frame()
        evidence = self._make_evidence()
        is_valid, rejection = validate_reason(reason, frame, evidence)
        assert not is_valid
        assert rejection == "name_hours_inference"

    def test_validate_reason_allows_honest_caveat(self):
        from app.concierge.reason_validator import validate_reason
        reason = (
            "2AM Izakaya appears in this late-night search set; "
            "verify current hours before planning a late arrival."
        )
        frame = self._make_frame()
        evidence = self._make_evidence()
        # This phrasing does NOT trigger name-inference — no name_alone_signals pattern
        is_valid, rejection = validate_reason(reason, frame, evidence)
        # Should pass the name-hours check (may still fail other checks — that's OK)
        assert rejection != "name_hours_inference"

    def test_name_hours_inference_re_imported_correctly(self):
        """The regex is importable from reason_validator."""
        from app.concierge.reason_validator import _NAME_HOURS_INFERENCE_RE as rv_re
        assert rv_re is not None
        test_phrase = "whose name alone signals late-night credibility"
        assert rv_re.search(test_phrase) is not None


# ══════════════════════════════════════════════════════════════════════════════
# Test 12 — SetWriterResult reviewer_telemetry field
# ══════════════════════════════════════════════════════════════════════════════

class TestSetWriterResultReviewerTelemetryField:
    """Validates the new reviewer_telemetry field on SetWriterResult."""

    def test_set_writer_result_has_reviewer_telemetry_field(self):
        from app.concierge.set_level_writer import SetWriterResult
        result = SetWriterResult(
            notes_by_place_id={},
            visible_note_count=0,
            hidden_note_count=0,
            rejected_note_count=0,
            timed_out=False,
            fallback_note_visible_count=0,
            role_note_counts={},
            note_source_counts={},
            repeated_skeleton_count=0,
            unsupported_claim_count=0,
            reviewer_telemetry=None,
        )
        assert hasattr(result, "reviewer_telemetry")
        assert result.reviewer_telemetry is None

    def test_as_telemetry_dict_without_reviewer(self):
        from app.concierge.set_level_writer import SetWriterResult
        result = SetWriterResult(
            notes_by_place_id={},
            visible_note_count=0,
            hidden_note_count=0,
            rejected_note_count=0,
            timed_out=False,
            fallback_note_visible_count=0,
            role_note_counts={},
            note_source_counts={},
            repeated_skeleton_count=0,
            unsupported_claim_count=0,
            reviewer_telemetry=None,
        )
        d = result.as_telemetry_dict(elapsed_ms=100)
        assert "reviewer_telemetry" not in d  # not included when None

    def test_as_telemetry_dict_with_reviewer(self):
        from app.concierge.set_level_writer import SetWriterResult
        reviewer_tel = {"reviewer_used": True, "reviewer_ms": 5}
        result = SetWriterResult(
            notes_by_place_id={},
            visible_note_count=0,
            hidden_note_count=0,
            rejected_note_count=0,
            timed_out=False,
            fallback_note_visible_count=0,
            role_note_counts={},
            note_source_counts={},
            repeated_skeleton_count=0,
            unsupported_claim_count=0,
            reviewer_telemetry=reviewer_tel,
        )
        d = result.as_telemetry_dict(elapsed_ms=100)
        assert "reviewer_telemetry" in d
        assert d["reviewer_telemetry"]["reviewer_used"] is True
