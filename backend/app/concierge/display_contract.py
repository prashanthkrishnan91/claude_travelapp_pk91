"""Canonical display contract normalizer for AI Concierge place cards.

This module is the single seam that every UnifiedRestaurantResult,
UnifiedAttractionResult, and UnifiedHotelResult must pass through before
serialization to the frontend.

Why this exists
---------------
Hotels and attractions historically used legacy adapters (``ConciergeService.
_to_unified_hotel`` / ``_to_unified_attraction``) that produced 10-point
ratings (``rating * 2``), no ``display`` block, no ``supporting_details``,
no address, no price, and no concierge note.  Restaurants from semantic
retrieval already shipped a clean 5-point rating with a populated ``display``
block.  The result was a card surface that was inconsistent across verticals
and trivially easy to wire incorrectly.

This adapter brings every card into the same canonical contract, regardless
of which producer built it (semantic_retrieval, legacy concierge service,
live_research, fast_dynamic_place_search).

Behavior
--------
- Idempotent: re-applying does not lose existing fields.
- Never invents data: only restructures already-present data into the
  canonical display block.  Absent data stays absent.
- Drops Chicago-era stale "Sample bar research data" disclaimer text.
- Coerces 10-point ratings (legacy producers) to 5-point (Google native).
- Marks absent reasons explicitly: when no concierge note exists,
  display.display_why_validated stays False so the frontend hides the note.

Public surface
--------------
- ``normalize_place_recommendations(response)``: in-place normalize all
  cards on a PlaceRecommendationsResponse / ConciergeSearchResponse.
- ``normalize_unified_card(card)``: normalize a single card.
- ``STALE_DISCLAIMER_FRAGMENTS``: substrings that must never reach the UI.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# Substrings that the cleanup explicitly purges from card text and source
# labels.  Centralized here so a contract test can iterate the list and
# adversarially scan response payloads.
STALE_DISCLAIMER_FRAGMENTS: tuple[str, ...] = (
    "Sample bar research data",
    "sample bar research data",
)

# Neutral replacement language for the legacy "Sample bar research data ·
# verify hours and current status before booking." string.  Mirrors the
# wording used by SOURCE_UNAVAILABLE so the frontend renders a single
# coverage caveat instead of two competing disclaimers.
NEUTRAL_LIMITED_COVERAGE_LABEL = (
    "Limited source coverage — verify hours and booking before adding."
)


_GOOGLE_PRICE_LEVEL_SYMBOL: Dict[str, str] = {
    "PRICE_LEVEL_FREE": "Free",
    "PRICE_LEVEL_INEXPENSIVE": "$",
    "PRICE_LEVEL_MODERATE": "$$",
    "PRICE_LEVEL_EXPENSIVE": "$$$",
    "PRICE_LEVEL_VERY_EXPENSIVE": "$$$$",
}


def _format_display_price(
    price_level: Optional[str],
    price_range: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Normalize a Google price signal into a compact UI string.

    Mirrors ``app.concierge.semantic_retrieval._format_display_price`` and
    ``app.services.fast_dynamic_place_search._format_display_price`` but
    lives here so non-semantic paths get the same formatting.
    """
    if price_range and isinstance(price_range, dict):
        start = price_range.get("startPrice") or {}
        end = price_range.get("endPrice") or {}
        if isinstance(start, dict) and isinstance(end, dict):
            try:
                start_units = int(start.get("units") or 0)
                end_units = int(end.get("units") or 0)
                currency = start.get("currencyCode") or end.get("currencyCode") or "USD"
                symbol = "$" if currency == "USD" else currency
                if start_units > 0 and end_units > 0:
                    return f"{symbol}{start_units}–{end_units}"
                if start_units > 0:
                    return f"From {symbol}{start_units}"
                if end_units > 0:
                    return f"Up to {symbol}{end_units}"
            except (TypeError, ValueError):
                pass
    if price_level:
        return _GOOGLE_PRICE_LEVEL_SYMBOL.get(price_level)
    return None


def _coerce_5point_rating(rating: Optional[float]) -> Optional[float]:
    """Coerce a possibly-10-point legacy rating into the canonical 5-point scale.

    Google Places returns 0-5.  The legacy ConciergeService adapters (pre-PR
    architecture rescue) doubled this to 0-10 for hotels and attractions.
    Anything > 5.05 is treated as a legacy 10-point value and halved.
    """
    if rating is None:
        return None
    try:
        value = float(rating)
    except (TypeError, ValueError):
        return None
    if value > 5.05:
        return round(value / 2.0, 1)
    return round(value, 1)


def _format_meta_line(
    rating: Optional[float],
    review_count: Optional[int],
) -> Optional[str]:
    """Format a star/review meta-line consistent with semantic retrieval cards."""
    if rating is None and not review_count:
        return None
    parts: List[str] = []
    if rating is not None:
        try:
            parts.append(f"★ {float(rating):.1f}")
        except (TypeError, ValueError):
            return None
    if review_count:
        try:
            parts[-1] = f"{parts[-1]} ({int(review_count):,} reviews)"
        except (TypeError, ValueError):
            pass
    return parts[0] if parts else None


def _format_hotel_price(
    price_per_night: Optional[float],
    price_level: Optional[str],
    price_range: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Hotels carry a numeric ``price_per_night`` instead of Google price fields.

    Prefer Google price signals when available; otherwise format the numeric
    nightly rate as ``$NNN/night`` so hotel cards no longer ship blank price.
    """
    google = _format_display_price(price_level, price_range)
    if google:
        return google
    if price_per_night is not None:
        try:
            return f"${int(round(float(price_per_night)))}/night"
        except (TypeError, ValueError):
            return None
    return None


def _strip_stale_disclaimer(text: Optional[str]) -> Optional[str]:
    """Remove stale 'Sample bar research data' disclaimer fragments.

    Returns None if stripping leaves an empty/whitespace-only string.
    """
    if text is None:
        return None
    cleaned = text
    for fragment in STALE_DISCLAIMER_FRAGMENTS:
        cleaned = cleaned.replace(fragment, "")
    cleaned = re.sub(r"\s*·\s*verify hours and current status before booking\.?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ·.")
    return cleaned or None


def _build_addability(card: Any) -> str:
    """Derive ``display.addability`` from existing card signals."""
    existing_display = getattr(card, "display", None)
    if existing_display is not None:
        existing_addability = getattr(existing_display, "addability", None)
        if existing_addability:
            return existing_addability
    gv = getattr(card, "google_verification", None)
    if gv is not None:
        place_id = getattr(gv, "provider_place_id", None) or getattr(gv, "providerPlaceId", None)
        business_status = getattr(gv, "business_status", None) or getattr(gv, "businessStatus", None)
        if place_id and (business_status is None or business_status == "OPERATIONAL"):
            return "addable"
    if getattr(card, "verified_place", False) is True:
        return "addable"
    return "research_only"


def _existing_display_field(card: Any, attr: str) -> Optional[Any]:
    display = getattr(card, "display", None)
    if display is None:
        return None
    return getattr(display, attr, None)


def _existing_supporting_field(card: Any, attr: str) -> Optional[Any]:
    sd = getattr(card, "supporting_details", None)
    if sd is None:
        return None
    return getattr(sd, attr, None)


def normalize_unified_card(card: Any, *, vertical: str) -> Any:
    """Ensure ``card.display`` and ``card.supporting_details`` follow the canonical
    contract.  Mutates the card in place and returns it for chaining.

    ``vertical`` ∈ {"restaurant", "attraction", "hotel"} drives small format
    differences (hotel uses ``area_label`` for address; attraction uses
    ``description`` for fallback display_why; etc.).
    """
    if card is None:
        return card

    # Lazy import to avoid circular import between models.concierge and
    # this module when reasoning helpers are also imported elsewhere.
    from app.models.concierge import (
        ConciergeDisplayFields,
        PlaceSupportingDetails,
    )

    name = getattr(card, "name", None) or "Place"

    # ── Rating: always 5-point Google scale ──────────────────────────────
    legacy_rating = getattr(card, "rating", None)
    rating_5 = _coerce_5point_rating(legacy_rating)
    if rating_5 is not None and rating_5 != legacy_rating:
        try:
            card.rating = rating_5
        except Exception:  # pragma: no cover — pydantic v2 sets are fine
            pass

    review_count = getattr(card, "review_count", None) or getattr(card, "user_rating_count", None)

    # ── Address resolution ───────────────────────────────────────────────
    gv = getattr(card, "google_verification", None)
    address_candidates: List[Optional[str]] = [
        _existing_supporting_field(card, "address"),
        getattr(gv, "formatted_address", None) if gv is not None else None,
        getattr(card, "address", None),
        getattr(card, "neighborhood", None),
        getattr(card, "area_label", None),
    ]
    address = next((a for a in address_candidates if a), None)

    # ── Price resolution ─────────────────────────────────────────────────
    price_level = _existing_supporting_field(card, "price_level") or getattr(card, "price_level", None)
    price_range = _existing_supporting_field(card, "price_range") or getattr(card, "price_range", None)
    if vertical == "hotel":
        display_price = _format_hotel_price(
            getattr(card, "price_per_night", None),
            price_level,
            price_range,
        )
    else:
        display_price = _existing_display_field(card, "display_price") or _format_display_price(price_level, price_range)

    # ── Display category ────────────────────────────────────────────────
    category_candidates: List[Optional[str]] = [
        _existing_display_field(card, "display_category"),
        _existing_supporting_field(card, "category_label"),
    ]
    if vertical == "restaurant":
        category_candidates.append(getattr(card, "cuisine", None))
        category_candidates.append("Restaurant")
    elif vertical == "attraction":
        category_candidates.append(getattr(card, "category", None))
        category_candidates.append("Attraction")
    elif vertical == "hotel":
        stars = getattr(card, "stars", None)
        if stars:
            try:
                star_int = int(round(float(stars)))
                category_candidates.append(f"{star_int}-star Hotel")
            except (TypeError, ValueError):
                pass
        category_candidates.append("Hotel")
    display_category = next((c for c in category_candidates if c), name)

    # ── Display why (concierge note) ─────────────────────────────────────
    why_candidates: List[Optional[str]] = [
        _existing_display_field(card, "display_why"),
        _existing_supporting_field(card, "why_pick"),
        getattr(card, "why_pick", None),
        getattr(card, "primary_reason", None),
        getattr(card, "summary", None) if vertical != "hotel" else None,
        getattr(card, "reason", None) if vertical == "hotel" else None,
        getattr(card, "description", None) if vertical == "attraction" else None,
    ]
    display_why_raw = next((w for w in why_candidates if w), None)
    display_why = _strip_stale_disclaimer(display_why_raw) or ""

    why_validated_existing = _existing_display_field(card, "display_why_validated")
    why_validated = bool(why_validated_existing) if why_validated_existing is not None else False
    why_source = _existing_display_field(card, "display_why_source")

    # ── Meta line ────────────────────────────────────────────────────────
    meta_line = _existing_display_field(card, "display_meta_line") or _existing_supporting_field(card, "meta_line")
    if not meta_line:
        meta_line = _format_meta_line(rating_5, review_count)

    # ── Badges ───────────────────────────────────────────────────────────
    badges = list(_existing_display_field(card, "display_badges") or [])

    # ── Addability ───────────────────────────────────────────────────────
    addability = _build_addability(card)

    # ── Build supporting_details (clean stale disclaimer fragments) ──────
    sd_existing = getattr(card, "supporting_details", None)
    sd_kwargs: Dict[str, Any] = {
        "rating": _existing_supporting_field(card, "rating") or (
            f"{rating_5:.1f}" if rating_5 is not None else None
        ),
        "review_count": _existing_supporting_field(card, "review_count") or review_count,
        "address": address,
        "tags": list(_existing_supporting_field(card, "tags") or getattr(card, "tags", []) or [])[:6],
        "meta_line": meta_line,
        "why_pick": _strip_stale_disclaimer(
            _existing_supporting_field(card, "why_pick") or display_why
        ),
        "concierge_note": _strip_stale_disclaimer(_existing_supporting_field(card, "concierge_note")),
        "category_label": _existing_supporting_field(card, "category_label") or display_category,
        "price_level": price_level,
        "price_range": price_range,
        "editorial_mentions": _existing_supporting_field(card, "editorial_mentions"),
    }
    # Preserve any legacy supporting_details fields we did not rebuild
    if sd_existing is not None:
        for key in ("editorial_mentions",):
            value = getattr(sd_existing, key, None)
            if value is not None:
                sd_kwargs[key] = value
    card.supporting_details = PlaceSupportingDetails(**{
        k: v for k, v in sd_kwargs.items() if v is not None or k in ("rating", "review_count", "address", "meta_line")
    })

    # ── Build display block ──────────────────────────────────────────────
    card.display = ConciergeDisplayFields(
        display_name=name,
        display_category=display_category,
        display_meta_line=meta_line,
        display_why=display_why,
        display_price=display_price,
        display_badges=badges,
        addability=addability,
        display_why_source=why_source,
        display_why_validated=why_validated,
    )

    # ── Strip stale disclaimer from top-level user-visible fields ────────
    for attr in ("summary", "description", "reason", "primary_reason", "why_pick"):
        value = getattr(card, attr, None)
        if isinstance(value, str):
            cleaned = _strip_stale_disclaimer(value)
            if cleaned != value:
                try:
                    setattr(card, attr, cleaned or None)
                except Exception:  # pragma: no cover
                    pass

    # The legacy "source" string was used to surface the
    # "Sample bar research data..." disclaimer.  Normalize it away so
    # frontend cards no longer carry the stale label.
    src = getattr(card, "source", None)
    if isinstance(src, str):
        for fragment in STALE_DISCLAIMER_FRAGMENTS:
            if fragment in src:
                try:
                    card.source = NEUTRAL_LIMITED_COVERAGE_LABEL
                except Exception:  # pragma: no cover
                    pass
                break

    return card


def normalize_place_recommendations(response: Any) -> Any:
    """Normalize every card on a PlaceRecommendationsResponse / ConciergeSearchResponse.

    Safe to call on any object that exposes ``restaurants``, ``attractions``,
    and ``hotels`` list attributes.  Idempotent.  Mutates in place.
    """
    if response is None:
        return response
    for vertical, attr in (
        ("restaurant", "restaurants"),
        ("attraction", "attractions"),
        ("hotel", "hotels"),
    ):
        cards = getattr(response, attr, None)
        if not cards:
            continue
        for card in cards:
            try:
                normalize_unified_card(card, vertical=vertical)
            except Exception:
                # A normalization failure must never break a response.
                # The card simply ships with whatever fields the producer
                # already gave it; the contract test will fail loudly in CI.
                continue

    # Strip stale disclaimer from response-level "sources" list as well.
    sources = getattr(response, "sources", None)
    if isinstance(sources, list):
        cleaned_sources: List[str] = []
        for src in sources:
            if not isinstance(src, str):
                cleaned_sources.append(src)
                continue
            replaced = src
            for fragment in STALE_DISCLAIMER_FRAGMENTS:
                if fragment in replaced:
                    replaced = NEUTRAL_LIMITED_COVERAGE_LABEL
                    break
            cleaned_sources.append(replaced)
        try:
            response.sources = cleaned_sources
        except Exception:  # pragma: no cover
            pass

    return response
