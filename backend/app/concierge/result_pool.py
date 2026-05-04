"""Short-lived in-memory result pool for AI Concierge continuation fast path.

On initial or refill place search, stores verified place cards so that a
subsequent "more options" turn can page through unused results without
a new provider call.

Limitations (documented for v1):
- In-memory only: pool is lost on process restart or Gunicorn worker recycle.
- Not shared across processes: multi-worker deployments each maintain independent
  pools. A worker that handled the initial search might not handle the next turn.
- Pool hit rate therefore depends on sticky-session or single-worker deployments.
  Railway with one replica benefits fully; multi-replica deployments fall back to
  the provider path more often.
- TTL: entries expire after POOL_TTL_SECONDS (default 10 min).
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

POOL_TTL_SECONDS = 600  # 10 minutes


class ContinuationResultPool:
    """Thread-safe in-memory pool of verified place cards for continuation paging.

    Each entry is keyed by (trip_id, canonical_query) and holds raw card dicts
    from the most recent search for that query. Cards are consumed (popped) on
    each continuation turn; the caller is responsible for re-storing any unused
    cards from a refill.
    """

    def __init__(self, ttl_seconds: int = POOL_TTL_SECONDS) -> None:
        self._lock = threading.Lock()
        # {(trip_id_str, canonical_query_lower): (monotonic_ts, buckets)}
        self._store: Dict[Tuple[str, str], Tuple[float, Dict[str, List[Any]]]] = {}
        self._ttl = ttl_seconds

    @staticmethod
    def _key(trip_id: str, canonical_query: str) -> Tuple[str, str]:
        return (str(trip_id), (canonical_query or "").strip().lower())

    def store(
        self,
        trip_id: str,
        canonical_query: str,
        buckets: Dict[str, List[Any]],
    ) -> None:
        """Store verified place card dicts for future continuation paging.

        buckets must contain "restaurants", "attractions", and "hotels" lists.
        Each element should be a dict representation of a Unified*Result card.
        """
        key = self._key(trip_id, canonical_query)
        stored: Dict[str, List[Any]] = {
            "restaurants": list(buckets.get("restaurants") or []),
            "attractions": list(buckets.get("attractions") or []),
            "hotels": list(buckets.get("hotels") or []),
        }
        total = sum(len(v) for v in stored.values())
        with self._lock:
            self._store[key] = (time.monotonic(), stored)
        logger.info(
            "result_pool.store trip_id=%s canonical_query=%r total=%d "
            "restaurants=%d attractions=%d hotels=%d",
            trip_id,
            key[1],
            total,
            len(stored["restaurants"]),
            len(stored["attractions"]),
            len(stored["hotels"]),
        )

    def pop(
        self,
        trip_id: str,
        canonical_query: str,
    ) -> Optional[Tuple[Dict[str, List[Any]], int]]:
        """Return all stored cards for the key and clear the pool entry.

        Returns (buckets, total_count) on hit, or None on miss / expired.
        Caller is responsible for deduplication against prior shown cards.
        """
        key = self._key(trip_id, canonical_query)
        with self._lock:
            entry = self._store.pop(key, None)
        if entry is None:
            logger.info(
                "result_pool.miss trip_id=%s canonical_query=%r",
                trip_id,
                key[1],
            )
            return None
        ts, buckets = entry
        if time.monotonic() - ts > self._ttl:
            logger.info(
                "result_pool.expired trip_id=%s canonical_query=%r age_s=%.0f",
                trip_id,
                key[1],
                time.monotonic() - ts,
            )
            return None
        total = sum(len(v) for v in buckets.values())
        logger.info(
            "result_pool.hit trip_id=%s canonical_query=%r total=%d",
            trip_id,
            key[1],
            total,
        )
        return buckets, total

    def clear(self, trip_id: str) -> None:
        """Remove all pool entries for a trip (called on category change / reset)."""
        with self._lock:
            to_del = [k for k in self._store if k[0] == str(trip_id)]
            for k in to_del:
                del self._store[k]
        if to_del:
            logger.info(
                "result_pool.clear trip_id=%s entries_cleared=%d",
                trip_id,
                len(to_del),
            )

    def pool_size(self) -> int:
        """Return number of active pool entries (for monitoring / tests)."""
        with self._lock:
            return len(self._store)


# Module-level singleton — same lifetime as the process worker.
_GLOBAL_CONTINUATION_POOL = ContinuationResultPool()
