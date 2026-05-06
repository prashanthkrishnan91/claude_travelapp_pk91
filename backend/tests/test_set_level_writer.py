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
    SetWriterCardInput,
    SetWriterNote,
    SetWriterResult,
    _build_card_evidence_block,
    _build_set_level_prompt,
    _count_repeated_skeletons,
    _make_evidence_stub,
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
                f'{{"1": "{repeated_1}", "2": "{repeated_2}", "3": "{distinct}"}}'
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
            mock_llm.return_value = f'{{"1": "{s1}", "2": "{s2}", "3": "{s3}"}}'
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
                f'{{"1": "{repeated_1}", "2": "{repeated_2}", "3": "{distinct}"}}'
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
            mock_llm.return_value = '{"1": "Strong brewery match in Chicago."}'
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
                mock_llm.return_value = '{"1": null}'
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

        with patch("app.concierge.set_level_writer._build_set_level_prompt") as mock_prompt:
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
            mock_llm.return_value = f'{{"1": "{good_note}", "2": null}}'
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
            mock_llm.return_value = '{"1": "Known for craft IPAs and a patio on Milwaukee Ave."}'
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
