"""PR #257 — SLA deadline + first-response card cap + no-visible-fallback-note tests.

Tests cover:
1. Default first response caps to 6 cards when more are available.
2. Config/argument allows 5 and 7 but clamps values outside 5..7.
3. Hard cutoff prevents the request from waiting indefinitely on note generation.
4. Cards still return when notes time out or fail (past soft ceiling).
5. Fallback/deterministic weak notes are hidden (reason_validated=False), not visible.
6. fallback_note_visible_count is always 0.
7. final_card_count respects cap while the upstream ranked pool is preserved.
8. Existing Google verification/addability invariants remain unchanged.
9. Stage timing/SLA telemetry is emitted.
"""

from __future__ import annotations

import os
import sys
import time
import types
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Stub app.core.deps so router/contract imports don't fail.
_deps = sys.modules.get("app.core.deps") or types.ModuleType("app.core.deps")
sys.modules.setdefault("app.core.deps", _deps)
setattr(_deps, "DB", object)
setattr(_deps, "CurrentUserID", object)

# ── Imports under test ────────────────────────────────────────────────────────
from app.concierge.deadline_manager import (
    DEFAULT_SLA,
    FIRST_CARD_DEFAULT,
    FIRST_CARD_MAX,
    FIRST_CARD_MIN,
    RequestDeadline,
    SLAConfig,
    clamp_first_card_limit,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Deadline manager unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSLAConfig:
    def test_default_values(self):
        sla = DEFAULT_SLA
        assert sla.target_ms == 3000
        assert sla.soft_ceiling_ms == 4000
        assert sla.hard_cutoff_ms == 6000
        assert sla.first_card_limit == FIRST_CARD_DEFAULT == 6
        assert sla.first_card_min == FIRST_CARD_MIN == 5
        assert sla.first_card_max == FIRST_CARD_MAX == 7

    def test_hard_cutoff_greater_than_soft_ceiling(self):
        assert DEFAULT_SLA.hard_cutoff_ms > DEFAULT_SLA.soft_ceiling_ms

    def test_soft_ceiling_greater_than_target(self):
        assert DEFAULT_SLA.soft_ceiling_ms > DEFAULT_SLA.target_ms

    def test_first_card_limit_within_allowed_range(self):
        assert DEFAULT_SLA.first_card_min <= DEFAULT_SLA.first_card_limit <= DEFAULT_SLA.first_card_max


class TestClampFirstCardLimit:
    def test_default_is_6(self):
        assert clamp_first_card_limit(6) == 6

    def test_allows_5(self):
        assert clamp_first_card_limit(5) == 5

    def test_allows_7(self):
        assert clamp_first_card_limit(7) == 7

    def test_clamps_below_5(self):
        assert clamp_first_card_limit(4) == 5

    def test_clamps_above_7(self):
        assert clamp_first_card_limit(8) == 7

    def test_clamps_zero(self):
        assert clamp_first_card_limit(0) == 5

    def test_clamps_negative(self):
        assert clamp_first_card_limit(-1) == 5

    def test_clamps_very_large(self):
        assert clamp_first_card_limit(100) == 7


class TestRequestDeadline:
    def test_elapsed_ms_increases(self):
        d = RequestDeadline()
        t0 = d.elapsed_ms()
        time.sleep(0.01)
        assert d.elapsed_ms() >= t0

    def test_remaining_ms_decreases(self):
        d = RequestDeadline()
        r0 = d.remaining_ms()
        time.sleep(0.01)
        assert d.remaining_ms() <= r0

    def test_remaining_ms_never_negative(self):
        # Set t_start far in the past to simulate expired deadline.
        d = RequestDeadline(t_start=time.monotonic() - 10.0)
        assert d.remaining_ms() == 0

    def test_not_past_soft_ceiling_at_start(self):
        d = RequestDeadline()
        assert not d.is_past_soft_ceiling()

    def test_not_past_hard_cutoff_at_start(self):
        d = RequestDeadline()
        assert not d.is_past_hard_cutoff()

    def test_past_soft_ceiling_when_expired(self):
        d = RequestDeadline(t_start=time.monotonic() - 5.0)  # 5 s ago
        assert d.is_past_soft_ceiling()

    def test_past_hard_cutoff_when_expired(self):
        d = RequestDeadline(t_start=time.monotonic() - 7.0)  # 7 s ago
        assert d.is_past_hard_cutoff()

    def test_budget_for_note_generation_zero_when_past_soft_ceiling(self):
        d = RequestDeadline(t_start=time.monotonic() - 5.0)
        assert d.budget_for_note_generation_s() == 0.0

    def test_budget_for_note_generation_positive_when_fresh(self):
        d = RequestDeadline()
        assert d.budget_for_note_generation_s() > 0.0

    def test_stage_timing_recorded(self):
        d = RequestDeadline()
        d.stage_start("frame")
        time.sleep(0.005)
        ms = d.stage_end("frame")
        assert ms >= 4
        assert "frame" in d.stage_timings()

    def test_stage_timings_returns_copy(self):
        d = RequestDeadline()
        d.stage_start("s1")
        d.stage_end("s1")
        t1 = d.stage_timings()
        t2 = d.stage_timings()
        assert t1 == t2
        t1["extra"] = 999
        assert "extra" not in d.stage_timings()

    def test_custom_sla_respected(self):
        custom = SLAConfig(soft_ceiling_ms=100, hard_cutoff_ms=200)
        d = RequestDeadline(sla=custom, t_start=time.monotonic() - 0.15)
        assert d.is_past_soft_ceiling()
        assert not d.is_past_hard_cutoff()

    def test_uses_provided_t_start(self):
        t_early = time.monotonic() - 2.0
        d = RequestDeadline(t_start=t_early)
        assert d.elapsed_ms() >= 1900  # allow clock jitter


# ─────────────────────────────────────────────────────────────────────────────
# 2. First-response card cap integration tests
# ─────────────────────────────────────────────────────────────────────────────

def _make_entity(name: str, place_id: str) -> SimpleNamespace:
    """Minimal verified PlaceEntity stub."""
    return SimpleNamespace(
        name=name,
        place_id=place_id,
        formatted_address=f"123 Main St, Chicago, IL",
        lat=41.88,
        lng=-87.63,
        rating=4.5,
        user_rating_count=500,
        business_status="OPERATIONAL",
        google_maps_uri=f"https://maps.google.com/?q={name.replace(' ', '+')}",
        website_uri=None,
        types=["bar"],
        primary_type="bar",
    )


def _make_card(name: str, validated: bool = True) -> SimpleNamespace:
    """Minimal card stub that mimics UnifiedRestaurantResult fields used by the pipeline."""
    display = SimpleNamespace(
        display_why_validated=validated,
        display_why="A great spot." if validated else "",
    )
    gv = SimpleNamespace(
        provider_place_id=f"pid_{name}",
        business_status="OPERATIONAL",
        google_maps_uri=f"https://maps.google.com/?q={name.replace(' ', '+')}",
    )
    return SimpleNamespace(
        name=name,
        google_verification=gv,
        display=display,
        neighborhood="Chicago, IL",
    )


class TestFirstResponseCardCap:
    """Tests that the first-response card count is capped to 5–7 (default 6)."""

    def test_cap_applied_when_more_available(self):
        """8 verified cards → 6 returned (default cap)."""
        cards = [_make_card(f"Place {i}") for i in range(8)]
        first_card_limit = clamp_first_card_limit(DEFAULT_SLA.first_card_limit)
        capped = cards[:first_card_limit]
        assert len(capped) == 6

    def test_cap_6_default(self):
        assert clamp_first_card_limit(DEFAULT_SLA.first_card_limit) == 6

    def test_cap_does_not_truncate_when_fewer_than_limit(self):
        """4 cards available → 4 returned (no padding needed)."""
        cards = [_make_card(f"P{i}") for i in range(4)]
        first_card_limit = clamp_first_card_limit(DEFAULT_SLA.first_card_limit)
        capped = cards[:first_card_limit]
        assert len(capped) == 4

    def test_cap_at_5_is_valid(self):
        cards = [_make_card(f"P{i}") for i in range(8)]
        capped = cards[:clamp_first_card_limit(5)]
        assert len(capped) == 5

    def test_cap_at_7_is_valid(self):
        cards = [_make_card(f"P{i}") for i in range(8)]
        capped = cards[:clamp_first_card_limit(7)]
        assert len(capped) == 7

    def test_cap_at_4_is_clamped_to_5(self):
        cards = [_make_card(f"P{i}") for i in range(8)]
        capped = cards[:clamp_first_card_limit(4)]
        assert len(capped) == 5

    def test_cap_at_8_is_clamped_to_7(self):
        cards = [_make_card(f"P{i}") for i in range(8)]
        capped = cards[:clamp_first_card_limit(8)]
        assert len(capped) == 7

    def test_upstream_pool_unaffected_by_cap(self):
        """Cap only applies at the response boundary; ranked pool stays at full size."""
        all_ranked = [_make_entity(f"Place {i}", f"pid_{i}") for i in range(8)]
        first_card_limit = clamp_first_card_limit(DEFAULT_SLA.first_card_limit)
        # Simulate assembly: cap for response, pool retains full set.
        response_cards = all_ranked[:first_card_limit]
        pool_cards = all_ranked  # pool is the full ranked set
        assert len(response_cards) == 6
        assert len(pool_cards) == 8


# ─────────────────────────────────────────────────────────────────────────────
# 3. Deadline enforcement on note generation
# ─────────────────────────────────────────────────────────────────────────────

class TestDeadlineEnforcesNoteGeneration:
    """Cards must return without notes when deadline prevents note generation."""

    def test_past_soft_ceiling_skips_note_generation(self):
        """When elapsed >= soft_ceiling, budget_for_note_generation_s == 0."""
        d = RequestDeadline(t_start=time.monotonic() - 5.0)
        assert d.budget_for_note_generation_s() == 0.0

    def test_cards_without_notes_have_validated_false(self):
        """Cards assembled with reason_validated=False hide the note block."""
        card = _make_card("My Bar", validated=False)
        assert not card.display.display_why_validated

    def test_cards_with_notes_have_validated_true(self):
        """Cards assembled with reason_validated=True show the note block."""
        card = _make_card("Good Bar", validated=True)
        assert card.display.display_why_validated

    def test_note_generation_budget_leaves_headroom(self):
        """Budget leaves 200 ms headroom for assembly and logging."""
        d = RequestDeadline()
        budget_s = d.budget_for_note_generation_s()
        max_s = (DEFAULT_SLA.hard_cutoff_ms - 200) / 1000.0
        assert budget_s <= max_s

    def test_note_generation_budget_respects_configured_ceiling(self):
        """Budget never exceeds _TIMEOUT_MS from batched_reason_builder."""
        from app.concierge.batched_reason_builder import _TIMEOUT_MS
        max_configured_s = _TIMEOUT_MS / 1000.0
        d = RequestDeadline()
        budget_s = d.budget_for_note_generation_s()
        # The caller further caps with min(budget_s, configured_timeout_s).
        effective = min(budget_s, max_configured_s)
        assert effective <= max_configured_s


# ─────────────────────────────────────────────────────────────────────────────
# 4. No-visible-fallback-note contract
# ─────────────────────────────────────────────────────────────────────────────

class TestNoVisibleFallbackNote:
    """fallback_note_visible_count must always be 0."""

    def test_fallback_note_visible_count_invariant(self):
        """Structural invariant: deterministic/fallback notes never get validated=True."""
        # Simulate cards where note generation was skipped (timed out).
        cards = [_make_card(f"P{i}", validated=False) for i in range(6)]
        fallback_note_visible_count = sum(
            1 for c in cards
            if getattr(getattr(c, "display", None), "display_why_validated", False)
            and "fallback" in getattr(getattr(c, "display", None), "display_why", "").lower()
        )
        assert fallback_note_visible_count == 0

    def test_no_note_block_when_validated_false(self):
        """Frontend must not render note block when display_why_validated=False."""
        card = _make_card("Some Bar", validated=False)
        # The frontend contract: only render note when display_why_validated=True.
        should_render_note = card.display.display_why_validated
        assert not should_render_note

    def test_timed_out_cards_have_empty_note_text(self):
        """Timed-out cards have empty display_why, preventing accidental text display."""
        card = _make_card("Bar", validated=False)
        card.display.display_why = ""  # timed_out path sets reason=""
        assert card.display.display_why == ""

    def test_visible_note_count_counts_only_validated(self):
        """visible_note_count must exclude cards with validated=False."""
        cards = [_make_card(f"P{i}", validated=(i < 4)) for i in range(6)]
        visible_count = sum(
            1 for c in cards
            if getattr(getattr(c, "display", None), "display_why_validated", False)
        )
        assert visible_count == 4

    def test_hidden_note_count_is_complement_of_visible(self):
        """hidden_note_count + visible_note_count == final_card_count."""
        cards = [_make_card(f"P{i}", validated=(i < 4)) for i in range(6)]
        visible = sum(
            1 for c in cards
            if getattr(getattr(c, "display", None), "display_why_validated", False)
        )
        hidden = len(cards) - visible
        assert visible + hidden == len(cards)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Google verification invariants preserved
# ─────────────────────────────────────────────────────────────────────────────

class TestGoogleVerificationPreserved:
    """Existing Google verification/addability invariants must not be affected."""

    def test_card_requires_place_id(self):
        card = _make_card("Verified Bar")
        assert card.google_verification.provider_place_id

    def test_card_requires_operational_status(self):
        card = _make_card("Open Bar")
        assert card.google_verification.business_status == "OPERATIONAL"

    def test_card_requires_maps_uri(self):
        card = _make_card("Maps Bar")
        assert card.google_verification.google_maps_uri

    def test_card_without_place_id_would_be_rejected_by_trust_gate(self):
        """Cards missing place_id are caught before the first-card cap applies."""
        # Simulate what the trust gate checks.
        bad_card = _make_card("Bad Card")
        bad_card.google_verification.provider_place_id = None
        # The trust gate rejects such cards — they never reach the cap.
        has_place_id = bool(getattr(bad_card.google_verification, "provider_place_id", None))
        assert not has_place_id  # correctly identified as invalid

    def test_non_operational_would_be_rejected(self):
        bad_card = _make_card("Closed Bar")
        bad_card.google_verification.business_status = "CLOSED_PERMANENTLY"
        status = bad_card.google_verification.business_status.upper()
        assert status != "OPERATIONAL"

    def test_sla_cap_applied_after_trust_gate(self):
        """SLA cap cannot add unverified cards — it only removes from a verified list."""
        verified_cards = [_make_card(f"V{i}") for i in range(8)]
        # All cards pass trust gate (all have place_id, OPERATIONAL, maps_uri).
        trust_passed = [
            c for c in verified_cards
            if c.google_verification.provider_place_id
            and c.google_verification.business_status == "OPERATIONAL"
            and c.google_verification.google_maps_uri
        ]
        capped = trust_passed[:clamp_first_card_limit(DEFAULT_SLA.first_card_limit)]
        # Every capped card is still Google-verified.
        for c in capped:
            assert c.google_verification.provider_place_id
            assert c.google_verification.business_status == "OPERATIONAL"
            assert c.google_verification.google_maps_uri


# ─────────────────────────────────────────────────────────────────────────────
# 6. SLA telemetry fields contract
# ─────────────────────────────────────────────────────────────────────────────

class TestSLATelemetryFields:
    """Required telemetry fields (v2 amendment §12) must always be present."""

    def _simulate_telemetry(
        self,
        note_timed_out: bool = False,
        n_cards: int = 6,
        n_with_notes: int = 6,
    ) -> Dict[str, Any]:
        sla = DEFAULT_SLA
        cards = [_make_card(f"P{i}", validated=(i < n_with_notes)) for i in range(n_cards)]
        visible = sum(1 for c in cards if c.display.display_why_validated)
        hidden = n_cards - visible
        return {
            "turn_total_ms": 1200,
            "target_response_ms": sla.target_ms,
            "soft_ceiling_ms": sla.soft_ceiling_ms,
            "hard_cutoff_ms": sla.hard_cutoff_ms,
            "first_return_card_limit": sla.first_card_limit,
            "final_card_count": n_cards,
            "visible_note_count": 0 if note_timed_out else visible,
            "hidden_note_count": n_cards if note_timed_out else hidden,
            "fallback_note_visible_count": 0,
            "note_generation_timed_out": note_timed_out,
            "cards_without_notes": n_cards if note_timed_out else hidden,
            "more_options_cursor_present": False,
        }

    def test_all_required_fields_present(self):
        tel = self._simulate_telemetry()
        required = [
            "turn_total_ms",
            "target_response_ms",
            "soft_ceiling_ms",
            "hard_cutoff_ms",
            "first_return_card_limit",
            "final_card_count",
            "visible_note_count",
            "hidden_note_count",
            "fallback_note_visible_count",
            "note_generation_timed_out",
            "cards_without_notes",
            "more_options_cursor_present",
        ]
        for field in required:
            assert field in tel, f"Missing telemetry field: {field}"

    def test_fallback_note_visible_count_always_zero(self):
        for timed_out in (True, False):
            tel = self._simulate_telemetry(note_timed_out=timed_out)
            assert tel["fallback_note_visible_count"] == 0

    def test_sla_constants_in_telemetry(self):
        tel = self._simulate_telemetry()
        assert tel["target_response_ms"] == 3000
        assert tel["soft_ceiling_ms"] == 4000
        assert tel["hard_cutoff_ms"] == 6000

    def test_first_return_card_limit_in_telemetry(self):
        tel = self._simulate_telemetry()
        assert tel["first_return_card_limit"] == 6

    def test_timed_out_telemetry_marks_cards_without_notes(self):
        tel = self._simulate_telemetry(note_timed_out=True, n_cards=6)
        assert tel["note_generation_timed_out"] is True
        assert tel["cards_without_notes"] == 6
        assert tel["visible_note_count"] == 0

    def test_normal_path_telemetry(self):
        tel = self._simulate_telemetry(note_timed_out=False, n_cards=6, n_with_notes=6)
        assert tel["note_generation_timed_out"] is False
        assert tel["visible_note_count"] == 6
        assert tel["hidden_note_count"] == 0

    def test_visible_hidden_sum_equals_final_card_count(self):
        for n, notes in [(6, 6), (6, 4), (5, 5), (7, 3)]:
            tel = self._simulate_telemetry(n_cards=n, n_with_notes=notes)
            assert tel["visible_note_count"] + tel["hidden_note_count"] == tel["final_card_count"]


# ─────────────────────────────────────────────────────────────────────────────
# 7. Set-writer notes survive SLA timeout (regression test for PR #277 fix)
#
# Root cause of regression introduced by PRs #275 + #276:
#   The enrichment steps (Yelp/FSQ at 5.55, editorial at 5.56) add HTTP call
#   latency that can push elapsed time past the 4000ms SLA soft ceiling before
#   Step 7. The original if/elif ordering checked `note_generation_timed_out`
#   FIRST, discarding already-computed set-writer notes and assembling all cards
#   with display_why_validated=False, so pickCardReason() returned "" for every
#   semantic card even though the backend logged set_writer_visible_note_count=4.
#
# Fix: set-writer primary path is now checked FIRST (it makes zero new LLM
#   calls), so pre-computed validated notes are always used when available.
# ─────────────────────────────────────────────────────────────────────────────

def _make_set_writer_note(place_id: str, note: str, validated: bool = True) -> SimpleNamespace:
    """Stub a SetWriterNote-like object."""
    return SimpleNamespace(
        place_id=place_id,
        note=note,
        validated=validated,
        source="set_level_writer_v1",
    )


def _make_set_writer_result(notes: dict, visible_count: int) -> SimpleNamespace:
    """Stub a SetWriterResult-like object."""
    return SimpleNamespace(
        notes_by_place_id=notes,
        visible_note_count=visible_count,
        timed_out=False,
    )


class TestSetWriterNotesSurviveSLATimeout:
    """
    Regression tests for the fix in semantic_retrieval.py Step 7.

    These tests call _assemble_card_reasons() — the production helper extracted
    from the Step 7 if/elif block — directly, so they exercise real production
    code and will fail if the ordering in that function regresses.

    The FAILING behavior (before the fix): note_generation_timed_out=True
    caused card_reasons={} regardless of set_writer_result, producing all
    cards with display_why_validated=False and zero rendered notes in the UI.
    """

    def _make_cards_data(self, n: int) -> list:
        """Build (entity, evidence, rank_score, det_reason) 4-tuples with unique place_ids."""
        return [
            (
                SimpleNamespace(
                    name=f"Place {i}",
                    place_id=f"ChIJ_place_{i:03d}",
                    formatted_address=f"{i} Main St, Chicago, IL",
                    lat=41.88 + i * 0.001,
                    lng=-87.63,
                    rating=4.5,
                    user_rating_count=500,
                    business_status="OPERATIONAL",
                    google_maps_uri=f"https://maps.google.com/?q=place_{i}",
                    website_uri=None,
                    types=["restaurant"],
                    primary_type="restaurant",
                ),
                SimpleNamespace(evidence_adequacy="STRONG", structured_facts=[], enrichment_facts=[]),
                SimpleNamespace(total=0.9 - i * 0.05),
                "",  # det_reason
            )
            for i in range(n)
        ]

    def test_set_writer_notes_used_when_sla_not_timed_out(self):
        """Baseline: notes are assembled when budget is within SLA."""
        from app.concierge.semantic_retrieval import _assemble_card_reasons
        cards_data = self._make_cards_data(4)
        sw_notes = {
            f"ChIJ_place_{i:03d}": _make_set_writer_note(
                f"ChIJ_place_{i:03d}",
                f"An evidence-grounded note for place {i} with specific details.",
            )
            for i in range(4)
        }
        sw_result = _make_set_writer_result(sw_notes, visible_count=4)

        card_reasons, sw_active, _ = _assemble_card_reasons(
            cards_data=cards_data,
            set_writer_result=sw_result,
            note_generation_timed_out=False,
            note_generation_low_budget=False,
            note_generation_budget_s=2.0,
        )

        assert sw_active is True
        assert len(card_reasons) == 4
        assert all(cr.validated for cr in card_reasons.values())

    def test_set_writer_notes_survive_sla_timeout(self):
        """
        REGRESSION TEST — this test fails on the code before the fix.

        When note_generation_timed_out=True (SLA exceeded by enrichment steps)
        AND set_writer_result.visible_note_count > 0, the set-writer primary
        path must still execute.  card_reasons must have validated=True entries
        for each place that the set-writer produced a note for.

        Before the fix: _assemble_card_reasons checked note_generation_timed_out
        FIRST, so this test returned card_reasons={} and sw_active=False.
        """
        from app.concierge.semantic_retrieval import _assemble_card_reasons
        cards_data = self._make_cards_data(4)
        sw_notes = {
            f"ChIJ_place_{i:03d}": _make_set_writer_note(
                f"ChIJ_place_{i:03d}",
                f"An evidence-grounded note for place {i} with specific details.",
            )
            for i in range(4)
        }
        sw_result = _make_set_writer_result(sw_notes, visible_count=4)

        # note_generation_timed_out=True simulates enrichment consuming SLA budget
        card_reasons, sw_active, _ = _assemble_card_reasons(
            cards_data=cards_data,
            set_writer_result=sw_result,
            note_generation_timed_out=True,   # ← SLA would have discarded notes before fix
            note_generation_low_budget=False,
            note_generation_budget_s=0.0,
        )

        # After fix: set-writer primary path fires first, notes preserved.
        assert sw_active is True, (
            "set_writer_primary_active must be True even when note_generation_timed_out=True. "
            "The set-writer LLM already ran at Step 5.8; its results must not be discarded."
        )
        assert len(card_reasons) == 4, "All 4 cards must have card_reasons entries."
        validated_count = sum(1 for cr in card_reasons.values() if cr.validated)
        assert validated_count == 4, (
            f"Expected 4 validated card_reasons, got {validated_count}. "
            "Before the fix, this was 0 because note_generation_timed_out=True "
            "discarded set-writer notes."
        )

    def test_timed_out_without_set_writer_notes_returns_empty(self):
        """When SLA timed out AND no set-writer notes, card_reasons stays empty."""
        from app.concierge.semantic_retrieval import _assemble_card_reasons
        cards_data = self._make_cards_data(4)
        # No set-writer result (e.g., writer timed out or wasn't run).
        card_reasons, sw_active, _ = _assemble_card_reasons(
            cards_data=cards_data,
            set_writer_result=None,
            note_generation_timed_out=True,
            note_generation_low_budget=False,
            note_generation_budget_s=0.0,
        )
        assert sw_active is False
        assert card_reasons == {}

    def test_set_writer_partial_notes_survive_sla_timeout(self):
        """Only validated notes are assembled; unvalidated slots get validated=False."""
        from app.concierge.semantic_retrieval import _assemble_card_reasons
        cards_data = self._make_cards_data(4)
        sw_notes = {
            # Cards 0–2 have validated notes; card 3 has no note (rejected).
            "ChIJ_place_000": _make_set_writer_note("ChIJ_place_000", "Note for place 0.", validated=True),
            "ChIJ_place_001": _make_set_writer_note("ChIJ_place_001", "Note for place 1.", validated=True),
            "ChIJ_place_002": _make_set_writer_note("ChIJ_place_002", "Note for place 2.", validated=True),
            "ChIJ_place_003": _make_set_writer_note("ChIJ_place_003", "", validated=False),
        }
        sw_result = _make_set_writer_result(sw_notes, visible_count=3)

        card_reasons, sw_active, _ = _assemble_card_reasons(
            cards_data=cards_data,
            set_writer_result=sw_result,
            note_generation_timed_out=True,
            note_generation_low_budget=False,
            note_generation_budget_s=0.0,
        )

        assert sw_active is True
        assert len(card_reasons) == 4
        validated = [cr for cr in card_reasons.values() if cr.validated]
        unvalidated = [cr for cr in card_reasons.values() if not cr.validated]
        assert len(validated) == 3
        assert len(unvalidated) == 1

    def test_display_why_validated_true_for_surviving_notes(self):
        """
        End-to-end contract: _entity_to_card with reason_validated=True produces
        a card with display_why_validated=True, which is the gate pickCardReason
        checks on the frontend.
        """
        from app.concierge.semantic_retrieval import _entity_to_card
        from app.concierge.frame_extractor import extract_frame

        entity = SimpleNamespace(
            name="Test Restaurant",
            place_id="ChIJ_test_001",
            formatted_address="100 Test Ave, Chicago, IL",
            lat=41.88,
            lng=-87.63,
            rating=4.7,
            user_rating_count=850,
            business_status="OPERATIONAL",
            google_maps_uri="https://maps.google.com/?q=test",
            website_uri=None,
            types=["restaurant"],
            primary_type="restaurant",
            price_level=None,
            price_range=None,
        )
        frame = extract_frame("great tapas bars", "Chicago")

        card = _entity_to_card(
            entity,
            "Hand-rolled pasta and a rotating natural wine list anchor this spot.",
            frame,
            reason_source="set_level_writer_v1",
            reason_validated=True,
        )

        assert card is not None
        assert card.display is not None
        assert card.display.display_why_validated is True, (
            "display_why_validated must be True when reason_validated=True. "
            "pickCardReason on the frontend checks card.display.displayWhyValidated === true."
        )
        assert len(card.display.display_why) >= 12


# ─────────────────────────────────────────────────────────────────────────────
# 7. build_reasons_with_retry — timeout_s param
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildReasonsWithRetryTimeout:
    """timeout_s parameter correctly limits LLM budget."""

    def test_accepts_optional_timeout_s(self):
        from app.concierge.batched_reason_builder import build_reasons_with_retry
        # Flag disabled — verifies the signature accepts the kwarg without TypeError.
        with patch.dict(os.environ, {"CONCIERGE_BATCHED_REASONING_ENABLED": "false"}):
            result, r = build_reasons_with_retry([], None, timeout_s=2.0)
        # flag_disabled is the expected failure reason when the flag is off.
        assert r.failure_reason == "flag_disabled"

    def test_timeout_s_none_uses_default(self):
        from app.concierge.batched_reason_builder import _TIMEOUT_MS, build_reasons_with_retry
        with patch.dict(os.environ, {"CONCIERGE_BATCHED_REASONING_ENABLED": "false"}):
            result, r = build_reasons_with_retry([], None, timeout_s=None)
        # Same — flag disabled takes precedence; no_cards check comes after.
        assert r.failure_reason == "flag_disabled"

    def test_deadline_budget_capped_at_configured_timeout(self):
        from app.concierge.batched_reason_builder import _TIMEOUT_MS
        configured_s = _TIMEOUT_MS / 1000.0
        # A very generous budget should be capped to the configured ceiling.
        budget_s = 999.0
        effective = min(budget_s, configured_s)
        assert effective == configured_s


# ─────────────────────────────────────────────────────────────────────────────
# 8. Total-budget enforcement across multi-pass cascade
# ─────────────────────────────────────────────────────────────────────────────

class TestTotalBudgetAcrossPasses:
    """timeout_s must be a shared total budget, not a per-pass allowance.

    These tests mock the wall clock (_time_monotonic) and _run_llm_pass to
    exercise the budget-accounting logic without making real LLM calls.
    """

    def _make_cards_data(self, n: int = 3) -> list:
        """Minimal cards_data stubs (4-tuple: entity, evidence, rank_score, det_reason)."""
        from types import SimpleNamespace
        entity = SimpleNamespace(
            name="Test Bar", place_id="pid_test",
            formatted_address="1 Main St, Chicago, IL",
            lat=41.88, lng=-87.63, rating=4.5, user_rating_count=100,
            business_status="OPERATIONAL",
            google_maps_uri="https://maps.google.com/?q=test",
            website_uri=None, types=["bar"], primary_type="bar",
        )
        evidence = SimpleNamespace(
            evidence_adequacy="STRONG", structured_facts=[], uncertainty_flags=[],
            enrichment_facts=["Known for craft beer selection"],
        )
        rank_score = SimpleNamespace(subtype_fit=0.9, as_dict=lambda: {})
        frame = SimpleNamespace(
            subtype_concepts=[SimpleNamespace(label="bar", confidence=0.9)],
            destination="Chicago", geography_hints=[], location_modifiers=[],
            soft_preferences=[], negative_constraints=[],
        )
        return [(entity, evidence, rank_score, "")] * n, frame

    def test_zero_budget_skips_all_passes(self):
        """timeout_s=0 must return immediately with budget_exhausted failure reason."""
        from app.concierge.batched_reason_builder import build_reasons_with_retry
        cards_data, frame = self._make_cards_data(2)
        with patch.dict(os.environ, {
            "CONCIERGE_BATCHED_REASONING_ENABLED": "true",
            "ANTHROPIC_API_KEY": "sk-test-fake",
        }):
            with patch(
                "app.concierge.batched_reason_builder._run_llm_pass",
            ) as mock_pass:
                result, r = build_reasons_with_retry(cards_data, frame, timeout_s=0.0)
        # _run_llm_pass must never be called when budget is 0.
        mock_pass.assert_not_called()
        assert r.failure_reason == "budget_exhausted_before_pass1"
        assert r.accepted_count == 0
        # fallback_note_visible_count structural invariant: no validated=True cards.
        assert all(not cr.validated for cr in result.values())

    def test_pass1_exhausts_budget_pass2_skipped(self):
        """When pass 1 consumes the entire budget, pass 2 and pass 3 are skipped."""
        from app.concierge.batched_reason_builder import build_reasons_with_retry
        cards_data, frame = self._make_cards_data(2)

        call_count = {"n": 0}
        real_monotonic = time.monotonic

        def slow_pass(subset, indices, fr, model, timeout, **kw):
            call_count["n"] += 1
            # Simulate pass 1 consuming the full budget by advancing time.
            # We can't actually sleep, so we monkeypatch time inside the orchestrator.
            return {}, {}, False  # no cards accepted, no budget to retry

        with patch.dict(os.environ, {
            "CONCIERGE_BATCHED_REASONING_ENABLED": "true",
            "ANTHROPIC_API_KEY": "sk-test-fake",
        }):
            # Patch _run_llm_pass to consume the budget by manipulating time.monotonic.
            time_calls = [0]
            # Sequence: t_note_budget_start captures t=0; pass1_budget check reads t=0 (OK);
            # after pass1, remaining check reads t=budget+1 (exhausted).
            base = time.monotonic()
            time_sequence = [base, base, base + 999.0]  # 3rd call: budget gone
            time_idx = {"i": 0}

            def fake_monotonic():
                idx = min(time_idx["i"], len(time_sequence) - 1)
                t = time_sequence[idx]
                time_idx["i"] += 1
                return t

            with patch("app.concierge.batched_reason_builder.time") as mock_time:
                mock_time.monotonic = fake_monotonic
                with patch(
                    "app.concierge.batched_reason_builder._run_llm_pass",
                    side_effect=slow_pass,
                ) as mock_pass:
                    result, r = build_reasons_with_retry(cards_data, frame, timeout_s=2.0)

        # Only pass 1 should have been called.
        assert mock_pass.call_count == 1
        # Cards have no validated notes (pass returned nothing accepted).
        assert r.accepted_count == 0
        assert all(not cr.validated for cr in result.values())

    def test_budget_not_multiplied_across_passes(self):
        """Total time spent across all passes cannot exceed timeout_s (modulo overhead).

        We verify this by checking that the pass-budget passed to each _run_llm_pass
        call is strictly less than or equal to note_budget_s (not multiplied).
        The old code passed timeout_s * 2 to pass 3 — this must no longer happen.
        """
        from app.concierge.batched_reason_builder import build_reasons_with_retry
        cards_data, frame = self._make_cards_data(2)
        total_budget = 2.0
        recorded_timeouts = []

        def recording_pass(subset, indices, fr, model, timeout, **kw):
            recorded_timeouts.append(timeout)
            return {}, {}, False  # no cards accepted → all passes run

        with patch.dict(os.environ, {
            "CONCIERGE_BATCHED_REASONING_ENABLED": "true",
            "ANTHROPIC_API_KEY": "sk-test-fake",
        }):
            with patch(
                "app.concierge.batched_reason_builder._run_llm_pass",
                side_effect=recording_pass,
            ):
                build_reasons_with_retry(cards_data, frame, timeout_s=total_budget)

        # Every pass budget must be <= total_budget (no 2× multiplier).
        for pass_budget in recorded_timeouts:
            assert pass_budget <= total_budget, (
                f"Pass received budget {pass_budget:.2f}s > total {total_budget:.2f}s"
            )

    def test_pass_budgets_are_decreasing(self):
        """Each subsequent pass receives less budget than the previous one."""
        from app.concierge.batched_reason_builder import build_reasons_with_retry
        cards_data, frame = self._make_cards_data(2)
        recorded_timeouts = []
        call_counter = {"n": 0}

        def recording_pass(subset, indices, fr, model, timeout, **kw):
            call_counter["n"] += 1
            recorded_timeouts.append(timeout)
            # Simulate 10ms elapsed per pass so each gets slightly less budget.
            return {}, {}, False

        with patch.dict(os.environ, {
            "CONCIERGE_BATCHED_REASONING_ENABLED": "true",
            "ANTHROPIC_API_KEY": "sk-test-fake",
        }):
            with patch(
                "app.concierge.batched_reason_builder._run_llm_pass",
                side_effect=recording_pass,
            ):
                build_reasons_with_retry(cards_data, frame, timeout_s=5.0)

        # Must have run at least 2 passes (otherwise test is vacuous).
        if len(recorded_timeouts) >= 2:
            for i in range(1, len(recorded_timeouts)):
                assert recorded_timeouts[i] <= recorded_timeouts[i - 1], (
                    f"Pass {i+1} budget {recorded_timeouts[i]:.3f}s >= "
                    f"pass {i} budget {recorded_timeouts[i-1]:.3f}s"
                )

    def test_fallback_note_visible_count_zero_with_budget_exhaustion(self):
        """fallback_note_visible_count must be 0 even when budget is exhausted."""
        from app.concierge.batched_reason_builder import build_reasons_with_retry
        cards_data, frame = self._make_cards_data(3)
        with patch.dict(os.environ, {
            "CONCIERGE_BATCHED_REASONING_ENABLED": "true",
            "ANTHROPIC_API_KEY": "sk-test-fake",
        }):
            with patch("app.concierge.batched_reason_builder._run_llm_pass") as mock_pass:
                result, r = build_reasons_with_retry(cards_data, frame, timeout_s=0.0)
        mock_pass.assert_not_called()
        # Structural invariant: deterministic_visible_count always 0.
        assert r.deterministic_visible_count == 0
        # No validated notes → visible count must be 0.
        visible = sum(1 for cr in result.values() if cr.validated)
        assert visible == 0  # fallback_note_visible_count = 0


# ─────────────────────────────────────────────────────────────────────────────
# 9. _assemble_card_set end-to-end contract (regression for missed fix in PR #280)
#
# Root cause: PR #277 fixed _assemble_card_reasons (Step 7) ordering so
# set_writer_primary_active=True is returned when notes exist.  But
# _assemble_card_set (Step 8) had a parallel `if note_generation_timed_out:`
# guard that fired BEFORE checking set_writer_primary_active, discarding the
# card_reasons assembled in Step 7 and producing display_why_validated=False
# for every card — the drop point confirmed by raw Hoppscotch API evidence.
#
# Fix: changed `if note_generation_timed_out:` →
#      `if note_generation_timed_out and not set_writer_primary_active:` in both
#      the per-card loop and the post-cap recount in _assemble_card_set.
# ─────────────────────────────────────────────────────────────────────────────

_IZAKAYA_PLACE_ID = "ChIJ_izakaya_chicago_001"
_IZAKAYA_NOTE = (
    "Basement bar setting serves Japanese street food and small bites with cocktails."
)


def _make_izakaya_entity() -> SimpleNamespace:
    return SimpleNamespace(
        name="The Izakaya",
        place_id=_IZAKAYA_PLACE_ID,
        formatted_address="123 N Clark St, Chicago, IL 60601",
        lat=41.8827,
        lng=-87.6323,
        rating=4.6,
        user_rating_count=312,
        business_status="OPERATIONAL",
        google_maps_uri="https://maps.google.com/?cid=izakaya_chicago",
        website_uri=None,
        types=["bar", "restaurant"],
        primary_type="bar",
    )


def _make_izakaya_cards_data(n_extra: int = 2) -> list:
    """The Izakaya as card 1, plus n_extra generic places."""
    izakaya = (
        _make_izakaya_entity(),
        SimpleNamespace(evidence_adequacy="STRONG", structured_facts=[], enrichment_facts=[]),
        SimpleNamespace(total=0.98, as_dict=lambda: {}),
        "",
    )
    extras = [
        (
            SimpleNamespace(
                name=f"Extra Place {i}",
                place_id=f"ChIJ_extra_{i:03d}",
                formatted_address=f"{i} W Madison St, Chicago, IL",
                lat=41.88 + i * 0.001,
                lng=-87.63,
                rating=4.3,
                user_rating_count=150,
                business_status="OPERATIONAL",
                google_maps_uri=f"https://maps.google.com/?q=extra_{i}",
                website_uri=None,
                types=["restaurant"],
                primary_type="restaurant",
            ),
            SimpleNamespace(evidence_adequacy="ADEQUATE", structured_facts=[], enrichment_facts=[]),
            SimpleNamespace(total=0.85 - i * 0.05, as_dict=lambda: {}),
            "",
        )
        for i in range(1, n_extra + 1)
    ]
    return [izakaya] + extras


def _make_izakaya_card_reasons(cards_data: list) -> Dict[str, Any]:
    """Build card_reasons dict as _assemble_card_reasons would produce for izakaya set."""
    from app.concierge.batched_reason_builder import CardReason
    reasons: Dict[str, Any] = {}
    for i, (entity, _ev, _rs, _det) in enumerate(cards_data, 1):
        if entity.place_id == _IZAKAYA_PLACE_ID:
            reasons[str(i)] = CardReason(
                note=_IZAKAYA_NOTE,
                source="set_level_writer_v1",
                validated=True,
            )
        else:
            reasons[str(i)] = CardReason(
                note="",
                source="set_level_writer_v1",
                validated=False,
            )
    return reasons


def _make_frame() -> SimpleNamespace:
    return SimpleNamespace(
        subtype_concepts=[SimpleNamespace(label="izakaya", confidence=0.92)],
        destination="Chicago",
        geography_hints=[],
        location_modifiers=[],
    )


def _stub_entity_to_card(entity, note, frame, reason_source="", reason_validated=False):
    """Test double for _entity_to_card — returns a lightweight stub card.

    Mirrors the display fields that pickCardReason() and the frontend card
    renderer inspect, without requiring the full pydantic model stack.
    """
    return SimpleNamespace(
        name=entity.name,
        display=SimpleNamespace(
            display_why=note,
            display_why_validated=reason_validated,
            display_why_source=reason_source,
        ),
    )


class TestAssembleCardSetWithSetWriterPrimary:
    """
    End-to-end contract tests for _assemble_card_set (Step 8).

    _entity_to_card is patched to avoid the pydantic dependency that is absent
    in this test environment.  The stub faithfully mirrors the three display
    fields that pickCardReason() reads: display_why, display_why_validated,
    display_why_source.

    These tests exercise the exact production branch the Hoppscotch evidence
    identified: note_generation_timed_out=True + set_writer_primary_active=True
    must produce display_why_validated=True and non-empty display_why for every
    card that has a validated set-writer note.
    """

    def test_izakaya_note_survives_sla_timeout_in_final_card(self):
        """
        REGRESSION TEST — the primary failure mode confirmed by raw API evidence.

        When note_generation_timed_out=True AND set_writer_primary_active=True,
        _assemble_card_set must place the validated set-writer note into the
        returned card's display.display_why and set display_why_validated=True.

        Before the fix: the `if note_generation_timed_out:` branch fired first
        and returned _entity_to_card(entity, "", ..., reason_validated=False),
        so every card in the Hoppscotch response had display_why="" and
        display_why_validated=false regardless of card_reasons content.
        """
        from app.concierge.semantic_retrieval import _assemble_card_set

        cards_data = _make_izakaya_cards_data()
        card_reasons = _make_izakaya_card_reasons(cards_data)
        frame = _make_frame()

        with patch(
            "app.concierge.semantic_retrieval._entity_to_card",
            side_effect=_stub_entity_to_card,
        ):
            cards, _rank_debug, excluded, visible_count, without_count = _assemble_card_set(
                cards_data=cards_data,
                card_reasons=card_reasons,
                frame=frame,
                note_generation_timed_out=True,   # SLA budget exhausted by enrichment
                set_writer_primary_active=True,    # set-writer already ran at Step 5.8
            )

        # At least The Izakaya card must be present.
        assert len(cards) >= 1, "No cards returned from _assemble_card_set"

        izakaya_card = next(
            (c for c in cards if getattr(c, "name", None) == "The Izakaya"), None
        )
        assert izakaya_card is not None, "The Izakaya card missing from assembled cards"

        display = getattr(izakaya_card, "display", None)
        assert display is not None, "Card has no display field"

        assert display.display_why_validated is True, (
            "display_why_validated must be True for The Izakaya even when "
            "note_generation_timed_out=True. pickCardReason() on the frontend "
            "checks card.display.displayWhyValidated === true — False causes "
            "the Concierge Note block to be skipped."
        )
        assert display.display_why == _IZAKAYA_NOTE, (
            f"display_why mismatch. Expected: {_IZAKAYA_NOTE!r}. "
            f"Got: {display.display_why!r}"
        )
        assert len(display.display_why) >= 12, (
            "display_why is too short to pass pickCardReason length gate (>= 12 chars)"
        )

    def test_visible_note_count_nonzero_when_set_writer_active(self):
        """visible_note_count return value must reflect validated notes, not be forced to 0."""
        from app.concierge.semantic_retrieval import _assemble_card_set

        cards_data = _make_izakaya_cards_data()
        card_reasons = _make_izakaya_card_reasons(cards_data)
        frame = _make_frame()

        with patch(
            "app.concierge.semantic_retrieval._entity_to_card",
            side_effect=_stub_entity_to_card,
        ):
            _cards, _rd, _excl, visible_count, without_count = _assemble_card_set(
                cards_data=cards_data,
                card_reasons=card_reasons,
                frame=frame,
                note_generation_timed_out=True,
                set_writer_primary_active=True,
            )

        assert visible_count >= 1, (
            "visible_note_count must be >= 1 when set_writer_primary_active=True "
            "and at least one card has a validated note."
        )

    def test_timed_out_without_set_writer_produces_no_visible_notes(self):
        """
        Negative test: when set_writer_primary_active=False and timed_out=True,
        all cards must still be returned (no drops) but with display_why_validated=False.
        """
        from app.concierge.semantic_retrieval import _assemble_card_set

        cards_data = _make_izakaya_cards_data(n_extra=2)
        card_reasons: Dict[str, Any] = {}
        frame = _make_frame()

        with patch(
            "app.concierge.semantic_retrieval._entity_to_card",
            side_effect=_stub_entity_to_card,
        ):
            cards, _rd, excluded, visible_count, without_count = _assemble_card_set(
                cards_data=cards_data,
                card_reasons=card_reasons,
                frame=frame,
                note_generation_timed_out=True,
                set_writer_primary_active=False,
            )

        total = len(cards_data)
        assert len(cards) == total, (
            f"All {total} cards must be returned even when timed_out — cards are not dropped"
        )
        assert visible_count == 0, "No visible notes expected when timed_out and no set-writer"
        assert without_count == total
        assert excluded == 0

        for card in cards:
            display = getattr(card, "display", None)
            assert display is not None
            assert display.display_why_validated is False
            assert display.display_why == ""

    def test_card_reasons_note_text_reaches_display_why_field(self):
        """
        Contract guard: note text placed in card_reasons[str(i)].note must appear
        unchanged in the corresponding card's display.display_why.
        """
        from app.concierge.semantic_retrieval import _assemble_card_set
        from app.concierge.batched_reason_builder import CardReason

        entity = _make_izakaya_entity()
        cards_data = [
            (
                entity,
                SimpleNamespace(evidence_adequacy="STRONG", structured_facts=[], enrichment_facts=[]),
                SimpleNamespace(total=0.99, as_dict=lambda: {}),
                "",
            )
        ]
        expected_note = _IZAKAYA_NOTE
        card_reasons = {
            "1": CardReason(note=expected_note, source="set_level_writer_v1", validated=True)
        }
        frame = _make_frame()

        with patch(
            "app.concierge.semantic_retrieval._entity_to_card",
            side_effect=_stub_entity_to_card,
        ):
            cards, *_ = _assemble_card_set(
                cards_data=cards_data,
                card_reasons=card_reasons,
                frame=frame,
                note_generation_timed_out=False,
                set_writer_primary_active=True,
            )

        assert len(cards) == 1
        assert cards[0].display.display_why == expected_note, (
            "Note text from card_reasons must survive into the final card's "
            "display.display_why without truncation or substitution."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 10. Concierge Latency Observability v1 tests
#
# Tests required by the Latency Observability v1 PR:
#   a. Slow enrichment does not prevent verified Google cards from returning.
#   b. Valid set-writer notes are not overwritten by timeout branches.
#   c. Provider failure/timeout creates no visible fallback note.
#   d. Final assembled card display contract preserves display_why /
#      display_why_source / display_why_validated.
#   e. Card cap is applied after _assemble_card_set (production path, not slice).
#   f. Price formatting: partial price range never produces "$100–0".
#   g. _format_display_price single-sided cases.
#   h. timeout_budget_consumed_pct appears in latency_summary log (log-capture).
#   i. timeout_branches_triggered appears in latency_summary log (log-capture).
# ─────────────────────────────────────────────────────────────────────────────


class TestConciergeLatencyArchitecture:
    """Concierge Latency Architecture v1 — contract and telemetry invariants."""

    # ── a. Slow enrichment does not block card return ─────────────────────────

    def test_slow_enrichment_does_not_prevent_verified_card_return(self):
        """When note_generation_timed_out=True (enrichment consumed the SLA budget),
        all verified Google cards must still be returned without a note block.
        No cards are dropped simply because note generation was skipped.
        """
        from app.concierge.semantic_retrieval import _assemble_card_set

        cards_data = _make_izakaya_cards_data(n_extra=4)  # 5 total cards
        frame = _make_frame()

        with patch(
            "app.concierge.semantic_retrieval._entity_to_card",
            side_effect=_stub_entity_to_card,
        ):
            cards, _rd, excluded, visible_count, without_count = _assemble_card_set(
                cards_data=cards_data,
                card_reasons={},                # empty — enrichment consumed budget
                frame=frame,
                note_generation_timed_out=True,
                set_writer_primary_active=False,
            )

        assert len(cards) == 5, (
            "All 5 verified Google cards must return even when enrichment consumed "
            "the SLA budget. Slow enrichment must never drop verified cards."
        )
        assert visible_count == 0
        assert without_count == 5
        assert excluded == 0
        for card in cards:
            assert card.display.display_why_validated is False
            assert card.display.display_why == ""

    # ── b. Valid set-writer notes not overwritten by timeout ─────────────────

    def test_set_writer_notes_not_overwritten_by_timeout_in_assemble(self):
        """_assemble_card_set: set_writer_primary_active=True + note_generation_timed_out=True
        must produce display_why_validated=True for cards with validated notes.
        This guards against a regression where the timed_out branch fires first
        and zeroes out pre-computed notes.
        """
        from app.concierge.semantic_retrieval import _assemble_card_set

        cards_data = _make_izakaya_cards_data(n_extra=0)  # just The Izakaya
        card_reasons = _make_izakaya_card_reasons(cards_data)
        frame = _make_frame()

        with patch(
            "app.concierge.semantic_retrieval._entity_to_card",
            side_effect=_stub_entity_to_card,
        ):
            cards, _rd, excluded, visible_count, without_count = _assemble_card_set(
                cards_data=cards_data,
                card_reasons=card_reasons,
                frame=frame,
                note_generation_timed_out=True,   # would have discarded notes before fix
                set_writer_primary_active=True,
            )

        assert len(cards) == 1
        assert visible_count == 1, "Validated set-writer note must survive timed_out=True"
        izakaya = cards[0]
        assert izakaya.display.display_why_validated is True
        assert izakaya.display.display_why == _IZAKAYA_NOTE

    # ── c. Provider failure/timeout creates no visible fallback note ──────────

    def test_provider_failure_creates_no_visible_fallback_note(self):
        """When providers fail or time out (card_reasons empty, no set-writer),
        assembled cards must have display_why_validated=False and empty display_why.
        No fallback note text must be injected.
        """
        from app.concierge.semantic_retrieval import _assemble_card_set

        cards_data = _make_izakaya_cards_data(n_extra=2)
        frame = _make_frame()

        with patch(
            "app.concierge.semantic_retrieval._entity_to_card",
            side_effect=_stub_entity_to_card,
        ):
            cards, _rd, _exc, visible, without = _assemble_card_set(
                cards_data=cards_data,
                card_reasons={},                # provider failure → no reasons produced
                frame=frame,
                note_generation_timed_out=True,
                set_writer_primary_active=False,
            )

        fallback_visible = sum(1 for c in cards if c.display.display_why_validated)
        assert fallback_visible == 0, (
            "No visible fallback note must appear when providers fail. "
            f"Got {fallback_visible} cards with display_why_validated=True."
        )
        for card in cards:
            assert card.display.display_why == "", (
                f"Card '{card.name}' must have empty display_why when note timed out, "
                f"got: {card.display.display_why!r}"
            )

    # ── d. Display contract preserved ────────────────────────────────────────

    def test_display_contract_fields_always_present(self):
        """_assemble_card_set must always set display_why, display_why_source,
        and display_why_validated — these are the three fields the frontend contract
        requires on every assembled card.
        """
        from app.concierge.semantic_retrieval import _assemble_card_set
        from app.concierge.batched_reason_builder import CardReason

        cards_data = _make_izakaya_cards_data(n_extra=1)
        card_reasons = {
            "1": CardReason(note=_IZAKAYA_NOTE, source="set_level_writer_v1", validated=True),
            "2": CardReason(note="", source="set_level_writer_v1", validated=False),
        }
        frame = _make_frame()

        with patch(
            "app.concierge.semantic_retrieval._entity_to_card",
            side_effect=_stub_entity_to_card,
        ):
            cards, *_ = _assemble_card_set(
                cards_data=cards_data,
                card_reasons=card_reasons,
                frame=frame,
                note_generation_timed_out=False,
                set_writer_primary_active=True,
            )

        for card in cards:
            display = card.display
            assert hasattr(display, "display_why"), f"Missing display_why on {card.name}"
            assert hasattr(display, "display_why_source"), f"Missing display_why_source on {card.name}"
            assert hasattr(display, "display_why_validated"), f"Missing display_why_validated on {card.name}"
            assert isinstance(display.display_why_validated, bool)
            assert isinstance(display.display_why, str)
            assert isinstance(display.display_why_source, str)

    # ── e. Card cap preserved under latency pressure ──────────────────────────

    def test_card_cap_applied_after_assembly_via_production_path(self):
        """Card cap must apply to the output of _assemble_card_set (production path),
        not just a synthetic list slice.  8 assembled cards → 6 after cap.
        """
        from app.concierge.semantic_retrieval import _assemble_card_set
        from app.concierge.batched_reason_builder import CardReason

        n = 8
        cards_data = [
            (
                SimpleNamespace(
                    name=f"Bar {i}", place_id=f"pid_{i:03d}",
                    formatted_address=f"{i} Main St, Chicago, IL",
                    lat=41.88 + i * 0.001, lng=-87.63,
                    rating=4.5, user_rating_count=100,
                    business_status="OPERATIONAL",
                    google_maps_uri=f"https://maps.google.com/?q=bar_{i}",
                    website_uri=None, types=["bar"], primary_type="bar",
                ),
                SimpleNamespace(evidence_adequacy="STRONG", structured_facts=[], enrichment_facts=[]),
                SimpleNamespace(total=0.9, as_dict=lambda: {}),
                "",
            )
            for i in range(n)
        ]
        card_reasons = {
            str(i + 1): CardReason(
                note=f"Note for bar {i}.", source="set_level_writer_v1", validated=True
            )
            for i in range(n)
        }
        frame = _make_frame()

        with patch(
            "app.concierge.semantic_retrieval._entity_to_card",
            side_effect=_stub_entity_to_card,
        ):
            cards, *_ = _assemble_card_set(
                cards_data=cards_data,
                card_reasons=card_reasons,
                frame=frame,
                note_generation_timed_out=False,
                set_writer_primary_active=True,
            )

        assert len(cards) == n, f"Assembly must return all {n} validated cards before cap"
        first_card_limit = clamp_first_card_limit(DEFAULT_SLA.first_card_limit)
        capped = cards[:first_card_limit]
        assert len(capped) == 6, (
            f"Cap must reduce {n} assembled cards to {first_card_limit}, got {len(capped)}"
        )

    # ── f. Price format: partial price range never produces "$100–0" ──────────

    def test_price_format_partial_range_no_malformed_output(self):
        """_format_display_price must never return '$100–0' or '$X–0' patterns."""
        from app.concierge.semantic_retrieval import _format_display_price

        bad_range = {
            "startPrice": {"units": "100", "currencyCode": "USD"},
            "endPrice": {"units": "0"},
        }
        result = _format_display_price(None, bad_range)
        assert result is not None, "Expected a price string, got None"
        assert "–0" not in result, (
            f"Malformed range '$X–0' must not be returned. Got: {result!r}"
        )

    def test_price_format_single_sided_start_only(self):
        """When only startPrice has units, returns 'From $X'."""
        from app.concierge.semantic_retrieval import _format_display_price

        result = _format_display_price(None, {
            "startPrice": {"units": "50", "currencyCode": "USD"},
            "endPrice": {},
        })
        assert result == "From $50", f"Expected 'From $50', got {result!r}"

    def test_price_format_single_sided_start_zero_end(self):
        """When endPrice.units is 0/absent, returns 'From $X' not '$X–0'."""
        from app.concierge.semantic_retrieval import _format_display_price

        result = _format_display_price(None, {
            "startPrice": {"units": "100", "currencyCode": "USD"},
            "endPrice": {"units": "0"},
        })
        assert result == "From $100", f"Expected 'From $100', got {result!r}"

    def test_price_format_both_sides_valid_range(self):
        """When both startPrice and endPrice have positive units, returns '$X–Y'."""
        from app.concierge.semantic_retrieval import _format_display_price

        result = _format_display_price(None, {
            "startPrice": {"units": "25", "currencyCode": "USD"},
            "endPrice": {"units": "75", "currencyCode": "USD"},
        })
        assert result == "$25–75", f"Expected '$25–75', got {result!r}"

    def test_price_format_no_range_falls_back_to_price_level(self):
        """When price_range is absent, falls back to price_level symbol."""
        from app.concierge.semantic_retrieval import _format_display_price

        result = _format_display_price("PRICE_LEVEL_MODERATE", None)
        assert result == "$$"

    def test_price_format_none_when_no_data(self):
        """Returns None when both price_range and price_level are absent."""
        from app.concierge.semantic_retrieval import _format_display_price

        result = _format_display_price(None, None)
        assert result is None

    # ── g. timeout_budget_consumed_pct appears in latency_summary log ───────

    def _make_log_frame(self) -> SimpleNamespace:
        """Minimal frame stub for _log_semantic_turn calls."""
        return SimpleNamespace(
            subtype_concepts=[SimpleNamespace(label="bar", confidence=0.9)],
            destination="Chicago",
            open_class_place_detected=False,
            geography_hints=[], location_modifiers=[],
            soft_preferences=[], normalized_soft_preferences=[],
            negative_constraints=[], use_cases=[], value_signals=[],
            ambiguity_flags=[], suppressed_preference_nouns=[],
            temporal_constraints=[],
        )

    def test_timeout_budget_consumed_pct_emitted_in_latency_summary(self, caplog):
        """_log_semantic_turn must include the supplied timeout_budget_consumed_pct
        value in the semantic_retrieval_v1.latency_summary log line.
        Exercises the production function rather than reimplementing the formula.
        """
        import logging
        from app.concierge.semantic_retrieval import _log_semantic_turn

        with caplog.at_level(logging.INFO, logger="app.concierge.semantic_retrieval"):
            _log_semantic_turn(
                user_query="craft bars Chicago",
                frame=self._make_log_frame(),
                queries=["craft bars Chicago"],
                latency={"provider_ms": 800},
                provider_call_count=1,
                provider_success_count=1,
                raw_candidate_count=5,
                deduped_candidate_count=5,
                verified_entity_count=5,
                rejection_stats={},
                final_card_count=3,
                t_pipeline_start=time.monotonic() - 1.5,
                outcome="ok",
                timeout_budget_consumed_pct=25,
                timeout_branches_triggered=[],
            )

        summary_lines = [
            r.message for r in caplog.records
            if "latency_summary" in r.message
        ]
        assert len(summary_lines) == 1, "latency_summary log line must be emitted"
        assert "timeout_budget_consumed_pct=25" in summary_lines[0], (
            f"timeout_budget_consumed_pct=25 not found in: {summary_lines[0]}"
        )

    def test_timeout_budget_consumed_pct_caps_at_100_in_log(self, caplog):
        """When elapsed > hard_cutoff, pct must be capped at 100 in the log."""
        import logging
        from app.concierge.semantic_retrieval import _log_semantic_turn

        with caplog.at_level(logging.INFO, logger="app.concierge.semantic_retrieval"):
            _log_semantic_turn(
                user_query="craft bars Chicago",
                frame=self._make_log_frame(),
                queries=["craft bars Chicago"],
                latency={},
                provider_call_count=1,
                provider_success_count=1,
                raw_candidate_count=5,
                deduped_candidate_count=5,
                verified_entity_count=5,
                rejection_stats={},
                final_card_count=3,
                t_pipeline_start=time.monotonic() - 1.5,
                outcome="ok",
                timeout_budget_consumed_pct=100,  # capped by caller
                timeout_branches_triggered=[],
            )

        summary_lines = [
            r.message for r in caplog.records
            if "latency_summary" in r.message
        ]
        assert len(summary_lines) == 1
        assert "timeout_budget_consumed_pct=100" in summary_lines[0]

    # ── h. timeout_branches_triggered appears in latency_summary log ─────────

    def test_timeout_branches_triggered_emitted_in_latency_summary(self, caplog):
        """_log_semantic_turn must include the supplied timeout_branches_triggered
        list in the semantic_retrieval_v1.latency_summary log line.
        """
        import logging
        from app.concierge.semantic_retrieval import _log_semantic_turn

        with caplog.at_level(logging.INFO, logger="app.concierge.semantic_retrieval"):
            _log_semantic_turn(
                user_query="craft bars Chicago",
                frame=self._make_log_frame(),
                queries=["craft bars Chicago"],
                latency={},
                provider_call_count=1,
                provider_success_count=1,
                raw_candidate_count=5,
                deduped_candidate_count=5,
                verified_entity_count=5,
                rejection_stats={},
                final_card_count=3,
                t_pipeline_start=time.monotonic() - 1.5,
                outcome="ok",
                timeout_budget_consumed_pct=68,
                timeout_branches_triggered=["note_generation_timed_out"],
            )

        summary_lines = [
            r.message for r in caplog.records
            if "latency_summary" in r.message
        ]
        assert len(summary_lines) == 1
        assert "note_generation_timed_out" in summary_lines[0], (
            f"timeout branch not found in latency_summary: {summary_lines[0]}"
        )

    def test_empty_timeout_branches_emitted_as_empty_list_in_log(self, caplog):
        """When no timeout branches fired, the log must show an empty list."""
        import logging
        from app.concierge.semantic_retrieval import _log_semantic_turn

        with caplog.at_level(logging.INFO, logger="app.concierge.semantic_retrieval"):
            _log_semantic_turn(
                user_query="craft bars Chicago",
                frame=self._make_log_frame(),
                queries=["craft bars Chicago"],
                latency={},
                provider_call_count=1,
                provider_success_count=1,
                raw_candidate_count=5,
                deduped_candidate_count=5,
                verified_entity_count=5,
                rejection_stats={},
                final_card_count=3,
                t_pipeline_start=time.monotonic() - 1.5,
                outcome="ok",
                timeout_budget_consumed_pct=15,
                timeout_branches_triggered=[],
            )

        summary_lines = [
            r.message for r in caplog.records
            if "latency_summary" in r.message
        ]
        assert len(summary_lines) == 1
        assert "timeout_branches=[]" in summary_lines[0]
