"""PR #258 — Parallel retrieval + critical/non-critical path split tests.

Tests:
1. Slow non-critical enrichment is skipped when past soft ceiling.
2. Google critical retrieval/verification required for addable cards.
3. Non-Google enrichment cannot mint addable cards.
4. Provider fanout respects remaining RequestDeadline budget.
5. Budget exhausted before enrichment → enrichment is skipped entirely.
6. Budget available → enrichment attaches evidence without changing card identity.
7. First response still caps at default 6 cards.
8. fallback_note_visible_count remains 0.
9. Telemetry emits provider timeout/skip counts and critical-path timing.
10. deadline.budget_for_enrichment_s() returns 0.0 past soft ceiling.
"""

from __future__ import annotations

import os
import sys
import time
import types
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Stub app.core.deps so router/contract imports don't fail.
_deps = sys.modules.get("app.core.deps") or types.ModuleType("app.core.deps")
sys.modules.setdefault("app.core.deps", _deps)
setattr(_deps, "DB", object)
setattr(_deps, "CurrentUserID", object)

# ── Imports under test ────────────────────────────────────────────────────────
from app.concierge.deadline_manager import (
    DEFAULT_SLA,
    RequestDeadline,
    SLAConfig,
)
from app.concierge.parallel_retrieval import (
    ENRICHMENT_BUDGET_RESERVE_MS,
    ENRICHMENT_MIN_TIMEOUT_S,
    CriticalPathResult,
    NonCriticalEnrichmentResult,
    ParallelRetrievalResult,
    run_critical_google_fanout,
    run_non_critical_enrichment,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_deadline(elapsed_ms: int = 0) -> RequestDeadline:
    """Return a RequestDeadline that started `elapsed_ms` ago."""
    t_start = time.monotonic() - elapsed_ms / 1000.0
    return RequestDeadline(sla=DEFAULT_SLA, t_start=t_start)


def _make_provider_result(query: str = "q", n_places: int = 3, error: Optional[str] = None):
    """Return a mock ProviderQueryResult."""
    r = MagicMock()
    r.query = query
    r.places = [{"id": f"place_{i}"} for i in range(n_places)]
    r.latency_ms = 200
    r.error = error
    r.succeeded = error is None
    return r


def _make_place_entity(place_id: str = "gp_abc"):
    """Return a minimal mock PlaceEntity."""
    e = MagicMock()
    e.place_id = place_id
    e.name = f"Place {place_id}"
    return e


def _make_place_details_result(place_id: str):
    """Return a minimal mock PlaceDetailsResult."""
    d = MagicMock()
    d.place_id = place_id
    d.editorial_summary = "Great place."
    d.review_snippets = ["Nice vibe."]
    d.has_differentiating_content.return_value = True
    return d


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Slow non-critical enrichment is skipped past soft ceiling
# ─────────────────────────────────────────────────────────────────────────────

class TestNonCriticalSkippedPastSoftCeiling:
    def test_enrichment_skipped_when_past_soft_ceiling(self):
        # Simulate: pipeline has already consumed soft_ceiling_ms.
        deadline = _make_deadline(elapsed_ms=DEFAULT_SLA.soft_ceiling_ms + 100)
        assert deadline.is_past_soft_ceiling()

        entities = [_make_place_entity("p1"), _make_place_entity("p2")]
        with patch("app.concierge.place_details_provider.enrich_top_cards") as mock_enrich:
            result = run_non_critical_enrichment(entities, api_key="key", deadline=deadline)

        mock_enrich.assert_not_called()
        assert result.skip_reason == "past_soft_ceiling"
        assert result.enrichment_map == {}
        assert result.used_count == 0
        assert result.skipped_count == min(4, len(entities))

    def test_enrichment_skipped_budget_exhausted(self):
        # Use a custom SLA where soft_ceiling is high enough that we can be
        # below it but still have remaining < reserve_ms.
        # soft_ceiling=5800ms, hard_cutoff=6000ms, reserve=500ms.
        # At elapsed=5600ms: remaining=400ms < reserve → budget_exhausted, not past soft ceiling.
        custom_sla = SLAConfig(soft_ceiling_ms=5800, hard_cutoff_ms=6000)
        t_start = time.monotonic() - 5.6  # 5600ms ago
        deadline = RequestDeadline(sla=custom_sla, t_start=t_start)
        assert not deadline.is_past_soft_ceiling()
        assert deadline.budget_for_enrichment_s() == 0.0

        entities = [_make_place_entity("p1")]
        with patch("app.concierge.place_details_provider.enrich_top_cards") as mock_enrich:
            result = run_non_critical_enrichment(entities, api_key="key", deadline=deadline)

        mock_enrich.assert_not_called()
        assert result.skip_reason == "budget_exhausted"
        assert result.enrichment_map == {}

    def test_verified_cards_still_return_after_enrichment_skipped(self):
        # Conceptual test: enrichment skip must not prevent card assembly.
        # The pipeline assembles cards from critical path data only.
        # Here we verify the skip result has empty map so callers use no enrichment.
        deadline = _make_deadline(elapsed_ms=DEFAULT_SLA.soft_ceiling_ms + 500)
        entities = [_make_place_entity("p1"), _make_place_entity("p2")]

        result = run_non_critical_enrichment(entities, api_key="key", deadline=deadline)

        assert result.enrichment_map == {}
        assert result.skip_reason is not None
        # elapsed_ms should be tiny — enrichment path exited immediately.
        assert result.elapsed_ms < 100


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Google critical retrieval required for addable cards
# ─────────────────────────────────────────────────────────────────────────────

class TestCriticalGoogleRetrieval:
    def test_critical_fanout_calls_execute_fanout(self):
        deadline = _make_deadline(elapsed_ms=0)
        provider_result = _make_provider_result("q1", n_places=5)

        with patch("app.concierge.provider_executor.execute_fanout") as mock_fanout:
            mock_fanout.return_value = [provider_result]
            result = run_critical_google_fanout(["q1"], api_key="key", deadline=deadline)

        mock_fanout.assert_called_once()
        assert result.success is True
        assert result.provider_results == [provider_result]

    def test_critical_fanout_returns_empty_when_budget_exhausted(self):
        # Simulate: deadline nearly expired — critical fanout should bail immediately.
        deadline = _make_deadline(elapsed_ms=DEFAULT_SLA.hard_cutoff_ms - 100)

        with patch("app.concierge.provider_executor.execute_fanout") as mock_fanout:
            result = run_critical_google_fanout(["q1"], api_key="key", deadline=deadline)

        # With < 0.5s remaining, fanout should be skipped.
        mock_fanout.assert_not_called()
        assert result.success is False
        assert result.provider_results == []
        assert result.timeout_count == 1  # 1 query was not executed

    def test_critical_timeout_count_tracks_failed_queries(self):
        deadline = _make_deadline(elapsed_ms=0)
        good = _make_provider_result("q1", n_places=3)
        bad = _make_provider_result("q2", n_places=0, error="http_timeout")

        with patch("app.concierge.provider_executor.execute_fanout") as mock_fanout:
            mock_fanout.return_value = [good, bad]
            result = run_critical_google_fanout(["q1", "q2"], api_key="key", deadline=deadline)

        assert result.timeout_count == 1
        assert result.success is True


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Non-Google enrichment cannot mint addable cards
# ─────────────────────────────────────────────────────────────────────────────

class TestEnrichmentCannotMintCards:
    def test_enrichment_result_has_no_card_identity_fields(self):
        # NonCriticalEnrichmentResult only holds evidence data, never card objects.
        result = NonCriticalEnrichmentResult(
            enrichment_map={"p1": _make_place_details_result("p1")},
            elapsed_ms=50,
            used_count=1,
            skipped_count=0,
            skip_reason=None,
        )
        # The result holds enrichment_map (evidence only), not cards or place entities.
        assert not hasattr(result, "cards")
        assert not hasattr(result, "entities")
        assert not hasattr(result, "provider_results")
        assert isinstance(result.enrichment_map, dict)

    def test_enrichment_map_values_are_details_not_cards(self):
        detail = _make_place_details_result("p1")
        result = NonCriticalEnrichmentResult(
            enrichment_map={"p1": detail},
            elapsed_ms=50,
            used_count=1,
            skipped_count=0,
            skip_reason=None,
        )
        # Values are PlaceDetailsResult (evidence), not UnifiedRestaurantResult (cards).
        assert result.enrichment_map["p1"] is detail

    def test_critical_path_result_contains_provider_results_not_cards(self):
        # CriticalPathResult contains raw Google API responses, not assembled cards.
        # Card assembly requires entity layer + trust gate — those are in semantic_retrieval.py.
        pr = _make_provider_result("q1", n_places=3)
        result = CriticalPathResult(
            provider_results=[pr],
            elapsed_ms=300,
            timeout_count=0,
            success=True,
        )
        assert not hasattr(result, "cards")
        assert not hasattr(result, "verified_entities")


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Provider fanout respects remaining RequestDeadline budget
# ─────────────────────────────────────────────────────────────────────────────

class TestDeadlinePropagationToFanout:
    def test_effective_timeout_bounded_by_remaining_budget(self):
        # With 2 s remaining, effective_timeout should be < 2 s.
        remaining_ms = 2000
        elapsed_ms = DEFAULT_SLA.hard_cutoff_ms - remaining_ms
        deadline = _make_deadline(elapsed_ms=elapsed_ms)

        captured_timeout = []

        def mock_fanout(queries, api_key, timeout, **kwargs):
            captured_timeout.append(timeout)
            return [_make_provider_result("q1")]

        with patch("app.concierge.provider_executor.execute_fanout", side_effect=mock_fanout):
            run_critical_google_fanout(
                ["q1"], api_key="key", deadline=deadline, timeout=5.0
            )

        # Effective timeout must be ≤ remaining_ms/1000 (minus small buffer).
        assert len(captured_timeout) == 1
        assert captured_timeout[0] <= remaining_ms / 1000.0

    def test_fanout_timeout_not_inflated_beyond_remaining_budget(self):
        # Even if caller requests 10 s timeout, budget caps it.
        remaining_ms = 1000
        elapsed_ms = DEFAULT_SLA.hard_cutoff_ms - remaining_ms
        deadline = _make_deadline(elapsed_ms=elapsed_ms)

        captured = []

        def mock_fanout(queries, api_key, timeout, **kwargs):
            captured.append(timeout)
            return [_make_provider_result("q1")]

        with patch("app.concierge.provider_executor.execute_fanout", side_effect=mock_fanout):
            run_critical_google_fanout(
                ["q1"], api_key="key", deadline=deadline, timeout=10.0
            )

        assert captured[0] <= remaining_ms / 1000.0


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Budget exhausted before enrichment → enrichment is skipped
# ─────────────────────────────────────────────────────────────────────────────

class TestEnrichmentSkippedOnLowBudget:
    def test_enrichment_skipped_when_budget_exactly_zero(self):
        # Create a deadline where budget_for_enrichment_s is exactly 0.
        sla = SLAConfig(soft_ceiling_ms=4000, hard_cutoff_ms=6000)
        # Elapsed = hard_cutoff - (reserve - 1) so remaining < reserve.
        elapsed_ms = sla.hard_cutoff_ms - ENRICHMENT_BUDGET_RESERVE_MS + 10
        deadline = RequestDeadline(sla=sla, t_start=time.monotonic() - elapsed_ms / 1000.0)

        assert deadline.budget_for_enrichment_s() == 0.0

        entities = [_make_place_entity("p1")]
        with patch("app.concierge.place_details_provider.enrich_top_cards") as mock_enrich:
            result = run_non_critical_enrichment(entities, api_key="key", deadline=deadline)

        mock_enrich.assert_not_called()
        assert result.enrichment_map == {}
        assert result.skip_reason is not None

    def test_enrichment_not_skipped_when_budget_sufficient(self):
        # Fresh deadline — plenty of budget.
        deadline = _make_deadline(elapsed_ms=200)
        assert deadline.budget_for_enrichment_s() > 0.0

        detail = _make_place_details_result("p1")
        entities = [_make_place_entity("p1")]

        with patch(
            "app.concierge.place_details_provider.enrich_top_cards",
            return_value={"p1": detail},
        ):
            result = run_non_critical_enrichment(entities, api_key="key", deadline=deadline)

        assert result.enrichment_map == {"p1": detail}
        assert result.skip_reason is None
        assert result.used_count == 1


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Budget available → enrichment attaches evidence without changing identity
# ─────────────────────────────────────────────────────────────────────────────

class TestEnrichmentWithBudget:
    def test_enrichment_returns_evidence_map_keyed_by_place_id(self):
        deadline = _make_deadline(elapsed_ms=300)
        detail_p1 = _make_place_details_result("p1")
        detail_p2 = _make_place_details_result("p2")
        entities = [_make_place_entity("p1"), _make_place_entity("p2")]

        with patch(
            "app.concierge.place_details_provider.enrich_top_cards",
            return_value={"p1": detail_p1, "p2": detail_p2},
        ):
            result = run_non_critical_enrichment(entities, api_key="key", deadline=deadline)

        assert result.used_count == 2
        assert result.enrichment_map["p1"] is detail_p1
        assert result.enrichment_map["p2"] is detail_p2
        # enrichment result holds evidence only — values are PlaceDetailsResult, not cards
        assert "p1" in result.enrichment_map
        # PlaceDetailsResult has editorial_summary, not google_verification (card field)
        assert hasattr(result.enrichment_map["p1"], "editorial_summary")

    def test_enrichment_failure_returns_empty_map_not_exception(self):
        deadline = _make_deadline(elapsed_ms=200)
        entities = [_make_place_entity("p1")]

        with patch(
            "app.concierge.place_details_provider.enrich_top_cards",
            side_effect=RuntimeError("network error"),
        ):
            result = run_non_critical_enrichment(entities, api_key="key", deadline=deadline)

        # Enrichment failure must not propagate — empty map returned safely.
        assert result.enrichment_map == {}
        assert result.used_count == 0


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: First response caps at default 6 cards
# ─────────────────────────────────────────────────────────────────────────────

class TestFirstResponseCardCap:
    def test_parallel_retrieval_result_does_not_cap_cards(self):
        # Card capping is in semantic_retrieval.py (applied after trust gate).
        # parallel_retrieval.py returns raw provider results — no cap applied.
        provider_results = [_make_provider_result("q", n_places=15)]
        critical = CriticalPathResult(
            provider_results=provider_results,
            elapsed_ms=300,
            timeout_count=0,
            success=True,
        )
        # The 15-place result is not capped here — semantic_retrieval applies the cap.
        assert len(critical.provider_results[0].places) == 15

    def test_card_limit_default_is_6(self):
        # Verify SLA default card limit contract preserved from PR #257.
        assert DEFAULT_SLA.first_card_limit == 6
        assert DEFAULT_SLA.first_card_min == 5
        assert DEFAULT_SLA.first_card_max == 7


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: fallback_note_visible_count remains 0
# ─────────────────────────────────────────────────────────────────────────────

class TestNoVisibleFallbackNotes:
    def test_enrichment_result_cannot_generate_visible_notes(self):
        # NonCriticalEnrichmentResult has no note/reason fields.
        # It cannot be the source of visible Concierge Notes.
        result = NonCriticalEnrichmentResult(
            enrichment_map={},
            elapsed_ms=0,
            used_count=0,
            skipped_count=0,
            skip_reason="no_entities",
        )
        assert not hasattr(result, "note")
        assert not hasattr(result, "reason")
        assert not hasattr(result, "display_why")
        assert not hasattr(result, "reason_validated")

    def test_critical_path_result_has_no_note_fields(self):
        # CriticalPathResult is raw API data — no notes generated here.
        result = CriticalPathResult(
            provider_results=[],
            elapsed_ms=100,
            timeout_count=0,
            success=False,
        )
        assert not hasattr(result, "note")
        assert not hasattr(result, "display_why")
        assert not hasattr(result, "fallback_note")


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Telemetry fields present and accurate
# ─────────────────────────────────────────────────────────────────────────────

class TestTelemetryFields:
    def test_parallel_retrieval_result_has_all_required_telemetry_fields(self):
        critical = CriticalPathResult(
            provider_results=[_make_provider_result("q1", n_places=5)],
            elapsed_ms=400,
            timeout_count=1,
            success=True,
        )
        non_critical = NonCriticalEnrichmentResult(
            enrichment_map={"p1": _make_place_details_result("p1")},
            elapsed_ms=200,
            used_count=1,
            skipped_count=2,
            skip_reason=None,
        )
        result = ParallelRetrievalResult(
            critical=critical,
            non_critical=non_critical,
            critical_path_ms=800,
            non_critical_enrichment_ms=200,
            provider_fanout_ms=400,
            provider_timeout_counts=1,
            provider_skipped_due_to_budget_counts=0,
            google_critical_success=True,
            google_critical_candidate_count=5,
            remaining_budget_before_enrichment_ms=3000,
            non_critical_enrichment_used_count=1,
            non_critical_enrichment_skipped_count=2,
        )
        assert result.critical_path_ms == 800
        assert result.non_critical_enrichment_ms == 200
        assert result.provider_fanout_ms == 400
        assert result.provider_timeout_counts == 1
        assert result.provider_skipped_due_to_budget_counts == 0
        assert result.google_critical_success is True
        assert result.google_critical_candidate_count == 5
        assert result.remaining_budget_before_enrichment_ms == 3000
        assert result.non_critical_enrichment_used_count == 1
        assert result.non_critical_enrichment_skipped_count == 2

    def test_critical_result_timeout_count_matches_failed_queries(self):
        deadline = _make_deadline(elapsed_ms=0)
        good = _make_provider_result("q1", n_places=3)
        fail1 = _make_provider_result("q2", n_places=0, error="timeout")
        fail2 = _make_provider_result("q3", n_places=0, error="http_500")

        with patch(
            "app.concierge.provider_executor.execute_fanout",
            return_value=[good, fail1, fail2],
        ):
            result = run_critical_google_fanout(
                ["q1", "q2", "q3"], api_key="key", deadline=deadline
            )

        assert result.timeout_count == 2
        assert result.success is True  # at least one succeeded

    def test_enrichment_skip_count_equals_budget_n_when_fully_skipped(self):
        deadline = _make_deadline(elapsed_ms=DEFAULT_SLA.soft_ceiling_ms + 200)
        entities = [_make_place_entity(f"p{i}") for i in range(4)]

        result = run_non_critical_enrichment(
            entities, api_key="key", deadline=deadline, budget_n=4
        )

        assert result.skipped_count == 4
        assert result.used_count == 0


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: deadline.budget_for_enrichment_s() returns 0.0 past soft ceiling
# ─────────────────────────────────────────────────────────────────────────────

class TestDeadlineBudgetForEnrichment:
    def test_returns_zero_past_soft_ceiling(self):
        deadline = _make_deadline(elapsed_ms=DEFAULT_SLA.soft_ceiling_ms + 1)
        assert deadline.budget_for_enrichment_s() == 0.0

    def test_returns_zero_when_remaining_below_reserve(self):
        sla = SLAConfig(soft_ceiling_ms=4000, hard_cutoff_ms=6000)
        # Leave only 400 ms remaining (< ENRICHMENT_BUDGET_RESERVE_MS = 500).
        elapsed_ms = sla.hard_cutoff_ms - 400
        deadline = RequestDeadline(sla=sla, t_start=time.monotonic() - elapsed_ms / 1000.0)
        assert deadline.budget_for_enrichment_s() == 0.0

    def test_returns_positive_with_sufficient_budget(self):
        deadline = _make_deadline(elapsed_ms=500)
        budget = deadline.budget_for_enrichment_s()
        assert budget > 0.0
        # Must be less than remaining hard cutoff budget.
        assert budget < deadline.remaining_ms() / 1000.0

    def test_budget_shrinks_as_time_passes(self):
        deadline = _make_deadline(elapsed_ms=0)
        b1 = deadline.budget_for_enrichment_s()
        time.sleep(0.05)
        b2 = deadline.budget_for_enrichment_s()
        assert b2 <= b1

    def test_reserve_ms_default_is_500(self):
        from app.concierge.parallel_retrieval import ENRICHMENT_BUDGET_RESERVE_MS
        assert ENRICHMENT_BUDGET_RESERVE_MS == 500

    def test_custom_reserve_ms_reduces_budget(self):
        deadline = _make_deadline(elapsed_ms=1000)
        default_budget = deadline.budget_for_enrichment_s(reserve_ms=500)
        higher_reserve = deadline.budget_for_enrichment_s(reserve_ms=1000)
        assert higher_reserve <= default_budget


# ─────────────────────────────────────────────────────────────────────────────
# Blocker fix tests: fanout_timeout parameter closes the +2s buffer issue
# ─────────────────────────────────────────────────────────────────────────────

class TestFanoutTimeoutBoundedByDeadline:
    """Prove execute_fanout does not add an unbounded +2s buffer when called
    via run_critical_google_fanout with a deadline-bounded effective_timeout."""

    def test_execute_fanout_uses_fanout_timeout_not_default_buffer(self):
        # When fanout_timeout is passed, as_completed must use it — not timeout+2.
        # Capture what timeout value as_completed receives.
        from app.concierge.provider_executor import execute_fanout
        from concurrent.futures import as_completed as real_as_completed

        captured_timeout = []

        def mock_as_completed(futures, timeout=None):
            captured_timeout.append(timeout)
            return iter([])  # return no futures — zero queries complete

        with patch("app.concierge.provider_executor.as_completed", side_effect=mock_as_completed):
            execute_fanout(["q1"], api_key="key", timeout=3.0, fanout_timeout=1.5)

        assert len(captured_timeout) == 1
        assert captured_timeout[0] == 1.5, (
            f"expected fanout_timeout=1.5, got {captured_timeout[0]}; "
            "execute_fanout must not add +2s when fanout_timeout is provided"
        )

    def test_execute_fanout_default_buffer_preserved_when_no_fanout_timeout(self):
        # Legacy callers without fanout_timeout still get timeout + 2.0.
        from app.concierge.provider_executor import execute_fanout

        captured_timeout = []

        def mock_as_completed(futures, timeout=None):
            captured_timeout.append(timeout)
            return iter([])

        with patch("app.concierge.provider_executor.as_completed", side_effect=mock_as_completed):
            execute_fanout(["q1"], api_key="key", timeout=3.0)

        assert len(captured_timeout) == 1
        assert captured_timeout[0] == pytest.approx(5.0), (
            f"legacy callers should still get timeout+2.0=5.0, got {captured_timeout[0]}"
        )

    def test_run_critical_fanout_passes_fanout_timeout_to_execute_fanout(self):
        # run_critical_google_fanout must forward a deadline-bounded fanout_timeout.
        deadline = _make_deadline(elapsed_ms=1000)  # ~5s remaining
        remaining_s = deadline.remaining_ms() / 1000.0

        captured_kwargs = {}

        def mock_execute_fanout(queries, api_key, timeout, fanout_timeout=None, **kwargs):
            captured_kwargs["timeout"] = timeout
            captured_kwargs["fanout_timeout"] = fanout_timeout
            return [_make_provider_result("q1")]

        with patch(
            "app.concierge.provider_executor.execute_fanout",
            side_effect=mock_execute_fanout,
        ):
            run_critical_google_fanout(["q1"], api_key="key", deadline=deadline, timeout=5.0)

        assert "fanout_timeout" in captured_kwargs, "fanout_timeout must be forwarded"
        ft = captured_kwargs["fanout_timeout"]
        assert ft is not None
        # fanout_timeout must not exceed remaining_s (the deadline budget).
        assert ft <= remaining_s, (
            f"fanout_timeout={ft:.3f}s must be <= remaining_s={remaining_s:.3f}s; "
            "fanout cannot overrun the deadline budget"
        )
        # fanout_timeout must be less than per-call timeout + 2.0 (old buffer).
        per_call = captured_kwargs["timeout"]
        assert ft < per_call + 2.0, (
            f"fanout_timeout={ft:.3f}s must be < per_call+2.0={per_call+2.0:.3f}s"
        )

    def test_fanout_timeout_bounded_when_little_budget_remains(self):
        # With only 2s remaining, fanout_timeout must stay well under 2s.
        remaining_ms = 2000
        elapsed_ms = DEFAULT_SLA.hard_cutoff_ms - remaining_ms
        deadline = _make_deadline(elapsed_ms=elapsed_ms)
        remaining_s = deadline.remaining_ms() / 1000.0

        captured = {}

        def mock_execute_fanout(queries, api_key, timeout, fanout_timeout=None, **kwargs):
            captured["fanout_timeout"] = fanout_timeout
            captured["per_call_timeout"] = timeout
            return [_make_provider_result("q1")]

        with patch(
            "app.concierge.provider_executor.execute_fanout",
            side_effect=mock_execute_fanout,
        ):
            run_critical_google_fanout(["q1"], api_key="key", deadline=deadline, timeout=5.0)

        ft = captured["fanout_timeout"]
        assert ft is not None
        # Must never exceed remaining_s — that would overrun the deadline.
        assert ft <= remaining_s, (
            f"fanout_timeout={ft:.3f}s must be <= remaining_s={remaining_s:.3f}s"
        )
        # Must also be less than timeout+2.0 (old unbounded buffer = 7.0s here).
        assert ft < 5.0 + 2.0
