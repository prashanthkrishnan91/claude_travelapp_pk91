"""Tests for AI Concierge context window and turn-mode classifier (PR 1 dark foundation)."""

import os
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Minimal stubs so context.py imports cleanly without the full stack ─────────

for _mod in ["fastapi", "supabase", "anthropic"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

for _mod in ["app.core", "app.core.config", "app.core.deps"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = types.ModuleType(_mod)

if not hasattr(sys.modules["app.core.config"], "get_settings"):
    sys.modules["app.core.config"].get_settings = lambda: MagicMock()

from app.concierge.context import (
    ContextWindow,
    RerankRule,
    TurnMode,
    _count_place_cards,
    build_context_window,
    classify_turn,
    log_context_turn,
)

FAKE_TRIP_ID = UUID("00000000-0000-0000-0000-000000000001")


# ── Helpers ────────────────────────────────────────────────────────────────────


def ctx_with_cards(n: int = 5) -> ContextWindow:
    return ContextWindow(trip_id=FAKE_TRIP_ID, card_pool_size=n, has_prior_cards=n > 0)


def ctx_no_cards() -> ContextWindow:
    return ContextWindow(trip_id=FAKE_TRIP_ID, card_pool_size=0, has_prior_cards=False)


# ── Classifier table tests ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("query", "has_cards", "expected_mode", "expected_rule"),
    [
        # ── refine_previous cases ──────────────────────────────────────────────
        ("top 3", True, "refine_previous", "top_n"),
        ("top three", True, "refine_previous", "top_n"),
        ("show me 5", True, "refine_previous", "top_n"),
        ("give me 3", True, "refine_previous", "top_n"),
        ("top 10", True, "refine_previous", "top_n"),
        ("best one", True, "refine_previous", "best_one"),
        ("which one is best", True, "refine_previous", "best_one"),
        ("best for date night", True, "refine_previous", "date_night"),
        ("cheapest", True, "refine_previous", "cheapest"),
        ("most upscale", True, "refine_previous", "most_upscale"),
        ("compare these", True, "refine_previous", "compare"),
        ("compare them", True, "refine_previous", "compare"),
        ("rank these", True, "refine_previous", "compare"),
        # ── new_search: no prior cards ─────────────────────────────────────────
        ("top 3", False, "new_search", "none"),
        ("cocktail bars", False, "new_search", "none"),
        ("best one", False, "new_search", "none"),
        # ── new_search: override signals present ──────────────────────────────
        ("the top 3 things to do", True, "new_search", "none"),
        ("more options", True, "new_search", "none"),
        ("cocktail bars in Wicker Park", True, "new_search", "none"),
        ("ramen in Shibuya", True, "new_search", "none"),
        ("restaurants near the first one", True, "anchor_new", "none"),  # anchor wins over "restaurants"
        ("things to do tomorrow", True, "new_search", "none"),
        # ── anchor_new ────────────────────────────────────────────────────────
        ("restaurants near the first one", True, "anchor_new", "none"),
        ("near #1", True, "anchor_new", "none"),
        ("near the first one", True, "anchor_new", "none"),
        ("around the second one", True, "anchor_new", "none"),
        ("same area as #2", True, "anchor_new", "none"),
        # anchor_new requires prior cards
        ("near #1", False, "new_search", "none"),
        # ── reset ─────────────────────────────────────────────────────────────
        ("start over", True, "reset", "none"),
        ("new chat", True, "reset", "none"),
        ("reset", True, "reset", "none"),
        # reset is unconditional
        ("start over", False, "reset", "none"),
    ],
)
def test_classify_turn_table(
    query: str, has_cards: bool, expected_mode: str, expected_rule: str
) -> None:
    ctx = ctx_with_cards() if has_cards else ctx_no_cards()
    mode, rule = classify_turn(query, ctx)
    assert mode == expected_mode, (
        f"query={query!r} has_cards={has_cards}: expected mode={expected_mode!r}, got {mode!r}"
    )
    assert rule == expected_rule, (
        f"query={query!r} has_cards={has_cards}: expected rule={expected_rule!r}, got {rule!r}"
    )


# ── Required explicit test cases from spec ─────────────────────────────────────


def test_top_3_with_prior_cards():
    mode, rule = classify_turn("top 3", ctx_with_cards())
    assert mode == "refine_previous"
    assert rule == "top_n"


def test_top_three_with_prior_cards():
    mode, rule = classify_turn("top three", ctx_with_cards())
    assert mode == "refine_previous"
    assert rule == "top_n"


def test_show_me_5_with_prior_cards():
    mode, rule = classify_turn("show me 5", ctx_with_cards())
    assert mode == "refine_previous"
    assert rule == "top_n"


def test_best_one_with_prior_cards():
    mode, rule = classify_turn("best one", ctx_with_cards())
    assert mode == "refine_previous"
    assert rule == "best_one"


def test_best_for_date_night_with_prior_cards():
    mode, rule = classify_turn("best for date night", ctx_with_cards())
    assert mode == "refine_previous"
    assert rule == "date_night"


def test_cheapest_with_prior_cards():
    mode, rule = classify_turn("cheapest", ctx_with_cards())
    assert mode == "refine_previous"
    assert rule == "cheapest"


def test_most_upscale_with_prior_cards():
    mode, rule = classify_turn("most upscale", ctx_with_cards())
    assert mode == "refine_previous"
    assert rule == "most_upscale"


def test_compare_these_with_prior_cards():
    mode, rule = classify_turn("compare these", ctx_with_cards())
    assert mode == "refine_previous"
    assert rule == "compare"


def test_top_3_no_prior_cards_is_new_search():
    mode, rule = classify_turn("top 3", ctx_no_cards())
    assert mode == "new_search"
    assert rule == "none"


def test_top_3_things_to_do_with_prior_cards_is_new_search():
    """'things to do' override forces new_search even with prior cards."""
    mode, rule = classify_turn("the top 3 things to do", ctx_with_cards())
    assert mode == "new_search"
    assert rule == "none"


def test_more_options_with_prior_cards_is_new_search():
    mode, rule = classify_turn("more options", ctx_with_cards())
    assert mode == "new_search"
    assert rule == "none"


def test_cocktail_bars_no_prior_cards_is_new_search():
    mode, rule = classify_turn("cocktail bars", ctx_no_cards())
    assert mode == "new_search"
    assert rule == "none"


def test_cocktail_bars_in_wicker_park_with_prior_cards_is_new_search():
    mode, rule = classify_turn("cocktail bars in Wicker Park", ctx_with_cards())
    assert mode == "new_search"
    assert rule == "none"


def test_near_first_one_with_prior_cards_is_anchor_new():
    mode, rule = classify_turn("restaurants near the first one", ctx_with_cards())
    assert mode == "anchor_new"
    assert rule == "none"


def test_near_hash_1_with_prior_cards_is_anchor_new():
    mode, rule = classify_turn("near #1", ctx_with_cards())
    assert mode == "anchor_new"
    assert rule == "none"


def test_start_over_with_prior_cards_is_reset():
    mode, rule = classify_turn("start over", ctx_with_cards())
    assert mode == "reset"
    assert rule == "none"


# ── Deny-by-default: ambiguous prompts ────────────────────────────────────────


def test_empty_query_is_new_search():
    mode, rule = classify_turn("", ctx_with_cards())
    assert mode == "new_search"


def test_ambiguous_prompt_is_new_search():
    mode, rule = classify_turn("hi", ctx_with_cards())
    assert mode == "new_search"


# ── ContextWindow model ────────────────────────────────────────────────────────


def test_context_window_defaults():
    ctx = ContextWindow(trip_id=FAKE_TRIP_ID)
    assert ctx.card_pool_size == 0
    assert ctx.has_prior_cards is False
    assert ctx.source_message_id is None
    assert ctx.prior_user_prompts == []
    assert ctx.reset_reason is None
    assert ctx.destination is None


def test_context_window_with_cards():
    ctx = ContextWindow(
        trip_id=FAKE_TRIP_ID,
        card_pool_size=7,
        has_prior_cards=True,
        source_message_id="msg-abc",
        destination="Chicago",
    )
    assert ctx.has_prior_cards is True
    assert ctx.card_pool_size == 7
    assert ctx.source_message_id == "msg-abc"


# ── _count_place_cards helper ──────────────────────────────────────────────────


def test_count_place_cards_restaurants():
    result = _count_place_cards({"restaurants": [{"name": "A"}, {"name": "B"}]})
    assert result == 2


def test_count_place_cards_mixed():
    result = _count_place_cards(
        {
            "restaurants": [{"name": "A"}],
            "attractions": [{"name": "B"}, {"name": "C"}],
            "hotels": [],
        }
    )
    assert result == 3


def test_count_place_cards_empty():
    assert _count_place_cards({}) == 0
    assert _count_place_cards(None) == 0
    assert _count_place_cards("not a dict") == 0


# ── build_context_window: table missing graceful degradation ──────────────────


def test_build_context_window_table_missing_returns_shell():
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.side_effect = Exception(
        "relation concierge_messages does not exist"
    )
    ctx = build_context_window(db, FAKE_TRIP_ID)
    assert ctx.trip_id == FAKE_TRIP_ID
    assert ctx.has_prior_cards is False
    assert ctx.card_pool_size == 0


def test_build_context_window_generic_error_returns_shell():
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.side_effect = Exception(
        "connection refused"
    )
    ctx = build_context_window(db, FAKE_TRIP_ID, destination="Tokyo")
    assert ctx.has_prior_cards is False
    assert ctx.destination == "Tokyo"


def test_build_context_window_no_messages_returns_shell():
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(
        data=[]
    )
    ctx = build_context_window(db, FAKE_TRIP_ID)
    assert ctx.has_prior_cards is False
    assert ctx.card_pool_size == 0
    assert ctx.prior_user_prompts == []


def test_build_context_window_finds_most_recent_assistant_with_cards():
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(
        data=[
            # Most recent message first (DESC order)
            {
                "id": "msg-1",
                "role": "user",
                "content": "cocktail bars",
                "structured_results": None,
            },
            {
                "id": "msg-2",
                "role": "assistant",
                "content": "Here are some great options",
                "structured_results": {
                    "restaurants": [{"name": "A"}, {"name": "B"}],
                    "attractions": [],
                    "hotels": [],
                },
            },
            {
                "id": "msg-3",
                "role": "user",
                "content": "cocktail bars",
                "structured_results": None,
            },
        ]
    )
    ctx = build_context_window(db, FAKE_TRIP_ID)
    assert ctx.has_prior_cards is True
    assert ctx.card_pool_size == 2
    assert ctx.source_message_id == "msg-2"
    # User prompts (most recent first): msg-1 user content first
    assert "cocktail bars" in ctx.prior_user_prompts


def test_build_context_window_no_assistant_with_cards():
    """If all assistant messages have empty structured results, has_prior_cards=False."""
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(
        data=[
            {
                "id": "msg-1",
                "role": "user",
                "content": "hello",
                "structured_results": None,
            },
            {
                "id": "msg-2",
                "role": "assistant",
                "content": "Hi",
                "structured_results": {"restaurants": [], "attractions": [], "hotels": []},
            },
        ]
    )
    ctx = build_context_window(db, FAKE_TRIP_ID)
    assert ctx.has_prior_cards is False
    assert ctx.card_pool_size == 0
    assert ctx.source_message_id is None


def test_build_context_window_propagates_destination():
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(
        data=[]
    )
    ctx = build_context_window(db, FAKE_TRIP_ID, destination="Kyoto")
    assert ctx.destination == "Kyoto"


# ── Integration-ish: refine_previous prompt still follows existing behavior ────


def test_refine_previous_classified_correctly_but_no_card_reuse():
    """Classify refine_previous correctly, confirm no cards or skipped providers in PR 1.

    This test verifies that classify_turn returns refine_previous for 'top 3' with
    prior cards, and that the dark classification does NOT change what cards are
    returned (that behavior is left for a future PR).
    """
    ctx = ctx_with_cards(n=5)
    mode, rule = classify_turn("top 3", ctx)
    assert mode == "refine_previous"
    assert rule == "top_n"

    # Confirm the context window itself doesn't reorder or subset cards — it's just metadata.
    assert ctx.card_pool_size == 5
    assert ctx.has_prior_cards is True
    # No reranked_cards, no filtered_cards, no reuse_pool — these don't exist in PR 1.
    assert not hasattr(ctx, "reranked_cards")
    assert not hasattr(ctx, "reuse_pool")


def test_anchor_new_classified_correctly_but_no_anchor_search_in_pr1():
    """anchor_new is classified but no anchor-based provider search is implemented."""
    ctx = ctx_with_cards(n=3)
    mode, rule = classify_turn("restaurants near the first one", ctx)
    assert mode == "anchor_new"
    assert rule == "none"
    # PR 1: no anchor search behavior on ContextWindow
    assert not hasattr(ctx, "anchor_place_id")


# ── log_context_turn: smoke test (no exception) ───────────────────────────────


def test_log_context_turn_does_not_raise():
    log_context_turn(
        trip_id=FAKE_TRIP_ID,
        request_id=None,
        turn_mode="refine_previous",
        rerank_rule="top_n",
        card_pool_size=5,
        has_prior_cards=True,
        source_message_id="msg-abc",
        reset_reason=None,
        provider_call_expected_for_future_mode=False,
    )


def test_log_context_turn_new_search_provider_call_expected_true():
    """For new_search, future mode still expects a provider call."""
    # Just ensure no exception and the logic is tested at the caller level in ai.py
    log_context_turn(
        trip_id=FAKE_TRIP_ID,
        turn_mode="new_search",
        rerank_rule="none",
        card_pool_size=0,
        has_prior_cards=False,
        provider_call_expected_for_future_mode=True,
    )
