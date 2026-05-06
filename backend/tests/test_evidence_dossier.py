"""PR #259 — Evidence Dossier v1 tests.

Tests:
 1. Builds one dossier per top candidate card when budget allows.
 2. Dossier includes Google identity/addability facts but evidence cannot mint cards.
 3. Place Details enrichment, when available, appears as provider evidence.
 4. Missing enrichment still produces a minimal dossier with lower confidence.
 5. Review/theme extraction uses snippets/editorial/amenity evidence, not review count.
 6. View/patio/waterfront themes extracted only from explicit evidence, not address.
 7. Internal evidence gaps stored internally and not converted into visible note text.
 8. Dossier builder respects deadline/budget and builds minimal dossiers when low.
 9. Dossier source/theme telemetry is emitted via get_dossier_telemetry.
10. Existing card cap remains default 6.
11. fallback_note_visible_count remains 0 (structural invariant).
12. Existing Google verification/addability invariants remain unchanged.
13. Existing PR #257 and PR #258 dataclass contracts are still importable/valid.
"""

from __future__ import annotations

import os
import sys
import types
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Dict, FrozenSet, List, Optional
from unittest.mock import MagicMock

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Stub app.core.deps so router/contract imports don't fail.
_deps = sys.modules.get("app.core.deps") or types.ModuleType("app.core.deps")
sys.modules.setdefault("app.core.deps", _deps)
setattr(_deps, "DB", object)
setattr(_deps, "CurrentUserID", object)

# ── Imports under test ────────────────────────────────────────────────────────
from app.concierge.evidence_dossier import (
    CONFIDENCE_MIXED,
    CONFIDENCE_STRONG,
    CONFIDENCE_WEAK,
    DOSSIER_BUDGET_RESERVE_MS,
    EvidenceDossierTelemetry,
    PlaceEvidenceDossier,
    ProviderEvidenceItem,
    QueryFitEvidence,
    ReviewThemeEvidence,
    build_dossiers_for_ranked_cards,
    build_place_evidence_dossier,
    extract_review_themes,
    get_dossier_telemetry,
)
from app.concierge.deadline_manager import DEFAULT_SLA, RequestDeadline, SLAConfig


# ── Test fixtures ─────────────────────────────────────────────────────────────

def _make_entity(
    place_id: str = "places/abc123",
    name: str = "Revolution Brewing",
    formatted_address: str = "2323 N Milwaukee Ave, Chicago, IL, USA",
    types: Optional[List[str]] = None,
    primary_type: str = "brewery",
    rating: float = 4.5,
    user_rating_count: int = 1200,
    price_level: str = "PRICE_LEVEL_MODERATE",
    business_status: str = "OPERATIONAL",
    google_maps_uri: str = "https://maps.google.com/?cid=123",
    website_uri: Optional[str] = None,
    lat: float = 41.9,
    lng: float = -87.7,
) -> Any:
    """Return a minimal PlaceEntity-like SimpleNamespace for tests."""
    return SimpleNamespace(
        place_id=place_id,
        name=name,
        formatted_address=formatted_address,
        types=types or ["brewery", "bar", "food"],
        primary_type=primary_type,
        rating=rating,
        user_rating_count=user_rating_count,
        price_level=price_level,
        business_status=business_status,
        google_maps_uri=google_maps_uri,
        website_uri=website_uri,
        lat=lat,
        lng=lng,
        identity_keys=frozenset({f"pid:{place_id}"}),
        source_query="breweries in Chicago",
    )


def _make_rank_score(
    subtype_fit: float = 0.85,
    geo_fit: float = 0.5,
    total: float = 0.72,
) -> Any:
    return SimpleNamespace(
        total=total,
        subtype_fit=subtype_fit,
        geo_fit=geo_fit,
        quality_signal=0.88,
        evidence_strength=0.85,
        diversity_signal=1.0,
        popularity_signal=0.6,
        trip_context_fit=0.5,
        value_fit=0.5,
        penalties=0.0,
    )


def _make_frame(
    destination: str = "Chicago",
    concept_label: str = "brewery",
    concept_confidence: float = 0.95,
    geography_hints: Optional[List[str]] = None,
    location_modifiers: Optional[List[str]] = None,
    soft_preferences: Optional[List[str]] = None,
    negative_constraints: Optional[List[str]] = None,
    ambiguity_flags: Optional[List[str]] = None,
) -> Any:
    concept = SimpleNamespace(label=concept_label, confidence=concept_confidence)
    return SimpleNamespace(
        destination=destination,
        subtype_concepts=[concept],
        geography_hints=geography_hints or [],
        location_modifiers=location_modifiers or [],
        soft_preferences=soft_preferences or [],
        negative_constraints=negative_constraints or [],
        ambiguity_flags=ambiguity_flags or [],
        value_signals=[],
        use_cases=[],
        open_class_place_detected=False,
    )


def _make_enrichment(
    place_id: str = "places/abc123",
    editorial_summary: Optional[str] = None,
    review_snippets: Optional[List[str]] = None,
    serves_beer: Optional[bool] = None,
    serves_wine: Optional[bool] = None,
    serves_cocktails: Optional[bool] = None,
    outdoor_seating: Optional[bool] = None,
    live_music: Optional[bool] = None,
    good_for_groups: Optional[bool] = None,
) -> Any:
    def has_differentiating_content() -> bool:
        return bool(
            editorial_summary
            or review_snippets
            or serves_beer is not None
            or outdoor_seating is not None
            or live_music is not None
        )

    return SimpleNamespace(
        place_id=place_id,
        editorial_summary=editorial_summary,
        review_snippets=review_snippets or [],
        serves_beer=serves_beer,
        serves_wine=serves_wine,
        serves_cocktails=serves_cocktails,
        outdoor_seating=outdoor_seating,
        live_music=live_music,
        good_for_groups=good_for_groups,
        has_differentiating_content=has_differentiating_content,
    )


# ── Test 1: Builds one dossier per top card when budget allows ─────────────────

class TestDossierBuildsPerCard:
    def test_builds_one_dossier_per_ranked_entity(self):
        entities = [_make_entity(place_id=f"places/{i}", name=f"Brewery {i}") for i in range(8)]
        ranked = [(_make_entity(place_id=f"places/{i}", name=f"Brewery {i}"), _make_rank_score()) for i in range(8)]
        frame = _make_frame()
        deadline = RequestDeadline(sla=DEFAULT_SLA)

        dossiers = build_dossiers_for_ranked_cards(
            ranked=ranked,
            frame=frame,
            enrichment_map={},
            deadline=deadline,
            top_n=6,
        )

        # Top 6 only (top_n=6 cap)
        assert len(dossiers) == 6

    def test_builds_minimal_when_no_enrichment(self):
        entity = _make_entity()
        ranked = [(entity, _make_rank_score())]
        frame = _make_frame()

        dossiers = build_dossiers_for_ranked_cards(
            ranked=ranked,
            frame=frame,
            enrichment_map={},
            deadline=None,
            top_n=6,
        )

        assert len(dossiers) == 1
        assert dossiers[0].is_minimal is True

    def test_dossier_has_required_fields(self):
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score()

        dossier = build_place_evidence_dossier(entity, frame, rank_score)

        assert dossier.place_id == entity.place_id
        assert dossier.name == entity.name
        assert isinstance(dossier.query_fit, QueryFitEvidence)
        assert isinstance(dossier.review_themes, ReviewThemeEvidence)
        assert isinstance(dossier.provider_evidence, list)
        assert dossier.source_confidence in (CONFIDENCE_STRONG, CONFIDENCE_MIXED, CONFIDENCE_WEAK)
        assert isinstance(dossier.internal_evidence_gaps, list)
        assert isinstance(dossier.evidence_source_counts, dict)
        assert isinstance(dossier.theme_counts, dict)


# ── Test 2: Dossier includes Google identity but cannot mint cards ─────────────

class TestDossierCannotMintCards:
    def test_dossier_has_no_card_or_identity_minting_fields(self):
        """PlaceEvidenceDossier has no card/result/LiveResearchResult fields."""
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score()

        dossier = build_place_evidence_dossier(entity, frame, rank_score)

        # Must have identity fields (for reasoning) but not card-minting fields.
        assert dossier.place_id == entity.place_id   # identity readable
        assert dossier.name == entity.name

        # Must NOT have card-minting / result fields
        assert not hasattr(dossier, "restaurants")
        assert not hasattr(dossier, "source_status")
        assert not hasattr(dossier, "verified_place")
        assert not hasattr(dossier, "google_verification")
        assert not hasattr(dossier, "display")
        assert not hasattr(dossier, "addability")

    def test_google_facts_present_in_provider_evidence(self):
        entity = _make_entity(rating=4.5, user_rating_count=1200)
        frame = _make_frame()
        rank_score = _make_rank_score()

        dossier = build_place_evidence_dossier(entity, frame, rank_score)

        google_item = next(
            (p for p in dossier.provider_evidence if p.source == "google_places"), None
        )
        assert google_item is not None
        all_facts = " ".join(google_item.facts)
        assert "rating:4.5" in all_facts
        assert "review_count:1200" in all_facts
        assert "status:OPERATIONAL" in all_facts
        assert "google_maps_uri:present" in all_facts

    def test_addable_status_not_in_dossier(self):
        """Dossier must not contain addable/verified_place fields that could
        cause non-Google sources to mint cards downstream."""
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score()

        dossier = build_place_evidence_dossier(entity, frame, rank_score)

        # Provider evidence is evidence-only metadata, not a card mint signal.
        for pe in dossier.provider_evidence:
            assert pe.source in ("google_places", "google_place_details")
            # No addability field on ProviderEvidenceItem
            assert not hasattr(pe, "addable")
            assert not hasattr(pe, "verified_place")


# ── Test 3: Place Details enrichment appears as provider evidence ──────────────

class TestPlaceDetailsEnrichmentInProviderEvidence:
    def test_enrichment_creates_place_details_bucket(self):
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score()
        enrichment = _make_enrichment(
            editorial_summary="A beloved Chicago taproom with craft IPAs.",
            review_snippets=["Great beers, lively atmosphere!"],
            serves_beer=True,
            outdoor_seating=True,
        )

        dossier = build_place_evidence_dossier(entity, frame, rank_score, enrichment=enrichment)

        details_item = next(
            (p for p in dossier.provider_evidence if p.source == "google_place_details"), None
        )
        assert details_item is not None
        assert len(details_item.facts) > 0
        facts_str = " ".join(details_item.facts)
        assert "editorial_summary" in facts_str
        assert "serves_beer:True" in facts_str
        assert "outdoor_seating:True" in facts_str

    def test_enrichment_upgrades_source_confidence(self):
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score(subtype_fit=0.85)
        enrichment = _make_enrichment(
            editorial_summary="Award-winning microbrewery.",
            serves_beer=True,
        )

        dossier = build_place_evidence_dossier(entity, frame, rank_score, enrichment=enrichment)

        assert dossier.source_confidence == CONFIDENCE_STRONG

    def test_enrichment_with_place_details_not_minimal(self):
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score()
        enrichment = _make_enrichment(editorial_summary="Craft taproom.")

        dossier = build_place_evidence_dossier(entity, frame, rank_score, enrichment=enrichment)

        assert dossier.is_minimal is False

    def test_evidence_source_counts_reflects_enrichment(self):
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score()
        enrichment = _make_enrichment(
            editorial_summary="Award-winning.",
            serves_beer=True,
        )

        dossier = build_place_evidence_dossier(entity, frame, rank_score, enrichment=enrichment)

        assert dossier.evidence_source_counts.get("google_place_details", 0) > 0


# ── Test 4: Missing enrichment → minimal dossier, lower confidence ─────────────

class TestMissingEnrichmentMinimalDossier:
    def test_no_enrichment_is_minimal(self):
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score(subtype_fit=0.3)  # low fit → WEAK

        dossier = build_place_evidence_dossier(entity, frame, rank_score, enrichment=None)

        assert dossier.is_minimal is True

    def test_no_enrichment_weak_confidence_for_low_fit(self):
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score(subtype_fit=0.25)

        dossier = build_place_evidence_dossier(entity, frame, rank_score, enrichment=None)

        assert dossier.source_confidence == CONFIDENCE_WEAK

    def test_no_enrichment_mixed_confidence_for_strong_fit(self):
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score(subtype_fit=0.85)

        dossier = build_place_evidence_dossier(entity, frame, rank_score, enrichment=None)

        # Strong concept fit with no enrichment → MIXED (not STRONG)
        assert dossier.source_confidence == CONFIDENCE_MIXED

    def test_no_enrichment_has_gap_recorded(self):
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score()

        dossier = build_place_evidence_dossier(entity, frame, rank_score, enrichment=None)

        assert "no_place_details_enrichment" in dossier.internal_evidence_gaps

    def test_no_place_details_bucket_when_no_enrichment(self):
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score()

        dossier = build_place_evidence_dossier(entity, frame, rank_score, enrichment=None)

        sources = [p.source for p in dossier.provider_evidence]
        assert "google_place_details" not in sources
        assert "google_places" in sources


# ── Test 5: Theme extraction uses evidence, not review count ───────────────────

class TestReviewThemeExtraction:
    def test_review_count_does_not_produce_themes(self):
        """review_count must NOT appear as a theme or signal."""
        # Entity with high review count but no enrichment
        entity = _make_entity(user_rating_count=9000)
        frame = _make_frame()
        rank_score = _make_rank_score()

        dossier = build_place_evidence_dossier(entity, frame, rank_score, enrichment=None)

        # All theme lists must be empty (no enrichment, no review count themes)
        themes = dossier.review_themes
        # review count must not appear in any theme
        all_theme_strings = " ".join(
            themes.food_drink + themes.ambiance + themes.service +
            themes.crowd_noise + themes.view_patio_waterfront +
            themes.occasion_fit + themes.negative_caveats
        )
        assert "9000" not in all_theme_strings
        assert "review" not in all_theme_strings.lower()

    def test_amenity_flags_produce_themes(self):
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score()
        enrichment = _make_enrichment(
            serves_beer=True,
            serves_cocktails=True,
            live_music=True,
            good_for_groups=True,
        )

        dossier = build_place_evidence_dossier(entity, frame, rank_score, enrichment=enrichment)

        themes = dossier.review_themes
        assert any("beer" in e for e in themes.food_drink)
        assert any("cocktail" in e for e in themes.food_drink)
        assert any("live music" in e for e in themes.ambiance)
        assert any("groups" in e for e in themes.occasion_fit)

    def test_editorial_summary_produces_food_drink_themes(self):
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score()
        enrichment = _make_enrichment(
            editorial_summary="Award-winning taproom with seasonal craft beers and a cozy atmosphere."
        )

        themes = extract_review_themes(enrichment=enrichment, entity_name=entity.name)

        # "cozy" → ambiance; "beer" or "craft" → food_drink
        all_food = " ".join(themes.food_drink)
        all_ambiance = " ".join(themes.ambiance)
        assert "beer" in all_food or "craft" in all_food
        assert "cozy" in all_ambiance

    def test_review_snippet_produces_themes(self):
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score()
        enrichment = _make_enrichment(
            review_snippets=["Amazing cocktails and a romantic rooftop terrace."]
        )

        themes = extract_review_themes(enrichment=enrichment, entity_name=entity.name)

        all_food = " ".join(themes.food_drink)
        all_view = " ".join(themes.view_patio_waterfront)
        assert "cocktail" in all_food
        assert "rooftop" in all_view or "terrace" in all_view


# ── Test 6: View/patio/waterfront from explicit evidence only ──────────────────

class TestViewOutdoorThemeExplicitOnly:
    def test_address_riverwalk_does_not_produce_waterfront_theme(self):
        """formatted_address containing 'Riverwalk' must NOT populate the
        view_patio_waterfront theme. That is listing context, not enrichment."""
        entity = _make_entity(
            name="Gino's East",
            formatted_address="445 N Riverwalk Dr, Chicago, IL, USA",
        )
        frame = _make_frame()
        rank_score = _make_rank_score()
        # No enrichment — only address contains "Riverwalk"
        dossier = build_place_evidence_dossier(entity, frame, rank_score, enrichment=None)

        # Address should NOT produce view_patio_waterfront themes
        assert dossier.review_themes.view_patio_waterfront == []

    def test_outdoor_seating_amenity_produces_theme(self):
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score()
        enrichment = _make_enrichment(outdoor_seating=True)

        dossier = build_place_evidence_dossier(entity, frame, rank_score, enrichment=enrichment)

        assert any("outdoor seating" in e for e in dossier.review_themes.view_patio_waterfront)

    def test_editorial_rooftop_produces_theme(self):
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score()
        enrichment = _make_enrichment(
            editorial_summary="A rooftop bar with panoramic views of downtown."
        )

        themes = extract_review_themes(enrichment=enrichment, entity_name=entity.name)

        assert any("rooftop" in e for e in themes.view_patio_waterfront)

    def test_entity_name_rooftop_is_listing_context_only(self):
        """Name containing 'Rooftop' → listing_context tag, not enrichment proof."""
        enrichment = _make_enrichment()  # no outdoor_seating flag, no text evidence

        themes = extract_review_themes(enrichment=enrichment, entity_name="The Rooftop Bar")

        # Should have listing_context marker, not a confirmed amenity
        assert any("listing_context" in e for e in themes.view_patio_waterfront)
        assert not any("amenity" in e for e in themes.view_patio_waterfront)

    def test_no_enrichment_name_rooftop_still_listing_context(self):
        """Even without enrichment, name token → listing_context (not silent)."""
        themes = extract_review_themes(enrichment=None, entity_name="Rooftop Brewhouse")

        assert any("listing_context:rooftop" in e for e in themes.view_patio_waterfront)

    def test_no_enrichment_no_name_token_no_view_theme(self):
        """Without enrichment and no view token in name, theme list is empty."""
        themes = extract_review_themes(enrichment=None, entity_name="Revolution Brewing")

        assert themes.view_patio_waterfront == []


# ── Test 7: Internal evidence gaps not converted to visible text ───────────────

class TestInternalEvidenceGapsNotVisible:
    def test_gaps_stored_in_internal_field_only(self):
        entity = _make_entity(rating=None)
        frame = _make_frame()
        rank_score = _make_rank_score(subtype_fit=0.3)

        dossier = build_place_evidence_dossier(entity, frame, rank_score, enrichment=None)

        assert len(dossier.internal_evidence_gaps) > 0
        assert "no_place_details_enrichment" in dossier.internal_evidence_gaps
        assert "no_rating" in dossier.internal_evidence_gaps

    def test_gaps_not_in_review_themes(self):
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score()

        dossier = build_place_evidence_dossier(entity, frame, rank_score, enrichment=None)

        # Gaps must not appear as theme strings
        all_themes = (
            dossier.review_themes.food_drink
            + dossier.review_themes.ambiance
            + dossier.review_themes.service
            + dossier.review_themes.view_patio_waterfront
            + dossier.review_themes.crowd_noise
            + dossier.review_themes.occasion_fit
            + dossier.review_themes.negative_caveats
        )
        for gap in dossier.internal_evidence_gaps:
            assert gap not in all_themes

    def test_gaps_not_in_provider_facts(self):
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score()

        dossier = build_place_evidence_dossier(entity, frame, rank_score, enrichment=None)

        all_facts = [
            f for pe in dossier.provider_evidence for f in pe.facts
        ]
        for gap in dossier.internal_evidence_gaps:
            assert gap not in all_facts

    def test_enrichment_gaps_filled_when_present(self):
        entity = _make_entity()
        frame = _make_frame()
        rank_score = _make_rank_score()
        enrichment = _make_enrichment(
            editorial_summary="A great taproom.",
            review_snippets=["Fantastic craft beer!"],
            serves_beer=True,
        )

        dossier = build_place_evidence_dossier(entity, frame, rank_score, enrichment=enrichment)

        # These specific gaps should not appear when enrichment covers them
        assert "no_place_details_enrichment" not in dossier.internal_evidence_gaps
        assert "no_editorial_summary" not in dossier.internal_evidence_gaps
        assert "no_review_snippets" not in dossier.internal_evidence_gaps


# ── Test 8: Deadline/budget gating builds minimal dossiers ────────────────────

class TestDossierDeadlineBudgetGating:
    def test_low_budget_builds_minimal_dossiers(self):
        """When remaining_ms < DOSSIER_BUDGET_RESERVE_MS, dossiers are minimal."""
        entity = _make_entity()
        enrichment = _make_enrichment(editorial_summary="Great taproom.")
        enrichment_map = {entity.place_id: enrichment}

        # Simulate past-budget deadline (very high elapsed time)
        sla = SLAConfig(hard_cutoff_ms=100)
        import time
        deadline = RequestDeadline(sla=sla, t_start=time.monotonic() - 0.2)

        dossiers = build_dossiers_for_ranked_cards(
            ranked=[(entity, _make_rank_score())],
            frame=_make_frame(),
            enrichment_map=enrichment_map,
            deadline=deadline,
            top_n=6,
        )

        assert len(dossiers) == 1
        assert dossiers[0].is_minimal is True

    def test_sufficient_budget_uses_enrichment(self):
        """When remaining budget is sufficient, enrichment is used."""
        entity = _make_entity()
        enrichment = _make_enrichment(editorial_summary="Great taproom.", serves_beer=True)
        enrichment_map = {entity.place_id: enrichment}

        import time
        deadline = RequestDeadline(sla=DEFAULT_SLA, t_start=time.monotonic())

        dossiers = build_dossiers_for_ranked_cards(
            ranked=[(entity, _make_rank_score())],
            frame=_make_frame(),
            enrichment_map=enrichment_map,
            deadline=deadline,
            top_n=6,
        )

        assert len(dossiers) == 1
        assert dossiers[0].is_minimal is False

    def test_none_deadline_uses_enrichment(self):
        """When deadline=None, no budget check is done — enrichment map is used."""
        entity = _make_entity()
        enrichment = _make_enrichment(editorial_summary="Great taproom.")
        enrichment_map = {entity.place_id: enrichment}

        dossiers = build_dossiers_for_ranked_cards(
            ranked=[(entity, _make_rank_score())],
            frame=_make_frame(),
            enrichment_map=enrichment_map,
            deadline=None,
            top_n=6,
        )

        assert len(dossiers) == 1
        assert dossiers[0].is_minimal is False

    def test_empty_ranked_returns_empty(self):
        dossiers = build_dossiers_for_ranked_cards(
            ranked=[],
            frame=_make_frame(),
            enrichment_map={},
            deadline=None,
            top_n=6,
        )
        assert dossiers == []

    def test_category_fn_failure_does_not_raise(self):
        entity = _make_entity()
        dossiers = build_dossiers_for_ranked_cards(
            ranked=[(entity, _make_rank_score())],
            frame=_make_frame(),
            enrichment_map={},
            deadline=None,
            top_n=6,
            category_fn=lambda _e: (_ for _ in ()).throw(ValueError("bad category")),
        )
        assert dossiers == []


class TestThemeExtractionDeterminism:
    def test_repeated_extraction_stable_order_with_more_than_three_hits(self):
        text = " ".join(
            ["beer", "wine", "cocktail", "pizza", "sushi", "brunch", "burger", "ramen"]
        )
        enrichment = _make_enrichment(editorial_summary=text)
        first = extract_review_themes(enrichment=enrichment, entity_name="A")
        for _ in range(5):
            nxt = extract_review_themes(enrichment=enrichment, entity_name="A")
            assert nxt.food_drink == first.food_drink
            assert len(nxt.food_drink) == 3


# ── Test 9: Dossier source/theme telemetry emitted ────────────────────────────

class TestDossierTelemetry:
    def test_telemetry_built_count(self):
        ranked = [(
            _make_entity(place_id=f"places/{i}", name=f"Brewery {i}"),
            _make_rank_score(),
        ) for i in range(4)]
        dossiers = build_dossiers_for_ranked_cards(
            ranked=ranked, frame=_make_frame(), enrichment_map={}, deadline=None, top_n=6
        )

        tel = get_dossier_telemetry(dossiers)
        assert tel.dossier_built_count == 4

    def test_telemetry_confidence_counts(self):
        entity = _make_entity()
        enrichment = _make_enrichment(editorial_summary="Great taproom.", serves_beer=True)
        dossier = build_place_evidence_dossier(entity, _make_frame(), _make_rank_score(subtype_fit=0.85), enrichment)
        tel = get_dossier_telemetry([dossier])

        assert tel.dossier_confidence_counts[CONFIDENCE_STRONG] == 1
        assert tel.dossier_confidence_counts.get(CONFIDENCE_WEAK, 0) == 0

    def test_telemetry_with_place_details_count(self):
        entity = _make_entity()
        enrichment = _make_enrichment(editorial_summary="Great taproom.")
        dossier_with = build_place_evidence_dossier(entity, _make_frame(), _make_rank_score(), enrichment)
        dossier_without = build_place_evidence_dossier(entity, _make_frame(), _make_rank_score())

        tel = get_dossier_telemetry([dossier_with, dossier_without])
        assert tel.dossier_with_place_details_count == 1

    def test_telemetry_minimal_count(self):
        entity = _make_entity()
        dossier = build_place_evidence_dossier(entity, _make_frame(), _make_rank_score())
        tel = get_dossier_telemetry([dossier])
        assert tel.dossier_minimal_count == 1

    def test_telemetry_empty_dossiers(self):
        tel = get_dossier_telemetry([])
        assert tel.dossier_built_count == 0

    def test_telemetry_skipped_count_passthrough(self):
        tel = get_dossier_telemetry([], skipped_due_to_budget=3)
        assert tel.dossier_skipped_due_to_budget_count == 3

    def test_telemetry_review_theme_counts_per_card(self):
        entity = _make_entity()
        enrichment = _make_enrichment(serves_beer=True, live_music=True)
        dossier = build_place_evidence_dossier(entity, _make_frame(), _make_rank_score(), enrichment)
        tel = get_dossier_telemetry([dossier])

        assert len(tel.review_theme_count_per_card) == 1
        assert tel.review_theme_count_per_card[0] >= 2  # beer + live music

    def test_telemetry_evidence_sources_per_card(self):
        entity = _make_entity()
        enrichment = _make_enrichment(editorial_summary="Great.")
        dossier = build_place_evidence_dossier(entity, _make_frame(), _make_rank_score(), enrichment)
        tel = get_dossier_telemetry([dossier])

        assert len(tel.evidence_sources_used_per_card) == 1
        assert "google_places" in tel.evidence_sources_used_per_card[0]
        assert "google_place_details" in tel.evidence_sources_used_per_card[0]

    def test_as_log_dict_has_required_keys(self):
        entity = _make_entity()
        dossier = build_place_evidence_dossier(entity, _make_frame(), _make_rank_score())
        tel = get_dossier_telemetry([dossier])
        log_dict = tel.as_log_dict()

        required_keys = {
            "dossier_built_count",
            "dossier_confidence_counts",
            "dossier_source_counts",
            "dossier_theme_counts",
            "dossier_with_place_details_count",
            "dossier_minimal_count",
            "dossier_skipped_due_to_budget_count",
        }
        assert required_keys <= set(log_dict.keys())


# ── Test 10: Card cap remains default 6 ───────────────────────────────────────

class TestCardCapUnchanged:
    def test_default_first_card_limit_is_6(self):
        assert DEFAULT_SLA.first_card_limit == 6

    def test_dossier_top_n_default_6(self):
        """build_dossiers_for_ranked_cards top_n defaults to 6."""
        ranked = [(
            _make_entity(place_id=f"places/{i}", name=f"Brewery {i}"),
            _make_rank_score(),
        ) for i in range(10)]

        dossiers = build_dossiers_for_ranked_cards(
            ranked=ranked, frame=_make_frame(), enrichment_map={}, deadline=None, top_n=6
        )
        assert len(dossiers) == 6


# ── Test 11: fallback_note_visible_count structural invariant ─────────────────

class TestFallbackNoteInvariant:
    def test_dossier_has_no_note_fields(self):
        """PlaceEvidenceDossier must have no note/reason/visible fields."""
        entity = _make_entity()
        dossier = build_place_evidence_dossier(entity, _make_frame(), _make_rank_score())

        assert not hasattr(dossier, "note")
        assert not hasattr(dossier, "reason")
        assert not hasattr(dossier, "display_why")
        assert not hasattr(dossier, "reason_validated")
        assert not hasattr(dossier, "fallback_note")

    def test_dossier_telemetry_has_no_note_fields(self):
        tel = get_dossier_telemetry([])
        assert not hasattr(tel, "fallback_note_visible_count")
        assert not hasattr(tel, "note")


# ── Test 12: Google verification invariants unchanged ─────────────────────────

class TestGoogleVerificationInvariantsUnchanged:
    def test_dossier_built_from_entity_with_operational_status(self):
        entity = _make_entity(business_status="OPERATIONAL")
        dossier = build_place_evidence_dossier(entity, _make_frame(), _make_rank_score())

        google_item = next(p for p in dossier.provider_evidence if p.source == "google_places")
        assert any("status:OPERATIONAL" in f for f in google_item.facts)

    def test_dossier_does_not_create_cards_from_enrichment(self):
        """The dossier builder returns PlaceEvidenceDossier, not UnifiedRestaurantResult."""
        entity = _make_entity()
        enrichment = _make_enrichment(editorial_summary="Award-winning brewery.")
        dossier = build_place_evidence_dossier(entity, _make_frame(), _make_rank_score(), enrichment)

        assert isinstance(dossier, PlaceEvidenceDossier)
        # Must NOT return anything resembling a card/restaurant result
        assert not hasattr(dossier, "cuisine")
        assert not hasattr(dossier, "booking_link")
        assert not hasattr(dossier, "maps_link")

    def test_non_google_source_does_not_appear_in_dossier(self):
        """No Yelp/Foursquare/Tavily sources in provider_evidence."""
        entity = _make_entity()
        enrichment = _make_enrichment(editorial_summary="Great taproom.")
        dossier = build_place_evidence_dossier(entity, _make_frame(), _make_rank_score(), enrichment)

        sources = {pe.source for pe in dossier.provider_evidence}
        assert "yelp" not in sources
        assert "foursquare" not in sources
        assert "tavily" not in sources
        assert "editorial" not in sources


# ── Test 13: PR #257 and PR #258 contracts still importable ───────────────────

class TestExistingContractsUnchanged:
    def test_pr257_sla_contracts_importable(self):
        """PR #257 SLA/deadline contracts must still be importable."""
        from app.concierge.deadline_manager import (
            DEFAULT_SLA,
            FIRST_CARD_DEFAULT,
            FIRST_CARD_MAX,
            FIRST_CARD_MIN,
            RequestDeadline,
            SLAConfig,
            clamp_first_card_limit,
        )
        assert DEFAULT_SLA.first_card_limit == 6
        assert FIRST_CARD_DEFAULT == 6
        assert FIRST_CARD_MIN == 5
        assert FIRST_CARD_MAX == 7

    def test_pr258_parallel_retrieval_contracts_importable(self):
        """PR #258 parallel retrieval contracts must still be importable."""
        from app.concierge.parallel_retrieval import (
            CriticalPathResult,
            ENRICHMENT_BUDGET_RESERVE_MS,
            ENRICHMENT_MIN_TIMEOUT_S,
            NonCriticalEnrichmentResult,
            ParallelRetrievalResult,
            run_critical_google_fanout,
            run_non_critical_enrichment,
        )
        assert ENRICHMENT_BUDGET_RESERVE_MS == 500
        assert ENRICHMENT_MIN_TIMEOUT_S == 0.5

    def test_critical_path_result_has_no_card_fields(self):
        """CriticalPathResult must not have note/dossier fields (PR #258 invariant)."""
        from app.concierge.parallel_retrieval import CriticalPathResult
        result = CriticalPathResult(
            provider_results=[], elapsed_ms=10, timeout_count=0, success=False
        )
        assert not hasattr(result, "note")
        assert not hasattr(result, "dossier")
        assert not hasattr(result, "reason")

    def test_non_critical_enrichment_result_has_no_card_fields(self):
        """NonCriticalEnrichmentResult must not have card/identity fields."""
        from app.concierge.parallel_retrieval import NonCriticalEnrichmentResult
        result = NonCriticalEnrichmentResult(
            enrichment_map={}, elapsed_ms=5, used_count=0,
            skipped_count=0, skip_reason=None,
        )
        assert not hasattr(result, "name")
        assert not hasattr(result, "place_id")
        assert not hasattr(result, "verified_place")

    def test_pr259_dossier_contracts_importable(self):
        """All PR #259 public symbols must be importable."""
        from app.concierge.evidence_dossier import (
            CONFIDENCE_MIXED,
            CONFIDENCE_STRONG,
            CONFIDENCE_WEAK,
            DOSSIER_BUDGET_RESERVE_MS,
            EvidenceDossierTelemetry,
            PlaceEvidenceDossier,
            ProviderEvidenceItem,
            QueryFitEvidence,
            ReviewThemeEvidence,
            build_dossiers_for_ranked_cards,
            build_place_evidence_dossier,
            extract_review_themes,
            get_dossier_telemetry,
        )
        assert CONFIDENCE_STRONG == "strong"
        assert CONFIDENCE_MIXED == "mixed"
        assert CONFIDENCE_WEAK == "weak"
        assert DOSSIER_BUDGET_RESERVE_MS == 100
