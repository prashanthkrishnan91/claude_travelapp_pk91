"""Request-scoped SLA deadline manager for AI Concierge search.

Enforces the amended v2 architecture contracts:
  target_ms   = 3000  (p50 goal)
  soft_ceiling = 4000  (if elapsed >= soft ceiling, skip note generation)
  hard_cutoff  = 6000  (absolute deadline; return best available response)
  first_card_limit = 6  (default first-response card count; range 5–7)

Usage:
    deadline = RequestDeadline(t_start=t_pipeline_start)
    ...
    if deadline.is_past_soft_ceiling():
        skip_note_generation = True
    note_budget_s = deadline.budget_for_note_generation_s()
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
