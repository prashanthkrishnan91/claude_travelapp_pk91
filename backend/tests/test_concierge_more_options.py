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
from app.models.concierge import ConciergeSearchRequest
from app.routes.ai import build_typed_concierge_response

FAKE_TRIP_ID = UUID("00000000-0000-0000-0000-000000000010")
FAKE_USER_ID = UUID("00000000-0000-0000-0000-000000000011")


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


def test_more_options_calls_search_with_contextualized_query() -> None:
    """Provider search must receive 'more cocktail bars', not 'more options'."""
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options")
    fake_response = _make_fake_place_response()
    mock_service = MagicMock()
    mock_service.search.return_value = fake_response

    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=_nightlife_ctx()),
    ):
        build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    mock_service.search.assert_called_once()
    call_args = mock_service.search.call_args
    # Second positional arg is the user_query sent to provider
    provider_query = call_args[0][1]
    assert provider_query == "more cocktail bars"
    assert provider_query != "more options"


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
    mock_service.search.return_value = _make_fake_place_response()
    with (
        patch("app.routes.ai.get_settings", return_value=_settings(flag=True)),
        patch("app.routes.ai.build_context_window", return_value=ctx),
    ):
        build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)
    assert mock_service.search.call_args[0][1] == "more italian restaurants"


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
    call_args = mock_service.search.call_args[0][1]
    assert call_args == "more restaurants"


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
    assert mock_service.search.call_args[0][1] == "more attractions"


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
