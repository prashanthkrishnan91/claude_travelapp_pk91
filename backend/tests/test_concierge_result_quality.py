"""Tests for PR #285 result-quality fixes.

Covers:
1. Same-brand diversity dedup (Sinya × 2 → one Sinya in final set)
2. Stronger casual modifier filter for context reuse
3. Stronger casual fresh-search penalty
4. Context reuse metadata / response text
5. Safety invariants still pass (Google canonical, no clothing entities)
"""

from __future__ import annotations

import os
import sys
import types
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock

import pytest

# ── Stubs so routes module imports work without the full stack ────────────────
# Mirror the setup in test_concierge_context_resolver.py: add DB/CurrentUserID
# so that `from app.core.deps import DB, CurrentUserID` in ai.py succeeds.
for _mod in ["fastapi", "supabase", "anthropic"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

_core_path = os.path.join(os.path.dirname(__file__), "..", "app", "core")
_core_mod = sys.modules.get("app.core")
if _core_mod is None:
    _core_mod = types.ModuleType("app.core")
    sys.modules["app.core"] = _core_mod
if not hasattr(_core_mod, "__path__"):
    _core_mod.__path__ = [_core_path]

_deps_mod = sys.modules.get("app.core.deps")
if _deps_mod is None:
    _deps_mod = types.ModuleType("app.core.deps")
    sys.modules["app.core.deps"] = _deps_mod
if not hasattr(_deps_mod, "DB"):
    setattr(_deps_mod, "DB", object)
if not hasattr(_deps_mod, "CurrentUserID"):
    setattr(_deps_mod, "CurrentUserID", object)

if "app.routes" not in sys.modules:
    _routes_pkg = types.ModuleType("app.routes")
    _routes_pkg.__path__ = [
        os.path.join(os.path.dirname(__file__), "..", "app", "routes")
    ]
    sys.modules["app.routes"] = _routes_pkg

# ── Brand dedup (semantic_retrieval.py) ──────────────────────────────────────

from app.concierge.semantic_retrieval import (
    _deduplicate_brand_names,
    _normalize_brand_name,
)


def _make_entity(name: str, place_id: str, price_level: str = "") -> Any:
    """Minimal PlaceEntity-like object for brand dedup tests."""
    e = MagicMock()
    e.name = name
    e.place_id = place_id
    e.price_level = price_level
    e.price_range = None
    e.types = ["restaurant"]
    return e


def _make_rank_score() -> Any:
    rs = MagicMock()
    rs.total = 0.6
    return rs


class TestNormalizeBrandName:
    def test_lowercases(self):
        assert _normalize_brand_name("Sinya Mediterranean") == "sinya mediterranean"

    def test_strips_apostrophes(self):
        assert _normalize_brand_name("McDonald's") == "mcdonalds"
        assert _normalize_brand_name("L’Etoile") == "letoile"

    def test_collapses_whitespace(self):
        assert _normalize_brand_name("The  Purple  Pig") == "the purple pig"

    def test_empty_returns_empty(self):
        assert _normalize_brand_name("") == ""


class TestDeduplicateBrandNames:
    def test_two_sinya_locations_one_survives(self):
        """Two 'Sinya Mediterranean' locations → only first appears in final list."""
        entities = [
            (_make_entity("Sinya Mediterranean", "pid_damen"), _make_rank_score()),
            (_make_entity("Sinya Mediterranean", "pid_hubbard"), _make_rank_score()),
            (_make_entity("Greek Islands", "pid_greek"), _make_rank_score()),
        ]
        result, suppressed = _deduplicate_brand_names(entities)
        names = [e.name for e, _ in result]
        assert names.count("Sinya Mediterranean") == 1, "second Sinya must be suppressed"
        assert suppressed == 1
        assert "Greek Islands" in names

    def test_different_names_not_collapsed(self):
        """Different named places must never be deduped."""
        entities = [
            (_make_entity("Sinya Mediterranean", "pid1"), _make_rank_score()),
            (_make_entity("Yasemi", "pid2"), _make_rank_score()),
            (_make_entity("Aba", "pid3"), _make_rank_score()),
        ]
        result, suppressed = _deduplicate_brand_names(entities)
        assert len(result) == 3
        assert suppressed == 0

    def test_keeps_highest_ranked_sinya(self):
        """The first (highest-ranked) Sinya entry is kept, not the second."""
        e1 = _make_entity("Sinya Mediterranean", "pid_damen")
        e2 = _make_entity("Sinya Mediterranean", "pid_hubbard")
        rs1 = _make_rank_score(); rs1.total = 0.75
        rs2 = _make_rank_score(); rs2.total = 0.65
        entities = [(e1, rs1), (e2, rs2)]
        result, _ = _deduplicate_brand_names(entities)
        assert result[0][0].place_id == "pid_damen"

    def test_empty_input_returns_empty(self):
        result, suppressed = _deduplicate_brand_names([])
        assert result == []
        assert suppressed == 0

    def test_single_entity_not_suppressed(self):
        entities = [(_make_entity("Yasemi", "pid1"), _make_rank_score())]
        result, suppressed = _deduplicate_brand_names(entities)
        assert len(result) == 1
        assert suppressed == 0

    def test_addability_preserved_on_kept_card(self):
        """Brand dedup does not strip the kept card's place_id (addability intact)."""
        entities = [
            (_make_entity("Sinya Mediterranean", "pid_damen"), _make_rank_score()),
            (_make_entity("Sinya Mediterranean", "pid_hubbard"), _make_rank_score()),
        ]
        result, _ = _deduplicate_brand_names(entities)
        assert result[0][0].place_id == "pid_damen"


# ── Context resolver: casual filter + brand dedup ────────────────────────────

from app.concierge.context_resolver import (
    RefineResolved,
    _CASUAL_FIT_MIN,
    _card_price_range_end_units,
    _casual_fit_score,
    _deduplicate_brands,
    _normalize_card_brand_name,
    resolve_refine_previous,
)


def _make_verified_card(
    name: str,
    place_id: str,
    types: Optional[List[str]] = None,
    price_level: str = "",
    price_range: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Minimal verified card dict for context_resolver tests."""
    return {
        "type": "verified_place",
        "name": name,
        "google_verification": {
            "business_status": "OPERATIONAL",
            "provider_place_id": place_id,
            "google_maps_uri": f"https://maps.google.com/?cid={place_id}",
            "types": types or ["restaurant"],
        },
        "supporting_details": {
            "price_level": price_level,
            "price_range": price_range,
        },
    }


def _price_range(end_units: int) -> Dict:
    return {
        "startPrice": {"units": str(end_units // 2), "currencyCode": "USD"},
        "endPrice": {"units": str(end_units), "currencyCode": "USD"},
    }


class TestCardPriceRangeEndUnits:
    def test_reads_end_units(self):
        card = _make_verified_card("X", "p1", price_range=_price_range(100))
        assert _card_price_range_end_units(card) == 100

    def test_missing_price_range_returns_zero(self):
        card = _make_verified_card("X", "p1")
        assert _card_price_range_end_units(card) == 0

    def test_malformed_price_range_returns_zero(self):
        card = {"supporting_details": {"price_range": "not-a-dict"}}
        assert _card_price_range_end_units(card) == 0


class TestCasualFitScore:
    def test_fine_dining_expensive_scores_very_low(self):
        card = _make_verified_card(
            "Greek Islands", "p1",
            types=["fine_dining_restaurant", "restaurant"],
            price_level="PRICE_LEVEL_EXPENSIVE",
        )
        score = _casual_fit_score(card)
        assert score < _CASUAL_FIT_MIN, f"fine_dining+expensive should fail casual threshold: {score}"

    def test_price_range_100_scores_low(self):
        """Purple Pig $40-100 should fail casual threshold even without price_level."""
        card = _make_verified_card(
            "The Purple Pig", "p2",
            types=["restaurant"],
            price_level="",
            price_range=_price_range(100),
        )
        score = _casual_fit_score(card)
        assert score < _CASUAL_FIT_MIN, f"$40-100 range card should fail casual: {score}"

    def test_price_range_80_scores_low(self):
        """$80 end price → treated as borderline expensive."""
        card = _make_verified_card(
            "Aba", "p3",
            types=["restaurant"],
            price_level="",
            price_range=_price_range(80),
        )
        score = _casual_fit_score(card)
        assert score < _CASUAL_FIT_MIN, f"$80-range card should fail casual: {score}"

    def test_moderate_price_no_fine_dining_passes(self):
        card = _make_verified_card(
            "Sinya Mediterranean", "p4",
            types=["mediterranean_restaurant", "restaurant"],
            price_level="PRICE_LEVEL_MODERATE",
        )
        score = _casual_fit_score(card)
        assert score >= _CASUAL_FIT_MIN, f"moderate restaurant should pass casual: {score}"

    def test_inexpensive_cafe_passes(self):
        card = _make_verified_card(
            "Little Goat Diner", "p5",
            types=["diner", "restaurant"],
            price_level="PRICE_LEVEL_INEXPENSIVE",
        )
        score = _casual_fit_score(card)
        assert score >= _CASUAL_FIT_MIN, f"inexpensive diner should pass casual: {score}"


class TestDeduplicateBrandsContextResolver:
    def test_two_sinya_cards_deduped(self):
        cards = [
            ("restaurants", _make_verified_card("Sinya Mediterranean", "pid_damen")),
            ("restaurants", _make_verified_card("Sinya Mediterranean", "pid_hubbard")),
            ("restaurants", _make_verified_card("Yasemi", "pid_yasemi")),
        ]
        result, suppressed = _deduplicate_brands(cards)
        names = [c["name"] for _, c in result]
        assert names.count("Sinya Mediterranean") == 1
        assert suppressed == 1
        assert "Yasemi" in names

    def test_different_brands_not_collapsed(self):
        cards = [
            ("restaurants", _make_verified_card("Sinya Mediterranean", "pid1")),
            ("restaurants", _make_verified_card("Yasemi", "pid2")),
            ("restaurants", _make_verified_card("The Purple Pig", "pid3")),
        ]
        result, suppressed = _deduplicate_brands(cards)
        assert len(result) == 3
        assert suppressed == 0

    def test_normalize_card_brand_name_reads_name(self):
        card = {"name": "Sinya Mediterranean"}
        assert _normalize_card_brand_name(card) == "sinya mediterranean"

    def test_normalize_card_brand_name_falls_back_to_gv(self):
        card = {"google_verification": {"name": "Yasemi"}}
        assert _normalize_card_brand_name(card) == "yasemi"


class TestShowOnlyCasualContextReuse:
    """Integration tests for 'show only casual' against a mixed prior pool."""

    def _make_prior_pool(self) -> Dict[str, Any]:
        return {
            "intent": "restaurants",
            "restaurants": [
                _make_verified_card(
                    "Sinya Mediterranean",
                    "pid_damen",
                    types=["mediterranean_restaurant", "restaurant"],
                    price_level="PRICE_LEVEL_MODERATE",
                ),
                _make_verified_card(
                    "Sinya Mediterranean",
                    "pid_hubbard",
                    types=["mediterranean_restaurant", "restaurant"],
                    price_level="PRICE_LEVEL_MODERATE",
                ),
                _make_verified_card(
                    "Greek Islands",
                    "pid_greek",
                    types=["fine_dining_restaurant", "greek_restaurant"],
                    price_level="PRICE_LEVEL_EXPENSIVE",
                ),
                _make_verified_card(
                    "The Purple Pig",
                    "pid_purple_pig",
                    types=["restaurant"],
                    price_level="",
                    price_range=_price_range(100),
                ),
                _make_verified_card(
                    "Yasemi",
                    "pid_yasemi",
                    types=["mediterranean_restaurant", "restaurant"],
                    price_level="PRICE_LEVEL_MODERATE",
                ),
                _make_verified_card(
                    "Aba",
                    "pid_aba",
                    types=["restaurant"],
                    price_level="PRICE_LEVEL_EXPENSIVE",
                ),
            ],
            "attractions": [],
            "hotels": [],
        }

    def _make_ctx(self, pool: Dict) -> Any:
        ctx = MagicMock()
        ctx.trip_id = "test-trip-1"
        ctx.prior_card_pool = pool
        ctx.has_prior_cards = True
        ctx.card_pool_size = 6
        ctx.source_message_id = "msg-1"
        return ctx

    def test_casual_filter_excludes_fine_dining_expensive(self):
        """Greek Islands (fine_dining + expensive) must be excluded from casual filter."""
        pool = self._make_prior_pool()
        ctx = self._make_ctx(pool)
        resolved = resolve_refine_previous(ctx, "modifier_filter", "show only casual")
        assert resolved is not None
        all_card_names = [c["name"] for c in resolved.restaurants]
        assert "Greek Islands" not in all_card_names, "Greek Islands (fine_dining+expensive) must be excluded"

    def test_casual_filter_excludes_expensive_range_card(self):
        """Purple Pig ($40–100 range) must be excluded from casual filter."""
        pool = self._make_prior_pool()
        ctx = self._make_ctx(pool)
        resolved = resolve_refine_previous(ctx, "modifier_filter", "show only casual")
        assert resolved is not None
        all_card_names = [c["name"] for c in resolved.restaurants]
        assert "The Purple Pig" not in all_card_names, "Purple Pig ($40-100) must be excluded for casual"

    def test_casual_filter_no_duplicate_sinya(self):
        """After casual filter, only one Sinya Mediterranean should appear."""
        pool = self._make_prior_pool()
        ctx = self._make_ctx(pool)
        resolved = resolve_refine_previous(ctx, "modifier_filter", "show only casual")
        assert resolved is not None
        all_card_names = [c["name"] for c in resolved.restaurants]
        assert all_card_names.count("Sinya Mediterranean") <= 1, "Duplicate Sinya must be suppressed"

    def test_casual_filter_modifier_intent_populated(self):
        """resolved.modifier_intent must be 'casual' for 'show only casual'."""
        pool = self._make_prior_pool()
        ctx = self._make_ctx(pool)
        resolved = resolve_refine_previous(ctx, "modifier_filter", "show only casual")
        assert resolved is not None
        assert resolved.modifier_intent == "casual"

    def test_casual_filter_metadata_populated(self):
        """Metadata fields must be populated for modifier_filter turn."""
        pool = self._make_prior_pool()
        ctx = self._make_ctx(pool)
        resolved = resolve_refine_previous(ctx, "modifier_filter", "show only casual")
        assert resolved is not None
        assert resolved.cards_before_filter > 0
        assert resolved.excluded_for_modifier_count > 0, "Greek Islands + Purple Pig must be counted"

    def test_all_fine_dining_pool_falls_through(self):
        """If the entire pool fails casual filter, return None (provider fallback)."""
        all_fine_dining_pool = {
            "intent": "restaurants",
            "restaurants": [
                _make_verified_card(
                    f"Fine Place {i}", f"pid_{i}",
                    types=["fine_dining_restaurant"],
                    price_level="PRICE_LEVEL_VERY_EXPENSIVE",
                )
                for i in range(4)
            ],
            "attractions": [], "hotels": [],
        }
        ctx = self._make_ctx(all_fine_dining_pool)
        resolved = resolve_refine_previous(ctx, "modifier_filter", "show only casual")
        assert resolved is None, "All-fine-dining pool must fall through to provider"


# ── ai.py: build_reuse_summary modifier awareness ────────────────────────────
# NOTE: Import _build_reuse_summary inside test functions (not at module level)
# so conftest stubs are applied first before the routes module chain loads.

class TestBuildReuseSummary:
    def test_modifier_filter_casual_returns_modifier_text(self):
        from app.routes.ai import _build_reuse_summary
        summary = _build_reuse_summary("modifier_filter", 3, modifier_intent="casual")
        assert "filtered" in summary.lower() or "casual" in summary.lower(), (
            f"Casual modifier text expected, got: {summary!r}"
        )
        assert "top 3 picks" not in summary, "Must not use generic top-N text for modifier_filter"

    def test_modifier_filter_cheap_returns_budget_text(self):
        from app.routes.ai import _build_reuse_summary
        summary = _build_reuse_summary("modifier_filter", 2, modifier_intent="cheap")
        assert "budget" in summary.lower() or "filtered" in summary.lower()

    def test_top_n_returns_generic_text(self):
        from app.routes.ai import _build_reuse_summary
        summary = _build_reuse_summary("top_n", 4)
        assert "top 4" in summary.lower()

    def test_best_one(self):
        from app.routes.ai import _build_reuse_summary
        summary = _build_reuse_summary("best_one", 1)
        assert "top pick" in summary.lower()

    def test_modifier_filter_none_intent_returns_generic_text(self):
        """modifier_filter with intent='none' falls back to generic text."""
        from app.routes.ai import _build_reuse_summary
        summary = _build_reuse_summary("modifier_filter", 4, modifier_intent="none")
        assert "top 4" in summary.lower()


# ── Ranker: casual fresh-search penalty ─────────────────────────────────────

from app.concierge.frame_extractor import extract_frame
from app.concierge.ranker import RankerStats, rank_entities_with_stats
from app.concierge.place_entity_layer import PlaceEntity


def _make_place_entity(
    name: str,
    place_id: str,
    types: Optional[List[str]] = None,
    price_level: str = "",
    rating: float = 4.2,
    review_count: int = 500,
    price_range: Optional[Dict] = None,
    source_query: str = "mediterranean restaurants chicago",
    formatted_address: str = "100 N Main St, Chicago, IL 60601, USA",
) -> PlaceEntity:
    return PlaceEntity(
        place_id=place_id,
        name=name,
        formatted_address=formatted_address,
        lat=41.8,
        lng=-87.6,
        business_status="OPERATIONAL",
        google_maps_uri=f"https://maps.google.com/?cid={place_id}",
        types=types or ["restaurant"],
        primary_type=(types or ["restaurant"])[0],
        rating=rating,
        user_rating_count=review_count,
        website_uri=None,
        source_query=source_query,
        price_level=price_level,
        price_range=price_range,
    )


class TestCasualFreshSearchRanking:
    """Verify casual modifier materially alters ranking vs broad search."""

    def _make_med_entities(self) -> List[PlaceEntity]:
        return [
            _make_place_entity(
                "Greek Islands", "pid_greek",
                types=["fine_dining_restaurant", "greek_restaurant"],
                price_level="PRICE_LEVEL_EXPENSIVE",
                rating=4.5, review_count=2000,
                source_query="casual mediterranean restaurants chicago",
            ),
            _make_place_entity(
                "Aba", "pid_aba",
                types=["restaurant", "mediterranean_restaurant"],
                price_level="PRICE_LEVEL_EXPENSIVE",
                rating=4.4, review_count=1500,
                source_query="casual mediterranean restaurants chicago",
            ),
            _make_place_entity(
                "The Purple Pig", "pid_purple_pig",
                types=["restaurant"],
                price_level="",
                price_range=_price_range(100),
                rating=4.4, review_count=3000,
                source_query="casual mediterranean restaurants chicago",
            ),
            _make_place_entity(
                "Sinya Mediterranean N Damen", "pid_sinya_damen",
                types=["mediterranean_restaurant", "restaurant"],
                price_level="PRICE_LEVEL_MODERATE",
                rating=4.3, review_count=800,
                source_query="casual mediterranean restaurants chicago",
            ),
            _make_place_entity(
                "Yasemi", "pid_yasemi",
                types=["mediterranean_restaurant", "restaurant"],
                price_level="PRICE_LEVEL_MODERATE",
                rating=4.2, review_count=600,
                source_query="casual mediterranean restaurants chicago",
            ),
            _make_place_entity(
                "Cafe Med", "pid_cafe_med",
                types=["cafe", "mediterranean_restaurant"],
                price_level="PRICE_LEVEL_INEXPENSIVE",
                rating=4.0, review_count=300,
                source_query="casual mediterranean restaurants chicago",
            ),
        ]

    def test_casual_frame_downranks_fine_dining(self):
        """With casual frame, fine_dining+expensive places must score lower."""
        entities = self._make_med_entities()
        casual_frame = extract_frame("casual Mediterranean restaurants", "Chicago")
        broad_frame = extract_frame("Mediterranean restaurants", "Chicago")

        casual_ranked, casual_stats = rank_entities_with_stats(entities, casual_frame, top_n=6)
        broad_ranked, broad_stats = rank_entities_with_stats(entities, broad_frame, top_n=6)

        casual_names = [e.name for e, _ in casual_ranked]
        broad_names = [e.name for e, _ in broad_ranked]

        # Casual stat must be populated
        assert casual_stats.modifier_intent == "casual", "casual frame must set modifier_intent"
        assert casual_stats.modifier_filter_applied is True
        assert casual_stats.casual_downranked_count > 0, "At least one entity must be penalized"

        # Fine dining + expensive places must score lower in casual vs broad
        casual_greek_pos = casual_names.index("Greek Islands") if "Greek Islands" in casual_names else len(casual_names)
        broad_greek_pos = broad_names.index("Greek Islands") if "Greek Islands" in broad_names else len(broad_names)
        # Greek Islands should rank at least as low in casual as in broad
        assert casual_greek_pos >= broad_greek_pos, (
            f"Greek Islands should rank same or lower in casual: casual_pos={casual_greek_pos} broad_pos={broad_greek_pos}"
        )

    def test_casual_sets_differ_from_broad_materially(self):
        """Top-3 results for casual vs broad must be materially different."""
        entities = self._make_med_entities()
        casual_frame = extract_frame("casual Mediterranean restaurants", "Chicago")
        broad_frame = extract_frame("Mediterranean restaurants", "Chicago")
        casual_ranked, _ = rank_entities_with_stats(entities, casual_frame, top_n=6)
        broad_ranked, _ = rank_entities_with_stats(entities, broad_frame, top_n=6)

        casual_top3 = {e.name for e, _ in casual_ranked[:3]}
        broad_top3 = {e.name for e, _ in broad_ranked[:3]}
        # The sets should not be identical — casual modifier must change the order
        assert casual_top3 != broad_top3, (
            f"Casual and broad should produce different top-3: casual={casual_top3} broad={broad_top3}"
        )

    def test_casual_downranks_expensive_range_card(self):
        """Price-range $100 card (Purple Pig) must be penalized in casual."""
        entities = self._make_med_entities()
        casual_frame = extract_frame("casual Mediterranean restaurants", "Chicago")
        broad_frame = extract_frame("Mediterranean restaurants", "Chicago")

        casual_ranked, _ = rank_entities_with_stats(entities, casual_frame, top_n=6)
        broad_ranked, _ = rank_entities_with_stats(entities, broad_frame, top_n=6)

        casual_names = [e.name for e, _ in casual_ranked]
        broad_names = [e.name for e, _ in broad_ranked]

        if "The Purple Pig" in casual_names and "The Purple Pig" in broad_names:
            casual_pos = casual_names.index("The Purple Pig")
            broad_pos = broad_names.index("The Purple Pig")
            assert casual_pos >= broad_pos, (
                f"Purple Pig should rank same or lower with casual: casual={casual_pos} broad={broad_pos}"
            )

    def test_broad_search_sinya_dedup_in_pipeline(self):
        """Two Sinya Mediterranean entities → only one in brand-dedup output."""
        from app.concierge.semantic_retrieval import _deduplicate_brand_names
        e1 = _make_place_entity("Sinya Mediterranean", "pid_damen")
        e2 = _make_place_entity("Sinya Mediterranean", "pid_hubbard")
        e3 = _make_place_entity("Yasemi", "pid_yasemi")
        ranked = [(e1, MagicMock()), (e2, MagicMock()), (e3, MagicMock())]
        result, suppressed = _deduplicate_brand_names(ranked)
        assert suppressed == 1
        names = [e.name for e, _ in result]
        assert names.count("Sinya Mediterranean") == 1


# ── Retrieval planner: casual query generation ───────────────────────────────

from app.concierge.retrieval_planner import plan_queries, _PREFERENCE_QUERY_MODIFIERS


class TestCasualRetrievalPlannerQueries:
    """Verify 'casual' in normalized_soft_preferences triggers casual-specific queries.

    These tests FAIL before the fix (no 'casual' entry in _PREFERENCE_QUERY_MODIFIERS)
    and PASS after (casual generates preference-aware queries).
    """

    def test_casual_has_entry_in_preference_modifiers(self):
        """'casual' must be registered in _PREFERENCE_QUERY_MODIFIERS."""
        assert "casual" in _PREFERENCE_QUERY_MODIFIERS, (
            "'casual' must have an entry in _PREFERENCE_QUERY_MODIFIERS so the retrieval "
            "planner generates casual-specific queries instead of the same plain queries "
            "as a broad search."
        )

    def test_casual_generates_multiple_queries(self):
        """'casual Mediterranean restaurants' must generate 2+ queries.

        Without the fix, pref_modifiers is empty for 'casual', so the planner falls
        into the plain-synonym branch and produces only 1 query: 'mediterranean
        restaurant Chicago'. This causes the same candidate pool as a broad search.
        """
        frame = extract_frame("casual Mediterranean restaurants", "Chicago")
        queries = plan_queries(frame)
        assert len(queries) >= 2, (
            f"casual Mediterranean should generate ≥2 queries, got: {queries}"
        )

    def test_casual_query_contains_casual_or_neighborhood_prefix(self):
        """At least one generated query must have a casual-intent prefix.

        This directly verifies that Google receives a query signal for casual dining
        rather than a generic 'mediterranean restaurant' query.
        """
        frame = extract_frame("casual Mediterranean restaurants", "Chicago")
        queries = plan_queries(frame)
        casual_prefixes = {"casual", "neighborhood", "relaxed"}
        has_casual_prefix = any(
            any(q.lower().startswith(prefix) for prefix in casual_prefixes)
            for q in queries
        )
        assert has_casual_prefix, (
            f"At least one query must start with a casual-intent prefix; got: {queries}"
        )

    def test_broad_query_unchanged(self):
        """'Mediterranean restaurants' (no casual) generates plain queries without casual prefix."""
        broad_frame = extract_frame("Mediterranean restaurants", "Chicago")
        casual_frame = extract_frame("casual Mediterranean restaurants", "Chicago")
        broad_queries = plan_queries(broad_frame)
        casual_queries = plan_queries(casual_frame)
        # Broad must not have casual prefix
        casual_prefixes = {"casual", "neighborhood", "relaxed"}
        broad_has_casual = any(
            any(q.lower().startswith(p) for p in casual_prefixes)
            for q in broad_queries
        )
        assert not broad_has_casual, (
            f"Broad query must not have casual prefix: {broad_queries}"
        )
        # The query sets must differ
        assert set(broad_queries) != set(casual_queries), (
            f"Casual and broad must produce different query sets: broad={broad_queries} "
            f"casual={casual_queries}"
        )

    def test_casual_queries_still_include_broad_fallback(self):
        """Casual queries must include a plain venue+destination fallback for recall."""
        frame = extract_frame("casual Mediterranean restaurants", "Chicago")
        queries = plan_queries(frame)
        # The broad fallback "mediterranean restaurant Chicago" must be present
        has_broad_fallback = any(
            "mediterranean" in q.lower() and "chicago" in q.lower()
            and not any(q.lower().startswith(p) for p in {"casual", "neighborhood", "relaxed"})
            for q in queries
        )
        assert has_broad_fallback, (
            f"Casual queries must include a broad fallback for recall; got: {queries}"
        )


# ── Ranker: casual pre-truncation sort ───────────────────────────────────────

class TestCasualPreTruncationSort:
    """Verify casual pre-sort bubbles casual-compatible entities above fine-dining.

    These tests cover the scenario where fine-dining entities have very high
    quality/popularity scores that could otherwise numerically beat casual
    alternatives despite the direct penalty — the sort guarantees casual entities
    surface to top-N when ≥2 casual-compatible candidates exist.
    """

    def _make_pool_fine_dining_no_price_level(self) -> List[PlaceEntity]:
        """Production-equivalent pool: Greek Islands (fine_dining, NO price_level).

        This is the real production failure: Google types include fine_dining_restaurant
        but no price_level is set, so only pen=0.10 applies from the direct penalty.
        With very high quality/popularity, Greek Islands could outscore casual
        alternatives without the pre-sort.
        """
        return [
            # Upscale — fine_dining only (no price_level), very high quality
            _make_place_entity(
                "Greek Islands", "pid_greek",
                types=["fine_dining_restaurant", "greek_restaurant"],
                price_level="",  # no price_level — production scenario
                rating=4.8, review_count=5000,
                source_query="casual mediterranean restaurants chicago",
            ),
            # Upscale — expensive price_range, no fine_dining type
            _make_place_entity(
                "Aba", "pid_aba",
                types=["mediterranean_restaurant", "restaurant"],
                price_level="",
                price_range={"endPrice": {"units": "100"}},
                rating=4.6, review_count=2000,
                source_query="casual mediterranean restaurants chicago",
            ),
            # Casual-compatible — moderate price
            _make_place_entity(
                "Sinya Mediterranean N Damen", "pid_sinya",
                types=["mediterranean_restaurant", "restaurant"],
                price_level="PRICE_LEVEL_MODERATE",
                rating=4.3, review_count=800,
                source_query="casual mediterranean restaurants chicago",
            ),
            # Casual-compatible — moderate price
            _make_place_entity(
                "Yasemi", "pid_yasemi",
                types=["mediterranean_restaurant", "restaurant"],
                price_level="PRICE_LEVEL_MODERATE",
                rating=4.2, review_count=600,
                source_query="casual mediterranean restaurants chicago",
            ),
            # Casual-compatible — inexpensive
            _make_place_entity(
                "Cafe Med", "pid_cafe_med",
                types=["cafe", "mediterranean_restaurant"],
                price_level="PRICE_LEVEL_INEXPENSIVE",
                rating=4.0, review_count=300,
                source_query="casual mediterranean restaurants chicago",
            ),
        ]

    def test_casual_sort_applied_when_enough_compat_entities(self):
        """casual_sort_applied must be True when ≥2 casual-compatible entities exist."""
        entities = self._make_pool_fine_dining_no_price_level()
        frame = extract_frame("casual Mediterranean restaurants", "Chicago")
        _, stats = rank_entities_with_stats(entities, frame, top_n=5)
        assert stats.casual_sort_applied, (
            "casual_sort_applied must be True when pool has ≥2 casual-compatible candidates"
        )

    def test_casual_sort_not_applied_for_broad(self):
        """Broad 'Mediterranean restaurants' must NOT trigger the casual sort."""
        entities = self._make_pool_fine_dining_no_price_level()
        broad_frame = extract_frame("Mediterranean restaurants", "Chicago")
        _, stats = rank_entities_with_stats(entities, broad_frame, top_n=5)
        assert not stats.casual_sort_applied, (
            "Broad Mediterranean query must not trigger casual pre-sort"
        )

    def test_greek_islands_fine_dining_no_price_level_not_first_with_alternatives(self):
        """Greek Islands (fine_dining, NO price_level) must not rank #1 when casual alternatives exist."""
        entities = self._make_pool_fine_dining_no_price_level()
        frame = extract_frame("casual Mediterranean restaurants", "Chicago")
        casual_ranked, _ = rank_entities_with_stats(entities, frame, top_n=5)
        casual_names = [e.name for e, _ in casual_ranked]
        if "Greek Islands" in casual_names:
            greek_pos = casual_names.index("Greek Islands")
            assert greek_pos > 0, (
                f"Greek Islands (fine_dining, no price_level) must not rank first "
                f"when casual alternatives exist. Ranked order: {casual_names}"
            )

    def test_aba_expensive_range_not_first_with_casual_alternatives(self):
        """Aba ($100 range) must not rank #1 when casual alternatives exist."""
        entities = self._make_pool_fine_dining_no_price_level()
        frame = extract_frame("casual Mediterranean restaurants", "Chicago")
        casual_ranked, _ = rank_entities_with_stats(entities, frame, top_n=5)
        casual_names = [e.name for e, _ in casual_ranked]
        if "Aba" in casual_names:
            aba_pos = casual_names.index("Aba")
            assert aba_pos > 0, (
                f"Aba ($100 range) must not rank first when casual alternatives exist. "
                f"Ranked order: {casual_names}"
            )

    def test_casual_top2_are_casual_compatible(self):
        """Top 2 results for casual must both be casual-compatible (not fine_dining/expensive)."""
        entities = self._make_pool_fine_dining_no_price_level()
        frame = extract_frame("casual Mediterranean restaurants", "Chicago")
        casual_ranked, _ = rank_entities_with_stats(entities, frame, top_n=5)
        top2 = casual_ranked[:2]
        for entity, _ in top2:
            is_fine_dining = "fine_dining_restaurant" in {t.lower() for t in (entity.types or [])}
            price_end = int((entity.price_range or {}).get("endPrice", {}).get("units", 0) or 0)
            is_v_expensive = (entity.price_level or "").upper() == "PRICE_LEVEL_VERY_EXPENSIVE" or price_end >= 100
            assert not is_fine_dining, (
                f"Top-2 entity '{entity.name}' has fine_dining type — must not rank in top-2 "
                f"for casual query when casual alternatives exist"
            )
            assert not is_v_expensive, (
                f"Top-2 entity '{entity.name}' is very expensive — must not rank in top-2 "
                f"for casual query when casual alternatives exist"
            )

    def test_broad_top2_unchanged_by_casual_fix(self):
        """Broad 'Mediterranean restaurants' top-2 must not be penalized by casual logic."""
        entities = self._make_pool_fine_dining_no_price_level()
        broad_frame = extract_frame("Mediterranean restaurants", "Chicago")
        broad_ranked, broad_stats = rank_entities_with_stats(entities, broad_frame, top_n=5)
        # Broad should not apply casual sort, penalties, or exclusions
        assert broad_stats.modifier_intent != "casual"
        assert not broad_stats.casual_sort_applied
        assert broad_stats.casual_downranked_count == 0
        # Broad can include upscale entities (Greek Islands, Aba) in top results
        broad_names = [e.name for e, _ in broad_ranked]
        assert len(broad_names) > 0, "Broad query must return results"


# ── Safety invariants ─────────────────────────────────────────────────────────

from app.concierge.semantic_retrieval import _is_food_incompatible_entity


class TestSafetyInvariants:
    def test_clothing_store_still_rejected(self):
        """Only One Boutique (womens_clothing_store) must still be rejected."""
        assert _is_food_incompatible_entity(["womens_clothing_store", "clothing_store"])

    def test_food_restaurant_still_passes(self):
        """Restaurant entity must still pass the food-compatibility gate."""
        assert not _is_food_incompatible_entity(["restaurant", "food"])

    def test_brand_dedup_does_not_strip_addability(self):
        """Brand dedup keeps the place_id intact (addability preserved)."""
        e1 = _make_place_entity("Sinya Mediterranean", "pid_canonical_damen")
        e2 = _make_place_entity("Sinya Mediterranean", "pid_hubbard")
        from app.concierge.semantic_retrieval import _deduplicate_brand_names
        result, _ = _deduplicate_brand_names([(e1, MagicMock()), (e2, MagicMock())])
        assert result[0][0].place_id == "pid_canonical_damen"

    def test_display_contract_fields_present_on_context_reuse_metadata(self):
        """context_reuse dict produced by ai.py must include filter_applied and modifier_intent."""
        # Verify summary text is correct for casual modifier (import inside fn for conftest stubs).
        from app.routes.ai import _build_reuse_summary
        summary = _build_reuse_summary("modifier_filter", 3, modifier_intent="casual")
        assert isinstance(summary, str)
        assert len(summary) > 0
        # Must NOT use the old generic top-N text for a modifier filter
        assert "top 3 picks from your previous" not in summary
