"""Card Role + Curated Set Ranker v1 — deterministic internal substrate.

PR #260: Assigns typed internal roles and curation scores to verified Google-backed
cards using PlaceEvidenceDossier v1. Optionally reorders the first-response set
within conservative bounds.

All outputs are internal — roles, scores, and signals are NEVER exposed as visible
card fields, note prose, or user-facing labels.

Architecture invariants:
- Deterministic: no LLM, no random elements, no category-specific keyword patches.
- Internal only: CuratedCard fields do not map to any visible card payload.
- Conservative reordering: concept_fit carries 0.50 weight — no low-concept card
  can overrank a strong-concept card via theme count alone (theme weight = 0.04 max).
- Never mints cards: only reorders existing (entity, rank_score) pairs.
- Never blocks card return: caller wraps curate_cards() in try/except; fallback = original order.
- Preserves card cap: output set is never larger than input set.
- Preserves fallback_note_visible_count=0: does not touch note generation.
- Modifier-confirmed role requires explicit enrichment evidence or confirmed ranker
  modifier_fit; listing_context name tokens alone are insufficient.
- Evidence-rich requires actual Place Details provider evidence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Role constants (strings, not Enum, for easy JSON serialisation) ────────────

ROLE_BEST_OVERALL = "best_overall"
ROLE_STRONGEST_QUERY_MATCH = "strongest_query_match"
ROLE_MODIFIER_CONFIRMED = "modifier_confirmed"
ROLE_EVIDENCE_RICH = "evidence_rich"
ROLE_DISTINCTIVE_THEME = "distinctive_theme"
ROLE_GEOGRAPHIC_FIT = "geographic_fit"
ROLE_SAFE_POPULAR_FALLBACK = "safe_popular_fallback"
ROLE_INTERESTING_BUT_WEAKER = "interesting_but_weaker"
ROLE_LOW_EVIDENCE_HOLDBACK = "low_evidence_holdback"

# Confidence constants (re-imported from evidence_dossier for clarity)
_CONF_STRONG = "strong"
_CONF_MIXED = "mixed"
_CONF_WEAK = "weak"


# ── Typed contracts ────────────────────────────────────────────────────────────

@dataclass
class CardCurationSignals:
    """Deterministic curation signals derived from dossier + rank score.

    All fields are computed from dossier data; no LLM, no new provider calls.
    Internal use only — not part of visible card payload.
    """

    concept_fit: float               # 0.0–1.0 from dossier.query_fit.concept_fit
    geo_fit: float                   # 0.0–1.0 from dossier.query_fit.geo_fit
    modifier_fit: str                # "confirmed" | "not_confirmed" | "none"
    source_confidence: str           # "strong" | "mixed" | "weak"
    theme_count: int                 # explicit (non-listing-context) positive themes
    has_place_details: bool          # google_place_details in provider_evidence
    has_explicit_modifier_evidence: bool  # view/patio theme from enrichment, not listing_context
    has_listing_context_only: bool   # view_patio_waterfront entries ALL listing_context:*
    negative_caveat_count: int       # len(review_themes.negative_caveats)
    evidence_gap_count: int          # len(internal_evidence_gaps)
    diversity_key: str               # primary_type or category for set-diversity signals
    original_rank_index: int         # position in original ranked list (0-based)


@dataclass
class CuratedCard:
    """One card with internal role assignment and curation metadata.

    entity and rank_score are the SAME objects from the original ranked list —
    no new card or payload fields are created.
    Internal use only.
    """

    entity: Any                              # original PlaceEntity from ranked list
    rank_score: Any                          # original RankScore from ranked list
    dossier: Any                             # PlaceEvidenceDossier
    role: str                                # one of ROLE_* constants
    curation_score: float                    # deterministic 0.0–1.0 composite
    curation_signals: CardCurationSignals
    curation_reasons_internal: List[str]     # human-readable justification (internal)
    original_rank_index: int                 # position in original ranked list (0-based)


@dataclass
class CuratedSetResult:
    """Result of one curation pass over a set of ranked verified cards."""

    curated_cards: List[CuratedCard]
    role_counts: Dict[str, int]
    source_confidence_counts: Dict[str, int]
    low_evidence_holdback_count: int
    modifier_confirmed_count: int
    evidence_rich_count: int
    reordered_count: int
    input_count: int
    output_count: int

    def as_telemetry_dict(self, elapsed_ms: int = 0) -> Dict[str, Any]:
        """Structured telemetry for semantic_retrieval_v1.curated_set_telemetry log."""
        return {
            "curated_input_count": self.input_count,
            "curated_output_count": self.output_count,
            "curated_role_counts": self.role_counts,
            "curated_confidence_counts": self.source_confidence_counts,
            "curated_reordered_count": self.reordered_count,
            "curated_modifier_confirmed_count": self.modifier_confirmed_count,
            "curated_evidence_rich_count": self.evidence_rich_count,
            "curated_low_evidence_holdback_count": self.low_evidence_holdback_count,
            "curated_fallback_to_original_order": False,
            "curated_ms": elapsed_ms,
        }


# ── Internal helpers ───────────────────────────────────────────────────────────

def _explicit_theme_count(review_themes: Any) -> int:
    """Count positive explicit themes (enrichment-derived, not listing_context)."""
    explicit_view = sum(
        1 for e in (review_themes.view_patio_waterfront or [])
        if not e.startswith("listing_context:")
    )
    return (
        len(review_themes.food_drink or [])
        + len(review_themes.ambiance or [])
        + len(review_themes.service or [])
        + len(review_themes.crowd_noise or [])
        + explicit_view
        + len(review_themes.occasion_fit or [])
        # negative_caveats tracked separately; excluded from positive count
    )


def _build_curation_signals(
    dossier: Any,  # PlaceEvidenceDossier
    original_rank_index: int,
) -> CardCurationSignals:
    """Extract CardCurationSignals from a PlaceEvidenceDossier."""
    themes = dossier.review_themes
    view_entries: List[str] = themes.view_patio_waterfront or []

    has_place_details = any(
        getattr(p, "source", "") == "google_place_details"
        for p in (dossier.provider_evidence or [])
    )

    # Explicit modifier evidence: view/outdoor entry NOT from listing_context
    has_explicit_modifier_evidence = any(
        not e.startswith("listing_context:") for e in view_entries
    )

    # Listing context only: non-empty list where ALL entries are listing_context
    has_listing_context_only = bool(view_entries) and all(
        e.startswith("listing_context:") for e in view_entries
    )

    theme_count = _explicit_theme_count(themes)
    negative_caveat_count = len(themes.negative_caveats or [])
    evidence_gap_count = len(dossier.internal_evidence_gaps or [])

    diversity_key = (
        dossier.primary_type
        or dossier.category
        or (dossier.google_types[0] if dossier.google_types else "unknown")
    )

    query_fit = dossier.query_fit
    return CardCurationSignals(
        concept_fit=getattr(query_fit, "concept_fit", 0.0),
        geo_fit=getattr(query_fit, "geo_fit", 0.0),
        modifier_fit=getattr(query_fit, "modifier_fit", None) or "none",
        source_confidence=dossier.source_confidence,
        theme_count=theme_count,
        has_place_details=has_place_details,
        has_explicit_modifier_evidence=has_explicit_modifier_evidence,
        has_listing_context_only=has_listing_context_only,
        negative_caveat_count=negative_caveat_count,
        evidence_gap_count=evidence_gap_count,
        diversity_key=diversity_key,
        original_rank_index=original_rank_index,
    )


def _assign_role(
    signals: CardCurationSignals,
    is_minimal: bool,
) -> Tuple[str, List[str]]:
    """Assign one primary role to a card. Deterministic, generic — no category hardcoding.

    Role priority (first match wins):
      1. best_overall        — high concept fit + strong evidence
      2. strongest_query_match — high concept fit
      3. modifier_confirmed  — confirmed modifier (explicit evidence required)
      4. distinctive_theme   — place details + rich explicit themes
      5. evidence_rich       — place details + any explicit themes
      6. geographic_fit      — strong geo signal
      7. safe_popular_fallback — moderate concept fit, Google-verified
      8. low_evidence_holdback — minimal dossier or very low concept fit
      9. interesting_but_weaker — catch-all
    """
    concept = signals.concept_fit
    geo = signals.geo_fit
    reasons: List[str] = []

    # ── Role 1: best_overall ──────────────────────────────────────────────────
    if concept >= 0.8 and signals.source_confidence == _CONF_STRONG:
        reasons.append(f"concept_fit={concept:.2f} source_confidence=strong")
        return ROLE_BEST_OVERALL, reasons

    # ── Role 2: strongest_query_match ─────────────────────────────────────────
    if concept >= 0.7:
        reasons.append(f"concept_fit={concept:.2f}")
        return ROLE_STRONGEST_QUERY_MATCH, reasons

    # ── Role 3: modifier_confirmed ────────────────────────────────────────────
    # Requires: confirmed modifier (ranker or explicit enrichment), concept >= 0.4,
    # and listing_context alone is NOT sufficient.
    modifier_confirmed = (
        signals.modifier_fit == "confirmed"
        or signals.has_explicit_modifier_evidence
    )
    if concept >= 0.4 and modifier_confirmed and not signals.has_listing_context_only:
        reasons.append(
            f"modifier_fit={signals.modifier_fit} "
            f"explicit_modifier_evidence={signals.has_explicit_modifier_evidence}"
        )
        return ROLE_MODIFIER_CONFIRMED, reasons

    # ── Role 4: distinctive_theme ─────────────────────────────────────────────
    # Requires place_details + rich explicit themes (>= 3)
    if concept >= 0.5 and signals.has_place_details and signals.theme_count >= 3:
        reasons.append(
            f"theme_count={signals.theme_count} has_place_details=True"
        )
        return ROLE_DISTINCTIVE_THEME, reasons

    # ── Role 5: evidence_rich ─────────────────────────────────────────────────
    # Requires place_details + at least one explicit theme
    if concept >= 0.4 and signals.has_place_details and signals.theme_count >= 1:
        reasons.append(
            f"has_place_details=True theme_count={signals.theme_count}"
        )
        return ROLE_EVIDENCE_RICH, reasons

    # ── Role 6: geographic_fit ────────────────────────────────────────────────
    if geo >= 0.7 and concept >= 0.3:
        reasons.append(f"geo_fit={geo:.2f} concept_fit={concept:.2f}")
        return ROLE_GEOGRAPHIC_FIT, reasons

    # ── Role 7: safe_popular_fallback ─────────────────────────────────────────
    if concept >= 0.25:
        reasons.append(f"concept_fit={concept:.2f} google_verified_fallback")
        return ROLE_SAFE_POPULAR_FALLBACK, reasons

    # ── Role 8: low_evidence_holdback ─────────────────────────────────────────
    if is_minimal or concept < 0.25:
        reasons.append(f"is_minimal={is_minimal} concept_fit={concept:.2f}")
        return ROLE_LOW_EVIDENCE_HOLDBACK, reasons

    # ── Role 9: catch-all ─────────────────────────────────────────────────────
    reasons.append(f"concept_fit={concept:.2f}")
    return ROLE_INTERESTING_BUT_WEAKER, reasons


def _compute_curation_score(signals: CardCurationSignals) -> float:
    """Deterministic curation score in [0.0, 1.0].

    Weight design rationale:
    - concept_fit = 0.50 dominant: no combination of secondary signals can flip a
      strongly-higher-concept card below a low-concept card (theme max = 0.04).
    - geo_fit = 0.20: meaningful geo proximity is a legitimate secondary signal.
    - modifier_bonus = 0.15: confirmed modifier is a strong positive signal.
    - source_confidence = 0.08: richer evidence modestly boosts score.
    - theme_contribution = 0.04 (max, requires place_details): theme count capped
      to prevent over-weighting when concept fit differs substantially.
    - Penalties are kept small to avoid over-penalising thin-evidence cards that are
      still Google-verified and conceptually relevant.
    """
    conf_val = {
        _CONF_STRONG: 1.0,
        _CONF_MIXED: 0.5,
        _CONF_WEAK: 0.0,
    }.get(signals.source_confidence, 0.0)

    # Modifier bonus: only when confirmed and not listing_context-only
    modifier_bonus = (
        0.15
        if (signals.modifier_fit == "confirmed" or signals.has_explicit_modifier_evidence)
        and not signals.has_listing_context_only
        else 0.0
    )

    # Theme evidence: capped at 0.04, requires place_details (explicit enrichment only)
    theme_contribution = (
        min(signals.theme_count / 5.0, 1.0) * 0.04
        if signals.has_place_details
        else 0.0
    )

    neg_penalty = min(signals.negative_caveat_count * 0.03, 0.09)
    gap_penalty = min(signals.evidence_gap_count * 0.02, 0.06)

    score = (
        0.50 * signals.concept_fit
        + 0.20 * signals.geo_fit
        + modifier_bonus
        + 0.08 * conf_val
        + theme_contribution
        - neg_penalty
        - gap_penalty
    )
    return max(0.0, min(1.0, score))


# ── Public API ────────────────────────────────────────────────────────────────

def curate_cards(
    ranked: List[Tuple[Any, Any]],
    dossiers: List[Any],  # List[PlaceEvidenceDossier]
    first_card_limit: int = 6,
) -> CuratedSetResult:
    """Assign roles and compute curation scores; conservatively reorder within cap.

    Args:
        ranked:           List of (PlaceEntity, RankScore) in original ranked order.
        dossiers:         List of PlaceEvidenceDossier in ranked order (top-N).
        first_card_limit: Maximum cards in the first response (default 6).

    Returns:
        CuratedSetResult with role-annotated cards.
        Reordering is applied only within the first first_card_limit entries.
        Cards without matching dossiers are skipped (treated as if not present in cap).
        Never raises — caller must wrap in try/except for safety.

    Contract:
        - Never mints new cards or card payload fields.
        - Never changes entity.place_id or any verified-place attributes.
        - Output count == input count (no cards dropped).
    """
    if not ranked or not dossiers:
        return CuratedSetResult(
            curated_cards=[],
            role_counts={},
            source_confidence_counts={},
            low_evidence_holdback_count=0,
            modifier_confirmed_count=0,
            evidence_rich_count=0,
            reordered_count=0,
            input_count=len(ranked),
            output_count=0,
        )

    # Build a place_id → dossier lookup for safe pairing
    dossier_map: Dict[str, Any] = {
        d.place_id: d for d in dossiers
    }

    curated: List[CuratedCard] = []
    for i, (entity, rank_score) in enumerate(ranked):
        place_id = getattr(entity, "place_id", None)
        dossier = dossier_map.get(place_id) if place_id else None
        if dossier is None:
            # No dossier available — preserve with minimal curation signal
            # so the card is not silently dropped from downstream
            logger.debug(
                "card_curator: no_dossier place_id=%s name=%s rank=%d",
                place_id,
                getattr(entity, "name", "?"),
                i,
            )
            # Assign safe_popular_fallback by default for no-dossier entries
            curated.append(CuratedCard(
                entity=entity,
                rank_score=rank_score,
                dossier=None,
                role=ROLE_INTERESTING_BUT_WEAKER,
                curation_score=max(0.0, getattr(rank_score, "subtype_fit", 0.0) * 0.5),
                curation_signals=CardCurationSignals(
                    concept_fit=getattr(rank_score, "subtype_fit", 0.0),
                    geo_fit=getattr(rank_score, "geo_fit", 0.0),
                    modifier_fit="none",
                    source_confidence=_CONF_WEAK,
                    theme_count=0,
                    has_place_details=False,
                    has_explicit_modifier_evidence=False,
                    has_listing_context_only=False,
                    negative_caveat_count=0,
                    evidence_gap_count=3,
                    diversity_key="unknown",
                    original_rank_index=i,
                ),
                curation_reasons_internal=["no_dossier"],
                original_rank_index=i,
            ))
            continue

        try:
            signals = _build_curation_signals(dossier, i)
            role, reasons = _assign_role(signals, dossier.is_minimal)
            score = _compute_curation_score(signals)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "card_curator: signal_build_failed place_id=%s name=%s rank=%d error=%s",
                place_id,
                getattr(entity, "name", "?"),
                i,
                exc,
            )
            curated.append(CuratedCard(
                entity=entity,
                rank_score=rank_score,
                dossier=dossier,
                role=ROLE_INTERESTING_BUT_WEAKER,
                curation_score=max(0.0, getattr(rank_score, "subtype_fit", 0.0) * 0.5),
                curation_signals=CardCurationSignals(
                    concept_fit=getattr(rank_score, "subtype_fit", 0.0),
                    geo_fit=getattr(rank_score, "geo_fit", 0.0),
                    modifier_fit="none",
                    source_confidence=_CONF_WEAK,
                    theme_count=0,
                    has_place_details=False,
                    has_explicit_modifier_evidence=False,
                    has_listing_context_only=False,
                    negative_caveat_count=0,
                    evidence_gap_count=3,
                    diversity_key="unknown",
                    original_rank_index=i,
                ),
                curation_reasons_internal=["signal_build_error"],
                original_rank_index=i,
            ))
            continue

        curated.append(CuratedCard(
            entity=entity,
            rank_score=rank_score,
            dossier=dossier,
            role=role,
            curation_score=score,
            curation_signals=signals,
            curation_reasons_internal=reasons,
            original_rank_index=i,
        ))

    if not curated:
        return CuratedSetResult(
            curated_cards=[],
            role_counts={},
            source_confidence_counts={},
            low_evidence_holdback_count=0,
            modifier_confirmed_count=0,
            evidence_rich_count=0,
            reordered_count=0,
            input_count=len(ranked),
            output_count=0,
        )

    # ── Conservative reorder within first_card_limit ─────────────────────────
    # Sort key: (-curation_score, original_rank_index) for deterministic stable output.
    # concept_fit weight (0.50) ensures no low-concept card can overrank a
    # strongly-higher-concept card via theme count alone (theme max = 0.04).
    in_cap = [c for c in curated if c.original_rank_index < first_card_limit]
    beyond_cap = [c for c in curated if c.original_rank_index >= first_card_limit]

    in_cap_original_order = sorted(in_cap, key=lambda c: c.original_rank_index)
    sorted_cap = sorted(in_cap, key=lambda c: (-c.curation_score, c.original_rank_index))

    reordered_count = sum(
        1
        for orig, new in zip(in_cap_original_order, sorted_cap)
        if orig.original_rank_index != new.original_rank_index
    )

    final_cards = sorted_cap + sorted(beyond_cap, key=lambda c: c.original_rank_index)

    # ── Aggregate telemetry ────────────────────────────────────────────────────
    role_counts: Dict[str, int] = {}
    conf_counts: Dict[str, int] = {}
    for c in final_cards:
        role_counts[c.role] = role_counts.get(c.role, 0) + 1
        conf_counts[c.curation_signals.source_confidence] = (
            conf_counts.get(c.curation_signals.source_confidence, 0) + 1
        )

    logger.info(
        "card_curator: curated input=%d output=%d reordered=%d "
        "role_counts=%r confidence_counts=%r",
        len(ranked),
        len(final_cards),
        reordered_count,
        role_counts,
        conf_counts,
    )

    return CuratedSetResult(
        curated_cards=final_cards,
        role_counts=role_counts,
        source_confidence_counts=conf_counts,
        low_evidence_holdback_count=role_counts.get(ROLE_LOW_EVIDENCE_HOLDBACK, 0),
        modifier_confirmed_count=role_counts.get(ROLE_MODIFIER_CONFIRMED, 0),
        evidence_rich_count=(
            role_counts.get(ROLE_EVIDENCE_RICH, 0)
            + role_counts.get(ROLE_DISTINCTIVE_THEME, 0)
        ),
        reordered_count=reordered_count,
        input_count=len(ranked),
        output_count=len(final_cards),
    )
