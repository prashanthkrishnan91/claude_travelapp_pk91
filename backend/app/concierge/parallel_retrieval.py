"""Parallel retrieval layer — PR #258.

Implements the critical vs non-critical path split from v2 amendment §5.

Critical path (blocking — must complete before cards can be returned):
  Google Text Search fanout with deadline-bounded per-call timeout.

Non-critical path (skippable — never blocks verified card return):
  Google Place Details enrichment for top-N ranked cards.
  Skipped entirely when remaining deadline budget is insufficient.
  Enrichment is evidence only — it cannot change card identity or addable status.

Architecture invariants enforced here:
  - Only Google can mint addable cards (critical path).
  - Non-critical enrichment is evidence for notes/reasoning only.
  - Slow or skipped enrichment must not delay first verified card response.
  - Provider timeout and skip counts are recorded for telemetry.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Minimum remaining-budget threshold below which enrichment is skipped.
# This protects headroom for note generation + response assembly downstream.
ENRICHMENT_BUDGET_RESERVE_MS: int = 500

# Minimum per-card timeout to make enrichment worth attempting.
ENRICHMENT_MIN_TIMEOUT_S: float = 0.5


@dataclass
class CriticalPathResult:
    """Outcome of the deadline-bounded Google Text Search fanout."""

    provider_results: List[Any]   # List[ProviderQueryResult]
    elapsed_ms: int
    timeout_count: int            # queries that errored or were skipped
    success: bool                 # True when at least one query returned places


@dataclass
class NonCriticalEnrichmentResult:
    """Outcome of the deadline-gated Google Place Details enrichment."""

    enrichment_map: Dict[str, Any]  # place_id → PlaceDetailsResult
    elapsed_ms: int
    used_count: int               # cards with returned enrichment data
    skipped_count: int            # cards not attempted (budget) or failed
    skip_reason: Optional[str]    # None | "budget_exhausted" | "past_soft_ceiling" | "no_entities"


@dataclass
class ParallelRetrievalResult:
    """Combined critical + non-critical results with PR #258 telemetry fields."""

    critical: CriticalPathResult
    non_critical: NonCriticalEnrichmentResult

    # PR #258 telemetry requirements
    critical_path_ms: int
    non_critical_enrichment_ms: int
    provider_fanout_ms: int
    provider_timeout_counts: int
    provider_skipped_due_to_budget_counts: int
    google_critical_success: bool
    google_critical_candidate_count: int       # raw places from successful queries
    remaining_budget_before_enrichment_ms: int
    non_critical_enrichment_used_count: int
    non_critical_enrichment_skipped_count: int


def run_critical_google_fanout(
    queries: List[str],
    api_key: str,
    deadline: Any,             # RequestDeadline
    timeout: float = 5.0,
) -> CriticalPathResult:
    """Execute Google Text Search queries with deadline-bounded timeout.

    Per-call HTTP timeout = min(timeout, remaining_deadline_s - 0.2s).
    Total fanout wait   = min(effective_timeout + 0.5s, remaining_s - 0.1s).

    The total fanout wait is always <= remaining deadline budget, preventing
    the legacy execute_fanout `timeout + 2.0` buffer from overrunning the SLA.
    Returns an empty failure result immediately when remaining budget < 0.5 s.
    """
    from app.concierge.provider_executor import execute_fanout

    t0 = time.monotonic()

    remaining_s = deadline.remaining_ms() / 1000.0
    effective_timeout = min(timeout, max(ENRICHMENT_MIN_TIMEOUT_S, remaining_s - 0.2))
    # Total as_completed wait: per-call timeout + 0.5s thread overhead, capped
    # at remaining_s - 0.1s so the fanout never overruns the deadline budget.
    fanout_timeout = min(effective_timeout + 0.5, max(effective_timeout, remaining_s - 0.1))

    if remaining_s < ENRICHMENT_MIN_TIMEOUT_S:
        logger.warning(
            "parallel_retrieval: critical_fanout_skipped_budget_exhausted remaining_ms=%d",
            deadline.remaining_ms(),
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return CriticalPathResult(
            provider_results=[],
            elapsed_ms=elapsed_ms,
            timeout_count=len(queries),
            success=False,
        )

    provider_results = execute_fanout(
        queries, api_key=api_key, timeout=effective_timeout, fanout_timeout=fanout_timeout
    )
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    timeout_count = sum(1 for r in provider_results if r.error is not None)
    success = any(r.succeeded for r in provider_results)

    logger.info(
        "parallel_retrieval: critical_fanout queries=%d timeout_count=%d "
        "success=%s elapsed_ms=%d effective_timeout=%.2fs",
        len(queries), timeout_count, success, elapsed_ms, effective_timeout,
    )
    return CriticalPathResult(
        provider_results=provider_results,
        elapsed_ms=elapsed_ms,
        timeout_count=timeout_count,
        success=success,
    )


def run_non_critical_enrichment(
    entities: List[Any],
    api_key: str,
    deadline: Any,             # RequestDeadline
    budget_n: int = 4,
) -> NonCriticalEnrichmentResult:
    """Fetch Google Place Details for top-N entities, gated by remaining budget.

    Skipped entirely when deadline.budget_for_enrichment_s() == 0.0.
    Never delays returning verified critical-path cards.
    Enrichment data is evidence only — card identity and addable status are
    determined solely by the critical Google path.
    """
    from app.concierge.place_details_provider import enrich_top_cards

    t0 = time.monotonic()

    if not entities:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return NonCriticalEnrichmentResult(
            enrichment_map={},
            elapsed_ms=elapsed_ms,
            used_count=0,
            skipped_count=0,
            skip_reason="no_entities",
        )

    enrichment_budget_s = deadline.budget_for_enrichment_s()

    if enrichment_budget_s <= 0.0:
        skip_reason = (
            "past_soft_ceiling"
            if deadline.is_past_soft_ceiling()
            else "budget_exhausted"
        )
        logger.info(
            "parallel_retrieval: non_critical_skipped reason=%s remaining_ms=%d",
            skip_reason, deadline.remaining_ms(),
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return NonCriticalEnrichmentResult(
            enrichment_map={},
            elapsed_ms=elapsed_ms,
            used_count=0,
            skipped_count=min(budget_n, len(entities)),
            skip_reason=skip_reason,
        )

    # Spread the budget evenly across the batch; never below minimum.
    per_card_timeout = max(
        ENRICHMENT_MIN_TIMEOUT_S,
        enrichment_budget_s / max(1, min(budget_n, len(entities))),
    )

    try:
        enrichment_map = enrich_top_cards(
            entities,
            api_key=api_key,
            budget_n=budget_n,
            timeout=per_card_timeout,
        )
    except Exception as exc:
        logger.debug("parallel_retrieval: enrichment_error error=%s", exc)
        enrichment_map = {}

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    used_count = len(enrichment_map)
    attempted_count = min(budget_n, len(entities))
    failed_count = max(0, attempted_count - used_count)

    logger.info(
        "parallel_retrieval: non_critical_enrichment used=%d failed=%d "
        "elapsed_ms=%d budget_s=%.2f",
        used_count, failed_count, elapsed_ms, enrichment_budget_s,
    )
    return NonCriticalEnrichmentResult(
        enrichment_map=enrichment_map,
        elapsed_ms=elapsed_ms,
        used_count=used_count,
        skipped_count=failed_count,
        skip_reason=None,
    )
