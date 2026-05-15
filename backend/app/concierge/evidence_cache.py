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
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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


def should_run_editorial(frame: Any) -> tuple:
    """Decide whether Tavily/editorial enrichment is likely to add value.

    Uses existing semantic frame signals — subtype_concepts, geography_hints,
    location_modifiers, normalized_soft_preferences, value_signals.

    Permissive rather than restrictive: when uncertain, allows Tavily.
    Skips only for clearly low-editorial-value category searches where
    Google + Yelp are sufficient.

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

    # Value/luxury signals suggest editorial sources have useful context
    if value_signals & {"luxury_for_less", "splurge", "michelin"}:
        return True, "editorial_worthy_value_signal"

    # Multi-concept queries benefit from editorial disambiguation
    if len(subtype_concepts) >= 2:
        return True, "multi_concept_query"

    # Simple category search with no discovery modifiers — Google/Yelp is
    # sufficient and Tavily adds minimal marginal value.
    if not geo_hints and not loc_mods and not normalized_prefs:
        return False, "low_editorial_value_simple_category"

    # Default: allow editorial when any signals are present
    return True, "default_allow"


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

    # Async late-note storage (0 until async completion is implemented)
    async_late_note_stored_count: int = 0

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
            "note_cache_write_count": self.note_cache_write_count,
            "async_late_note_stored_count": self.async_late_note_stored_count,
        }
