"""Deterministic why-pick reasoning with evidence chips."""

from __future__ import annotations

import re
from typing import Iterable, List, Literal, Optional, Sequence, Tuple, TypedDict

BANNED_STRINGS_RE = re.compile(
    r"(source checked|editorial mention|source fit|evidence:|tavily|verification score|###|https?://)",
    re.IGNORECASE,
)

# Phrases that signal generic, template-level output — must never appear in display_why.
GENERIC_PHRASES_RE = re.compile(
    r"(a strong pick for well-reviewed|guest feedback, location, and relevance|"
    r"polished night-out experience|viable option|great fit for this trip|"
    r"trusted place signals|fits this request as a google-verified|"
    r"well-reviewed food|well-reviewed drinks|matches this dining request|"
    r"matches this value-dinner request|fits this hotel request|"
    r"fits this Michelin request|is a strong attraction match|"
    r"available evidence|selected for this|verified restaurant details|"
    r"verified drinks-focused|verified place details|backed by|"
    r"consistent guest ratings|"
    r"\bwell-rated\b)",
    re.IGNORECASE,
)

# Patterns that indicate the old bad template output — must never appear.
# Note: [^,]* (no-comma) stops at the first comma so sentences like
# "Kumiko is a bar in West Loop, a reliable spot for drinks with 4.7 rating"
# are not falsely rejected (the comma before the descriptive clause breaks the match).
_BAD_TEMPLATE_RE = re.compile(
    r"^\s*[A-Za-z][^.!?]+\s+is\s+a\s+(?:restaurant|bar|hotel|attraction|place)\b[^,]*with\s+\d|"
    r"^\s*[Ww]ith\s+\d+[\.,]\d+\s+rating",
    re.IGNORECASE,
)

# Pure rating/location chips added as fallbacks — not editorial evidence.
_PURE_RATING_CHIP_RE = re.compile(
    r"^(?:rated\s+)?\d+[\.,]\d+|^google verified listing|^near\s+",
    re.IGNORECASE,
)

# Internal intent/category labels injected as tags — must never be used as editorial leads.
_INTERNAL_INTENT_TAGS = frozenset({
    "nightlife", "hidden gem", "luxury value", "romantic", "family-friendly",
    "google verified", "editorial", "google",
})

_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
_PLACE_WORD_RE = re.compile(r"\b(?:in|near|at)\s+[A-Z][\w''.-]*(?:\s+[A-Z][\w''.-]*)*\b")


def _trim_to_word(text: str, max_len: int = 140) -> str:
    """Trim text to at most max_len characters at a word boundary.

    Never cuts mid-word; backs up to the last space and ensures the
    result ends with a sentence-terminating punctuation mark.
    """
    if len(text) <= max_len:
        return text
    trimmed = text[:max_len]
    last_space = trimmed.rfind(" ")
    if last_space > max_len // 2:
        trimmed = trimmed[:last_space]
    return trimmed.rstrip(" .,;:!?") + "."


# Nightlife category inference signals
_NIGHTLIFE_VIEW_SIGNALS: frozenset = frozenset({
    "observatory", "tower", "rooftop", "roof", "perch", "summit", "sky",
    "altitude", "heights", "view", "vista", "lookout",
})
_NIGHTLIFE_SPEAKEASY_SIGNALS: frozenset = frozenset({
    "speakeasy", "underground",
})


class WhyPick(TypedDict):
    text: str
    generation_method: Literal["deterministic", "llm"]


class WhyPickResult(TypedDict):
    why_pick: WhyPick
    template_id: Literal["rating_and_editorial", "editorial_only", "google_only", "fallback", "michelin"]


def _clean_chip(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip(" .,-")
    cleaned = re.sub(r"[\[\]#*`]+", "", cleaned).strip()
    return cleaned


def _is_pure_rating_chip(chip: str) -> bool:
    """Return True for fallback rating/location chips that carry no editorial signal."""
    return bool(_PURE_RATING_CHIP_RE.match(chip.strip()))


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


def infer_nightlife_category_label(
    google_types: Optional[List[str]],
    place_name: str,
) -> Tuple[str, str]:
    """Derive bar display label from Google place types + name signals.

    Returns (label, source) where source is one of:
      'google_types' | 'name_signal' | 'intent_fallback'

    Priority: Google types → name signals → intent fallback.
    """
    type_blob = " ".join((t or "").lower() for t in (google_types or []))
    name_lower = (place_name or "").lower()

    # Google types are authoritative
    if "cocktail_bar" in type_blob:
        return "Cocktail Bar", "google_types"
    if "wine_bar" in type_blob:
        return "Wine Bar", "google_types"
    if "lounge_bar" in type_blob:
        return "Lounge", "google_types"
    if "brewery" in type_blob or "brewpub" in type_blob:
        return "Brewery", "google_types"

    # Name signals: rooftop/view/landmark structures
    if any(sig in name_lower for sig in _NIGHTLIFE_VIEW_SIGNALS):
        is_rooftop = any(s in name_lower for s in ("rooftop", "roof", "sky"))
        return ("Rooftop Bar" if is_rooftop else "View Bar"), "name_signal"
    if any(sig in name_lower for sig in _NIGHTLIFE_SPEAKEASY_SIGNALS):
        return "Speakeasy", "name_signal"
    if "lounge" in name_lower:
        return "Lounge", "name_signal"
    if any(s in name_lower for s in ("winery", " wine ")):
        return "Wine Bar", "name_signal"
    if "brewery" in name_lower or "brewing" in name_lower:
        return "Brewery", "name_signal"

    # Distinguish bar+restaurant vs pure bar from Google types
    if type_blob:
        has_restaurant = any(t in type_blob for t in ("restaurant", "food", "meal"))
        has_bar = any(t in type_blob for t in ("bar", "night_club"))
        if has_restaurant and has_bar:
            return "Bar & Restaurant", "google_types"
        if has_bar:
            return "Bar", "google_types"
        if "night_club" in type_blob:
            return "Nightclub", "google_types"

    return "Cocktail Bar", "intent_fallback"


def _build_nightlife_display_why(
    *,
    place_name: str,
    google_types: Optional[List[str]],
    rating: Optional[float],
    review_count: Optional[int],
    specialty_tags: Optional[List[str]] = None,
) -> str:
    """Premium deterministic concierge copy for nightlife/bar cards with no clean location.

    Produces place-specific copy using specialty signals first, then category inference.
    Never produces a bare rating-only sentence.
    """
    category_label, _ = infer_nightlife_category_label(google_types, place_name)
    cat = category_label.lower()
    name_lower = (place_name or "").lower()
    r = float(rating or 0)
    rc = int(review_count or 0)

    # View/landmark venues — the setting is the primary draw
    if any(sig in name_lower for sig in _NIGHTLIFE_VIEW_SIGNALS):
        landmark = "landmark tower" if any(s in name_lower for s in ("tower", "observatory")) else "landmark building"
        return (
            f"A {cat} in a {landmark} setting, "
            f"best when the setting matters as much as the drinks."
        )[:150]

    if any(sig in name_lower for sig in _NIGHTLIFE_SPEAKEASY_SIGNALS):
        return (
            f"A speakeasy-style bar with a hidden-door atmosphere, "
            f"good for a memorable and off-the-beaten-path night out."
        )[:150]

    # Specialty tag — venue's own signature (craft cocktails, natural wine, mezcal, etc.)
    if specialty_tags:
        tag = specialty_tags[0].lower().strip()
        return _trim_to_word(
            f"A {cat} known for {tag}, worth seeking out for a distinct evening."
        )

    # Volume + quality characterization (fallback when no specialty signal)
    if rc >= 2000 and r >= 4.2:
        return (
            f"A high-volume {cat} with a devoted crowd, "
            f"reliable for a lively and well-regarded drinks stop."
        )[:150]

    if rc >= 500 and r >= 4.5:
        return (
            f"A {cat} with deep review volume and consistent praise, "
            f"a dependable pick for the evening."
        )[:150]

    if rc < 300 and r >= 4.5:
        return (
            f"A smaller {cat} with excellent ratings, "
            f"better for a local-feeling night out away from tourist-heavy spots."
        )[:150]

    if r >= 4.5:
        return f"A highly-rated {cat}, a confident pick for an evening out."[:150]

    if r >= 4.2:
        return f"A {cat} with strong guest ratings, useful for a dependable evening stop."[:150]

    return f"A {cat} with solid Google presence, a consistent nightlife option."[:150]


def _michelin_stars_text(status: str) -> str:
    """Translate raw michelin_status to natural adjective form."""
    s = (status or "").strip()
    low = s.lower().replace("-", " ")  # normalize "3-star" → "3 star"
    if "3 star" in low or "three" in low:
        return "three-Michelin-star"
    if "2 star" in low or "two" in low:
        return "two-Michelin-star"
    if "1 star" in low:
        return "Michelin-starred"
    if "bib gourmand" in low:
        return "Michelin Bib Gourmand"
    if "star" in low:
        return "Michelin-starred"
    return s


def _build_cuisine_restaurant_display_why(
    *,
    cuisine: str,
    loc: Optional[str] = None,
    rating: Optional[float] = None,
    review_count: Optional[int] = None,
    place_name: Optional[str] = None,
    specialty_tags: Optional[List[str]] = None,
) -> str:
    """Premium deterministic concierge copy for cuisine-specific restaurant cards (D).

    ``loc`` must be a pre-validated area-level neighborhood (never a full address,
    never the place's own name). Uses specialty signals first, then volume/quality.
    """
    cat = cuisine.lower()
    if not cat.endswith("restaurant"):
        cat = f"{cat} restaurant"
    r = float(rating or 0)
    rc = int(review_count or 0)
    loc_part = f" in {loc}" if loc else ""
    name = place_name or ""

    # Specialty tag — the venue's own signature draw
    if specialty_tags:
        tag = specialty_tags[0].lower().strip()
        if name:
            return _trim_to_word(f"{name} is a {cat}{loc_part} known for {tag}.")
        return _trim_to_word(f"A {cat}{loc_part} known for {tag}.")

    # Deep review volume + high quality = proven anchor
    if rc >= 1500 and r >= 4.5:
        if name:
            return _trim_to_word(f"{name} is a{loc_part} {cat} with a devoted following and deep review volume, a reliable neighborhood anchor.")
        return _trim_to_word(f"A high-volume{loc_part} {cat} with a devoted following, a reliable neighborhood anchor.")

    if rc >= 1000 and r >= 4.2:
        if name:
            return _trim_to_word(f"{name} is a{loc_part} {cat} with a loyal crowd and strong Google volume, a well-established pick.")
        return _trim_to_word(f"A well-established{loc_part} {cat} with a loyal crowd and strong Google volume.")

    # Small + excellent = local gem feel
    if rc < 400 and r >= 4.6:
        if name:
            return _trim_to_word(f"{name} is a smaller{loc_part} {cat} with unusually high ratings, a strong local-feeling pick.")
        return _trim_to_word(f"A smaller{loc_part} {cat} with unusually high ratings, better for a local-feeling pick.")

    # High rating with moderate volume
    if r >= 4.7:
        if name:
            return _trim_to_word(f"{name} is an unusually well-rated{loc_part} {cat}, a confident pick for the cuisine.")
        return _trim_to_word(f"An unusually well-rated{loc_part} {cat}, a confident pick for the cuisine.")

    if r >= 4.5:
        if loc:
            if name:
                return _trim_to_word(f"{name} is a highly rated {loc} {cat}, a solid neighborhood choice.")
            return _trim_to_word(f"A highly rated {loc} {cat}, a solid neighborhood choice.")
        return _trim_to_word(f"A highly rated {cat}, a solid pick in this area.")

    if r >= 4.2:
        if loc:
            return _trim_to_word(f"A {loc} {cat} with solid guest ratings and strong Google presence.")
        return _trim_to_word(f"A {cat} with solid guest ratings and strong Google presence.")

    if loc:
        return _trim_to_word(f"A {cat} in {loc} with solid Google presence.")
    return _trim_to_word(f"A {cat} with solid Google presence.")


def has_concrete_fact(text: str) -> bool:
    if _NUMBER_RE.search(text):
        return True
    if _PLACE_WORD_RE.search(text):
        return True
    keyword_hits = ("guide", "michelin", "bar", "restaurant", "cafe", "hotel", "museum", "park", "reviews")
    return any(k in text.lower() for k in keyword_hits)


def build_concierge_display_reason(
    *,
    place_name: str,
    query_context: str = "",
    intent: Optional[str] = None,
    category: Optional[str] = None,
    cuisine: Optional[str] = None,
    neighborhood: Optional[str] = None,
    michelin_status: Optional[str] = None,
    rating: Optional[float] = None,
    review_count: Optional[int] = None,
    price_level: Optional[int] = None,
    evidence: Optional[Sequence[str]] = None,
    tags: Optional[Iterable[str]] = None,
    google_types: Optional[List[str]] = None,
) -> str:
    """Canonical display reason using a prioritized evidence ladder.

    Priority:
      a) Michelin status / explicit intent match (Michelin, cocktail, hidden gem, etc.)
      b) Editorial / list source evidence
      c) Neighborhood + cuisine/category
      d) Category fit with rating as supporting detail
      e) Rating-only fallback (never the main sentence structure)
      f) Absolute fallback: "A verified {category} that fits this request, with strong Google signals."

    Never produces "X is a restaurant with rating" or "With rating, X is a restaurant."
    Rating is always supporting detail appended to a category/location anchor.
    Max 140 chars.
    """
    query_low = (query_context or "").lower()

    # Separate editorial evidence from pure fallback rating/location chips and internal intent tags.
    editorial = [
        e for e in (evidence or [])
        if e and not _is_pure_rating_chip(e) and not BANNED_STRINGS_RE.search(e)
        and e.strip().lower() not in _INTERNAL_INTENT_TAGS
    ]

    # Rating as supporting detail string.
    rating_support = _rating_phrase(rating, review_count, list(evidence or []))

    # Location anchor (area-level, not full address).
    loc = _location_area_phrase(neighborhood) or _location_phrase(neighborhood)
    # Safety (E): never use a location that appears to be the place's own name.
    if loc and place_name:
        _pl_lower = place_name.lower()
        _loc_clean = re.sub(r"['’]s?\s*$", "", loc, flags=re.IGNORECASE).strip().lower()
        _loc_tokens = {t for t in re.split(r"\W+", _loc_clean) if t and len(t) > 2}
        _name_tokens = {t for t in re.split(r"\W+", _pl_lower) if t and len(t) > 2}
        # Reject if the loc is a subset of the place name tokens or vice-versa
        if _loc_tokens and _loc_tokens.issubset(_name_tokens):
            loc = None
    loc_part = f" in {loc}" if loc else ""
    query_city_match = re.search(r"\b(?:in|near)\s+([A-Za-z][A-Za-z\s\-']{1,40})\b", query_low)
    query_city = query_city_match.group(1).strip().title() if query_city_match else None

    # Is this a cocktail / nightlife request?
    is_cocktail = (
        (category or "").lower() in ("bar", "night_club", "cocktail_bar")
        or intent == "nightlife"
        or "cocktail" in query_low
    )

    def _append_rating(base: str) -> str:
        """Append rating as supporting detail if it fits within 140 chars."""
        stripped = base.rstrip(".")
        if rating_support and not stripped.lower().endswith(rating_support.lower()):
            candidate = f"{stripped} with {rating_support}."
            if len(candidate) <= 140:
                return candidate
        return stripped + "."

    # ── Priority a: Michelin status ──────────────────────────────────────────
    if michelin_status:
        stars = _michelin_stars_text(michelin_status)
        cat_part = f" {cuisine.lower()}" if cuisine else ""
        dest = loc_part or ""
        return _trim_to_word(f"{place_name} is a {stars}{cat_part} destination{dest}, making it a standout for fine dining.")

    # ── Priority b: Cocktail/nightlife — bar framing, editorial only if bar-specific ─
    # Use Google types to infer precise category label; editorial leads when available.
    if is_cocktail:
        _BAR_TOKENS = ("cocktail", "bar", "drinks", "nightlife", "spirits", "lounge", "speakeasy")
        edit_with_bar_signal = next(
            (e for e in editorial if any(tok in e.lower() for tok in _BAR_TOKENS)),
            None,
        )
        if edit_with_bar_signal:
            best = _clean_chip(edit_with_bar_signal)
            if len(best) > 100:
                best = best[:97] + "..."
            result = best.rstrip(".")
            if loc and loc.lower() not in result.lower():
                result += f" ({loc})"
            if rating_support and len(result) + len(rating_support) + 5 <= 135:
                result += f" — {rating_support}."
            else:
                result += "."
            return _trim_to_word(result)

        # Infer precise category from Google types + name signals
        _cat_label, _ = infer_nightlife_category_label(google_types, place_name)
        _cat_lower = _cat_label.lower()

        if loc_part:
            # Specialty tag takes priority over generic "reliable spot" phrasing
            _specialty = list(tags)[0].lower() if tags else None
            if _specialty:
                if place_name:
                    return _trim_to_word(f"{place_name} is a {_cat_lower}{loc_part} known for {_specialty}.")
                return _trim_to_word(f"A {_cat_lower}{loc_part} known for {_specialty}.")
            if place_name:
                return _trim_to_word(_append_rating(f"{place_name} is a {_cat_lower}{loc_part}, a reliable spot for evening drinks"))
            return _trim_to_word(_append_rating(f"A {_cat_lower}{loc_part}, a reliable spot for evening drinks"))

        # No clean location → use specialty tags then volume/type characterization
        return _build_nightlife_display_why(
            place_name=place_name,
            google_types=google_types,
            rating=rating,
            review_count=review_count,
            specialty_tags=list(tags) if tags else None,
        )[:150]

    # ── Priority c: Editorial / list source evidence ─────────────────────────
    if editorial:
        best = _clean_chip(editorial[0])
        if len(best) > 100:
            best = best[:97] + "..."
        result = best.rstrip(".")
        if loc and loc.lower() not in result.lower():
            result += f" ({loc})"
        if rating_support and len(result) + len(rating_support) + 5 <= 135:
            result += f" — {rating_support}."
        else:
            result += "."
        return _trim_to_word(result)

    # ── Priority d: Intent-specific category framing (no editorial) ──────────
    if intent == "hidden_gems":
        if cuisine and category == "restaurant":
            inner = f"{cuisine.lower()} restaurant"
        elif cuisine:
            inner = cuisine.lower()
        else:
            inner = (category or "spot").replace("_", " ")
        return _trim_to_word(_append_rating(f"A local {inner}{loc_part}"))

    if "near my hotel" in query_low or "near hotel" in query_low:
        if category in ("cafe", "bar", "hotel", "attraction"):
            inner = category
        elif cuisine:
            inner = cuisine.lower()
        else:
            inner = (category or "pick").replace("_", " ")
        if inner.lower() == "restaurant":
            return _trim_to_word(_append_rating(f"A well-regarded nearby restaurant{loc_part}"))
        return _trim_to_word(_append_rating(f"A {inner}{loc_part}"))

    if "brunch" in query_low:
        return _trim_to_word(_append_rating(f"A popular brunch spot{loc_part}"))

    if intent == "romantic":
        inner = cuisine.lower() if cuisine else (category or "spot").replace("_", " ")
        return _trim_to_word(_append_rating(f"A romantic {inner}{loc_part}"))

    if intent == "family_friendly":
        inner = cuisine.lower() if cuisine else (category or "spot").replace("_", " ")
        return _trim_to_word(_append_rating(f"A family-friendly {inner}{loc_part}"))

    # ── Priority e1: Hotel-specific location-led copy (never rating-first) ──
    if (category or "").lower() == "hotel":
        hotel_anchor = loc or query_city or "city-center"
        return (
            f"{place_name} is a well-located {hotel_anchor} hotel with strong review volume, "
            "making it a practical base for exploring the city."
        )[:170]

    # ── Priority e: Cuisine-specific restaurant — volume/quality framing (D) ──
    # For cuisine-specific restaurant queries without editorial, use the dedicated
    # cuisine-restaurant copy builder instead of the generic rating template.
    _is_cuisine_restaurant = (
        cuisine
        and (category or "").lower() in ("restaurant", "")
        and intent not in ("romantic", "family_friendly", "hidden_gems", "nightlife")
    )
    if _is_cuisine_restaurant:
        return _build_cuisine_restaurant_display_why(
            cuisine=cuisine,  # type: ignore[arg-type]
            loc=loc,
            rating=rating,
            review_count=review_count,
            place_name=place_name,
            specialty_tags=list(tags) if tags else None,
        )

    # ── Priority f: Neighborhood + generic category ──────────────────────────
    if loc and cuisine:
        return _trim_to_word(_append_rating(f"A top-rated {cuisine.lower()}{loc_part}"))

    if loc:
        inner = (category or "place").replace("_", " ")
        if inner.lower() == "restaurant":
            return _trim_to_word(_append_rating(f"A well-regarded {loc} restaurant"))
        return _trim_to_word(_append_rating(f"A {inner}{loc_part}"))

    # ── Priority g: Category + rating (no location) ──────────────────────────
    if rating_support:
        inner = cuisine.lower() if cuisine else (category or "place").replace("_", " ")
        if inner.lower() == "restaurant":
            return _trim_to_word(f"A well-regarded restaurant with strong review volume and verified listing details.")
        return _trim_to_word(f"A verified {inner} with {rating_support}.")

    # ── Priority h: Absolute fallback ────────────────────────────────────────
    inner = cuisine.lower() if cuisine else (category or "place").replace("_", " ")
    return _trim_to_word(f"A verified {inner} that fits this request, with strong Google signals.")


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
    google_types: Optional[List[str]] = None,
    specialty_tags: Optional[List[str]] = None,
) -> WhyPickResult:
    def _safe_fallback_text() -> str:
        loc = _location_phrase(neighborhood)
        loc_part = f" in {loc}" if loc else ""
        cat = (category or "place").replace("_", " ").lower()
        if cat == "hotel":
            return f"{place_name or 'This hotel'} is a well-located hotel{loc_part}, making it a practical base for exploring the city."
        if cat == "restaurant":
            return f"A well-regarded restaurant{loc_part} with verified listing details and strong review volume."
        if cat == "bar":
            return f"A reliable bar{loc_part} with verified listing details and strong review volume."
        return f"A well-regarded {cat}{loc_part} with verified listing details."

    has_michelin_evidence = bool(michelin_status) or any("michelin" in _clean_chip(ev).lower() for ev in evidence)
    template_id: Literal["rating_and_editorial", "editorial_only", "google_only", "fallback", "michelin"] = (
        "michelin" if category == "restaurant" and has_michelin_evidence
        else _pick_template(evidence, rating, review_count)
    )

    # Promote michelin_status when it's embedded only in evidence chips.
    effective_michelin = michelin_status
    if not effective_michelin and has_michelin_evidence:
        for chip in evidence:
            if "michelin" in chip.lower():
                effective_michelin = chip.rstrip(".")
                break

    text = build_concierge_display_reason(
        place_name=place_name or "This place",
        query_context=user_query,
        intent=intent,
        category=category,
        cuisine=cuisine,
        neighborhood=neighborhood,
        michelin_status=effective_michelin,
        rating=rating,
        review_count=review_count,
        price_level=price_level,
        evidence=evidence,
        google_types=google_types,
        tags=specialty_tags,
    )

    # Final guards — must never reach these in normal flow.
    if BANNED_STRINGS_RE.search(text) or GENERIC_PHRASES_RE.search(text) or _BAD_TEMPLATE_RE.search(text):
        text = _safe_fallback_text()

    if "backed by" in text.lower() or "with rated" in text.lower():
        text = re.sub(r"\bbacked by\b", "with", text, flags=re.IGNORECASE)
        text = re.sub(r"\bwith rated\b", "with a", text, flags=re.IGNORECASE)

    if not has_concrete_fact(text):
        text = _safe_fallback_text()

    return {
        "why_pick": {"text": text, "generation_method": "deterministic"},
        "template_id": template_id,
    }


def build_why_pick_with_structured_evidence(
    *,
    place_name: str,
    evidence: Sequence[str],
    rating: Optional[float],
    review_count: Optional[int],
    evidence_units: Optional[List] = None,
    category: Optional[str] = None,
    neighborhood: Optional[str] = None,
    cuisine: Optional[str] = None,
    michelin_status: Optional[str] = None,
    price_level: Optional[int] = None,
    user_query: str = "",
    intent: Optional[str] = None,
    google_types: Optional[List[str]] = None,
    city: str = "",
    api_key: Optional[str] = None,
    known_venue_names: Optional[List[str]] = None,
) -> WhyPickResult:
    """Try LLM-synthesized whyPick first; fall back to deterministic on any failure.

    The LLM path is used only when:
    - evidence_units is provided and non-empty
    - at least one unit is safe_for_copy
    - api_key is configured

    Alignment guarantee: the returned why_pick.text is always propagated to
    venue.why_pick, supporting_details.why_pick, and display.display_why by
    the caller (live_research._apply_google_gate).
    """
    # Extract foursquare specialty labels for the deterministic fallback path.
    # Only foursquare_tag claims are venue-specific signals (e.g. "handmade tortillas").
    # foursquare_category labels (e.g. "Mexican Restaurant") are category identifiers,
    # not specialties, so they must not be used for "known for" copy.
    specialty_tags: Optional[List[str]] = None
    if evidence_units:
        _tags: List[str] = []
        for eu in evidence_units:
            if eu.claim_type == "foursquare_tag":
                tag = re.sub(r"^tagged as\s+", "", eu.claim, flags=re.IGNORECASE).strip()
                if tag:
                    _tags.append(tag)
        if _tags:
            specialty_tags = _tags[:3]

    if evidence_units:
        try:
            from app.concierge.whypick_prompt import generate_llm_why_pick
            llm_result = generate_llm_why_pick(
                venue_name=place_name,
                category=category or "place",
                intent=intent or "",
                city=city,
                evidence_units=evidence_units,
                api_key=api_key,
                known_venue_names=known_venue_names,
            )
            if llm_result is not None:
                llm_text = llm_result["whyPick"].strip()
                if llm_text and not BANNED_STRINGS_RE.search(llm_text) and not GENERIC_PHRASES_RE.search(llm_text):
                    template_id: Literal["rating_and_editorial", "editorial_only", "google_only", "fallback", "michelin"] = (
                        "michelin" if michelin_status or any("michelin" in eu.claim.lower() for eu in evidence_units)
                        else "rating_and_editorial"
                    )
                    return {
                        "why_pick": {"text": llm_text, "generation_method": "llm"},
                        "template_id": template_id,
                    }
        except Exception:
            pass

    return build_why_pick(
        place_name=place_name,
        evidence=evidence,
        rating=rating,
        review_count=review_count,
        category=category,
        neighborhood=neighborhood,
        cuisine=cuisine,
        michelin_status=michelin_status,
        price_level=price_level,
        user_query=user_query,
        intent=intent,
        google_types=google_types,
        specialty_tags=specialty_tags,
    )
