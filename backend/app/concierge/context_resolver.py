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

_SUPPORTED_RULES: frozenset[str] = frozenset({"top_n", "best_one", "compare", "modifier_filter"})
_MAX_COMPARE_CARDS = 6

# Modifier words that indicate a desired casualness/price/formality direction.
# Used by modifier_filter to score and reorder prior verified cards.
_CASUAL_SIGNALS = frozenset({
    "casual", "chill", "relaxed", "laid-back", "laid back", "laidback",
    "informal", "low-key", "lowkey",
})
_FORMAL_SIGNALS = frozenset({
    "fancy", "fancier", "upscale", "elegant", "formal", "fine dining",
    "fine-dining", "luxury", "luxurious", "posh", "sophisticated",
})
_CHEAP_SIGNALS = frozenset({
    "cheap", "cheaper", "budget", "affordable", "inexpensive",
    "less expensive", "lower price", "economical",
})
_EXPENSIVE_SIGNALS = frozenset({
    "expensive", "pricey", "pricier", "luxury", "luxurious",
    "splurge", "high end", "high-end",
})

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


def _detect_modifier_intent(user_query: str) -> str:
    """Detect the dominant modifier intent from a modifier-only follow-up query.

    Returns one of: "casual", "formal", "cheap", "expensive", "none".
    """
    q = (user_query or "").lower()
    if any(s in q for s in _CASUAL_SIGNALS):
        return "casual"
    if any(s in q for s in _CHEAP_SIGNALS):
        return "cheap"
    if any(s in q for s in _FORMAL_SIGNALS):
        return "formal"
    if any(s in q for s in _EXPENSIVE_SIGNALS):
        return "expensive"
    return "none"


def _casual_fit_score(card: Dict[str, Any]) -> float:
    """Score how 'casual-friendly' a prior verified card appears (0.0–1.0).

    Uses Google price level and type signals from the card's google_verification.
    Does NOT use notes or enrichment — only structural Google fields.
    Higher = more casual-compatible.
    """
    gv = card.get("google_verification") or {}
    types = gv.get("types") or []
    types_lower = [t.lower() for t in types]

    # Fine-dining and expensive markers reduce casual fit
    penalty = 0.0
    if "fine_dining_restaurant" in types_lower:
        penalty += 0.4
    if "PRICE_LEVEL_VERY_EXPENSIVE" in types:
        penalty += 0.3
    elif "PRICE_LEVEL_EXPENSIVE" in types:
        penalty += 0.15

    # Casual-compatible markers boost casual fit
    boost = 0.0
    casual_type_terms = {
        "cafe", "coffee_shop", "fast_food_restaurant", "sandwich_shop",
        "pizza_restaurant", "burger_restaurant", "diner",
    }
    if any(t in types_lower for t in casual_type_terms):
        boost += 0.2
    if "PRICE_LEVEL_INEXPENSIVE" in types or "PRICE_LEVEL_FREE" in types:
        boost += 0.15

    return max(0.0, min(1.0, 0.5 + boost - penalty))


def _reorder_for_modifier(
    verified: List[Tuple[str, Dict[str, Any]]],
    modifier_intent: str,
) -> List[Tuple[str, Dict[str, Any]]]:
    """Reorder verified cards to surface those that best match the modifier."""
    if modifier_intent == "casual":
        return sorted(verified, key=lambda bc: _casual_fit_score(bc[1]), reverse=True)
    if modifier_intent == "cheap":
        # Sort by price level ascending (cheapest first)
        _price_order = {
            "PRICE_LEVEL_FREE": 0,
            "PRICE_LEVEL_INEXPENSIVE": 1,
            "PRICE_LEVEL_MODERATE": 2,
            "PRICE_LEVEL_EXPENSIVE": 3,
            "PRICE_LEVEL_VERY_EXPENSIVE": 4,
            "": 2,  # unknown → middle
        }
        def _price_key(bc: Tuple[str, Dict[str, Any]]) -> int:
            gv = bc[1].get("google_verification") or {}
            types = gv.get("types") or []
            for t in types:
                if t in _price_order:
                    return _price_order[t]
            return 2
        return sorted(verified, key=_price_key)
    if modifier_intent == "formal":
        # Reverse casual: sort by casual_fit ascending (formal first)
        return sorted(verified, key=lambda bc: _casual_fit_score(bc[1]))
    # expensive: prefer higher price levels
    if modifier_intent == "expensive":
        return sorted(verified, key=lambda bc: _casual_fit_score(bc[1]))
    return list(verified)


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

    modifier_intent = "none"
    if rerank_rule == "best_one":
        selected = verified[:1]
    elif rerank_rule == "top_n":
        n = _parse_top_n(user_query, len(verified))
        selected = verified[:n]
    elif rerank_rule == "modifier_filter":
        # Detect the modifier intent and reorder cards accordingly.
        # All prior verified cards are kept (we never drop cards on modifier alone —
        # the user may still want all of them, just reordered to surface better fits).
        modifier_intent = _detect_modifier_intent(user_query)
        reordered = _reorder_for_modifier(verified, modifier_intent)
        selected = reordered
        logger.info(
            "concierge.context_resolver.modifier_filter trip_id=%s "
            "modifier_intent=%s query=%r pool_before=%d pool_after=%d "
            "context_reuse=true provider_call_skipped=true",
            ctx.trip_id, modifier_intent, user_query, pool_size_before, len(selected),
        )
    else:  # compare
        selected = verified[:_MAX_COMPARE_CARDS]

    pool_size_after = len(selected)
    restaurants, attractions, hotels = _reassemble_buckets(selected)
    prior_intent = ctx.prior_card_pool.get("intent")

    logger.info(
        "concierge.context_resolver.resolved trip_id=%s turn_mode=refine_previous "
        "rerank_rule=%s modifier_intent=%s provider_call=false "
        "pool_size_before=%d pool_size_after=%d "
        "context_reuse=true prior_cards_reused_count=%d "
        "provider_call_skipped_for_refinement=true "
        "refinement_modifier_detected=%s refinement_rule_applied=%s "
        "source_message_id=%s feature_flag_enabled=true",
        ctx.trip_id,
        rerank_rule,
        modifier_intent,
        pool_size_before,
        pool_size_after,
        pool_size_after,
        modifier_intent if rerank_rule == "modifier_filter" else "",
        rerank_rule,
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
