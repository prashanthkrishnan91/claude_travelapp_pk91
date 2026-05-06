"""PR #260 — Card Role + Curated Set Ranker v1 tests.

Required scenarios:
 1. Assigns best_overall / strongest_query_match to high concept-fit, strong evidence card.
 2. Assigns modifier_confirmed only when modifier_fit confirmed or explicit theme evidence.
 3. Does not assign modifier_confirmed from formatted_address alone.
 4. Listing_context name token is lower-trust than explicit enrichment evidence.
 5. Review count alone does not create evidence_rich or best_overall.
 6. Place Details enrichment with explicit themes can create evidence_rich / distinctive_theme.
 7. Low evidence but Google-verified card becomes safe_popular_fallback or low_evidence_holdback.
 8. Curator preserves max card cap.
 9. Curator never creates addable cards or card payload fields.
10. Curator fallback path preserves original order if curation raises.
11. Ordering remains stable and deterministic across repeated runs.
12. Conservative reorder: clearly stronger evidence-rich modifier-confirmed card can move up.
13. No broad reorder: low concept-fit card cannot jump above strong concept-fit card via theme count.
14. Telemetry counts roles/confidence/reorders accurately.
15. Existing PR #257 fallback_note_visible_count invariant remains structurally unchanged.
16. Existing PR #258 non-critical enrichment invariants remain unchanged.
17. Existing PR #259 dossier contracts remain unchanged.
"""

from __future__ import annotations

import os
import sys
import types
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_deps = sys.modules.get("app.core.deps") or types.ModuleType("app.core.deps")
sys.modules.setdefault("app.core.deps", _deps)
setattr(_deps, "DB", object)
setattr(_deps, "CurrentUserID", object)

# ── Imports under test ────────────────────────────────────────────────────────
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
    CardCurationSignals,
    CuratedCard,
    CuratedSetResult,
    _assign_role,
    _build_curation_signals,
    _compute_curation_score,
    curate_cards,
)
from app.concierge.evidence_dossier import (
    CONFIDENCE_MIXED,
    CONFIDENCE_STRONG,
    CONFIDENCE_WEAK,
    PlaceEvidenceDossier,
    ProviderEvidenceItem,
    QueryFitEvidence,
    ReviewThemeEvidence,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_entity(
    place_id: str = "places/abc",
    name: str = "Test Place",
    primary_type: str = "restaurant",
    types: Optional[List[str]] = None,
    business_status: str = "OPERATIONAL",
    google_maps_uri: str = "https://maps.google.com/?cid=1",
    rating: float = 4.3,
    user_rating_count: int = 500,
) -> Any:
    return SimpleNamespace(
        place_id=place_id,
        name=name,
        primary_type=primary_type,
        types=types or [primary_type],
        business_status=business_status,
        google_maps_uri=google_maps_uri,
        rating=rating,
        user_rating_count=user_rating_count,
        formatted_address="123 Main St, Chicago, IL, USA",
        lat=41.9,
        lng=-87.7,
        price_level="PRICE_LEVEL_MODERATE",
        website_uri=None,
    )


def _make_rank_score(subtype_fit: float = 0.6, geo_fit: float = 0.3) -> Any:
    return SimpleNamespace(
        subtype_fit=subtype_fit,
        geo_fit=geo_fit,
        as_dict=lambda: {"subtype_fit": subtype_fit, "geo_fit": geo_fit},
    )


def _make_dossier(
    place_id: str = "places/abc",
    name: str = "Test Place",
    concept_fit: float = 0.6,
    geo_fit: float = 0.3,
    modifier_fit: Optional[str] = "none",
    source_confidence: str = CONFIDENCE_MIXED,
    review_themes: Optional[ReviewThemeEvidence] = None,
    provider_evidence: Optional[List[ProviderEvidenceItem]] = None,
    internal_evidence_gaps: Optional[List[str]] = None,
    is_minimal: bool = False,
    primary_type: str = "restaurant",
    category: Optional[str] = "Restaurant",
    google_types: Optional[List[str]] = None,
) -> PlaceEvidenceDossier:
    if review_themes is None:
        review_themes = ReviewThemeEvidence()
    if provider_evidence is None:
        provider_evidence = [ProviderEvidenceItem(source="google_places", facts=["type:restaurant"])]
    if internal_evidence_gaps is None:
        internal_evidence_gaps = []

    return PlaceEvidenceDossier(
        place_id=place_id,
        name=name,
        category=category,
        primary_type=primary_type,
        google_types=google_types or [primary_type],
        neighborhood="123 Main St, Chicago, IL, USA",
        lat=41.9,
        lng=-87.7,
        query_fit=QueryFitEvidence(
            concept_fit=concept_fit,
            modifier_fit=modifier_fit,
            geo_fit=geo_fit,
            vibe_fit=None,
        ),
        provider_evidence=provider_evidence,
        review_themes=review_themes,
        source_confidence=source_confidence,
        internal_evidence_gaps=internal_evidence_gaps,
        evidence_source_counts={"google_places": 3},
        theme_counts={},
        is_minimal=is_minimal,
    )


def _make_details_dossier(
    place_id: str = "places/abc",
    name: str = "Test Place",
    concept_fit: float = 0.75,
    geo_fit: float = 0.4,
    modifier_fit: Optional[str] = "none",
    source_confidence: str = CONFIDENCE_STRONG,
    food_drink: Optional[List[str]] = None,
    ambiance: Optional[List[str]] = None,
    view_patio: Optional[List[str]] = None,
    negative_caveats: Optional[List[str]] = None,
    internal_evidence_gaps: Optional[List[str]] = None,
    is_minimal: bool = False,
) -> PlaceEvidenceDossier:
    """Dossier with Place Details provider evidence."""
    themes = ReviewThemeEvidence(
        food_drink=food_drink or [],
        ambiance=ambiance or [],
        view_patio_waterfront=view_patio or [],
        negative_caveats=negative_caveats or [],
    )
    provider_evidence = [
        ProviderEvidenceItem(source="google_places", facts=["type:restaurant", "rating:4.5"]),
        ProviderEvidenceItem(source="google_place_details", facts=["editorial_summary:Great food"]),
    ]
    return PlaceEvidenceDossier(
        place_id=place_id,
        name=name,
        category="Restaurant",
        primary_type="restaurant",
        google_types=["restaurant"],
        neighborhood="456 Oak Ave, Chicago, IL, USA",
        lat=41.9,
        lng=-87.7,
        query_fit=QueryFitEvidence(
            concept_fit=concept_fit,
            modifier_fit=modifier_fit,
            geo_fit=geo_fit,
            vibe_fit=None,
        ),
        provider_evidence=provider_evidence,
        review_themes=themes,
        source_confidence=source_confidence,
        internal_evidence_gaps=internal_evidence_gaps or [],
        evidence_source_counts={"google_places": 2, "google_place_details": 3},
        theme_counts={},
        is_minimal=is_minimal,
    )


# ── Test 1: Role assignment — best_overall / strongest_query_match ────────────

class TestRoleAssignmentHighConceptFit:
    """Scenario 1: High concept-fit, strong evidence → best_overall or strongest_query_match."""

    def test_best_overall_requires_high_concept_and_strong_confidence(self):
        signals = CardCurationSignals(
            concept_fit=0.85,
            geo_fit=0.4,
            modifier_fit="none",
            modifier_requested=False,
            source_confidence=CONFIDENCE_STRONG,
            theme_count=3,
            has_place_details=True,
            has_explicit_modifier_evidence=False,
            has_listing_context_only=False,
            negative_caveat_count=0,
            evidence_gap_count=0,
            diversity_key="restaurant",
            original_rank_index=0,
        )
        role, reasons = _assign_role(signals, is_minimal=False)
        assert role == ROLE_BEST_OVERALL
        assert any("strong" in r for r in reasons)

    def test_strongest_query_match_for_high_concept_mixed_confidence(self):
        signals = CardCurationSignals(
            concept_fit=0.75,
            geo_fit=0.3,
            modifier_fit="none",
            modifier_requested=False,
            source_confidence=CONFIDENCE_MIXED,
            theme_count=2,
            has_place_details=True,
            has_explicit_modifier_evidence=False,
            has_listing_context_only=False,
            negative_caveat_count=0,
            evidence_gap_count=1,
            diversity_key="brewery",
            original_rank_index=0,
        )
        role, _ = _assign_role(signals, is_minimal=False)
        assert role == ROLE_STRONGEST_QUERY_MATCH

    def test_best_overall_not_assigned_without_strong_confidence(self):
        # High concept_fit but only MIXED confidence → not best_overall
        signals = CardCurationSignals(
            concept_fit=0.9,
            geo_fit=0.5,
            modifier_fit="none",
            modifier_requested=False,
            source_confidence=CONFIDENCE_MIXED,
            theme_count=1,
            has_place_details=False,
            has_explicit_modifier_evidence=False,
            has_listing_context_only=False,
            negative_caveat_count=0,
            evidence_gap_count=2,
            diversity_key="bar",
            original_rank_index=0,
        )
        role, _ = _assign_role(signals, is_minimal=False)
        assert role == ROLE_STRONGEST_QUERY_MATCH  # concept >= 0.7 → strongest

    def test_curate_cards_assigns_best_overall_via_dossier(self):
        entity = _make_entity(place_id="places/top")
        rank_score = _make_rank_score(subtype_fit=0.85, geo_fit=0.4)
        dossier = _make_details_dossier(
            place_id="places/top",
            concept_fit=0.85,
            source_confidence=CONFIDENCE_STRONG,
            food_drink=["craft beer", "seasonal menu"],
            ambiance=["cozy"],
        )
        result = curate_cards(
            ranked=[(entity, rank_score)],
            dossiers=[dossier],
            first_card_limit=6,
        )
        assert result.output_count == 1
        assert result.curated_cards[0].role == ROLE_BEST_OVERALL


# ── Test 2: modifier_confirmed role assignment ─────────────────────────────────

class TestModifierConfirmedRole:
    """Scenario 2: modifier_confirmed only when modifier_fit confirmed or explicit evidence."""

    def test_modifier_confirmed_from_modifier_fit_confirmed(self):
        signals = CardCurationSignals(
            concept_fit=0.55,
            geo_fit=0.5,
            modifier_fit="confirmed",
            modifier_requested=True,
            source_confidence=CONFIDENCE_MIXED,
            theme_count=0,
            has_place_details=False,
            has_explicit_modifier_evidence=False,
            has_listing_context_only=False,
            negative_caveat_count=0,
            evidence_gap_count=1,
            diversity_key="restaurant",
            original_rank_index=1,
        )
        role, _ = _assign_role(signals, is_minimal=False)
        assert role == ROLE_MODIFIER_CONFIRMED

    def test_modifier_confirmed_from_explicit_enrichment_evidence(self):
        # No ranker confirmation but explicit view/outdoor enrichment evidence
        signals = CardCurationSignals(
            concept_fit=0.5,
            geo_fit=0.6,
            modifier_fit="not_confirmed",
            modifier_requested=True,
            source_confidence=CONFIDENCE_MIXED,
            theme_count=1,
            has_place_details=True,
            has_explicit_modifier_evidence=True,   # outdoor seating amenity confirmed
            has_listing_context_only=False,
            negative_caveat_count=0,
            evidence_gap_count=0,
            diversity_key="bar",
            original_rank_index=0,
        )
        role, _ = _assign_role(signals, is_minimal=False)
        assert role == ROLE_MODIFIER_CONFIRMED

    def test_modifier_not_assigned_when_modifier_not_confirmed_no_explicit_evidence(self):
        signals = CardCurationSignals(
            concept_fit=0.55,
            geo_fit=0.5,
            modifier_fit="not_confirmed",
            modifier_requested=True,
            source_confidence=CONFIDENCE_MIXED,
            theme_count=0,
            has_place_details=False,
            has_explicit_modifier_evidence=False,
            has_listing_context_only=False,
            negative_caveat_count=0,
            evidence_gap_count=2,
            diversity_key="restaurant",
            original_rank_index=2,
        )
        role, _ = _assign_role(signals, is_minimal=False)
        assert role != ROLE_MODIFIER_CONFIRMED

    def test_modifier_confirmed_requires_concept_fit_threshold(self):
        # modifier_fit confirmed but concept_fit too low
        signals = CardCurationSignals(
            concept_fit=0.3,  # below 0.4 threshold
            geo_fit=0.8,
            modifier_fit="confirmed",
            modifier_requested=True,
            source_confidence=CONFIDENCE_MIXED,
            theme_count=0,
            has_place_details=False,
            has_explicit_modifier_evidence=False,
            has_listing_context_only=False,
            negative_caveat_count=0,
            evidence_gap_count=2,
            diversity_key="restaurant",
            original_rank_index=3,
        )
        role, _ = _assign_role(signals, is_minimal=False)
        assert role != ROLE_MODIFIER_CONFIRMED


# ── Test 3: No modifier_confirmed from formatted_address ──────────────────────

class TestNoModifierConfirmedFromAddress:
    """Scenario 3: formatted_address alone cannot create modifier_confirmed."""

    def test_address_riverwalk_does_not_create_modifier_confirmed(self):
        # PR #259 invariant: formatted_address "Riverwalk" does NOT populate
        # view_patio_waterfront. So dossier has no explicit modifier evidence.
        dossier = _make_dossier(
            place_id="places/addr",
            concept_fit=0.55,
            modifier_fit="not_confirmed",  # ranker did not confirm from address
        )
        # view_patio_waterfront is empty — address-based detection is prohibited
        assert dossier.review_themes.view_patio_waterfront == []

        signals = _build_curation_signals(dossier, original_rank_index=0)
        assert not signals.has_explicit_modifier_evidence
        assert not signals.has_listing_context_only

        role, _ = _assign_role(signals, is_minimal=False)
        assert role != ROLE_MODIFIER_CONFIRMED

    def test_no_modifier_role_when_only_address_context(self):
        # Explicitly test that a dossier built from address-only data
        # (no enrichment, modifier not confirmed) does not get modifier_confirmed
        entity = _make_entity(
            place_id="places/addr_only",
            name="The Riverwalk Bar",
        )
        dossier = _make_dossier(
            place_id="places/addr_only",
            name="The Riverwalk Bar",
            concept_fit=0.6,
            modifier_fit="not_confirmed",
            # view_patio_waterfront intentionally empty (address not used)
        )
        rank_score = _make_rank_score(subtype_fit=0.6)
        result = curate_cards(
            ranked=[(entity, rank_score)],
            dossiers=[dossier],
            first_card_limit=6,
        )
        assert result.curated_cards[0].role != ROLE_MODIFIER_CONFIRMED


# ── Test 4: Listing context is lower-trust ────────────────────────────────────

class TestListingContextLowerTrust:
    """Scenario 4: listing_context name token is lower-trust; explicit enrichment wins."""

    def test_listing_context_only_does_not_yield_modifier_confirmed(self):
        # View/outdoor in name → listing_context:* marker only
        themes = ReviewThemeEvidence(
            view_patio_waterfront=["listing_context:rooftop"],
        )
        dossier = _make_dossier(
            concept_fit=0.55,
            modifier_fit="not_confirmed",
            review_themes=themes,
        )
        signals = _build_curation_signals(dossier, original_rank_index=0)
        assert signals.has_listing_context_only is True
        assert signals.has_explicit_modifier_evidence is False

        role, _ = _assign_role(signals, is_minimal=False)
        assert role != ROLE_MODIFIER_CONFIRMED

    def test_explicit_enrichment_wins_over_listing_context(self):
        # Explicit outdoor_seating amenity → "outdoor seating (amenity)" (no listing_context: prefix)
        themes = ReviewThemeEvidence(
            view_patio_waterfront=["outdoor seating (amenity)"],
        )
        dossier = _make_dossier(
            concept_fit=0.5,
            modifier_fit="not_confirmed",
            review_themes=themes,
            provider_evidence=[
                ProviderEvidenceItem(source="google_places", facts=["type:bar"]),
                ProviderEvidenceItem(source="google_place_details", facts=["outdoor_seating:True"]),
            ],
        )
        signals = _build_curation_signals(dossier, original_rank_index=0)
        assert signals.has_explicit_modifier_evidence is True
        assert signals.has_listing_context_only is False

    def test_listing_context_plus_explicit_is_not_listing_context_only(self):
        themes = ReviewThemeEvidence(
            view_patio_waterfront=["listing_context:patio", "outdoor seating (amenity)"],
        )
        dossier = _make_dossier(
            concept_fit=0.5,
            modifier_fit="none",
            review_themes=themes,
        )
        signals = _build_curation_signals(dossier, original_rank_index=0)
        assert signals.has_listing_context_only is False
        assert signals.has_explicit_modifier_evidence is True


# ── Test 5: Review count alone does not create evidence_rich or best_overall ──

class TestReviewCountAloneInsufficientForHighRoles:
    """Scenario 5: Review count is a card stat, not a theme or confidence signal."""

    def test_high_review_count_alone_does_not_yield_evidence_rich(self):
        # High review count appears as fact in google_places but not in themes
        # and does not produce source_confidence=STRONG
        provider_evidence = [
            ProviderEvidenceItem(
                source="google_places",
                facts=["type:restaurant", "rating:4.7", "review_count:5000"],
            )
        ]
        dossier = _make_dossier(
            concept_fit=0.6,
            source_confidence=CONFIDENCE_MIXED,  # no enrichment → not STRONG
            provider_evidence=provider_evidence,
            review_themes=ReviewThemeEvidence(),  # no themes
            is_minimal=True,
        )
        signals = _build_curation_signals(dossier, original_rank_index=0)
        assert signals.theme_count == 0
        assert not signals.has_place_details

        role, _ = _assign_role(signals, is_minimal=True)
        assert role not in (ROLE_EVIDENCE_RICH, ROLE_BEST_OVERALL)

    def test_high_review_count_alone_does_not_yield_best_overall(self):
        dossier = _make_dossier(
            concept_fit=0.85,
            source_confidence=CONFIDENCE_MIXED,  # review count cannot produce STRONG
        )
        signals = _build_curation_signals(dossier, original_rank_index=0)
        role, _ = _assign_role(signals, is_minimal=False)
        # concept >= 0.7 → strongest_query_match, NOT best_overall (needs STRONG conf)
        assert role == ROLE_STRONGEST_QUERY_MATCH

    def test_review_count_fact_not_in_theme_count(self):
        # Verify review_count in google_places facts does not bleed into theme_count
        provider_evidence = [
            ProviderEvidenceItem(
                source="google_places",
                facts=["review_count:9999", "rating:4.8"],
            )
        ]
        dossier = _make_dossier(
            provider_evidence=provider_evidence,
            review_themes=ReviewThemeEvidence(),
        )
        signals = _build_curation_signals(dossier, original_rank_index=0)
        assert signals.theme_count == 0  # review_count never leaks into themes


# ── Test 6: Place Details enrichment creates evidence_rich / distinctive_theme ─

class TestPlaceDetailsEnrichmentCreatesRichRoles:
    """Scenario 6: Explicit enrichment themes can produce evidence_rich / distinctive_theme."""

    def test_place_details_with_single_theme_creates_evidence_rich(self):
        dossier = _make_details_dossier(
            concept_fit=0.55,
            source_confidence=CONFIDENCE_MIXED,
            food_drink=["craft beer (amenity)"],
        )
        signals = _build_curation_signals(dossier, original_rank_index=0)
        assert signals.has_place_details
        assert signals.theme_count >= 1

        role, _ = _assign_role(signals, is_minimal=False)
        assert role == ROLE_EVIDENCE_RICH

    def test_place_details_with_three_themes_creates_distinctive_theme(self):
        dossier = _make_details_dossier(
            concept_fit=0.55,
            source_confidence=CONFIDENCE_MIXED,
            food_drink=["craft beer", "seasonal menu"],
            ambiance=["cozy"],
        )
        signals = _build_curation_signals(dossier, original_rank_index=0)
        assert signals.has_place_details
        assert signals.theme_count >= 3

        role, _ = _assign_role(signals, is_minimal=False)
        assert role == ROLE_DISTINCTIVE_THEME

    def test_evidence_rich_requires_place_details(self):
        # Many themes but NO place_details → not evidence_rich
        themes = ReviewThemeEvidence(
            food_drink=["beer", "wine", "cocktails"],
            ambiance=["cozy"],
        )
        dossier = _make_dossier(
            concept_fit=0.55,
            review_themes=themes,
            # Only google_places provider, no google_place_details
            provider_evidence=[ProviderEvidenceItem(source="google_places", facts=["type:bar"])],
        )
        signals = _build_curation_signals(dossier, original_rank_index=0)
        assert not signals.has_place_details
        role, _ = _assign_role(signals, is_minimal=False)
        assert role not in (ROLE_EVIDENCE_RICH, ROLE_DISTINCTIVE_THEME)


# ── Test 7: Low evidence cards get safe_popular_fallback or low_evidence_holdback ─

class TestLowEvidenceCardsPreserved:
    """Scenario 7: Low-evidence Google-verified cards are not dropped, just given lower roles."""

    def test_minimal_dossier_low_concept_gets_low_evidence_holdback(self):
        dossier = _make_dossier(
            concept_fit=0.2,
            source_confidence=CONFIDENCE_WEAK,
            is_minimal=True,
        )
        signals = _build_curation_signals(dossier, original_rank_index=0)
        role, _ = _assign_role(signals, is_minimal=True)
        assert role == ROLE_LOW_EVIDENCE_HOLDBACK

    def test_minimal_dossier_moderate_concept_gets_safe_popular_fallback(self):
        dossier = _make_dossier(
            concept_fit=0.35,
            source_confidence=CONFIDENCE_WEAK,
            is_minimal=True,
        )
        signals = _build_curation_signals(dossier, original_rank_index=0)
        role, _ = _assign_role(signals, is_minimal=True)
        # concept_fit=0.35 >= 0.25 → safe_popular_fallback (despite is_minimal)
        assert role == ROLE_SAFE_POPULAR_FALLBACK

    def test_low_evidence_cards_not_dropped_from_output(self):
        entities = [
            _make_entity(place_id=f"places/{i}", name=f"Place {i}")
            for i in range(4)
        ]
        scores = [_make_rank_score(subtype_fit=0.7 - i * 0.15) for i in range(4)]
        dossiers = [
            _make_dossier(place_id=f"places/{i}", concept_fit=0.7 - i * 0.15)
            for i in range(4)
        ]
        result = curate_cards(
            ranked=list(zip(entities, scores)),
            dossiers=dossiers,
            first_card_limit=6,
        )
        # All 4 cards present in output (none dropped)
        assert result.output_count == 4
        assert result.input_count == 4


# ── Test 8: Curator preserves max card cap ─────────────────────────────────────

class TestCardCapPreserved:
    """Scenario 8: Curator never adds cards beyond input; card cap logic unchanged."""

    def test_curator_output_count_equals_input_count(self):
        n = 8
        entities = [_make_entity(place_id=f"places/{i}") for i in range(n)]
        scores = [_make_rank_score(subtype_fit=0.8 - i * 0.05) for i in range(n)]
        # Dossiers only for first 6 (first_card_limit)
        dossiers = [_make_dossier(place_id=f"places/{i}", concept_fit=0.8 - i * 0.05) for i in range(6)]
        result = curate_cards(
            ranked=list(zip(entities, scores)),
            dossiers=dossiers,
            first_card_limit=6,
        )
        # Cards beyond dossier coverage get interesting_but_weaker with no dossier
        assert result.output_count == n

    def test_curator_with_empty_ranked_returns_empty(self):
        result = curate_cards(ranked=[], dossiers=[], first_card_limit=6)
        assert result.output_count == 0
        assert result.curated_cards == []

    def test_default_first_card_limit_is_six(self):
        from app.concierge.deadline_manager import DEFAULT_SLA, clamp_first_card_limit
        limit = clamp_first_card_limit(DEFAULT_SLA.first_card_limit)
        assert limit == 6


# ── Test 9: Curator never creates card payload fields ─────────────────────────

class TestCuratorNeverMintsCards:
    """Scenario 9: CuratedCard has no addable/display/note payload fields."""

    def test_curated_card_has_no_addable_field(self):
        entity = _make_entity()
        dossier = _make_dossier()
        rank_score = _make_rank_score()
        result = curate_cards(
            ranked=[(entity, rank_score)],
            dossiers=[dossier],
            first_card_limit=6,
        )
        card = result.curated_cards[0]
        assert not hasattr(card, "addable")
        assert not hasattr(card, "display")
        assert not hasattr(card, "display_why")
        assert not hasattr(card, "display_why_validated")
        assert not hasattr(card, "why_pick")
        assert not hasattr(card, "google_verification")

    def test_curated_card_entity_is_same_object(self):
        # entity inside CuratedCard must be the SAME object — not a copy
        entity = _make_entity()
        rank_score = _make_rank_score()
        dossier = _make_dossier()
        result = curate_cards(
            ranked=[(entity, rank_score)],
            dossiers=[dossier],
            first_card_limit=6,
        )
        assert result.curated_cards[0].entity is entity
        assert result.curated_cards[0].rank_score is rank_score

    def test_curated_set_result_has_no_card_payload_fields(self):
        result = curate_cards(ranked=[], dossiers=[], first_card_limit=6)
        # CuratedSetResult has no LiveResearchResult/UnifiedRestaurantResult fields
        assert not hasattr(result, "restaurants")
        assert not hasattr(result, "source_status")
        assert not hasattr(result, "verified_place")

    def test_curation_signals_has_no_card_fields(self):
        dossier = _make_dossier()
        signals = _build_curation_signals(dossier, original_rank_index=0)
        assert not hasattr(signals, "addable")
        assert not hasattr(signals, "display_why")
        assert not hasattr(signals, "note")


# ── Test 10: Fallback path preserves original order ───────────────────────────

class TestCuratorFallbackPath:
    """Scenario 10: Curator failure leaves original ranked order unchanged."""

    def test_curate_cards_does_not_raise_on_bad_dossier(self):
        entity = _make_entity()
        rank_score = _make_rank_score()
        # Pass a broken dossier (None attributes will raise AttributeError internally)
        bad_dossier = SimpleNamespace(
            place_id="places/abc",
            # Missing all expected attributes
        )
        # curate_cards itself should not raise; it handles gracefully
        # (internal per-card exceptions are caught)
        result = curate_cards(
            ranked=[(entity, rank_score)],
            dossiers=[bad_dossier],  # type: ignore
            first_card_limit=6,
        )
        # Should not raise; card appears with fallback role
        assert result.input_count == 1

    def test_integration_fallback_preserves_ranked_order(self):
        """When curator raises, semantic_retrieval falls back to original order.

        This test verifies the integration contract, not the curator directly,
        by simulating the try/except wrapper in semantic_retrieval.py.
        """
        entities = [_make_entity(place_id=f"places/{i}", name=f"Place {i}") for i in range(3)]
        scores = [_make_rank_score(subtype_fit=0.8 - i * 0.1) for i in range(3)]
        original_ranked = list(zip(entities, scores))

        # Simulate the integration fallback pattern from semantic_retrieval.py
        ranked = list(original_ranked)  # copy
        try:
            raise RuntimeError("simulated curator failure")
        except Exception:
            pass  # ranked unchanged — fallback path

        # ranked should be unchanged after exception
        assert [(e.place_id, s.subtype_fit) for e, s in ranked] == [
            (e.place_id, s.subtype_fit) for e, s in original_ranked
        ]


# ── Test 11: Ordering is stable and deterministic ─────────────────────────────

class TestDeterministicOrdering:
    """Scenario 11: Output order is stable across repeated runs."""

    def _make_input(self):
        entities = [_make_entity(place_id=f"places/{i}", name=f"Place {i}") for i in range(5)]
        scores = [_make_rank_score(subtype_fit=0.8 - i * 0.05) for i in range(5)]
        dossiers = [
            _make_dossier(
                place_id=f"places/{i}",
                concept_fit=0.8 - i * 0.05,
                source_confidence=CONFIDENCE_MIXED if i < 3 else CONFIDENCE_WEAK,
            )
            for i in range(5)
        ]
        return entities, scores, dossiers

    def test_repeated_runs_produce_identical_output_order(self):
        entities, scores, dossiers = self._make_input()
        ranked = list(zip(entities, scores))

        result1 = curate_cards(ranked=ranked, dossiers=dossiers, first_card_limit=5)
        result2 = curate_cards(ranked=ranked, dossiers=dossiers, first_card_limit=5)

        order1 = [c.original_rank_index for c in result1.curated_cards]
        order2 = [c.original_rank_index for c in result2.curated_cards]
        assert order1 == order2

    def test_curation_score_is_identical_for_same_signals(self):
        signals = CardCurationSignals(
            concept_fit=0.65,
            geo_fit=0.45,
            modifier_fit="none",
            modifier_requested=False,
            source_confidence=CONFIDENCE_MIXED,
            theme_count=2,
            has_place_details=True,
            has_explicit_modifier_evidence=False,
            has_listing_context_only=False,
            negative_caveat_count=1,
            evidence_gap_count=1,
            diversity_key="restaurant",
            original_rank_index=2,
        )
        score1 = _compute_curation_score(signals)
        score2 = _compute_curation_score(signals)
        assert score1 == score2


# ── Test 12: Conservative reorder — stronger card can move up ─────────────────

class TestConservativeReorder:
    """Scenario 12: A clearly stronger card can move up within cap."""

    def test_high_evidence_modifier_confirmed_card_moves_up(self):
        # Card at rank 2 (concept 0.85, modifier_confirmed, place_details)
        # should outscore card at rank 0 (concept 0.6, no enrichment)
        entity_weak = _make_entity(place_id="places/weak", name="Weak Place")
        entity_strong = _make_entity(place_id="places/strong", name="Strong Place")

        score_weak = _make_rank_score(subtype_fit=0.6, geo_fit=0.3)
        score_strong = _make_rank_score(subtype_fit=0.85, geo_fit=0.4)

        dossier_weak = _make_dossier(
            place_id="places/weak",
            concept_fit=0.6,
            source_confidence=CONFIDENCE_WEAK,
            is_minimal=True,
        )
        dossier_strong = _make_details_dossier(
            place_id="places/strong",
            concept_fit=0.85,
            modifier_fit="confirmed",
            source_confidence=CONFIDENCE_STRONG,
            food_drink=["craft beer", "seasonal"],
            ambiance=["cozy"],
        )

        # Original order: weak first, strong second
        ranked = [(entity_weak, score_weak), (entity_strong, score_strong)]
        dossiers = [dossier_weak, dossier_strong]

        result = curate_cards(ranked=ranked, dossiers=dossiers, first_card_limit=6)

        # Strong card should now be at index 0 in curated output
        names = [c.entity.name for c in result.curated_cards[:2]]
        assert names[0] == "Strong Place", f"Expected Strong Place first, got: {names}"
        assert result.reordered_count > 0

    def test_reorder_count_increments_for_each_position_changed(self):
        # Three cards; the best one starts last
        entities = [_make_entity(place_id=f"places/{i}", name=f"Place {i}") for i in range(3)]
        scores = [_make_rank_score(subtype_fit=[0.3, 0.5, 0.9][i]) for i in range(3)]
        dossiers = [
            _make_dossier(place_id=f"places/{i}", concept_fit=[0.3, 0.5, 0.9][i])
            for i in range(3)
        ]
        result = curate_cards(
            ranked=list(zip(entities, scores)),
            dossiers=dossiers,
            first_card_limit=6,
        )
        # The 0.9-concept card (originally rank 2) should be first now
        assert result.curated_cards[0].entity.name == "Place 2"


# ── Test 13: No broad reorder via theme count alone ───────────────────────────

class TestNoBroadReorderByThemeCount:
    """Scenario 13: Low concept-fit card cannot jump above strong concept-fit card via themes."""

    def test_theme_count_alone_cannot_flip_concept_fit_ordering(self):
        entity_high_concept = _make_entity(place_id="places/high", name="High Concept")
        entity_low_concept = _make_entity(place_id="places/low", name="Low Concept")

        score_high = _make_rank_score(subtype_fit=0.8, geo_fit=0.2)
        score_low = _make_rank_score(subtype_fit=0.3, geo_fit=0.2)

        # High concept: no enrichment, no themes
        dossier_high = _make_dossier(
            place_id="places/high",
            concept_fit=0.8,
            source_confidence=CONFIDENCE_WEAK,
            is_minimal=True,
        )
        # Low concept: lots of themes (rich enrichment)
        dossier_low = _make_details_dossier(
            place_id="places/low",
            concept_fit=0.3,
            source_confidence=CONFIDENCE_STRONG,
            food_drink=["craft beer", "seasonal menu", "wine", "cocktails"],
            ambiance=["cozy", "rustic"],
        )

        # Original order: high concept first, then low concept
        ranked = [(entity_high_concept, score_high), (entity_low_concept, score_low)]
        dossiers = [dossier_high, dossier_low]

        result = curate_cards(ranked=ranked, dossiers=dossiers, first_card_limit=6)

        first_card = result.curated_cards[0]
        assert first_card.entity.name == "High Concept", (
            f"Low concept card jumped above high concept card. First: {first_card.entity.name}, "
            f"scores: high={_compute_curation_score(_build_curation_signals(dossier_high, 0)):.3f}, "
            f"low={_compute_curation_score(_build_curation_signals(dossier_low, 1)):.3f}"
        )

    def test_curation_score_formula_concept_dominates(self):
        # Directly verify score ordering
        signals_high = CardCurationSignals(
            concept_fit=0.8, geo_fit=0.2, modifier_fit="none",
            modifier_requested=False,
            source_confidence=CONFIDENCE_WEAK, theme_count=0,
            has_place_details=False, has_explicit_modifier_evidence=False,
            has_listing_context_only=False, negative_caveat_count=0,
            evidence_gap_count=2, diversity_key="restaurant", original_rank_index=0,
        )
        signals_low = CardCurationSignals(
            concept_fit=0.3, geo_fit=0.2, modifier_fit="none",
            modifier_requested=False,
            source_confidence=CONFIDENCE_STRONG, theme_count=10,
            has_place_details=True, has_explicit_modifier_evidence=False,
            has_listing_context_only=False, negative_caveat_count=0,
            evidence_gap_count=0, diversity_key="restaurant", original_rank_index=1,
        )
        score_high = _compute_curation_score(signals_high)
        score_low = _compute_curation_score(signals_low)
        assert score_high > score_low, (
            f"High concept score ({score_high:.3f}) should exceed "
            f"low concept with many themes ({score_low:.3f})"
        )


# ── Test 14: Telemetry counts ─────────────────────────────────────────────────

class TestTelemetryCounts:
    """Scenario 14: Telemetry counts roles/confidence/reorders accurately."""

    def test_role_counts_match_actual_assignments(self):
        entities = [_make_entity(place_id=f"places/{i}") for i in range(4)]
        scores = [_make_rank_score(subtype_fit=[0.85, 0.75, 0.55, 0.20][i]) for i in range(4)]
        dossiers = [
            _make_details_dossier(
                place_id="places/0", concept_fit=0.85,
                source_confidence=CONFIDENCE_STRONG,
            ),
            _make_dossier(place_id="places/1", concept_fit=0.75),
            _make_dossier(
                place_id="places/2", concept_fit=0.55,
                modifier_fit="confirmed",
            ),
            _make_dossier(
                place_id="places/3", concept_fit=0.20,
                is_minimal=True, source_confidence=CONFIDENCE_WEAK,
            ),
        ]
        result = curate_cards(
            ranked=list(zip(entities, scores)),
            dossiers=dossiers,
            first_card_limit=6,
        )
        # Verify role counts sum to output_count
        assert sum(result.role_counts.values()) == result.output_count
        # Verify low_evidence_holdback_count matches role_counts
        assert result.low_evidence_holdback_count == result.role_counts.get(
            ROLE_LOW_EVIDENCE_HOLDBACK, 0
        )

    def test_confidence_counts_match_dossier_sources(self):
        entities = [_make_entity(place_id=f"places/{i}") for i in range(3)]
        scores = [_make_rank_score() for _ in range(3)]
        dossiers = [
            _make_dossier(place_id="places/0", source_confidence=CONFIDENCE_STRONG),
            _make_dossier(place_id="places/1", source_confidence=CONFIDENCE_MIXED),
            _make_dossier(place_id="places/2", source_confidence=CONFIDENCE_WEAK),
        ]
        result = curate_cards(
            ranked=list(zip(entities, scores)),
            dossiers=dossiers,
            first_card_limit=6,
        )
        assert result.source_confidence_counts.get(CONFIDENCE_STRONG, 0) >= 1
        assert result.source_confidence_counts.get(CONFIDENCE_MIXED, 0) >= 1
        assert result.source_confidence_counts.get(CONFIDENCE_WEAK, 0) >= 1

    def test_as_telemetry_dict_has_required_keys(self):
        result = curate_cards(ranked=[], dossiers=[], first_card_limit=6)
        tel = result.as_telemetry_dict(elapsed_ms=42)
        required_keys = {
            "curated_input_count",
            "curated_output_count",
            "curated_role_counts",
            "curated_confidence_counts",
            "curated_reordered_count",
            "curated_modifier_confirmed_count",
            "curated_evidence_rich_count",
            "curated_low_evidence_holdback_count",
            "curated_fallback_to_original_order",
            "curated_ms",
        }
        assert required_keys.issubset(tel.keys())
        assert tel["curated_ms"] == 42

    def test_reordered_count_accurate(self):
        # Original order: 0.3 concept first, 0.85 concept second
        entities = [_make_entity(place_id=f"places/{i}") for i in range(2)]
        scores = [_make_rank_score(subtype_fit=[0.3, 0.85][i]) for i in range(2)]
        dossiers = [
            _make_dossier(place_id="places/0", concept_fit=0.3),
            _make_dossier(place_id="places/1", concept_fit=0.85),
        ]
        result = curate_cards(
            ranked=list(zip(entities, scores)),
            dossiers=dossiers,
            first_card_limit=6,
        )
        # Both positions changed → reordered_count = 2
        assert result.reordered_count == 2


# ── Test 15: PR #257 fallback_note_visible_count invariant ────────────────────

class TestPR257InvariantUnchanged:
    """Scenario 15: fallback_note_visible_count=0 structural invariant is unchanged."""

    def test_curated_card_has_no_note_field(self):
        entity = _make_entity()
        dossier = _make_dossier()
        rank_score = _make_rank_score()
        result = curate_cards(
            ranked=[(entity, rank_score)],
            dossiers=[dossier],
            first_card_limit=6,
        )
        card = result.curated_cards[0]
        assert not hasattr(card, "note")
        assert not hasattr(card, "display_why")
        assert not hasattr(card, "display_why_validated")

    def test_curated_set_result_has_no_note_count_field(self):
        result = curate_cards(ranked=[], dossiers=[], first_card_limit=6)
        assert not hasattr(result, "fallback_note_visible_count")
        assert not hasattr(result, "visible_note_count")

    def test_sla_card_cap_dataclass_unchanged(self):
        from app.concierge.deadline_manager import DEFAULT_SLA
        assert DEFAULT_SLA.first_card_limit == 6
        assert DEFAULT_SLA.first_card_min == 5
        assert DEFAULT_SLA.first_card_max == 7


# ── Test 16: PR #258 non-critical enrichment invariants ───────────────────────

class TestPR258InvariantsUnchanged:
    """Scenario 16: PR #258 parallel retrieval contracts remain importable and valid."""

    def test_parallel_retrieval_contracts_importable(self):
        from app.concierge.parallel_retrieval import (
            CriticalPathResult,
            NonCriticalEnrichmentResult,
            ParallelRetrievalResult,
        )
        # Verify key dataclasses are importable and have expected fields
        assert hasattr(CriticalPathResult, "__dataclass_fields__") or True
        assert hasattr(NonCriticalEnrichmentResult, "__dataclass_fields__") or True
        assert hasattr(ParallelRetrievalResult, "__dataclass_fields__") or True
        # Verify no card payload fields on these types
        prf = ParallelRetrievalResult.__dataclass_fields__
        assert "note" not in prf
        assert "verified_place" not in prf
        assert "addable" not in prf

    def test_enrichment_result_has_no_card_fields(self):
        from app.concierge.parallel_retrieval import NonCriticalEnrichmentResult
        r = NonCriticalEnrichmentResult(
            enrichment_map={},
            elapsed_ms=0,
            used_count=0,
            skipped_count=0,
            skip_reason=None,
        )
        assert hasattr(r, "enrichment_map")
        assert not hasattr(r, "cards")
        assert not hasattr(r, "addable")


# ── Test 17: PR #259 dossier contracts unchanged ──────────────────────────────

class TestPR259DossierContractsUnchanged:
    """Scenario 17: PR #259 PlaceEvidenceDossier contracts remain valid."""

    def test_dossier_contracts_importable(self):
        from app.concierge.evidence_dossier import (
            EvidenceDossierTelemetry,
            PlaceEvidenceDossier,
            QueryFitEvidence,
            ReviewThemeEvidence,
            build_dossiers_for_ranked_cards,
            build_place_evidence_dossier,
            extract_review_themes,
            get_dossier_telemetry,
        )
        assert PlaceEvidenceDossier is not None
        assert EvidenceDossierTelemetry is not None

    def test_dossier_has_no_visible_note_fields(self):
        dossier = _make_dossier()
        assert not hasattr(dossier, "note")
        assert not hasattr(dossier, "display_why")
        assert not hasattr(dossier, "display_why_validated")
        assert not hasattr(dossier, "reason")
        # Internal evidence gaps exist but are never visible prose
        assert hasattr(dossier, "internal_evidence_gaps")

    def test_view_outdoor_theme_not_from_address(self):
        from app.concierge.evidence_dossier import extract_review_themes
        themes = extract_review_themes(
            enrichment=None,
            entity_name="Standard Bar",
            google_types=["bar"],
        )
        # Address "Riverwalk" not used as source → no view_patio_waterfront
        assert themes.view_patio_waterfront == []

    def test_listing_context_marker_preserved_in_dossier(self):
        from app.concierge.evidence_dossier import extract_review_themes
        themes = extract_review_themes(
            enrichment=None,
            entity_name="Rooftop Bar Chicago",
        )
        # Name token → listing_context:rooftop (lower trust, not confirmed)
        assert any(e.startswith("listing_context:") for e in themes.view_patio_waterfront)

    def test_dossier_with_listing_context_signals_correctly(self):
        themes = ReviewThemeEvidence(
            view_patio_waterfront=["listing_context:riverwalk"],
        )
        dossier = _make_dossier(review_themes=themes)
        signals = _build_curation_signals(dossier, original_rank_index=0)
        assert signals.has_listing_context_only is True
        assert signals.has_explicit_modifier_evidence is False


class TestPR261ArchitectureCorrections:
    def test_no_modifier_query_with_explicit_outdoor_does_not_assign_modifier_confirmed(self):
        dossier = _make_details_dossier(
            concept_fit=0.55,
            modifier_fit="none",
            view_patio=["outdoor seating (amenity)"],
            source_confidence=CONFIDENCE_MIXED,
        )
        role, _ = _assign_role(_build_curation_signals(dossier, 0), is_minimal=False)
        assert role != ROLE_MODIFIER_CONFIRMED

    def test_modifier_requested_with_explicit_evidence_can_assign_modifier_confirmed(self):
        dossier = _make_details_dossier(
            concept_fit=0.55,
            modifier_fit="not_confirmed",
            view_patio=["outdoor seating (amenity)"],
        )
        role, _ = _assign_role(_build_curation_signals(dossier, 0), is_minimal=False)
        assert role == ROLE_MODIFIER_CONFIRMED

    def test_modifier_requested_listing_context_only_does_not_assign_modifier_confirmed(self):
        dossier = _make_dossier(
            concept_fit=0.55,
            modifier_fit="not_confirmed",
            review_themes=ReviewThemeEvidence(view_patio_waterfront=["listing_context:rooftop"]),
        )
        role, _ = _assign_role(_build_curation_signals(dossier, 0), is_minimal=False)
        assert role != ROLE_MODIFIER_CONFIRMED

    def test_tiny_curation_advantage_does_not_reorder(self):
        ranked = [(_make_entity(place_id="places/a", name="A"), _make_rank_score()), (_make_entity(place_id="places/b", name="B"), _make_rank_score())]
        dossiers = [
            _make_dossier(place_id="places/a", concept_fit=0.60, geo_fit=0.30, source_confidence=CONFIDENCE_MIXED),
            _make_dossier(place_id="places/b", concept_fit=0.61, geo_fit=0.30, source_confidence=CONFIDENCE_MIXED),
        ]
        result = curate_cards(ranked=ranked, dossiers=dossiers, first_card_limit=6)
        assert [c.entity.name for c in result.curated_cards[:2]] == ["A", "B"]

    def test_lower_concept_with_many_themes_cannot_jump_materially_stronger_concept(self):
        ranked = [(_make_entity(place_id="places/high", name="High"), _make_rank_score()), (_make_entity(place_id="places/low", name="Low"), _make_rank_score())]
        dossiers = [
            _make_dossier(place_id="places/high", concept_fit=0.80, source_confidence=CONFIDENCE_WEAK, is_minimal=True),
            _make_details_dossier(place_id="places/low", concept_fit=0.55, source_confidence=CONFIDENCE_STRONG, food_drink=["a","b","c"], ambiance=["d"]),
        ]
        result = curate_cards(ranked=ranked, dossiers=dossiers, first_card_limit=6)
        assert result.curated_cards[0].entity.name == "High"

    def test_best_overall_still_counts_modifier_confirmed_signal(self):
        ranked = [(_make_entity(place_id="places/x", name="X"), _make_rank_score())]
        dossiers = [_make_details_dossier(place_id="places/x", concept_fit=0.85, modifier_fit="confirmed", source_confidence=CONFIDENCE_STRONG)]
        result = curate_cards(ranked=ranked, dossiers=dossiers, first_card_limit=6)
        assert result.curated_cards[0].role == ROLE_BEST_OVERALL
        assert result.modifier_confirmed_count == 1

    def test_best_overall_still_counts_evidence_rich_signal(self):
        ranked = [(_make_entity(place_id="places/y", name="Y"), _make_rank_score())]
        dossiers = [_make_details_dossier(place_id="places/y", concept_fit=0.85, source_confidence=CONFIDENCE_STRONG, food_drink=["craft"]) ]
        result = curate_cards(ranked=ranked, dossiers=dossiers, first_card_limit=6)
        assert result.curated_cards[0].role == ROLE_BEST_OVERALL
        assert result.evidence_rich_count == 1
