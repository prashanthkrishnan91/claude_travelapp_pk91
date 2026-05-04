"""Tests for AI Concierge context resolver — PR 2 refine_previous card reuse."""

from __future__ import annotations

import copy
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

# Ensure app.core is a package (has __path__) so submodule imports resolve.
# test_concierge_context.py may have stubbed it as a flat ModuleType without __path__.
_core_path = os.path.join(os.path.dirname(__file__), "..", "app", "core")
_core_mod = sys.modules.get("app.core")
if _core_mod is None:
    _core_mod = types.ModuleType("app.core")
    sys.modules["app.core"] = _core_mod
if not hasattr(_core_mod, "__path__"):
    _core_mod.__path__ = [_core_path]  # type: ignore[attr-defined]

# Stub only app.core.deps (DB / CurrentUserID) — the rest of app.core loads from disk.
_deps_mod = sys.modules.get("app.core.deps")
if _deps_mod is None:
    _deps_mod = types.ModuleType("app.core.deps")
    sys.modules["app.core.deps"] = _deps_mod
if not hasattr(_deps_mod, "DB"):
    setattr(_deps_mod, "DB", object)
if not hasattr(_deps_mod, "CurrentUserID"):
    setattr(_deps_mod, "CurrentUserID", object)

# Register app.routes as a package so patch("app.routes.ai.*") resolves correctly.
if "app.routes" not in sys.modules:
    _routes_pkg = types.ModuleType("app.routes")
    _routes_pkg.__path__ = [  # type: ignore[attr-defined]
        os.path.join(os.path.dirname(__file__), "..", "app", "routes")
    ]
    sys.modules["app.routes"] = _routes_pkg

from app.concierge.context import ContextWindow
from app.concierge.context_resolver import (
    RefineResolved,
    _MAX_COMPARE_CARDS,
    _SUPPORTED_RULES,
    _card_passes_trust_gate,
    _extract_pool_buckets,
    _parse_top_n,
    _reassemble_buckets,
    resolve_refine_previous,
)

FAKE_TRIP_ID = UUID("00000000-0000-0000-0000-000000000002")


# ── Card factories ─────────────────────────────────────────────────────────────


def _verified_card(name: str = "TestBar", bucket: str = "restaurants") -> dict:
    """Build a minimal verified_place card that passes the trust gate."""
    return {
        "type": "verified_place",
        "name": name,
        "source": "google_places",
        "why_pick": f"Known for great vibes.",
        "supporting_details": {"rating": "4.5", "why_pick": f"Known for great vibes."},
        "display": {
            "display_name": name,
            "display_category": "Bar",
            "display_why": f"Known for great vibes.",
            "addability": "addable",
        },
        "google_verification": {
            "provider": "google_places",
            "business_status": "OPERATIONAL",
            "provider_place_id": f"ChIJ_{name.lower().replace(' ', '_')}",
            "google_maps_uri": f"https://maps.google.com/?cid={name.lower()}",
            "name": name,
            "formatted_address": f"123 {name} St",
            "rating": 4.5,
            "user_rating_count": 200,
        },
    }


def _unverified_card(name: str = "ClosedBar", reason: str = "closed") -> dict:
    """Build a card that fails the trust gate."""
    card = _verified_card(name)
    if reason == "closed":
        card["google_verification"]["business_status"] = "CLOSED_TEMPORARILY"
    elif reason == "no_place_id":
        card["google_verification"]["provider_place_id"] = None
    elif reason == "no_maps_uri":
        card["google_verification"]["google_maps_uri"] = None
    elif reason == "no_gv":
        card["google_verification"] = None
    elif reason == "wrong_type":
        card["type"] = "research_source"
    return card


def _pool_with(
    restaurants: list | None = None,
    attractions: list | None = None,
    hotels: list | None = None,
    intent: str = "nightlife",
) -> dict:
    return {
        "intent": intent,
        "response": "Here are some options.",
        "restaurants": restaurants or [],
        "attractions": attractions or [],
        "hotels": hotels or [],
    }


def _ctx_with_pool(pool: dict, n: int | None = None) -> ContextWindow:
    total = sum(
        len(pool.get(b, [])) for b in ("restaurants", "attractions", "hotels")
    )
    pool_size = n if n is not None else total
    return ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=pool_size,
        has_prior_cards=pool_size > 0,
        source_message_id="msg-prev",
        prior_card_pool=pool,
    )


def _ctx_no_pool() -> ContextWindow:
    return ContextWindow(trip_id=FAKE_TRIP_ID, card_pool_size=0, has_prior_cards=False)


# ── _card_passes_trust_gate ────────────────────────────────────────────────────


def test_trust_gate_passes_verified_card():
    assert _card_passes_trust_gate(_verified_card()) is True


def test_trust_gate_fails_not_a_dict():
    assert _card_passes_trust_gate("not a dict") is False
    assert _card_passes_trust_gate(None) is False
    assert _card_passes_trust_gate(42) is False


def test_trust_gate_fails_wrong_type():
    assert _card_passes_trust_gate(_unverified_card(reason="wrong_type")) is False


def test_trust_gate_fails_no_google_verification():
    assert _card_passes_trust_gate(_unverified_card(reason="no_gv")) is False


def test_trust_gate_fails_closed():
    assert _card_passes_trust_gate(_unverified_card(reason="closed")) is False


def test_trust_gate_fails_no_place_id():
    assert _card_passes_trust_gate(_unverified_card(reason="no_place_id")) is False


def test_trust_gate_fails_no_maps_uri():
    assert _card_passes_trust_gate(_unverified_card(reason="no_maps_uri")) is False


# ── _parse_top_n ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("query", "pool", "expected"),
    [
        ("top 3", 5, 3),
        ("top three", 5, 3),
        ("show me 5", 5, 5),
        ("show me 10", 7, 7),   # clamped to pool
        ("give me 1", 5, 1),
        ("top 0", 5, 1),        # clamped to minimum 1
        ("top two", 5, 2),
        ("top ten", 8, 8),      # clamped to pool
        ("no number here", 4, 3),  # fallback = min(3, pool)
        ("no number here", 2, 2),  # fallback = min(3, pool=2)
    ],
)
def test_parse_top_n(query, pool, expected):
    assert _parse_top_n(query, pool) == expected


# ── _extract_pool_buckets ──────────────────────────────────────────────────────


def test_extract_pool_buckets_order():
    pool = _pool_with(
        restaurants=[_verified_card("R1"), _verified_card("R2")],
        attractions=[_verified_card("A1", "attractions")],
    )
    pairs = _extract_pool_buckets(pool)
    assert len(pairs) == 3
    assert pairs[0] == ("restaurants", pool["restaurants"][0])
    assert pairs[1] == ("restaurants", pool["restaurants"][1])
    assert pairs[2] == ("attractions", pool["attractions"][0])


def test_extract_pool_buckets_empty():
    assert _extract_pool_buckets({}) == []
    assert _extract_pool_buckets(_pool_with()) == []


# ── resolve_refine_previous: fall-through cases ────────────────────────────────


def test_resolve_unsupported_rule_returns_none():
    ctx = _ctx_with_pool(_pool_with(restaurants=[_verified_card()]))
    result = resolve_refine_previous(ctx, "date_night", "best for date night")
    assert result is None


def test_resolve_unsupported_rule_cheapest():
    ctx = _ctx_with_pool(_pool_with(restaurants=[_verified_card()]))
    assert resolve_refine_previous(ctx, "cheapest", "cheapest") is None


def test_resolve_unsupported_rule_most_upscale():
    ctx = _ctx_with_pool(_pool_with(restaurants=[_verified_card()]))
    assert resolve_refine_previous(ctx, "most_upscale", "most upscale") is None


def test_resolve_no_prior_pool_returns_none():
    ctx = _ctx_no_pool()
    assert resolve_refine_previous(ctx, "top_n", "top 3") is None


def test_resolve_no_prior_pool_with_rule_returns_none():
    ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=0,
        has_prior_cards=False,
        prior_card_pool=None,
    )
    assert resolve_refine_previous(ctx, "best_one", "best one") is None


def test_resolve_empty_pool_returns_none():
    ctx = _ctx_with_pool(_pool_with())  # all lists empty
    assert resolve_refine_previous(ctx, "top_n", "top 3") is None


def test_resolve_all_cards_fail_trust_gate_returns_none():
    pool = _pool_with(
        restaurants=[
            _unverified_card("C1", "closed"),
            _unverified_card("C2", "no_place_id"),
            _unverified_card("C3", "no_maps_uri"),
        ]
    )
    ctx = _ctx_with_pool(pool)
    result = resolve_refine_previous(ctx, "top_n", "top 3")
    assert result is None


def test_resolve_stale_card_dropped_not_patched():
    """An untrusted card is dropped. The remaining verified card is returned unchanged."""
    good = _verified_card("GoodBar")
    bad = _unverified_card("BadBar", "closed")
    pool = _pool_with(restaurants=[bad, good])
    ctx = _ctx_with_pool(pool)

    result = resolve_refine_previous(ctx, "top_n", "top 2")
    assert result is not None
    assert result.pool_size_before == 2
    assert result.pool_size_after == 1
    assert len(result.restaurants) == 1
    assert result.restaurants[0]["name"] == "GoodBar"


# ── resolve_refine_previous: successful cases ──────────────────────────────────


def test_resolve_top_n_returns_first_3_of_5():
    cards = [_verified_card(f"Bar{i}") for i in range(5)]
    pool = _pool_with(restaurants=cards)
    ctx = _ctx_with_pool(pool)

    result = resolve_refine_previous(ctx, "top_n", "top 3")
    assert result is not None
    assert result.pool_size_before == 5
    assert result.pool_size_after == 3
    assert len(result.restaurants) == 3
    assert result.restaurants[0]["name"] == "Bar0"
    assert result.restaurants[1]["name"] == "Bar1"
    assert result.restaurants[2]["name"] == "Bar2"


def test_resolve_top_n_with_show_me_5():
    cards = [_verified_card(f"Bar{i}") for i in range(7)]
    pool = _pool_with(restaurants=cards)
    ctx = _ctx_with_pool(pool)

    result = resolve_refine_previous(ctx, "top_n", "show me 5")
    assert result is not None
    assert result.pool_size_after == 5


def test_resolve_best_one_returns_first_card():
    cards = [_verified_card(f"Bar{i}") for i in range(4)]
    pool = _pool_with(restaurants=cards)
    ctx = _ctx_with_pool(pool)

    result = resolve_refine_previous(ctx, "best_one", "best one")
    assert result is not None
    assert result.pool_size_after == 1
    assert len(result.restaurants) == 1
    assert result.restaurants[0]["name"] == "Bar0"


def test_resolve_compare_returns_up_to_max():
    cards = [_verified_card(f"Bar{i}") for i in range(10)]
    pool = _pool_with(restaurants=cards)
    ctx = _ctx_with_pool(pool)

    result = resolve_refine_previous(ctx, "compare", "compare these")
    assert result is not None
    assert result.pool_size_after == _MAX_COMPARE_CARDS
    assert len(result.restaurants) == _MAX_COMPARE_CARDS


def test_resolve_compare_fewer_than_max():
    cards = [_verified_card(f"Bar{i}") for i in range(3)]
    pool = _pool_with(restaurants=cards)
    ctx = _ctx_with_pool(pool)

    result = resolve_refine_previous(ctx, "compare", "compare these")
    assert result is not None
    assert result.pool_size_after == 3


def test_resolve_preserves_source_message_id():
    pool = _pool_with(restaurants=[_verified_card()])
    ctx = _ctx_with_pool(pool)
    ctx = ctx.model_copy(update={"source_message_id": "msg-abc-123"})

    result = resolve_refine_previous(ctx, "best_one", "best one")
    assert result is not None
    assert result.source_message_id == "msg-abc-123"


def test_resolve_preserves_prior_intent():
    pool = _pool_with(restaurants=[_verified_card()], intent="nightlife")
    ctx = _ctx_with_pool(pool)

    result = resolve_refine_previous(ctx, "best_one", "best one")
    assert result is not None
    assert result.prior_intent == "nightlife"


def test_resolve_returns_correct_rerank_rule():
    pool = _pool_with(restaurants=[_verified_card()])
    ctx = _ctx_with_pool(pool)

    for rule in ("top_n", "best_one", "compare"):
        result = resolve_refine_previous(ctx, rule, "top 1")  # type: ignore[arg-type]
        assert result is not None
        assert result.rerank_rule == rule


# ── Card identity / field preservation ────────────────────────────────────────


def test_reused_card_deep_equals_original():
    """Reused card must be bit-for-bit identical to the original from the prior pool."""
    original = _verified_card("KumikoBar")
    pool = _pool_with(restaurants=[original])
    ctx = _ctx_with_pool(pool)

    result = resolve_refine_previous(ctx, "best_one", "best one")
    assert result is not None
    assert len(result.restaurants) == 1
    assert result.restaurants[0] is original  # same object, not a copy


def test_reused_card_why_pick_unchanged():
    card = _verified_card("Venue")
    card["why_pick"] = "A special reason that must not be rewritten."
    pool = _pool_with(restaurants=[card])
    ctx = _ctx_with_pool(pool)

    result = resolve_refine_previous(ctx, "best_one", "best one")
    assert result is not None
    assert result.restaurants[0]["why_pick"] == "A special reason that must not be rewritten."


def test_reused_card_display_fields_unchanged():
    card = _verified_card("DisplayVenue")
    card["display"]["display_why"] = "A display reason."
    card["display"]["display_name"] = "My Display Name"
    pool = _pool_with(restaurants=[card])
    ctx = _ctx_with_pool(pool)

    result = resolve_refine_previous(ctx, "best_one", "best one")
    assert result is not None
    r = result.restaurants[0]
    assert r["display"]["display_why"] == "A display reason."
    assert r["display"]["display_name"] == "My Display Name"


def test_reused_card_supporting_details_unchanged():
    card = _verified_card("SupportVenue")
    card["supporting_details"]["why_pick"] = "Supporting why pick."
    pool = _pool_with(restaurants=[card])
    ctx = _ctx_with_pool(pool)

    result = resolve_refine_previous(ctx, "best_one", "best one")
    assert result is not None
    assert result.restaurants[0]["supporting_details"]["why_pick"] == "Supporting why pick."


def test_reused_card_google_verification_identity_unchanged():
    card = _verified_card("GVVenue")
    orig_place_id = card["google_verification"]["provider_place_id"]
    orig_maps_uri = card["google_verification"]["google_maps_uri"]
    pool = _pool_with(restaurants=[card])
    ctx = _ctx_with_pool(pool)

    result = resolve_refine_previous(ctx, "best_one", "best one")
    assert result is not None
    gv = result.restaurants[0]["google_verification"]
    assert gv["provider_place_id"] == orig_place_id
    assert gv["google_maps_uri"] == orig_maps_uri


# ── Mixed bucket handling ──────────────────────────────────────────────────────


def test_resolve_top_n_mixed_buckets_preserves_order():
    """Cards from restaurants/attractions/hotels are drawn in bucket order."""
    r1 = _verified_card("R1", "restaurants")
    a1 = _verified_card("A1", "attractions")
    r2 = _verified_card("R2", "restaurants")
    pool = _pool_with(restaurants=[r1, r2], attractions=[a1])
    ctx = _ctx_with_pool(pool)

    result = resolve_refine_previous(ctx, "top_n", "top 2")
    assert result is not None
    assert result.pool_size_after == 2
    # First 2 come from restaurants (bucket order: restaurants first)
    assert len(result.restaurants) == 2
    assert len(result.attractions) == 0


def test_resolve_compare_mixed_buckets_reassembled():
    r1 = _verified_card("R1")
    a1 = _verified_card("A1")
    h1 = _verified_card("H1")
    pool = _pool_with(restaurants=[r1], attractions=[a1], hotels=[h1])
    ctx = _ctx_with_pool(pool)

    result = resolve_refine_previous(ctx, "compare", "compare them")
    assert result is not None
    assert len(result.restaurants) == 1
    assert len(result.attractions) == 1
    assert len(result.hotels) == 1


# ── Feature flag integration: flag OFF does not invoke resolver ────────────────


def test_flag_off_route_calls_provider_not_resolver():
    """When concierge_context_v1_enabled is False, resolver is never called."""
    # Import module first so patch target is resolvable
    from app.routes.ai import build_typed_concierge_response  # noqa: F401  # loads module
    from app.concierge.context_resolver import resolve_refine_previous as real_resolver
    from app.models.concierge import ConciergeSearchRequest

    settings_ns = SimpleNamespace(
        concierge_context_v1_enabled=False,
        concierge_router_v2=False,
        trip_advice_builder_enabled=False,
    )

    with patch(
        "app.routes.ai.resolve_refine_previous", wraps=real_resolver
    ) as mock_resolver, patch(
        "app.routes.ai.get_settings", return_value=settings_ns
    ):
        mock_service = MagicMock()
        mock_service._db = MagicMock()
        _setup_db_with_cards(
            mock_service._db,
            [_verified_card("Bar1"), _verified_card("Bar2")],
        )
        mock_service.search.return_value = _mock_search_response()

        payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="top 3")
        from app.routes.ai import build_typed_concierge_response as _fn
        _fn(mock_service, payload, FAKE_TRIP_ID)

        # Resolver was NOT called (flag off)
        mock_resolver.assert_not_called()
        # Provider was called
        mock_service.search.assert_called_once()


# ── Feature flag integration: flag ON + refine_previous skips provider ────────


def _flag_on_settings() -> SimpleNamespace:
    return SimpleNamespace(
        concierge_context_v1_enabled=True,
        concierge_router_v2=False,
        trip_advice_builder_enabled=False,
    )


def test_flag_on_top3_skips_provider_call():
    """Flag ON + top 3 + verified prior cards: provider (service.search) not called."""
    from app.models.concierge import ConciergeSearchRequest
    from app.routes.ai import build_typed_concierge_response

    cards = [_verified_card(f"Bar{i}") for i in range(5)]

    with patch("app.routes.ai.get_settings", return_value=_flag_on_settings()):
        mock_service = MagicMock()
        mock_service._db = MagicMock()
        _setup_db_with_cards(mock_service._db, cards)

        payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="top 3")
        response, decision = build_typed_concierge_response(
            mock_service, payload, FAKE_TRIP_ID
        )

        mock_service.search.assert_not_called()
        assert decision.code == "refine_previous_card_reuse"
        assert response.turn_mode == "refine_previous"
        assert response.context_reuse is not None
        assert response.context_reuse["provider_call"] is False
        assert response.context_reuse["rerank_rule"] == "top_n"
        total = len(response.restaurants) + len(response.attractions) + len(response.hotels)
        assert total == 3


def test_flag_on_best_one_returns_1_card():
    from app.models.concierge import ConciergeSearchRequest
    from app.routes.ai import build_typed_concierge_response

    cards = [_verified_card(f"Bar{i}") for i in range(4)]

    with patch("app.routes.ai.get_settings", return_value=_flag_on_settings()):
        mock_service = MagicMock()
        mock_service._db = MagicMock()
        _setup_db_with_cards(mock_service._db, cards)

        payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="best one")
        response, decision = build_typed_concierge_response(
            mock_service, payload, FAKE_TRIP_ID
        )

        mock_service.search.assert_not_called()
        assert decision.code == "refine_previous_card_reuse"
        total = len(response.restaurants) + len(response.attractions) + len(response.hotels)
        assert total == 1


def test_flag_on_compare_returns_prior_cards():
    from app.models.concierge import ConciergeSearchRequest
    from app.routes.ai import build_typed_concierge_response

    cards = [_verified_card(f"Bar{i}") for i in range(4)]

    with patch("app.routes.ai.get_settings", return_value=_flag_on_settings()):
        mock_service = MagicMock()
        mock_service._db = MagicMock()
        _setup_db_with_cards(mock_service._db, cards)

        payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="compare these")
        response, decision = build_typed_concierge_response(
            mock_service, payload, FAKE_TRIP_ID
        )

        mock_service.search.assert_not_called()
        assert decision.code == "refine_previous_card_reuse"
        total = len(response.restaurants) + len(response.attractions) + len(response.hotels)
        assert total == 4  # all 4 (below _MAX_COMPARE_CARDS)


def test_flag_on_no_prior_cards_falls_through():
    """When there are no prior verified cards, falls through to existing search."""
    from app.models.concierge import ConciergeSearchRequest
    from app.routes.ai import build_typed_concierge_response

    with patch("app.routes.ai.get_settings", return_value=_flag_on_settings()):
        mock_service = MagicMock()
        mock_service._db = MagicMock()
        _setup_db_with_cards(mock_service._db, [])  # no prior cards
        mock_service.search.return_value = _mock_search_response()

        payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="top 3")
        build_typed_concierge_response(mock_service, payload, FAKE_TRIP_ID)

        mock_service.search.assert_called_once()


def test_flag_on_unsupported_rule_falls_through():
    """date_night is not a supported PR 2 rule — falls through to provider."""
    from app.models.concierge import ConciergeSearchRequest
    from app.routes.ai import build_typed_concierge_response

    cards = [_verified_card(f"Bar{i}") for i in range(3)]

    with patch("app.routes.ai.get_settings", return_value=_flag_on_settings()):
        mock_service = MagicMock()
        mock_service._db = MagicMock()
        _setup_db_with_cards(mock_service._db, cards)
        mock_service.search.return_value = _mock_search_response()

        payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="best for date night")
        build_typed_concierge_response(mock_service, payload, FAKE_TRIP_ID)

        mock_service.search.assert_called_once()


def test_flag_on_all_cards_stale_falls_through():
    """All prior cards fail trust gate => fall through to existing provider search."""
    from app.models.concierge import ConciergeSearchRequest
    from app.routes.ai import build_typed_concierge_response

    cards = [_unverified_card("C1", "closed"), _unverified_card("C2", "no_place_id")]

    with patch("app.routes.ai.get_settings", return_value=_flag_on_settings()):
        mock_service = MagicMock()
        mock_service._db = MagicMock()
        _setup_db_with_cards(mock_service._db, cards)
        mock_service.search.return_value = _mock_search_response()

        payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="top 2")
        build_typed_concierge_response(mock_service, payload, FAKE_TRIP_ID)

        mock_service.search.assert_called_once()


# ── Integration-ish sequence test ─────────────────────────────────────────────


def test_sequence_cocktail_bars_top3_more_options():
    """
    Turn 1: 'cocktail bars' => new_search, provider called
    Turn 2: 'top 3' with flag ON + prior verified cards => reused, provider NOT called
    Turn 3: 'more options' => new_search override, provider called again
    """
    from app.models.concierge import ConciergeSearchRequest
    from app.routes.ai import build_typed_concierge_response

    cards = [_verified_card(f"Bar{i}") for i in range(5)]

    with patch("app.routes.ai.get_settings", return_value=_flag_on_settings()):

        # --- Turn 1: 'cocktail bars' — no prior cards ---
        svc1 = MagicMock()
        svc1._db = MagicMock()
        _setup_db_with_cards(svc1._db, [])
        svc1.search.return_value = _mock_search_response()

        build_typed_concierge_response(svc1, ConciergeSearchRequest(
            trip_id=FAKE_TRIP_ID, user_query="cocktail bars"
        ), FAKE_TRIP_ID)
        assert svc1.search.call_count == 1, "Turn 1: provider should be called"

        # --- Turn 2: 'top 3' — prior verified cards available ---
        svc2 = MagicMock()
        svc2._db = MagicMock()
        _setup_db_with_cards(svc2._db, cards)

        response2, decision2 = build_typed_concierge_response(
            svc2, ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="top 3"), FAKE_TRIP_ID
        )
        svc2.search.assert_not_called()
        assert decision2.code == "refine_previous_card_reuse"
        total2 = len(response2.restaurants) + len(response2.attractions) + len(response2.hotels)
        assert total2 == 3

        # --- Turn 3: 'more options' — new_search override ---
        svc3 = MagicMock()
        svc3._db = MagicMock()
        _setup_db_with_cards(svc3._db, cards)
        svc3.search.return_value = _mock_search_response()

        build_typed_concierge_response(
            svc3, ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="more options"), FAKE_TRIP_ID
        )
        svc3.search.assert_called_once()


# ── Helpers ────────────────────────────────────────────────────────────────────


def _setup_db_with_cards(mock_db: MagicMock, cards: list) -> None:
    """Wire mock_db so build_context_window() returns the given card pool."""
    structured = _pool_with(restaurants=cards) if cards else None
    messages = []
    if cards:
        messages.append({
            "id": "msg-prev",
            "role": "assistant",
            "content": "Here are some options.",
            "structured_results": structured,
        })
    (
        mock_db.table.return_value
        .select.return_value
        .eq.return_value
        .order.return_value
        .limit.return_value
        .execute.return_value
    ) = SimpleNamespace(data=messages)


def _mock_search_response() -> MagicMock:
    """Build a minimal mock ConciergeSearchResponse for fall-through path."""
    r = MagicMock()
    r.model_dump.return_value = {
        "response": "Here are your options.",
        "intent": "nightlife",
        "retrieval_used": True,
        "source_status": "live_search",
        "cached": False,
        "live_provider": None,
        "restaurants": [],
        "attractions": [],
        "hotels": [],
        "research_sources": [],
        "areas": [],
        "area_comparisons": [],
        "suggestions": [],
        "sources": [],
        "warnings": [],
        "turn_mode": None,
        "context_reuse": None,
    }
    return r
