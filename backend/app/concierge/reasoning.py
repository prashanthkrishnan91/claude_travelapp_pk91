"""Deterministic why-pick reasoning with evidence chips."""

from __future__ import annotations

import re
from typing import Iterable, List, Literal, Optional, Sequence, Tuple, TypedDict

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


def _location_area_phrase(neighborhood: Optional[str]) -> Optional[str]:
    loc = _location_phrase(neighborhood)
    if not loc:
        return None
    if "," not in loc:
        return loc
    parts = [p.strip() for p in loc.split(",") if p.strip()]
    for part in parts[1:]:
        if not re.search(r"\b\d{1,6}\b", part):
            return part
    return parts[0] if parts else None


def _price_level_phrase(price_level: Optional[int]) -> Optional[str]:
    if price_level is None:
        return None
    try:
        p = int(price_level)
    except (TypeError, ValueError):
        return None
    if p <= 1:
        return "inexpensive pricing"
    if p == 2:
        return "moderate pricing"
    if p >= 4:
        return "very expensive pricing"
    return "expensive pricing"


def _editorial_phrase(evidence: Sequence[str]) -> Optional[str]:
    for chip in evidence:
        low = chip.lower()
        if "michelin" in low:
            continue
        if any(tok in low for tok in ("guide", "list", "editor", "featured", "recommended", "infatuation", "eater")):
            return chip.rstrip(".")
    return None


def _tag_or_sentiment_phrase(evidence: Sequence[str]) -> Optional[str]:
    for chip in evidence:
        low = chip.lower()
        if any(tok in low for tok in ("foursquare", "yelp", "tag", "sentiment")):
            return chip.rstrip(".")
    return None


def _value_evidence_phrase(
    evidence: Sequence[str],
    *,
    price_level: Optional[int],
) -> Optional[str]:
    price_phrase = _price_level_phrase(price_level)
    if price_phrase and int(price_level or 0) <= 2:
        return price_phrase
    for chip in evidence:
        low = chip.lower()
        if any(tok in low for tok in ("affordable", "budget", "good deal", "prix fixe", "happy hour", "inexpensive")):
            return chip.rstrip(".")
        if "value" in low and any(tok in low for tok in ("$", "price", "priced", "menu", "cost", "under", "around")):
            return chip.rstrip(".")
        if "$" in chip and any(tok in low for tok in ("under", "around", "from", "prix")):
            return chip.rstrip(".")
    return None


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
    price_level: Optional[int] = None,
) -> str:
    place = place_name or "This place"
    cuisine_phrase = _normalize_phrase(cuisine)
    location = _location_area_phrase(neighborhood) or _location_phrase(neighborhood)
    query_low = (user_query or "").lower()
    is_cocktail = category == "bar" or intent == "nightlife" or ("cocktail" in query_low and "bar" in query_low)
    rating_signal = _rating_phrase(rating, review_count, evidence)
    editorial_signal = _editorial_phrase(evidence)
    tag_signal = _tag_or_sentiment_phrase(evidence)
    value_signal = _value_evidence_phrase(evidence, price_level=price_level)
    has_michelin_evidence = bool(michelin_status) or any("michelin" in _clean_chip(ev).lower() for ev in evidence)

    if has_michelin_evidence and category == "restaurant":
        loc_part = f" in {location}" if location else ""
        cuisine_part = f" for {cuisine_phrase.lower()}" if cuisine_phrase else ""
        rating_part = f", with {rating_signal}" if rating_signal else ""
        star_text = michelin_status or "Michelin-recognized"
        return f"{place} is {star_text}{loc_part}{cuisine_part}{rating_part}."

    if category == "restaurant":
        category_phrase = cuisine_phrase.lower() if cuisine_phrase else "restaurant"
    elif is_cocktail:
        category_phrase = "cocktail bar"
    elif category:
        category_phrase = category.replace("_", " ")
    else:
        category_phrase = "place"

    evidence_bits: List[str] = []
    if rating_signal:
        evidence_bits.append(rating_signal)
    if value_signal:
        evidence_bits.append(value_signal)
    if editorial_signal:
        evidence_bits.append(editorial_signal)
    elif tag_signal:
        evidence_bits.append(tag_signal)

    base = f"{place}"
    if location:
        base = f"{base} in {location}"
    base = f"{base} is a {category_phrase}"

    if not evidence_bits:
        return f"{base} with verified listing details."

    seed = sum(ord(c) for c in f"{place}|{category_phrase}|{location or ''}|{rating_signal or ''}") % 3
    first, rest = evidence_bits[0], evidence_bits[1:]
    if seed == 0:
        tail = ", ".join(rest)
        return f"{base} backed by {first}" + (f" plus {tail}." if tail else ".")
    if seed == 1:
        tail = ", ".join(rest)
        return f"With {first}" + (f" and {tail}, {base}." if tail else f", {base}.")
    tail = ", ".join(rest)
    return f"{base}, with {first}" + (f" and {tail}." if tail else ".")


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
    price_level: Optional[int] = None,
    user_query: str = "",
    intent: Optional[str] = None,
) -> WhyPickResult:
    has_michelin_evidence = bool(michelin_status) or any("michelin" in _clean_chip(ev).lower() for ev in evidence)
    template_id = "michelin" if category == "restaurant" and has_michelin_evidence else _pick_template(evidence, rating, review_count)

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
        price_level=price_level,
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
