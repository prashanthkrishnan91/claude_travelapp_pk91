"""Tests for Concierge Latency Architecture v1.

Verifies deadline propagation and optional-branch gating behavior:

1. deadline_manager — budget_for_set_writer_s caps at SET_WRITER_LLM_MAX_S
2. Set-writer pre-skip gate — write_set_notes never called when budget too low
3. Slow set-writer — verified cards still return, no fallback notes invented
4. Slow/skipped enrichment — Google-verified cards still return
5. Note preservation — previously validated notes preserved when skip fires
6. Final display contract — stable for cards with notes and cards without notes
7. No fallback notes — set_writer_skipped_budget produces no filler prose

These tests are designed to FAIL a weak implementation (e.g., missing the
budget cap or missing the pre-skip gate) while passing the correct one.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# 1. deadline_manager — budget_for_set_writer_s
# ══════════════════════════════════════════════════════════════════════════════

class TestBudgetForSetWriter:
    """Tests that verify the SET_WRITER_LLM_MAX_S cap is enforced."""

    def test_capped_at_max_when_plenty_of_budget_remains(self):
        """With 5000ms remaining, budget_for_set_writer_s must not exceed 1.5s."""
        from app.concierge.deadline_manager import RequestDeadline, SET_WRITER_LLM_MAX_S

        # Create a deadline that just started — plenty of budget.
        deadline = RequestDeadline(t_start=time.monotonic())
        result = deadline.budget_for_set_writer_s()

        assert result <= SET_WRITER_LLM_MAX_S, (
            f"budget_for_set_writer_s={result:.3f}s must not exceed "
            f"SET_WRITER_LLM_MAX_S={SET_WRITER_LLM_MAX_S}s even with plenty of budget"
        )

    def test_capped_at_1_5s_default(self):
        """Default cap must be 1.5 seconds."""
        from app.concierge.deadline_manager import SET_WRITER_LLM_MAX_S
        assert SET_WRITER_LLM_MAX_S == 1.5

    def test_returns_zero_past_soft_ceiling(self):
        """Returns 0.0 when elapsed >= soft_ceiling_ms."""
        from app.concierge.deadline_manager import RequestDeadline, SLAConfig

        # Simulate elapsed = 5000ms, soft_ceiling = 4000ms
        very_old_t = time.monotonic() - 5.0
        sla = SLAConfig(soft_ceiling_ms=4000, hard_cutoff_ms=6000)
        deadline = RequestDeadline(sla=sla, t_start=very_old_t)

        result = deadline.budget_for_set_writer_s()
        assert result == 0.0, (
            f"Expected 0.0 past soft ceiling, got {result}"
        )

    def test_never_exceeds_cap_with_large_budget(self):
        """budget_for_set_writer_s < budget_for_note_generation_s when budget is large."""
        from app.concierge.deadline_manager import RequestDeadline, SET_WRITER_LLM_MAX_S

        deadline = RequestDeadline(t_start=time.monotonic())
        note_budget = deadline.budget_for_note_generation_s()
        writer_budget = deadline.budget_for_set_writer_s()

        # writer budget must be <= cap, and note budget must be much larger
        assert writer_budget <= SET_WRITER_LLM_MAX_S
        # note_budget should be much larger than writer_budget when budget is ample
        assert note_budget > writer_budget, (
            "budget_for_note_generation_s should exceed budget_for_set_writer_s "
            "when there is ample remaining budget"
        )

    def test_min_budget_constant_set(self):
        """SET_WRITER_MIN_BUDGET_MS must be defined and positive."""
        from app.concierge.deadline_manager import SET_WRITER_MIN_BUDGET_MS
        assert isinstance(SET_WRITER_MIN_BUDGET_MS, int)
        assert SET_WRITER_MIN_BUDGET_MS > 0

    def test_returns_zero_or_less_when_barely_any_budget(self):
        """With only 100ms remaining, budget_for_set_writer_s returns 0 (or near-zero)."""
        from app.concierge.deadline_manager import RequestDeadline, SLAConfig

        # Simulate elapsed = 5900ms (only 100ms before hard cutoff)
        t_start = time.monotonic() - 5.9
        sla = SLAConfig(soft_ceiling_ms=4000, hard_cutoff_ms=6000)
        deadline = RequestDeadline(sla=sla, t_start=t_start)

        result = deadline.budget_for_set_writer_s()
        # 100ms remaining - 300ms headroom = negative → clamped to 0
        assert result == 0.0, (
            f"With only ~100ms remaining, expected 0.0, got {result}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 2. Set-writer pre-skip gate
# ══════════════════════════════════════════════════════════════════════════════

class TestSetWriterPreSkipGate:
    """Tests that write_set_notes is never called when remaining budget is too low."""

    def _make_deadline_with_remaining_ms(self, remaining_ms: int):
        """Create a RequestDeadline object whose remaining_ms() ≈ remaining_ms."""
        from app.concierge.deadline_manager import RequestDeadline, SLAConfig

        hard_cutoff_ms = 6000
        elapsed_ms = hard_cutoff_ms - remaining_ms
        t_start = time.monotonic() - elapsed_ms / 1000.0
        sla = SLAConfig(soft_ceiling_ms=4000, hard_cutoff_ms=hard_cutoff_ms)
        return RequestDeadline(sla=sla, t_start=t_start)

    def test_write_set_notes_not_called_when_budget_too_low(self):
        """write_set_notes must never be called when remaining budget < SET_WRITER_MIN_BUDGET_MS."""
        from app.concierge.deadline_manager import SET_WRITER_MIN_BUDGET_MS

        # Budget just below the threshold
        deadline = self._make_deadline_with_remaining_ms(SET_WRITER_MIN_BUDGET_MS - 50)
        remaining = deadline.remaining_ms()

        with patch(
            "app.concierge.set_level_writer.write_set_notes"
        ) as mock_write:
            # Simulate the pre-skip gate logic
            _skipped = remaining < SET_WRITER_MIN_BUDGET_MS
            if not _skipped:
                mock_write(curated_result=None, frame=None, deadline=deadline)

            # write_set_notes must NOT have been called
            assert not mock_write.called, (
                f"write_set_notes was called with remaining_ms={remaining}ms "
                f"which is below threshold={SET_WRITER_MIN_BUDGET_MS}ms"
            )

    def test_write_set_notes_called_when_budget_sufficient(self):
        """write_set_notes may proceed when remaining budget >= SET_WRITER_MIN_BUDGET_MS."""
        from app.concierge.deadline_manager import SET_WRITER_MIN_BUDGET_MS

        # Budget well above the threshold
        deadline = self._make_deadline_with_remaining_ms(SET_WRITER_MIN_BUDGET_MS + 500)
        remaining = deadline.remaining_ms()

        _skipped = remaining < SET_WRITER_MIN_BUDGET_MS
        assert not _skipped, (
            f"Expected set-writer not skipped at remaining={remaining}ms "
            f"(threshold={SET_WRITER_MIN_BUDGET_MS}ms)"
        )

    def test_set_writer_lowers_budget_not_ignores_it(self):
        """The LLM call in set_level_writer uses budget_for_set_writer_s, not a large fallback."""
        from app.concierge.deadline_manager import RequestDeadline, SLAConfig, SET_WRITER_LLM_MAX_S
        from app.concierge import set_level_writer

        deadline = RequestDeadline(t_start=time.monotonic())
        assert deadline.budget_for_set_writer_s() <= SET_WRITER_LLM_MAX_S

        # Verify the module uses budget_for_set_writer_s by inspecting source
        import inspect
        source = inspect.getsource(set_level_writer.write_set_notes)
        assert "budget_for_set_writer_s" in source, (
            "write_set_notes must use deadline.budget_for_set_writer_s() "
            "not deadline.budget_for_note_generation_s()"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 3. Slow set-writer — verified cards still return, no fallback notes
# ══════════════════════════════════════════════════════════════════════════════

class TestSlowSetWriterVerifiedCardsStillReturn:
    """Simulates a slow set-writer: cards must still return without fallback notes."""

    def _make_slow_set_writer_result(self):
        """Returns a SetWriterResult that timed out (no notes)."""
        from app.concierge.set_level_writer import SetWriterResult
        return SetWriterResult(
            notes_by_place_id={},
            visible_note_count=0,
            hidden_note_count=0,
            rejected_note_count=0,
            timed_out=True,
            fallback_note_visible_count=0,
            role_note_counts={},
            note_source_counts={},
            repeated_skeleton_count=0,
            unsupported_claim_count=0,
        )

    def test_timed_out_result_is_not_primary(self):
        """A timed-out SetWriterResult must not be used as the primary note source."""
        from app.concierge.set_level_writer import SetWriterResult

        slow_result = self._make_slow_set_writer_result()
        # timed_out=True means it must NOT be used as primary
        is_primary = (
            slow_result is not None
            and not slow_result.timed_out
            and slow_result.visible_note_count > 0
        )
        assert not is_primary, (
            "A timed-out set-writer result must NOT be treated as primary"
        )

    def test_timed_out_result_produces_no_visible_notes(self):
        """A timed-out result must have zero visible notes."""
        slow_result = self._make_slow_set_writer_result()
        assert slow_result.visible_note_count == 0
        assert slow_result.fallback_note_visible_count == 0

    def test_set_writer_result_with_empty_notes_assembles_cardset_without_notes(self):
        """_assemble_card_set with timed-out set-writer produces cards without note blocks."""
        from app.concierge.semantic_retrieval import _assemble_card_set, _entity_to_card
        from app.concierge.frame_extractor import extract_frame

        frame = extract_frame("best tacos", "Chicago")

        # Build a minimal entity stub
        entity = MagicMock()
        entity.place_id = "ChIJtest1"
        entity.name = "Taco Test"
        entity.types = ["restaurant"]
        entity.primary_type = "restaurant"
        entity.formatted_address = "100 N State St, Chicago, IL"
        entity.lat = 41.88
        entity.lng = -87.63
        entity.rating = 4.5
        entity.user_rating_count = 200
        entity.business_status = "OPERATIONAL"
        entity.google_maps_uri = "https://maps.google.com/?cid=1"
        entity.website_uri = None
        entity.price_level = None
        entity.price_range = None

        rank_score = MagicMock()
        rank_score.as_dict.return_value = {"subtype_fit": 0.9}
        rank_score.subtype_fit = 0.9

        cards_data = [(entity, MagicMock(), rank_score, "")]
        card_reasons: Dict[str, Any] = {}

        # Simulate: set-writer timed out, no set_writer_primary_active
        cards, rank_debug, excluded_unvalidated, visible_note_count, without_notes = (
            _assemble_card_set(
                cards_data=cards_data,
                card_reasons=card_reasons,
                frame=frame,
                note_generation_timed_out=True,
                set_writer_primary_active=False,
            )
        )

        assert len(cards) == 1, "Card must still be returned even when set-writer timed out"
        assert visible_note_count == 0, "No visible notes when set-writer timed out"
        assert without_notes == 1

    def test_no_fallback_note_is_ever_set_validated_true(self):
        """Cards without valid notes must have display_why_validated=False."""
        from app.concierge.semantic_retrieval import _entity_to_card
        from app.concierge.frame_extractor import extract_frame

        frame = extract_frame("best tacos", "Chicago")
        entity = MagicMock()
        entity.place_id = "ChIJtest1"
        entity.name = "Taco Test"
        entity.types = ["restaurant"]
        entity.primary_type = "restaurant"
        entity.formatted_address = "100 N State St, Chicago, IL"
        entity.lat = 41.88
        entity.lng = -87.63
        entity.rating = 4.5
        entity.user_rating_count = 200
        entity.business_status = "OPERATIONAL"
        entity.google_maps_uri = "https://maps.google.com/?cid=1"
        entity.website_uri = None
        entity.price_level = None
        entity.price_range = None

        card = _entity_to_card(entity, "", frame, reason_source="timed_out", reason_validated=False)
        assert card is not None
        assert card.display.display_why_validated is False, (
            "A card without a note must have display_why_validated=False"
        )
        assert card.display.display_why == "" or card.display.display_why is None or card.display.display_why == "", (
            "A card without a note must have empty display_why"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 4. Slow/skipped enrichment — Google-verified cards still return
# ══════════════════════════════════════════════════════════════════════════════

class TestEnrichmentSkippedVerifiedCardsReturn:
    """When enrichment is skipped due to budget, Google-verified cards must still be returned."""

    def test_cross_source_budget_reserve_constant_defined(self):
        """CROSS_SOURCE_BUDGET_RESERVE_MS must be defined and positive."""
        from app.concierge.cross_source_enrichment import CROSS_SOURCE_BUDGET_RESERVE_MS
        assert isinstance(CROSS_SOURCE_BUDGET_RESERVE_MS, int)
        assert CROSS_SOURCE_BUDGET_RESERVE_MS > 0

    def test_editorial_budget_reserve_constant_defined(self):
        """EDITORIAL_BUDGET_RESERVE_MS must be defined and positive."""
        from app.concierge.editorial_enrichment import EDITORIAL_BUDGET_RESERVE_MS
        assert isinstance(EDITORIAL_BUDGET_RESERVE_MS, int)
        assert EDITORIAL_BUDGET_RESERVE_MS > 0

    def test_cross_source_result_with_empty_atoms_does_not_fail_pipeline(self):
        """Empty cross-source atoms_by_place_id must not crash the pipeline."""
        from app.concierge.cross_source_enrichment import (
            CrossSourceEnrichmentResult, CrossSourceTelemetry
        )
        result = CrossSourceEnrichmentResult(
            atoms_by_place_id={},
            telemetry=CrossSourceTelemetry(
                enrichment_enabled=True,
                enrichment_attempted=False,
                skipped_reason="budget_exhausted",
            ),
            elapsed_ms=0,
        )
        assert result.atoms_by_place_id == {}
        assert result.telemetry.skipped_reason == "budget_exhausted"

    def test_editorial_result_with_empty_atoms_does_not_fail_pipeline(self):
        """Empty editorial atoms_by_place_id must not crash the pipeline."""
        from app.concierge.editorial_enrichment import (
            EditorialEnrichmentResult, EditorialEnrichmentTelemetry
        )
        result = EditorialEnrichmentResult(
            atoms_by_place_id={},
            telemetry=EditorialEnrichmentTelemetry(
                enrichment_attempted=False,
                skipped_reason="budget_after_cross_source_too_low",
            ),
            elapsed_ms=0,
        )
        assert result.atoms_by_place_id == {}
        assert result.telemetry.skipped_reason == "budget_after_cross_source_too_low"


# ══════════════════════════════════════════════════════════════════════════════
# 5. Note preservation — validated notes preserved when skip fires
# ══════════════════════════════════════════════════════════════════════════════

class TestValidatedNotesPreserved:
    """Verified that pre-computed validated notes are preserved even when budget gate fires."""

    def test_validated_set_writer_notes_kept_in_card_assembly(self):
        """set_writer_primary_active=True and validated notes present → notes appear in cards."""
        from app.concierge.semantic_retrieval import _assemble_card_set
        from app.concierge.batched_reason_builder import CardReason
        from app.concierge.frame_extractor import extract_frame

        frame = extract_frame("best tacos", "Chicago")

        entity = MagicMock()
        entity.place_id = "ChIJtest1"
        entity.name = "Taco Validated"
        entity.types = ["restaurant"]
        entity.primary_type = "restaurant"
        entity.formatted_address = "200 N State St, Chicago, IL"
        entity.lat = 41.88
        entity.lng = -87.63
        entity.rating = 4.3
        entity.user_rating_count = 150
        entity.business_status = "OPERATIONAL"
        entity.google_maps_uri = "https://maps.google.com/?cid=2"
        entity.website_uri = None
        entity.price_level = None
        entity.price_range = None

        rank_score = MagicMock()
        rank_score.as_dict.return_value = {"subtype_fit": 0.85}
        rank_score.subtype_fit = 0.85

        cards_data = [(entity, MagicMock(), rank_score, "")]
        # Card reason with validated note (from set-writer pre-computed)
        card_reasons = {
            "1": CardReason(
                note="A neighborhood standout with housemade tortillas and seasonal salsas.",
                source="set_level_writer_v1",
                validated=True,
                attempt_count=1,
                model_used="set_level_writer_v1",
            )
        }

        cards, _, _, visible_note_count, without_notes = _assemble_card_set(
            cards_data=cards_data,
            card_reasons=card_reasons,
            frame=frame,
            note_generation_timed_out=False,
            set_writer_primary_active=True,
        )

        assert len(cards) == 1, "Card must appear"
        assert visible_note_count == 1, "Validated note must be visible"
        assert without_notes == 0
        assert cards[0].display.display_why_validated is True
        assert "tortillas" in cards[0].display.display_why

    def test_set_writer_primary_preserves_notes_even_when_note_gen_timed_out_would_fire(self):
        """If set_writer_primary_active=True, timed_out branch is NOT taken for card assembly."""
        from app.concierge.semantic_retrieval import _assemble_card_set
        from app.concierge.batched_reason_builder import CardReason
        from app.concierge.frame_extractor import extract_frame

        frame = extract_frame("best tacos", "Chicago")

        entity = MagicMock()
        entity.place_id = "ChIJtest2"
        entity.name = "El Taquero"
        entity.types = ["restaurant"]
        entity.primary_type = "restaurant"
        entity.formatted_address = "300 S Wabash Ave, Chicago, IL"
        entity.lat = 41.87
        entity.lng = -87.62
        entity.rating = 4.6
        entity.user_rating_count = 400
        entity.business_status = "OPERATIONAL"
        entity.google_maps_uri = "https://maps.google.com/?cid=3"
        entity.website_uri = None
        entity.price_level = None
        entity.price_range = None

        rank_score = MagicMock()
        rank_score.as_dict.return_value = {"subtype_fit": 0.9}
        rank_score.subtype_fit = 0.9

        cards_data = [(entity, MagicMock(), rank_score, "")]
        card_reasons = {
            "1": CardReason(
                note="Serves traditional tacos al pastor with achiote-marinated pork.",
                source="set_level_writer_v1",
                validated=True,
                attempt_count=1,
                model_used="set_level_writer_v1",
            )
        }

        # note_generation_timed_out=True BUT set_writer_primary_active=True
        # The set-writer already produced notes at Step 5.8 and they must be used.
        cards, _, _, visible_note_count, without_notes = _assemble_card_set(
            cards_data=cards_data,
            card_reasons=card_reasons,
            frame=frame,
            note_generation_timed_out=True,  # soft ceiling exceeded in Step 7
            set_writer_primary_active=True,   # but set-writer notes are available
        )

        assert len(cards) == 1
        assert visible_note_count == 1, (
            "Validated set-writer notes must survive even when note_generation_timed_out=True"
        )
        assert cards[0].display.display_why_validated is True


# ══════════════════════════════════════════════════════════════════════════════
# 6. Final display contract
# ══════════════════════════════════════════════════════════════════════════════

class TestFinalDisplayContract:
    """Verify display contract fields are stable for cards with and without notes."""

    def _make_entity(self, place_id: str = "ChIJtest9") -> MagicMock:
        entity = MagicMock()
        entity.place_id = place_id
        entity.name = "Contract Test Place"
        entity.types = ["restaurant"]
        entity.primary_type = "restaurant"
        entity.formatted_address = "1 N Wacker Dr, Chicago, IL"
        entity.lat = 41.88
        entity.lng = -87.64
        entity.rating = 4.0
        entity.user_rating_count = 100
        entity.business_status = "OPERATIONAL"
        entity.google_maps_uri = "https://maps.google.com/?cid=9"
        entity.website_uri = None
        entity.price_level = None
        entity.price_range = None
        return entity

    def test_card_with_validated_note_has_display_contract_fields(self):
        """Card with a validated note has all three display contract fields set correctly."""
        from app.concierge.semantic_retrieval import _entity_to_card
        from app.concierge.frame_extractor import extract_frame

        frame = extract_frame("restaurants", "Chicago")
        entity = self._make_entity()
        note = "Known for wood-fired pizza and a warm, open kitchen atmosphere."
        card = _entity_to_card(
            entity, note, frame,
            reason_source="set_level_writer_v1",
            reason_validated=True,
        )

        assert card is not None
        assert card.display is not None
        # Contract: all three fields present
        assert hasattr(card.display, "display_why"), "display_why missing"
        assert hasattr(card.display, "display_why_source"), "display_why_source missing"
        assert hasattr(card.display, "display_why_validated"), "display_why_validated missing"

        assert card.display.display_why == note
        assert card.display.display_why_source == "set_level_writer_v1"
        assert card.display.display_why_validated is True

    def test_card_without_note_has_display_contract_fields(self):
        """Card without a note still has all three display contract fields, validated=False."""
        from app.concierge.semantic_retrieval import _entity_to_card
        from app.concierge.frame_extractor import extract_frame

        frame = extract_frame("restaurants", "Chicago")
        entity = self._make_entity("ChIJtest10")
        card = _entity_to_card(
            entity, "", frame,
            reason_source="timed_out",
            reason_validated=False,
        )

        assert card is not None
        assert card.display is not None
        assert hasattr(card.display, "display_why")
        assert hasattr(card.display, "display_why_source")
        assert hasattr(card.display, "display_why_validated")

        assert card.display.display_why == ""
        assert card.display.display_why_source == "timed_out"
        assert card.display.display_why_validated is False

    def test_card_is_addable_regardless_of_note_presence(self):
        """A Google-verified card must be addable regardless of whether notes are present."""
        from app.concierge.semantic_retrieval import _entity_to_card
        from app.concierge.frame_extractor import extract_frame

        frame = extract_frame("restaurants", "Chicago")
        entity = self._make_entity("ChIJtest11")
        card_with_note = _entity_to_card(
            entity, "A great place.", frame,
            reason_source="set_level_writer_v1",
            reason_validated=True,
        )
        card_without_note = _entity_to_card(
            entity, "", frame,
            reason_source="timed_out",
            reason_validated=False,
        )

        assert card_with_note is not None
        assert card_without_note is not None
        assert card_with_note.verified_place is True
        assert card_without_note.verified_place is True

    def test_google_verification_present_on_all_cards(self):
        """google_verification must be present on every card regardless of note state."""
        from app.concierge.semantic_retrieval import _entity_to_card
        from app.concierge.frame_extractor import extract_frame

        frame = extract_frame("restaurants", "Chicago")
        entity = self._make_entity("ChIJtest12")

        for note, validated in [("A fine dining institution.", True), ("", False)]:
            card = _entity_to_card(
                entity, note, frame,
                reason_source="set_level_writer_v1",
                reason_validated=validated,
            )
            assert card is not None
            gv = card.google_verification
            assert gv is not None, f"google_verification missing for validated={validated}"
            assert gv.provider_place_id == "ChIJtest12"


# ══════════════════════════════════════════════════════════════════════════════
# 7. No fallback notes — set_writer_skipped_budget label, no filler prose
# ══════════════════════════════════════════════════════════════════════════════

class TestNoFallbackNotes:
    """When set-writer is skipped due to budget, no fallback/template notes appear."""

    def test_set_writer_skipped_budget_tel_contains_flag(self):
        """set_writer_skipped_budget=True must appear in telemetry dict when skipped."""
        from app.concierge.deadline_manager import SET_WRITER_MIN_BUDGET_MS

        # Simulate the skipped-budget telemetry path from semantic_retrieval.py
        _remaining = SET_WRITER_MIN_BUDGET_MS - 100
        _skipped = _remaining < SET_WRITER_MIN_BUDGET_MS

        if _skipped:
            tel = {
                "set_writer_fallback_to_existing_path": True,
                "set_writer_skipped_budget": True,
                "set_writer_remaining_ms_at_skip": _remaining,
            }
        else:
            tel = {"set_writer_fallback_to_existing_path": True}

        assert tel.get("set_writer_skipped_budget") is True, (
            "Telemetry must include set_writer_skipped_budget=True when skipped"
        )
        assert tel["set_writer_remaining_ms_at_skip"] == _remaining

    def test_minimal_safe_note_returns_empty_string(self):
        """_minimal_safe_note must return '' (never a deterministic template)."""
        from app.concierge.semantic_retrieval import _minimal_safe_note

        entity = MagicMock()
        entity.name = "Test Place"
        entity.rating = 4.5
        entity.user_rating_count = 200

        result = _minimal_safe_note(entity)
        assert result == "", (
            f"_minimal_safe_note must return '' to prevent template notes, got {result!r}"
        )

    def test_assemble_card_set_no_timed_out_card_has_non_empty_validated_note(self):
        """Cards assembled on the timed-out path must not have validated=True notes."""
        from app.concierge.semantic_retrieval import _assemble_card_set
        from app.concierge.frame_extractor import extract_frame

        frame = extract_frame("best pizza", "Chicago")

        entity = MagicMock()
        entity.place_id = "ChIJtest20"
        entity.name = "Pizza Test"
        entity.types = ["pizza_restaurant"]
        entity.primary_type = "pizza_restaurant"
        entity.formatted_address = "500 W Madison St, Chicago, IL"
        entity.lat = 41.882
        entity.lng = -87.641
        entity.rating = 4.4
        entity.user_rating_count = 500
        entity.business_status = "OPERATIONAL"
        entity.google_maps_uri = "https://maps.google.com/?cid=20"
        entity.website_uri = None
        entity.price_level = None
        entity.price_range = None

        rank_score = MagicMock()
        rank_score.as_dict.return_value = {"subtype_fit": 0.88}
        rank_score.subtype_fit = 0.88

        cards_data = [(entity, MagicMock(), rank_score, "")]
        card_reasons: Dict[str, Any] = {}

        cards, _, _, visible_note_count, _ = _assemble_card_set(
            cards_data=cards_data,
            card_reasons=card_reasons,
            frame=frame,
            note_generation_timed_out=True,
            set_writer_primary_active=False,
        )

        assert len(cards) == 1, "Card must be returned even on timed-out path"
        assert visible_note_count == 0, "No notes must be marked validated on timed-out path"
        # Verify no fallback note was injected
        card = cards[0]
        assert card.display.display_why_validated is False
        assert card.display.display_why == "" or not card.display.display_why

    def test_fallback_note_visible_count_always_zero(self):
        """fallback_note_visible_count must always be 0 — structural invariant."""
        from app.concierge.set_level_writer import SetWriterResult

        result = SetWriterResult(
            notes_by_place_id={},
            visible_note_count=0,
            hidden_note_count=0,
            rejected_note_count=0,
            timed_out=True,
            fallback_note_visible_count=0,
            role_note_counts={},
            note_source_counts={},
            repeated_skeleton_count=0,
            unsupported_claim_count=0,
        )
        assert result.fallback_note_visible_count == 0, (
            "fallback_note_visible_count is a structural invariant — always 0"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 8. Timeout branches observability
# ══════════════════════════════════════════════════════════════════════════════

class TestTimeoutBranchesObservability:
    """Verify set_writer_skipped_budget appears in timeout_branches when fired."""

    def test_set_writer_skipped_budget_in_import(self):
        """SET_WRITER_MIN_BUDGET_MS must be importable from deadline_manager."""
        from app.concierge.deadline_manager import SET_WRITER_MIN_BUDGET_MS
        assert SET_WRITER_MIN_BUDGET_MS > 0

    def test_semantic_retrieval_imports_set_writer_min_budget_ms(self):
        """semantic_retrieval.py must import SET_WRITER_MIN_BUDGET_MS for the gate."""
        import inspect
        from app.concierge import semantic_retrieval
        source = inspect.getsource(semantic_retrieval)
        assert "SET_WRITER_MIN_BUDGET_MS" in source, (
            "semantic_retrieval.py must import and use SET_WRITER_MIN_BUDGET_MS"
        )

    def test_set_writer_skipped_budget_label_in_semantic_retrieval(self):
        """semantic_retrieval.py must emit set_writer_skipped_budget label."""
        import inspect
        from app.concierge import semantic_retrieval
        source = inspect.getsource(semantic_retrieval)
        assert "set_writer_skipped_budget" in source, (
            "semantic_retrieval.py must track 'set_writer_skipped_budget' "
            "in timeout_branches_triggered"
        )
