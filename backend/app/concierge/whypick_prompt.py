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
) -> str:
    safe_units = [eu for eu in evidence_units if eu.safe_for_copy][:8]
    evidence_lines = "\n".join(
        f"  [{eu.id}] {eu.claim_type}: {eu.claim}"
        for eu in safe_units
    ) if safe_units else "  (none)"
    return (
        f"Venue: {venue_name}\n"
        f"Category: {category}\n"
        f"Request intent: {intent}\n"
        f"\nEvidence units (safe_for_copy only):\n{evidence_lines}\n\n"
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

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=effective_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=_build_system_prompt(),
            messages=[{"role": "user", "content": _build_user_prompt(
                venue_name, category, intent, evidence_units,
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
