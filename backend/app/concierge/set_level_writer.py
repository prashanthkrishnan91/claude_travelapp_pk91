"""Set-Level Writer v1 — evidence-grounded, set-aware note generation.

PR #261: Uses CuratedSetResult and PlaceEvidenceDossier to generate per-card
notes as a coordinated set, replacing isolated generic one-offs.

Architecture invariants:
- Evidence-grounded: notes use only dossier-supplied evidence; fabricated claims
  are blocked by the same reason_validator already used in batched_reason_builder.
- Set-aware: notes are generated together with cross-card distinctness enforced
  in both the prompt and a post-generation skeleton-diversity check.
- Role-aware: internal roles are converted to user-friendly LLM hints; raw
  role labels (best_overall, evidence_rich, etc.) are NEVER written to notes.
- Never surfaces: internal_evidence_gaps, role names, dossier internals.
- Never mints fallback visible prose: failed validation hides the note; no
  deterministic text is ever written with validated=True.
- fallback_note_visible_count is always 0 (structural invariant from PR #257).
- Failure cannot block card return: all exceptions are caught; caller receives
  timed_out=True / empty notes_by_place_id on any error.
- Preserves deadline: respects deadline.budget_for_note_generation_s().
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

# ── Quality thresholds (re-used from batched_reason_builder) ──────────────────
from app.concierge.batched_reason_builder import (
    _PURE_CAVEAT_FULL_NOTE_RE,
    _QUALITY_THIN_RE,
    _REASON_MAX_CHARS,
    _REASON_MIN_WORDS,
    _skeleton,
    SOURCE_OMITTED,
)

# Source identifier for notes produced by this module.
SOURCE_SET_WRITER = "set_level_writer_v1"

# ── Role → user-friendly LLM hint (NEVER exposes raw role label) ──────────────
_ROLE_PROMPT_HINTS: Dict[str, str] = {
    "best_overall": (
        "Strong overall fit: this place closely matches the concept and has "
        "strong supporting evidence — use specific differentiating details."
    ),
    "strongest_query_match": (
        "Closely matches what was asked for — use concept-specific details "
        "from the evidence."
    ),
    "modifier_confirmed": (
        "Evidence confirms the requested modifier/setting — you may state it "
        "as confirmed if evidence shows it explicitly."
    ),
    "evidence_rich": (
        "Specific Place Details available — use the enrichment themes and facts "
        "to write a differentiated note."
    ),
    "distinctive_theme": (
        "Multiple specific themes available — highlight the most distinctive "
        "detail; avoid generic phrases."
    ),
    "geographic_fit": (
        "Strong geographic proximity signal — mention location context if it "
        "adds useful information beyond the address."
    ),
    "safe_popular_fallback": (
        "Moderate evidence — use name/type/address anchors; keep the note "
        "specific and honest about what is known."
    ),
    "interesting_but_weaker": (
        "Weaker evidence — be conservative; anchor on the name, street, or "
        "category; do not claim unsupported attributes."
    ),
    "low_evidence_holdback": (
        "Minimal evidence — use only name/type/address; do not make specific "
        "claims; return null if nothing useful can be said."
    ),
}


# ── Typed contracts ────────────────────────────────────────────────────────────

@dataclass
class SetWriterCardInput:
    """Input for the set-level writer for one card."""

    entity: Any                          # PlaceEntity (identity, address, name)
    rank_score: Any                      # RankScore from semantic ranker
    dossier: Any                         # PlaceEvidenceDossier (may be None)
    role: str                            # internal role (never exposed in output)
    curation_signals: Any                # CardCurationSignals
    original_rank_index: int             # 0-based position in original ranked list


@dataclass
class SetWriterNote:
    """One validated note produced by the set-level writer for a single card."""

    place_id: str
    note: str                            # "" when hidden (failed validation)
    validated: bool                      # True only for validator-approved notes
    rejection_reason: str                # reason for rejection, or ""
    source: str                          # SOURCE_SET_WRITER or SOURCE_OMITTED
    role_used_internal: str              # internal role (never surfaced in note)
    evidence_terms_used: List[str]       # snippet terms from dossier used in note
    caveat_type: str                     # "" | "listing_context" | "unconfirmed_modifier" | "low_evidence"


@dataclass
class SetWriterResult:
    """Result of one set-level writing pass."""

    notes_by_place_id: Dict[str, SetWriterNote]
    visible_note_count: int
    hidden_note_count: int
    rejected_note_count: int
    timed_out: bool
    fallback_note_visible_count: int     # structural invariant: always 0
    role_note_counts: Dict[str, int]     # role → visible note count
    note_source_counts: Dict[str, int]   # source → count
    repeated_skeleton_count: int
    unsupported_claim_count: int
    # PR #267 reviewer telemetry (optional — None when reviewer was not run)
    reviewer_telemetry: Optional[Dict[str, Any]] = None

    def as_telemetry_dict(self, elapsed_ms: int = 0) -> Dict[str, Any]:
        """Telemetry dict for semantic_retrieval_v1.set_writer_telemetry log."""
        d: Dict[str, Any] = {
            "set_writer_input_count": len(self.notes_by_place_id),
            "set_writer_output_count": self.visible_note_count + self.hidden_note_count,
            "set_writer_visible_note_count": self.visible_note_count,
            "set_writer_hidden_note_count": self.hidden_note_count,
            "set_writer_rejected_note_count": self.rejected_note_count,
            "set_writer_timed_out": self.timed_out,
            "set_writer_fallback_to_existing_path": False,
            "set_writer_fallback_note_visible_count": 0,  # invariant
            "set_writer_role_note_counts": self.role_note_counts,
            "set_writer_note_source_counts": self.note_source_counts,
            "set_writer_repeated_skeleton_count": self.repeated_skeleton_count,
            "set_writer_unsupported_claim_count": self.unsupported_claim_count,
            "set_writer_ms": elapsed_ms,
        }
        if self.reviewer_telemetry:
            d["reviewer_telemetry"] = self.reviewer_telemetry
        return d


# ── Evidence stub for reason_validator ───────────────────────────────────────
# reason_validator.validate_reason() needs an evidence-like object with
# structured_facts, uncertainty_flags, and optionally an entity sub-object.

@dataclass
class _EvidenceStub:
    """Minimal evidence-like object built from dossier for use with validate_reason."""

    structured_facts: List[str] = field(default_factory=list)
    uncertainty_flags: List[str] = field(default_factory=list)
    geo_note: Optional[str] = None
    evidence_adequacy: str = "OK"
    entity: Optional[Any] = None        # used by validator for listing-context checks


def _make_evidence_stub(
    card_input: SetWriterCardInput,
    frame: Any,
) -> _EvidenceStub:
    """Build an evidence stub from dossier + frame for use with validate_reason."""
    dossier = card_input.dossier
    entity = card_input.entity

    structured_facts: List[str] = []
    uncertainty_flags: List[str] = []

    if dossier is not None:
        # Include provider evidence facts
        for pev in (dossier.provider_evidence or []):
            structured_facts.extend(getattr(pev, "facts", [])[:8])

        # Modifier not-confirmed → uncertainty flag
        mfit = getattr(getattr(dossier, "query_fit", None), "modifier_fit", None) or ""
        location_modifiers = getattr(frame, "location_modifiers", []) or []
        if mfit == "not_confirmed" and location_modifiers:
            uncertainty_flags.append(
                f"location_modifier_not_confirmed:{location_modifiers[0]}"
            )
        # Explicit modifier evidence in structured_facts
        if mfit == "confirmed" and location_modifiers:
            structured_facts.append(
                f"confirms {location_modifiers[0]} modifier"
            )

        # View/outdoor confirmed evidence → include in structured_facts so
        # validator allows the claim
        view_entries = getattr(
            getattr(dossier, "review_themes", None), "view_patio_waterfront", []
        ) or []
        for entry in view_entries:
            if not entry.startswith("listing_context:"):
                structured_facts.append(entry)

        adequacy = "THIN" if dossier.is_minimal else (
            "STRONG" if dossier.source_confidence == "strong" else "OK"
        )
        geo_note = dossier.neighborhood
    else:
        adequacy = "THIN"
        geo_note = getattr(entity, "formatted_address", None)

    return _EvidenceStub(
        structured_facts=structured_facts,
        uncertainty_flags=uncertainty_flags,
        geo_note=geo_note,
        evidence_adequacy=adequacy,
        entity=entity,
    )


# ── LLM call ──────────────────────────────────────────────────────────────────

_SET_WRITER_MODEL = os.getenv(
    "CONCIERGE_SET_WRITER_MODEL",
    os.getenv("CONCIERGE_CARD_REASONING_PRIMARY_MODEL", "claude-haiku-4-5-20251001"),
)


def _call_set_writer_llm(prompt: str, timeout_s: float) -> Optional[str]:
    """Call Claude API for set-level note generation. Returns raw text or None."""
    try:
        import anthropic  # type: ignore[import]
    except ImportError:
        logger.warning("set_level_writer: anthropic SDK not installed")
        return None

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("set_level_writer: ANTHROPIC_API_KEY not set")
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=_SET_WRITER_MODEL,
            max_tokens=1024,
            timeout=timeout_s,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text if message.content else None
    except Exception as exc:
        logger.warning("set_level_writer: llm_call_failed model=%s error=%s", _SET_WRITER_MODEL, exc)
        return None


def _parse_set_writer_response(
    response_text: str,
    expected_count: int,
) -> Dict[str, Optional[str]]:
    """Parse JSON from LLM response. Returns empty dict on any parse error."""
    if not response_text:
        return {}
    try:
        json_match = re.search(r"\{[^{}]+\}", response_text, re.DOTALL)
        if not json_match:
            return {}
        raw = json.loads(json_match.group(0))
        result: Dict[str, Optional[str]] = {}
        for k, v in raw.items():
            if v is None:
                result[str(k)] = None
            elif isinstance(v, str) and v.strip():
                result[str(k)] = v.strip()
        return result
    except (json.JSONDecodeError, ValueError):
        return {}


# ── Evidence block builder ─────────────────────────────────────────────────────

def _build_card_evidence_block(
    card_input: SetWriterCardInput,
    card_1based: int,
    total: int,
    frame: Any,
) -> str:
    """Render one card's dossier evidence as structured text for the LLM prompt."""
    dossier = card_input.dossier
    entity = card_input.entity

    name = (dossier.name if dossier else None) or getattr(entity, "name", "Unknown")
    lines: List[str] = [f"Place {card_1based}/{total}: {name}"]

    # Role hint — user-friendly language, never raw label
    hint = _ROLE_PROMPT_HINTS.get(card_input.role, "")
    if hint:
        lines.append(f"  [Context for writer: {hint}]")

    # Category and location
    if dossier:
        if dossier.category:
            lines.append(f"  - Category: {dossier.category}")
        elif dossier.primary_type:
            lines.append(f"  - Type: {dossier.primary_type.replace('_', ' ')}")

        if dossier.neighborhood:
            lines.append(f"  - Location: {dossier.neighborhood}")

        # Query fit / modifier
        qf = dossier.query_fit
        mfit = getattr(qf, "modifier_fit", None) or ""
        location_modifiers = getattr(frame, "location_modifiers", []) or []
        geo_hints = getattr(frame, "geography_hints", []) or []
        requested_mod = location_modifiers[0] if location_modifiers else (
            geo_hints[0] if geo_hints else ""
        )
        if requested_mod:
            if mfit == "confirmed":
                lines.append(f"  - Modifier '{requested_mod}': CONFIRMED in evidence")
            elif mfit == "not_confirmed":
                lines.append(
                    f"  - Modifier '{requested_mod}': NOT CONFIRMED from available data "
                    f"— do not claim confirmed; honest caveat required"
                )

        # Provider evidence facts (cap to prevent prompt bloat)
        for pev in (dossier.provider_evidence or []):
            source = getattr(pev, "source", "")
            facts = getattr(pev, "facts", []) or []
            # Skip pure rating/review_count facts — these are visible card fields
            allowed = [
                f for f in facts
                if not f.startswith("rating:") and not f.startswith("review_count:")
            ]
            for fact in allowed[:6]:
                lines.append(f"  - [{source}] {fact}")

        # Review theme evidence
        themes = dossier.review_themes
        if themes:
            if themes.food_drink:
                lines.append(f"  - Food/drink themes: {', '.join(themes.food_drink[:3])}")
            if themes.ambiance:
                lines.append(f"  - Ambiance: {', '.join(themes.ambiance[:3])}")
            if themes.service:
                lines.append(f"  - Service: {', '.join(themes.service[:2])}")
            if themes.occasion_fit:
                lines.append(f"  - Occasion: {', '.join(themes.occasion_fit[:2])}")

            # View/outdoor: explicit vs listing-context — different trust levels
            view_explicit = [
                e for e in (themes.view_patio_waterfront or [])
                if not e.startswith("listing_context:")
            ]
            view_listing = [
                e for e in (themes.view_patio_waterfront or [])
                if e.startswith("listing_context:")
            ]
            if view_explicit:
                lines.append(
                    f"  - Outdoor/view (confirmed by amenity or editorial evidence): "
                    f"{', '.join(view_explicit[:2])}"
                )
            elif view_listing:
                # Listing context only — lower trust
                tokens = [e.replace("listing_context:", "") for e in view_listing[:2]]
                lines.append(
                    f"  - Outdoor/view (listing name context ONLY — not amenity-confirmed): "
                    f"venue name/listing contains: {', '.join(tokens)}"
                )

            if themes.negative_caveats:
                lines.append(
                    f"  - Noted caveats: {', '.join(themes.negative_caveats[:2])}"
                )

        # Evidence quality signal
        if dossier.is_minimal:
            lines.append(
                "  - Evidence quality: THIN — use name/type/address only; "
                "avoid specific claims; consider returning null"
            )
        elif dossier.source_confidence == "strong":
            lines.append("  - Evidence quality: STRONG — specific details available above")
        else:
            lines.append("  - Evidence quality: OK — moderate evidence available")

    else:
        # No dossier — minimal fallback
        addr = getattr(entity, "formatted_address", "") or ""
        if addr:
            lines.append(f"  - Location: {addr}")
        lines.append(
            "  - Evidence quality: THIN — use name/address only; "
            "consider returning null"
        )

    return "\n".join(lines)


# ── Prompt builder ─────────────────────────────────────────────────────────────

def _build_set_level_prompt(
    card_inputs: List[SetWriterCardInput],
    frame: Any,
) -> str:
    """Build the set-level LLM prompt for all cards in one turn."""
    user_query = getattr(frame, "literal_ask", "") or ""
    venue_concept = ""
    if getattr(frame, "subtype_concepts", None):
        venue_concept = frame.subtype_concepts[0].label if frame.subtype_concepts else ""

    location_modifiers = getattr(frame, "location_modifiers", []) or []
    geo_hints = getattr(frame, "geography_hints", []) or []
    ambiguity_flags = getattr(frame, "ambiguity_flags", []) or []

    n = len(card_inputs)

    # Per-card evidence blocks
    evidence_text = "\n\n".join(
        _build_card_evidence_block(ci, i + 1, n, frame)
        for i, ci in enumerate(card_inputs)
    )

    # Modifier handling section
    modifier_lines: List[str] = []
    if location_modifiers:
        modifier_lines.append(
            f"  - User asked for places near/on: {location_modifiers[0]}. "
            "State as confirmed ONLY when evidence says CONFIRMED. "
            "Otherwise acknowledge it was requested but not confirmed."
        )
    if geo_hints:
        geo_h = geo_hints[0]
        modifier_lines.append(
            f"  - User requested a setting/geography modifier: '{geo_h}'. "
            "THREE-WAY DISTINCTION required per card:\n"
            f"    a) LISTING CONTEXT: venue's verified name/listing contains '{geo_h}' "
            "or a related term → say 'The verified listing places this venue in "
            f"{geo_h} context.' This is a listing fact, NOT a scenic claim.\n"
            "    b) VERIFIED FEATURE: amenity evidence (outdoor seating, patio, etc.) "
            "confirmed → you may mention it.\n"
            f"    c) UNKNOWN: neither applies → say the '{geo_h}' attribute is not "
            "confirmed from available listing data.\n"
            "DO NOT claim scenic views or physical settings unless explicitly confirmed."
        )
    if ambiguity_flags and any(
        "not_structurally_verifiable" in f for f in ambiguity_flags
    ):
        modifier_lines.append(
            "  - UNVERIFIABLE ATTRIBUTE: the requested setting cannot be confirmed "
            "from Google listing data — be honest, do not imply the attribute."
        )
    if not modifier_lines:
        modifier_lines.append("  - No location or setting modifiers requested.")

    modifier_text = "\n".join(modifier_lines)
    concept_label = venue_concept or "place"

    prompt = f"""You are a travel concierge writing one-sentence notes for {n} places.
User asked: "{user_query}"

Your task: write a note that helps the traveler choose between these specific places, \
or return null if the evidence is too thin to say anything useful.

User modifiers to respect:
{modifier_text}

CRITICAL RULES — notes violating these will be rejected:
- DO NOT lead with or center on rating (★) or review count — these are already \
visible on the card. Rating/reviews may appear ONLY as secondary context after a \
concrete differentiator.
- DO NOT use: "highest-rated", "most-reviewed", "review base", "review volume", \
"review footprint", "review count", "feedback volume", "notably high ratings", \
"high engagement", "steady review volume", "lightest review footprint", or any \
indirect rating/review-count framing as the primary differentiator.
- DO NOT use: "matches the {concept_label} concept", "solid {concept_label} signals", \
"strong {concept_label} match", "great option", "top pick", "well-regarded", \
"highly rated", "consistent quality" — these are too generic.
- DO NOT expose internal role labels, evidence gap descriptions, dossier fields, \
or anything framed as "missing", "internal gap", "not available in our data".
- DO NOT claim waterfront/view/river/lake scenic proximity without explicit \
amenity evidence confirming it.
- DO NOT claim Michelin stars, awards, quiet/romantic atmosphere, exact price, \
hours, or reservations.
- RETURN null (not "") when evidence is too thin for a genuinely useful note — \
null is better than a generic note.

SET-LEVEL DISTINCTNESS:
- Each note must be distinct from the others — do not reuse the same sentence \
structure across cards.
- Vary: the opening, the specific detail highlighted, the angle (specialty, \
location context, theme, format, or honest caveat).

WHAT MAKES A GOOD NOTE:
- Tells the traveler something specific they cannot already see from the card title/rating.
- Anchors on the evidence above: name implication, category, editorial summary, \
amenity flags, review themes, location context.
- For THIN evidence: anchor on the name (what does the name itself imply?) and \
address/street — do not fabricate.
- Concise: one sentence or two short clauses, under {_REASON_MAX_CHARS} characters.

EVIDENCE (use ONLY what is listed here — do not invent facts):
{evidence_text}

Return ONLY a JSON object mapping the place number (string key) to a note string or null:
{{"1": "...", "2": null, "3": "..."}}"""

    return prompt


# ── Per-note validation ────────────────────────────────────────────────────────

def _validate_set_writer_note(
    note: Optional[str],
    card_input: SetWriterCardInput,
    frame: Any,
) -> Tuple[bool, str]:
    """Validate one set-writer note through safety + quality gates.

    Returns (passes, rejection_reason).
    Uses the same validator chain as batched_reason_builder.
    """
    if note is None:
        return False, "thin_evidence_null"

    words = note.split()
    if len(words) < _REASON_MIN_WORDS:
        return False, f"too_short:{len(words)}_words"

    trimmed = (
        note[:_REASON_MAX_CHARS].rsplit(" ", 1)[0] + "…"
        if len(note) > _REASON_MAX_CHARS
        else note
    )

    # Safety gate via reason_validator
    evidence_stub = _make_evidence_stub(card_input, frame)
    from app.concierge.reason_validator import validate_reason
    is_valid, rejection = validate_reason(trimmed, frame, evidence_stub)
    if not is_valid:
        return False, rejection

    # Quality gate: same patterns as batched_reason_builder._assess_quality
    if re.match(r"^\s*\d[\d.]*\s*★", trimmed):
        return False, "rating_residue_lead"
    if _PURE_CAVEAT_FULL_NOTE_RE.match(trimmed):
        return False, "pure_caveat_no_differentiator"
    if _QUALITY_THIN_RE.search(trimmed):
        return False, "thin_concept_fit_only"

    neg_words = trimmed.lower().split()
    neg_count = sum(
        1 for w in neg_words
        if w in {"not", "cannot", "no", "unavailable", "unconfirmed",
                 "unverified", "isn't", "doesn't", "don't"}
    )
    if len(neg_words) >= 6 and neg_count / len(neg_words) > 0.45:
        return False, "mostly_negation_no_positive_content"

    return True, ""


def _trim_note(note: str) -> str:
    """Trim note to max char length."""
    if len(note) > _REASON_MAX_CHARS:
        return note[:_REASON_MAX_CHARS].rsplit(" ", 1)[0] + "…"
    return note


# ── Cross-card diversity check ─────────────────────────────────────────────────

def _count_repeated_skeletons(validated_notes: Dict[str, str]) -> int:
    """Count notes that share a skeleton prefix with another — structural repetition."""
    if len(validated_notes) < 2:
        return 0
    prefixes = [_skeleton(n)[:50] for n in validated_notes.values()]
    from collections import Counter
    counts = Counter(prefixes)
    repeated = 0
    for cnt in counts.values():
        if cnt > 1:
            repeated += cnt - 1
    return repeated


def _enforce_repeated_skeleton_diversity(
    notes_by_place_id: Dict[str, SetWriterNote],
    validated_notes_for_diversity: Dict[str, str],
) -> int:
    """Hide repeated-skeleton notes, preserving only first note per skeleton.

    Returns number of notes hidden due to repeated skeletons.
    """
    from collections import defaultdict

    groups: Dict[str, List[str]] = defaultdict(list)
    for place_id, note in validated_notes_for_diversity.items():
        groups[_skeleton(note)[:50]].append(place_id)

    hidden_due_to_repeated = 0
    for place_ids in groups.values():
        if len(place_ids) <= 1:
            continue
        # Keep first visible; hide the rest.
        for repeated_place_id in place_ids[1:]:
            note_obj = notes_by_place_id[repeated_place_id]
            note_obj.validated = False
            note_obj.note = ""
            note_obj.source = SOURCE_OMITTED
            note_obj.rejection_reason = "repeated_skeleton"
            hidden_due_to_repeated += 1

    return hidden_due_to_repeated


# ── Main entry point ──────────────────────────────────────────────────────────

def write_set_notes(
    curated_result: Any,   # CuratedSetResult
    frame: Any,            # ExperienceFrame
    deadline: Optional[Any] = None,
    first_card_limit: int = 6,
) -> "SetWriterResult":
    """Generate set-level notes from CuratedSetResult + PlaceEvidenceDossier.

    Args:
        curated_result:  CuratedSetResult from card_curator.curate_cards().
        frame:           ExperienceFrame for the current turn.
        deadline:        Optional RequestDeadline for budget-gating.
        first_card_limit: Cap on first-response cards (default 6).

    Returns:
        SetWriterResult with notes_by_place_id keyed by Google place_id.
        On timeout or LLM absence, timed_out=True and notes are empty.
        Never raises — all exceptions return timed_out=True result.

    Contracts:
        - fallback_note_visible_count is always 0.
        - Internal role labels never appear in note text.
        - internal_evidence_gaps never appear in note text.
        - Failed validation hides note (validated=False); card is not removed.
    """
    t_start = time.monotonic()

    def _empty(timed_out: bool = False, reason: str = "") -> SetWriterResult:
        logger.debug("set_level_writer: empty_result timed_out=%s reason=%s", timed_out, reason)
        return SetWriterResult(
            notes_by_place_id={},
            visible_note_count=0,
            hidden_note_count=0,
            rejected_note_count=0,
            timed_out=timed_out,
            fallback_note_visible_count=0,
            role_note_counts={},
            note_source_counts={},
            repeated_skeleton_count=0,
            unsupported_claim_count=0,
            reviewer_telemetry=None,
        )

    try:
        # ── Budget gate ───────────────────────────────────────────────────────
        if deadline is not None:
            budget_s = deadline.budget_for_note_generation_s()
            if budget_s <= 0.0:
                logger.info(
                    "set_level_writer: skipped_no_budget remaining_ms=%d",
                    deadline.remaining_ms(),
                )
                return _empty(timed_out=True, reason="no_budget")
        else:
            budget_s = float(os.getenv("CONCIERGE_CARD_REASONING_TIMEOUT_MS", "8000")) / 1000.0

        # ── Build card inputs from curated result ─────────────────────────────
        curated_cards = getattr(curated_result, "curated_cards", []) or []
        target_cards = curated_cards[:first_card_limit]

        if not target_cards:
            return _empty(reason="no_curated_cards")

        card_inputs: List[SetWriterCardInput] = []
        for cc in target_cards:
            card_inputs.append(SetWriterCardInput(
                entity=cc.entity,
                rank_score=cc.rank_score,
                dossier=cc.dossier,
                role=cc.role,
                curation_signals=cc.curation_signals,
                original_rank_index=cc.original_rank_index,
            ))

        # ── Check LLM availability ────────────────────────────────────────────
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            logger.info("set_level_writer: no_api_key — writer unavailable")
            return _empty(timed_out=False, reason="no_api_key")

        # ── Build prompt ──────────────────────────────────────────────────────
        try:
            prompt = _build_set_level_prompt(card_inputs, frame)
        except Exception as prompt_exc:
            logger.error("set_level_writer: prompt_build_error error=%s", prompt_exc)
            return _empty(reason=f"prompt_build_error:{prompt_exc}")

        # ── LLM call ──────────────────────────────────────────────────────────
        raw = _call_set_writer_llm(prompt, timeout_s=budget_s)
        elapsed_ms = int((time.monotonic() - t_start) * 1000)

        if raw is None:
            logger.info("set_level_writer: no_llm_response elapsed_ms=%d", elapsed_ms)
            return _empty(reason="llm_no_response")

        # ── Parse response ────────────────────────────────────────────────────
        parsed = _parse_set_writer_response(raw, len(card_inputs))
        if not parsed:
            logger.warning(
                "set_level_writer: parse_failed elapsed_ms=%d response=%r",
                elapsed_ms, raw[:200],
            )
            return _empty(reason="parse_failed")

        # ── Validate notes ────────────────────────────────────────────────────
        notes_by_place_id: Dict[str, SetWriterNote] = {}
        validated_notes_for_diversity: Dict[str, str] = {}
        rejected_count = 0
        hidden_count = 0
        unsupported_claim_count = 0
        role_note_counts: Dict[str, int] = {}

        for i, ci in enumerate(card_inputs):
            idx_str = str(i + 1)
            place_id = getattr(ci.entity, "place_id", None) or f"unknown_{i}"
            raw_note = parsed.get(idx_str)

            passes, rejection = _validate_set_writer_note(raw_note, ci, frame)

            if "unsupported_attribute_claim" in rejection:
                unsupported_claim_count += 1

            if passes and raw_note is not None:
                trimmed = _trim_note(raw_note)
                # Determine caveat type for telemetry
                caveat_type = ""
                signals = ci.curation_signals
                if getattr(signals, "has_listing_context_only", False):
                    caveat_type = "listing_context"
                elif getattr(signals, "modifier_fit", "") == "not_confirmed":
                    caveat_type = "unconfirmed_modifier"
                elif getattr(ci, "dossier", None) and getattr(ci.dossier, "is_minimal", False):
                    caveat_type = "low_evidence"

                note_obj = SetWriterNote(
                    place_id=place_id,
                    note=trimmed,
                    validated=True,
                    rejection_reason="",
                    source=SOURCE_SET_WRITER,
                    role_used_internal=ci.role,
                    evidence_terms_used=[],  # telemetry detail; not exposed
                    caveat_type=caveat_type,
                )
                notes_by_place_id[place_id] = note_obj
                validated_notes_for_diversity[place_id] = trimmed
                role_note_counts[ci.role] = role_note_counts.get(ci.role, 0) + 1
            else:
                rejection_to_use = rejection if rejection else "thin_evidence_null"
                hidden_count += 1
                if raw_note is not None:
                    rejected_count += 1

                note_obj = SetWriterNote(
                    place_id=place_id,
                    note="",
                    validated=False,
                    rejection_reason=rejection_to_use,
                    source=SOURCE_OMITTED,
                    role_used_internal=ci.role,
                    evidence_terms_used=[],
                    caveat_type="",
                )
                notes_by_place_id[place_id] = note_obj

        # ── Cross-card diversity check ─────────────────────────────────────────
        repeated_skeleton_count = _enforce_repeated_skeleton_diversity(
            notes_by_place_id,
            validated_notes_for_diversity,
        )
        if repeated_skeleton_count > 0:
            logger.warning(
                "set_level_writer: repeated_skeletons_hidden count=%d pre_enforcement_visible=%d",
                repeated_skeleton_count, len(validated_notes_for_diversity),
            )

        visible_count = sum(1 for note in notes_by_place_id.values() if note.validated)
        hidden_count = sum(1 for note in notes_by_place_id.values() if not note.validated)
        rejected_count += repeated_skeleton_count

        role_note_counts = {}
        note_source_counts: Dict[str, int] = {}
        for note in notes_by_place_id.values():
            if note.validated:
                role_note_counts[note.role_used_internal] = (
                    role_note_counts.get(note.role_used_internal, 0) + 1
                )
            note_source_counts[note.source] = note_source_counts.get(note.source, 0) + 1

        # ── Claim-safety reviewer gate (PR #267) ──────────────────────────────
        # Additional deterministic review pass on all validated notes. Reviewer
        # fails closed: rejected notes are hidden but cards are NOT dropped.
        # Budget: up to remaining time budget minus a small reserve, capped at 2s.
        reviewer_telemetry_dict: Optional[Dict[str, Any]] = None
        try:
            from app.concierge.claim_safety_reviewer import review_notes_set
            reviewer_budget_s = min(
                2.0,
                (budget_s - (time.monotonic() - t_start)),
            )
            if reviewer_budget_s > 0.05:
                _validated_for_review: Dict[str, str] = {
                    note.place_id: note.note
                    for note in notes_by_place_id.values()
                    if note.validated and note.note
                }
                _entity_names: Dict[str, str] = {
                    ci.entity.place_id: getattr(ci.entity, "name", "")
                    for ci in card_inputs
                    if getattr(ci.entity, "place_id", None)
                }
                reviewer_results, reviewer_tel = review_notes_set(
                    notes=_validated_for_review,
                    entity_name_by_place_id=_entity_names,
                    frame=frame,
                    timeout_s=reviewer_budget_s,
                )
                # Apply reviewer decisions: hide rejected notes; cards remain.
                for place_id, r_result in reviewer_results.items():
                    if not r_result.passed and place_id in notes_by_place_id:
                        note_obj = notes_by_place_id[place_id]
                        note_obj.validated = False
                        note_obj.note = ""
                        note_obj.source = SOURCE_OMITTED
                        note_obj.rejection_reason = (
                            f"reviewer:{r_result.rejection_reason}"
                        )
                        unsupported_claim_count += 1

                # Recount after reviewer gate
                visible_count = sum(
                    1 for note in notes_by_place_id.values() if note.validated
                )
                hidden_count = sum(
                    1 for note in notes_by_place_id.values() if not note.validated
                )
                rejected_count += reviewer_tel.reviewer_rejected_note_count
                reviewer_tel.final_note_visible_count = visible_count
                reviewer_tel.fallback_note_visible_count = 0   # invariant
                reviewer_tel.deterministic_visible_count = 0   # invariant
                reviewer_telemetry_dict = reviewer_tel.as_dict()

                if reviewer_tel.reviewer_rejected_note_count > 0:
                    logger.info(
                        "set_level_writer: reviewer_gate_applied "
                        "reviewer_rejected=%d reviewer_ms=%d",
                        reviewer_tel.reviewer_rejected_note_count,
                        reviewer_tel.reviewer_ms,
                    )
            else:
                logger.info(
                    "set_level_writer: reviewer_gate_skipped_no_budget "
                    "remaining_s=%.3f", reviewer_budget_s
                )
        except Exception as rev_exc:
            logger.warning(
                "set_level_writer: reviewer_gate_error error=%s — "
                "notes visible as-is (fail open for already-validated notes)",
                rev_exc,
            )

        elapsed_ms = int((time.monotonic() - t_start) * 1000)
        logger.info(
            "set_level_writer: complete input=%d visible=%d hidden=%d "
            "rejected=%d repeated_skeleton=%d unsupported_claim=%d elapsed_ms=%d",
            len(card_inputs), visible_count, hidden_count,
            rejected_count, repeated_skeleton_count, unsupported_claim_count, elapsed_ms,
        )

        return SetWriterResult(
            notes_by_place_id=notes_by_place_id,
            visible_note_count=visible_count,
            hidden_note_count=hidden_count,
            rejected_note_count=rejected_count,
            timed_out=False,
            fallback_note_visible_count=0,  # structural invariant
            role_note_counts=role_note_counts,
            note_source_counts=note_source_counts,
            repeated_skeleton_count=repeated_skeleton_count,
            unsupported_claim_count=unsupported_claim_count,
            reviewer_telemetry=reviewer_telemetry_dict,
        )

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - t_start) * 1000)
        logger.warning(
            "set_level_writer: unhandled_exception elapsed_ms=%d error=%s",
            elapsed_ms, exc,
        )
        return _empty(timed_out=True, reason=f"unhandled_exception:{exc}")
