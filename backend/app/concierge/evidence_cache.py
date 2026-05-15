"""Evidence and note caching for AI Concierge credit ROI reliability.

Prevents Tavily/editorial credit waste when the LLM note writer times out or
produces no visible notes. Provides:

  - build_evidence_fingerprint: stable cache key for editorial evidence
  - should_run_editorial: selectivity gate using semantic frame signals
  - EvidenceAtomCache: TTL cache for accepted editorial evidence atoms
  - NoteCache: TTL cache for approved, validated concierge notes
  - CreditROITelemetry: structured ROI log fields per concierge search

Architecture invariants:
  - No SQL. In-memory only. Thread-safe.
  - Only accepted evidence atoms (passed entity matching) are cached.
  - Only approved, validated notes (passed quality gate) are cached.
  - Failed/timeout/generic/rating-only/rejected notes are never cached.
  - Evidence cache is keyed by semantic fingerprint, not raw query text.
  - Note cache is keyed by (place_id, evidence_fingerprint) to prevent
    cross-context bleed.
  - Google verification, card identity, and addability are never affected.
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Evidence fingerprinting ──────────────────────────────────────────────────

# Bump this salt when Tavily query strategy changes to invalidate stale cache.
_EVIDENCE_VERSION_SALT = "editorial_v1"


def _normalize_concept(s: str) -> str:
    """Lowercase, punctuation-stripped normalization for fingerprint components."""
    if not s:
        return ""
    return re.sub(r"[^a-z0-9 ]", "", s.lower().strip())[:32]


def build_evidence_fingerprint(
    destination: str,
    subtype_concepts: List[str],
    location_modifiers: List[str],
    geography_hints: List[str],
    normalized_soft_preferences: List[str],
) -> str:
    """Build a stable, deterministic fingerprint for editorial evidence reuse.

    Components:
      - destination (normalized)
      - primary subtype concept (first label, normalized)
      - location modifier (first modifier, normalized)
      - geography hint (first hint, normalized)
      - top-2 sorted normalized soft preferences
      - provider/version salt

    Conservative: collapses equivalent searches without collapsing
    different intents. "breweries" and "waterfront breweries" in Chicago
    produce different fingerprints because the geo modifier differs.

    Returns:
        16-char hex string suitable as a cache key.
    """
    dest_norm = _normalize_concept(destination)
    primary_concept = _normalize_concept(subtype_concepts[0]) if subtype_concepts else ""
    loc_mod = _normalize_concept(location_modifiers[0]) if location_modifiers else ""
    geo_hint = _normalize_concept(geography_hints[0]) if geography_hints else ""
    prefs = sorted(_normalize_concept(p) for p in normalized_soft_preferences[:2])
    prefs_str = ",".join(prefs)

    raw = f"{dest_norm}|{primary_concept}|{loc_mod}|{geo_hint}|{prefs_str}|{_EVIDENCE_VERSION_SALT}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


# ── Editorial selectivity gate ────────────────────────────────────────────────

# Normalized soft-preference labels (from frame_extractor) that indicate
# editorial evidence would add real value. These are semantic frame signals,
# not hardcoded query phrases.
_EDITORIAL_WORTHY_PREFS: frozenset = frozenset({
    "hidden_gem", "scenic_view", "view_or_geo", "romantic", "quiet",
    "lively", "locals_only", "off_beaten_path", "undiscovered",
    "upscale", "michelin_tier", "tasting_menu", "award_worthy",
    "luxury_for_less", "special_occasion", "boutique", "iconic",
})

# Location/geography modifier tokens that suggest editorial sources have
# useful neighborhood or setting context.
_EDITORIAL_WORTHY_GEO: frozenset = frozenset({
    "waterfront", "riverwalk", "riverfront", "lakefront", "rooftop",
    "skyline", "ocean", "scenic", "garden", "terrace", "pier",
    "harbor", "beachfront", "view", "panoramic", "overlook",
})

# Qualitative ranking/discovery markers in the raw query — "best X", "top X".
# The frame extractor deliberately strips these words from concept extraction
# (they are in _FILLER_WORDS), so they never surface in subtype_concepts,
# normalized_soft_preferences, or value_signals. Checking frame.literal_ask
# (an existing ExperienceFrame field) is the correct reuse point.
# Kept deliberately tight: only true superlatives that signal ranking/discovery intent.
_QUALITATIVE_RANKING_RE = re.compile(r"\b(?:best|top)\b", re.I)


# ── Subtype-concept canonicalization ─────────────────────────────────────────
# Used by the multi-concept editorial gate to prevent singular/plural or
# duplicate variants from being counted as truly distinct concepts.
# Rules are general suffix patterns, never hardcoded example pairs.

def _stem_word(w: str) -> str:
    """Strip common English plural suffixes from a single normalized word.

    Rules applied in order (most-specific first):
      'ies' → 'y'     (bakeries→bakery, breweries→brewery)
      'xes' → 'x'     (boxes→box)
      'ches' → 'ch'   (benches→bench, beaches→beach)
      'shes' → 'sh'   (dishes→dish)
      'sses' → 'ss'   (glasses→glass, masses→mass)
      trailing 's'     (bars→bar, sports→sport, restaurants→restaurant)
        — skipped when the word already ends in 'ss' (class, grass)
    """
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    for suffix, base in (("xes", "x"), ("ches", "ch"), ("shes", "sh"), ("sses", "ss")):
        if w.endswith(suffix) and len(w) > len(suffix) + 1:
            return w[: -len(suffix)] + base
    if w.endswith("s") and len(w) > 2 and not w.endswith("ss"):
        return w[:-1]
    return w


def _canonical_concept_label(label: str) -> str:
    """Return a case/whitespace/suffix-normalized form of a concept label.

    Applies word-level suffix stripping so that "sports bar" and "sport bars"
    and "sports bars" all canonicalize to the same string ("sport bar").
    """
    norm = re.sub(r"[^a-z0-9 ]", "", label.lower().strip())
    return " ".join(_stem_word(w) for w in norm.split() if w)


def _distinct_concept_count(subtype_concepts: List[Any]) -> int:
    """Return the number of genuinely distinct concepts in a subtype list.

    Extracts the 'label' attribute from each concept object, normalizes
    case/whitespace, singularizes common plural forms via generic suffix rules,
    and collapses duplicates that share the same canonical stem.  Only truly
    distinct canonical forms are counted.

    Example: [SubtypeConcept("sport"), SubtypeConcept("sports")] → 1
             [SubtypeConcept("bar"), SubtypeConcept("brewery")] → 2
    """
    seen: set = set()
    for concept in subtype_concepts:
        label = getattr(concept, "label", None)
        if not label:
            continue
        canonical = _canonical_concept_label(str(label))
        if canonical:
            seen.add(canonical)
    return len(seen)


def should_run_editorial(frame: Any) -> tuple:
    """Decide whether Tavily/editorial enrichment is likely to add value.

    Uses existing semantic frame signals — subtype_concepts, geography_hints,
    location_modifiers, normalized_soft_preferences, value_signals.

    Restrictive by default: runs Tavily only when an explicit editorial signal
    is present (preference, geo modifier, value signal, multi-concept, or
    best/top ranking intent). Plain subtype-only queries ("sports bars",
    "speakeasy bars") skip Tavily because Google + Yelp are sufficient without
    any qualifying signal.

    Args:
        frame: ExperienceFrame from frame_extractor (or None).

    Returns:
        (should_run: bool, reason: str)
    """
    if frame is None:
        return True, "no_frame_available"

    normalized_prefs = set(getattr(frame, "normalized_soft_preferences", []) or [])
    geo_hints = [h.lower() for h in (getattr(frame, "geography_hints", []) or [])]
    loc_mods = [m.lower() for m in (getattr(frame, "location_modifiers", []) or [])]
    subtype_concepts = getattr(frame, "subtype_concepts", []) or []
    value_signals = set(getattr(frame, "value_signals", []) or [])

    # Editorial-worthy soft preferences (discovery/vibe/occasion signals)
    matched_prefs = normalized_prefs & _EDITORIAL_WORTHY_PREFS
    if matched_prefs:
        return True, f"editorial_worthy_pref:{','.join(sorted(matched_prefs)[:2])}"

    # Editorial-worthy geo/setting modifiers
    all_geo = set(geo_hints + loc_mods)
    geo_editorial = all_geo & _EDITORIAL_WORTHY_GEO
    if geo_editorial:
        return True, f"editorial_worthy_geo:{','.join(sorted(geo_editorial)[:2])}"

    # Value/luxury signals suggest editorial sources have useful context.
    # Includes actual labels produced by _extract_value_signals() ("luxury",
    # "budget", "value_for_money") plus any legacy/future labels.
    if value_signals & {"luxury", "budget", "value_for_money", "luxury_for_less", "splurge", "michelin"}:
        return True, "editorial_worthy_value_signal"

    # Multi-concept queries benefit from editorial disambiguation.
    # Use canonical distinct count to avoid counting singular/plural or duplicate
    # variants (e.g. [sport, sports], [bar, bars]) as two separate concepts.
    if _distinct_concept_count(subtype_concepts) >= 2:
        return True, "multi_concept_query"

    # Qualitative ranking/discovery intent — "best X", "top X" in the raw query.
    # frame_extractor strips "best"/"top" from concept extraction (_FILLER_WORDS),
    # so they never appear in subtype_concepts or normalized_soft_preferences.
    # Reusing frame.literal_ask (existing ExperienceFrame field) is the correct
    # signal reuse point without adding a new editorial-intent subsystem.
    literal_ask = getattr(frame, "literal_ask", "") or ""
    if literal_ask and _QUALITATIVE_RANKING_RE.search(literal_ask):
        return True, "qualitative_ranking_intent"

    # No qualifying editorial signal — Google/Yelp is sufficient. A plain
    # subtype-only query ("sports bars", "speakeasy bars", "cocktail bars")
    # without a preference, geo, value, multi-concept, or best/top signal
    # does not warrant Tavily. Credits are spent only when there is a signal
    # that editorial sources can actually enrich.
    return False, "low_editorial_value_simple_category"


def should_skip_writer_no_evidence(
    accepted_editorial_evidence_count: int,
    cached_notes: Dict[str, Any],
) -> bool:
    """Return True when the set-level LLM note writer should be skipped.

    Retained for backward compatibility with existing tests.
    Production code uses make_note_decision() instead.
    """
    return accepted_editorial_evidence_count == 0 and not cached_notes


# ── Shared note/evidence decision ─────────────────────────────────────────────


@dataclass
class NoteDecision:
    """Single shared decision for all optional note/evidence paths in one pipeline turn.

    Computed once from frame signals and actual editorial/cache outcomes after
    Step 5.56 (editorial enrichment) and the note cache lookup.

    This is the single source of truth for optional Tavily/editorial/LLM note
    work in semantic retrieval. No note path may run without approval here.
    """

    should_run_editorial_enrichment: bool
    editorial_enrichment_skip_reason: Optional[str]

    should_run_set_writer: bool
    set_writer_skip_reason: Optional[str]

    should_run_legacy_batched_reasoning: bool
    legacy_batched_reasoning_skip_reason: Optional[str]

    has_cached_approved_notes: bool
    has_accepted_editorial_evidence: bool
    is_plain_category_query: bool
    accepted_editorial_evidence_count: int = 0


def make_note_decision(
    frame: Any,
    cached_notes: Dict[str, Any],
    accepted_editorial_evidence_count: int,
) -> "NoteDecision":
    """Compute the shared note/evidence decision for one pipeline turn.

    Called after editorial enrichment (Step 5.56) when we know:
    - The frame's editorial intent (via should_run_editorial)
    - The actual accepted editorial evidence count
    - The cached approved notes for this fingerprint

    LLM note paths (set_level_writer, batched_reason_builder) run only when
    there is evidence grounding: accepted editorial atoms from Tavily/Serper
    OR pre-approved cached notes. Without either, notes would be generic or
    empty, fail the quality gate, and waste credits with no visible output.

    Args:
        frame: ExperienceFrame (may be None).
        cached_notes: Dict of place_id -> note for pre-approved cached notes.
        accepted_editorial_evidence_count: Total accepted atoms from Step 5.56.

    Returns:
        NoteDecision with should_run_* flags and skip reasons.
    """
    editorial_should_run, editorial_reason = should_run_editorial(frame)

    has_cached_notes = bool(cached_notes)
    has_editorial_evidence = accepted_editorial_evidence_count > 0

    # LLM note paths run only when there is evidence grounding.
    # Without either accepted atoms or cached notes, writers produce generic
    # or empty notes that fail the quality gate — spending credits for no output.
    should_run_notes = has_editorial_evidence or has_cached_notes

    note_skip_reason: Optional[str] = (
        "no_editorial_evidence_no_cached_notes" if not should_run_notes else None
    )

    return NoteDecision(
        should_run_editorial_enrichment=editorial_should_run,
        editorial_enrichment_skip_reason=None if editorial_should_run else editorial_reason,
        should_run_set_writer=should_run_notes,
        set_writer_skip_reason=note_skip_reason,
        should_run_legacy_batched_reasoning=should_run_notes,
        legacy_batched_reasoning_skip_reason=note_skip_reason,
        has_cached_approved_notes=has_cached_notes,
        has_accepted_editorial_evidence=has_editorial_evidence,
        is_plain_category_query=not editorial_should_run,
        accepted_editorial_evidence_count=accepted_editorial_evidence_count,
    )


# ── In-memory evidence atom cache ────────────────────────────────────────────


@dataclass
class EvidenceCacheEntry:
    """One cached editorial evidence result for a query fingerprint."""

    atoms_by_place_id: Dict[str, List[Any]]  # place_id → List[EnrichmentAtom]
    accepted_count: int
    expires_at: float


class EvidenceAtomCache:
    """Thread-safe in-memory TTL cache for accepted editorial evidence atoms.

    Keyed by evidence_fingerprint. Stores only accepted atoms (those that
    passed entity matching and confidence thresholds in editorial_enrichment).

    Rejected/low-confidence atoms are never cached. Evidence is cached even
    when the LLM note writer times out — so the next matching search can
    reuse atoms without re-calling Tavily.
    """

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._ttl = ttl_seconds
        self._store: Dict[str, EvidenceCacheEntry] = {}
        self._lock = threading.Lock()

    def get(self, fingerprint: str) -> Optional[EvidenceCacheEntry]:
        """Return a fresh cache entry, or None if missing/stale."""
        with self._lock:
            entry = self._store.get(fingerprint)
            if entry is None:
                return None
            if time.monotonic() > entry.expires_at:
                del self._store[fingerprint]
                return None
            return entry

    def set(
        self,
        fingerprint: str,
        atoms_by_place_id: Dict[str, List[Any]],
        accepted_count: int,
    ) -> None:
        """Store accepted evidence atoms under a fingerprint."""
        with self._lock:
            self._store[fingerprint] = EvidenceCacheEntry(
                atoms_by_place_id={k: list(v) for k, v in atoms_by_place_id.items()},
                accepted_count=accepted_count,
                expires_at=time.monotonic() + self._ttl,
            )

    def size(self) -> int:
        """Return number of cached entries (for testing/monitoring)."""
        with self._lock:
            return len(self._store)


# Module-level singleton — shared across requests in a single worker process.
_EVIDENCE_ATOM_CACHE = EvidenceAtomCache(ttl_seconds=3600)


# ── In-memory note cache ──────────────────────────────────────────────────────


@dataclass
class NoteCacheEntry:
    """One approved, validated concierge note for a (place_id, fingerprint) pair."""

    note: str
    source: str
    evidence_fingerprint: str
    expires_at: float


class NoteCache:
    """Thread-safe in-memory TTL cache for approved, validated concierge notes.

    Keyed by (place_id, evidence_fingerprint). Only stores notes that:
      - Passed the quality gate (validated=True in SetWriterResult)
      - Are non-empty strings
      - Were produced by an evidence-grounded writer

    Never stores: failed, timeout, generic, rating-only, rejected, or
    unvalidated notes. The (place_id, evidence_fingerprint) compound key
    prevents notes from bleeding across unrelated search contexts.
    """

    def __init__(self, ttl_seconds: int = 7200) -> None:
        self._ttl = ttl_seconds
        self._store: Dict[str, NoteCacheEntry] = {}
        self._lock = threading.Lock()

    def _key(self, place_id: str, fingerprint: str) -> str:
        return f"{place_id}:{fingerprint}"

    def get(self, place_id: str, fingerprint: str) -> Optional[NoteCacheEntry]:
        """Return a fresh cached note, or None if missing/stale."""
        with self._lock:
            key = self._key(place_id, fingerprint)
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry.expires_at:
                del self._store[key]
                return None
            return entry

    def set(
        self,
        place_id: str,
        fingerprint: str,
        note: str,
        source: str,
    ) -> None:
        """Store an approved, validated note. Silently ignores empty notes."""
        if not note or not note.strip():
            return
        with self._lock:
            key = self._key(place_id, fingerprint)
            self._store[key] = NoteCacheEntry(
                note=note,
                source=source,
                evidence_fingerprint=fingerprint,
                expires_at=time.monotonic() + self._ttl,
            )

    def size(self) -> int:
        """Return number of cached entries (for testing/monitoring)."""
        with self._lock:
            return len(self._store)


# Module-level singleton
_NOTE_CACHE = NoteCache(ttl_seconds=7200)


# ── Durable (Supabase) cache layer ────────────────────────────────────────────

_DURABLE_EVIDENCE_TTL_DAYS: int = 14
_DURABLE_NOTE_TTL_DAYS: int = 30


def _atom_to_dict(atom: Any) -> Dict[str, Any]:
    """Serialize an EnrichmentAtom to a JSON-safe dict for Supabase storage."""
    return {
        "source_provider": getattr(atom, "source_provider", ""),
        "evidence_type": getattr(atom, "evidence_type", ""),
        "normalized_value": getattr(atom, "normalized_value", ""),
        "confidence": float(getattr(atom, "confidence", 0.0)),
        "provenance": dict(getattr(atom, "provenance", {}) or {}),
        "allowed_into_writer": bool(getattr(atom, "allowed_into_writer", False)),
        "conflict_status": getattr(atom, "conflict_status", "ok"),
    }


def _atom_from_dict(d: Dict[str, Any]) -> Any:
    """Deserialize an EnrichmentAtom from a JSON dict (Supabase row field)."""
    from app.concierge.cross_source_enrichment import EnrichmentAtom
    return EnrichmentAtom(
        source_provider=d.get("source_provider", ""),
        evidence_type=d.get("evidence_type", ""),
        normalized_value=d.get("normalized_value", ""),
        confidence=float(d.get("confidence", 0.0)),
        provenance=dict(d.get("provenance", {}) or {}),
        allowed_into_writer=bool(d.get("allowed_into_writer", False)),
        conflict_status=d.get("conflict_status", "ok"),
    )


def _parse_iso_datetime(s: str) -> Optional[datetime]:
    """Parse ISO datetime string to aware datetime, returning None on error."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


class SupabaseEvidenceCache:
    """Supabase-backed durable evidence atom cache (second read/write layer).

    Used after a miss on the in-memory EvidenceAtomCache hot layer.
    Serializes EnrichmentAtom objects to/from JSONB for cross-restart durability.
    All errors are non-fatal: exceptions are logged and the caller falls through
    to the live Tavily path.
    """

    def __init__(self, ttl_days: int = _DURABLE_EVIDENCE_TTL_DAYS) -> None:
        self._ttl_days = ttl_days
        self._version_salt = _EVIDENCE_VERSION_SALT

    def get(self, fingerprint: str) -> Optional[EvidenceCacheEntry]:
        """Return a fresh entry from Supabase, or None on miss/expiry/error."""
        try:
            from app.db.client import get_supabase
            db = get_supabase()
            result = (
                db.table("concierge_evidence_cache")
                .select("atoms_by_place_id,accepted_count,expires_at")
                .eq("evidence_fingerprint", fingerprint)
                .eq("version_salt", self._version_salt)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if not rows:
                return None
            row = rows[0]
            # Client-side expiry (works with both real Supabase and mock)
            expires_dt = _parse_iso_datetime(row.get("expires_at", ""))
            if expires_dt is not None and expires_dt <= datetime.now(timezone.utc):
                return None
            atoms_raw = row.get("atoms_by_place_id") or {}
            atoms_by_place_id: Dict[str, List[Any]] = {}
            for pid, atom_list in atoms_raw.items():
                try:
                    atoms_by_place_id[pid] = [
                        _atom_from_dict(d) for d in (atom_list or [])
                    ]
                except Exception:
                    atoms_by_place_id[pid] = []
            return EvidenceCacheEntry(
                atoms_by_place_id=atoms_by_place_id,
                accepted_count=int(row.get("accepted_count", 0)),
                expires_at=time.monotonic() + 3600,
            )
        except Exception as exc:
            logger.debug(
                "durable_evidence_cache: get_failed fingerprint=%s error=%s",
                fingerprint, exc,
            )
            return None

    def set(
        self,
        fingerprint: str,
        atoms_by_place_id: Dict[str, List[Any]],
        accepted_count: int,
        destination: str = "",
    ) -> bool:
        """Persist accepted evidence atoms to Supabase. Returns True on success."""
        try:
            from app.db.client import get_supabase
            db = get_supabase()
            expires_at = (
                datetime.now(timezone.utc) + timedelta(days=self._ttl_days)
            ).isoformat()
            atoms_serialized = {
                pid: [_atom_to_dict(a) for a in atoms]
                for pid, atoms in atoms_by_place_id.items()
            }
            db.table("concierge_evidence_cache").upsert(
                {
                    "evidence_fingerprint": fingerprint,
                    "destination": destination or "",
                    "normalized_context": {},
                    "atoms_by_place_id": atoms_serialized,
                    "accepted_count": accepted_count,
                    "version_salt": self._version_salt,
                    "expires_at": expires_at,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="evidence_fingerprint,version_salt",
            ).execute()
            return True
        except Exception as exc:
            logger.debug(
                "durable_evidence_cache: set_failed fingerprint=%s error=%s",
                fingerprint, exc,
            )
            return False


class SupabaseNoteCache:
    """Supabase-backed durable note cache (second read/write layer).

    Used after a miss on the in-memory NoteCache hot layer.
    Only stores notes that passed the quality gate (validated=True).
    Generic, rating-only, rejected, template, or empty notes are never stored.
    All errors are non-fatal: exceptions are logged and the caller falls through.
    """

    def __init__(self, ttl_days: int = _DURABLE_NOTE_TTL_DAYS) -> None:
        self._ttl_days = ttl_days
        self._version_salt = _EVIDENCE_VERSION_SALT

    def get(self, place_id: str, fingerprint: str) -> Optional[NoteCacheEntry]:
        """Return a fresh note from Supabase, or None on miss/expiry/error."""
        try:
            from app.db.client import get_supabase
            db = get_supabase()
            result = (
                db.table("concierge_note_cache")
                .select("note,source,expires_at")
                .eq("provider_place_id", place_id)
                .eq("evidence_fingerprint", fingerprint)
                .eq("version_salt", self._version_salt)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if not rows:
                return None
            row = rows[0]
            expires_dt = _parse_iso_datetime(row.get("expires_at", ""))
            if expires_dt is not None and expires_dt <= datetime.now(timezone.utc):
                return None
            note = row.get("note", "")
            if not note or not note.strip():
                return None
            return NoteCacheEntry(
                note=note,
                source=row.get("source", ""),
                evidence_fingerprint=fingerprint,
                expires_at=time.monotonic() + 7200,
            )
        except Exception as exc:
            logger.debug(
                "durable_note_cache: get_failed place_id=%s error=%s",
                place_id, exc,
            )
            return None

    def set(
        self,
        place_id: str,
        fingerprint: str,
        note: str,
        source: str,
    ) -> bool:
        """Persist an approved note to Supabase. Returns True on success."""
        if not note or not note.strip():
            return False
        try:
            from app.db.client import get_supabase
            db = get_supabase()
            expires_at = (
                datetime.now(timezone.utc) + timedelta(days=self._ttl_days)
            ).isoformat()
            db.table("concierge_note_cache").upsert(
                {
                    "evidence_fingerprint": fingerprint,
                    "provider_place_id": place_id,
                    "note": note,
                    "source": source,
                    "version_salt": self._version_salt,
                    "expires_at": expires_at,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="provider_place_id,evidence_fingerprint,version_salt",
            ).execute()
            return True
        except Exception as exc:
            logger.debug(
                "durable_note_cache: set_failed place_id=%s error=%s",
                place_id, exc,
            )
            return False


# Module-level durable singletons — shared across requests in a single worker.
_SUPABASE_EVIDENCE_CACHE = SupabaseEvidenceCache()
_SUPABASE_NOTE_CACHE = SupabaseNoteCache()


# ── Credit ROI telemetry ──────────────────────────────────────────────────────


@dataclass
class CreditROITelemetry:
    """Structured telemetry for one concierge search credit ROI audit.

    Emitted as a separate log line after each semantic retrieval turn so
    credit waste (Tavily called but no visible notes) is immediately visible.

    All fields default to safe sentinel values so incomplete pipelines
    still produce a valid log line.
    """

    # Tavily/editorial enrichment
    tavily_attempted: bool = False
    tavily_skipped_reason: Optional[str] = None

    # Evidence cache
    evidence_cache_hit: bool = False
    evidence_cache_write: bool = False
    accepted_editorial_evidence_count: int = 0

    # Note cache
    note_cache_hit_count: int = 0
    note_cache_write_count: int = 0

    # LLM note writer
    note_writer_attempted: bool = False
    note_writer_timed_out: bool = False

    # Output counts
    approved_note_count: int = 0
    visible_note_count: int = 0
    omitted_note_reasons: Dict[str, int] = field(default_factory=dict)

    # Credit waste signal: Tavily ran but produced no visible notes
    credits_spent_but_no_visible_notes: bool = False

    # Durable (Supabase) cache fields — v2 addition
    durable_evidence_cache_hit: bool = False
    durable_evidence_cache_write: bool = False
    durable_note_cache_hit_count: int = 0
    durable_note_cache_write_count: int = 0
    durable_cache_error_count: int = 0

    # Async late-note storage (0 until async completion is implemented)
    async_late_note_stored_count: int = 0

    # Control-plane decision telemetry (v3 — control-plane fix)
    set_writer_skipped_reason: Optional[str] = None
    legacy_batched_reason_attempted: bool = False
    legacy_batched_reason_skipped_reason: Optional[str] = None
    final_card_count_before_notes: int = 0
    final_card_count_after_notes: int = 0
    card_count_collapsed_due_to_notes: bool = False  # invariant: always False

    def record_omission(self, reason: str) -> None:
        """Increment the omitted-note reason counter."""
        self.omitted_note_reasons[reason] = self.omitted_note_reasons.get(reason, 0) + 1

    def as_log_dict(self) -> Dict[str, Any]:
        """Serialise to a flat dict for structured logging."""
        return {
            "tavily_attempted": self.tavily_attempted,
            "tavily_skipped_reason": self.tavily_skipped_reason,
            "evidence_cache_hit": self.evidence_cache_hit,
            "evidence_cache_write": self.evidence_cache_write,
            "accepted_editorial_evidence_count": self.accepted_editorial_evidence_count,
            "note_cache_hit_count": self.note_cache_hit_count,
            "note_cache_write_count": self.note_cache_write_count,
            "note_writer_attempted": self.note_writer_attempted,
            "note_writer_timed_out": self.note_writer_timed_out,
            "approved_note_count": self.approved_note_count,
            "visible_note_count": self.visible_note_count,
            "omitted_note_reasons": self.omitted_note_reasons,
            "credits_spent_but_no_visible_notes": self.credits_spent_but_no_visible_notes,
            "async_late_note_stored_count": self.async_late_note_stored_count,
            # Durable cache fields (v2)
            "durable_evidence_cache_hit": self.durable_evidence_cache_hit,
            "durable_evidence_cache_write": self.durable_evidence_cache_write,
            "durable_note_cache_hit_count": self.durable_note_cache_hit_count,
            "durable_note_cache_write_count": self.durable_note_cache_write_count,
            "durable_cache_error_count": self.durable_cache_error_count,
            # Control-plane decision fields (v3)
            "set_writer_skipped_reason": self.set_writer_skipped_reason,
            "legacy_batched_reason_attempted": self.legacy_batched_reason_attempted,
            "legacy_batched_reason_skipped_reason": self.legacy_batched_reason_skipped_reason,
            "final_card_count_before_notes": self.final_card_count_before_notes,
            "final_card_count_after_notes": self.final_card_count_after_notes,
            "card_count_collapsed_due_to_notes": self.card_count_collapsed_due_to_notes,
        }
