"""SafeReasonBuilder v1 — deterministic, honest, ask-anchored reasons.

Phase 1 reasons must be:
- Safe (no hallucinated facts)
- Specific (anchored to the user's actual ask and verified data)
- Non-hallucinatory (no invented views, awards, ambiance, Michelin mentions)

Banned claims (never generated):
  - waterfront views / water views (always caveated — cannot be structurally verified)
  - romantic ambience / quietness / specific vibes
  - awards or Michelin mentions
  - "Strong X match in {city}" generic boilerplate
  - opening hours, prices, booking/reservation details

Format: "Verified {type} [on/in {location}] with {rating}★ across {N} Google reviews[; caveat]."
"""

from __future__ import annotations

import re
from typing import List, Optional

from app.concierge.frame_extractor import ExperienceFrame
from app.concierge.place_entity_layer import PlaceEntity
from app.concierge.ranker import MinimalEvidenceBundle, RankScore

_MAX_REASON_CHARS = 220

# Address fragments that indicate floor/unit/level info, NOT a neighborhood.
_NON_NEIGHBORHOOD_FRAGMENTS = frozenset({
    "lower level", "upper level", "ground floor", "ground level",
    "lobby level", "lobby", "basement", "mezzanine", "concourse",
    "suite", "ste", "floor", "unit", "apt", "apartment",
    "building", "bldg", "center", "centre", "mall", "terminal",
    "level", "room", "wing", "gate",
})

# Tokens that are modifier-only (never a true venue head). If the extracted
# primary concept happens to be one of these, the reason builder treats it
# as having no concept anchor.
_MODIFIER_ONLY_LABELS = {
    "waterfront", "riverwalk", "lakefront", "rooftop", "outdoor", "indoor",
    "patio", "terrace", "view", "views", "river", "lake", "ocean", "sea",
    "bay", "harbor", "harbour", "coast", "beachfront", "waterside",
    "downtown", "uptown", "midtown",
    "romantic", "intimate", "cozy", "cosy", "casual", "quiet", "lively",
    "trendy", "hip", "fancy", "upscale", "luxury", "modern", "elegant",
}

# Water/view-related geo hint tokens — always caveated, never asserted
_WATER_GEO_TOKENS = frozenset({
    "waterfront", "water", "river", "lake", "riverwalk", "lakefront",
    "harbor", "harbour", "marina", "pier", "dock", "bay", "coast",
    "shoreline", "beachfront", "waterside",
})


def _clip(text: str, max_chars: int = _MAX_REASON_CHARS) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    last_period = cut.rfind(".")
    if last_period > max_chars // 2:
        return cut[:last_period + 1]
    return cut.rstrip() + "…"


def _area_from_address(address: Optional[str], destination: str) -> Optional[str]:
    """Extract short neighborhood/area from formatted address.

    Skips floor/level/unit fragments and the destination city itself.
    """
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
        p_lower = p.lower()
        if p_lower in {"usa", "us", "il", "ny", "ca", "tx", "fl", "wa", "il 60601"}:
            continue
        if p_lower == dest_lower:
            continue
        if p_lower in _NON_NEIGHBORHOOD_FRAGMENTS:
            continue
        if any(p_lower.startswith(frag) for frag in _NON_NEIGHBORHOOD_FRAGMENTS if len(frag) > 4):
            continue
        return p
    return None


def _location_modifier_phrase(
    evidence: MinimalEvidenceBundle,
    frame: ExperienceFrame,
    area: Optional[str],
) -> tuple:
    """Return (confirmed_modifier, caveat_text) for location modifiers.

    confirmed_modifier: the modifier string if address confirms it, else "".
    caveat_text: honest caveat sentence when modifier is requested but unconfirmed.
    """
    location_modifiers = getattr(frame, "location_modifiers", []) or []
    if not location_modifiers:
        return "", ""

    modifier = location_modifiers[0]

    for flag in evidence.uncertainty_flags:
        if flag.startswith("location_modifier_not_confirmed:"):
            caveat = f"Not directly on {modifier} — nearest match in {area or frame.destination or 'the area'}."
            return "", caveat

    for fact in evidence.structured_facts:
        if "confirms" in fact and modifier.lower() in fact.lower():
            return modifier, ""

    return "", ""


def build_safe_reason(
    entity: PlaceEntity,
    evidence: MinimalEvidenceBundle,
    frame: ExperienceFrame,
    rank_score: RankScore,
) -> str:
    """Build a deterministic, honest, ask-anchored reason for a ranked entity.

    Format: "Verified {type} [on/in {location}] with {rating}★ across {N} Google reviews."
    Followed by caveats for unconfirmed geo/location modifiers.

    Never emits:
    - "Strong X match in {city}" (generic boilerplate)
    - Unsupported waterfront/view/riverwalk claims
    - Invented awards, hours, prices, or ambiance

    Args:
        entity: Verified PlaceEntity.
        evidence: MinimalEvidenceBundle for this entity.
        frame: ExperienceFrame with the user's ask context.
        rank_score: RankScore for this entity (used for geo confirmation check).

    Returns:
        A short, honest reason string (≤ _MAX_REASON_CHARS characters).
    """
    destination = frame.destination
    primary_concept = frame.subtype_concepts[0].label if frame.subtype_concepts else ""
    if primary_concept and primary_concept.strip().lower() in _MODIFIER_ONLY_LABELS:
        primary_concept = ""
    geo_hints = frame.geography_hints
    ambiguity_flags = getattr(frame, "ambiguity_flags", []) or []

    area = _area_from_address(entity.formatted_address, destination)

    # Location modifier (explicit street/neighborhood in the user's query)
    confirmed_modifier, loc_modifier_caveat = _location_modifier_phrase(
        evidence, frame, area
    )

    # Type label: use concept if present (more specific), else Google type
    type_label = primary_concept.title() if primary_concept else ""
    if not type_label:
        if entity.primary_type:
            type_label = entity.primary_type.replace("_", " ").title()
        elif entity.types:
            type_label = entity.types[0].replace("_", " ").title()

    # Opening: "Verified {type}" or generic "Verified Google place"
    opening = f"Verified {type_label}" if type_label else "Verified Google place"

    # Add specific location when confirmed
    if confirmed_modifier:
        opening += f" on {confirmed_modifier}"
    elif area and area.strip().lower() != (destination or "").strip().lower():
        # Use neighborhood/area from address only if it is NOT the destination city.
        # Never append " in {destination}" — that is generic and useless.
        opening += f" in {area}"

    # Rating part: use raw facts, no qualitative wrappers
    rating = entity.rating
    review_count = entity.user_rating_count
    if rating is not None and review_count:
        rating_part = f"{rating:.1f}★ across {review_count:,} Google reviews"
    elif rating is not None:
        rating_part = f"{rating:.1f}★ on Google"
    else:
        rating_part = ""

    # Core note
    if rating_part:
        core = f"{opening} with {rating_part}."
    else:
        core = f"{opening}."

    # Geo caveat: honest about what was requested but not confirmed.
    # We NEVER assert waterfront/river/lake/view proximity — always caveat.
    geo_caveat = ""
    if geo_hints:
        geo_hint = geo_hints[0]
        hint_lower = geo_hint.lower()
        is_water_related = any(w in hint_lower for w in _WATER_GEO_TOKENS)
        if is_water_related:
            geo_caveat = (
                f"The requested {geo_hint} setting is not confirmed in available data."
            )

    # Also check ambiguity_flags regardless of geo_hints — "taprooms with a view"
    # sets the flag even though "view" may not appear in geo_hints.
    if not geo_caveat:
        for flag in ambiguity_flags:
            flag_lower = flag.lower()
            if "view" in flag_lower or "waterfront" in flag_lower:
                geo_caveat = "The requested view cannot be structurally verified."
                break

    if loc_modifier_caveat:
        core += f" {loc_modifier_caveat}"
    if geo_caveat:
        core += f" {geo_caveat}"

    return _clip(core)
