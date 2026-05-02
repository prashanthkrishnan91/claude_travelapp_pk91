"""Provider Result Cache v1 — soft TTL with quality gate.

Three-tier TTL behavior for live provider result payloads:

  FRESH  (0–6h):  return cached result directly; skip live provider call
  STALE (6–24h):  return cached result only if quality gate passes
  EXPIRED (24h+): bypass cache entirely, force live provider call

Usage pattern — wrap, never replace:
  1. Call get_with_status(key) before any expensive provider call.
  2. On FRESH hit with quality ok:  return cached result.
  3. On STALE hit with quality ok:  return cached result.
  4. On FRESH/STALE with quality fail, EXPIRED, or MISS: call live provider.
  5. After a successful live call: call set(key, payload) to store.
     Do NOT store failed, empty, or error responses.

Thread-safe. No database migration required (in-memory only).
"""

import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# TTL tier boundaries
FRESH_SECONDS: int = 6 * 3600   # 6 hours — fresh, reuse by default
STALE_SECONDS: int = 24 * 3600  # 24 hours — stale, quality gate required

# source_status values that indicate a payload is not worth reusing
_WEAK_SOURCE_STATUSES = frozenset({"unavailable", "error", "none", ""})

# Minimum usable candidates per bucket to accept a cached payload
_MIN_CANDIDATES: int = 1

# Intent groups for the intent-aware quality check (values match INTENT_* constants
# from app.models.concierge — kept as literals here to avoid a circular import)
_RESTAURANT_INTENTS = frozenset({
    "restaurants", "nightlife", "hidden_gems", "romantic",
    "family_friendly", "luxury_value", "michelin_restaurants",
})
_ATTRACTION_INTENTS = frozenset({"attractions", "plan_day"})
_HOTEL_INTENTS = frozenset({"hotels"})


# ---------------------------------------------------------------------------
# Cache class
# ---------------------------------------------------------------------------

class ProviderResultCache:
    """In-memory soft-TTL cache for live provider result payloads.

    Store format: key → (stored_at_monotonic: float, payload: dict)

    All public methods are thread-safe via a single re-entrant lock.
    """

    def __init__(
        self,
        fresh_seconds: int = FRESH_SECONDS,
        stale_seconds: int = STALE_SECONDS,
    ) -> None:
        self._fresh = max(0, int(fresh_seconds))
        self._stale = max(0, int(stale_seconds))
        self._store: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Primary interface
    # ------------------------------------------------------------------

    def get_with_status(self, key: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Return ("fresh"|"stale", payload) or None if expired/missing.

        Expired entries are evicted from the store on read.
        """
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            stored_at, payload = entry
            age = now - stored_at
            if age > self._stale:
                self._store.pop(key, None)
                return None
            status = "fresh" if age <= self._fresh else "stale"
            return status, payload

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Return payload only when FRESH, else None.

        Backward-compatible with _TTLCache.get() — stale results are not
        returned; callers that want soft-stale behaviour must use
        get_with_status() directly.
        """
        result = self.get_with_status(key)
        if result is None:
            return None
        status, payload = result
        return payload if status == "fresh" else None

    def set(self, key: str, payload: Dict[str, Any]) -> None:
        """Store a live result payload under key."""
        with self._lock:
            self._store[key] = (time.monotonic(), payload)

    # ------------------------------------------------------------------
    # Maintenance helpers
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def clear_matching(self, predicate) -> int:
        """Remove all entries whose key satisfies predicate; return count removed."""
        removed = 0
        with self._lock:
            keys = [k for k in list(self._store) if predicate(k)]
            for k in keys:
                self._store.pop(k, None)
                removed += 1
        return removed

    def size(self) -> int:
        """Return number of entries currently held (for diagnostics)."""
        with self._lock:
            return len(self._store)


# ---------------------------------------------------------------------------
# Quality gate
# ---------------------------------------------------------------------------

def is_live_research_payload_quality_sufficient(
    payload: Dict[str, Any],
    *,
    intent: Optional[str] = None,
    cache_version: Optional[int] = None,
) -> bool:
    """Return True if the cached payload is worth reusing.

    Quality rules (all must pass):
    1. payload is a non-empty dict
    2. cache_version matches the expected version (if provided)
    3. source_status is not an error/unavailable/empty marker
    4. At least _MIN_CANDIDATES usable results exist for the given intent
    """
    if not payload or not isinstance(payload, dict):
        return False

    if cache_version is not None:
        if payload.get("cache_version") != cache_version:
            return False

    source_status = (payload.get("source_status") or "").lower()
    if source_status in _WEAK_SOURCE_STATUSES:
        return False

    restaurants = payload.get("restaurants") or []
    attractions = payload.get("attractions") or []
    hotels = payload.get("hotels") or []
    research_sources = payload.get("research_sources") or []

    total_any = len(restaurants) + len(attractions) + len(hotels) + len(research_sources)
    if total_any == 0:
        # Truly empty — nothing worth reusing regardless of intent
        return False

    if intent in _RESTAURANT_INTENTS:
        # Accept addable cards OR editorial research sources (partial-but-valid result)
        if len(restaurants) < _MIN_CANDIDATES and not research_sources:
            return False
    elif intent in _ATTRACTION_INTENTS:
        if len(attractions) < _MIN_CANDIDATES and not research_sources:
            return False
    elif intent in _HOTEL_INTENTS:
        if len(hotels) < _MIN_CANDIDATES and not research_sources:
            return False
    # else: any non-zero total passes for general/unknown intent

    return True


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_PROVIDER_CACHE = ProviderResultCache()


def get_provider_cache() -> ProviderResultCache:
    """Return the module-level provider result cache singleton."""
    return _PROVIDER_CACHE


def reset_provider_cache() -> None:
    """Test helper — clear the module-level singleton."""
    _PROVIDER_CACHE.clear()
