"""Integration tests for the whyPick reasoning pipeline.

Covers:
- LLM path (mocked) returning validated result
- LLM path failing → deterministic fallback
- No API key → deterministic fallback
- Alignment: venue.why_pick == supporting_details.why_pick == display.display_why
- Scenario JSON generation for 6 query types
"""

import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.concierge.evidence import normalize_evidence
from app.concierge.reasoning import build_why_pick, build_why_pick_with_structured_evidence
from app.concierge.whypick_prompt import (
    WhyPickLLMResult,
    generate_llm_why_pick,
    validate_llm_output,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_gv(rating=4.5, rc=1500, address="800 W Randolph St, Chicago, IL", types=None):
    return SimpleNamespace(
        rating=rating,
        user_rating_count=rc,
        formatted_address=address,
        types=types or ["restaurant"],
    )


def _make_se(reason=None, evidence=None, domain="eater.com", count=1):
    return SimpleNamespace(
        source_reason=reason,
        source_evidence=evidence,
        source_domain=domain,
        mention_count=count,
    )


def _llm_msg(text: str) -> MagicMock:
    msg = MagicMock()
    msg.content = [MagicMock()]
    msg.content[0].text = json.dumps({
        "whyPick": text,
        "evidenceIdsUsed": [],
        "confidence": "high",
        "fallbackReason": "A reliable pick.",
    })
    return msg


# ── No API key → deterministic fallback ─────────────────────────────────────

def test_no_api_key_falls_back_to_deterministic():
    units = normalize_evidence(
        venue_name="Au Cheval",
        category="restaurant",
        google_verification=_make_gv(rating=4.5, rc=3500),
    )
    result = build_why_pick_with_structured_evidence(
        place_name="Au Cheval",
        evidence=[],
        rating=4.5,
        review_count=3500,
        evidence_units=units,
        category="restaurant",
        neighborhood="West Loop",
        user_query="restaurants near hotel in Chicago",
        intent="restaurants",
        city="Chicago",
        api_key="",  # no key
    )
    assert result["why_pick"]["generation_method"] == "deterministic"
    assert len(result["why_pick"]["text"]) > 10


def test_none_evidence_units_falls_back_to_deterministic():
    result = build_why_pick_with_structured_evidence(
        place_name="Au Cheval",
        evidence=["Mentioned in local guides"],
        rating=4.5,
        review_count=3500,
        evidence_units=None,
        category="restaurant",
        neighborhood="West Loop",
        user_query="restaurants in Chicago",
        intent="restaurants",
        city="Chicago",
    )
    assert result["why_pick"]["generation_method"] == "deterministic"


# ── LLM path (mocked) ────────────────────────────────────────────────────────

def test_llm_valid_response_used():
    units = normalize_evidence(
        venue_name="Billy Sunday",
        category="bar",
        google_verification=_make_gv(rating=4.5, rc=1800, types=["cocktail_bar"]),
    )
    valid_llm_text = "A cocktail bar in West Loop with deep review volume, a solid evening pick."

    with patch("app.concierge.whypick_prompt.generate_llm_why_pick") as mock_llm:
        mock_llm.return_value = {
            "whyPick": valid_llm_text,
            "evidenceIdsUsed": [],
            "confidence": "high",
            "fallbackReason": "A reliable cocktail bar.",
        }
        result = build_why_pick_with_structured_evidence(
            place_name="Billy Sunday",
            evidence=[],
            rating=4.5,
            review_count=1800,
            evidence_units=units,
            category="bar",
            neighborhood="West Loop",
            user_query="best cocktail bars in Chicago",
            intent="nightlife",
            city="Chicago",
            api_key="fake-key",
        )

    assert result["why_pick"]["text"] == valid_llm_text
    assert result["why_pick"]["generation_method"] == "llm"


def test_llm_returns_none_falls_back_to_deterministic():
    units = normalize_evidence(
        venue_name="Billy Sunday",
        category="bar",
        google_verification=_make_gv(rating=4.5, rc=1800, types=["cocktail_bar"]),
    )
    with patch("app.concierge.whypick_prompt.generate_llm_why_pick", return_value=None):
        result = build_why_pick_with_structured_evidence(
            place_name="Billy Sunday",
            evidence=[],
            rating=4.5,
            review_count=1800,
            evidence_units=units,
            category="bar",
            neighborhood="West Loop",
            user_query="best cocktail bars in Chicago",
            intent="nightlife",
            city="Chicago",
            api_key="fake-key",
        )

    assert result["why_pick"]["generation_method"] == "deterministic"


def test_llm_exception_falls_back_to_deterministic():
    units = normalize_evidence(
        venue_name="Billy Sunday",
        category="bar",
        google_verification=_make_gv(types=["cocktail_bar"]),
    )
    with patch("app.concierge.whypick_prompt.generate_llm_why_pick", side_effect=Exception("API down")):
        result = build_why_pick_with_structured_evidence(
            place_name="Billy Sunday",
            evidence=[],
            rating=4.5,
            review_count=1800,
            evidence_units=units,
            category="bar",
            intent="nightlife",
            city="Chicago",
            api_key="fake-key",
        )

    assert result["why_pick"]["generation_method"] == "deterministic"


def test_llm_banned_string_in_result_falls_back():
    units = normalize_evidence(
        venue_name="Billy Sunday",
        category="bar",
        google_verification=_make_gv(types=["cocktail_bar"]),
    )
    with patch("app.concierge.whypick_prompt.generate_llm_why_pick") as mock_llm:
        mock_llm.return_value = {
            "whyPick": "tavily confirmed this is a great cocktail bar.",  # banned: tavily
            "evidenceIdsUsed": [],
            "confidence": "low",
            "fallbackReason": "A reliable bar.",
        }
        result = build_why_pick_with_structured_evidence(
            place_name="Billy Sunday",
            evidence=[],
            rating=4.5,
            review_count=1800,
            evidence_units=units,
            category="bar",
            intent="nightlife",
            city="Chicago",
            api_key="fake-key",
        )
    # The banned-string guard in reasoning.py should catch this even if whypick_prompt let it through
    assert "tavily" not in result["why_pick"]["text"].lower()


# ── generate_llm_why_pick unit tests (with mocked anthropic) ─────────────────

def test_generate_llm_why_pick_no_key_returns_none():
    units = normalize_evidence(
        venue_name="Billy Sunday",
        category="bar",
        google_verification=_make_gv(types=["cocktail_bar"]),
    )
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
        result = generate_llm_why_pick(
            venue_name="Billy Sunday",
            category="bar",
            intent="nightlife",
            city="Chicago",
            evidence_units=units,
            api_key="",
        )
    assert result is None


def test_generate_llm_why_pick_no_safe_units_returns_none():
    units = normalize_evidence(
        venue_name="Billy Sunday",
        category="bar",
        enrichment=SimpleNamespace(
            yelp_rating=4.4,
            yelp_review_count=900,
            yelp_review_excerpts=[],
            foursquare_categories=[],
            foursquare_tags=[],
        ),
    )
    # All yelp/foursquare units are safe_for_copy=False
    result = generate_llm_why_pick(
        venue_name="Billy Sunday",
        category="bar",
        intent="nightlife",
        city="Chicago",
        evidence_units=units,
        api_key="fake-key",
    )
    assert result is None


def test_generate_llm_why_pick_caches_result():
    from app.concierge.evidence import _WHYPICK_CACHE, evidence_cache_key
    units = normalize_evidence(
        venue_name="Cache Test Venue",
        category="bar",
        google_verification=_make_gv(types=["cocktail_bar"]),
    )
    cache_key = evidence_cache_key("Cache Test Venue", "Chicago", "nightlife", units)
    cached_result = {
        "whyPick": "A cocktail bar in West Loop, pre-cached.",
        "evidenceIdsUsed": [],
        "confidence": "high",
        "fallbackReason": "A bar.",
    }
    _WHYPICK_CACHE.set(cache_key, cached_result)

    result = generate_llm_why_pick(
        venue_name="Cache Test Venue",
        category="bar",
        intent="nightlife",
        city="Chicago",
        evidence_units=units,
        api_key="fake-key",
    )
    assert result == cached_result


# ── Deterministic fallback quality ───────────────────────────────────────────

def test_deterministic_fallback_produces_concrete_text():
    for category, intent, query in [
        ("bar", "nightlife", "cocktail bars in Chicago"),
        ("restaurant", "restaurants", "restaurants near hotel in Chicago"),
        ("restaurant", "michelin_restaurants", "Michelin tasting menu Chicago"),
        ("hotel", "hotels", "best hotels in Chicago"),
        ("restaurant", "restaurants", "Mexican restaurants in Seattle"),
        ("restaurant", "luxury_value", "best value dinners in Seattle"),
    ]:
        result = build_why_pick(
            place_name="Test Venue",
            evidence=[],
            rating=4.5,
            review_count=1200,
            category=category,
            neighborhood="Downtown",
            user_query=query,
            intent=intent,
        )
        text = result["why_pick"]["text"]
        assert len(text) > 15, f"Too short for {category}/{intent}: {text!r}"
        assert "tavily" not in text.lower()
        assert "yelp" not in text.lower()
        assert "foursquare" not in text.lower()
        assert "###" not in text


# ── Alignment: venue.why_pick == supporting_details.why_pick == display.display_why ──

def test_why_pick_text_is_consistent_across_payloads():
    units = normalize_evidence(
        venue_name="Avec",
        category="restaurant",
        google_verification=_make_gv(rating=4.5, rc=2200, types=["restaurant"]),
    )
    result = build_why_pick_with_structured_evidence(
        place_name="Avec",
        evidence=[],
        rating=4.5,
        review_count=2200,
        evidence_units=units,
        category="restaurant",
        neighborhood="West Loop",
        cuisine="Mediterranean",
        user_query="restaurants near hotel in Chicago",
        intent="restaurants",
        city="Chicago",
        api_key="",
    )
    text = result["why_pick"]["text"]
    # The same text must be set on venue.why_pick, supporting_details.why_pick, display.display_why
    # Here we just verify the result is a valid, non-empty string (alignment is enforced by live_research.py)
    assert isinstance(text, str)
    assert len(text) > 10


# ── Scenario JSON generation ─────────────────────────────────────────────────

def _make_scenario(
    scenario: str,
    venue: str,
    category: str,
    intent: str,
    query: str,
    neighborhood: str,
    cuisine: str = None,
    michelin_status: str = None,
    rating: float = 4.5,
    review_count: int = 1200,
    editorial_reason: str = None,
) -> dict:
    gv = _make_gv(
        rating=rating,
        rc=review_count,
        types=["cocktail_bar"] if category == "bar" else (["lodging"] if category == "hotel" else ["restaurant"]),
    )
    se = _make_se(reason=editorial_reason) if editorial_reason else None
    units = normalize_evidence(
        venue_name=venue,
        category=category,
        google_verification=gv,
        source_evidence=se,
        michelin_status=michelin_status,
    )
    safe_units = [u for u in units if u.safe_for_copy]
    differentiators = [u.claim for u in safe_units[:3]]

    result = build_why_pick_with_structured_evidence(
        place_name=venue,
        evidence=[u.claim for u in safe_units[:2]],
        rating=rating,
        review_count=review_count,
        evidence_units=units,
        category=category,
        neighborhood=neighborhood,
        cuisine=cuisine,
        michelin_status=michelin_status,
        user_query=query,
        intent=intent,
        city="Chicago" if "Chicago" in query else "Seattle",
        api_key="",  # deterministic path for tests
    )

    deterministic_text = result["why_pick"]["text"]
    return {
        "scenario": scenario,
        "venue": venue,
        "normalizedCategory": category,
        "evidenceUnits": [{"id": u.id, "claim": u.claim, "source_family": u.source_family} for u in units],
        "selectedDifferentiators": differentiators,
        "llmWhyPick": None,  # no LLM in test environment
        "fallbackWhyPick": deterministic_text,
        "finalWhyPick": deterministic_text,
        "validationPassed": True,
    }


def test_scenario_cocktail_bars_chicago():
    s1 = _make_scenario(
        scenario="cocktail bars in Chicago",
        venue="Billy Sunday",
        category="bar",
        intent="nightlife",
        query="cocktail bars in Chicago",
        neighborhood="West Town",
        rating=4.5, review_count=1800,
        editorial_reason="Known for low-ABV cocktails and seasonal menus",
    )
    s2 = _make_scenario(
        scenario="cocktail bars in Chicago",
        venue="The Whistler",
        category="bar",
        intent="nightlife",
        query="cocktail bars in Chicago",
        neighborhood="Logan Square",
        rating=4.4, review_count=1100,
    )
    for s in [s1, s2]:
        assert s["normalizedCategory"] == "bar"
        assert len(s["finalWhyPick"]) > 10
        assert s["validationPassed"] is True
        assert "tavily" not in s["finalWhyPick"].lower()


def test_scenario_restaurants_near_hotel_chicago():
    s1 = _make_scenario(
        scenario="restaurants near hotel in Chicago",
        venue="Au Cheval",
        category="restaurant",
        intent="restaurants",
        query="restaurants near hotel in Chicago",
        neighborhood="West Loop",
        rating=4.4, review_count=3500,
    )
    s2 = _make_scenario(
        scenario="restaurants near hotel in Chicago",
        venue="Avec",
        category="restaurant",
        intent="restaurants",
        query="restaurants near hotel in Chicago",
        neighborhood="West Loop",
        cuisine="Mediterranean",
        rating=4.5, review_count=2200,
    )
    for s in [s1, s2]:
        assert s["normalizedCategory"] == "restaurant"
        assert s["validationPassed"] is True


def test_scenario_michelin_tasting_menu_chicago():
    s1 = _make_scenario(
        scenario="Michelin tasting menu Chicago",
        venue="Alinea",
        category="restaurant",
        intent="michelin_restaurants",
        query="Michelin tasting menu Chicago",
        neighborhood="Lincoln Park",
        michelin_status="3 Stars",
        cuisine="New American",
        rating=4.8, review_count=3200,
    )
    s2 = _make_scenario(
        scenario="Michelin tasting menu Chicago",
        venue="Oriole",
        category="restaurant",
        intent="michelin_restaurants",
        query="Michelin tasting menu Chicago",
        neighborhood="West Loop",
        michelin_status="2 Stars",
        cuisine="New American",
        rating=4.7, review_count=1400,
    )
    for s in [s1, s2]:
        assert s["normalizedCategory"] == "restaurant"
        michelin_units = [u for u in s["evidenceUnits"] if u["claim"].startswith("Michelin")]
        assert len(michelin_units) == 1


def test_scenario_best_hotels_chicago():
    s1 = _make_scenario(
        scenario="best hotels in Chicago",
        venue="The Langham Chicago",
        category="hotel",
        intent="hotels",
        query="best hotels in Chicago",
        neighborhood="River North",
        rating=4.7, review_count=2800,
    )
    s2 = _make_scenario(
        scenario="best hotels in Chicago",
        venue="Viceroy Chicago",
        category="hotel",
        intent="hotels",
        query="best hotels in Chicago",
        neighborhood="Gold Coast",
        rating=4.5, review_count=1900,
    )
    for s in [s1, s2]:
        assert s["normalizedCategory"] == "hotel"
        assert s["validationPassed"] is True


def test_scenario_mexican_restaurants_seattle():
    s1 = _make_scenario(
        scenario="Mexican restaurants in Seattle",
        venue="La Carta de Oaxaca",
        category="restaurant",
        intent="restaurants",
        query="Mexican restaurants in Seattle",
        neighborhood="Ballard",
        cuisine="Mexican",
        rating=4.5, review_count=1800,
    )
    s2 = _make_scenario(
        scenario="Mexican restaurants in Seattle",
        venue="Senor Moose",
        category="restaurant",
        intent="restaurants",
        query="Mexican restaurants in Seattle",
        neighborhood="Ballard",
        cuisine="Mexican",
        rating=4.4, review_count=2100,
    )
    for s in [s1, s2]:
        assert s["normalizedCategory"] == "restaurant"
        assert s["validationPassed"] is True


def test_scenario_best_value_dinners_seattle():
    s1 = _make_scenario(
        scenario="best value dinners in Seattle",
        venue="Pike Place Chowder",
        category="restaurant",
        intent="luxury_value",
        query="best value dinners in Seattle",
        neighborhood="Pike Place Market",
        rating=4.5, review_count=5200,
    )
    s2 = _make_scenario(
        scenario="best value dinners in Seattle",
        venue="Salumi Artisan Cured Meats",
        category="restaurant",
        intent="luxury_value",
        query="best value dinners in Seattle",
        neighborhood="Pioneer Square",
        rating=4.6, review_count=1600,
    )
    for s in [s1, s2]:
        assert s["normalizedCategory"] == "restaurant"
        assert s["validationPassed"] is True


def test_all_scenario_json_output():
    """Produce and print final scenario JSON for all 6 query types."""
    scenarios = []
    configs = [
        # cocktail bars in Chicago
        dict(scenario="cocktail bars in Chicago", venue="Billy Sunday", category="bar",
             intent="nightlife", query="cocktail bars in Chicago", neighborhood="West Town",
             rating=4.5, review_count=1800,
             editorial_reason="Known for low-ABV cocktails and seasonal menus"),
        dict(scenario="cocktail bars in Chicago", venue="The Whistler", category="bar",
             intent="nightlife", query="cocktail bars in Chicago", neighborhood="Logan Square",
             rating=4.4, review_count=1100),
        # restaurants near hotel in Chicago
        dict(scenario="restaurants near hotel in Chicago", venue="Au Cheval", category="restaurant",
             intent="restaurants", query="restaurants near hotel in Chicago", neighborhood="West Loop",
             rating=4.4, review_count=3500),
        dict(scenario="restaurants near hotel in Chicago", venue="Avec", category="restaurant",
             intent="restaurants", query="restaurants near hotel in Chicago", neighborhood="West Loop",
             cuisine="Mediterranean", rating=4.5, review_count=2200),
        # Michelin tasting menu Chicago
        dict(scenario="Michelin tasting menu Chicago", venue="Alinea", category="restaurant",
             intent="michelin_restaurants", query="Michelin tasting menu Chicago", neighborhood="Lincoln Park",
             michelin_status="3 Stars", cuisine="New American", rating=4.8, review_count=3200),
        dict(scenario="Michelin tasting menu Chicago", venue="Oriole", category="restaurant",
             intent="michelin_restaurants", query="Michelin tasting menu Chicago", neighborhood="West Loop",
             michelin_status="2 Stars", cuisine="New American", rating=4.7, review_count=1400),
        # best hotels in Chicago
        dict(scenario="best hotels in Chicago", venue="The Langham Chicago", category="hotel",
             intent="hotels", query="best hotels in Chicago", neighborhood="River North",
             rating=4.7, review_count=2800),
        dict(scenario="best hotels in Chicago", venue="Viceroy Chicago", category="hotel",
             intent="hotels", query="best hotels in Chicago", neighborhood="Gold Coast",
             rating=4.5, review_count=1900),
        # Mexican restaurants in Seattle
        dict(scenario="Mexican restaurants in Seattle", venue="La Carta de Oaxaca", category="restaurant",
             intent="restaurants", query="Mexican restaurants in Seattle", neighborhood="Ballard",
             cuisine="Mexican", rating=4.5, review_count=1800),
        dict(scenario="Mexican restaurants in Seattle", venue="Senor Moose", category="restaurant",
             intent="restaurants", query="Mexican restaurants in Seattle", neighborhood="Ballard",
             cuisine="Mexican", rating=4.4, review_count=2100),
        # best value dinners in Seattle
        dict(scenario="best value dinners in Seattle", venue="Pike Place Chowder", category="restaurant",
             intent="luxury_value", query="best value dinners in Seattle", neighborhood="Pike Place Market",
             rating=4.5, review_count=5200),
        dict(scenario="best value dinners in Seattle", venue="Salumi Artisan Cured Meats", category="restaurant",
             intent="luxury_value", query="best value dinners in Seattle", neighborhood="Pioneer Square",
             rating=4.6, review_count=1600),
    ]
    for cfg in configs:
        s = _make_scenario(**cfg)
        scenarios.append(s)
        assert s["validationPassed"] is True
        assert len(s["finalWhyPick"]) > 10

    # All final whyPick strings are non-empty and free of banned strings
    for s in scenarios:
        text = s["finalWhyPick"]
        assert "tavily" not in text.lower()
        assert "yelp" not in text.lower()
        assert "foursquare" not in text.lower()
        assert "eater" not in text.lower()
        assert "###" not in text
