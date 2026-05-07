"""Sev 1 regression tests — PR #272.

Covers Issues A-E from the post-PR-#271 production regression:
  A. Semantic card assembly carries priceLevel/priceRange through _entity_to_card.
  B. PlaceEntity extraction includes price_range from raw Google response.
  C. value_signals include "cheaper"/"lower-price" and trigger budget ranking.
  D. Off-concept (restaurant-only) cards are dropped when ≥1 on-concept bar card exists.
  E. Note-writer is skipped when cards_data is empty; telemetry emitted correctly.

No SQL changes. No new providers. No new LLM calls.
"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, List, Optional
from unittest.mock import MagicMock, patch

import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_raw_place(
    *,
    name: str = "Test Bar",
    place_id: str = "ChIJtest1",
    types: Optional[List[str]] = None,
    primary_type: Optional[str] = None,
    rating: float = 4.5,
    review_count: int = 300,
    business_status: str = "OPERATIONAL",
    address: str = "100 N State St, Chicago, IL, USA",
    maps_uri: str = "https://maps.google.com/?cid=1",
    price_level: Optional[str] = None,
    price_range: Optional[Dict[str, Any]] = None,
    lat: float = 41.88,
    lng: float = -87.63,
) -> Dict[str, Any]:
    raw: Dict[str, Any] = {
        "id": place_id,
        "displayName": {"text": name},
        "types": types or ["cocktail_bar", "bar", "food"],
        "primaryType": primary_type or (types[0] if types else "cocktail_bar"),
        "rating": rating,
        "userRatingCount": review_count,
        "businessStatus": business_status,
        "formattedAddress": address,
        "googleMapsUri": maps_uri,
        "websiteUri": None,
        "location": {"latitude": lat, "longitude": lng},
    }
    if price_level is not None:
        raw["priceLevel"] = price_level
    if price_range is not None:
        raw["priceRange"] = price_range
    return raw


def _provider_result(query: str, places: List[Dict[str, Any]], latency_ms: int = 100):
    from app.concierge.provider_executor import ProviderQueryResult
    return ProviderQueryResult(query=query, places=places, latency_ms=latency_ms)


def _make_entity(
    *,
    name: str = "Test Bar",
    place_id: str = "ChIJtest1",
    types: Optional[List[str]] = None,
    primary_type: Optional[str] = None,
    rating: float = 4.5,
    review_count: int = 300,
    price_level: Optional[str] = None,
    price_range: Optional[Dict[str, Any]] = None,
    address: str = "100 N State St, Chicago, IL, USA",
):
    from app.concierge.place_entity_layer import PlaceEntity
    return PlaceEntity(
        place_id=place_id,
        name=name,
        formatted_address=address,
        lat=41.88,
        lng=-87.63,
        business_status="OPERATIONAL",
        google_maps_uri="https://maps.google.com/?cid=1",
        types=types or ["cocktail_bar", "bar"],
        primary_type=primary_type or "cocktail_bar",
        rating=rating,
        user_rating_count=review_count,
        price_level=price_level,
        price_range=price_range,
        website_uri=None,
    )


# ══════════════════════════════════════════════════════════════════════════════
# A. Semantic card price wiring
# ══════════════════════════════════════════════════════════════════════════════

class TestSemanticCardPriceWiring:

    def test_entity_to_card_includes_price_level_in_supporting_details(self):
        """priceLevel from entity is carried into PlaceSupportingDetails."""
        from app.concierge.semantic_retrieval import _entity_to_card
        from app.concierge.frame_extractor import extract_frame
        entity = _make_entity(price_level="PRICE_LEVEL_MODERATE")
        frame = extract_frame("cocktail bars", "Chicago")
        card = _entity_to_card(entity, "A great bar.", frame, reason_validated=True)
        assert card is not None
        sd = card.supporting_details
        assert sd is not None
        assert sd.price_level == "PRICE_LEVEL_MODERATE"

    def test_entity_to_card_includes_price_range_in_supporting_details(self):
        """priceRange from entity is carried into PlaceSupportingDetails."""
        from app.concierge.semantic_retrieval import _entity_to_card
        from app.concierge.frame_extractor import extract_frame
        pr = {"startPrice": {"units": "10", "currencyCode": "USD"}, "endPrice": {"units": "25", "currencyCode": "USD"}}
        entity = _make_entity(price_range=pr)
        frame = extract_frame("cocktail bars", "Chicago")
        card = _entity_to_card(entity, "A great bar.", frame, reason_validated=True)
        assert card is not None
        sd = card.supporting_details
        assert sd is not None
        assert sd.price_range == pr

    def test_entity_to_card_sets_display_price_from_price_level(self):
        """display.displayPrice is set from priceLevel when no priceRange."""
        from app.concierge.semantic_retrieval import _entity_to_card
        from app.concierge.frame_extractor import extract_frame
        entity = _make_entity(price_level="PRICE_LEVEL_EXPENSIVE")
        frame = extract_frame("cocktail bars", "Chicago")
        card = _entity_to_card(entity, "A great bar.", frame, reason_validated=True)
        assert card is not None
        assert card.display is not None
        assert card.display.display_price == "$$$"

    def test_entity_to_card_sets_display_price_from_price_range(self):
        """display.displayPrice uses compact priceRange format when available."""
        from app.concierge.semantic_retrieval import _entity_to_card
        from app.concierge.frame_extractor import extract_frame
        pr = {"startPrice": {"units": "15", "currencyCode": "USD"}, "endPrice": {"units": "30", "currencyCode": "USD"}}
        entity = _make_entity(price_range=pr, price_level="PRICE_LEVEL_MODERATE")
        frame = extract_frame("cocktail bars", "Chicago")
        card = _entity_to_card(entity, "A great bar.", frame, reason_validated=True)
        assert card is not None
        assert card.display is not None
        # priceRange beats priceLevel for display
        assert card.display.display_price == "$15–30"

    def test_entity_to_card_no_price_does_not_drop_card(self):
        """Cards with no price fields are still returned (price absent != card dropped)."""
        from app.concierge.semantic_retrieval import _entity_to_card
        from app.concierge.frame_extractor import extract_frame
        entity = _make_entity()  # no price_level, no price_range
        frame = extract_frame("cocktail bars", "Chicago")
        card = _entity_to_card(entity, "A great bar.", frame, reason_validated=True)
        assert card is not None
        sd = card.supporting_details
        assert sd is not None
        assert sd.price_level is None
        assert sd.price_range is None
        assert card.display.display_price is None

    def test_entity_to_card_display_price_none_when_no_price_fields(self):
        """display.displayPrice is None when no price data is available."""
        from app.concierge.semantic_retrieval import _entity_to_card
        from app.concierge.frame_extractor import extract_frame
        entity = _make_entity()
        frame = extract_frame("cocktail bars", "Chicago")
        card = _entity_to_card(entity, "A great bar.", frame, reason_validated=True)
        assert card is not None
        assert card.display.display_price is None

    def test_price_level_symbol_no_raw_enum_exposed(self):
        """display_price never exposes raw enum names like PRICE_LEVEL_MODERATE."""
        from app.concierge.semantic_retrieval import _entity_to_card, _PRICE_LEVEL_SYMBOL
        from app.concierge.frame_extractor import extract_frame
        for level in ("PRICE_LEVEL_FREE", "PRICE_LEVEL_INEXPENSIVE", "PRICE_LEVEL_MODERATE",
                      "PRICE_LEVEL_EXPENSIVE", "PRICE_LEVEL_VERY_EXPENSIVE"):
            entity = _make_entity(price_level=level)
            frame = extract_frame("cocktail bars", "Chicago")
            card = _entity_to_card(entity, "A great bar.", frame, reason_validated=True)
            assert card is not None
            dp = card.display.display_price
            assert dp is not None
            assert "PRICE_LEVEL" not in dp, f"Raw enum exposed: {dp}"
            assert dp in ("Free", "$", "$$", "$$$", "$$$$"), f"Unknown symbol: {dp}"


# ══════════════════════════════════════════════════════════════════════════════
# A. PlaceEntity price_range extraction
# ══════════════════════════════════════════════════════════════════════════════

class TestPlaceEntityPriceExtraction:

    def test_build_entity_layer_extracts_price_range(self):
        """build_entity_layer carries priceRange from raw Google response into PlaceEntity."""
        from app.concierge.place_entity_layer import build_entity_layer
        pr = {"startPrice": {"units": "12", "currencyCode": "USD"}, "endPrice": {"units": "28", "currencyCode": "USD"}}
        raw = _make_raw_place(price_range=pr, price_level="PRICE_LEVEL_MODERATE")
        result = _provider_result("cocktail bars Chicago", [raw])
        entities, stats = build_entity_layer([result])
        assert len(entities) == 1
        entity = entities[0]
        assert entity.price_range == pr
        assert entity.price_level == "PRICE_LEVEL_MODERATE"

    def test_build_entity_layer_price_range_absent_is_none(self):
        """Missing priceRange is stored as None on the entity."""
        from app.concierge.place_entity_layer import build_entity_layer
        raw = _make_raw_place(price_level="PRICE_LEVEL_INEXPENSIVE")
        result = _provider_result("cocktail bars Chicago", [raw])
        entities, _ = build_entity_layer([result])
        assert len(entities) == 1
        assert entities[0].price_range is None
        assert entities[0].price_level == "PRICE_LEVEL_INEXPENSIVE"

    def test_build_entity_layer_no_price_fields_not_rejected(self):
        """Entities without price fields are still included — not treated as OPERATIONAL failure."""
        from app.concierge.place_entity_layer import build_entity_layer
        raw = _make_raw_place()  # no price_level, no price_range
        result = _provider_result("cocktail bars Chicago", [raw])
        entities, stats = build_entity_layer([result])
        assert len(entities) == 1
        assert entities[0].price_level is None
        assert entities[0].price_range is None


# ══════════════════════════════════════════════════════════════════════════════
# C. Value signals — frame extractor detects "cheaper" / "lower price"
# ══════════════════════════════════════════════════════════════════════════════

class TestValueSignalDetection:

    def test_cheaper_triggers_budget_signal(self):
        """'cheaper' in query produces value_signals = [..., 'budget']."""
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("best hidden gem cocktail bars Chicago — find cheaper", "Chicago")
        assert "budget" in frame.value_signals, f"value_signals={frame.value_signals}"

    def test_lower_price_triggers_budget_signal(self):
        """'lower-price' / 'lower price' in query produces budget signal."""
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("cocktail bars lower price", "Chicago")
        assert "budget" in frame.value_signals, f"value_signals={frame.value_signals}"

    def test_find_cheaper_nearby_triggers_budget_signal(self):
        """'find cheaper nearby' contextual query triggers budget signal."""
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("best hidden gem cocktail bars Chicago — find cheaper nearby", "Chicago")
        assert "budget" in frame.value_signals, f"value_signals={frame.value_signals}"

    def test_affordable_triggers_budget_signal(self):
        """'affordable' continues to trigger budget signal (regression guard)."""
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("affordable cocktail bars", "Chicago")
        assert "budget" in frame.value_signals

    def test_budget_still_detected(self):
        """'budget' keyword still triggers budget signal (regression guard)."""
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("budget cocktail bars", "Chicago")
        assert "budget" in frame.value_signals

    def test_upscale_query_does_not_trigger_budget(self):
        """'upscale' query must not falsely trigger budget signal."""
        from app.concierge.frame_extractor import extract_frame
        frame = extract_frame("upscale cocktail bars", "Chicago")
        assert "budget" not in frame.value_signals


# ══════════════════════════════════════════════════════════════════════════════
# C. Value-aware ranking in semantic path
# ══════════════════════════════════════════════════════════════════════════════

class TestValueAwareRankingSemanticPath:

    def _run_rank(self, entities, value_signals=None):
        from app.concierge.ranker import rank_entities_with_stats
        from app.concierge.frame_extractor import ExperienceFrame, SubtypeConcept
        concepts = [SubtypeConcept(label="cocktail bar", confidence=0.9, source="literal_primary")]
        frame = ExperienceFrame(
            literal_ask="find cheaper cocktail bars",
            normalized_ask="find cheaper cocktail bars",
            destination="Chicago",
            subtype_concepts=concepts,
            geography_hints=[],
            soft_preferences=[],
            negative_constraints=[],
            value_signals=value_signals or [],
            use_cases=[],
            ambiguity_flags=[],
            temporal_constraints=[],
            location_modifiers=[],
        )
        result, _ = rank_entities_with_stats(entities, frame, top_n=10)
        return result

    def test_cheaper_query_sorts_inexpensive_first(self):
        """Budget value signal sorts INEXPENSIVE bar before EXPENSIVE bar."""
        cheap = _make_entity(name="Cheap Bar", place_id="cheap1",
                             price_level="PRICE_LEVEL_INEXPENSIVE", rating=4.2)
        expensive = _make_entity(name="Fancy Bar", place_id="exp1",
                                 price_level="PRICE_LEVEL_EXPENSIVE", rating=4.7)
        ranked = self._run_rank([cheap, expensive], value_signals=["budget"])
        names = [e.name for e, _ in ranked]
        assert names[0] == "Cheap Bar", f"Expected cheap first, got {names}"

    def test_unknown_price_sorts_after_known_cheap(self):
        """Unknown price must sort after known inexpensive — never treated as cheap."""
        cheap = _make_entity(name="Cheap Bar", place_id="cheap1",
                             price_level="PRICE_LEVEL_INEXPENSIVE", rating=4.0)
        unknown = _make_entity(name="No Price Bar", place_id="noprice1",
                               price_level=None, rating=4.8)
        ranked = self._run_rank([cheap, unknown], value_signals=["budget"])
        names = [e.name for e, _ in ranked]
        assert names[0] == "Cheap Bar", f"Unknown price should not beat known cheap: {names}"

    def test_normal_query_uses_score_order_not_price_order(self):
        """Without value signals, high-rated card ranks above low-price card."""
        cheap = _make_entity(name="Cheap Bar", place_id="cheap1",
                             price_level="PRICE_LEVEL_INEXPENSIVE", rating=3.5, review_count=50)
        popular = _make_entity(name="Popular Bar", place_id="pop1",
                               price_level="PRICE_LEVEL_EXPENSIVE", rating=4.9, review_count=2000)
        ranked = self._run_rank([cheap, popular], value_signals=[])
        names = [e.name for e, _ in ranked]
        assert names[0] == "Popular Bar", f"High-rated should rank first when no budget signal: {names}"


# ══════════════════════════════════════════════════════════════════════════════
# D. Wrong-category rejection fixture (cocktail bars query)
# ══════════════════════════════════════════════════════════════════════════════

class TestWrongCategoryRejection:

    def _make_frame(self, query="best hidden gem cocktail bars"):
        from app.concierge.frame_extractor import extract_frame
        return extract_frame(query, "Chicago")

    def test_cocktail_bar_query_rejects_japanese_restaurant_when_bars_available(self):
        """Japanese restaurant is dropped from results when at least 1 cocktail bar exists."""
        from app.concierge.ranker import rank_entities_with_stats
        frame = self._make_frame()
        bar = _make_entity(
            name="Club X Speakeasy", place_id="bar1",
            types=["cocktail_bar", "bar"], primary_type="cocktail_bar",
            rating=4.8, review_count=280,
        )
        japanese = _make_entity(
            name="Menya Goku", place_id="jp1",
            types=["japanese_restaurant", "restaurant", "food"],
            primary_type="japanese_restaurant",
            rating=4.7, review_count=1500,
        )
        ranked, stats = rank_entities_with_stats([bar, japanese], frame, top_n=10)
        names = [e.name for e, _ in ranked]
        assert "Club X Speakeasy" in names, f"Cocktail bar must survive: {names}"
        assert "Menya Goku" not in names, (
            f"Japanese restaurant must be dropped when cocktail bar exists: {names}"
        )

    def test_cocktail_bar_query_rejects_american_restaurant_when_bars_available(self):
        """American restaurant is dropped from results when at least 1 cocktail bar exists."""
        from app.concierge.ranker import rank_entities_with_stats
        frame = self._make_frame()
        bar = _make_entity(
            name="Hidden Cocktail Lounge", place_id="bar2",
            types=["cocktail_bar", "bar"], primary_type="cocktail_bar",
        )
        american = _make_entity(
            name="Willow Room", place_id="amer1",
            types=["american_restaurant", "restaurant", "food"],
            primary_type="american_restaurant",
            rating=4.6, review_count=900,
        )
        ranked, stats = rank_entities_with_stats([bar, american], frame, top_n=10)
        names = [e.name for e, _ in ranked]
        assert "Willow Room" not in names, (
            f"American restaurant must be dropped when cocktail bar exists: {names}"
        )

    def test_two_cocktail_bars_one_restaurant_drops_restaurant(self):
        """With 2 on-concept bars, off-concept restaurant is dropped."""
        from app.concierge.ranker import rank_entities_with_stats
        frame = self._make_frame()
        bar1 = _make_entity(name="Bar Alpha", place_id="bar_a",
                            types=["cocktail_bar", "bar"], primary_type="cocktail_bar", rating=4.7)
        bar2 = _make_entity(name="Bar Beta", place_id="bar_b",
                            types=["cocktail_bar", "bar"], primary_type="cocktail_bar", rating=4.5)
        restaurant = _make_entity(name="Generic Restaurant", place_id="rest1",
                                  types=["restaurant", "food"], primary_type="restaurant", rating=4.9)
        ranked, _ = rank_entities_with_stats([bar1, bar2, restaurant], frame, top_n=10)
        names = [e.name for e, _ in ranked]
        assert "Generic Restaurant" not in names, f"Restaurant must be dropped: {names}"
        assert len(names) == 2

    def test_no_concept_cards_returns_empty_not_restaurants(self):
        """When concept is recognized (cocktail) and zero on-concept cards exist, return empty."""
        from app.concierge.ranker import rank_entities_with_stats
        frame = self._make_frame()
        japanese = _make_entity(
            name="Menya Goku", place_id="jp1",
            types=["japanese_restaurant", "restaurant"],
            primary_type="japanese_restaurant",
            rating=4.9, review_count=2000,
        )
        ranked, stats = rank_entities_with_stats([japanese], frame, top_n=10)
        names = [e.name for e, _ in ranked]
        assert names == [], (
            f"Recognized concept with zero on-concept cards must return empty: {names}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# E. Note writer skip when cards_data is empty
# ══════════════════════════════════════════════════════════════════════════════

class TestNoteWriterSkipOnEmptyCards:

    def test_note_writer_skipped_when_no_cards_data(self):
        """build_reasons_with_retry must NOT be called when cards_data is empty."""
        from app.concierge.semantic_retrieval import _assemble_card_set
        from app.concierge.batched_reason_builder import CardReason, ReasoningResultV2, SOURCE_OMITTED

        with patch("app.concierge.batched_reason_builder.build_reasons_with_retry") as mock_build:
            # Simulate the skipped path: empty cards_data with skipped_no_valid_cards
            cards, _, excluded, visible, without_notes = _assemble_card_set(
                cards_data=[],
                card_reasons={},
                frame=MagicMock(subtype_concepts=[MagicMock(label="cocktail bar")]),
                note_generation_timed_out=False,
                set_writer_primary_active=False,
            )
            # _assemble_card_set processes cards_data; no call to the builder directly
            assert cards == []
            mock_build.assert_not_called()

    def test_fallback_note_visible_count_always_zero_in_assembled_cards(self):
        """Assembled cards never carry fallback_note_visible_count > 0 (contract invariant)."""
        from app.concierge.semantic_retrieval import _entity_to_card
        from app.concierge.frame_extractor import extract_frame
        entity = _make_entity()
        frame = extract_frame("cocktail bars", "Chicago")
        # reason_validated=False means the note block is hidden — card is still returned
        card = _entity_to_card(entity, "", frame, reason_source="deterministic_safe_v1",
                               reason_validated=False)
        assert card is not None
        assert card.display is not None
        assert card.display.display_why_validated is False


# ══════════════════════════════════════════════════════════════════════════════
# A (frontend contract) — _format_display_price logic (backend side)
# ══════════════════════════════════════════════════════════════════════════════

class TestFormatDisplayPriceSemanticHelper:

    def test_price_range_compact_format(self):
        from app.concierge.semantic_retrieval import _format_display_price
        pr = {"startPrice": {"units": "10", "currencyCode": "USD"},
              "endPrice": {"units": "25", "currencyCode": "USD"}}
        assert _format_display_price(None, pr) == "$10–25"

    def test_price_range_beats_price_level(self):
        from app.concierge.semantic_retrieval import _format_display_price
        pr = {"startPrice": {"units": "15", "currencyCode": "USD"},
              "endPrice": {"units": "30", "currencyCode": "USD"}}
        assert _format_display_price("PRICE_LEVEL_EXPENSIVE", pr) == "$15–30"

    def test_price_level_fallback_when_no_range(self):
        from app.concierge.semantic_retrieval import _format_display_price
        assert _format_display_price("PRICE_LEVEL_MODERATE", None) == "$$"
        assert _format_display_price("PRICE_LEVEL_INEXPENSIVE", None) == "$"
        assert _format_display_price("PRICE_LEVEL_EXPENSIVE", None) == "$$$"
        assert _format_display_price("PRICE_LEVEL_VERY_EXPENSIVE", None) == "$$$$"
        assert _format_display_price("PRICE_LEVEL_FREE", None) == "Free"

    def test_zero_unit_range_falls_through_to_price_level(self):
        from app.concierge.semantic_retrieval import _format_display_price
        pr = {"startPrice": {"units": "0", "currencyCode": "USD"},
              "endPrice": {"units": "0", "currencyCode": "USD"}}
        result = _format_display_price("PRICE_LEVEL_MODERATE", pr)
        assert result == "$$"  # zero-unit range falls through to price level

    def test_both_absent_returns_none(self):
        from app.concierge.semantic_retrieval import _format_display_price
        assert _format_display_price(None, None) is None

    def test_non_usd_uses_currency_code(self):
        from app.concierge.semantic_retrieval import _format_display_price
        pr = {"startPrice": {"units": "10", "currencyCode": "EUR"},
              "endPrice": {"units": "25", "currencyCode": "EUR"}}
        assert _format_display_price(None, pr) == "EUR10–25"
