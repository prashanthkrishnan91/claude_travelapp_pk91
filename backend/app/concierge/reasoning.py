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
    template_id: Literal["rating_and_editorial", "editorial_only", "google_only", "fallback"]


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


def _compose_text(template_id: str, place_name: str, evidence: Sequence[str]) -> str:
    first = evidence[0]
    second = evidence[1] if len(evidence) > 1 else None
    if template_id == "rating_and_editorial" and second:
        return f"{place_name} stands out for {first.lower()} and {second.lower()}."
    if template_id == "editorial_only":
        return f"{place_name} is a practical pick based on {first.lower()}."
    if template_id == "google_only":
        return f"{place_name} is a solid choice with {first.lower()}."
    return f"{place_name} is a viable option with {first.lower()}."


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
) -> WhyPickResult:
    template_id = _pick_template(evidence, rating, review_count)
    text = _compose_text(template_id, place_name or "This place", evidence)
    low = text.lower()
    if category == "bar" and any(tok in low for tok in ("dining", "menu", "chef", "cuisine", "plates", "tasting menu")):
        text = f"{place_name or 'This place'} is a strong pick for well-reviewed drinks, atmosphere, and a polished night-out experience."
    elif category == "restaurant" and any(tok in low for tok in ("cocktail", "nightlife", "speakeasy", "bartender", "lounge")):
        text = f"{place_name or 'This place'} is a strong pick for well-reviewed food, polished service, and a comfortable dining setting."
    elif category == "bar" and not any(tok in low for tok in ("cocktail", "drinks", "atmosphere", "night-out", "night out")):
        text = f"{place_name or 'This place'} is a strong pick for well-reviewed drinks, atmosphere, and a polished night-out experience."
    elif category == "restaurant" and not any(tok in low for tok in ("food", "dining", "menu", "cuisine")):
        text = f"{place_name or 'This place'} is a strong pick for well-reviewed food, polished service, and a comfortable dining setting."
    if BANNED_STRINGS_RE.search(text):
        text = f"{place_name or 'This place'} is a viable option with {evidence[0].lower()}."
    if not has_concrete_fact(text):
        text = f"{place_name or 'This place'} is a viable option with {evidence[0].lower()} in this area."
    return {
        "why_pick": {"text": text, "generation_method": "deterministic"},
        "template_id": template_id,
    }
