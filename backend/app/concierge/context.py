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
    "cheapest", "most_upscale", "filter_constraint",
    "modifier_filter",  # style/price/geo modifier-only follow-up
    "none",
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
    # PR 2.5: derived category hint from prior pool intent (e.g. "cocktail bars", "restaurants").
    # Used by the more-options continuation path to construct a provider-facing query.
    prior_place_category: Optional[str] = None
    # PR 2.6: subtype-aware prior place phrase (e.g. "Italian restaurants").
    prior_place_query_hint: Optional[str] = None


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


# Continuation phrases: "more options" and equivalents.
# These are a subset of new_search override signals; the classifier correctly
# returns new_search for them. The continuation helper below uses these patterns
# to distinguish "more of the same" from a genuinely unrelated new search.
_CONTINUATION_PATTERNS = [
    re.compile(r"\bmore options\b", re.IGNORECASE),
    re.compile(r"\bshow more\b", re.IGNORECASE),
    re.compile(r"\bmore like these\b", re.IGNORECASE),
    re.compile(r"\bgive me more\b", re.IGNORECASE),
    re.compile(r"\banother batch\b", re.IGNORECASE),
]

# Venue category words — when any of these appear in the query, it is a new search
# even if it looks like a modifier-only phrase. This prevents "casual restaurants"
# from being misclassified as a modifier-only refinement of prior hotel cards.
_VENUE_CATEGORY_RE = re.compile(
    r"\b(restaurants?|bar|bars|cafe|cafes|cocktail|ramen|sushi|tacos?|taqueria|"
    r"hotels?|attraction|attractions|museum|museums|nightlife|"
    r"brewery|breweries|winery|wineries|taproom|bistro|tavern|diner|lounge)\b",
    re.IGNORECASE,
)

# Modifier-only utterances that should refine prior cards rather than trigger a
# fresh provider search. These patterns match SHORT follow-ups that contain only
# style/price/geo modifiers and NO venue category words.
#
# Examples that must route as refine_previous/modifier_filter:
#   "show only casual", "only casual", "just casual ones", "more casual",
#   "less fancy", "make it cheaper", "show cheaper ones", "near the river",
#   "with a view", "more affordable", "fancier ones".
#
# The pattern is intentionally narrow: it must not match queries containing
# venue category words (restaurants, bars, hotels, etc.) — those remain new_search.
_MODIFIER_ONLY_UTTERANCE_RE = re.compile(
    r"^\s*"
    # Optional leading refinement command words
    r"(?:show\s+(?:me\s+)?(?:only\s+)?|only\s+|just\s+|filter\s+(?:to\s+)?|"
    r"make\s+it\s+|get\s+(?:me\s+)?(?:the\s+)?|switch\s+to\s+)?"
    # Optional intensifier
    r"(?:(?:the\s+)?(?:more\s+|less\s+|even\s+(?:more\s+)?|"
    r"a\s+(?:bit\s+|little\s+)?|somewhat\s+))?"
    # Optional "only/just" before the modifier
    r"(?:only\s+|just\s+)?"
    # Core modifier: style, price, or geo (no venue category words allowed)
    r"(?:casual|chill|relaxed|laid[\s-]?back"
    r"|fancy|fancier|upscale|formal|elegant|fine[\s-]?dining"
    r"|cheap(?:er)?|budget|affordable|inexpensive|less[\s-]?expensive"
    r"|expensive|pricey|luxury|luxurious|pricier"
    r"|outdoor|outside"
    r"|nearby|closer"
    r"|with\s+a?\s+(?:view|patio|outdoor(?:\s+seating)?|terrace|rooftop)"
    r"|near\s+the\s+(?:river|lake|water|park|bay|ocean|harbor|waterfront)"
    r")"
    # Optional trailing nouns (ones, options, places, restaurants)
    r"(?:\s+(?:ones?|options?|places?|restaurants?|spots?|choices?|picks?))?"
    r"\s*$",
    re.IGNORECASE,
)

# Maps prior card pool intent to a provider-facing category phrase.
# Only intents that map cleanly to a searchable category are included.
# Omitted intents fall through to the bucket-based fallback.
_INTENT_TO_QUERY_HINT: Dict[str, str] = {
    "nightlife": "cocktail bars",
    "restaurants": "restaurants",
    "michelin_restaurants": "restaurants",
    "hidden_gems": "restaurants",
    "luxury_value": "restaurants",
    "romantic": "restaurants",
    "family_friendly": "attractions",
    "attractions": "attractions",
    "hotels": "hotels",
}


def derive_category_hint(prior_card_pool: Optional[Dict[str, Any]]) -> Optional[str]:
    """Derive a provider-facing category phrase from a prior card pool.

    Returns a phrase like 'cocktail bars', 'restaurants', 'attractions', or None
    when no safe derivation is possible (falls through to existing behavior).
    """
    if not isinstance(prior_card_pool, dict):
        return None

    intent = prior_card_pool.get("intent")
    if intent and isinstance(intent, str):
        hint = _INTENT_TO_QUERY_HINT.get(intent)
        if hint:
            return hint

    # Fall back to dominant bucket when intent is missing or unmapped.
    n_restaurants = len(prior_card_pool.get("restaurants") or [])
    n_attractions = len(prior_card_pool.get("attractions") or [])
    n_hotels = len(prior_card_pool.get("hotels") or [])

    if n_restaurants > 0 and n_restaurants >= n_attractions and n_restaurants >= n_hotels:
        return "restaurants"
    if n_attractions > 0 and n_attractions >= n_hotels:
        return "attractions"
    if n_hotels > 0:
        return "hotels"

    return None


def derive_prior_place_query_hint(
    prior_card_pool: Optional[Dict[str, Any]],
    prior_user_prompts: Optional[List[str]] = None,
) -> Optional[str]:
    """Derive a subtype-aware place query hint for continuation turns.

    Prefers the most recent explicit place phrase from prior prompts (e.g.
    "Italian restaurants"), then falls back to coarse category hint.
    """
    prompts = prior_user_prompts or []
    for raw_prompt in prompts:
        prompt = (raw_prompt or "").strip()
        if not prompt:
            continue
        m = re.search(
            r"\b([a-z][a-z\s&'-]{1,40})\s+"
            r"(restaurants?|bars?|cocktail bars?|coffee shops?|cafes?|attractions?|hotels?)\b",
            prompt,
            re.IGNORECASE,
        )
        if not m:
            continue
        phrase = re.sub(r"\s+", " ", m.group(0).strip().lower())
        if phrase.startswith(("more ", "show ", "give ", "another ")):
            continue
        return phrase
    return derive_category_hint(prior_card_pool)


def is_more_options_continuation(
    user_query: str,
    context_window: ContextWindow,
) -> bool:
    """Return True when the query is a continuation phrase and prior place cards exist.

    Continuation phrases mean "give me more of the same category" after a verified
    place search. Requires has_prior_cards so it falls through for fresh sessions.
    """
    if not context_window.has_prior_cards:
        return False
    text = (user_query or "").strip()
    return any(pat.search(text) for pat in _CONTINUATION_PATTERNS)


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

        # Modifier-only utterances: check BEFORE new_search_override so that
        # short follow-ups like "show only casual", "near the river", "cheaper ones"
        # route as refine_previous/modifier_filter instead of falling through to
        # a fresh provider search.
        # Guard: must not contain venue category words to avoid mis-classifying real new searches.
        if not _VENUE_CATEGORY_RE.search(text) and _MODIFIER_ONLY_UTTERANCE_RE.match(text):
            logger.debug(
                "concierge.context.modifier_only_refinement query=%r "
                "turn_mode=refine_previous rule=modifier_filter",
                text,
            )
            return "refine_previous", "modifier_filter"

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

    prior_place_category = derive_category_hint(prior_card_pool) if prior_card_pool else None
    prior_place_query_hint = derive_prior_place_query_hint(prior_card_pool, user_prompts) if prior_card_pool else None

    return ContextWindow(
        trip_id=trip_id,
        destination=destination,
        card_pool_size=card_pool_size,
        has_prior_cards=card_pool_size > 0,
        source_message_id=source_id,
        prior_user_prompts=user_prompts,
        prior_card_pool=prior_card_pool,
        prior_place_category=prior_place_category,
        prior_place_query_hint=prior_place_query_hint,
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
