"""Cross-vertical AI Concierge card display contract tests.

Architecture rescue (2026-05-08): hotels and attractions historically
shipped through legacy ``ConciergeService._to_unified_*`` adapters that
produced 10-point ratings, no ``display`` block, no ``supporting_details``,
no address, and stale "Sample bar research data" disclaimer text.
Restaurants from semantic retrieval already shipped a clean canonical
display contract.

These contract tests are the future-drift gate: every public UI-facing
place card path — restaurants, attractions, hotels, area-like results —
must normalize through ``app.concierge.display_contract`` before
serialization.

Goals:
1. Prove every card type populates ``display`` with the canonical fields.
2. Prove rating is 5-point Google-native, never 10-point.
3. Prove address is present whenever the producer carried it on the card.
4. Prove price normalizes into ``display.display_price`` for hotels too.
5. Prove "Sample bar research data" cannot appear in any visible field.
6. Prove the normalizer is idempotent and lossless.

These tests do NOT depend on Supabase, Anthropic, or any provider env.
"""
from __future__ import annotations

from typing import Any, List

import pytest

from app.concierge.display_contract import (
    NEUTRAL_LIMITED_COVERAGE_LABEL,
    STALE_DISCLAIMER_FRAGMENTS,
    normalize_place_recommendations,
    normalize_unified_card,
)
from app.concierge.contracts import PlaceRecommendationsResponse
from app.models.concierge import (
    ConciergeDisplayFields,
    GoogleVerification,
    PlaceSupportingDetails,
    UnifiedAttractionResult,
    UnifiedHotelResult,
    UnifiedRestaurantResult,
)


# ── Fixtures: representative cards for each vertical ────────────────────────


def _legacy_hotel_card() -> UnifiedHotelResult:
    """A hotel card as the legacy ``_to_unified_hotel`` produced before the rescue.

    No ``display`` block, no ``supporting_details``, no Google verification,
    rating value chosen so a normalizer that does NOT halve a 10-point input
    would visibly fail.
    """
    return UnifiedHotelResult(
        name="Grand Plaza Hotel",
        source="Hotel search",
        area_label="River North",
        stars=4,
        rating=8.4,  # legacy 10-point representation
        price_per_night=275.0,
        maps_link="https://maps.google.com/?q=Grand+Plaza",
        reason="Centrally located in River North; 4-star upscale property",
        ai_score=0.85,
        tags=["Best Value"],
    )


def _legacy_attraction_card() -> UnifiedAttractionResult:
    return UnifiedAttractionResult(
        name="Lakefront Trail",
        source="Attraction database",
        category="park",
        description="Lakefront Trail fits as a park stop around Grant Park.",
        neighborhood="Grant Park",
        rating=8.6,  # legacy 10-point representation
        review_count=4200,
        address="Lakeshore Dr",
        maps_link="https://maps.google.com/?q=Lakefront+Trail",
        ai_score=0.9,
        tags=["Outdoor"],
    )


def _semantic_restaurant_card() -> UnifiedRestaurantResult:
    """A restaurant card as ``semantic_retrieval._entity_to_card`` produces:
    full canonical display contract from a Google-verified place."""
    gv = GoogleVerification(
        provider="google_places",
        provider_place_id="ChIJabc123",
        name="Pizzeria Portofino",
        formatted_address="200 W Erie St, Chicago, IL 60654",
        business_status="OPERATIONAL",
        rating=4.7,
        user_rating_count=2806,
        types=["italian_restaurant", "restaurant"],
        confidence="high",
        score=1.0,
    )
    return UnifiedRestaurantResult(
        name="Pizzeria Portofino",
        source="Google Places",
        cuisine="Italian",
        neighborhood="200 W Erie St, Chicago, IL 60654",
        rating=4.7,
        review_count=2806,
        google_verification=gv,
        verified_place=True,
        primary_reason="Wood-fired Neapolitan pizza in River North.",
        why_pick="Wood-fired Neapolitan pizza in River North.",
        supporting_details=PlaceSupportingDetails(
            why_pick="Wood-fired Neapolitan pizza in River North.",
            meta_line="★ 4.7 (2,806 reviews)",
            address="200 W Erie St, Chicago, IL 60654",
            category_label="Italian",
            price_level="PRICE_LEVEL_MODERATE",
        ),
        display=ConciergeDisplayFields(
            display_name="Pizzeria Portofino",
            display_category="Italian",
            display_meta_line="★ 4.7 (2,806 reviews)",
            display_why="Wood-fired Neapolitan pizza in River North.",
            display_price="$$",
            display_badges=[],
            addability="addable",
            display_why_source="llm_evidence_pack_v2_primary",
            display_why_validated=True,
        ),
        maps_link="https://maps.google.com/?q=Pizzeria+Portofino",
    )


# ── Canonical contract: every card gets a populated `display` block ────────


CARD_BUILDERS = [
    pytest.param(_legacy_hotel_card, "hotel", id="legacy_hotel"),
    pytest.param(_legacy_attraction_card, "attraction", id="legacy_attraction"),
    pytest.param(_semantic_restaurant_card, "restaurant", id="semantic_restaurant"),
]


@pytest.mark.parametrize("build_card,vertical", CARD_BUILDERS)
def test_normalize_populates_canonical_display_block(build_card, vertical):
    card = build_card()
    normalize_unified_card(card, vertical=vertical)

    assert card.display is not None, f"{vertical}: display must be populated"
    assert card.display.display_name == card.name
    assert card.display.display_category, f"{vertical}: display_category must be non-empty"
    # display_why may be empty when the producer had no reason; the contract
    # only requires the field exists and is a string.
    assert isinstance(card.display.display_why, str)
    assert card.display.addability in {"addable", "research_only", "closed"}


@pytest.mark.parametrize("build_card,vertical", CARD_BUILDERS)
def test_normalize_populates_supporting_details(build_card, vertical):
    card = build_card()
    normalize_unified_card(card, vertical=vertical)

    assert card.supporting_details is not None, f"{vertical}: supporting_details must be populated"
    assert card.supporting_details.category_label, f"{vertical}: category_label required"


# ── Rating contract: must be 0-5 Google native, never 10-point ─────────────


@pytest.mark.parametrize("build_card,vertical", CARD_BUILDERS)
def test_normalize_coerces_rating_to_5_point(build_card, vertical):
    card = build_card()
    normalize_unified_card(card, vertical=vertical)

    if card.rating is None:
        pytest.skip("card has no rating to coerce")
    assert 0.0 <= card.rating <= 5.05, (
        f"{vertical}: rating {card.rating} must be on the 0-5 Google scale, "
        "not the legacy 10-point scale"
    )


def test_legacy_hotel_10point_rating_is_halved():
    card = _legacy_hotel_card()  # rating=8.4
    normalize_unified_card(card, vertical="hotel")
    assert card.rating is not None
    assert abs(card.rating - 4.2) < 0.01, f"8.4/10 should normalize to 4.2/5, got {card.rating}"


def test_legacy_attraction_10point_rating_is_halved():
    card = _legacy_attraction_card()  # rating=8.6
    normalize_unified_card(card, vertical="attraction")
    assert card.rating is not None
    assert abs(card.rating - 4.3) < 0.01, f"8.6/10 should normalize to 4.3/5, got {card.rating}"


def test_native_5point_rating_is_preserved():
    card = _semantic_restaurant_card()  # rating=4.7
    normalize_unified_card(card, vertical="restaurant")
    assert card.rating is not None
    assert abs(card.rating - 4.7) < 0.01


# ── Address contract: present when producer had any location signal ────────


def test_hotel_address_falls_back_to_area_label():
    card = _legacy_hotel_card()  # area_label="River North", no formatted_address
    normalize_unified_card(card, vertical="hotel")
    assert card.supporting_details is not None
    assert card.supporting_details.address == "River North"


def test_attraction_address_falls_back_to_neighborhood():
    card = _legacy_attraction_card()
    normalize_unified_card(card, vertical="attraction")
    assert card.supporting_details is not None
    # Producer-supplied address wins over neighborhood when present.
    assert card.supporting_details.address == "Lakeshore Dr"


def test_restaurant_address_uses_google_formatted_address():
    card = _semantic_restaurant_card()
    normalize_unified_card(card, vertical="restaurant")
    assert card.supporting_details is not None
    assert card.supporting_details.address == "200 W Erie St, Chicago, IL 60654"


# ── Price contract: hotels get $NNN/night, restaurants get $-symbol ────────


def test_hotel_price_per_night_renders_in_display_price():
    card = _legacy_hotel_card()  # price_per_night=275
    normalize_unified_card(card, vertical="hotel")
    assert card.display is not None
    assert card.display.display_price == "$275/night"


def test_restaurant_google_price_level_renders_in_display_price():
    card = _semantic_restaurant_card()
    normalize_unified_card(card, vertical="restaurant")
    assert card.display is not None
    assert card.display.display_price == "$$"


def test_hotel_without_price_yields_no_display_price():
    card = _legacy_hotel_card()
    card.price_per_night = None
    normalize_unified_card(card, vertical="hotel")
    assert card.display is not None
    assert card.display.display_price is None


# ── Stale disclaimer cannot appear in any visible field ────────────────────


def test_stale_disclaimer_never_in_card_text_after_normalize_hotel():
    card = UnifiedHotelResult(
        name="Test Hotel",
        source="Sample bar research data · verify hours and current status before booking.",
        area_label="River North",
        rating=4.0,
        reason="A solid pick. Sample bar research data · verify hours and current status before booking.",
        primary_reason="Sample bar research data — old text",
    )
    normalize_unified_card(card, vertical="hotel")

    assert card.source == NEUTRAL_LIMITED_COVERAGE_LABEL
    assert card.display is not None
    for fragment in STALE_DISCLAIMER_FRAGMENTS:
        assert fragment not in (card.display.display_why or "")
        assert fragment not in (card.supporting_details.why_pick or "" if card.supporting_details else "")
        assert fragment not in (card.reason or "")
        assert fragment not in (card.primary_reason or "")
        assert fragment not in (card.source or "")


def test_stale_disclaimer_never_in_card_text_after_normalize_restaurant():
    card = UnifiedRestaurantResult(
        name="Test Bar",
        source="Sample bar research data · verify hours and current status before booking.",
        cuisine="Cocktail Bar",
        rating=4.0,
        summary="Precision cocktails. Sample bar research data · verify hours and current status before booking.",
        primary_reason="Sample bar research data — old text",
    )
    normalize_unified_card(card, vertical="restaurant")

    assert card.source == NEUTRAL_LIMITED_COVERAGE_LABEL
    assert card.display is not None
    for fragment in STALE_DISCLAIMER_FRAGMENTS:
        assert fragment not in (card.display.display_why or "")
        assert fragment not in (card.supporting_details.why_pick or "" if card.supporting_details else "")
        assert fragment not in (card.summary or "")
        assert fragment not in (card.primary_reason or "")
        assert fragment not in (card.source or "")


def test_normalize_response_strips_stale_disclaimer_from_sources_list():
    response = PlaceRecommendationsResponse(
        response="ok",
        intent="hotels",
        sources=[
            "Live search · tavily",
            "Sample bar research data · verify hours and current status before booking.",
        ],
    )
    normalize_place_recommendations(response)
    assert all(
        fragment not in src
        for src in response.sources
        for fragment in STALE_DISCLAIMER_FRAGMENTS
    )
    assert NEUTRAL_LIMITED_COVERAGE_LABEL in response.sources


# ── Idempotency: re-running the normalizer is safe ─────────────────────────


@pytest.mark.parametrize("build_card,vertical", CARD_BUILDERS)
def test_normalize_is_idempotent(build_card, vertical):
    card = build_card()
    normalize_unified_card(card, vertical=vertical)
    snapshot1 = card.model_dump(mode="json")
    normalize_unified_card(card, vertical=vertical)
    snapshot2 = card.model_dump(mode="json")
    assert snapshot1 == snapshot2, f"{vertical}: normalizer is not idempotent"


# ── Cross-vertical: place_recommendations response level coverage ──────────


def test_place_recommendations_normalizes_all_three_verticals():
    response = PlaceRecommendationsResponse(
        response="hotels and attractions",
        intent="hotels",
        restaurants=[_semantic_restaurant_card()],
        attractions=[_legacy_attraction_card()],
        hotels=[_legacy_hotel_card()],
    )
    normalize_place_recommendations(response)

    # Restaurants: existing display block preserved.
    r = response.restaurants[0]
    assert r.display is not None
    assert r.display.display_why_validated is True
    assert r.rating == pytest.approx(4.7)

    # Attractions: legacy producer left no display — normalizer must populate.
    a = response.attractions[0]
    assert a.display is not None
    assert a.display.display_name == "Lakefront Trail"
    assert a.display.display_category, "attraction display_category required"
    assert a.rating == pytest.approx(4.3, abs=0.01), (
        f"attraction rating must be 5-point: got {a.rating}"
    )

    # Hotels: legacy producer left no display — normalizer must populate.
    h = response.hotels[0]
    assert h.display is not None
    assert h.display.display_name == "Grand Plaza Hotel"
    assert h.display.display_category.startswith("4-star")
    assert h.rating == pytest.approx(4.2, abs=0.01), (
        f"hotel rating must be 5-point: got {h.rating}"
    )
    assert h.display.display_price == "$275/night"
    assert h.supporting_details is not None
    assert h.supporting_details.address == "River North"


# ── Adversarial: legacy concierge.py producers wired through normalizer ────


def _make_search_hotel(rating: float, price: float, name: str = "Test Hotel") -> Any:
    """Mimic the duck-typed object returned by SearchService.search_hotels."""
    from types import SimpleNamespace
    return SimpleNamespace(
        name=name,
        location="River North",
        tags=["Best Value"],
        ai_score=0.85,
        area_label="River North",
        stars=4,
        price_per_night=price,
        rating=rating,
        num_reviews=1200,
        proximity_label=None,
        savings_vs_best=None,
        booking_options=[],
    )


def _make_search_attraction(rating: float, name: str = "Test Park") -> Any:
    from types import SimpleNamespace
    return SimpleNamespace(
        name=name,
        location="Grant Park",
        category="park",
        tags=["Outdoor"],
        ai_score=0.9,
        rating=rating,
        num_reviews=4200,
        address="Lakeshore Dr",
        description=None,
        duration_minutes=90,
        price_level=0,
    )


def test_legacy_to_unified_hotel_emits_5point_rating_directly():
    """The legacy producer must no longer double Google's 0-5 rating to 0-10."""
    from app.services.concierge import ConciergeService

    # bypass __init__ — _to_unified_hotel does not need self._db
    service = object.__new__(ConciergeService)
    raw = _make_search_hotel(rating=4.2, price=275.0)
    card = service._to_unified_hotel(raw)
    assert card.rating == pytest.approx(4.2)
    # display contract populated by the producer itself (defense-in-depth
    # alongside the response-boundary normalizer)
    assert card.display is not None
    assert card.display.display_price == "$275/night"
    assert card.supporting_details is not None
    assert card.supporting_details.address == "River North"
    # No stale disclaimer text in source/reason
    for fragment in STALE_DISCLAIMER_FRAGMENTS:
        assert fragment not in (card.source or "")
        assert fragment not in (card.reason or "")


def test_legacy_to_unified_attraction_emits_5point_rating_directly():
    from app.services.concierge import ConciergeService

    service = object.__new__(ConciergeService)
    raw = _make_search_attraction(rating=4.3)
    card = service._to_unified_attraction(raw, destination="Chicago")
    assert card.rating == pytest.approx(4.3)
    assert card.display is not None
    assert card.display.display_category, "attraction display_category required"
    assert card.supporting_details is not None
    assert card.supporting_details.address == "Lakeshore Dr"


# ── Sample-data fallback no longer leaks the stale disclaimer ───────────────


def test_sample_nightlife_results_no_longer_emit_stale_disclaimer():
    """The Chicago-only sample fallback must not surface the stale text.

    Even though the fallback is itself a documented project-invariant smell
    (hard-coded venues), it remains in the codebase for now as a safety net
    when no nightlife data is available.  After the rescue, the text it
    emits MUST go through the canonical neutral label.
    """
    from app.services.concierge import ConciergeService

    service = object.__new__(ConciergeService)
    cards = service._sample_nightlife_results("Chicago")
    for card in cards:
        for fragment in STALE_DISCLAIMER_FRAGMENTS:
            assert fragment not in (card.source or ""), (
                f"sample card source still contains stale fragment: {card.source!r}"
            )
            assert fragment not in (card.summary or ""), (
                f"sample card summary still contains stale fragment: {card.summary!r}"
            )


# ── Repository-wide leak guard: no stale disclaimer in production code ──────


def test_stale_disclaimer_not_in_production_code() -> None:
    """No production .py file (excluding the normalizer's scrub list and
    legacy-cleanup tests) may carry the stale disclaimer string.

    The display_contract module deliberately holds the fragments to scrub;
    test files are exempt because they may need to construct adversarial
    input proving cleanup works.
    """
    import pathlib

    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    backend_app = repo_root / "backend" / "app"
    frontend_src = repo_root / "frontend" / "src"

    allowed_files = {
        backend_app / "concierge" / "display_contract.py",
    }

    leaks: List[str] = []
    for root in (backend_app, frontend_src):
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in {".py", ".ts", ".tsx", ".js"}:
                continue
            if path in allowed_files:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for fragment in STALE_DISCLAIMER_FRAGMENTS:
                if fragment in text:
                    leaks.append(f"{path.relative_to(repo_root)}: {fragment!r}")

    assert not leaks, (
        "Stale disclaimer fragments leaked into production code:\n"
        + "\n".join(leaks)
    )
