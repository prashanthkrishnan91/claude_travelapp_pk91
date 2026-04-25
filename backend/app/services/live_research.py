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
    SOURCE_LIVE_SEARCH,
    SOURCE_NONE,
    UnifiedAttractionResult,
    UnifiedHotelResult,
    UnifiedResearchSourceResult,
    UnifiedRestaurantResult,
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

MAX_VERIFICATION_CANDIDATES: int = 8

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
CONCIERGE_CACHE_VERSION = 2


def _make_cache_key(intent: str, destination: str, query: str, dates: Optional[str] = None) -> str:
    parts = [
        intent or "general",
        (destination or "").strip().lower(),
        re.sub(r"\s+", " ", (query or "").strip().lower()),
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
        name = raw.strip(" \t.,;:\"'“”‘’")
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


def normalize_hits(
    hits: List[LiveSearchHit],
    *,
    intent: str,
    destination: str,
    user_query: str,
    max_per_kind: int = 6,
    verified_candidates: Optional[Dict[str, VerificationResult]] = None,
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
        # Track corroboration count across article extractions.
        # (Only used for article-extracted candidates.)
        # We recompute lazily from all hits for determinism and minimal state coupling.
        corroboration_counter: Counter = Counter()
        for article_hit in hits:
            if _classify_hit(
                _strip_publisher(article_hit.title),
                article_hit.snippet,
                article_hit.url,
                intent=intent,
                destination=destination,
            ) != "article_listicle_blog_directory":
                continue
            for raw_name in _extract_venue_names_from_text(article_hit.snippet):
                normalized_name = _recover_candidate_name(raw_name)
                if normalized_name:
                    corroboration_counter[normalized_name.lower()] += 1

        if classification != "venue_place":
            # For article/listicle hits attempt to extract real venue names first.
            if classification == "article_listicle_blog_directory":
                extracted = _extract_venue_names_from_text(hit.snippet)
                source_text = "\n".join(_iter_hit_source_fragments(hit))
                for candidate in extracted:
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
                    extracted_ai_score = max(0.0, extracted_ai_score - _chain_penalty(normalized_candidate, user_query))
                    if is_restaurant_intent and len(restaurants) < max_per_kind:
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
                            )
                        )
                    elif is_attraction_intent and len(attractions) < max_per_kind:
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
                            )
                        )
                    elif is_hotel_intent and len(hotels) < max_per_kind:
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
                            )
                        )

            summary = _build_summary(
                hit.snippet,
                fallback=_NEUTRAL_RESEARCH_REASON,
            )
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

        if is_restaurant_intent and len(restaurants) < max_per_kind:
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
        elif is_attraction_intent and len(attractions) < max_per_kind:
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
        elif is_hotel_intent and len(hotels) < max_per_kind:
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
    restaurants = _dedupe_overlapping_venues(restaurants)[:max_per_kind]
    attractions = _dedupe_overlapping_venues(attractions)[:max_per_kind]
    hotels = _dedupe_overlapping_venues(hotels)[:max_per_kind]
    restaurants = _final_hard_filter_closed_venues(restaurants, kind_label="venue", research_sources=research_sources)
    attractions = _final_hard_filter_closed_venues(attractions, kind_label="attraction", research_sources=research_sources)
    hotels = _final_hard_filter_closed_venues(hotels, kind_label="hotel", research_sources=research_sources)

    venue_count = len(restaurants) + len(attractions) + len(hotels)
    # Hide research-source cards when ≥3 venues exist; keep at most 2 otherwise.
    if venue_count >= 3:
        research_cap = 0
    elif venue_count > 0:
        research_cap = 2
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
    ) -> None:
        self._provider = provider or select_default_provider()
        self._cache = cache if cache is not None else _GLOBAL_CACHE
        self._verification_cache = (
            verification_cache if verification_cache is not None else _VERIFICATION_CACHE
        )
        self._enabled = enabled
        self._max_results = max_results

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

        cache_key = _make_cache_key(intent, destination, user_query, dates)
        cached = self._cache.get(cache_key)
        if cached is not None:
            payload = self._payload_to_result(cached)
            if payload is not None:
                payload.cached = True
                return payload

        if not self._provider.available or isinstance(self._provider, _NoopProvider):
            return LiveResearchResult()

        query = _build_search_query(intent, destination, user_query)
        try:
            hits = self._provider.search(query, max_results=self._max_results)
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning("Live research provider %s raised %s", self._provider.name, exc)
            hits = []

        if not hits:
            return LiveResearchResult(provider_name=self._provider.name)

        # ── Phase 2: extract candidates from articles and verify each ─────────
        verified_candidates: Dict[str, VerificationResult] = {}
        candidate_names: List[str] = []
        seen_lower: set = set()
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
                if len(candidate_names) >= MAX_VERIFICATION_CANDIDATES:
                    break
            if len(candidate_names) >= MAX_VERIFICATION_CANDIDATES:
                break

        for norm in candidate_names:
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

        normalized = normalize_hits(
            hits,
            intent=intent,
            destination=destination,
            user_query=user_query,
            verified_candidates=verified_candidates,
        )

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
        return cleared_results + cleared_verifications

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
