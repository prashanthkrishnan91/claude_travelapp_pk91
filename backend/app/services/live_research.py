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
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

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
    "closed permanently",
    "now closed",
    "is closed",
    "shut down",
    "shuttered",
    "out of business",
    "ceased operations",
    "no longer in operation",
    "no longer open",
    "has closed",
)

_FRESHNESS_HIGH_DAYS = 90
_FRESHNESS_MEDIUM_DAYS = 365
_MARKDOWN_HEADING_PAT = re.compile(r"^\s{0,3}#{1,6}\s*")
_SYMBOL_RUN_PAT = re.compile(r"([!?.\-_*~])\1{2,}")
_WHITESPACE_PAT = re.compile(r"\s+")
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


def _looks_closed(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(kw in lower for kw in _CLOSED_KEYWORDS)


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


# Module-level cache so multiple ConciergeService instances share results.
_GLOBAL_CACHE = _TTLCache(ttl_seconds=1800)


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

    return s or fallback


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


def _validate_venue_candidate(
    name: str, context: str, *, intent: str, destination: str
) -> bool:
    """Return True if *name* is a plausible addable venue, not a generic article phrase."""
    if not name or len(name.strip()) < 3:
        return False
    if _GENERIC_CANDIDATE_PAT.match(name):
        return False
    if not _title_looks_like_venue_name(name):
        return False
    has_cat = _category_signal(intent, context)
    has_loc = bool(
        _ADDRESS_HINT.search(context)
        or (destination and destination.lower() in context.lower())
        or _NEIGHBORHOOD_HINT.search(context)
    )
    return has_cat or has_loc


def normalize_hits(
    hits: List[LiveSearchHit],
    *,
    intent: str,
    destination: str,
    user_query: str,
    max_per_kind: int = 6,
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
        if _looks_closed(combined):
            continue

        title = _strip_publisher(hit.title)
        if not title:
            continue
        neighborhood = _extract_neighborhood(combined, destination)
        confidence = _confidence_from_age(hit.fetched_at)
        provider_label = hit.provider or "Live search"
        classification = _classify_hit(
            title,
            hit.snippet,
            hit.url,
            intent=intent,
            destination=destination,
        )

        if classification != "venue_place":
            # For article/listicle hits attempt to extract real venue names first.
            if classification == "article_listicle_blog_directory":
                extracted = _extract_venue_names_from_text(hit.snippet)
                for candidate in extracted:
                    if not _validate_venue_candidate(
                        candidate, combined, intent=intent, destination=destination
                    ):
                        continue
                    if _looks_closed(candidate):
                        continue
                    article_snippet = _build_summary(hit.snippet, fallback="")
                    cand_summary = (
                        f"Featured in \"{title}\". {article_snippet}".rstrip(". ")
                        if article_snippet
                        else f"Featured in \"{title}\"."
                    )
                    cand_neighborhood = _extract_neighborhood(hit.snippet, destination)
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
                                name=candidate,
                                source=f"Live search · {provider_label}",
                                cuisine=cand_cuisine,
                                neighborhood=cand_neighborhood,
                                summary=cand_summary,
                                booking_link=hit.url,
                                source_url=hit.url,
                                last_verified_at=hit.fetched_at,
                                confidence=confidence,
                                tags=cand_tags,
                                ai_score=0.7,
                            )
                        )
                    elif is_attraction_intent and len(attractions) < max_per_kind:
                        attractions.append(
                            UnifiedAttractionResult(
                                name=candidate,
                                source=f"Live search · {provider_label}",
                                category="attraction",
                                description=cand_summary,
                                neighborhood=cand_neighborhood,
                                source_url=hit.url,
                                last_verified_at=hit.fetched_at,
                                confidence=confidence,
                                ai_score=0.7,
                            )
                        )
                    elif is_hotel_intent and len(hotels) < max_per_kind:
                        hotels.append(
                            UnifiedHotelResult(
                                name=candidate,
                                source=f"Live search · {provider_label}",
                                area_label=cand_neighborhood,
                                reason=cand_summary,
                                booking_url=hit.url,
                                source_url=hit.url,
                                last_verified_at=hit.fetched_at,
                                confidence=confidence,
                                ai_score=0.7,
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
                    ai_score=1.0,
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
                )
            )

    # Sort venues: direct hits (ai_score=1.0) before article-extracted ones (ai_score=0.7).
    restaurants.sort(key=lambda r: r.ai_score or 0.0, reverse=True)
    attractions.sort(key=lambda a: a.ai_score or 0.0, reverse=True)
    hotels.sort(key=lambda h: h.ai_score or 0.0, reverse=True)

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
    ) -> None:
        self._provider = provider or select_default_provider()
        self._cache = cache if cache is not None else _GLOBAL_CACHE
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

        normalized = normalize_hits(
            hits,
            intent=intent,
            destination=destination,
            user_query=user_query,
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

    @staticmethod
    def _result_to_payload(result: LiveResearchResult) -> Dict[str, Any]:
        return {
            "restaurants": [r.model_dump(mode="json") for r in result.restaurants],
            "attractions": [a.model_dump(mode="json") for a in result.attractions],
            "hotels": [h.model_dump(mode="json") for h in result.hotels],
            "research_sources": [s.model_dump(mode="json") for s in result.research_sources],
            "source_status": result.source_status,
            "provider_name": result.provider_name,
            "source_url": result.source_url,
        }

    @staticmethod
    def _payload_to_result(payload: Dict[str, Any]) -> LiveResearchResult:
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
    """Test helper — clear the module-level cache."""
    _GLOBAL_CACHE.clear()
