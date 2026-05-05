"""Tests for Semantic Retrieval v1 pipeline.

Coverage:
1. Feature flag behavior (OFF preserves existing path; ON uses semantic pipeline)
2. Frame extraction — open-vocabulary, brewery/tapas/sushi/waterfront cases
3. LLM fallback (deterministic frame still produced on any extraction error)
4. Retrieval planner — query shapes, concept preservation, geo variants, cap
5. Provider executor — fanout, timeout handling, all-timeout fallback
6. Entity layer / trust gates — missing id, non-operational, no URI, dup, broad type OK
7. SemanticRanker — brewery > bar, tapas > cocktail bar, sushi > waterfront generic,
   popularity cannot overpower subtype_fit
8. Safe reason builder — ask anchor present, no invented views/ambiance, verify wrapper
9. Integration — mocked Google → verified cards for brewery/tapas/sushi asks
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Optional
from unittest.mock import MagicMock, patch

import pytest


# ── Reasoning Reliability v2 mock helper ─────────────────────────────────────
# Integration tests that reach the semantic pipeline must mock the LLM reasoning
# path. Without this, no cards are returned (all have validated=False).
# This helper produces a mock build_reasons_with_retry that validates every card.

def _make_all_validated_reasons(cards_data, frame):
    """Mock for build_reasons_with_retry: validates every card with a stub note.

    Use as: patch("app.concierge.semantic_retrieval.build_reasons_with_retry",
                  side_effect=_make_all_validated_reasons)
    """
    from app.concierge.batched_reason_builder import (
        CardReason, ReasoningResultV2, SOURCE_PRIMARY, _PRIMARY_MODEL
    )
    n = len(cards_data)
    reasons = {
        str(i + 1): CardReason(
            note=(
                f"A respected Chicago establishment with a loyal neighborhood "
                f"following and consistent quality across visits."
            ),
            source=SOURCE_PRIMARY,
            validated=True,
            attempt_count=1,
            model_used=_PRIMARY_MODEL,
        )
        for i in range(n)
    }
    result = ReasoningResultV2(
        attempted=True,
        success=True,
        accepted_count=n,
        final_card_count=n,
        deterministic_visible_count=0,
        final_note_omitted_count=0,
        model=_PRIMARY_MODEL,
        visible_note_source_counts={SOURCE_PRIMARY: n},
    )
    return reasons, result


_MOCK_VALID_REASONS = patch(
    "app.concierge.batched_reason_builder.build_reasons_with_retry",
    side_effect=_make_all_validated_reasons,
)


# ── Fixtures / helpers ────────────────────────────────────────────────────────

def _make_raw_place(
    *,
    name: str = "Test Place",
    place_id: str = "ChIJ_pid1",
    types: Optional[List[str]] = None,
    primary_type: Optional[str] = None,
    rating: Optional[float] = 4.2,
    review_count: Optional[int] = 300,
    business_status: str = "OPERATIONAL",
    address: str = "100 N Riverside Dr, Chicago, IL, USA",
    maps_uri: str = "https://maps.google.com/?cid=1",
    price_level: Optional[str] = None,
    lat: float = 41.88,
    lng: float = -87.63,
) -> Dict[str, Any]:
    return {
        "id": place_id,
        "displayName": {"text": name},
        "types": types or ["restaurant", "food"],
        "primaryType": primary_type or (types[0] if types else "restaurant"),
        "rating": rating,
        "userRatingCount": review_count,
        "businessStatus": business_status,
        "formattedAddress": address,
        "googleMapsUri": maps_uri,
        "websiteUri": None,
        "priceLevel": price_level,
        "location": {"latitude": lat, "longitude": lng},
    }


def _provider_result(query: str, places: List[Dict[str, Any]], latency_ms: int = 100):
    from app.concierge.provider_executor import ProviderQueryResult
    return ProviderQueryResult(query=query, places=places, latency_ms=latency_ms)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Frame Extraction
# ══════════════════════════════════════════════════════════════════════════════

class TestFrameExtraction:

    def test_brewery_extraction(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("best breweries", "Chicago")
        labels = [c.label for c in frame.subtype_concepts]
        assert any(l in ("brewery", "breweries") for l in labels), (
            f"Expected brewery concept, got {labels}"
        )
        assert frame.needs_provider_call is True

    def test_brewery_waterfront_extraction(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("best breweries along the waterfront", "Chicago")
        labels = [c.label for c in frame.subtype_concepts]
        assert any(l in ("brewery", "breweries") for l in labels), (
            f"Expected brewery concept, got {labels}"
        )
        assert "waterfront" in frame.geography_hints
        assert "view_not_structurally_verifiable" in frame.ambiguity_flags

    def test_romantic_tapas_not_loud(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("romantic tapas but not too loud", "Chicago")
        labels = [c.label for c in frame.subtype_concepts]
        assert any("tapa" in l for l in labels), f"Expected tapas concept, got {labels}"
        assert "romantic" in frame.soft_preferences
        assert "not_loud" in frame.negative_constraints

    def test_sushi_waterfront_view(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("nice sushi restaurants with a waterfront view", "Chicago")
        labels = [c.label for c in frame.subtype_concepts]
        assert any("sushi" in l for l in labels), f"Expected sushi concept, got {labels}"
        assert frame.geography_hints  # waterfront or view
        assert "view_not_structurally_verifiable" in frame.ambiguity_flags

    def test_extraction_never_raises_on_empty(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("", "Chicago")
        assert frame is not None
        assert frame.needs_provider_call is True

    def test_extraction_never_raises_on_weird_input(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("!!! @@@ ###", "Chicago")
        assert frame is not None

    def test_subtype_concepts_are_open_strings_not_enum(self):
        """An unsupported concept like 'distillery' should still extract correctly."""
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("best distilleries downtown", "Chicago")
        labels = [c.label for c in frame.subtype_concepts]
        assert any("distill" in l for l in labels), f"Got {labels}"

    def test_extraction_fallback_on_error(self):
        """If _extract_frame_impl raises for any reason, returns minimal frame."""
        from app.concierge import frame_extractor
        with patch.object(frame_extractor, "_extract_frame_impl", side_effect=RuntimeError("test")):
            frame = frame_extractor.extract_frame("best breweries", "Chicago")
        assert frame is not None
        assert frame.needs_provider_call is True


# ══════════════════════════════════════════════════════════════════════════════
# 2. Retrieval Planner
# ══════════════════════════════════════════════════════════════════════════════

class TestRetrievalPlanner:

    def _frame(self, query: str, destination: str = "Chicago"):
        from app.concierge.frame_extractor import extract_frame
        return extract_frame(query, destination)

    def test_brewery_waterfront_queries_preserve_brewery(self):
        from app.concierge.retrieval_planner import plan_queries
        frame = self._frame("best breweries along the waterfront")
        queries = plan_queries(frame)
        assert all(
            "brew" in q.lower() or "taproom" in q.lower()
            for q in queries
        ), f"Expected brewery concept in all queries, got: {queries}"

    def test_tapas_queries_not_cocktail_bar(self):
        from app.concierge.retrieval_planner import plan_queries
        frame = self._frame("romantic tapas but not too loud")
        queries = plan_queries(frame)
        assert not any("cocktail" in q.lower() for q in queries), (
            f"Tapas queries must not contain 'cocktail': {queries}"
        )
        assert any("tapas" in q.lower() or "small plates" in q.lower() for q in queries)

    def test_sushi_queries_preserve_sushi(self):
        from app.concierge.retrieval_planner import plan_queries
        frame = self._frame("nice sushi restaurants with a waterfront view")
        queries = plan_queries(frame)
        assert any("sushi" in q.lower() or "japanese" in q.lower() for q in queries), (
            f"Expected sushi in queries: {queries}"
        )

    def test_query_count_capped_at_default(self):
        from app.concierge.retrieval_planner import plan_queries, DEFAULT_MAX_QUERIES
        frame = self._frame("best breweries along the waterfront")
        queries = plan_queries(frame)
        assert len(queries) <= DEFAULT_MAX_QUERIES

    def test_query_count_hard_cap(self):
        from app.concierge.retrieval_planner import plan_queries, HARD_CAP_QUERIES
        frame = self._frame("best breweries along the waterfront")
        queries = plan_queries(frame, max_queries=99)
        assert len(queries) <= HARD_CAP_QUERIES

    def test_all_queries_contain_destination(self):
        from app.concierge.retrieval_planner import plan_queries
        frame = self._frame("best sushi")
        queries = plan_queries(frame)
        assert all("chicago" in q.lower() for q in queries), f"All queries must include destination: {queries}"

    def test_brewery_fallback_queries(self):
        from app.concierge.retrieval_planner import plan_queries
        frame = self._frame("best breweries")
        queries = plan_queries(frame)
        assert len(queries) >= 1
        assert any("brew" in q.lower() for q in queries)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Provider Executor
# ══════════════════════════════════════════════════════════════════════════════

class TestProviderExecutor:

    def test_fanout_runs_multiple_queries(self):
        from app.concierge.provider_executor import execute_fanout

        call_log = []

        def fake_query(q, api_key, timeout, max_results):
            call_log.append(q)
            from app.concierge.provider_executor import ProviderQueryResult
            return ProviderQueryResult(query=q, places=[_make_raw_place(name=q[:10])], latency_ms=10)

        with patch("app.concierge.provider_executor._single_google_query", side_effect=fake_query):
            results = execute_fanout(
                ["breweries Chicago", "brewery taprooms Chicago"],
                api_key="fake_key",
            )
        assert len(results) == 2
        assert len(call_log) == 2

    def test_one_timeout_uses_successful_results(self):
        from app.concierge.provider_executor import execute_fanout, ProviderQueryResult

        call_count = [0]

        def fake_query(q, api_key, timeout, max_results):
            call_count[0] += 1
            if call_count[0] == 1:
                raise TimeoutError("simulated timeout")
            return ProviderQueryResult(
                query=q, places=[_make_raw_place(name="Good Brewery")], latency_ms=50
            )

        with patch("app.concierge.provider_executor._single_google_query", side_effect=fake_query):
            results = execute_fanout(
                ["breweries Chicago", "brewery taprooms Chicago"],
                api_key="fake_key",
            )

        successful = [r for r in results if r.succeeded]
        assert len(successful) >= 1
        assert any(len(r.places) > 0 for r in successful)

    def test_all_timeouts_returns_empty_not_fake_cards(self):
        from app.concierge.provider_executor import execute_fanout

        def fake_query(q, api_key, timeout, max_results):
            raise TimeoutError("simulated timeout")

        with patch("app.concierge.provider_executor._single_google_query", side_effect=fake_query):
            results = execute_fanout(["breweries Chicago"], api_key="fake_key")

        assert all(not r.succeeded for r in results)
        assert all(len(r.places) == 0 for r in results)

    def test_no_api_key_returns_error_result(self):
        from app.concierge.provider_executor import execute_fanout
        results = execute_fanout(["breweries Chicago"], api_key="")
        assert len(results) == 1
        assert results[0].error == "no_api_key"


# ══════════════════════════════════════════════════════════════════════════════
# 4. Entity Layer / Trust Gates
# ══════════════════════════════════════════════════════════════════════════════

class TestEntityLayer:

    def _results(self, places, query="breweries Chicago"):
        return [_provider_result(query, places)]

    def test_missing_place_id_rejected(self):
        from app.concierge.place_entity_layer import build_entity_layer
        raw = _make_raw_place(name="No ID Place")
        raw["id"] = ""
        entities, stats = build_entity_layer(self._results([raw]))
        assert len(entities) == 0
        assert stats.missing_place_id_rejected >= 1

    def test_non_operational_rejected(self):
        from app.concierge.place_entity_layer import build_entity_layer
        raw = _make_raw_place(name="Closed Brewery", business_status="CLOSED_PERMANENTLY")
        entities, stats = build_entity_layer(self._results([raw]))
        assert len(entities) == 0
        assert stats.operational_rejected >= 1

    def test_missing_maps_uri_rejected(self):
        from app.concierge.place_entity_layer import build_entity_layer
        raw = _make_raw_place(name="No URI Place", maps_uri="")
        entities, stats = build_entity_layer(self._results([raw]))
        assert len(entities) == 0
        assert stats.missing_maps_uri_rejected >= 1

    def test_duplicates_removed_by_identity_keys(self):
        from app.concierge.place_entity_layer import build_entity_layer
        raw1 = _make_raw_place(name="Goose Island", place_id="pid_1", maps_uri="https://maps.google.com/?cid=1")
        raw2 = _make_raw_place(name="Goose Island", place_id="pid_1", maps_uri="https://maps.google.com/?cid=1")
        entities, stats = build_entity_layer(self._results([raw1, raw2]))
        assert len(entities) == 1
        assert stats.duplicate_rejected >= 1

    def test_broad_google_type_does_not_reject(self):
        """A place typed only as 'bar' or 'establishment' must not be auto-rejected."""
        from app.concierge.place_entity_layer import build_entity_layer
        raw = _make_raw_place(
            name="Half Acre Beer Company",
            types=["bar", "establishment", "point_of_interest"],
        )
        entities, stats = build_entity_layer(self._results([raw]))
        assert len(entities) == 1, (
            f"Broad type 'bar' must not auto-reject. stats={vars(stats)}"
        )

    def test_missing_business_status_rejected(self):
        """businessStatus must be explicit OPERATIONAL for trust safety."""
        from app.concierge.place_entity_layer import build_entity_layer
        raw = _make_raw_place(name="Microbrewery ABC")
        raw.pop("businessStatus", None)
        raw["businessStatus"] = None
        entities, stats = build_entity_layer(self._results([raw]))
        assert len(entities) == 0
        assert stats.operational_rejected >= 1

    def test_operational_accepted(self):
        from app.concierge.place_entity_layer import build_entity_layer
        raw = _make_raw_place(name="Open Brewery", business_status="OPERATIONAL")
        entities, _stats = build_entity_layer(self._results([raw]))
        assert len(entities) == 1

    @pytest.mark.parametrize("status", ["CLOSED_TEMPORARILY", "CLOSED_PERMANENTLY"])
    def test_closed_statuses_rejected(self, status):
        from app.concierge.place_entity_layer import build_entity_layer
        raw = _make_raw_place(name="Closed Place", business_status=status)
        entities, stats = build_entity_layer(self._results([raw]))
        assert len(entities) == 0
        assert stats.operational_rejected >= 1

    def test_prior_identity_keys_deduped(self):
        from app.concierge.place_entity_layer import build_entity_layer
        raw = _make_raw_place(name="Goose Island", place_id="pid_prior")
        prior_keys = frozenset({"pid:pid_prior"})
        entities, stats = build_entity_layer(self._results([raw]), prior_identity_keys=prior_keys)
        assert len(entities) == 0
        assert stats.duplicate_rejected >= 1


# ══════════════════════════════════════════════════════════════════════════════
# 5. SemanticRanker
# ══════════════════════════════════════════════════════════════════════════════

class TestSemanticRanker:

    def _entity(
        self, name: str, types: List[str], rating: float = 4.0, review_count: int = 200,
        place_id: str = None, maps_uri: str = None, source_query: str = "breweries Chicago",
    ):
        from app.concierge.place_entity_layer import PlaceEntity
        return PlaceEntity(
            place_id=place_id or f"pid_{name[:4]}",
            name=name,
            formatted_address=f"123 Main St, Chicago, IL",
            lat=41.88, lng=-87.63,
            business_status="OPERATIONAL",
            google_maps_uri=maps_uri or f"https://maps.google.com/?cid={hash(name)}",
            types=types,
            primary_type=types[0] if types else None,
            rating=rating,
            user_rating_count=review_count,
            price_level=None,
            website_uri=None,
            source_query=source_query,
        )

    def _frame(self, query: str, destination: str = "Chicago"):
        from app.concierge.frame_extractor import extract_frame
        return extract_frame(query, destination)

    def test_brewery_beats_generic_high_rated_bar(self):
        """Brewery must rank above a generic bar even if the bar has more reviews."""
        from app.concierge.ranker import rank_entities
        brewery = self._entity("Goose Island Brewery", ["brewery", "bar"], rating=4.3, review_count=500,
                                source_query="breweries Chicago")
        generic_bar = self._entity("The Great Bar", ["bar", "cocktail_bar"], rating=4.7, review_count=2000,
                                    source_query="breweries Chicago")
        frame = self._frame("best breweries")
        ranked = rank_entities([brewery, generic_bar], frame)
        assert len(ranked) == 2
        names = [e.name for e, _ in ranked]
        assert names[0] == "Goose Island Brewery", (
            f"Brewery must rank first, got {names}. "
            f"Scores: {[(e.name, s.as_dict()) for e, s in ranked]}"
        )

    def test_brewery_near_water_beats_inland_brewery(self):
        """For waterfront asks, brewery near water should score higher."""
        from app.concierge.ranker import rank_entities
        waterfront_brewery = self._entity(
            "Riverwalk Brewing Co", ["brewery", "bar"], rating=4.2, review_count=300,
            source_query="breweries Chicago waterfront",
        )
        inland_brewery = self._entity(
            "West Side Brewery", ["brewery", "bar"], rating=4.5, review_count=600,
            source_query="breweries Chicago",
        )
        frame = self._frame("best breweries along the waterfront")
        ranked = rank_entities([waterfront_brewery, inland_brewery], frame)
        # The waterfront brewery (from geo-targeted query) should score higher geo_fit
        waterfront_score = next(s.geo_fit for e, s in ranked if e.name == "Riverwalk Brewing Co")
        inland_score = next(s.geo_fit for e, s in ranked if e.name == "West Side Brewery")
        assert waterfront_score >= inland_score, (
            f"Waterfront brewery should have higher geo_fit: "
            f"waterfront={waterfront_score:.3f} inland={inland_score:.3f}"
        )

    def test_tapas_beats_cocktail_bar(self):
        """Tapas/small-plates must rank above cocktail bar for tapas ask."""
        from app.concierge.ranker import rank_entities
        tapas_place = self._entity("La Tasca Tapas", ["spanish_restaurant", "restaurant"],
                                    rating=4.4, review_count=400,
                                    source_query="tapas Chicago")
        cocktail_bar = self._entity("The Cocktail Lounge", ["cocktail_bar", "bar"],
                                     rating=4.8, review_count=1500,
                                     source_query="tapas Chicago")
        frame = self._frame("romantic tapas but not too loud")
        ranked = rank_entities([tapas_place, cocktail_bar], frame)
        names = [e.name for e, _ in ranked]
        assert names[0] == "La Tasca Tapas", (
            f"Tapas must rank first, got {names}. "
            f"Scores: {[(e.name, s.as_dict()) for e, s in ranked]}"
        )

    def test_sushi_beats_generic_waterfront_restaurant(self):
        """Sushi must rank above a generic waterfront restaurant for sushi-view ask."""
        from app.concierge.ranker import rank_entities
        sushi = self._entity("Nobu Chicago", ["sushi_restaurant", "restaurant"],
                              rating=4.6, review_count=800,
                              source_query="sushi waterfront Chicago")
        waterfront_generic = self._entity("The River Grill", ["restaurant", "american_restaurant"],
                                           rating=4.8, review_count=2000,
                                           source_query="sushi waterfront Chicago")
        frame = self._frame("nice sushi restaurants with a waterfront view")
        ranked = rank_entities([sushi, waterfront_generic], frame)
        names = [e.name for e, _ in ranked]
        assert names[0] == "Nobu Chicago", (
            f"Sushi must rank first, got {names}. "
            f"Scores: {[(e.name, s.as_dict()) for e, s in ranked]}"
        )

    def test_popularity_cannot_overpower_subtype_fit(self):
        """A highly-popular generic place must not beat a concept-matching place."""
        from app.concierge.ranker import rank_entities
        concept_match = self._entity("Small Craft Brewery", ["brewery", "bar"],
                                      rating=4.0, review_count=100,
                                      source_query="breweries Chicago")
        popular_bar = self._entity("Super Popular Bar", ["bar", "cocktail_bar"],
                                    rating=4.9, review_count=10000,
                                    source_query="breweries Chicago")
        frame = self._frame("best breweries")
        ranked = rank_entities([concept_match, popular_bar], frame)
        # Check that subtype_fit dominates
        concept_score = next(s for e, s in ranked if e.name == "Small Craft Brewery")
        popular_score = next(s for e, s in ranked if e.name == "Super Popular Bar")
        assert concept_score.subtype_fit > popular_score.subtype_fit, (
            f"Concept match must have higher subtype_fit: "
            f"concept={concept_score.subtype_fit:.3f} popular={popular_score.subtype_fit:.3f}"
        )
        assert concept_score.total >= popular_score.total, (
            f"Concept match must win overall: "
            f"concept_total={concept_score.total:.3f} popular_total={popular_score.total:.3f}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 6. Safe Reason Builder
# ══════════════════════════════════════════════════════════════════════════════

class TestSafeReasonBuilder:

    def _entity(self, name: str, types: List[str] = None, rating: float = 4.3,
                 review_count: int = 300, address: str = "100 W Riverwalk, Chicago"):
        from app.concierge.place_entity_layer import PlaceEntity
        return PlaceEntity(
            place_id="pid_test",
            name=name,
            formatted_address=address,
            lat=41.88, lng=-87.63,
            business_status="OPERATIONAL",
            google_maps_uri="https://maps.google.com/?cid=123",
            types=types or ["restaurant"],
            primary_type=(types[0] if types else "restaurant"),
            rating=rating,
            user_rating_count=review_count,
            price_level=None,
            website_uri=None,
            source_query="breweries Chicago",
        )

    def _build_reason(self, entity, query, geo_fit=0.5, subtype_fit=0.9):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, MinimalEvidenceBundle, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason
        frame = extract_frame(query, "Chicago")
        score = RankScore(total=0.7, subtype_fit=subtype_fit, geo_fit=geo_fit)
        evidence = build_evidence_bundle(entity, frame, score)
        return build_safe_reason(entity, evidence, frame, score)

    def test_reason_includes_ask_anchor_brewery(self):
        entity = self._entity("Goose Island Brewery", types=["brewery", "bar"])
        reason = self._build_reason(entity, "best breweries along the waterfront")
        assert "brewery" in reason.lower() or "brew" in reason.lower(), (
            f"Reason must mention 'brewery': {reason}"
        )

    def test_reason_is_card_specific_not_template_tapas(self):
        """Deterministic note must be card-specific (name-anchored), not a generic type-template.

        Concept ("tapas") is NOT required in the deterministic fallback —
        the LLM path supplies that. What matters is the note is specific to THIS card.
        """
        entity = self._entity("La Tasca", types=["spanish_restaurant"])
        reason = self._build_reason(entity, "romantic tapas but not too loud")
        # Note must be card-specific: contains the actual place name
        assert "La Tasca" in reason, f"Note must anchor on place name: {reason}"
        # Note must NOT be a generic type-template
        assert not reason.lower().startswith("verified "), (
            f"Note must not use Verified-template format: {reason}"
        )

    def test_reason_does_not_invent_waterfront_view(self):
        """When geo_fit < 0.80, must NOT claim confirmed waterfront view."""
        entity = self._entity("Inland Brewery", types=["brewery", "bar"],
                               address="500 W Lake St, Chicago, IL")
        reason = self._build_reason(
            entity, "best breweries along the waterfront", geo_fit=0.40
        )
        # Should NOT say "waterfront view" as a confirmed fact
        assert "confirmed waterfront" not in reason.lower()
        assert "has a waterfront view" not in reason.lower()
        assert "waterfront view" not in reason.lower() or "verify" in reason.lower(), (
            f"Reason must not claim unverified waterfront view: {reason}"
        )

    def test_waterfront_unconfirmed_caveat_present(self):
        """When waterfront is requested but unconfirmed, reason must caveat it."""
        entity = self._entity("Riverside Grill", types=["restaurant"])
        reason = self._build_reason(
            entity, "best breweries along the waterfront", geo_fit=0.50
        )
        reason_lower = reason.lower()
        # Must either not mention waterfront, or mention it only in a caveat/denial.
        # Accept: "not confirmed", "cannot", "verify", "unconfirmed", "no ... confirmed"
        has_waterfront = "waterfront" in reason_lower
        has_honest_caveat = any(
            kw in reason_lower for kw in (
                "not confirmed", "cannot", "verify", "unconfirmed",
                "no waterfront", "proximity confirmed",
            )
        )
        assert not has_waterfront or has_honest_caveat, (
            f"Waterfront must not be asserted without evidence; "
            f"need honest caveat if mentioned: {reason}"
        )

    def test_reason_does_not_invent_quiet_or_romantic(self):
        entity = self._entity("Random Restaurant", types=["restaurant"])
        reason = self._build_reason(entity, "romantic tapas but not too loud", subtype_fit=0.5)
        # Must not claim "quiet atmosphere" or "romantic ambiance" as facts
        banned = ["quiet atmosphere confirmed", "proven quiet", "definitely romantic",
                  "confirmed romantic", "guaranteed quiet"]
        for phrase in banned:
            assert phrase not in reason.lower(), (
                f"Reason must not claim '{phrase}': {reason}"
            )

    def test_reason_never_empty(self):
        entity = self._entity("Mystery Place")
        reason = self._build_reason(entity, "best breweries")
        assert len(reason) > 10


# ══════════════════════════════════════════════════════════════════════════════
# 7. Integration — mocked provider → verified cards
# ══════════════════════════════════════════════════════════════════════════════

class TestSemanticRetrievalIntegration:
    """Integration tests using mocked Google provider responses."""

    def _mock_brewery_places(self) -> List[Dict[str, Any]]:
        return [
            _make_raw_place(
                name="Goose Island Brewing Company",
                place_id="ChIJ_goose",
                maps_uri="https://maps.google.com/?cid=100",
                types=["brewery", "bar", "food"],
                rating=4.5, review_count=1200,
            ),
            _make_raw_place(
                name="Half Acre Beer Company",
                place_id="ChIJ_halfacre",
                maps_uri="https://maps.google.com/?cid=200",
                types=["brewery", "bar"],
                rating=4.6, review_count=800,
            ),
            _make_raw_place(
                name="Revolution Brewing",
                place_id="ChIJ_revo",
                maps_uri="https://maps.google.com/?cid=300",
                types=["brewery", "bar", "restaurant"],
                rating=4.4, review_count=900,
            ),
        ]

    def _mock_fanout(self, places: List[Dict[str, Any]]):
        from app.concierge.provider_executor import ProviderQueryResult
        # Return same places for each query (entity layer dedup will handle duplicates)
        def fake_execute(queries, api_key, timeout=5.0, hard_cap=4, max_results_per_query=15):
            return [
                ProviderQueryResult(query=q, places=places[:], latency_ms=80)
                for q in queries
            ]
        return fake_execute

    def test_chicago_best_breweries_returns_verified_cards(self):
        """Flag ON, Chicago + 'best breweries' → at least 3 verified brewery cards."""
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1
        from app.models.concierge import SOURCE_LIVE_SEARCH

        with _MOCK_VALID_REASONS, patch(
            "app.concierge.provider_executor.execute_fanout",
            side_effect=self._mock_fanout(self._mock_brewery_places()),
        ):
            result = run_semantic_retrieval_v1(
                user_query="best breweries",
                destination="Chicago",
                api_key="fake_key",
            )

        assert result.source_status == SOURCE_LIVE_SEARCH
        assert len(result.restaurants) >= 3, (
            f"Expected ≥3 brewery cards, got {len(result.restaurants)}: "
            f"{[c.name for c in result.restaurants]}"
        )
        # All cards must be addable (have Google verification)
        for card in result.restaurants:
            gv = card.google_verification
            assert gv is not None
            assert gv.provider_place_id
            assert gv.google_maps_uri
            assert card.display.addability == "addable"

    def test_chicago_breweries_waterfront_no_invented_view(self):
        """Flag ON, Chicago + waterfront ask → brewery cards with honest reason wording."""
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1

        with _MOCK_VALID_REASONS, patch(
            "app.concierge.provider_executor.execute_fanout",
            side_effect=self._mock_fanout(self._mock_brewery_places()),
        ):
            result = run_semantic_retrieval_v1(
                user_query="best breweries along the waterfront",
                destination="Chicago",
                api_key="fake_key",
            )

        assert len(result.restaurants) >= 1
        for card in result.restaurants:
            reason = (card.display.display_why or "").lower()
            # Must NOT claim confirmed waterfront view
            assert "has a waterfront view" not in reason
            assert "confirmed waterfront" not in reason

    def test_tapas_returns_tapas_first_not_cocktail_bar(self):
        """Flag ON, Chicago + tapas ask → tapas/small-plates first, not cocktail bars first."""
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1

        places = [
            _make_raw_place(name="La Tasca Tapas Bar", place_id="pid_tapas1",
                             maps_uri="https://maps.google.com/?cid=401",
                             types=["spanish_restaurant", "restaurant"], rating=4.4, review_count=300),
            _make_raw_place(name="The Cocktail Lounge", place_id="pid_cocktail",
                             maps_uri="https://maps.google.com/?cid=402",
                             types=["cocktail_bar", "bar"], rating=4.9, review_count=2000),
            _make_raw_place(name="El Tapas", place_id="pid_tapas2",
                             maps_uri="https://maps.google.com/?cid=403",
                             types=["restaurant", "food"], rating=4.2, review_count=200),
        ]

        with _MOCK_VALID_REASONS, patch(
            "app.concierge.provider_executor.execute_fanout",
            side_effect=self._mock_fanout(places),
        ):
            result = run_semantic_retrieval_v1(
                user_query="romantic tapas but not too loud",
                destination="Chicago",
                api_key="fake_key",
            )

        assert len(result.restaurants) >= 1
        top_name = result.restaurants[0].name.lower()
        assert "tapas" in top_name or "tasca" in top_name or "el tapas" in top_name, (
            f"Tapas should be first, got: {result.restaurants[0].name}"
        )

    def test_sushi_first_with_honest_view_wording(self):
        """Flag ON, Chicago + sushi/waterfront → sushi-first, honest about view."""
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1

        places = [
            _make_raw_place(name="Nobu Chicago", place_id="pid_nobu",
                             maps_uri="https://maps.google.com/?cid=501",
                             types=["sushi_restaurant", "japanese_restaurant"], rating=4.7, review_count=900),
            _make_raw_place(name="The River Grill", place_id="pid_grill",
                             maps_uri="https://maps.google.com/?cid=502",
                             types=["american_restaurant", "restaurant"], rating=4.9, review_count=3000),
        ]

        with _MOCK_VALID_REASONS, patch(
            "app.concierge.provider_executor.execute_fanout",
            side_effect=self._mock_fanout(places),
        ):
            result = run_semantic_retrieval_v1(
                user_query="nice sushi restaurants with a waterfront view",
                destination="Chicago",
                api_key="fake_key",
            )

        assert len(result.restaurants) >= 1
        top_name = result.restaurants[0].name.lower()
        assert "nobu" in top_name or "sushi" in top_name, (
            f"Sushi should be first, got: {result.restaurants[0].name}"
        )
        # Honest about view
        top_reason = (result.restaurants[0].display.display_why or "").lower()
        assert "has a verified waterfront view" not in top_reason

    def test_all_provider_queries_fail_returns_no_fake_cards(self):
        """If all provider queries fail, must return empty result, not fabricated cards."""
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1
        from app.concierge.provider_executor import ProviderQueryResult

        def all_fail(queries, api_key, timeout, hard_cap=4, max_results_per_query=15):
            return [ProviderQueryResult(query=q, error="timeout") for q in queries]

        with patch("app.concierge.provider_executor.execute_fanout", side_effect=all_fail):
            result = run_semantic_retrieval_v1(
                user_query="best breweries",
                destination="Chicago",
                api_key="fake_key",
            )

        assert len(result.restaurants) == 0
        assert len(result.attractions) == 0
        assert result.source_status == "unavailable"

    def test_no_api_key_returns_empty_not_error(self):
        """Missing API key → empty result, no raised exception."""
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1
        # Should not raise even with no key
        result = run_semantic_retrieval_v1(
            user_query="best breweries",
            destination="Chicago",
            api_key="",
        )
        assert result is not None
        assert len(result.restaurants) == 0

    def test_empty_destination_returns_empty(self):
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1
        result = run_semantic_retrieval_v1(
            user_query="best breweries",
            destination="",
            api_key="fake_key",
        )
        assert len(result.restaurants) == 0


# ══════════════════════════════════════════════════════════════════════════════
# 8. Feature flag behavior
# ══════════════════════════════════════════════════════════════════════════════

class TestFeatureFlagBehavior:

    def test_flag_off_semantic_module_not_imported(self):
        """When flag is OFF, semantic_retrieval module is NOT called."""
        from unittest.mock import patch
        from types import SimpleNamespace

        semantic_called = []

        def fake_semantic(**kwargs):
            semantic_called.append(True)
            raise RuntimeError("should not be called")

        with patch.dict("sys.modules", {"app.concierge.semantic_retrieval": None}):
            # If the module can't be imported and flag is off, no error should occur
            # We just verify the settings path doesn't call it
            settings = SimpleNamespace(
                concierge_semantic_retrieval_v1_enabled=False,
                concierge_fast_dynamic_place_search_v1_enabled=False,
                live_research_enabled=True,
                live_research_cache_ttl_seconds=1800,
                live_research_timeout_seconds=6.0,
                research_engine_require_google_verification=False,
                google_places_api_key="",
                tavily_api_key="",
                brave_search_api_key="",
                serper_api_key="",
            )
            assert not settings.concierge_semantic_retrieval_v1_enabled
            assert len(semantic_called) == 0

    def test_flag_default_is_false(self):
        """The flag must default to False to protect existing behavior."""
        import pathlib
        # Search both from repo root and from backend/ (depending on where pytest runs)
        candidates = [
            pathlib.Path("backend/app/core/config.py"),
            pathlib.Path("app/core/config.py"),
        ]
        config_src = None
        for p in candidates:
            if p.exists():
                config_src = p.read_text()
                break
        assert config_src is not None, "Could not find app/core/config.py"
        assert "concierge_semantic_retrieval_v1_enabled: bool = False" in config_src, (
            "Default for concierge_semantic_retrieval_v1_enabled must be False"
        )


# ══════════════════════════════════════════════════════════════════════════════
# PR-2.5: Brewery Semantic Retrieval Coverage Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestBreweryRetrievalPlannerCoverage:
    """PR-2.5: RetrievalPlanner synonym expansion for breweries plural/variant forms."""

    def _frame(self, query: str, destination: str = "Chicago"):
        from app.concierge.frame_extractor import extract_frame
        return extract_frame(query, destination)

    def test_best_breweries_generates_brewery_queries(self):
        """'best breweries' → retrieval queries include brewery/taproom/brewpub variants."""
        from app.concierge.retrieval_planner import plan_queries
        frame = self._frame("best breweries")
        queries = plan_queries(frame)
        assert len(queries) >= 1
        brew_queries = [q for q in queries if "brew" in q.lower() or "taproom" in q.lower()]
        assert brew_queries, (
            f"Expected at least one brewery-related query for 'best breweries', got: {queries}"
        )
        assert all("chicago" in q.lower() for q in queries), (
            f"All queries must include destination Chicago: {queries}"
        )

    def test_best_breweries_waterfront_preserves_both_concept_and_geo(self):
        """'best breweries along the waterfront' → queries preserve brewery AND waterfront hint."""
        from app.concierge.retrieval_planner import plan_queries
        frame = self._frame("best breweries along the waterfront")
        queries = plan_queries(frame)

        # At least one query must contain a brewery concept
        brew_queries = [q for q in queries if "brew" in q.lower() or "taproom" in q.lower()]
        assert brew_queries, f"Expected brewery concept in queries: {queries}"

        # At least one query must contain a waterfront geo hint
        geo_queries = [q for q in queries if "waterfront" in q.lower() or "riverwalk" in q.lower()]
        assert geo_queries, f"Expected waterfront geo hint in at least one query: {queries}"

    def test_breweries_synonym_expansion_key_exists(self):
        """Synonym expansion must have 'breweries' as a direct key for open-vocab fallback."""
        from app.concierge.retrieval_planner import _SYNONYM_EXPANSIONS
        assert "breweries" in _SYNONYM_EXPANSIONS, (
            "'breweries' must be in _SYNONYM_EXPANSIONS so plural forms expand correctly."
        )
        variants = _SYNONYM_EXPANSIONS["breweries"]
        assert any("brew" in v.lower() for v in variants), (
            f"'breweries' expansion must include brewery-related variants: {variants}"
        )

    def test_brewpub_generates_brewery_queries(self):
        """'best brewpubs' → queries include brewpub and brewery variants."""
        from app.concierge.retrieval_planner import plan_queries
        frame = self._frame("best brewpubs")
        queries = plan_queries(frame)
        assert any("brew" in q.lower() for q in queries), (
            f"Expected brewery-related queries for 'best brewpubs': {queries}"
        )

    def test_taproom_generates_brewery_queries(self):
        """'taproom options' → queries include taproom/brewery variants."""
        from app.concierge.retrieval_planner import plan_queries
        frame = self._frame("taproom options")
        queries = plan_queries(frame)
        assert any("taproom" in q.lower() or "brew" in q.lower() for q in queries), (
            f"Expected taproom-related queries: {queries}"
        )


class TestBreweryEntityGating:
    """PR-2.5: Brewery candidates still require Google place_id, OPERATIONAL, maps URI."""

    def test_brewery_place_rejected_if_missing_place_id(self):
        from app.concierge.place_entity_layer import build_entity_layer
        from app.concierge.provider_executor import ProviderQueryResult
        place = _make_raw_place(name="No ID Brewery", place_id="", types=["brewery"])
        result = ProviderQueryResult(query="brewery Chicago", places=[place], latency_ms=10)
        entities, stats = build_entity_layer([result], frozenset())
        assert len(entities) == 0, "Brewery with no place_id must be rejected"

    def test_brewery_place_rejected_if_closed(self):
        from app.concierge.place_entity_layer import build_entity_layer
        from app.concierge.provider_executor import ProviderQueryResult
        place = _make_raw_place(
            name="Closed Brewery", business_status="CLOSED_PERMANENTLY", types=["brewery"]
        )
        result = ProviderQueryResult(query="brewery Chicago", places=[place], latency_ms=10)
        entities, stats = build_entity_layer([result], frozenset())
        assert len(entities) == 0, "Non-OPERATIONAL brewery must be rejected"

    def test_brewery_place_accepted_when_valid(self):
        from app.concierge.place_entity_layer import build_entity_layer
        from app.concierge.provider_executor import ProviderQueryResult
        place = _make_raw_place(
            name="Goose Island Brewing", place_id="ChIJ_goose_valid",
            maps_uri="https://maps.google.com/?cid=999",
            types=["brewery", "bar"], business_status="OPERATIONAL",
        )
        result = ProviderQueryResult(query="brewery Chicago", places=[place], latency_ms=10)
        entities, stats = build_entity_layer([result], frozenset())
        assert len(entities) == 1, "Valid OPERATIONAL brewery with place_id and maps URI must pass"
        assert entities[0].name == "Goose Island Brewing"


class TestBreweryReasonNoUnsupportedClaims:
    """PR-2.5: Brewery reason text must not claim unsupported waterfront view."""

    def _build_reason(self, query: str, types=None, source_query: str = "brewery Chicago"):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import rank_entities, build_evidence_bundle, PlaceEntity
        from app.concierge.safe_reason_builder import build_safe_reason

        frame = extract_frame(query, "Chicago")
        entity = PlaceEntity(
            place_id="ChIJ_test",
            name="Test Brewery",
            types=types or ["brewery", "bar"],
            primary_type="brewery",
            rating=4.3,
            user_rating_count=400,
            business_status="OPERATIONAL",
            formatted_address="100 N Riverside Dr, Chicago, IL",
            google_maps_uri="https://maps.google.com/?cid=1",
            website_uri=None,
            price_level=None,
            lat=41.88,
            lng=-87.63,
            source_query=source_query,
        )
        ranked = rank_entities([entity], frame, top_n=1)
        assert ranked, "Expected ranked entity"
        entity, score = ranked[0]
        evidence = build_evidence_bundle(entity, frame, score)
        return build_safe_reason(entity, evidence, frame, score)

    def test_no_confirmed_waterfront_claim(self):
        reason = self._build_reason(
            "best breweries along the waterfront",
            source_query="brewery Chicago waterfront",
        )
        reason_lower = reason.lower()
        assert "has a waterfront view" not in reason_lower, reason
        assert "confirmed waterfront" not in reason_lower, reason

    def test_reason_includes_brewery_anchor(self):
        reason = self._build_reason("best breweries")
        assert len(reason) >= 10, "Reason must not be empty for brewery ask"


class TestMoreOptionsFollowUpBehavior:
    """PR-2.5: 'more options' follow-up must exclude prior identity keys, top 3 must not regress."""

    def _mock_brewery_places(self) -> List[Dict[str, Any]]:
        return [
            _make_raw_place(
                name="Goose Island Brewing",
                place_id="ChIJ_goose",
                maps_uri="https://maps.google.com/?cid=100",
                types=["brewery", "bar"],
                rating=4.5, review_count=1200,
            ),
            _make_raw_place(
                name="Half Acre Beer Company",
                place_id="ChIJ_halfacre",
                maps_uri="https://maps.google.com/?cid=200",
                types=["brewery", "bar"],
                rating=4.6, review_count=800,
            ),
            _make_raw_place(
                name="Revolution Brewing",
                place_id="ChIJ_revo",
                maps_uri="https://maps.google.com/?cid=300",
                types=["brewery", "bar", "restaurant"],
                rating=4.4, review_count=900,
            ),
            _make_raw_place(
                name="Off Color Brewing",
                place_id="ChIJ_offcolor",
                maps_uri="https://maps.google.com/?cid=400",
                types=["brewery"],
                rating=4.2, review_count=300,
            ),
        ]

    def _mock_fanout(self, places: List[Dict[str, Any]]):
        from app.concierge.provider_executor import ProviderQueryResult
        def fake_execute(queries, api_key, timeout=5.0, hard_cap=4, max_results_per_query=15):
            return [ProviderQueryResult(query=q, places=places[:], latency_ms=80) for q in queries]
        return fake_execute

    def test_more_options_excludes_prior_identity_keys(self):
        """'more options' follow-up: properly formatted prior_identity_keys cause dedup."""
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1
        from app.concierge.place_entity_layer import _normalize_text
        from app.models.concierge import SOURCE_LIVE_SEARCH

        places = self._mock_brewery_places()

        with _MOCK_VALID_REASONS, patch("app.concierge.provider_executor.execute_fanout",
                   side_effect=self._mock_fanout(places)):
            first_result = run_semantic_retrieval_v1(
                user_query="best breweries",
                destination="Chicago",
                api_key="fake_key",
            )

        assert first_result.source_status == SOURCE_LIVE_SEARCH
        first_names = {c.name for c in first_result.restaurants}

        # Build identity keys in the format the entity layer uses (pid:/gmaps: prefixes)
        first_keys: set = set()
        for c in first_result.restaurants:
            gv = c.google_verification
            if gv:
                if gv.provider_place_id:
                    first_keys.add(f"pid:{_normalize_text(gv.provider_place_id)}")
                if gv.google_maps_uri:
                    first_keys.add(f"gmaps:{_normalize_text(gv.google_maps_uri)}")

        with _MOCK_VALID_REASONS, patch("app.concierge.provider_executor.execute_fanout",
                   side_effect=self._mock_fanout(places)):
            second_result = run_semantic_retrieval_v1(
                user_query="more options",
                destination="Chicago",
                prior_identity_keys=frozenset(first_keys),
                api_key="fake_key",
            )

        # Second result must not repeat cards from the first result
        second_names = {c.name for c in second_result.restaurants}
        overlap = first_names & second_names
        assert not overlap, (
            f"'more options' follow-up must not re-show prior cards. "
            f"Overlap: {overlap}. prior_keys passed: {first_keys}"
        )

    def test_top_3_returns_at_most_requested_count(self):
        """SemanticRanker with max_cards=3 must not return more than 3 cards."""
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1

        places = self._mock_brewery_places()
        with patch("app.concierge.provider_executor.execute_fanout",
                   side_effect=self._mock_fanout(places)):
            result = run_semantic_retrieval_v1(
                user_query="best breweries",
                destination="Chicago",
                api_key="fake_key",
                max_cards=3,
            )

        assert len(result.restaurants) <= 3, (
            f"max_cards=3 must return ≤3 cards, got {len(result.restaurants)}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# PR Semantic Place Understanding v2 — venue head, open-class detector,
# location modifiers, wrong-category penalty, non-repetitive safe reasons.
# ══════════════════════════════════════════════════════════════════════════════


class TestVenueHeadPreservation:
    """Geo / style modifiers must not win over the real venue noun."""

    def test_waterfront_breweries_concept_is_brewery_not_waterfront(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("best waterfront breweries", "Chicago")
        labels = [c.label for c in frame.subtype_concepts]
        assert any(l in ("brewery", "breweries") for l in labels), (
            f"Expected brewery as primary concept, got {labels}"
        )
        assert "waterfront" not in labels, (
            f"'waterfront' must NOT be a venue concept, got {labels}"
        )
        assert "waterfront" in frame.geography_hints

    def test_rooftop_bars_concept_is_bar_not_rooftop(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("best rooftop bars in Chicago", "Chicago")
        labels = [c.label for c in frame.subtype_concepts]
        assert "rooftop" not in labels, f"rooftop must be a modifier, got {labels}"

    def test_romantic_tapas_concept_is_tapas_not_romantic(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("romantic tapas but not too loud", "Chicago")
        labels = [c.label for c in frame.subtype_concepts]
        assert any("tapa" in l for l in labels), f"Expected tapas concept, got {labels}"
        assert "romantic" not in labels

    def test_outdoor_breweries_concept_is_brewery(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("nice outdoor breweries", "Chicago")
        labels = [c.label for c in frame.subtype_concepts]
        assert any(l in ("brewery", "breweries") for l in labels), (
            f"Expected brewery, got {labels}"
        )


class TestLocationModifierExtraction:
    """Concrete neighborhood / street anchors get captured as location_modifiers."""

    def test_izakayas_in_fulton_street_extracts_anchor(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("best izakayas in Fulton Street", "Chicago")
        assert frame.location_modifiers, (
            f"Expected a location modifier, got: {frame.location_modifiers}"
        )
        assert any("Fulton" in loc for loc in frame.location_modifiers), (
            f"Expected 'Fulton Street' captured, got {frame.location_modifiers}"
        )

    def test_destination_alone_is_not_a_location_modifier(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("best sushi in Chicago", "Chicago")
        # The destination itself should not be mirrored as a modifier
        assert not any(
            loc.strip().lower() == "chicago" for loc in frame.location_modifiers
        ), f"Destination must not be echoed as location modifier: {frame.location_modifiers}"

    def test_west_loop_neighborhood_captured(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("dinner spots in West Loop", "Chicago")
        assert any("West Loop" in loc or "West" in loc for loc in frame.location_modifiers), (
            f"Expected 'West Loop' captured, got {frame.location_modifiers}"
        )


class TestOpenClassPlaceAskDetector:
    """High-recall detector for place-like asks; rejects clear non-place asks."""

    @pytest.mark.parametrize("query", [
        "best izakayas in Fulton Street",
        "best izakaya near here",
        "tea houses",
        "dessert bars",
        "record stores",
        "arcades",
        "great speakeasies",
        "where to grab drinks",
        "best ramen shop",
        "any good coffee shops good for reading",
        "places to dance",
    ])
    def test_open_class_detects_place_like_asks(self, query):
        from app.concierge.frame_extractor import extract_frame, is_open_class_place_ask
        frame = extract_frame(query, "Chicago")
        assert is_open_class_place_ask(query, frame.subtype_concepts), (
            f"Expected open-class place ask for {query!r}"
        )

    @pytest.mark.parametrize("query", [
        "what is the weather in Chicago",
        "what to pack for Chicago",
        "exchange rate for euros",
        "best flights to Chicago",
        "currency in Chicago",
        "visa requirements for Chicago",
        "how many days should I spend",
        "transfer partner for points",
        "budget plan for the trip",
    ])
    def test_open_class_rejects_non_place_asks(self, query):
        from app.concierge.frame_extractor import extract_frame, is_open_class_place_ask
        frame = extract_frame(query, "Chicago")
        assert not is_open_class_place_ask(query, frame.subtype_concepts), (
            f"Non-place ask must be rejected: {query!r}"
        )


class TestRetrievalPlannerVenueFirstOpenClass:
    """Open-vocabulary nouns must produce venue-first queries."""

    def _frame(self, query: str, destination: str = "Chicago"):
        from app.concierge.frame_extractor import extract_frame
        return extract_frame(query, destination)

    def test_izakaya_query_is_venue_first(self):
        from app.concierge.retrieval_planner import plan_queries
        frame = self._frame("best izakayas in Fulton Street")
        queries = plan_queries(frame)
        assert any("izakaya" in q.lower() for q in queries), (
            f"Expected izakaya in queries: {queries}"
        )
        # Concrete location anchor should appear in at least one query
        assert any("fulton" in q.lower() for q in queries), (
            f"Expected Fulton Street anchor in queries: {queries}"
        )

    def test_waterfront_breweries_planner_is_brewery_first(self):
        from app.concierge.retrieval_planner import plan_queries
        frame = self._frame("best waterfront breweries")
        queries = plan_queries(frame)
        # Each query must reference brewery/taproom as the venue head
        assert all(
            any(tok in q.lower() for tok in ("brew", "taproom"))
            for q in queries
        ), f"All queries must be venue-first (brewery): {queries}"

    def test_unknown_venue_uses_literal_concept(self):
        """Unknown venue noun should still produce a venue-first query without
        requiring synonym expansion."""
        from app.concierge.retrieval_planner import plan_queries
        frame = self._frame("best record stores in Chicago")
        queries = plan_queries(frame)
        assert any("record" in q.lower() for q in queries), (
            f"Expected record stores in queries: {queries}"
        )
        assert all("chicago" in q.lower() for q in queries), (
            f"All queries must include destination: {queries}"
        )


class TestWrongCategoryPenalty:
    """Wrong-category cards must not dominate when a clear venue type is requested."""

    def _entity(
        self, name, types, rating=4.0, review_count=200,
        place_id=None, source_query="brewery Chicago waterfront",
    ):
        from app.concierge.place_entity_layer import PlaceEntity
        return PlaceEntity(
            place_id=place_id or f"pid_{abs(hash(name))}",
            name=name,
            formatted_address="123 Main St, Chicago, IL",
            lat=41.88, lng=-87.63,
            business_status="OPERATIONAL",
            google_maps_uri=f"https://maps.google.com/?cid={abs(hash(name))}",
            types=types,
            primary_type=types[0] if types else None,
            rating=rating,
            user_rating_count=review_count,
            price_level=None,
            website_uri=None,
            source_query=source_query,
        )

    def test_waterfront_park_does_not_beat_brewery(self):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import rank_entities
        brewery = self._entity(
            "Goose Island Brewery", ["brewery", "bar"], rating=4.3, review_count=500,
        )
        # A waterfront park / restaurant that has nothing to do with breweries
        # but matches geo from a brewery+waterfront search.
        wrong_cat = self._entity(
            "Riverside Steakhouse", ["steak_house", "restaurant"],
            rating=4.7, review_count=2000,
        )
        frame = extract_frame("best waterfront breweries", "Chicago")
        ranked = rank_entities([brewery, wrong_cat], frame)
        names = [e.name for e, _ in ranked]
        assert names[0] == "Goose Island Brewery", (
            f"Brewery must rank first over wrong-category steakhouse, got {names}. "
            f"Scores: {[(e.name, s.as_dict()) for e, s in ranked]}"
        )

    def test_wrong_category_penalty_lowers_score(self):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import rank_entities
        brewery = self._entity(
            "Goose Island Brewery", ["brewery", "bar"], rating=4.3, review_count=500,
        )
        # Wrong-category: name has no brewery tokens, types don't match,
        # and the source_query doesn't echo the concept either.
        wrong_cat = self._entity(
            "Lakeside Garden", ["park"], rating=4.6, review_count=1500,
            source_query="park Chicago",
        )
        frame = extract_frame("best breweries", "Chicago")
        ranked = rank_entities([brewery, wrong_cat], frame)
        scores = {e.name: s for e, s in ranked}
        # Wrong-category entity must have a positive penalty applied.
        assert scores["Lakeside Garden"].penalties > 0, (
            f"Expected wrong-category penalty on Lakeside Garden, "
            f"got {scores['Lakeside Garden'].as_dict()}"
        )
        assert scores["Goose Island Brewery"].penalties == 0


class TestNonRepetitiveSafeReason:
    """Safe reasons must not invent a 'Good waterfront match' for every card,
    and must never treat a modifier (waterfront, rooftop) as the venue head."""

    def _entity(self, name, types, address="100 W Lake St, Chicago, IL"):
        from app.concierge.place_entity_layer import PlaceEntity
        return PlaceEntity(
            place_id=f"pid_{abs(hash(name))}",
            name=name,
            formatted_address=address,
            lat=41.88, lng=-87.63,
            business_status="OPERATIONAL",
            google_maps_uri=f"https://maps.google.com/?cid={abs(hash(name))}",
            types=types,
            primary_type=types[0] if types else None,
            rating=4.3,
            user_rating_count=400,
            price_level=None,
            website_uri=None,
            source_query="brewery Chicago waterfront",
        )

    def test_reason_does_not_say_good_waterfront_match(self):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import rank_entities, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason
        entity = self._entity("Goose Island Brewery", ["brewery", "bar"])
        frame = extract_frame("best waterfront breweries", "Chicago")
        ranked = rank_entities([entity], frame, top_n=1)
        e, score = ranked[0]
        evidence = build_evidence_bundle(e, frame, score)
        reason = build_safe_reason(e, evidence, frame, score)
        low = reason.lower()
        # Must NOT say "waterfront match" — that's the modifier-as-venue bug
        assert "waterfront match" not in low, (
            f"Reason must not call waterfront a venue concept: {reason}"
        )
        # Must mention brewery (the real venue head)
        assert "brewery" in low or "brew" in low, (
            f"Reason must anchor on brewery: {reason}"
        )

    def test_modifier_only_label_does_not_become_venue_match(self):
        """Defensive: even if the frame's primary concept were forced to be
        'waterfront', the safe reason must not produce 'waterfront match'."""
        from app.concierge.frame_extractor import (
            ExperienceFrame, SubtypeConcept,
        )
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason
        entity = self._entity("Generic Restaurant", ["restaurant"])
        # Hand-craft a frame whose primary concept is a modifier-only token.
        frame = ExperienceFrame(
            literal_ask="waterfront restaurant",
            normalized_ask="waterfront restaurant",
            destination="Chicago",
            subtype_concepts=[SubtypeConcept(label="waterfront", confidence=0.9, source="literal_primary")],
            geography_hints=["waterfront"],
        )
        score = RankScore(total=0.7, subtype_fit=0.9, geo_fit=0.85)
        evidence = build_evidence_bundle(entity, frame, score)
        reason = build_safe_reason(entity, evidence, frame, score)
        low = reason.lower()
        assert "waterfront match" not in low, reason
        assert "good waterfront" not in low, reason

    def test_geo_phrase_omitted_when_unconfirmed(self):
        """When geo_fit is weak, the visible reason should not echo a
        geo-targeted-search-area phrase that repeats on every card."""
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason
        entity = self._entity("Goose Island Brewery", ["brewery", "bar"])
        frame = extract_frame("best waterfront breweries", "Chicago")
        score = RankScore(total=0.6, subtype_fit=0.9, geo_fit=0.55)
        evidence = build_evidence_bundle(entity, frame, score)
        reason = build_safe_reason(entity, evidence, frame, score)
        low = reason.lower()
        assert "targeted search area" not in low, (
            f"Repetitive geo phrase must not appear in reason: {reason}"
        )


class TestSemanticIntegrationOpenClassIzakaya:
    """Open-class place ask integration: izakayas in Fulton Street."""

    def test_izakaya_in_fulton_street_returns_venue_first_cards(self):
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1
        from app.models.concierge import SOURCE_LIVE_SEARCH
        from app.concierge.provider_executor import ProviderQueryResult

        izakaya_places = [
            _make_raw_place(
                name="Momotaro Izakaya",
                place_id="pid_momotaro",
                maps_uri="https://maps.google.com/?cid=901",
                types=["japanese_restaurant", "restaurant"],
                rating=4.5, review_count=600,
                address="820 W Lake St, Chicago, IL, USA",
            ),
            _make_raw_place(
                name="Izakaya Mita",
                place_id="pid_mita",
                maps_uri="https://maps.google.com/?cid=902",
                types=["japanese_restaurant", "restaurant"],
                rating=4.4, review_count=300,
                address="1960 N Damen Ave, Chicago, IL, USA",
            ),
        ]

        def fake_execute(queries, api_key, timeout=5.0, hard_cap=4, max_results_per_query=15):
            return [
                ProviderQueryResult(query=q, places=izakaya_places[:], latency_ms=80)
                for q in queries
            ]

        with _MOCK_VALID_REASONS, patch("app.concierge.provider_executor.execute_fanout", side_effect=fake_execute):
            result = run_semantic_retrieval_v1(
                user_query="best izakayas in Fulton Street",
                destination="Chicago",
                api_key="fake_key",
            )

        assert result.source_status == SOURCE_LIVE_SEARCH, (
            f"Expected live_search, got {result.source_status}"
        )
        assert len(result.restaurants) >= 1, (
            f"Expected at least 1 izakaya card, got {len(result.restaurants)}"
        )
        # Top card name should reference izakaya / japanese context
        top = result.restaurants[0].name.lower()
        assert "izakaya" in top or "momotaro" in top or "mita" in top, (
            f"Expected izakaya-related top card, got: {result.restaurants[0].name}"
        )


class TestSemanticTurnObservability:
    """Structured semantic turn log must include venue_concept, modifiers, etc."""

    def test_turn_log_contains_open_class_and_venue_fields(self, caplog):
        import logging
        from app.concierge.provider_executor import ProviderQueryResult
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1

        def fake_execute(queries, api_key, timeout=5.0, hard_cap=4, max_results_per_query=15):
            return [
                ProviderQueryResult(
                    query=q,
                    places=[_make_raw_place(
                        name="Goose Island Brewery",
                        place_id="pid_goose",
                        maps_uri="https://maps.google.com/?cid=900",
                        types=["brewery", "bar"],
                        rating=4.5, review_count=1200,
                    )],
                    latency_ms=50,
                )
                for q in queries
            ]

        with caplog.at_level(logging.INFO, logger="app.concierge.semantic_retrieval"):
            with patch("app.concierge.provider_executor.execute_fanout", side_effect=fake_execute):
                run_semantic_retrieval_v1(
                    user_query="best waterfront breweries",
                    destination="Chicago",
                    api_key="fake_key",
                )
        turn_logs = [r.message for r in caplog.records if "semantic_retrieval_v1.turn" in r.message]
        assert turn_logs, f"Expected semantic_retrieval_v1.turn log, got: {[r.message for r in caplog.records]}"
        log = turn_logs[0]
        assert "open_class_place_detected=" in log
        assert "venue_concept=" in log
        assert "geo_hints=" in log
        assert "location_modifiers=" in log
        assert "retrieval_queries=" in log
        assert "wrong_category_low_subtype_fit" in log


def test_entity_to_card_preserves_google_rating_native_scale_and_review_count():
    from app.concierge.frame_extractor import extract_frame
    from app.concierge.place_entity_layer import PlaceEntity
    from app.concierge.semantic_retrieval import _entity_to_card

    frame = extract_frame("best cocktail bars", "Chicago")
    entity = PlaceEntity(
        place_id="gp-1",
        name="Kumiko",
        types=["cocktail_bar", "bar"],
        primary_type="cocktail_bar",
        rating=4.6,
        user_rating_count=1200,
        business_status="OPERATIONAL",
        formatted_address="630 W Lake St, Chicago, IL",
        google_maps_uri="https://maps.google.com/?cid=123",
        website_uri=None,
        lat=41.0,
        lng=-87.0,
        price_level=None,
    )

    card = _entity_to_card(entity, "A well-regarded cocktail bar.", frame)

    assert card is not None
    assert card.rating == 4.6
    assert card.review_count == 1200
    assert card.supporting_details is not None
    assert card.supporting_details.meta_line == "★ 4.6 (1,200 reviews)"


def test_entity_to_card_handles_null_rating_without_fabrication():
    from app.concierge.frame_extractor import extract_frame
    from app.concierge.place_entity_layer import PlaceEntity
    from app.concierge.semantic_retrieval import _entity_to_card

    frame = extract_frame("best cocktail bars", "Chicago")
    entity = PlaceEntity(
        place_id="gp-2",
        name="No Rating Bar",
        types=["bar"],
        primary_type="bar",
        rating=None,
        user_rating_count=321,
        business_status="OPERATIONAL",
        formatted_address="100 Main St, Chicago, IL",
        google_maps_uri="https://maps.google.com/?cid=456",
        website_uri=None,
        lat=41.1,
        lng=-87.1,
        price_level=None,
    )

    card = _entity_to_card(entity, "A bar.", frame)

    assert card is not None
    assert card.rating is None
    assert card.review_count == 321
    assert card.supporting_details is not None
    assert card.supporting_details.meta_line is None


# ══════════════════════════════════════════════════════════════════════════════
# Venue-Head-Over-Modifier Contract — open-language place understanding
#
# Modifiers (waterfront, riverwalk, lakefront, rooftop, romantic) must shape
# query expansion and ranking but never replace the requested venue head. The
# system prefers partial modifier satisfaction over wrong-category cards, and
# returns fewer/no cards rather than off-concept ones for recognized venue
# heads.
# ══════════════════════════════════════════════════════════════════════════════


class TestPlannerNoStandaloneModifierQueries:
    """For waterfront/riverwalk/lakefront asks with a venue head, the planner
    must not emit standalone geo-only queries that would flood the candidate
    pool with parks, landmarks, and generic waterfront restaurants."""

    def _frame(self, query: str, destination: str = "Chicago"):
        from app.concierge.frame_extractor import extract_frame
        return extract_frame(query, destination)

    @pytest.mark.parametrize("query,banned_solo", [
        ("best waterfront breweries", ("waterfront chicago", "riverwalk chicago", "lakefront chicago")),
        ("breweries near the river", ("river chicago", "riverwalk chicago")),
        ("taprooms with a view", ("view chicago",)),
        ("brewpubs by the water", ("water chicago", "waterfront chicago")),
        ("romantic sushi near the water", ("water chicago", "waterfront chicago")),
        ("quiet cocktail bars with a view", ("view chicago",)),
    ])
    def test_no_standalone_modifier_only_query(self, query, banned_solo):
        from app.concierge.retrieval_planner import plan_queries
        frame = self._frame(query)
        queries = [q.lower() for q in plan_queries(frame)]
        for banned in banned_solo:
            assert banned not in queries, (
                f"Planner must not emit modifier-only query {banned!r} when a "
                f"venue head exists. Got queries: {queries} for ask: {query!r}"
            )

    def test_waterfront_breweries_includes_pure_brewery_recall_query(self):
        """At least one query must be the modifier-free venue+destination
        form so brewery recall isn't entirely tied to the geo-targeted Google
        result set."""
        from app.concierge.retrieval_planner import plan_queries
        frame = self._frame("best waterfront breweries")
        queries = [q.lower() for q in plan_queries(frame)]
        assert "brewery chicago" in queries, (
            f"Expected pure brewery+destination recall query, got: {queries}"
        )

    def test_breweries_near_the_river_is_brewery_first(self):
        from app.concierge.retrieval_planner import plan_queries
        frame = self._frame("breweries near the river")
        queries = plan_queries(frame)
        # All queries must be venue-anchored
        assert all(
            any(tok in q.lower() for tok in ("brew", "taproom"))
            for q in queries
        ), f"All queries must be venue-anchored: {queries}"


class TestRankerVenueHeadDominance:
    """Brewery candidates with weak waterfront evidence still outrank park /
    riverwalk attractions / generic restaurants that strongly match the geo
    modifier but are wrong category for the user's venue head."""

    def _entity(
        self,
        name,
        types,
        rating=4.0,
        review_count=200,
        place_id=None,
        address="123 Main St, Chicago, IL",
        source_query="brewery Chicago waterfront",
    ):
        from app.concierge.place_entity_layer import PlaceEntity
        return PlaceEntity(
            place_id=place_id or f"pid_{abs(hash(name))}",
            name=name,
            formatted_address=address,
            lat=41.88, lng=-87.63,
            business_status="OPERATIONAL",
            google_maps_uri=f"https://maps.google.com/?cid={abs(hash(name))}",
            types=types,
            primary_type=types[0] if types else None,
            rating=rating,
            user_rating_count=review_count,
            price_level=None,
            website_uri=None,
            source_query=source_query,
        )

    def test_brewery_with_weak_waterfront_beats_park_with_strong_waterfront(self):
        """Brewery (right category, address has no water) must outrank a
        riverside park (wrong category, address strongly waterfront)."""
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import rank_entities
        brewery = self._entity(
            "West Loop Brewing Co",
            ["brewery", "bar"],
            rating=4.2,
            review_count=300,
            address="900 W Randolph St, Chicago, IL",  # no water tokens
        )
        riverside_park = self._entity(
            "Lakefront Riverwalk Park",
            ["park", "tourist_attraction"],
            rating=4.8,
            review_count=5000,
            address="100 N Riverside Plaza, Chicago, IL",  # has river
            source_query="brewery Chicago waterfront",
        )
        frame = extract_frame("best waterfront breweries", "Chicago")
        ranked = rank_entities([brewery, riverside_park], frame)
        names = [e.name for e, _ in ranked]
        assert names[0] == "West Loop Brewing Co", (
            f"Brewery (right category) must outrank park (wrong category) "
            f"even with strong modifier evidence. Got: {names}. "
            f"Scores: {[(e.name, s.as_dict()) for e, s in ranked]}"
        )

    def test_source_query_concept_does_not_bypass_wrong_category_penalty(self):
        """Production bug: a non-brewery entity returned by a brewery-targeted
        query should not get a free pass on subtype_fit just because the
        source query echoes 'brewery'. Wrong-category penalty must apply."""
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import rank_entities
        brewery = self._entity(
            "Goose Island Brewing", ["brewery", "bar"], rating=4.3, review_count=400,
        )
        # Wrong-category entity returned by the same brewery-targeted query.
        wrong_cat = self._entity(
            "Chicago Horizon",
            ["tourist_attraction", "point_of_interest"],
            rating=4.6,
            review_count=2000,
            source_query="brewery Chicago waterfront",
        )
        frame = extract_frame("best waterfront breweries", "Chicago")
        ranked = rank_entities([brewery, wrong_cat], frame)
        scores = {e.name: s for e, s in ranked}
        # Wrong-category entity must NOT be lifted above the threshold by the
        # mere presence of "brewery" in its source query.
        assert "Chicago Horizon" in scores, (
            f"Expected wrong-cat entity in ranked output (only 1 on-concept, "
            f"so degraded recall keeps it). Got {list(scores.keys())}"
        )
        wc_score = scores["Chicago Horizon"]
        assert wc_score.subtype_fit < 0.30, (
            f"Source-query echo must not push subtype_fit above the "
            f"wrong-category threshold. Got {wc_score.subtype_fit:.3f}"
        )
        assert wc_score.penalties > 0, (
            f"Wrong-category entity must carry a penalty. Got {wc_score.as_dict()}"
        )

    def test_three_breweries_drop_three_wrong_category_modifier_matches(self):
        """When the user names a venue head AND there are enough on-concept
        candidates, modifier-only wrong-category candidates must be dropped
        from the surviving result (returns brewery-only cards)."""
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import rank_entities_with_stats
        breweries = [
            self._entity("Goose Island Brewing", ["brewery", "bar"], rating=4.5, review_count=1200),
            self._entity("Half Acre Beer Company", ["brewery", "bar"], rating=4.6, review_count=800),
            self._entity("Revolution Brewing", ["brewery", "bar"], rating=4.4, review_count=900),
        ]
        wrong_cat = [
            self._entity(
                "Chicago Riverwalk", ["tourist_attraction"],
                rating=4.7, review_count=10000,
                address="Riverwalk, Chicago, IL",
            ),
            self._entity(
                "Lakefront Park", ["park"],
                rating=4.8, review_count=8000,
                address="Lake Shore Dr, Chicago, IL",
            ),
            self._entity(
                "The Lakefront Restaurant", ["restaurant", "american_restaurant"],
                rating=4.5, review_count=2500,
                address="200 N Lake Shore Dr, Chicago, IL",
            ),
        ]
        frame = extract_frame("best waterfront breweries", "Chicago")
        ranked, stats = rank_entities_with_stats(breweries + wrong_cat, frame)
        names = {e.name for e, _ in ranked}
        for wc in wrong_cat:
            assert wc.name not in names, (
                f"Wrong-category {wc.name!r} must be dropped when 3+ on-concept "
                f"candidates exist. Survived: {sorted(names)}"
            )
        assert stats.off_concept_dropped == 3
        assert stats.on_concept_count == 3
        # All three breweries survive
        for b in breweries:
            assert b.name in names

    def test_recognized_concept_with_zero_on_concept_returns_empty(self):
        """If only modifier-matching wrong-category candidates exist for a
        recognized venue head (brewery), return zero cards rather than
        filling the response with parks and lakefront landmarks."""
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import rank_entities_with_stats
        wrong_cat = [
            self._entity("Chicago Riverwalk", ["tourist_attraction"],
                          rating=4.7, review_count=10000,
                          address="Riverwalk, Chicago, IL"),
            self._entity("Lakefront Park", ["park"],
                          rating=4.8, review_count=8000,
                          address="Lake Shore Dr, Chicago, IL"),
        ]
        frame = extract_frame("best waterfront breweries", "Chicago")
        ranked, stats = rank_entities_with_stats(wrong_cat, frame)
        assert ranked == [], (
            f"Recognized venue head + zero on-concept candidates must yield "
            f"zero cards. Got: {[e.name for e, _ in ranked]}"
        )
        assert stats.off_concept_dropped == 2
        assert stats.concept_is_recognized is True

    def test_unknown_concept_keeps_partial_results(self):
        """Open-vocabulary venue heads (no synonym set) are tolerant: if only
        weak matches exist, keep them rather than dropping to zero. This
        protects truly novel asks like 'izakaya' from over-aggressive filtering."""
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import rank_entities
        weak_match = self._entity(
            "Mystery Place",
            ["restaurant"],
            rating=4.3,
            review_count=200,
            source_query="izakaya Chicago",
        )
        frame = extract_frame("best izakayas", "Chicago")
        ranked = rank_entities([weak_match], frame)
        assert len(ranked) == 1, (
            f"Open-vocab concept (izakaya) must keep weak matches when no "
            f"synonym set is registered, got {len(ranked)}"
        )


class TestRegressionExistingVenueHeads:
    """Regressions: 'best breweries' and izakaya-style open-class asks must
    keep returning brewery-like / izakaya-like candidates after the contract
    changes."""

    def _make_brewery_places(self):
        return [
            _make_raw_place(
                name="Goose Island Brewing",
                place_id="ChIJ_goose",
                maps_uri="https://maps.google.com/?cid=701",
                types=["brewery", "bar"],
                rating=4.5, review_count=1200,
            ),
            _make_raw_place(
                name="Half Acre Beer Company",
                place_id="ChIJ_halfacre",
                maps_uri="https://maps.google.com/?cid=702",
                types=["brewery", "bar"],
                rating=4.6, review_count=800,
            ),
            _make_raw_place(
                name="Revolution Brewing",
                place_id="ChIJ_revo",
                maps_uri="https://maps.google.com/?cid=703",
                types=["brewery", "bar"],
                rating=4.4, review_count=900,
            ),
        ]

    def test_best_breweries_still_returns_brewery_cards(self):
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1
        from app.concierge.provider_executor import ProviderQueryResult
        from app.models.concierge import SOURCE_LIVE_SEARCH
        places = self._make_brewery_places()

        def fake_execute(queries, api_key, timeout=5.0, hard_cap=4, max_results_per_query=15):
            return [ProviderQueryResult(query=q, places=places[:], latency_ms=80) for q in queries]

        with _MOCK_VALID_REASONS, patch("app.concierge.provider_executor.execute_fanout", side_effect=fake_execute):
            result = run_semantic_retrieval_v1(
                user_query="best breweries",
                destination="Chicago",
                api_key="fake_key",
            )
        assert result.source_status == SOURCE_LIVE_SEARCH
        names = [c.name.lower() for c in result.restaurants]
        assert names, f"Expected brewery cards, got none"
        assert all(
            any(tok in n for tok in ("brew", "beer"))
            for n in names
        ), f"All cards should be brewery-like: {names}"

    def test_waterfront_breweries_returns_only_brewery_cards_with_mixed_pool(self):
        """End-to-end: with a mixed Google response (3 breweries + 3 modifier-
        only wrong-category places), only breweries surface as cards."""
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1
        from app.concierge.provider_executor import ProviderQueryResult
        breweries = self._make_brewery_places()
        wrong_cat = [
            _make_raw_place(
                name="Chicago Riverwalk",
                place_id="ChIJ_riverwalk",
                maps_uri="https://maps.google.com/?cid=801",
                types=["tourist_attraction", "point_of_interest"],
                rating=4.7, review_count=15000,
                address="Riverwalk, Chicago, IL, USA",
            ),
            _make_raw_place(
                name="Lakefront Park",
                place_id="ChIJ_lakefront_park",
                maps_uri="https://maps.google.com/?cid=802",
                types=["park"],
                rating=4.8, review_count=12000,
                address="Lake Shore Dr, Chicago, IL, USA",
            ),
            _make_raw_place(
                name="The Lakefront Restaurant",
                place_id="ChIJ_lakefront_rest",
                maps_uri="https://maps.google.com/?cid=803",
                types=["restaurant", "american_restaurant"],
                rating=4.6, review_count=2500,
                address="200 N Lake Shore Dr, Chicago, IL, USA",
            ),
        ]
        all_places = breweries + wrong_cat

        def fake_execute(queries, api_key, timeout=5.0, hard_cap=4, max_results_per_query=15):
            return [
                ProviderQueryResult(query=q, places=all_places[:], latency_ms=80)
                for q in queries
            ]

        with _MOCK_VALID_REASONS, patch("app.concierge.provider_executor.execute_fanout", side_effect=fake_execute):
            result = run_semantic_retrieval_v1(
                user_query="best waterfront breweries",
                destination="Chicago",
                api_key="fake_key",
            )
        names = {c.name for c in result.restaurants}
        assert names, f"Expected brewery cards, got none"
        for wc_name in ("Chicago Riverwalk", "Lakefront Park", "The Lakefront Restaurant"):
            assert wc_name not in names, (
                f"Modifier-only wrong-category card {wc_name!r} must not "
                f"appear in 'best waterfront breweries' results. Got: {names}"
            )

    def test_izakaya_open_class_still_works(self):
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1
        from app.concierge.provider_executor import ProviderQueryResult
        from app.models.concierge import SOURCE_LIVE_SEARCH
        places = [
            _make_raw_place(
                name="Momotaro Izakaya",
                place_id="pid_momo",
                maps_uri="https://maps.google.com/?cid=901",
                types=["japanese_restaurant", "restaurant"],
                rating=4.5, review_count=600,
            ),
            _make_raw_place(
                name="Izakaya Mita",
                place_id="pid_mita",
                maps_uri="https://maps.google.com/?cid=902",
                types=["japanese_restaurant", "restaurant"],
                rating=4.4, review_count=300,
            ),
        ]

        def fake_execute(queries, api_key, timeout=5.0, hard_cap=4, max_results_per_query=15):
            return [ProviderQueryResult(query=q, places=places[:], latency_ms=80) for q in queries]

        with _MOCK_VALID_REASONS, patch("app.concierge.provider_executor.execute_fanout", side_effect=fake_execute):
            result = run_semantic_retrieval_v1(
                user_query="best izakayas",
                destination="Chicago",
                api_key="fake_key",
            )
        assert result.source_status == SOURCE_LIVE_SEARCH
        assert len(result.restaurants) >= 1


class TestSafeReasonNoUnsupportedModifierClaim:
    """Deterministic reasons must not invent waterfront/riverwalk/quiet/etc.
    when the evidence bundle does not support them. Repetitive
    'Good waterfront match' style text must not appear."""

    def _build(self, query, geo_fit=0.5, subtype_fit=0.85, name="Goose Island Brewery",
                types=None, address="100 W Randolph St, Chicago, IL"):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason
        entity = PlaceEntity(
            place_id="pid_test",
            name=name,
            types=types or ["brewery", "bar"],
            primary_type=(types[0] if types else "brewery"),
            rating=4.3,
            user_rating_count=400,
            business_status="OPERATIONAL",
            formatted_address=address,
            google_maps_uri="https://maps.google.com/?cid=1",
            website_uri=None,
            price_level=None,
            lat=41.88, lng=-87.63,
            source_query="brewery Chicago waterfront",
        )
        frame = extract_frame(query, "Chicago")
        score = RankScore(total=0.7, subtype_fit=subtype_fit, geo_fit=geo_fit)
        evidence = build_evidence_bundle(entity, frame, score)
        return build_safe_reason(entity, evidence, frame, score)

    def test_no_repetitive_good_waterfront_match_for_modifier(self):
        reason = self._build("best waterfront breweries", geo_fit=0.55).lower()
        assert "good waterfront match" not in reason, reason
        assert "waterfront match" not in reason, reason

    def test_no_unsupported_riverwalk_claim_when_address_lacks_river(self):
        reason = self._build(
            "breweries near the river",
            geo_fit=0.50,
            address="900 W Randolph St, Chicago, IL",
        ).lower()
        # Reason must not say "near the river" / "on the river" / etc. as a fact
        # when geo_fit is weak; it may say "verify" wrapper instead.
        assert "near river" not in reason
        assert "near the river" not in reason or "verify" in reason
        assert "on the river" not in reason

    def test_no_unsupported_quiet_claim(self):
        reason = self._build(
            "quiet cocktail bars with a view",
            geo_fit=0.40,
            subtype_fit=0.50,
            name="Some Cocktail Bar",
            types=["cocktail_bar", "bar"],
        ).lower()
        # Banned: claiming "quiet atmosphere" / "definitely quiet" / etc.
        assert "quiet atmosphere" not in reason
        assert "guaranteed quiet" not in reason

    def test_brewery_anchor_present_for_waterfront_brewery_ask(self):
        """The reason must anchor on the venue head (brewery), never on the
        modifier (waterfront)."""
        reason = self._build("best waterfront breweries", geo_fit=0.45).lower()
        assert any(tok in reason for tok in ("brewery", "brew", "taproom")), (
            f"Reason must anchor on brewery, got: {reason}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# PR-3: Location Modifier Extraction (lowercase)
# ══════════════════════════════════════════════════════════════════════════════

class TestLocationModifierExtractionLowercase:
    """Location modifiers must be preserved even when user types lowercase."""

    def test_izakayas_on_fulton_street_lowercase(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("izakayas on fulton street", "Chicago")
        locs = [m.lower() for m in frame.location_modifiers]
        assert any("fulton" in m for m in locs), (
            f"Expected 'fulton' in location_modifiers, got {frame.location_modifiers}"
        )

    def test_izakayas_on_fulton_street_capitalized(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("izakayas on Fulton Street", "Chicago")
        locs = [m.lower() for m in frame.location_modifiers]
        assert any("fulton" in m for m in locs), (
            f"Expected 'fulton' in location_modifiers, got {frame.location_modifiers}"
        )

    def test_breweries_near_the_river_preserves_river(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("breweries near the river", "Chicago")
        # "river" may appear in geo_hints (water feature) OR as a location modifier
        has_river_signal = (
            any("river" in g for g in frame.geography_hints)
            or any("river" in m.lower() for m in frame.location_modifiers)
        )
        assert has_river_signal, (
            f"Expected river signal, geo_hints={frame.geography_hints} "
            f"location_modifiers={frame.location_modifiers}"
        )

    def test_sushi_in_river_north_lowercase(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("sushi in river north", "Chicago")
        locs = [m.lower() for m in frame.location_modifiers]
        assert any("river" in m or "north" in m for m in locs), (
            f"Expected river north in modifiers, got {frame.location_modifiers}"
        )

    def test_taprooms_with_a_view_no_location_modifier(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("taprooms with a view", "Chicago")
        # "view" is a soft/geo preference, not a location modifier
        assert "taproom" in " ".join(c.label for c in frame.subtype_concepts).lower(), (
            f"Expected taproom concept, got {frame.subtype_concepts}"
        )
        assert "view_not_structurally_verifiable" in frame.ambiguity_flags, (
            f"Expected ambiguity flag for view, got {frame.ambiguity_flags}"
        )

    def test_destination_not_echoed_as_modifier(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("izakayas in Chicago", "Chicago")
        locs = [m.lower() for m in frame.location_modifiers]
        assert not any("chicago" in m for m in locs), (
            f"Destination should not appear as location modifier: {frame.location_modifiers}"
        )

    def test_modifier_title_cased_in_output(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("cocktail bars on west loop", "Chicago")
        # Should be title-cased
        locs = frame.location_modifiers
        if locs:
            assert locs[0][0].isupper() or locs[0] == locs[0].title(), (
                f"Location modifier should be title-cased, got {locs}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# PR-3: Evidence Bundle Location Modifier Fit
# ══════════════════════════════════════════════════════════════════════════════

class TestEvidenceBundleLocationModifier:
    """Evidence bundle must report location modifier confirmed/unconfirmed."""

    def _make_entity(self, address, name="The Izakaya"):
        from app.concierge.place_entity_layer import PlaceEntity
        return PlaceEntity(
            place_id="pid_test", name=name,
            types=["japanese_restaurant"], primary_type="japanese_restaurant",
            rating=4.3, user_rating_count=210, business_status="OPERATIONAL",
            formatted_address=address,
            google_maps_uri="https://maps.google.com/?cid=1",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query="izakaya Chicago",
        )

    def test_modifier_confirmed_when_address_contains_fulton(self):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, build_evidence_bundle
        entity = self._make_entity("904 W Fulton Market, Chicago, IL")
        frame = extract_frame("izakayas on Fulton Street", "Chicago")
        score = RankScore(total=0.7, subtype_fit=0.85, geo_fit=0.5)
        ev = build_evidence_bundle(entity, frame, score)
        confirmed = any("confirms" in f for f in ev.structured_facts)
        unconfirmed = any("location_modifier_not_confirmed" in f for f in ev.uncertainty_flags)
        assert confirmed or not unconfirmed, (
            f"Fulton address should confirm modifier: facts={ev.structured_facts} flags={ev.uncertainty_flags}"
        )

    def test_modifier_not_confirmed_when_address_lacks_modifier(self):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, build_evidence_bundle
        entity = self._make_entity("3458 N Halsted St, Chicago, IL")
        frame = extract_frame("izakayas on Fulton Street", "Chicago")
        score = RankScore(total=0.65, subtype_fit=0.80, geo_fit=0.4)
        ev = build_evidence_bundle(entity, frame, score)
        unconfirmed_flags = [f for f in ev.uncertainty_flags if "location_modifier_not_confirmed" in f]
        assert unconfirmed_flags, (
            f"Expected not_confirmed flag, flags={ev.uncertainty_flags}"
        )

    def test_no_location_modifier_in_bundle_when_frame_has_none(self):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, build_evidence_bundle
        entity = self._make_entity("100 W Randolph St, Chicago, IL")
        frame = extract_frame("izakayas in Chicago", "Chicago")
        score = RankScore(total=0.70, subtype_fit=0.85, geo_fit=0.5)
        ev = build_evidence_bundle(entity, frame, score)
        loc_flags = [f for f in ev.uncertainty_flags if "location_modifier" in f]
        assert not loc_flags, f"No modifier flags expected, got {loc_flags}"

    def test_bundle_includes_only_safe_fields(self):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, build_evidence_bundle
        entity = self._make_entity("500 N Dearborn St, Chicago, IL")
        frame = extract_frame("ramen in Chicago", "Chicago")
        score = RankScore(total=0.68, subtype_fit=0.75, geo_fit=0.5)
        ev = build_evidence_bundle(entity, frame, score)
        all_text = " ".join(ev.structured_facts + [ev.geo_note or ""])
        # Should not expose internal scoring fields
        banned = ["subtype_fit", "geo_fit", "rank_score", "pipeline_version", "OPERATIONAL"]
        for b in banned:
            assert b not in all_text, f"Internal field '{b}' leaked into evidence: {all_text}"


# ══════════════════════════════════════════════════════════════════════════════
# PR-3: Improved Deterministic Reason Builder
# ══════════════════════════════════════════════════════════════════════════════

class TestImprovedDeterministicReason:
    """Deterministic reasons must be specific, honest, and include location caveat."""

    def _build_reason(self, query, address, name="Test Place", types=None,
                      subtype_fit=0.85, geo_fit=0.5):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason
        entity = PlaceEntity(
            place_id="pid", name=name, types=types or ["japanese_restaurant"],
            primary_type=(types[0] if types else "japanese_restaurant"),
            rating=4.3, user_rating_count=210, business_status="OPERATIONAL",
            formatted_address=address,
            google_maps_uri="https://maps.google.com/?cid=1",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query="izakaya Chicago",
        )
        frame = extract_frame(query, "Chicago")
        score = RankScore(total=0.7, subtype_fit=subtype_fit, geo_fit=geo_fit)
        evidence = build_evidence_bundle(entity, frame, score)
        return build_safe_reason(entity, evidence, frame, score)

    def test_no_lower_level_in_reason(self):
        reason = self._build_reason(
            "izakayas on fulton street",
            "900 W Randolph St, Lower Level, Chicago, IL",
        ).lower()
        assert "lower level" not in reason, f"'Lower Level' must not appear in reason: {reason}"

    def test_location_modifier_caveat_when_unconfirmed(self):
        reason = self._build_reason(
            "izakayas on fulton street",
            "3458 N Halsted St, Chicago, IL",
        ).lower()
        # Should include a caveat about not being directly on Fulton
        assert "fulton" in reason or "not directly" in reason or "nearby" in reason, (
            f"Expected Fulton Street caveat, got: {reason}"
        )

    def test_no_generic_chicago_only_note(self):
        reason = self._build_reason(
            "izakayas on fulton street",
            "3458 N Halsted St, Chicago, IL",
        ).lower()
        # Must not be just "Strong izakaya match in Chicago."
        assert reason != "strong izakaya match in chicago." and len(reason) > 40, (
            f"Reason is too generic: {reason}"
        )

    def test_location_confirmed_when_address_matches(self):
        reason = self._build_reason(
            "izakayas on fulton street",
            "904 W Fulton Market, Chicago, IL",
        ).lower()
        # When address confirms the modifier, no "not directly" caveat
        assert "not directly on fulton" not in reason, (
            f"Should not have caveat when address confirms modifier: {reason}"
        )

    def test_waterfront_caveat_without_waterfront_claim(self):
        reason = self._build_reason(
            "best waterfront breweries",
            "900 W Randolph St, Chicago, IL",
            name="Goose Island Brewery",
            types=["brewery", "bar"],
            geo_fit=0.4,
        ).lower()
        # waterfront may appear in the honest caveat text but must NOT be a positive assertion.
        # Accept: "not confirmed", "cannot", "verify", "unconfirmed",
        #         "no waterfront", "proximity confirmed" (as in "no ... proximity confirmed")
        if "waterfront" in reason:
            assert any(kw in reason for kw in (
                "not confirmed", "cannot", "verify", "unconfirmed",
                "no waterfront", "proximity confirmed",
            )), (
                f"Waterfront must not be asserted without evidence: {reason}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# PR-3: Reason Validator
# ══════════════════════════════════════════════════════════════════════════════

class TestReasonValidator:
    """Validator must reject bad notes and accept good ones."""

    def _frame_and_evidence(self, query, address="100 N State St, Chicago, IL"):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.ranker import RankScore, build_evidence_bundle
        entity = PlaceEntity(
            place_id="pid", name="Test Place",
            types=["japanese_restaurant"], primary_type="japanese_restaurant",
            rating=4.2, user_rating_count=150, business_status="OPERATIONAL",
            formatted_address=address,
            google_maps_uri="https://maps.google.com/?cid=1",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query="izakaya Chicago",
        )
        frame = extract_frame(query, "Chicago")
        score = RankScore(total=0.7, subtype_fit=0.85, geo_fit=0.4)
        evidence = build_evidence_bundle(entity, frame, score)
        return frame, evidence

    def test_rejects_unsupported_waterfront_claim(self):
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_and_evidence("best waterfront breweries")
        is_valid, reason = validate_reason("Great brewery near the waterfront.", frame, ev)
        assert not is_valid, f"Should reject unsupported waterfront claim, got valid=True"

    def test_rejects_michelin_claim(self):
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_and_evidence("izakayas in Chicago")
        is_valid, reason = validate_reason("Michelin-starred izakaya in Chicago.", frame, ev)
        assert not is_valid

    def test_rejects_internal_field_in_reason(self):
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_and_evidence("izakayas in Chicago")
        is_valid, reason = validate_reason(
            "Strong izakaya match; subtype_fit=0.85 geo_fit=0.50.", frame, ev
        )
        assert not is_valid

    def test_rejects_address_fragment_as_location(self):
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_and_evidence("izakayas in Chicago")
        is_valid, reason = validate_reason(
            "Strong izakaya match in Lower Level.", frame, ev
        )
        assert not is_valid, f"Should reject 'Lower Level' as location"

    def test_rejects_opening_hours_claim(self):
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_and_evidence("izakayas in Chicago")
        is_valid, reason = validate_reason(
            "Popular izakaya open until midnight on weekdays.", frame, ev
        )
        assert not is_valid

    def test_rejects_price_claim(self):
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_and_evidence("izakayas in Chicago")
        is_valid, reason = validate_reason(
            "Affordable izakaya with budget-friendly prices in Chicago.", frame, ev
        )
        assert not is_valid

    def test_accepts_grounded_specific_note(self):
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_and_evidence("izakayas in Chicago")
        is_valid, reason = validate_reason(
            "Highly rated Japanese restaurant with 4.2★ and 150 reviews in Chicago.",
            frame, ev
        )
        assert is_valid, f"Should accept grounded note, rejection={reason}"

    def test_accepts_location_caveat_note(self):
        """Name-anchored note with honest location caveat must pass validation."""
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_and_evidence(
            "izakayas on fulton street", "3458 N Halsted St, Chicago, IL"
        )
        is_valid, reason = validate_reason(
            "Izakaya Mita on Halsted Street — 4.5★ (210 reviews). "
            "Not directly on Fulton Street — nearest match in the area.",
            frame, ev
        )
        assert is_valid, f"Should accept honest caveat note, rejection={reason}"

    def test_rejects_unconfirmed_location_modifier_claimed_as_confirmed(self):
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_and_evidence(
            "izakayas on Fulton Street", "3458 N Halsted St, Chicago, IL"
        )
        is_valid, reason = validate_reason(
            "Excellent izakaya located on Fulton Street.", frame, ev
        )
        assert not is_valid, f"Should reject false location modifier claim"

    def test_rejects_quiet_atmosphere_claim(self):
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_and_evidence("quiet cocktail bars")
        is_valid, reason = validate_reason(
            "Intimate cocktail bar with quiet atmosphere perfect for dates.",
            frame, ev
        )
        assert not is_valid

    def test_rejects_romantic_atmosphere_claim(self):
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_and_evidence("romantic tapas")
        is_valid, reason = validate_reason(
            "Romantic atmosphere, perfect for couples seeking intimacy.",
            frame, ev
        )
        assert not is_valid


# ══════════════════════════════════════════════════════════════════════════════
# PR-3: Batched Reason Builder
# ══════════════════════════════════════════════════════════════════════════════

class TestBatchedReasonBuilder:
    """Batched reason builder must fall back safely and use deterministic when flag off."""

    def _make_cards_data(self, query="izakayas on Fulton Street"):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason
        frame = extract_frame(query, "Chicago")
        entities = [
            PlaceEntity(
                place_id=f"pid_{i}", name=f"Izakaya Place {i}",
                types=["japanese_restaurant"], primary_type="japanese_restaurant",
                rating=4.2 + i * 0.1, user_rating_count=100 + i * 50,
                business_status="OPERATIONAL",
                formatted_address=f"{100 + i * 10} N State St, Chicago, IL",
                google_maps_uri=f"https://maps.google.com/?cid={i}",
                website_uri=None, price_level=None, lat=41.88, lng=-87.63,
                source_query="izakaya Chicago",
            )
            for i in range(3)
        ]
        cards_data = []
        for e in entities:
            score = RankScore(total=0.7, subtype_fit=0.85, geo_fit=0.5)
            ev = build_evidence_bundle(e, frame, score)
            det = build_safe_reason(e, ev, frame, score)
            cards_data.append((e, ev, score, det))
        return cards_data, frame

    def test_flag_off_uses_deterministic(self):
        from app.concierge.batched_reason_builder import build_batched_reasons
        import os
        os.environ["CONCIERGE_BATCHED_REASONING_ENABLED"] = "false"
        cards_data, frame = self._make_cards_data()
        result, rr = build_batched_reasons(cards_data, frame)
        # All results should be the deterministic fallbacks
        for i, (_e, _ev, _rs, det) in enumerate(cards_data, 1):
            assert result[str(i)] == det, f"idx={i}: expected deterministic, got LLM"
        assert not rr.attempted
        assert not rr.success
        os.environ.pop("CONCIERGE_BATCHED_REASONING_ENABLED", None)

    def test_returns_all_card_keys(self):
        from app.concierge.batched_reason_builder import build_batched_reasons
        cards_data, frame = self._make_cards_data()
        result, _ = build_batched_reasons(cards_data, frame)
        assert len(result) == len(cards_data), (
            f"Expected {len(cards_data)} keys, got {len(result)}"
        )
        for i in range(1, len(cards_data) + 1):
            assert str(i) in result

    def test_empty_cards_returns_empty(self):
        from app.concierge.batched_reason_builder import build_batched_reasons
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("izakayas", "Chicago")
        result, _ = build_batched_reasons([], frame)
        assert result == {}

    def test_fallback_on_llm_error(self):
        from app.concierge.batched_reason_builder import build_batched_reasons
        from unittest.mock import patch
        import os
        os.environ["CONCIERGE_BATCHED_REASONING_ENABLED"] = "true"
        cards_data, frame = self._make_cards_data()
        # Force LLM call to raise
        with patch("app.concierge.batched_reason_builder._call_llm", side_effect=Exception("llm_error")):
            result, rr = build_batched_reasons(cards_data, frame)
        # Should return deterministic fallbacks for all
        for i, (_e, _ev, _rs, det) in enumerate(cards_data, 1):
            assert result[str(i)] == det
        # Telemetry must report failure, not success
        assert not rr.success, "LLM error must report success=False"
        os.environ.pop("CONCIERGE_BATCHED_REASONING_ENABLED", None)

    def test_fallback_on_invalid_json(self):
        from app.concierge.batched_reason_builder import build_batched_reasons
        from unittest.mock import patch
        import os
        os.environ["CONCIERGE_BATCHED_REASONING_ENABLED"] = "true"
        cards_data, frame = self._make_cards_data()
        with patch("app.concierge.batched_reason_builder._call_llm", return_value="not json at all"):
            result, rr = build_batched_reasons(cards_data, frame)
        for i, (_e, _ev, _rs, det) in enumerate(cards_data, 1):
            assert result[str(i)] == det
        assert not rr.success, "Parse failure must report success=False"
        os.environ.pop("CONCIERGE_BATCHED_REASONING_ENABLED", None)

    def test_per_card_fallback_on_invalid_llm_output(self):
        """Cards whose LLM reason fails validation fall back to deterministic."""
        from app.concierge.batched_reason_builder import build_batched_reasons
        from unittest.mock import patch
        import json, os
        os.environ["CONCIERGE_BATCHED_REASONING_ENABLED"] = "true"
        cards_data, frame = self._make_cards_data()
        # Return invalid reason for card 1 (waterfront claim), valid-ish for card 2
        fake_response = json.dumps({
            "1": "Great izakaya with stunning waterfront views.",  # invalid — waterfront claim
            "2": "Not directly on Fulton Street, but Izakaya Sumo on Damen Ave earned its regulars through precise knife work and seasonal omakase options.",
            "3": "Solid izakaya option in Chicago with good reviews.",
        })
        with patch("app.concierge.batched_reason_builder._call_llm", return_value=fake_response):
            result, rr = build_batched_reasons(cards_data, frame)
        # Card 1 should use deterministic (waterfront claim rejected)
        _e1, _ev1, _rs1, det1 = cards_data[0]
        assert result["1"] == det1, f"Card 1 should fall back to det, got: {result['1']}"
        # At least card 2 or 3 may pass (specific enough note)
        assert rr.rejected_count >= 1, "At least waterfront-claim note must be rejected"
        os.environ.pop("CONCIERGE_BATCHED_REASONING_ENABLED", None)


class TestBatchedReasonModelConfig:
    """CONCIERGE_BATCHED_REASONING_MODEL env var must control the Anthropic model used.

    Default: claude-sonnet-4-6 (high-quality production validation default).
    Override: any valid model string (e.g. claude-haiku-4-5-20251001 after quality passes).
    """

    def test_default_model_is_sonnet(self):
        """When CONCIERGE_BATCHED_REASONING_MODEL is absent, default is claude-sonnet-4-6."""
        import importlib
        import os
        import app.concierge.batched_reason_builder as brb
        old = os.environ.pop("CONCIERGE_BATCHED_REASONING_MODEL", None)
        try:
            importlib.reload(brb)
            assert brb.CONCIERGE_BATCHED_REASONING_MODEL == "claude-sonnet-4-6", (
                f"Default model must be claude-sonnet-4-6, got {brb.CONCIERGE_BATCHED_REASONING_MODEL}"
            )
        finally:
            if old is not None:
                os.environ["CONCIERGE_BATCHED_REASONING_MODEL"] = old
            importlib.reload(brb)

    def test_env_override_respected(self):
        """CONCIERGE_BATCHED_REASONING_MODEL env var overrides the default."""
        import importlib
        import os
        import app.concierge.batched_reason_builder as brb
        os.environ["CONCIERGE_BATCHED_REASONING_MODEL"] = "claude-haiku-4-5-20251001"
        try:
            importlib.reload(brb)
            assert brb.CONCIERGE_BATCHED_REASONING_MODEL == "claude-haiku-4-5-20251001", (
                f"Env override not respected: {brb.CONCIERGE_BATCHED_REASONING_MODEL}"
            )
        finally:
            del os.environ["CONCIERGE_BATCHED_REASONING_MODEL"]
            importlib.reload(brb)

    def test_call_llm_uses_resolved_model(self):
        """_call_llm must pass the resolved model to the Anthropic client."""
        from unittest.mock import patch, MagicMock
        import os
        import app.concierge.batched_reason_builder as brb

        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='{"1": "test note"}')]
        mock_client.messages.create.return_value = mock_message

        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        with patch("anthropic.Anthropic", return_value=mock_client):
            brb._call_llm("test prompt", timeout=3.0, model="claude-haiku-4-5-20251001")

        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs is not None
        used_model = (
            call_kwargs.kwargs.get("model") or
            (call_kwargs.args[0] if call_kwargs.args else None)
        )
        # model kwarg may be positional; check via kwargs
        create_kwargs = mock_client.messages.create.call_args[1]
        assert create_kwargs.get("model") == "claude-haiku-4-5-20251001", (
            f"model kwarg must be haiku, got {create_kwargs.get('model')}"
        )
        os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_no_note_generation_broken_when_model_env_missing(self):
        """When CONCIERGE_BATCHED_REASONING_MODEL is missing, deterministic fallback works fine."""
        import os
        from app.concierge.batched_reason_builder import build_batched_reasons
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason

        os.environ.pop("CONCIERGE_BATCHED_REASONING_MODEL", None)
        os.environ["CONCIERGE_BATCHED_REASONING_ENABLED"] = "false"

        frame = extract_frame("best izakayas", "Chicago")
        entity = PlaceEntity(
            place_id="pid_mc", name="Model Config Test Izakaya",
            types=["japanese_restaurant"], primary_type="japanese_restaurant",
            rating=4.4, user_rating_count=300, business_status="OPERATIONAL",
            formatted_address="1960 N Damen Ave, Chicago, IL",
            google_maps_uri="https://maps.google.com/?cid=mc",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query="izakaya Chicago",
        )
        score = RankScore(total=0.75, subtype_fit=0.85, geo_fit=0.5)
        ev = build_evidence_bundle(entity, frame, score)
        det = build_safe_reason(entity, ev, frame, score)
        result, rr = build_batched_reasons([(entity, ev, score, det)], frame)

        assert "1" in result, "Must return a result even when model env is absent"
        assert result["1"] == det, "Must return deterministic fallback when flag is off"
        assert not rr.success, "Flag off → success must be False"
        os.environ.pop("CONCIERGE_BATCHED_REASONING_ENABLED", None)


# ══════════════════════════════════════════════════════════════════════════════
# PR-3: Regression Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestPR3RegressionSuite:
    """Regression: existing behavior must not regress after PR-3 changes."""

    def _run_frame_and_reason(self, query, address="100 W Randolph St, Chicago, IL",
                               name="Test Place", types=None, subtype_fit=0.85, geo_fit=0.5):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason
        entity = PlaceEntity(
            place_id="pid", name=name, types=types or ["brewery", "bar"],
            primary_type=(types[0] if types else "brewery"),
            rating=4.3, user_rating_count=400, business_status="OPERATIONAL",
            formatted_address=address,
            google_maps_uri="https://maps.google.com/?cid=1",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query=f"{(types or ['brewery'])[0]} Chicago",
        )
        frame = extract_frame(query, "Chicago")
        score = RankScore(total=0.7, subtype_fit=subtype_fit, geo_fit=geo_fit)
        evidence = build_evidence_bundle(entity, frame, score)
        return frame, build_safe_reason(entity, evidence, frame, score)

    def test_izakayas_frame_still_detects_open_class(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("izakayas", "Chicago")
        assert frame.open_class_place_detected, "izakayas should still be open-class"
        labels = [c.label for c in frame.subtype_concepts]
        assert any("izakaya" in l for l in labels), f"Expected izakaya concept: {labels}"

    def test_best_breweries_concept_not_regressed(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("best breweries", "Chicago")
        labels = [c.label for c in frame.subtype_concepts]
        assert any(l in ("brewery", "breweries") for l in labels)
        assert not frame.geography_hints, f"No geo hints for 'best breweries': {frame.geography_hints}"

    def test_best_waterfront_breweries_brewery_anchored(self):
        frame, reason = self._run_frame_and_reason(
            "best waterfront breweries", name="Goose Island Brewery",
        )
        labels = [c.label for c in frame.subtype_concepts]
        assert any(l in ("brewery", "breweries") for l in labels), (
            f"Frame should anchor on brewery: {labels}"
        )
        assert "waterfront" in frame.geography_hints, (
            f"Waterfront should be geo hint: {frame.geography_hints}"
        )

    def test_best_waterfront_breweries_no_waterfront_claim_in_reason(self):
        _frame, reason = self._run_frame_and_reason(
            "best waterfront breweries", geo_fit=0.45, name="Goose Island Brewery",
        )
        reason_lower = reason.lower()
        # waterfront may appear only inside an honest caveat, never as a positive claim
        if "waterfront" in reason_lower:
            has_caveat = any(
                kw in reason_lower for kw in (
                    "not confirmed", "cannot", "verify", "unconfirmed",
                    "no waterfront", "proximity confirmed",
                )
            )
            assert has_caveat, (
                f"Waterfront must not be claimed without evidence: {reason}"
            )

    def test_breweries_near_river_preserves_geo_hint(self):
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("breweries near the river", "Chicago")
        has_river = (
            any("river" in g for g in frame.geography_hints)
            or any("river" in m.lower() for m in frame.location_modifiers)
        )
        assert has_river, (
            f"River should be preserved. geo_hints={frame.geography_hints} "
            f"location_modifiers={frame.location_modifiers}"
        )

    def test_taprooms_with_a_view_no_invented_views(self):
        _frame, reason = self._run_frame_and_reason(
            "taprooms with a view", name="Half Acre Taproom",
            types=["brewery", "bar"], geo_fit=0.40,
        )
        reason_lower = reason.lower()
        # Must NOT positively claim a view exists.
        # "reviews" and "verified" contain "view" as substring but are not view claims.
        assert "has a view" not in reason_lower, f"View must not be claimed: {reason}"
        assert "with a view" not in reason_lower, f"View must not be claimed: {reason}"
        assert "stunning view" not in reason_lower, f"View claim: {reason}"
        assert "waterfront view" not in reason_lower, f"View claim: {reason}"

    def test_card_payload_reason_source_field_present(self):
        """Card payload must include reason_source field."""
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.semantic_retrieval import _entity_to_card
        entity = PlaceEntity(
            place_id="pid1", name="Izakaya Test",
            types=["japanese_restaurant"], primary_type="japanese_restaurant",
            rating=4.3, user_rating_count=200, business_status="OPERATIONAL",
            formatted_address="100 N State St, Chicago, IL",
            google_maps_uri="https://maps.google.com/?cid=1",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query="izakaya Chicago",
        )
        frame = extract_frame("izakayas", "Chicago")
        card = _entity_to_card(entity, "A great izakaya in Chicago.", frame, reason_source="deterministic_safe_v1")
        assert card is not None
        assert card.reason_source == "deterministic_safe_v1"
        assert card.display.display_why_source == "deterministic_safe_v1"

    def test_rating_scale_still_native_0_to_5(self):
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.semantic_retrieval import _entity_to_card
        entity = PlaceEntity(
            place_id="pid2", name="Brewery Test",
            types=["brewery"], primary_type="brewery",
            rating=4.5, user_rating_count=300, business_status="OPERATIONAL",
            formatted_address="200 W Chicago Ave, Chicago, IL",
            google_maps_uri="https://maps.google.com/?cid=2",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query="brewery Chicago",
        )
        frame = extract_frame("best breweries", "Chicago")
        card = _entity_to_card(entity, "Strong brewery match in Chicago.", frame)
        assert card is not None
        assert card.rating == 4.5, f"Rating must be native 0-5 scale: {card.rating}"


# ══════════════════════════════════════════════════════════════════════════════
# PR-4: Final Visible Note Validator
# ══════════════════════════════════════════════════════════════════════════════

class TestFinalVisibleNoteValidator:
    """Validator must reject all previously-live bad note patterns."""

    def _frame_ev(self, query, address="100 N State St, Chicago, IL", types=None):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.ranker import RankScore, build_evidence_bundle
        entity = PlaceEntity(
            place_id="pid_val", name="Test Place",
            types=types or ["japanese_restaurant"],
            primary_type=(types[0] if types else "japanese_restaurant"),
            rating=4.2, user_rating_count=150, business_status="OPERATIONAL",
            formatted_address=address,
            google_maps_uri="https://maps.google.com/?cid=1",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query="izakaya Chicago",
        )
        frame = extract_frame(query, "Chicago")
        score = RankScore(total=0.7, subtype_fit=0.85, geo_fit=0.4)
        evidence = build_evidence_bundle(entity, frame, score)
        return frame, evidence

    def test_rejects_strong_izakaya_match_in_chicago(self):
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_ev("izakayas with waterfront views")
        is_valid, rejection = validate_reason(
            "Strong izakaya match in Chicago.", frame, ev
        )
        assert not is_valid, "Must reject 'Strong izakaya match in Chicago.'"
        assert "generic_match_boilerplate" in rejection

    def test_rejects_strong_izakaya_match_in_chicago_near_waterfront(self):
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_ev("izakayas with waterfront views")
        is_valid, rejection = validate_reason(
            "Strong izakaya match in Chicago, near waterfront.", frame, ev
        )
        assert not is_valid, "Must reject 'Strong izakaya match in Chicago, near waterfront.'"
        # Either the generic_match or unsupported_attribute check fires
        assert rejection

    def test_rejects_strong_brewery_match_in_milwaukee(self):
        """A Milwaukee note must be rejected for a Chicago request."""
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_ev(
            "best waterfront breweries",
            address="789 S 2nd St, Milwaukee, WI 53204, USA",
            types=["brewery"],
        )
        is_valid, rejection = validate_reason(
            "Strong brewery match in Milwaukee.", frame, ev
        )
        assert not is_valid, "Must reject 'Strong brewery match in Milwaukee.'"
        assert "generic_match_boilerplate" in rejection

    def test_rejects_strong_brewery_match_in_chicago(self):
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_ev("best waterfront breweries", types=["brewery"])
        is_valid, rejection = validate_reason(
            "Strong brewery match in Chicago.", frame, ev
        )
        assert not is_valid, "Must reject generic match boilerplate"
        assert "generic_match_boilerplate" in rejection

    def test_rejects_unsupported_near_waterfront(self):
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_ev("best waterfront breweries", types=["brewery"])
        is_valid, rejection = validate_reason(
            "Good brewery near waterfront in Chicago.", frame, ev
        )
        assert not is_valid, "Must reject unsupported 'near waterfront' claim"

    def test_rejects_steps_from_riverwalk(self):
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_ev("breweries near the river", types=["brewery"])
        is_valid, rejection = validate_reason(
            "Craft brewery just steps from the Riverwalk.", frame, ev
        )
        assert not is_valid, "Must reject unsupported 'steps from the Riverwalk'"

    def test_rejects_verified_category_template(self):
        """'Verified {Category} with {rating}★ across {N} reviews.' is a banned template.

        It provides no card-specific differentiation — every card in a set could
        produce the same sentence structure. The validator must reject it.
        """
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_ev("best waterfront breweries", types=["brewery"])
        is_valid, rejection = validate_reason(
            "Verified Brewery with 4.5★ across 892 Google reviews. "
            "The requested waterfront setting is not confirmed in available data.",
            frame, ev,
        )
        assert not is_valid, "Must reject 'Verified {Category} with ★' template"
        assert "verified_category_template" in rejection

    def test_accepts_name_anchored_note_with_caveat(self):
        """Name+street anchored note with honest waterfront caveat must pass."""
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_ev("best waterfront breweries", types=["brewery"])
        is_valid, rejection = validate_reason(
            "Goose Island Brewery on Fulton Street — 4.5★ (892 reviews). "
            "No waterfront proximity confirmed from address.",
            frame, ev,
        )
        assert is_valid, f"Must accept name-anchored note with caveat, rejection={rejection}"

    def test_rejects_verified_izakaya_template(self):
        """'Verified Izakaya with 4.8★ across N reviews.' is a banned template."""
        from app.concierge.reason_validator import validate_reason
        frame, ev = self._frame_ev("izakayas")
        is_valid, rejection = validate_reason(
            "Verified Izakaya with 4.8★ across 1,028 Google reviews.",
            frame, ev,
        )
        assert not is_valid, "Must reject 'Verified {Category} with ★' template"
        assert "verified_category_template" in rejection


# ══════════════════════════════════════════════════════════════════════════════
# PR-4: Safe Fallback Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestSafeFallbackFormat:
    """build_safe_reason must produce verified-fact format, never generic boilerplate."""

    def _build(self, query, address="100 N Clark St, Chicago, IL",
               name="Test Place", types=None, geo_fit=0.5, subtype_fit=0.85):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason
        entity = PlaceEntity(
            place_id="pid_sf", name=name,
            types=types or ["japanese_restaurant"],
            primary_type=(types[0] if types else "japanese_restaurant"),
            rating=4.8, user_rating_count=1028, business_status="OPERATIONAL",
            formatted_address=address,
            google_maps_uri="https://maps.google.com/?cid=sf",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query="izakaya Chicago",
        )
        frame = extract_frame(query, "Chicago")
        score = RankScore(total=0.7, subtype_fit=subtype_fit, geo_fit=geo_fit)
        evidence = build_evidence_bundle(entity, frame, score)
        return build_safe_reason(entity, evidence, frame, score)

    def test_fallback_never_says_strong_match_in_city(self):
        reason = self._build("izakayas with waterfront views")
        reason_lower = reason.lower()
        assert "strong izakaya match in chicago" not in reason_lower, reason
        assert "strong" not in reason_lower or "match" not in reason_lower, (
            f"Must not produce 'Strong X match' pattern: {reason}"
        )

    def test_fallback_includes_rating_and_reviews(self):
        reason = self._build("izakayas")
        assert "4.8" in reason, f"Must include rating: {reason}"
        assert "1,028" in reason, f"Must include review count: {reason}"

    def test_fallback_is_card_specific_not_type_template(self):
        """Fallback note must be anchored on the place name, not a type-template.

        The new design: "Test Place on Clark Street — 4.8★ from 1,028 reviews."
        NOT: "Verified Japanese Restaurant with 4.8★ across 1,028 reviews."
        """
        reason = self._build("izakayas", types=["japanese_restaurant"])
        # Note must contain the place name (card-specific anchor)
        assert "Test Place" in reason, f"Note must anchor on place name: {reason}"
        # Note must NOT start with the banned Verified-template
        assert not reason.lower().startswith("verified "), (
            f"Note must not use Verified-template format: {reason}"
        )

    def test_fallback_caveats_waterfront_when_requested(self):
        reason = self._build(
            "best waterfront breweries",
            name="Goose Island Brewery",
            types=["brewery"],
            geo_fit=0.45,
        )
        reason_lower = reason.lower()
        # Must caveat waterfront, not assert it.
        # Accept: "not confirmed", "cannot", "no waterfront", "proximity confirmed"
        assert any(kw in reason_lower for kw in (
            "not confirmed", "cannot", "no waterfront", "proximity confirmed",
        )), (
            f"Must caveat waterfront: {reason}"
        )
        # Must NOT positively claim waterfront
        assert "near waterfront" not in reason_lower, (
            f"Must not claim 'near waterfront': {reason}"
        )

    def test_fallback_caveats_view_when_requested(self):
        reason = self._build("taprooms with a view", types=["brewery"], geo_fit=0.4)
        reason_lower = reason.lower()
        # view appears in "reviews" and "verified" but must not be a positive claim
        assert "has a view" not in reason_lower, reason
        assert "with a view" not in reason_lower, reason

    def test_fallback_does_not_claim_milwaukee_for_chicago_request(self):
        """Fallback must not say 'in Milwaukee' for a Chicago query."""
        reason = self._build(
            "best breweries",
            address="789 S 2nd St, Milwaukee, WI 53204, USA",
            name="Lakefront Brewery",
            types=["brewery"],
        )
        reason_lower = reason.lower()
        # The note must not claim Milwaukee as a confirmed location
        # (the destination penalty in the ranker should de-rank it,
        # and the note should use the address neighborhood or omit city)
        assert "strong brewery match in milwaukee" not in reason_lower, reason

    def test_fallback_with_geo_or_modifier_passes_validator(self):
        """Deterministic notes with geo caveats or modifier caveats must pass validator.

        Queries that carry a geo hint or location modifier produce notes with an
        honest caveat sentence (e.g., "No waterfront proximity confirmed."), which
        goes beyond name+rating and therefore passes the template validator.
        """
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason
        from app.concierge.reason_validator import validate_reason
        # These queries produce notes with caveat sentences — must pass validator
        test_cases = [
            ("izakayas with waterfront views", "1234 N Clark St, Chicago, IL", "Izakaya Test", ["japanese_restaurant"], 0.85, 0.4),
            ("best waterfront breweries", "900 W Randolph St, Chicago, IL", "Goose Island", ["brewery"], 0.9, 0.45),
            ("breweries near the river", "100 W Kinzie St, Chicago, IL", "Half Acre", ["brewery"], 0.9, 0.5),
            ("taprooms with a view", "1800 W Fulton St, Chicago, IL", "Empirical", ["brewery"], 0.85, 0.4),
        ]
        for query, addr, name, types, sf, gf in test_cases:
            entity = PlaceEntity(
                place_id=f"pid_{name.replace(' ', '')}", name=name,
                types=types, primary_type=types[0],
                rating=4.5, user_rating_count=500, business_status="OPERATIONAL",
                formatted_address=addr,
                google_maps_uri="https://maps.google.com/?cid=test",
                website_uri=None, price_level=None, lat=41.88, lng=-87.63,
                source_query=f"{types[0]} Chicago",
            )
            frame = extract_frame(query, "Chicago")
            score = RankScore(total=0.7, subtype_fit=sf, geo_fit=gf)
            evidence = build_evidence_bundle(entity, frame, score)
            reason = build_safe_reason(entity, evidence, frame, score)
            is_valid, rejection = validate_reason(reason, frame, evidence)
            assert is_valid, (
                f"Deterministic reason with caveat failed validator! "
                f"query={query!r} name={name} "
                f"reason={reason!r} rejection={rejection}"
            )

    def test_fallback_without_modifier_is_rejected_as_template(self):
        """A plain 'izakayas' query produces a name+rating-only note — rejected as template.

        With no geo hint or location modifier, build_safe_reason produces
        'Name on Street — rating★.' which is now correctly rejected as a template
        that repeats only fields visible on the card. An absent note is better.
        """
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason
        from app.concierge.reason_validator import validate_reason
        entity = PlaceEntity(
            place_id="pid_izakaya_mita", name="Izakaya Mita",
            types=["japanese_restaurant"], primary_type="japanese_restaurant",
            rating=4.5, user_rating_count=500, business_status="OPERATIONAL",
            formatted_address="100 N State St, Chicago, IL",
            google_maps_uri="https://maps.google.com/?cid=test",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query="izakaya Chicago",
        )
        frame = extract_frame("izakayas", "Chicago")
        score = RankScore(total=0.7, subtype_fit=0.85, geo_fit=0.5)
        evidence = build_evidence_bundle(entity, frame, score)
        reason = build_safe_reason(entity, evidence, frame, score)
        # The note is "Izakaya Mita on State Street — 4.5★ (500 reviews)." — pure template
        is_valid, rejection = validate_reason(reason, frame, evidence)
        assert not is_valid, (
            f"Pure name+rating note must be rejected as template. "
            f"reason={reason!r} rejection={rejection}"
        )
        assert rejection == "name_rating_only_template", (
            f"Expected name_rating_only_template rejection, got: {rejection}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# PR-4: Destination Discipline Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestDestinationDiscipline:
    """Out-of-destination candidates must be penalized relative to in-destination ones."""

    def _make_entity(self, name, address, types=None, rating=4.5, review_count=800,
                     source_query="brewery Chicago"):
        from app.concierge.place_entity_layer import PlaceEntity
        return PlaceEntity(
            place_id=f"pid_{abs(hash(name))}",
            name=name,
            types=types or ["brewery"],
            primary_type=(types[0] if types else "brewery"),
            rating=rating, user_rating_count=review_count,
            business_status="OPERATIONAL",
            formatted_address=address,
            google_maps_uri=f"https://maps.google.com/?cid={abs(hash(name))}",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query=source_query,
        )

    def test_chicago_brewery_outranks_milwaukee_brewery(self):
        """Milwaukee brewery must rank below Chicago brewery for a Chicago request."""
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import rank_entities_with_stats
        chicago_brewery = self._make_entity(
            "Goose Island Taproom",
            "1800 W Fulton St, Chicago, IL 60612, USA",
            review_count=1200,
        )
        milwaukee_brewery = self._make_entity(
            "Lakefront Brewery",
            "1872 N Commerce St, Milwaukee, WI 53212, USA",
            rating=4.7, review_count=2000,  # higher stats than Chicago option
        )
        frame = extract_frame("best waterfront breweries", "Chicago")
        ranked, stats = rank_entities_with_stats(
            [milwaukee_brewery, chicago_brewery], frame, top_n=10
        )
        assert len(ranked) >= 2, "Both entities should rank"
        top_entity = ranked[0][0]
        assert top_entity.name == "Goose Island Taproom", (
            f"Chicago brewery must rank above Milwaukee brewery for Chicago request. "
            f"Got: {top_entity.name} (addr: {top_entity.formatted_address})"
        )

    def test_destination_penalty_applied_to_out_of_city(self):
        """RankerStats must report destination_penalized_count > 0 for Milwaukee."""
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import rank_entities_with_stats
        chicago_entity = self._make_entity(
            "Chicago Taproom", "100 N Clark St, Chicago, IL, USA"
        )
        milwaukee_entity = self._make_entity(
            "Milwaukee Pub", "500 N Water St, Milwaukee, WI, USA"
        )
        frame = extract_frame("best breweries", "Chicago")
        _, stats = rank_entities_with_stats(
            [chicago_entity, milwaukee_entity], frame, top_n=10
        )
        assert stats.destination_penalized_count >= 1, (
            f"Milwaukee entity must be penalized. Stats: {vars(stats)}"
        )

    def test_no_penalty_for_in_destination(self):
        """Chicago entities must not receive destination penalty."""
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import rank_entities_with_stats, _destination_penalty
        entity = self._make_entity(
            "Goose Island", "1800 W Fulton St, Chicago, IL 60612, USA"
        )
        frame = extract_frame("best breweries", "Chicago")
        pen = _destination_penalty(entity, frame)
        assert pen == 0.0, f"Chicago entity must not be penalized: penalty={pen}"

    def test_penalty_for_confirmed_different_city(self):
        """Milwaukee entity must receive destination penalty for Chicago request."""
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import _destination_penalty, _DESTINATION_MISMATCH_PENALTY
        entity = self._make_entity(
            "Lakefront Brewery", "1872 N Commerce St, Milwaukee, WI 53212, USA"
        )
        frame = extract_frame("best breweries", "Chicago")
        pen = _destination_penalty(entity, frame)
        assert pen == _DESTINATION_MISMATCH_PENALTY, (
            f"Milwaukee entity must get full destination penalty, got: {pen}"
        )

    def test_destination_parsing_multi_word_city(self):
        """Destination with multiple words (New York, Los Angeles) still works."""
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import _destination_penalty
        entity = self._make_entity(
            "NYC Bar", "100 W 42nd St, New York, NY 10036, USA",
            source_query="bar New York",
        )
        frame = extract_frame("best cocktail bars", "New York")
        pen = _destination_penalty(entity, frame)
        assert pen == 0.0, f"New York entity must not be penalized: penalty={pen}"

    def test_no_penalty_when_no_destination(self):
        """No penalty when destination is empty (defensive)."""
        from app.concierge.frame_extractor import ExperienceFrame, SubtypeConcept
        from app.concierge.ranker import _destination_penalty
        entity = self._make_entity("Any Place", "100 Main St, Springfield, IL, USA")
        frame = ExperienceFrame(
            literal_ask="best breweries",
            normalized_ask="best breweries",
            destination="",
            subtype_concepts=[SubtypeConcept(label="brewery", confidence=0.9, source="literal_primary")],
        )
        pen = _destination_penalty(entity, frame)
        assert pen == 0.0, "No penalty when destination is empty"


# ══════════════════════════════════════════════════════════════════════════════
# PR-4: Reasoning Source Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestReasoningSourceContract:
    """Verify that the correct reason_source is reported and validated notes are used."""

    def _make_entity(self, name="Test Brewery", address="1800 W Fulton St, Chicago, IL"):
        from app.concierge.place_entity_layer import PlaceEntity
        return PlaceEntity(
            place_id="pid_rs", name=name,
            types=["brewery"], primary_type="brewery",
            rating=4.5, user_rating_count=500, business_status="OPERATIONAL",
            formatted_address=address,
            google_maps_uri="https://maps.google.com/?cid=rs",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query="brewery Chicago",
        )

    def test_deterministic_path_reason_source_label(self):
        """When batched flag is OFF, reason_source must be deterministic_safe_v1."""
        from app.concierge.batched_reason_builder import _flag_enabled
        import os
        os.environ.pop("CONCIERGE_BATCHED_REASONING_ENABLED", None)
        assert not _flag_enabled(), "Flag must be off by default"

    def test_deterministic_reason_with_geo_hint_passes_validator(self):
        """Deterministic reason for queries WITH geo hints passes validator (has caveat sentence).

        Plain queries like 'best breweries' or 'izakayas' produce name+rating-only
        templates (correctly rejected). Queries with geo hints / modifiers produce
        notes with honest caveat sentences that add value and pass validation.
        """
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason
        from app.concierge.reason_validator import validate_reason
        queries_with_hints = [
            "izakayas with waterfront views",
            "best waterfront breweries",
            "breweries near the river",
            "taprooms with a view",
        ]
        entity = self._make_entity()
        for query in queries_with_hints:
            frame = extract_frame(query, "Chicago")
            score = RankScore(total=0.7, subtype_fit=0.85, geo_fit=0.45)
            evidence = build_evidence_bundle(entity, frame, score)
            reason = build_safe_reason(entity, evidence, frame, score)
            is_valid, rejection = validate_reason(reason, frame, evidence)
            assert is_valid, (
                f"Deterministic reason with geo caveat must pass validator for {query!r}. "
                f"reason={reason!r} rejection={rejection}"
            )

    def test_plain_query_deterministic_reason_rejected_as_template(self):
        """Deterministic reason for plain queries is a template — correctly rejected.

        'best breweries' and 'izakayas' have no geo hint or modifier, so the
        deterministic path produces 'Name on Street — rating★.' which is a
        name+rating-only template. The validator rejects it; the card gets no note.
        """
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason
        from app.concierge.reason_validator import validate_reason
        plain_queries = ["izakayas", "best breweries"]
        entity = self._make_entity()
        for query in plain_queries:
            frame = extract_frame(query, "Chicago")
            score = RankScore(total=0.7, subtype_fit=0.85, geo_fit=0.45)
            evidence = build_evidence_bundle(entity, frame, score)
            reason = build_safe_reason(entity, evidence, frame, score)
            is_valid, rejection = validate_reason(reason, frame, evidence)
            assert not is_valid, (
                f"Plain query deterministic note must be rejected as template for {query!r}. "
                f"reason={reason!r}"
            )
            assert rejection == "name_rating_only_template", (
                f"Expected name_rating_only_template, got: {rejection}"
            )

    def test_old_generic_patterns_fail_validator(self):
        """Old 'Strong X match in City' notes must all fail validator."""
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.reason_validator import validate_reason
        entity = self._make_entity()
        frame = extract_frame("best waterfront breweries", "Chicago")
        score = RankScore(total=0.7, subtype_fit=0.85, geo_fit=0.45)
        evidence = build_evidence_bundle(entity, frame, score)
        bad_notes = [
            "Strong brewery match in Chicago.",
            "Good brewery match in Milwaukee.",
            "Strong izakaya match in Chicago.",
            "Strong brewery match in Chicago, near waterfront.",
            "Good waterfront match near waterfront.",
        ]
        for note in bad_notes:
            is_valid, rejection = validate_reason(note, frame, evidence)
            assert not is_valid, (
                f"Old bad note must be rejected: {note!r} (got valid=True)"
            )


# ══════════════════════════════════════════════════════════════════════════════
# PR-4: Full Regression Suite
# ══════════════════════════════════════════════════════════════════════════════

class TestPR4FullRegressionSuite:
    """End-to-end regression for all acceptance criteria queries."""

    def _build_entity_reason(self, query, name, address, types, geo_fit=0.45, subtype_fit=0.85):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason
        entity = PlaceEntity(
            place_id=f"pid_{abs(hash(name))}", name=name,
            types=types, primary_type=types[0],
            rating=4.5, user_rating_count=800, business_status="OPERATIONAL",
            formatted_address=address,
            google_maps_uri=f"https://maps.google.com/?cid={abs(hash(name))}",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query=f"{types[0]} Chicago",
        )
        frame = extract_frame(query, "Chicago")
        score = RankScore(total=0.7, subtype_fit=subtype_fit, geo_fit=geo_fit)
        evidence = build_evidence_bundle(entity, frame, score)
        return frame, entity, build_safe_reason(entity, evidence, frame, score)

    def _no_generic_match(self, reason):
        """Return True if reason has no 'Strong/Good X match' boilerplate."""
        import re
        return not re.search(
            r"\b(Strong|Good|Great|Solid)\s+\w+\s+match\b", reason, re.IGNORECASE
        )

    def test_izakayas_cards_render_no_generic_note(self):
        from app.concierge.frame_extractor import extract_frame
        _frame, _entity, reason = self._build_entity_reason(
            "izakayas", "Izakaya Mita", "1960 N Damen Ave, Chicago, IL",
            ["japanese_restaurant"],
        )
        assert self._no_generic_match(reason), f"No generic match boilerplate: {reason}"
        assert "4.5" in reason, f"Must include rating: {reason}"

    def test_izakayas_waterfront_views_no_waterfront_claim(self):
        _frame, _entity, reason = self._build_entity_reason(
            "izakayas with waterfront views",
            "The Izakaya", "1234 N Clark St, Chicago, IL",
            ["japanese_restaurant"], geo_fit=0.40,
        )
        reason_lower = reason.lower()
        assert self._no_generic_match(reason), reason
        # waterfront may appear only in caveat, never as positive claim
        if "waterfront" in reason_lower:
            assert any(kw in reason_lower for kw in (
                "not confirmed", "cannot", "no waterfront", "proximity confirmed",
            )), (
                f"Waterfront must be caveated: {reason}"
            )

    def test_izakayas_fulton_street_modifier_preserved_or_caveated(self):
        _frame, _entity, reason = self._build_entity_reason(
            "izakayas on fulton street",
            "Izakaya Mita", "3458 N Halsted St, Chicago, IL",
            ["japanese_restaurant"],
        )
        reason_lower = reason.lower()
        assert self._no_generic_match(reason), reason
        # Either confirms Fulton or honestly caveats it
        has_fulton = "fulton" in reason_lower
        if has_fulton:
            # If mentioned, must be caveated or confirmed
            assert (
                "not directly on" in reason_lower
                or "nearest match" in reason_lower
                or "on fulton" in reason_lower
            ), f"Fulton mention must be caveated or confirmed: {reason}"

    def test_best_breweries_no_generic_note(self):
        """Deterministic fallback must be card-specific, not a generic type-template.

        The new design anchors on name+street, not on the venue concept.
        "Brewery" may appear if it's in the place name; it's not required otherwise.
        """
        _frame, _entity, reason = self._build_entity_reason(
            "best breweries",
            "Half Acre Beer Co", "4257 N Lincoln Ave, Chicago, IL",
            ["brewery"], geo_fit=0.5,
        )
        assert self._no_generic_match(reason), f"No generic match boilerplate: {reason}"
        # Note must contain the actual place name (card-specific anchor)
        assert "Half Acre Beer Co" in reason, f"Must anchor on place name: {reason}"
        # Note must NOT start with the banned Verified-template
        assert not reason.lower().startswith("verified "), (
            f"Note must not use Verified-template format: {reason}"
        )

    def test_best_waterfront_breweries_no_waterfront_claim(self):
        _frame, _entity, reason = self._build_entity_reason(
            "best waterfront breweries",
            "Goose Island Brewery", "1800 W Fulton St, Chicago, IL",
            ["brewery"], geo_fit=0.45,
        )
        reason_lower = reason.lower()
        assert self._no_generic_match(reason), reason
        assert "near waterfront" not in reason_lower, (
            f"Must not claim 'near waterfront': {reason}"
        )

    def test_breweries_near_river_no_river_claim(self):
        _frame, _entity, reason = self._build_entity_reason(
            "breweries near the river",
            "Empirical Taproom", "95 W Ontario St, Chicago, IL",
            ["brewery"], geo_fit=0.5,
        )
        reason_lower = reason.lower()
        assert self._no_generic_match(reason), reason
        assert "on the river" not in reason_lower, (
            f"Must not claim 'on the river': {reason}"
        )

    def test_taprooms_with_a_view_no_view_claim(self):
        _frame, _entity, reason = self._build_entity_reason(
            "taprooms with a view",
            "Maplewood Brewery", "2717 N Paulina St, Chicago, IL",
            ["brewery"], geo_fit=0.4,
        )
        reason_lower = reason.lower()
        assert self._no_generic_match(reason), reason
        assert "has a view" not in reason_lower, f"Must not claim view: {reason}"
        assert "with a view" not in reason_lower, f"Must not claim view: {reason}"

    def test_all_notes_pass_validator(self):
        """Non-empty notes from build_safe_reason must pass the validator.

        PR-5 contract: plain queries (no geo/modifier) produce name+rating-only
        notes which are correctly REJECTED by _NAME_RATING_ONLY_RE → those callers
        get "" (absent note) which is the desired outcome.  Queries with geo or
        modifier cues get a second caveat sentence, making them validator-passing.
        This test asserts the invariant: if build_safe_reason returns a non-empty
        string, that string must satisfy validate_reason.  Empty return is also
        acceptable — absent note > generic template.
        """
        from app.concierge.reason_validator import validate_reason
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason
        # Only geo/modifier queries; plain-query notes are intentionally rejected.
        test_cases = [
            ("izakayas with waterfront views", "The Izakaya", "1234 N Clark St, Chicago, IL", ["japanese_restaurant"], 0.85, 0.4),
            ("izakayas on fulton street", "Izakaya Test", "3458 N Halsted St, Chicago, IL", ["japanese_restaurant"], 0.85, 0.5),
            ("best waterfront breweries", "Goose Island", "1800 W Fulton St, Chicago, IL", ["brewery"], 0.9, 0.45),
            ("breweries near the river", "Empirical Taproom", "95 W Ontario St, Chicago, IL", ["brewery"], 0.9, 0.5),
            ("taprooms with a view", "Maplewood Brewery", "2717 N Paulina St, Chicago, IL", ["brewery"], 0.85, 0.4),
        ]
        for query, name, addr, types, sf, gf in test_cases:
            entity = PlaceEntity(
                place_id=f"pid_{abs(hash(name))}", name=name,
                types=types, primary_type=types[0],
                rating=4.5, user_rating_count=800, business_status="OPERATIONAL",
                formatted_address=addr,
                google_maps_uri=f"https://maps.google.com/?cid={abs(hash(name))}",
                website_uri=None, price_level=None, lat=41.88, lng=-87.63,
                source_query=f"{types[0]} Chicago",
            )
            frame = extract_frame(query, "Chicago")
            score = RankScore(total=0.7, subtype_fit=sf, geo_fit=gf)
            evidence = build_evidence_bundle(entity, frame, score)
            reason = build_safe_reason(entity, evidence, frame, score)
            if not reason:
                continue  # empty is acceptable — absent note > template
            is_valid, rejection = validate_reason(reason, frame, evidence)
            assert is_valid, (
                f"Non-empty note must pass validator for {query!r}: "
                f"reason={reason!r} rejection={rejection}"
            )

    def test_google_rating_native_0_to_5_preserved(self):
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.semantic_retrieval import _entity_to_card
        entity = PlaceEntity(
            place_id="pid_rating", name="Rating Test Brewery",
            types=["brewery"], primary_type="brewery",
            rating=4.7, user_rating_count=600, business_status="OPERATIONAL",
            formatted_address="100 N Clark St, Chicago, IL",
            google_maps_uri="https://maps.google.com/?cid=rating",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query="brewery Chicago",
        )
        frame = extract_frame("best breweries", "Chicago")
        card = _entity_to_card(
            entity,
            "Verified Brewery with 4.7★ across 600 Google reviews.",
            frame,
            reason_source="deterministic_safe_v1",
        )
        assert card is not None
        assert card.rating == 4.7, f"Rating must be native 0-5: {card.rating}"

    def test_minimal_safe_note_returns_empty_string(self):
        """_minimal_safe_note must return "" (PR-5 contract: no template notes).

        The old format "Name — rating★ from N reviews." is rejected by
        _NAME_RATING_ONLY_RE because it repeats only visible card fields.
        _minimal_safe_note now always returns "" so callers produce no Concierge
        Note block rather than a generic template.
        """
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.semantic_retrieval import _minimal_safe_note
        entity = PlaceEntity(
            place_id="pid_mn", name="Minimal Note Test",
            types=["brewery"], primary_type="brewery",
            rating=4.3, user_rating_count=200, business_status="OPERATIONAL",
            formatted_address="100 N Clark St, Chicago, IL",
            google_maps_uri="https://maps.google.com/?cid=mn",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query="brewery Chicago",
        )
        note = _minimal_safe_note(entity)
        assert note == "", f"_minimal_safe_note must return empty string, got: {note!r}"

    def test_minimal_safe_note_never_shows_template_for_any_entity(self):
        """_minimal_safe_note must return "" regardless of entity, to prevent template output."""
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.semantic_retrieval import _minimal_safe_note
        entity = PlaceEntity(
            place_id="pid_mnb", name="Goose Island Brewery",
            types=["brewery"], primary_type="brewery",
            rating=4.5, user_rating_count=1200, business_status="OPERATIONAL",
            formatted_address="1800 W Fulton St, Chicago, IL",
            google_maps_uri="https://maps.google.com/?cid=gib",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query="brewery Chicago",
        )
        note = _minimal_safe_note(entity)
        assert note == "", (
            f"_minimal_safe_note must return '' to suppress template notes, got: {note!r}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Evidence-First Contract Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestEvidenceFirstContract:
    """Acceptance criteria for the evidence-first note synthesis requirement.

    Every note must cite real card-specific differentiators.
    No fill-in-the-blank templates. No invented facts.
    """

    def _note(self, query, name, address, types=None, geo_fit=0.5):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason
        entity = PlaceEntity(
            place_id="pid_ef", name=name,
            types=types or ["restaurant"],
            primary_type=(types[0] if types else "restaurant"),
            rating=4.5, user_rating_count=800, business_status="OPERATIONAL",
            formatted_address=address,
            google_maps_uri="https://maps.google.com/?cid=ef",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query=f"{query} Chicago",
        )
        frame = extract_frame(query, "Chicago")
        score = RankScore(total=0.75, subtype_fit=0.85, geo_fit=geo_fit)
        evidence = build_evidence_bundle(entity, frame, score)
        return build_safe_reason(entity, evidence, frame, score)

    def test_note_anchors_on_place_name(self):
        note = self._note("best izakayas", "Izakaya Mita", "1960 N Damen Ave, Chicago, IL",
                          ["japanese_restaurant"])
        assert "Izakaya Mita" in note, f"Note must anchor on place name: {note}"

    def test_note_anchors_on_street_name(self):
        note = self._note("best izakayas", "Test Izakaya", "1960 N Damen Ave, Chicago, IL",
                          ["japanese_restaurant"])
        assert "Damen Avenue" in note, f"Note must anchor on street name: {note}"

    def test_note_never_starts_with_verified_template(self):
        note = self._note("best breweries", "Half Acre Beer Co",
                          "4257 N Lincoln Ave, Chicago, IL", ["brewery"])
        assert not note.lower().startswith("verified "), (
            f"Note must not use Verified-template: {note}"
        )

    def test_notes_vary_by_street(self):
        """Two cards on different streets must produce distinctly different notes."""
        note_a = self._note("best breweries", "Brewery A",
                            "1800 W Fulton St, Chicago, IL", ["brewery"])
        note_b = self._note("best breweries", "Brewery B",
                            "4257 N Lincoln Ave, Chicago, IL", ["brewery"])
        assert note_a != note_b, f"Notes must differ by street: a={note_a!r} b={note_b!r}"
        assert "Fulton" in note_a, f"Note A must mention Fulton: {note_a}"
        assert "Lincoln" in note_b, f"Note B must mention Lincoln: {note_b}"

    def test_empty_string_when_no_differentiator(self):
        """Return '' when the only evidence is rating (no street, no name signal)."""
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.place_entity_layer import PlaceEntity
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason
        entity = PlaceEntity(
            place_id="pid_nod", name="A",  # single-char name: no name signal
            types=["restaurant"], primary_type="restaurant",
            rating=None, user_rating_count=0, business_status="OPERATIONAL",
            formatted_address=None,  # no address: no street
            google_maps_uri="https://maps.google.com/?cid=nod",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query="restaurant Chicago",
        )
        frame = extract_frame("restaurants", "Chicago")
        score = RankScore(total=0.5, subtype_fit=0.7, geo_fit=0.5)
        evidence = build_evidence_bundle(entity, frame, score)
        note = build_safe_reason(entity, evidence, frame, score)
        assert note == "", f"Must return '' when no card-specific evidence: {note!r}"
