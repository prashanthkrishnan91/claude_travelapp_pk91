"""Claim Safety Reviewer — deterministic gate for set-writer visible outputs.

PR #267: Guards per-card concierge notes and set-level summary text against
unsupported claims before response serialization. All checks are regex-based
(deterministic) with a configurable timeout for fail-closed behavior.

PR #268: Extends with visible copy-quality gates:
  - Malformed rating residue in summaries (e.g. "Taproom.8" → "Taproom").
  - Unsupported after-hours/crowd positioning claims ("purpose-built for
    after-hours crowds").
  - Hidden-gem/localness superlatives in summaries without evidence support.
  - Unsupported scenic/view claims in summaries.
  - Generic occasion-sprawl in per-card notes.

Hard rule: A business name is NEVER sufficient evidence for a temporal claim.
"2AM Izakaya, whose name alone signals late-night credibility" is rejected
regardless of evidence. Only actual hours, provider metadata, review snippets,
or editorial facts may support a late-night/24-hour/open-late claim.

Fail-closed contract:
  - Note reviewer timeout → hide note, keep card (no card drop).
  - Summary reviewer timeout → omit summary (no unsafe prose shown).
  - Errors → same as timeout (fail closed for text, not for cards).

Telemetry fields emitted:
  reviewer_used, reviewer_ms, reviewer_timed_out,
  reviewer_rejected_note_count, reviewer_hidden_note_count,
  reviewer_rejected_summary, reviewer_sanitized_summary,
  reviewer_unsupported_claim_count, reviewer_internal_leakage_count,
  malformed_summary_count, unsupported_superlative_count,
  generic_note_hidden_count,
  final_summary_visible, final_note_visible_count,
  fallback_note_visible_count (invariant: 0),
  deterministic_visible_count (invariant: 0).
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Default reviewer timeout ───────────────────────────────────────────────────
# Deterministic regex review is fast (<1ms), but we set a guard against
# pathological input. Fail closed means: if we can't review it, hide it.
_DEFAULT_REVIEWER_TIMEOUT_S: float = 1.0


# ── Name-based hours inference ─────────────────────────────────────────────────
# Rejects any note that infers operating hours from a business name alone.
# Hard rule: the name "2AM Izakaya" is not evidence of late-night hours.
# Accepts only when actual hours, provider metadata, review text, or editorial
# facts explicitly confirm the temporal attribute.
#
# Blocked patterns (examples):
#   "2AM Izakaya, whose name alone signals late-night credibility"
#   "name implies 24-hour availability"
#   "name suggests open late"
#   "whose name indicates after-hours"
_NAME_HOURS_INFERENCE_RE = re.compile(
    r"\b(?:"
    # "name [alone] {signals|implies|suggests|indicates} {temporal_term}"
    r"name\s+(?:alone\s+)?(?:signals?|implies?|suggests?|indicates?)\s+"
    r"(?:late[-\s]?night|24[-\s]?hour|open[-\s]?late|after[-\s]?hours?"
    r"|overnight|all[-\s]?night|credibility|late[-\s]?night\s+\w+)"
    # "name itself {signals|implies|suggests} {temporal_term}"
    r"|name\s+itself\s+(?:signals?|implies?|suggests?|indicates?)\s+"
    r"(?:late[-\s]?night|24[-\s]?hour|open[-\s]?late|after[-\s]?hours?)"
    # "whose name {alone} {signals|implies|suggests|indicates}"
    r"|whose\s+name\s+(?:alone\s+)?(?:signals?|implies?|suggests?|indicates?)"
    # "the name alone" followed by temporal inference words
    r"|the\s+name\s+alone\s+(?:signals?|implies?|suggests?|indicates?|conveys?|hints?)"
    r")",
    re.IGNORECASE,
)


# ── Unsupported preference terms ───────────────────────────────────────────────
# These require evidence confirmation before use in visible output.
# The reviewer checks frame soft_preferences and evidence for support.
_HIDDEN_GEM_TERMS_RE = re.compile(
    r"\b(?:hidden\s+gem|local\s+favorite|locals?\s+love|locals?\s+know|"
    r"underrated|undiscovered|off[-\s]the[-\s]beaten|best[-\s]kept\s+secrets?"
    r"|under[-\s]the[-\s]radar|sleeper\s+(?:hit|spot|pick))\b",
    re.IGNORECASE,
)

# ── Unsupported localness/hidden-gem editorial claims in summaries ─────────────
# Narrower than _HIDDEN_GEM_TERMS_RE: targets overconfident editorial assertions
# that cannot be supported in a set-level summary context. Deliberately does NOT
# block user-intent framing like "hidden gem bars" or "hidden-gem-style matches"
# — these are the user's query phrasing and do not constitute an editorial claim.
#
# Blocked (unsupported editorial assertions):
#   "most authentically local", "authentically local"
#   "under-the-radar picks/spots/bars/..." (noun-phrase form)
#   "are/is/the most under-the-radar" (predicate form)
#   "locals love/know/favor", "only locals know"
#   "best-kept secret(s)"
#   "tourists rarely/never find/know"
#   "true local secret", "true hidden gem"
#   "undiscovered gem/spot/..." or "truly undiscovered"
#   "off-the-beaten-path/track"
#
# Allowed (safe user-intent framing):
#   "For hidden gem bars in Chicago..."
#   "hidden gem bar matches from the search set"
#   "hidden-gem-style bars"
_SUMMARY_LOCALNESS_CLAIM_RE = re.compile(
    r"(?:"
    r"\bmost\s+authentically\s+local\b"
    r"|\bauthentically\s+local\b"
    # "under-the-radar [noun]" — editorial noun-phrase positioning
    r"|\bunder[-\s]the[-\s]radar\s+(?:picks?|spots?|bars?|restaurants?|finds?|gems?|options?|places?|choices?|selections?)\b"
    # "are/is/the most/truly under-the-radar" — predicate form
    r"|\b(?:are|is|the\s+most|truly|most)\s+under[-\s]the[-\s]radar\b"
    r"|\blocals?\s+(?:love|know|frequent|haunt|favor|find|visit)\b"
    r"|\bonly\s+locals?\s+(?:know|find|visit)\b"
    r"|\bbest[-\s]kept\s+secrets?\b"
    r"|\btourists?\s+(?:rarely|never)\s+(?:find|know|visit|discover)\b"
    r"|\btrue\s+(?:local\s+secret|hidden\s+gem)\b"
    r"|\b(?:truly|largely|mostly)\s+undiscovered\b"
    r"|\bundiscovered\s+(?:gem|spot|bar|restaurant|place)\b"
    r"|\boff[-\s]the[-\s]beaten[-\s](?:path|track)\b"
    r")",
    re.IGNORECASE,
)

_ROMANTIC_TERMS_RE = re.compile(
    r"\b(?:romantic\s+(?:spot|setting|bar|restaurant|date|evening)|"
    r"perfect\s+for\s+(?:a\s+)?date|great\s+for\s+(?:a\s+)?date|"
    r"date\s+night\s+(?:spot|pick|destination)|couples?\s+(?:dining|night\s+out))\b",
    re.IGNORECASE,
)

_SCENIC_TERMS_RE = re.compile(
    r"\b(?:scenic\s+view|stunning\s+view|beautiful\s+view|panoramic\s+view"
    r"|scenic\s+setting|scenic\s+spot)\b",
    re.IGNORECASE,
)

_BEST_VALUE_TERMS_RE = re.compile(
    r"\b(?:best\s+value(?:\s+in\s+\w+)?|great\s+value(?:\s+for\s+money)?)\b",
    re.IGNORECASE,
)


# ── Malformed rating residue ───────────────────────────────────────────────────
# Blocks strings like "Taproom.8" where a decimal rating is accidentally
# concatenated to the last word of a business name. Pattern: a capitalized word
# (3+ chars, CamelCase) immediately followed by "." and a digit.
# e.g. "Taproom.8", "Bar.4", "Place.4.5" → sanitize to "Taproom", "Bar", "Place".
_MALFORMED_RATING_RESIDUE_RE = re.compile(
    r"\b[A-Z][a-z]{2,}\.\d(?:\.\d+)?\b",
    re.UNICODE,
)


# ── Unsupported after-hours/crowd positioning ─────────────────────────────────
# Rejects overconfident claims that a venue is "purpose-built for after-hours
# crowds" or equivalently positioned for late-night audiences without actual
# hours, crowd-density, or late-night editorial evidence. This is distinct from
# name-inference (blocked by _NAME_HOURS_INFERENCE_RE) and covers superlative
# capability-positioning language in set-level summaries and per-card notes.
_AFTER_HOURS_CROWD_RE = re.compile(
    r"\b(?:"
    r"purpose[-\s]?built\s+for\s+(?:after[-\s]?hours?|late[-\s]?night)"
    r"|built\s+for\s+(?:after[-\s]?hours?|late[-\s]?night)\s+crowds?"
    r"|designed\s+for\s+(?:after[-\s]?hours?|late[-\s]?night)\s+crowds?"
    r"|catered?\s+to(?:ward)?\s+(?:after[-\s]?hours?|late[-\s]?night)\s+crowds?"
    r"|tailored\s+(?:to|for)\s+(?:after[-\s]?hours?|late[-\s]?night)\s+crowds?"
    r")\b",
    re.IGNORECASE,
)


# ── Generic occasion-sprawl in per-card notes ─────────────────────────────────
# Rejects notes claiming suitability for a vague range of occasions without
# evidence. E.g. "suited for occasions ranging from casual groups to
# anniversaries" provides no concrete differentiator and is rejected.
_OCCASION_SPRAWL_RE = re.compile(
    r"\b(?:"
    # "suited for occasions ranging from X to Y"
    r"suited\s+for\s+occasions?\s+ranging\s+from"
    # "suited for [groups/dinners/etc.] ranging from X to Y"
    r"|suited\s+for\s+\w+(?:\s+\w+)?\s+ranging\s+from\s+\w+(?:\s+\w+)?\s+to\s+\w+"
    # "a range/variety of occasions" (with or without preceding "for"/"to")
    r"|(?:a\s+)?(?:range|variety)\s+of\s+occasions?"
    # "from casual [groups/dinners] to anniversaries/weddings/special occasions"
    r"|from\s+casual\s+(?:\w+\s+)?(?:groups?|hangouts?|dinners?|gatherings?|evenings?)"
    r"\s+to\s+(?:anniversaries?|weddings?|special\s+occasions?|romantic\s+\w+)"
    r")\b",
    re.IGNORECASE,
)


# ── Unsupported scenic/view claims in summaries ────────────────────────────────
# For per-card notes, reason_validator._UNSUPPORTED_ATTRIBUTE_RE handles
# view/waterfront evidence-gating. For set-level summaries, this reviewer
# enforces the same constraint via sentence-level sanitization.
# Superlatives and explicit venue-feature claims are targeted; general phrases
# like "with a view" (user-intent language) are not blocked here.
_SUMMARY_VIEW_CLAIM_RE = re.compile(
    r"\b(?:"
    r"stunning\s+views?|beautiful\s+views?|panoramic\s+(?:views?|setting)"
    r"|scenic\s+(?:views?|setting|spot|backdrop|experience|waterfront)"
    r"|waterfront\s+(?:dining|seating|setting|views?|bar|spot|experience)"
    r"|lakefront\s+(?:dining|seating|views?|bar|spot)"
    r"|rooftop\s+views?|lake\s+views?|river\s+views?|ocean\s+views?|sea\s+views?"
    r")\b",
    re.IGNORECASE,
)


# ── Internal label leakage ─────────────────────────────────────────────────────
# Internal role labels, evidence adequacy labels, dossier internals, and
# reviewer diagnostics must never appear in user-visible output.
_INTERNAL_LABEL_RE = re.compile(
    r"\b(?:"
    # Internal role labels from card_curator / set_level_writer
    r"best_overall|strongest_query_match|modifier_confirmed|evidence_rich"
    r"|distinctive_theme|geographic_fit|safe_popular_fallback"
    r"|interesting_but_weaker|low_evidence_holdback"
    # Evidence adequacy internals
    r"|evidence_adequacy|source_confidence|is_minimal|provider_evidence"
    r"|evidence_gap|internal_gap|evidence_quality:\s*(?:STRONG|OK|THIN)"
    r"|CardReason|SetWriterNote|PlaceEvidenceDossier"
    # Reviewer diagnostics that must never reach users
    r"|reviewer_rejected|reviewer_hidden|claim_safety|unsupported_claim_count"
    r"|reviewer_label|telemetry_field|dossier_internal"
    r")\b",
    re.IGNORECASE,
)


# ── Generic filler / repeated skeleton ────────────────────────────────────────
# Phrases that convey no information and indicate a low-quality note.
_FILLER_SKELETON_RE = re.compile(
    r"(?:"
    r"a\s+(?:great|solid|good|fine)\s+(?:option|choice|pick)\s+for\s+\w+"
    r"|perfect\s+for\s+those\s+(?:looking|who\s+want)"
    r"|makes\s+a\s+(?:great|good|solid)\s+(?:choice|option)\s+for\s+\w+\s+lovers?"
    r"|a\s+must[-\s]try\s+for\s+\w+\s+enthusiasts?"
    r")",
    re.IGNORECASE,
)


# ── Telemetry dataclasses ─────────────────────────────────────────────────────

@dataclass
class NoteReviewResult:
    """Result of reviewing one per-card note."""
    note: str               # final visible note ("" when rejected)
    passed: bool            # True = note passed reviewer
    rejection_reason: str   # "" when passed
    reviewer_ms: int        # wall-clock time spent reviewing


@dataclass
class SummaryReviewResult:
    """Result of reviewing a set-level summary."""
    summary: str            # final visible summary (may be sanitized or "")
    passed: bool            # True = original summary passed or was safely sanitized
    rejected: bool          # True = original summary was rejected outright
    sanitized: bool         # True = summary text was modified/trimmed
    rejection_reason: str   # "" when passed without change
    reviewer_ms: int


@dataclass
class ReviewerTelemetry:
    """Aggregated claim-safety reviewer telemetry for one pipeline turn."""
    reviewer_used: bool = False
    reviewer_ms: int = 0
    reviewer_timed_out: bool = False
    reviewer_rejected_note_count: int = 0
    reviewer_hidden_note_count: int = 0
    reviewer_rejected_summary: bool = False
    reviewer_sanitized_summary: bool = False
    reviewer_unsupported_claim_count: int = 0
    reviewer_internal_leakage_count: int = 0
    # PR #268 copy-quality telemetry
    malformed_summary_count: int = 0       # summaries with malformed rating residue
    unsupported_superlative_count: int = 0 # notes with unsupported after-hours/crowd claims
    generic_note_hidden_count: int = 0     # notes hidden due to occasion-sprawl
    final_summary_visible: bool = False
    final_note_visible_count: int = 0
    fallback_note_visible_count: int = 0  # structural invariant: always 0
    deterministic_visible_count: int = 0  # structural invariant: always 0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "reviewer_used": self.reviewer_used,
            "reviewer_ms": self.reviewer_ms,
            "reviewer_timed_out": self.reviewer_timed_out,
            "reviewer_rejected_note_count": self.reviewer_rejected_note_count,
            "reviewer_hidden_note_count": self.reviewer_hidden_note_count,
            "reviewer_rejected_summary": self.reviewer_rejected_summary,
            "reviewer_sanitized_summary": self.reviewer_sanitized_summary,
            "reviewer_unsupported_claim_count": self.reviewer_unsupported_claim_count,
            "reviewer_internal_leakage_count": self.reviewer_internal_leakage_count,
            "malformed_summary_count": self.malformed_summary_count,
            "unsupported_superlative_count": self.unsupported_superlative_count,
            "generic_note_hidden_count": self.generic_note_hidden_count,
            "final_summary_visible": self.final_summary_visible,
            "final_note_visible_count": self.final_note_visible_count,
            "fallback_note_visible_count": self.fallback_note_visible_count,
            "deterministic_visible_count": self.deterministic_visible_count,
        }


# ── Per-note reviewer ─────────────────────────────────────────────────────────

def review_note(
    note: str,
    entity_name: str,
    frame: Any,
    evidence: Any = None,
    timeout_s: float = _DEFAULT_REVIEWER_TIMEOUT_S,
) -> NoteReviewResult:
    """Review one per-card note for claim safety.

    Checks are deterministic (regex-based). If the reviewer times out or errors,
    it fails closed: returns an empty note so no unsafe prose is shown. The
    caller must NOT drop the card — only the note is hidden.

    Args:
        note: The candidate note text from the set-level writer.
        entity_name: Verified Google business name (for name-hours check context).
        frame: ExperienceFrame (used for soft_preferences context).
        evidence: Evidence bundle (optional; used for claim support checks).
        timeout_s: Max time budget for this review (fail closed on timeout).

    Returns:
        NoteReviewResult with final note ("" if rejected) and telemetry.
    """
    t0 = time.monotonic()

    def _elapsed_s() -> float:
        return time.monotonic() - t0

    def _ms() -> int:
        return int(_elapsed_s() * 1000)

    def _reject(reason: str) -> NoteReviewResult:
        return NoteReviewResult(note="", passed=False, rejection_reason=reason, reviewer_ms=_ms())

    def _pass() -> NoteReviewResult:
        return NoteReviewResult(note=note, passed=True, rejection_reason="", reviewer_ms=_ms())

    if not note or not note.strip():
        return _reject("empty_note")

    try:
        # Guard: timeout on pathological input
        if _elapsed_s() >= timeout_s:
            logger.warning("claim_safety_reviewer.review_note: timed_out name=%s", entity_name)
            return _reject("reviewer_timeout")

        # 1. Name-based hours inference — hard rejection, no evidence exception.
        #    A business name is NEVER sufficient evidence for a temporal claim.
        if _NAME_HOURS_INFERENCE_RE.search(note):
            logger.info(
                "claim_safety_reviewer: name_hours_inference name=%r note=%r",
                entity_name, note[:120],
            )
            return _reject("name_hours_inference")

        # 1b. Entity-name-as-subject temporal inference:
        #     "{EntityName} signals/implies/suggests {temporal_claim}"
        #     e.g. "2AM Izakaya signals 24-hour availability"
        if entity_name and entity_name.strip():
            _entity_pattern = re.compile(
                re.escape(entity_name.strip())
                + r"\s+(?:signals?|implies?|suggests?|indicates?)\s+"
                r"(?:24[-\s]?hour|late[-\s]?night|open[-\s]?late|"
                r"after[-\s]?hours?|overnight|all[-\s]?night)",
                re.IGNORECASE,
            )
            if _entity_pattern.search(note):
                logger.info(
                    "claim_safety_reviewer: entity_name_temporal_inference "
                    "name=%r note=%r",
                    entity_name, note[:120],
                )
                return _reject("name_temporal_inference")

        if _elapsed_s() >= timeout_s:
            return _reject("reviewer_timeout")

        # 2. Internal label leakage — role names, dossier internals, diagnostics.
        if _INTERNAL_LABEL_RE.search(note):
            logger.info(
                "claim_safety_reviewer: internal_label_leaked name=%r", entity_name
            )
            return _reject("internal_label_leakage")

        if _elapsed_s() >= timeout_s:
            return _reject("reviewer_timeout")

        # 3. Generic filler / repeated skeleton
        if _FILLER_SKELETON_RE.search(note):
            logger.info(
                "claim_safety_reviewer: generic_filler name=%r note=%r",
                entity_name, note[:80],
            )
            return _reject("generic_filler")

        if _elapsed_s() >= timeout_s:
            return _reject("reviewer_timeout")

        # 4. Unsupported after-hours/crowd positioning (PR #268).
        #    "purpose-built for after-hours crowds" is not supported unless
        #    actual hours, late-night editorial, or crowd evidence is present.
        if _AFTER_HOURS_CROWD_RE.search(note):
            logger.info(
                "claim_safety_reviewer: after_hours_crowd_overconfidence name=%r note=%r",
                entity_name, note[:120],
            )
            return _reject("after_hours_crowd_overconfidence")

        if _elapsed_s() >= timeout_s:
            return _reject("reviewer_timeout")

        # 5. Generic occasion-sprawl (PR #268).
        #    "suited for occasions ranging from casual groups to anniversaries"
        #    provides no concrete differentiator and is rejected.
        if _OCCASION_SPRAWL_RE.search(note):
            logger.info(
                "claim_safety_reviewer: generic_occasion_sprawl name=%r note=%r",
                entity_name, note[:120],
            )
            return _reject("generic_occasion_sprawl")

        return _pass()

    except Exception as exc:
        logger.warning(
            "claim_safety_reviewer.review_note: error name=%r error=%s",
            entity_name, exc,
        )
        return _reject(f"reviewer_error:{exc}")


# ── Summary reviewer ──────────────────────────────────────────────────────────

def review_summary(
    summary: str,
    frame: Any,
    timeout_s: float = _DEFAULT_REVIEWER_TIMEOUT_S,
) -> SummaryReviewResult:
    """Review a set-level summary for claim safety.

    Unlike review_note(), attempts sanitization first (removing the unsafe
    sentence/clause), and only rejects outright if the whole summary is unsafe.
    If summary cannot be made safe, returns empty summary rather than unsafe prose.

    Args:
        summary: The set-level summary text.
        frame: ExperienceFrame (for context).
        timeout_s: Max time budget (fail closed on timeout).

    Returns:
        SummaryReviewResult with final summary and telemetry.
    """
    t0 = time.monotonic()

    def _elapsed_s() -> float:
        return time.monotonic() - t0

    def _ms() -> int:
        return int(_elapsed_s() * 1000)

    def _reject(reason: str) -> SummaryReviewResult:
        return SummaryReviewResult(
            summary="",
            passed=False,
            rejected=True,
            sanitized=False,
            rejection_reason=reason,
            reviewer_ms=_ms(),
        )

    def _pass(text: str, sanitized: bool = False) -> SummaryReviewResult:
        return SummaryReviewResult(
            summary=text,
            passed=True,
            rejected=False,
            sanitized=sanitized,
            rejection_reason="",
            reviewer_ms=_ms(),
        )

    if not summary or not summary.strip():
        return _reject("empty_summary")

    try:
        if _elapsed_s() >= timeout_s:
            logger.warning("claim_safety_reviewer.review_summary: timed_out")
            return _reject("reviewer_timeout")

        # Working text accumulates sanitizations across all passes.
        working_text = summary
        was_sanitized = False

        # 1. Malformed rating residue (PR #268) — sanitize in-place.
        #    "Taproom.8" → "Taproom"; preserves the rest of the summary.
        if _MALFORMED_RATING_RESIDUE_RE.search(working_text):
            cleaned = _sanitize_malformed_rating_residue(working_text)
            if cleaned and cleaned.strip():
                logger.info(
                    "claim_safety_reviewer.review_summary: sanitized malformed_rating_residue"
                )
                working_text = cleaned
                was_sanitized = True
            else:
                return _reject("malformed_rating_residue")

        if _elapsed_s() >= timeout_s:
            return _reject("reviewer_timeout")

        # 2. Unsupported after-hours/crowd positioning (PR #268) — sanitize sentence.
        #    "purpose-built for after-hours crowds" without hours/crowd evidence.
        if _AFTER_HOURS_CROWD_RE.search(working_text):
            cleaned = _remove_sentence_with_pattern(working_text, _AFTER_HOURS_CROWD_RE)
            if cleaned and cleaned.strip():
                logger.info(
                    "claim_safety_reviewer.review_summary: sanitized after_hours_crowd_overconfidence"
                )
                working_text = cleaned
                was_sanitized = True
            else:
                return _reject("after_hours_crowd_overconfidence")

        if _elapsed_s() >= timeout_s:
            return _reject("reviewer_timeout")

        # 3. Hidden-gem/localness editorial claims (PR #268) — sanitize sentence.
        #    Uses _SUMMARY_LOCALNESS_CLAIM_RE (narrower than _HIDDEN_GEM_TERMS_RE)
        #    so that user-intent framing like "hidden gem bars" is NOT removed —
        #    only unsupported editorial claims like "most authentically local",
        #    "under-the-radar picks", "locals love", "best-kept secrets" are blocked.
        if _SUMMARY_LOCALNESS_CLAIM_RE.search(working_text):
            cleaned = _remove_sentence_with_pattern(working_text, _SUMMARY_LOCALNESS_CLAIM_RE)
            if cleaned and cleaned.strip():
                logger.info(
                    "claim_safety_reviewer.review_summary: sanitized localness_editorial_claim"
                )
                working_text = cleaned
                was_sanitized = True
            else:
                return _reject("localness_editorial_claim")

        if _elapsed_s() >= timeout_s:
            return _reject("reviewer_timeout")

        # 4. Unsupported scenic/view claims in summaries (PR #268) — sanitize sentence.
        #    "stunning lake views", "waterfront dining" without amenity evidence.
        if _SUMMARY_VIEW_CLAIM_RE.search(working_text):
            cleaned = _remove_sentence_with_pattern(working_text, _SUMMARY_VIEW_CLAIM_RE)
            if cleaned and cleaned.strip():
                logger.info(
                    "claim_safety_reviewer.review_summary: sanitized unsupported_view_claim"
                )
                working_text = cleaned
                was_sanitized = True
            else:
                return _reject("unsupported_view_claim")

        if _elapsed_s() >= timeout_s:
            return _reject("reviewer_timeout")

        # 5. Name-based hours inference — hard rejection for any sentence containing it.
        if _NAME_HOURS_INFERENCE_RE.search(working_text):
            # Attempt to sanitize by removing the offending sentence.
            cleaned = _remove_sentence_with_pattern(working_text, _NAME_HOURS_INFERENCE_RE)
            if cleaned and cleaned.strip():
                logger.info(
                    "claim_safety_reviewer.review_summary: sanitized name_hours_inference"
                )
                return _pass(cleaned, sanitized=True)
            # Cannot sanitize — reject outright.
            logger.info(
                "claim_safety_reviewer.review_summary: rejected name_hours_inference"
            )
            return _reject("name_hours_inference")

        if _elapsed_s() >= timeout_s:
            return _reject("reviewer_timeout")

        # 6. Internal label leakage — always reject (no sanitization attempted).
        if _INTERNAL_LABEL_RE.search(working_text):
            logger.info("claim_safety_reviewer.review_summary: rejected internal_label_leakage")
            return _reject("internal_label_leakage")

        if _elapsed_s() >= timeout_s:
            return _reject("reviewer_timeout")

        return _pass(working_text, sanitized=was_sanitized)

    except Exception as exc:
        logger.warning("claim_safety_reviewer.review_summary: error=%s", exc)
        return _reject(f"reviewer_error:{exc}")


def _remove_sentence_with_pattern(text: str, pattern: re.Pattern) -> str:
    """Remove any sentence containing a match for pattern from text.

    Splits on sentence boundaries (. ! ?), removes matching sentences,
    and rejoins. Returns empty string if all sentences are removed.
    """
    # Split into sentences preserving delimiters
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    safe_parts = [p for p in parts if not pattern.search(p)]
    return " ".join(safe_parts)


def _sanitize_malformed_rating_residue(text: str) -> str:
    """Strip decimal-digit suffix accidentally attached to a business name word.

    Transforms "Taproom.8" → "Taproom", "Bar.4.5" → "Bar".
    Only applies to CamelCase words (capital + 2+ lowercase) to avoid
    false positives with version numbers or abbreviations.
    """
    return _MALFORMED_RATING_RESIDUE_RE.sub(
        lambda m: re.sub(r"\.\d(?:\.\d+)?$", "", m.group(0)),
        text,
    )


# ── Convenience: review a set of notes with aggregated telemetry ───────────────

def gate_summary_claim_safety(summary: str, timeout_s: float = 1.0) -> str:
    """Apply claim-safety review to the visible summary text before serialization.

    This is the function wired into the concierge response assembly path
    (concierge.py: _gate_summary_claim_safety). It is the authoritative gate
    for the visible chat bubble / set-level response text.

    Fail-closed contract:
    - Reviewer error or timeout → return "" (omit; no unsafe prose shown).
    - Reviewer sanitizes one bad sentence → return safe remaining text.
    - Reviewer rejects entire summary → return "" (omit).
    - Empty input → returned unchanged.
    - Cards are NEVER affected — only the response text may be omitted/trimmed.

    Args:
        summary: The visible response/summary string to gate.
        timeout_s: Max time for the review (fail closed on timeout).

    Returns:
        Safe summary string (may be "" if original was fully rejected).
    """
    if not summary or not summary.strip():
        return summary
    result = review_summary(summary, frame=None, timeout_s=timeout_s)
    if result.rejected:
        logger.info(
            "claim_safety_reviewer.gate_summary: rejected reason=%s original=%r",
            result.rejection_reason, summary[:120],
        )
        return ""
    if result.sanitized:
        logger.info(
            "claim_safety_reviewer.gate_summary: sanitized original=%r safe=%r",
            summary[:80], result.summary[:80],
        )
        return result.summary
    return summary


def review_notes_set(
    notes: Dict[str, str],
    entity_name_by_place_id: Dict[str, str],
    frame: Any,
    timeout_s: float = _DEFAULT_REVIEWER_TIMEOUT_S,
) -> Tuple[Dict[str, NoteReviewResult], ReviewerTelemetry]:
    """Review a dict of place_id → note. Returns per-note results + telemetry.

    Args:
        notes: Mapping of place_id → note text (validated=True notes only).
        entity_name_by_place_id: Mapping of place_id → business name.
        frame: ExperienceFrame.
        timeout_s: Total budget for all reviews (shared across notes).

    Returns:
        (results_by_place_id, aggregated_telemetry).
    """
    t0 = time.monotonic()
    results: Dict[str, NoteReviewResult] = {}
    rejected = 0
    hidden = 0
    unsupported_claim = 0
    internal_leakage = 0
    unsupported_superlative = 0
    generic_note_hidden = 0
    timed_out = False

    for place_id, note in notes.items():
        remaining = timeout_s - (time.monotonic() - t0)
        if remaining <= 0:
            logger.warning("claim_safety_reviewer.review_notes_set: global_timeout reached")
            timed_out = True
            results[place_id] = NoteReviewResult(
                note="", passed=False, rejection_reason="reviewer_timeout", reviewer_ms=0
            )
            hidden += 1
            continue

        entity_name = entity_name_by_place_id.get(place_id, "")
        result = review_note(note, entity_name, frame, timeout_s=min(remaining, 0.5))
        results[place_id] = result

        if not result.passed:
            rejected += 1
            hidden += 1
            reason = result.rejection_reason
            if reason == "name_hours_inference":
                unsupported_claim += 1
            elif reason == "internal_label_leakage":
                internal_leakage += 1
            elif reason == "after_hours_crowd_overconfidence":
                unsupported_superlative += 1
            elif reason == "generic_occasion_sprawl":
                generic_note_hidden += 1

    total_ms = int((time.monotonic() - t0) * 1000)

    telemetry = ReviewerTelemetry(
        reviewer_used=True,
        reviewer_ms=total_ms,
        reviewer_timed_out=timed_out,
        reviewer_rejected_note_count=rejected,
        reviewer_hidden_note_count=hidden,
        reviewer_rejected_summary=False,
        reviewer_sanitized_summary=False,
        reviewer_unsupported_claim_count=unsupported_claim,
        reviewer_internal_leakage_count=internal_leakage,
        unsupported_superlative_count=unsupported_superlative,
        generic_note_hidden_count=generic_note_hidden,
        final_summary_visible=False,
        final_note_visible_count=len(notes) - hidden,
        fallback_note_visible_count=0,  # invariant
        deterministic_visible_count=0,  # invariant
    )

    return results, telemetry
