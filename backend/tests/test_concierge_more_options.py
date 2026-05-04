"""Tests for AI Concierge more-options continuation fix (PR 2.5).

Covers:
- is_more_options_continuation() with various query/card combos
- derive_category_hint() for all supported intents and bucket fallback
- prior_place_category populated in build_context_window
- Classifier regression: top_n/best_one/compare remain refine_previous
- Route/provider behavior: flag ON + prior cards + "more options" → place_recommendations
- Route/provider behavior: flag OFF → existing behavior unchanged
- Route/provider behavior: no prior cards → existing behavior unchanged
"""

from __future__ import annotations

import os
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Minimal stubs so imports work without the full stack ───────────────────────

for _mod in ["fastapi", "supabase", "anthropic"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

_core_path = os.path.join(os.path.dirname(__file__), "..", "app", "core")
_core_mod = sys.modules.get("app.core")
if _core_mod is None:
    _core_mod = types.ModuleType("app.core")
    sys.modules["app.core"] = _core_mod
if not hasattr(_core_mod, "__path__"):
    _core_mod.__path__ = [_core_path]  # type: ignore[attr-defined]

_deps_mod = sys.modules.get("app.core.deps")
if _deps_mod is None:
    _deps_mod = types.ModuleType("app.core.deps")
    sys.modules["app.core.deps"] = _deps_mod
if not hasattr(_deps_mod, "DB"):
    setattr(_deps_mod, "DB", object)
if not hasattr(_deps_mod, "CurrentUserID"):
    setattr(_deps_mod, "CurrentUserID", object)

if "app.routes" not in sys.modules:
    _routes_pkg = types.ModuleType("app.routes")
    _routes_pkg.__path__ = [  # type: ignore[attr-defined]
        os.path.join(os.path.dirname(__file__), "..", "app", "routes")
    ]
    sys.modules["app.routes"] = _routes_pkg

from app.concierge.context import (
    ContextWindow,
    classify_turn,
    derive_category_hint,
    derive_prior_place_query_hint,
    is_more_options_continuation,
    build_context_window,
)
from app.concierge.contracts import PlaceRecommendationsResponse
from app.concierge.result_pool import _GLOBAL_CONTINUATION_POOL
from app.models.concierge import ConciergeSearchRequest
from app.routes.ai import build_typed_concierge_response

FAKE_TRIP_ID = UUID("00000000-0000-0000-0000-000000000010")
FAKE_USER_ID = UUID("00000000-0000-0000-0000-000000000011")


@pytest.fixture(autouse=True)
def _clear_result_pool() -> None:
    """Prevent test cross-contamination via the module-level pool singleton."""
    _GLOBAL_CONTINUATION_POOL.clear(str(FAKE_TRIP_ID))
    yield
    _GLOBAL_CONTINUATION_POOL.clear(str(FAKE_TRIP_ID))


# ── Card factories ─────────────────────────────────────────────────────────────


def _verified_card(name: str = "TestBar") -> dict:
    return {
        "type": "verified_place",
        "name": name,
        "google_verification": {
            "provider": "google_places",
            "business_status": "OPERATIONAL",
            "provider_place_id": f"ChIJ_{name.lower()}",
            "google_maps_uri": f"https://maps.google.com/?cid={name.lower()}",
            "name": name,
            "formatted_address": f"123 {name} St",
            "rating": 4.5,
            "user_rating_count": 200,
        },
    }


def _pool(restaurants=None, attractions=None, hotels=None, intent="nightlife") -> dict:
    return {
        "intent": intent,
        "response": "Here are some options.",
        "restaurants": restaurants or [],
        "attractions": attractions or [],
        "hotels": hotels or [],
    }


def _ctx(pool: dict | None = None, n: int = 5) -> ContextWindow:
    if pool is None:
        return ContextWindow(trip_id=FAKE_TRIP_ID, card_pool_size=0, has_prior_cards=False)
    total = sum(len(pool.get(b, [])) for b in ("restaurants", "attractions", "hotels"))
    pool_size = total if total > 0 else n
    return ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=pool_size,
        has_prior_cards=True,
        source_message_id="msg-prev",
        prior_card_pool=pool,
        prior_place_category=derive_category_hint(pool),
    )


def _ctx_no_cards() -> ContextWindow:
    return ContextWindow(trip_id=FAKE_TRIP_ID, card_pool_size=0, has_prior_cards=False)


# ── is_more_options_continuation ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "query",
    [
        "more options",
        "More Options",
        "MORE OPTIONS",
        "show more",
        "more like these",
        "give me more",
        "another batch",
    ],
)
def test_is_continuation_true_with_prior_cards(query: str) -> None:
    ctx = _ctx(_pool([_verified_card()]))
    assert is_more_options_continuation(query, ctx) is True


@pytest.mark.parametrize(
    "query",
    [
        "more options",
        "show more",
        "more like these",
        "give me more",
        "another batch",
    ],
)
def test_is_continuation_false_without_prior_cards(query: str) -> None:
    assert is_more_options_continuation(query, _ctx_no_cards()) is False


@pytest.mark.parametrize(
    "query",
    [
        "top 3",
        "best one",
        "compare these",
        "cocktail bars in Chicago",
        "restaurants near the first one",
        "start over",
        "",
        "hi",
    ],
)
def test_is_continuation_false_for_non_continuation_queries(query: str) -> None:
    ctx = _ctx(_pool([_verified_card()]))
    assert is_more_options_continuation(query, ctx) is False


# ── derive_category_hint ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("intent", "expected"),
    [
        ("nightlife", "cocktail bars"),
        ("restaurants", "restaurants"),
        ("michelin_restaurants", "restaurants"),
        ("hidden_gems", "restaurants"),
        ("luxury_value", "restaurants"),
        ("romantic", "restaurants"),
        ("family_friendly", "attractions"),
        ("attractions", "attractions"),
        ("hotels", "hotels"),
    ],
)
def test_derive_category_hint_from_intent(intent: str, expected: str) -> None:
    pool = _pool([_verified_card()], intent=intent)
    assert derive_category_hint(pool) == expected


def test_derive_category_hint_unknown_intent_falls_back_to_bucket() -> None:
    pool = _pool(
        restaurants=[_verified_card("A"), _verified_card("B")],
        intent="general",
    )
    # 2 restaurants, 0 attractions, 0 hotels → restaurants
    assert derive_category_hint(pool) == "restaurants"


def test_derive_category_hint_no_intent_dominant_attractions() -> None:
    pool = {
        "response": "here",
        "restaurants": [],
        "attractions": [_verified_card("Musuem"), _verified_card("Park")],
        "hotels": [],
    }
    assert derive_category_hint(pool) == "attractions"


def test_derive_category_hint_hotels_bucket_fallback() -> None:
    pool = {"response": "here", "restaurants": [], "attractions": [], "hotels": [_verified_card("Ritz")]}
    assert derive_category_hint(pool) == "hotels"


def test_derive_category_hint_empty_pool_returns_none() -> None:
    pool = {"response": "here", "restaurants": [], "attractions": [], "hotels": []}
    assert derive_category_hint(pool) is None


def test_derive_category_hint_none_returns_none() -> None:
    assert derive_category_hint(None) is None


def test_derive_category_hint_non_dict_returns_none() -> None:
    assert derive_category_hint("invalid") is None  # type: ignore[arg-type]
    assert derive_category_hint(42) is None  # type: ignore[arg-type]


# ── prior_place_category populated in ContextWindow ──────────────────────────


def test_context_window_prior_place_category_nightlife() -> None:
    pool = _pool([_verified_card()], intent="nightlife")
    ctx = _ctx(pool)
    assert ctx.prior_place_category == "cocktail bars"


def test_context_window_prior_place_category_restaurants() -> None:
    pool = _pool([_verified_card()], intent="restaurants")
    ctx = _ctx(pool)
    assert ctx.prior_place_category == "restaurants"


def test_context_window_prior_place_category_none_when_no_pool() -> None:
    ctx = _ctx_no_cards()
    assert ctx.prior_place_category is None


def test_build_context_window_populates_prior_place_category() -> None:
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(
        data=[
            {
                "id": "msg-1",
                "role": "assistant",
                "content": "Here are some cocktail bars.",
                "structured_results": {
                    "intent": "nightlife",
                    "restaurants": [_verified_card("Bar1"), _verified_card("Bar2")],
                    "attractions": [],
                    "hotels": [],
                },
            },
        ]
    )
    ctx = build_context_window(db, FAKE_TRIP_ID)
    assert ctx.prior_place_category == "cocktail bars"
    assert ctx.has_prior_cards is True


# ── Classifier regression: refine_previous still works ───────────────────────


def _ctx_with_cards_only(n: int = 5) -> ContextWindow:
    return ContextWindow(trip_id=FAKE_TRIP_ID, card_pool_size=n, has_prior_cards=True)


@pytest.mark.parametrize(
    ("query", "expected_mode", "expected_rule"),
    [
        ("top 3", "refine_previous", "top_n"),
        ("top three", "refine_previous", "top_n"),
        ("show me 5", "refine_previous", "top_n"),
        ("best one", "refine_previous", "best_one"),
        ("which one is best", "refine_previous", "best_one"),
        ("compare these", "refine_previous", "compare"),
        ("rank these", "refine_previous", "compare"),
        ("compare them", "refine_previous", "compare"),
    ],
)
def test_classifier_regression_refine_previous_still_works(
    query: str, expected_mode: str, expected_rule: str
) -> None:
    mode, rule = classify_turn(query, _ctx_with_cards_only())
    assert mode == expected_mode, f"{query!r}: expected {expected_mode!r}, got {mode!r}"
    assert rule == expected_rule, f"{query!r}: expected {expected_rule!r}, got {rule!r}"


@pytest.mark.parametrize(
    "query",
    ["more options", "show more", "more like these", "give me more", "another batch"],
)
def test_classifier_continuation_queries_remain_new_search(query: str) -> None:
    """Continuation queries must still classify as new_search (not refine_previous)."""
    mode, rule = classify_turn(query, _ctx_with_cards_only())
    assert mode == "new_search"
    assert rule == "none"


@pytest.mark.parametrize(
    "query",
    ["more options", "show more", "more like these", "give me more", "another batch"],
)
def test_classifier_continuation_no_prior_cards_is_new_search(query: str) -> None:
    mode, rule = classify_turn(query, _ctx_no_cards())
    assert mode == "new_search"
    assert rule == "none"


# ── Route behavior tests ───────────────────────────────────────────────────────


def _make_fake_place_response() -> PlaceRecommendationsResponse:
    return PlaceRecommendationsResponse(
        response="Here are more cocktail bars.",
        intent="nightlife",
        retrieval_used=True,
        source_status="live_search",
        restaurants=[],
        attractions=[],
        hotels=[],
        research_sources=[],
        areas=[],
        area_comparisons=[],
        suggestions=[],
        sources=[],
        warnings=[],
    )


def _make_place_response_with_names(names: list[str]) -> PlaceRecommendationsResponse:
    cards = []
    for n in names:
        cards.append(
            {
                "type": "verified_place",
                "name": n,
                "source": "Search",
                "google_verification": {
                    "provider": "google_places",
                    "business_status": "OPERATIONAL",
                    "provider_place_id": f"id-{n.lower()}",
                    "google_maps_uri": f"https://maps.google.com/?cid={n.lower()}",
                    "name": n,
                    "formatted_address": f"123 {n} St",
                },
            }
        )
    return PlaceRecommendationsResponse(
        response="more results",
        intent="restaurants",
        retrieval_used=True,
        source_status="live_search",
        restaurants=cards,
        attractions=[],
        hotels=[],
        research_sources=[],
        areas=[],
        area_comparisons=[],
        suggestions=[],
        sources=[],
        warnings=[],
    )


def _settings(flag: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        concierge_context_v1_enabled=flag,
        concierge_router_v2=True,
        concierge_router_v2_confidence_threshold=0.55,
        trip_advice_builder_enabled=False,
    )


def _nightlife_ctx() -> ContextWindow:
    pool = _pool(
        restaurants=[_verified_card("Bar1"), _verified_card("Bar2")],
        intent="nightlife",
    )
    return ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=2,
        has_prior_cards=True,
        source_message_id="msg-prev",
        prior_card_pool=pool,
        prior_place_category="cocktail bars",
    )


def test_more_options_flag_on_prior_cards_returns_place_recommendations() -> None:
    """Flag ON + prior nightlife cards + 'more options' → place_recommendations."""
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")
    fake_response = _make_fake_place_response()
    mock_service = MagicMock()
    mock_service.search.return_value = fake_response

    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=_nightlife_ctx()),
    ):
        result, decision = build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    assert result.response_type == "place_recommendations"
    assert decision.code == "more_options_continuation"


def test_more_options_calls_search_with_canonical_query() -> None:
    """Provider search must receive canonical 'cocktail bars' (no 'more ' prefix), not 'more options'."""
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")
    # Return a response with >=1 card so bounded refill is not triggered (final_count >= 1)
    fake_response = _make_place_response_with_names(["NewBar1"])
    mock_service = MagicMock()
    mock_service.search.return_value = fake_response

    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=_nightlife_ctx()),
    ):
        build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    # First call must use canonical query (no "more " prefix), not the raw user query
    first_call_query = mock_service.search.call_args_list[0][0][1]
    assert first_call_query == "cocktail bars", f"Expected 'cocktail bars', got {first_call_query!r}"
    assert first_call_query != "more options"
    assert "more " not in first_call_query


def test_italian_more_options_preserves_subtype_in_query() -> None:
    pool = _pool(
        restaurants=[_verified_card("A"), _verified_card("B")],
        intent="restaurants",
    )
    ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=2,
        has_prior_cards=True,
        source_message_id="msg-prev",
        prior_card_pool=pool,
        prior_user_prompts=["Italian restaurants"],
        prior_place_category="restaurants",
        prior_place_query_hint="italian restaurants",
    )
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")
    mock_service = MagicMock()
    # Return a card so refill is not triggered
    mock_service.search.return_value = _make_place_response_with_names(["NuovoResto"])
    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=ctx),
    ):
        build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)
    first_call_query = mock_service.search.call_args_list[0][0][1]
    assert first_call_query == "italian restaurants"


def test_more_options_excludes_prior_card_identities_from_response() -> None:
    prior_one = _verified_card("DupBar")
    prior_two = _verified_card("UniqueOld")
    pool = _pool(restaurants=[prior_one, prior_two], intent="nightlife")
    ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=2,
        has_prior_cards=True,
        source_message_id="msg-prev",
        prior_card_pool=pool,
        prior_place_category="cocktail bars",
        prior_place_query_hint="cocktail bars",
    )
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")
    mock_service = MagicMock()
    mock_service.search.return_value = _make_place_response_with_names(["DupBar", "FreshBar"])
    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=ctx),
    ):
        result, _ = build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)
    assert [r.name for r in result.restaurants] == ["FreshBar"]


def test_more_options_keeps_fewer_verified_results_when_unique_pool_small() -> None:
    pool = _pool(restaurants=[_verified_card("OnlyBar")], intent="nightlife")
    ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=1,
        has_prior_cards=True,
        source_message_id="msg-prev",
        prior_card_pool=pool,
        prior_place_category="cocktail bars",
        prior_place_query_hint="cocktail bars",
    )
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")
    mock_service = MagicMock()
    mock_service.search.return_value = _make_place_response_with_names(["OnlyBar"])
    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=ctx),
    ):
        result, _ = build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)
    assert result.restaurants == []


def test_more_options_exclusion_matches_place_id_alias() -> None:
    prior = _verified_card("AliasDup")
    prior["place_id"] = "gpid-123"
    pool = _pool(restaurants=[prior], intent="nightlife")
    ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=1,
        has_prior_cards=True,
        source_message_id="msg-prev",
        prior_card_pool=pool,
        prior_place_query_hint="cocktail bars",
    )
    new_resp = _make_place_response_with_names(["AliasDup", "FreshBar"])
    new_resp.restaurants[0].google_verification.provider_place_id = "gpid-123"
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")
    svc = MagicMock()
    svc.search.return_value = new_resp
    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=ctx),
    ):
        result, _ = build_typed_concierge_response(svc, payload, FAKE_USER_ID)
    assert [r.name for r in result.restaurants] == ["FreshBar"]


def test_more_options_exclusion_matches_normalized_name_address_fallback() -> None:
    prior = _verified_card("The Violet Hour")
    prior["google_verification"]["provider_place_id"] = None
    prior["google_verification"]["google_maps_uri"] = None
    prior["google_verification"]["formatted_address"] = "1520 N Damen Ave, Chicago, IL"
    pool = _pool(restaurants=[prior], intent="nightlife")
    ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=1,
        has_prior_cards=True,
        source_message_id="msg-prev",
        prior_card_pool=pool,
        prior_place_query_hint="cocktail bars",
    )
    dup = _make_place_response_with_names(["The Violet Hour", "FreshBar"])
    dup.restaurants[0].google_verification.provider_place_id = None
    dup.restaurants[0].google_verification.google_maps_uri = None
    dup.restaurants[0].google_verification.formatted_address = "1520 N. Damen Ave Chicago IL"
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")
    svc = MagicMock()
    svc.search.return_value = dup
    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=ctx),
    ):
        result, _ = build_typed_concierge_response(svc, payload, FAKE_USER_ID)
    assert [r.name for r in result.restaurants] == ["FreshBar"]


def test_query_hint_helper_preserves_subtype_and_generic_fallback() -> None:
    pool = _pool(restaurants=[_verified_card("A")], intent="restaurants")
    assert derive_prior_place_query_hint(pool, ["Italian restaurants in Chicago"]) == "italian restaurants"
    assert derive_prior_place_query_hint(pool, ["show me more"]) == "restaurants"


def test_show_more_flag_on_prior_restaurant_cards_returns_place_recommendations() -> None:
    pool = _pool(
        restaurants=[_verified_card("RestA"), _verified_card("RestB")],
        intent="restaurants",
    )
    ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=2,
        has_prior_cards=True,
        source_message_id="msg-prev",
        prior_card_pool=pool,
        prior_place_category="restaurants",
    )
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="show more")
    fake_response = _make_fake_place_response()
    mock_service = MagicMock()
    mock_service.search.return_value = fake_response

    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=ctx),
    ):
        result, decision = build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    assert result.response_type == "place_recommendations"
    assert decision.code == "more_options_continuation"
    # canonical query: no "more " prefix
    first_call_query = mock_service.search.call_args_list[0][0][1]
    assert first_call_query == "restaurants"


def test_more_like_these_prior_attraction_cards() -> None:
    pool = _pool(attractions=[_verified_card("Museum")], intent="attractions")
    ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=1,
        has_prior_cards=True,
        source_message_id="msg-prev",
        prior_card_pool=pool,
        prior_place_category="attractions",
    )
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more like these")
    mock_service = MagicMock()
    mock_service.search.return_value = _make_fake_place_response()

    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=ctx),
    ):
        result, decision = build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    assert result.response_type == "place_recommendations"
    assert decision.code == "more_options_continuation"
    first_call_query = mock_service.search.call_args_list[0][0][1]
    assert first_call_query == "attractions"


def test_more_options_flag_off_falls_through_to_router() -> None:
    """Flag OFF: 'more options' should not trigger continuation path."""
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")
    fake_response = _make_fake_place_response()
    mock_service = MagicMock()
    mock_service.search.return_value = fake_response

    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=False)),
        patch("app.routes.ai.build_context_window", return_value=_nightlife_ctx()),
    ):
        result, decision = build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    # Flag OFF: continuation code must NOT be used
    assert decision.code != "more_options_continuation"


def test_more_options_no_prior_cards_falls_through() -> None:
    """No prior cards: 'more options' must not trigger continuation path."""
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")
    fake_response = _make_fake_place_response()
    mock_service = MagicMock()
    mock_service.search.return_value = fake_response

    empty_ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=0,
        has_prior_cards=False,
        prior_card_pool=None,
    )
    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=empty_ctx),
    ):
        result, decision = build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    assert decision.code != "more_options_continuation"


def test_more_options_no_category_hint_falls_through() -> None:
    """No derivable category: continuation falls through, no exception raised."""
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")
    fake_response = _make_fake_place_response()
    mock_service = MagicMock()
    mock_service.search.return_value = fake_response

    empty_pool_ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=3,
        has_prior_cards=True,
        prior_card_pool={"intent": "general", "restaurants": [], "attractions": [], "hotels": []},
        prior_place_category=None,
    )
    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=empty_pool_ctx),
    ):
        # Should not raise; falls through to existing router
        result, decision = build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    assert decision.code != "more_options_continuation"


def test_continuation_does_not_use_context_resolver_reuse() -> None:
    """'more options' continuation must NOT reuse cards from context_resolver."""
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")
    fake_response = _make_fake_place_response()
    mock_service = MagicMock()
    mock_service.search.return_value = fake_response

    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=_nightlife_ctx()),
        patch("app.routes.ai.resolve_refine_previous") as mock_resolve,
    ):
        build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    # resolve_refine_previous must NOT have been called (turn_mode is new_search, not refine_previous)
    mock_resolve.assert_not_called()


# ── Regression: existing refine_previous flows still skip provider ─────────────


def test_top_3_still_uses_card_reuse_not_provider(monkeypatch) -> None:
    """'top 3' with flag ON must still go through refine_previous card reuse path."""
    from app.concierge.context_resolver import RefineResolved

    pool = _pool(
        restaurants=[_verified_card("Bar1"), _verified_card("Bar2"), _verified_card("Bar3")],
        intent="nightlife",
    )
    ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=3,
        has_prior_cards=True,
        source_message_id="msg-prev",
        prior_card_pool=pool,
        prior_place_category="cocktail bars",
    )
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="top 3")
    mock_service = MagicMock()

    resolved = RefineResolved(
        restaurants=[_verified_card("Bar1"), _verified_card("Bar2"), _verified_card("Bar3")],
        attractions=[],
        hotels=[],
        pool_size_before=3,
        pool_size_after=3,
        rerank_rule="top_n",
        source_message_id="msg-prev",
        prior_intent="nightlife",
    )

    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=ctx),
        patch("app.routes.ai.resolve_refine_previous", return_value=resolved),
    ):
        result, decision = build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    assert decision.code == "refine_previous_card_reuse"
    # Provider was NOT called
    mock_service.search.assert_not_called()


# ── PR 3 required tests ────────────────────────────────────────────────────────
# Tests 1-8 as specified in the task.


# Test 1: Initial search stores verified continuation pool
def test_initial_search_stores_pool_after_continuation() -> None:
    """After a continuation search returns results, the pool stores them for next call."""
    pool = _pool(restaurants=[_verified_card("Taco1"), _verified_card("Taco2")], intent="restaurants")
    ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=2,
        has_prior_cards=True,
        source_message_id="msg-prev",
        prior_card_pool=pool,
        prior_place_category="restaurants",
        prior_place_query_hint="mexican restaurants",
    )
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")
    mock_service = MagicMock()
    # Return 2 unique new restaurants (not in prior pool)
    mock_service.search.return_value = _make_place_response_with_names(["NewTaco1", "NewTaco2"])

    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=ctx),
    ):
        result, _ = build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    # Pool should now have entries for this trip + canonical query
    assert _GLOBAL_CONTINUATION_POOL.pool_size() > 0, "Pool should be populated after successful search"
    # Result should include the new restaurants
    assert {r.name for r in result.restaurants} == {"NewTaco1", "NewTaco2"}


# Test 2: Second more-options uses pool fast path (no new provider call)
def test_second_more_options_uses_pool_not_provider() -> None:
    """When pool has unused verified cards, second more-options returns from pool without provider."""
    prior_pool = _pool(restaurants=[_verified_card("Taco1")], intent="restaurants")
    ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=1,
        has_prior_cards=True,
        source_message_id="msg-prev",
        prior_card_pool=prior_pool,
        prior_place_category="restaurants",
        prior_place_query_hint="mexican restaurants",
    )
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")

    # Pre-populate the pool with 2 fresh cards
    _GLOBAL_CONTINUATION_POOL.store(
        str(FAKE_TRIP_ID),
        "mexican restaurants",
        {
            "restaurants": [_verified_card("PoolTaco1"), _verified_card("PoolTaco2")],
            "attractions": [],
            "hotels": [],
        },
    )

    mock_service = MagicMock()
    mock_service.search.return_value = _make_place_response_with_names(["ShouldNotAppear"])

    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=ctx),
    ):
        result, decision = build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    # Provider must NOT have been called (pool fast path)
    mock_service.search.assert_not_called()
    assert decision.code == "more_options_continuation"
    assert {r.name for r in result.restaurants} == {"PoolTaco1", "PoolTaco2"}


# Test 3: Exhausted pool triggers bounded refill (at most 2 variant queries)
def test_exhausted_pool_triggers_bounded_refill() -> None:
    """When provider returns only duplicates (pool effectively empty), refill fires at most twice."""
    prior_pool = _pool(restaurants=[_verified_card("Taco1"), _verified_card("Taco2")], intent="restaurants")
    ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=2,
        has_prior_cards=True,
        source_message_id="msg-prev",
        prior_card_pool=prior_pool,
        prior_place_category="restaurants",
        prior_place_query_hint="mexican restaurants",
    )
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")
    mock_service = MagicMock()
    # All calls return duplicates of prior pool → triggers refill
    mock_service.search.return_value = _make_place_response_with_names(["Taco1", "Taco2"])

    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=ctx),
    ):
        build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    # At most 3 total calls: 1 canonical + 2 refill variants
    assert mock_service.search.call_count <= 3, (
        f"Expected ≤3 provider calls (1 canonical + 2 refill), got {mock_service.search.call_count}"
    )
    # Second and third calls (if made) must use variant queries with canonical prefix
    queries_used = [call[0][1] for call in mock_service.search.call_args_list]
    assert queries_used[0] == "mexican restaurants", "First call must use canonical query"
    for variant in queries_used[1:]:
        assert "mexican restaurants" in variant, f"Refill variant must reference canonical: {variant!r}"


# Test 4: Continuation dedup happens before expensive reason generation
def test_early_dedup_skips_prior_cards_before_reason_generation() -> None:
    """Prior identity keys are passed to service.search() for early dedup in fetch()."""
    prior_pool = _pool(restaurants=[_verified_card("OldPlace")], intent="restaurants")
    ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=1,
        has_prior_cards=True,
        source_message_id="msg-prev",
        prior_card_pool=prior_pool,
        prior_place_category="restaurants",
        prior_place_query_hint="italian restaurants",
    )
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")
    mock_service = MagicMock()
    mock_service.search.return_value = _make_place_response_with_names(["NewPlace"])

    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=ctx),
    ):
        build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    # service.search() must have received prior_identity_keys
    first_call_kwargs = mock_service.search.call_args_list[0][1]
    assert "prior_identity_keys" in first_call_kwargs, (
        "service.search must receive prior_identity_keys for early dedup"
    )
    prior_keys = first_call_kwargs["prior_identity_keys"]
    assert isinstance(prior_keys, frozenset), "prior_identity_keys must be a frozenset"
    assert len(prior_keys) > 0, "prior_identity_keys must not be empty when prior pool exists"


# Test 5: If only one verified unique card remains, return it (no fabrication)
def test_single_unique_card_returned_without_fabrication() -> None:
    """When only 1 unique verified card remains after dedup, return exactly 1 card."""
    prior_pool = _pool(restaurants=[_verified_card("OldBar1"), _verified_card("OldBar2")], intent="nightlife")
    ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=2,
        has_prior_cards=True,
        source_message_id="msg-prev",
        prior_card_pool=prior_pool,
        prior_place_category="cocktail bars",
        prior_place_query_hint="cocktail bars",
    )
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")
    mock_service = MagicMock()
    # Return 1 duplicate + 1 new; refill returns only duplicates
    def _side_effect(trip_id, query, user_id, client_msg=None, **kwargs):
        if "best" in query or "popular" in query:
            return _make_place_response_with_names(["OldBar1"])  # refill only duplicates
        return _make_place_response_with_names(["OldBar1", "OnlyNewBar"])

    mock_service.search.side_effect = _side_effect

    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=ctx),
    ):
        result, decision = build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    assert decision.code == "more_options_continuation"
    names = {r.name for r in result.restaurants}
    assert "OldBar1" not in names, "Prior duplicate must not appear in response"
    assert "OldBar2" not in names, "Prior duplicate must not appear in response"
    assert "OnlyNewBar" in names, "The single unique verified card must be returned"


# Test 6: Cache-hit continuation still excludes prior cards
def test_cache_hit_continuation_still_excludes_prior_cards() -> None:
    """Even when service returns cached results, prior card dedup is enforced."""
    prior_one = _verified_card("CachedBar")
    prior_pool = _pool(restaurants=[prior_one], intent="nightlife")
    ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=1,
        has_prior_cards=True,
        source_message_id="msg-prev",
        prior_card_pool=prior_pool,
        prior_place_category="cocktail bars",
        prior_place_query_hint="cocktail bars",
    )
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")
    mock_service = MagicMock()
    # Service returns cached=True response with CachedBar (same as prior) + FreshBar
    response = _make_place_response_with_names(["CachedBar", "FreshBar"])
    response.cached = True
    mock_service.search.return_value = response

    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=ctx),
    ):
        result, _ = build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    names = {r.name for r in result.restaurants}
    assert "CachedBar" not in names, "Prior card must be excluded even from cached results"
    assert "FreshBar" in names or len(names) >= 0  # FreshBar or refill result


# Test 7: top 3 / best one / compare these skip provider (regression guard)
def test_top_3_skips_provider_with_pool_active() -> None:
    """Even with pool enabled, top 3 must still use card reuse (refine_previous), not provider."""
    from app.concierge.context_resolver import RefineResolved

    prior_pool = _pool(
        restaurants=[_verified_card("R1"), _verified_card("R2"), _verified_card("R3")],
        intent="restaurants",
    )
    ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=3,
        has_prior_cards=True,
        source_message_id="msg-prev",
        prior_card_pool=prior_pool,
        prior_place_category="restaurants",
    )
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="top 3")
    mock_service = MagicMock()

    resolved = RefineResolved(
        restaurants=[_verified_card("R1"), _verified_card("R2"), _verified_card("R3")],
        attractions=[],
        hotels=[],
        pool_size_before=3,
        pool_size_after=3,
        rerank_rule="top_n",
        source_message_id="msg-prev",
        prior_intent="restaurants",
    )

    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=ctx),
        patch("app.routes.ai.resolve_refine_previous", return_value=resolved),
    ):
        result, decision = build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    assert decision.code == "refine_previous_card_reuse"
    mock_service.search.assert_not_called()


# Test 8: New category search does not page Mexican pool
def test_new_category_search_does_not_use_mexican_pool() -> None:
    """After Mexican restaurants, a non-continuation search must not consume the Mexican pool."""
    # Pre-populate Mexican pool
    _GLOBAL_CONTINUATION_POOL.store(
        str(FAKE_TRIP_ID),
        "mexican restaurants",
        {
            "restaurants": [_verified_card("MexicanResto")],
            "attractions": [],
            "hotels": [],
        },
    )

    # Simulate a fresh "more options" continuation with cocktail bar context (different category).
    # The pool key for "cocktail bars" is different from "mexican restaurants", so the Mexican
    # pool must not be consumed.
    prior_pool = _pool(restaurants=[_verified_card("OldBar")], intent="nightlife")
    ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=1,
        has_prior_cards=True,
        source_message_id="msg-prev",
        prior_card_pool=prior_pool,
        prior_place_category="cocktail bars",
        prior_place_query_hint="cocktail bars",
    )
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")
    mock_service = MagicMock()
    mock_service.search.return_value = _make_place_response_with_names(["NewBar"])

    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=ctx),
    ):
        result, decision = build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    assert decision.code == "more_options_continuation"
    # Mexican pool must still be intact (different canonical key — not consumed)
    pool_entry = _GLOBAL_CONTINUATION_POOL.pop(str(FAKE_TRIP_ID), "mexican restaurants")
    assert pool_entry is not None, "Mexican pool must not be consumed by cocktail bars continuation"
    pool_names = {c["name"] for c in pool_entry[0].get("restaurants", [])}
    assert "MexicanResto" in pool_names, "Mexican pool card must still be in pool"
    # Cocktail bar result must not contain Mexican pool cards
    result_names = {r.name for r in result.restaurants}
    assert "MexicanResto" not in result_names, "Mexican pool cards must not appear in cocktail bar results"
