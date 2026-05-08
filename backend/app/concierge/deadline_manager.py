"""Request-scoped SLA deadline manager for AI Concierge search.

Enforces the amended v2 architecture contracts:
  target_ms   = 3000  (p50 goal)
  soft_ceiling = 4000  (if elapsed >= soft ceiling, skip note generation)
  hard_cutoff  = 6000  (absolute deadline; return best available response)
  first_card_limit = 6  (default first-response card count; range 5–7)

Latency Architecture v1 additions:
  SET_WRITER_LLM_MAX_S   = 1.5  (hard cap on set-writer LLM call timeout)
  SET_WRITER_MIN_BUDGET_MS = 1200  (minimum remaining ms to START set-writer)

Usage:
    deadline = RequestDeadline(t_start=t_pipeline_start)
    ...
    if deadline.is_past_soft_ceiling():
        skip_note_generation = True
    note_budget_s = deadline.budget_for_note_generation_s()
    set_writer_budget_s = deadline.budget_for_set_writer_s()
    ...
    cards = cards[:deadline.sla.first_card_limit]

Never raises. All timing values are in milliseconds unless noted.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional

# Allowed first-card range per v2 amendment §4 invariant 3.
FIRST_CARD_MIN = 5
FIRST_CARD_MAX = 7
FIRST_CARD_DEFAULT = 6

# Latency Architecture v1: set-writer budget policy.
# Cap on the set-writer LLM call timeout. Haiku at 384 max_tokens completes
# well under 1.5s in normal operation; capping prevents the writer from
# consuming the full remaining note-gen budget when budget appears large.
SET_WRITER_LLM_MAX_S: float = 1.5

# Minimum remaining budget (ms) required to START the set-writer at all.
# Ensures enough headroom for one capped LLM call + parse/validate/assembly.
SET_WRITER_MIN_BUDGET_MS: int = 1200


@dataclass
class SLAConfig:
    """Immutable SLA constants for one pipeline configuration."""
    target_ms: int = 3000
    soft_ceiling_ms: int = 4000
    hard_cutoff_ms: int = 6000
    first_card_limit: int = FIRST_CARD_DEFAULT
    first_card_min: int = FIRST_CARD_MIN
    first_card_max: int = FIRST_CARD_MAX


DEFAULT_SLA = SLAConfig()


class RequestDeadline:
    """Tracks elapsed time and remaining budget for a single concierge pipeline run.

    Instantiate once per pipeline run, passing the monotonic start time already
    captured before the pipeline began.
    """

    def __init__(
        self,
        sla: SLAConfig = DEFAULT_SLA,
        t_start: Optional[float] = None,
    ) -> None:
        self.sla = sla
        self._t_start: float = t_start if t_start is not None else time.monotonic()
        self._stage_starts: Dict[str, float] = {}
        self._stage_durations: Dict[str, int] = {}  # ms

    # ── Time queries ──────────────────────────────────────────────────────────

    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self._t_start) * 1000)

    def remaining_ms(self) -> int:
        """Remaining milliseconds before the hard cutoff. Never negative."""
        return max(0, self.sla.hard_cutoff_ms - self.elapsed_ms())

    def is_past_soft_ceiling(self) -> bool:
        """True when elapsed >= soft ceiling; note generation should be skipped."""
        return self.elapsed_ms() >= self.sla.soft_ceiling_ms

    def is_past_hard_cutoff(self) -> bool:
        """True when elapsed >= hard cutoff; pipeline must return immediately."""
        return self.elapsed_ms() >= self.sla.hard_cutoff_ms

    def budget_for_note_generation_s(self) -> float:
        """Seconds available for LLM note generation.

        Returns 0.0 when past the soft ceiling so callers can skip the step.
        Reserves 200 ms for assembly and logging overhead.
        """
        if self.is_past_soft_ceiling():
            return 0.0
        headroom_ms = 200
        available = max(0, self.remaining_ms() - headroom_ms)
        return available / 1000.0

    def budget_for_set_writer_s(self, max_cap_s: float = SET_WRITER_LLM_MAX_S) -> float:
        """Seconds available for the set-writer LLM call, capped at max_cap_s.

        Unlike budget_for_note_generation_s, this always caps at max_cap_s so
        the set-writer cannot consume the full remaining budget even when budget
        appears large. Returns 0.0 when past the soft ceiling.
        """
        if self.is_past_soft_ceiling():
            return 0.0
        headroom_ms = 300  # parse + validate + assembly overhead
        available = max(0, self.remaining_ms() - headroom_ms)
        return min(available / 1000.0, max_cap_s)

    def budget_for_enrichment_s(self, reserve_ms: int = 500) -> float:
        """Seconds available for non-critical enrichment after the critical path.

        Returns 0.0 when past the soft ceiling or when remaining budget is too
        small to safely run enrichment without starving note generation and
        response assembly.

        reserve_ms: headroom kept for note generation + assembly downstream.
        """
        if self.is_past_soft_ceiling():
            return 0.0
        available = max(0, self.remaining_ms() - reserve_ms)
        return available / 1000.0

    # ── Stage timing ─────────────────────────────────────────────────────────

    def stage_start(self, name: str) -> None:
        self._stage_starts[name] = time.monotonic()

    def stage_end(self, name: str) -> int:
        """Record stage end and return duration in ms."""
        t0 = self._stage_starts.get(name, self._t_start)
        ms = int((time.monotonic() - t0) * 1000)
        self._stage_durations[name] = ms
        return ms

    def stage_timings(self) -> Dict[str, int]:
        """Return a copy of all recorded stage durations."""
        return dict(self._stage_durations)


# ── Helpers ───────────────────────────────────────────────────────────────────

def clamp_first_card_limit(n: int, sla: SLAConfig = DEFAULT_SLA) -> int:
    """Clamp n to [first_card_min, first_card_max].

    Values outside 5–7 are clamped (not rejected) so callers never blow up.
    """
    return max(sla.first_card_min, min(sla.first_card_max, n))
