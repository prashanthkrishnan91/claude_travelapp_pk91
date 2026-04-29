"""Narrow LLM whyPick generation with structured evidence injection.

LLM may only synthesize from provided safe EvidenceUnits.
It must not discover facts, rank places, or decide addability.
Returns None on any failure so the caller uses deterministic fallback.
No Supabase SQL required.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import List, Literal, Optional, TypedDict

from app.concierge.evidence import EvidenceUnit, _WHYPICK_CACHE, evidence_cache_key

logger = logging.getLogger(__name__)

_SOURCE_NAME_RE = re.compile(
    r"\b(yelp|foursquare|tavily|eater|infatuation|timeout|tripadvisor|opentable|resy|google)\b",
    re.IGNORECASE,
)
_MARKDOWN_RE = re.compile(r"#{1,6}\s|[*`\[\]]|^\s*[-•]\s+", re.MULTILINE)
_RATING_FIRST_RE = re.compile(r"^\s*(?:with\s+)?(?:rated?\s+)?\d+[\.,]\d+", re.IGNORECASE)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_VAGUE_PHRASES = frozenset({
    "a great place",
    "a wonderful place",
    "highly recommended",
    "a must visit",
    "a must-visit",
    "very popular",
    "a popular choice",
    "well known",
    "well-known",
})

# ── Differentiator selection ──────────────────────────────────────────────────

# Preferred claim types for differentiator selection (lower index = higher priority).
# Specialty/vibe/editorial signals first; generic rating/count/location last.
_DIFFERENTIATOR_PREFERRED: tuple = (
    "michelin_status",
    "editorial_mention",
    "foursquare_tag",
    "foursquare_category",
    "attribute",
    "tavily_snippet",
)

# Claim types too generic to anchor a whyPick sentence.
_GENERIC_CLAIM_TYPES: frozenset = frozenset({
    "rating",
    "yelp_rating",
    "review_volume",
    "location",
    "google_verified",
    "neighborhood",
    "price_level",
    "yelp_review_excerpt",
})


def select_differentiators(evidence_units: List[EvidenceUnit]) -> List[EvidenceUnit]:
    """Pick 1–2 venue-specific differentiators before the LLM call.

    Prefers specialty, vibe, editorial, and crowd-specific signals.
    Deprioritizes rating, review count, location, and Google verification.
    Returns an empty list when no strong differentiators exist.
    """
    preferred_order = {ct: i for i, ct in enumerate(_DIFFERENTIATOR_PREFERRED)}
    candidates = [
        eu for eu in evidence_units
        if eu.safe_for_copy and eu.claim_type not in _GENERIC_CLAIM_TYPES
    ]
    candidates.sort(key=lambda eu: preferred_order.get(eu.claim_type, len(_DIFFERENTIATOR_PREFERRED)))
    return candidates[:2]


# ── Generic output detection ──────────────────────────────────────────────────

# Strip rating/count/volume signals when checking for specificity.
_STRIP_RATING_VOLUME_RE = re.compile(
    r"\b\d+[\.,]\d+\s+(?:rating|stars?)\b"
    r"|\b\d[\d,]+\s+(?:reviews?|ratings?)\b"
    r"|\b(?:strong|high|solid|deep|standout|large|great|impressive)\s+(?:review\s+)?(?:volume|depth|count)\b"
    r"|\b(?:consistent|reliable|strong|high|solid|great)\s+ratings?\b"
    r"|\b(?:highly|well)[- ]rated\b"
    r"|\bgoogle[- ]verified\b"
    r"|\bverified\s+(?:on\s+)?google\b"
    r"|\boperational\s+and\s+verified\b",
    re.IGNORECASE,
)

# Words that are structurally necessary but carry no venue-specific signal.
_GENERIC_TOKENS: frozenset = frozenset({
    "a", "an", "the", "is", "are", "was", "with", "and", "or", "for",
    "to", "of", "on", "at", "in", "near", "by", "its", "this", "that",
    "which", "where", "has", "have", "been", "their", "here", "there",
    "from", "into", "per", "via", "out", "all", "both", "just",
    # Generic quality adjectives
    "well", "solid", "reliable", "popular", "good", "great", "strong",
    "consistent", "dependable", "trusted", "practical", "useful", "lively",
    "busy", "high", "deep", "standout", "large", "impressive", "notable",
    # Words that appear in "well-regarded", "well-rated", etc.
    "regarded", "rated", "noted", "established", "known", "recognized",
    "verified", "operational", "confirmed", "listed",
    # Generic outcome nouns
    "pick", "option", "choice", "stop", "spot", "evening", "night",
    "dining", "drinks", "anchor", "staple", "base", "destination",
    "making", "providing", "offering", "being",
})

# Venue category tokens that are not differentiators.
_CATEGORY_TOKENS: frozenset = frozenset({
    "restaurant", "restaurants", "bar", "bars", "cafe", "cafes", "hotel",
    "hotels", "attraction", "venue", "venues", "place", "places",
    "cocktail", "cocktails", "nightclub", "lounge", "brewery", "winery",
    "dining", "bistro",
})


def _lacks_venue_specific_differentiator(text: str) -> bool:
    """Return True when the text's main content is only category + location + rating/volume.

    After stripping rating/count/volume patterns, location phrases, and generic
    structural words, fewer than 2 substantive tokens means nothing venue-specific remains.
    """
    working = _STRIP_RATING_VOLUME_RE.sub("", text.strip())
    # Remove location phrases ("in West Loop", "near the hotel", "in Chicago")
    working = re.sub(
        r"\b(?:in|near|at)\s+[A-Z][\w''.\-]+(?:\s+[A-Z][\w''.\-]+)*\b", "", working
    )
    working = re.sub(r"\b(?:in|near|at)\s+the\s+\w+\b", "", working, flags=re.IGNORECASE)
    tokens = re.findall(r"[a-zA-Z]{3,}", working.lower())
    substantive = [t for t in tokens if t not in _GENERIC_TOKENS and t not in _CATEGORY_TOKENS]
    return len(substantive) < 2


class WhyPickLLMResult(TypedDict):
    whyPick: str
    evidenceIdsUsed: List[str]
    confidence: Literal["high", "medium", "low"]
    fallbackReason: str


def _build_system_prompt() -> str:
    return (
        "You are a travel concierge copywriter. Write a single, concrete, one-sentence "
        "reason (max 140 characters) why a traveler should choose a specific venue, "
        "based ONLY on the evidence units provided.\n\n"
        "Strict rules:\n"
        "- Use ONLY the provided evidence; never invent or imply facts not present\n"
        "- Never mention source platform names (Yelp, Foursquare, Tavily, Eater, etc.)\n"
        "- No markdown, bullets, or debug metadata\n"
        "- Exactly ONE sentence, max 140 characters\n"
        "- Lead with the venue category or distinctive quality, not its rating number\n"
        "- Never rank or compare to other places, never judge addability\n"
        "- Output must be valid JSON only, no preamble"
    )


def _build_user_prompt(
    venue_name: str,
    category: str,
    intent: str,
    evidence_units: List[EvidenceUnit],
    selected_differentiators: Optional[List[EvidenceUnit]] = None,
) -> str:
    safe_units = [eu for eu in evidence_units if eu.safe_for_copy][:8]
    evidence_lines = "\n".join(
        f"  [{eu.id}] {eu.claim_type}: {eu.claim}"
        for eu in safe_units
    ) if safe_units else "  (none)"

    if selected_differentiators:
        diff_lines = "\n".join(
            f"  [{eu.id}] {eu.claim_type}: {eu.claim}"
            for eu in selected_differentiators
        )
        diff_section = (
            f"\nPRIMARY DIFFERENTIATORS — anchor your whyPick on 1–2 of these:\n"
            f"{diff_lines}\n"
            "\nCritical rules:\n"
            "- Your whyPick MUST use the PRIMARY DIFFERENTIATORS as its main hook\n"
            "- Do NOT use rating numbers, review counts, or Google verification as the primary reason\n"
            "- Do NOT use location alone — pair it with a specific quality from the differentiators\n"
        )
    else:
        diff_section = (
            "\nNo strong differentiators found — use the most specific evidence available.\n"
            "- Do NOT lead with rating, review count, or location alone\n"
        )

    return (
        f"Venue: {venue_name}\n"
        f"Category: {category}\n"
        f"Request intent: {intent}\n"
        f"{diff_section}"
        f"\nAll evidence (context):\n{evidence_lines}\n\n"
        "Respond with JSON only — no preamble, no markdown:\n"
        '{"whyPick": "...", "evidenceIdsUsed": ["id1", ...], '
        '"confidence": "high|medium|low", "fallbackReason": "..."}'
    )


def validate_llm_output(
    result: WhyPickLLMResult,
    *,
    venue_name: str,
    category: str,
    evidence_units: List[EvidenceUnit],
    known_venue_names: Optional[List[str]] = None,
) -> Optional[str]:
    """Validate LLM whyPick output. Returns a rejection reason string, or None if valid."""
    text = (result.get("whyPick") or "").strip()

    if len(text) < 15:
        return "output too short"

    normalized = text.lower().strip(" .")
    if normalized in _VAGUE_PHRASES:
        return "vague output"

    if _SOURCE_NAME_RE.search(text):
        return "source name in user-facing copy"

    if _MARKDOWN_RE.search(text):
        return "markdown or debug text in output"

    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    if len(sentences) > 2:
        return "multi-sentence output"
    if len(sentences) == 2 and len(text) > 140:
        return "output too long"

    if _RATING_FIRST_RE.match(text):
        return "rating-first output"

    cat_lower = (category or "").lower()
    if cat_lower in ("restaurant", "cafe"):
        bar_tokens = ("speakeasy", "nightclub", "cocktail bar", "late-night", "after-hours")
        if any(t in text.lower() for t in bar_tokens):
            return "category mismatch: bar language in restaurant context"
    if cat_lower == "bar":
        restaurant_tokens = ("tasting menu", "fine dining restaurant", "michelin-starred restaurant")
        if any(t in text.lower() for t in restaurant_tokens):
            return "category mismatch: restaurant language in bar context"

    for other_name in (known_venue_names or []):
        if other_name and other_name.lower() != venue_name.lower():
            if len(other_name) >= 4 and other_name.lower() in text.lower():
                return f"cross-venue contamination: {other_name}"

    evidence_ids_used = result.get("evidenceIdsUsed") or []
    valid_ids = {eu.id for eu in evidence_units}
    if evidence_ids_used and not any(eid in valid_ids for eid in evidence_ids_used):
        return "evidence IDs do not match provided units"

    if _lacks_venue_specific_differentiator(text):
        return "generic output: lacks venue-specific differentiator"

    return None


def generate_llm_why_pick(
    *,
    venue_name: str,
    category: str,
    intent: str,
    city: str,
    evidence_units: List[EvidenceUnit],
    api_key: Optional[str] = None,
    known_venue_names: Optional[List[str]] = None,
) -> Optional[WhyPickLLMResult]:
    """Call the LLM to synthesize a whyPick from structured evidence.

    Returns None on any failure — the caller must always have a
    deterministic fallback ready. Cache key = venue + city + intent + evidence hash.
    Never raises exceptions.
    """
    effective_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not effective_key:
        return None

    safe_units = [eu for eu in evidence_units if eu.safe_for_copy]
    if not safe_units:
        return None

    cache_key = evidence_cache_key(venue_name, city, intent, evidence_units)
    cached = _WHYPICK_CACHE.get(cache_key)
    if cached is not None:
        return cached

    differentiators = select_differentiators(evidence_units)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=effective_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=_build_system_prompt(),
            messages=[{"role": "user", "content": _build_user_prompt(
                venue_name, category, intent, evidence_units,
                selected_differentiators=differentiators,
            )}],
        )
        raw = message.content[0].text.strip()
    except Exception as exc:
        logger.debug("whyPick LLM call failed for %s: %s", venue_name, exc)
        return None

    try:
        clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        result: WhyPickLLMResult = json.loads(clean)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.debug("whyPick JSON parse failed for %s: %s", venue_name, exc)
        return None

    rejection = validate_llm_output(
        result,
        venue_name=venue_name,
        category=category,
        evidence_units=evidence_units,
        known_venue_names=known_venue_names,
    )
    if rejection:
        logger.debug("whyPick validation rejected for %s: %s", venue_name, rejection)
        return None

    _WHYPICK_CACHE.set(cache_key, result)
    return result
