"""Set-Level Writer v2 — fast evidence-compressed, set-aware note generation.

PR #273 (Fast LLM Set Writer Core): Replaces verbose per-card evidence blocks
with compact AllowedClaimsPackets and a Micro Set Writer prompt. One LLM call,
materially smaller dynamic payload, max_tokens reduced from 1024 → 384.

Architecture invariants (unchanged from PR #261):
- Evidence-grounded: notes use only dossier-supplied evidence; fabricated claims
  are blocked by the same reason_validator already used in batched_reason_builder.
- Set-aware: notes generated together with cross-card distinctness enforced.
- Role-aware: internal roles NEVER written to notes.
- Never surfaces: internal_evidence_gaps, role names, dossier internals.
- Never mints fallback visible prose: failed validation hides the note.
- fallback_note_visible_count is always 0 (structural invariant from PR #257).
- Failure cannot block card return: all exceptions caught; caller receives
  timed_out=True / empty notes_by_place_id on any error.
- Preserves deadline: respects deadline.budget_for_note_generation_s().

Performance changes (PR #273):
- AllowedClaimsPacket: compact typed distillation replaces verbose evidence blocks.
- Micro Set Writer prompt: stable static policy + small dynamic packet payload.
- max_tokens: 384 (was 1024) — sufficient for 6 × 180-char notes + JSON overhead.
- Improved parse: tries full json.loads() before regex fallback.
- Structured telemetry: evidence_distill_ms, prompt_build_ms, llm_call_ms,
  parse_ms, validation_ms, dynamic_packet_count/char_count, dynamic_prompt_char_count.

TODO (PR #274): Validated-note cache — exact-fingerprint, in-memory only,
validated notes only, revalidated on cache hit, cross-card diversity still
enforced. Gate on PR #273 telemetry to confirm packet size reduction and latency.
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

# ── Token budget ───────────────────────────────────────────────────────────────
# 384 covers 6 × ~45-token notes + JSON wrapper + stop margin.
# Increase to 512 only if empirical telemetry shows output truncation at 384.
_MAX_TOKENS_DEFAULT = int(os.getenv("CONCIERGE_SET_WRITER_MAX_TOKENS", "384"))

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
    # PR #273 writer telemetry (timing, token, packet size data)
    writer_telemetry: Optional[Dict[str, Any]] = None

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
        if self.writer_telemetry:
            d.update(self.writer_telemetry)
        return d


# ── Evidence stub for reason_validator ───────────────────────────────────────

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


# ── AllowedClaimsPacket — compact evidence distillation (PR #273) ─────────────

@dataclass
class AllowedClaimsPacket:
    """Compact typed distillation of evidence for one card.

    This is NOT prose generation and NOT templating.
    It is evidence compression + safety boundary construction.
    Thin evidence produces sparse packets that make null output likely.
    Rating/review counts are never claim atoms.
    Place name is identity, not evidence — never used to infer vibe/temporal claims.
    Internal role labels are never included in packet text sent to the LLM.
    """
    place_id: str
    display_name: str
    category: str                     # e.g. "Brewery / Taproom" or "bar"
    neighborhood: str                 # address/location hint, may be ""
    allowed_claim_atoms: List[str]    # 2–4 concrete allowed claim atoms from evidence
    safe_caveats: List[str]           # 0–2 honest caveats (modifier unconfirmed, etc.)
    disallowed_boundaries: List[str]  # claim types blocked for this card
    evidence_strength: str            # "strong" | "ok" | "thin"
    modifier_support: str             # "confirmed" | "listing_context_only" | "not_confirmed" | "not_applicable"


# Claim boundaries that always apply regardless of evidence.
_DISALLOWED_ALWAYS = [
    "rating/review-count prose",
    "hidden-gem/local-favorite/underrated",
    "hours/open-late/late-night (name alone is not evidence)",
    "waterfront/scenic-view/river-lake (unless amenity-confirmed)",
    "romantic/date-night",
    "Michelin/awards",
    "price/reservations",
]


def _distill_allowed_claims_packet(
    card_input: SetWriterCardInput,
    frame: Any,
) -> AllowedClaimsPacket:
    """Convert one card's dossier into a compact AllowedClaimsPacket.

    Rating and review counts are excluded as note-writing angles.
    Place name is treated as identity only — never inferred as evidence
    for hidden-gem, late-night, waterfront, romantic, cheaper, speakeasy,
    cocktail-forward, local-favorite, scenic, or patio claims.
    """
    dossier = card_input.dossier
    entity = card_input.entity

    place_id = getattr(entity, "place_id", "") or ""
    display_name = (
        (dossier.name if dossier else None)
        or getattr(entity, "name", "Unknown")
    )

    # Category
    if dossier:
        category = dossier.category or (
            (dossier.primary_type or "").replace("_", " ")
        ) or ""
    else:
        category = (getattr(entity, "primary_type", "") or "").replace("_", " ")

    # Neighborhood / location hint
    if dossier:
        neighborhood = dossier.neighborhood or getattr(entity, "formatted_address", "") or ""
    else:
        neighborhood = getattr(entity, "formatted_address", "") or ""

    # Evidence strength
    if dossier is None:
        evidence_strength = "thin"
    elif dossier.is_minimal:
        evidence_strength = "thin"
    elif dossier.source_confidence == "strong":
        evidence_strength = "strong"
    else:
        evidence_strength = "ok"

    # Modifier support
    mfit = ""
    location_modifiers = getattr(frame, "location_modifiers", []) or []
    geo_hints = getattr(frame, "geography_hints", []) or []
    requested_mod = location_modifiers[0] if location_modifiers else (
        geo_hints[0] if geo_hints else ""
    )

    if dossier and requested_mod:
        mfit = getattr(getattr(dossier, "query_fit", None), "modifier_fit", "") or ""
        if mfit == "confirmed":
            modifier_support = "confirmed"
        elif mfit == "not_confirmed":
            modifier_support = "not_confirmed"
        else:
            # Check for listing context on view entries
            view_entries = getattr(
                getattr(dossier, "review_themes", None), "view_patio_waterfront", []
            ) or []
            if any(e.startswith("listing_context:") for e in view_entries):
                modifier_support = "listing_context_only"
            else:
                modifier_support = "not_applicable"
    elif requested_mod:
        modifier_support = "not_confirmed"
    else:
        modifier_support = "not_applicable"

    # Allowed claim atoms — from evidence only, not from name
    allowed_claim_atoms: List[str] = []
    if dossier and not dossier.is_minimal:
        # Provider evidence facts (non-rating/review)
        for pev in (dossier.provider_evidence or []):
            facts = getattr(pev, "facts", []) or []
            for f in facts[:6]:
                if (
                    not f.startswith("rating:")
                    and not f.startswith("review_count:")
                    and not f.startswith("status:")
                    and len(allowed_claim_atoms) < 4
                ):
                    allowed_claim_atoms.append(f)

        # Review themes (concrete evidence)
        themes = dossier.review_themes
        if themes:
            for item in (themes.food_drink or [])[:2]:
                if len(allowed_claim_atoms) < 4:
                    allowed_claim_atoms.append(f"food/drink: {item}")
            for item in (themes.ambiance or [])[:1]:
                if len(allowed_claim_atoms) < 4:
                    allowed_claim_atoms.append(f"ambiance: {item}")
            for item in (themes.service or [])[:1]:
                if len(allowed_claim_atoms) < 4:
                    allowed_claim_atoms.append(f"service: {item}")

            # View/outdoor: explicit amenity evidence only (not listing context)
            view_explicit = [
                e for e in (themes.view_patio_waterfront or [])
                if not e.startswith("listing_context:")
            ]
            for item in view_explicit[:1]:
                if len(allowed_claim_atoms) < 4:
                    allowed_claim_atoms.append(f"outdoor/amenity (confirmed): {item}")

        # Modifier confirmed
        if modifier_support == "confirmed" and requested_mod:
            if len(allowed_claim_atoms) < 4:
                allowed_claim_atoms.append(f"modifier '{requested_mod}': confirmed in evidence")

    # Safe caveats
    safe_caveats: List[str] = []
    if evidence_strength == "thin":
        safe_caveats.append(
            "thin evidence — no supported differentiator; return null unless a claim atom is present"
        )
    if modifier_support == "not_confirmed" and requested_mod:
        safe_caveats.append(
            f"modifier '{requested_mod}' requested but NOT confirmed — "
            "do not claim it; honest caveat required"
        )
    elif modifier_support == "listing_context_only" and requested_mod:
        safe_caveats.append(
            f"modifier '{requested_mod}': listing context only — "
            "may reference listing context; do not claim scenic feature"
        )
    if dossier:
        themes = getattr(dossier, "review_themes", None)
        if themes:
            for nc in (getattr(themes, "negative_caveats", None) or [])[:1]:
                safe_caveats.append(f"caveat: {nc}")
    safe_caveats = safe_caveats[:2]

    # Disallowed boundaries: always-on + card-specific
    disallowed_boundaries = list(_DISALLOWED_ALWAYS)
    if modifier_support in ("not_confirmed", "listing_context_only", "not_applicable"):
        if requested_mod:
            disallowed_boundaries.append(
                f"claiming '{requested_mod}' as confirmed physical attribute"
            )

    # View/waterfront blocked unless explicitly confirmed
    if modifier_support != "confirmed":
        view_entries = []
        if dossier:
            themes = getattr(dossier, "review_themes", None)
            if themes:
                view_entries = getattr(themes, "view_patio_waterfront", []) or []
        explicit_view = [e for e in view_entries if not e.startswith("listing_context:")]
        if not explicit_view:
            disallowed_boundaries.append("outdoor-seating/patio/view (no amenity evidence)")

    return AllowedClaimsPacket(
        place_id=place_id,
        display_name=display_name,
        category=category,
        neighborhood=neighborhood,
        allowed_claim_atoms=allowed_claim_atoms,
        safe_caveats=safe_caveats,
        disallowed_boundaries=disallowed_boundaries,
        evidence_strength=evidence_strength,
        modifier_support=modifier_support,
    )


# ── Micro Set Prompt builder (PR #273) ────────────────────────────────────────

# Static policy block — never changes; only dynamic packet section varies.
_MICRO_POLICY = """\
RULES (violations → note hidden):
- DO NOT use: rating/review count, "highly rated", "most-reviewed", "review base", \
"review volume", "review footprint", "notable review", "high engagement", \
"steady review volume", "consistent quality", "established reputation".
- DO NOT use: "hidden gem", "local favorite", "locals love", "under-the-radar", \
"underrated", "best-kept secret", "off-the-beaten-path".
- DO NOT use: "great option", "top pick", "well-regarded", "strong match", \
"matches the concept", "solid signals", "worth a visit", "perfect for", \
"a must-try", "great choice".
- DO NOT claim: waterfront, scenic view, river/lake view, patio/outdoor seating \
unless the packet lists it as allowed_claim_atom with "(confirmed)".
- DO NOT claim: Michelin, awards, hours, "open late", romantic, price/reservations.
- DO NOT infer late-night, hidden-gem, waterfront, romantic, cheaper, local-favorite, \
scenic, patio, or speakeasy from a business name alone — name is identity, not evidence.
- If allowed_claims is none, return null — name/category/location are identity, not copy.
- RETURN null (not "") when evidence is thin or no concrete differentiator exists.
- One sentence or two short clauses. Under 220 characters.

DISTINCTNESS: Each note must differ in opening, angle, and specific detail. Do not reuse sentence structure across cards.\
"""


def _render_packet(packet: AllowedClaimsPacket, idx_1based: int, total: int) -> str:
    """Render one AllowedClaimsPacket as a compact string for the prompt."""
    lines = [f"[{idx_1based}/{total}] id={packet.place_id!r}"]
    lines.append(f"  name: {packet.display_name}")
    if packet.category:
        lines.append(f"  type: {packet.category}")
    if packet.neighborhood:
        lines.append(f"  location: {packet.neighborhood}")
    lines.append(f"  evidence_strength: {packet.evidence_strength}")
    if packet.modifier_support != "not_applicable":
        lines.append(f"  modifier_support: {packet.modifier_support}")
    if packet.allowed_claim_atoms:
        lines.append(f"  allowed_claims: {'; '.join(packet.allowed_claim_atoms)}")
    else:
        lines.append(
            "  allowed_claims: none — return null; "
            "name/category/location identify the place but do not support a note"
        )
    if packet.safe_caveats:
        lines.append(f"  caveats: {'; '.join(packet.safe_caveats)}")
    # Render card-specific blocked claims (cap to 5 to avoid prompt bloat)
    if packet.disallowed_boundaries:
        lines.append(f"  blocked_claims: {'; '.join(packet.disallowed_boundaries[:5])}")
    return "\n".join(lines)


def _build_micro_set_prompt(
    packets: List[AllowedClaimsPacket],
    frame: Any,
) -> str:
    """Build compact micro set writer prompt from AllowedClaimsPackets.

    Static policy text is a module-level constant.
    Only the dynamic packet payload varies per request.
    """
    user_query = getattr(frame, "literal_ask", "") or ""
    n = len(packets)

    packet_text = "\n\n".join(
        _render_packet(p, i + 1, n)
        for i, p in enumerate(packets)
    )

    # Build index → place_id map for the output instruction
    id_map = ", ".join(f'"{i + 1}": note_or_null' for i in range(n))

    return (
        f'Write one concise note per place (or null) for a traveler choosing.\n'
        f'Query: "{user_query}"\n\n'
        f"{_MICRO_POLICY}\n\n"
        f"EVIDENCE PACKETS (use ONLY what is listed — do not invent facts):\n\n"
        f"{packet_text}\n\n"
        f'Return ONLY strict JSON: {{{id_map}}}'
    )


# ── Legacy evidence block builder (kept for backward compat / existing tests) ──

def _build_card_evidence_block(
    card_input: SetWriterCardInput,
    card_1based: int,
    total: int,
    frame: Any,
) -> str:
    """Render one card's dossier evidence as structured text for the LLM prompt.

    Kept for backward compatibility with existing tests. The primary writer
    path now uses _distill_allowed_claims_packet + _build_micro_set_prompt.
    """
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
        addr = getattr(entity, "formatted_address", "") or ""
        if addr:
            lines.append(f"  - Location: {addr}")
        lines.append(
            "  - Evidence quality: THIN — use name/address only; "
            "consider returning null"
        )

    return "\n".join(lines)


# ── Legacy prompt builder (kept for backward compat / existing tests) ──────────

def _build_set_level_prompt(
    card_inputs: List[SetWriterCardInput],
    frame: Any,
) -> str:
    """Build the set-level LLM prompt for all cards in one turn.

    Kept for backward compatibility with existing tests. The primary writer
    path now uses _build_micro_set_prompt with AllowedClaimsPackets.
    """
    user_query = getattr(frame, "literal_ask", "") or ""
    venue_concept = ""
    if getattr(frame, "subtype_concepts", None):
        venue_concept = frame.subtype_concepts[0].label if frame.subtype_concepts else ""

    location_modifiers = getattr(frame, "location_modifiers", []) or []
    geo_hints = getattr(frame, "geography_hints", []) or []
    ambiguity_flags = getattr(frame, "ambiguity_flags", []) or []

    n = len(card_inputs)

    evidence_text = "\n\n".join(
        _build_card_evidence_block(ci, i + 1, n, frame)
        for i, ci in enumerate(card_inputs)
    )

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


# ── LLM call ──────────────────────────────────────────────────────────────────

_SET_WRITER_MODEL = os.getenv(
    "CONCIERGE_SET_WRITER_MODEL",
    os.getenv("CONCIERGE_CARD_REASONING_PRIMARY_MODEL", "claude-haiku-4-5-20251001"),
)


def _call_set_writer_llm(
    prompt: str,
    timeout_s: float,
    max_tokens: int = _MAX_TOKENS_DEFAULT,
) -> Tuple[Optional[str], Dict[str, Any]]:
    """Call Claude API for set-level note generation.

    Returns (raw_text_or_None, llm_telemetry_dict).
    llm_telemetry_dict always present; contains model, max_tokens, and optionally
    output_stop_reason, input_tokens, output_tokens.
    """
    tel: Dict[str, Any] = {
        "model": _SET_WRITER_MODEL,
        "max_tokens": max_tokens,
    }
    try:
        import anthropic  # type: ignore[import]
    except ImportError:
        logger.warning("set_level_writer: anthropic SDK not installed")
        return None, tel

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("set_level_writer: ANTHROPIC_API_KEY not set")
        return None, tel

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=_SET_WRITER_MODEL,
            max_tokens=max_tokens,
            timeout=timeout_s,
            messages=[{"role": "user", "content": prompt}],
        )
        # Capture available SDK telemetry fields
        tel["output_stop_reason"] = getattr(message, "stop_reason", None)
        usage = getattr(message, "usage", None)
        if usage is not None:
            tel["input_tokens"] = getattr(usage, "input_tokens", None)
            tel["output_tokens"] = getattr(usage, "output_tokens", None)
            # Cache tokens — only include if present (requires prompt caching, deferred PR #274)
            crit = getattr(usage, "cache_read_input_tokens", None)
            ccrt = getattr(usage, "cache_creation_input_tokens", None)
            if crit is not None:
                tel["cache_read_input_tokens"] = crit
            if ccrt is not None:
                tel["cache_creation_input_tokens"] = ccrt
        raw_text = message.content[0].text if message.content else None
        return raw_text, tel
    except Exception as exc:
        logger.warning(
            "set_level_writer: llm_call_failed model=%s error=%s",
            _SET_WRITER_MODEL, exc,
        )
        tel["llm_error"] = str(exc)[:200]
        return None, tel


# ── Parse response ─────────────────────────────────────────────────────────────

def _parse_set_writer_response(
    response_text: str,
    expected_count: int,
) -> Dict[str, Optional[str]]:
    """Parse JSON from LLM response. Returns empty dict on any parse error.

    Tries full json.loads() first (clean JSON response), then falls back to
    regex extraction (prose-wrapped JSON) to avoid fragile grab-first-object.
    """
    if not response_text:
        return {}

    def _validate_map(raw: Any) -> Dict[str, Optional[str]]:
        if not isinstance(raw, dict):
            return {}
        result: Dict[str, Optional[str]] = {}
        for k, v in raw.items():
            if v is None:
                result[str(k)] = None
            elif isinstance(v, str) and v.strip():
                result[str(k)] = v.strip()
        return result

    # Attempt 1: full parse (handles clean JSON with no surrounding prose)
    stripped = response_text.strip()
    if stripped.startswith("{"):
        try:
            raw = json.loads(stripped)
            parsed = _validate_map(raw)
            if parsed is not None:
                return parsed
        except json.JSONDecodeError:
            pass

    # Attempt 2: regex extraction (handles JSON embedded in prose)
    try:
        json_match = re.search(r"\{[^{}]+\}", response_text, re.DOTALL)
        if not json_match:
            return {}
        raw = json.loads(json_match.group(0))
        return _validate_map(raw)
    except (json.JSONDecodeError, ValueError):
        return {}


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

    def _empty(
        timed_out: bool = False,
        reason: str = "",
        tel: Optional[Dict[str, Any]] = None,
    ) -> SetWriterResult:
        logger.debug(
            "set_level_writer: empty_result timed_out=%s reason=%s", timed_out, reason
        )
        if tel is not None:
            tel.setdefault("notes_visible_count", 0)
            tel.setdefault("notes_hidden_count", 0)
            tel.setdefault("notes_rejected_count", 0)
            tel.setdefault("set_writer_timed_out", timed_out)
            if "set_writer_total_ms" not in tel:
                tel["set_writer_total_ms"] = int((time.monotonic() - t_start) * 1000)
            if reason:
                tel["writer_failure_reason"] = reason
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
            writer_telemetry=tel,
        )

    # Accumulated writer telemetry
    wtel: Dict[str, Any] = {
        "model": _SET_WRITER_MODEL,
        "max_tokens": _MAX_TOKENS_DEFAULT,
        "evidence_distill_ms": 0,
        "prompt_build_ms": 0,
        "input_token_estimate": 0,
        "llm_call_ms": 0,
        "parse_ms": 0,
        "validation_ms": 0,
        "set_writer_total_ms": 0,
        "dynamic_packet_count": 0,
        "dynamic_packet_char_count": 0,
        "dynamic_prompt_char_count": 0,
        "set_writer_timed_out": False,
    }

    try:
        # ── Budget gate ───────────────────────────────────────────────────────
        # Latency Architecture v1: use budget_for_set_writer_s() which caps the
        # LLM timeout at SET_WRITER_LLM_MAX_S (1.5s) regardless of how much
        # budget remains on paper. This prevents the set-writer from consuming
        # the full remaining note-gen window on slow requests.
        if deadline is not None:
            budget_s = deadline.budget_for_set_writer_s()
            if budget_s <= 0.0:
                logger.info(
                    "set_level_writer: skipped_no_budget remaining_ms=%d",
                    deadline.remaining_ms(),
                )
                wtel["set_writer_timed_out"] = True
                return _empty(timed_out=True, reason="no_budget", tel=wtel)
        else:
            budget_s = float(
                os.getenv("CONCIERGE_CARD_REASONING_TIMEOUT_MS", "8000")
            ) / 1000.0

        # ── Build card inputs from curated result ─────────────────────────────
        curated_cards = getattr(curated_result, "curated_cards", []) or []
        target_cards = curated_cards[:first_card_limit]

        if not target_cards:
            return _empty(reason="no_curated_cards", tel=wtel)

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
            return _empty(timed_out=False, reason="no_api_key", tel=wtel)

        # ── Distill AllowedClaimsPackets ──────────────────────────────────────
        t_distill = time.monotonic()
        try:
            packets = [
                _distill_allowed_claims_packet(ci, frame)
                for ci in card_inputs
            ]
        except Exception as dist_exc:
            logger.error(
                "set_level_writer: distill_error error=%s", dist_exc
            )
            wtel["evidence_distill_ms"] = int((time.monotonic() - t_distill) * 1000)
            return _empty(reason=f"distill_error:{dist_exc}", tel=wtel)
        wtel["evidence_distill_ms"] = int((time.monotonic() - t_distill) * 1000)

        # ── Build micro prompt ────────────────────────────────────────────────
        t_prompt = time.monotonic()
        try:
            prompt = _build_micro_set_prompt(packets, frame)
        except Exception as prompt_exc:
            logger.error(
                "set_level_writer: prompt_build_error error=%s", prompt_exc
            )
            wtel["prompt_build_ms"] = int((time.monotonic() - t_prompt) * 1000)
            return _empty(reason=f"prompt_build_error:{prompt_exc}", tel=wtel)
        wtel["prompt_build_ms"] = int((time.monotonic() - t_prompt) * 1000)

        # Packet/prompt size telemetry
        wtel["dynamic_packet_count"] = len(packets)
        wtel["dynamic_packet_char_count"] = sum(
            len(_render_packet(p, i + 1, len(packets)))
            for i, p in enumerate(packets)
        )
        wtel["dynamic_prompt_char_count"] = len(prompt)
        wtel["input_token_estimate"] = len(prompt) // 4

        # ── LLM call ──────────────────────────────────────────────────────────
        t_llm = time.monotonic()
        raw, llm_tel = _call_set_writer_llm(prompt, timeout_s=budget_s)
        wtel["llm_call_ms"] = int((time.monotonic() - t_llm) * 1000)
        wtel.update(llm_tel)  # model, max_tokens, stop_reason, token counts

        if raw is None:
            logger.info(
                "set_level_writer: no_llm_response elapsed_ms=%d",
                int((time.monotonic() - t_start) * 1000),
            )
            wtel["set_writer_total_ms"] = int((time.monotonic() - t_start) * 1000)
            return _empty(reason="llm_no_response", tel=wtel)

        # ── Parse response ────────────────────────────────────────────────────
        t_parse = time.monotonic()
        parsed = _parse_set_writer_response(raw, len(card_inputs))
        wtel["parse_ms"] = int((time.monotonic() - t_parse) * 1000)

        if not parsed:
            logger.warning(
                "set_level_writer: parse_failed elapsed_ms=%d response=%r",
                int((time.monotonic() - t_start) * 1000), raw[:200],
            )
            wtel["set_writer_total_ms"] = int((time.monotonic() - t_start) * 1000)
            return _empty(reason="parse_failed", tel=wtel)

        # ── Validate notes ────────────────────────────────────────────────────
        t_validate = time.monotonic()
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
                caveat_type = ""
                signals = ci.curation_signals
                if getattr(signals, "has_listing_context_only", False):
                    caveat_type = "listing_context"
                elif getattr(signals, "modifier_fit", "") == "not_confirmed":
                    caveat_type = "unconfirmed_modifier"
                elif getattr(ci, "dossier", None) and getattr(
                    ci.dossier, "is_minimal", False
                ):
                    caveat_type = "low_evidence"

                note_obj = SetWriterNote(
                    place_id=place_id,
                    note=trimmed,
                    validated=True,
                    rejection_reason="",
                    source=SOURCE_SET_WRITER,
                    role_used_internal=ci.role,
                    evidence_terms_used=[],
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

        wtel["validation_ms"] = int((time.monotonic() - t_validate) * 1000)

        # ── Cross-card diversity check ─────────────────────────────────────────
        repeated_skeleton_count = _enforce_repeated_skeleton_diversity(
            notes_by_place_id,
            validated_notes_for_diversity,
        )
        if repeated_skeleton_count > 0:
            logger.warning(
                "set_level_writer: repeated_skeletons_hidden count=%d "
                "pre_enforcement_visible=%d",
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
                "hiding all validated notes (fail closed for text, cards kept)",
                rev_exc,
            )
            _hidden_on_error = 0
            for _note_obj in notes_by_place_id.values():
                if _note_obj.validated:
                    _note_obj.validated = False
                    _note_obj.note = ""
                    _note_obj.source = SOURCE_OMITTED
                    _note_obj.rejection_reason = "reviewer_error:fail_closed"
                    _hidden_on_error += 1
            visible_count = 0
            hidden_count = len(notes_by_place_id)
            reviewer_telemetry_dict = {
                "reviewer_used": True,
                "reviewer_timed_out": True,
                "reviewer_rejected_note_count": 0,
                "reviewer_hidden_note_count": _hidden_on_error,
                "reviewer_error": str(rev_exc)[:200],
                "fallback_note_visible_count": 0,   # invariant
                "deterministic_visible_count": 0,   # invariant
            }

        elapsed_ms = int((time.monotonic() - t_start) * 1000)
        wtel["set_writer_total_ms"] = elapsed_ms
        wtel["notes_visible_count"] = visible_count
        wtel["notes_hidden_count"] = hidden_count
        wtel["notes_rejected_count"] = rejected_count

        logger.info(
            "set_level_writer: complete input=%d visible=%d hidden=%d "
            "rejected=%d repeated_skeleton=%d unsupported_claim=%d "
            "elapsed_ms=%d llm_call_ms=%d prompt_chars=%d packet_count=%d",
            len(card_inputs), visible_count, hidden_count,
            rejected_count, repeated_skeleton_count, unsupported_claim_count,
            elapsed_ms, wtel.get("llm_call_ms", 0),
            wtel.get("dynamic_prompt_char_count", 0),
            wtel.get("dynamic_packet_count", 0),
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
            writer_telemetry=wtel,
        )

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - t_start) * 1000)
        logger.warning(
            "set_level_writer: unhandled_exception elapsed_ms=%d error=%s",
            elapsed_ms, exc,
        )
        return _empty(timed_out=True, reason=f"unhandled_exception:{exc}")
