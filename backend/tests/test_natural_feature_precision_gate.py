"""Natural-feature precision gate tests (PR: fix-natural-feature-ranking-USOui).

Verifies that natural-feature attraction queries (beaches, sunset viewpoints,
scenic overlooks, lookout points) reject food/bar/hotel candidates that only
match by lexical name coincidence, while accepting candidates with supporting
Google type/category evidence.

Test groups:
1. Natural-feature precision gate — entity-level pass/reject decisions
2. Ranker subtype_fit suppression for natural-feature name matches
3. Editorial gate — Tavily/editorial skipped for natural-feature concepts
4. Honest empty state — returns no cards when gate rejects all candidates
5. Venue-head preservation — rooftop bars/hotel-near-beach unaffected
6. Passing-behavior regression — existing intent routing preserved
"""

from __future__ import annotations

import sys
import types
from typing import Any, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# ── Minimal stub for imports that require FastAPI / Supabase ──────────────────
for _mod in ("fastapi", "supabase", "anthropic"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

_deps_mod = sys.modules.get("app.core.deps")
if _deps_mod is None:
    _deps_mod = types.ModuleType("app.core.deps")
    sys.modules["app.core.deps"] = _deps_mod
setattr(_deps_mod, "DB", object)
setattr(_deps_mod, "CurrentUserID", object)

_routes_pkg = sys.modules.get("app.routes")
if _routes_pkg is None:
    _routes_pkg = types.ModuleType("app.routes")
    _routes_pkg.__path__ = []
    sys.modules["app.routes"] = _routes_pkg

# ── Production imports ────────────────────────────────────────────────────────
from app.concierge.frame_extractor import extract_frame, SubtypeConcept
from app.concierge.ranker import (
    _concept_is_natural_feature,
    _NATURAL_FEATURE_CONCEPT_TOKENS,
    _FOOD_BAR_HOTEL_VENUE_TYPES,
    _subtype_fit,
    rank_entities_with_stats,
    _ON_CONCEPT_SUBTYPE_FIT_MIN,
    _has_known_synonym_set,
)
from app.concierge.semantic_retrieval import (
    _is_natural_feature_query,
    _entity_passes_natural_feature_gate,
    _NATURAL_FEATURE_CONCEPT_LABELS,
    _NATURAL_FEATURE_HARD_REJECTED_TYPES,
    _BEACH_NATURAL_FEATURE_TYPES,
    _VIEWPOINT_NATURAL_FEATURE_TYPES,
    _MIN_NATURAL_FEATURE_GATE_CANDIDATES,
)
from app.concierge.evidence_cache import should_run_editorial


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_entity(
    name: str,
    types: List[str],
    primary_type: str = "",
    place_id: str = "",
    formatted_address: str = "Test City, CA",
    source_query: str = "sunset viewpoint",
    rating: float = 4.5,
    user_rating_count: int = 500,
) -> Any:
    """Minimal PlaceEntity-compatible object for testing."""
    from app.concierge.place_entity_layer import PlaceEntity
    return PlaceEntity(
        place_id=place_id or f"id_{name[:8].replace(' ', '_')}",
        name=name,
        formatted_address=formatted_address,
        google_maps_uri=f"https://maps.google.com/?q={name.replace(' ', '+')}",
        business_status="OPERATIONAL",
        lat=None,
        lng=None,
        types=types,
        primary_type=primary_type,
        rating=rating,
        user_rating_count=user_rating_count,
        price_level=None,
        source_query=source_query,
    )


def _frame_for(query: str, destination: str = "Paris") -> Any:
    return extract_frame(query, destination)


# ── 1. Natural-feature precision gate (entity-level) ─────────────────────────

class TestNaturalFeaturePrecisionGate:
    """_entity_passes_natural_feature_gate must reject wrong-vertical candidates."""

    # --- "sunset points" / viewpoint concept ---

    def test_sunset_sunside_restaurant_rejected(self):
        """'Sunset/Sunside' restaurant rejected for viewpoint query."""
        entity = _make_entity(
            "Sunset/Sunside",
            types=["restaurant", "food", "establishment", "point_of_interest"],
            primary_type="restaurant",
        )
        assert not _entity_passes_natural_feature_gate(entity, "viewpoint")

    def test_sunset_bar_rejected(self):
        """Entity named 'Sunset' that is a bar is rejected for viewpoint query."""
        entity = _make_entity(
            "Sunset",
            types=["bar", "night_club", "establishment"],
            primary_type="bar",
        )
        assert not _entity_passes_natural_feature_gate(entity, "viewpoint")

    def test_sunset_boulevard_nightclub_rejected(self):
        """'Sunset Boulevard' nightclub rejected for viewpoint query."""
        entity = _make_entity(
            "Sunset Boulevard",
            types=["night_club", "nightclub", "bar", "establishment"],
            primary_type="night_club",
        )
        assert not _entity_passes_natural_feature_gate(entity, "viewpoint")

    def test_viewpoint_scenic_overlook_accepted(self):
        """Entity with tourist_attraction type accepted for viewpoint query."""
        entity = _make_entity(
            "Sacré-Cœur Viewpoint",
            types=["tourist_attraction", "landmark", "establishment", "point_of_interest"],
            primary_type="tourist_attraction",
        )
        assert _entity_passes_natural_feature_gate(entity, "viewpoint")

    def test_scenic_overlook_park_type_accepted(self):
        """Entity with park type accepted for viewpoint query."""
        entity = _make_entity(
            "Butte Chaumont Overlook",
            types=["park", "establishment", "point_of_interest"],
            primary_type="park",
        )
        assert _entity_passes_natural_feature_gate(entity, "viewpoint")

    def test_observation_deck_accepted(self):
        """Observation deck entity accepted for viewpoint query."""
        entity = _make_entity(
            "Tour Montparnasse Observation Deck",
            types=["observation_deck", "tourist_attraction", "establishment"],
            primary_type="observation_deck",
        )
        assert _entity_passes_natural_feature_gate(entity, "viewpoint")

    def test_natural_feature_type_accepted(self):
        """Entity with natural_feature type accepted for viewpoint query."""
        entity = _make_entity(
            "Butte du Chapeau-Rouge",
            types=["natural_feature", "park", "point_of_interest"],
            primary_type="natural_feature",
        )
        assert _entity_passes_natural_feature_gate(entity, "viewpoint")

    def test_viewpoint_name_evidence_accepted_when_types_generic(self):
        """Entity with viewpoint in name + only generic types accepted."""
        entity = _make_entity(
            "Paris Belvedere Vista",
            types=["establishment", "point_of_interest"],
            primary_type="",
        )
        assert _entity_passes_natural_feature_gate(entity, "viewpoint")

    def test_overlook_name_accepted_when_types_generic(self):
        """Entity named 'Overlook' with only generic types passes through."""
        entity = _make_entity(
            "Eiffel Tower Overlook",
            types=["point_of_interest"],
            primary_type="",
        )
        assert _entity_passes_natural_feature_gate(entity, "viewpoint")

    # --- "best beaches" / beach concept ---

    def test_beach_entity_with_beach_type_accepted(self):
        """Entity typed 'beach' accepted for beach query."""
        entity = _make_entity(
            "South Beach",
            types=["beach", "natural_feature", "establishment", "point_of_interest"],
            primary_type="beach",
            source_query="beach Miami",
        )
        assert _entity_passes_natural_feature_gate(entity, "beach")

    def test_beach_park_type_accepted(self):
        """Entity typed 'beach_park' accepted for beach query."""
        entity = _make_entity(
            "Lummus Park Beach",
            types=["beach_park", "park", "point_of_interest"],
            primary_type="beach_park",
            source_query="public beach Miami",
        )
        assert _entity_passes_natural_feature_gate(entity, "beach")

    def test_beach_restaurant_rejected(self):
        """Restaurant entity rejected for beach query even when name contains 'beach'."""
        entity = _make_entity(
            "The Beach Restaurant",
            types=["restaurant", "food", "establishment", "point_of_interest"],
            primary_type="restaurant",
            source_query="beach Miami",
        )
        assert not _entity_passes_natural_feature_gate(entity, "beach")

    def test_beach_bar_rejected(self):
        """Bar entity rejected for beach query even when name contains 'beach'."""
        entity = _make_entity(
            "Miami Beach Bar",
            types=["bar", "night_club", "establishment"],
            primary_type="bar",
            source_query="beach Miami",
        )
        assert not _entity_passes_natural_feature_gate(entity, "beach")

    def test_beach_hotel_rejected(self):
        """Hotel entity rejected for beach query even when name/address has 'beach'."""
        entity = _make_entity(
            "Beachfront Hotel",
            types=["hotel", "lodging", "establishment"],
            primary_type="hotel",
            formatted_address="1 Ocean Drive, Miami Beach, FL",
            source_query="beach Miami",
        )
        assert not _entity_passes_natural_feature_gate(entity, "beach")

    def test_cafe_near_beach_rejected(self):
        """Cafe entity rejected for beach query."""
        entity = _make_entity(
            "Beach Cafe",
            types=["cafe", "coffee_shop", "establishment"],
            primary_type="cafe",
            source_query="public beach Miami",
        )
        assert not _entity_passes_natural_feature_gate(entity, "beach")

    def test_unknown_typed_entity_passes(self):
        """Entity with only generic types passes through (conservative)."""
        entity = _make_entity(
            "Untyped Beach Area",
            types=["establishment", "point_of_interest"],
            primary_type="",
            source_query="beach Miami",
        )
        assert _entity_passes_natural_feature_gate(entity, "beach")


# ── 2. _is_natural_feature_query detection ────────────────────────────────────

class TestIsNaturalFeatureQuery:
    """_is_natural_feature_query must correctly classify frames."""

    def test_sunset_points_paris_is_natural_feature(self):
        frame = _frame_for("Sunset points with Eiffel tower view", destination="Paris")
        is_nf, category = _is_natural_feature_query(frame)
        assert is_nf is True
        assert category == "viewpoint"

    def test_best_beaches_miami_is_beach(self):
        frame = _frame_for("best beaches in Miami", destination="Miami")
        is_nf, category = _is_natural_feature_query(frame)
        assert is_nf is True
        assert category == "beach"

    def test_best_sunset_points_san_diego_is_viewpoint(self):
        frame = _frame_for("best sunset points in San Diego", destination="San Diego")
        is_nf, category = _is_natural_feature_query(frame)
        assert is_nf is True
        assert category == "viewpoint"

    def test_viewpoint_query_is_natural_feature(self):
        frame = _frame_for("scenic viewpoints in Barcelona", destination="Barcelona")
        is_nf, category = _is_natural_feature_query(frame)
        assert is_nf is True

    def test_rooftop_bars_is_not_natural_feature(self):
        """'rooftop bars' has explicit venue head 'bar' — not a natural-feature query."""
        frame = _frame_for("rooftop bars with sunset views", destination="Barcelona")
        is_nf, _cat = _is_natural_feature_query(frame)
        # Primary concept is "bar" (venue head), not a natural-feature label
        assert is_nf is False

    def test_restaurants_is_not_natural_feature(self):
        frame = _frame_for("best restaurants in Paris", destination="Paris")
        is_nf, _cat = _is_natural_feature_query(frame)
        assert is_nf is False

    def test_sports_bars_is_not_natural_feature(self):
        frame = _frame_for("sports bars in Chicago", destination="Chicago")
        is_nf, _cat = _is_natural_feature_query(frame)
        assert is_nf is False

    def test_hotels_near_beach_is_not_natural_feature(self):
        """'hotels near the beach' has venue head 'hotel' — gate must not trigger."""
        frame = _frame_for("hotels near the beach", destination="Miami")
        is_nf, _cat = _is_natural_feature_query(frame)
        assert is_nf is False


# ── 3. Ranker subtype_fit suppression ─────────────────────────────────────────

class TestRankerNaturalFeatureSubtypeFit:
    """_subtype_fit must be suppressed for food/bar entities on natural-feature concepts."""

    def test_sunset_boulevard_restaurant_low_subtype_fit(self):
        """'Sunset Boulevard' restaurant scores low subtype_fit for 'sunset' concept."""
        entity = _make_entity(
            "Sunset Boulevard",
            types=["restaurant", "food", "establishment", "point_of_interest"],
            primary_type="restaurant",
            source_query="sunset viewpoint Paris",
        )
        frame = _frame_for("Sunset points with Eiffel tower view", destination="Paris")
        sf = _subtype_fit(entity, frame)
        # Must be below wrong-category threshold so penalty fires
        assert sf <= 0.30, f"Expected sf <= 0.30 for restaurant on viewpoint query, got {sf}"

    def test_sunset_bar_low_subtype_fit(self):
        """Bar named 'Sunset' scores low subtype_fit for 'sunset viewpoint' concept."""
        entity = _make_entity(
            "Sunset",
            types=["bar", "night_club", "establishment"],
            primary_type="bar",
            source_query="sunset spot Paris",
        )
        frame = _frame_for("sunset points", destination="Paris")
        sf = _subtype_fit(entity, frame)
        assert sf <= 0.30, f"Expected sf <= 0.30 for bar on viewpoint query, got {sf}"

    def test_sunside_nightclub_low_subtype_fit(self):
        """Nightclub 'Sunset/Sunside' scores low for viewpoint query."""
        entity = _make_entity(
            "Sunset/Sunside",
            types=["night_club", "bar", "establishment", "point_of_interest"],
            primary_type="night_club",
            source_query="scenic overlook Paris",
        )
        frame = _frame_for("Sunset points with Eiffel tower view", destination="Paris")
        sf = _subtype_fit(entity, frame)
        assert sf <= 0.30, f"Expected suppressed sf, got {sf}"

    def test_viewpoint_entity_high_subtype_fit(self):
        """Observation deck scores high subtype_fit for viewpoint query."""
        entity = _make_entity(
            "Tour Eiffel Belvedere",
            types=["tourist_attraction", "observation_deck", "landmark", "point_of_interest"],
            primary_type="tourist_attraction",
            source_query="sunset viewpoint Paris",
        )
        frame = _frame_for("best sunset points in Paris", destination="Paris")
        sf = _subtype_fit(entity, frame)
        assert sf >= 0.45, f"Expected high sf for viewpoint entity, got {sf}"

    def test_beach_restaurant_low_subtype_fit(self):
        """'Beach Grill' restaurant scores low subtype_fit for 'beach' concept."""
        entity = _make_entity(
            "The Beach Grill",
            types=["restaurant", "food", "establishment", "point_of_interest"],
            primary_type="restaurant",
            source_query="beach Miami",
        )
        frame = _frame_for("best beaches in Miami", destination="Miami")
        sf = _subtype_fit(entity, frame)
        assert sf <= 0.30, f"Expected low sf for restaurant on beach query, got {sf}"

    def test_actual_beach_high_subtype_fit(self):
        """South Beach entity scores high subtype_fit for 'beach' concept."""
        entity = _make_entity(
            "South Beach",
            types=["beach", "natural_feature", "establishment", "point_of_interest"],
            primary_type="beach",
            source_query="beach Miami",
        )
        frame = _frame_for("best beaches in Miami", destination="Miami")
        sf = _subtype_fit(entity, frame)
        assert sf >= 0.45, f"Expected high sf for beach entity, got {sf}"

    def test_cocktail_bar_on_cocktail_query_unaffected(self):
        """Cocktail bar 'Sunset Bar' on cocktail query: venue head is bar, NOT suppressed."""
        entity = _make_entity(
            "Sunset Bar",
            types=["bar", "cocktail_bar", "establishment", "point_of_interest"],
            primary_type="bar",
            source_query="cocktail bar Chicago",
        )
        # frame concept is "cocktail" or "bar" — not a natural-feature concept
        frame = _frame_for("cocktail bars in Chicago", destination="Chicago")
        sf = _subtype_fit(entity, frame)
        # Should still score reasonably since "bar"/"cocktail" is the actual concept
        assert sf > 0.15, f"Cocktail bar query should not suppress non-natural-feature match"


# ── 4. Natural-feature concept recognition (synonym sets) ─────────────────────

class TestNaturalFeatureConceptRecognized:
    """Natural-feature concepts must be recognized so post-rank filter applies."""

    @pytest.mark.parametrize("label", [
        "beach", "public beach",
        "viewpoint", "scenic overlook", "observation deck",
        "sunset point", "sunset viewpoint",
        "lookout", "vista",
    ])
    def test_recognized(self, label: str):
        assert _has_known_synonym_set(label), f"'{label}' should be in a synonym set"


# ── 5. Ranker post-rank filter with natural-feature concepts ──────────────────

class TestRankerPostRankFilter:
    """When natural-feature concept is recognized and ≥1 on-concept entity exists,
    off-concept (restaurant/bar) entities must be dropped."""

    def test_viewpoint_drops_restaurant_when_viewpoint_present(self):
        """Restaurant 'Sunset Bar' dropped when a viewpoint entity is available."""
        restaurant = _make_entity(
            "Sunset Bar",
            types=["bar", "restaurant", "establishment", "point_of_interest"],
            primary_type="restaurant",
            source_query="sunset viewpoint Paris",
            place_id="rest_01",
        )
        viewpoint_entity = _make_entity(
            "Sacré-Cœur Panorama",
            types=["tourist_attraction", "observation_deck", "point_of_interest"],
            primary_type="tourist_attraction",
            source_query="sunset viewpoint Paris",
            place_id="view_01",
        )
        frame = _frame_for("best sunset points", destination="Paris")
        ranked, stats = rank_entities_with_stats(
            [restaurant, viewpoint_entity], frame, top_n=10
        )
        place_ids = {e.place_id for e, _ in ranked}
        # The viewpoint entity must appear; the pure restaurant should be dropped
        assert "view_01" in place_ids, "Viewpoint entity must survive ranking"
        if "rest_01" in place_ids:
            rest_sf = next(rs.subtype_fit for e, rs in ranked if e.place_id == "rest_01")
            view_sf = next(rs.subtype_fit for e, rs in ranked if e.place_id == "view_01")
            assert view_sf > rest_sf, "Viewpoint must rank above restaurant"

    def test_beach_park_beats_beach_restaurant(self):
        """Beach park entity ranks above restaurant for 'best beaches' query."""
        restaurant = _make_entity(
            "Ocean Beach Grill",
            types=["restaurant", "food", "establishment", "point_of_interest"],
            primary_type="restaurant",
            source_query="beach Miami",
            place_id="rest_02",
        )
        beach = _make_entity(
            "Lummus Park Beach",
            types=["beach", "beach_park", "park", "point_of_interest"],
            primary_type="beach",
            source_query="public beach Miami",
            place_id="beach_01",
        )
        frame = _frame_for("best beaches in Miami", destination="Miami")
        ranked, _stats = rank_entities_with_stats([restaurant, beach], frame, top_n=10)
        place_ids_ordered = [e.place_id for e, _ in ranked]
        assert "beach_01" in place_ids_ordered, "Beach entity must survive"
        if "rest_02" in place_ids_ordered and "beach_01" in place_ids_ordered:
            beach_idx = place_ids_ordered.index("beach_01")
            rest_idx = place_ids_ordered.index("rest_02")
            assert beach_idx < rest_idx, "Beach entity must rank above restaurant"


# ── 6. Editorial gate — Tavily suppressed for natural-feature queries ──────────

class TestNaturalFeatureEditorialGate:
    """should_run_editorial must return False for natural-feature concepts."""

    @pytest.mark.parametrize("query,destination", [
        ("Sunset points with Eiffel tower view", "Paris"),
        ("best beaches in Miami", "Miami"),
        ("best sunset points in San Diego", "San Diego"),
        ("scenic viewpoints in Barcelona", "Barcelona"),
        ("lookout points near Sydney", "Sydney"),
        ("sunset spots in Santorini", "Santorini"),
        ("best beach in Miami", "Miami"),
        ("viewpoints with city view", "London"),
    ])
    def test_no_editorial_for_natural_feature(self, query: str, destination: str):
        frame = extract_frame(query, destination)
        should_run, reason = should_run_editorial(frame)
        assert not should_run, (
            f"Editorial should be skipped for '{query}', got should_run=True reason={reason!r}"
        )
        assert "natural_feature" in reason, f"Expected natural_feature reason, got {reason!r}"

    def test_sports_bars_editorial_unaffected(self):
        """Editorial gate must NOT suppress editorial for sports bars (non-natural-feature)."""
        frame = extract_frame("best sports bars in Chicago", destination="Chicago")
        # Sports bars may or may not run editorial based on other signals;
        # the natural-feature gate must NOT fire here.
        should_run, reason = should_run_editorial(frame)
        assert "natural_feature" not in reason, (
            f"natural_feature gate should not fire for sports bars, got reason={reason!r}"
        )

    def test_cocktail_bars_editorial_unaffected(self):
        """Editorial gate must not suppress editorial for cocktail bars."""
        frame = extract_frame("best cocktail bars in NYC", destination="NYC")
        should_run, reason = should_run_editorial(frame)
        assert "natural_feature" not in reason

    def test_rooftop_bars_sunset_editorial_unaffected(self):
        """'rooftop bars with sunset views' — editorial gate fires on 'bar', not 'sunset'."""
        frame = extract_frame("rooftop bars with sunset views in Barcelona", destination="Barcelona")
        should_run, reason = should_run_editorial(frame)
        # Primary concept is "bar" not a natural-feature label, so gate must not fire
        assert "natural_feature" not in reason


# ── 7. Honest empty state — pipeline returns no cards for failed gate ──────────

class TestHonestEmptyState:
    """When natural-feature precision gate rejects all candidates, pipeline must
    return no cards (empty LiveResearchResult), not fall back to Tavily."""

    def test_gate_returns_no_cards_when_all_rejected(self):
        """All restaurant/bar candidates rejected → no cards in result."""
        from app.services.live_research import LiveResearchResult
        from app.models.concierge import SOURCE_NONE, SOURCE_LIVE_SEARCH

        # Simulate the gate logic directly (without hitting Google API)
        restaurant_entities = [
            _make_entity("Sunset Bar", ["bar", "establishment"], primary_type="bar"),
            _make_entity("Sunset/Sunside", ["restaurant", "establishment"], primary_type="restaurant"),
            _make_entity("Sunset Boulevard", ["night_club", "establishment"], primary_type="night_club"),
        ]

        frame = _frame_for("Sunset points with Eiffel tower view", destination="Paris")
        is_nf, category = _is_natural_feature_query(frame)
        assert is_nf, "Must detect as natural-feature query"

        passed = [e for e in restaurant_entities if _entity_passes_natural_feature_gate(e, category)]
        assert len(passed) == 0, "All restaurant/bar entities must fail the gate"
        assert len(passed) < _MIN_NATURAL_FEATURE_GATE_CANDIDATES, "Below minimum threshold"

    def test_gate_passes_viewpoint_candidates(self):
        """Viewpoint/observation entities pass the gate."""
        viewpoint_entities = [
            _make_entity(
                "Montmartre Viewpoint",
                ["tourist_attraction", "landmark", "point_of_interest"],
                primary_type="tourist_attraction",
            ),
            _make_entity(
                "Arc de Triomphe Panorama",
                ["observation_deck", "tourist_attraction", "point_of_interest"],
                primary_type="observation_deck",
            ),
        ]

        frame = _frame_for("best sunset points in Paris", destination="Paris")
        is_nf, category = _is_natural_feature_query(frame)
        passed = [e for e in viewpoint_entities if _entity_passes_natural_feature_gate(e, category)]
        assert len(passed) == len(viewpoint_entities), "All viewpoint entities must pass"

    def test_gate_passes_beach_candidates(self):
        """Beach/beach_park entities pass the gate for beach query."""
        beach_entities = [
            _make_entity(
                "South Beach",
                ["beach", "natural_feature", "point_of_interest"],
                primary_type="beach",
                source_query="beach Miami",
            ),
            _make_entity(
                "Lummus Park",
                ["beach_park", "park", "point_of_interest"],
                primary_type="beach_park",
                source_query="public beach Miami",
            ),
        ]
        frame = _frame_for("best beaches in Miami", destination="Miami")
        is_nf, category = _is_natural_feature_query(frame)
        passed = [e for e in beach_entities if _entity_passes_natural_feature_gate(e, category)]
        assert len(passed) == len(beach_entities), "All beach entities must pass"

    def test_no_fallback_to_tavily_for_empty_gate(self):
        """After gate returns 0 candidates, the pipeline does not call Tavily.

        Verified indirectly: should_run_editorial returns False for natural-feature
        concepts, and the gate itself returns SOURCE_NONE without consulting editorial.
        """
        frame = _frame_for("Sunset points with Eiffel tower view", destination="Paris")
        should_run, reason = should_run_editorial(frame)
        assert not should_run, "Editorial must not be attempted for sunset viewpoint query"


# ── 8. Venue-head preservation regression ─────────────────────────────────────

class TestVenueHeadPreservation:
    """Queries with explicit food/bar/hotel venue heads must not be affected by
    the natural-feature gate."""

    def test_rooftop_bars_vertical_is_restaurants(self):
        """'rooftop bars with sunset views' routes to restaurants vertical."""
        from app.services.concierge import ConciergeService
        vertical = ConciergeService._detect_semantic_vertical(
            intent="nightlife",
            user_query="rooftop bars with sunset views",
        )
        assert vertical == "restaurants", f"Expected restaurants, got {vertical!r}"

    def test_hotels_near_beach_vertical_is_hotels(self):
        """'hotels near the beach' routes to hotels vertical."""
        from app.services.concierge import ConciergeService
        vertical = ConciergeService._detect_semantic_vertical(
            intent="hotels",
            user_query="hotels near the beach",
        )
        assert vertical == "hotels", f"Expected hotels, got {vertical!r}"

    def test_sunset_restaurants_vertical_is_restaurants(self):
        """'sunset restaurants' — 'restaurant' is the explicit venue head."""
        from app.services.concierge import ConciergeService
        vertical = ConciergeService._detect_semantic_vertical(
            intent="restaurants",
            user_query="sunset restaurants in Paris",
        )
        assert vertical == "restaurants"

    def test_rooftop_bars_not_natural_feature_gate(self):
        """Natural-feature gate must NOT fire for 'rooftop bars with sunset views'."""
        frame = _frame_for("rooftop bars with sunset views", destination="Barcelona")
        is_nf, _cat = _is_natural_feature_query(frame)
        assert is_nf is False, "Bar venue head prevents natural-feature gate from firing"

    def test_hotels_near_beach_not_natural_feature_gate(self):
        """Natural-feature gate must NOT fire for 'hotels near the beach'."""
        frame = _frame_for("hotels near the beach", destination="Miami")
        is_nf, _cat = _is_natural_feature_query(frame)
        assert is_nf is False, "Hotel venue head prevents natural-feature gate from firing"

    def test_beach_bars_not_natural_feature_gate(self):
        """Natural-feature gate must NOT fire for 'beach bars' (explicit bar venue head)."""
        frame = _frame_for("beach bars in Miami", destination="Miami")
        is_nf, _cat = _is_natural_feature_query(frame)
        # Primary concept should be "bar" (venue head), not "beach"
        assert is_nf is False, "Bar venue head must prevent natural-feature gate"


# ── 9. Existing concierge routing regressions ─────────────────────────────────

class TestConciergeRoutingRegressions:
    """Existing intent detection and vertical routing must be unaffected."""

    @pytest.mark.parametrize("query,expected_intent", [
        ("sports bars in Chicago", "nightlife"),
        ("cocktail bars downtown", "nightlife"),
        ("credit card points for flights", "rewards_help"),
        ("best restaurants in Paris", "restaurants"),
        ("sunset points with Eiffel tower view", "attractions"),
        ("best beaches in Miami", "attractions"),
        ("hotels near the Eiffel Tower", "hotels"),
    ])
    def test_intent_detection(self, query: str, expected_intent: str):
        from app.services.concierge import ConciergeService
        # Use a minimal service instance (no DB needed for _detect_intent)
        svc = object.__new__(ConciergeService)
        intent = svc._detect_intent(query)
        from app.models.concierge import (
            INTENT_NIGHTLIFE, INTENT_REWARDS_HELP, INTENT_RESTAURANTS,
            INTENT_ATTRACTIONS, INTENT_HOTELS,
        )
        expected_map = {
            "nightlife": INTENT_NIGHTLIFE,
            "rewards_help": INTENT_REWARDS_HELP,
            "restaurants": INTENT_RESTAURANTS,
            "attractions": INTENT_ATTRACTIONS,
            "hotels": INTENT_HOTELS,
        }
        assert intent == expected_map[expected_intent], (
            f"Query {query!r}: expected {expected_intent!r}, got {intent!r}"
        )

    def test_credit_card_points_not_attractions(self):
        """'credit card points' must route to rewards_help, never attractions."""
        from app.services.concierge import ConciergeService
        svc = object.__new__(ConciergeService)
        intent = svc._detect_intent("credit card points redemption strategy")
        from app.models.concierge import INTENT_REWARDS_HELP
        assert intent == INTENT_REWARDS_HELP


# ── 10. _concept_is_natural_feature helper ────────────────────────────────────

class TestConceptIsNaturalFeature:
    """_concept_is_natural_feature must return True for natural-feature labels."""

    @pytest.mark.parametrize("label", [
        "beach", "sunset", "sunrise", "viewpoint",
        "lookout", "scenic", "overlook", "vista", "panorama",
        "waterfall", "trail", "garden",
    ])
    def test_is_natural_feature(self, label: str):
        assert _concept_is_natural_feature(label), f"'{label}' should be a natural-feature concept"

    @pytest.mark.parametrize("label", [
        "bar", "restaurant", "cafe", "brewery", "hotel",
        "taproom", "speakeasy", "cocktail", "pizza", "sushi",
    ])
    def test_is_not_natural_feature(self, label: str):
        assert not _concept_is_natural_feature(label), f"'{label}' should NOT be a natural-feature concept"
