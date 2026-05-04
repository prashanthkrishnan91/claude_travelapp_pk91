"""Tests for the Fast Dynamic Place Search pipeline.

Coverage:
1. Natural-language extraction: tapas/sushi/seafood/cocktail intent preservation.
2. Fast path returns only OPERATIONAL Google-verified addable cards.
3. Fast path does NOT call the old slow serial reason-generation path.
4. Dynamic reasons are specific to the user ask, never generic rating repeats.
5. Reasons do not invent unsupported facts.
6. Category scoring: tapas, sushi, cocktail, seafood stay in the right bucket.
7. Cache/pool key separation by query subtype.
8. Feature flag OFF preserves existing path (no fast-search import).
9. Google unavailable returns safe warning quickly.
10. More-options pool logic is compatible (unit-level only).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from app.services.fast_dynamic_place_search import (
    FastDynamicPlaceSearch,
    ParsedPlaceQuery,
    _OPERATIONAL,
    _bayesian_score,
    _build_dynamic_why,
    _category_score,
    _derive_cuisine_label,
    parse_place_query,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_place(
    *,
    name: str = "Test Place",
    types: Optional[List[str]] = None,
    rating: Optional[float] = 4.5,
    review_count: Optional[int] = 500,
    place_id: str = "pid123",
    business_status: str = _OPERATIONAL,
    address: str = "100 Main St, Chicago, IL, USA",
    maps_uri: str = "https://maps.google.com/?cid=1",
    price_level: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": place_id,
        "displayName": {"text": name},
        "types": types or ["restaurant", "food"],
        "rating": rating,
        "userRatingCount": review_count,
        "businessStatus": business_status,
        "formattedAddress": address,
        "googleMapsUri": maps_uri,
        "websiteUri": None,
        "priceLevel": price_level,
    }


def _tapas_parsed() -> ParsedPlaceQuery:
    return parse_place_query("tapas bar", "Chicago")


def _sushi_waterfront_parsed() -> ParsedPlaceQuery:
    return parse_place_query("nice sushi restaurants with a waterfront view", "Chicago")


def _romantic_tapas_parsed() -> ParsedPlaceQuery:
    return parse_place_query("romantic tapas but not too loud", "Chicago")


def _cocktail_parsed() -> ParsedPlaceQuery:
    return parse_place_query("cocktail bars", "Chicago")


def _seafood_parsed() -> ParsedPlaceQuery:
    return parse_place_query("seafood restaurants", "Chicago")


# ── 1. Natural-language extraction ────────────────────────────────────────────


class TestParseQuery:
    def test_tapas_bar_preserves_tapas_subtype(self) -> None:
        parsed = _tapas_parsed()
        assert parsed.cuisine == "tapas", "tapas must be extracted as subtype"
        assert "tapas" in parsed.search_query.lower(), "search_query must include tapas"
        assert "cocktail" not in parsed.search_query.lower(), "must NOT collapse to cocktail bars"

    def test_tapas_bar_place_type_is_restaurant_or_bar(self) -> None:
        parsed = _tapas_parsed()
        assert parsed.place_type in (
            "restaurant_or_bar", "restaurant",
        ), "tapas bar should be restaurant-first, not pure nightlife bar"

    def test_sushi_waterfront_extracts_cuisine_and_constraint(self) -> None:
        parsed = _sushi_waterfront_parsed()
        assert parsed.cuisine == "sushi", "sushi must be extracted"
        assert parsed.constraint in (
            "waterfront", "view", "water",
        ), f"waterfront constraint expected, got {parsed.constraint!r}"

    def test_romantic_tapas_not_loud(self) -> None:
        parsed = _romantic_tapas_parsed()
        assert parsed.cuisine == "tapas"
        assert parsed.vibe == "romantic"
        assert parsed.negative_constraint is not None
        assert "loud" in (parsed.negative_constraint or "")
        # Search query should not include the negative constraint
        assert "not too loud" not in parsed.search_query.lower()

    def test_seafood_restaurants_remains_seafood(self) -> None:
        parsed = _seafood_parsed()
        assert parsed.cuisine == "seafood"
        assert "seafood" in parsed.search_query.lower()

    def test_cocktail_bars_remains_cocktail_bar(self) -> None:
        parsed = _cocktail_parsed()
        assert parsed.place_type == "bar"
        assert parsed.cuisine is None or "cocktail" not in (parsed.cuisine or "")
        assert "cocktail" in parsed.search_query.lower()

    def test_italian_restaurants(self) -> None:
        parsed = parse_place_query("Italian restaurants", "Chicago")
        assert parsed.cuisine == "italian"
        assert "italian" in parsed.search_query.lower()

    def test_mexican_restaurants(self) -> None:
        parsed = parse_place_query("Mexican restaurants", "Chicago")
        assert parsed.cuisine == "mexican"

    def test_destination_is_appended_to_search_query(self) -> None:
        parsed = parse_place_query("sushi", "Seattle")
        assert "Seattle" in parsed.search_query


# ── 2. Category scoring ────────────────────────────────────────────────────────


class TestCategoryScore:
    def test_tapas_name_match_scores_highest(self) -> None:
        place = _make_place(name="La Taperia Tapas", types=["restaurant"])
        score = _category_score(place, _tapas_parsed())
        assert score >= 0.9, f"tapas in name should score >= 0.9, got {score}"

    def test_tapas_spanish_restaurant_type_scores_high(self) -> None:
        place = _make_place(name="El Rincón", types=["spanish_restaurant", "restaurant"])
        score = _category_score(place, _tapas_parsed())
        assert score >= 0.85, f"spanish_restaurant for tapas should score >= 0.85, got {score}"

    def test_cocktail_bar_scores_low_for_tapas(self) -> None:
        place = _make_place(name="The Aviary", types=["cocktail_bar", "bar"])
        score = _category_score(place, _tapas_parsed())
        assert score < 0.5, (
            f"cocktail bar should score low for tapas query, got {score}"
        )

    def test_cocktail_bar_scores_high_for_cocktail_query(self) -> None:
        place = _make_place(name="The Violet Hour", types=["cocktail_bar", "bar"])
        score = _category_score(place, _cocktail_parsed())
        assert score >= 0.9, f"cocktail_bar should score >= 0.9 for cocktail bars query, got {score}"

    def test_non_operational_returns_minus_one(self) -> None:
        place = _make_place(business_status="CLOSED_PERMANENTLY")
        score = _category_score(place, _tapas_parsed())
        assert score == -1.0

    def test_sushi_restaurant_type_scores_high_for_sushi(self) -> None:
        place = _make_place(name="Omakase Chicago", types=["sushi_restaurant", "japanese_restaurant"])
        score = _category_score(place, _sushi_waterfront_parsed())
        assert score >= 0.9, f"sushi_restaurant for sushi query should score >= 0.9, got {score}"

    def test_seafood_restaurant_type_scores_high(self) -> None:
        place = _make_place(name="Shaw's Crab House", types=["seafood_restaurant", "restaurant"])
        score = _category_score(place, _seafood_parsed())
        assert score >= 0.9, f"seafood_restaurant should score >= 0.9, got {score}"

    def test_restaurant_without_cuisine_match_penalized(self) -> None:
        # Generic restaurant for a cuisine-specific query should be penalized
        place = _make_place(name="American Grill", types=["restaurant", "food"])
        parsed = parse_place_query("sushi restaurants", "Chicago")
        score = _category_score(place, parsed)
        assert score <= 0.5, (
            f"generic restaurant should score <= 0.5 for cuisine-specific query, got {score}"
        )


# ── 3. Dynamic reasons — specific, not generic ────────────────────────────────


class TestDynamicReasons:
    def test_tapas_reason_mentions_tapas_not_cocktail_as_main_category(self) -> None:
        why = _build_dynamic_why(
            place_name="El Milagro",
            types=["spanish_restaurant"],
            cuisine_label="Tapas / Spanish",
            address="200 W Randolph St, Chicago, IL",
            rating=4.6,
            review_count=300,
            price_level=None,

            parsed=_tapas_parsed(),
        )
        assert "tapas" in why.lower(), f"tapas reason must mention tapas: {why!r}"
        # The reason may contrast with "cocktail bar" to differentiate the result,
        # but it must not describe this place AS a cocktail bar.
        # Bad: "This is a cocktail bar." Good: "tapas match, not a cocktail bar."
        lower = why.lower()
        if "cocktail" in lower:
            assert any(
                neg in lower for neg in ("not a", "than a", "no cocktail", "unlike")
            ), (
                f"if 'cocktail' appears, it must be in a differentiating/negative context: {why!r}"
            )

    def test_tapas_romantic_reason_mentions_dinner_date(self) -> None:
        why = _build_dynamic_why(
            place_name="Café Ibérico",
            types=["spanish_restaurant"],
            cuisine_label="Tapas / Spanish",
            address="739 N LaSalle Dr, Chicago, IL",
            rating=4.5,
            review_count=1200,
            price_level=None,

            parsed=_romantic_tapas_parsed(),
        )
        lower = why.lower()
        assert (
            "romantic" in lower or "dinner" in lower or "date" in lower
        ), f"romantic tapas reason should reference dinner/date/romantic: {why!r}"
        assert "tapas" in lower, f"romantic tapas reason must mention tapas: {why!r}"

    def test_sushi_waterfront_reason_mentions_both(self) -> None:
        why = _build_dynamic_why(
            place_name="Sushi-San",
            types=["sushi_restaurant"],
            cuisine_label="Sushi Restaurant",
            address="55 W Illinois St, Chicago, IL",
            rating=4.7,
            review_count=800,
            price_level=None,

            parsed=_sushi_waterfront_parsed(),
        )
        lower = why.lower()
        assert "sushi" in lower, f"sushi waterfront reason must mention sushi: {why!r}"
        assert any(w in lower for w in ("waterfront", "view", "water")), (
            f"sushi waterfront reason must mention waterfront/view/water: {why!r}"
        )

    def test_reason_does_not_just_repeat_rating(self) -> None:
        why = _build_dynamic_why(
            place_name="Great Tapas",
            types=["spanish_restaurant"],
            cuisine_label="Tapas / Spanish",
            address="Chicago, IL",
            rating=4.5,
            review_count=500,
            price_level=None,

            parsed=_tapas_parsed(),
        )
        # Must not start with just the rating
        assert not why.strip().startswith("4."), f"reason must not start with rating: {why!r}"
        assert not re.match(r"^This place has", why, re.IGNORECASE), (
            f"reason must not be generic: {why!r}"
        )

    def test_reason_does_not_invent_michelin(self) -> None:
        why = _build_dynamic_why(
            place_name="Tapas Express",
            types=["restaurant"],
            cuisine_label="Restaurant",
            address="Chicago, IL",
            rating=4.2,
            review_count=100,
            price_level=None,

            parsed=_tapas_parsed(),
        )
        assert "michelin" not in why.lower(), f"must not invent Michelin: {why!r}"

    def test_reason_does_not_invent_awards(self) -> None:
        why = _build_dynamic_why(
            place_name="Generic Grill",
            types=["restaurant"],
            cuisine_label="Restaurant",
            address="Chicago, IL",
            rating=4.0,
            review_count=50,
            price_level=None,

            parsed=_tapas_parsed(),
        )
        assert "award" not in why.lower(), f"must not invent awards: {why!r}"
        assert "james beard" not in why.lower(), f"must not invent James Beard: {why!r}"

    def test_reason_max_length(self) -> None:
        why = _build_dynamic_why(
            place_name="A Very Long Named Tapas Restaurant That Exists in Chicago",
            types=["spanish_restaurant"],
            cuisine_label="Tapas / Spanish",
            address="1234 N Long Address Street, Suite 100, Chicago, IL 60601",
            rating=4.5,
            review_count=500,
            price_level=None,

            parsed=_tapas_parsed(),
        )
        assert len(why) <= 165, f"reason must be <= 165 chars, got {len(why)}: {why!r}"

    def test_upscale_price_level_appears_in_reason(self) -> None:
        why = _build_dynamic_why(
            place_name="Sushi Nakazawa",
            types=["sushi_restaurant"],
            cuisine_label="Sushi Restaurant",
            address="200 W Grand Ave, Chicago, IL",
            rating=4.8,
            review_count=900,
            price_level="PRICE_LEVEL_EXPENSIVE",
            parsed=parse_place_query("sushi", "Chicago"),
        )
        assert "upscale" in why.lower(), f"EXPENSIVE price level should surface as 'upscale': {why!r}"

    def test_most_reviewed_tier_appears_for_high_count(self) -> None:
        why = _build_dynamic_why(
            place_name="Girl & the Goat",
            types=["restaurant"],
            cuisine_label="American Restaurant",
            address="820 W Randolph St, Chicago, IL",
            rating=4.5,
            review_count=2500,
            price_level=None,
            parsed=parse_place_query("dinner restaurants", "Chicago"),
        )
        assert "most-reviewed" in why.lower() or "well-rated" in why.lower(), (
            f"2500 reviews should trigger high-volume tier language: {why!r}"
        )


# ── 4. Cuisine label derivation ───────────────────────────────────────────────


class TestCuisineLabel:
    def test_spanish_restaurant_type_gives_spanish_label(self) -> None:
        label = _derive_cuisine_label(["spanish_restaurant", "restaurant"], None)
        assert label == "Spanish Restaurant"

    def test_tapas_hint_gives_tapas_label(self) -> None:
        label = _derive_cuisine_label(["restaurant"], "tapas")
        assert label == "Tapas / Spanish"

    def test_sushi_restaurant_type_takes_priority(self) -> None:
        label = _derive_cuisine_label(["sushi_restaurant", "japanese_restaurant"], "sushi")
        assert label == "Sushi Restaurant"

    def test_cocktail_bar_type_gives_cocktail_bar_label(self) -> None:
        label = _derive_cuisine_label(["cocktail_bar", "bar"], None)
        assert label == "Cocktail Bar"


# ── 5. FastDynamicPlaceSearch integration (mocked) ────────────────────────────


class TestFastDynamicSearchIntegration:
    """Integration tests that mock _google_text_search directly (no httpx needed)."""

    def _make_service(self) -> FastDynamicPlaceSearch:
        return FastDynamicPlaceSearch(api_key="test-key", max_candidates=10)

    def test_tapas_query_returns_restaurant_cards_not_cocktail_bars(self) -> None:
        tapas_place = _make_place(
            name="El Milagro Tapas", types=["spanish_restaurant", "restaurant"],
            place_id="tapas123",
        )
        cocktail_place = _make_place(
            name="The Aviary", types=["cocktail_bar", "bar"],
            place_id="aviary456",
        )
        svc = self._make_service()

        with patch.object(svc, "_google_text_search", return_value=[tapas_place, cocktail_place]):
            result = svc.search(
                user_query="tapas bar",
                destination="Chicago",
                intent="nightlife",
            )

        assert result.restaurants, "must return at least one card"
        names = [r.name for r in result.restaurants]
        assert "El Milagro Tapas" in names, f"tapas place must be in results: {names}"

    def test_tapas_card_why_is_tapas_specific(self) -> None:
        tapas_place = _make_place(
            name="Café Ibérico", types=["spanish_restaurant", "restaurant"],
            place_id="tapas789",
        )
        svc = self._make_service()

        with patch.object(svc, "_google_text_search", return_value=[tapas_place]):
            result = svc.search(
                user_query="tapas bar",
                destination="Chicago",
                intent="restaurants",
            )

        assert result.restaurants
        card = result.restaurants[0]
        assert card.display is not None
        why = card.display.display_why
        assert "tapas" in why.lower(), (
            f"card reason must mention tapas for tapas query: {why!r}"
        )
        # The reason may say "not a cocktail bar" but must not describe it AS one
        lower = why.lower()
        if "cocktail" in lower:
            assert any(neg in lower for neg in ("not a", "than a", "unlike")), (
                f"if 'cocktail' appears, it must be in differentiating context: {why!r}"
            )

    def test_fast_path_does_not_call_slow_reason_builder(self) -> None:
        """Fast path must NOT call build_why_pick_with_structured_evidence (old serial path)."""
        tapas_place = _make_place(name="Jaleo", types=["spanish_restaurant"])
        svc = self._make_service()

        with patch.object(svc, "_google_text_search", return_value=[tapas_place]), patch(
            "app.concierge.reasoning.build_why_pick_with_structured_evidence"
        ) as mock_slow_builder:
            svc.search(
                user_query="tapas bar",
                destination="Chicago",
                intent="restaurants",
            )

        mock_slow_builder.assert_not_called(), (
            "fast path must not call the slow serial LLM reason builder"
        )

    def test_only_operational_places_are_returned(self) -> None:
        closed_place = _make_place(
            name="Closed Tapas", types=["spanish_restaurant"],
            business_status="CLOSED_PERMANENTLY", place_id="closed1",
        )
        open_place = _make_place(
            name="Open Tapas", types=["spanish_restaurant"],
            business_status=_OPERATIONAL, place_id="open1",
        )
        svc = self._make_service()

        with patch.object(svc, "_google_text_search", return_value=[closed_place, open_place]):
            result = svc.search(
                user_query="tapas bar", destination="Chicago", intent="restaurants"
            )

        names = [r.name for r in result.restaurants]
        assert "Closed Tapas" not in names, "closed places must not be returned"
        assert "Open Tapas" in names, "open operational places must be returned"

    def test_prior_identity_keys_dedup(self) -> None:
        """Places whose place_id appears in prior_identity_keys must be excluded."""
        place = _make_place(name="Already Shown", types=["restaurant"], place_id="pid_shown")
        svc = self._make_service()

        with patch.object(svc, "_google_text_search", return_value=[place]):
            result = svc.search(
                user_query="restaurants",
                destination="Chicago",
                intent="restaurants",
                prior_identity_keys={"pid:pid_shown"},
            )

        assert not result.restaurants, "already-shown place must be excluded"

    def test_unavailable_returns_source_unavailable(self) -> None:
        svc = FastDynamicPlaceSearch(api_key="", max_candidates=10)
        result = svc.search(
            user_query="tapas bar", destination="Chicago", intent="restaurants"
        )
        from app.models.concierge import SOURCE_UNAVAILABLE
        assert result.source_status == SOURCE_UNAVAILABLE

    def test_google_api_failure_returns_empty_result(self) -> None:
        svc = self._make_service()
        with patch.object(svc, "_google_text_search", return_value=[]):
            result = svc.search(
                user_query="tapas bar", destination="Chicago", intent="restaurants"
            )

        assert result.restaurants == []
        assert result.provider_name == "google_places_fast_dynamic"


# ── 6. Feature flag OFF — existing path unchanged ─────────────────────────────


class TestFeatureFlag:
    def test_feature_flag_off_does_not_import_fast_service(self) -> None:
        """When flag is OFF, fast_dynamic_place_search.search must NOT be called."""
        from unittest.mock import MagicMock, patch

        # Build minimal ConciergeService-like scenario
        with patch("app.services.fast_dynamic_place_search.get_fast_dynamic_search") as mock_fast, \
             patch("app.services.concierge.get_settings") as mock_settings:
            settings = MagicMock()
            settings.concierge_fast_dynamic_place_search_v1_enabled = False
            mock_settings.return_value = settings

            from app.services.concierge import ConciergeService
            db = MagicMock()
            svc = ConciergeService(db=db)
            svc._settings = settings

            # live research returns empty — we just want to ensure fast path not called
            mock_live = MagicMock()
            mock_live.is_live_capable = False
            svc._live_research = mock_live

            svc._fetch_live_research(
                intent="restaurants",
                destination="Chicago",
                user_query="tapas bar",
                trip={},
            )

        mock_fast.assert_not_called(), "get_fast_dynamic_search must not be called when flag OFF"

    def test_feature_flag_on_calls_fast_service(self) -> None:
        """When flag is ON, fast_dynamic_place_search.search must be called for place intents."""
        from unittest.mock import MagicMock, patch
        from app.services.live_research import LiveResearchResult
        from app.models.concierge import SOURCE_LIVE_SEARCH

        mock_fast_svc = MagicMock()
        mock_fast_svc.available = True
        mock_fast_svc.search.return_value = LiveResearchResult(
            source_status=SOURCE_LIVE_SEARCH
        )

        with patch(
            "app.services.fast_dynamic_place_search.get_fast_dynamic_search",
            return_value=mock_fast_svc,
        ), patch("app.services.concierge.get_settings") as mock_settings:
            settings = MagicMock()
            settings.concierge_fast_dynamic_place_search_v1_enabled = True
            mock_settings.return_value = settings

            from app.services.concierge import ConciergeService
            db = MagicMock()
            svc = ConciergeService(db=db)
            svc._settings = settings

            svc._fetch_live_research(
                intent="restaurants",
                destination="Chicago",
                user_query="tapas bar",
                trip={},
            )

        mock_fast_svc.search.assert_called_once()
        call_kwargs = mock_fast_svc.search.call_args.kwargs
        assert call_kwargs["user_query"] == "tapas bar"
        assert call_kwargs["destination"] == "Chicago"


# ── 7. Pool / cache key separation ────────────────────────────────────────────


class TestCacheKeySeparation:
    """Verify that different queries produce different ParsedPlaceQuery search_queries."""

    def test_tapas_bar_vs_cocktail_bars_different_keys(self) -> None:
        tapas = parse_place_query("tapas bar", "Chicago")
        cocktail = parse_place_query("cocktail bars", "Chicago")
        assert tapas.search_query != cocktail.search_query, (
            "tapas bar and cocktail bars must produce different search queries"
        )

    def test_seafood_vs_tapas_different_keys(self) -> None:
        seafood = parse_place_query("seafood restaurants", "Chicago")
        tapas = parse_place_query("tapas bar", "Chicago")
        assert seafood.search_query != tapas.search_query

    def test_sushi_waterfront_vs_plain_sushi_different_keys(self) -> None:
        sushi_view = parse_place_query("sushi restaurants with waterfront view", "Chicago")
        plain_sushi = parse_place_query("sushi restaurants", "Chicago")
        # Both contain sushi but are different queries
        assert sushi_view.search_query != plain_sushi.search_query

    def test_italian_vs_mexican_different_keys(self) -> None:
        italian = parse_place_query("Italian restaurants", "Chicago")
        mexican = parse_place_query("Mexican restaurants", "Chicago")
        assert italian.search_query != mexican.search_query


# ── 8. Bayesian scoring ───────────────────────────────────────────────────────


class TestBayesianScore:
    def test_high_rating_high_volume_scores_high(self) -> None:
        score = _bayesian_score(4.8, 2000)
        assert score > 4.5

    def test_none_rating_scores_zero(self) -> None:
        assert _bayesian_score(None, 500) == 0.0

    def test_low_volume_high_rating_is_shrunk(self) -> None:
        # With few reviews, Bayesian shrinks toward the mean (4.0)
        score_low_vol = _bayesian_score(5.0, 10)
        score_high_vol = _bayesian_score(5.0, 5000)
        assert score_low_vol < score_high_vol


# ── 9. Filter and rank ordering ───────────────────────────────────────────────


class TestFilterAndRank:
    def test_tapas_name_match_ranked_above_generic_restaurant(self) -> None:
        tapas_specific = _make_place(
            name="El Tapas", types=["spanish_restaurant"], place_id="t1"
        )
        generic = _make_place(
            name="Big American Grill", types=["restaurant"], place_id="t2"
        )
        svc = FastDynamicPlaceSearch(api_key="key")
        ranked = svc._filter_and_rank(
            [generic, tapas_specific],  # generic first in input
            parsed=_tapas_parsed(),
            prior_identity_keys=None,
        )
        assert ranked[0]["id"] == "t1", (
            "tapas-specific place should rank above generic restaurant"
        )

    def test_cocktail_bar_ranked_first_for_cocktail_query(self) -> None:
        cocktail = _make_place(
            name="The Violet Hour", types=["cocktail_bar", "bar"], place_id="c1"
        )
        restaurant = _make_place(
            name="Random Restaurant", types=["restaurant"], place_id="r1"
        )
        svc = FastDynamicPlaceSearch(api_key="key")
        ranked = svc._filter_and_rank(
            [restaurant, cocktail],
            parsed=_cocktail_parsed(),
            prior_identity_keys=None,
        )
        assert ranked[0]["id"] == "c1", (
            "cocktail bar must rank first for cocktail bars query"
        )
