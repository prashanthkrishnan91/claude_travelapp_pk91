"""SafeReasonBuilder v1 — deterministic, honest, ask-anchored reasons.

Phase 1 reasons are not final concierge-grade LLM reasons. They must be:
- Safe (no hallucinated facts)
- Specific enough (anchored to the user's actual ask)
- Non-hallucinatory (no invented views, awards, ambiance, Michelin mentions)

Banned claims (never generated):
  - waterfront views / water views (unless address confirms proximity)
  - romantic ambience / quietness / specific vibes
  - awards or Michelin mentions
  - exact neighborhoods (unless from formatted_address)
  - opening hours, prices, booking/reservation details

Weak-evidence wrapper ("Verify when booking") is used ONLY for attributes the
user explicitly asked for that cannot be structurally confirmed from Google fields.
"""

from __future__ import annotations

import re
from typing import List, Optional

from app.concierge.frame_extractor import ExperienceFrame
from app.concierge.place_entity_layer import PlaceEntity
from app.concierge.ranker import MinimalEvidenceBundle, RankScore

_PRICE_LEVEL_LABEL = {
    "PRICE_LEVEL_INEXPENSIVE": "budget-friendly",
    "PRICE_LEVEL_MODERATE": "mid-range",
    "PRICE_LEVEL_EXPENSIVE": "upscale",
    "PRICE_LEVEL_VERY_EXPENSIVE": "fine-dining",
}

_MAX_REASON_CHARS = 220

# Attributes the user might request that cannot be verified structurally
_WEAK_VERIFY_ATTRIBUTES = {
    "waterfront", "water view", "river view", "lake view", "ocean view",
    "riverwalk", "lakefront", "view", "quiet", "not_loud", "romantic",
    "intimate", "cozy", "ambiance", "vibe",
}

# Tokens that are modifier-only (never a true venue head). If the extracted
# primary concept happens to be one of these, the reason builder will treat
# it as having no concept anchor instead of saying "Good waterfront match".
_MODIFIER_ONLY_LABELS = {
    "waterfront", "riverwalk", "lakefront", "rooftop", "outdoor", "indoor",
    "patio", "terrace", "view", "views", "river", "lake", "ocean", "sea",
    "bay", "harbor", "harbour", "coast", "beachfront", "waterside",
    "downtown", "uptown", "midtown",
    "romantic", "intimate", "cozy", "cosy", "casual", "quiet", "lively",
    "trendy", "hip", "fancy", "upscale", "luxury", "modern", "elegant",
}


def _clip(text: str, max_chars: int = _MAX_REASON_CHARS) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    # Clip at last sentence boundary before limit
    cut = text[:max_chars]
    last_period = cut.rfind(".")
    if last_period > max_chars // 2:
        return cut[:last_period + 1]
    return cut.rstrip() + "…"


def _area_from_address(address: Optional[str], destination: str) -> Optional[str]:
    """Extract short neighborhood/area from formatted address."""
    if not address:
        return None
    dest_lower = (destination or "").lower()
    parts = [p.strip() for p in address.split(",")]
    for part in parts:
        p = part.strip()
        if not p or any(c.isdigit() for c in p):
            continue
        if len(p) <= 2:
            continue
        if p.lower() in {"usa", "us", "il", "ny", "ca", "tx", "fl", "wa", "il 60601"}:
            continue
        if p.lower() == dest_lower:
            continue
        return p
    return None


def _rating_phrase(entity: PlaceEntity) -> str:
    if entity.rating is not None and entity.user_rating_count:
        if entity.user_rating_count >= 1500:
            return f"one of the most-reviewed ({entity.rating:.1f}★)"
        if entity.user_rating_count >= 400:
            return f"consistently well-rated ({entity.rating:.1f}★)"
        if entity.user_rating_count >= 100:
            return f"well-regarded ({entity.rating:.1f}★)"
        return f"{entity.rating:.1f}★"
    if entity.rating is not None:
        return f"{entity.rating:.1f}★"
    return ""


def _price_phrase(entity: PlaceEntity) -> str:
    return _PRICE_LEVEL_LABEL.get(entity.price_level or "", "")


def _verify_wrapper(attributes: List[str]) -> str:
    """Build a 'verify when booking' suffix for explicitly requested weak attributes."""
    if not attributes:
        return ""
    joined = " and ".join(a.replace("_", " ") for a in attributes[:2])
    return f"Verify {joined} before booking."


def build_safe_reason(
    entity: PlaceEntity,
    evidence: MinimalEvidenceBundle,
    frame: ExperienceFrame,
    rank_score: RankScore,
) -> str:
    """Build a deterministic, honest, ask-anchored reason for a ranked entity.

    The reason:
    1. Mentions the primary ask anchor (brewery, tapas, sushi, etc.)
    2. States the verification basis (Google-verified OPERATIONAL place)
    3. Mentions geo proximity only when supported by data
    4. Uses "Verify when booking" only for user-requested weak attributes
    5. Never invents views, awards, ambiance, quietness, prices, or hours

    Args:
        entity: Verified PlaceEntity.
        evidence: MinimalEvidenceBundle for this entity.
        frame: ExperienceFrame with the user's ask context.
        rank_score: RankScore with subtype_fit and geo_fit for this entity.

    Returns:
        A short, honest reason string (≤ _MAX_REASON_CHARS characters).
    """
    destination = frame.destination
    primary_concept = frame.subtype_concepts[0].label if frame.subtype_concepts else ""
    # Defensive: never treat a pure modifier word as a venue head in the
    # user-visible reason text. This prevents repetition like
    # "Good waterfront match" on every card if upstream extraction misfires.
    if primary_concept and primary_concept.strip().lower() in _MODIFIER_ONLY_LABELS:
        primary_concept = ""
    geo_hints = frame.geography_hints
    soft_prefs = frame.soft_preferences
    neg_constraints = frame.negative_constraints
    value_signals = frame.value_signals

    area = _area_from_address(entity.formatted_address, destination)
    loc_part = f" in {area}" if area else f" in {destination}" if destination else ""

    rating_phrase = _rating_phrase(entity)
    price_phrase = _price_phrase(entity)

    # Determine which user-requested attributes are weakly verified
    weak_attrs: List[str] = []
    for attr in geo_hints:
        if attr.lower() in _WEAK_VERIFY_ATTRIBUTES and rank_score.geo_fit < 0.80:
            weak_attrs.append(attr)
    for attr in neg_constraints:
        if attr.lower().replace("_", " ") in _WEAK_VERIFY_ATTRIBUTES:
            weak_attrs.append(attr.replace("_", " "))
    if "romantic" in soft_prefs or "intimate" in soft_prefs:
        if rank_score.subtype_fit < 0.9:
            weak_attrs.append("romantic ambiance")

    verify_suffix = _verify_wrapper(weak_attrs) if weak_attrs else ""

    # ── Build the core reason ─────────────────────────────────────────────────

    if primary_concept:
        # Has a strong concept match
        if rank_score.subtype_fit >= 0.80:
            match_qual = f"Strong {primary_concept} match"
        elif rank_score.subtype_fit >= 0.55:
            match_qual = f"Good {primary_concept} match"
        else:
            match_qual = f"Returned for {primary_concept} search"

        # Geo context: honest phrasing. Only state proximity when the entity
        # address actually confirms it (geo_fit ≥ 0.80). For weaker signals
        # the verify suffix handles transparency, so we omit the geo phrase
        # to avoid the same line ("Good waterfront match") repeating on
        # every card in a turn.
        if geo_hints and rank_score.geo_fit >= 0.80:
            geo_phrase = f"near {geo_hints[0]}"
        else:
            geo_phrase = ""

        parts: List[str] = [f"{match_qual}{loc_part}"]
        if geo_phrase:
            parts[0] += f", {geo_phrase}"
        parts[0] += "."

        # Add rating/quality signal
        if rating_phrase:
            rating_prefix = f"{price_phrase}, " if price_phrase else ""
            parts.append(f"Verified Google place; {rating_prefix}{rating_phrase}.")

        # Add verify wrapper for weak attributes
        if verify_suffix:
            parts.append(verify_suffix)

        reason = " ".join(parts)

    else:
        # No concept extracted — generic but still honest
        base = f"Verified Google place{loc_part}"
        if rating_phrase:
            price_prefix = f"{price_phrase}, " if price_phrase else ""
            base += f"; {price_prefix}{rating_phrase}"
        base += "."
        if verify_suffix:
            base += f" {verify_suffix}"
        reason = base

    return _clip(reason)
