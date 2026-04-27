"""Deterministic why-pick reasoning with evidence chips."""

from __future__ import annotations

import re
from typing import Iterable, List, Literal, Optional, Sequence, TypedDict

BANNED_STRINGS_RE = re.compile(
    r"(source checked|editorial mention|source fit|evidence:|tavily|verification score|###|https?://)",
    re.IGNORECASE,
)

# Phrases that signal generic, template-level output — must never appear in why_pick.
GENERIC_PHRASES_RE = re.compile(
    r"(a strong pick for well-reviewed|guest feedback, location, and relevance|"
    r"polished night-out experience|viable option|great fit for this trip|"
    r"trusted place signals|fits this request as a google-verified|"
    r"well-reviewed food|well-reviewed drinks|matches this dining request|"
    r"matches this value-dinner request|fits this hotel request|"
    r"fits this Michelin request|is a strong attraction match|"
    r"\bwell-rated\b)",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
_PLACE_WORD_RE = re.compile(r"\b(?:in|near|at)\s+[A-Z][\w'’.-]*(?:\s+[A-Z][\w'’.-]*)*\b")


class WhyPick(TypedDict):
    text: str
    generation_method: Literal["deterministic"]


class WhyPickResult(TypedDict):
    why_pick: WhyPick
    template_id: Literal["rating_and_editorial", "editorial_only", "google_only", "fallback", "michelin"]


def _clean_chip(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip(" .,-")
    cleaned = re.sub(r"[\[\]#*`]+", "", cleaned).strip()
    return cleaned


def ensure_non_empty_evidence(
    evidence: Sequence[str],
    *,
    rating: Optional[float],
    review_count: Optional[int],
    neighborhood: Optional[str],
    tags: Optional[Iterable[str]],
) -> List[str]:
    chips: List[str] = []
    for value in evidence:
        clean = _clean_chip(value)
        if clean and clean not in chips and not BANNED_STRINGS_RE.search(clean):
            chips.append(clean)

    if not chips and rating is not None:
        if review_count and review_count > 0:
            chips.append(f"Rated {rating:.1f} ({int(review_count):,} reviews)")
        else:
            chips.append(f"Rated {rating:.1f}")

    if neighborhood and len(chips) < 2:
        chips.append(f"Near {neighborhood}")

    for tag in tags or []:
        clean_tag = _clean_chip(tag)
        if clean_tag and clean_tag.lower() not in {c.lower() for c in chips}:
            chips.append(clean_tag)
        if len(chips) >= 3:
            break

    if not chips:
        chips.append("Google verified listing")
    return chips[:3]


def _pick_template(evidence: Sequence[str], rating: Optional[float], review_count: Optional[int]) -> str:
    has_editorial = any("guide" in chip.lower() or "mention" in chip.lower() for chip in evidence)
    has_rating = rating is not None or any("rated" in chip.lower() or "review" in chip.lower() for chip in evidence)
    if has_editorial and has_rating:
        return "rating_and_editorial"
    if has_editorial:
        return "editorial_only"
    if has_rating:
        return "google_only"
    return "fallback"


def _normalize_phrase(value: Optional[str]) -> Optional[str]:
    clean = _clean_chip(value or "")
    return clean if clean else None


def _rating_phrase(rating: Optional[float], review_count: Optional[int], evidence: Sequence[str]) -> Optional[str]:
    if rating is not None:
        if review_count and int(review_count) > 0:
            return f"{float(rating):.1f} rating across {int(review_count):,} reviews"
        return f"{float(rating):.1f} rating"
    for chip in evidence:
        low = chip.lower()
        if "rated" in low or "review" in low:
            return chip
    return None


def _location_phrase(neighborhood: Optional[str]) -> Optional[str]:
    if not neighborhood:
        return None
    clean = _normalize_phrase(neighborhood)
    if not clean:
        return None
    if re.search(r"\b\d{1,6}\s+", clean):
        return None
    return clean.replace(", Chicago, IL", "").replace(", IL", "")


def _compose_text(
    *,
    template_id: str,
    place_name: str,
    evidence: Sequence[str],
    category: Optional[str],
    cuisine: Optional[str],
    neighborhood: Optional[str],
    michelin_status: Optional[str],
    intent: Optional[str],
    user_query: str,
    rating: Optional[float] = None,
    review_count: Optional[int] = None,
) -> str:
    place = place_name or "This place"
    cuisine_phrase = _normalize_phrase(cuisine)
    location = _location_phrase(neighborhood)
    query_low = (user_query or "").lower()
    is_hidden_gems = intent == "hidden_gems" or "hidden gem" in query_low
    is_cocktail = intent == "nightlife" or ("cocktail" in query_low and "bar" in query_low)
    is_value = "value" in query_low or intent == "luxury_value"

    # Prefer direct rating/review_count; fall back to scanning evidence chips.
    if rating is not None:
        if review_count and int(review_count) > 0:
            rating_str: Optional[str] = f"a {float(rating):.1f} rating across {int(review_count):,} reviews"
        else:
            rating_str = f"a {float(rating):.1f} rating"
    else:
        rating_str = None
        for chip in evidence:
            low = chip.lower()
            if "rated" in low or "review" in low:
                rating_str = chip.rstrip(".")
                break

    cuisine_low = cuisine_phrase.lower() if cuisine_phrase else None
    rating_part = f" with {rating_str}" if rating_str else ""

    # Michelin
    if michelin_status or template_id == "michelin":
        star_text = michelin_status or "Michelin-recognized"
        cuisine_part = f" {cuisine_low}" if cuisine_low else ""
        loc_part = f" {location}" if location else ""
        return (
            f"{place} is a {star_text}{loc_part}{cuisine_part} destination, "
            f"making it the top splurge option for a Michelin-focused dinner."
        )

    # Bar / cocktail bar
    if category == "bar" or is_cocktail:
        category_label = "cocktail bar" if is_cocktail else "bar"
        desc = f"{location + ' ' if location else ''}{category_label}"
        if is_hidden_gems:
            return (
                f"{place} is a lower-profile {desc}{rating_part}, "
                f"making it a strong local find away from tourist-heavy areas."
            )
        return f"{place} is a {desc}{rating_part}, making it a reliable nearby drinks option."

    # Restaurant
    if category == "restaurant":
        type_label = cuisine_low or "restaurant"
        if is_hidden_gems:
            spot_label = f"{location + ' ' if location else ''}{cuisine_low + ' ' if cuisine_low else ''}spot"
            return (
                f"{place} is a lower-profile {spot_label}{rating_part}, "
                f"making it a strong local favorite away from tourist-heavy areas."
            )
        desc = f"{location + ' ' if location else ''}{type_label}"
        if is_value:
            return f"{place} is a {desc}{rating_part}, offering a strong value alternative."
        return f"{place} is a {desc}{rating_part}, making it a top dining choice."

    # Hotel
    if category == "hotel":
        desc = f"{location + ' ' if location else ''}hotel"
        return f"{place} is a {desc}{rating_part}, making it a solid accommodation option."

    # Attraction
    if category == "attraction":
        type_label = cuisine_low or "attraction"
        desc = f"{location + ' ' if location else ''}{type_label}"
        return f"{place} is a {desc}{rating_part}, making it a top draw for this area."

    # Generic — still anchored to real data when available
    if rating_str:
        loc_bit = f" {location}" if location else ""
        type_bit = f" {cuisine_low}" if cuisine_low else ""
        return f"{place} is a{loc_bit}{type_bit} option{rating_part}."
    if location or cuisine_low:
        parts = [p for p in [location, cuisine_low] if p]
        return f"{place} is a {' '.join(parts)} option."
    return f"{place} is a verified place matching this request."


def has_concrete_fact(text: str) -> bool:
    if _NUMBER_RE.search(text):
        return True
    if _PLACE_WORD_RE.search(text):
        return True
    keyword_hits = ("guide", "michelin", "bar", "restaurant", "cafe", "hotel", "museum", "park", "reviews")
    return any(k in text.lower() for k in keyword_hits)


def build_why_pick(
    *,
    place_name: str,
    evidence: Sequence[str],
    rating: Optional[float],
    review_count: Optional[int],
    category: Optional[str] = None,
    neighborhood: Optional[str] = None,
    cuisine: Optional[str] = None,
    michelin_status: Optional[str] = None,
    user_query: str = "",
    intent: Optional[str] = None,
) -> WhyPickResult:
    template_id = "michelin" if category == "restaurant" and (
        michelin_status
        or intent == "michelin_restaurants"
        or any("michelin" in _clean_chip(ev).lower() for ev in evidence)
    ) else _pick_template(evidence, rating, review_count)

    concrete_evidence = list(evidence)
    rating_phrase = _rating_phrase(rating, review_count, concrete_evidence)
    if rating_phrase and all(rating_phrase.lower() != ev.lower() for ev in concrete_evidence):
        concrete_evidence = [rating_phrase, *concrete_evidence]

    text = _compose_text(
        template_id=template_id,
        place_name=place_name or "This place",
        evidence=concrete_evidence,
        category=category,
        cuisine=cuisine,
        neighborhood=neighborhood,
        michelin_status=michelin_status,
        intent=intent,
        user_query=user_query,
        rating=rating,
        review_count=review_count,
    )

    if BANNED_STRINGS_RE.search(text) or GENERIC_PHRASES_RE.search(text):
        loc = _location_phrase(neighborhood)
        loc_part = f" {loc}" if loc else ""
        rp = _rating_phrase(rating, review_count, concrete_evidence) or "verified place details"
        text = f"{place_name or 'This place'} is a{loc_part} option with {rp.lower()}."
    if "backed by rated" in text.lower() or "with rated" in text.lower():
        text = text.replace("backed by rated", "with a").replace("with rated", "with a")
    if not has_concrete_fact(text):
        loc = _location_phrase(neighborhood)
        loc_part = f" {loc}" if loc else ""
        rating_part = _rating_phrase(rating, review_count, concrete_evidence) or "verified place details"
        text = f"{place_name or 'This place'} is a{loc_part} option with {rating_part.lower()}."

    return {
        "why_pick": {"text": text, "generation_method": "deterministic"},
        "template_id": template_id,
    }
