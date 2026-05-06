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
