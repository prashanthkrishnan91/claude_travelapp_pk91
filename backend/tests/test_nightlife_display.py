"""Tests for the nightlife/bar display normalization pipeline.

Acceptance criteria:
- Distinct, place-specific displayWhy for each card
- Category labels derived from Google types (not all forced to Cocktail Bar)
- No generic "A cocktail bar with X rating across Y reviews." template
- Rating/address stay in metaLine only
- Drink names from Tavily are rejected by the extractor guard
"""

from __future__ import annotations

import re
from typing import List, Optional

import pytest

from app.concierge.reasoning import (
    build_concierge_display_reason,
    build_why_pick,
    infer_nightlife_category_label,
    _build_nightlife_display_why,
)
from app.services.live_research import _category_label, _is_likely_drink_name


# ── Helper ────────────────────────────────────────────────────────────────────

_GENERIC_TEMPLATE_RE = re.compile(
    r"^A cocktail bar with \d+[\.,]\d+ rating across [\d,]+ reviews\.$",
    re.IGNORECASE,
)

def _assert_not_generic_template(text: str, label: str = "") -> None:
    prefix = f"[{label}] " if label else ""
    assert not _GENERIC_TEMPLATE_RE.match(text), (
        f"{prefix}Generic rating-only template detected: {text!r}"
    )
    assert len(text) >= 15, f"{prefix}display_why too short: {text!r}"
    assert len(text) <= 160, f"{prefix}display_why too long: {text!r}"


# ── A. infer_nightlife_category_label ─────────────────────────────────────────

class TestInferNightlifeCategoryLabel:
    def test_cocktail_bar_google_type(self):
        label, source = infer_nightlife_category_label(["cocktail_bar", "bar"], "Some Bar")
        assert label == "Cocktail Bar"
        assert source == "google_types"

    def test_wine_bar_google_type(self):
        label, source = infer_nightlife_category_label(["wine_bar", "bar"], "Pike Wine")
        assert label == "Wine Bar"
        assert source == "google_types"

    def test_lounge_bar_google_type(self):
        label, source = infer_nightlife_category_label(["lounge_bar"], "Upstairs Lounge")
        assert label == "Lounge"
        assert source == "google_types"

    def test_bar_plus_restaurant_is_not_cocktail_bar(self):
        """Von's: american_restaurant + bar + restaurant → 'Bar & Restaurant'."""
        label, source = infer_nightlife_category_label(
            ["american_restaurant", "bar", "restaurant"], "Von's 1000Spirits"
        )
        assert label == "Bar & Restaurant"
        assert source == "google_types"
        assert label != "Cocktail Bar"

    def test_bar_without_restaurant_gives_bar(self):
        label, source = infer_nightlife_category_label(["bar"], "Lonely Siren")
        assert label in ("Bar", "Cocktail Bar")  # pure bar without cocktail_bar type

    def test_smith_tower_name_signal_view_bar(self):
        """Smith Tower Observatory & Bar → view bar from name signal."""
        label, source = infer_nightlife_category_label(
            ["bar", "restaurant"], "Smith Tower Observatory & Bar"
        )
        assert label in ("View Bar", "Rooftop Bar")
        assert source == "name_signal"
        assert "cocktail" not in label.lower()

    def test_rooftop_name_signal(self):
        label, source = infer_nightlife_category_label(["bar"], "The Rooftop Bar")
        assert label == "Rooftop Bar"
        assert source == "name_signal"

    def test_speakeasy_name_signal(self):
        label, source = infer_nightlife_category_label(["bar"], "Underground Speakeasy")
        assert label == "Speakeasy"
        assert source == "name_signal"

    def test_no_google_types_fallback(self):
        """No types and generic name → intent fallback 'Cocktail Bar'."""
        label, source = infer_nightlife_category_label(None, "Test Bar")
        assert label == "Cocktail Bar"
        assert source == "intent_fallback"

    def test_brewery_google_type(self):
        label, source = infer_nightlife_category_label(["brewery", "bar"], "Fremont Brewing")
        assert label == "Brewery"
        assert source == "google_types"


# ── B. _category_label uses google_types ─────────────────────────────────────

class TestCategoryLabel:
    def test_bar_with_cocktail_bar_types_returns_cocktail_bar(self):
        label = _category_label("bar", None, google_types=["cocktail_bar", "bar"])
        assert label == "Cocktail Bar"

    def test_bar_with_mixed_types_returns_bar_and_restaurant(self):
        """Von's: bar + american_restaurant → 'Bar & Restaurant', not 'Cocktail Bar'."""
        label = _category_label("bar", None, google_types=["american_restaurant", "bar", "restaurant"])
        assert label == "Bar & Restaurant"
        assert label != "Cocktail Bar"

    def test_bar_with_tower_name_returns_view_bar(self):
        class FakeVenue:
            name = "Smith Tower Observatory & Bar"
        label = _category_label("bar", FakeVenue(), google_types=["bar", "restaurant"])
        assert label in ("View Bar", "Rooftop Bar")
        assert "cocktail" not in label.lower()

    def test_restaurant_with_cocktail_bar_cuisine_returns_restaurant(self):
        """Prevent legacy cuisine='Cocktail Bar' leaking as restaurant label."""
        class FakeVenue:
            cuisine = "Cocktail Bar"
        label = _category_label("restaurant", FakeVenue(), google_types=["restaurant"])
        assert label == "Restaurant"

    def test_restaurant_with_restaurant_cuisine_returns_restaurant(self):
        class FakeVenue:
            cuisine = "Restaurant"
        label = _category_label("restaurant", FakeVenue(), google_types=["restaurant"])
        assert label == "Restaurant"

    def test_bar_no_google_types_returns_cocktail_bar_fallback(self):
        label = _category_label("bar", None, google_types=None)
        assert label == "Cocktail Bar"  # intent_fallback for backward compat


# ── C. Premium deterministic display_why ─────────────────────────────────────

class TestPremiumNightlifeDisplayWhy:
    def test_view_venue_leads_with_setting(self):
        text = _build_nightlife_display_why(
            place_name="Smith Tower Observatory & Bar",
            google_types=["bar", "restaurant"],
            rating=4.6,
            review_count=800,
        )
        assert "setting" in text.lower() or "landmark" in text.lower()
        _assert_not_generic_template(text, "smith_tower")

    def test_high_volume_bar_uses_review_depth_signal(self):
        text = _build_nightlife_display_why(
            place_name="Von's 1000Spirits",
            google_types=["american_restaurant", "bar", "restaurant"],
            rating=4.6,
            review_count=7146,
        )
        assert "high-volume" in text.lower() or "standout" in text.lower()
        _assert_not_generic_template(text, "vons_high_volume")

    def test_smaller_high_rated_bar_uses_local_signal(self):
        text = _build_nightlife_display_why(
            place_name="Otter on the Rocks",
            google_types=["cocktail_bar"],
            rating=4.8,
            review_count=180,
        )
        assert "smaller" in text.lower() or "local" in text.lower()
        _assert_not_generic_template(text, "otter_small")

    def test_no_generic_rating_only_template(self):
        """The core bug: must not produce 'A cocktail bar with X rating across Y reviews.'"""
        text = build_concierge_display_reason(
            place_name="Von's 1000Spirits",
            query_context="cocktail bars in seattle",
            intent="nightlife",
            category="bar",
            neighborhood=None,  # no clean neighborhood
            rating=4.6,
            review_count=7146,
            evidence=["Rated 4.6 (7,146 reviews)"],
            google_types=["american_restaurant", "bar", "restaurant"],
        )
        _assert_not_generic_template(text, "vons_no_generic")
        assert "bar & restaurant" in text.lower() or "bar" in text.lower()

    def test_cocktail_bar_with_full_address_neighborhood_not_generic(self):
        """When neighborhood is a full address, must NOT produce rating-only template."""
        text = build_concierge_display_reason(
            place_name="Diller Room",
            query_context="cocktail bars in seattle",
            intent="nightlife",
            category="bar",
            neighborhood="1225 1st Ave, Seattle, WA 98101",  # full address
            rating=4.5,
            review_count=2268,
            evidence=["Rated 4.5 (2,268 reviews)"],
            google_types=["cocktail_bar", "bar"],
        )
        _assert_not_generic_template(text, "diller_full_address")

    def test_each_bar_produces_distinct_why(self):
        """Multiple bars with different profiles must get distinct display_why."""
        configs = [
            dict(name="Von's 1000Spirits", types=["american_restaurant", "bar"], rating=4.6, rc=7146),
            dict(name="Smith Tower Observatory & Bar", types=["bar", "restaurant"], rating=4.6, rc=800),
            dict(name="Otter on the Rocks", types=["cocktail_bar"], rating=4.8, rc=150),
            dict(name="Diller Room", types=["cocktail_bar", "bar"], rating=4.5, rc=2268),
            dict(name="Fremont Brewing", types=["brewery", "bar"], rating=4.7, rc=3000),
        ]
        texts = set()
        for c in configs:
            text = _build_nightlife_display_why(
                place_name=c["name"],
                google_types=c["types"],
                rating=c["rating"],
                review_count=c["rc"],
            )
            texts.add(text)
            _assert_not_generic_template(text, c["name"])
        # Must produce distinct text for at least 4 of the 5 configurations
        assert len(texts) >= 4, f"Too many duplicate display_why outputs: {texts}"

    def test_speakeasy_uses_atmosphere_framing(self):
        text = _build_nightlife_display_why(
            place_name="Underground Speakeasy",
            google_types=["bar"],
            rating=4.7,
            review_count=200,
        )
        assert "speakeasy" in text.lower() or "hidden" in text.lower()
        _assert_not_generic_template(text, "speakeasy")


# ── D. build_concierge_display_reason — nightlife path ───────────────────────

class TestNightlifeBuildDisplayReason:
    def test_with_clean_neighborhood_uses_correct_category_label(self):
        """When neighborhood is clean area, still includes it; category matches google_types."""
        text = build_concierge_display_reason(
            place_name="Test Bar",
            query_context="cocktail bars in Seattle",
            intent="nightlife",
            category="bar",
            neighborhood="Capitol Hill",
            rating=4.4,
            review_count=500,
            evidence=["Rated 4.4 (500 reviews)"],
            google_types=["cocktail_bar", "bar"],
        )
        assert "capitol hill" in text.lower()
        assert "cocktail bar" in text.lower()
        _assert_not_generic_template(text)

    def test_bar_and_restaurant_type_gives_correct_label_in_why(self):
        text = build_concierge_display_reason(
            place_name="Local Bar & Grill",
            query_context="bars in Seattle",
            intent="nightlife",
            category="bar",
            neighborhood=None,
            rating=4.3,
            review_count=1200,
            evidence=[],
            google_types=["american_restaurant", "bar", "restaurant"],
        )
        assert "bar" in text.lower()
        _assert_not_generic_template(text)

    def test_without_google_types_backward_compat(self):
        """Old callers without google_types still produce acceptable output."""
        text = build_concierge_display_reason(
            place_name="Old Bar",
            query_context="cocktail bars",
            intent="nightlife",
            category="bar",
            neighborhood="Wicker Park",
            rating=4.5,
            review_count=900,
            evidence=["Rated 4.5 (900 reviews)"],
        )
        assert "cocktail bar" in text.lower()
        assert "wicker park" in text.lower()
        _assert_not_generic_template(text)

    def test_editorial_evidence_still_leads(self):
        """When editorial evidence mentions bar terms, it should still lead."""
        text = build_concierge_display_reason(
            place_name="The Drifter",
            query_context="cocktail bars",
            intent="nightlife",
            category="bar",
            neighborhood="River North",
            rating=4.4,
            review_count=826,
            evidence=["Mentioned in Eater Chicago cocktail lists"],
            google_types=["cocktail_bar"],
        )
        assert "eater" in text.lower()
        _assert_not_generic_template(text)


# ── E. Drink name extractor guard ────────────────────────────────────────────

class TestDrinkNameGuard:
    @pytest.mark.parametrize("name", [
        "Cucumber Collins",
        "Spiced Mule",
        "Pineapple Express",
        "Ginger Sour",
        "Mango Fizz",
        "Lemon Spritz",
    ])
    def test_rejects_obvious_cocktail_names(self, name: str):
        assert _is_likely_drink_name(name), f"Should be flagged as drink name: {name!r}"

    @pytest.mark.parametrize("name", [
        "Von's 1000Spirits",
        "Diller Room",
        "Smith Tower Observatory & Bar",
        "Otter on the Rocks",
        "The Lonely Siren",
        "Capitol Cider",
        "The Stoup Brewing",
    ])
    def test_does_not_reject_venue_names(self, name: str):
        assert not _is_likely_drink_name(name), f"Venue name incorrectly flagged: {name!r}"

    def test_single_word_not_flagged(self):
        assert not _is_likely_drink_name("Negroni")  # 1 word, not flagged

    def test_long_names_not_flagged(self):
        assert not _is_likely_drink_name("The Lemon Gin Tonic Bar Seattle")


# ── F. Category label not polluted by legacy cuisine field ───────────────────

class TestLegacyCuisineNotDisplayed:
    def test_cuisine_cocktail_bar_on_restaurant_category_returns_restaurant(self):
        """Legacy cuisine='Cocktail Bar' from Tavily extraction must not become display label."""
        class FakeVenue:
            name = "Test Bar"
            cuisine = "Cocktail Bar"
        label = _category_label("restaurant", FakeVenue(), google_types=["restaurant", "food"])
        assert label == "Restaurant"
        assert "cocktail" not in label.lower()

    def test_bar_category_ignores_cuisine_field_uses_types(self):
        """For bar category, cuisine is irrelevant; google_types determine label."""
        class FakeVenue:
            name = "Wine & Spirits"
            cuisine = "Restaurant"  # wrong/noisy legacy field
        label = _category_label("bar", FakeVenue(), google_types=["wine_bar", "bar"])
        assert label == "Wine Bar"
        assert label != "Restaurant"


# ── G. build_why_pick passes google_types through ────────────────────────────

class TestBuildWhyPickWithGoogleTypes:
    def test_bar_with_view_name_gets_view_framing(self):
        result = build_why_pick(
            place_name="Sky Bar & Observatory",
            evidence=["Rated 4.6 (900 reviews)"],
            rating=4.6,
            review_count=900,
            category="bar",
            neighborhood=None,
            user_query="cocktail bars in Seattle",
            intent="nightlife",
            google_types=["bar", "restaurant"],
        )
        text = result["why_pick"]["text"]
        assert "setting" in text.lower() or "landmark" in text.lower() or "view" in text.lower()

    def test_high_volume_bar_gets_volume_signal(self):
        result = build_why_pick(
            place_name="Popular Bar",
            evidence=["Rated 4.5 (5000 reviews)"],
            rating=4.5,
            review_count=5000,
            category="bar",
            neighborhood=None,
            user_query="bars in Seattle",
            intent="nightlife",
            google_types=["bar"],
        )
        text = result["why_pick"]["text"]
        _assert_not_generic_template(text, "high_volume_build_why_pick")
