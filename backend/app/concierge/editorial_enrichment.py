"""Editorial Corroboration v1 — Tavily/Serper trusted editorial enrichment.

Architecture invariants (immutable):
- Google is canonical: Tavily/Serper cannot mint cards, override identity,
  addability, operational status, address, maps URI, or place_id.
- Editorial sources corroborate already Google-verified cards only.
- Editorial snippets cannot directly create visible prose.
- Editorial data becomes structured evidence atoms first.
- Low-confidence entity/article matches are discarded (fail closed).
- Unsupported claims (best/top/famous/hidden gem/etc.) are blocked from writer path.
- Conflicts are logged and downgraded/discarded, never accepted into writer.
- Cards return even if editorial enrichment fails, times out, or rate-limits.
- If remaining deadline budget is too low, editorial enrichment is skipped entirely.
- No SQL. No UI changes. No new LLM calls. No cache.

Performance:
- Deadline-bounded: skipped when remaining budget < EDITORIAL_BUDGET_RESERVE_MS.
- Cards parallelized via ThreadPoolExecutor with non-blocking lifecycle
  (same pattern as PR #275 cross_source_enrichment.py).
- Tavily and Serper run sequentially within each card task.
- Request count: at most budget_n cards × 2 providers per pipeline turn.
- Max 3 search results per provider per card; only matched articles yield atoms.

Provider roles:
- Tavily: entity-specific bounded queries → trusted editorial source atoms.
- Serper: corroboration/discovery source only → same entity-match + trust gates.
- Neither provider can create cards, override Google gates, or produce prose directly.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.concierge.cross_source_enrichment import (
    EnrichmentAtom,
    _MAX_ATOMS_PER_PROVIDER,
    _extract_domain,
    _normalize_match_name,
)

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────

# Minimum entity-match confidence to accept any atoms from an article.
EDITORIAL_ENTITY_MATCH_THRESHOLD: float = 0.70

# Minimum entity-match confidence to set allowed_into_writer=True.
EDITORIAL_WRITER_ALLOW_THRESHOLD: float = 0.75

# Minimum remaining deadline budget (ms) to attempt editorial enrichment.
EDITORIAL_BUDGET_RESERVE_MS: int = 400

# Per-provider HTTP timeout in seconds.
_DEFAULT_EDITORIAL_TIMEOUT: float = 1.5

# Maximum search results to fetch per provider per card.
_MAX_SEARCH_RESULTS: int = 3

# Maximum editorial atoms per provider per card.
_MAX_EDITORIAL_ATOMS_PER_PROVIDER: int = _MAX_ATOMS_PER_PROVIDER


# ── Trusted editorial domains ─────────────────────────────────────────────────
# Simple explicit allowlist. Prefer high-authority travel/food/local sources.
# v1: explicit list only — do not over-generalize.

TRUSTED_EDITORIAL_DOMAINS: frozenset = frozenset({
    # Fine dining / food criticism
    "guide.michelin.com",
    "michelinguide.com",
    "eater.com",
    "theinfatuation.com",
    "grubstreet.com",
    "seriouseats.com",
    "bonappetit.com",
    "foodandwine.com",
    # City/travel editorial
    "timeout.com",
    "cntraveler.com",
    "travelandleisure.com",
    "thrillist.com",
    "newyorker.com",
    # City magazines
    "nymag.com",
    "chicagomag.com",
    "washingtonian.com",
    "phillymag.com",
    "bostonmagazine.com",
    "seattlemag.com",
    "miaminewtimes.com",
    "austinchronicle.com",
    "laweekly.com",
    "sfgate.com",
    "sfchronicle.com",
    # Travel guides
    "lonelyplanet.com",
    "fodors.com",
    "frommers.com",
    # Zagat
    "zagat.com",
})


# ── Specialty keywords safe to extract from snippets ─────────────────────────
# Only these explicit phrases may produce specialty_context atoms.
# Ordered from most specific to least specific for greedy matching.
# Short/ambiguous terms omitted to avoid false positives.

_SPECIALTY_KEYWORDS: List[str] = [
    # Beverage / bar concepts
    "craft cocktail", "classic cocktails", "innovative cocktails",
    "natural wine bar", "natural wine", "wine bar", "sake bar",
    "whiskey bar", "tequila bar", "mezcal bar", "gin bar", "rum bar",
    "champagne bar", "craft beer bar", "taproom", "brewpub",
    "speakeasy", "rooftop bar", "jazz bar", "blues bar",
    # Dining concepts
    "omakase counter", "omakase", "chef's counter", "tasting menu",
    "prix fixe", "farm-to-table", "farm to table", "seasonal menu",
    "wood-fired", "wood fired", "charcoal-grilled", "yakitori",
    "izakaya", "kaiseki", "dim sum", "hot pot", "sushi bar", "raw bar",
    "oyster bar", "seafood bar", "charcuterie bar",
    # Outdoor / view
    "rooftop terrace", "rooftop patio", "outdoor seating", "patio dining",
    "waterfront dining", "lakefront dining", "riverfront dining",
    "skyline view", "river view", "lake view", "scenic view", "al fresco",
    # Occasion context
    "late night bar", "late-night bar", "bottomless brunch", "happy hour",
    "neighborhood bar", "dive bar",
    # Distillery / brewery
    "craft distillery", "craft brewery", "microbrewery",
]

# Compiled lowercase versions for fast matching
_SPECIALTY_KEYWORDS_LOWER: List[str] = [kw.lower() for kw in _SPECIALTY_KEYWORDS]


# ── Disallowed claim patterns ─────────────────────────────────────────────────
# Normalized_value strings matching these patterns get allowed_into_writer=False.
# Prevents generic praise, superlatives, and unsupported claims from reaching writer.

_DISALLOWED_CLAIM_PATTERNS: List[str] = [
    "best", "top", "#1", "award-winning", "award winning", "world-class",
    "world class", "famous", "renowned", "legendary", "must-visit", "must visit",
    "hidden gem", "can't miss", "cant miss", "one of the best", "highly recommended",
    "great option", "excellent choice", "reviewers say", "featured by", "as seen in",
    "critics love", "rave reviews", "can't go wrong", "a must", "don't miss",
    "do not miss", "you won't regret", "not to be missed",
]

# Pre-compiled word-boundary patterns for disallowed claims.
# Using \b ensures "top" doesn't match inside "rooftop", "best" doesn't match "lobster", etc.
_DISALLOWED_CLAIM_REGEXES: List[re.Pattern] = [
    re.compile(r"\b" + re.escape(p) + r"\b", re.IGNORECASE)
    for p in _DISALLOWED_CLAIM_PATTERNS
]


def _is_disallowed_claim(value_lower: str) -> bool:
    """Return True if the normalized value contains a disallowed superlative/generic claim.

    Uses word-boundary matching so "rooftop" does not match "top",
    and "lobster" does not match "best".
    """
    return any(rx.search(value_lower) for rx in _DISALLOWED_CLAIM_REGEXES)


# ── Source trust scoring ───────────────────────────────────────────────────────

def _source_trust_score(domain: str) -> float:
    """Return a trust score for an article domain.

    Returns:
        1.0 — trusted editorial domain (TRUSTED_EDITORIAL_DOMAINS)
        0.5 — all other domains (not in allowlist)
    """
    if not domain:
        return 0.5
    clean = domain.lower()
    if clean.startswith("www."):
        clean = clean[4:]
    if clean in TRUSTED_EDITORIAL_DOMAINS:
        return 1.0
    # Subdomain match (e.g., "chicago.eater.com" → "eater.com")
    parts = clean.split(".")
    if len(parts) >= 2:
        base = ".".join(parts[-2:])
        if base in TRUSTED_EDITORIAL_DOMAINS:
            return 1.0
    return 0.5


# ── Entity match scoring ───────────────────────────────────────────────────────

def _entity_match_score(
    venue_name: str,
    title: str,
    snippet: str,
    url: str,
) -> float:
    """Compute entity-match confidence for an article vs a Google-verified venue.

    Strategy (fail closed):
    - Normalize venue name and check for presence in title (strongest signal),
      snippet (moderate signal), or URL slug (weak boost).
    - Returns 0.0 when the article clearly does not name this specific venue.
    - Does NOT accept "best X in Y"-style articles unless the venue is
      explicitly named in title or snippet.

    Args:
        venue_name: Google-verified venue name.
        title:      Article title from search result.
        snippet:    Article snippet/content from search result.
        url:        Article URL.

    Returns:
        float 0.0–1.0 entity-match confidence. Values < EDITORIAL_ENTITY_MATCH_THRESHOLD
        should be discarded by callers.
    """
    norm_name = _normalize_match_name(venue_name)
    if not norm_name:
        return 0.0

    title_lower = (title or "").lower()
    snippet_lower = (snippet or "").lower()
    url_lower = (url or "").lower()
    norm_title = _normalize_match_name(title)
    norm_snippet_words = set(re.findall(r"[a-z0-9]+", snippet_lower))

    # Check for exact normalized-name presence in title
    name_in_title = norm_name in norm_title

    # Check for presence in snippet: require all significant name tokens present
    name_tokens = set(re.findall(r"[a-z0-9]+", norm_name))
    # Filter trivial tokens (articles, short words)
    sig_tokens = {t for t in name_tokens if len(t) >= 3}
    name_in_snippet = bool(sig_tokens) and sig_tokens.issubset(norm_snippet_words)

    # URL slug: very weak signal — only used as a tiebreaker boost
    # Replace dashes/underscores with spaces for URL slug check
    url_slug = re.sub(r"[-_/]", " ", url_lower)
    name_tokens_in_url = bool(sig_tokens) and sig_tokens.issubset(
        set(re.findall(r"[a-z0-9]+", url_slug))
    )

    if name_in_title and name_in_snippet:
        return 0.95
    if name_in_title:
        return 0.88
    if name_in_snippet and name_tokens_in_url:
        return 0.82
    if name_in_snippet:
        return 0.75
    # Name not found in title or snippet → discard
    return 0.0


# ── Specialty atom extraction ─────────────────────────────────────────────────

def _extract_specialty_atoms(
    title: str,
    snippet: str,
    entity_match: float,
    source_trust: float,
    source_provider: str,
    provenance: Dict[str, Any],
) -> List[EnrichmentAtom]:
    """Extract specialty_context atoms from an article title/snippet.

    Only _SPECIALTY_KEYWORDS explicitly present in title or snippet are extracted.
    Disallowed claims are blocked from allowed_into_writer=True.
    Returns at most 2 specialty atoms per article.

    Args:
        title:           Article title.
        snippet:         Article snippet/content.
        entity_match:    Entity-match confidence for this article.
        source_trust:    Domain trust score (0.5 or 1.0).
        source_provider: "tavily" or "serper".
        provenance:      Provenance dict (title, domain, url, snippet).

    Returns:
        List of EnrichmentAtom with evidence_type="specialty_context".
    """
    combined = f"{(title or '')} {(snippet or '')}".lower()
    atoms: List[EnrichmentAtom] = []
    seen: set = set()

    confidence = entity_match * source_trust

    for kw in _SPECIALTY_KEYWORDS_LOWER:
        if len(atoms) >= 2:
            break
        if kw in combined and kw not in seen:
            seen.add(kw)
            normalized_value = f"specialty_context:{kw}"
            value_lower = normalized_value.lower()
            disallowed = _is_disallowed_claim(value_lower)
            allowed = (
                not disallowed
                and entity_match >= EDITORIAL_WRITER_ALLOW_THRESHOLD
                and confidence >= EDITORIAL_WRITER_ALLOW_THRESHOLD
            )
            atoms.append(EnrichmentAtom(
                source_provider=source_provider,
                evidence_type="specialty_context",
                normalized_value=normalized_value,
                confidence=confidence,
                provenance=provenance,
                allowed_into_writer=allowed,
                conflict_status="ok" if not disallowed else "discarded",
            ))

    return atoms


def _make_editorial_mention_atom(
    entity_match: float,
    source_trust: float,
    source_provider: str,
    provenance: Dict[str, Any],
) -> Optional[EnrichmentAtom]:
    """Create an editorial_mention atom for a strong trusted-source match.

    An editorial_mention signals that the venue was explicitly named by an
    editorial source. Only produced for trusted domains with strong entity match.
    Allowed into writer only when confidence is high enough.

    Returns None when conditions are not met (fail closed).
    """
    if source_trust < 1.0:
        # Only trusted domains produce editorial_mention atoms
        return None
    if entity_match < EDITORIAL_WRITER_ALLOW_THRESHOLD:
        return None

    confidence = entity_match * source_trust
    domain = provenance.get("domain", "")
    normalized_value = f"editorial_mention:{domain}"

    return EnrichmentAtom(
        source_provider=source_provider,
        evidence_type="editorial_mention",
        normalized_value=normalized_value,
        confidence=confidence,
        provenance=provenance,
        allowed_into_writer=True,
        conflict_status="ok",
    )


# ── Article-level atom builder ────────────────────────────────────────────────

def _atoms_from_article(
    venue_name: str,
    title: str,
    snippet: str,
    url: str,
    source_provider: str,
    tel_stats: Dict[str, Any],
) -> List[EnrichmentAtom]:
    """Evaluate one article result and produce atoms.

    Fail closed: discard entirely when entity-match confidence is below threshold.
    Only structured specialty + editorial_mention atoms are produced.
    No free-text snippets pass through to writer.

    Args:
        venue_name:      Google-verified venue name.
        title:           Article title.
        snippet:         Article snippet/content.
        url:             Article URL.
        source_provider: "tavily" or "serper".
        tel_stats:       Mutable stats dict updated in-place for telemetry.

    Returns:
        List of EnrichmentAtom (empty when entity-match fails or no atoms extracted).
    """
    entity_match = _entity_match_score(venue_name, title, snippet, url)

    if entity_match < EDITORIAL_ENTITY_MATCH_THRESHOLD:
        tel_stats["discarded_low_confidence"] = tel_stats.get("discarded_low_confidence", 0) + 1
        logger.debug(
            "editorial_enrichment: article_discarded_low_entity_match "
            "provider=%s name=%r title=%r match=%.2f",
            source_provider, venue_name, title[:60], entity_match,
        )
        return []

    domain = _extract_domain(url)
    source_trust = _source_trust_score(domain)

    provenance: Dict[str, Any] = {
        "title": (title or "")[:120],
        "domain": domain,
        "url": (url or "")[:200],
        "snippet": (snippet or "")[:120],
    }

    atoms: List[EnrichmentAtom] = []

    # Editorial mention atom (trusted domains only, strong entity match)
    mention_atom = _make_editorial_mention_atom(
        entity_match=entity_match,
        source_trust=source_trust,
        source_provider=source_provider,
        provenance=provenance,
    )
    if mention_atom is not None:
        atoms.append(mention_atom)

    # Specialty context atoms from title/snippet
    specialty_atoms = _extract_specialty_atoms(
        title=title,
        snippet=snippet,
        entity_match=entity_match,
        source_trust=source_trust,
        source_provider=source_provider,
        provenance=provenance,
    )
    atoms.extend(specialty_atoms)

    if atoms:
        tel_stats["accepted"] = tel_stats.get("accepted", 0) + 1
    else:
        tel_stats["discarded_no_atoms"] = tel_stats.get("discarded_no_atoms", 0) + 1

    return atoms


# ── Tavily search ─────────────────────────────────────────────────────────────

_TAVILY_ENDPOINT = "https://api.tavily.com/search"


def _fetch_tavily_atoms(
    entity: Any,
    tavily_key: str,
    timeout: float,
    destination: str,
) -> Tuple[bool, List[EnrichmentAtom], Dict[str, Any]]:
    """Fetch Tavily search results for a Google-verified entity.

    Query is bounded to the specific venue name + destination.
    Returns (attempted, atoms, per_provider_stats).

    Tavily cannot mint cards, override Google identity, or create visible prose.
    Fail closed: low-confidence matches and non-entity articles are discarded.
    """
    stats: Dict[str, Any] = {"attempted": False, "error": False, "timeout": False}
    if not tavily_key:
        return False, [], stats

    name = (getattr(entity, "name", "") or "").strip()
    if not name:
        return False, [], stats

    dest = (destination or "").strip()
    query = f'"{name}" {dest}'.strip()

    payload = {
        "api_key": tavily_key,
        "query": query,
        "search_depth": "basic",
        "max_results": _MAX_SEARCH_RESULTS,
        "include_answer": False,
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _TAVILY_ENDPOINT,
        data=data_bytes,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )

    stats["attempted"] = True
    t0 = time.monotonic()

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.URLError as exc:
        elapsed = time.monotonic() - t0
        if elapsed >= timeout * 0.90:
            stats["timeout"] = True
        else:
            stats["error"] = True
        logger.debug(
            "editorial_enrichment: tavily_request_failed name=%r error=%s",
            name, exc,
        )
        return True, [], stats
    except Exception as exc:
        stats["error"] = True
        logger.debug(
            "editorial_enrichment: tavily_error name=%r error=%s",
            name, exc,
        )
        return True, [], stats

    results = data.get("results") or []
    tel_stats: Dict[str, Any] = {}
    all_atoms: List[EnrichmentAtom] = []

    for item in results:
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        snippet = str(
            item.get("content") or item.get("snippet") or ""
        ).strip()
        if not title or not url:
            continue
        article_atoms = _atoms_from_article(
            venue_name=name,
            title=title,
            snippet=snippet,
            url=url,
            source_provider="tavily",
            tel_stats=tel_stats,
        )
        all_atoms.extend(article_atoms)

    stats["article_accepted"] = tel_stats.get("accepted", 0)
    stats["article_discarded_low_confidence"] = tel_stats.get("discarded_low_confidence", 0)
    stats["article_discarded_no_atoms"] = tel_stats.get("discarded_no_atoms", 0)

    return True, all_atoms[:_MAX_EDITORIAL_ATOMS_PER_PROVIDER], stats


# ── Serper search ─────────────────────────────────────────────────────────────

_SERPER_ENDPOINT = "https://google.serper.dev/search"


def _fetch_serper_atoms(
    entity: Any,
    serper_key: str,
    timeout: float,
    destination: str,
) -> Tuple[bool, List[EnrichmentAtom], Dict[str, Any]]:
    """Fetch Serper (Google SERP) search results for a Google-verified entity.

    Query is bounded to the specific venue name + destination.
    Returns (attempted, atoms, per_provider_stats).

    Serper cannot mint cards, override Google identity, or create visible prose.
    Fail closed: low-confidence matches and non-entity articles are discarded.
    """
    stats: Dict[str, Any] = {"attempted": False, "error": False, "timeout": False}
    if not serper_key:
        return False, [], stats

    name = (getattr(entity, "name", "") or "").strip()
    if not name:
        return False, [], stats

    dest = (destination or "").strip()
    query = f'"{name}" {dest}'.strip()

    payload = {"q": query, "num": _MAX_SEARCH_RESULTS}
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _SERPER_ENDPOINT,
        data=data_bytes,
        headers={
            "X-API-KEY": serper_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    stats["attempted"] = True
    t0 = time.monotonic()

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.URLError as exc:
        elapsed = time.monotonic() - t0
        if elapsed >= timeout * 0.90:
            stats["timeout"] = True
        else:
            stats["error"] = True
        logger.debug(
            "editorial_enrichment: serper_request_failed name=%r error=%s",
            name, exc,
        )
        return True, [], stats
    except Exception as exc:
        stats["error"] = True
        logger.debug(
            "editorial_enrichment: serper_error name=%r error=%s",
            name, exc,
        )
        return True, [], stats

    # Serper returns "organic" results list
    results = data.get("organic") or []
    tel_stats: Dict[str, Any] = {}
    all_atoms: List[EnrichmentAtom] = []

    for item in results:
        title = str(item.get("title") or "").strip()
        url = str(item.get("link") or "").strip()
        snippet = str(item.get("snippet") or "").strip()
        if not title or not url:
            continue
        article_atoms = _atoms_from_article(
            venue_name=name,
            title=title,
            snippet=snippet,
            url=url,
            source_provider="serper",
            tel_stats=tel_stats,
        )
        all_atoms.extend(article_atoms)

    stats["article_accepted"] = tel_stats.get("accepted", 0)
    stats["article_discarded_low_confidence"] = tel_stats.get("discarded_low_confidence", 0)
    stats["article_discarded_no_atoms"] = tel_stats.get("discarded_no_atoms", 0)

    return True, all_atoms[:_MAX_EDITORIAL_ATOMS_PER_PROVIDER], stats


# ── Card-level enrichment task ─────────────────────────────────────────────────

def _enrich_one_card_editorial(
    entity: Any,
    tavily_key: str,
    serper_key: str,
    timeout: float,
    destination: str,
) -> Tuple[str, List[EnrichmentAtom], Dict[str, Any]]:
    """Fetch Tavily + Serper editorial enrichment for one Google-verified card.

    Tavily and Serper calls run sequentially within this function.
    The caller (run_editorial_enrichment) runs multiple card tasks in parallel.
    Returns (place_id, atoms, stats).

    Failure from any provider is isolated — the other provider still runs.
    """
    place_id: str = getattr(entity, "place_id", "") or ""
    all_atoms: List[EnrichmentAtom] = []
    stats: Dict[str, Any] = {
        "tavily_attempted": False, "tavily_accepted": 0,
        "tavily_discarded_low_confidence": 0, "tavily_error": False, "tavily_timeout": False,
        "serper_attempted": False, "serper_accepted": 0,
        "serper_discarded_low_confidence": 0, "serper_error": False, "serper_timeout": False,
        "trusted_domain_hit": False,
    }

    # ── Tavily ────────────────────────────────────────────────────────────────
    if tavily_key:
        t0 = time.monotonic()
        try:
            attempted, atoms, pstats = _fetch_tavily_atoms(entity, tavily_key, timeout, destination)
            elapsed = time.monotonic() - t0
            stats["tavily_attempted"] = attempted
            if attempted:
                if elapsed >= timeout * 0.95:
                    stats["tavily_timeout"] = True
                if pstats.get("error"):
                    stats["tavily_error"] = True
                if pstats.get("timeout"):
                    stats["tavily_timeout"] = True
                stats["tavily_accepted"] = pstats.get("article_accepted", 0)
                stats["tavily_discarded_low_confidence"] = pstats.get("article_discarded_low_confidence", 0)
                all_atoms.extend(atoms)
                if any(a.evidence_type == "editorial_mention" for a in atoms):
                    stats["trusted_domain_hit"] = True
        except Exception as exc:
            logger.debug(
                "editorial_enrichment: tavily_task_error place_id=%s error=%s",
                place_id, exc,
            )
            stats["tavily_error"] = True

    # ── Serper ────────────────────────────────────────────────────────────────
    if serper_key:
        t0 = time.monotonic()
        try:
            attempted, atoms, pstats = _fetch_serper_atoms(entity, serper_key, timeout, destination)
            elapsed = time.monotonic() - t0
            stats["serper_attempted"] = attempted
            if attempted:
                if elapsed >= timeout * 0.95:
                    stats["serper_timeout"] = True
                if pstats.get("error"):
                    stats["serper_error"] = True
                if pstats.get("timeout"):
                    stats["serper_timeout"] = True
                stats["serper_accepted"] = pstats.get("article_accepted", 0)
                stats["serper_discarded_low_confidence"] = pstats.get("article_discarded_low_confidence", 0)
                all_atoms.extend(atoms)
                if any(a.evidence_type == "editorial_mention" for a in atoms):
                    stats["trusted_domain_hit"] = True
        except Exception as exc:
            logger.debug(
                "editorial_enrichment: serper_task_error place_id=%s error=%s",
                place_id, exc,
            )
            stats["serper_error"] = True

    return place_id, all_atoms, stats


# ── Telemetry ──────────────────────────────────────────────────────────────────

@dataclass
class EditorialEnrichmentTelemetry:
    """Structured telemetry for one pipeline turn's editorial enrichment pass."""

    enrichment_attempted: bool = False
    skipped_reason: Optional[str] = None  # None | "budget_exhausted" | "no_keys" | "no_entities"

    tavily_attempted_count: int = 0
    tavily_accepted_count: int = 0
    tavily_discarded_low_confidence_count: int = 0
    tavily_error_count: int = 0
    tavily_timeout_count: int = 0

    serper_attempted_count: int = 0
    serper_accepted_count: int = 0
    serper_discarded_low_confidence_count: int = 0
    serper_error_count: int = 0
    serper_timeout_count: int = 0

    editorial_atoms_by_provider: Dict[str, int] = field(default_factory=dict)
    editorial_atoms_by_type: Dict[str, int] = field(default_factory=dict)
    trusted_domain_counts: int = 0
    editorial_conflict_or_downgrade_count: int = 0

    def as_log_dict(self) -> Dict[str, Any]:
        return {
            "editorial_enrichment_attempted": self.enrichment_attempted,
            "editorial_skipped_reason": self.skipped_reason,
            "tavily_attempted": self.tavily_attempted_count,
            "tavily_accepted": self.tavily_accepted_count,
            "tavily_discarded_low_confidence": self.tavily_discarded_low_confidence_count,
            "tavily_errors": self.tavily_error_count,
            "tavily_timeouts": self.tavily_timeout_count,
            "serper_attempted": self.serper_attempted_count,
            "serper_accepted": self.serper_accepted_count,
            "serper_discarded_low_confidence": self.serper_discarded_low_confidence_count,
            "serper_errors": self.serper_error_count,
            "serper_timeouts": self.serper_timeout_count,
            "editorial_atoms_by_provider": self.editorial_atoms_by_provider,
            "editorial_atoms_by_type": self.editorial_atoms_by_type,
            "trusted_domain_counts": self.trusted_domain_counts,
            "editorial_conflict_or_downgrade_count": self.editorial_conflict_or_downgrade_count,
        }


@dataclass
class EditorialEnrichmentResult:
    """Result of one editorial enrichment pass for a batch of Google-verified cards."""

    atoms_by_place_id: Dict[str, List[EnrichmentAtom]]  # place_id → atoms
    telemetry: EditorialEnrichmentTelemetry
    elapsed_ms: int


# ── Stats merge ───────────────────────────────────────────────────────────────

def _merge_editorial_stats(tel: EditorialEnrichmentTelemetry, stats: Dict[str, Any]) -> None:
    """Merge per-card stats into aggregated telemetry."""
    if stats.get("tavily_attempted"):
        tel.tavily_attempted_count += 1
    if stats.get("tavily_accepted", 0) > 0:
        tel.tavily_accepted_count += stats["tavily_accepted"]
    tel.tavily_discarded_low_confidence_count += stats.get("tavily_discarded_low_confidence", 0)
    if stats.get("tavily_error"):
        tel.tavily_error_count += 1
    if stats.get("tavily_timeout"):
        tel.tavily_timeout_count += 1

    if stats.get("serper_attempted"):
        tel.serper_attempted_count += 1
    if stats.get("serper_accepted", 0) > 0:
        tel.serper_accepted_count += stats["serper_accepted"]
    tel.serper_discarded_low_confidence_count += stats.get("serper_discarded_low_confidence", 0)
    if stats.get("serper_error"):
        tel.serper_error_count += 1
    if stats.get("serper_timeout"):
        tel.serper_timeout_count += 1

    if stats.get("trusted_domain_hit"):
        tel.trusted_domain_counts += 1


# ── Main entry point ───────────────────────────────────────────────────────────

def run_editorial_enrichment(
    entities: List[Any],
    *,
    deadline: Any,
    tavily_key: str,
    serper_key: str,
    destination: str,
    budget_n: int = 6,
) -> EditorialEnrichmentResult:
    """Deadline-bounded Tavily + Serper editorial enrichment for Google-verified cards.

    Args:
        entities:    List of Google-verified PlaceEntity (ranked order). At most
                     budget_n entities are enriched.
        deadline:    RequestDeadline from the pipeline.
        tavily_key:  Tavily API key (empty string = skip Tavily).
        serper_key:  Serper API key (empty string = skip Serper).
        destination: User destination string used to bound search queries.
        budget_n:    Maximum entities to attempt enrichment for.

    Returns:
        EditorialEnrichmentResult with atoms_by_place_id and telemetry.
        Never raises — all errors are isolated internally.
        Cards always return even when enrichment fails, times out, or skips.

    Safety invariants:
        - Only entities from the input list receive atoms (keyed by place_id).
        - Tavily/Serper cannot create cards or override Google gates.
        - Low-confidence entity matches are discarded.
        - Disallowed claims are blocked from allowed_into_writer=True.
    """
    t0 = time.monotonic()
    tel = EditorialEnrichmentTelemetry()

    if not entities:
        tel.skipped_reason = "no_entities"
        return EditorialEnrichmentResult(
            atoms_by_place_id={},
            telemetry=tel,
            elapsed_ms=0,
        )

    if not tavily_key and not serper_key:
        tel.skipped_reason = "no_keys"
        tel.enrichment_attempted = False
        logger.info("editorial_enrichment: skipped reason=no_keys")
        return EditorialEnrichmentResult(
            atoms_by_place_id={},
            telemetry=tel,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )

    remaining_ms = deadline.remaining_ms()
    if remaining_ms < EDITORIAL_BUDGET_RESERVE_MS:
        tel.skipped_reason = "budget_exhausted"
        tel.enrichment_attempted = False
        logger.info(
            "editorial_enrichment: skipped reason=budget_exhausted remaining_ms=%d",
            remaining_ms,
        )
        return EditorialEnrichmentResult(
            atoms_by_place_id={},
            telemetry=tel,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )

    tel.enrichment_attempted = True
    targets = entities[:budget_n]

    # Per-provider timeout: divide remaining budget across cards, cap at default
    per_card_timeout = min(
        _DEFAULT_EDITORIAL_TIMEOUT,
        max(0.5, (remaining_ms / 1000.0 - 0.2) / max(1, len(targets))),
    )

    atoms_by_place_id: Dict[str, List[EnrichmentAtom]] = {}

    # Non-blocking executor lifecycle — mirrors cross_source_enrichment.py pattern.
    # Do NOT use `with ThreadPoolExecutor`: its __exit__ calls shutdown(wait=True),
    # which blocks until all in-flight HTTP threads finish, defeating the deadline.
    executor = ThreadPoolExecutor(max_workers=min(len(targets), 4))
    futures = {
        executor.submit(
            _enrich_one_card_editorial,
            entity, tavily_key, serper_key, per_card_timeout, destination,
        ): entity
        for entity in targets
    }
    fanout_deadline = max(0.1, remaining_ms / 1000.0 - 0.1)
    try:
        try:
            for future in as_completed(futures, timeout=fanout_deadline):
                try:
                    place_id, atoms, stats = future.result(timeout=0)
                    if atoms:
                        atoms_by_place_id[place_id] = atoms
                    _merge_editorial_stats(tel, stats)
                except Exception as exc:
                    entity = futures[future]
                    logger.debug(
                        "editorial_enrichment: future_error name=%r error=%s",
                        getattr(entity, "name", "?"), exc,
                    )
        except FutureTimeoutError:
            logger.debug(
                "editorial_enrichment: fanout_timeout deadline=%.2fs",
                fanout_deadline,
            )
    finally:
        for fut in futures:
            fut.cancel()
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            executor.shutdown(wait=False)

    # Aggregate atom telemetry
    all_atoms: List[EnrichmentAtom] = [a for atoms in atoms_by_place_id.values() for a in atoms]
    for atom in all_atoms:
        tel.editorial_atoms_by_provider[atom.source_provider] = (
            tel.editorial_atoms_by_provider.get(atom.source_provider, 0) + 1
        )
        tel.editorial_atoms_by_type[atom.evidence_type] = (
            tel.editorial_atoms_by_type.get(atom.evidence_type, 0) + 1
        )
        if not atom.allowed_into_writer and atom.conflict_status in ("downgraded", "discarded"):
            tel.editorial_conflict_or_downgrade_count += 1

    elapsed_ms = int((time.monotonic() - t0) * 1000)

    logger.info(
        "editorial_enrichment: done elapsed_ms=%d entities=%d enriched=%d "
        "total_atoms=%d tavily_accepted=%d serper_accepted=%d trusted_domains=%d",
        elapsed_ms,
        len(targets),
        len(atoms_by_place_id),
        len(all_atoms),
        tel.tavily_accepted_count,
        tel.serper_accepted_count,
        tel.trusted_domain_counts,
    )

    return EditorialEnrichmentResult(
        atoms_by_place_id=atoms_by_place_id,
        telemetry=tel,
        elapsed_ms=elapsed_ms,
    )


# ── API key helpers ────────────────────────────────────────────────────────────

def get_tavily_key() -> str:
    """Return the Tavily API key from settings config, with env fallback."""
    try:
        from app.core.config import get_settings
        key = get_settings().tavily_api_key
        if key:
            return key.strip()
    except Exception:
        pass
    return os.getenv("TAVILY_API_KEY", "").strip()


def get_serper_key() -> str:
    """Return the Serper API key from settings config, with env fallback."""
    try:
        from app.core.config import get_settings
        key = get_settings().serper_api_key
        if key:
            return key.strip()
    except Exception:
        pass
    return os.getenv("SERPER_API_KEY", "").strip()
