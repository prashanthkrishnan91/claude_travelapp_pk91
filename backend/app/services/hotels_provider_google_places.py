"""Google Places lodging provider — Hotels v1.

Backend-only HTTP integration plugged behind the
``app.services.hotels_provider.HotelProvider`` seam.  Honors the Hotels
Product Contract v1: never raises on transport / API failures, never
fabricates rows, and only emits ``HotelResult`` rows that satisfy
``assert_persistable_hotel``.

Important product caveat
------------------------
Google Places returns operational lodging entities (name, address,
rating, Google Maps URI) but **not** true nightly rates, room
availability, cancellation policy, or bookable inventory.  This adapter
emits ``HotelOfferKind.DISCOVERY`` rows only; ``price_per_night`` and
``price`` default to ``0.0`` (the wire model requires a numeric value),
and ``stars``/``amenities`` are left empty rather than invented.  A
future Hotels v2 (Booking.com Demand API or Amadeus Hotels) will add a
true bookable-rate adapter once partner credentials are confirmed.

Env vars (read at provider construction):

- ``GOOGLE_PLACES_API_KEY`` — already used by the canonical restaurants
  search; reused here so deployments do not need a second key.
- ``GOOGLE_HOTELS_ENABLED`` (optional; defaults to enabled when the key
  is present, disabled when absent).  Setting it to ``0``/``false``
  turns the adapter off without removing the key.

Security: all calls are server-side only; the API key is never exposed
to the frontend or persisted.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:  # pragma: no cover — httpx in requirements.txt
    httpx = None  # type: ignore[assignment]

from app.contracts.hotels import (
    HotelContractViolation,
    HotelSourceStatus,
    assert_persistable_hotel,
)
from app.models.search import HotelResult, HotelSearchRequest
from app.services.hotels_provider import HotelProviderResult


logger = logging.getLogger(__name__)


_PLACES_ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
_HTTP_TIMEOUT_SECONDS = 6.0
_MAX_RESULTS = 8

_LODGING_TYPES: frozenset = frozenset({
    "lodging",
    "hotel",
    "resort_hotel",
    "motel",
    "bed_and_breakfast",
    "guest_house",
    "extended_stay_hotel",
    "inn",
    "hostel",
})

_FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.businessStatus",
    "places.types",
    "places.primaryType",
    "places.rating",
    "places.userRatingCount",
    "places.googleMapsUri",
    "places.priceLevel",
])


_TRUTHY = {"1", "true", "yes", "on"}


def _truthy(value: Optional[str]) -> bool:
    return bool(value) and value.strip().lower() in _TRUTHY


class GooglePlacesHotelProvider:
    """Adapter for Google Places (New) Text Search restricted to lodging.

    Construct via :func:`build_google_places_hotel_provider_from_env` so
    credential and feature-flag checks live in one place.  The adapter
    holds no token (Google Places uses an API key) and no in-process
    cache; ``SearchService`` owns the per-query Supabase cache.
    """

    def __init__(
        self,
        *,
        api_key: str,
        http_client: Optional["httpx.Client"] = None,
        timeout: float = _HTTP_TIMEOUT_SECONDS,
        max_results: int = _MAX_RESULTS,
    ) -> None:
        if not api_key:
            raise ValueError("GooglePlacesHotelProvider requires an API key")
        self._api_key = api_key
        self._client = http_client
        self._owns_client = http_client is None
        self._timeout = timeout
        self._max_results = max(1, min(int(max_results), 10))

    def _get_http(self) -> "httpx.Client":
        if self._client is None:
            if httpx is None:  # pragma: no cover
                raise RuntimeError("httpx is not installed")
            self._client = httpx.Client(timeout=self._timeout)
        return self._client

    # ------------------------------------------------------------------
    # Public seam
    # ------------------------------------------------------------------

    def search_hotels(self, req: HotelSearchRequest) -> HotelProviderResult:
        location = (req.location or "").strip()
        if not location:
            return HotelProviderResult(
                status=HotelSourceStatus.EMPTY,
                rows=[],
                reason="missing location",
            )

        query = f"hotels in {location}"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": _FIELD_MASK,
        }
        body = {
            "textQuery": query,
            "maxResultCount": self._max_results,
            "includedType": "lodging",
        }

        try:
            resp = self._get_http().post(_PLACES_ENDPOINT, headers=headers, json=body)
        except Exception as exc:
            logger.warning("[google_hotels.transport_error] %s", exc)
            return HotelProviderResult(
                status=HotelSourceStatus.ERROR,
                rows=[],
                reason=f"transport error: {exc}",
            )

        if resp.status_code != 200:
            logger.warning(
                "[google_hotels.status] status=%d body=%s",
                resp.status_code,
                (resp.text or "")[:200],
            )
            return HotelProviderResult(
                status=HotelSourceStatus.ERROR,
                rows=[],
                reason=f"google places http {resp.status_code}",
            )

        try:
            payload = resp.json()
        except Exception as exc:
            logger.warning("[google_hotels.parse_error] %s", exc)
            return HotelProviderResult(
                status=HotelSourceStatus.ERROR,
                rows=[],
                reason=f"parse error: {exc}",
            )

        places = list(payload.get("places") or [])
        if not places:
            return HotelProviderResult(
                status=HotelSourceStatus.EMPTY,
                rows=[],
                reason="google places returned zero results",
            )

        rows: List[HotelResult] = []
        skipped = 0
        for place in places:
            row = _map_place_to_hotel(place, req)
            if row is None:
                skipped += 1
                continue
            try:
                assert_persistable_hotel(row)
            except HotelContractViolation:
                skipped += 1
                continue
            rows.append(row)

        if not rows:
            logger.info(
                "[google_hotels.all_skipped] skipped=%d location=%s",
                skipped, location,
            )
            return HotelProviderResult(
                status=HotelSourceStatus.EMPTY,
                rows=[],
                reason=f"all {skipped} candidates failed contract",
            )

        return HotelProviderResult(status=HotelSourceStatus.OK, rows=rows)


# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------


def _looks_like_lodging(types: List[str], primary_type: str) -> bool:
    lower_types = {(t or "").lower() for t in (types or [])}
    if (primary_type or "").lower() in _LODGING_TYPES:
        return True
    return bool(lower_types & _LODGING_TYPES)


def _map_place_to_hotel(
    place: Dict[str, Any],
    req: HotelSearchRequest,
) -> Optional[HotelResult]:
    """Map a Google Places lodging candidate to a contract-safe ``HotelResult``.

    Returns ``None`` when the candidate is not lodging, not operational,
    or missing required identity fields.  No fabricated booking URLs,
    no invented nightly rate, no invented stars/amenities.
    """
    if (place.get("businessStatus") or "OPERATIONAL") != "OPERATIONAL":
        return None

    place_id = (place.get("id") or "").strip()
    if not place_id:
        return None

    primary_type = (place.get("primaryType") or "").strip()
    types = list(place.get("types") or [])
    if not _looks_like_lodging(types, primary_type):
        return None

    display = place.get("displayName") or {}
    if isinstance(display, dict):
        name = (display.get("text") or "").strip()
    else:
        name = str(display or "").strip()
    if not name:
        return None

    formatted_address = (place.get("formattedAddress") or "").strip()
    location_data = place.get("location") or {}
    lat = location_data.get("latitude") if isinstance(location_data, dict) else None
    lng = location_data.get("longitude") if isinstance(location_data, dict) else None

    rating_raw = place.get("rating")
    try:
        rating = float(rating_raw) if rating_raw is not None else None
        if rating is not None and not (0.0 <= rating <= 5.0):
            rating = None
    except Exception:
        rating = None

    google_maps_uri = (place.get("googleMapsUri") or "").strip()

    nights = (req.check_out - req.check_in).days
    if nights <= 0:
        nights = 1

    # Real Google Maps URI is the only acceptable booking_url for a
    # discovery-only row.  We fall back to the deterministic place_id
    # URL so the wire model's required ``booking_url`` field always
    # carries a real, non-fabricated link.
    booking_url = google_maps_uri or (
        f"https://www.google.com/maps/place/?q=place_id:{place_id}"
    )

    location_str = formatted_address or req.location

    try:
        return HotelResult(
            id=f"gp-{place_id}",
            price=None,
            points_estimate=None,
            rating=rating,
            location=location_str,
            booking_url=booking_url,
            source="google_places",
            booking_options=[],
            name=name,
            check_in=req.check_in,
            check_out=req.check_out,
            nights=nights,
            stars=None,
            amenities=[],
            price_per_night=0.0,
            # Lodging discovery only — Google Places does not return a
            # true nightly rate.  ``has_real_rate=False`` is the contract
            # marker the frontend uses to refuse priced package
            # optimization on discovery-only rows.
            offer_kind="discovery",
            has_real_rate=False,
            ai_score=None,
            recommendation_tag="Lodging Discovery",
            tags=[],
            savings_vs_best=None,
            explanation="",
            lat=lat,
            lng=lng,
            location_score=None,
            proximity_label=None,
            area_label=None,
            distance_to_best_area=None,
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Env-gated builder
# ---------------------------------------------------------------------------


def google_places_hotels_enabled_from_env(env: Optional[Dict[str, str]] = None) -> bool:
    """True iff the env enables Google Places lodging discovery.

    The API key is required.  When ``GOOGLE_HOTELS_ENABLED`` is unset
    the adapter is enabled by default whenever the key is present;
    setting it to ``0``/``false`` explicitly disables the adapter.
    """
    env = env if env is not None else os.environ  # type: ignore[assignment]
    api_key = env.get("GOOGLE_PLACES_API_KEY") or ""
    if not api_key:
        return False
    flag = env.get("GOOGLE_HOTELS_ENABLED")
    if flag is None or flag == "":
        return True
    return _truthy(flag)


def build_google_places_hotel_provider_from_env(
    env: Optional[Dict[str, str]] = None,
) -> Optional[GooglePlacesHotelProvider]:
    env = env if env is not None else os.environ  # type: ignore[assignment]
    if not google_places_hotels_enabled_from_env(env):
        return None
    return GooglePlacesHotelProvider(
        api_key=env.get("GOOGLE_PLACES_API_KEY") or "",
    )


__all__ = [
    "GooglePlacesHotelProvider",
    "build_google_places_hotel_provider_from_env",
    "google_places_hotels_enabled_from_env",
]
