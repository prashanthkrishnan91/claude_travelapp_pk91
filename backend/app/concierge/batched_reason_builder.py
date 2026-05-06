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

--- Reasoning Reliability v2 ---

build_reasons_with_retry() is the new orchestrator for semantic place cards.
It implements a three-pass cascade:
  Pass 1: Primary model, all cards in one batch.
  Pass 2: Primary model retry for any cards missing after pass 1.
  Pass 3: Fallback model for any cards still missing after pass 2.

Cards without validated notes after all passes are returned with validated=False.
Callers MUST exclude cards with validated=False from the visible card set.
Deterministic fallback is NEVER used as a visible Concierge Note.

New env vars (Reasoning Reliability v2):
  CONCIERGE_CARD_REASONING_PRIMARY_MODEL  (default: claude-haiku-4-5-20251001)
  CONCIERGE_CARD_REASONING_FALLBACK_MODEL (default: claude-sonnet-4-6)
  CONCIERGE_CARD_REASONING_TIMEOUT_MS     (default: 8000)
  CONCIERGE_CARD_REASONING_MAX_RETRIES    (default: 1)
  CONCIERGE_CARD_REASONING_BATCH_SIZE     (default: 6)
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

# ── Quality critic patterns ───────────────────────────────────────────────────
# These pass the validator (no fabricated claims, no banned attributes) but
# are too shallow to be useful concierge notes. Reject and retry.
_QUALITY_THIN_RE = re.compile(
    r"(?:"
    r"matches?\s+(?:the\s+)?\w+\s+concept\b"               # "matches the taproom concept"
    r"|\bsolid\s+\w+\s+signals?\b"                          # "solid brewery signals"
    r"|\bstrong\s+name[\s\-]+and[\s\-]+type\b"              # "strong name-and-type concept signals"
    r"|\bmatches?\s+on\s+\w+\s+type\s+and\s+name\b"         # "matches on taproom type and name"
    r"|\breliable\s+\w+\s+destination\b"                    # "a reliable taproom destination"
    r"|\ban?\s+established\s+\w+\s+with\s+solid\b"          # "an established taproom with solid..."
    r"|\bhas\s+(?:solid|strong)\s+\w+\s+(?:signals?|fit)\b" # "has solid concept fit"
    r"|\b\w+\s+concept\s+(?:fit|match|signals?)\b"          # "izakaya concept fit"
    r"|\bwell[\s\-]regarded\b"                              # "well-regarded" / "well regarded"
    r"|\bhighly[\s\-]rated\b"                               # "highly rated" / "highly-rated"
    r"|\bgreat\s+option\b"                                  # "great option"
    r"|\btop\s+pick\b"                                      # "top pick"
    r"|\bstrong\s+local\s+following\b"                      # "strong local following"
    r"|\bconsistent\s+quality\b"                            # "consistent quality"
    r"|\bchicago\s+institution\b"                           # "Chicago institution"
    # Rating/review-count as primary differentiator — never concierge-grade on their own
    r"|\bhighest[\s\-]rated\b"                              # "highest-rated taproom in this set"
    r"|\bmost[\s\-]reviewed\b"                              # "most-reviewed brewery"
    r"|\breview\s+base\b"                                   # "second-largest review base"
    r"|\bsmallest\s+review\b"                               # "smallest review base"
    r"|\bsmaller\s+review\b"                                # "smaller review count (313)"
    r"|\bsolid\s+mid[\s\-]tier\b"                           # "solid mid-tier option"
    r"|\bstrong\s+on\s+volume\b"                            # "strong on volume of feedback"
    r"|\bconsistent\s+crowd\s+draw\b"                       # "consistent crowd draw"
    r"|\bstrong\s+flagship\s+choice\b"                      # "strong flagship choice"
    r"|\bestablished\s+reputation\b"                        # "established reputation"
    r"|\bvolume\s+of\s+feedback\b"                          # "volume of feedback"
    r"|\bordinal\s+rank\b"                                  # generic rank phrase
    # New v5 patterns — indirect rating/review phrasings that still lead with metrics
    r"|\bnotably\s+high\s+ratings?\b"                       # "notably high ratings (4.8★)"
    r"|\bhigh\s+engagement\b"                               # "draws consistently high engagement"
    r"|\breview\s+volume\b"                                  # "review volume" in any context
    r"|\breview\s+footprint\b"                              # "lightest/smaller review footprint"
    r"|\breview\s+count\b"                                  # "smaller review count"
    r"|\bfeedback\s+volume\b"                               # "feedback volume"
    r"|\bsteady\s+review\b"                                 # "steady review volume"
    r"|\blightest\s+review\b"                               # "lightest review footprint"
    r"|\bcarr(?:y|ies|ying|ied)\s+review\b"                # "carries/carrying review volume"
    r"|\bstrongest\s+review\b"                              # "strongest review volume"
    r"|\brating[\s\-]+lead\b"                               # explicit rating lead
    r")",
    re.IGNORECASE,
)

# Detects notes whose ENTIRE content is a view/setting denial with no positive differentiator.
# Anchored at start (^) and end ($) — only matches notes with NO useful positive content before the caveat.
# This prevents pure "X is not confirmed." notes from reaching the user while allowing
# notes that combine a positive differentiator (e.g. address, specialty) with an honest view caveat.
_PURE_CAVEAT_FULL_NOTE_RE = re.compile(
    r"^"
    # Subject: various forms of "view(s)" as the note's only subject
    r"(?:"
    r"(?:the\s+)?(?:requested\s+)?(?:outdoor\s+)?(?:scenic\s+)?views?"
    r"|(?:the\s+)?(?:requested\s+)?view(?:\s+setting)?"
    r"|(?:a\s+)?(?:scenic|waterfront|river|outdoor|panoramic)\s+views?"
    r")"
    r"\s+"
    # Predicate: denial of verification in any form
    r"(?:(?:are|is)\s+not\s+|cannot\s+be\s+|can(?:not|'t)\s+be\s+|isn'?t\s+)"
    r"(?:confirmed|verified)"
    # Optional trailing "from X" clause (e.g. "from the available address")
    r"(?:\s+from\s+.+?)?"
    r"[.,!?]?\s*$",
    re.IGNORECASE,
)

BATCHED_REASON_TIMEOUT_S = float(os.getenv("BATCHED_REASON_TIMEOUT_S", "3.0"))
MAX_CARDS_FOR_LLM_BATCH = int(os.getenv("BATCHED_REASON_MAX_CARDS", "8"))
# Default: sonnet for production validation quality. Downgrade to haiku only after
# production quality passes. Override via Railway env: CONCIERGE_BATCHED_REASONING_MODEL.
CONCIERGE_BATCHED_REASONING_MODEL = os.getenv(
    "CONCIERGE_BATCHED_REASONING_MODEL", "claude-sonnet-4-6"
)
_REASON_MIN_WORDS = 8
_REASON_MAX_CHARS = 220

# ── Reasoning Reliability v2 env-driven config ────────────────────────────────
# Haiku is fast (~1-2s) and reliable for concise card notes.
# Sonnet is the quality fallback for cards haiku couldn't reason about.
_PRIMARY_MODEL = os.getenv(
    "CONCIERGE_CARD_REASONING_PRIMARY_MODEL", "claude-haiku-4-5-20251001"
)
_FALLBACK_MODEL = os.getenv(
    "CONCIERGE_CARD_REASONING_FALLBACK_MODEL", "claude-sonnet-4-6"
)
# 8s timeout — ample for haiku, reasonable for sonnet on card-note sized outputs.
_TIMEOUT_MS = int(os.getenv("CONCIERGE_CARD_REASONING_TIMEOUT_MS", "8000"))
_MAX_RETRIES = int(os.getenv("CONCIERGE_CARD_REASONING_MAX_RETRIES", "1"))
_BATCH_SIZE = int(os.getenv("CONCIERGE_CARD_REASONING_BATCH_SIZE", "6"))

# Per-card note source identifiers for display_why_source.
SOURCE_PRIMARY = "llm_evidence_pack_v2_primary"
SOURCE_RETRY = "llm_evidence_pack_v2_retry"
SOURCE_FALLBACK = "llm_evidence_pack_v2_fallback"
SOURCE_OMITTED = "omitted"


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


@dataclass
class CardReason:
    """Per-card reasoning result with full provenance for Reasoning Reliability v2.

    validated=True ONLY when a validated LLM/evidence-grounded note was accepted.
    Callers must exclude cards with validated=False from the visible card set.
    Deterministic text must never populate a CardReason with validated=True.
    """
    note: str = ""                          # validated LLM note, or "" if absent
    source: str = SOURCE_OMITTED            # SOURCE_PRIMARY | SOURCE_RETRY | SOURCE_FALLBACK | SOURCE_OMITTED
    validated: bool = False                 # True only for validated LLM/evidence-grounded notes
    attempt_count: int = 0                  # total LLM call passes attempted for this card
    retry_used: bool = False                # True if the note came from a retry pass
    fallback_model_used: bool = False       # True if fallback model provided the note
    model_used: str = ""                    # which model produced the accepted note


@dataclass
class ReasoningResultV2:
    """Extended telemetry for Reasoning Reliability v2 orchestrator.

    success=True ONLY when accepted_count == final_card_count (all cards reasoned).
    deterministic_visible_count must always be 0 — no deterministic visible notes allowed.
    """
    attempted: bool = False
    success: bool = False                           # True when ALL cards have validated notes
    failure_reason: Optional[str] = None
    accepted_count: int = 0                         # cards with validated LLM notes
    final_card_count: int = 0                       # total cards the orchestrator considered
    retry_recovered_count: int = 0                  # cards rescued by retry pass
    fallback_model_used_count: int = 0              # cards rescued by fallback model
    deterministic_visible_count: int = 0            # MUST always be 0
    final_note_omitted_count: int = 0               # cards with no validated note
    prompt_error: bool = False
    diversity_flagged: bool = False
    model: str = ""                                 # primary model used
    fallback_model: str = ""                        # fallback model (if configured)
    visible_note_source_counts: Dict[str, int] = field(default_factory=dict)  # source → count


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

    # Enrichment facts from Place Details (editorial summary, amenity flags, review snippets)
    for fact in getattr(evidence, "enrichment_facts", []):
        lines.append(f"  - {fact}")

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

    # Evidence adequacy hint for the LLM
    adequacy = getattr(evidence, "evidence_adequacy", "THIN")
    if adequacy == "THIN":
        lines.append(
            "  - Evidence quality: THIN — use name/street/address/type as your only anchors; "
            "be specific about what the name/address tells you; do not use generic concept-fit phrasing"
        )
    elif adequacy == "OK":
        lines.append("  - Evidence quality: OK — concept match + location context available")
    elif adequacy == "STRONG":
        lines.append("  - Evidence quality: STRONG — specific differentiating details above")

    return "\n".join(lines)


def _build_batch_prompt(
    cards_data: List[Tuple[Any, Any, Any, Any]],
    frame: Any,
    per_card_hints: Optional[Dict[int, str]] = None,
) -> str:
    """Build the batched LLM prompt for all cards in one turn.

    Args:
        per_card_hints: Optional 1-based card index → quality rejection reason.
                        When provided (repair pass), adds targeted guidance per card.

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
        geo_h = geo_hints[0]
        modifier_lines.append(
            f"  - User mentioned a geographic/setting modifier: '{geo_h}'. "
            "THREE-WAY DISTINCTION required for each card:\n"
            f"    a) LISTING CONTEXT: if the venue's verified Google NAME or address "
            f"contains '{geo_h}' or a related term, you may say: "
            f"'The verified listing places this venue in {geo_h} context.' "
            "This is a listing-name fact, not a scenic or amenity claim.\n"
            "    b) VERIFIED FEATURE: only if evidence explicitly confirms the relevant "
            "amenity (outdoor seating, patio, garden, terrace, etc.) — you may mention it.\n"
            "    c) UNKNOWN: if neither (a) nor (b) applies, say the requested "
            f"'{geo_h}' attribute is not confirmed from available listing data.\n"
            "DO NOT claim unverified proximity or setting unless evidence confirms it. "
            "DO NOT claim scenic or physical attributes unless confirmed by amenity evidence."
        )
    if ambiguity_flags:
        unverifiable = [
            f for f in ambiguity_flags
            if "not_structurally_verifiable" in f or "not_verifiable" in f
        ]
        if unverifiable:
            modifier_lines.append(
                "  - UNVERIFIABLE ATTRIBUTE requested: the requested setting or ambiance "
                "cannot be structurally confirmed from Google listing data. Be honest — "
                "do not invent or imply the attribute. Provide a concrete venue-specific "
                "reason instead (name implication, specialty, neighborhood, concept format)."
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

    # Build per-card repair guidance when retrying quality-failed notes
    repair_section = ""
    if per_card_hints:
        hint_lines = []
        for card_1based, reason in sorted(per_card_hints.items()):
            base_hint = (
                f"  - Card {card_1based}: previous note rejected ({reason}). "
                "Write a more specific note using the place's street/address, "
                "what the name implies about its specialty, or an honest caveat — "
                "avoid generic concept-fit phrases and rating/review-count comparisons."
            )
            # Listing-context repair: if the rejection was for an unsupported attribute claim,
            # guide the LLM to use safe listing-name language rather than inventing amenities.
            # This is generic — applies to any geographic/setting term (Riverwalk, waterfront,
            # garden, rooftop, etc.) found in the verified Google listing name or address.
            if "unsupported_attribute_claim" in reason:
                claim_match = re.search(r"unsupported_attribute_claim:([^\s,]+)", reason)
                claimed_term = claim_match.group(1) if claim_match else "the requested term"
                base_hint += (
                    f" LISTING CONTEXT REPAIR: if the venue's verified Google NAME or address "
                    f"contains '{claimed_term}' or a related term, you may note that as a "
                    f"listing fact — e.g., 'The verified listing places this venue in "
                    f"{claimed_term} context.' Do NOT claim scenic views, seating, or physical "
                    "amenities unless amenity evidence explicitly confirms them."
                )
            hint_lines.append(base_hint)
        repair_section = "\nREPAIR GUIDANCE — previous notes for these cards were rejected:\n" + "\n".join(hint_lines) + "\n"

    # NOTE: All {example} placeholders below use {{double braces}} to prevent
    # Python f-string evaluation. These are literal text in the prompt.
    prompt = f"""You are a travel concierge writing one-sentence notes for {n} places. User asked: "{user_query}"

Your task: analyze each place's evidence and write a note that helps the traveler choose — or return null if the evidence is too thin to say anything useful.

User modifiers to respect:
{modifier_text}
{repair_section}
ANTI-PATTERNS — these will be automatically rejected, do not waste tokens on them:
- "{{Name}} — {{rating}}★ from {{N}} reviews."                    ← just repeats the visible card
- "{{Name}} on {{Street}} — {{rating}}★ from {{N}} reviews."     ← same, just repeats fields
- "Verified {{category}} with {{rating}}★ across {{N}} reviews." ← fill-in-the-blank, no value
- "Strong/Good/Great {{concept}} match in {{city}}."             ← zero information
- Any phrase like "matches the {{concept}} concept", "solid {{concept}} signals", or "established {{concept}} with solid..." ← all too generic
- Any note where the PRIMARY differentiator is rating or review count — even if phrased indirectly:
  "highest-rated", "most-reviewed", "review base", "review volume", "review footprint",
  "review count", "feedback volume", "notably high ratings", "high engagement",
  "steady review volume", "lightest review footprint", "strongest review volume",
  "smaller review count", "draws high engagement", "carries review volume",
  "solid mid-tier option", "strong on volume of feedback" — all rejected
- Any note that compares cards by rating rank or review count rank
- Any note where the FIRST clause (before any ; — , or .) is only about rating/reviews —
  ratings and review counts may only appear as SECONDARY context after a concrete differentiator
- Any note that claims waterfront/view/river scenic proximity without CONFIRMED in evidence
  (EXCEPTION: if the verified Google NAME contains 'Riverwalk'/'riverfront'/etc., you may
  say "The verified listing places this venue in Riverwalk context" — that is a listing fact)
- Any note that claims Michelin stars, awards, quiet/romantic atmosphere, price range, or hours
- Any note that repeats only name + rating + review count with no additional insight
- Any note so generic it could apply to any {concept_label} in this list

WHAT MAKES A USEFUL NOTE:
- It tells the traveler something specific they cannot already see from the card title and rating
- DO NOT lead with or center on rating (★) or review count — these are already visible on the card
- Rating/reviews may appear only as SECONDARY context after a concrete differentiator
- For THIN evidence: anchor on the place's name (what does the name itself imply?) and street/address
- For geographic/setting modifier queries: use the THREE-WAY DISTINCTION above (listing context / verified / unknown)
- For UNVERIFIABLE MODIFIER queries (scenic views, waterfront, garden, quiet, etc.): if the
  attribute is not confirmed by evidence, explicitly say it is not verified AND give a concrete
  venue-specific reason (name implication, concept/specialty, neighborhood). Do NOT substitute
  rating or review count as the differentiator.
- For CONCEPT/SPECIALTY queries: use name/menu/format/style clues from the evidence — the venue's
  concept-specific specialty, format (bar, tasting menu, casual, late-night), neighborhood fit,
  or category-specific detail. Do NOT use review volume as a differentiator.
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


def _assess_quality(note: str, evidence: Any) -> Tuple[bool, str]:
    """Quality gate: is this validated note concierge-grade (useful, not just valid)?

    Returns (passes_quality, rejection_reason).
    passes_quality=True means the note provides genuine differentiating value.
    Called after the safety validator passes — only catches thin-but-valid notes.
    """
    # Rating-lead: note begins with a rating number (e.g. "4.7★ from 1,344 reviews.")
    if re.match(r"^\s*\d[\d.]*\s*★", note):
        return False, "rating_residue_lead"
    # Pure-caveat: entire note is a view/setting denial with no positive differentiator
    if _PURE_CAVEAT_FULL_NOTE_RE.match(note):
        return False, "pure_caveat_no_differentiator"
    if _QUALITY_THIN_RE.search(note):
        return False, "thin_concept_fit_only"
    # Reject notes that are pure negation with no actionable content
    # ("not confirmed", "cannot be verified", etc. covering >60% of the note)
    words = note.lower().split()
    neg_count = sum(1 for w in words if w in {
        "not", "cannot", "no", "unavailable", "unconfirmed", "unverified",
        "isn't", "doesn't", "don't",
    })
    if len(words) >= 6 and neg_count / len(words) > 0.45:
        return False, "mostly_negation_no_positive_content"
    return True, ""


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


# ══════════════════════════════════════════════════════════════════════════════
# Reasoning Reliability v2 — three-pass orchestrator with retry + fallback model
# ══════════════════════════════════════════════════════════════════════════════


def _validate_and_trim(
    note: Optional[str],
    evidence: Any,
    frame: Any,
) -> Tuple[Optional[str], str]:
    """Validate a single LLM-produced note, trimming to max length if needed.

    Returns (trimmed_note, rejection_reason).
    trimmed_note is None when the note is invalid or thin.
    rejection_reason is empty string when valid.
    """
    if note is None:
        return None, "thin_evidence_null"
    words = note.split()
    if len(words) < _REASON_MIN_WORDS:
        return None, f"too_short:{len(words)}_words"
    trimmed = note[:_REASON_MAX_CHARS].rsplit(" ", 1)[0] + "…" if len(note) > _REASON_MAX_CHARS else note
    from app.concierge.reason_validator import validate_reason
    is_valid, rejection = validate_reason(trimmed, frame, evidence)
    if not is_valid:
        return None, rejection
    return trimmed, ""


def _run_llm_pass(
    subset_cards_data: List[Tuple[Any, Any, Any, Any]],
    original_indices: List[int],
    frame: Any,
    model: str,
    timeout_s: float,
    quality_hints: Optional[Dict[int, str]] = None,
) -> Tuple[Dict[int, str], Dict[int, str], bool]:
    """Run one LLM call for a subset of cards.

    Args:
        subset_cards_data: cards to reason about (may be a subset of the full list).
        original_indices: 0-based positions of each subset card in the original cards_data.
        frame: ExperienceFrame.
        model: model identifier to use.
        timeout_s: LLM call timeout in seconds.
        quality_hints: Optional 1-based card index → rejection reason from previous pass.
                       When provided, passed to the prompt builder as repair guidance.

    Returns:
        (accepted_map, quality_failed_map, call_succeeded):
            accepted_map maps original 0-based index → validated note string.
            quality_failed_map maps original 0-based index → quality rejection reason
              for notes that passed the safety validator but failed the quality gate.
            call_succeeded is True when the LLM returned a parseable response.
    """
    try:
        prompt = _build_batch_prompt(subset_cards_data, frame, per_card_hints=quality_hints)
    except Exception as exc:
        logger.error("_run_llm_pass: prompt_build_error model=%s error=%s", model, exc)
        return {}, {}, False

    raw = _call_llm(prompt, timeout=timeout_s, model=model)
    if raw is None:
        logger.info("_run_llm_pass: no_llm_response model=%s subset_size=%d", model, len(subset_cards_data))
        return {}, {}, False

    parsed = _parse_llm_response(raw, len(subset_cards_data))
    if not parsed:
        logger.warning("_run_llm_pass: parse_failed model=%s response=%r", model, raw[:120])
        return {}, {}, False

    evidence_by_subset = {
        str(i + 1): ev for i, (_e, ev, _rs, _det) in enumerate(subset_cards_data)
    }

    accepted: Dict[int, str] = {}
    quality_failed: Dict[int, str] = {}
    for subset_idx_str, llm_note in parsed.items():
        try:
            subset_1based = int(subset_idx_str)
            subset_0based = subset_1based - 1
            if subset_0based < 0 or subset_0based >= len(subset_cards_data):
                continue
        except ValueError:
            continue

        ev = evidence_by_subset.get(subset_idx_str)
        if ev is None:
            continue

        trimmed, rejection = _validate_and_trim(llm_note, ev, frame)
        if trimmed is not None:
            # Apply quality gate after safety validator
            quality_ok, quality_reason = _assess_quality(trimmed, ev)
            orig_0based = original_indices[subset_0based]
            if quality_ok:
                accepted[orig_0based] = trimmed
            else:
                quality_failed[orig_0based] = quality_reason
                logger.debug(
                    "_run_llm_pass: quality_rejected model=%s subset_idx=%s reason=%s note=%r",
                    model, subset_idx_str, quality_reason, trimmed[:80],
                )
        else:
            logger.debug(
                "_run_llm_pass: note_rejected model=%s subset_idx=%s rejection=%s",
                model, subset_idx_str, rejection,
            )

    return accepted, quality_failed, True


def build_reasons_with_retry(
    cards_data: List[Tuple[Any, Any, Any, Any]],
    frame: Any,
) -> Tuple[Dict[str, "CardReason"], "ReasoningResultV2"]:
    """Reasoning Reliability v2 orchestrator.

    Three-pass cascade:
      Pass 1: Primary model, all cards.
      Pass 2: Primary model retry for any cards missing after pass 1.
      Pass 3: Fallback model for any cards still missing after pass 2.

    Returns (card_reasons, ReasoningResultV2):
      card_reasons maps str(1-based index) → CardReason.
      Cards with validated=False had no accepted LLM note after all passes.

    IMPORTANT: Callers MUST exclude cards with validated=False from the returned
    card set. Deterministic text is NEVER used to populate a visible note.

    Never raises. Returns all-omitted result on any unhandled error.
    """
    n = len(cards_data)
    result: Dict[str, CardReason] = {str(i + 1): CardReason() for i in range(n)}
    r = ReasoningResultV2(final_card_count=n, model=_PRIMARY_MODEL, fallback_model=_FALLBACK_MODEL)

    if not _flag_enabled():
        r.failure_reason = "flag_disabled"
        r.final_note_omitted_count = n
        logger.debug("build_reasons_with_retry: flag_disabled, all cards omitted")
        return result, r

    if not cards_data:
        r.failure_reason = "no_cards"
        return result, r

    if len(cards_data) > _BATCH_SIZE:
        logger.info(
            "build_reasons_with_retry: card_count=%d exceeds batch_size=%d, reasoning all cards",
            len(cards_data), _BATCH_SIZE,
        )

    r.attempted = True
    timeout_s = _TIMEOUT_MS / 1000.0

    try:
        all_indices = list(range(n))

        # ── Pass 1: Primary model, all cards ─────────────────────────────────
        accepted_1, quality_failed_1, _ = _run_llm_pass(
            cards_data, all_indices, frame, _PRIMARY_MODEL, timeout_s
        )
        for orig_0idx, note in accepted_1.items():
            result[str(orig_0idx + 1)] = CardReason(
                note=note, source=SOURCE_PRIMARY, validated=True,
                attempt_count=1, model_used=_PRIMARY_MODEL,
            )

        # ── Pass 2: Retry primary model for missing cards ─────────────────────
        # missing_after_1 includes both validator-rejected and quality-failed cards.
        # Build repair hints for quality-failed cards so Pass 2 can write better notes.
        missing_after_1 = [i for i in all_indices if i not in accepted_1]
        if missing_after_1 and _MAX_RETRIES >= 1:
            subset_2 = [cards_data[i] for i in missing_after_1]
            repair_hints_2: Dict[int, str] = {
                subset_0idx + 1: quality_failed_1[orig_0idx]
                for subset_0idx, orig_0idx in enumerate(missing_after_1)
                if orig_0idx in quality_failed_1
            }
            accepted_2, quality_failed_2, _ = _run_llm_pass(
                subset_2, missing_after_1, frame, _PRIMARY_MODEL, timeout_s,
                quality_hints=repair_hints_2 or None,
            )
            for orig_0idx, note in accepted_2.items():
                result[str(orig_0idx + 1)] = CardReason(
                    note=note, source=SOURCE_RETRY, validated=True,
                    attempt_count=2, retry_used=True, model_used=_PRIMARY_MODEL,
                )
                r.retry_recovered_count += 1
        else:
            accepted_2 = {}
            quality_failed_2: Dict[int, str] = {}

        # ── Pass 3: Fallback model for cards still missing ────────────────────
        accepted_so_far = set(accepted_1) | set(accepted_2)
        missing_after_2 = [i for i in all_indices if i not in accepted_so_far]
        if missing_after_2 and _FALLBACK_MODEL and _FALLBACK_MODEL != _PRIMARY_MODEL:
            subset_3 = [cards_data[i] for i in missing_after_2]
            # Fallback model gets 2× timeout and repair hints from earlier quality failures.
            repair_hints_3: Dict[int, str] = {
                subset_0idx + 1: (quality_failed_2.get(orig_0idx) or quality_failed_1.get(orig_0idx, ""))
                for subset_0idx, orig_0idx in enumerate(missing_after_2)
                if orig_0idx in quality_failed_2 or orig_0idx in quality_failed_1
            }
            accepted_3, _, _ = _run_llm_pass(
                subset_3, missing_after_2, frame, _FALLBACK_MODEL, timeout_s * 2,
                quality_hints=repair_hints_3 or None,
            )
            for orig_0idx, note in accepted_3.items():
                result[str(orig_0idx + 1)] = CardReason(
                    note=note, source=SOURCE_FALLBACK, validated=True,
                    attempt_count=3, retry_used=True, fallback_model_used=True,
                    model_used=_FALLBACK_MODEL,
                )
                r.fallback_model_used_count += 1
        else:
            accepted_3 = {}

        # ── Final telemetry ───────────────────────────────────────────────────
        r.accepted_count = sum(1 for cr in result.values() if cr.validated)
        r.final_note_omitted_count = n - r.accepted_count
        r.deterministic_visible_count = 0  # invariant: always 0

        # success = True only when ALL cards have validated notes
        r.success = r.accepted_count == n
        if not r.success:
            r.failure_reason = (
                f"incomplete_reasoning:{r.final_note_omitted_count}_of_{n}_missing"
            )

        # Per-source counts for telemetry
        for cr in result.values():
            if cr.validated:
                r.visible_note_source_counts[cr.source] = (
                    r.visible_note_source_counts.get(cr.source, 0) + 1
                )

        # Diversity check on accepted notes
        accepted_notes = {k: cr.note for k, cr in result.items() if cr.validated}
        if len(accepted_notes) >= 2 and not _check_note_diversity(accepted_notes):
            r.diversity_flagged = True

        logger.info(
            "build_reasons_with_retry: "
            "primary_model=%s fallback_model=%s timeout_ms=%d "
            "accepted=%d/%d retry_recovered=%d fallback_used=%d "
            "success=%s failure_reason=%s source_counts=%s",
            _PRIMARY_MODEL, _FALLBACK_MODEL, _TIMEOUT_MS,
            r.accepted_count, n, r.retry_recovered_count, r.fallback_model_used_count,
            r.success, r.failure_reason, r.visible_note_source_counts,
        )
        return result, r

    except Exception as exc:
        logger.warning("build_reasons_with_retry: unhandled_error=%s", exc)
        r.failure_reason = f"unhandled_error:{exc}"
        r.final_note_omitted_count = n
        r.success = False
        return result, r
