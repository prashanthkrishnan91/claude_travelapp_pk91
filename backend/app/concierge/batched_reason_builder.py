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
# Default: sonnet for production validation quality. Downgrade to haiku only after
# production quality passes. Override via Railway env: CONCIERGE_BATCHED_REASONING_MODEL.
CONCIERGE_BATCHED_REASONING_MODEL = os.getenv(
    "CONCIERGE_BATCHED_REASONING_MODEL", "claude-sonnet-4-6"
)
_REASON_MIN_WORDS = 8
_REASON_MAX_CHARS = 220


def _flag_enabled() -> bool:
    """LLM reasoning is the preferred path — auto-enable when ANTHROPIC_API_KEY is present.

    Override with CONCIERGE_BATCHED_REASONING_ENABLED=true/false to force on/off.
    When auto (env var not set), enabled iff ANTHROPIC_API_KEY is configured.
    """
    explicit = os.getenv("CONCIERGE_BATCHED_REASONING_ENABLED", "").lower()
    if explicit in ("true", "false"):
        return explicit == "true"
    # Auto-enable when API key is present — LLM synthesis is the quality path
    return bool(os.getenv("ANTHROPIC_API_KEY", ""))


def _extract_street_from_address(address: str) -> str:
    """Extract the street name portion (e.g. 'Fulton Street') from a formatted address."""
    import re
    if not address:
        return ""
    first_part = address.split(",")[0].strip()
    without_number = re.sub(r"^\d+\s*", "", first_part).strip()
    without_dir = re.sub(
        r"^(?:North|South|East|West|NW|SW|NE|SE|N|S|E|W)\s+",
        "", without_number, flags=re.IGNORECASE,
    ).strip()
    expansions = {
        r"\bSt\b": "Street", r"\bAve\b": "Avenue", r"\bBlvd\b": "Boulevard",
        r"\bDr\b": "Drive", r"\bRd\b": "Road", r"\bPl\b": "Place",
        r"\bCt\b": "Court", r"\bLn\b": "Lane", r"\bPkwy\b": "Parkway",
    }
    result = without_dir
    for pat, rep in expansions.items():
        result = re.sub(pat, rep, result, flags=re.IGNORECASE)
    result = result.strip()
    if len(result) >= 3 and not re.match(r"^\d", result):
        return result
    return ""


def _build_evidence_text(
    entity: Any,
    evidence: Any,
    frame: Any,
    rank_score: Any,
    card_index: int,
    total_cards: int = 0,
) -> str:
    """Render an evidence bundle as structured text for the LLM prompt.

    Every field exposed here is a grounding anchor for the LLM note.
    The LLM must only write claims that appear in this evidence block.
    """
    lines = [f"Place {card_index}{f'/{total_cards}' if total_cards else ''}: {entity.name}"]

    # Street name — key card-specific anchor
    addr = entity.formatted_address or ""
    street = _extract_street_from_address(addr)
    if street:
        lines.append(f"  - Street: {street}")
    if addr:
        lines.append(f"  - Full address: {addr}")

    # Name signal: does the name mention the concept? (informative to the LLM)
    primary_concept = ""
    if getattr(frame, "subtype_concepts", None):
        primary_concept = frame.subtype_concepts[0].label if frame.subtype_concepts else ""
    if primary_concept:
        name_lower = entity.name.lower()
        concept_tokens = [t for t in primary_concept.lower().split() if len(t) >= 4]
        if any(t in name_lower for t in concept_tokens):
            lines.append(f"  - Name signal: name includes '{primary_concept}' concept")

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
            lines.append(f"  - Location: CONFIRMED on {modifier}")
        elif not_confirmed:
            lines.append(f"  - Location: NOT confirmed on {modifier} — address does not mention it")

    # Geo note
    if evidence.geo_note:
        lines.append(f"  - Geo note: {evidence.geo_note}")

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

    n = len(cards_data)
    evidence_blocks = []
    for i, (entity, evidence, rank_score, _det_reason) in enumerate(cards_data, 1):
        evidence_blocks.append(
            _build_evidence_text(entity, evidence, frame, rank_score, i, total_cards=n)
        )

    evidence_text = "\n\n".join(evidence_blocks)

    prompt = f"""You are writing concierge notes for a travel app. The user asked: "{user_query}"
Venue concept: {venue_concept or "place"}{modifier_note}

RULES — read before writing:
1. Ground every note ONLY in the evidence fields provided (Street, Full address, Rating, Name signal, Geo note, Location confirmed/not confirmed). Do not invent facts.
2. Each note must name something SPECIFIC to that place: its street name, a rating, its actual name, or a confirmed location. Generic sentences like "A great spot for {concept} lovers" are banned.
3. BANNED TEMPLATES — never produce these patterns:
   - "Verified {category} with {rating}★ across {N} reviews."  ← no card specificity
   - "Strong/Good/Great {concept} match in {city}."  ← generic
   - "Perfect for {concept} enthusiasts in {city}."  ← generic
4. If a location modifier is NOT confirmed in the evidence, say so honestly ("not directly on X, but nearby"). Never claim a place IS on the modifier unless evidence says CONFIRMED.
5. If the only available evidence is name + rating (no street, no confirmed modifier, no geo note), return null for that place — an empty note is better than a generic template.
6. Notes must VARY across cards — do not repeat the same sentence structure for all places. Each note should read distinctly.
7. Do NOT use words: "verified", "Google", "OPERATIONAL", "subtype_fit", "geo_fit", "rank_score".

{evidence_text}

Respond with ONLY a valid JSON object mapping place number (as string) to the note (or null for thin evidence):
{{"1": "note for place 1", "2": null, "3": "note for place 3", ...}}"""

    return prompt


def _call_llm(prompt: str, timeout: float, model: str = "") -> Optional[str]:
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

    resolved_model = model or CONCIERGE_BATCHED_REASONING_MODEL
    logger.debug("batched_reason_builder: calling model=%s", resolved_model)
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=resolved_model,
            max_tokens=1024,
            timeout=timeout,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text if message.content else None
    except Exception as exc:
        logger.warning(
            "batched_reason_builder: llm_call_failed model=%s error=%s", resolved_model, exc
        )
        return None


def _parse_llm_response(response_text: str, expected_count: int) -> Dict[str, Optional[str]]:
    """Parse JSON from LLM response. Returns empty dict on any parse error.

    Values may be str (note) or None (LLM signaled thin evidence — use deterministic fallback).
    """
    if not response_text:
        return {}
    try:
        # Try to extract JSON from the response (handles preamble/postamble from LLM)
        json_match = re.search(r"\{[^{}]+\}", response_text, re.DOTALL)
        if not json_match:
            return {}
        raw = json.loads(json_match.group(0))
        # Accept str values (notes) and None (thin-evidence signal)
        result: Dict[str, Optional[str]] = {}
        for k, v in raw.items():
            if v is None:
                result[str(k)] = None  # thin-evidence: caller will use deterministic fallback
            elif isinstance(v, str) and v.strip():
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
            # None means LLM signaled thin evidence — stay on deterministic fallback
            if llm_reason is None:
                rejected_reasons.append(f"idx={idx_str}:thin_evidence_null")
                continue

            idx_int = None
            try:
                idx_int = int(idx_str)
                cards_data[idx_int - 1][0]  # validate index
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

        validator_rejected = len([r for r in rejected_reasons if "thin_evidence" not in r])
        logger.info(
            "batched_reason_builder: llm_path "
            "grounded_reason_model=%s "
            "grounded_reason_attempted=%d "
            "grounded_reason_success=%d "
            "fallback_note_count=%d "
            "validator_rejected_count=%d "
            "elapsed_ms=%d "
            "rejected=%r",
            CONCIERGE_BATCHED_REASONING_MODEL,
            len(cards_data),
            accepted,
            len(cards_data) - accepted,
            validator_rejected,
            elapsed_ms,
            rejected_reasons,
        )
        return result

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - t_start) * 1000)
        logger.warning(
            "batched_reason_builder: unhandled_error elapsed_ms=%d error=%s",
            elapsed_ms, exc,
        )
        return fallback
