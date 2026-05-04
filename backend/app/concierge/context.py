"""Concierge context window and turn-mode classifier — dark foundation (PR 1).

Classifies each user turn as new_search / refine_previous / anchor_new / reset.
Builds a lightweight ContextWindow from persisted concierge_messages.

PR 1 contract: classifier runs and logs, existing search flow is unchanged.
No reranking, no card reuse, no provider-call skipping implemented here.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Literal, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ── Turn mode and rerank rule literals ────────────────────────────────────────

TurnMode = Literal["new_search", "refine_previous", "anchor_new", "reset"]
RerankRule = Literal[
    "top_n", "best_one", "compare", "date_night",
    "cheapest", "most_upscale", "filter_constraint", "none",
]

# ── ContextWindow ─────────────────────────────────────────────────────────────


class ContextWindow(BaseModel):
    """Lightweight snapshot of recent concierge context for one trip."""

    trip_id: UUID
    destination: Optional[str] = None
    card_pool_size: int = 0
    has_prior_cards: bool = False
    source_message_id: Optional[str] = None
    # Most recent user prompts, capped to 3, newest first.
    prior_user_prompts: List[str] = []
    reset_reason: Optional[str] = None
    # PR 2: raw structured_results dict from most recent assistant message with cards.
    # Populated only when has_prior_cards is True. Used by context_resolver for card reuse.
    prior_card_pool: Optional[Dict[str, Any]] = None


# ── Classifier patterns ────────────────────────────────────────────────────────

_RESET_PATTERNS = [
    re.compile(r"\b(start\s+over|new\s+chat|reset)\b", re.IGNORECASE),
]

# Anchor patterns require prior cards. Order matters: more-specific patterns first.
_ANCHOR_PATTERNS = [
    re.compile(r"\bnear the first one\b", re.IGNORECASE),
    re.compile(r"\baround the second one\b", re.IGNORECASE),
    re.compile(r"\bnear (the )?(first|#1|one)\b", re.IGNORECASE),
    re.compile(r"\bnear #\d+\b", re.IGNORECASE),
    re.compile(r"\baround (the )?(second|third|fourth|#\d+|one)\b", re.IGNORECASE),
    re.compile(r"\bsame area as #?\d+\b", re.IGNORECASE),
]

# Refine patterns: exact short follow-ups, ordered by specificity.
_REFINE_PATTERNS: List[Tuple[re.Pattern, RerankRule]] = [
    (re.compile(r"\bbest for date night\b", re.IGNORECASE), "date_night"),
    (re.compile(r"\bmost upscale\b", re.IGNORECASE), "most_upscale"),
    (re.compile(r"\bcheapest\b", re.IGNORECASE), "cheapest"),
    (re.compile(r"\bbest one\b", re.IGNORECASE), "best_one"),
    (re.compile(r"\bwhich one is best\b", re.IGNORECASE), "best_one"),
    (re.compile(r"\b(compare (these|them)|rank these)\b", re.IGNORECASE), "compare"),
    (
        re.compile(
            r"\b(top|show me|give me)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b",
            re.IGNORECASE,
        ),
        "top_n",
    ),
]

# Signals that force new_search even when a refine pattern matches.
# These indicate a new category, location, or temporal context — deny-by-default.
_NEW_SEARCH_OVERRIDE_PATTERNS = [
    re.compile(r"\bmore options\b", re.IGNORECASE),
    re.compile(r"\bthings to do\b", re.IGNORECASE),
    # Explicit location anchor signals a new search, not a refinement.
    re.compile(r"\b(in|near|around)\s+[A-Za-z][A-Za-z\s]+", re.IGNORECASE),
    # Named categories indicate a new search intent.
    re.compile(
        r"\b(restaurants?|bar|bars|cafe|cafes|cocktail|ramen|sushi|tacos?|taqueria|"
        r"hotels?|attraction|attractions|museum|museums|nightlife)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(tomorrow|tonight|this weekend|next week)\b", re.IGNORECASE),
]


def classify_turn(
    user_query: str,
    context_window: ContextWindow,
) -> Tuple[TurnMode, RerankRule]:
    """Classify the user turn deterministically. Deny-by-default: ambiguous → new_search.

    Returns (TurnMode, RerankRule). RerankRule is 'none' for non-refine modes.
    """
    text = (user_query or "").strip()

    # Reset is unconditional — applies regardless of prior card state.
    for pat in _RESET_PATTERNS:
        if pat.search(text):
            return "reset", "none"

    if context_window.has_prior_cards:
        # Anchor patterns take priority over new_search override signals.
        for pat in _ANCHOR_PATTERNS:
            if pat.search(text):
                return "anchor_new", "none"

        # New_search override signals block refine classification.
        has_new_search_signal = any(
            pat.search(text) for pat in _NEW_SEARCH_OVERRIDE_PATTERNS
        )
        if not has_new_search_signal:
            for pat, rule in _REFINE_PATTERNS:
                if pat.search(text):
                    return "refine_previous", rule

    return "new_search", "none"


# ── Context window builder ────────────────────────────────────────────────────

_MESSAGES_TABLE = "concierge_messages"
_MAX_MESSAGES = 6


def _count_place_cards(structured_results: Optional[Dict[str, Any]]) -> int:
    """Count place-producing cards in a structured_results blob."""
    if not isinstance(structured_results, dict):
        return 0
    return (
        len(structured_results.get("restaurants") or [])
        + len(structured_results.get("attractions") or [])
        + len(structured_results.get("hotels") or [])
    )


def _is_messages_table_missing(exc: Exception) -> bool:
    text = str(exc).lower()
    return (
        "pgrst205" in text
        or "schema cache" in text
        or "could not find the table" in text
        or ("concierge_messages" in text and "not found" in text)
        or (
            "relation" in text
            and "concierge_messages" in text
            and "does not exist" in text
        )
    )


def build_context_window(
    db: Any,
    trip_id: UUID,
    destination: Optional[str] = None,
) -> ContextWindow:
    """Read recent messages for the trip and build a ContextWindow.

    Reads up to _MAX_MESSAGES rows ordered newest-first.
    Never raises: any DB failure returns a shell context with no prior cards.
    """
    try:
        rows = (
            db.table(_MESSAGES_TABLE)
            .select("id,role,content,structured_results")
            .eq("trip_id", str(trip_id))
            .order("created_at", desc=True)
            .limit(_MAX_MESSAGES)
            .execute()
        )
        messages: List[Dict[str, Any]] = rows.data or []
    except Exception as exc:
        if _is_messages_table_missing(exc):
            logger.warning(
                "concierge.context.messages_table_missing trip_id=%s", trip_id
            )
        else:
            logger.warning(
                "concierge.context.messages_load_failed trip_id=%s error=%s",
                trip_id,
                exc,
            )
        return ContextWindow(trip_id=trip_id, destination=destination)

    # Collect user prompts most-recent-first (rows already ordered DESC).
    user_prompts: List[str] = [
        m["content"]
        for m in messages
        if m.get("role") == "user" and m.get("content")
    ][:3]

    # Find the most recent assistant message with place-producing cards.
    source_id: Optional[str] = None
    card_pool_size = 0
    prior_card_pool: Optional[Dict[str, Any]] = None
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        structured = msg.get("structured_results")
        count = _count_place_cards(structured)
        if count > 0:
            raw_id = msg.get("id")
            source_id = str(raw_id) if raw_id is not None else None
            card_pool_size = count
            prior_card_pool = structured  # raw dict; used by context_resolver for card reuse
            break

    return ContextWindow(
        trip_id=trip_id,
        destination=destination,
        card_pool_size=card_pool_size,
        has_prior_cards=card_pool_size > 0,
        source_message_id=source_id,
        prior_user_prompts=user_prompts,
        prior_card_pool=prior_card_pool,
    )


# ── Observability ─────────────────────────────────────────────────────────────


def log_context_turn(
    *,
    trip_id: UUID,
    request_id: Optional[UUID] = None,
    turn_mode: TurnMode,
    rerank_rule: RerankRule,
    card_pool_size: int,
    has_prior_cards: bool,
    source_message_id: Optional[str] = None,
    reset_reason: Optional[str] = None,
    provider_call_expected_for_future_mode: bool = True,
) -> None:
    """Emit one structured log line per concierge turn for observability."""
    logger.info(
        "concierge.context.turn trip_id=%s request_id=%s turn_mode=%s rerank_rule=%s "
        "card_pool_size=%d has_prior_cards=%s "
        "provider_call_expected_for_future_mode=%s "
        "source_message_id=%s reset_reason=%s",
        trip_id,
        request_id,
        turn_mode,
        rerank_rule,
        card_pool_size,
        has_prior_cards,
        provider_call_expected_for_future_mode,
        source_message_id,
        reset_reason,
    )
