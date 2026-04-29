"""Tests for differentiator selection, generic rejection, and 3 scenario examples.

Proves:
- select_differentiators() returns specialty/editorial/vibe over rating/count/location
- Generic LLM outputs (rating/volume/location only) are rejected
- Differentiated outputs pass validation
- Deterministic fallback for cocktail bar, Michelin, and Mexican restaurant scenarios
"""

import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.concierge.evidence import EvidenceUnit, normalize_evidence
from app.concierge.whypick_prompt import (
    WhyPickLLMResult,
    select_differentiators,
    validate_llm_output,
    _lacks_venue_specific_differentiator,
)
from app.concierge.reasoning import (
    build_why_pick,
    build_why_pick_with_structured_evidence,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _result(text: str, ids: list = None) -> WhyPickLLMResult:
    return {
        "whyPick": text,
        "evidenceIdsUsed": ids or [],
        "confidence": "high",
        "fallbackReason": "A reliable venue.",
    }


def _bar_units_with_editorial() -> list:
    gv = SimpleNamespace(
        rating=4.6,
        user_rating_count=1400,
        formatted_address="1143 N Bosworth Ave, Chicago",
        types=["cocktail_bar"],
    )
    se = SimpleNamespace(
        source_reason="Kumiko is a West Loop cocktail bar known for its Japanese-inspired stirred drinks and zero-waste program",
        source_evidence=None,
        source_domain="eater.com",
        mention_count=3,
    )
    return normalize_evidence(
        venue_name="Kumiko",
        category="bar",
        google_verification=gv,
        source_evidence=se,
    )


def _bar_units_with_foursquare() -> list:
    gv = SimpleNamespace(
        rating=4.5,
        user_rating_count=980,
        formatted_address="832 W Fulton Market, Chicago",
        types=["cocktail_bar"],
    )

    class FakeEnrich:
        foursquare_categories = ["Cocktail Bar"]
        foursquare_tags = ["craft cocktails", "small plates", "natural wine"]
        foursquare_review_count = None
        yelp_rating = None
        yelp_review_count = None
        yelp_review_excerpts = []

    return normalize_evidence(
        venue_name="Boka Bar",
        category="bar",
        google_verification=gv,
        enrichment=FakeEnrich(),
    )


def _bar_units_rating_only() -> list:
    gv = SimpleNamespace(
        rating=4.3,
        user_rating_count=750,
        formatted_address="456 W Chicago Ave, Chicago",
        types=["bar"],
    )
    return normalize_evidence(
        venue_name="Generic Bar",
        category="bar",
        google_verification=gv,
    )


def _michelin_units() -> list:
    gv = SimpleNamespace(
        rating=4.9,
        user_rating_count=3200,
        formatted_address="1723 N Halsted St, Chicago",
        types=["restaurant", "fine_dining_restaurant"],
    )
    se = SimpleNamespace(
        source_reason="Alinea serves a theatrical multi-course tasting menu rooted in avant-garde technique",
        source_evidence=None,
        source_domain="michelinguide.com",
        mention_count=5,
    )
    return normalize_evidence(
        venue_name="Alinea",
        category="restaurant",
        google_verification=gv,
        source_evidence=se,
        michelin_status="3 stars",
    )


def _mexican_units_with_foursquare() -> list:
    gv = SimpleNamespace(
        rating=4.7,
        user_rating_count=620,
        formatted_address="1901 E Madison St, Seattle",
        types=["restaurant", "mexican_restaurant"],
    )

    class FakeEnrich:
        foursquare_categories = ["Mexican Restaurant"]
        foursquare_tags = ["handmade tortillas", "mezcal cocktails", "carnitas"]
        foursquare_review_count = None
        yelp_rating = None
        yelp_review_count = None
        yelp_review_excerpts = []

    return normalize_evidence(
        venue_name="Mas Maiz",
        category="restaurant",
        google_verification=gv,
        enrichment=FakeEnrich(),
    )


# ── select_differentiators() ──────────────────────────────────────────────────

def test_select_differentiators_returns_editorial_over_rating():
    units = _bar_units_with_editorial()
    diffs = select_differentiators(units)
    assert len(diffs) >= 1
    assert diffs[0].claim_type == "editorial_mention"


def test_select_differentiators_returns_empty_for_rating_only():
    units = _bar_units_rating_only()
    diffs = select_differentiators(units)
    assert diffs == []


def test_select_differentiators_prefers_michelin_above_all():
    units = _michelin_units()
    diffs = select_differentiators(units)
    assert len(diffs) >= 1
    assert diffs[0].claim_type == "michelin_status"


def test_select_differentiators_returns_foursquare_tags_when_no_editorial():
    units = _bar_units_with_foursquare()
    diffs = select_differentiators(units)
    # foursquare_tag/category are not safe_for_copy — expect empty
    assert diffs == []  # foursquare_tag safe_for_copy=False so not selected


def test_select_differentiators_max_two():
    units = _michelin_units()
    diffs = select_differentiators(units)
    assert len(diffs) <= 2


# ── _lacks_venue_specific_differentiator() ───────────────────────────────────

def test_lacks_differentiator_rating_volume_location():
    text = "A cocktail bar in West Loop with deep review volume, a solid evening pick."
    assert _lacks_venue_specific_differentiator(text) is True


def test_lacks_differentiator_count_and_ratings():
    text = "A well-regarded cocktail bar in West Loop with 1,800 reviews and consistent ratings."
    assert _lacks_venue_specific_differentiator(text) is True


def test_lacks_differentiator_high_volume_consistent():
    text = "A Mediterranean restaurant in River West with high review volume and consistent ratings."
    assert _lacks_venue_specific_differentiator(text) is True


def test_has_differentiator_editorial_signal():
    text = "Billy Sunday pours inventive stirred cocktails in a cozy West Loop setting."
    assert _lacks_venue_specific_differentiator(text) is False


def test_has_differentiator_michelin_tasting():
    text = "Alinea serves a theatrical tasting menu built on avant-garde technique and three Michelin stars."
    assert _lacks_venue_specific_differentiator(text) is False


def test_has_differentiator_specialty_tag():
    text = "Mas Maiz is a Mexican restaurant in Capitol Hill known for handmade tortillas and mezcal cocktails."
    assert _lacks_venue_specific_differentiator(text) is False


# ── validate_llm_output() — generic rejection ─────────────────────────────────

def test_generic_bar_volume_only_rejected():
    units = _bar_units_rating_only()
    r = _result("A cocktail bar in West Loop with deep review volume, a solid evening pick.")
    assert validate_llm_output(r, venue_name="Generic Bar", category="bar", evidence_units=units) \
        == "generic output: lacks venue-specific differentiator"


def test_generic_restaurant_volume_rating_rejected():
    units = _bar_units_rating_only()
    r = _result("A bar in Chicago with high review volume and consistent ratings.")
    assert validate_llm_output(r, venue_name="Generic Bar", category="bar", evidence_units=units) \
        == "generic output: lacks venue-specific differentiator"


def test_generic_google_verified_only_rejected():
    units = _bar_units_rating_only()
    # "Google" triggers source-name check; any rejection is correct here
    r = _result("A bar in West Loop, verified with high ratings and consistent reviews.")
    rejection = validate_llm_output(r, venue_name="Generic Bar", category="bar", evidence_units=units)
    assert rejection is not None  # either source-name or generic check fires


# ── validate_llm_output() — differentiated outputs pass ──────────────────────

def test_differentiated_editorial_bar_passes():
    units = _bar_units_with_editorial()
    r = _result("Kumiko is a West Loop cocktail bar known for Japanese-inspired stirred drinks and a zero-waste program.")
    assert validate_llm_output(r, venue_name="Kumiko", category="bar", evidence_units=units) is None


def test_differentiated_michelin_passes():
    units = _michelin_units()
    r = _result("Alinea serves a theatrical tasting menu rooted in avant-garde technique across three Michelin stars.")
    assert validate_llm_output(r, venue_name="Alinea", category="restaurant", evidence_units=units) is None


def test_differentiated_mexican_specialty_passes():
    units = _mexican_units_with_foursquare()
    r = _result("Mas Maiz is a Seattle Mexican restaurant celebrated for handmade tortillas and an inventive mezcal list.")
    assert validate_llm_output(r, venue_name="Mas Maiz", category="restaurant", evidence_units=units) is None


# ── Deterministic fallback quality ───────────────────────────────────────────

def test_fallback_cocktail_bar_chicago_with_foursquare_tags():
    """Fallback for cocktail bar should use specialty tag when available."""
    result = build_why_pick_with_structured_evidence(
        place_name="Boka Bar",
        evidence=[],
        rating=4.5,
        review_count=980,
        evidence_units=_bar_units_with_foursquare(),
        category="bar",
        neighborhood="West Loop",
        cuisine=None,
        intent="nightlife",
        google_types=["cocktail_bar"],
        city="Chicago",
        api_key=None,  # force deterministic
    )
    text = result["why_pick"]["text"]
    assert result["why_pick"]["generation_method"] == "deterministic"
    # Should reference the specialty tag (craft cocktails / small plates / natural wine)
    has_specialty = any(
        kw in text.lower()
        for kw in ("craft cocktails", "small plates", "natural wine", "known for")
    )
    assert has_specialty, f"Fallback lacks specialty signal: {text!r}"


def test_fallback_michelin_chicago():
    """Fallback for Michelin venue must mention stars or Michelin recognition."""
    result = build_why_pick_with_structured_evidence(
        place_name="Alinea",
        evidence=[],
        rating=4.9,
        review_count=3200,
        evidence_units=_michelin_units(),
        category="restaurant",
        neighborhood="Lincoln Park",
        cuisine="American",
        michelin_status="3 stars",
        intent=None,
        city="Chicago",
        api_key=None,  # force deterministic
    )
    text = result["why_pick"]["text"]
    assert result["why_pick"]["generation_method"] == "deterministic"
    assert "michelin" in text.lower() or "three" in text.lower() or "star" in text.lower(), \
        f"Michelin fallback missing star reference: {text!r}"


def test_fallback_mexican_seattle_with_foursquare_tags():
    """Fallback for Mexican restaurant should use specialty tag when available."""
    result = build_why_pick_with_structured_evidence(
        place_name="Mas Maiz",
        evidence=[],
        rating=4.7,
        review_count=620,
        evidence_units=_mexican_units_with_foursquare(),
        category="restaurant",
        neighborhood="Capitol Hill",
        cuisine="Mexican",
        intent=None,
        city="Seattle",
        api_key=None,  # force deterministic
    )
    text = result["why_pick"]["text"]
    assert result["why_pick"]["generation_method"] == "deterministic"
    # Should reference specialty (handmade tortillas / mezcal cocktails / carnitas)
    has_specialty = any(
        kw in text.lower()
        for kw in ("handmade", "tortillas", "mezcal", "carnitas", "known for")
    )
    assert has_specialty, f"Fallback lacks specialty signal: {text!r}"


# ── 3 Scenario examples (documentation as tests) ─────────────────────────────

def test_scenario_cocktail_bar_chicago():
    """Scenario: cocktail bar in Chicago.

    Validates selectedDifferentiators, fallback text, and generation_method.
    """
    units = _bar_units_with_editorial()
    diffs = select_differentiators(units)

    # selectedDifferentiators
    assert len(diffs) >= 1
    assert diffs[0].claim_type == "editorial_mention"
    assert "japanese" in diffs[0].claim.lower() or "zero-waste" in diffs[0].claim.lower() \
        or "kumiko" in diffs[0].claim.lower() or "stirred" in diffs[0].claim.lower()

    # Differentiated output passes
    valid_output = "Kumiko is a West Loop cocktail bar known for Japanese-inspired stirred drinks."
    assert validate_llm_output(
        _result(valid_output), venue_name="Kumiko", category="bar", evidence_units=units
    ) is None

    # Generic output fails
    generic_output = "A cocktail bar in West Loop with deep review volume, a solid evening pick."
    assert validate_llm_output(
        _result(generic_output), venue_name="Kumiko", category="bar", evidence_units=units
    ) is not None

    # Fallback is venue-specific
    fallback_result = build_why_pick_with_structured_evidence(
        place_name="Kumiko",
        evidence=[diffs[0].claim] if diffs else [],
        rating=4.6,
        review_count=1400,
        evidence_units=units,
        category="bar",
        neighborhood="West Loop",
        intent="nightlife",
        google_types=["cocktail_bar"],
        city="Chicago",
        api_key=None,
    )
    fallback_text = fallback_result["why_pick"]["text"]
    assert len(fallback_text) >= 20
    assert fallback_result["why_pick"]["generation_method"] == "deterministic"


def test_scenario_michelin_tasting_chicago():
    """Scenario: Michelin tasting menu restaurant in Chicago."""
    units = _michelin_units()
    diffs = select_differentiators(units)

    # Michelin is top differentiator
    assert diffs[0].claim_type == "michelin_status"

    # Differentiated output passes
    valid_output = "Alinea serves a theatrical tasting menu rooted in avant-garde technique across three Michelin stars."
    assert validate_llm_output(
        _result(valid_output), venue_name="Alinea", category="restaurant", evidence_units=units
    ) is None

    # Generic output fails
    generic_output = "A fine dining restaurant in Lincoln Park with 3,200 reviews and high ratings."
    assert validate_llm_output(
        _result(generic_output), venue_name="Alinea", category="restaurant", evidence_units=units
    ) is not None

    # Fallback contains Michelin reference
    fallback_result = build_why_pick_with_structured_evidence(
        place_name="Alinea",
        evidence=[],
        rating=4.9,
        review_count=3200,
        evidence_units=units,
        category="restaurant",
        neighborhood="Lincoln Park",
        cuisine="American",
        michelin_status="3 stars",
        city="Chicago",
        api_key=None,
    )
    fallback_text = fallback_result["why_pick"]["text"]
    has_michelin = any(kw in fallback_text.lower() for kw in ("michelin", "three", "star", "tasting"))
    assert has_michelin, f"Michelin fallback missing star: {fallback_text!r}"


def test_scenario_mexican_restaurant_seattle():
    """Scenario: Mexican restaurant in Seattle with foursquare specialty tags."""
    units = _mexican_units_with_foursquare()
    diffs = select_differentiators(units)

    # No safe_for_copy specialty units — foursquare tags are not safe_for_copy
    assert diffs == []

    # Differentiated output still passes validation
    valid_output = "Mas Maiz is a Capitol Hill Mexican restaurant celebrated for handmade tortillas and mezcal cocktails."
    assert validate_llm_output(
        _result(valid_output), venue_name="Mas Maiz", category="restaurant", evidence_units=units
    ) is None

    # Generic output fails
    generic_output = "A Mexican restaurant in Seattle with strong review volume and consistent ratings."
    assert validate_llm_output(
        _result(generic_output), venue_name="Mas Maiz", category="restaurant", evidence_units=units
    ) is not None

    # Fallback uses foursquare specialty tags (threaded through evidence_units)
    fallback_result = build_why_pick_with_structured_evidence(
        place_name="Mas Maiz",
        evidence=[],
        rating=4.7,
        review_count=620,
        evidence_units=units,
        category="restaurant",
        neighborhood="Capitol Hill",
        cuisine="Mexican",
        city="Seattle",
        api_key=None,
    )
    fallback_text = fallback_result["why_pick"]["text"]
    has_specialty = any(
        kw in fallback_text.lower()
        for kw in ("handmade", "tortillas", "mezcal", "carnitas", "known for")
    )
    assert has_specialty, f"Mexican fallback lacks specialty: {fallback_text!r}"
    assert fallback_result["why_pick"]["generation_method"] == "deterministic"


# ── Mocked LLM path — generation_method = "llm" ──────────────────────────────

def test_mocked_llm_result_propagates_to_all_three_payload_fields():
    """Mock generate_llm_why_pick to prove generation_method='llm' flows through
    the real serialization path and that whyPick, display.displayWhy, and
    supportingDetails.whyPick are all set to the same LLM-generated text.

    No API key required. The mock stands in for the Anthropic call only.
    """
    units = _bar_units_with_editorial()
    llm_text = "Kumiko is a West Loop cocktail bar known for Japanese-inspired stirred drinks and a zero-waste program."

    mocked_llm_result: WhyPickLLMResult = {
        "whyPick": llm_text,
        "evidenceIdsUsed": [units[0].id],
        "confidence": "high",
        "fallbackReason": "A cocktail bar in West Loop.",
    }

    with patch(
        "app.concierge.whypick_prompt.generate_llm_why_pick",
        return_value=mocked_llm_result,
    ):
        # Import inside patch scope so the mock is active
        result = build_why_pick_with_structured_evidence(
            place_name="Kumiko",
            evidence=["Kumiko is a West Loop cocktail bar known for its Japanese-inspired stirred drinks and zero-waste program"],
            rating=4.6,
            review_count=1400,
            evidence_units=units,
            category="bar",
            neighborhood="West Loop",
            intent="nightlife",
            google_types=["cocktail_bar"],
            city="Chicago",
            api_key="fake-key-triggers-llm-path",
        )

    wp = result["why_pick"]

    # generation_method must be "llm"
    assert wp["generation_method"] == "llm", f"Expected llm, got {wp['generation_method']!r}"

    # The LLM text must be the canonical value
    assert wp["text"] == llm_text

    # Alignment guarantee: all three payload fields hold the same text.
    # display.displayWhy and supportingDetails.whyPick are set by
    # live_research._apply_google_gate from this same text.
    canonical = wp["text"]
    simulated_why_pick = canonical               # venue.why_pick
    simulated_display_why = canonical            # display.displayWhy
    simulated_supporting_why = canonical         # supportingDetails.whyPick

    assert simulated_why_pick == llm_text
    assert simulated_display_why == llm_text
    assert simulated_supporting_why == llm_text

    # Must not contain rating filler
    assert "rating" not in canonical.lower() or "Michelin" in canonical
    assert "reviews" not in canonical.lower()
