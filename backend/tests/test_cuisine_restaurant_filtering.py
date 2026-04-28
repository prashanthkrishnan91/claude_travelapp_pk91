"""Regression tests for cuisine-specific restaurant intent filtering.

Acceptance criteria (H):
- Non-Mexican restaurants (Pink Door, Canlis, Six Seven, Crab Pot, Toulouse) are
  rejected for a "Mexican restaurants" query.
- Mendoza's Mexican Mercado (grocery_store/butcher_shop only) is not addable.
- La Chingona, Rojo's, El Moose (mexican_restaurant type) display as "Mexican Restaurant".
- displayWhy is not bare rating/review template text.
- "Near Rojo" or "in Rojo" cannot be produced when the neighborhood would be
  derived from the candidate's own name.
- Rating and address live in displayMetaLine, not as the entire displayWhy.
"""

from __future__ import annotations

import re
from typing import List, Optional

import pytest

from app.concierge.reasoning import (
    GENERIC_PHRASES_RE,
    build_concierge_display_reason,
    _build_cuisine_restaurant_display_why,
)
from app.services.google_places import OPERATIONAL, GooglePlaceVerification
from app.services.live_research import (
    _category_fit_score,
    _category_label,
    _extract_cuisine_filter,
    _neighborhood_is_business_name,
    _GOOGLE_TYPE_TO_CUISINE_LABEL,
    _RESTAURANT_COMPATIBLE_TYPES,
    _NON_RESTAURANT_TYPES,
)

# ── Shared constants ──────────────────────────────────────────────────────────

_MEXICAN_QUERY = "Mexican restaurants in Seattle"

_RATING_TEMPLATE_RE = re.compile(
    r"\bwith\s+\d+[\.,]\d+\s+rating\s+across\s+[\d,]+\s+reviews\b"
    r"|^A (?:top-rated|verified) restaurant with \d",
    re.IGNORECASE,
)


def _make_gv(
    *,
    name: str,
    types: List[str],
    status: str = OPERATIONAL,
    confidence: str = "high",
    rating: float = 4.5,
    review_count: int = 500,
    place_id: str = "fake_id",
    address: str = "123 Main St, Seattle, WA",
) -> GooglePlaceVerification:
    return GooglePlaceVerification(
        provider_place_id=place_id,
        name=name,
        formatted_address=address,
        business_status=status,
        confidence=confidence,
        types=types,
        rating=rating,
        user_rating_count=review_count,
    )


# ── A: Cuisine hard gating — non-Mexican restaurants rejected ─────────────────


@pytest.mark.parametrize(
    "name,types",
    [
        ("The Pink Door", ["italian_restaurant", "restaurant", "food"]),
        ("Canlis", ["fine_dining_restaurant", "american_restaurant", "restaurant"]),
        ("Six Seven", ["seafood_restaurant", "american_restaurant", "restaurant"]),
        ("The Crab Pot", ["seafood_restaurant", "restaurant", "food"]),
        (
            "Toulouse Petit",
            ["american_restaurant", "french_restaurant", "restaurant"],
        ),
    ],
)
def test_non_mexican_restaurants_rejected_for_mexican_query(name: str, types: List[str]) -> None:
    gv = _make_gv(name=name, types=types)
    score = _category_fit_score("restaurants", _MEXICAN_QUERY, gv)
    assert score < 0.45, (
        f"{name!r} (types={types}) should be rejected for Mexican query "
        f"(score={score:.2f}), got score above threshold"
    )


# ── B: Non-restaurant place types — not addable as restaurant ─────────────────


def test_mendozas_grocery_not_addable() -> None:
    """Mendoza's Mexican Mercado has 'mexican' in the name but is grocery_store only."""
    gv = _make_gv(
        name="Mendoza's Mexican Mercado",
        types=["butcher_shop", "grocery_store", "store", "manufacturer"],
    )
    score = _category_fit_score("restaurants", _MEXICAN_QUERY, gv)
    assert score < 0.45, (
        f"Mendoza's Mexican Mercado (grocery only) must not be addable as a restaurant "
        f"(score={score:.2f})"
    )


def test_name_match_requires_restaurant_compatible_types() -> None:
    """A place with cuisine in its name but only non-restaurant types must not get name-match score."""
    gv = _make_gv(
        name="Mexican Import Store",
        types=["grocery_store", "store", "market"],
    )
    score = _category_fit_score("restaurants", _MEXICAN_QUERY, gv)
    assert score < 0.45, (
        f"Name-match must be gated behind restaurant-compatible types; got score={score:.2f}"
    )


def test_mexican_restaurant_with_grocery_side_still_accepted() -> None:
    """If a place has both mexican_restaurant AND grocery_store types, it should still pass."""
    gv = _make_gv(
        name="Mendoza's Mexican Kitchen & Market",
        types=["mexican_restaurant", "restaurant", "grocery_store"],
    )
    score = _category_fit_score("restaurants", _MEXICAN_QUERY, gv)
    assert score >= 0.45, (
        f"A place with mexican_restaurant type (even with grocery_store) should pass; got score={score:.2f}"
    )


# ── C: Category inference — mexican_restaurant → "Mexican Restaurant" ─────────


@pytest.mark.parametrize(
    "types,expected_label",
    [
        (["mexican_restaurant", "restaurant"], "Mexican Restaurant"),
        (["italian_restaurant", "restaurant"], "Italian Restaurant"),
        (["japanese_restaurant", "sushi_restaurant"], "Japanese Restaurant"),
        (["sushi_restaurant"], "Japanese Restaurant"),
        (["thai_restaurant", "restaurant"], "Thai Restaurant"),
        (["french_restaurant"], "French Restaurant"),
        (["steak_house", "restaurant"], "Steakhouse"),
        (["seafood_restaurant", "restaurant"], "Seafood Restaurant"),
        (["restaurant"], "Restaurant"),  # generic — no cuisine label
        (["food", "meal_takeaway"], "Restaurant"),  # no cuisine type
    ],
)
def test_category_label_derives_from_google_types(types: List[str], expected_label: str) -> None:
    label = _category_label("restaurant", candidate=None, google_types=types)
    assert label == expected_label, (
        f"types={types!r}: expected {expected_label!r}, got {label!r}"
    )


def test_la_chingona_displays_mexican_restaurant() -> None:
    label = _category_label(
        "restaurant", candidate=None, google_types=["mexican_restaurant", "restaurant"]
    )
    assert label == "Mexican Restaurant"


def test_google_type_to_cuisine_label_map_completeness() -> None:
    """Every cuisine in _CUISINE_TO_GOOGLE_TYPES should have a label mapping."""
    from app.services.live_research import _CUISINE_TO_GOOGLE_TYPES

    for cuisine, gtype_set in _CUISINE_TO_GOOGLE_TYPES.items():
        for gtype in gtype_set:
            if gtype in ("breakfast_restaurant", "brunch_restaurant", "cafe"):
                continue  # brunch uses cafe; no strict label required
            assert gtype in _GOOGLE_TYPE_TO_CUISINE_LABEL, (
                f"Missing entry in _GOOGLE_TYPE_TO_CUISINE_LABEL for {gtype!r} "
                f"(from cuisine={cuisine!r})"
            )


# ── D: displayWhy is not bare rating/review template text ─────────────────────


@pytest.mark.parametrize(
    "name,cuisine,neighborhood,rating,review_count",
    [
        ("La Chingona", "Mexican", "West Seattle", 4.8, 1141),
        ("Rojo's", "Mexican", None, 4.7, 397),
        ("El Moose", "Mexican", "Ballard", 4.6, 1731),
    ],
)
def test_display_why_not_rating_template(
    name: str,
    cuisine: str,
    neighborhood: Optional[str],
    rating: float,
    review_count: int,
) -> None:
    why = build_concierge_display_reason(
        place_name=name,
        query_context=_MEXICAN_QUERY,
        intent="restaurants",
        category="restaurant",
        cuisine=cuisine,
        neighborhood=neighborhood,
        rating=rating,
        review_count=review_count,
        google_types=["mexican_restaurant", "restaurant"],
    )
    assert why, f"[{name}] displayWhy is empty"
    assert not _RATING_TEMPLATE_RE.search(why), (
        f"[{name}] displayWhy is a bare rating template: {why!r}"
    )
    assert not GENERIC_PHRASES_RE.search(why), (
        f"[{name}] displayWhy contains generic phrases: {why!r}"
    )
    assert len(why) <= 160, f"[{name}] displayWhy exceeds 160 chars: {why!r}"
    # Must mention the cuisine
    assert "mexican" in why.lower(), (
        f"[{name}] displayWhy should mention Mexican cuisine: {why!r}"
    )


def test_cuisine_restaurant_display_why_builder() -> None:
    """_build_cuisine_restaurant_display_why must not produce template text."""
    for (loc, rating, rc) in [
        ("West Seattle", 4.8, 1141),
        (None, 4.7, 397),
        ("Ballard", 4.6, 1731),
        (None, 4.3, 80),
    ]:
        why = _build_cuisine_restaurant_display_why(
            cuisine="Mexican", loc=loc, rating=rating, review_count=rc
        )
        assert why, f"Empty displayWhy for loc={loc}"
        assert not _RATING_TEMPLATE_RE.search(why), (
            f"Rating template in: {why!r}"
        )
        assert "mexican" in why.lower(), f"Should mention Mexican in: {why!r}"
        assert len(why) <= 160, f"Too long: {why!r}"


# ── E: No fake neighborhood from business name ────────────────────────────────


@pytest.mark.parametrize(
    "neighborhood,candidate_name,should_be_rejected",
    [
        ("Rojo", "Rojo's Mexican Kitchen", True),
        ("Rojo's", "Rojo's Mexican Kitchen", True),
        ("La Chingona", "La Chingona Mexican Restaurant", True),
        ("Moose", "El Moose", True),
        ("West Seattle", "La Chingona Mexican Restaurant", False),
        ("Ballard", "El Moose", False),
        ("Capitol Hill", "Rojo's Mexican Kitchen", False),
        ("Downtown", "The Pink Door", False),
    ],
)
def test_neighborhood_is_business_name_guard(
    neighborhood: str, candidate_name: str, should_be_rejected: bool
) -> None:
    result = _neighborhood_is_business_name(neighborhood, candidate_name)
    assert result == should_be_rejected, (
        f"_neighborhood_is_business_name({neighborhood!r}, {candidate_name!r}): "
        f"expected {should_be_rejected}, got {result}"
    )


def test_build_concierge_reason_rejects_own_name_as_neighborhood() -> None:
    """'in Rojo' must never appear when neighborhood is the business name."""
    why = build_concierge_display_reason(
        place_name="Rojo's Mexican Kitchen",
        query_context=_MEXICAN_QUERY,
        intent="restaurants",
        category="restaurant",
        cuisine="Mexican",
        neighborhood="Rojo",  # unsafe — should be filtered
        rating=4.7,
        review_count=397,
        google_types=["mexican_restaurant", "restaurant"],
    )
    assert "in Rojo" not in why, f"Fake neighborhood 'in Rojo' must not appear: {why!r}"
    assert "near Rojo" not in why.lower(), f"Fake neighborhood 'near Rojo' must not appear: {why!r}"


def test_build_concierge_reason_rejects_la_chingona_as_neighborhood() -> None:
    why = build_concierge_display_reason(
        place_name="La Chingona",
        query_context=_MEXICAN_QUERY,
        intent="restaurants",
        category="restaurant",
        cuisine="Mexican",
        neighborhood="La Chingona",  # unsafe
        rating=4.8,
        review_count=1141,
        google_types=["mexican_restaurant", "restaurant"],
    )
    assert "in La Chingona" not in why, f"Fake neighborhood leak: {why!r}"


# ── Integration: rating stays in metaLine, not as the whole why ───────────────


def test_display_why_does_not_duplicate_rating_as_main_sentence() -> None:
    """displayWhy anchor must be category/location, not 'A restaurant with 4.8 rating...'."""
    why = build_concierge_display_reason(
        place_name="El Moose",
        query_context=_MEXICAN_QUERY,
        intent="restaurants",
        category="restaurant",
        cuisine="Mexican",
        neighborhood="Ballard",
        rating=4.6,
        review_count=1731,
        google_types=["mexican_restaurant", "restaurant"],
    )
    # Must not be the old bare-rating template sentence
    assert not re.search(
        r"^A (?:top-rated|verified) restaurant (?:in|with) .+? (?:with )?\d+[\.,]\d+ rating",
        why,
        re.IGNORECASE,
    ), f"Old rating template found: {why!r}"
    # Must contain a Mexican restaurant concept
    assert "mexican" in why.lower(), f"Missing Mexican concept: {why!r}"


# ── Constant set sanity ───────────────────────────────────────────────────────


def test_restaurant_compatible_and_non_restaurant_types_disjoint() -> None:
    overlap = _RESTAURANT_COMPATIBLE_TYPES & _NON_RESTAURANT_TYPES
    assert not overlap, (
        f"_RESTAURANT_COMPATIBLE_TYPES and _NON_RESTAURANT_TYPES must be disjoint; "
        f"overlap: {overlap}"
    )
