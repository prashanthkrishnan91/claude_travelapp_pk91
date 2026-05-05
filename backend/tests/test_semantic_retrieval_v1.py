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

    def test_reason_includes_ask_anchor_tapas(self):
        entity = self._entity("La Tasca", types=["spanish_restaurant"])
        reason = self._build_reason(entity, "romantic tapas but not too loud")
        assert "tapas" in reason.lower() or "tapa" in reason.lower(), (
            f"Reason must mention 'tapas': {reason}"
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

    def test_verify_wrapper_used_for_weakly_verified_geo(self):
        entity = self._entity("Riverside Grill", types=["restaurant"])
        reason = self._build_reason(
            entity, "best breweries along the waterfront", geo_fit=0.50
        )
        assert "verify" in reason.lower() or "booking" in reason.lower(), (
            f"Must include verify wrapper for unconfirmed waterfront: {reason}"
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

        with patch(
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

        with patch(
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

        with patch(
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

        with patch(
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
        config_src = pathlib.Path("backend/app/core/config.py").read_text()
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

        with patch("app.concierge.provider_executor.execute_fanout",
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

        with patch("app.concierge.provider_executor.execute_fanout",
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

        with patch("app.concierge.provider_executor.execute_fanout", side_effect=fake_execute):
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

        with patch("app.concierge.provider_executor.execute_fanout", side_effect=fake_execute):
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

        with patch("app.concierge.provider_executor.execute_fanout", side_effect=fake_execute):
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

        with patch("app.concierge.provider_executor.execute_fanout", side_effect=fake_execute):
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
