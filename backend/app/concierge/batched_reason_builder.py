"""BatchedReasonBuilder — one LLM call for all card reasons in a turn.

Feature flag: CONCIERGE_BATCHED_REASONING_ENABLED (default: auto when ANTHROPIC_API_KEY set)

Design:
- Builds a single LLM prompt with evidence bundles for all cards.
- LLM must analyze evidence and decide whether a note is useful; it does not fill templates.
- Validates each output with ReasonValidator before accepting.
- Returns ReasoningResult contract alongside the note dict so callers can set truthful telemetry.
- Hard timeout guardrail: if the LLM call exceeds BATCHED_REASON_TIMEOUT_S,
  all cards fall back to their deterministic reasons (passed in by caller).
- Budget gate: skips LLM entirely if card count > MAX_CARDS_FOR_LLM_BATCH
  or if flag is disabled.

IMPORTANT: Any exception in the prompt builder or LLM call is reported in
ReasoningResult.prompt_error / failure_reason. grounded_reason_success in
telemetry MUST only be True when at least one LLM note was accepted.

Never raises. Always returns (dict, ReasoningResult).
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
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


@dataclass
class ReasoningResult:
    """Typed contract for the outcome of a batched reasoning run.

    Callers MUST use this to set telemetry. Do NOT infer success from
    reason_source strings or dict presence.
    """
    attempted: bool = False
    model: Optional[str] = None
    success: bool = False          # True only if accepted_count >= 1
    failure_reason: Optional[str] = None
    accepted_count: int = 0        # LLM notes that passed validation
    rejected_count: int = 0        # LLM notes rejected by validator
    omitted_count: int = 0         # Cards with no note (thin evidence)
    fallback_count: int = 0        # Cards using deterministic fallback
    prompt_error: bool = False     # True if prompt builder threw
    validator_rejection_reasons: List[str] = field(default_factory=list)
    diversity_flagged: bool = False


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
    lines.append(f"  - Rank position: {card_index} of {total_cards or '?'}")

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
            lines.append(f"  - Name signal: name includes concept '{primary_concept}'")

    # Source query used to find this place
    if getattr(entity, "source_query", None):
        lines.append(f"  - Found via query: {entity.source_query}")

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
            lines.append(f"  - Location: NOT confirmed on {modifier} — address does not match")

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
    """Build the batched LLM prompt for all cards in one turn.

    IMPORTANT: All {placeholder} examples in the prompt text must use double braces
    {{placeholder}} because this string is an f-string. Literal braces in the
    output text must be escaped. Failure to do this causes NameError at runtime.
    """
    user_query = getattr(frame, "literal_ask", "") or ""
    venue_concept = (
        frame.subtype_concepts[0].label if getattr(frame, "subtype_concepts", None) else ""
    )
    location_modifiers = getattr(frame, "location_modifiers", []) or []
    geo_hints = getattr(frame, "geography_hints", []) or []
    ambiguity_flags = getattr(frame, "ambiguity_flags", []) or []

    # Build user modifier context
    modifier_lines = []
    if location_modifiers:
        modifier_lines.append(
            f"  - User asked for places on/near: {location_modifiers[0]}. "
            "Mention ONLY as confirmed if the evidence says CONFIRMED. "
            "Otherwise acknowledge it was requested but not confirmed."
        )
    if geo_hints:
        modifier_lines.append(
            f"  - User mentioned geography: {geo_hints[0]}. "
            "Do NOT claim waterfront/river/lake/view proximity unless evidence confirms it."
        )
    if any("view" in f or "waterfront" in f for f in ambiguity_flags):
        modifier_lines.append(
            "  - VIEW/WATERFRONT requested: cannot be structurally verified from Google data. "
            "Be honest about this — do not invent or imply views."
        )
    if not modifier_lines:
        modifier_lines.append("  - No location or geography modifiers.")

    n = len(cards_data)
    evidence_blocks = []
    for i, (entity, evidence, rank_score, _det_reason) in enumerate(cards_data, 1):
        evidence_blocks.append(
            _build_evidence_text(entity, evidence, frame, rank_score, i, total_cards=n)
        )

    evidence_text = "\n\n".join(evidence_blocks)
    modifier_text = "\n".join(modifier_lines)
    concept_label = venue_concept or "place"

    # NOTE: All {example} placeholders below use {{double braces}} to prevent
    # Python f-string evaluation. These are literal text in the prompt.
    prompt = f"""You are a travel concierge writing one-sentence notes for {n} places. User asked: "{user_query}"

Your task: analyze each place's evidence and write a note that helps the traveler choose — or return null if the evidence is too thin to say anything useful.

User modifiers to respect:
{modifier_text}

ANTI-PATTERNS — these will be automatically rejected, do not waste tokens on them:
- "{{Name}} — {{rating}}★ from {{N}} reviews."                    ← just repeats the visible card
- "{{Name}} on {{Street}} — {{rating}}★ from {{N}} reviews."     ← same, just repeats fields
- "Verified {{category}} with {{rating}}★ across {{N}} reviews." ← fill-in-the-blank, no value
- "Strong/Good/Great {{concept}} match in {{city}}."             ← zero information
- Any note that claims waterfront/view/river proximity without CONFIRMED in evidence
- Any note that claims Michelin stars, awards, quiet/romantic atmosphere, price range, or hours
- Any note that repeats only name + rating + review count with no additional insight
- Any note so generic it could apply to any {concept_label} in this list

WHAT MAKES A USEFUL NOTE:
- It tells the traveler something specific they cannot already see from the card title and rating
- It honestly handles modifiers: confirmed → state it; not confirmed → acknowledge the gap
- It varies meaningfully across the {n} places — do not reuse the same sentence structure
- It is concise (one sentence or two short clauses, under {_REASON_MAX_CHARS} characters)
- Return null when evidence is too thin for a genuinely useful note (null is better than generic)

EVIDENCE — use ONLY what is listed here, do not invent facts:
{evidence_text}

Return ONLY a JSON object mapping place number (string) to note (string) or null:
{{"1": "...", "2": null, "3": "..."}}"""

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

    Values may be str (note) or None (LLM signaled thin evidence).
    """
    if not response_text:
        return {}
    try:
        # Try to extract JSON from the response (handles preamble/postamble from LLM)
        json_match = re.search(r"\{[^{}]+\}", response_text, re.DOTALL)
        if not json_match:
            return {}
        raw = json.loads(json_match.group(0))
        result: Dict[str, Optional[str]] = {}
        for k, v in raw.items():
            if v is None:
                result[str(k)] = None  # thin-evidence: caller will use empty/omitted
            elif isinstance(v, str) and v.strip():
                result[str(k)] = v.strip()
        return result
    except (json.JSONDecodeError, ValueError):
        return {}


def _skeleton(note: str) -> str:
    """Compute a structural skeleton by stripping names, numbers, and stopwords.

    Used for cross-card diversity checks. Two notes with the same skeleton
    are structurally identical even if they name different places.
    """
    s = re.sub(r"\d[\d.,]*\s*★?", "N", note)
    s = re.sub(r"\b(from|with|across|at|on|in|the|a|an|for|of|and|or|but)\b", "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def _check_note_diversity(accepted: Dict[str, str]) -> bool:
    """Return True if the accepted note set has adequate structural diversity.

    Returns False when too many notes share the same skeleton — a sign that
    the LLM is producing templates rather than genuine analysis.
    """
    notes = list(accepted.values())
    if len(notes) < 2:
        return True
    skeletons = [_skeleton(n) for n in notes]
    # Count how many notes share a skeleton prefix (first 50 chars is usually enough)
    prefixes = [s[:50] for s in skeletons]
    from collections import Counter
    prefix_counts = Counter(prefixes)
    if prefix_counts.most_common(1)[0][1] > 2:
        return False
    return True


def build_batched_reasons(
    cards_data: List[Tuple[Any, Any, Any, Any]],
    frame: Any,
    timeout: float = BATCHED_REASON_TIMEOUT_S,
) -> Tuple[Dict[str, str], ReasoningResult]:
    """Build grounded concierge notes for all cards in one LLM call.

    Args:
        cards_data: List of (entity, evidence_bundle, rank_score, det_reason)
                    where det_reason is the deterministic fallback for each card.
        frame: ExperienceFrame for the current turn.
        timeout: LLM call timeout in seconds.

    Returns:
        (note_dict, ReasoningResult) where note_dict maps str(1-based index) → reason.
        Falls back to deterministic reason per card on any failure.
        ReasoningResult.success is True ONLY when at least one LLM note was accepted.
        Never raises.
    """
    # Build deterministic fallback map upfront
    fallback = {str(i): det for i, (_e, _ev, _rs, det) in enumerate(cards_data, 1)}

    if not _flag_enabled():
        logger.debug("batched_reason_builder: flag disabled, using deterministic")
        result = ReasoningResult(
            attempted=False,
            success=False,
            failure_reason="flag_disabled",
            fallback_count=len(cards_data),
        )
        return fallback, result

    if not cards_data:
        return fallback, ReasoningResult(attempted=False, failure_reason="no_cards")

    if len(cards_data) > MAX_CARDS_FOR_LLM_BATCH:
        logger.info(
            "batched_reason_builder: card_count=%d exceeds max=%d, using deterministic",
            len(cards_data), MAX_CARDS_FOR_LLM_BATCH,
        )
        return fallback, ReasoningResult(
            attempted=False,
            failure_reason=f"card_count_exceeds_max:{len(cards_data)}",
            fallback_count=len(cards_data),
        )

    t_start = time.monotonic()
    reasoning_result = ReasoningResult(
        attempted=True,
        model=CONCIERGE_BATCHED_REASONING_MODEL,
    )

    try:
        # ── Build prompt ──────────────────────────────────────────────────────
        # Any exception here is a prompt_error — must NOT be reported as success.
        try:
            prompt = _build_batch_prompt(cards_data, frame)
        except Exception as prompt_exc:
            elapsed_ms = int((time.monotonic() - t_start) * 1000)
            logger.error(
                "batched_reason_builder: prompt_build_error elapsed_ms=%d error=%s",
                elapsed_ms, prompt_exc,
            )
            reasoning_result.prompt_error = True
            reasoning_result.success = False
            reasoning_result.failure_reason = f"prompt_build_error:{prompt_exc}"
            reasoning_result.fallback_count = len(cards_data)
            return fallback, reasoning_result

        # ── Call LLM ─────────────────────────────────────────────────────────
        raw_response = _call_llm(prompt, timeout=timeout)
        elapsed_ms = int((time.monotonic() - t_start) * 1000)

        if raw_response is None:
            logger.info(
                "batched_reason_builder: llm_no_response elapsed_ms=%d, using deterministic",
                elapsed_ms,
            )
            reasoning_result.failure_reason = "llm_no_response"
            reasoning_result.fallback_count = len(cards_data)
            return fallback, reasoning_result

        # ── Parse LLM response ────────────────────────────────────────────────
        parsed = _parse_llm_response(raw_response, len(cards_data))
        if not parsed:
            logger.warning(
                "batched_reason_builder: parse_failed elapsed_ms=%d response=%r",
                elapsed_ms, raw_response[:200],
            )
            reasoning_result.failure_reason = "parse_failed"
            reasoning_result.fallback_count = len(cards_data)
            return fallback, reasoning_result

        # ── Validate each LLM note ────────────────────────────────────────────
        from app.concierge.reason_validator import validate_reason
        evidence_by_idx = {
            str(i): ev for i, (_e, ev, _rs, _det) in enumerate(cards_data, 1)
        }

        result_notes = dict(fallback)  # start with all deterministic fallbacks
        accepted: Dict[str, str] = {}
        rejected_reasons: List[str] = []

        for idx_str, llm_reason in parsed.items():
            # None means LLM signaled thin evidence — omit note (use fallback or empty)
            if llm_reason is None:
                rejected_reasons.append(f"idx={idx_str}:thin_evidence_null")
                reasoning_result.omitted_count += 1
                continue

            idx_int = None
            try:
                idx_int = int(idx_str)
                cards_data[idx_int - 1][0]  # validate index in range
            except (ValueError, IndexError):
                continue

            ev = evidence_by_idx.get(idx_str)
            if ev is None:
                continue

            # Basic length check
            words = llm_reason.split()
            if len(words) < _REASON_MIN_WORDS:
                rejected_reasons.append(f"idx={idx_str}:too_short")
                reasoning_result.rejected_count += 1
                continue
            if len(llm_reason) > _REASON_MAX_CHARS:
                llm_reason = llm_reason[:_REASON_MAX_CHARS].rsplit(" ", 1)[0] + "…"

            is_valid, rejection = validate_reason(llm_reason, frame, ev)
            if is_valid:
                result_notes[idx_str] = llm_reason
                accepted[idx_str] = llm_reason
                reasoning_result.accepted_count += 1
            else:
                rejected_reasons.append(f"idx={idx_str}:{rejection}")
                reasoning_result.rejected_count += 1

        # ── Cross-card diversity check ────────────────────────────────────────
        if len(accepted) >= 2 and not _check_note_diversity(accepted):
            logger.warning(
                "batched_reason_builder: low_diversity accepted=%d, flagging",
                len(accepted),
            )
            reasoning_result.diversity_flagged = True
            # Don't discard — let them render (per-card validator already blocked worst cases)

        reasoning_result.fallback_count = len(cards_data) - reasoning_result.accepted_count - reasoning_result.omitted_count
        reasoning_result.validator_rejection_reasons = rejected_reasons

        # success = True only when at least one LLM note was accepted
        reasoning_result.success = reasoning_result.accepted_count >= 1
        if not reasoning_result.success:
            reasoning_result.failure_reason = (
                "all_llm_notes_rejected_or_thin"
                if not reasoning_result.failure_reason
                else reasoning_result.failure_reason
            )

        validator_rejected = reasoning_result.rejected_count
        logger.info(
            "batched_reason_builder: llm_path "
            "reasoning_model=%s "
            "reasoning_attempted=true "
            "reasoning_success=%s "
            "llm_accepted_count=%d "
            "validator_rejected_count=%d "
            "note_omitted_count=%d "
            "fallback_count=%d "
            "diversity_flagged=%s "
            "elapsed_ms=%d "
            "rejected=%r",
            CONCIERGE_BATCHED_REASONING_MODEL,
            reasoning_result.success,
            reasoning_result.accepted_count,
            validator_rejected,
            reasoning_result.omitted_count,
            reasoning_result.fallback_count,
            reasoning_result.diversity_flagged,
            elapsed_ms,
            rejected_reasons,
        )
        return result_notes, reasoning_result

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - t_start) * 1000)
        logger.warning(
            "batched_reason_builder: unhandled_error elapsed_ms=%d error=%s",
            elapsed_ms, exc,
        )
        reasoning_result.success = False
        reasoning_result.failure_reason = f"unhandled_error:{exc}"
        reasoning_result.fallback_count = len(cards_data)
        return fallback, reasoning_result
