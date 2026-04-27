"""Deterministic why-pick reasoning with evidence chips."""

from __future__ import annotations

import re
from typing import Iterable, List, Literal, Optional, Sequence, TypedDict

BANNED_STRINGS_RE = re.compile(
    r"(source checked|editorial mention|source fit|evidence:|tavily|verification score|###|https?://)",
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
) -> str:
    place = place_name or "This place"
    cuisine_phrase = _normalize_phrase(cuisine)
    location = _location_phrase(neighborhood)
    query_low = (user_query or "").lower()
    is_hidden_gems = intent == "hidden_gems" or "hidden gem" in query_low
    is_cocktail = intent == "nightlife" or ("cocktail" in query_low and "bar" in query_low)

    # Build concrete evidence phrases from available chips.
    concrete: List[str] = []
    for chip in evidence:
        clean = _normalize_phrase(chip)
        if clean and clean.lower() not in {c.lower() for c in concrete}:
            concrete.append(clean)

    rating_phrase = None
    for chip in concrete:
        low = chip.lower()
        if "rated" in low or "review" in low:
            rating_phrase = chip
            break
    if not rating_phrase:
        rating_phrase = "well-rated"

    if category == "restaurant" and (michelin_status or intent == "michelin_restaurants" or template_id == "michelin"):
        parts = [p for p in [michelin_status, cuisine_phrase, location] if p]
        if parts:
            return f"{place} fits this Michelin request as a {', '.join(parts)} option with {rating_phrase.lower()}."
        return f"{place} fits this Michelin request with {rating_phrase.lower()}."

    if category == "bar" or is_cocktail:
        category_text = "cocktail bar" if is_cocktail else "bar"
        loc = f" in {location}" if location else ""
        cuisine_bit = f" known for {cuisine_phrase.lower()}" if cuisine_phrase and category != "bar" else ""
        hidden = " with a lower-profile local feel" if is_hidden_gems else ""
        return f"{place} fits this request as a Google-verified {category_text}{loc} with {rating_phrase.lower()}{cuisine_bit}{hidden}."

    if category == "restaurant":
        cuisine_bit = f" for {cuisine_phrase.lower()}" if cuisine_phrase else ""
        loc = f" in {location}" if location else ""
        hidden = " with a lower-profile local profile" if is_hidden_gems else ""
        if "value" in query_low:
            return f"{place} matches this value-dinner request{cuisine_bit}{loc} with {rating_phrase.lower()}{hidden}."
        return f"{place} matches this dining request{cuisine_bit}{loc} with {rating_phrase.lower()}{hidden}."

    if category == "hotel":
        loc = f" in {location}" if location else ""
        return f"{place} fits this hotel request{loc} with {rating_phrase.lower()}."

    if category == "attraction":
        loc = f" in {location}" if location else ""
        return f"{place} is a strong attraction match{loc} with {rating_phrase.lower()}."

    if concrete:
        return f"{place} matches this request based on {concrete[0].lower()}."
    return f"{place} matches this request based on verified place details."


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
    )

    if BANNED_STRINGS_RE.search(text):
        text = f"{place_name or 'This place'} matches this request based on verified place details."
    if "backed by rated" in text.lower() or "with rated" in text.lower():
        text = text.replace("backed by rated", "with a").replace("with rated", "with a")
    if not has_concrete_fact(text):
        loc = _location_phrase(neighborhood)
        loc_part = f" in {loc}" if loc else ""
        rating_part = _rating_phrase(rating, review_count, concrete_evidence) or "verified place details"
        text = f"{place_name or 'This place'} matches this request{loc_part} with {rating_part.lower()}."

    return {
        "why_pick": {"text": text, "generation_method": "deterministic"},
        "template_id": template_id,
    }
