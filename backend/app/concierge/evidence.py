"""Evidence normalization for the whyPick reasoning pipeline.

EvidenceUnit is the atomic evidence atom passed to LLM synthesis.
Google is canonical for existence/status/rating/address/addability.
Yelp/Foursquare/Tavily/editorial are enrichment signals only.
No Supabase SQL required.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

ClaimType = Literal[
    "editorial_mention",
    "rating",
    "review_volume",
    "location",
    "michelin_status",
    "neighborhood",
    "cuisine",
    "price_level",
    "attribute",
    "yelp_rating",
    "yelp_review_excerpt",
    "foursquare_category",
    "foursquare_tag",
    "tavily_snippet",
    "google_verified",
]

# ── Foursquare tag specificity filter ────────────────────────────────────────

# Tags that carry no venue-specific differentiating signal.
_GENERIC_FS_TAGS: frozenset = frozenset({
    "popular", "popular spot", "great food", "good food", "good service",
    "nice atmosphere", "must visit", "must-visit", "nearby", "casual dining",
    "outdoor seating", "outdoor dining", "wifi", "takeout", "delivery",
    "dine-in", "reservations", "fast service", "friendly staff", "good value",
    "trendy", "hipster", "local", "neighborhood spot", "late night",
    "happy hour", "bar bites", "drinks", "date night", "date-night",
    "romantic", "groups", "parking", "accessible", "family-friendly",
    "family friendly", "vegetarian-friendly", "vegetarian friendly",
    "vegan", "gluten free", "gluten-free", "cash only", "credit cards",
    "takeaway", "sit down", "quick bite", "dinner", "lunch", "brunch",
    "breakfast", "late night food", "comfort food", "neighborhood",
    "casual", "laid-back", "laid back", "chill", "cozy", "intimate",
    "cocktail bar", "highly rated", "good drinks", "nightlife",
})

# Pure venue-category tokens — not differentiators on their own.
_FS_CATEGORY_TOKENS: frozenset = frozenset({
    "restaurant", "bar", "cafe", "hotel", "lounge", "brewery", "winery",
    "bistro", "pub", "club", "diner", "grill", "brasserie", "tavern",
})


def _foursquare_tag_is_specific(tag: str) -> bool:
    """Return True when a Foursquare tag is a genuine venue differentiator.

    Rejects generic sentiment/use-case labels ("trendy", "date-night") and
    pure category names ("bar", "restaurant"). Accepts specific dish/drink/
    program signals ("handmade tortillas", "craft cocktails", "zero-waste").
    """
    if not tag:
        return False
    tag_low = tag.lower().strip()
    if len(tag_low) < 3:
        return False
    if tag_low in _GENERIC_FS_TAGS:
        return False
    tokens = set(re.findall(r"[a-z]+", tag_low))
    if tokens and tokens.issubset(_FS_CATEGORY_TOKENS):
        return False
    return True


# ── Award / recognition signal patterns ─────────────────────────────────────

_AWARD_SIGNAL_RE = re.compile(
    r"\b(michelin[\s\-]+(?:stars?|starred|bib|guide|recognized|selected)"
    r"|bib[\s\-]+gourmand"
    r"|james[\s\-]+beard(?:[\s\-]+award)?(?:[\s\-]+(?:winner|finalist|nominated|semifinalist))?"
    r"|award[\s\-]winning"
    r"|(?:one|two|three|1|2|3)[\s\-]+michelin[\s\-]+stars?"
    r"|world(?:'s|s)?[\s]+50[\s]+best)\b",
    re.IGNORECASE,
)

# ── "Known for X" extraction pattern ────────────────────────────────────────

_KNOWN_FOR_RE = re.compile(
    r"(?:known|celebrated|acclaimed|famous|noted|recognized|lauded)\s+for\s+(?:its?\s+)?([^,;.!?\n]{5,80})",
    re.IGNORECASE,
)



# Generic “known for” tails that are not true differentiators.
_GENERIC_KNOWN_FOR_SIGNALS: frozenset = frozenset({
    "great", "customer", "service", "popular", "nice", "friendly",
    "good food", "good drinks",
})


def _is_specific_known_for_signal(signal: str) -> bool:
    if not signal:
        return False
    clean = re.sub(r"\s+", " ", signal.lower().strip(" .,!;:-"))
    if clean in _GENERIC_KNOWN_FOR_SIGNALS:
        return False
    tokens = [t for t in re.findall(r"[a-z]+", clean) if t]
    if not tokens:
        return False
    generic_vocab = {"great", "customer", "service", "popular", "nice", "friendly", "good", "food", "drinks"}
    stopwords = {"and", "the", "a", "an", "its", "their", "very"}
    meaningful = [t for t in tokens if t not in stopwords]
    if meaningful and all(t in generic_vocab for t in meaningful):
        return False
    return True

SourceFamily = Literal["google", "editorial", "yelp", "foursquare", "tavily", "internal"]


@dataclass
class EvidenceUnit:
    """Atomic evidence unit for whyPick LLM synthesis or deterministic fallback.

    Fields
    ------
    id            Deterministic 8-char hash key.
    claim         Human-readable claim text.
    claim_type    Semantic type of the claim.
    source_family Origin family.
    confidence    high | medium | low.
    safe_for_copy True only when the claim text can appear verbatim in user copy.
    venue_name    Anti-contamination: the venue this unit belongs to.
    category      Venue category (restaurant | bar | hotel | …).
    metadata      Optional structured key-value pairs for downstream use.
    """

    id: str
    claim: str
    claim_type: ClaimType
    source_family: SourceFamily
    confidence: Literal["high", "medium", "low"]
    safe_for_copy: bool
    venue_name: str
    category: str
    metadata: Dict[str, Any] = field(default_factory=dict)


def _eid(venue_name: str, claim_type: str, index: int = 0) -> str:
    """Deterministic 8-char ID for a (venue, claim_type, index) triple."""
    return hashlib.md5(f"{venue_name}:{claim_type}:{index}".encode()).hexdigest()[:8]


def normalize_evidence(
    *,
    venue_name: str,
    category: str,
    google_verification: Optional[Any] = None,
    source_evidence: Optional[Any] = None,
    enrichment: Optional[Any] = None,
    tavily_snippets: Optional[List[str]] = None,
    michelin_status: Optional[str] = None,
) -> List[EvidenceUnit]:
    """Build an EvidenceUnit list from all available structured sources.

    Google remains canonical — its facts are marked high-confidence.
    Yelp / Foursquare / Tavily / editorial are enrichment only.
    """
    units: List[EvidenceUnit] = []

    # ── Google (canonical) ──────────────────────────────────────────────────
    gv = google_verification
    if gv is not None:
        rating = getattr(gv, "rating", None)
        rc = getattr(gv, "user_rating_count", None)
        if rating is not None:
            claim = f"Google rating {float(rating):.1f}"
            if rc:
                claim += f" across {int(rc):,} reviews"
            units.append(EvidenceUnit(
                id=_eid(venue_name, "rating"),
                claim=claim,
                claim_type="rating",
                source_family="google",
                confidence="high",
                safe_for_copy=True,
                venue_name=venue_name,
                category=category,
                metadata={"rating": rating, "review_count": rc},
            ))
        address = getattr(gv, "formatted_address", None)
        if address:
            units.append(EvidenceUnit(
                id=_eid(venue_name, "location"),
                claim=f"Located at {address}",
                claim_type="location",
                source_family="google",
                confidence="high",
                safe_for_copy=False,
                venue_name=venue_name,
                category=category,
                metadata={"address": address},
            ))
        units.append(EvidenceUnit(
            id=_eid(venue_name, "google_verified"),
            claim="Operational and verified on Google Places",
            claim_type="google_verified",
            source_family="google",
            confidence="high",
            safe_for_copy=True,
            venue_name=venue_name,
            category=category,
        ))

    # ── Michelin status ─────────────────────────────────────────────────────
    if michelin_status:
        units.append(EvidenceUnit(
            id=_eid(venue_name, "michelin_status"),
            claim=f"Michelin recognition: {michelin_status}",
            claim_type="michelin_status",
            source_family="editorial",
            confidence="high",
            safe_for_copy=True,
            venue_name=venue_name,
            category=category,
            metadata={"michelin_status": michelin_status},
        ))

    # ── Editorial / article source evidence ─────────────────────────────────
    se = source_evidence
    if se is not None:
        source_reason = getattr(se, "source_reason", None)
        source_ev_text = getattr(se, "source_evidence", None)
        if source_reason:
            units.append(EvidenceUnit(
                id=_eid(venue_name, "editorial_mention", 0),
                claim=str(source_reason),
                claim_type="editorial_mention",
                source_family="editorial",
                confidence="medium",
                safe_for_copy=True,
                venue_name=venue_name,
                category=category,
                metadata={
                    "source_domain": getattr(se, "source_domain", None),
                    "mention_count": getattr(se, "mention_count", 1),
                },
            ))
        if source_ev_text and source_ev_text != source_reason:
            units.append(EvidenceUnit(
                id=_eid(venue_name, "editorial_mention", 1),
                claim=str(source_ev_text),
                claim_type="editorial_mention",
                source_family="editorial",
                confidence="low",
                safe_for_copy=False,
                venue_name=venue_name,
                category=category,
                metadata={"source_domain": getattr(se, "source_domain", None)},
            ))

    # ── Tavily snippets ─────────────────────────────────────────────────────
    for i, snippet in enumerate(tavily_snippets or []):
        clean = (snippet or "").strip()
        if len(clean) > 10:
            units.append(EvidenceUnit(
                id=_eid(venue_name, "tavily_snippet", i),
                claim=clean[:200],
                claim_type="tavily_snippet",
                source_family="tavily",
                confidence="low",
                safe_for_copy=False,
                venue_name=venue_name,
                category=category,
            ))
            # Promote award signals (Michelin, James Beard) from Tavily as
            # structured attribute units safe for LLM differentiator selection.
            award_match = _AWARD_SIGNAL_RE.search(clean)
            if award_match:
                award_phrase = award_match.group(0).strip()
                units.append(EvidenceUnit(
                    id=_eid(venue_name, "attribute_t", i),
                    claim=f"Award recognition: {award_phrase}",
                    claim_type="attribute",
                    source_family="tavily",
                    confidence="medium",
                    safe_for_copy=True,
                    venue_name=venue_name,
                    category=category,
                    metadata={"award_phrase": award_phrase},
                ))

    # ── Yelp enrichment (non-canonical) ────────────────────────────────────
    if enrichment is not None:
        yelp_rating = getattr(enrichment, "yelp_rating", None)
        yelp_rc = getattr(enrichment, "yelp_review_count", None)
        if yelp_rating is not None:
            claim = f"Yelp rating {float(yelp_rating):.1f}"
            if yelp_rc:
                claim += f" ({int(yelp_rc):,} Yelp reviews)"
            units.append(EvidenceUnit(
                id=_eid(venue_name, "yelp_rating"),
                claim=claim,
                claim_type="yelp_rating",
                source_family="yelp",
                confidence="medium",
                safe_for_copy=False,
                venue_name=venue_name,
                category=category,
                metadata={"yelp_rating": yelp_rating, "yelp_review_count": yelp_rc},
            ))
        for i, excerpt in enumerate(getattr(enrichment, "yelp_review_excerpts", [])[:2]):
            clean = (excerpt or "").strip()
            if len(clean) > 10:
                units.append(EvidenceUnit(
                    id=_eid(venue_name, "yelp_review_excerpt", i),
                    claim=clean[:150],
                    claim_type="yelp_review_excerpt",
                    source_family="yelp",
                    confidence="low",
                    safe_for_copy=False,
                    venue_name=venue_name,
                    category=category,
                ))
                # Extract "known for X" signals from Yelp excerpts as structured
                # attribute units safe for LLM differentiator selection.
                kf_match = _KNOWN_FOR_RE.search(clean)
                if kf_match:
                    signal = kf_match.group(1).strip()[:60]
                    if len(signal) >= 5 and _is_specific_known_for_signal(signal):
                        units.append(EvidenceUnit(
                            id=_eid(venue_name, "attribute_y", i),
                            claim=f"Known for {signal}",
                            claim_type="attribute",
                            source_family="yelp",
                            confidence="medium",
                            safe_for_copy=True,
                            venue_name=venue_name,
                            category=category,
                        ))

    # ── Foursquare enrichment (non-canonical) ──────────────────────────────
    if enrichment is not None:
        for i, fs_cat in enumerate(getattr(enrichment, "foursquare_categories", [])[:2]):
            if fs_cat:
                units.append(EvidenceUnit(
                    id=_eid(venue_name, "foursquare_category", i),
                    claim=f"Categorized as {fs_cat} on Foursquare",
                    claim_type="foursquare_category",
                    source_family="foursquare",
                    confidence="medium",
                    safe_for_copy=False,
                    venue_name=venue_name,
                    category=category,
                ))
        for i, fs_tag in enumerate(getattr(enrichment, "foursquare_tags", [])[:3]):
            if fs_tag:
                is_specific = _foursquare_tag_is_specific(fs_tag)
                units.append(EvidenceUnit(
                    id=_eid(venue_name, "foursquare_tag", i),
                    claim=f"Tagged as {fs_tag}",
                    claim_type="foursquare_tag",
                    source_family="foursquare",
                    # Specific venue signals (e.g. "handmade tortillas",
                    # "craft cocktails") are safe to surface in LLM copy.
                    # Generic/use-case labels remain unsafe.
                    confidence="medium" if is_specific else "low",
                    safe_for_copy=is_specific,
                    venue_name=venue_name,
                    category=category,
                ))

    return units


def evidence_cache_key(
    venue_name: str,
    city: str,
    intent: str,
    evidence_units: List[EvidenceUnit],
) -> str:
    """Deterministic whyPick cache key = venue + city + intent + evidence hash."""
    claims = sorted(eu.claim for eu in evidence_units)
    evidence_hash = hashlib.md5(
        json.dumps(claims, ensure_ascii=False).encode()
    ).hexdigest()[:8]

    def _safe(s: str) -> str:
        return re.sub(r"\W+", "_", (s or "").lower())[:24]

    return f"whypick:{_safe(venue_name)}:{_safe(city)}:{_safe(intent)}:{evidence_hash}"


class _WhyPickCache:
    """Lightweight in-memory TTL cache for whyPick LLM results. Thread-safe."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._ttl = ttl_seconds
        self._store: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            payload, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return payload

    def set(self, key: str, payload: Any) -> None:
        with self._lock:
            self._store[key] = (payload, time.monotonic() + self._ttl)


_WHYPICK_CACHE = _WhyPickCache(ttl_seconds=3600)
