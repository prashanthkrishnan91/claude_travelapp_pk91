"""Cross-Source Evidence Enrichment v1 — provider-agnostic enrichment spine.

Architecture invariants (immutable):
- Google is canonical: identity, addability, operational status never overridden.
- Yelp/Foursquare are enrichment only — they cannot mint cards or create prose.
- Only high-confidence provider matches (composite >= HIGH_CONFIDENCE_THRESHOLD)
  produce accepted atoms.
- Low-confidence matches are discarded; conflicts are logged and downgraded.
- Enrichment failing, timing out, or missing provider keys never blocks card return.
- Fail closed: ambiguous matches → discard, not accept.

Performance:
- Deadline-bounded: skipped when remaining budget < CROSS_SOURCE_BUDGET_RESERVE_MS.
- Cards parallelized via ThreadPoolExecutor; Yelp and Foursquare run sequentially
  within each card task (2 HTTP calls per card at most).
- Non-blocking executor lifecycle: futures are cancelled and executor is shut down
  with wait=False so a hung provider call does not delay card return beyond the
  fanout budget. Mirrors the pattern in provider_executor.py.
- Request count: at most budget_n cards × 2 providers (Yelp + FSQ) per pipeline turn.

No SQL. No UI. No new LLM calls. No cache.
"""

from __future__ import annotations

import difflib
import json
import logging
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────

# Composite match score required to accept enrichment atoms from a provider.
HIGH_CONFIDENCE_THRESHOLD: float = 0.65

# Hard name-similarity gate: below this threshold, composite is not evaluated.
HARD_NAME_GATE: float = 0.50

# Maximum distance in meters to score distance at all.
# Beyond this range distance_score = 0.0 (but not auto-rejected; name+phone can still pass).
MAX_DISTANCE_SCORE_M: float = 300.0

# Minimum remaining deadline budget (ms) to attempt cross-source enrichment.
CROSS_SOURCE_BUDGET_RESERVE_MS: int = 300

# Per-provider HTTP timeout in seconds.
_DEFAULT_PROVIDER_TIMEOUT: float = 1.5

# Maximum atoms per provider per card to merge into dossier.
_MAX_ATOMS_PER_PROVIDER: int = 4


# ── Typed structures ──────────────────────────────────────────────────────────

@dataclass
class EnrichmentAtom:
    """One structured piece of cross-source evidence for a Google-verified card.

    All atoms are internal. Only atoms with allowed_into_writer=True may be
    included in the evidence claims seen by the set-level writer.
    No atom may override Google identity, addability, or operational status.
    """

    source_provider: str        # "yelp" | "foursquare"
    evidence_type: str          # "category" | "price" | "attribute" | "rating_context" | "popularity_context"
    normalized_value: str       # clean, structured value string safe for internal use
    confidence: float           # 0.0–1.0, reflects provider match confidence
    provenance: Dict[str, Any]  # provider-side id, source field — never exposed in UI
    allowed_into_writer: bool   # True only for high-confidence, non-conflicting atoms
    conflict_status: str        # "ok" | "downgraded" | "discarded" | "conflict_logged"


@dataclass
class ProviderMatchScore:
    """Composite match score for one provider result vs one Google-verified card."""

    name_similarity: float          # SequenceMatcher ratio on normalized names
    distance_m: Optional[float]     # haversine meters; None when lat/lng unavailable
    phone_match: bool
    domain_match: bool
    composite_score: float          # final weighted score
    accepted: bool                  # True when composite >= HIGH_CONFIDENCE_THRESHOLD


@dataclass
class CrossSourceTelemetry:
    """Structured telemetry for one pipeline turn's cross-source enrichment pass."""

    enrichment_enabled: bool = True
    enrichment_attempted: bool = False
    skipped_reason: Optional[str] = None           # None | "budget_exhausted" | "no_keys" | "no_entities"

    yelp_attempted_count: int = 0
    yelp_accepted_count: int = 0
    yelp_discarded_low_confidence_count: int = 0
    yelp_conflict_downgrade_count: int = 0
    yelp_error_count: int = 0
    yelp_timeout_count: int = 0

    foursquare_attempted_count: int = 0
    foursquare_accepted_count: int = 0
    foursquare_discarded_low_confidence_count: int = 0
    foursquare_conflict_downgrade_count: int = 0
    foursquare_error_count: int = 0
    foursquare_timeout_count: int = 0

    total_atoms_before_enrichment: int = 0
    total_atoms_after_enrichment: int = 0
    atoms_by_provider: Dict[str, int] = field(default_factory=dict)
    atoms_by_type: Dict[str, int] = field(default_factory=dict)

    def as_log_dict(self) -> Dict[str, Any]:
        return {
            "cross_source_enrichment_enabled": self.enrichment_enabled,
            "cross_source_enrichment_attempted": self.enrichment_attempted,
            "cross_source_skipped_reason": self.skipped_reason,
            "yelp_attempted": self.yelp_attempted_count,
            "yelp_accepted": self.yelp_accepted_count,
            "yelp_discarded_low_confidence": self.yelp_discarded_low_confidence_count,
            "yelp_conflict_downgrade": self.yelp_conflict_downgrade_count,
            "yelp_errors": self.yelp_error_count,
            "yelp_timeouts": self.yelp_timeout_count,
            "foursquare_attempted": self.foursquare_attempted_count,
            "foursquare_accepted": self.foursquare_accepted_count,
            "foursquare_discarded_low_confidence": self.foursquare_discarded_low_confidence_count,
            "foursquare_conflict_downgrade": self.foursquare_conflict_downgrade_count,
            "foursquare_errors": self.foursquare_error_count,
            "foursquare_timeouts": self.foursquare_timeout_count,
            "evidence_atom_count_before": self.total_atoms_before_enrichment,
            "evidence_atom_count_after": self.total_atoms_after_enrichment,
            "atoms_by_provider": self.atoms_by_provider,
            "atoms_by_type": self.atoms_by_type,
        }


@dataclass
class CrossSourceEnrichmentResult:
    """Result of one cross-source enrichment pass for a batch of Google-verified cards."""

    atoms_by_place_id: Dict[str, List[EnrichmentAtom]]  # place_id → accepted atoms
    telemetry: CrossSourceTelemetry
    elapsed_ms: int


# ── Name normalization ─────────────────────────────────────────────────────────

_SUFFIX_RE = re.compile(
    r"\s*\b(restaurant|bar|pub|grill|cafe|bistro|eatery|kitchen|lounge|tavern"
    r"|brewery|taproom|llc|inc|ltd|co)\b\s*$",
    re.IGNORECASE,
)
_PREFIX_THE_RE = re.compile(r"^the\s+", re.IGNORECASE)
_PUNCT_RE = re.compile(r"[^\w\s]")
_SPACE_RE = re.compile(r"\s+")


def _normalize_match_name(name: str) -> str:
    """Normalize a venue name for match scoring.

    Removes leading "The ", common business suffixes, punctuation, and
    collapses whitespace. Does NOT strip city/neighborhood qualifiers since
    those are unpredictable and could introduce false positives.
    """
    s = (name or "").strip()
    s = _PREFIX_THE_RE.sub("", s)
    s = _SUFFIX_RE.sub("", s)
    s = _PUNCT_RE.sub(" ", s)
    s = _SPACE_RE.sub(" ", s).strip().lower()
    return s


def _extract_domain(uri: str) -> str:
    """Extract registrable domain from a URI for domain-match scoring."""
    try:
        parsed = urllib.parse.urlparse(uri if "://" in uri else f"https://{uri}")
        host = (parsed.hostname or "").lower()
        # Strip www. prefix
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


# ── Distance helper ────────────────────────────────────────────────────────────

def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance in meters between two lat/lng points."""
    R = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2.0 * math.asin(math.sqrt(min(1.0, a)))


# ── Provider match scorer ──────────────────────────────────────────────────────

def score_provider_match(
    *,
    google_name: str,
    google_lat: Optional[float],
    google_lng: Optional[float],
    google_phone: Optional[str] = None,
    google_domain: Optional[str] = None,
    provider_name: str,
    provider_lat: Optional[float] = None,
    provider_lng: Optional[float] = None,
    provider_phone: Optional[str] = None,
    provider_domain: Optional[str] = None,
) -> ProviderMatchScore:
    """Compute a composite match score between a Google entity and a provider result.

    Inputs support: name similarity, distance, phone match, and website/domain match.
    Fail closed: returns accepted=False for any ambiguous or low-confidence signal.
    Does not use weak substring-only matching — uses SequenceMatcher ratio.

    Args:
        google_*:   Signals from the Google-verified card (canonical).
        provider_*: Signals from the provider's returned result (enrichment candidate).

    Returns:
        ProviderMatchScore with composite_score and accepted flag.
    """
    norm_google = _normalize_match_name(google_name)
    norm_provider = _normalize_match_name(provider_name)

    # Name similarity via SequenceMatcher (not substring-only)
    name_similarity: float = difflib.SequenceMatcher(
        None, norm_google, norm_provider
    ).ratio()

    # Hard gate — fail closed before any weighted scoring
    if name_similarity < HARD_NAME_GATE:
        return ProviderMatchScore(
            name_similarity=name_similarity,
            distance_m=None,
            phone_match=False,
            domain_match=False,
            composite_score=0.0,
            accepted=False,
        )

    # Distance score
    has_location = (
        google_lat is not None
        and google_lng is not None
        and provider_lat is not None
        and provider_lng is not None
    )
    distance_m: Optional[float] = None
    dist_score: float = 0.0
    if has_location:
        distance_m = _haversine_m(google_lat, google_lng, provider_lat, provider_lng)  # type: ignore[arg-type]
        dist_score = max(0.0, 1.0 - distance_m / MAX_DISTANCE_SCORE_M)

    # Phone match (normalized last-10 digits)
    phone_match = False
    if google_phone and provider_phone:
        gp = re.sub(r"\D", "", google_phone)[-10:]
        pp = re.sub(r"\D", "", provider_phone)[-10:]
        phone_match = bool(gp and pp and len(gp) >= 7 and gp == pp)

    # Domain match
    domain_match = False
    if google_domain and provider_domain:
        gd = _extract_domain(google_domain)
        pd = _extract_domain(provider_domain)
        domain_match = bool(gd and pd and gd == pd and len(gd) > 3)

    # Weighted composite — distance weight redistributes to name when no location
    if has_location:
        composite = (
            0.55 * name_similarity
            + 0.30 * dist_score
            + 0.10 * float(phone_match)
            + 0.05 * float(domain_match)
        )
    else:
        composite = (
            0.75 * name_similarity
            + 0.15 * float(phone_match)
            + 0.10 * float(domain_match)
        )

    accepted = composite >= HIGH_CONFIDENCE_THRESHOLD

    return ProviderMatchScore(
        name_similarity=name_similarity,
        distance_m=distance_m,
        phone_match=phone_match,
        domain_match=domain_match,
        composite_score=composite,
        accepted=accepted,
    )


# ── Conflict detection ─────────────────────────────────────────────────────────

# Broad Google venue-type groups for conflict detection.
# If a provider returns a category from a conflicting group, the atom is logged
# and downgraded rather than accepted.
_VENUE_TYPE_GROUPS: Dict[str, frozenset] = {
    "food_drink": frozenset({
        "restaurant", "bar", "pub", "grill", "cafe", "bistro", "eatery",
        "kitchen", "brewery", "taproom", "winery", "distillery", "lounge",
        "food", "drink", "pizza", "sushi", "ramen", "steakhouse", "bakery",
        "coffee", "tea", "cocktail", "izakaya",
    }),
    "retail": frozenset({
        "shopping", "shop", "store", "boutique", "clothing", "fashion",
        "hardware", "electronics", "furniture", "gift", "bookstore",
    }),
    "lodging": frozenset({
        "hotel", "motel", "inn", "hostel", "resort", "b&b", "bed and breakfast",
        "lodge", "accommodation",
    }),
    "attractions": frozenset({
        "museum", "gallery", "theater", "theatre", "park", "zoo", "aquarium",
        "attraction", "monument", "landmark",
    }),
}


def _google_type_group(google_types: List[str]) -> Optional[str]:
    """Return the primary venue group for a Google entity's types list."""
    type_set = {t.lower().replace("_", " ") for t in (google_types or [])}
    for group, keywords in _VENUE_TYPE_GROUPS.items():
        if type_set & keywords:
            return group
    return None


def _provider_category_group(category_lower: str) -> Optional[str]:
    """Return venue group for a provider category string."""
    for group, keywords in _VENUE_TYPE_GROUPS.items():
        for kw in keywords:
            if kw in category_lower:
                return group
    return None


def _check_category_conflict(
    provider_category: str,
    google_types: List[str],
) -> str:
    """Return conflict_status for a category atom vs Google types.

    Returns:
        "ok"              — no conflict detected
        "conflict_logged" — provider group conflicts with Google group (atom blocked)
    """
    google_group = _google_type_group(google_types)
    if google_group is None:
        return "ok"
    provider_group = _provider_category_group(provider_category.lower())
    if provider_group is None:
        return "ok"
    if google_group != provider_group:
        logger.info(
            "cross_source_enrichment: category_conflict "
            "provider_category=%r google_group=%r provider_group=%r",
            provider_category, google_group, provider_group,
        )
        return "conflict_logged"
    return "ok"


# ── Yelp Fusion enrichment ─────────────────────────────────────────────────────

_YELP_SEARCH_URL = "https://api.yelp.com/v3/businesses/search"


def _fetch_yelp_atoms(
    entity: Any,
    yelp_key: str,
    timeout: float,
) -> Tuple[Optional[ProviderMatchScore], List[EnrichmentAtom]]:
    """Fetch Yelp Fusion search result for a Google-verified entity.

    Returns (match_score, atoms). match_score is None on error/skip.
    Atoms list is empty on error, no match, or low-confidence match.

    Yelp cannot mint cards, override Google identity, or create visible prose.
    """
    if not yelp_key:
        return None, []

    name = getattr(entity, "name", "") or ""
    lat = getattr(entity, "lat", None)
    lng = getattr(entity, "lng", None)
    google_types: List[str] = getattr(entity, "types", []) or []

    params: Dict[str, Any] = {
        "term": name,
        "limit": 1,
        "sort_by": "best_match",
    }
    if lat is not None and lng is not None:
        params["latitude"] = str(lat)
        params["longitude"] = str(lng)

    url = _YELP_SEARCH_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {yelp_key}", "Accept": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.URLError as exc:
        logger.debug("cross_source_enrichment: yelp_request_failed name=%r error=%s", name, exc)
        return None, []
    except Exception as exc:
        logger.debug("cross_source_enrichment: yelp_error name=%r error=%s", name, exc)
        return None, []

    businesses = data.get("businesses") or []
    if not businesses:
        return None, []

    biz = businesses[0]
    provider_name = (biz.get("name") or "").strip()
    coords = biz.get("coordinates") or {}
    provider_lat = coords.get("latitude")
    provider_lng = coords.get("longitude")
    provider_phone = (biz.get("phone") or "").strip() or None
    biz_url = (biz.get("url") or "").strip() or None

    match_score = score_provider_match(
        google_name=name,
        google_lat=lat,
        google_lng=lng,
        google_phone=None,
        google_domain=getattr(entity, "website_uri", None),
        provider_name=provider_name,
        provider_lat=provider_lat,
        provider_lng=provider_lng,
        provider_phone=provider_phone,
        provider_domain=biz_url,
    )

    if not match_score.accepted:
        logger.debug(
            "cross_source_enrichment: yelp_low_confidence "
            "name=%r provider=%r composite=%.2f",
            name, provider_name, match_score.composite_score,
        )
        return match_score, []

    # Extract structured atoms from accepted match
    atoms: List[EnrichmentAtom] = []
    yelp_id = biz.get("id") or ""

    # Categories (taxonomy)
    for cat in (biz.get("categories") or [])[:3]:
        cat_title = (cat.get("title") or "").strip()
        if not cat_title:
            continue
        conflict = _check_category_conflict(cat_title, google_types)
        allowed = conflict == "ok"
        atoms.append(EnrichmentAtom(
            source_provider="yelp",
            evidence_type="category",
            normalized_value=f"yelp_category:{cat_title}",
            confidence=match_score.composite_score,
            provenance={"yelp_id": yelp_id, "source_field": "categories", "alias": cat.get("alias", "")},
            allowed_into_writer=allowed,
            conflict_status=conflict,
        ))

    # Price level
    price = (biz.get("price") or "").strip()
    if price:
        atoms.append(EnrichmentAtom(
            source_provider="yelp",
            evidence_type="price",
            normalized_value=f"yelp_price:{price}",
            confidence=match_score.composite_score,
            provenance={"yelp_id": yelp_id, "source_field": "price"},
            allowed_into_writer=True,
            conflict_status="ok",
        ))

    # Rating context (internal metadata only — not for writer prose)
    yelp_rating = biz.get("rating")
    yelp_rc = biz.get("review_count")
    if yelp_rating is not None:
        atoms.append(EnrichmentAtom(
            source_provider="yelp",
            evidence_type="rating_context",
            normalized_value=f"yelp_rating:{yelp_rating}",
            confidence=match_score.composite_score,
            provenance={"yelp_id": yelp_id, "source_field": "rating", "review_count": yelp_rc},
            allowed_into_writer=False,  # rating context: not for writer prose
            conflict_status="ok",
        ))

    return match_score, atoms[:_MAX_ATOMS_PER_PROVIDER]


# ── Foursquare Places enrichment ───────────────────────────────────────────────

_FSQ_SEARCH_URL = "https://api.foursquare.com/v3/places/search"

# Foursquare price → human label
_FSQ_PRICE_LABELS: Dict[int, str] = {
    1: "inexpensive",
    2: "moderate",
    3: "expensive",
    4: "very expensive",
}


def _fetch_foursquare_atoms(
    entity: Any,
    fsq_key: str,
    timeout: float,
) -> Tuple[Optional[ProviderMatchScore], List[EnrichmentAtom]]:
    """Fetch Foursquare Places v3 search result for a Google-verified entity.

    Returns (match_score, atoms). match_score is None on error/skip.
    Atoms list is empty on error, no match, or low-confidence match.

    Foursquare cannot mint cards, override Google identity, or create visible prose.
    """
    if not fsq_key:
        return None, []

    name = getattr(entity, "name", "") or ""
    lat = getattr(entity, "lat", None)
    lng = getattr(entity, "lng", None)
    google_types: List[str] = getattr(entity, "types", []) or []

    params: Dict[str, Any] = {
        "query": name,
        "limit": 1,
    }
    if lat is not None and lng is not None:
        params["ll"] = f"{lat},{lng}"
        params["radius"] = 250

    url = _FSQ_SEARCH_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": fsq_key,
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.URLError as exc:
        logger.debug("cross_source_enrichment: foursquare_request_failed name=%r error=%s", name, exc)
        return None, []
    except Exception as exc:
        logger.debug("cross_source_enrichment: foursquare_error name=%r error=%s", name, exc)
        return None, []

    results = data.get("results") or []
    if not results:
        return None, []

    venue = results[0]
    provider_name = (venue.get("name") or "").strip()
    geocodes = venue.get("geocodes") or {}
    main_geo = geocodes.get("main") or {}
    provider_lat = main_geo.get("latitude")
    provider_lng = main_geo.get("longitude")

    match_score = score_provider_match(
        google_name=name,
        google_lat=lat,
        google_lng=lng,
        google_phone=None,
        google_domain=getattr(entity, "website_uri", None),
        provider_name=provider_name,
        provider_lat=provider_lat,
        provider_lng=provider_lng,
        provider_phone=None,
        provider_domain=None,
    )

    if not match_score.accepted:
        logger.debug(
            "cross_source_enrichment: foursquare_low_confidence "
            "name=%r provider=%r composite=%.2f",
            name, provider_name, match_score.composite_score,
        )
        return match_score, []

    # Extract structured atoms from accepted match
    atoms: List[EnrichmentAtom] = []
    fsq_id = venue.get("fsq_id") or ""

    # Categories (taxonomy)
    for cat in (venue.get("categories") or [])[:3]:
        cat_name = (cat.get("name") or "").strip()
        if not cat_name:
            continue
        conflict = _check_category_conflict(cat_name, google_types)
        allowed = conflict == "ok"
        atoms.append(EnrichmentAtom(
            source_provider="foursquare",
            evidence_type="category",
            normalized_value=f"fsq_category:{cat_name}",
            confidence=match_score.composite_score,
            provenance={"fsq_id": fsq_id, "source_field": "categories", "cat_id": cat.get("id", "")},
            allowed_into_writer=allowed,
            conflict_status=conflict,
        ))

    # Price level
    price_val = venue.get("price")
    if isinstance(price_val, int) and price_val in _FSQ_PRICE_LABELS:
        atoms.append(EnrichmentAtom(
            source_provider="foursquare",
            evidence_type="price",
            normalized_value=f"fsq_price:{_FSQ_PRICE_LABELS[price_val]}",
            confidence=match_score.composite_score,
            provenance={"fsq_id": fsq_id, "source_field": "price", "price_int": price_val},
            allowed_into_writer=True,
            conflict_status="ok",
        ))

    # Popularity context (internal metadata only — not for writer prose)
    popularity = venue.get("popularity")
    if popularity is not None:
        atoms.append(EnrichmentAtom(
            source_provider="foursquare",
            evidence_type="popularity_context",
            normalized_value=f"fsq_popularity:{popularity:.2f}",
            confidence=match_score.composite_score,
            provenance={"fsq_id": fsq_id, "source_field": "popularity"},
            allowed_into_writer=False,  # popularity context: not for writer prose
            conflict_status="ok",
        ))

    return match_score, atoms[:_MAX_ATOMS_PER_PROVIDER]


# ── Card-level enrichment task ─────────────────────────────────────────────────

def _enrich_one_card(
    entity: Any,
    yelp_key: str,
    fsq_key: str,
    timeout: float,
) -> Tuple[str, List[EnrichmentAtom], Dict[str, Any]]:
    """Fetch Yelp + Foursquare enrichment for one Google-verified card.

    Yelp and Foursquare calls run sequentially within this function.
    The caller (run_cross_source_enrichment) runs multiple card tasks in parallel.
    Returns (place_id, atoms, stats).

    Failure from any provider is isolated — the other provider still runs.
    """
    place_id: str = getattr(entity, "place_id", "") or ""
    all_atoms: List[EnrichmentAtom] = []
    stats: Dict[str, Any] = {
        "yelp_attempted": False, "yelp_accepted": False,
        "yelp_discarded": False, "yelp_error": False, "yelp_timeout": False,
        "fsq_attempted": False, "fsq_accepted": False,
        "fsq_discarded": False, "fsq_error": False, "fsq_timeout": False,
    }

    # ── Yelp ──────────────────────────────────────────────────────────────────
    if yelp_key:
        stats["yelp_attempted"] = True
        t0 = time.monotonic()
        try:
            match_score, atoms = _fetch_yelp_atoms(entity, yelp_key, timeout)
            elapsed = time.monotonic() - t0
            if elapsed >= timeout * 0.95:
                stats["yelp_timeout"] = True
            if match_score is None:
                stats["yelp_error"] = True
            elif match_score.accepted:
                stats["yelp_accepted"] = True
                all_atoms.extend(atoms)
            else:
                stats["yelp_discarded"] = True
        except Exception as exc:
            logger.debug("cross_source_enrichment: yelp_task_error place_id=%s error=%s", place_id, exc)
            stats["yelp_error"] = True

    # ── Foursquare ────────────────────────────────────────────────────────────
    if fsq_key:
        stats["fsq_attempted"] = True
        t0 = time.monotonic()
        try:
            match_score, atoms = _fetch_foursquare_atoms(entity, fsq_key, timeout)
            elapsed = time.monotonic() - t0
            if elapsed >= timeout * 0.95:
                stats["fsq_timeout"] = True
            if match_score is None:
                stats["fsq_error"] = True
            elif match_score.accepted:
                stats["fsq_accepted"] = True
                all_atoms.extend(atoms)
            else:
                stats["fsq_discarded"] = True
        except Exception as exc:
            logger.debug("cross_source_enrichment: fsq_task_error place_id=%s error=%s", place_id, exc)
            stats["fsq_error"] = True

    return place_id, all_atoms, stats


# ── Main entry point ───────────────────────────────────────────────────────────

def run_cross_source_enrichment(
    entities: List[Any],
    *,
    deadline: Any,
    yelp_key: str,
    fsq_key: str,
    budget_n: int = 6,
) -> CrossSourceEnrichmentResult:
    """Deadline-bounded Yelp + Foursquare enrichment for Google-verified cards.

    Args:
        entities:  List of Google-verified PlaceEntity (ranked order). At most
                   budget_n entities are enriched.
        deadline:  RequestDeadline from the pipeline.
        yelp_key:  Yelp Fusion API key (empty string = skip Yelp).
        fsq_key:   Foursquare Places API key (empty string = skip FSQ).
        budget_n:  Maximum entities to attempt enrichment for.

    Returns:
        CrossSourceEnrichmentResult with atoms_by_place_id and telemetry.
        Never raises — all errors are isolated internally.
        Cards always return even when enrichment fails, times out, or skips.
    """
    t0 = time.monotonic()
    tel = CrossSourceTelemetry(enrichment_enabled=True)

    if not entities:
        tel.skipped_reason = "no_entities"
        return CrossSourceEnrichmentResult(
            atoms_by_place_id={},
            telemetry=tel,
            elapsed_ms=0,
        )

    if not yelp_key and not fsq_key:
        tel.skipped_reason = "no_keys"
        tel.enrichment_attempted = False
        logger.info("cross_source_enrichment: skipped reason=no_keys")
        return CrossSourceEnrichmentResult(
            atoms_by_place_id={},
            telemetry=tel,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )

    remaining_ms = deadline.remaining_ms()
    if remaining_ms < CROSS_SOURCE_BUDGET_RESERVE_MS:
        tel.skipped_reason = "budget_exhausted"
        tel.enrichment_attempted = False
        logger.info(
            "cross_source_enrichment: skipped reason=budget_exhausted remaining_ms=%d",
            remaining_ms,
        )
        return CrossSourceEnrichmentResult(
            atoms_by_place_id={},
            telemetry=tel,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )

    tel.enrichment_attempted = True
    targets = entities[:budget_n]

    # Per-provider timeout: divide remaining budget across cards, cap at _DEFAULT_PROVIDER_TIMEOUT
    per_card_timeout = min(
        _DEFAULT_PROVIDER_TIMEOUT,
        max(0.5, (remaining_ms / 1000.0 - 0.2) / max(1, len(targets))),
    )

    atoms_by_place_id: Dict[str, List[EnrichmentAtom]] = {}

    # Non-blocking executor lifecycle — mirrors provider_executor.py.
    # Do NOT use `with ThreadPoolExecutor` here: its __exit__ calls shutdown(wait=True)
    # which blocks until all in-flight HTTP threads finish, defeating the fanout deadline.
    # Instead: explicit creation, cancel pending futures, shutdown(wait=False) in finally.
    executor = ThreadPoolExecutor(max_workers=min(len(targets), 4))
    futures = {
        executor.submit(
            _enrich_one_card, entity, yelp_key, fsq_key, per_card_timeout
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
                    _merge_card_stats(tel, stats)
                except Exception as exc:
                    entity = futures[future]
                    logger.debug(
                        "cross_source_enrichment: future_error name=%r error=%s",
                        getattr(entity, "name", "?"), exc,
                    )
        except FutureTimeoutError:
            logger.debug(
                "cross_source_enrichment: fanout_timeout deadline=%.2fs",
                fanout_deadline,
            )
    finally:
        # Cancel any futures not yet started; return immediately without blocking
        # on in-flight HTTP threads (they will finish in the background).
        for fut in futures:
            fut.cancel()
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            # Python < 3.9 does not have cancel_futures.
            executor.shutdown(wait=False)

    # Aggregate telemetry
    all_atoms: List[EnrichmentAtom] = [a for atoms in atoms_by_place_id.values() for a in atoms]
    for atom in all_atoms:
        tel.atoms_by_provider[atom.source_provider] = (
            tel.atoms_by_provider.get(atom.source_provider, 0) + 1
        )
        tel.atoms_by_type[atom.evidence_type] = (
            tel.atoms_by_type.get(atom.evidence_type, 0) + 1
        )
    tel.total_atoms_after_enrichment = len(all_atoms)

    elapsed_ms = int((time.monotonic() - t0) * 1000)

    logger.info(
        "cross_source_enrichment: done elapsed_ms=%d entities=%d enriched=%d "
        "total_atoms=%d yelp_accepted=%d fsq_accepted=%d",
        elapsed_ms,
        len(targets),
        len(atoms_by_place_id),
        len(all_atoms),
        tel.yelp_accepted_count,
        tel.foursquare_accepted_count,
    )

    return CrossSourceEnrichmentResult(
        atoms_by_place_id=atoms_by_place_id,
        telemetry=tel,
        elapsed_ms=elapsed_ms,
    )


def _merge_card_stats(tel: CrossSourceTelemetry, stats: Dict[str, Any]) -> None:
    """Merge per-card provider stats into the aggregated telemetry object."""
    if stats.get("yelp_attempted"):
        tel.yelp_attempted_count += 1
    if stats.get("yelp_accepted"):
        tel.yelp_accepted_count += 1
    if stats.get("yelp_discarded"):
        tel.yelp_discarded_low_confidence_count += 1
    if stats.get("yelp_error"):
        tel.yelp_error_count += 1
    if stats.get("yelp_timeout"):
        tel.yelp_timeout_count += 1
    if stats.get("fsq_attempted"):
        tel.foursquare_attempted_count += 1
    if stats.get("fsq_accepted"):
        tel.foursquare_accepted_count += 1
    if stats.get("fsq_discarded"):
        tel.foursquare_discarded_low_confidence_count += 1
    if stats.get("fsq_error"):
        tel.foursquare_error_count += 1
    if stats.get("fsq_timeout"):
        tel.foursquare_timeout_count += 1


# ── API key helpers ────────────────────────────────────────────────────────────

def get_yelp_key() -> str:
    """Return the Yelp API key from settings config, with env fallback.

    Reads from app.core.config.get_settings().yelp_api_key first (the repo-standard
    pydantic-settings path, already backed by YELP_API_KEY env var).
    Falls back to os.getenv("YELP_API_KEY") for compatibility in test/minimal setups.
    """
    try:
        from app.core.config import get_settings
        key = get_settings().yelp_api_key
        if key:
            return key.strip()
    except Exception:
        pass
    return os.getenv("YELP_API_KEY", "").strip()


def get_foursquare_key() -> str:
    """Return the Foursquare API key from settings config, with env fallback.

    Reads from app.core.config.get_settings().foursquare_api_key first (the
    repo-standard pydantic-settings path, already backed by FOURSQUARE_API_KEY env var).
    Falls back to os.getenv("FOURSQUARE_API_KEY") for compatibility.
    """
    try:
        from app.core.config import get_settings
        key = get_settings().foursquare_api_key
        if key:
            return key.strip()
    except Exception:
        pass
    return os.getenv("FOURSQUARE_API_KEY", "").strip()
