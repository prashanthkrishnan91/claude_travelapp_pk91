"""SafeReasonBuilder v1 — evidence-first, name-anchored deterministic fallback.

This module is the FALLBACK for when LLM-based batched reasoning is unavailable.
The primary path is batched_reason_builder.py (auto-enabled when ANTHROPIC_API_KEY present).

Design contract:
- Notes are anchored to the place's actual NAME and STREET, not to a type-template.
- "Goose Island Brewery on Fulton Street — 4.5★ from 1,159 reviews." is acceptable.
- "Verified Brewery with 4.5★ across 1,159 reviews." is BANNED — it is a type-template
  that provides no card-specific evidence.
- Returns "" when the only available evidence is venue type + city + rating.
  An empty note is better than a generic template.

Banned output patterns (enforced by reason_validator.py):
  - "Strong {venue} match in {city}."          ← generic match boilerplate
  - "Verified {category} with {rating}★ across {N} reviews."  ← type template
  - any claim of waterfront/view/river/award/Michelin/hours/prices
  - any note that could be generated without card-specific evidence
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

# Tokens that are modifier-only (never a true venue head).
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

# Common street-name suffix abbreviations for expansion
_STREET_SUFFIX_EXPANSIONS = {
    r"\bSt\b": "Street", r"\bAve\b": "Avenue", r"\bBlvd\b": "Boulevard",
    r"\bDr\b": "Drive", r"\bRd\b": "Road", r"\bPl\b": "Place",
    r"\bCt\b": "Court", r"\bLn\b": "Lane", r"\bFwy\b": "Freeway",
    r"\bHwy\b": "Highway", r"\bPkwy\b": "Parkway", r"\bMkt\b": "Market",
}


def _clip(text: str, max_chars: int = _MAX_REASON_CHARS) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    last_period = cut.rfind(".")
    if last_period > max_chars // 2:
        return cut[:last_period + 1]
    return cut.rstrip() + "…"


def _street_name_from_address(address: Optional[str]) -> Optional[str]:
    """Extract the street name from a formatted address.

    "1800 W Fulton St, Chicago, IL" → "Fulton Street"
    "4257 N Lincoln Ave, Chicago, IL" → "Lincoln Avenue"
    "95 W Ontario St, Chicago, IL" → "Ontario Street"

    Returns None when no recognizable street name is found.
    """
    if not address:
        return None
    first_part = address.split(",")[0].strip()
    # Remove leading street number
    without_number = re.sub(r"^\d+\s*", "", first_part).strip()
    # Remove leading directional (W, E, N, S, NW, SW, NE, SE)
    without_dir = re.sub(r"^(?:North|South|East|West|NW|SW|NE|SE|N|S|E|W)\s+",
                         "", without_number, flags=re.IGNORECASE).strip()
    # Expand common abbreviations
    result = without_dir
    for pattern, replacement in _STREET_SUFFIX_EXPANSIONS.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    result = result.strip()
    # Must be at least 3 chars and not look like a zip code or state
    if len(result) >= 3 and not re.match(r"^\d", result):
        return result
    return None


def _area_from_address(address: Optional[str], destination: str) -> Optional[str]:
    """Extract short neighborhood/area from formatted address.

    Skips floor/level/unit fragments and the destination city itself.
    Only returns a value when there is a meaningful intermediate segment
    (e.g., a neighborhood like "Wicker Park" if Google includes it).
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
        if p_lower in {"usa", "us", "il", "ny", "ca", "tx", "fl", "wa"}:
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
    """Return (confirmed_modifier, caveat_text) for location modifiers."""
    location_modifiers = getattr(frame, "location_modifiers", []) or []
    if not location_modifiers:
        return "", ""

    modifier = location_modifiers[0]

    for flag in evidence.uncertainty_flags:
        if flag.startswith("location_modifier_not_confirmed:"):
            caveat = (
                f"Not directly on {modifier} — nearest match in "
                f"{area or frame.destination or 'the area'}."
            )
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
    """Build an evidence-first, name-anchored deterministic note.

    This is the FALLBACK for when LLM reasoning is unavailable. It anchors
    on the place's actual name and street address — not on a type-template.

    Returns "" when the only available evidence is generic (type + city + rating)
    and no card-specific differentiator (name signal, street, modifier) is present.

    The banned pattern "Verified {type} with {rating}★ across {N} reviews." is
    NOT produced here — that tells the user nothing card-specific.

    Args:
        entity: Verified PlaceEntity.
        evidence: MinimalEvidenceBundle for this entity.
        frame: ExperienceFrame with the user's ask context.
        rank_score: RankScore for this entity.

    Returns:
        A short, evidence-specific note (≤ _MAX_REASON_CHARS chars), or "".
    """
    destination = frame.destination
    primary_concept = frame.subtype_concepts[0].label if frame.subtype_concepts else ""
    if primary_concept and primary_concept.strip().lower() in _MODIFIER_ONLY_LABELS:
        primary_concept = ""
    geo_hints = frame.geography_hints
    ambiguity_flags = getattr(frame, "ambiguity_flags", []) or []

    # ── Gather card-specific evidence ────────────────────────────────────────

    # 1. Street name from address (specific to this card)
    street = _street_name_from_address(entity.formatted_address)

    # 2. Location modifier handling
    area = _area_from_address(entity.formatted_address, destination)
    confirmed_modifier, loc_modifier_caveat = _location_modifier_phrase(evidence, frame, area)

    # 3. Does the place name contain the requested concept? (name is informative)
    concept_in_name = bool(
        primary_concept
        and any(
            tok in entity.name.lower()
            for tok in primary_concept.lower().split()
            if len(tok) >= 4
        )
    )

    # 4. Rating context
    rating = entity.rating
    review_count = entity.user_rating_count or 0
    has_rating = rating is not None and review_count >= 50

    # ── Gate: require at least one card-specific differentiator ──────────────
    # If all we have is type + city + rating, return "" — the LLM path
    # or a "limited evidence" placeholder is better than a type-template.
    has_specific_location = bool(street and street.lower() != (destination or "").lower()) or bool(confirmed_modifier)
    has_name_signal = concept_in_name or len(entity.name.split()) >= 2

    if not has_specific_location and not has_name_signal and not has_rating:
        return ""

    # ── Build the lead: anchored on name + specific location ─────────────────
    place_name = entity.name.strip()

    if confirmed_modifier:
        lead = f"{place_name} on {confirmed_modifier}"
    elif street:
        lead = f"{place_name} on {street}"
    else:
        # Name alone is specific (still card-specific, not a type-template)
        lead = place_name

    # ── Rating segment ────────────────────────────────────────────────────────
    if has_rating:
        if review_count >= 1000:
            rating_part = f"{rating:.1f}★ from {review_count:,} reviews"
        elif review_count >= 200:
            rating_part = f"{rating:.1f}★ ({review_count:,} reviews)"
        else:
            rating_part = f"{rating:.1f}★"
    else:
        rating_part = ""

    # ── Assemble core note ────────────────────────────────────────────────────
    if rating_part:
        core = f"{lead} — {rating_part}."
    else:
        core = f"{lead}."

    # ── Geo caveat: honest about unconfirmed modifiers ────────────────────────
    # We NEVER positively claim waterfront/river/view proximity.
    geo_caveat = ""
    if geo_hints:
        geo_hint = geo_hints[0]
        hint_lower = geo_hint.lower()
        if any(w in hint_lower for w in _WATER_GEO_TOKENS):
            geo_caveat = f"No {geo_hint} proximity confirmed from address."

    if not geo_caveat:
        for flag in ambiguity_flags:
            if "view" in flag.lower() or "waterfront" in flag.lower():
                geo_caveat = "The requested view setting is not verified."
                break

    # ── Location modifier caveat ──────────────────────────────────────────────
    if loc_modifier_caveat:
        core += f" {loc_modifier_caveat}"
    if geo_caveat:
        core += f" {geo_caveat}"

    return _clip(core)
