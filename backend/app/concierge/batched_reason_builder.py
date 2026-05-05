"""BatchedReasonBuilder — one LLM call for all card reasons in a turn.

Feature flag: CONCIERGE_BATCHED_REASONING_ENABLED (default False)

Design:
- Builds a single LLM prompt with evidence bundles for all cards.
- LLM may only write from the provided evidence. No invented facts.
- Validates each output with ReasonValidator before accepting.
- Per-card fallback to SafeReasonBuilder deterministic output on any failure.
- Hard timeout guardrail: if the LLM call exceeds BATCHED_REASON_TIMEOUT_S,
  all cards fall back to deterministic reasons.
- Budget gate: skips LLM entirely if card count > MAX_CARDS_FOR_LLM_BATCH
  or if flag is disabled.

Never raises. Always returns a dict of card_key → reason string.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

BATCHED_REASON_TIMEOUT_S = float(os.getenv("BATCHED_REASON_TIMEOUT_S", "3.0"))
MAX_CARDS_FOR_LLM_BATCH = int(os.getenv("BATCHED_REASON_MAX_CARDS", "8"))
_REASON_MIN_WORDS = 8
_REASON_MAX_CHARS = 220


def _flag_enabled() -> bool:
    return os.getenv("CONCIERGE_BATCHED_REASONING_ENABLED", "false").lower() == "true"


def _build_evidence_text(
    entity: Any,
    evidence: Any,
    frame: Any,
    rank_score: Any,
    card_index: int,
) -> str:
    """Render an evidence bundle as structured text for the LLM prompt."""
    lines = [f"Place {card_index}: {entity.name}"]

    # Google type
    for fact in evidence.structured_facts:
        if "Google type" in fact:
            lines.append(f"  - {fact}")
            break

    # Rating fact
    for fact in evidence.structured_facts:
        if "Rating:" in fact:
            lines.append(f"  - {fact}")
            break

    # Address (short)
    addr = entity.formatted_address or ""
    if addr:
        lines.append(f"  - Address: {addr}")

    # Concept match signal
    for fact in evidence.structured_facts:
        if "match" in fact.lower():
            lines.append(f"  - {fact}")
            break

    # Location modifier status
    location_modifiers = getattr(frame, "location_modifiers", []) or []
    if location_modifiers:
        modifier = location_modifiers[0]
        confirmed = any(
            "confirms" in f and modifier.lower() in f.lower()
            for f in evidence.structured_facts
        )
        not_confirmed = any(
            f.startswith(f"location_modifier_not_confirmed:{modifier}")
            for f in evidence.uncertainty_flags
        )
        if confirmed:
            lines.append(f"  - Location: confirmed in {modifier} area")
        elif not_confirmed:
            lines.append(f"  - Location: NOT confirmed on {modifier} (address does not mention it)")

    # Geo note
    if evidence.geo_note:
        lines.append(f"  - Geo: {evidence.geo_note}")

    # Uncertainty flags (redacted to user-safe phrasing)
    safe_flags = []
    for flag in evidence.uncertainty_flags:
        if "water_view" in flag:
            safe_flags.append("water view cannot be verified from Google data")
        elif "noise_level" in flag:
            safe_flags.append("noise level cannot be verified from Google data")
        elif "ambiance" in flag:
            safe_flags.append("ambiance cannot be verified from Google data")
    if safe_flags:
        lines.append(f"  - Cannot verify: {', '.join(safe_flags)}")

    return "\n".join(lines)


def _build_batch_prompt(
    cards_data: List[Tuple[Any, Any, Any, Any]],
    frame: Any,
) -> str:
    """Build the batched LLM prompt for all cards in one turn."""
    user_query = getattr(frame, "literal_ask", "") or ""
    venue_concept = (
        frame.subtype_concepts[0].label if getattr(frame, "subtype_concepts", None) else ""
    )
    location_modifiers = getattr(frame, "location_modifiers", []) or []
    geo_hints = getattr(frame, "geography_hints", []) or []

    modifier_note = ""
    if location_modifiers:
        modifier_note = (
            f"\nUser's location modifier: {location_modifiers[0]}"
            " — ONLY mention this as confirmed if the evidence says so."
        )
    if geo_hints:
        modifier_note += f"\nUser's geography hint: {geo_hints[0]} (soft preference, may not be verifiable)"

    evidence_blocks = []
    for i, (entity, evidence, rank_score, _det_reason) in enumerate(cards_data, 1):
        evidence_blocks.append(
            _build_evidence_text(entity, evidence, frame, rank_score, i)
        )

    evidence_text = "\n\n".join(evidence_blocks)

    prompt = f"""You are writing concierge notes for a travel app. The user asked: "{user_query}"
Venue concept: {venue_concept or "place"}{modifier_note}

For each place below, write ONE concise sentence (20-50 words) that:
- Is grounded ONLY in the evidence provided below
- Answers why this place fits the user's request
- ONLY mentions the location modifier if evidence says it is confirmed there
- If NOT confirmed on the modifier, says so honestly (e.g., "not directly on X, but nearby")
- Does NOT invent waterfront views, ambience, awards, Michelin stars, prices, or hours
- Does NOT use words: "verified", "Google", "OPERATIONAL", "subtype_fit", "geo_fit"
- Does NOT repeat the same phrase across all cards

{evidence_text}

Respond with ONLY a valid JSON object mapping place number (as string) to the note:
{{"1": "note for place 1", "2": "note for place 2", ...}}"""

    return prompt


def _call_llm(prompt: str, timeout: float) -> Optional[str]:
    """Call the Claude API with a timeout. Returns raw response text or None."""
    try:
        import anthropic  # type: ignore[import]
    except ImportError:
        logger.warning("batched_reason_builder: anthropic SDK not installed, skipping LLM")
        return None

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("batched_reason_builder: ANTHROPIC_API_KEY not set, skipping LLM")
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            timeout=timeout,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text if message.content else None
    except Exception as exc:
        logger.warning("batched_reason_builder: llm_call_failed error=%s", exc)
        return None


def _parse_llm_response(response_text: str, expected_count: int) -> Dict[str, str]:
    """Parse JSON from LLM response. Returns empty dict on any parse error."""
    if not response_text:
        return {}
    try:
        # Try to extract JSON from the response
        json_match = re.search(r"\{[^{}]+\}", response_text, re.DOTALL)
        if not json_match:
            return {}
        raw = json.loads(json_match.group(0))
        # Validate structure: must be str→str with numeric keys
        result = {}
        for k, v in raw.items():
            if isinstance(v, str) and v.strip():
                result[str(k)] = v.strip()
        return result
    except (json.JSONDecodeError, ValueError):
        return {}


def build_batched_reasons(
    cards_data: List[Tuple[Any, Any, Any, Any]],
    frame: Any,
    timeout: float = BATCHED_REASON_TIMEOUT_S,
) -> Dict[str, str]:
    """Build grounded concierge notes for all cards in one LLM call.

    Args:
        cards_data: List of (entity, evidence_bundle, rank_score, det_reason)
                    where det_reason is the deterministic fallback for each card.
        frame: ExperienceFrame for the current turn.
        timeout: LLM call timeout in seconds.

    Returns:
        Dict mapping str(card_index_1based) → reason string.
        Falls back to deterministic reason per card on any failure.
        Never raises.
    """
    # Build deterministic fallback map upfront
    fallback = {str(i): det for i, (_e, _ev, _rs, det) in enumerate(cards_data, 1)}

    if not _flag_enabled():
        logger.debug("batched_reason_builder: flag disabled, using deterministic")
        return fallback

    if not cards_data:
        return fallback

    if len(cards_data) > MAX_CARDS_FOR_LLM_BATCH:
        logger.info(
            "batched_reason_builder: card_count=%d exceeds max=%d, using deterministic",
            len(cards_data), MAX_CARDS_FOR_LLM_BATCH,
        )
        return fallback

    t_start = time.monotonic()
    try:
        prompt = _build_batch_prompt(cards_data, frame)
        raw_response = _call_llm(prompt, timeout=timeout)
        elapsed_ms = int((time.monotonic() - t_start) * 1000)

        if raw_response is None:
            logger.info(
                "batched_reason_builder: llm_no_response elapsed_ms=%d, using deterministic",
                elapsed_ms,
            )
            return fallback

        parsed = _parse_llm_response(raw_response, len(cards_data))
        if not parsed:
            logger.warning(
                "batched_reason_builder: parse_failed elapsed_ms=%d response=%r",
                elapsed_ms, raw_response[:200],
            )
            return fallback

        # Validate each LLM reason; fall back per-card if invalid
        from app.concierge.reason_validator import validate_reason
        evidence_by_idx = {
            str(i): ev for i, (_e, ev, _rs, _det) in enumerate(cards_data, 1)
        }

        result = dict(fallback)  # start with all deterministic fallbacks
        accepted = 0
        rejected_reasons: List[str] = []

        for idx_str, llm_reason in parsed.items():
            entity = None
            idx_int = None
            try:
                idx_int = int(idx_str)
                entity = cards_data[idx_int - 1][0]
            except (ValueError, IndexError):
                continue

            ev = evidence_by_idx.get(idx_str)
            if ev is None:
                continue

            # Basic length check
            words = llm_reason.split()
            if len(words) < _REASON_MIN_WORDS:
                rejected_reasons.append(f"idx={idx_str}:too_short")
                continue
            if len(llm_reason) > _REASON_MAX_CHARS:
                llm_reason = llm_reason[:_REASON_MAX_CHARS].rsplit(" ", 1)[0] + "…"

            is_valid, rejection = validate_reason(llm_reason, frame, ev)
            if is_valid:
                result[idx_str] = llm_reason
                accepted += 1
            else:
                rejected_reasons.append(f"idx={idx_str}:{rejection}")

        logger.info(
            "batched_reason_builder: llm_path elapsed_ms=%d accepted=%d/%d rejected=%r",
            elapsed_ms, accepted, len(cards_data), rejected_reasons,
        )
        return result

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - t_start) * 1000)
        logger.warning(
            "batched_reason_builder: unhandled_error elapsed_ms=%d error=%s",
            elapsed_ms, exc,
        )
        return fallback
