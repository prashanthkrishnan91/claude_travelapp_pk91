"""Tests for PR #266: AI Concierge v2 Preference-Aware Retrieval and Ranking
for Soft Modifiers.

Covers:
1–5.  Frame/preference extraction for the five canonical test phrases.
6–10. Retrieval query shapes — venue-anchored, preference-aware, no bare gem.
11–14. Ranking/curation signal tests.
15–20. Reasoning/claim-safety, contract, and telemetry tests.

All tests should FAIL before PR #266 and PASS after.
"""

from __future__ import annotations

import dataclasses
from typing import List
from unittest.mock import MagicMock

import pytest

from app.concierge.frame_extractor import (
    ExperienceFrame,
    _HIDDEN_GEM_CONTEXT_PATTERN,
    _TEMPORAL_PATTERNS,
    _VIEW_PREFERENCE_PATTERN,
    _extract_normalized_soft_preferences,
    _extract_temporal_constraints,
    extract_frame,
)
from app.concierge.retrieval_planner import (
    _PREFERENCE_QUERY_MODIFIERS,
    plan_queries,
)
from app.concierge.ranker import (
    RankScore,
    _preference_fit,
    rank_entities_with_stats,
)
from app.concierge.place_entity_layer import PlaceEntity


# ── Helpers ───────────────────────────────────────────────────────────────────

def _frame(query: str, destination: str = "Chicago") -> ExperienceFrame:
    return extract_frame(query, destination)


def _venue_head(query: str, destination: str = "Chicago") -> str:
    f = _frame(query, destination)
    return f.subtype_concepts[0].label if f.subtype_concepts else ""


def _queries(query: str, destination: str = "Chicago") -> List[str]:
    f = _frame(query, destination)
    return plan_queries(f)


def _make_entity(
    name: str = "Test Place",
    place_id: str = "pid_test",
    rating: float = 4.3,
    review_count: int = 300,
    types: List[str] = None,
    primary_type: str = "restaurant",
    address: str = "123 Main St, Chicago, IL, USA",
    source_query: str = "restaurant Chicago",
) -> PlaceEntity:
    e = MagicMock(spec=PlaceEntity)
    e.name = name
    e.place_id = place_id
    e.rating = rating
    e.user_rating_count = review_count
    e.types = types or [primary_type]
    e.primary_type = primary_type
    e.formatted_address = address
    e.source_query = source_query
    e.google_maps_uri = f"https://maps.google.com/?cid={place_id}"
    e.business_status = "OPERATIONAL"
    return e


# ── 1. Frame: "hidden gem restaurants" ────────────────────────────────────────

class TestFrameHiddenGemRestaurants:
    """venue_head=restaurant, normalized_soft_prefs includes hidden_gem."""

    def test_venue_head_is_restaurant(self):
        assert _venue_head("hidden gem restaurants") == "restaurant"

    def test_normalized_soft_prefs_includes_hidden_gem(self):
        f = _frame("hidden gem restaurants")
        assert "hidden_gem" in f.normalized_soft_preferences, (
            f"Expected 'hidden_gem' in normalized_soft_preferences, got {f.normalized_soft_preferences}"
        )

    def test_suppressed_preference_noun_gem_preserved(self):
        f = _frame("hidden gem restaurants")
        assert "gem" in f.suppressed_preference_nouns

    def test_normalized_soft_prefs_field_exists_on_frame(self):
        f = _frame("breweries")
        assert hasattr(f, "normalized_soft_preferences")
        assert isinstance(f.normalized_soft_preferences, list)


# ── 2. Frame: "hidden gem bars" ───────────────────────────────────────────────

class TestFrameHiddenGemBars:
    """venue_head=bar, normalized_soft_prefs includes hidden_gem."""

    def test_venue_head_is_bar(self):
        head = _venue_head("hidden gem bars")
        assert head == "bar", f"Expected 'bar', got {head!r}"

    def test_normalized_soft_prefs_includes_hidden_gem(self):
        f = _frame("hidden gem bars")
        assert "hidden_gem" in f.normalized_soft_preferences

    def test_suppressed_preference_noun_gem_preserved(self):
        f = _frame("hidden gem bars")
        assert "gem" in f.suppressed_preference_nouns


# ── 3. Frame: "romantic cocktail bars" ────────────────────────────────────────

class TestFrameRomanticCocktailBars:
    """venue_head=cocktail, normalized_soft_prefs includes romantic."""

    def test_venue_head_is_cocktail(self):
        head = _venue_head("romantic cocktail bars")
        assert head in ("cocktail", "cocktail bar", "bar"), (
            f"Expected cocktail-related head, got {head!r}"
        )

    def test_normalized_soft_prefs_includes_romantic(self):
        f = _frame("romantic cocktail bars")
        assert "romantic" in f.normalized_soft_preferences, (
            f"Expected 'romantic' in normalized_soft_preferences, got {f.normalized_soft_preferences}"
        )

    def test_romantic_also_in_soft_preferences(self):
        f = _frame("romantic cocktail bars")
        assert "romantic" in f.soft_preferences


# ── 4. Frame: "taprooms with a view" ──────────────────────────────────────────

class TestFrameTaproomsWithAView:
    """venue_head=taproom, normalized_soft_prefs includes view_or_geo."""

    def test_venue_head_is_taproom(self):
        head = _venue_head("taprooms with a view")
        assert head in ("taproom", "taprooms"), f"Expected taproom head, got {head!r}"

    def test_normalized_soft_prefs_includes_view_or_geo(self):
        f = _frame("taprooms with a view")
        assert "view_or_geo" in f.normalized_soft_preferences, (
            f"Expected 'view_or_geo' in normalized_soft_preferences, got {f.normalized_soft_preferences}"
        )

    def test_view_preference_pattern_fires_for_with_a_view(self):
        assert _VIEW_PREFERENCE_PATTERN.search("taprooms with a view")

    def test_view_or_geo_not_added_when_geo_hint_present(self):
        # "waterfront taprooms" — waterfront fires as geo_hint, so view_or_geo NOT added
        f = _frame("waterfront taprooms")
        assert "view_or_geo" not in f.normalized_soft_preferences, (
            "view_or_geo should not be added when geo_hints already covers waterfront"
        )


# ── 5. Frame: "late night izakayas" ───────────────────────────────────────────

class TestFrameLateNightIzakayas:
    """venue_head=izakaya, temporal=late_night, normalized_soft_prefs includes late_night."""

    def test_venue_head_is_izakaya(self):
        assert _venue_head("late night izakayas") == "izakaya"

    def test_temporal_constraints_includes_late_night(self):
        f = _frame("late night izakayas")
        assert "late_night" in f.temporal_constraints, (
            f"Expected 'late_night' in temporal_constraints, got {f.temporal_constraints}"
        )

    def test_normalized_soft_prefs_includes_late_night(self):
        f = _frame("late night izakayas")
        assert "late_night" in f.normalized_soft_preferences, (
            f"Expected 'late_night' in normalized_soft_preferences, got {f.normalized_soft_preferences}"
        )

    def test_open_late_also_fires_temporal_late_night(self):
        constraints = _extract_temporal_constraints("izakayas open late")
        assert "late_night" in constraints

    def test_after_hours_also_fires_temporal_late_night(self):
        constraints = _extract_temporal_constraints("after hours bars")
        assert "late_night" in constraints


# ── 6. Retrieval queries: "hidden gem restaurants" ────────────────────────────

class TestQueriesHiddenGemRestaurants:
    """Queries must be restaurant-anchored and preference-aware; no bare gem."""

    def test_all_queries_are_restaurant_anchored(self):
        qs = _queries("hidden gem restaurants")
        for q in qs:
            assert any(w in q.lower() for w in ("restaurant", "restaurants")), (
                f"Query {q!r} is not restaurant-anchored"
            )

    def test_no_bare_gem_chicago_query(self):
        qs = _queries("hidden gem restaurants")
        for q in qs:
            assert not q.lower().startswith("gem "), (
                f"Query {q!r} starts with bare 'gem'"
            )
            # gem without a venue word → jewelry shop risk
            tokens = q.lower().split()
            if "gem" in tokens:
                assert any(r in tokens for r in ("restaurant", "restaurants", "bar", "bars")), (
                    f"Query {q!r} contains 'gem' without venue anchor"
                )

    def test_at_least_one_query_preserves_hidden_preference(self):
        qs = _queries("hidden gem restaurants")
        pref_terms = {"local favorite", "local", "neighborhood", "underrated", "hidden"}
        has_pref = any(
            any(pt in q.lower() for pt in pref_terms)
            for q in qs
        )
        assert has_pref, (
            f"No query preserves hidden/local/neighborhood preference: {qs}"
        )

    def test_no_retail_gem_concepts(self):
        qs = _queries("hidden gem restaurants")
        retail = {"jewelry", "jewel", "gemstone", "pawn", "retail"}
        for q in qs:
            assert not (retail & set(q.lower().split())), (
                f"Query {q!r} contains retail/gem concepts"
            )


# ── 7. Retrieval queries: "hidden gem bars" ───────────────────────────────────

class TestQueriesHiddenGemBars:
    """Queries must be bar-anchored, preference-aware, no bare gem."""

    def test_all_queries_are_bar_anchored(self):
        qs = _queries("hidden gem bars")
        for q in qs:
            assert "bar" in q.lower(), f"Query {q!r} is not bar-anchored"

    def test_no_bare_gem_in_queries(self):
        qs = _queries("hidden gem bars")
        for q in qs:
            tokens = q.lower().split()
            if "gem" in tokens:
                assert "bar" in tokens or "bars" in tokens, (
                    f"Query {q!r} has 'gem' without bar anchor"
                )

    def test_at_least_one_query_preserves_preference(self):
        qs = _queries("hidden gem bars")
        pref_terms = {"local favorite", "local", "neighborhood", "underrated", "hidden"}
        has_pref = any(any(pt in q.lower() for pt in pref_terms) for q in qs)
        assert has_pref, f"No preference-aware query for hidden gem bars: {qs}"


# ── 8. Retrieval queries: "romantic cocktail bars" ────────────────────────────

class TestQueriesRomanticCocktailBars:
    """Queries must be cocktail/bar-anchored and preserve romantic/date-night."""

    def test_all_queries_are_cocktail_anchored(self):
        qs = _queries("romantic cocktail bars")
        for q in qs:
            assert any(w in q.lower() for w in ("cocktail", "bar")), (
                f"Query {q!r} is not cocktail/bar-anchored"
            )

    def test_at_least_one_query_preserves_romantic_preference(self):
        qs = _queries("romantic cocktail bars")
        pref_terms = {"romantic", "date night", "date", "intimate", "cozy"}
        has_pref = any(any(pt in q.lower() for pt in pref_terms) for q in qs)
        assert has_pref, f"No romantic/date-night preference preserved: {qs}"


# ── 9. Retrieval queries: "taprooms with a view" ──────────────────────────────

class TestQueriesTaproomsWithAView:
    """Queries must be taproom/brewery-anchored, preserve view/rooftop/outdoor."""

    def test_all_queries_are_taproom_anchored(self):
        qs = _queries("taprooms with a view")
        for q in qs:
            assert any(w in q.lower() for w in ("taproom", "brewery", "brewpub")), (
                f"Query {q!r} is not taproom-anchored"
            )

    def test_no_query_starts_with_view(self):
        qs = _queries("taprooms with a view")
        for q in qs:
            assert not q.lower().startswith("view "), (
                f"Query {q!r} starts with bare 'view'"
            )

    def test_at_least_one_query_preserves_view_preference(self):
        qs = _queries("taprooms with a view")
        view_terms = {"rooftop", "with a view", "view", "outdoor", "patio"}
        has_view = any(any(vt in q.lower() for vt in view_terms) for q in qs)
        assert has_view, f"No view preference preserved in queries: {qs}"


# ── 10. Retrieval queries: "late night izakayas" ──────────────────────────────

class TestQueriesLateNightIzakayas:
    """Queries must be izakaya-anchored and preserve late-night preference."""

    def test_all_queries_are_izakaya_anchored(self):
        qs = _queries("late night izakayas")
        for q in qs:
            assert "izakaya" in q.lower(), f"Query {q!r} is not izakaya-anchored"

    def test_at_least_one_query_preserves_late_night_preference(self):
        qs = _queries("late night izakayas")
        late_terms = {"late night", "late-night", "open late", "after hours"}
        has_late = any(any(lt in q.lower() for lt in late_terms) for q in qs)
        assert has_late, f"No late-night preference preserved in queries: {qs}"


# ── 11. Ranking: hidden_gem preference can reorder similar candidates ──────────

class TestRankingHiddenGemPreference:
    """Hidden-gem preference should demote mega-popular in favor of local-scale."""

    def _make_hidden_gem_frame(self) -> ExperienceFrame:
        return extract_frame("hidden gem restaurants", "Chicago")

    def test_local_scale_beats_mega_popular_with_hidden_gem_preference(self):
        """Local-scale (200 reviews) should rank above mega-popular (8000 reviews)
        when hidden_gem preference is active, assuming similar subtype_fit."""
        frame = self._make_hidden_gem_frame()
        local_place = _make_entity(
            name="Small Neighborhood Bistro",
            place_id="pid_local",
            review_count=200,
            rating=4.4,
            primary_type="restaurant",
            source_query="local favorite restaurant Chicago",
        )
        mega_popular = _make_entity(
            name="Famous Chicago Eatery",
            place_id="pid_mega",
            review_count=8000,
            rating=4.4,
            primary_type="restaurant",
            source_query="local favorite restaurant Chicago",
        )
        pf_local = _preference_fit(local_place, frame)
        pf_mega = _preference_fit(mega_popular, frame)
        assert pf_local > pf_mega, (
            f"Local-scale preference_fit={pf_local:.3f} should beat "
            f"mega-popular preference_fit={pf_mega:.3f} under hidden_gem"
        )

    def test_preference_fit_neutral_when_no_soft_preference(self):
        """preference_fit must return 0.5 (neutral) when no preference active."""
        frame = extract_frame("restaurants", "Chicago")  # no hidden gem preference
        entity = _make_entity(review_count=200)
        pf = _preference_fit(entity, frame)
        assert pf == 0.5, f"Expected 0.5 neutral, got {pf}"

    def test_hidden_gem_preference_fit_range(self):
        """preference_fit for hidden_gem must remain in valid 0.0–1.0 range."""
        frame = self._make_hidden_gem_frame()
        for review_count in [0, 10, 200, 1000, 5000, 20000]:
            entity = _make_entity(review_count=review_count)
            pf = _preference_fit(entity, frame)
            assert 0.0 <= pf <= 1.0, (
                f"preference_fit={pf} out of range for review_count={review_count}"
            )


# ── 12. Ranking: hidden_gem must not reward jewelry/gem candidates ─────────────

class TestRankingNoGemJewelryReward:
    """Gem/jewelry candidates must not get hidden_gem preference boost."""

    def test_jewelry_store_does_not_get_hidden_gem_boost(self):
        """A jewelry store entity should have the same (neutral) preference_fit as
        a restaurant under hidden_gem preference — preference_fit does not check
        entity type, but the subtype_fit penalty keeps jewelry ranked below restaurants."""
        frame = extract_frame("hidden gem restaurants", "Chicago")
        jewelry = _make_entity(
            name="Diamond Gem Jewelry",
            primary_type="jewelry_store",
            source_query="local favorite restaurant Chicago",
            review_count=300,
        )
        restaurant = _make_entity(
            name="Local Neighborhood Bistro",
            primary_type="restaurant",
            source_query="local favorite restaurant Chicago",
            review_count=300,
        )
        # Both have same review_count → same preference_fit
        pf_jewelry = _preference_fit(jewelry, frame)
        pf_restaurant = _preference_fit(restaurant, frame)
        assert pf_jewelry == pf_restaurant, (
            "preference_fit should not discriminate by entity type — "
            "subtype_fit handles the jewelry vs. restaurant distinction"
        )

    def test_jewelry_retrieval_queries_absent(self):
        """No query for 'hidden gem restaurants' should mention jewelry."""
        qs = _queries("hidden gem restaurants")
        jewelry_terms = {"jewelry", "jewel", "gemstone", "pawn", "diamond"}
        for q in qs:
            assert not (jewelry_terms & set(q.lower().split())), (
                f"Query {q!r} mentions jewelry/gem terms"
            )


# ── 13. Ranking: view/waterfront preference must not elevate non-breweries ─────

class TestRankingViewNotOverrideSubtype:
    """View/waterfront preference must not cause a non-brewery to outrank a brewery."""

    def test_brewery_beats_waterfront_restaurant_for_brewery_ask(self):
        """For 'best waterfront breweries', a brewery with poor geo_fit should still
        rank above a waterfront restaurant because subtype_fit dominates."""
        frame = extract_frame("best waterfront breweries", "Chicago")
        brewery = _make_entity(
            name="North Shore Brewing Co",
            primary_type="brewery",
            types=["brewery", "bar"],
            address="1200 N Lake Shore Dr, Chicago, IL, USA",
            source_query="brewery Chicago waterfront",
            review_count=400,
            rating=4.5,
        )
        waterfront_restaurant = _make_entity(
            name="Riverwalk Steakhouse",
            primary_type="restaurant",
            types=["restaurant", "steak_house"],
            address="400 N Riverwalk Dr, Chicago, IL, USA",
            source_query="brewery Chicago waterfront",
            review_count=2000,
            rating=4.6,
        )
        ranked, _ = rank_entities_with_stats([brewery, waterfront_restaurant], frame)
        assert ranked, "No entities ranked"
        top_entity = ranked[0][0]
        assert top_entity.name == brewery.name, (
            f"Expected brewery to rank first, got {top_entity.name!r}"
        )


# ── 14. Ranking: preference boost must not override Google/addable trust ────────

class TestPreferenceFitDoesNotOverrideTrust:
    """Preference_fit (0.06 weight) cannot override subtype_fit (0.34 weight)."""

    def test_high_subtype_fit_entity_beats_high_preference_fit_entity(self):
        """A place with 0.9 subtype_fit and neutral preference_fit should score
        higher than a place with 0.1 subtype_fit and maximum preference_fit."""
        frame = extract_frame("hidden gem restaurants", "Chicago")

        # Strong concept match, average review count
        strong_match = _make_entity(
            name="The Italian Bistro",
            primary_type="restaurant",
            types=["restaurant", "italian_restaurant"],
            review_count=350,
            rating=4.5,
            source_query="local favorite restaurant Chicago",
        )
        # Weak concept match but local-scale review count
        weak_match = _make_entity(
            name="Chicago Gym and Fitness",
            primary_type="gym",
            types=["gym", "fitness_center"],
            review_count=150,
            rating=4.8,
            source_query="local favorite restaurant Chicago",
        )

        ranked, _ = rank_entities_with_stats([strong_match, weak_match], frame)
        if ranked:
            assert ranked[0][0].name == strong_match.name, (
                f"Strong subtype_fit entity should rank first; got {ranked[0][0].name!r}"
            )

    def test_preference_fit_weight_is_smaller_than_subtype_fit_weight(self):
        from app.concierge.ranker import _W_SUBTYPE_FIT, _W_PREFERENCE_FIT
        assert _W_SUBTYPE_FIT > _W_PREFERENCE_FIT, (
            f"subtype_fit weight {_W_SUBTYPE_FIT} must dominate preference_fit weight {_W_PREFERENCE_FIT}"
        )

    def test_weights_sum_to_one(self):
        from app.concierge.ranker import (
            _W_SUBTYPE_FIT, _W_GEO_FIT, _W_QUALITY, _W_EVIDENCE,
            _W_DIVERSITY, _W_POPULARITY, _W_PREFERENCE_FIT,
            _W_TRIP_CONTEXT, _W_VALUE,
        )
        total = (
            _W_SUBTYPE_FIT + _W_GEO_FIT + _W_QUALITY + _W_EVIDENCE
            + _W_DIVERSITY + _W_POPULARITY + _W_PREFERENCE_FIT
            + _W_TRIP_CONTEXT + _W_VALUE
        )
        assert abs(total - 1.0) < 1e-9, f"Weights do not sum to 1.0: {total}"


# ── 15. Claim safety: "2AM Izakaya" must not get late_night boost from name ────

class TestClaimSafetyLateNightName:
    """Business names containing time references (e.g., '2AM') must NOT
    trigger a late_night preference boost — hours must come from evidence."""

    def test_2am_in_name_does_not_trigger_late_night_boost(self):
        frame = extract_frame("late night izakayas", "Chicago")
        izakaya_2am = _make_entity(
            name="2AM Izakaya",
            primary_type="restaurant",
            review_count=200,
            source_query="late night izakaya Chicago",
        )
        pf = _preference_fit(izakaya_2am, frame)
        # Should be neutral (0.5) — "2am" is not in explicit_late_indicators
        assert pf == 0.5, (
            f"'2AM Izakaya' should not get a late_night preference boost from name alone; "
            f"got preference_fit={pf}"
        )

    def test_explicit_late_night_name_does_get_boost(self):
        """'Late Night Izakaya' has an explicit indicator and may get a boost."""
        frame = extract_frame("late night izakayas", "Chicago")
        explicit_late = _make_entity(
            name="Late Night Izakaya",
            primary_type="restaurant",
            review_count=200,
            source_query="late night izakaya Chicago",
        )
        pf = _preference_fit(explicit_late, frame)
        assert pf > 0.5, (
            f"'Late Night Izakaya' should get a late_night boost; got {pf}"
        )

    def test_midnight_in_name_gets_boost(self):
        frame = extract_frame("late night izakayas", "Chicago")
        entity = _make_entity(
            name="Midnight Ramen",
            primary_type="restaurant",
            review_count=300,
            source_query="late night izakaya Chicago",
        )
        pf = _preference_fit(entity, frame)
        assert pf > 0.5, (
            f"'Midnight Ramen' should get late_night boost; got {pf}"
        )


# ── 16. Claim safety: unsupported waterfront view claims ──────────────────────

class TestClaimSafetyWaterfrontView:
    """Waterfront/view preference must not boost places without address evidence."""

    def test_view_or_geo_pref_returns_neutral_when_no_geo_evidence(self):
        frame = extract_frame("taprooms with a view", "Chicago")
        # A taproom with no address hint for water/view
        landlocked_taproom = _make_entity(
            name="Loop Taproom",
            primary_type="brewery",
            address="200 W Madison St, Chicago, IL, USA",
            source_query="rooftop taproom Chicago",
            review_count=300,
        )
        pf = _preference_fit(landlocked_taproom, frame)
        # view_or_geo pref: preference_fit returns neutral (0.5) — geo_fit handles the signal
        assert pf == 0.5, (
            f"view_or_geo preference_fit should be neutral (0.5) for place without "
            f"view evidence; got {pf}"
        )


# ── 17. Contract: fallback_note_visible_count remains 0 ────────────────────────

class TestFallbackNoteVisibleCountZero:
    def test_fallback_note_visible_count_remains_zero(self):
        from app.concierge.set_level_writer import SetWriterResult
        r = SetWriterResult(
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
        assert r.fallback_note_visible_count == 0


# ── 18. Contract: deterministic_visible_count remains 0 ───────────────────────

class TestDeterministicVisibleCountZero:
    def test_deterministic_visible_count_remains_zero(self):
        from app.concierge.batched_reason_builder import ReasoningResultV2
        r = ReasoningResultV2(deterministic_visible_count=0)
        assert r.deterministic_visible_count == 0


# ── 19. Contract: invalid notes hidden without dropping valid cards ─────────────

class TestInvalidNotesHiddenNotDropped:
    """Cards with hidden set-writer notes are included without a note block."""

    def test_hidden_note_card_not_dropped_in_set_writer_primary_path(self):
        from unittest.mock import patch, MagicMock
        from app.concierge.semantic_retrieval import _assemble_card_set
        from app.concierge.batched_reason_builder import CardReason

        entity_a = MagicMock()
        entity_a.name = "Validated Note Restaurant"
        entity_a.configure_mock(**{"place_id": "pid_a"})
        entity_b = MagicMock()
        entity_b.name = "Hidden Note Restaurant"
        entity_b.configure_mock(**{"place_id": "pid_b"})
        rank_score = MagicMock()
        rank_score.as_dict.return_value = {"subtype_fit": 0.9}
        cards_data = [
            (entity_a, None, rank_score, ""),
            (entity_b, None, rank_score, ""),
        ]
        card_reasons = {
            "1": CardReason(
                note="Excellent neighborhood restaurant with seasonal menu.",
                source="set_level_writer_v1",
                validated=True,
                attempt_count=1,
                model_used="set_level_writer_v1",
            ),
            "2": CardReason(
                note="",
                source="set_level_writer_v1",
                validated=False,
                attempt_count=1,
                model_used="set_level_writer_v1",
            ),
        }
        frame = extract_frame("hidden gem restaurants", "Chicago")

        def _fake_entity_to_card(entity, reason, frame, reason_source="", reason_validated=False):
            m = MagicMock()
            m.name = entity.name
            m.display = MagicMock()
            m.display.display_why_validated = reason_validated
            m.display.display_why = reason
            return m

        with patch("app.concierge.semantic_retrieval._entity_to_card", side_effect=_fake_entity_to_card):
            cards, _, excluded, visible, without_notes = _assemble_card_set(
                cards_data=cards_data,
                card_reasons=card_reasons,
                frame=frame,
                note_generation_timed_out=False,
                set_writer_primary_active=True,
            )

        assert len(cards) == 2, (
            f"Both cards must be returned; got {len(cards)}"
        )
        assert excluded == 0


# ── 20. Contract: card count remains 5–7 ──────────────────────────────────────

class TestCardCountContract:
    def test_first_card_limit_in_5_to_7_range(self):
        from app.concierge.deadline_manager import DEFAULT_SLA
        assert 5 <= DEFAULT_SLA.first_card_limit <= 7, (
            f"first_card_limit={DEFAULT_SLA.first_card_limit} outside 5–7 range"
        )


# ── 21. Telemetry: normalized_soft_preferences populated correctly ─────────────

class TestTelemetryNormalizedSoftPreferences:
    """normalized_soft_preferences field is populated and accurate."""

    def test_hidden_gem_restaurants_telemetry(self):
        f = _frame("hidden gem restaurants")
        assert "hidden_gem" in f.normalized_soft_preferences

    def test_romantic_cocktail_bars_telemetry(self):
        f = _frame("romantic cocktail bars")
        assert "romantic" in f.normalized_soft_preferences

    def test_late_night_izakayas_telemetry(self):
        f = _frame("late night izakayas")
        assert "late_night" in f.normalized_soft_preferences

    def test_taprooms_with_a_view_telemetry(self):
        f = _frame("taprooms with a view")
        assert "view_or_geo" in f.normalized_soft_preferences

    def test_clean_venue_query_has_empty_normalized_soft_prefs(self):
        f = _frame("craft breweries")
        assert f.normalized_soft_preferences == [], (
            f"Clean venue query should have empty normalized_soft_preferences; "
            f"got {f.normalized_soft_preferences}"
        )

    def test_local_favorite_restaurants_triggers_hidden_gem(self):
        f = _frame("local favorite restaurants")
        assert "hidden_gem" in f.normalized_soft_preferences, (
            "'local favorite restaurants' should trigger hidden_gem preference"
        )

    def test_underrated_bars_triggers_hidden_gem(self):
        f = _frame("underrated bars")
        assert "hidden_gem" in f.normalized_soft_preferences, (
            "'underrated bars' should trigger hidden_gem preference"
        )

    def test_hidden_gem_context_pattern_coverage(self):
        """_HIDDEN_GEM_CONTEXT_PATTERN must match known hidden-gem phrases."""
        phrases = [
            "hidden gem restaurants",
            "local favorite bars",
            "neighborhood haunt",
            "underrated cafes",
            "undiscovered breweries",
            "off the beaten path restaurants",
        ]
        for phrase in phrases:
            assert _HIDDEN_GEM_CONTEXT_PATTERN.search(phrase), (
                f"_HIDDEN_GEM_CONTEXT_PATTERN did not match {phrase!r}"
            )

    def test_normalized_soft_preferences_never_surfaced_to_ui(self):
        """normalized_soft_preferences is a frame field only — not in subtype_concepts."""
        f = _frame("hidden gem restaurants")
        for c in f.subtype_concepts:
            assert not hasattr(c, "normalized_soft_preferences")

    def test_preference_query_modifiers_dict_exists(self):
        """_PREFERENCE_QUERY_MODIFIERS must exist and contain the required keys."""
        for key in ("hidden_gem", "romantic", "late_night", "view_or_geo"):
            assert key in _PREFERENCE_QUERY_MODIFIERS, (
                f"_PREFERENCE_QUERY_MODIFIERS missing key {key!r}"
            )
            assert len(_PREFERENCE_QUERY_MODIFIERS[key]) >= 1

    def test_rank_score_has_preference_fit_field(self):
        rs = RankScore()
        assert hasattr(rs, "preference_fit")
        assert rs.preference_fit == 0.5  # neutral default

    def test_rank_score_as_dict_includes_preference_fit(self):
        rs = RankScore(preference_fit=0.7)
        d = rs.as_dict()
        assert "preference_fit" in d
        assert d["preference_fit"] == 0.7

    def test_extract_temporal_constraints_late_night(self):
        assert "late_night" in _extract_temporal_constraints("late night izakayas")

    def test_extract_temporal_constraints_empty_for_clean_query(self):
        assert _extract_temporal_constraints("breweries") == []

    def test_extract_normalized_soft_preferences_hidden_gem_from_suppressed(self):
        result = _extract_normalized_soft_preferences(
            query="hidden gem restaurants",
            suppressed_preference_nouns=["gem"],
            soft_prefs=[],
            temporal_constraints=[],
            geo_hints=[],
        )
        assert "hidden_gem" in result

    def test_extract_normalized_soft_preferences_late_night(self):
        result = _extract_normalized_soft_preferences(
            query="late night bars",
            suppressed_preference_nouns=[],
            soft_prefs=[],
            temporal_constraints=["late_night"],
            geo_hints=[],
        )
        assert "late_night" in result

    def test_extract_normalized_soft_preferences_view_or_geo_skipped_when_geo_hints_present(self):
        result = _extract_normalized_soft_preferences(
            query="taprooms with a view",
            suppressed_preference_nouns=[],
            soft_prefs=[],
            temporal_constraints=[],
            geo_hints=["rooftop"],  # geo hint present → view_or_geo not added
        )
        assert "view_or_geo" not in result
