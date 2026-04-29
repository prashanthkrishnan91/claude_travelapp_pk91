"""Tests for whyPick LLM output validation."""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.concierge.evidence import EvidenceUnit, normalize_evidence
from app.concierge.whypick_prompt import WhyPickLLMResult, validate_llm_output


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_result(
    why_pick: str = "Billy Sunday pours inventive stirred cocktails in a cozy West Loop setting.",
    evidence_ids: list = None,
    confidence: str = "high",
    fallback: str = "A reliable cocktail bar.",
) -> WhyPickLLMResult:
    return {
        "whyPick": why_pick,
        "evidenceIdsUsed": evidence_ids or [],
        "confidence": confidence,
        "fallbackReason": fallback,
    }


def _make_bar_units() -> list:
    gv = SimpleNamespace(
        rating=4.5,
        user_rating_count=1800,
        formatted_address="1143 N Bosworth Ave, Chicago",
        types=["cocktail_bar"],
    )
    return normalize_evidence(venue_name="Billy Sunday", category="bar", google_verification=gv)


def _make_restaurant_units() -> list:
    gv = SimpleNamespace(
        rating=4.4,
        user_rating_count=2200,
        formatted_address="800 W Randolph St, Chicago",
        types=["restaurant"],
    )
    return normalize_evidence(venue_name="Avec", category="restaurant", google_verification=gv)


# ── Valid output ─────────────────────────────────────────────────────────────

def test_valid_bar_output_passes():
    units = _make_bar_units()
    result = _make_result("Billy Sunday pours inventive stirred cocktails in a cozy West Loop setting.")
    assert validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units) is None


def test_valid_restaurant_output_passes():
    units = _make_restaurant_units()
    result = _make_result("Avec serves wood-fired small plates in a River West space built for sharing.")
    assert validate_llm_output(result, venue_name="Avec", category="restaurant", evidence_units=units) is None


def test_valid_hotel_output_passes():
    units = []
    result = _make_result("A well-located downtown hotel with strong review volume and easy access to the Loop.")
    assert validate_llm_output(result, venue_name="The Langham", category="hotel", evidence_units=units) is None


# ── Empty / too short ────────────────────────────────────────────────────────

def test_empty_string_rejected():
    units = _make_bar_units()
    result = _make_result("")
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection is not None
    assert "short" in rejection


def test_too_short_rejected():
    units = _make_bar_units()
    result = _make_result("Nice bar.")
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection is not None


def test_missing_why_pick_key_rejected():
    units = _make_bar_units()
    result: WhyPickLLMResult = {"whyPick": "", "evidenceIdsUsed": [], "confidence": "high", "fallbackReason": ""}
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection is not None


# ── Source names in copy ─────────────────────────────────────────────────────

def test_yelp_in_copy_rejected():
    units = _make_bar_units()
    result = _make_result("A cocktail bar rated 4.5 on Yelp with strong evening reviews.")
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection == "source name in user-facing copy"


def test_foursquare_in_copy_rejected():
    units = _make_bar_units()
    result = _make_result("Listed on Foursquare as a top cocktail bar in the city.")
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection == "source name in user-facing copy"


def test_tavily_in_copy_rejected():
    units = _make_bar_units()
    result = _make_result("Tavily research confirms this is a top-rated cocktail bar.")
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection == "source name in user-facing copy"


def test_google_in_copy_rejected():
    units = _make_bar_units()
    result = _make_result("A cocktail bar verified on Google with a 4.5 rating.")
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection == "source name in user-facing copy"


def test_eater_in_copy_rejected():
    units = _make_bar_units()
    result = _make_result("Featured in Eater as one of the best cocktail bars in Chicago.")
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection == "source name in user-facing copy"


# ── Markdown / debug text ────────────────────────────────────────────────────

def test_markdown_header_rejected():
    units = _make_bar_units()
    result = _make_result("## A great cocktail bar in West Loop with solid ratings.")
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection is not None
    assert "markdown" in rejection


def test_bold_text_rejected():
    units = _make_bar_units()
    result = _make_result("A **great** cocktail bar in West Loop.")
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection is not None


def test_backtick_rejected():
    units = _make_bar_units()
    result = _make_result("A `cocktail bar` in West Loop with solid ratings.")
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection is not None


# ── Cross-venue contamination ────────────────────────────────────────────────

def test_cross_venue_contamination_rejected():
    units = _make_bar_units()
    result = _make_result("Better than The Aviary, this is a cocktail bar in West Loop.")
    rejection = validate_llm_output(
        result,
        venue_name="Billy Sunday",
        category="bar",
        evidence_units=units,
        known_venue_names=["The Aviary", "Billy Sunday"],
    )
    assert rejection is not None
    assert "cross-venue" in rejection


def test_own_venue_name_in_copy_is_fine():
    units = _make_bar_units()
    result = _make_result("Billy Sunday is a cocktail bar in West Loop with deep review volume.")
    rejection = validate_llm_output(
        result,
        venue_name="Billy Sunday",
        category="bar",
        evidence_units=units,
        known_venue_names=["Billy Sunday", "The Aviary"],
    )
    assert rejection is None


# ── Rating-first generic ─────────────────────────────────────────────────────

def test_rating_first_rejected():
    units = _make_bar_units()
    result = _make_result("4.5 rated cocktail bar in West Loop with 1,800 reviews.")
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection == "rating-first output"


def test_rated_first_rejected():
    units = _make_bar_units()
    result = _make_result("Rated 4.5 with strong volume, this cocktail bar is in West Loop.")
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection == "rating-first output"


# ── Category mismatch language ───────────────────────────────────────────────

def test_speakeasy_language_in_restaurant_rejected():
    units = _make_restaurant_units()
    result = _make_result("A speakeasy-style venue with a tasting menu in the West Loop.")
    rejection = validate_llm_output(result, venue_name="Avec", category="restaurant", evidence_units=units)
    assert rejection is not None
    assert "category mismatch" in rejection


def test_cocktail_bar_language_in_restaurant_rejected():
    units = _make_restaurant_units()
    result = _make_result("A cocktail bar with food options, popular for late-night crowds.")
    rejection = validate_llm_output(result, venue_name="Avec", category="restaurant", evidence_units=units)
    assert rejection is not None
    assert "category mismatch" in rejection


def test_bar_language_in_bar_context_is_fine():
    units = _make_bar_units()
    result = _make_result("Billy Sunday is a cocktail bar in West Loop known for its inventive seasonal cocktail program.")
    assert validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units) is None


# ── Multi-sentence rambling ──────────────────────────────────────────────────

def test_three_sentences_rejected():
    units = _make_bar_units()
    result = _make_result(
        "A cocktail bar in West Loop. It has strong ratings. A good place for the evening."
    )
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection == "multi-sentence output"


def test_two_sentences_short_passes():
    units = _make_bar_units()
    result = _make_result("Billy Sunday serves inventive cocktails in West Loop. A strong pick for the evening.")
    # two short sentences under 140 chars with specific signal — allowed
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection is None


def test_two_sentences_over_140_chars_rejected():
    units = _make_bar_units()
    long_text = (
        "A cocktail bar in the West Loop neighborhood of Chicago with deep review volume. "
        "A solid evening pick for both locals and visitors to the city looking for craft drinks."
    )
    assert len(long_text) > 140
    result = _make_result(long_text)
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection == "output too long"


# ── Evidence IDs ─────────────────────────────────────────────────────────────

def test_invalid_evidence_ids_rejected():
    units = _make_bar_units()
    result = _make_result(
        "Billy Sunday is a cocktail bar in West Loop with an inventive seasonal program.",
        evidence_ids=["deadbeef", "cafebabe"],  # none match
    )
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection == "evidence IDs do not match provided units"


def test_valid_evidence_ids_pass():
    units = _make_bar_units()
    valid_id = units[0].id
    result = _make_result(
        "Billy Sunday is a cocktail bar in West Loop with an inventive seasonal program.",
        evidence_ids=[valid_id],
    )
    assert validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units) is None


def test_empty_evidence_ids_passes():
    units = _make_bar_units()
    result = _make_result(
        "Billy Sunday is a cocktail bar in West Loop with an inventive seasonal program.",
        evidence_ids=[],
    )
    assert validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units) is None


# ── Vague output ─────────────────────────────────────────────────────────────

def test_vague_phrase_rejected():
    units = _make_bar_units()
    result = _make_result("a must visit")
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection is not None


def test_concrete_specific_output_passes():
    units = _make_bar_units()
    result = _make_result("Billy Sunday is a cocktail bar in West Loop celebrated for its zero-waste spirit program.")
    assert validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units) is None


# ── Generic (rating/volume/location only) outputs now rejected ───────────────

def test_generic_bar_rating_volume_rejected():
    units = _make_bar_units()
    result = _make_result("A cocktail bar in West Loop with deep review volume, a solid evening pick.")
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection == "generic output: lacks venue-specific differentiator"


def test_generic_restaurant_volume_rating_rejected():
    units = _make_restaurant_units()
    result = _make_result("A Mediterranean restaurant in River West with high review volume and consistent ratings.")
    rejection = validate_llm_output(result, venue_name="Avec", category="restaurant", evidence_units=units)
    assert rejection == "generic output: lacks venue-specific differentiator"


def test_generic_bar_count_only_rejected():
    units = _make_bar_units()
    result = _make_result("A well-regarded cocktail bar in West Loop with 1,800 reviews and consistent ratings.")
    rejection = validate_llm_output(result, venue_name="Billy Sunday", category="bar", evidence_units=units)
    assert rejection == "generic output: lacks venue-specific differentiator"
