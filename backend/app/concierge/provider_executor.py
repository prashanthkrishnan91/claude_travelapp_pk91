"""Provider Executor — parallel Google Text Search fanout for Semantic Retrieval v1.

Runs multiple Google Places text_search queries in parallel with per-call
deadlines. One query timing out or failing does not kill the whole turn.
If ALL queries fail, returns empty results (no fabrication).

Scope: Google Text Search only. No Tavily, Brave, Serper, Yelp, or Foursquare
in this module. No dependency on Google AI summaries or editorial summaries.
"""

from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_GOOGLE_ENDPOINT = "https://places.googleapis.com/v1/places:searchText"

# Minimal field mask for Phase 1 — only verified structured fields.
# No reviewSummary, neighborhoodSummary, generativeSummary, or atmosphere.
_FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.businessStatus",
        "places.types",
        "places.primaryType",
        "places.rating",
        "places.userRatingCount",
        "places.priceLevel",
        "places.googleMapsUri",
        "places.websiteUri",
    ]
)

DEFAULT_TIMEOUT = 5.0
MAX_RESULTS_PER_QUERY = 15
HARD_CAP_QUERIES = 4


@dataclass
class ProviderQueryResult:
    """Result of a single Google Text Search query."""

    query: str
    places: List[Dict[str, Any]] = field(default_factory=list)
    latency_ms: int = 0
    error: Optional[str] = None

    @property
    def succeeded(self) -> bool:
        return self.error is None


def execute_fanout(
    queries: List[str],
    api_key: str,
    timeout: float = DEFAULT_TIMEOUT,
    hard_cap: int = HARD_CAP_QUERIES,
    max_results_per_query: int = MAX_RESULTS_PER_QUERY,
) -> List[ProviderQueryResult]:
    """Run multiple Google Text Search queries in parallel.

    Args:
        queries: List of query strings. Capped at hard_cap.
        api_key: Google Places API key.
        timeout: Per-call HTTP deadline in seconds.
        hard_cap: Maximum number of queries to execute.
        max_results_per_query: Max places returned per query (Google max: 20).

    Returns:
        List of ProviderQueryResult, one per query (including failed ones).
        Order is not guaranteed (parallel execution).
    """
    if not queries:
        return []
    if not api_key:
        logger.warning("provider_executor: no Google Places API key configured")
        return [ProviderQueryResult(query=q, error="no_api_key") for q in queries[:hard_cap]]

    capped = queries[:hard_cap]

    results: List[ProviderQueryResult] = []
    with ThreadPoolExecutor(max_workers=len(capped)) as executor:
        future_to_query = {
            executor.submit(
                _single_google_query, q, api_key, timeout, max_results_per_query
            ): q
            for q in capped
        }
        # Wait up to timeout + buffer for all futures
        try:
            for future in as_completed(future_to_query, timeout=timeout + 2.0):
                q = future_to_query[future]
                try:
                    result = future.result(timeout=0)
                    results.append(result)
                except Exception as exc:
                    logger.warning(
                        "provider_executor: query=%r future failed: %s", q, exc
                    )
                    results.append(ProviderQueryResult(query=q, error=str(exc)[:120]))
        except TimeoutError:
            logger.warning(
                "provider_executor: fanout_timeout timeout=%.2fs; returning partial results",
                timeout + 2.0,
            )

    # Add error records for any queries that didn't complete (edge case)
    completed_queries = {r.query for r in results}
    for q in capped:
        if q not in completed_queries:
            results.append(ProviderQueryResult(query=q, error="incomplete"))

    successful = sum(1 for r in results if r.succeeded)
    total_places = sum(len(r.places) for r in results)
    logger.info(
        "provider_executor: queries=%d successful=%d total_places=%d",
        len(capped), successful, total_places,
    )

    return results


def _single_google_query(
    query: str,
    api_key: str,
    timeout: float,
    max_results: int,
) -> ProviderQueryResult:
    """Execute one Google Places text_search request. Does not raise."""
    t0 = time.monotonic()
    try:
        import httpx
    except ImportError:
        return ProviderQueryResult(query=query, error="httpx_not_installed")

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": _FIELD_MASK,
    }
    body = {
        "textQuery": query,
        "maxResultCount": min(max_results, 20),
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(_GOOGLE_ENDPOINT, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
        places = list(data.get("places") or [])
        latency_ms = int((time.monotonic() - t0) * 1000)
        logger.debug(
            "provider_executor: query=%r places=%d latency_ms=%d",
            query, len(places), latency_ms,
        )
        return ProviderQueryResult(query=query, places=places, latency_ms=latency_ms)
    except Exception as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        logger.warning(
            "provider_executor: query=%r failed latency_ms=%d error=%s",
            query, latency_ms, exc,
        )
        return ProviderQueryResult(
            query=query, places=[], latency_ms=latency_ms, error=str(exc)[:120]
        )


def get_api_key() -> str:
    """Return the Google Places API key from environment."""
    return os.getenv("GOOGLE_PLACES_API_KEY", "")
