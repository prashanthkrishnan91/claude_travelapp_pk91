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


def _compose_text(
    *,
    template_id: str,
    place_name: str,
    evidence: Sequence[str],
    category: Optional[str],
    cuisine: Optional[str],
    neighborhood: Optional[str],
    michelin_status: Optional[str],
) -> str:
    place = place_name or "This place"
    first = _normalize_phrase(evidence[0]) or "solid local fit"
    second = _normalize_phrase(evidence[1] if len(evidence) > 1 else None)
    cuisine_phrase = _normalize_phrase(cuisine)
    neighborhood_phrase = _normalize_phrase(neighborhood)
    michelin_phrase = _normalize_phrase(michelin_status)

    if (category == "restaurant" and michelin_phrase) or template_id == "michelin":
        details = [michelin_phrase, cuisine_phrase, neighborhood_phrase]
        detail_blob = ", ".join([d for d in details if d])
        if detail_blob:
            return f"{place} is a {detail_blob} pick that fits this Michelin-focused request."
        return f"{place} is a Michelin-oriented restaurant choice with strong fit for this request."

    if category == "bar":
        location = f" in {neighborhood_phrase}" if neighborhood_phrase else ""
        support = f" with {second.lower()}" if second else ""
        return f"{place} is a cocktail-forward bar{location}, backed by {first.lower()}{support}."
    if category == "restaurant":
        cuisine_bit = f" for {cuisine_phrase.lower()} cuisine" if cuisine_phrase else ""
        location = f" in {neighborhood_phrase}" if neighborhood_phrase else ""
        support = f" and {second.lower()}" if second else ""
        return f"{place} is a strong restaurant pick{cuisine_bit}{location}, supported by {first.lower()}{support}."
    if category == "hotel":
        location = f" in {neighborhood_phrase}" if neighborhood_phrase else ""
        support = f" and {second.lower()}" if second else ""
        return f"{place} is a reliable hotel option{location}, with {first.lower()}{support}."
    if category == "attraction":
        location = f" in {neighborhood_phrase}" if neighborhood_phrase else ""
        support = f" and {second.lower()}" if second else ""
        return f"{place} is a high-fit attraction{location}, with {first.lower()}{support}."
    if template_id == "rating_and_editorial" and second:
        return f"{place} stands out for {first.lower()} and {second.lower()}."
    if template_id == "editorial_only":
        return f"{place} is a practical pick based on {first.lower()}."
    if template_id == "google_only":
        return f"{place} is a solid choice with {first.lower()}."
    return f"{place} is a viable option with {first.lower()}."


def has_concrete_fact(text: str) -> bool:
    if _NUMBER_RE.search(text):
        return True
    if _PLACE_WORD_RE.search(text):
        return True
    keyword_hits = ("guide", "michelin", "bar", "restaurant", "cafe", "hotel", "museum", "park")
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
) -> WhyPickResult:
    template_id = "michelin" if category == "restaurant" and michelin_status else _pick_template(evidence, rating, review_count)
    text = _compose_text(
        template_id=template_id,
        place_name=place_name or "This place",
        evidence=evidence,
        category=category,
        cuisine=cuisine,
        neighborhood=neighborhood,
        michelin_status=michelin_status,
    )
    low = text.lower()
    if category == "bar" and any(tok in low for tok in ("dining", "menu", "chef", "cuisine", "plates", "tasting menu")):
        text = f"{place_name or 'This place'} is a cocktail-focused bar in {neighborhood or 'this area'}, backed by {evidence[0].lower()}."
    elif category == "restaurant" and any(tok in low for tok in ("cocktail", "nightlife", "speakeasy", "bartender", "lounge")):
        text = f"{place_name or 'This place'} is a dining-focused restaurant in {neighborhood or 'this area'}, supported by {evidence[0].lower()}."
    elif category == "bar" and not any(tok in low for tok in ("cocktail", "drinks", "bar")):
        text = f"{place_name or 'This place'} is a bar pick in {neighborhood or 'this area'}, with {evidence[0].lower()}."
    elif category == "restaurant" and not any(tok in low for tok in ("food", "dining", "menu", "cuisine", "restaurant", "michelin")):
        text = f"{place_name or 'This place'} is a restaurant pick in {neighborhood or 'this area'}, with {evidence[0].lower()}."
    if BANNED_STRINGS_RE.search(text):
        text = f"{place_name or 'This place'} is a viable option with {evidence[0].lower()}."
    if not has_concrete_fact(text):
        text = f"{place_name or 'This place'} is a viable option with {evidence[0].lower()} in this area."
    return {
        "why_pick": {"text": text, "generation_method": "deterministic"},
        "template_id": template_id,
    }
