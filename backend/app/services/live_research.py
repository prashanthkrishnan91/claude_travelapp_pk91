"""Live Research Layer v1 — source-backed travel research for the AI Concierge.

Provides a small provider abstraction so multiple live-search backends (Tavily,
Brave Search, Serper) can plug in cleanly. Results are normalized into the
existing Concierge `Unified*` card shapes, filtered for permanently-closed /
stale venues, and cached in-memory with a TTL keyed by intent + destination +
query (no DB migration required).

Architecture
------------
    UserQuery + Destination + Intent
            │
            ▼
    LiveResearchService.fetch(...)
            │
            ├─▶ in-memory TTL cache (hit?) → cached normalized results
            │
            └─▶ provider.search(query)         (real or stub)
                    │
                    ▼
            _normalize_hits(intent, ...) → Unified{Restaurant,Attraction,Hotel,Area}Result[]
                    │
                    ▼
            _filter_closed_or_stale(...)
                    │
                    ▼
            cache + return (results, source_status, cached, provider_name)

Source label honesty
--------------------
- Real provider hits → SOURCE_LIVE_SEARCH (with source_url + last_verified_at)
- No provider configured / no hits → SOURCE_NONE (concierge falls back to existing
  curated/app-database/sample paths and labels them honestly).
- Sample data is NEVER relabeled as live.

No Supabase SQL is required for this layer.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from collections import Counter
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from app.concierge.reasoning import (
    build_why_pick,
    ensure_non_empty_evidence,
)
from app.models.concierge import (
    INTENT_ATTRACTIONS,
    INTENT_BEST_AREA,
    INTENT_AREA_ADVICE,
    INTENT_COMPARE,
    INTENT_FAMILY_FRIENDLY,
    INTENT_HIDDEN_GEMS,
    INTENT_HOTELS,
    INTENT_LUXURY_VALUE,
    INTENT_MICHELIN_RESTAURANTS,
    INTENT_NIGHTLIFE,
    INTENT_PLAN_DAY,
    INTENT_RESTAURANTS,
    INTENT_REWARDS_HELP,
    INTENT_ROMANTIC,
    GoogleVerification,
    SOURCE_LIVE_SEARCH,
    SOURCE_NONE,
    PlaceSupportingDetails,
    SourceEvidence,
    VenueEnrichment,
    UnifiedAttractionResult,
    UnifiedHotelResult,
    UnifiedResearchSourceResult,
    UnifiedRestaurantResult,
)
from app.services.google_places import (
    GooglePlaceVerification,
    GooglePlacesService,
    OPERATIONAL,
    is_addable as _google_is_addable,
)

logger = logging.getLogger(__name__)


# ── Closed/stale heuristics ──────────────────────────────────────────────────

_CLOSED_KEYWORDS = (
    "permanently closed",
    "closes permanently",
    "closed permanently",
    "closed for good",
    "closed for the final time",
    "closed its doors",
    "now closed",
    "is closed",
    "closing after",
    "closing permanently",
    "closed after",
    "shut down",
    "shuttered",
    "out of business",
    "ceased operations",
    "no longer in operation",
    "no longer open",
    "has closed",
    "won't reopen",
    "will not reopen",
)
_CLOSED_PROXIMITY_CHARS = 300
_MONTH_YEAR_HINT = re.compile(
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{4}\b",
    re.IGNORECASE,
)
_ARTICLE_CONTEXT_HINT = re.compile(
    r"\b(article|news|guide|best|top|things to|where to|list|roundup|directory|review)\b",
    re.IGNORECASE,
)
_YEAR_HINT = re.compile(r"\b(19|20)\d{2}\b")
_LIST_ITEM_BOUNDARY_HINT = re.compile(r"\b\d{1,2}[.)]\s+\w", re.IGNORECASE)

_FRESHNESS_HIGH_DAYS = 90
_FRESHNESS_MEDIUM_DAYS = 365
_MARKDOWN_HEADING_PAT = re.compile(r"^\s{0,3}#{1,6}\s*")
_SYMBOL_RUN_PAT = re.compile(r"([!?.\-_*~])\1{2,}")
_WHITESPACE_PAT = re.compile(r"\s+")
_DANGLING_YEAR_PAREN_PAT = re.compile(r"\(\s*\d{4}\.?\s*$")
_LEADING_LIST_NUMBER_PAT = re.compile(r"^\s*(?:\d{1,3}[.)]|[-*])\s+")
_BROKEN_MARKDOWN_TOKENS_PAT = re.compile(r"(?:^|\s)#{1,6}\s*")
_GENERIC_REASON_PATTERNS = (
    re.compile(r"\bis a\b.*\boption\b", re.IGNORECASE),
    re.compile(r"\bgreat fit for (this trip|your trip)\b", re.IGNORECASE),
    re.compile(r"\bmatches your request\b", re.IGNORECASE),
    re.compile(r"\bfits your request\b", re.IGNORECASE),
)
_RAW_URL_PAT = re.compile(r"https?://", re.IGNORECASE)
_MARKDOWN_LIST_PAT = re.compile(r"^\s*(?:[-*]|\d{1,3}[.)])\s+", re.MULTILINE)
_ARTICLE_FRAGMENT_PAT = re.compile(
    r"\b(?:best|top)\s+\d{1,3}\b|\b(listicle|roundup|newsletter|advertisement)\b",
    re.IGNORECASE,
)
_REASON_ARTIFACT_PAT = re.compile(r"(####|\[\.\.\.\]|</|https?://|\bfor music\b|\bfor something\b)", re.IGNORECASE)
_HTML_TAG_PAT = re.compile(r"<[^>]+>")
_ADDRESS_LIKE_PAT = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9'\.\-\s]{2,50}\s(?:st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive|ln|lane|ct|court|pl|place)\b",
    re.IGNORECASE,
)

# ── Verify-before-add constants ──────────────────────────────────────────────

_OBVIOUS_NON_VENUE_LOWER: frozenset = frozenset({
    "united states",
    "united states of america",
    "united kingdom",
    "great britain",
    "united arab emirates",
    "north america",
    "south america",
    "latin america",
    "central america",
    "western europe",
    "eastern europe",
    "southeast asia",
    "east asia",
    "the middle east",
    "middle east",
})

_NON_VENUE_SUFFIX_WORDS: frozenset = frozenset({
    "special", "specials", "launch", "promotion", "promotions",
    "explore", "exploration", "discovery", "guide", "guides",
    "overview", "roundup", "roundups", "review", "reviews",
    "update", "updates", "edition", "editions", "award", "awards",
    "deal", "deals", "offer", "offers", "sale", "newsletter",
    "blog", "list", "listing", "listings", "directory",
})

_PLACE_PLATFORM_HINT = re.compile(
    r"(yelp\.com|tripadvisor\.|opentable\.com|resy\.com|"
    r"guide\.michelin|michelin\.com|google\.[^/\s]+/maps|"
    r"maps\.google|foursquare\.com|zomato\.com)",
    re.IGNORECASE,
)

MAX_VERIFICATION_CANDIDATES: int = 40
MIN_ADDABLE_RESULTS: int = 5
RESEARCH_SUPPRESS_THRESHOLD: int = 3

_PLACE_INTENT_MIN_RESULTS = {
    INTENT_NIGHTLIFE,
    INTENT_RESTAURANTS,
    INTENT_HIDDEN_GEMS,
    INTENT_LUXURY_VALUE,
    INTENT_ROMANTIC,
    INTENT_FAMILY_FRIENDLY,
    INTENT_MICHELIN_RESTAURANTS,
}

_BOILERPLATE_PATTERNS = [
    re.compile(r"\b(advertising|advertisement|sponsored)\b", re.IGNORECASE),
    re.compile(r"\b(subscribe|sign in|sign up|newsletter)\b", re.IGNORECASE),
    re.compile(r"\b(sorry[, ]+you\b|we are sorry|page not found)\b", re.IGNORECASE),
    re.compile(r"\bcookie(s)?\b", re.IGNORECASE),
]
_LOW_QUALITY_MARKERS = (
    "advertising",
    "subscribe",
    "newsletter",
    "sign in",
    "sign up",
    "cookie policy",
    "page not found",
)
_NEUTRAL_RESEARCH_REASON = (
    "This source may contain relevant background, but it is not a confirmed venue."
)
_NEUTRAL_RESEARCH_REASON_ARTICLE = (
    "Used for background discovery; individual venues were verified separately."
)
_NOISY_TITLE_SUFFIX_PAT = re.compile(r"\(?\bupdated\s+\d{4}\b\)?", re.IGNORECASE)
_TOP_LISTICLE_TITLE_PAT = re.compile(r"\b(the\s+)?\d{1,3}\s+best\b", re.IGNORECASE)
_SOURCE_HOST_STRIP_PAT = re.compile(r"^www\.", re.IGNORECASE)
_HIGH_AUTHORITY_EDITORIAL_HOSTS = (
    "michelin.com",
    "guide.michelin.com",
    "eater.com",
    "theinfatuation.com",
    "timeout.com",
    "cntraveler.com",
)
_RESTAURANT_PLATFORM_HOSTS = ("resy.com", "opentable.com")
_CORROBORATION_ONLY_HOSTS = ("tripadvisor.", "yelp.", "google.", "maps.google", "foursquare.com")


def _looks_closed(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(kw in lower for kw in _CLOSED_KEYWORDS)


def _closed_research_summary(title: str) -> str:
    return "This appears closed and was not added as a trip option."


def _iter_hit_source_fragments(hit: LiveSearchHit) -> List[str]:
    raw = hit.raw if isinstance(hit.raw, dict) else {}
    fragments: List[str] = [hit.title or "", hit.snippet or ""]
    for key in (
        "content",
        "raw_content",
        "rawContent",
        "text",
        "source_text",
        "sourceText",
        "description",
        "snippet",
        "title",
    ):
        val = raw.get(key)
        if isinstance(val, str) and val.strip():
            fragments.append(val.strip())
    if raw:
        try:
            fragments.append(json.dumps(raw, ensure_ascii=False))
        except Exception:
            pass
    return fragments


def _candidate_mentions_closed(candidate: str, text: str, *, proximity_chars: int = _CLOSED_PROXIMITY_CHARS) -> bool:
    if not candidate or not text or not _looks_closed(text):
        return False
    for chunk in re.split(r"(?<=[.!?])\s+|\n+", text):
        if candidate.lower() in chunk.lower() and _looks_closed(chunk):
            return True
    low_text = text.lower()
    low_candidate = candidate.lower()
    start = 0
    while True:
        idx = low_text.find(low_candidate, start)
        if idx < 0:
            break
        window = low_text[max(0, idx - proximity_chars) : idx + len(low_candidate) + proximity_chars]
        if _looks_closed(window):
            nearest_closed_idx = -1
            nearest_distance = proximity_chars + 1
            for kw in _CLOSED_KEYWORDS:
                kw_idx = window.find(kw)
                if kw_idx < 0:
                    continue
                # candidate index inside this window
                candidate_window_idx = idx - max(0, idx - proximity_chars)
                dist = abs(kw_idx - candidate_window_idx)
                if dist < nearest_distance:
                    nearest_distance = dist
                    nearest_closed_idx = kw_idx
            if nearest_closed_idx >= 0:
                candidate_window_idx = idx - max(0, idx - proximity_chars)
                lo, hi = sorted((candidate_window_idx, nearest_closed_idx))
                between = window[lo:hi]
                if not _LIST_ITEM_BOUNDARY_HINT.search(between):
                    return True
        start = idx + len(low_candidate)
    return False


def _candidate_closed_from_source(candidate: str, *, source_title: str, source_text: str) -> bool:
    if not candidate:
        return False
    lower_title = (source_title or "").lower()
    lower_candidate = candidate.lower()
    title_targets_candidate = lower_candidate in lower_title and _looks_closed(lower_title)
    return title_targets_candidate or _candidate_mentions_closed(candidate, source_text)


def _extract_latest_year(text: str) -> Optional[int]:
    years = [int(m.group(0)) for m in _YEAR_HINT.finditer(text or "")]
    if not years:
        return None
    return max(years)


def _is_stale_operating_status_signal(text: str, url: str) -> bool:
    if not text:
        return False
    latest_year = _extract_latest_year(text)
    if latest_year is None or latest_year >= datetime.now(timezone.utc).year:
        return False
    lower_text = text.lower()
    lower_url = (url or "").lower()
    article_like = bool(_MONTH_YEAR_HINT.search(text)) or bool(_ARTICLE_CONTEXT_HINT.search(text))
    article_like = article_like or any(marker in lower_url for marker in ("/news", "/blog", "/guide", "/best-", "/top-"))
    return article_like


# ── Hit dataclass ────────────────────────────────────────────────────────────

@dataclass
class LiveSearchHit:
    """Generic result returned by a live search provider before normalization."""

    title: str
    url: str
    snippet: str = ""
    provider: str = ""
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    """Outcome of a second-pass focused search for a single candidate venue."""

    verified: bool = False
    source_url: Optional[str] = None
    category: Optional[str] = None
    neighborhood: Optional[str] = None
    reason: Optional[str] = None


# ── Provider abstraction ─────────────────────────────────────────────────────

class LiveSearchProvider(ABC):
    """Abstract live web/search-style provider."""

    name: str = "unknown"

    @abstractmethod
    def search(self, query: str, *, max_results: int = 10) -> List[LiveSearchHit]:
        """Run a live search and return up to ``max_results`` normalized hits."""

    @property
    def available(self) -> bool:
        return True


class _NoopProvider(LiveSearchProvider):
    """Returned when no real provider is configured."""

    name = "none"

    @property
    def available(self) -> bool:
        return False

    def search(self, query: str, *, max_results: int = 10) -> List[LiveSearchHit]:
        return []


class TavilyProvider(LiveSearchProvider):
    """Tavily Search API — https://docs.tavily.com/

    Wired as the v1 real provider since its `search_depth=advanced` mode is
    well-suited to travel research and is commonly configured for AI agents.
    Activates when ``TAVILY_API_KEY`` is set.
    """

    name = "Tavily"
    _ENDPOINT = "https://api.tavily.com/search"

    def __init__(self, api_key: str, timeout: float = 6.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def search(self, query: str, *, max_results: int = 10) -> List[LiveSearchHit]:
        if not self.available:
            return []
        try:
            import httpx
        except ImportError:
            logger.warning("httpx not installed; Tavily provider disabled")
            return []
        payload = {
            "api_key": self._api_key,
            "query": query,
            "search_depth": "advanced",
            "max_results": max_results,
            "include_answer": False,
        }
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(self._ENDPOINT, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("Tavily search failed: %s", exc)
            return []
        return [
            LiveSearchHit(
                title=str(item.get("title", "")).strip(),
                url=str(item.get("url", "")).strip(),
                snippet=str(item.get("content", "") or item.get("snippet", "")).strip(),
                provider=self.name,
                raw=item,
            )
            for item in (data.get("results") or [])
            if item.get("title") and item.get("url")
        ]


class BraveSearchProvider(LiveSearchProvider):
    """Brave Search API — https://brave.com/search/api/

    Activates when ``BRAVE_SEARCH_API_KEY`` is set. Uses the web search endpoint.
    """

    name = "Brave Search"
    _ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str, timeout: float = 6.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def search(self, query: str, *, max_results: int = 10) -> List[LiveSearchHit]:
        if not self.available:
            return []
        try:
            import httpx
        except ImportError:
            logger.warning("httpx not installed; Brave provider disabled")
            return []
        params = {"q": query, "count": max_results}
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self._api_key,
        }
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(self._ENDPOINT, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("Brave search failed: %s", exc)
            return []
        web = (data.get("web") or {}).get("results") or []
        return [
            LiveSearchHit(
                title=str(item.get("title", "")).strip(),
                url=str(item.get("url", "")).strip(),
                snippet=str(item.get("description", "")).strip(),
                provider=self.name,
                raw=item,
            )
            for item in web
            if item.get("title") and item.get("url")
        ]


class SerperProvider(LiveSearchProvider):
    """Serper.dev (Google SERP wrapper) — https://serper.dev/

    Activates when ``SERPER_API_KEY`` is set.
    """

    name = "Google (via Serper)"
    _ENDPOINT = "https://google.serper.dev/search"

    def __init__(self, api_key: str, timeout: float = 6.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def search(self, query: str, *, max_results: int = 10) -> List[LiveSearchHit]:
        if not self.available:
            return []
        try:
            import httpx
        except ImportError:
            logger.warning("httpx not installed; Serper provider disabled")
            return []
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(
                    self._ENDPOINT,
                    headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
                    json={"q": query, "num": max_results},
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("Serper search failed: %s", exc)
            return []
        return [
            LiveSearchHit(
                title=str(item.get("title", "")).strip(),
                url=str(item.get("link", "")).strip(),
                snippet=str(item.get("snippet", "")).strip(),
                provider=self.name,
                raw=item,
            )
            for item in (data.get("organic") or [])
            if item.get("title") and item.get("link")
        ]


class StubLiveSearchProvider(LiveSearchProvider):
    """Test/wire-later adapter — returns the hits it was constructed with.

    Used by tests and as a development placeholder. Never automatically
    returned from ``select_default_provider`` so production environments
    without real keys see ``SOURCE_NONE`` and fall back honestly.
    """

    name = "stub"

    def __init__(self, hits: Optional[List[LiveSearchHit]] = None) -> None:
        self._hits = list(hits or [])

    @property
    def available(self) -> bool:
        return True

    def search(self, query: str, *, max_results: int = 10) -> List[LiveSearchHit]:
        return list(self._hits[:max_results])


# ── In-memory TTL cache ──────────────────────────────────────────────────────

class _TTLCache:
    """Process-local in-memory cache. No DB migration required.

    Entries are tuples of (expires_at_epoch, payload).
    """

    def __init__(self, ttl_seconds: int = 1800) -> None:
        self._ttl = max(0, int(ttl_seconds))
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        if self._ttl <= 0:
            return None
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires_at, payload = entry
            if expires_at < now:
                self._store.pop(key, None)
                return None
            return payload

    def set(self, key: str, payload: Any) -> None:
        if self._ttl <= 0:
            return
        with self._lock:
            self._store[key] = (time.monotonic() + self._ttl, payload)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def clear_matching(self, predicate) -> int:
        removed = 0
        with self._lock:
            keys = [k for k in self._store.keys() if predicate(k)]
            for key in keys:
                self._store.pop(key, None)
                removed += 1
        return removed


# Module-level cache so multiple ConciergeService instances share results.
_GLOBAL_CACHE = _TTLCache(ttl_seconds=1800)
# Separate cache for candidate verification results.
_VERIFICATION_CACHE = _TTLCache(ttl_seconds=1800)
# Bumped to invalidate stale cached reasons after why_pick guard wiring fixes.
CONCIERGE_CACHE_VERSION = 5


def _normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", (query or "").strip().lower())


def _derive_location_anchor(query: str) -> str:
    low = _normalize_query(query)
    if "near my hotel" in low or "near hotel" in low:
        return "hotel_anchor"
    if "near me" in low:
        return "near_me"
    if "west loop" in low:
        return "west_loop"
    if "river north" in low:
        return "river_north"
    return "none"


def _derive_query_category(intent: str, query: str) -> str:
    low = _normalize_query(query)
    if intent == INTENT_NIGHTLIFE:
        return "nightlife_bar"
    if intent in {INTENT_RESTAURANTS, INTENT_HIDDEN_GEMS, INTENT_ROMANTIC, INTENT_FAMILY_FRIENDLY, INTENT_LUXURY_VALUE}:
        if any(tok in low for tok in ("brunch", "breakfast", "cafe", "coffee", "bakery")):
            return "brunch_cafe"
        return "restaurant"
    if intent in {INTENT_ATTRACTIONS, INTENT_PLAN_DAY}:
        return "attraction"
    if intent == INTENT_HOTELS:
        return "hotel"
    return "general"


def _make_cache_key(intent: str, destination: str, query: str, dates: Optional[str] = None) -> str:
    normalized_query = _normalize_query(query)
    derived_category = _derive_query_category(intent, query)
    location_anchor = _derive_location_anchor(query)
    parts = [
        intent or "general",
        (destination or "").strip().lower(),
        normalized_query,
        derived_category,
        location_anchor,
        dates or "",
    ]
    return "::".join(parts)


# ── Provider selection ───────────────────────────────────────────────────────

def select_default_provider(timeout: float = 6.0) -> LiveSearchProvider:
    """Return the first real provider whose API key is present in the env.

    Priority: Tavily → Brave → Serper → Noop (no live data available).
    Settings are read from environment variables directly so that this module
    has no hard dependency on ``app.core.config`` (which imports pydantic-
    settings) and stays unit-testable in minimal harnesses.
    """
    tavily = os.getenv("TAVILY_API_KEY") or ""
    if tavily:
        return TavilyProvider(api_key=tavily, timeout=timeout)
    brave = os.getenv("BRAVE_SEARCH_API_KEY") or ""
    if brave:
        return BraveSearchProvider(api_key=brave, timeout=timeout)
    serper = os.getenv("SERPER_API_KEY") or ""
    if serper:
        return SerperProvider(api_key=serper, timeout=timeout)
    return _NoopProvider()


# ── Query routing ────────────────────────────────────────────────────────────

_LIVE_ENABLED_INTENTS = {
    INTENT_NIGHTLIFE,
    INTENT_RESTAURANTS,
    INTENT_HIDDEN_GEMS,
    INTENT_LUXURY_VALUE,
    INTENT_ROMANTIC,
    INTENT_FAMILY_FRIENDLY,
    INTENT_ATTRACTIONS,
    INTENT_PLAN_DAY,
    INTENT_HOTELS,
    INTENT_BEST_AREA,
    INTENT_AREA_ADVICE,
    INTENT_MICHELIN_RESTAURANTS,
    INTENT_REWARDS_HELP,
}


def _build_search_query(intent: str, destination: str, user_query: str) -> str:
    """Build a focused live-search query for a given intent + destination."""
    dest = destination.strip()
    raw = (user_query or "").strip()
    if intent == INTENT_NIGHTLIFE:
        return f"best cocktail bars and nightlife in {dest} 2026"
    if intent == INTENT_MICHELIN_RESTAURANTS:
        return f"current Michelin starred and Bib Gourmand restaurants in {dest}"
    if intent == INTENT_HIDDEN_GEMS:
        return f"hidden gem restaurants locals love in {dest} (recent)"
    if intent == INTENT_LUXURY_VALUE:
        return f"best luxury fine dining with value in {dest}"
    if intent == INTENT_ROMANTIC:
        return f"romantic restaurants in {dest} for date night"
    if intent == INTENT_FAMILY_FRIENDLY:
        return f"family-friendly restaurants in {dest}"
    if intent == INTENT_RESTAURANTS:
        if raw:
            return f"{raw} in {dest}".strip()
        return f"best restaurants in {dest} 2026"
    if intent in (INTENT_ATTRACTIONS, INTENT_PLAN_DAY):
        return f"top things to do and attractions in {dest}"
    if intent == INTENT_HOTELS:
        return f"best hotels with location and value in {dest}"
    if intent in (INTENT_BEST_AREA, INTENT_AREA_ADVICE):
        return f"best neighborhoods to stay in {dest}"
    if intent == INTENT_REWARDS_HELP:
        return f"best ways to use points and miles in {dest}"
    if raw:
        return f"{raw} {dest}".strip()
    return dest


def _is_place_intent(intent: str) -> bool:
    return intent in _PLACE_INTENT_MIN_RESULTS


def _google_fallback_queries(intent: str, destination: str, user_query: str) -> List[str]:
    dest = (destination or "").strip()
    base = (user_query or "").strip()
    if not dest:
        return []
    queries: List[str] = []
    if intent == INTENT_NIGHTLIFE:
        near_variant = "nearby cocktail bars" if "nearby" in base.lower() else "cocktail bars near me"
        queries.extend(
            [
                f"cocktail bars near {dest}",
                f"best cocktail bars in {dest}",
                f"top speakeasy bars in {dest}",
                f"open now cocktail bars in {dest}",
                f"{near_variant} in {dest}",
            ]
        )
    elif intent == INTENT_RESTAURANTS:
        queries.extend([f"best restaurants near {dest}", f"restaurants in {dest}"])
    elif intent == INTENT_MICHELIN_RESTAURANTS:
        queries.extend(
            [
                f"Michelin restaurants in {dest}",
                f"Michelin star restaurants {dest}",
                f"Bib Gourmand restaurants in {dest}",
                f"fine dining in {dest}",
            ]
        )
    else:
        queries.extend([f"{base or 'places'} near {dest}", f"{base or 'best places'} in {dest}"])
    # preserve order while deduping
    seen: set = set()
    deduped: List[str] = []
    for query in queries:
        norm = query.lower().strip()
        if not norm or norm in seen:
            continue
        seen.add(norm)
        deduped.append(query)
    return deduped


# ── Normalization ────────────────────────────────────────────────────────────

_NEIGHBORHOOD_HINT = re.compile(
    r"\b(in|at)\s+([A-Z][A-Za-z'\-\.]+(?:\s+[A-Z][A-Za-z'\-\.]+){0,2})"
)
_ADDRESS_HINT = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9'\.\-\s]{2,40}\s(?:st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive|ln|lane|ct|court|pl|place)\b",
    re.IGNORECASE,
)
_PRICE_HINT = re.compile(r"\$\s?\d{1,4}(?:[\.,]\d{1,2})?")
_RATING_HINT = re.compile(r"(\d(?:\.\d)?)\s*/\s*5")
_ARTICLE_PREFIX_HINT = re.compile(
    r"^\s*(best|top|guide to|where to|things to|ultimate guide|what to do|"
    r"\d+\s+best|\d+\s+top)\b",
    re.IGNORECASE,
)
_ARTICLE_HINT = re.compile(
    r"\b(best|top|guide|list|listicle|blog|directory|things to do|where to|"
    r"ultimate guide|itinerary|neighborhood guide)\b",
    re.IGNORECASE,
)

# ── Venue extraction patterns ────────────────────────────────────────────────

# "1. Kumiko — ...", "2. The Aviary — ..."
_NUMBERED_ITEM_PAT = re.compile(
    r"(?<![A-Za-z])\d{1,2}[.)]\s+([A-Z][A-Za-z'\-\.& ]{2,50}?)"
    r"(?=\s*[–—\-]|\s*[\n:]|\s*\d{1,2}[.)]|\s*$)"
)
# "Kumiko — West Loop", "The Aviary — Avant-garde"
_PROPER_NOUN_DASH_PAT = re.compile(
    r"([A-Z][A-Za-z'\-\.&]+(?:\s+(?:&|[Tt]he|[Oo]f|[A-Z][A-Za-z'\-\.]+)){0,4})"
    r"\s*[–—]\s"
)
# "Kumiko", "The Violet Hour" in quotes
_QUOTED_VENUE_PAT = re.compile(r'["“]([A-Z][A-Za-z\'\-\.& ]{2,40}?)["”]')
# Candidates that start with generic/article-like words → reject
_GENERIC_CANDIDATE_PAT = re.compile(
    r"^\s*(?:best|top|great|amazing|new|list|guide|things?|where|what|why|how|"
    r"food|drink|dining|nightlife|travel|visit|explore|"
    r"neighborhood|district|city|cities|places?|spots?|options?)\b",
    re.IGNORECASE,
)
_CONTEXT_START_WORDS = {
    "for",
    "with",
    "near",
    "around",
    "including",
    "featuring",
    "from",
    "at",
    "in",
    "on",
}
_AMBIGUOUS_SINGLE_WORD_CANDIDATES = {
    "lime",
    "olive",
    "violet",
    "green",
    "gold",
    "red",
    "blue",
    "velvet",
    "union",
    "loop",
    "district",
}
_TRUSTED_EDITORIAL_SOURCE_HINT = re.compile(
    r"(timeout|tripadvisor|infatuation|eater|cntraveler|lonelyplanet|michelin|opentable|resy|thrillist|fodor)",
    re.IGNORECASE,
)
_DIRECT_PLACE_SOURCE_HINT = re.compile(
    r"(google\.[^/]+/maps|maps\.google|yelp\.|opentable|resy|tripadvisor|foursquare)",
    re.IGNORECASE,
)
_TRAILING_CONTEXT_WORDS = {"music", "food", "drink", "drinks", "dancing", "brunch", "nightlife"}
_CLEAN_LIST_NAME_TMPL = r"(?<![A-Za-z0-9])(?:\d{{1,2}}[.)]\s+|[-•]\s+){name}(?=\s*[–—:\-]|\s*$)"
_NAME_LINKER_WORDS = {"in", "near", "around", "with", "featuring", "including", "from", "for"}
_BANNED_SOURCE_REASON_PHRASES: Tuple[str, ...] = (
    "extracted from local guide",
    "confirmed as an operational google place",
    "found in article",
    "verified on google",
    "confirmed as operational",
)

_CHAIN_RESTAURANT_NAMES = (
    "the capital grille",
    "ruth's chris",
    "ruths chris",
    "morton's",
    "mortons",
    "fogo de chão",
    "fogo de chao",
    "benihana",
    "cheesecake factory",
)
_CUISINE_OR_VIBE_HINTS = (
    "brasserie",
    "tasting menu",
    "omakase",
    "bbq",
    "barbecue",
    "cocktail bar",
    "wine bar",
    "jazz club",
    "jazz bar",
    "speakeasy",
    "bistro",
    "steakhouse",
    "rooftop bar",
)
_PRICE_VALUE_HINT = re.compile(
    r"(\$\s?\d{2,3}|under\s+\$\s?\d{2,3}|prix fixe|value|good value|affordable|splurge|budget|under\s+\d{2,3})",
    re.IGNORECASE,
)
_AWARD_HINT = re.compile(r"(michelin|james beard|award-winning|award winning|starred)", re.IGNORECASE)
_LUXURY_HINT = re.compile(r"(luxury|fine dining|chef'?s tasting|degustation)", re.IGNORECASE)


def _confidence_from_age(fetched_at: str) -> str:
    try:
        ts = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return "unknown"
    age = (datetime.now(timezone.utc) - ts).total_seconds() / 86400.0
    if age <= _FRESHNESS_HIGH_DAYS:
        return "high"
    if age <= _FRESHNESS_MEDIUM_DAYS:
        return "medium"
    return "low"


def _extract_source_reason(candidate: str, snippet: str) -> Optional[str]:
    """Extract human-readable reason from 'candidate — description' article pattern."""
    if not candidate or not snippet:
        return None
    pat = re.compile(
        re.escape(candidate) + r"\s*[–—-]\s*([^.!?\n]{10,250}[.!?]?)",
        re.IGNORECASE,
    )
    m = pat.search(snippet)
    if not m:
        return None
    reason = m.group(1).strip().strip(".,;:")
    lower = reason.lower()
    if any(banned in lower for banned in _BANNED_SOURCE_REASON_PHRASES):
        return None
    cleaned = _sanitize_reason_evidence_text(reason, own_name=candidate, known_candidate_names=[candidate], max_len=140)
    return cleaned or None


def _extract_source_evidence_text(candidate: str, snippet: str) -> Optional[str]:
    """Extract a window of text around the candidate mention in the snippet."""
    if not candidate or not snippet:
        return None
    low = snippet.lower()
    idx = low.find(candidate.lower())
    if idx < 0:
        return None
    start = max(0, idx - 30)
    end = min(len(snippet), idx + len(candidate) + 200)
    raw = snippet[start:end].strip() or None
    if not raw:
        return None
    return _sanitize_reason_evidence_text(raw, own_name=candidate, known_candidate_names=[candidate], max_len=120)


def _build_source_evidence(
    *,
    candidate: str,
    source_title: str,
    source_url: str,
    source_rank: int,
    snippet: str,
    source_category: Optional[str],
    neighborhood_hint: Optional[str],
) -> SourceEvidence:
    """Build a SourceEvidence from article extraction data."""
    domain = _SOURCE_HOST_STRIP_PAT.sub("", (urlparse(source_url).netloc or "").lower()) or None
    source_reason = _extract_source_reason(candidate, snippet)
    evidence_text = _extract_source_evidence_text(candidate, snippet)
    return SourceEvidence(
        source_title=_normalize_source_title(source_title) or None,
        source_url=source_url or None,
        source_domain=domain,
        source_rank=source_rank,
        source_reason=source_reason,
        source_evidence=evidence_text,
        source_category=source_category,
        neighborhood_hint=neighborhood_hint,
        mention_count=1,
    )


def _compose_reason_with_google(
    *,
    source_evidence: Optional[SourceEvidence],
    verification: "GooglePlaceVerification",
    intent: str,
    source_count: int = 0,
) -> str:
    """Compose the final card reason from article evidence + Google verification data."""
    google_bits: List[str] = []
    if verification.formatted_address:
        google_bits.append(f"at {verification.formatted_address}")
    if verification.rating is not None:
        google_bits.append(f"with a {verification.rating:.1f} rating")
    google_support = f"Google verifies it {' '.join(google_bits)}" if google_bits else "Confirmed operational by Google"

    if source_evidence and source_evidence.source_reason:
        reason = source_evidence.source_reason
        # Add mention-count context only when multiple articles surfaced this venue.
        if source_evidence.mention_count > 1:
            prefix = f"Mentioned by {source_evidence.mention_count} guides. "
            reason = prefix + reason
        return f"{reason} {google_support}.".strip()

    if source_evidence and source_evidence.source_evidence:
        # Derive a short reason from the raw evidence text.
        derived = _clean_reason_text(source_evidence.source_evidence[:200])
        if derived:
            return f"{derived} {google_support}.".strip()

    # No article evidence — build a data-rich reason from Google fields only.
    # For direct venue hits this is the primary reason (keep rating/address).
    bits: List[str] = []
    if source_count > 1:
        bits.append(f"Found in {source_count} local guides.")
    elif source_count == 1:
        bits.append("Featured in a local guide.")
    if verification.rating is not None:
        bits.append(f"Google rating {verification.rating:.1f}")
    if verification.formatted_address:
        bits.append(f"at {verification.formatted_address}")
    if bits:
        return ". ".join(bits) + "."
    return "Verified on Google after appearing in a local guide."


def _query_intent_label(user_query: str, intent: str) -> str:
    clean = _clean_reason_text(user_query)
    if clean and len(clean) <= 24:
        return clean
    intent_map = {
        INTENT_NIGHTLIFE: "cocktail and nightlife plans",
        INTENT_ROMANTIC: "a romantic dining experience",
        INTENT_HIDDEN_GEMS: "hidden-gem local spots",
        INTENT_RESTAURANTS: "restaurant planning",
        INTENT_MICHELIN_RESTAURANTS: "fine-dining planning",
        INTENT_ATTRACTIONS: "sightseeing plans",
        INTENT_PLAN_DAY: "a full-day itinerary",
        INTENT_HOTELS: "hotel selection",
    }
    return intent_map.get(intent, (intent or "this trip").replace("_", " "))


def _intent_best_for_tags(intent: str, user_query: str) -> List[str]:
    low_q = (user_query or "").lower()
    tags: List[str] = []
    if intent == INTENT_NIGHTLIFE:
        tags.extend(["nightlife", "cocktails"])
        if "date" in low_q or "romantic" in low_q:
            tags.append("date-night")
    elif intent in {INTENT_RESTAURANTS, INTENT_MICHELIN_RESTAURANTS, INTENT_HIDDEN_GEMS, INTENT_LUXURY_VALUE}:
        tags.append("dining")
        if "michelin" in low_q or intent == INTENT_MICHELIN_RESTAURANTS:
            tags.append("fine-dining")
        if "value" in low_q:
            tags.append("value")
    elif intent in {INTENT_ATTRACTIONS, INTENT_PLAN_DAY}:
        tags.append("sightseeing")
    elif intent == INTENT_HOTELS:
        tags.append("stay")
    seen: set = set()
    deduped: List[str] = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    return deduped


def _best_for_angle(intent: str, user_query: str, candidate: Any) -> Optional[str]:
    tags = _intent_best_for_tags(intent, user_query)
    if hasattr(candidate, "tags"):
        try:
            for t in list(getattr(candidate, "tags") or []):
                if isinstance(t, str) and t.strip():
                    tags.append(t.strip().lower())
        except Exception:
            pass
    if not tags:
        return None
    normalized: List[str] = []
    seen: set = set()
    for tag in tags:
        cleaned = _clean_reason_text(str(tag)).lower().replace("_", " ").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    if not normalized:
        return None
    return ", ".join(normalized[:2])


def _contains_other_candidate_name(text: str, own_name: str, known_candidate_names: List[str]) -> bool:
    low_text = (text or "").lower()
    own = (own_name or "").lower()
    for name in known_candidate_names:
        low = (name or "").lower().strip()
        if not low or low == own:
            continue
        if low in low_text:
            return True
    return False


def _reason_guard(reason: str, own_name: str, known_candidate_names: List[str]) -> bool:
    text = (reason or "").strip()
    if not text:
        return False
    if _MARKDOWN_HEADING_PAT.search(text) or _BROKEN_MARKDOWN_TOKENS_PAT.search(text):
        return False
    if _MARKDOWN_LIST_PAT.search(text):
        return False
    if _RAW_URL_PAT.search(text):
        return False
    if _ARTICLE_FRAGMENT_PAT.search(text):
        return False
    if _contains_other_candidate_name(text, own_name, known_candidate_names):
        return False
    first_sentence = text.split(".")[0]
    if _ADDRESS_LIKE_PAT.search(first_sentence):
        return False
    if "google reviews" in first_sentence.lower() or "★" in first_sentence:
        return False
    low = text.lower()
    generic_match = any(p.search(low) for p in _GENERIC_REASON_PATTERNS)
    has_concrete_signal = bool(
        re.search(r"\b\d+(?:\.\d+)?\b", text)
        or re.search(r"\b\d{1,3}(?:,\d{3})+\s+reviews?\b", low)
        or any(
            tok in low
            for tok in (
                "rating",
                "reviews",
                "michelin",
                "cocktail bar",
                "restaurant",
                "cafe",
                "hotel",
                "attraction",
                "west loop",
                "river north",
                "lincoln park",
            )
        )
    )
    if generic_match and not has_concrete_signal:
        return False
    return True


# ── User-facing reason composition ───────────────────────────────────────────
#
# A premium concierge reason must:
#   • Match the venue's actual category (no "bar known for dining" leak).
#   • Never expose source/debug metadata.
#   • Never reference another candidate by name.
#   • Stay one short, polished sentence.

_CATEGORY_FALLBACK_REASON = {
    "restaurant": "Selected for this dining request based on verified restaurant details and available evidence.",
    "bar": "Selected for this bar request based on verified drinks-focused details and available evidence.",
    "cafe": "A strong pick for coffee, casual atmosphere, and consistently positive guest feedback.",
    "hotel": "A strong pick for location, comfort, and consistently positive guest feedback.",
    "attraction": "Selected for this attraction request based on verified place details and available evidence.",
    "place": "Selected for this request based on verified place details and available evidence.",
}

_CATEGORY_REASON_TEMPLATES = {
    "restaurant": {
        "premium": "A standout pick for polished plates, attentive service, and consistently strong diner feedback.",
        "good": "A reliable choice for well-reviewed food and a comfortable dining setting.",
    },
    "bar": {
        "premium": "A standout pick for crafted cocktails, lively atmosphere, and a buzzing late-night crowd.",
        "good": "Selected as a bar option based on verified details and available evidence.",
    },
    "cafe": {
        "premium": "A standout cafe for quality coffee, a relaxed setting, and warm guest feedback.",
        "good": "A solid choice for a casual coffee stop with consistently positive reviews.",
    },
    "hotel": {
        "premium": "A standout stay for location, comfort, and consistently glowing guest reviews.",
        "good": "A reliable choice for a comfortable stay with positive guest feedback.",
    },
    "attraction": {
        "premium": "A standout local choice with strong guest feedback for this kind of trip plan.",
        "good": "A solid choice with positive reviews and good fit for this trip plan.",
    },
    "place": {
        "premium": "A standout local choice with strong guest feedback for this kind of trip plan.",
        "good": "A solid choice with positive reviews and good fit for this trip plan.",
    },
}

_CATEGORY_LEAD_NOUN = {
    "restaurant": "restaurant",
    "bar": "bar",
    "cafe": "cafe",
    "hotel": "hotel",
    "attraction": "place",
    "place": "place",
}

# Phrases that, if produced by the editorial path, indicate a category mismatch
# (e.g. "bar" reason that talks about "dining"). When a venue is a bar we never
# allow restaurant-only language to leak in, and vice versa.
_RESTAURANT_ONLY_TOKENS = ("dining", "menu", "tasting menu", "chef", "cuisine", "plates")
_BAR_ONLY_TOKENS = ("cocktail", "nightlife", "speakeasy", "late-night", "late night", "lounge", "bartender")
_CAFE_ONLY_TOKENS = ("espresso", "latte", "barista", "coffee bar", "pastry", "pastries")


def _normalize_place_category(
    types: List[str],
    candidate: Any = None,
    *,
    intent: Optional[str] = None,
    user_query: str = "",
) -> str:
    """Return a canonical user-facing category from Google place types.

    Google primary types are canonical; candidate-provided cuisine/category is
    only used as a last-resort hint when Google doesn't classify.
    """
    normalized_types = [(t or "").lower() for t in (types or [])]
    blob = " ".join(normalized_types)
    primary_type = normalized_types[0] if normalized_types else ""
    query_category = _derive_query_category(intent or "", user_query or "")
    restaurant_query = query_category in {"restaurant", "brunch_cafe"} or intent == INTENT_MICHELIN_RESTAURANTS
    has_restaurant_signal = any(tok in blob for tok in ("restaurant", "food", "meal_takeaway", "meal_delivery"))
    has_bar_signal = any(tok in blob for tok in ("bar", "night_club", "cocktail_bar"))
    if "lodging" in blob or "hotel" in blob:
        return "hotel"
    if restaurant_query and has_restaurant_signal:
        # Dinner/restaurant intent should stay restaurant-first unless Google
        # clearly marks the place as bar-only.
        if primary_type in {"bar", "night_club", "cocktail_bar"} and not has_restaurant_signal:
            return "bar"
        return "restaurant"
    if has_bar_signal:
        return "bar"
    if "cafe" in blob or "coffee_shop" in blob or "bakery" in blob:
        return "cafe"
    if "restaurant" in blob or "meal_takeaway" in blob or "meal_delivery" in blob or "food" in blob:
        return "restaurant"
    if any(tok in blob for tok in ("museum", "park", "tourist_attraction", "art_gallery", "landmark", "zoo", "aquarium")):
        return "attraction"
    if not (types or []) and candidate is not None:
        cuisine = getattr(candidate, "cuisine", None)
        category = getattr(candidate, "category", None)
        hint = f"{cuisine or ''} {category or ''}".lower()
        if any(tok in hint for tok in ("bar", "cocktail", "lounge", "nightclub")):
            return "bar"
        if any(tok in hint for tok in ("cafe", "coffee", "bakery")):
            return "cafe"
        if any(tok in hint for tok in ("hotel", "stay", "resort", "inn")):
            return "hotel"
        if cuisine or category:
            return "restaurant" if cuisine else "attraction"
    return "place"


def _category_label(category: str, candidate: Any = None) -> str:
    """Return the short user-facing label shown under the place name."""
    if category == "restaurant":
        cuisine = getattr(candidate, "cuisine", None) if candidate is not None else None
        if cuisine and isinstance(cuisine, str) and cuisine.strip():
            cuisine_clean = cuisine.strip()
            if cuisine_clean.lower() in {"cocktail bar", "bar", "nightclub", "lounge"}:
                return "Restaurant"
            return cuisine_clean.title()
        return "Restaurant"
    if category == "bar":
        return "Cocktail Bar"
    if category == "cafe":
        return "Cafe"
    if category == "hotel":
        return "Hotel"
    if category == "attraction":
        attraction_cat = getattr(candidate, "category", None) if candidate is not None else None
        if attraction_cat and isinstance(attraction_cat, str) and attraction_cat.strip():
            return attraction_cat.strip().title()
        return "Attraction"
    return "Place"


def _category_intent_mismatch(reason_text: str, category: str) -> bool:
    """Reject reasons that mix mismatched category language."""
    low = (reason_text or "").lower()
    if category == "bar":
        return any(tok in low for tok in _RESTAURANT_ONLY_TOKENS)
    if category == "restaurant":
        return any(tok in low for tok in _BAR_ONLY_TOKENS)
    if category == "cafe":
        return any(tok in low for tok in _BAR_ONLY_TOKENS)
    return False


def _reason_quality_tier(rating: Optional[float], review_count: Optional[int]) -> str:
    if rating is None:
        return "default"
    r = float(rating)
    rc = int(review_count or 0)
    if r >= 4.5 and rc >= 200:
        return "premium"
    if r >= 4.2 and rc >= 50:
        return "good"
    return "default"


def _safe_google_only_reason(
    name: str,
    *,
    category: str,
    location: Optional[str],
    rating: Optional[float],
    review_count: Optional[int],
) -> str:
    del name, location, rating, review_count
    return _CATEGORY_FALLBACK_REASON.get(category, _CATEGORY_FALLBACK_REASON["place"])


def _validate_or_fallback_reason(
    reason_text: str,
    *,
    category: str,
    own_name: str,
    known_candidate_names: List[str],
) -> Tuple[str, str]:
    """Validation layer for deterministic copy; fallback on any mismatch."""
    reason = (reason_text or "").strip()
    if not reason:
        return _CATEGORY_FALLBACK_REASON.get(category, _CATEGORY_FALLBACK_REASON["place"]), "fallback"
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", reason, maxsplit=1)
    first_sentence = (parts[0] if parts else reason).strip()
    if not first_sentence:
        return _CATEGORY_FALLBACK_REASON.get(category, _CATEGORY_FALLBACK_REASON["place"]), "fallback"
    if first_sentence[-1] not in ".!?":
        reason = first_sentence + "."
    else:
        reason = first_sentence
    if not _reason_guard(reason, own_name, known_candidate_names):
        return _CATEGORY_FALLBACK_REASON.get(category, _CATEGORY_FALLBACK_REASON["place"]), "fallback"
    if _category_intent_mismatch(reason, category):
        return _CATEGORY_FALLBACK_REASON.get(category, _CATEGORY_FALLBACK_REASON["place"]), "fallback"
    return reason, "deterministic_validated"


def _category_fit_score(intent: str, user_query: str, verification: "GooglePlaceVerification") -> float:
    blob = " ".join((t or "").lower() for t in (verification.types or []))
    qcat = _derive_query_category(intent, user_query)
    if qcat == "nightlife_bar":
        if any(tok in blob for tok in ("cocktail_bar", "bar", "night_club")):
            return 1.0
        if "restaurant" in blob:
            return 0.35
        return 0.1
    if qcat == "brunch_cafe":
        score = 0.0
        if any(tok in blob for tok in ("cafe", "coffee_shop", "bakery", "breakfast_restaurant", "brunch_restaurant")):
            score += 0.75
        if "restaurant" in blob or "food" in blob:
            score += 0.25
        if any(tok in blob for tok in ("bar", "night_club", "liquor_store", "steak_house")):
            score -= 0.7
        return max(0.0, min(1.0, score))
    if qcat == "restaurant":
        if any(tok in blob for tok in ("restaurant", "food", "meal_takeaway")):
            return 0.9
        if any(tok in blob for tok in ("cafe", "bakery", "coffee_shop")):
            return 0.75
        if any(tok in blob for tok in ("bar", "night_club")):
            return 0.2
        return 0.4
    return 0.6


def _bayesian_google_score(rating: Optional[float], review_count: Optional[int]) -> float:
    if rating is None:
        return 0.0
    v = float(max(0, review_count or 0))
    m = 80.0
    c = 4.0
    r = float(rating)
    return ((v / (v + m)) * r) + ((m / (v + m)) * c)


def build_place_reason(
    *,
    candidate_name: str,
    user_query: str,
    intent: str,
    candidate: Any,
    verified_place: GooglePlaceVerification,
    known_candidate_names: Optional[List[str]] = None,
) -> Tuple[str, str]:
    """Compose a clean, premium concierge reason for a Google-verified place.

    Rules:
      • Never combines the venue's category with mismatched intent vocabulary.
      • Never references another candidate by name.
      • Never exposes source/debug metadata.
      • Falls back to a category-appropriate safe sentence on any uncertainty.
    """
    name = verified_place.name or candidate_name or "This place"
    category = _normalize_place_category(
        verified_place.types,
        candidate,
        intent=intent,
        user_query=user_query,
    )
    rating = verified_place.rating
    review_count = verified_place.user_rating_count
    category_fit = _category_fit_score(intent, user_query, verified_place)
    evidence_reason = None
    source_ev = getattr(candidate, "source_evidence", None)
    if source_ev is not None:
        evidence_reason = _sanitize_reason_evidence_text(
            str(getattr(source_ev, "source_reason", None) or getattr(source_ev, "source_evidence", None) or ""),
            own_name=name,
            known_candidate_names=known_candidate_names or [],
            max_len=120,
        )
    bits: List[str] = []
    if _derive_query_category(intent, user_query) == "brunch_cafe":
        bits.append("Strong brunch/cafe fit")
    elif intent == INTENT_NIGHTLIFE:
        bits.append("Strong cocktail/nightlife fit")
    if rating is not None:
        if review_count and int(review_count) > 0:
            bits.append(f"Rated {float(rating):.1f} across {int(review_count):,} reviews")
        else:
            bits.append(f"Rated {float(rating):.1f}")
    if evidence_reason:
        bits.append(evidence_reason)
    if category_fit >= 0.45 and bits:
        candidate_reason = ". ".join(bits) + "."
    else:
        candidate_reason = _CATEGORY_FALLBACK_REASON.get(category, _CATEGORY_FALLBACK_REASON["place"])
    if not _reason_guard(candidate_reason, name, known_candidate_names or []):
        return _CATEGORY_FALLBACK_REASON.get(category, _CATEGORY_FALLBACK_REASON["place"]), "fallback"
    if _category_intent_mismatch(candidate_reason, category):
        return _CATEGORY_FALLBACK_REASON.get(category, _CATEGORY_FALLBACK_REASON["place"]), "fallback"
    return candidate_reason, ("deterministic_evidence" if evidence_reason else "deterministic_scoring")


def _format_meta_line(
    rating: Optional[float],
    review_count: Optional[int],
    address: Optional[str],
) -> Optional[str]:
    """Compose the subheader line: '★ 4.8 (9,483 reviews) · Address'."""
    parts: List[str] = []
    if rating is not None:
        rating_text = f"★ {float(rating):.1f}"
        if review_count and int(review_count) > 0:
            rating_text = f"{rating_text} ({int(review_count):,} reviews)"
        parts.append(rating_text)
    if address:
        parts.append(str(address).strip())
    if not parts:
        return None
    return " · ".join(parts)


def _build_supporting_details(
    venue: Any,
    verification: GooglePlaceVerification,
    *,
    why_pick: Optional[Any] = None,
    intent: Optional[str] = None,
    user_query: str = "",
) -> PlaceSupportingDetails:
    """Build the clean, user-facing display payload.

    Internal metadata (editorial_mentions, source tags, evidence counts, source
    badges) is intentionally NOT exposed here. Those remain on the venue model
    for backend scoring/diagnostics only.
    """
    details = PlaceSupportingDetails()
    if verification.rating is not None:
        details.rating = f"{verification.rating:.1f}"
    if verification.user_rating_count is not None:
        details.review_count = int(verification.user_rating_count)
    if verification.formatted_address:
        details.address = verification.formatted_address
    details.meta_line = _format_meta_line(
        verification.rating,
        verification.user_rating_count,
        verification.formatted_address,
    )
    category = _normalize_place_category(
        verification.types,
        venue,
        intent=intent,
        user_query=user_query,
    )
    details.category_label = _category_label(category, venue)
    if why_pick:
        details.why_pick = why_pick
    return details


def _reason_mentions_other_candidate(reason: str, own_name: str, known_candidate_names: List[str]) -> bool:
    low_reason = (reason or "").lower()
    own = (own_name or "").lower()
    for candidate in known_candidate_names:
        candidate_low = (candidate or "").lower()
        if not candidate_low or candidate_low == own:
            continue
        if candidate_low in low_reason:
            return True
    return False


def _strip_publisher(title: str) -> str:
    """Remove trailing '— Publisher' / '| Publisher' fragments from titles."""
    if not title:
        return title
    for sep in (" | ", " - ", " — ", " – "):
        if sep in title:
            head, _ = title.split(sep, 1)
            if len(head) >= 4:
                return head.strip()
    return title.strip()


def _normalize_source_title(title: str) -> str:
    cleaned = _strip_publisher(title or "")
    cleaned = _NOISY_TITLE_SUFFIX_PAT.sub("", cleaned).strip(" -–—|:;,()")
    if not cleaned:
        return ""
    letters = [ch for ch in cleaned if ch.isalpha()]
    if letters:
        uppercase_ratio = sum(1 for ch in letters if ch.isupper()) / max(1, len(letters))
        if uppercase_ratio >= 0.7:
            cleaned = cleaned.title()
    cleaned = _WHITESPACE_PAT.sub(" ", cleaned).strip()
    return cleaned


def _source_quality_tier(url: str, title: str, snippet: str, classification: str) -> str:
    host = _SOURCE_HOST_STRIP_PAT.sub("", (urlparse(url).netloc or "").lower())
    lower_title = (title or "").lower()
    lower_snippet = (snippet or "").lower()
    text = f"{lower_title}\n{lower_snippet}"

    if classification == "venue_place" and host:
        if any(marker in host for marker in _CORROBORATION_ONLY_HOSTS):
            return "corroboration"
        if any(host == h or host.endswith(f".{h}") for h in _HIGH_AUTHORITY_EDITORIAL_HOSTS):
            return "editorial"
        if any(host == h or host.endswith(f".{h}") for h in _RESTAURANT_PLATFORM_HOSTS):
            return "platform"
        # For direct venue pages on non-directory hosts, treat as primary.
        return "official"

    if any(host == h or host.endswith(f".{h}") for h in _HIGH_AUTHORITY_EDITORIAL_HOSTS):
        return "editorial"
    if any(host == h or host.endswith(f".{h}") for h in _RESTAURANT_PLATFORM_HOSTS):
        return "platform"
    if any(marker in host for marker in _CORROBORATION_ONLY_HOSTS):
        return "corroboration"
    if _TOP_LISTICLE_TITLE_PAT.search(lower_title) or any(tok in text for tok in ("top 10", "best of", "directory")):
        return "weak"
    if len(lower_snippet.strip()) < 70:
        return "weak"
    return "standard"


def _quality_weight(tier: str) -> float:
    return {
        "official": 1.0,
        "editorial": 0.94,
        "platform": 0.88,
        "standard": 0.8,
        "corroboration": 0.72,
        "weak": 0.58,
    }.get(tier, 0.75)


def _extract_neighborhood(text: str, destination: str) -> Optional[str]:
    if not text:
        return None
    m = _NEIGHBORHOOD_HINT.search(text)
    if not m:
        return None
    candidate = m.group(2).strip()
    # Avoid echoing the destination back.
    if destination and candidate.lower() == destination.lower():
        return None
    return candidate


def _extract_candidate_neighborhood(candidate: str, text: str, destination: str) -> Optional[str]:
    """Extract neighborhood signal near the specific candidate mention."""
    if not text:
        return None
    if not candidate:
        return _extract_neighborhood(text, destination)
    low_text = text.lower()
    idx = low_text.find(candidate.lower())
    if idx < 0:
        return None
    window = text[max(0, idx - 100) : idx + len(candidate) + 140]
    return _extract_neighborhood(window, destination)


def _clean_reason_text(text: str) -> str:
    clean = (text or "").strip()
    if not clean:
        return ""
    clean = _BROKEN_MARKDOWN_TOKENS_PAT.sub(" ", clean)
    clean = _LEADING_LIST_NUMBER_PAT.sub("", clean)
    clean = _WHITESPACE_PAT.sub(" ", clean).strip(" -–—|:,;")
    clean = _DANGLING_YEAR_PAREN_PAT.sub("", clean).strip(" -–—|:,;()")
    if not clean:
        return ""
    if clean.lower().startswith("why this pick"):
        clean = clean.split(":", 1)[-1].strip()
    if len(clean) <= 2 or re.fullmatch(r"\d+[.)]?", clean):
        return ""
    return clean


def _dedupe_repeated_words(text: str) -> str:
    words = [w for w in (text or "").split(" ") if w]
    if not words:
        return ""
    out: List[str] = []
    prev = ""
    for w in words:
        low = w.lower()
        if low == prev:
            continue
        out.append(w)
        prev = low
    return " ".join(out)


def _sanitize_reason_evidence_text(
    text: str,
    *,
    own_name: str,
    known_candidate_names: Optional[List[str]],
    max_len: int = 160,
) -> Optional[str]:
    clean = (text or "").strip()
    if not clean:
        return None
    if _REASON_ARTIFACT_PAT.search(clean):
        return None
    clean = _HTML_TAG_PAT.sub(" ", clean)
    clean = re.sub(r"^\s{0,3}#{1,6}\s*", " ", clean, flags=re.MULTILINE)
    clean = re.sub(r"^\s*(?:[-*]|\d{1,3}[.)])\s+", " ", clean, flags=re.MULTILINE)
    clean = re.sub(r"\[[^\]]*\]", " ", clean)
    clean = clean.replace("…", " ").replace("...", " ")
    clean = _clean_reason_text(clean)
    clean = _dedupe_repeated_words(clean)
    if not clean:
        return None
    if len(clean) > max_len:
        return None
    if _contains_other_candidate_name(clean, own_name, known_candidate_names or []):
        return None
    if _reason_guard(clean, own_name, known_candidate_names or []):
        return clean
    return None


def _build_summary(snippet: str, fallback: str = "") -> str:
    s = (snippet or "").strip()
    if not s:
        return fallback

    s = _MARKDOWN_HEADING_PAT.sub("", s)
    s = s.replace("`", " ").replace("|", " ")
    s = _SYMBOL_RUN_PAT.sub(r"\1\1", s)
    s = _WHITESPACE_PAT.sub(" ", s).strip(" -–—|:;,.")

    lowered = s.lower()
    if any(p.search(s) for p in _BOILERPLATE_PATTERNS):
        s = ""
    elif any(marker in lowered for marker in _LOW_QUALITY_MARKERS):
        s = ""

    if len(s) > 320:
        s = s[:317].rsplit(" ", 1)[0].rstrip() + "…"

    final_text = _clean_reason_text(s or fallback)
    return final_text or fallback


def _is_article_like(title: str, snippet: str, url: str) -> bool:
    text = f"{title}\n{snippet}"
    lower_url = (url or "").lower()
    if _ARTICLE_PREFIX_HINT.match(title or ""):
        return True
    if _ARTICLE_HINT.search(text):
        return True
    return any(
        token in lower_url
        for token in ("/blog", "/guide", "/guides", "/best-", "/top-", "/things-to-do", "/directory")
    )


def _looks_like_neighborhood_source(title: str, snippet: str) -> bool:
    text = f"{title}\n{snippet}".lower()
    return any(kw in text for kw in ("neighborhood", "neighbourhood", "district", "area", "where to stay"))


def _category_signal(intent: str, text: str) -> bool:
    lower = (text or "").lower()
    if intent == INTENT_HOTELS:
        return any(kw in lower for kw in ("hotel", "resort", "inn", "suite", "stay"))
    if intent in {INTENT_ATTRACTIONS, INTENT_PLAN_DAY}:
        return any(kw in lower for kw in ("museum", "park", "gallery", "attraction", "landmark", "tour"))
    if intent in {
        INTENT_RESTAURANTS,
        INTENT_HIDDEN_GEMS,
        INTENT_LUXURY_VALUE,
        INTENT_ROMANTIC,
        INTENT_FAMILY_FRIENDLY,
        INTENT_NIGHTLIFE,
        INTENT_MICHELIN_RESTAURANTS,
    }:
        return any(
            kw in lower
            for kw in (
                "restaurant",
                "dining",
                "bistro",
                "bar",
                "cocktail",
                "nightclub",
                "tavern",
                "speakeasy",
                "michelin",
                "eatery",
            )
        )
    return False


def _title_looks_like_venue_name(title: str) -> bool:
    if not title:
        return False
    if ":" in title:
        return False
    words = [w for w in re.split(r"\s+", title.strip()) if w]
    if not words or len(words) > 9:
        return False
    if _GENERIC_CANDIDATE_PAT.match(title):
        return False
    lower = title.lower()
    return not any(
        phrase in lower
        for phrase in ("best ", "top ", "guide", "things to", "where to", "ultimate guide", "directory", "list")
    )


def _has_location_signal(combined: str, neighborhood: Optional[str], destination: str) -> bool:
    if neighborhood:
        return True
    if _ADDRESS_HINT.search(combined or ""):
        return True
    return bool(destination and destination.lower() in (combined or "").lower())


def _classify_hit(title: str, snippet: str, url: str, *, intent: str, destination: str) -> str:
    combined = f"{title}\n{snippet}"
    if _is_article_like(title, snippet, url):
        return "article_listicle_blog_directory"
    if _looks_like_neighborhood_source(title, snippet):
        return "neighborhood_area"
    neighborhood = _extract_neighborhood(combined, destination)
    signals = 0
    title_is_venue_like = _title_looks_like_venue_name(title)
    if title_is_venue_like:
        signals += 1
    if _has_location_signal(combined, neighborhood, destination):
        signals += 1
    if _category_signal(intent, combined):
        signals += 1
    if title_is_venue_like:
        return "venue_place"
    if signals >= 2:
        return "venue_place"
    return "generic_info_source"


def _extract_venue_names_from_text(text: str) -> List[str]:
    """Extract candidate venue names from article/listicle snippet text."""
    if not text:
        return []
    candidates: List[str] = []
    seen: set = set()

    def _add(raw: str) -> None:
        name = raw.strip(" \t.,;:\'\"").strip("\u201c\u201d\u2018\u2019")
        low = name.lower()
        if 2 < len(name) <= 60 and low not in seen:
            seen.add(low)
            candidates.append(name)

    for m in _NUMBERED_ITEM_PAT.finditer(text):
        _add(m.group(1))
    for m in _PROPER_NOUN_DASH_PAT.finditer(text):
        _add(m.group(1))
    for m in _QUOTED_VENUE_PAT.finditer(text):
        _add(m.group(1))

    return candidates


def _extract_venue_names_with_rank(text: str) -> "List[Tuple[str, int]]":
    """Like _extract_venue_names_from_text but returns (name, 1-based-rank) tuples."""
    if not text:
        return []
    results: "List[Tuple[str, int]]" = []
    seen: set = set()

    def _add_ranked(raw: str, rank: int) -> None:
        name = raw.strip(" \t.,;:\'\"").strip("\u201c\u201d\u2018\u2019")
        low = name.lower()
        if 2 < len(name) <= 60 and low not in seen:
            seen.add(low)
            results.append((name, rank))

    # Numbered items with explicit rank capture.
    _num_rank_pat = re.compile(
        r"(?<![A-Za-z])(?P<num>\d{1,2})[.)]\s+(?P<name>[A-Z][A-Za-z\u2019\-\.& ]{2,50}?)"
        r"(?=\s*[\u2013\u2014\-]|\s*[\n:]|\s*\d{1,2}[.)]|\s*$)"
    )
    numbered_seen: set = set()
    for m in _num_rank_pat.finditer(text):
        name_raw = m.group("name")
        low = name_raw.strip().lower()
        if low not in numbered_seen:
            numbered_seen.add(low)
            _add_ranked(name_raw, int(m.group("num")))

    for m in _PROPER_NOUN_DASH_PAT.finditer(text):
        _add_ranked(m.group(1), 0)
    for m in _QUOTED_VENUE_PAT.finditer(text):
        _add_ranked(m.group(1), 0)

    return results


def _split_words(name: str) -> List[str]:
    return [w for w in re.split(r"\s+", (name or "").strip()) if w]


def _looks_phrase_like_candidate(name: str) -> bool:
    words = _split_words(name)
    if not words:
        return True
    lowered = [w.lower() for w in words]
    if len(words) > 6:
        return True
    if any(w in _NAME_LINKER_WORDS for w in lowered):
        return True
    return False


def _looks_like_glued_candidate(name: str) -> bool:
    words = _split_words(name)
    if len(words) < 3:
        return False
    # Common bad pattern: one venue-like token followed by another title-cased phrase.
    if len(words) == 3 and words[1].lower() == "the" and words[0][:1].isupper() and words[2][:1].isupper():
        return True
    # "… Restaurant Bub City" style joins.
    for idx in range(1, len(words) - 1):
        if words[idx].lower() in {"restaurant", "bar", "hotel", "inn", "tavern"} and words[idx + 1][:1].isupper():
            return True
    # Long all-titlecase runs are often two names glued together.
    capitalized = sum(1 for w in words if w[:1].isupper() or w in {"&"})
    if len(words) >= 4 and capitalized >= len(words) - 1 and _looks_phrase_like_candidate(name):
        return True
    return False


def _overlap_contains(a: str, b: str) -> bool:
    low_a = f" {a.lower()} "
    low_b = f" {b.lower()} "
    return low_a in low_b or low_b in low_a


def _name_cleanliness_score(name: str) -> int:
    score = 100
    words = _split_words(name)
    if len(words) <= 3:
        score += 8
    if len(words) >= 6:
        score -= 10
    if _looks_phrase_like_candidate(name):
        score -= 12
    if _looks_like_glued_candidate(name):
        score -= 25
    return score


def _prefer_cleaner_overlap(existing_name: str, candidate_name: str) -> str:
    existing_score = _name_cleanliness_score(existing_name)
    candidate_score = _name_cleanliness_score(candidate_name)
    if candidate_score > existing_score:
        return candidate_name
    if existing_score > candidate_score:
        return existing_name
    return min((existing_name, candidate_name), key=lambda n: len(n))


def _dedupe_overlapping_venues(items: List[Any]) -> List[Any]:
    deduped: List[Any] = []
    for item in items:
        name = getattr(item, "name", "").strip()
        if not name:
            continue
        replaced = False
        for idx, kept in enumerate(deduped):
            kept_name = getattr(kept, "name", "").strip()
            if not kept_name:
                continue
            if name.lower() == kept_name.lower():
                replaced = True
                break
            if _overlap_contains(name, kept_name):
                preferred = _prefer_cleaner_overlap(kept_name, name)
                if preferred.lower() == name.lower():
                    deduped[idx] = item
                replaced = True
                break
        if not replaced:
            deduped.append(item)
    return deduped


def _final_hard_filter_closed_venues(
    venues: List[Any],
    *,
    kind_label: str,
    research_sources: List[UnifiedResearchSourceResult],
) -> List[Any]:
    """Final guard: never return closed-signal items as addable venues."""
    def _read_field(record: Any, field: str, fallback: Any = "") -> Any:
        if isinstance(record, dict):
            return record.get(field, fallback)
        return getattr(record, field, fallback)

    filtered: List[Any] = []
    for venue in venues:
        text_blob = "\n".join([
            str(_read_field(venue, "name", "") or ""),
            str(_read_field(venue, "title", "") or ""),
            str(_read_field(venue, "summary", "") or ""),
            str(_read_field(venue, "description", "") or ""),
            str(_read_field(venue, "snippet", "") or ""),
            str(_read_field(venue, "reason", "") or ""),
            str(_read_field(venue, "source", "") or ""),
            str(_read_field(venue, "source_text", "") or ""),
            str(_read_field(venue, "sourceText", "") or ""),
            str(_read_field(venue, "raw_text", "") or ""),
            str(_read_field(venue, "url", "") or ""),
            str(_read_field(venue, "source_url", "") or ""),
            str(_read_field(venue, "sourceUrl", "") or ""),
            str(_read_field(venue, "raw", "") or ""),
        ])
        if _looks_closed(text_blob):
            research_sources.append(
                UnifiedResearchSourceResult(
                    title=str(_read_field(venue, "name", f"Closed {kind_label}") or f"Closed {kind_label}"),
                    source=str(_read_field(venue, "source", "Live search") or "Live search"),
                    source_type="generic_info_source",
                    summary=_closed_research_summary(str(_read_field(venue, "name", "") or "")),
                    source_url=_read_field(venue, "source_url", None) or _read_field(venue, "sourceUrl", None),
                    neighborhood=_read_field(venue, "neighborhood", None) or _read_field(venue, "area_label", None),
                    last_verified_at=_read_field(venue, "last_verified_at", None) or _read_field(venue, "lastVerifiedAt", None),
                    confidence=_read_field(venue, "confidence", None),
                    trip_addable=False,
                )
            )
            continue
        filtered.append(venue)
    return filtered


def _result_category_label(intent: str) -> str:
    if intent == INTENT_HOTELS:
        return "hotel"
    if intent in {INTENT_ATTRACTIONS, INTENT_PLAN_DAY}:
        return "attraction"
    if intent == INTENT_NIGHTLIFE:
        return "nightlife"
    return "restaurant"


def _context_type_hint(snippet: str) -> Optional[str]:
    low = (snippet or "").lower()
    if "speakeasy" in low:
        return "speakeasy"
    if "cocktail bar" in low:
        return "cocktail bar"
    if "jazz bar" in low or "jazz club" in low:
        return "jazz club"
    if "brasserie" in low:
        return "French brasserie"
    if "tasting menu" in low:
        return "tasting-menu destination"
    if "omakase" in low:
        return "omakase restaurant"
    if "michelin" in low:
        return "Michelin dining"
    if "hotel" in low:
        return "hotel"
    return None


def _query_explicitly_requests_chains(user_query: str) -> bool:
    low = (user_query or "").lower()
    if "chain" in low:
        return True
    return any(name in low for name in _CHAIN_RESTAURANT_NAMES)


def _is_common_chain_venue(name: str) -> bool:
    low = (name or "").lower()
    return any(chain in low for chain in _CHAIN_RESTAURANT_NAMES)


def _chain_penalty(name: str, user_query: str) -> float:
    if _query_explicitly_requests_chains(user_query):
        return 0.0
    if _is_common_chain_venue(name):
        return 0.18
    return 0.0


def _build_extracted_reason(
    *,
    candidate_name: str,
    source_title: str,
    intent: str,
    destination: str,
    neighborhood: Optional[str],
    snippet: str,
    quality_tier: str,
) -> Optional[str]:
    low_snippet = (snippet or "").lower()
    pieces: List[str] = []

    type_hint = _context_type_hint(snippet)
    has_cuisine_or_vibe = False
    if type_hint:
        pieces.append(type_hint)
        has_cuisine_or_vibe = True
    else:
        vibe_hint = next((kw for kw in _CUISINE_OR_VIBE_HINTS if kw in low_snippet), None)
        if vibe_hint:
            pieces.append(vibe_hint)
            has_cuisine_or_vibe = True

    price_or_value = bool(_PRICE_VALUE_HINT.search(snippet or ""))
    if price_or_value:
        pieces.append("price/value detail")

    award_signal = bool(_AWARD_HINT.search(snippet or ""))
    if award_signal:
        pieces.append("award-level recognition")

    luxury_signal = bool(_LUXURY_HINT.search(snippet or ""))
    if luxury_signal and intent in {INTENT_LUXURY_VALUE, INTENT_MICHELIN_RESTAURANTS, INTENT_ROMANTIC}:
        pieces.append("fine-dining signal")

    intent_match_signal = False
    if intent == INTENT_NIGHTLIFE and any(kw in low_snippet for kw in ("cocktail", "nightlife", "bar", "jazz", "club")):
        intent_match_signal = True
    if intent in {INTENT_LUXURY_VALUE, INTENT_MICHELIN_RESTAURANTS} and (
        price_or_value or award_signal or luxury_signal
    ):
        intent_match_signal = True

    cleaned_neighborhood = (neighborhood or "").strip(" .,-")
    if destination and cleaned_neighborhood and cleaned_neighborhood.lower() == destination.lower():
        cleaned_neighborhood = ""
    has_specific_detail = bool(has_cuisine_or_vibe or cleaned_neighborhood or price_or_value or award_signal or intent_match_signal)
    if not has_specific_detail:
        if intent == INTENT_NIGHTLIFE:
            return "Mentioned in current nightlife research, but details need confirmation."
        return None

    if intent == INTENT_LUXURY_VALUE and not (price_or_value or award_signal or luxury_signal or quality_tier == "editorial"):
        return None
    if intent == INTENT_MICHELIN_RESTAURANTS and not (award_signal or luxury_signal or quality_tier == "editorial"):
        return None

    lead = f"{candidate_name} stands out"
    if type_hint:
        lead = f"{candidate_name} is noted as a {type_hint}"
    reason = lead
    if cleaned_neighborhood:
        reason = f"{reason} in {cleaned_neighborhood}"
    if price_or_value:
        reason = f"{reason} with clear value or pricing context"
    if award_signal:
        reason = f"{reason} and recognized by Michelin/awards"
    reason = f"{reason}."
    if source_title:
        safe_source_title = _clean_reason_text(source_title)
        if safe_source_title:
            reason = f"{reason} Backed by coverage in {safe_source_title}."
    if quality_tier == "weak":
        if intent == INTENT_NIGHTLIFE:
            reason = "Mentioned in current nightlife research, but details need confirmation."
        else:
            reason = f"{reason} Verify current reviews and value before booking."
    return _clean_reason_text(reason)


def _extracted_ai_score(quality_tier: str) -> float:
    return {
        "editorial": 0.9,
        "official": 0.88,
        "platform": 0.84,
        "standard": 0.78,
        "corroboration": 0.72,
        "weak": 0.62,
    }.get(quality_tier, 0.75)


def _recover_candidate_name(raw: str) -> Optional[str]:
    candidate = (raw or "").strip(" \t.,;:\"'“”‘’")
    if not candidate:
        return None
    words = [w for w in re.split(r"\s+", candidate) if w]
    if not words:
        return None
    if words[0].lower() in _CONTEXT_START_WORDS:
        tail = " ".join(words[1:]).strip()
        if not tail:
            return None
        tail_words = [w for w in re.split(r"\s+", tail) if w]
        while tail_words and tail_words[0].lower() in _TRAILING_CONTEXT_WORDS:
            tail_words = tail_words[1:]
        tail = " ".join(tail_words).strip()
        if not tail:
            return None
        match = re.search(
            r"([A-Z][A-Za-z'\-&\.]+(?:\s+(?:[A-Z][A-Za-z'\-&\.]+|&|of|the)){0,4})$",
            tail,
        )
        if not match:
            return None
        return match.group(1).strip()
    return candidate


def _is_venue_like_proper_noun(name: str) -> bool:
    if not _title_looks_like_venue_name(name):
        return False
    words = [w for w in re.split(r"\s+", (name or "").strip()) if w]
    if not words:
        return False
    content_words = [w for w in words if w.lower() not in {"the", "of", "&", "and"}]
    return bool(content_words) and any(w[:1].isupper() for w in content_words)


def _candidate_has_category_nearby(candidate: str, context: str, intent: str) -> bool:
    if not candidate or not context:
        return False
    low_context = context.lower()
    idx = low_context.find(candidate.lower())
    if idx < 0:
        return _category_signal(intent, context)
    window = context[max(0, idx - 120) : idx + len(candidate) + 120]
    return _category_signal(intent, window)


def _trusted_source_signal(url: str, title: str, snippet: str) -> bool:
    host = (urlparse(url).netloc or "").lower()
    text = f"{host} {title} {snippet}"
    return bool(_TRUSTED_EDITORIAL_SOURCE_HINT.search(text))


def _direct_place_source_signal(url: str, snippet: str) -> bool:
    if _DIRECT_PLACE_SOURCE_HINT.search(url or ""):
        return True
    return bool(_ADDRESS_HINT.search(snippet or ""))


def _appears_in_clean_list(candidate: str, snippet: str) -> bool:
    if not candidate or not snippet:
        return False
    pat = re.compile(_CLEAN_LIST_NAME_TMPL.format(name=re.escape(candidate)))
    return bool(pat.search(snippet))


def _validate_venue_candidate(
    name: str,
    context: str,
    *,
    intent: str,
    destination: str,
    title: str = "",
    url: str = "",
    snippet: str = "",
    corroborating_hits: int = 1,
) -> Tuple[bool, str, List[str]]:
    """Return (is_valid, normalized_name, evidence_reasons)."""
    normalized = _recover_candidate_name(name) or ""
    evidence: List[str] = []
    if not normalized or len(normalized.strip()) < 3:
        return False, "", evidence
    if _GENERIC_CANDIDATE_PAT.match(normalized):
        return False, "", evidence

    words = [w for w in re.split(r"\s+", normalized.strip()) if w]
    if words and words[0].lower() in _CONTEXT_START_WORDS:
        return False, "", evidence
    if not _is_venue_like_proper_noun(normalized):
        return False, "", evidence
    if _looks_phrase_like_candidate(normalized) or _looks_like_glued_candidate(normalized):
        return False, "", evidence
    has_proper = True
    has_cat = _candidate_has_category_nearby(normalized, context, intent)
    has_loc = bool(
        _ADDRESS_HINT.search(context)
        or (destination and destination.lower() in context.lower())
        or _NEIGHBORHOOD_HINT.search(context)
    )
    has_trusted_source = _trusted_source_signal(url, title, snippet)
    in_clean_list = _appears_in_clean_list(normalized, snippet) or _appears_in_clean_list(normalized, context)
    has_direct_place = _direct_place_source_signal(url, context)

    if has_proper:
        evidence.append("venue-like proper noun name")
    if has_cat:
        evidence.append("category signal near candidate")
    if has_loc:
        evidence.append("location or neighborhood signal")
    if has_trusted_source:
        evidence.append("trusted source signal")
    if in_clean_list:
        evidence.append("clean list pattern")
    if corroborating_hits > 1:
        evidence.append("multiple corroborating hits")

    strong_signal_count = sum((has_proper, has_cat, has_loc, has_trusted_source, in_clean_list))
    if strong_signal_count < 2:
        return False, normalized, evidence

    if len(words) == 1:
        low = words[0].lower()
        if low in _AMBIGUOUS_SINGLE_WORD_CANDIDATES:
            if not (has_direct_place or corroborating_hits > 1):
                return False, normalized, evidence
        elif strong_signal_count < 3 and not (has_direct_place or corroborating_hits > 1):
            return False, normalized, evidence

    return True, normalized, evidence


# ── Verify-before-add helpers ────────────────────────────────────────────────

def _is_obvious_non_venue(name: str, destination: str) -> bool:
    """Return True for candidates that are clearly not venue names.

    Catches geographic names, promotional phrases, and '{destination} {generic}'
    patterns before they waste a verification API call.
    """
    if not name:
        return True
    low = name.lower().strip()
    if low in _OBVIOUS_NON_VENUE_LOWER:
        return True
    if destination and low == destination.lower():
        return True
    words = low.split()
    if not words:
        return True
    # "{Destination} {non-venue-word}" e.g. "Chicago Explore", "Chicago Guide"
    if len(words) >= 2 and destination:
        dest_words = destination.lower().split()
        if words[: len(dest_words)] == dest_words and words[-1] in _NON_VENUE_SUFFIX_WORDS:
            return True
    # Ends with a promotional/article word e.g. "Launch Special", "Summer Guide"
    if words[-1] in _NON_VENUE_SUFFIX_WORDS:
        return True
    return False


def _build_verification_query(candidate: str, destination: str, intent: str) -> str:
    """Build a focused second-pass query to verify a single candidate place."""
    if intent == INTENT_HOTELS:
        kind = "hotel"
    elif intent in {INTENT_ATTRACTIONS, INTENT_PLAN_DAY}:
        kind = "attraction"
    elif intent == INTENT_NIGHTLIFE:
        kind = "bar"
    else:
        kind = "restaurant"
    return f'"{candidate}" {destination} {kind}'


def _check_verification_hits(
    candidate: str,
    destination: str,
    hits: List[LiveSearchHit],
) -> VerificationResult:
    """Return VerificationResult from focused verification-search hits.

    A candidate is verified if any hit mentions the candidate name AND either:
    - the hit URL is from a known place platform (Yelp, TripAdvisor, etc.), or
    - the snippet contains a street address plus a location reference.
    """
    low_candidate = (candidate or "").lower()
    for hit in hits:
        combined = f"{hit.title}\n{hit.snippet}"
        low_combined = combined.lower()
        if low_candidate not in low_combined:
            continue
        url = hit.url or ""
        platform_hit = bool(
            _PLACE_PLATFORM_HINT.search(url) or _DIRECT_PLACE_SOURCE_HINT.search(url)
        )
        address_hit = bool(_ADDRESS_HINT.search(combined))
        location_hit = bool(
            destination and destination.lower() in low_combined
        ) or bool(_NEIGHBORHOOD_HINT.search(combined))
        if not platform_hit and _is_stale_operating_status_signal(combined, url):
            continue
        if platform_hit or (address_hit and location_hit):
            neighborhood = _extract_neighborhood(combined, destination)
            return VerificationResult(
                verified=True,
                source_url=url or None,
                category=_context_type_hint(hit.snippet),
                neighborhood=neighborhood,
                reason=_build_summary(hit.snippet)
                or f"Verified as a real place in {destination}.",
            )
    return VerificationResult(verified=False)


def _google_verification_for(
    name: str,
    google_verifications: Optional[Dict[str, GooglePlaceVerification]],
) -> Optional[GooglePlaceVerification]:
    if not google_verifications or not name:
        return None
    return google_verifications.get(name.lower())


def _is_listicle_like_text(value: str) -> bool:
    text = (value or "").lower()
    if not text:
        return False
    if re.search(r"\b(best|top)\s+\d+\b", text):
        return True
    if re.search(r"\b(top|best)\b.*\bin\b", text):
        return True
    return bool(re.search(r"\b(best|top|guide|listicle|things to do|where to)\b", text))


def _is_listicle_like_source(*, title: Optional[str], source_url: Optional[str]) -> bool:
    if _is_listicle_like_text(title or ""):
        return True
    lower_url = (source_url or "").lower()
    if not lower_url:
        return False
    if re.search(r"/(blog|blogs|guide|guides|list|lists|directory|roundup)/", lower_url):
        return True
    return any(token in lower_url for token in ("/best-", "/top-", "/things-to-do", "/where-to"))


def _google_reason_for_venue(
    *,
    verification: GooglePlaceVerification,
    intent: str,
    source_count: int = 0,
) -> str:
    type_blob = " ".join((verification.types or [])).lower()

    if intent == INTENT_NIGHTLIFE:
        guide_label = "cocktail-bar guide"
    elif intent == INTENT_HOTELS:
        guide_label = "hotel guide"
    elif intent in {INTENT_ATTRACTIONS, INTENT_PLAN_DAY}:
        guide_label = "local guide"
    elif intent == INTENT_MICHELIN_RESTAURANTS:
        guide_label = "dining guide"
    else:
        guide_label = "local guide"

    if source_count > 1:
        lead = f"Found in {source_count} trusted {guide_label}s and verified on Google"
    elif source_count == 1:
        lead = "Extracted from local guide; confirmed as an operational Google place"
    else:
        # Direct venue_place hit (not article-extracted)
        if "cocktail_bar" in type_blob or "bar" in type_blob:
            lead = "Confirmed as operational by Google (bar/nightlife types)"
        elif "lodging" in type_blob or "hotel" in type_blob:
            lead = "Confirmed as operational by Google (hotel/lodging types)"
        elif "restaurant" in type_blob or "food" in type_blob:
            lead = "Confirmed as operational by Google (dining types)"
        else:
            lead = "Confirmed as an operational Google place"

    bits: List[str] = [lead]
    if verification.rating is not None:
        bits.append(f"Google rating {verification.rating:.1f}")
    if verification.formatted_address:
        bits.append(f"at {verification.formatted_address}")
    return ". ".join(bits) + "."


def _apply_google_gate(
    venues: List[Any],
    *,
    google_verifications: Dict[str, GooglePlaceVerification],
    research_sources: List[UnifiedResearchSourceResult],
    kind_label: str,
    provider_label_default: str,
    intent: str,
    user_query: str,
    known_candidate_names: List[str],
    seen_place_ids: Optional[set] = None,
    corroboration_counter: Optional[Counter] = None,
) -> List[Any]:
    """Drop venues that don't pass Google Places verification — anything that
    isn't matched + OPERATIONAL with high/medium confidence is demoted to
    research_sources only.

    Cards that pass have ``google_verification`` attached, ``verified_place``
    forced to True, and richer fields (maps URI / website) populated from the
    Google match when the source didn't already provide them.

    ``seen_place_ids`` is a shared set across all three category lists so the
    same Google place_id cannot appear as both a direct hit and an article-
    extracted hit. ``corroboration_counter`` drives the "Found in N guides"
    copy in the card reason.
    """
    debug_mode = os.getenv("RESEARCH_ENGINE_DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}
    kept: List[Any] = []
    rejected_by_reason: Counter = Counter()
    for venue in venues:
        verification = _google_verification_for(getattr(venue, "name", ""), google_verifications)
        final_score = 0.0
        guard_ok: Optional[bool] = None
        rejection_reason: Optional[str] = None
        if _google_is_addable(verification):
            assert verification is not None  # for type checkers
            # Dedup by Google place_id — prevents the same venue appearing from
            # both a direct_place hit and an article-extracted candidate.
            pid = verification.provider_place_id
            if pid and seen_place_ids is not None:
                if pid in seen_place_ids:
                    # Already kept this exact Google place — increment mention_count
                    # on the first-kept card so the UI can show "Mentioned by N guides".
                    for existing in kept:
                        ev = getattr(existing, "source_evidence", None)
                        existing_gv = getattr(existing, "google_verification", None)
                        existing_pid = getattr(existing_gv, "provider_place_id", None) if existing_gv else None
                        if existing_pid == pid and ev is not None:
                            try:
                                ev.mention_count += 1
                            except Exception:
                                pass
                            break
                    continue
                seen_place_ids.add(pid)
            if not verification.provider_place_id:
                research_sources.append(
                    UnifiedResearchSourceResult(
                        title=str(getattr(venue, "name", f"Unverified {kind_label}") or f"Unverified {kind_label}"),
                        source=str(getattr(venue, "source", provider_label_default) or provider_label_default),
                        source_type="generic_info_source",
                        summary="Google result missing place identifier — research only.",
                        source_url=getattr(venue, "source_url", None),
                        neighborhood=getattr(venue, "neighborhood", None) or getattr(venue, "area_label", None),
                        last_verified_at=getattr(venue, "last_verified_at", None),
                        confidence=getattr(venue, "confidence", None),
                        trip_addable=False,
                    )
                )
                rejected_by_reason["missing_place_id"] += 1
                continue
            pyd = _to_pydantic_google_verification(verification)
            try:
                venue.google_verification = pyd
            except Exception:
                pass
            try:
                venue.verified_place = True
            except Exception:
                pass
            try:
                venue.source = "Google Places"
            except Exception:
                pass
            try:
                venue.name = verification.name or getattr(venue, "name", "")
            except Exception:
                pass
            try:
                venue.rating = verification.rating
            except Exception:
                pass
            try:
                venue.review_count = verification.user_rating_count
            except Exception:
                pass
            try:
                name_lower = (getattr(venue, "name", "") or "").lower()
                src_count = (corroboration_counter or {}).get(name_lower, 0)
                venue_source_ev = getattr(venue, "source_evidence", None)
                category_fit = _category_fit_score(intent, user_query, verification)
                if category_fit < 0.45:
                    rejected_by_reason["intent_category_mismatch"] += 1
                    research_sources.append(
                        UnifiedResearchSourceResult(
                            title=str(getattr(venue, "name", f"Off-intent {kind_label}") or f"Off-intent {kind_label}"),
                            source="Google Places",
                            source_type="generic_info_source",
                            summary="Google verified the place exists, but its category does not match this query intent.",
                            source_url=getattr(venue, "source_url", None) or verification.google_maps_uri,
                            neighborhood=getattr(venue, "neighborhood", None) or verification.formatted_address,
                            last_verified_at=getattr(venue, "last_verified_at", None),
                            confidence=getattr(venue, "confidence", None),
                            trip_addable=False,
                        )
                    )
                    continue
                reason, reason_source = build_place_reason(
                    candidate_name=getattr(venue, "name", "") or verification.name or "",
                    user_query=user_query,
                    intent=intent,
                    candidate=venue,
                    verified_place=verification,
                    known_candidate_names=known_candidate_names,
                )
                if _reason_mentions_other_candidate(reason, getattr(venue, "name", ""), known_candidate_names):
                    reason = _safe_google_only_reason(
                        verification.name or getattr(venue, "name", "This place"),
                        category="place",
                        location=verification.formatted_address,
                        rating=verification.rating,
                        review_count=verification.user_rating_count,
                    )
                if hasattr(venue, "summary"):
                    venue.summary = reason
                elif hasattr(venue, "description"):
                    venue.description = reason
                elif hasattr(venue, "reason"):
                    venue.reason = reason
                try:
                    venue.primary_reason = reason
                except Exception:
                    pass
                try:
                    venue.reason_source = reason_source
                except Exception:
                    pass
                clean_evidence: List[str] = []
                if venue_source_ev is not None:
                    for raw_ev in (
                        getattr(venue_source_ev, "source_reason", None),
                        getattr(venue_source_ev, "source_evidence", None),
                    ):
                        cleaned = _sanitize_reason_evidence_text(
                            str(raw_ev or ""),
                            own_name=getattr(venue, "name", ""),
                            known_candidate_names=known_candidate_names,
                            max_len=100,
                        )
                        if cleaned and cleaned not in clean_evidence:
                            clean_evidence.append(cleaned)
                clean_evidence = ensure_non_empty_evidence(
                    clean_evidence,
                    rating=verification.rating,
                    review_count=verification.user_rating_count,
                    neighborhood=getattr(venue, "neighborhood", None) or verification.formatted_address,
                    tags=getattr(venue, "tags", []),
                )
                category = _normalize_place_category(
                    verification.types,
                    venue,
                    intent=intent,
                    user_query=user_query,
                )
                why_pick_payload = build_why_pick(
                    place_name=getattr(venue, "name", "") or verification.name or "This place",
                    evidence=clean_evidence,
                    rating=verification.rating,
                    review_count=verification.user_rating_count,
                    category=category,
                    neighborhood=getattr(venue, "neighborhood", None) or verification.formatted_address,
                    cuisine=getattr(venue, "cuisine", None),
                    michelin_status=getattr(venue, "michelin_status", None),
                    user_query=user_query,
                    intent=intent,
                )
                reason, validation_source = _validate_or_fallback_reason(
                    why_pick_payload["why_pick"]["text"],
                    category=category,
                    own_name=getattr(venue, "name", ""),
                    known_candidate_names=known_candidate_names,
                )
                if (
                    intent == INTENT_MICHELIN_RESTAURANTS
                    and validation_source == "fallback"
                    and category == "restaurant"
                ):
                    michelin_status = getattr(venue, "michelin_status", None)
                    cuisine = getattr(venue, "cuisine", None)
                    neighborhood = getattr(venue, "neighborhood", None) or verification.formatted_address
                    if michelin_status or cuisine or neighborhood:
                        parts = [p for p in [michelin_status, cuisine, neighborhood] if p]
                        reason = (
                            f"{getattr(venue, 'name', '') or verification.name or 'This restaurant'} is a "
                            f"{', '.join(parts)} pick that fits this Michelin-focused request."
                        )
                        validation_source = "deterministic_validated"
                reason_source = (
                    why_pick_payload["why_pick"]["generation_method"]
                    if validation_source == "deterministic_validated"
                    else validation_source
                )
                try:
                    venue.evidence = clean_evidence[:2]
                except Exception:
                    pass
                guard_ok = _reason_guard(reason, getattr(venue, "name", ""), known_candidate_names)
                try:
                    venue.best_for_tags = _intent_best_for_tags(intent, user_query)
                except Exception:
                    pass
                try:
                    mention_count = getattr(venue_source_ev, "mention_count", 0) if venue_source_ev else 0
                    venue.evidence_count = int(max(0, mention_count))
                except Exception:
                    pass
                try:
                    venue.primary_reason = reason
                except Exception:
                    pass
                try:
                    venue.supporting_details = _build_supporting_details(
                        venue,
                        verification,
                        why_pick=reason,
                        intent=intent,
                        user_query=user_query,
                    )
                except Exception:
                    pass
                try:
                    badges = ["Google Verified"]
                    if verification.rating is not None:
                        badges.append("Google")
                    if src_count > 0:
                        badges.append("Editorial")
                    venue.source_badges = badges
                except Exception:
                    pass
                try:
                    base = _bayesian_google_score(verification.rating, verification.user_rating_count)
                    relevance = 0.25 if any(t in (user_query or "").lower() for t in _intent_best_for_tags(intent, user_query)) else 0.0
                    distance_hint = 0.2 if verification.formatted_address and getattr(venue, "neighborhood", None) else 0.0
                    evidence_bonus = min(0.3, 0.1 * float(max(0, src_count)))
                    venue.category_fit_score = round(category_fit, 4)
                    venue.ai_score = round((category_fit * 2.0) + base + relevance + distance_hint + evidence_bonus, 4)
                    final_score = float(venue.ai_score or 0.0)
                except Exception:
                    pass
                logger.info(
                    "reason_generation place=%s source=%s model=%s payload=intent:%s query:%s fit=%.2f",
                    getattr(venue, "name", ""),
                    reason_source,
                    "none",
                    intent,
                    _normalize_query(user_query)[:120],
                    category_fit,
                )
            except Exception:
                pass
            try:
                venue.verification_tier = "primary" if verification.confidence == "high" else "secondary"
            except Exception:
                pass
            # Prefer Google's first-party links when the article didn't have one.
            if verification.google_maps_uri:
                try:
                    venue.maps_link = verification.google_maps_uri
                except Exception:
                    pass
            if verification.formatted_address:
                try:
                    if hasattr(venue, "address"):
                        venue.address = verification.formatted_address
                    if hasattr(venue, "neighborhood"):
                        venue.neighborhood = verification.formatted_address
                    if hasattr(venue, "area_label"):
                        venue.area_label = verification.formatted_address
                except Exception:
                    pass
            if verification.website_uri:
                if hasattr(venue, "booking_link") and not getattr(venue, "booking_link", None):
                    try:
                        venue.booking_link = verification.website_uri
                    except Exception:
                        pass
                elif hasattr(venue, "booking_url") and not getattr(venue, "booking_url", None):
                    try:
                        venue.booking_url = verification.website_uri
                    except Exception:
                        pass
            kept.append(venue)
            if debug_mode and hash(getattr(venue, "name", "")) % 4 == 0:
                logger.debug(
                    "candidate_trace name=%s source_kind=%s google_status=%s rejection_reason=%s final_score=%.4f reason_guard=%s",
                    getattr(venue, "name", ""),
                    "verified_place",
                    getattr(verification, "business_status", None),
                    rejection_reason,
                    final_score,
                    guard_ok,
                )
            continue

        # Failed Google Places gate → demote to research source so the user
        # can still see the candidate as background research, but it is not
        # addable and never carries the LIVE/Operational badge.
        reason = (
            verification.failure_reason
            if verification is not None
            else "google_match_unavailable"
        )
        if verification is not None and verification.is_closed:
            summary = "Marked as closed by Google Places — not addable."
            rejected_by_reason["closed"] += 1
            rejection_reason = "closed"
        elif verification is None or not verification.matched:
            summary = "Not yet verified by Google Places — research only."
            rejected_by_reason["no_match"] += 1
            rejection_reason = "no_match"
        else:
            summary = f"Google Places match was below confidence threshold ({reason})."
            rejected_by_reason["low_confidence"] += 1
            rejection_reason = "low_confidence"

        source = str(getattr(venue, "source", provider_label_default) or provider_label_default)
        research_sources.append(
            UnifiedResearchSourceResult(
                title=str(getattr(venue, "name", f"Unverified {kind_label}") or f"Unverified {kind_label}"),
                source=source,
                source_type="generic_info_source",
                summary=summary,
                source_url=getattr(venue, "source_url", None),
                neighborhood=getattr(venue, "neighborhood", None) or getattr(venue, "area_label", None),
                last_verified_at=getattr(venue, "last_verified_at", None),
                confidence=getattr(venue, "confidence", None),
                trip_addable=False,
            )
        )
        logger.info(
            "rejected_candidate name=%s rejection_reason=%s",
            str(getattr(venue, "name", "") or ""),
            rejection_reason,
        )
        if debug_mode and hash(getattr(venue, "name", "")) % 4 == 0:
            logger.debug(
                "candidate_trace name=%s source_kind=%s google_status=%s rejection_reason=%s final_score=%.4f reason_guard=%s",
                getattr(venue, "name", ""),
                "research_only",
                getattr(verification, "business_status", None) if verification is not None else None,
                rejection_reason,
                final_score,
                guard_ok,
            )
    logger.info(
        "google_gate kind=%s kept=%d rejected=%d reasons=%s",
        kind_label,
        len(kept),
        sum(rejected_by_reason.values()),
        dict(rejected_by_reason),
    )
    return kept


def _to_pydantic_google_verification(
    verification: Optional[GooglePlaceVerification],
) -> Optional[GoogleVerification]:
    if verification is None:
        return None
    return GoogleVerification(
        provider=verification.provider,  # type: ignore[arg-type]
        provider_place_id=verification.provider_place_id,
        name=verification.name,
        formatted_address=verification.formatted_address,
        lat=verification.lat,
        lng=verification.lng,
        business_status=verification.business_status,
        google_maps_uri=verification.google_maps_uri,
        website_uri=verification.website_uri,
        rating=verification.rating,
        user_rating_count=verification.user_rating_count,
        types=list(verification.types or []),
        confidence=verification.confidence,  # type: ignore[arg-type]
        score=verification.score,
        reason=verification.reason,
        failure_reason=verification.failure_reason,
    )


def normalize_hits(
    hits: List[LiveSearchHit],
    *,
    intent: str,
    destination: str,
    user_query: str,
    max_per_kind: int = 8,
    verified_candidates: Optional[Dict[str, VerificationResult]] = None,
    google_verifications: Optional[Dict[str, GooglePlaceVerification]] = None,
) -> Dict[str, List[Any]]:
    """Convert raw provider hits into Concierge Unified result lists.

    Returns a dict with keys ``restaurants``, ``attractions``, ``hotels``.
    Closed venues are filtered out. Fields that are unavailable from the snippet
    (rating, review counts, exact address) are simply left as ``None`` rather
    than fabricated.
    """
    restaurants: List[UnifiedRestaurantResult] = []
    attractions: List[UnifiedAttractionResult] = []
    hotels: List[UnifiedHotelResult] = []
    research_sources: List[UnifiedResearchSourceResult] = []

    is_restaurant_intent = intent in {
        INTENT_RESTAURANTS,
        INTENT_HIDDEN_GEMS,
        INTENT_LUXURY_VALUE,
        INTENT_ROMANTIC,
        INTENT_FAMILY_FRIENDLY,
        INTENT_NIGHTLIFE,
        INTENT_MICHELIN_RESTAURANTS,
    }
    is_attraction_intent = intent in {INTENT_ATTRACTIONS, INTENT_PLAN_DAY}
    is_hotel_intent = intent == INTENT_HOTELS

    # Pre-compute corroboration counts once (how many article snippets mention
    # each candidate name). Used to boost ai_score and build reason copy.
    corroboration_counter: Counter = Counter()
    for _ah in hits:
        if _classify_hit(
            _strip_publisher(_ah.title),
            _ah.snippet,
            _ah.url,
            intent=intent,
            destination=destination,
        ) != "article_listicle_blog_directory":
            continue
        for _rn in _extract_venue_names_from_text(_ah.snippet):
            _nn = _recover_candidate_name(_rn)
            if _nn:
                corroboration_counter[_nn.lower()] += 1

    # Track which candidate names were extracted from which article URL so we
    # can later set venues_discovered on the matching research source record.
    article_url_to_candidates: Dict[str, List[str]] = {}

    for hit in hits:
        combined = f"{hit.title}\n{hit.snippet}"
        title = _normalize_source_title(hit.title)
        if not title:
            continue
        classification = _classify_hit(
            title,
            hit.snippet,
            hit.url,
            intent=intent,
            destination=destination,
        )
        if _looks_closed(combined) and classification == "venue_place":
            research_sources.append(
                UnifiedResearchSourceResult(
                    title=title,
                    source=f"Live search · {hit.provider or 'Live search'}",
                    source_type="generic_info_source",
                    summary=_closed_research_summary(title),
                    source_url=hit.url,
                    neighborhood=_extract_neighborhood(combined, destination),
                    last_verified_at=hit.fetched_at,
                    confidence=_confidence_from_age(hit.fetched_at),
                    trip_addable=False,
                )
            )
            continue
        neighborhood = _extract_neighborhood(combined, destination)
        confidence = _confidence_from_age(hit.fetched_at)
        provider_label = hit.provider or "Live search"

        if classification != "venue_place":
            # For article/listicle hits attempt to extract real venue names first.
            if classification == "article_listicle_blog_directory":
                extracted_with_rank = _extract_venue_names_with_rank(hit.snippet)
                source_text = "\n".join(_iter_hit_source_fragments(hit))
                for candidate, cand_rank in extracted_with_rank:
                    is_valid, normalized_candidate, _evidence = _validate_venue_candidate(
                        candidate,
                        combined,
                        intent=intent,
                        destination=destination,
                        title=title,
                        url=hit.url,
                        snippet=hit.snippet,
                        corroborating_hits=corroboration_counter.get(
                            (_recover_candidate_name(candidate) or "").lower(), 1
                        ),
                    )
                    if not is_valid:
                        continue
                    if _candidate_closed_from_source(
                        normalized_candidate,
                        source_title=title,
                        source_text=source_text,
                    ):
                        continue
                    # Verify-before-add gate: only promote candidates confirmed
                    # by a second focused search when verified_candidates is set.
                    if verified_candidates is not None:
                        _vr = verified_candidates.get(normalized_candidate.lower())
                        if _vr is None or not _vr.verified:
                            continue
                        cand_neighborhood = (
                            _vr.neighborhood
                            or _extract_candidate_neighborhood(normalized_candidate, hit.snippet, destination)
                        )
                        cand_source_url = _vr.source_url or hit.url
                        cand_verified: Optional[bool] = True
                    else:
                        cand_neighborhood = _extract_candidate_neighborhood(normalized_candidate, hit.snippet, destination)
                        cand_source_url = hit.url
                        cand_verified = None
                    quality_tier = _source_quality_tier(hit.url, title, hit.snippet, classification)
                    cand_summary = _build_extracted_reason(
                        candidate_name=normalized_candidate,
                        source_title=title,
                        intent=intent,
                        destination=destination,
                        neighborhood=cand_neighborhood,
                        snippet=hit.snippet,
                        quality_tier=quality_tier,
                    )
                    if not cand_summary:
                        continue
                    extracted_ai_score = _extracted_ai_score(quality_tier)
                    # Boost score for venues corroborated by multiple article sources.
                    corr = corroboration_counter.get(normalized_candidate.lower(), 1)
                    corr_boost = min(0.10, (corr - 1) * 0.05)
                    extracted_ai_score = max(
                        0.0,
                        extracted_ai_score + corr_boost - _chain_penalty(normalized_candidate, user_query),
                    )
                    # Build structured article evidence for this candidate.
                    cand_category = _context_type_hint(hit.snippet)
                    cand_source_ev = _build_source_evidence(
                        candidate=normalized_candidate,
                        source_title=title,
                        source_url=hit.url,
                        source_rank=cand_rank or 0,
                        snippet=hit.snippet,
                        source_category=cand_category,
                        neighborhood_hint=cand_neighborhood,
                    )
                    # Track this candidate against its source URL for venues_discovered.
                    article_url_to_candidates.setdefault(hit.url, []).append(
                        normalized_candidate.lower()
                    )
                    if is_restaurant_intent:
                        cand_cuisine = "Cocktail Bar" if intent == INTENT_NIGHTLIFE else "Restaurant"
                        cand_tags: List[str] = []
                        if intent == INTENT_NIGHTLIFE:
                            cand_tags.append("Nightlife")
                        if intent == INTENT_HIDDEN_GEMS:
                            cand_tags.append("Hidden Gem")
                        if intent == INTENT_LUXURY_VALUE:
                            cand_tags.append("Luxury Value")
                        if intent == INTENT_ROMANTIC:
                            cand_tags.append("Romantic")
                        restaurants.append(
                            UnifiedRestaurantResult(
                                name=normalized_candidate,
                                source=f"Live search · {provider_label}",
                                cuisine=cand_cuisine,
                                neighborhood=cand_neighborhood,
                                summary=cand_summary,
                                booking_link=cand_source_url,
                                source_url=cand_source_url,
                                last_verified_at=hit.fetched_at,
                                confidence=confidence,
                                tags=cand_tags,
                                ai_score=extracted_ai_score,
                                verified_place=cand_verified,
                                source_evidence=cand_source_ev,
                            )
                        )
                    elif is_attraction_intent:
                        attractions.append(
                            UnifiedAttractionResult(
                                name=normalized_candidate,
                                source=f"Live search · {provider_label}",
                                category="attraction",
                                description=cand_summary,
                                neighborhood=cand_neighborhood,
                                source_url=cand_source_url,
                                last_verified_at=hit.fetched_at,
                                confidence=confidence,
                                ai_score=extracted_ai_score,
                                verified_place=cand_verified,
                                source_evidence=cand_source_ev,
                            )
                        )
                    elif is_hotel_intent:
                        hotels.append(
                            UnifiedHotelResult(
                                name=normalized_candidate,
                                source=f"Live search · {provider_label}",
                                area_label=cand_neighborhood,
                                reason=cand_summary,
                                booking_url=cand_source_url,
                                source_url=cand_source_url,
                                last_verified_at=hit.fetched_at,
                                confidence=confidence,
                                ai_score=extracted_ai_score,
                                verified_place=cand_verified,
                                source_evidence=cand_source_ev,
                            )
                        )

            _article_fallback = (
                _NEUTRAL_RESEARCH_REASON_ARTICLE
                if classification == "article_listicle_blog_directory"
                else _NEUTRAL_RESEARCH_REASON
            )
            summary = _build_summary(hit.snippet, fallback=_article_fallback)
            research_sources.append(
                UnifiedResearchSourceResult(
                    title=title,
                    source=f"Live search · {provider_label}",
                    source_type=classification,
                    summary=summary,
                    source_url=hit.url,
                    neighborhood=neighborhood,
                    last_verified_at=hit.fetched_at,
                    confidence=confidence,
                    trip_addable=False,
                )
            )
            continue

        if is_restaurant_intent:
            cuisine = "Cocktail Bar" if intent == INTENT_NIGHTLIFE else "Restaurant"
            summary = _build_summary(
                hit.snippet,
                fallback=f"Live result from {provider_label} matching \"{user_query}\".",
            )
            tags: List[str] = []
            if intent == INTENT_NIGHTLIFE:
                tags.append("Nightlife")
            if intent == INTENT_HIDDEN_GEMS:
                tags.append("Hidden Gem")
            if intent == INTENT_LUXURY_VALUE:
                tags.append("Luxury Value")
            if intent == INTENT_ROMANTIC:
                tags.append("Romantic")
            restaurants.append(
                UnifiedRestaurantResult(
                    name=title,
                    source=f"Live search · {provider_label}",
                    cuisine=cuisine,
                    neighborhood=neighborhood,
                    summary=summary,
                    booking_link=hit.url,
                    source_url=hit.url,
                    last_verified_at=hit.fetched_at,
                    confidence=confidence,
                    tags=tags,
                    ai_score=max(0.0, 1.0 - _chain_penalty(title, user_query)),
                    verified_place=True,
                )
            )
        elif is_attraction_intent:
            description = _build_summary(
                hit.snippet,
                fallback=f"Live result from {provider_label}.",
            )
            attractions.append(
                UnifiedAttractionResult(
                    name=title,
                    source=f"Live search · {provider_label}",
                    category="attraction",
                    description=description,
                    neighborhood=neighborhood,
                    source_url=hit.url,
                    last_verified_at=hit.fetched_at,
                    confidence=confidence,
                    ai_score=1.0,
                    verified_place=True,
                )
            )
        elif is_hotel_intent:
            reason = _build_summary(
                hit.snippet,
                fallback=f"Live result from {provider_label}.",
            )
            hotels.append(
                UnifiedHotelResult(
                    name=title,
                    source=f"Live search · {provider_label}",
                    area_label=neighborhood,
                    reason=reason,
                    booking_url=hit.url,
                    source_url=hit.url,
                    last_verified_at=hit.fetched_at,
                    confidence=confidence,
                    ai_score=1.0,
                    verified_place=True,
                )
            )

    # Sort venues: direct hits (ai_score=1.0) before lower-confidence extracted venues.
    restaurants.sort(key=lambda r: r.ai_score or 0.0, reverse=True)
    attractions.sort(key=lambda a: a.ai_score or 0.0, reverse=True)
    hotels.sort(key=lambda h: h.ai_score or 0.0, reverse=True)
    research_sources.sort(
        key=lambda s: _quality_weight(_source_quality_tier(s.source_url or "", s.title or "", s.summary or "", s.source_type)),
        reverse=True,
    )
    restaurants = _dedupe_overlapping_venues(restaurants)
    attractions = _dedupe_overlapping_venues(attractions)
    hotels = _dedupe_overlapping_venues(hotels)
    restaurants = _final_hard_filter_closed_venues(restaurants, kind_label="venue", research_sources=research_sources)
    attractions = _final_hard_filter_closed_venues(attractions, kind_label="attraction", research_sources=research_sources)
    hotels = _final_hard_filter_closed_venues(hotels, kind_label="hotel", research_sources=research_sources)

    # ── Google Places gate ─────────────────────────────────────────────────
    # Article search alone never produces an addable card. When Google
    # verifications are supplied, every card must clear ``is_addable`` to
    # remain in restaurants/attractions/hotels. Anything else gets demoted
    # to research_sources.
    #
    # ``seen_place_ids`` is shared so the same Google place_id cannot appear
    # across both direct hits and article-extracted hits.
    if google_verifications is not None:
        _seen_pids: set = set()
        restaurants = _apply_google_gate(
            restaurants,
            google_verifications=google_verifications,
            research_sources=research_sources,
            kind_label="restaurant",
            provider_label_default="Live search",
            intent=intent,
            user_query=user_query,
            known_candidate_names=list(google_verifications.keys()),
            seen_place_ids=_seen_pids,
            corroboration_counter=corroboration_counter,
        )
        attractions = _apply_google_gate(
            attractions,
            google_verifications=google_verifications,
            research_sources=research_sources,
            kind_label="attraction",
            provider_label_default="Live search",
            intent=intent,
            user_query=user_query,
            known_candidate_names=list(google_verifications.keys()),
            seen_place_ids=_seen_pids,
            corroboration_counter=corroboration_counter,
        )
        hotels = _apply_google_gate(
            hotels,
            google_verifications=google_verifications,
            research_sources=research_sources,
            kind_label="hotel",
            provider_label_default="Live search",
            intent=intent,
            user_query=user_query,
            known_candidate_names=list(google_verifications.keys()),
            seen_place_ids=_seen_pids,
            corroboration_counter=corroboration_counter,
        )

    # Cap only after verification + tiering so we don't underflow.
    restaurants.sort(
        key=lambda v: (
            1 if getattr(v, "verification_tier", None) == "primary" else 0,
            getattr(v, "ai_score", 0.0) or 0.0,
        ),
        reverse=True,
    )
    attractions.sort(
        key=lambda v: (
            1 if getattr(v, "verification_tier", None) == "primary" else 0,
            getattr(v, "ai_score", 0.0) or 0.0,
        ),
        reverse=True,
    )
    hotels.sort(
        key=lambda v: (
            1 if getattr(v, "verification_tier", None) == "primary" else 0,
            getattr(v, "ai_score", 0.0) or 0.0,
        ),
        reverse=True,
    )
    restaurants = restaurants[:max_per_kind]
    attractions = attractions[:max_per_kind]
    hotels = hotels[:max_per_kind]

    # ── venues_discovered: annotate article research sources ───────────────
    # After the gate we know which venues made it through. Update each
    # article-type research source with a count of how many verified places
    # were extracted from it so the UI can show "Used to discover N places."
    _verified_names: set = {
        (getattr(v, "name", "") or "").lower()
        for kind_list in (restaurants, attractions, hotels)
        for v in kind_list
    }
    for _src in research_sources:
        if _src.source_type != "article_listicle_blog_directory" or not _src.source_url:
            continue
        _cands = article_url_to_candidates.get(_src.source_url, [])
        _count = sum(1 for c in _cands if c in _verified_names)
        try:
            _src.venues_discovered = _count
        except Exception:
            pass
        if _count > 0:
            _note = f"Used to discover {_count} verified place{'s' if _count != 1 else ''}."
            try:
                _src.summary = f"{_note} {_src.summary or ''}".strip()
            except Exception:
                pass

    venue_count = len(restaurants) + len(attractions) + len(hotels)
    debug_mode = os.getenv("RESEARCH_ENGINE_DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}
    low_query = (user_query or "").lower()
    explicit_sources = any(token in low_query for token in ("show sources", "sources", "articles", "blogs"))
    # For place intents, suppress research sources whenever we already have
    # enough addable Google-verified venues.
    if _is_place_intent(intent) and venue_count >= RESEARCH_SUPPRESS_THRESHOLD and not debug_mode and not explicit_sources:
        research_cap = 0
    elif venue_count > 0 and not debug_mode:
        research_cap = 1
    else:
        research_cap = max_per_kind
    return {
        "restaurants": restaurants,
        "attractions": attractions,
        "hotels": hotels,
        "research_sources": research_sources[:research_cap],
    }


# ── Service ──────────────────────────────────────────────────────────────────

@dataclass
class LiveResearchResult:
    """Bundle returned by ``LiveResearchService.fetch``."""

    restaurants: List[UnifiedRestaurantResult] = field(default_factory=list)
    attractions: List[UnifiedAttractionResult] = field(default_factory=list)
    hotels: List[UnifiedHotelResult] = field(default_factory=list)
    research_sources: List[UnifiedResearchSourceResult] = field(default_factory=list)
    source_status: str = SOURCE_NONE
    cached: bool = False
    provider_name: Optional[str] = None
    source_url: Optional[str] = None  # representative URL (first hit)

    def has_data(self) -> bool:
        return bool(self.restaurants or self.attractions or self.hotels or self.research_sources)


class LiveResearchService:
    """Orchestrates live-search providers, normalization, filtering, caching."""

    def __init__(
        self,
        provider: Optional[LiveSearchProvider] = None,
        cache: Optional[_TTLCache] = None,
        *,
        enabled: bool = True,
        max_results: int = 10,
        verification_cache: Optional[_TTLCache] = None,
        place_verifier: Optional[GooglePlacesService] = None,
    ) -> None:
        self._provider = provider or select_default_provider()
        self._cache = cache if cache is not None else _GLOBAL_CACHE
        self._verification_cache = (
            verification_cache if verification_cache is not None else _VERIFICATION_CACHE
        )
        self._enabled = enabled
        self._max_results = max_results
        self._place_verifier = place_verifier if place_verifier is not None else GooglePlacesService()
        self._require_google_verification = (
            os.getenv("RESEARCH_ENGINE_REQUIRE_GOOGLE_VERIFICATION", "false").strip().lower()
            in {"1", "true", "yes", "on"}
        )
        self._debug_mode = (
            os.getenv("RESEARCH_ENGINE_DEBUG", "false").strip().lower()
            in {"1", "true", "yes", "on"}
        )

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def is_live_capable(self) -> bool:
        return self._enabled and self._provider.available and not isinstance(self._provider, _NoopProvider)

    def fetch(
        self,
        *,
        intent: str,
        destination: str,
        user_query: str,
        dates: Optional[str] = None,
    ) -> LiveResearchResult:
        if not self._enabled or intent not in _LIVE_ENABLED_INTENTS or not destination:
            return LiveResearchResult()

        derived_category = _derive_query_category(intent, user_query)
        cache_key = _make_cache_key(intent, destination, user_query, dates)
        logger.info(
            "live_research_request query=%r intent=%s derived_category=%s destination=%s cache_key=%s",
            user_query,
            intent,
            derived_category,
            destination,
            cache_key,
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("live_research_cache hit key=%s", cache_key)
            payload = self._payload_to_result(cached)
            if payload is not None:
                payload.cached = True
                return payload
        logger.info("live_research_cache miss key=%s", cache_key)

        if not self._provider.available or isinstance(self._provider, _NoopProvider):
            return LiveResearchResult()

        query = _build_search_query(intent, destination, user_query)
        try:
            hits = self._provider.search(query, max_results=self._max_results)
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning("Live research provider %s raised %s", self._provider.name, exc)
            hits = []
        logger.info("source=tavily count=%d", len(hits))

        if not hits:
            return LiveResearchResult(provider_name=self._provider.name)

        # ── Phase 2: extract candidates from articles and verify each ─────────
        verified_candidates: Dict[str, VerificationResult] = {}
        candidate_names: List[str] = []
        seen_lower: set = set()
        candidate_neighborhoods: Dict[str, Optional[str]] = {}
        extracted_candidate_count = 0
        direct_candidate_count = 0
        for h in hits:
            if _classify_hit(
                _strip_publisher(h.title),
                h.snippet,
                h.url,
                intent=intent,
                destination=destination,
            ) != "article_listicle_blog_directory":
                continue
            for raw_name in _extract_venue_names_from_text(h.snippet):
                norm = _recover_candidate_name(raw_name)
                if not norm:
                    continue
                low = norm.lower()
                if low in seen_lower:
                    continue
                if _is_obvious_non_venue(norm, destination):
                    continue
                if not _is_venue_like_proper_noun(norm):
                    continue
                seen_lower.add(low)
                candidate_names.append(norm)
                extracted_candidate_count += 1
                candidate_neighborhoods[low] = _extract_candidate_neighborhood(
                    norm, h.snippet, destination
                )
        raw_candidate_count = len(candidate_names)

        for norm in candidate_names[:MAX_VERIFICATION_CANDIDATES]:
            low = norm.lower()
            vkey = f"verify::{destination.lower()}::{low}::{intent}"
            cached_vr = self._verification_cache.get(vkey)
            if cached_vr is not None:
                vr = VerificationResult(**cached_vr)
            else:
                vq = _build_verification_query(norm, destination, intent)
                try:
                    vhits = self._provider.search(vq, max_results=5)
                except Exception as exc:
                    logger.warning("Verification search failed for %r: %s", norm, exc)
                    vhits = []
                vr = _check_verification_hits(norm, destination, vhits)
                self._verification_cache.set(vkey, {
                    "verified": vr.verified,
                    "source_url": vr.source_url,
                    "category": vr.category,
                    "neighborhood": vr.neighborhood,
                    "reason": vr.reason,
                })
            verified_candidates[low] = vr
        # ── /Phase 2 ──────────────────────────────────────────────────────────

        # ── Phase 3: Google Places verification gate ──────────────────────────
        # Article extraction + Tavily/Brave/Serper "verification" do not prove
        # a venue is currently open. Every candidate (article-extracted AND
        # direct venue_place hits) is now resolved against Google Places. Only
        # OPERATIONAL matches with high/medium confidence are addable.
        #
        # When the Google Places provider is unavailable (no API key in env),
        # we pass ``google_verifications=None`` so normalize_hits keeps the
        # legacy Tavily-only behavior — required for local dev without keys.
        # In production the API key is configured and the gate is enforced.
        google_verifications: Optional[Dict[str, GooglePlaceVerification]] = None
        place_verifier_available = bool(getattr(self._place_verifier, "available", False))
        if place_verifier_available:
            google_verifications = {}
            display_for_low: Dict[str, str] = {n.lower(): n for n in candidate_names}

            # Direct venue_place hits also need Google verification before
            # becoming LIVE/addable cards.
            for h in hits:
                cls = _classify_hit(
                    _strip_publisher(h.title),
                    h.snippet,
                    h.url,
                    intent=intent,
                    destination=destination,
                )
                if cls != "venue_place":
                    continue
                direct_name = _normalize_source_title(h.title)
                if not direct_name:
                    continue
                low = direct_name.lower()
                if low in candidate_neighborhoods:
                    continue
                if _is_obvious_non_venue(direct_name, destination):
                    continue
                candidate_neighborhoods[low] = _extract_neighborhood(
                    f"{h.title}\n{h.snippet}", destination
                )
                direct_candidate_count += 1
                display_for_low.setdefault(low, direct_name)

            logger.info(
                "live_research candidates: extracted=%d direct=%d deduped=%d",
                extracted_candidate_count,
                direct_candidate_count,
                len(candidate_neighborhoods),
            )

            if _is_place_intent(intent) and len(candidate_neighborhoods) < max(MIN_ADDABLE_RESULTS, 8):
                verifier_client = getattr(self._place_verifier, "_client", None)
                if verifier_client is None or not hasattr(verifier_client, "text_search"):
                    verifier_client = None
                for query in _google_fallback_queries(intent, destination, user_query):
                    if verifier_client is None:
                        break
                    places = verifier_client.text_search(query)[:8]
                    for place in places:
                        display_name = (
                            ((place.get("displayName") or {}).get("text"))
                            or place.get("name")
                            or ""
                        ).strip()
                        if not display_name:
                            continue
                        low = display_name.lower()
                        if low in candidate_neighborhoods:
                            continue
                        candidate_neighborhoods[low] = place.get("formattedAddress")
                        display_for_low.setdefault(low, display_name)
                    if len(candidate_neighborhoods) >= 8:
                        break

            for low, neighborhood in list(candidate_neighborhoods.items())[:MAX_VERIFICATION_CANDIDATES]:
                display_name = display_for_low.get(low, low)
                try:
                    gv = self._place_verifier.verify(
                        display_name,
                        destination,
                        neighborhood=neighborhood,
                        intent=intent,
                    )
                except Exception as exc:  # pragma: no cover — defensive
                    logger.warning(
                        "Google Places verification raised for %r: %s", display_name, exc
                    )
                    gv = GooglePlaceVerification(
                        confidence="unknown",
                        failure_reason=f"provider_error:{type(exc).__name__}",
                    )
                google_verifications[low] = gv

            high_conf = 0
            med_conf = 0
            low_conf = 0
            closed = 0
            failed = 0
            for gv in google_verifications.values():
                if gv.is_closed:
                    closed += 1
                    continue
                if not gv.matched:
                    failed += 1
                    continue
                if gv.confidence == "high" and gv.is_operational:
                    high_conf += 1
                elif gv.confidence == "medium" and gv.is_operational:
                    med_conf += 1
                else:
                    low_conf += 1
            logger.info(
                "google_verify: high=%d medium=%d low=%d closed=%d failed=%d",
                high_conf,
                med_conf,
                low_conf,
                closed,
                failed,
            )

            # Google is authoritative — when it says OPERATIONAL with
            # high/medium confidence, the candidate is allowed past the
            # Tavily phase-2 gate so the Google gate can have the final say.
            for low, gv in google_verifications.items():
                if _google_is_addable(gv):
                    verified_candidates[low] = VerificationResult(
                        verified=True,
                        source_url=gv.google_maps_uri,
                        category=None,
                        neighborhood=gv.formatted_address,
                        reason="Google Places operational match",
                    )
        # ── /Phase 3 ──────────────────────────────────────────────────────────
        elif self._require_google_verification:
            logger.warning(
                "Google verification is required but unavailable; returning research sources only."
            )
            return LiveResearchResult(
                restaurants=[],
                attractions=[],
                hotels=[],
                research_sources=[
                    UnifiedResearchSourceResult(
                        title=_normalize_source_title(h.title) or "Research source",
                        source=f"Live search · {self._provider.name}",
                        source_type="article_listicle_blog_directory" if _is_article_like(h.title, h.snippet, h.url) else "generic_info_source",
                        summary="Google verification unavailable; results kept as research-only evidence.",
                        source_url=h.url,
                        confidence="low",
                        trip_addable=False,
                    )
                    for h in hits[: min(len(hits), 8)]
                ],
                source_status=SOURCE_LIVE_SEARCH,
                provider_name=self._provider.name,
                source_url=hits[0].url if hits else None,
            )
        elif not place_verifier_available:
            logger.warning(
                "Google Places verifier unavailable; live research will return non-authoritative addable candidates only because REQUIRE_GOOGLE is disabled."
            )

        normalized = normalize_hits(
            hits,
            intent=intent,
            destination=destination,
            user_query=user_query,
            verified_candidates=verified_candidates,
            google_verifications=google_verifications,
        )
        self._apply_optional_enrichment(normalized, destination=destination)

        google_verified_count = 0
        if google_verifications is not None:
            google_verified_count = sum(
                1 for verification in google_verifications.values() if _google_is_addable(verification)
            )
        logger.info("source=google_places count=%d", google_verified_count)

        final_verified_count = (
            len(normalized["restaurants"]) + len(normalized["attractions"]) + len(normalized["hotels"])
        )
        if final_verified_count >= RESEARCH_SUPPRESS_THRESHOLD:
            normalized["research_sources"] = []
        if _is_place_intent(intent) and final_verified_count < MIN_ADDABLE_RESULTS:
            logger.warning(
                "addable_underflow intent=%s final_addable_count=%d required_min=%d",
                intent,
                final_verified_count,
                MIN_ADDABLE_RESULTS,
            )
        if google_verifications is not None:
            rejected_closed = 0
            rejected_no_match = 0
            rejected_low_confidence = 0
            for verification in google_verifications.values():
                if verification.is_closed:
                    rejected_closed += 1
                elif not verification.matched:
                    rejected_no_match += 1
                elif not _google_is_addable(verification):
                    rejected_low_confidence += 1
            logger.info(
                "addable_pipeline_stats raw_candidate_count=%d deduped_candidate_count=%d google_verified_total=%d google_high_confidence=%d google_medium_confidence=%d rejected_closed=%d rejected_no_match=%d final_addable_count=%d",
                raw_candidate_count + direct_candidate_count,
                len(candidate_neighborhoods),
                google_verified_count,
                sum(1 for verification in google_verifications.values() if verification.confidence == "high" and verification.is_operational),
                sum(1 for verification in google_verifications.values() if verification.confidence == "medium" and verification.is_operational),
                rejected_closed,
                rejected_no_match + rejected_low_confidence,
                final_verified_count,
            )
        logger.info(
            "final_results: addable=%d research_sources=%d",
            final_verified_count,
            len(normalized["research_sources"]),
        )
        if normalized["restaurants"]:
            dist: Counter = Counter()
            for item in normalized["restaurants"]:
                gv = getattr(item, "google_verification", None)
                types = getattr(gv, "types", []) if gv is not None else []
                dist[_normalize_place_category(types, item)] += 1
            logger.info("final_result_category_distribution intent=%s categories=%s", intent, dict(dist))

        if not (
            normalized["restaurants"]
            or normalized["attractions"]
            or normalized["hotels"]
            or normalized["research_sources"]
        ):
            return LiveResearchResult(provider_name=self._provider.name)

        first_url = next(
            (
                item.source_url
                for kind in ("restaurants", "attractions", "hotels")
                for item in normalized[kind]
                if getattr(item, "source_url", None)
            ),
            None,
        )

        result = LiveResearchResult(
            restaurants=normalized["restaurants"],
            attractions=normalized["attractions"],
            hotels=normalized["hotels"],
            research_sources=normalized["research_sources"],
            source_status=SOURCE_LIVE_SEARCH,
            cached=False,
            provider_name=self._provider.name,
            source_url=first_url,
        )
        self._cache.set(cache_key, self._result_to_payload(result))
        return result

    def _apply_optional_enrichment(self, normalized: Dict[str, List[Any]], *, destination: str) -> None:
        """Best-effort enrichment for already Google-verified places only.

        Enrichment is strictly non-authoritative and never introduces new venues.
        """
        yelp_key = os.getenv("YELP_API_KEY", "").strip()
        fsq_key = os.getenv("FOURSQUARE_API_KEY", "").strip()
        for kind in ("restaurants", "attractions", "hotels"):
            for place in normalized.get(kind, []):
                gv = getattr(place, "google_verification", None)
                if not gv or gv.business_status != OPERATIONAL:
                    continue
                enrichment = VenueEnrichment()
                if yelp_key:
                    try:
                        self._populate_yelp_enrichment(
                            enrichment,
                            place_name=getattr(place, "name", ""),
                            destination=destination,
                            api_key=yelp_key,
                        )
                    except Exception as exc:
                        logger.debug("yelp enrichment failed for %s: %s", getattr(place, "name", ""), exc)
                if fsq_key:
                    try:
                        self._populate_foursquare_enrichment(
                            enrichment,
                            place_name=getattr(place, "name", ""),
                            destination=destination,
                            api_key=fsq_key,
                        )
                    except Exception as exc:
                        logger.debug("foursquare enrichment failed for %s: %s", getattr(place, "name", ""), exc)
                if (
                    enrichment.yelp_rating is not None
                    or enrichment.yelp_review_count is not None
                    or enrichment.yelp_review_excerpts
                    or enrichment.foursquare_categories
                    or enrichment.foursquare_tags
                    or enrichment.foursquare_popularity is not None
                ):
                    try:
                        place.enrichment = enrichment
                    except Exception:
                        pass
                    try:
                        badges = list(getattr(place, "source_badges", []) or [])
                        if enrichment.yelp_rating is not None and "Yelp" not in badges:
                            badges.append("Yelp")
                        if (enrichment.foursquare_categories or enrichment.foursquare_tags) and "Foursquare" not in badges:
                            badges.append("Foursquare")
                        place.source_badges = badges
                    except Exception:
                        pass

    def _populate_yelp_enrichment(self, enrichment: VenueEnrichment, *, place_name: str, destination: str, api_key: str) -> None:
        try:
            import httpx
        except ImportError:
            return
        try:
            with httpx.Client(timeout=4.5) as client:
                resp = client.get(
                    "https://api.yelp.com/v3/businesses/search",
                    headers={"Authorization": f"Bearer {api_key}"},
                    params={"term": place_name, "location": destination, "limit": 1},
                )
                resp.raise_for_status()
                biz = (resp.json().get("businesses") or [{}])[0]
                rating = biz.get("rating")
                reviews = biz.get("review_count")
                if isinstance(rating, (int, float)):
                    enrichment.yelp_rating = float(rating)
                if isinstance(reviews, int):
                    enrichment.yelp_review_count = reviews
        except Exception:
            return

    def _populate_foursquare_enrichment(self, enrichment: VenueEnrichment, *, place_name: str, destination: str, api_key: str) -> None:
        try:
            import httpx
        except ImportError:
            return
        try:
            with httpx.Client(timeout=4.5) as client:
                resp = client.get(
                    "https://api.foursquare.com/v3/places/search",
                    headers={"Authorization": api_key, "Accept": "application/json"},
                    params={"query": place_name, "near": destination, "limit": 1},
                )
                resp.raise_for_status()
                result = (resp.json().get("results") or [{}])[0]
                categories = [c.get("name") for c in (result.get("categories") or []) if c.get("name")]
                if categories:
                    enrichment.foursquare_categories = categories[:4]
        except Exception:
            return

    def clear_cache_for_context(self, destination: str, dates: Optional[str] = None) -> int:
        normalized_destination = (destination or "").strip().lower()
        normalized_dates = (dates or "").strip()

        def _matches(key: str) -> bool:
            parts = key.split("::")
            if len(parts) < 4:
                return False
            key_destination = parts[1].strip().lower()
            key_dates = "::".join(parts[3:]).strip()
            if key_destination != normalized_destination:
                return False
            if normalized_dates and key_dates != normalized_dates:
                return False
            return True

        cleared_results = self._cache.clear_matching(_matches)
        cleared_verifications = self._verification_cache.clear_matching(
            lambda key: key.startswith(f"verify::{normalized_destination}::")
        )
        cleared_google = 0
        try:
            cleared_google = self._place_verifier.clear_cache_for_destination(destination)
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning("Google Places cache clear failed: %s", exc)
        return cleared_results + cleared_verifications + cleared_google

    @staticmethod
    def _result_to_payload(result: LiveResearchResult) -> Dict[str, Any]:
        return {
            "cache_version": CONCIERGE_CACHE_VERSION,
            "restaurants": [r.model_dump(mode="json") for r in result.restaurants],
            "attractions": [a.model_dump(mode="json") for a in result.attractions],
            "hotels": [h.model_dump(mode="json") for h in result.hotels],
            "research_sources": [s.model_dump(mode="json") for s in result.research_sources],
            "source_status": result.source_status,
            "provider_name": result.provider_name,
            "source_url": result.source_url,
        }

    @staticmethod
    def _payload_to_result(payload: Dict[str, Any]) -> Optional[LiveResearchResult]:
        if payload.get("cache_version") != CONCIERGE_CACHE_VERSION:
            return None
        return LiveResearchResult(
            restaurants=[UnifiedRestaurantResult(**r) for r in payload.get("restaurants", [])],
            attractions=[UnifiedAttractionResult(**a) for a in payload.get("attractions", [])],
            hotels=[UnifiedHotelResult(**h) for h in payload.get("hotels", [])],
            research_sources=[UnifiedResearchSourceResult(**s) for s in payload.get("research_sources", [])],
            source_status=payload.get("source_status", SOURCE_LIVE_SEARCH),
            provider_name=payload.get("provider_name"),
            source_url=payload.get("source_url"),
        )


def reset_global_cache() -> None:
    """Test helper — clear the module-level caches."""
    _GLOBAL_CACHE.clear()
    _VERIFICATION_CACHE.clear()
    # Also reset the Google Places verification cache so tests start clean.
    from app.services.google_places import reset_global_place_cache
    reset_global_place_cache()
