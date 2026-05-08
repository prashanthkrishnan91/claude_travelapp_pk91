"""Sev 1 catastrophic fix regression tests — PR #284.

Covers all four catastrophic failure modes observed in production after PR #283:

  1. Modifier-only follow-ups (e.g. "show only casual") routing as fresh provider
     search instead of refine_previous/modifier_filter context reuse.
  2. Non-restaurant clothing/store entities appearing in restaurant results
     (e.g. "Only One Boutique" womens_clothing_store).
  3. Fabricated category labels ("Only Restaurant", "Casual Restaurant") from
     _derive_display_category using modifier/command words as concept prefix.
  4. Set-writer exceeding production cap (set_writer_ms=6043 despite SDK timeout).

Additionally covers:
  - "casual" and "upscale" in normalized_soft_preferences for ranker integration.
  - modifier_filter context reuse telemetry.
  - display_why/display_why_source/display_why_validated API contract never broken.
  - Legitimate entities (restaurants, cafes, bars) still pass the entity type gate.
"""

from __future__ import annotations

import os
import sys
import types
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

# ── Minimal module stubs so imports work without the full app stack ────────────

for _mod in ["fastapi", "supabase", "anthropic"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

for _mod in ["app.core", "app.core.config", "app.core.deps"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = types.ModuleType(_mod)

if not hasattr(sys.modules["app.core.config"], "get_settings"):
    sys.modules["app.core.config"].get_settings = lambda: MagicMock()

# ── Imports under test ─────────────────────────────────────────────────────────

from app.concierge.context import (
    ContextWindow,
    classify_turn,
)
from app.concierge.context_resolver import (
    _card_passes_trust_gate,
    _detect_modifier_intent,
    _reorder_for_modifier,
    resolve_refine_previous,
    RefineResolved,
)
from app.concierge.frame_extractor import (
    _FILLER_WORDS,
    extract_frame,
)
from app.concierge.semantic_retrieval import (
    _CONCEPT_LABEL_BLOCKLIST,
    _derive_display_category,
    _is_food_incompatible_entity,
)

FAKE_TRIP_ID = UUID("00000000-0000-0000-0000-000000000099")


# ── Helpers ────────────────────────────────────────────────────────────────────


def _ctx(n: int = 5) -> ContextWindow:
    return ContextWindow(trip_id=FAKE_TRIP_ID, card_pool_size=n, has_prior_cards=n > 0)


def _ctx_no_cards() -> ContextWindow:
    return ContextWindow(trip_id=FAKE_TRIP_ID, card_pool_size=0, has_prior_cards=False)


def _verified_card(
    name: str = "Test Place",
    place_id: str = "ChIJtest1",
    maps_uri: str = "https://maps.google.com/?cid=1",
    types: Optional[List[str]] = None,
    price_level: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a minimal verified_place card that passes _card_passes_trust_gate."""
    gv: Dict[str, Any] = {
        "business_status": "OPERATIONAL",
        "provider_place_id": place_id,
        "google_maps_uri": maps_uri,
        "types": types or ["restaurant", "food"],
    }
    if price_level:
        gv["types"] = (types or ["restaurant", "food"]) + [price_level]
    return {
        "type": "verified_place",
        "name": name,
        "google_verification": gv,
    }


def _prior_card_pool(cards: List[Dict[str, Any]], intent: str = "restaurants") -> Dict[str, Any]:
    return {"restaurants": cards, "attractions": [], "hotels": [], "intent": intent}


def _ctx_with_pool(cards: List[Dict[str, Any]], intent: str = "restaurants") -> ContextWindow:
    pool = _prior_card_pool(cards, intent)
    return ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=len(cards),
        has_prior_cards=len(cards) > 0,
        prior_card_pool=pool,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Section 1: Modifier-only follow-up routing
# "show only casual" must route as refine_previous/modifier_filter, NOT new_search
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "query",
    [
        "show only casual",
        "only casual",
        "just casual ones",
        "more casual",
        "less fancy",
        "make it cheaper",
        "show cheaper ones",
        "more affordable",
        "fancier ones",
        "less expensive",
        "upscale",
        "more upscale",
        "casual",
    ],
)
def test_modifier_only_routes_as_refine_previous(query: str) -> None:
    """Modifier-only follow-ups must route as refine_previous/modifier_filter."""
    mode, rule = classify_turn(query, _ctx(5))
    assert mode == "refine_previous", (
        f"query={query!r}: expected refine_previous, got {mode!r}"
    )
    assert rule == "modifier_filter", (
        f"query={query!r}: expected modifier_filter, got {rule!r}"
    )


@pytest.mark.parametrize(
    "query",
    [
        "show only casual",
        "only casual",
        "just casual ones",
    ],
)
def test_modifier_only_no_cards_falls_to_new_search(query: str) -> None:
    """Modifier-only follow-ups without prior cards must fall back to new_search."""
    mode, _rule = classify_turn(query, _ctx_no_cards())
    assert mode == "new_search", (
        f"query={query!r} (no prior cards): expected new_search, got {mode!r}"
    )


@pytest.mark.parametrize(
    "query",
    [
        "casual restaurants",
        "casual restaurants in Chicago",
        "more casual bars",
        "fancy cocktail bars",
    ],
)
def test_modifier_with_venue_category_stays_new_search(query: str) -> None:
    """Queries containing venue category words must NOT route as modifier_filter."""
    mode, _rule = classify_turn(query, _ctx(5))
    assert mode == "new_search", (
        f"query={query!r}: should be new_search (has venue category), got {mode!r}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Section 2: "only" and modifier words NEVER become a concept/venue head
# This prevents the Google query "Only restaurants in X" being issued
# ══════════════════════════════════════════════════════════════════════════════


def test_only_is_in_filler_words() -> None:
    """'only' must be in _FILLER_WORDS so it is never extracted as a venue concept."""
    assert "only" in _FILLER_WORDS, "'only' must be in _FILLER_WORDS"


@pytest.mark.parametrize("word", ["only", "just", "make", "filter", "switch", "change"])
def test_refinement_command_words_in_filler_words(word: str) -> None:
    assert word in _FILLER_WORDS, f"refinement command word {word!r} must be in _FILLER_WORDS"


def test_show_only_casual_produces_no_only_concept() -> None:
    """'show only casual' must not extract 'only' as a primary concept."""
    frame = extract_frame("show only casual", "Chicago")
    concept_labels = [c.label.lower() for c in (frame.subtype_concepts or [])]
    assert "only" not in concept_labels, (
        f"'only' must not appear as a concept label; got concepts={concept_labels}"
    )


def test_only_not_concept_label_for_modifier_query() -> None:
    """The concept label 'only' must not appear for any variant of the query."""
    for q in ("show only casual", "only casual ones", "only"):
        frame = extract_frame(q, "Chicago")
        labels = [c.label.lower() for c in (frame.subtype_concepts or [])]
        assert "only" not in labels, f"query={q!r}: 'only' must not be a concept label"


# ══════════════════════════════════════════════════════════════════════════════
# Section 3: Fabricated category labels must not be produced
# _derive_display_category must never return "Only Restaurant" or "Casual Restaurant"
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("word", ["only", "just", "casual", "fancy", "cheap", "cheaper", "more", "less", "make", "filter", "show"])
def test_concept_label_blocklist_contains_modifier_words(word: str) -> None:
    """Modifier/command words must be in the concept label blocklist."""
    assert word in _CONCEPT_LABEL_BLOCKLIST, (
        f"{word!r} must be in _CONCEPT_LABEL_BLOCKLIST to prevent fabricated labels"
    )


@pytest.mark.parametrize(
    ("types", "primary_type", "concept_label", "forbidden_prefix"),
    [
        (["restaurant", "food"], "restaurant", "only", "Only"),
        (["restaurant", "food"], "restaurant", "casual", "Casual"),
        (["restaurant", "food"], "restaurant", "just", "Just"),
        (["restaurant", "food"], "restaurant", "make", "Make"),
        (["restaurant", "food"], "restaurant", "filter", "Filter"),
    ],
)
def test_derive_display_category_blocklisted_concept_returns_safe_fallback(
    types: List[str],
    primary_type: str,
    concept_label: str,
    forbidden_prefix: str,
) -> None:
    """When concept label is a modifier/command word, category must fall back to 'Restaurant'."""
    # _derive_display_category takes a plain string for concept_label
    result = _derive_display_category(types, primary_type, concept_label)
    assert not result.startswith(forbidden_prefix), (
        f"concept_label={concept_label!r}: must not produce category starting with "
        f"{forbidden_prefix!r}, got {result!r}"
    )
    assert result != "Only Restaurant", f"Must not produce 'Only Restaurant', got {result!r}"
    assert result != "Casual Restaurant", f"Must not produce 'Casual Restaurant', got {result!r}"


def test_derive_display_category_safe_with_none_concept() -> None:
    """None concept must return a safe category string."""
    result = _derive_display_category(["restaurant", "food"], "restaurant", None)
    assert isinstance(result, str)
    assert len(result) > 0


def test_derive_display_category_legitimate_concept_preserved() -> None:
    """Legitimate concepts like 'Mediterranean' must produce a label when types are generic."""
    # Use generic types so type map doesn't match, forcing the concept fallback path
    result = _derive_display_category(["establishment", "point_of_interest"], None, "Mediterranean")
    assert "Mediterranean" in result, (
        f"Legitimate concept 'Mediterranean' should appear in category, got {result!r}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Section 4: Entity type gate — clothing/retail stores rejected from restaurant results
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "types",
    [
        ["womens_clothing_store"],
        ["clothing_store"],
        ["mens_clothing_store"],
        ["shoe_store"],
        ["boutique"],
        ["department_store"],
        ["jewelry_store"],
        ["clothing_store", "store"],
        ["womens_clothing_store", "boutique"],
    ],
)
def test_clothing_and_retail_types_are_food_incompatible(types: List[str]) -> None:
    """Clothing/retail entities with no food-compatible types must be rejected."""
    assert _is_food_incompatible_entity(types), (
        f"types={types} should be food-incompatible (entity type gate must reject)"
    )


@pytest.mark.parametrize(
    "types",
    [
        ["restaurant", "food"],
        ["cafe", "food"],
        ["coffee_shop"],
        ["bar", "food"],
        ["bakery"],
        ["cocktail_bar", "bar", "food"],
        ["fine_dining_restaurant", "restaurant"],
        ["pizza_restaurant", "restaurant", "food"],
        ["fast_food_restaurant", "food"],
    ],
)
def test_food_compatible_types_pass_entity_gate(types: List[str]) -> None:
    """Restaurant/cafe/bar entities must NOT be rejected by the entity type gate."""
    assert not _is_food_incompatible_entity(types), (
        f"types={types} should pass entity gate (food-compatible)"
    )


def test_clothing_with_food_type_passes_gate() -> None:
    """An entity that has both clothing_store AND restaurant (hybrid) should pass."""
    types = ["clothing_store", "restaurant", "food"]
    assert not _is_food_incompatible_entity(types), (
        "Hybrid entity with food-compatible type must pass entity gate"
    )


def test_only_one_boutique_would_be_rejected() -> None:
    """Simulate 'Only One Boutique' (womens_clothing_store) — must be rejected."""
    only_one_boutique_types = ["womens_clothing_store", "boutique", "store", "point_of_interest", "establishment"]
    assert _is_food_incompatible_entity(only_one_boutique_types), (
        "'Only One Boutique' style entity must be rejected by entity type gate"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Section 5: modifier_filter context reuse — prior cards reused without provider call
# ══════════════════════════════════════════════════════════════════════════════


def test_modifier_filter_resolves_from_prior_pool() -> None:
    """modifier_filter rule must resolve from prior pool (no provider call)."""
    cards = [
        _verified_card("Aba", "ChIJ1", types=["fine_dining_restaurant", "restaurant"], price_level="PRICE_LEVEL_EXPENSIVE"),
        _verified_card("Do-Rite Donuts", "ChIJ2", types=["fast_food_restaurant", "food"]),
        _verified_card("Cafe Gelato", "ChIJ3", types=["cafe", "coffee_shop"]),
    ]
    ctx = _ctx_with_pool(cards)
    result = resolve_refine_previous(ctx, "modifier_filter", "show only casual")
    assert result is not None, "modifier_filter must resolve from prior pool"
    assert isinstance(result, RefineResolved)
    assert result.pool_size_after == 3, "All cards kept (modifier_filter never drops)"
    assert result.rerank_rule == "modifier_filter"


def test_modifier_filter_casual_reorders_fine_dining_last() -> None:
    """Casual modifier_filter must push fine-dining/expensive cards toward the back."""
    fine_dining = _verified_card(
        "Fine Dining Place", "ChIJfine",
        types=["fine_dining_restaurant", "restaurant", "food", "PRICE_LEVEL_VERY_EXPENSIVE"],
    )
    casual_cafe = _verified_card(
        "Casual Cafe", "ChIJcafe",
        types=["cafe", "coffee_shop", "PRICE_LEVEL_INEXPENSIVE"],
    )
    cards = [fine_dining, casual_cafe]
    ctx = _ctx_with_pool(cards)
    result = resolve_refine_previous(ctx, "modifier_filter", "show only casual")
    assert result is not None
    # Casual cafe should be surfaced first
    all_cards = result.restaurants + result.attractions + result.hotels
    assert len(all_cards) == 2
    first_name = all_cards[0]["name"]
    assert first_name == "Casual Cafe", (
        f"Casual modifier should surface casual cafe first, got {first_name!r}"
    )


def test_modifier_filter_no_prior_pool_returns_none() -> None:
    """modifier_filter with no prior pool must return None (fall-through to provider)."""
    ctx = _ctx(5)  # has_prior_cards=True but no prior_card_pool
    ctx.prior_card_pool = None
    result = resolve_refine_previous(ctx, "modifier_filter", "show only casual")
    assert result is None, "No prior pool → must return None (provider call needed)"


def test_modifier_filter_all_trust_gate_failures_returns_none() -> None:
    """modifier_filter when all cards fail trust gate must return None."""
    bad_card = {
        "type": "verified_place",
        "name": "Bad Card",
        "google_verification": {
            "business_status": "CLOSED_PERMANENTLY",  # fails trust gate
            "provider_place_id": "ChIJbad",
            "google_maps_uri": "https://maps.google.com/?cid=bad",
        },
    }
    ctx = _ctx_with_pool([bad_card])
    result = resolve_refine_previous(ctx, "modifier_filter", "only casual")
    assert result is None


def test_modifier_filter_provider_call_skipped_telemetry(caplog) -> None:
    """modifier_filter log must contain provider_call_skipped=true telemetry."""
    import logging
    cards = [_verified_card()]
    ctx = _ctx_with_pool(cards)
    with caplog.at_level(logging.INFO, logger="app.concierge.context_resolver"):
        result = resolve_refine_previous(ctx, "modifier_filter", "only casual")
    assert result is not None
    combined = " ".join(r.message for r in caplog.records)
    assert "provider_call_skipped" in combined, (
        "modifier_filter must log provider_call_skipped"
    )
    assert "context_reuse=true" in combined, (
        "modifier_filter must log context_reuse=true"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Section 6: casual/upscale in normalized_soft_preferences
# ══════════════════════════════════════════════════════════════════════════════


def test_casual_soft_pref_extracted_from_casual_query() -> None:
    """'casual' must appear in normalized_soft_preferences for casual queries."""
    frame = extract_frame("casual Mediterranean restaurants", "Chicago")
    assert "casual" in (frame.normalized_soft_preferences or []), (
        f"'casual' must be in normalized_soft_preferences, got {frame.normalized_soft_preferences}"
    )


def test_upscale_soft_pref_extracted_from_upscale_query() -> None:
    """'upscale' must appear in normalized_soft_preferences for upscale queries."""
    frame = extract_frame("upscale restaurants", "Chicago")
    assert "upscale" in (frame.normalized_soft_preferences or []), (
        f"'upscale' must be in normalized_soft_preferences, got {frame.normalized_soft_preferences}"
    )


def test_casual_not_a_concept_for_casual_mediterranean() -> None:
    """'casual Mediterranean restaurants': concept must be 'mediterranean', not 'casual'."""
    frame = extract_frame("casual Mediterranean restaurants", "Chicago")
    concept_labels = [c.label.lower() for c in (frame.subtype_concepts or [])]
    assert "casual" not in concept_labels, (
        f"'casual' must not be a concept label; got {concept_labels}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Section 7: _detect_modifier_intent covers all signal categories
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    ("query", "expected_intent"),
    [
        ("show only casual", "casual"),
        ("only casual", "casual"),
        ("just casual ones", "casual"),
        ("more casual", "casual"),
        ("chill spots", "casual"),
        ("relaxed vibe", "casual"),
        ("less fancy", "formal"),  # "fancy" triggers formal signal (no negation logic)
        ("make it cheaper", "cheap"),
        ("more affordable", "cheap"),
        ("budget options", "cheap"),
        ("inexpensive", "cheap"),
        ("fancy options", "formal"),
        ("fancier", "formal"),
        ("upscale only", "formal"),
        ("fine dining", "formal"),
        ("elegant", "formal"),
        ("pricier options", "expensive"),
        ("luxury", "formal"),  # "luxury" is in both formal+expensive; formal checked first
        ("splurge", "expensive"),
        ("something generic", "none"),
    ],
)
def test_detect_modifier_intent(query: str, expected_intent: str) -> None:
    intent = _detect_modifier_intent(query)
    assert intent == expected_intent, (
        f"query={query!r}: expected modifier_intent={expected_intent!r}, got {intent!r}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Section 8: Trust gate contract
# ══════════════════════════════════════════════════════════════════════════════


def test_trust_gate_passes_valid_card() -> None:
    card = _verified_card()
    assert _card_passes_trust_gate(card)


@pytest.mark.parametrize(
    "mutation",
    [
        {"type": "unverified_place"},
        {"google_verification": None},
        {"google_verification": {"business_status": "CLOSED_PERMANENTLY", "provider_place_id": "x", "google_maps_uri": "y"}},
        {"google_verification": {"business_status": "OPERATIONAL", "provider_place_id": "", "google_maps_uri": "y"}},
        {"google_verification": {"business_status": "OPERATIONAL", "provider_place_id": "x", "google_maps_uri": ""}},
    ],
)
def test_trust_gate_rejects_invalid_card(mutation: Dict[str, Any]) -> None:
    card = _verified_card()
    card.update(mutation)
    if "google_verification" in mutation and mutation["google_verification"] is not None:
        card["google_verification"] = mutation["google_verification"]
    assert not _card_passes_trust_gate(card), f"Should fail trust gate: {mutation}"


# ══════════════════════════════════════════════════════════════════════════════
# Section 9: display_why API contract — ConciergeDisplayFields has required fields
# display_why_source must never be absent; display_why_validated must be bool
# ══════════════════════════════════════════════════════════════════════════════


def test_display_fields_model_has_display_why_source() -> None:
    """ConciergeDisplayFields must define display_why_source field."""
    from app.models.concierge import ConciergeDisplayFields
    fields = ConciergeDisplayFields.model_fields
    assert "display_why_source" in fields, (
        "ConciergeDisplayFields must have display_why_source field (API contract)"
    )


def test_display_fields_model_has_display_why_validated() -> None:
    """ConciergeDisplayFields must define display_why_validated field."""
    from app.models.concierge import ConciergeDisplayFields
    fields = ConciergeDisplayFields.model_fields
    assert "display_why_validated" in fields, (
        "ConciergeDisplayFields must have display_why_validated field (API contract)"
    )


def test_display_fields_model_has_display_why() -> None:
    """ConciergeDisplayFields must define display_why field."""
    from app.models.concierge import ConciergeDisplayFields
    fields = ConciergeDisplayFields.model_fields
    assert "display_why" in fields, (
        "ConciergeDisplayFields must have display_why field (API contract)"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Section 10: Set-writer wall-clock timeout — timeout returns None without crash
# ══════════════════════════════════════════════════════════════════════════════


def test_set_writer_wall_clock_timeout_returns_none() -> None:
    """Wall-clock timeout on set-writer must return None without raising."""
    import concurrent.futures

    from app.concierge.set_level_writer import _call_set_writer_llm

    def _slow_inner(*args, **kwargs):
        import time
        time.sleep(10)  # simulate stuck LLM call
        return ("text", {})

    with patch("app.concierge.set_level_writer._call_set_writer_llm_inner", side_effect=_slow_inner):
        # Use 0.1s cap — should time out quickly
        result, tel = _call_set_writer_llm("prompt text", timeout_s=0.1)
        assert result is None, "Timed-out set-writer must return None, not raise"
        assert tel.get("llm_error") is not None, "Timed-out call must record llm_error in telemetry"


def test_set_writer_wall_clock_timeout_telemetry_has_error_field() -> None:
    """Telemetry from wall-clock timeout must contain llm_error field."""
    from app.concierge.set_level_writer import _call_set_writer_llm

    def _stuck(*args, **kwargs):
        import time
        time.sleep(10)

    with patch("app.concierge.set_level_writer._call_set_writer_llm_inner", side_effect=_stuck):
        _raw, tel = _call_set_writer_llm("prompt", timeout_s=0.05)
        assert "llm_error" in tel
        assert "wall_clock_timeout" in tel["llm_error"]


# ══════════════════════════════════════════════════════════════════════════════
# Section 11: End-to-end routing invariant — "show only casual" must never
#             produce a Google provider search for "Only" as a query term
# ══════════════════════════════════════════════════════════════════════════════


def test_show_only_casual_routes_to_modifier_filter_not_new_search() -> None:
    """Production regression: 'show only casual' must NOT trigger new provider search."""
    ctx = _ctx(6)
    mode, rule = classify_turn("show only casual", ctx)
    # Must be refine_previous with modifier_filter (no provider call)
    assert mode == "refine_previous"
    assert rule == "modifier_filter"


def test_show_only_casual_does_not_extract_only_as_frame_concept() -> None:
    """The word 'only' must never become a subtype concept in the frame."""
    frame = extract_frame("show only casual", "Chicago")
    labels = {c.label.lower() for c in (frame.subtype_concepts or [])}
    assert "only" not in labels


def test_show_only_casual_does_not_produce_only_restaurant_category() -> None:
    """No amount of 'show only casual' processing must produce an 'Only Restaurant' label."""
    category = _derive_display_category(["restaurant", "food"], "restaurant", "only")
    assert "Only" not in category
    assert category != "Only Restaurant"


# ══════════════════════════════════════════════════════════════════════════════
# Section 12: Classifier backward-compat — existing refine/new_search unaffected
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    ("query", "has_cards", "expected_mode", "expected_rule"),
    [
        # Refine paths still work
        ("top 3", True, "refine_previous", "top_n"),
        ("top three", True, "refine_previous", "top_n"),
        ("best one", True, "refine_previous", "best_one"),
        ("compare these", True, "refine_previous", "compare"),
        ("compare them", True, "refine_previous", "compare"),
        # New-search paths still work
        ("cocktail bars in Wicker Park", True, "new_search", "none"),
        ("ramen in Shibuya", True, "new_search", "none"),
        ("more options", True, "new_search", "none"),
        ("things to do tomorrow", True, "new_search", "none"),
        # No cards → new search
        ("top 3", False, "new_search", "none"),
        ("show only casual", False, "new_search", "none"),
    ],
)
def test_classifier_backward_compat(
    query: str, has_cards: bool, expected_mode: str, expected_rule: str
) -> None:
    ctx = _ctx(5) if has_cards else _ctx_no_cards()
    mode, rule = classify_turn(query, ctx)
    assert mode == expected_mode, (
        f"query={query!r} has_cards={has_cards}: expected mode={expected_mode!r}, got {mode!r}"
    )
    assert rule == expected_rule, (
        f"query={query!r} has_cards={has_cards}: expected rule={expected_rule!r}, got {rule!r}"
    )
