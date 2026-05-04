"""Concierge context resolver — PR 2 refine_previous card reuse.

When feature flag concierge_context_v1_enabled is ON and turn_mode == refine_previous,
attempts to reuse verified cards from the prior assistant message pool for supported
rules (top_n, best_one, compare), skipping provider calls entirely.

PR 2 scope:
- Supported rules: top_n, best_one, compare
- All other rules: fall through to existing provider search (unchanged)
- No scoring, no reranking, no card mutation
- Trust gate: each card must have OPERATIONAL business_status, provider_place_id,
  google_maps_uri, and type == "verified_place"
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.concierge.context import ContextWindow, RerankRule

logger = logging.getLogger(__name__)

_SUPPORTED_RULES: frozenset[str] = frozenset({"top_n", "best_one", "compare"})
_MAX_COMPARE_CARDS = 6

_TOP_N_WORD_MAP: Dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
_TOP_N_RE = re.compile(
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\b",
    re.IGNORECASE,
)


@dataclass
class RefineResolved:
    """Successful refine resolution — reused verified cards and context metadata."""
    restaurants: List[Dict[str, Any]] = field(default_factory=list)
    attractions: List[Dict[str, Any]] = field(default_factory=list)
    hotels: List[Dict[str, Any]] = field(default_factory=list)
    pool_size_before: int = 0
    pool_size_after: int = 0
    rerank_rule: str = "none"
    source_message_id: Optional[str] = None
    prior_intent: Optional[str] = None


def _card_passes_trust_gate(card: Any) -> bool:
    """Return True only when the card has verified Google place identity.

    All four conditions must hold:
    - card is a dict with type == "verified_place"
    - google_verification.business_status == "OPERATIONAL"
    - google_verification.provider_place_id is non-empty
    - google_verification.google_maps_uri is non-empty
    """
    if not isinstance(card, dict):
        return False
    if card.get("type") != "verified_place":
        return False
    gv = card.get("google_verification")
    if not isinstance(gv, dict):
        return False
    if gv.get("business_status") != "OPERATIONAL":
        return False
    if not gv.get("provider_place_id"):
        return False
    if not gv.get("google_maps_uri"):
        return False
    return True


def _extract_pool_buckets(
    prior_card_pool: Dict[str, Any],
) -> List[Tuple[str, Dict[str, Any]]]:
    """Extract (bucket_name, card_dict) pairs preserving prior provider order."""
    result: List[Tuple[str, Dict[str, Any]]] = []
    for bucket in ("restaurants", "attractions", "hotels"):
        for card in (prior_card_pool.get(bucket) or []):
            if isinstance(card, dict):
                result.append((bucket, card))
    return result


def _parse_top_n(user_query: str, pool_size: int) -> int:
    """Parse N from 'top N' / 'show me N' queries. Clamps to [1, pool_size]."""
    for m in _TOP_N_RE.finditer(user_query or ""):
        token = m.group(1).lower()
        raw: Optional[int] = int(token) if token.isdigit() else _TOP_N_WORD_MAP.get(token)
        if raw is not None:
            return max(1, min(raw, pool_size))
    return min(3, pool_size)


def _reassemble_buckets(
    selected: List[Tuple[str, Dict[str, Any]]],
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Split (bucket, card) pairs back into three typed lists."""
    restaurants: List[Dict] = []
    attractions: List[Dict] = []
    hotels: List[Dict] = []
    for bucket, card in selected:
        if bucket == "restaurants":
            restaurants.append(card)
        elif bucket == "attractions":
            attractions.append(card)
        else:
            hotels.append(card)
    return restaurants, attractions, hotels


def resolve_refine_previous(
    ctx: ContextWindow,
    rerank_rule: RerankRule,
    user_query: str,
) -> Optional[RefineResolved]:
    """Attempt to resolve a refine_previous turn by reusing prior verified cards.

    Returns RefineResolved on success, or None to signal fall-through to the
    existing provider search path.

    Caller must check feature flag and turn_mode before calling this function.
    """
    if rerank_rule not in _SUPPORTED_RULES:
        logger.debug(
            "concierge.context_resolver.unsupported_rule rule=%s trip_id=%s "
            "fall_through_reason=unsupported_rule provider_call=true",
            rerank_rule,
            ctx.trip_id,
        )
        return None

    if not ctx.prior_card_pool:
        logger.info(
            "concierge.context_resolver.no_pool trip_id=%s "
            "fall_through_reason=no_prior_card_pool provider_call=true",
            ctx.trip_id,
        )
        return None

    all_cards = _extract_pool_buckets(ctx.prior_card_pool)
    pool_size_before = len(all_cards)

    verified = [(b, c) for b, c in all_cards if _card_passes_trust_gate(c)]
    dropped = pool_size_before - len(verified)
    if dropped > 0:
        logger.info(
            "concierge.context_resolver.cards_dropped dropped=%d verified=%d trip_id=%s",
            dropped,
            len(verified),
            ctx.trip_id,
        )

    if not verified:
        logger.info(
            "concierge.context_resolver.all_dropped_fall_through trip_id=%s "
            "fall_through_reason=all_cards_failed_trust_gate provider_call=true",
            ctx.trip_id,
        )
        return None

    if rerank_rule == "best_one":
        selected = verified[:1]
    elif rerank_rule == "top_n":
        n = _parse_top_n(user_query, len(verified))
        selected = verified[:n]
    else:  # compare
        selected = verified[:_MAX_COMPARE_CARDS]

    pool_size_after = len(selected)
    restaurants, attractions, hotels = _reassemble_buckets(selected)
    prior_intent = ctx.prior_card_pool.get("intent")

    logger.info(
        "concierge.context_resolver.resolved trip_id=%s turn_mode=refine_previous "
        "rerank_rule=%s provider_call=false pool_size_before=%d pool_size_after=%d "
        "source_message_id=%s feature_flag_enabled=true",
        ctx.trip_id,
        rerank_rule,
        pool_size_before,
        pool_size_after,
        ctx.source_message_id,
    )
    return RefineResolved(
        restaurants=restaurants,
        attractions=attractions,
        hotels=hotels,
        pool_size_before=pool_size_before,
        pool_size_after=pool_size_after,
        rerank_rule=rerank_rule,
        source_message_id=ctx.source_message_id,
        prior_intent=prior_intent,
    )
