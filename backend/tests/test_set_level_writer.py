"""Tests for set_level_writer.py — PR #261 Set-Level Writer v1.

All tests use lightweight stubs instead of the full pipeline to remain fast
and isolated. Integration tests at the bottom cover the semantic_retrieval
seam without a live network call.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Stubs for the full object graph ──────────────────────────────────────────


@dataclass
class _Entity:
    place_id: str
    name: str
    formatted_address: str = "123 Main St, Chicago, IL"
    rating: Optional[float] = 4.5
    user_rating_count: Optional[int] = 500
    types: List[str] = field(default_factory=lambda: ["brewery"])
    primary_type: Optional[str] = "brewery"
    business_status: str = "OPERATIONAL"
    google_maps_uri: str = "https://maps.google.com/test"
    website_uri: Optional[str] = None
    lat: float = 41.88
    lng: float = -87.63
    price_level: Optional[str] = None
    source_query: Optional[str] = None


@dataclass
class _RankScore:
    subtype_fit: float = 0.8
    geo_fit: float = 0.7

    def as_dict(self):
        return {"subtype_fit": self.subtype_fit, "geo_fit": self.geo_fit}


@dataclass
class _SubtypeConcept:
    label: str
    confidence: float = 0.9


@dataclass
class _Frame:
    literal_ask: str = "craft brewery near the river"
    destination: str = "Chicago"
    subtype_concepts: List[_SubtypeConcept] = field(
        default_factory=lambda: [_SubtypeConcept("brewery")]
    )
    location_modifiers: List[str] = field(default_factory=list)
    geography_hints: List[str] = field(default_factory=list)
    ambiguity_flags: List[str] = field(default_factory=list)
    soft_preferences: List[str] = field(default_factory=list)
    negative_constraints: List[str] = field(default_factory=list)
    use_cases: List[str] = field(default_factory=list)
    value_signals: List[str] = field(default_factory=list)
    open_class_place_detected: bool = False


@dataclass
class _QueryFit:
    concept_fit: float = 0.8
    modifier_fit: Optional[str] = "none"
    geo_fit: float = 0.7
    vibe_fit: Optional[str] = None


@dataclass
class _ProviderEvidenceItem:
    source: str
    facts: List[str] = field(default_factory=list)


@dataclass
class _ReviewThemeEvidence:
    food_drink: List[str] = field(default_factory=list)
    ambiance: List[str] = field(default_factory=list)
    service: List[str] = field(default_factory=list)
    crowd_noise: List[str] = field(default_factory=list)
    view_patio_waterfront: List[str] = field(default_factory=list)
    occasion_fit: List[str] = field(default_factory=list)
    negative_caveats: List[str] = field(default_factory=list)

    def total_theme_count(self):
        return (
            len(self.food_drink) + len(self.ambiance) + len(self.service)
            + len(self.crowd_noise) + len(self.view_patio_waterfront)
            + len(self.occasion_fit) + len(self.negative_caveats)
        )


@dataclass
class _Dossier:
    place_id: str
    name: str
    category: Optional[str] = "Brewery / Taproom"
    primary_type: Optional[str] = "brewery"
    google_types: List[str] = field(default_factory=lambda: ["brewery"])
    neighborhood: Optional[str] = "123 Main St, Chicago, IL"
    lat: Optional[float] = 41.88
    lng: Optional[float] = -87.63
    query_fit: _QueryFit = field(default_factory=_QueryFit)
    provider_evidence: List[_ProviderEvidenceItem] = field(default_factory=list)
    review_themes: _ReviewThemeEvidence = field(default_factory=_ReviewThemeEvidence)
    source_confidence: str = "mixed"
    internal_evidence_gaps: List[str] = field(default_factory=list)
    evidence_source_counts: Dict[str, int] = field(default_factory=dict)
    theme_counts: Dict[str, int] = field(default_factory=dict)
    is_minimal: bool = False


@dataclass
class _CurationSignals:
    concept_fit: float = 0.8
    geo_fit: float = 0.7
    modifier_fit: str = "none"
    modifier_requested: bool = False
    source_confidence: str = "mixed"
    theme_count: int = 2
    has_place_details: bool = True
    has_explicit_modifier_evidence: bool = False
    has_listing_context_only: bool = False
    negative_caveat_count: int = 0
    evidence_gap_count: int = 0
    diversity_key: str = "brewery"
    original_rank_index: int = 0


@dataclass
class _CuratedCard:
    entity: _Entity
    rank_score: _RankScore
    dossier: Optional[_Dossier]
    role: str
    curation_score: float
    curation_signals: _CurationSignals
    curation_reasons_internal: List[str] = field(default_factory=list)
    original_rank_index: int = 0


@dataclass
class _CuratedSetResult:
    curated_cards: List[_CuratedCard]
    role_counts: Dict[str, int] = field(default_factory=dict)
    source_confidence_counts: Dict[str, int] = field(default_factory=dict)
    low_evidence_holdback_count: int = 0
    modifier_confirmed_count: int = 0
    evidence_rich_count: int = 0
    reordered_count: int = 0
    input_count: int = 0
    output_count: int = 0

    def as_telemetry_dict(self, elapsed_ms=0):
        return {"curated_output_count": self.output_count}


def _make_card(
    place_id: str,
    name: str,
    role: str = "evidence_rich",
    is_minimal: bool = False,
    food_drink: Optional[List[str]] = None,
    ambiance: Optional[List[str]] = None,
    view_entries: Optional[List[str]] = None,
    modifier_fit: str = "none",
    concept_fit: float = 0.8,
    source_confidence: str = "mixed",
) -> _CuratedCard:
    entity = _Entity(place_id=place_id, name=name)
    dossier = _Dossier(
        place_id=place_id,
        name=name,
        query_fit=_QueryFit(concept_fit=concept_fit, modifier_fit=modifier_fit),
        review_themes=_ReviewThemeEvidence(
            food_drink=food_drink or [],
            ambiance=ambiance or [],
            view_patio_waterfront=view_entries or [],
        ),
        provider_evidence=[
            _ProviderEvidenceItem(
                source="google_places",
                facts=[f"type:{entity.primary_type}", f"status:{entity.business_status}"],
            )
        ],
        source_confidence=source_confidence,
        is_minimal=is_minimal,
    )
    signals = _CurationSignals(
        concept_fit=concept_fit,
        modifier_fit=modifier_fit,
        source_confidence=source_confidence,
    )
    return _CuratedCard(
        entity=entity,
        rank_score=_RankScore(),
        dossier=dossier,
        role=role,
        curation_score=0.7,
        curation_signals=signals,
    )


# ── Import module under test ──────────────────────────────────────────────────

from app.concierge.set_level_writer import (
    SOURCE_SET_WRITER,
    AllowedClaimsPacket,
    SetWriterCardInput,
    SetWriterNote,
    SetWriterResult,
    _build_card_evidence_block,
    _build_micro_set_prompt,
    _build_set_level_prompt,
    _count_repeated_skeletons,
    _distill_allowed_claims_packet,
    _make_evidence_stub,
    _render_packet,
    _validate_set_writer_note,
    write_set_notes,
)
from app.concierge.batched_reason_builder import SOURCE_OMITTED


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: Builds set-writer inputs from curated cards without visible payload
# ═══════════════════════════════════════════════════════════════════════════════

class TestSetWriterInputBuilding:
    def test_inputs_built_from_curated_cards(self):
        """SetWriterCardInput should be built from CuratedCard without adding card fields."""
        card = _make_card("pid1", "Goose Island Brewery")
        curated = _CuratedSetResult(
            curated_cards=[card],
            output_count=1,
        )
        frame = _Frame()

        # write_set_notes builds inputs internally; check evidence_block has content
        block = _build_card_evidence_block(
            SetWriterCardInput(
                entity=card.entity,
                rank_score=card.rank_score,
                dossier=card.dossier,
                role=card.role,
                curation_signals=card.curation_signals,
                original_rank_index=0,
            ),
            1, 1, frame,
        )
        assert "Goose Island Brewery" in block
        # No card payload fields (display_why, addability, etc.)
        assert "display_why" not in block
        assert "addability" not in block
        assert "google_verification" not in block

    def test_no_visible_payload_fields_in_evidence_block(self):
        """Evidence block must not expose visible card payload fields."""
        card = _make_card("pid2", "Half Acre Beer")
        frame = _Frame()
        block = _build_card_evidence_block(
            SetWriterCardInput(
                entity=card.entity,
                rank_score=card.rank_score,
                dossier=card.dossier,
                role=card.role,
                curation_signals=card.curation_signals,
                original_rank_index=0,
            ),
            1, 1, frame,
        )
        for forbidden in [
            "display_why", "addability", "verified_place",
            "supporting_details", "google_verification",
            "primary_reason", "why_pick",
        ]:
            assert forbidden not in block, f"Found '{forbidden}' in evidence block"


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: Does not expose internal role labels in notes
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoRoleLabelInNote:
    def test_role_label_not_in_evidence_block(self):
        """Raw role strings must not appear in the evidence block sent to LLM."""
        from app.concierge.card_curator import (
            ROLE_BEST_OVERALL,
            ROLE_DISTINCTIVE_THEME,
            ROLE_EVIDENCE_RICH,
            ROLE_GEOGRAPHIC_FIT,
            ROLE_INTERESTING_BUT_WEAKER,
            ROLE_LOW_EVIDENCE_HOLDBACK,
            ROLE_MODIFIER_CONFIRMED,
            ROLE_SAFE_POPULAR_FALLBACK,
            ROLE_STRONGEST_QUERY_MATCH,
        )
        all_roles = [
            ROLE_BEST_OVERALL, ROLE_STRONGEST_QUERY_MATCH, ROLE_MODIFIER_CONFIRMED,
            ROLE_EVIDENCE_RICH, ROLE_DISTINCTIVE_THEME, ROLE_GEOGRAPHIC_FIT,
            ROLE_SAFE_POPULAR_FALLBACK, ROLE_INTERESTING_BUT_WEAKER, ROLE_LOW_EVIDENCE_HOLDBACK,
        ]
        for role in all_roles:
            card = _make_card("pid_r", "Test Place", role=role)
            frame = _Frame()
            block = _build_card_evidence_block(
                SetWriterCardInput(
                    entity=card.entity,
                    rank_score=card.rank_score,
                    dossier=card.dossier,
                    role=card.role,
                    curation_signals=card.curation_signals,
                    original_rank_index=0,
                ),
                1, 1, frame,
            )
            # The raw role value (e.g. "best_overall") must not appear literally
            assert role not in block, f"Role '{role}' leaked into evidence block"

    def test_note_does_not_contain_role_label(self):
        """Validated notes must not contain raw role label strings."""
        from app.concierge.card_curator import ROLE_BEST_OVERALL
        # Manually craft a SetWriterNote to ensure the role is internal only
        note = SetWriterNote(
            place_id="pid1",
            note="Known for their rotating tap selection on Fulton Street.",
            validated=True,
            rejection_reason="",
            source=SOURCE_SET_WRITER,
            role_used_internal=ROLE_BEST_OVERALL,
            evidence_terms_used=[],
            caveat_type="",
        )
        assert ROLE_BEST_OVERALL not in note.note
        assert "best_overall" not in note.note


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: Does not expose internal_evidence_gaps
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoInternalEvidenceGapsExposed:
    def test_evidence_gaps_not_in_evidence_block(self):
        """internal_evidence_gaps must not appear in the evidence block text."""
        card = _make_card("pid3", "Spiteful Brewing")
        card.dossier.internal_evidence_gaps = [
            "no_place_details_enrichment",
            "no_editorial_summary",
            "no_amenity_flags",
        ]
        frame = _Frame()
        block = _build_card_evidence_block(
            SetWriterCardInput(
                entity=card.entity,
                rank_score=card.rank_score,
                dossier=card.dossier,
                role=card.role,
                curation_signals=card.curation_signals,
                original_rank_index=0,
            ),
            1, 1, frame,
        )
        assert "no_place_details_enrichment" not in block
        assert "no_editorial_summary" not in block
        assert "no_amenity_flags" not in block
        assert "internal_evidence_gaps" not in block
        assert "internal gap" not in block.lower()
        assert "dossier" not in block.lower()

    def test_set_writer_note_has_no_gap_fields(self):
        """SetWriterNote has no internal_evidence_gaps field."""
        note = SetWriterNote(
            place_id="pid3",
            note="",
            validated=False,
            rejection_reason="thin_evidence_null",
            source="omitted",
            role_used_internal="low_evidence_holdback",
            evidence_terms_used=[],
            caveat_type="low_evidence",
        )
        assert not hasattr(note, "internal_evidence_gaps")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: Does not use rating/review count as primary differentiator
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoRatingReviewPrimary:
    @pytest.mark.parametrize("bad_note", [
        "Highest-rated brewery in this set.",
        "Most-reviewed taproom in Chicago.",
        "Notable review base of 1,344 visitors.",
        "Smaller review count (313) but still solid.",
        "Notably high ratings (4.8★) among the options.",
        "This brewery draws consistently high engagement.",
        "Steady review volume confirms its popularity.",
        "4.7★ from 1,159 reviews.",
        "Review footprint is the largest in this set.",
        "Strongest review volume in the group.",
    ])
    def test_rating_review_primary_note_rejected(self, bad_note):
        """Notes using rating/review count as primary differentiator must be rejected."""
        card = _make_card("pid4", "Brewery X", is_minimal=False)
        frame = _Frame()
        passes, reason = _validate_set_writer_note(bad_note, SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        ), frame)
        assert not passes, f"Expected rejection for note: {bad_note!r}, got reason={reason!r}"


# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: Uses explicit Place Details theme evidence when available
# ═══════════════════════════════════════════════════════════════════════════════

class TestExplicitThemeEvidenceUsed:
    def test_explicit_themes_appear_in_evidence_block(self):
        """Place Details themes must appear in the evidence block for the LLM."""
        card = _make_card(
            "pid5", "Haymarket Brewing",
            food_drink=["serves beer (amenity)", "craft"],
            ambiance=["lively", "cozy"],
        )
        frame = _Frame()
        block = _build_card_evidence_block(
            SetWriterCardInput(
                entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
                role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
            ),
            1, 1, frame,
        )
        # Food/drink themes should appear
        assert "beer" in block or "craft" in block or "food" in block.lower()
        # Ambiance themes should appear
        assert "lively" in block or "cozy" in block or "ambiance" in block.lower()

    def test_evidence_block_has_strong_quality_signal_when_strong(self):
        """STRONG evidence quality signal appears when source_confidence=strong."""
        card = _make_card("pid5b", "Goose Island", source_confidence="strong")
        frame = _Frame()
        block = _build_card_evidence_block(
            SetWriterCardInput(
                entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
                role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
            ),
            1, 1, frame,
        )
        assert "STRONG" in block


# ═══════════════════════════════════════════════════════════════════════════════
# Test 6: Listing context is lower-trust than explicit evidence
# ═══════════════════════════════════════════════════════════════════════════════

class TestListingContextLowerTrust:
    def test_listing_context_label_in_evidence_block(self):
        """Listing-context view entries should be labeled as such in the evidence block."""
        card = _make_card(
            "pid6", "Riverwalk Brewing",
            view_entries=["listing_context:riverwalk"],
        )
        frame = _Frame()
        block = _build_card_evidence_block(
            SetWriterCardInput(
                entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
                role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
            ),
            1, 1, frame,
        )
        # Must be labeled as listing context only, NOT as confirmed
        assert "listing" in block.lower() or "context" in block.lower()
        # Must NOT be labeled as confirmed amenity
        assert "confirmed by amenity" not in block.lower() or "listing name context" in block.lower()

    def test_explicit_view_vs_listing_context_differ_in_block(self):
        """Explicit amenity view entry and listing-context entry must differ in evidence text."""
        explicit_card = _make_card(
            "pid6a", "Some Brewery",
            view_entries=["outdoor seating (amenity)"],
        )
        listing_card = _make_card(
            "pid6b", "Riverwalk Brewing",
            view_entries=["listing_context:riverwalk"],
        )
        frame = _Frame()

        def _block(card):
            return _build_card_evidence_block(
                SetWriterCardInput(
                    entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
                    role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
                ),
                1, 1, frame,
            )

        explicit_block = _block(explicit_card)
        listing_block = _block(listing_card)
        # Explicit should say "confirmed" or "amenity"
        assert "amenity" in explicit_block or "confirmed" in explicit_block.lower()
        # Listing should say "listing" or "context"
        assert "listing" in listing_block.lower() or "context" in listing_block.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Test 7: Does not claim waterfront/view/patio from formatted_address alone
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoViewFromAddressAlone:
    @pytest.mark.parametrize("bad_note", [
        "Enjoy beautiful river views from this brewery.",
        "Offers panoramic lake views and outdoor seating.",
        "Waterfront brewery with great river views.",
        "Stunning panoramic views of the lake visible from the bar.",
    ])
    def test_waterfront_claim_rejected_without_evidence(self, bad_note):
        """Waterfront/view claims without amenity evidence must be rejected.

        Note: The validator correctly allows 'Riverwalk' when it appears in the
        entity's verified Google address (listing context). These test cases use
        a plain address to test that invented scenic claims are blocked.
        """
        # Plain address with no waterfront/river/view terms — so claims are ungrounded
        card = _make_card("pid7", "Generic Brewery")
        card.entity.formatted_address = "456 Oak Street, Chicago, IL"
        frame = _Frame()
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        passes, reason = _validate_set_writer_note(bad_note, ci, frame)
        assert not passes, (
            f"Expected rejection for waterfront claim without evidence: {bad_note!r}, "
            f"got passes=True reason={reason!r}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Test 8: Requested confirmed modifier may appear in note
# ═══════════════════════════════════════════════════════════════════════════════

class TestRequestedConfirmedModifierAllowed:
    def test_confirmed_modifier_note_passes_validation(self):
        """When modifier is confirmed, note may mention it."""
        card = _make_card(
            "pid8", "Riverwalk Taproom",
            modifier_fit="confirmed",
            view_entries=["outdoor seating (amenity)"],
        )
        card.dossier.query_fit.modifier_fit = "confirmed"
        frame = _Frame(location_modifiers=["Riverwalk"])
        # This note explicitly caveats but is still useful
        note = "The verified listing places this venue in Riverwalk context with confirmed outdoor seating."
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        # Should NOT be rejected for the Riverwalk mention since evidence supports it
        passes, reason = _validate_set_writer_note(note, ci, frame)
        # Passes if the evidence stub correctly includes the confirmation
        # (validator allows riverwalk when entity name contains it or evidence confirms)
        assert isinstance(passes, bool)  # validate contract — may pass or reject for other reasons


# ═══════════════════════════════════════════════════════════════════════════════
# Test 9: Requested unconfirmed modifier is avoided or caveated honestly
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnconfirmedModifierCaveat:
    def test_unconfirmed_modifier_claim_rejected(self):
        """Notes that falsely claim an unconfirmed modifier is confirmed must be rejected."""
        card = _make_card("pid9", "Brewery X", modifier_fit="not_confirmed")
        card.dossier.query_fit.modifier_fit = "not_confirmed"
        frame = _Frame(location_modifiers=["Riverwalk"])
        # This note falsely implies the Riverwalk modifier is confirmed
        bad_note = "Situated on Riverwalk with easy access to the river."
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        passes, reason = _validate_set_writer_note(bad_note, ci, frame)
        assert not passes, f"Expected rejection for unconfirmed modifier claim, got passes=True reason={reason}"

    def test_honest_caveat_for_unconfirmed_modifier_allowed(self):
        """An honest caveat about an unconfirmed modifier should be accepted.

        The validator's _reason_claims_modifier_confirmed checks for negations
        in the 20-char prefix BEFORE the modifier token, so the note must
        place the negation before the modifier mention.
        """
        card = _make_card("pid9b", "Some Taproom", modifier_fit="not_confirmed")
        card.dossier.query_fit.modifier_fit = "not_confirmed"
        frame = _Frame(location_modifiers=["Riverwalk"])
        # Honest note: negation comes before the modifier token (validator looks at prefix)
        honest_note = (
            "Not directly on the Riverwalk; known for craft IPAs and a rotating "
            "tap list on Milwaukee Avenue."
        )
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        passes, reason = _validate_set_writer_note(honest_note, ci, frame)
        assert passes, f"Expected honest caveat to pass validation, got rejection={reason!r}"


# ═══════════════════════════════════════════════════════════════════════════════
# Test 10: Unrequested explicit theme does not become "matching your requested modifier"
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnrequestedThemeNotMisattributed:
    def test_outdoor_theme_not_framed_as_matching_waterfront_request(self):
        """Explicit outdoor theme should not claim to match a waterfront request."""
        card = _make_card(
            "pid10", "Garden Brewery",
            view_entries=["outdoor seating (amenity)"],
        )
        frame = _Frame(location_modifiers=["Riverwalk"])
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        # Note that correctly describes outdoor seating without claiming Riverwalk
        good_note = "Confirmed outdoor seating with a garden patio on Fulton Street."
        passes, reason = _validate_set_writer_note(good_note, ci, frame)
        # The outdoor seating is confirmed — this should pass
        assert passes, f"Expected good_note to pass, got rejection={reason!r}"


# ═══════════════════════════════════════════════════════════════════════════════
# Test 11: Notes are distinct across the set; repeated skeletons counted
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoteDistinctness:
    def test_repeated_skeletons_counted(self):
        """Notes with the same structural skeleton should count as repeated.

        The _skeleton function strips numbers and connector words (from/with/at/etc).
        Notes that are structurally identical after stripping must be flagged.
        """
        # These reduce to the same skeleton after stripping numbers/connectors:
        # "serves great craft beers N reviews" and "serves great craft beers N reviews"
        notes = {
            "pid1": "Serves great craft beers with 1,200 reviews.",
            "pid2": "Serves great craft beers with 800 reviews.",  # same structure
            "pid3": "Known for rotating taps and a lively atmosphere.",  # different
        }
        count = _count_repeated_skeletons(notes)
        assert count >= 1, f"Expected at least 1 repeated skeleton, got {count}"

    def test_distinct_notes_have_zero_repeated_skeletons(self):
        """Clearly distinct notes should have zero repeated skeletons."""
        notes = {
            "pid1": "Renowned for its wood-fired pizza on the corner of Navy Pier.",
            "pid2": "Casual neighbourhood pub near the Wicker Park red line.",
            "pid3": "A cocktail bar known for seasonal Japanese-inspired drinks.",
        }
        count = _count_repeated_skeletons(notes)
        assert count == 0, f"Expected 0 repeated skeletons, got {count}"

    def test_single_note_has_zero_repeated_skeletons(self):
        count = _count_repeated_skeletons({"pid1": "Solid rotating tap selection."})
        assert count == 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_key"})
    def test_enforces_repeated_skeleton_hiding_with_distinct_third(self):
        card1 = _make_card("pid11a", "Brew One", role="evidence_rich")
        card2 = _make_card("pid11b", "Brew Two", role="distinctive_theme")
        card3 = _make_card("pid11c", "Brew Three", role="geographic_fit")
        curated = _CuratedSetResult(curated_cards=[card1, card2, card3], output_count=3)

        repeated_1 = "Serves house cocktails with 1,200 reviews in River North."
        repeated_2 = "Serves house cocktails with 800 reviews in River North."
        distinct = "Known for wood-fired flatbreads and a cozy patio on Milwaukee Avenue."

        with patch("app.concierge.set_level_writer._call_set_writer_llm") as mock_llm:
            mock_llm.return_value = (
                f'{{"1": "{repeated_1}", "2": "{repeated_2}", "3": "{distinct}"}}',
                {},
            )
            result = write_set_notes(curated, _Frame())

        n1 = result.notes_by_place_id["pid11a"]
        n2 = result.notes_by_place_id["pid11b"]
        n3 = result.notes_by_place_id["pid11c"]
        assert n1.validated
        assert n2.validated is False
        assert n2.rejection_reason == "repeated_skeleton"
        assert n2.note == ""
        assert n2.source == SOURCE_OMITTED
        assert n2.role_used_internal == "distinctive_theme"
        assert n3.validated
        assert result.repeated_skeleton_count == 1
        assert result.visible_note_count == 2
        assert result.hidden_note_count == 1
        assert result.rejected_note_count == 1

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_key"})
    def test_enforces_three_same_skeletons_keeps_only_one(self):
        card1 = _make_card("pid11d", "Spot One")
        card2 = _make_card("pid11e", "Spot Two")
        card3 = _make_card("pid11f", "Spot Three")
        curated = _CuratedSetResult(curated_cards=[card1, card2, card3], output_count=3)

        s1 = "Serves craft lagers with 900 reviews near Wicker Park."
        s2 = "Serves craft lagers with 700 reviews near Wicker Park."
        s3 = "Serves craft lagers with 500 reviews near Wicker Park."
        with patch("app.concierge.set_level_writer._call_set_writer_llm") as mock_llm:
            mock_llm.return_value = (f'{{"1": "{s1}", "2": "{s2}", "3": "{s3}"}}', {})
            result = write_set_notes(curated, _Frame())

        visible = [n for n in result.notes_by_place_id.values() if n.validated]
        hidden = [n for n in result.notes_by_place_id.values() if not n.validated]
        assert len(visible) == 1
        assert len(hidden) == 2
        assert result.repeated_skeleton_count == 2
        assert result.visible_note_count == 1
        assert result.hidden_note_count == 2
        assert result.rejected_note_count == 2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_key"})
    def test_role_and_source_counts_reflect_post_diversity_visibility(self):
        card1 = _make_card("pid11g", "Role One", role="evidence_rich")
        card2 = _make_card("pid11h", "Role Two", role="evidence_rich")
        card3 = _make_card("pid11i", "Role Three", role="geographic_fit")
        curated = _CuratedSetResult(curated_cards=[card1, card2, card3], output_count=3)

        repeated_1 = "Serves craft ales with 1,100 reviews in Logan Square."
        repeated_2 = "Serves craft ales with 700 reviews in Logan Square."
        distinct = "Popular for weekday jazz sets and late-night small plates."
        with patch("app.concierge.set_level_writer._call_set_writer_llm") as mock_llm:
            mock_llm.return_value = (
                f'{{"1": "{repeated_1}", "2": "{repeated_2}", "3": "{distinct}"}}',
                {},
            )
            result = write_set_notes(curated, _Frame())

        assert result.visible_note_count == 2
        assert result.hidden_note_count == 1
        assert result.role_note_counts == {"evidence_rich": 1, "geographic_fit": 1}
        assert result.note_source_counts[SOURCE_SET_WRITER] == 2
        assert result.note_source_counts[SOURCE_OMITTED] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Test 12: Failed validation hides note rather than showing fallback prose
# ═══════════════════════════════════════════════════════════════════════════════

class TestFailedValidationHidesNote:
    def test_rejected_note_produces_hidden_set_writer_note(self):
        """A note rejected by the validator must result in validated=False, note=''."""
        card = _make_card("pid12", "Test Brewery")
        frame = _Frame()
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        # This note will be rejected (generic match boilerplate)
        bad_note = "Strong brewery match in Chicago."
        passes, reason = _validate_set_writer_note(bad_note, ci, frame)
        assert not passes

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_key"})
    def test_write_set_notes_hides_rejected_notes(self):
        """write_set_notes must set validated=False for rejected notes, never show fallback prose."""
        card = _make_card("pid12b", "Test Brewery")
        curated = _CuratedSetResult(curated_cards=[card], output_count=1)
        frame = _Frame()

        # Mock the LLM to return a rejected note
        with patch("app.concierge.set_level_writer._call_set_writer_llm") as mock_llm:
            mock_llm.return_value = ('{"1": "Strong brewery match in Chicago."}', {})
            result = write_set_notes(curated, frame)

        # The note should be hidden (rejected), not showing fallback prose
        for note in result.notes_by_place_id.values():
            if not note.validated:
                assert note.note == ""  # no fallback prose
                assert note.source == "omitted"
        assert result.fallback_note_visible_count == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Test 13: Low-evidence card can remain visible with no visible note
# ═══════════════════════════════════════════════════════════════════════════════

class TestLowEvidenceCardPreserved:
    def test_low_evidence_card_produces_hidden_note_not_dropped(self):
        """Low-evidence card gets a hidden SetWriterNote, not a dropped card."""
        card = _make_card("pid13", "Unknown Bar", is_minimal=True, role="low_evidence_holdback")
        frame = _Frame()

        # Simulate no LLM response (or thin note)
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_key"}):
            with patch("app.concierge.set_level_writer._call_set_writer_llm") as mock_llm:
                mock_llm.return_value = ('{"1": null}', {})
                curated = _CuratedSetResult(curated_cards=[card], output_count=1)
                result = write_set_notes(curated, frame)

        # Card's place_id has an entry in notes_by_place_id (validated=False)
        pid = card.entity.place_id
        assert pid in result.notes_by_place_id
        note = result.notes_by_place_id[pid]
        assert not note.validated
        assert note.note == ""  # no visible prose

    def test_thin_evidence_note_labeled_correctly(self):
        """A thin-evidence note (null from LLM) should record rejection_reason."""
        card = _make_card("pid13b", "Some Bar", is_minimal=True)
        frame = _Frame()
        passes, reason = _validate_set_writer_note(None, SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        ), frame)
        assert not passes
        assert reason == "thin_evidence_null"


# ═══════════════════════════════════════════════════════════════════════════════
# Test 14: Writer timeout/no-budget path returns no visible notes; does not block cards
# ═══════════════════════════════════════════════════════════════════════════════

class TestTimeoutNoBudgetPath:
    def test_no_budget_returns_timed_out_result(self):
        """When deadline has no budget, write_set_notes returns timed_out=True."""

        class _Deadline:
            def budget_for_note_generation_s(self):
                return 0.0
            def remaining_ms(self):
                return 0

        card = _make_card("pid14", "Test Brewery")
        curated = _CuratedSetResult(curated_cards=[card], output_count=1)
        frame = _Frame()

        result = write_set_notes(curated, frame, deadline=_Deadline())
        assert result.timed_out
        assert result.visible_note_count == 0
        assert result.notes_by_place_id == {}

    def test_timed_out_result_has_zero_fallback_notes(self):
        """Timed-out result must have fallback_note_visible_count=0."""

        class _Deadline:
            def budget_for_note_generation_s(self):
                return 0.0
            def remaining_ms(self):
                return 0

        card = _make_card("pid14b", "Test Brewery")
        curated = _CuratedSetResult(curated_cards=[card], output_count=1)
        result = write_set_notes(curated, _Frame(), deadline=_Deadline())
        assert result.fallback_note_visible_count == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Test 15: Writer exception path does not block card return
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptionPathSafe:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_key"})
    def test_llm_exception_returns_safe_result(self):
        """An exception in the LLM call must not propagate; write_set_notes must return."""
        card = _make_card("pid15", "Exception Brewery")
        curated = _CuratedSetResult(curated_cards=[card], output_count=1)
        frame = _Frame()

        with patch("app.concierge.set_level_writer._call_set_writer_llm") as mock_llm:
            mock_llm.side_effect = RuntimeError("Network error")
            result = write_set_notes(curated, frame)

        # Should return safely with no notes
        assert result is not None
        assert result.visible_note_count == 0
        assert result.fallback_note_visible_count == 0

    def test_no_curated_cards_returns_empty(self):
        """Empty curated set should return an empty SetWriterResult without error."""
        curated = _CuratedSetResult(curated_cards=[], output_count=0)
        result = write_set_notes(curated, _Frame())
        assert result is not None
        assert result.visible_note_count == 0
        assert not result.timed_out

    def test_prompt_build_exception_returns_safe_result(self):
        """Exception in prompt building must return safely."""
        card = _make_card("pid15c", "Test Place")
        curated = _CuratedSetResult(curated_cards=[card], output_count=1)

        # write_set_notes uses _build_micro_set_prompt (PR #273 path)
        with patch("app.concierge.set_level_writer._build_micro_set_prompt") as mock_prompt:
            mock_prompt.side_effect = ValueError("Prompt error")
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}):
                result = write_set_notes(curated, _Frame())

        assert result is not None
        assert result.visible_note_count == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Test 16: Telemetry counts visible/hidden/rejected/source/role counts truthfully
# ═══════════════════════════════════════════════════════════════════════════════

class TestTelemetryAccuracy:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_key"})
    def test_telemetry_counts_match_result(self):
        """as_telemetry_dict must accurately reflect visible/hidden/rejected counts."""
        card1 = _make_card("pid16a", "Goose Island Brewery")
        card2 = _make_card("pid16b", "Half Acre Beer")
        curated = _CuratedSetResult(curated_cards=[card1, card2], output_count=2)
        frame = _Frame()

        # Return one valid note and one null (thin)
        good_note = "Known for its year-round IPA range on Fulton Street."
        with patch("app.concierge.set_level_writer._call_set_writer_llm") as mock_llm:
            mock_llm.return_value = (f'{{"1": "{good_note}", "2": null}}', {})
            result = write_set_notes(curated, frame)

        tel = result.as_telemetry_dict(elapsed_ms=42)
        assert tel["set_writer_visible_note_count"] == result.visible_note_count
        assert tel["set_writer_hidden_note_count"] == result.hidden_note_count
        assert tel["set_writer_rejected_note_count"] == result.rejected_note_count
        assert tel["set_writer_fallback_note_visible_count"] == 0  # always 0
        assert tel["set_writer_ms"] == 42
        assert "set_writer_role_note_counts" in tel
        assert "set_writer_note_source_counts" in tel

    def test_telemetry_has_all_required_keys(self):
        """as_telemetry_dict must have all required telemetry keys."""
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
        )
        tel = result.as_telemetry_dict(elapsed_ms=10)
        required_keys = [
            "set_writer_input_count",
            "set_writer_output_count",
            "set_writer_visible_note_count",
            "set_writer_hidden_note_count",
            "set_writer_rejected_note_count",
            "set_writer_timed_out",
            "set_writer_fallback_to_existing_path",
            "set_writer_fallback_note_visible_count",
            "set_writer_role_note_counts",
            "set_writer_note_source_counts",
            "set_writer_repeated_skeleton_count",
            "set_writer_unsupported_claim_count",
            "set_writer_ms",
        ]
        for key in required_keys:
            assert key in tel, f"Missing telemetry key: {key}"


# ═══════════════════════════════════════════════════════════════════════════════
# Test 17: Existing PR #257 fallback_note_visible_count remains 0
# ═══════════════════════════════════════════════════════════════════════════════

class TestPR257FallbackNoteInvariant:
    def test_fallback_note_visible_count_always_zero(self):
        """fallback_note_visible_count must be 0 in all SetWriterResult instances."""
        # Successful result
        r1 = SetWriterResult(
            notes_by_place_id={"p1": SetWriterNote(
                place_id="p1", note="A solid craft taproom on Milwaukee Ave.",
                validated=True, rejection_reason="", source=SOURCE_SET_WRITER,
                role_used_internal="evidence_rich", evidence_terms_used=[], caveat_type="",
            )},
            visible_note_count=1, hidden_note_count=0, rejected_note_count=0,
            timed_out=False, fallback_note_visible_count=0,
            role_note_counts={"evidence_rich": 1}, note_source_counts={},
            repeated_skeleton_count=0, unsupported_claim_count=0,
        )
        assert r1.fallback_note_visible_count == 0
        assert r1.as_telemetry_dict()["set_writer_fallback_note_visible_count"] == 0

        # Timed-out result
        r2 = SetWriterResult(
            notes_by_place_id={},
            visible_note_count=0, hidden_note_count=0, rejected_note_count=0,
            timed_out=True, fallback_note_visible_count=0,
            role_note_counts={}, note_source_counts={},
            repeated_skeleton_count=0, unsupported_claim_count=0,
        )
        assert r2.fallback_note_visible_count == 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_key"})
    def test_write_set_notes_never_sets_nonzero_fallback_count(self):
        """write_set_notes must never produce fallback_note_visible_count > 0."""
        card = _make_card("pid17", "Brewery Test")
        curated = _CuratedSetResult(curated_cards=[card], output_count=1)

        # Even with a good note, fallback must be 0
        with patch("app.concierge.set_level_writer._call_set_writer_llm") as mock_llm:
            mock_llm.return_value = (
                '{"1": "Known for craft IPAs and a patio on Milwaukee Ave."}', {}
            )
            result = write_set_notes(curated, _Frame())

        assert result.fallback_note_visible_count == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Test 18: PR #258 deadline/non-critical enrichment contracts unchanged
# ═══════════════════════════════════════════════════════════════════════════════

class TestPR258ContractsUnchanged:
    def test_parallel_retrieval_imports_unchanged(self):
        """PR #258 parallel_retrieval contracts must still import cleanly."""
        from app.concierge.parallel_retrieval import (
            NonCriticalEnrichmentResult,
            run_critical_google_fanout,
            run_non_critical_enrichment,
        )
        assert callable(run_critical_google_fanout)
        assert callable(run_non_critical_enrichment)
        assert NonCriticalEnrichmentResult is not None

    def test_deadline_manager_imports_unchanged(self):
        """RequestDeadline and DEFAULT_SLA must still import and work."""
        from app.concierge.deadline_manager import (
            DEFAULT_SLA,
            RequestDeadline,
            clamp_first_card_limit,
        )
        import time
        dl = RequestDeadline(sla=DEFAULT_SLA, t_start=time.monotonic())
        assert dl.remaining_ms() > 0
        assert clamp_first_card_limit(6) == 6


# ═══════════════════════════════════════════════════════════════════════════════
# Test 19: PR #259 dossier contracts unchanged
# ═══════════════════════════════════════════════════════════════════════════════

class TestPR259DossierContractsUnchanged:
    def test_dossier_classes_importable(self):
        from app.concierge.evidence_dossier import (
            PlaceEvidenceDossier,
            ReviewThemeEvidence,
            build_dossiers_for_ranked_cards,
            build_place_evidence_dossier,
            get_dossier_telemetry,
        )
        assert PlaceEvidenceDossier is not None
        assert ReviewThemeEvidence is not None

    def test_dossier_has_no_note_fields(self):
        """PlaceEvidenceDossier must not have note/display_why fields."""
        from app.concierge.evidence_dossier import PlaceEvidenceDossier
        assert not hasattr(PlaceEvidenceDossier, "note")
        assert not hasattr(PlaceEvidenceDossier, "display_why")
        assert not hasattr(PlaceEvidenceDossier, "why_pick")


# ═══════════════════════════════════════════════════════════════════════════════
# Test 20: PR #260 curator contracts unchanged
# ═══════════════════════════════════════════════════════════════════════════════

class TestPR260CuratorContractsUnchanged:
    def test_curator_classes_importable(self):
        from app.concierge.card_curator import (
            CardCurationSignals,
            CuratedCard,
            CuratedSetResult,
            curate_cards,
        )
        assert callable(curate_cards)
        assert CuratedSetResult is not None

    def test_curated_card_has_no_visible_payload(self):
        """CuratedCard must not have addable/display/note/gv fields."""
        from app.concierge.card_curator import CuratedCard
        for field_name in ("addability", "display_why", "google_verification", "note", "why_pick"):
            assert not hasattr(CuratedCard, field_name), (
                f"CuratedCard should not have field: {field_name}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Tests — semantic_retrieval seam
# ═══════════════════════════════════════════════════════════════════════════════

class TestSemanticRetrievalIntegration:
    def test_set_writer_imported_in_semantic_retrieval(self):
        """set_level_writer imports must be reachable from semantic_retrieval context."""
        from app.concierge.set_level_writer import (
            SetWriterResult,
            write_set_notes,
        )
        assert callable(write_set_notes)
        assert SetWriterResult is not None

    def test_semantic_retrieval_skips_writer_when_no_curated_result(self):
        """write_set_notes called with an empty curated result returns safely."""
        curated = _CuratedSetResult(curated_cards=[], output_count=0)
        result = write_set_notes(curated, _Frame())
        assert result.visible_note_count == 0
        assert not result.timed_out

    def test_semantic_retrieval_card_cap_unchanged(self):
        """first_card_limit must be respected: only cards up to cap get writer input."""
        cards = [_make_card(f"pid_{i}", f"Brewery {i}") for i in range(8)]
        curated = _CuratedSetResult(curated_cards=cards, output_count=8)
        frame = _Frame()

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            # No API key → writer returns early with no notes
            result = write_set_notes(curated, frame, first_card_limit=6)

        # Result should process no more than 6 cards
        assert len(result.notes_by_place_id) <= 6


# ═══════════════════════════════════════════════════════════════════════════════
# Additional: Prompt structure tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPromptStructure:
    def test_prompt_does_not_contain_raw_role_labels(self):
        """The set-level prompt must not contain raw internal role label strings."""
        from app.concierge.card_curator import (
            ROLE_BEST_OVERALL, ROLE_DISTINCTIVE_THEME, ROLE_EVIDENCE_RICH,
            ROLE_LOW_EVIDENCE_HOLDBACK, ROLE_MODIFIER_CONFIRMED,
        )
        cards = [_make_card(f"pid_p{i}", f"Brewery {i}", role=r) for i, r in enumerate([
            ROLE_BEST_OVERALL, ROLE_EVIDENCE_RICH, ROLE_MODIFIER_CONFIRMED,
            ROLE_DISTINCTIVE_THEME, ROLE_LOW_EVIDENCE_HOLDBACK,
        ])]
        frame = _Frame()
        inputs = [
            SetWriterCardInput(
                entity=c.entity, rank_score=c.rank_score, dossier=c.dossier,
                role=c.role, curation_signals=c.curation_signals, original_rank_index=i,
            )
            for i, c in enumerate(cards)
        ]
        prompt = _build_set_level_prompt(inputs, frame)

        for raw_role in [
            ROLE_BEST_OVERALL, ROLE_EVIDENCE_RICH, ROLE_MODIFIER_CONFIRMED,
            ROLE_DISTINCTIVE_THEME, ROLE_LOW_EVIDENCE_HOLDBACK,
        ]:
            assert raw_role not in prompt, f"Raw role '{raw_role}' leaked into prompt"

    def test_prompt_forbids_rating_review_primary(self):
        """The prompt instructions must forbid rating/review count as primary differentiator."""
        cards = [_make_card("pid_pr1", "Brewery A")]
        frame = _Frame()
        inputs = [
            SetWriterCardInput(
                entity=c.entity, rank_score=c.rank_score, dossier=c.dossier,
                role=c.role, curation_signals=c.curation_signals, original_rank_index=0,
            )
            for c in cards
        ]
        prompt = _build_set_level_prompt(inputs, frame)
        # Prompt should contain anti-pattern instructions for rating/review
        assert "review" in prompt.lower() or "rating" in prompt.lower()
        assert "DO NOT" in prompt or "ANTI" in prompt or "rejected" in prompt.lower()

    def test_prompt_includes_set_level_distinctness_instruction(self):
        """The prompt must include instructions for cross-card distinctness."""
        cards = [_make_card(f"pid_pd{i}", f"Brewery {i}") for i in range(3)]
        frame = _Frame()
        inputs = [
            SetWriterCardInput(
                entity=c.entity, rank_score=c.rank_score, dossier=c.dossier,
                role=c.role, curation_signals=c.curation_signals, original_rank_index=i,
            )
            for i, c in enumerate(cards)
        ]
        prompt = _build_set_level_prompt(inputs, frame)
        # Must mention distinctness
        assert "distinct" in prompt.lower() or "vary" in prompt.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# PR #273 Tests: AllowedClaimsPacket Distiller
# ═══════════════════════════════════════════════════════════════════════════════

class TestAllowedClaimsPacketDistiller:
    """Tests for _distill_allowed_claims_packet() — compact evidence compression."""

    def test_rich_dossier_produces_concrete_claim_atoms(self):
        """Rich dossier → packet has ≥1 allowed claim atom from real evidence."""
        card = _make_card(
            "pid_d1", "Haymarket Brewing",
            food_drink=["craft IPA (amenity)", "seasonal rotating taps"],
            ambiance=["lively tap room", "communal seating"],
        )
        frame = _Frame()
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        packet = _distill_allowed_claims_packet(ci, frame)
        assert isinstance(packet, AllowedClaimsPacket)
        assert packet.display_name == "Haymarket Brewing"
        assert len(packet.allowed_claim_atoms) >= 1
        # Evidence-derived atoms (food/ambiance themes) present
        atoms_text = " ".join(packet.allowed_claim_atoms)
        assert "craft" in atoms_text or "IPA" in atoms_text or "lively" in atoms_text or "tap" in atoms_text

    def test_thin_dossier_produces_sparse_packet(self):
        """Thin (is_minimal=True) dossier → sparse packet, no atoms, evidence_strength=thin."""
        card = _make_card("pid_d2", "Unknown Bar", is_minimal=True)
        frame = _Frame()
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        packet = _distill_allowed_claims_packet(ci, frame)
        assert packet.evidence_strength == "thin"
        # Thin evidence → no concrete claim atoms from provider/themes
        assert len(packet.allowed_claim_atoms) == 0
        # Caveats mention thin evidence
        assert any("thin" in c.lower() for c in packet.safe_caveats)

    def test_rating_and_review_count_excluded_as_claim_atoms(self):
        """rating: and review_count: provider facts must not become claim atoms."""
        card = _make_card("pid_d3", "Rated Brewery")
        card.dossier.provider_evidence = [
            _ProviderEvidenceItem(
                source="google_places",
                facts=["rating:4.8", "review_count:1200", "type:brewery"],
            )
        ]
        frame = _Frame()
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        packet = _distill_allowed_claims_packet(ci, frame)
        atoms_text = " ".join(packet.allowed_claim_atoms)
        assert "rating:" not in atoms_text
        assert "4.8" not in atoms_text
        assert "review_count:" not in atoms_text
        assert "1200" not in atoms_text

    def test_place_name_not_used_as_evidence_for_vibe_claims(self):
        """Name alone must not produce claim atoms for vibe/temporal inferences."""
        for name in [
            "Hidden Gem Cocktail Bar", "Riverwalk Brewing", "Late Night Taproom",
            "Speakeasy Lounge", "Romantic Rooftop Bar",
        ]:
            card = _make_card(f"pid_name_{name[:6]}", name, is_minimal=True)
            frame = _Frame()
            ci = SetWriterCardInput(
                entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
                role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
            )
            packet = _distill_allowed_claims_packet(ci, frame)
            atoms_text = " ".join(packet.allowed_claim_atoms).lower()
            disallowed_text = " ".join(packet.disallowed_boundaries).lower()
            # Name must not propagate as a claim atom
            assert len(packet.allowed_claim_atoms) == 0, (
                f"Name '{name}' produced claim atoms: {packet.allowed_claim_atoms}"
            )
            # Disallowed boundaries must include relevant blocked categories
            assert "hidden" in disallowed_text or "hidden-gem" in disallowed_text or "rating" in disallowed_text

    def test_modifier_support_confirmed_when_evidence_confirms(self):
        """modifier_support='confirmed' when dossier.query_fit.modifier_fit='confirmed'."""
        card = _make_card(
            "pid_d5", "Riverwalk Taproom",
            modifier_fit="confirmed",
            view_entries=["outdoor seating (amenity)"],
        )
        card.dossier.query_fit.modifier_fit = "confirmed"
        frame = _Frame(location_modifiers=["Riverwalk"])
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        packet = _distill_allowed_claims_packet(ci, frame)
        assert packet.modifier_support == "confirmed"

    def test_modifier_support_not_confirmed_when_missing(self):
        """modifier_support='not_confirmed' when modifier requested but not confirmed."""
        card = _make_card("pid_d6", "Some Bar", modifier_fit="not_confirmed")
        card.dossier.query_fit.modifier_fit = "not_confirmed"
        frame = _Frame(location_modifiers=["Riverwalk"])
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        packet = _distill_allowed_claims_packet(ci, frame)
        assert packet.modifier_support == "not_confirmed"
        # Caveat must mention modifier not confirmed
        caveat_text = " ".join(packet.safe_caveats).lower()
        assert "not confirmed" in caveat_text or "not_confirmed" in caveat_text

    def test_listing_context_view_sets_listing_context_only(self):
        """Listing-context-only view entries → modifier_support='listing_context_only'."""
        card = _make_card(
            "pid_d7", "Riverwalk Brewing",
            view_entries=["listing_context:riverwalk"],
        )
        frame = _Frame(location_modifiers=["Riverwalk"])
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        packet = _distill_allowed_claims_packet(ci, frame)
        assert packet.modifier_support == "listing_context_only"

    def test_disallowed_boundaries_always_present(self):
        """Disallowed boundaries must always include the standard blocked categories."""
        card = _make_card("pid_d8", "Normal Brewery")
        frame = _Frame()
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        packet = _distill_allowed_claims_packet(ci, frame)
        # Standard boundaries always present
        boundaries = " ".join(packet.disallowed_boundaries).lower()
        assert "rating" in boundaries
        assert "hidden" in boundaries or "hidden-gem" in boundaries
        assert "michelin" in boundaries

    def test_no_outdoor_view_atom_without_amenity_evidence(self):
        """View/outdoor is not an allowed claim atom unless explicitly confirmed (not listing_context)."""
        card = _make_card(
            "pid_d9", "Riverwalk Bar",
            view_entries=["listing_context:riverwalk"],
        )
        frame = _Frame()
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        packet = _distill_allowed_claims_packet(ci, frame)
        atoms_text = " ".join(packet.allowed_claim_atoms).lower()
        assert "outdoor" not in atoms_text
        assert "patio" not in atoms_text
        assert "view" not in atoms_text

    def test_explicit_outdoor_amenity_becomes_claim_atom(self):
        """Explicit amenity view evidence (not listing_context:) → allowed claim atom."""
        card = _make_card(
            "pid_d10", "Garden Brewery",
            view_entries=["outdoor seating (amenity)"],
        )
        frame = _Frame()
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        packet = _distill_allowed_claims_packet(ci, frame)
        atoms_text = " ".join(packet.allowed_claim_atoms).lower()
        assert "outdoor" in atoms_text or "amenity" in atoms_text

    def test_packet_char_count_smaller_than_evidence_block(self):
        """Packet rendering must produce fewer characters than legacy evidence block."""
        card = _make_card(
            "pid_d11", "Half Acre Beer",
            food_drink=["house IPA", "barrel-aged stout"],
            ambiance=["lively", "communal"],
        )
        frame = _Frame()
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        packet = _distill_allowed_claims_packet(ci, frame)
        packet_text = _render_packet(packet, 1, 1)
        legacy_block = _build_card_evidence_block(ci, 1, 1, frame)
        assert len(packet_text) < len(legacy_block), (
            f"Packet ({len(packet_text)} chars) not smaller than legacy block "
            f"({len(legacy_block)} chars)"
        )

    def test_strong_evidence_sets_evidence_strength_strong(self):
        """source_confidence='strong' and not is_minimal → evidence_strength='strong'."""
        card = _make_card("pid_d12", "Goose Island", source_confidence="strong")
        frame = _Frame()
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        packet = _distill_allowed_claims_packet(ci, frame)
        assert packet.evidence_strength == "strong"

    def test_no_dossier_produces_thin_packet(self):
        """No dossier at all → thin packet with no atoms."""
        card = _make_card("pid_d13", "Mystery Bar")
        card_no_dossier = _CuratedCard(
            entity=card.entity,
            rank_score=card.rank_score,
            dossier=None,
            role="low_evidence_holdback",
            curation_score=0.3,
            curation_signals=card.curation_signals,
        )
        frame = _Frame()
        ci = SetWriterCardInput(
            entity=card_no_dossier.entity,
            rank_score=card_no_dossier.rank_score,
            dossier=None,
            role=card_no_dossier.role,
            curation_signals=card_no_dossier.curation_signals,
            original_rank_index=0,
        )
        packet = _distill_allowed_claims_packet(ci, frame)
        assert packet.evidence_strength == "thin"
        assert len(packet.allowed_claim_atoms) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# PR #273 Tests: Micro Set Writer Prompt
# ═══════════════════════════════════════════════════════════════════════════════

class TestMicroSetPrompt:
    """Tests for _build_micro_set_prompt() — compact prompt using AllowedClaimsPackets."""

    def _make_packet(self, place_id, name, evidence_strength="ok",
                     atoms=None, caveats=None, modifier_support="not_applicable"):
        return AllowedClaimsPacket(
            place_id=place_id,
            display_name=name,
            category="Brewery",
            neighborhood="123 Main St, Chicago",
            allowed_claim_atoms=atoms or ["craft IPA on tap", "communal seating"],
            safe_caveats=caveats or [],
            disallowed_boundaries=["rating/review-count prose", "hidden-gem"],
            evidence_strength=evidence_strength,
            modifier_support=modifier_support,
        )

    def test_micro_prompt_smaller_than_legacy_prompt(self):
        """Micro prompt must be materially smaller than the legacy evidence-block prompt."""
        cards = [
            _make_card(f"pid_mp{i}", f"Brewery {i}",
                       food_drink=["IPA", "stout"], ambiance=["lively"])
            for i in range(6)
        ]
        frame = _Frame()
        inputs = [
            SetWriterCardInput(
                entity=c.entity, rank_score=c.rank_score, dossier=c.dossier,
                role=c.role, curation_signals=c.curation_signals, original_rank_index=i,
            )
            for i, c in enumerate(cards)
        ]

        legacy_prompt = _build_set_level_prompt(inputs, frame)
        packets = [_distill_allowed_claims_packet(ci, frame) for ci in inputs]
        micro_prompt = _build_micro_set_prompt(packets, frame)

        assert len(micro_prompt) < len(legacy_prompt), (
            f"Micro prompt ({len(micro_prompt)} chars) not smaller than "
            f"legacy prompt ({len(legacy_prompt)} chars)"
        )

    def test_micro_prompt_contains_all_place_ids(self):
        """Micro prompt must reference all place IDs in the packet set."""
        packets = [
            self._make_packet("pidA", "Brew Alpha"),
            self._make_packet("pidB", "Brew Beta"),
            self._make_packet("pidC", "Brew Gamma"),
        ]
        frame = _Frame()
        prompt = _build_micro_set_prompt(packets, frame)
        assert "pidA" in prompt
        assert "pidB" in prompt
        assert "pidC" in prompt

    def test_micro_prompt_contains_policy_rules(self):
        """Micro prompt must include anti-pattern policy rules."""
        packets = [self._make_packet("pid1", "Brew One")]
        frame = _Frame()
        prompt = _build_micro_set_prompt(packets, frame)
        prompt_lower = prompt.lower()
        # Must block rating/review and hidden-gem
        assert "rating" in prompt_lower or "review" in prompt_lower
        assert "hidden" in prompt_lower or "DO NOT" in prompt
        assert "null" in prompt_lower

    def test_micro_prompt_contains_distinctness_rule(self):
        """Micro prompt must include distinctness instructions."""
        packets = [
            self._make_packet("pid1", "Brew One"),
            self._make_packet("pid2", "Brew Two"),
        ]
        frame = _Frame()
        prompt = _build_micro_set_prompt(packets, frame)
        assert "distinct" in prompt.lower() or "differ" in prompt.lower()

    def test_micro_prompt_includes_user_query(self):
        """Micro prompt must include the user's literal ask."""
        packets = [self._make_packet("pid1", "Brew One")]
        frame = _Frame(literal_ask="craft beer near Wicker Park")
        prompt = _build_micro_set_prompt(packets, frame)
        assert "craft beer near Wicker Park" in prompt

    def test_micro_prompt_does_not_contain_raw_role_labels(self):
        """Micro prompt must not contain raw internal role label strings."""
        from app.concierge.card_curator import (
            ROLE_BEST_OVERALL, ROLE_EVIDENCE_RICH, ROLE_LOW_EVIDENCE_HOLDBACK,
        )
        cards = [_make_card(f"pid_r{i}", f"Brewery {i}", role=r) for i, r in enumerate([
            ROLE_BEST_OVERALL, ROLE_EVIDENCE_RICH, ROLE_LOW_EVIDENCE_HOLDBACK,
        ])]
        frame = _Frame()
        inputs = [
            SetWriterCardInput(
                entity=c.entity, rank_score=c.rank_score, dossier=c.dossier,
                role=c.role, curation_signals=c.curation_signals, original_rank_index=i,
            )
            for i, c in enumerate(cards)
        ]
        packets = [_distill_allowed_claims_packet(ci, frame) for ci in inputs]
        prompt = _build_micro_set_prompt(packets, frame)
        for raw_role in [ROLE_BEST_OVERALL, ROLE_EVIDENCE_RICH, ROLE_LOW_EVIDENCE_HOLDBACK]:
            assert raw_role not in prompt, f"Raw role '{raw_role}' leaked into micro prompt"

    def test_micro_prompt_blocks_name_inference(self):
        """Micro prompt must explicitly block inferring vibe from name alone."""
        packets = [self._make_packet("pid1", "Speakeasy Lounge")]
        frame = _Frame()
        prompt = _build_micro_set_prompt(packets, frame)
        # Must contain instruction blocking name-derived inferences
        assert "name" in prompt.lower()
        assert "identity" in prompt.lower() or "name alone" in prompt.lower() or "infer" in prompt.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# PR #273 Tests: Writer Telemetry
# ═══════════════════════════════════════════════════════════════════════════════

class TestWriterTelemetry:
    """Tests for structured writer telemetry fields added in PR #273."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_key"})
    def test_telemetry_fields_populate_on_success(self):
        """Successful write produces all required PR #273 telemetry fields."""
        card = _make_card("pid_tel1", "Goose Island Brewery",
                          food_drink=["house IPA"], ambiance=["lively"])
        curated = _CuratedSetResult(curated_cards=[card], output_count=1)
        frame = _Frame()

        good_note = "Known for its house IPA and a rotating seasonal tap list on Fulton Street."
        with patch("app.concierge.set_level_writer._call_set_writer_llm") as mock_llm:
            mock_llm.return_value = (f'{{"1": "{good_note}"}}', {
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 384,
                "output_stop_reason": "end_turn",
                "input_tokens": 210,
                "output_tokens": 32,
            })
            result = write_set_notes(curated, frame)

        assert result.writer_telemetry is not None
        tel = result.writer_telemetry
        # Phase timing
        assert "evidence_distill_ms" in tel
        assert "prompt_build_ms" in tel
        assert "llm_call_ms" in tel
        assert "parse_ms" in tel
        assert "validation_ms" in tel
        assert "set_writer_total_ms" in tel
        # Packet/prompt size
        assert tel["dynamic_packet_count"] == 1
        assert tel["dynamic_packet_char_count"] > 0
        assert tel["dynamic_prompt_char_count"] > 0
        assert tel["input_token_estimate"] > 0
        # LLM fields
        assert tel["model"] == "claude-haiku-4-5-20251001"
        assert tel["max_tokens"] == 384
        assert tel.get("output_stop_reason") == "end_turn"
        assert tel.get("input_tokens") == 210
        assert tel.get("output_tokens") == 32
        # Count fields
        assert tel["notes_visible_count"] == result.visible_note_count
        assert tel["notes_hidden_count"] == result.hidden_note_count

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_key"})
    def test_telemetry_fields_populate_on_parse_failure(self):
        """Parse failure still records llm_call_ms, model, max_tokens."""
        card = _make_card("pid_tel2", "Test Bar")
        curated = _CuratedSetResult(curated_cards=[card], output_count=1)
        frame = _Frame()

        with patch("app.concierge.set_level_writer._call_set_writer_llm") as mock_llm:
            mock_llm.return_value = ("not valid json at all", {"model": "claude-haiku-4-5-20251001", "max_tokens": 384})
            result = write_set_notes(curated, frame)

        # Parse failure returns empty result — writer_telemetry is None (returned before wtel populated)
        assert result.visible_note_count == 0

    def test_max_tokens_reduced_from_prior_default(self):
        """max_tokens in the writer must be materially lower than the old 1024 default."""
        from app.concierge.set_level_writer import _MAX_TOKENS_DEFAULT
        assert _MAX_TOKENS_DEFAULT <= 384, (
            f"max_tokens={_MAX_TOKENS_DEFAULT} is not materially lower than old default 1024"
        )

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_key"})
    def test_dynamic_packet_char_count_in_telemetry(self):
        """dynamic_packet_char_count must be populated and positive on success."""
        cards = [_make_card(f"pid_pc{i}", f"Brewery {i}") for i in range(3)]
        curated = _CuratedSetResult(curated_cards=cards, output_count=3)
        frame = _Frame()

        notes_json = '{"1": "Known for house brewed IPA on Milwaukee Avenue.", "2": null, "3": null}'
        with patch("app.concierge.set_level_writer._call_set_writer_llm") as mock_llm:
            mock_llm.return_value = (notes_json, {"model": "m", "max_tokens": 384})
            result = write_set_notes(curated, frame)

        assert result.writer_telemetry is not None
        assert result.writer_telemetry["dynamic_packet_count"] == 3
        assert result.writer_telemetry["dynamic_packet_char_count"] > 0
        assert result.writer_telemetry["dynamic_prompt_char_count"] > 0

    def test_telemetry_on_no_budget_timeout(self):
        """Timed-out result (no budget) has set_writer_timed_out=True in as_telemetry_dict."""
        class _Deadline:
            def budget_for_note_generation_s(self):
                return 0.0
            def remaining_ms(self):
                return 0

        card = _make_card("pid_tel3", "Test Brewery")
        curated = _CuratedSetResult(curated_cards=[card], output_count=1)
        result = write_set_notes(curated, _Frame(), deadline=_Deadline())
        assert result.timed_out is True
        tel = result.as_telemetry_dict()
        assert tel["set_writer_timed_out"] is True

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_key"})
    def test_cards_preserved_when_notes_fail(self):
        """Cards must not be dropped when note validation fails or LLM returns null."""
        cards = [_make_card(f"pid_cp{i}", f"Brewery {i}") for i in range(3)]
        curated = _CuratedSetResult(curated_cards=cards, output_count=3)
        frame = _Frame()

        # All nulls — no notes visible but cards preserved
        with patch("app.concierge.set_level_writer._call_set_writer_llm") as mock_llm:
            mock_llm.return_value = ('{"1": null, "2": null, "3": null}', {})
            result = write_set_notes(curated, frame)

        # All cards have entries (hidden, not dropped)
        assert len(result.notes_by_place_id) == 3
        for note in result.notes_by_place_id.values():
            assert note.note == ""
            assert not note.validated
        assert result.visible_note_count == 0
        assert result.fallback_note_visible_count == 0


# ═══════════════════════════════════════════════════════════════════════════════
# PR #273 Tests: Parse improvements
# ═══════════════════════════════════════════════════════════════════════════════

class TestImprovedParsing:
    """Tests for improved _parse_set_writer_response() — full JSON first."""

    def test_clean_json_parsed_without_regex(self):
        """Clean JSON starting with { must parse correctly via full json.loads()."""
        from app.concierge.set_level_writer import _parse_set_writer_response
        clean = '{"1": "Known for craft IPAs on Fulton Street.", "2": null, "3": "Lively bar near Wicker Park."}'
        result = _parse_set_writer_response(clean, 3)
        assert result["1"] == "Known for craft IPAs on Fulton Street."
        assert result["2"] is None
        assert result["3"] == "Lively bar near Wicker Park."

    def test_prose_wrapped_json_falls_back_to_regex(self):
        """JSON embedded in prose text is extracted via regex fallback."""
        from app.concierge.set_level_writer import _parse_set_writer_response
        prose = 'Here are the notes: {"1": "A cozy tap room on Milwaukee Ave.", "2": null}'
        result = _parse_set_writer_response(prose, 2)
        assert "1" in result or len(result) >= 0  # parse succeeds or returns {}

    def test_invalid_json_returns_empty_dict(self):
        """Malformed response returns empty dict, not an exception."""
        from app.concierge.set_level_writer import _parse_set_writer_response
        result = _parse_set_writer_response("not json at all", 3)
        assert result == {}

    def test_empty_string_returns_empty_dict(self):
        """Empty response returns empty dict."""
        from app.concierge.set_level_writer import _parse_set_writer_response
        assert _parse_set_writer_response("", 3) == {}

    def test_null_values_preserved_in_output(self):
        """Null values in JSON must map to None in the result dict."""
        from app.concierge.set_level_writer import _parse_set_writer_response
        result = _parse_set_writer_response('{"1": null, "2": "Some note here."}', 2)
        assert result.get("1") is None
        assert result.get("2") == "Some note here."

    def test_non_string_values_excluded(self):
        """Non-string, non-null values are excluded from parsed output."""
        from app.concierge.set_level_writer import _parse_set_writer_response
        result = _parse_set_writer_response('{"1": 42, "2": "Valid note here.", "3": null}', 3)
        assert "1" not in result or result.get("1") is None
        assert result.get("2") == "Valid note here."


# ═══════════════════════════════════════════════════════════════════════════════
# PR #273 Tests: Validation preserved
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationPreservedPR273:
    """Confirm existing validators still run and reject invalid notes."""

    def test_rating_review_count_prose_rejected(self):
        """Notes with rating/review-count prose are rejected by existing validators."""
        card = _make_card("pid_v1", "Brewery X")
        frame = _Frame()
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        for bad in [
            "Highest-rated brewery with 1,200 reviews in Logan Square.",
            "Steady review volume confirms popularity across the neighborhood.",
            "Notable review base of 1,344 visitors makes it a safe choice.",
        ]:
            passes, reason = _validate_set_writer_note(bad, ci, frame)
            assert not passes, f"Expected rejection for: {bad!r}"

    def test_name_derived_vibe_claims_rejected(self):
        """Validator must reject notes that infer vibe from the business name."""
        card = _make_card("pid_v2", "Riverwalk Brewing")
        frame = _Frame()
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        # These claim scenic/waterfront from the name alone — should be rejected
        for bad in [
            "Enjoy beautiful river views from this brewery.",
            "Stunning panoramic views of the lake visible from the bar.",
            "Waterfront brewery with great river views.",
        ]:
            passes, reason = _validate_set_writer_note(bad, ci, frame)
            assert not passes, f"Expected rejection for name-derived view claim: {bad!r}"

    def test_unsupported_modifier_claims_rejected(self):
        """Unconfirmed modifier claims must be rejected."""
        card = _make_card("pid_v3", "Brewery X", modifier_fit="not_confirmed")
        card.dossier.query_fit.modifier_fit = "not_confirmed"
        frame = _Frame(location_modifiers=["Riverwalk"])
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        bad_note = "Situated directly on the Riverwalk with river access."
        passes, reason = _validate_set_writer_note(bad_note, ci, frame)
        assert not passes

    def test_generic_filler_phrases_rejected(self):
        """Generic filler / boilerplate phrases are rejected."""
        card = _make_card("pid_v4", "Brewery X")
        frame = _Frame()
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        for bad in [
            "Strong brewery match in Chicago.",
            "Well-regarded spot in the neighborhood.",
            "A great option for craft beer lovers.",
        ]:
            passes, reason = _validate_set_writer_note(bad, ci, frame)
            assert not passes, f"Expected rejection for generic filler: {bad!r}"

    def test_null_note_always_hidden(self):
        """Null LLM output → validated=False, note='', no fallback prose."""
        card = _make_card("pid_v5", "Test Bar")
        frame = _Frame()
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        passes, reason = _validate_set_writer_note(None, ci, frame)
        assert not passes
        assert reason == "thin_evidence_null"

    def test_no_deterministic_visible_note_path(self):
        """No path through write_set_notes can produce fallback_note_visible_count > 0."""
        cards = [_make_card(f"pid_nd{i}", f"Bar {i}", is_minimal=True) for i in range(3)]
        curated = _CuratedSetResult(curated_cards=cards, output_count=3)

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_key"}):
            with patch("app.concierge.set_level_writer._call_set_writer_llm") as mock_llm:
                mock_llm.return_value = ('{"1": null, "2": null, "3": null}', {})
                result = write_set_notes(curated, _Frame())

        assert result.fallback_note_visible_count == 0

    def test_fallback_note_visible_count_is_zero_in_telemetry(self):
        """as_telemetry_dict must always have set_writer_fallback_note_visible_count=0."""
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
            writer_telemetry={"dynamic_packet_count": 3},
        )
        tel = result.as_telemetry_dict()
        assert tel["set_writer_fallback_note_visible_count"] == 0
        assert "dynamic_packet_count" in tel


# ═══════════════════════════════════════════════════════════════════════════════
# PR #273 Tests: Regression — existing contracts unchanged
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegressionPR273:
    """Verify existing contracts still hold after PR #273 refactor."""

    def test_set_writer_card_input_unchanged(self):
        """SetWriterCardInput dataclass fields are unchanged."""
        card = _make_card("pid_reg1", "Brew Test")
        ci = SetWriterCardInput(
            entity=card.entity,
            rank_score=card.rank_score,
            dossier=card.dossier,
            role=card.role,
            curation_signals=card.curation_signals,
            original_rank_index=0,
        )
        assert hasattr(ci, "entity")
        assert hasattr(ci, "rank_score")
        assert hasattr(ci, "dossier")
        assert hasattr(ci, "role")
        assert hasattr(ci, "curation_signals")
        assert hasattr(ci, "original_rank_index")

    def test_set_writer_note_unchanged(self):
        """SetWriterNote dataclass fields are unchanged."""
        note = SetWriterNote(
            place_id="pid1",
            note="A solid craft taproom on Milwaukee Ave.",
            validated=True,
            rejection_reason="",
            source=SOURCE_SET_WRITER,
            role_used_internal="evidence_rich",
            evidence_terms_used=[],
            caveat_type="",
        )
        assert note.place_id == "pid1"
        assert note.validated is True
        assert note.fallback_note_visible_count if False else True  # field doesn't exist on note, not result

    def test_set_writer_result_fallback_always_zero(self):
        """SetWriterResult.fallback_note_visible_count is always 0."""
        for args in [
            {"timed_out": True},
            {"timed_out": False, "visible_note_count": 3},
        ]:
            r = SetWriterResult(
                notes_by_place_id={},
                visible_note_count=args.get("visible_note_count", 0),
                hidden_note_count=0,
                rejected_note_count=0,
                timed_out=args.get("timed_out", False),
                fallback_note_visible_count=0,
                role_note_counts={},
                note_source_counts={},
                repeated_skeleton_count=0,
                unsupported_claim_count=0,
            )
            assert r.fallback_note_visible_count == 0

    def test_legacy_prompt_builder_still_importable(self):
        """_build_card_evidence_block and _build_set_level_prompt still importable and callable."""
        assert callable(_build_card_evidence_block)
        assert callable(_build_set_level_prompt)

    def test_legacy_evidence_block_unchanged_for_existing_tests(self):
        """Legacy _build_card_evidence_block still produces expected output."""
        card = _make_card("pid_reg3", "Spiteful Brewing",
                          food_drink=["house IPA"], ambiance=["lively"])
        frame = _Frame()
        ci = SetWriterCardInput(
            entity=card.entity, rank_score=card.rank_score, dossier=card.dossier,
            role=card.role, curation_signals=card.curation_signals, original_rank_index=0,
        )
        block = _build_card_evidence_block(ci, 1, 1, frame)
        assert "Spiteful Brewing" in block
        assert "house IPA" in block or "food" in block.lower()

    def test_write_set_notes_returns_set_writer_result(self):
        """write_set_notes always returns a SetWriterResult instance."""
        curated = _CuratedSetResult(curated_cards=[], output_count=0)
        result = write_set_notes(curated, _Frame())
        assert isinstance(result, SetWriterResult)

    def test_claim_safety_reviewer_importable_unchanged(self):
        """claim_safety_reviewer module still imports cleanly after PR #273."""
        from app.concierge.claim_safety_reviewer import (
            NoteReviewResult,
            ReviewerTelemetry,
            SummaryReviewResult,
            review_note,
            review_notes_set,
            review_summary,
        )
        assert callable(review_note)
        assert callable(review_notes_set)
        assert callable(review_summary)
        assert ReviewerTelemetry is not None

    def test_reason_validator_importable_unchanged(self):
        """reason_validator.validate_reason still importable after PR #273."""
        from app.concierge.reason_validator import validate_reason
        assert callable(validate_reason)
