"""Google Places verification — Phase 3 gate for addable concierge venues.

This module provides ``GooglePlacesService`` (a.k.a. PlaceVerificationService),
the authoritative way to confirm a candidate venue surfaced from Tavily /
Serper / Brave article research is a real, currently-OPERATIONAL place.

Article search alone is not allowed to mark a card LIVE / addable. Every
candidate must pass through ``verify(name, destination, ...)`` and only
``business_status == "OPERATIONAL"`` matches with an acceptable confidence
score may flow into the restaurants / attractions / hotels arrays.

The verification result shape (``GooglePlaceVerification``) is normalized so
the rest of the pipeline does not depend on Google's HTTP wire format and so
results can be stored in cache transparently.

No SQL migration is required — verification results are kept in a process-
local TTL cache keyed by (candidate_name, destination, optional address /
neighborhood).
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Cache version — bump to invalidate previously-stored verification payloads
# whenever the verification logic / shape changes meaningfully.
GOOGLE_VERIFICATION_CACHE_VERSION = 1

# Field mask requested from the Google Places API. Keep it minimal to control
# cost — every additional field changes the SKU tier.
_PLACES_FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.businessStatus",
        "places.types",
        "places.rating",
        "places.userRatingCount",
        "places.googleMapsUri",
        "places.websiteUri",
        "places.regularOpeningHours",
        "places.currentOpeningHours",
    ]
)

OPERATIONAL = "OPERATIONAL"
CLOSED_PERMANENTLY = "CLOSED_PERMANENTLY"
CLOSED_TEMPORARILY = "CLOSED_TEMPORARILY"

PROVIDER_NAME = "google_places"

# Google Places category families that should never be surfaced as addable venue
# cards even if a name superficially matches (e.g. matching a candidate against
# a magazine publisher's listing page).
_NON_VENUE_TYPE_HINTS = frozenset(
    {
        "country",
        "administrative_area_level_1",
        "administrative_area_level_2",
        "administrative_area_level_3",
        "locality",
        "sublocality",
        "neighborhood",
        "postal_code",
        "political",
        "route",
        "establishment_unspecified",
        "news",
        "publisher",
    }
)

# Minimum normalized-name similarity required when only the name matches and
# we don't have separate strong address evidence.
_NAME_ONLY_MIN_SIMILARITY = 0.86
# When address evidence corroborates the match we can be slightly more lenient.
_NAME_WITH_ADDRESS_MIN_SIMILARITY = 0.65

_WHITESPACE_PAT = re.compile(r"\s+")
_NON_ALNUM_PAT = re.compile(r"[^a-z0-9 ]+")
_ARTICLE_LIKE_TYPES = frozenset({"news", "publisher", "newspaper"})


def _strip_diacritics(value: str) -> str:
    if not value:
        return ""
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", value) if not unicodedata.combining(ch)
    )


def _normalize_name(value: str) -> str:
    """Lowercase, drop diacritics + punctuation, collapse whitespace."""
    if not value:
        return ""
    base = _strip_diacritics(value).lower()
    base = _NON_ALNUM_PAT.sub(" ", base)
    base = _WHITESPACE_PAT.sub(" ", base).strip()
    return base


def _token_set(value: str) -> set:
    norm = _normalize_name(value)
    return {tok for tok in norm.split(" ") if tok}


def _name_similarity(a: str, b: str) -> float:
    """Jaccard similarity over normalized token sets — deterministic and cheap."""
    set_a = _token_set(a)
    set_b = _token_set(b)
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def _is_obvious_non_venue_types(types: List[str]) -> bool:
    if not types:
        return False
    lower = {(t or "").lower() for t in types}
    if lower & _ARTICLE_LIKE_TYPES:
        return True
    # Pure administrative result with no establishment-level type.
    has_establishment = any(
        t.endswith("_store") or t in {"restaurant", "bar", "cafe", "lodging", "hotel",
                                      "tourist_attraction", "museum", "park", "night_club",
                                      "food", "establishment", "point_of_interest"}
        for t in lower
    )
    if not has_establishment and (lower & _NON_VENUE_TYPE_HINTS):
        return True
    return False


def _looks_like_hotel(types: List[str]) -> bool:
    lower = {(t or "").lower() for t in (types or [])}
    return bool(lower & {"lodging", "hotel"})


def _candidate_inside_hotel_context(
    candidate: str,
    formatted_address: str,
    extracted_neighborhood: Optional[str],
) -> bool:
    """Return True when the candidate name plausibly references a venue inside a
    hotel — to allow hotel-typed Google matches when the article specifically
    pointed at, say, "Aviary at the Robey".
    """
    low_cand = (candidate or "").lower()
    if "hotel" in low_cand or "resort" in low_cand:
        return True
    if extracted_neighborhood and "hotel" in (extracted_neighborhood or "").lower():
        return True
    if formatted_address and "hotel" in formatted_address.lower():
        return True
    return False


@dataclass
class GooglePlaceVerification:
    """Normalized verification record returned from ``GooglePlacesService.verify``.

    A ``confidence`` of "high" or "medium" combined with ``business_status`` ==
    OPERATIONAL is required for the candidate to be promoted to an addable
    trip card. Anything else (no match / closed / low confidence) means the
    candidate stays in research_sources only.
    """

    provider: str = PROVIDER_NAME
    provider_place_id: Optional[str] = None
    name: Optional[str] = None
    formatted_address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    business_status: Optional[str] = None
    google_maps_uri: Optional[str] = None
    website_uri: Optional[str] = None
    rating: Optional[float] = None
    user_rating_count: Optional[int] = None
    types: List[str] = field(default_factory=list)
    confidence: str = "unknown"  # "high" | "medium" | "low" | "unknown"
    failure_reason: Optional[str] = None

    @property
    def is_operational(self) -> bool:
        return self.business_status == OPERATIONAL

    @property
    def is_closed(self) -> bool:
        return self.business_status in {CLOSED_PERMANENTLY, CLOSED_TEMPORARILY}

    @property
    def matched(self) -> bool:
        return bool(self.provider_place_id)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "GooglePlaceVerification":
        return cls(**{k: v for k, v in payload.items() if k in cls.__dataclass_fields__})


# ── Cache ────────────────────────────────────────────────────────────────────


class _GooglePlaceVerificationCache:
    """Thread-safe TTL cache shared across ConciergeService instances.

    Keys include a version prefix so a stale concierge cache from before the
    Google verification gate is automatically ignored on read.
    """

    def __init__(self, ttl_seconds: int = 1800) -> None:
        self._ttl = max(0, int(ttl_seconds))
        self._store: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def _wrap(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"_v": GOOGLE_VERIFICATION_CACHE_VERSION, **payload}

    def _unwrap(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return None
        if payload.get("_v") != GOOGLE_VERIFICATION_CACHE_VERSION:
            return None
        unwrapped = dict(payload)
        unwrapped.pop("_v", None)
        return unwrapped

    def get(self, key: str) -> Optional[GooglePlaceVerification]:
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
            inner = self._unwrap(payload)
            if inner is None:
                self._store.pop(key, None)
                return None
            return GooglePlaceVerification.from_dict(inner)

    def set(self, key: str, verification: GooglePlaceVerification) -> None:
        if self._ttl <= 0:
            return
        with self._lock:
            self._store[key] = (
                time.monotonic() + self._ttl,
                self._wrap(verification.to_dict()),
            )

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


_GLOBAL_PLACE_CACHE = _GooglePlaceVerificationCache(ttl_seconds=1800)


def _make_cache_key(
    candidate: str,
    destination: str,
    address: Optional[str] = None,
    neighborhood: Optional[str] = None,
) -> str:
    parts = [
        f"v{GOOGLE_VERIFICATION_CACHE_VERSION}",
        _normalize_name(candidate),
        _normalize_name(destination),
        _normalize_name(address or ""),
        _normalize_name(neighborhood or ""),
    ]
    return "gplace::" + "::".join(parts)


# ── HTTP client abstraction ──────────────────────────────────────────────────


class _GooglePlacesHTTPClient:
    """Thin wrapper around the Google Places (New) Text Search endpoint.

    Kept separate from the service so tests can substitute a stub without
    needing to mock httpx itself.
    """

    _ENDPOINT = "https://places.googleapis.com/v1/places:searchText"

    def __init__(self, api_key: str, timeout: float = 6.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def text_search(self, query: str) -> List[Dict[str, Any]]:
        if not self.available:
            return []
        try:
            import httpx
        except ImportError:
            logger.warning("httpx not installed; Google Places verification disabled")
            return []
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": _PLACES_FIELD_MASK,
        }
        body = {"textQuery": query, "maxResultCount": 5}
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(self._ENDPOINT, headers=headers, json=body)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("Google Places search failed: %s", exc)
            return []
        return list(data.get("places") or [])


# ── Service ──────────────────────────────────────────────────────────────────


class GooglePlacesService:
    """Verify a candidate venue with Google Places before it is shown LIVE.

    Usage::

        svc = GooglePlacesService()
        result = svc.verify("Kumiko", "Chicago", neighborhood="West Loop")
        if result.is_operational and result.confidence in {"high", "medium"}:
            ...  # promote to addable

    The service degrades gracefully if no API key is configured: ``verify``
    returns a verification record with ``confidence="unknown"`` and
    ``failure_reason="provider_unavailable"`` so callers can keep the
    candidate as research_source only.
    """

    def __init__(
        self,
        client: Optional[_GooglePlacesHTTPClient] = None,
        cache: Optional[_GooglePlaceVerificationCache] = None,
        *,
        api_key: Optional[str] = None,
        timeout: float = 6.0,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            resolved_key = api_key if api_key is not None else os.getenv("GOOGLE_PLACES_API_KEY", "")
            self._client = _GooglePlacesHTTPClient(api_key=resolved_key or "", timeout=timeout)
        self._cache = cache if cache is not None else _GLOBAL_PLACE_CACHE

    @property
    def available(self) -> bool:
        return bool(self._client.available)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def verify(
        self,
        candidate: str,
        destination: str,
        *,
        address: Optional[str] = None,
        neighborhood: Optional[str] = None,
        intent: Optional[str] = None,
    ) -> GooglePlaceVerification:
        """Resolve a single candidate against Google Places.

        Always returns a ``GooglePlaceVerification`` — never raises. Callers
        decide how to act based on ``business_status`` / ``confidence``.
        """
        candidate_clean = (candidate or "").strip()
        destination_clean = (destination or "").strip()
        if not candidate_clean or not destination_clean:
            return GooglePlaceVerification(
                confidence="unknown",
                failure_reason="empty_candidate_or_destination",
            )

        cache_key = _make_cache_key(candidate_clean, destination_clean, address, neighborhood)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if not self.available:
            verification = GooglePlaceVerification(
                confidence="unknown",
                failure_reason="provider_unavailable",
            )
            # Do NOT cache provider_unavailable — caller may configure later.
            return verification

        query = self._build_query(candidate_clean, destination_clean, address, neighborhood)
        try:
            places = self._client.text_search(query)
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning("Google Places verification raised: %s", exc)
            verification = GooglePlaceVerification(
                confidence="unknown",
                failure_reason=f"provider_error:{type(exc).__name__}",
            )
            return verification

        verification = self._select_best_match(
            candidate=candidate_clean,
            destination=destination_clean,
            places=places,
            address=address,
            neighborhood=neighborhood,
            intent=intent,
        )
        # Cache both matched and no-match results so we don't burn API calls on
        # the same candidate twice within the TTL window.
        self._cache.set(cache_key, verification)
        self._log_decision(candidate_clean, destination_clean, verification)
        return verification

    def verify_many(
        self,
        candidates: List[Tuple[str, Optional[str]]],
        destination: str,
        *,
        intent: Optional[str] = None,
    ) -> Dict[str, GooglePlaceVerification]:
        """Verify a batch of candidates. Returns a {lowercased name: result} map.

        ``candidates`` is a list of ``(name, neighborhood)`` tuples — the
        neighborhood may be ``None`` if not extracted from the article.
        """
        results: Dict[str, GooglePlaceVerification] = {}
        for name, neighborhood in candidates:
            if not name:
                continue
            key = name.lower()
            if key in results:
                continue
            results[key] = self.verify(name, destination, neighborhood=neighborhood, intent=intent)
        return results

    def clear_cache_for_destination(self, destination: str) -> int:
        """Drop every cached verification for a given destination."""
        norm_destination = _normalize_name(destination)
        if not norm_destination:
            return 0

        def _matches(key: str) -> bool:
            parts = key.split("::")
            # gplace::vN::<candidate>::<destination>::<address>::<neighborhood>
            if len(parts) < 4:
                return False
            return parts[3] == norm_destination

        return self._cache.clear_matching(_matches)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_query(
        self,
        candidate: str,
        destination: str,
        address: Optional[str],
        neighborhood: Optional[str],
    ) -> str:
        parts = [candidate]
        if neighborhood and _normalize_name(neighborhood) != _normalize_name(destination):
            parts.append(neighborhood)
        if address:
            parts.append(address)
        parts.append(destination)
        return " ".join(p for p in parts if p).strip()

    def _select_best_match(
        self,
        *,
        candidate: str,
        destination: str,
        places: List[Dict[str, Any]],
        address: Optional[str],
        neighborhood: Optional[str],
        intent: Optional[str],
    ) -> GooglePlaceVerification:
        if not places:
            return GooglePlaceVerification(
                confidence="low",
                failure_reason="no_match",
            )

        norm_destination = _normalize_name(destination)
        norm_neighborhood = _normalize_name(neighborhood or "")
        norm_address = _normalize_name(address or "")

        best: Optional[GooglePlaceVerification] = None
        best_score = 0.0
        best_failure: Optional[str] = None

        for place in places:
            name = (place.get("displayName") or {}).get("text") or place.get("displayName")
            if isinstance(name, dict):
                name = name.get("text", "")
            name = (name or "").strip()
            similarity = _name_similarity(candidate, name)

            formatted_address = (place.get("formattedAddress") or "").strip()
            norm_formatted_address = _normalize_name(formatted_address)
            types = list(place.get("types") or [])
            location = place.get("location") or {}
            lat = location.get("latitude") if isinstance(location, dict) else None
            lng = location.get("longitude") if isinstance(location, dict) else None
            business_status = place.get("businessStatus")
            place_id = place.get("id")

            failure_reason: Optional[str] = None

            address_evidence = bool(
                (norm_destination and norm_destination in norm_formatted_address)
                or (norm_neighborhood and norm_neighborhood in norm_formatted_address)
                or (norm_address and norm_address in norm_formatted_address)
            )

            if _is_obvious_non_venue_types(types):
                failure_reason = "non_venue_types"
            else:
                if not address_evidence and similarity < _NAME_ONLY_MIN_SIMILARITY:
                    failure_reason = "weak_match_no_address"
                elif address_evidence and similarity < _NAME_WITH_ADDRESS_MIN_SIMILARITY:
                    failure_reason = "weak_name_match"

                # Reject hotel-typed matches when the candidate isn't itself a
                # hotel and the article didn't reference one — avoids matching
                # to an unrelated hotel listing page.
                if (
                    failure_reason is None
                    and _looks_like_hotel(types)
                    and intent != "hotels"
                    and not _candidate_inside_hotel_context(candidate, formatted_address, neighborhood)
                ):
                    failure_reason = "hotel_match_for_non_hotel_candidate"

            confidence = self._score_to_confidence(similarity, address_evidence=address_evidence)

            verification = GooglePlaceVerification(
                provider=PROVIDER_NAME,
                provider_place_id=place_id if failure_reason is None else None,
                name=name or None,
                formatted_address=formatted_address or None,
                lat=lat,
                lng=lng,
                business_status=business_status,
                google_maps_uri=place.get("googleMapsUri"),
                website_uri=place.get("websiteUri"),
                rating=place.get("rating"),
                user_rating_count=place.get("userRatingCount"),
                types=types,
                confidence=confidence if failure_reason is None else "low",
                failure_reason=failure_reason,
            )

            score = similarity + (0.15 if business_status == OPERATIONAL else 0.0)
            if failure_reason is None and score > best_score:
                best = verification
                best_score = score
                best_failure = None
            elif best is None:
                # Track best-effort for failure reporting if no clean match.
                best = verification
                best_failure = failure_reason

        if best is None:
            return GooglePlaceVerification(confidence="low", failure_reason="no_match")
        if best_failure and best.failure_reason is None:
            best.failure_reason = best_failure
        return best

    @staticmethod
    def _score_to_confidence(similarity: float, *, address_evidence: bool) -> str:
        if similarity >= 0.95 and address_evidence:
            return "high"
        if similarity >= 0.86 or (similarity >= 0.75 and address_evidence):
            return "medium"
        if similarity >= 0.5:
            return "low"
        return "unknown"

    def _log_decision(
        self,
        candidate: str,
        destination: str,
        verification: GooglePlaceVerification,
    ) -> None:
        logger.info(
            "google_places.verify candidate=%r destination=%r matched=%s status=%s confidence=%s reason=%s",
            candidate,
            destination,
            verification.matched,
            verification.business_status,
            verification.confidence,
            verification.failure_reason,
        )


# ── Helpers exposed for the rest of the pipeline ────────────────────────────


def is_addable(verification: Optional[GooglePlaceVerification]) -> bool:
    """Single source of truth for whether a card may flow into addable arrays."""
    if verification is None:
        return False
    if not verification.matched:
        return False
    if not verification.is_operational:
        return False
    if verification.confidence not in {"high", "medium"}:
        return False
    return True


def reset_global_place_cache() -> None:
    """Test helper — clear the module-level Google Places verification cache."""
    _GLOBAL_PLACE_CACHE.clear()


def clear_place_cache_for_destination(destination: str) -> int:
    """Module-level helper for clearing cache without a service instance."""
    return _GLOBAL_PLACE_CACHE.clear_matching(
        lambda key: key.split("::")[3:4] == [_normalize_name(destination)]
    )
