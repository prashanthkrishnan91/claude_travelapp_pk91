"""Integration tests for the canonical AI Concierge display contract.

Verifies that build_concierge_display_reason and build_why_pick produce
display_why text that:
  - exists and is non-empty
  - is NOT rating-only ("X is a restaurant with rating", "With 4.x rating…")
  - contains NO banned generic/template phrases
  - is ≤ 140 chars (soft target verified as < 160 to allow minor overflow)
  - uses venue-specific anchors (neighborhood, cuisine, intent, editorial)

These tests simulate the canonical query intents listed in the task spec.
"""

from __future__ import annotations

import re
from typing import Any, Dict

import pytest

from app.concierge.reasoning import (
    BANNED_STRINGS_RE,
    GENERIC_PHRASES_RE,
    build_concierge_display_reason,
    build_why_pick,
)
from app.models.concierge import ConciergeDisplayFields

# ── Acceptance guards ──────────────────────────────────────────────────────────

_RATING_ONLY_SENTENCE_RE = re.compile(
    # "With 4.6 rating across…, X is a restaurant."
    r"^[Ww]ith\s+\d+[\.,]\d+\s+rating"
    # "Pizzeria Portofino is a restaurant, with 4.8 rating…"
    r"|[A-Za-z][^.!?]+\s+is\s+a\s+(?:restaurant|bar|hotel|attraction|place)\b[^.!?]*with\s+\d+[\.,]\d+\s+rating",
    re.IGNORECASE,
)

_BANNED_PHRASES = [
    "backed by",
    "selected for this",
    "available evidence",
    "consistent guest ratings",
    "verified restaurant details",
    "verified drinks-focused",
    "verified place details",
    "with rated",
]


def _assert_display_why_quality(text: str, *, label: str = "") -> None:
    prefix = f"[{label}] " if label else ""
    assert text, f"{prefix}display_why is empty"
    assert len(text) >= 12, f"{prefix}display_why too short: {text!r}"
    assert len(text) < 160, f"{prefix}display_why exceeds soft limit: {text!r}"
    assert not BANNED_STRINGS_RE.search(text), f"{prefix}BANNED_STRINGS in: {text!r}"
    assert not GENERIC_PHRASES_RE.search(text), f"{prefix}GENERIC_PHRASES in: {text!r}"
    assert not _RATING_ONLY_SENTENCE_RE.search(text), (
        f"{prefix}Rating-only template sentence detected: {text!r}"
    )
    for phrase in _BANNED_PHRASES:
        assert phrase.lower() not in text.lower(), (
            f"{prefix}Banned phrase {phrase!r} found in: {text!r}"
        )


# ── ConciergeDisplayFields model ──────────────────────────────────────────────

def test_concierge_display_fields_model():
    obj = ConciergeDisplayFields(
        display_name="Alinea",
        display_category="Restaurant",
        display_meta_line="★ 4.6 (1,900 reviews) · Lincoln Park",
        display_why="Michelin 3-star tasting menu in Lincoln Park with 4.6 rating across 1,900 reviews.",
        display_badges=["Google Verified", "Editorial"],
        addability="addable",
    )
    assert obj.display_why
    assert obj.addability == "addable"
    assert obj.display_name == "Alinea"


def test_concierge_display_fields_addability_values():
    for value in ("addable", "research_only", "closed"):
        f = ConciergeDisplayFields(
            display_name="Test", display_category="Place", display_why="ok", addability=value
        )
        assert f.addability == value


# ── Scenario: best restaurants near hotel in Chicago ─────────────────────────

def test_near_hotel_restaurants_display_why():
    text = build_concierge_display_reason(
        place_name="Monteverde",
        query_context="best restaurants near my hotel in Chicago",
        intent="restaurants",
        category="restaurant",
        cuisine="Italian",
        neighborhood="West Loop",
        rating=4.7,
        review_count=3200,
        evidence=["Rated 4.7 (3,200 reviews)"],
    )
    _assert_display_why_quality(text, label="near_hotel_restaurant")
    # Should anchor on cuisine/neighborhood, not lead with rating sentence
    assert "italian" in text.lower() or "west loop" in text.lower(), (
        f"Expected cuisine or neighborhood anchor: {text!r}"
    )


def test_near_hotel_restaurant_no_rating_only_sentence():
    for cuisine, neighborhood in [
        ("American", "River North"),
        ("Japanese", "Wicker Park"),
        (None, "Lincoln Park"),
    ]:
        text = build_concierge_display_reason(
            place_name="Test Restaurant",
            query_context="restaurants near my hotel",
            intent="restaurants",
            category="restaurant",
            cuisine=cuisine,
            neighborhood=neighborhood,
            rating=4.5,
            review_count=800,
            evidence=["Rated 4.5 (800 reviews)"],
        )
        _assert_display_why_quality(text, label=f"near_hotel_{cuisine or 'no_cuisine'}")


# ── Scenario: nearby cocktail bars ────────────────────────────────────────────

def test_cocktail_bars_display_why_contains_category():
    for neighborhood, rating, reviews in [
        ("Fulton Market", 4.3, 970),
        ("Wicker Park", 4.6, 1500),
        ("River North", 4.5, 2200),
    ]:
        text = build_concierge_display_reason(
            place_name="Test Bar",
            query_context="nearby cocktail bars",
            intent="nightlife",
            category="bar",
            neighborhood=neighborhood,
            rating=rating,
            review_count=reviews,
            evidence=[f"Rated {rating} ({reviews} reviews)"],
        )
        _assert_display_why_quality(text, label=f"cocktail_{neighborhood}")
        assert "cocktail bar" in text.lower(), (
            f"Expected 'cocktail bar' category anchor in: {text!r}"
        )
        assert neighborhood.lower() in text.lower(), (
            f"Expected neighborhood '{neighborhood}' in: {text!r}"
        )


def test_cocktail_bar_with_editorial_evidence_leads_with_editorial():
    text = build_concierge_display_reason(
        place_name="The Drifter",
        query_context="cocktail bars in chicago",
        intent="nightlife",
        category="bar",
        neighborhood="River North",
        rating=4.4,
        review_count=826,
        evidence=["Mentioned in Eater Chicago cocktail lists"],
    )
    _assert_display_why_quality(text, label="cocktail_editorial")
    assert "eater chicago" in text.lower(), (
        f"Editorial evidence should lead: {text!r}"
    )


# ── Scenario: Michelin restaurants ───────────────────────────────────────────

def test_michelin_restaurants_leads_with_star_status():
    text = build_concierge_display_reason(
        place_name="Alinea",
        query_context="Michelin restaurants in Chicago",
        intent="michelin_restaurants",
        category="restaurant",
        cuisine="Tasting menu",
        neighborhood="Lincoln Park",
        michelin_status="Michelin 3-star",
        rating=4.6,
        review_count=1900,
        evidence=["Rated 4.6 (1,900 reviews)"],
    )
    _assert_display_why_quality(text, label="michelin_starred")
    assert "michelin 3-star" in text.lower(), f"Expected Michelin status lead: {text!r}"
    assert "lincoln park" in text.lower(), f"Expected neighborhood: {text!r}"
    assert "4.6 rating across 1,900 reviews" in text, f"Expected rating detail: {text!r}"


def test_michelin_via_evidence_chip_no_explicit_status():
    text = build_why_pick(
        place_name="Smyth",
        evidence=["Rated 4.7 (1,400 reviews)", "Listed in Michelin Guide Chicago"],
        rating=4.7,
        review_count=1400,
        category="restaurant",
        cuisine="Tasting menu",
        neighborhood="West Loop",
        user_query="Michelin restaurants",
        intent="michelin_restaurants",
    )["why_pick"]["text"]
    _assert_display_why_quality(text, label="michelin_via_evidence")
    assert "michelin" in text.lower(), f"Michelin evidence should appear: {text!r}"


def test_michelin_intent_without_michelin_evidence_no_michelin_word():
    text = build_concierge_display_reason(
        place_name="Boka",
        query_context="Michelin restaurants in chicago",
        intent="michelin_restaurants",
        category="restaurant",
        cuisine="American",
        neighborhood="Lincoln Park",
        rating=4.7,
        review_count=3100,
        evidence=["Rated 4.7 (3,100 reviews)"],
    )
    _assert_display_why_quality(text, label="michelin_no_evidence")
    assert "michelin" not in text.lower(), (
        f"'michelin' must not appear without michelin_status or michelin evidence: {text!r}"
    )


# ── Scenario: hidden gems ─────────────────────────────────────────────────────

def test_hidden_gems_leads_with_local_anchor():
    text = build_concierge_display_reason(
        place_name="Daisies",
        query_context="hidden gems in Chicago",
        intent="hidden_gems",
        category="restaurant",
        cuisine="Midwestern",
        neighborhood="Logan Square",
        rating=4.7,
        review_count=612,
        evidence=["Rated 4.7 (612 reviews)", "Near Logan Square"],
    )
    _assert_display_why_quality(text, label="hidden_gems")
    assert "local" in text.lower(), f"Expected 'local' anchor for hidden gem: {text!r}"
    assert "logan square" in text.lower(), f"Expected neighborhood: {text!r}"


def test_hidden_gems_various_categories():
    for category, cuisine in [
        ("restaurant", "Italian"),
        ("bar", None),
        ("attraction", None),
    ]:
        text = build_concierge_display_reason(
            place_name="Secret Spot",
            query_context="hidden gems off the beaten path",
            intent="hidden_gems",
            category=category,
            cuisine=cuisine,
            neighborhood="Pilsen",
            rating=4.5,
            review_count=300,
            evidence=["Rated 4.5 (300 reviews)"],
        )
        _assert_display_why_quality(text, label=f"hidden_gems_{category}")


# ── Scenario: hotels ──────────────────────────────────────────────────────────

def test_hotels_display_why_quality():
    for neighborhood, rating in [
        ("River North", 4.5),
        ("Magnificent Mile", 4.7),
        ("West Loop", 4.2),
    ]:
        text = build_concierge_display_reason(
            place_name="Test Hotel",
            query_context="hotels in Chicago",
            intent="hotels",
            category="hotel",
            neighborhood=neighborhood,
            rating=rating,
            review_count=2000,
            evidence=[f"Rated {rating} (2,000 reviews)"],
        )
        _assert_display_why_quality(text, label=f"hotel_{neighborhood}")
        # Should NOT produce "Test Hotel is a hotel with X rating"
        assert not _RATING_ONLY_SENTENCE_RE.search(text), (
            f"Rating-only template in hotel card: {text!r}"
        )


# ── Acceptance: no banned output patterns ─────────────────────────────────────

ACCEPTANCE_BANNED_OUTPUTS = [
    "With 4.6 rating across 5,185 reviews, Ema is a restaurant.",
    "Pizzeria Portofino is a restaurant, with 4.8 rating across 15,738 reviews.",
    "A verified cocktail bar with consistent guest ratings.",
    "backed by strong Google signals",
    "selected for this request",
    "available evidence",
]


@pytest.mark.parametrize("bad_text", ACCEPTANCE_BANNED_OUTPUTS)
def test_acceptance_banned_outputs_are_caught(bad_text: str):
    """Verify each bad output from the acceptance criteria is blocked by our guards."""
    caught = (
        BANNED_STRINGS_RE.search(bad_text)
        or GENERIC_PHRASES_RE.search(bad_text)
        or _RATING_ONLY_SENTENCE_RE.search(bad_text)
        or any(p in bad_text.lower() for p in _BANNED_PHRASES)
    )
    assert caught, f"Bad output not caught by any guard: {bad_text!r}"


# ── Corpus sweep: 50 synthetic cards across all intents ──────────────────────

_INTENT_CONFIGS = [
    dict(intent="restaurants", category="restaurant", cuisine="Italian", query="best restaurants near my hotel in Chicago"),
    dict(intent="nightlife", category="bar", cuisine=None, query="nearby cocktail bars"),
    dict(intent="michelin_restaurants", category="restaurant", cuisine="French", michelin_status="Michelin 1-star", query="Michelin restaurants"),
    dict(intent="hidden_gems", category="restaurant", cuisine="Mexican", query="hidden gems in Chicago"),
    dict(intent="hotels", category="hotel", cuisine=None, query="hotels in Chicago"),
    dict(intent="attractions", category="attraction", cuisine="Museum", query="must-see attractions"),
    dict(intent="romantic", category="restaurant", cuisine="Italian", query="romantic dinner"),
    dict(intent="family_friendly", category="restaurant", cuisine="American", query="family friendly places"),
]

_NEIGHBORHOODS = ["River North", "West Loop", "Lincoln Park", "Wicker Park", "Logan Square", "Pilsen"]


def test_corpus_sweep_no_banned_output():
    import itertools
    count = 0
    for i, (cfg, nbhd) in enumerate(itertools.product(_INTENT_CONFIGS, _NEIGHBORHOODS)):
        rating = 4.0 + (i % 10) * 0.09
        review_count = 100 + i * 47
        evidence = [f"Rated {rating:.1f} ({review_count} reviews)"]
        text = build_concierge_display_reason(
            place_name=f"Venue {i}",
            query_context=cfg["query"],
            intent=cfg.get("intent"),
            category=cfg.get("category"),
            cuisine=cfg.get("cuisine"),
            neighborhood=nbhd,
            michelin_status=cfg.get("michelin_status"),
            rating=rating,
            review_count=review_count,
            evidence=evidence,
        )
        _assert_display_why_quality(text, label=f"corpus_{i}")
        count += 1
    assert count >= 48, "Corpus sweep ran fewer cases than expected"


# ── display field vs legacy field consistency ─────────────────────────────────

def test_build_why_pick_and_build_concierge_display_reason_agree():
    """Both entry points must produce non-banned text for the same inputs."""
    kwargs = dict(
        place_name="Green Street Smoked Meats",
        evidence=["Rated 4.5 (1,400 reviews)"],
        rating=4.5,
        review_count=1400,
        category="restaurant",
        cuisine="BBQ",
        neighborhood="Fulton Market",
        user_query="best BBQ in Chicago",
        intent="restaurants",
    )
    wp = build_why_pick(**kwargs)["why_pick"]["text"]
    dr = build_concierge_display_reason(
        place_name=kwargs["place_name"],
        query_context=kwargs["user_query"],
        intent=kwargs["intent"],
        category=kwargs["category"],
        cuisine=kwargs["cuisine"],
        neighborhood=kwargs["neighborhood"],
        rating=kwargs["rating"],
        review_count=kwargs["review_count"],
        evidence=kwargs["evidence"],
    )
    _assert_display_why_quality(wp, label="build_why_pick")
    _assert_display_why_quality(dr, label="build_concierge_display_reason")


# ── Editorial evidence takes priority over generic rating ─────────────────────

def test_editorial_evidence_beats_rating_only():
    text = build_concierge_display_reason(
        place_name="Avec",
        query_context="best restaurants Chicago",
        intent="restaurants",
        category="restaurant",
        cuisine="Mediterranean",
        neighborhood="West Loop",
        rating=4.8,
        review_count=9400,
        evidence=["Featured in Bon Appétit's best new restaurants"],
    )
    _assert_display_why_quality(text, label="editorial_beats_rating")
    assert "bon" in text.lower() or "appétit" in text.lower() or "featured" in text.lower(), (
        f"Editorial lead expected: {text!r}"
    )
    # Must not lead with the place name + "is a restaurant"
    assert not text.startswith("Avec is a"), f"Must not start with 'Avec is a': {text!r}"


# ── Google-only (no editorial) stays clean ────────────────────────────────────

def test_google_only_no_editorial_still_clean():
    text = build_concierge_display_reason(
        place_name="Portofino",
        query_context="best italian in Chicago",
        intent="restaurants",
        category="restaurant",
        cuisine="Italian",
        neighborhood="Riverwalk",
        rating=4.8,
        review_count=15738,
        evidence=["Rated 4.8 (15,738 reviews)"],
    )
    _assert_display_why_quality(text, label="google_only")
    # Must not produce "Portofino is a restaurant with 4.8 rating…"
    assert "portofino is a restaurant" not in text.lower(), (
        f"Old bad template detected: {text!r}"
    )
    assert "italian" in text.lower() or "riverwalk" in text.lower(), (
        f"Expected cuisine/neighborhood anchor: {text!r}"
    )


# ── Absolute fallback (no rating, no location, no evidence) ──────────────────

def test_absolute_fallback_is_clean():
    text = build_concierge_display_reason(
        place_name="Mystery Spot",
        query_context="best places",
        intent=None,
        category="restaurant",
        rating=None,
        review_count=None,
        evidence=[],
    )
    _assert_display_why_quality(text, label="absolute_fallback")
    assert "mystery spot is a" not in text.lower(), (
        f"Must not use old template in fallback: {text!r}"
    )
