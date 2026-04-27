import re

from app.concierge.reasoning import (
    BANNED_STRINGS_RE,
    GENERIC_PHRASES_RE,
    build_why_pick,
    ensure_non_empty_evidence,
)

_BLOCKED_GENERIC = [
    "a strong pick for well-reviewed",
    "guest feedback, location, and relevance",
    "polished night-out experience",
    "viable option",
    "great fit for this trip",
    "trusted place signals",
    "fits this request as a google-verified",
    "matches this dining request",
    "fits this hotel request",
    "fits this michelin request",
    "is a strong attraction match",
    "well-rated",
]

_RATING_RE = re.compile(r"\b\d+\.\d+\b")  # any decimal number = rating
_REVIEW_RE = re.compile(r"\b\d{1,3}(,\d{3})*\s+reviews?\b", re.IGNORECASE)


def _has_concrete_data_signal(text: str) -> bool:
    """At least one of: a rating number, review count, neighbourhood name, or cuisine."""
    if _RATING_RE.search(text):
        return True
    if _REVIEW_RE.search(text):
        return True
    location_words = ("loop", "park", "market", "square", "river north", "downtown", "village", "lakeview")
    return any(w in text.lower() for w in location_words)


def test_synthetic_payloads_all_pass_banned_strings_filter():
    for i in range(50):
        evidence = ensure_non_empty_evidence(
            [f"Mentioned by {i % 5 + 1} guides" if i % 2 == 0 else ""],
            rating=4.0 + ((i % 10) / 10.0),
            review_count=100 + i,
            neighborhood="West Loop" if i % 3 == 0 else None,
            tags=["cocktail bar", "late-night"],
        )
        payload = build_why_pick(
            place_name=f"Place {i}",
            evidence=evidence,
            rating=4.0 + ((i % 10) / 10.0),
            review_count=100 + i,
            category="bar",
            neighborhood="West Loop",
            user_query="nearby cocktail bars",
            intent="nightlife",
        )
        text = payload["why_pick"]["text"]
        assert text
        assert not BANNED_STRINGS_RE.search(text)
        assert not GENERIC_PHRASES_RE.search(text), f"Generic phrase in: {text!r}"
        assert "with rated" not in text.lower()
        assert "backed by rated" not in text.lower()
        # Must contain actual rating number
        assert _RATING_RE.search(text), f"No rating number found in: {text!r}"


def test_template_selection_is_deterministic_for_evidence_shape():
    both = build_why_pick(
        place_name="Kumiko",
        evidence=["Rated 4.7 (1,200 reviews)", "Mentioned by 3 guides"],
        rating=4.7,
        review_count=1200,
    )
    assert both["template_id"] == "rating_and_editorial"

    editorial_only = build_why_pick(
        place_name="Alinea",
        evidence=["Mentioned by 4 guides"],
        rating=None,
        review_count=None,
    )
    assert editorial_only["template_id"] == "editorial_only"

    google_only = build_why_pick(
        place_name="Cloud Gate",
        evidence=["Rated 4.8 (20,121 reviews)"],
        rating=4.8,
        review_count=20121,
    )
    assert google_only["template_id"] == "google_only"


def test_hidden_gem_and_michelin_reasons_include_concrete_fields():
    hidden_text = build_why_pick(
        place_name="Daisies",
        evidence=["Rated 4.7 (612 reviews)", "Near Logan Square"],
        rating=4.7,
        review_count=612,
        category="restaurant",
        cuisine="Midwestern",
        neighborhood="Logan Square",
        user_query="Hidden gems in Chicago",
        intent="hidden_gems",
    )["why_pick"]["text"]
    hidden = hidden_text.lower()
    assert "rating" in hidden or "review" in hidden, f"No rating/review in: {hidden_text!r}"
    assert "logan square" in hidden, f"No location in: {hidden_text!r}"
    assert "lower-profile" in hidden, f"Missing hidden-gem framing: {hidden_text!r}"

    michelin_text = build_why_pick(
        place_name="Alinea",
        evidence=["Rated 4.6 (1,900 reviews)", "Mentioned by Michelin guide"],
        rating=4.6,
        review_count=1900,
        category="restaurant",
        cuisine="Tasting menu",
        neighborhood="Lincoln Park",
        michelin_status="Michelin 3-star",
        user_query="Michelin restaurants",
        intent="michelin_restaurants",
    )["why_pick"]["text"]
    michelin = michelin_text.lower()
    assert "michelin" in michelin, f"No Michelin mention in: {michelin_text!r}"
    assert "lincoln park" in michelin, f"No location in: {michelin_text!r}"
    assert "destination" in michelin, f"Missing destination framing: {michelin_text!r}"


def test_why_pick_cocktail_bar_output_quality():
    text = build_why_pick(
        place_name="Blind Barber",
        evidence=["4.3 rating across 970 reviews"],
        rating=4.3,
        review_count=970,
        category="bar",
        neighborhood="Fulton Market",
        user_query="nearby cocktail bars",
        intent="nightlife",
    )["why_pick"]["text"]
    low = text.lower()
    assert "4.3" in text, f"Rating missing: {text!r}"
    assert "970" in text, f"Review count missing: {text!r}"
    assert "fulton market" in low, f"Neighbourhood missing: {text!r}"
    assert "cocktail bar" in low, f"Category missing: {text!r}"
    for phrase in _BLOCKED_GENERIC:
        assert phrase not in low, f"Blocked phrase {phrase!r} found in: {text!r}"


def test_why_pick_value_restaurant_output_quality():
    text = build_why_pick(
        place_name="La Grande Boucherie",
        evidence=["4.6 rating across 2,300 reviews"],
        rating=4.6,
        review_count=2300,
        category="restaurant",
        cuisine="French brasserie",
        neighborhood="River North",
        user_query="value dinner options",
        intent="luxury_value",
    )["why_pick"]["text"]
    low = text.lower()
    assert "4.6" in text, f"Rating missing: {text!r}"
    assert "river north" in low, f"Neighbourhood missing: {text!r}"
    assert "french brasserie" in low, f"Cuisine missing: {text!r}"
    for phrase in _BLOCKED_GENERIC:
        assert phrase not in low, f"Blocked phrase {phrase!r} found in: {text!r}"


def test_why_pick_no_generic_fallback_when_data_exists():
    """When rating + location are available, output must contain concrete data, never generic filler."""
    cases = [
        dict(category="restaurant", cuisine="Italian", neighborhood="West Loop", rating=4.5, review_count=800),
        dict(category="bar", cuisine=None, neighborhood="Logan Square", rating=4.2, review_count=300),
        dict(category="hotel", cuisine=None, neighborhood="River North", rating=4.7, review_count=1500),
        dict(category="attraction", cuisine="Museum", neighborhood="Museum Campus", rating=4.9, review_count=50000),
    ]
    for kw in cases:
        rating = kw.pop("rating")
        review_count = kw.pop("review_count")
        text = build_why_pick(
            place_name="Test Place",
            evidence=[f"{rating} rating across {review_count} reviews"],
            rating=rating,
            review_count=review_count,
            user_query="best options",
            **kw,
        )["why_pick"]["text"]
        assert _has_concrete_data_signal(text), f"No concrete signal in: {text!r}"
        for phrase in _BLOCKED_GENERIC:
            assert phrase not in text.lower(), f"Blocked phrase {phrase!r} in: {text!r}"
