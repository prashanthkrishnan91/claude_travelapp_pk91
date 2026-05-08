"""SearchService — fetch (or generate mock) results and cache them in Supabase.

Architecture
------------
1. Build a deterministic cache_key from the serialised query.
2. Check research_cache for a live hit (not expired).
3. On miss: call the appropriate _fetch_* method (currently returns realistic
   mock data; swap in real provider clients when API keys are available).
4. Persist the result set to research_cache with a configurable TTL.
5. Return the normalised result list to the route handler.

Product Surface Pruning v1A — legacy mock quarantine
----------------------------------------------------
The ``_mock_flights`` / ``_mock_hotels`` helpers in this module are
**legacy test/demo-only fixtures** preserved for the future
provider-backed Flights/Hotels v1 product track.  They predate the
canonical AI Concierge display contract (see
``backend/app/concierge/display_contract.py``) and are still reachable
through the legacy ``/search/{flights,hotels,round-trip-flights}`` routes
consumed by ``OptimizeTripModal`` (the only remaining live caller).
``/trips/create-with-search`` and ``OptimizeTripModal`` fail closed on any
mock-derived row (``source ∈ {mock, demo, fixture}`` or
``book.example.com`` booking URL), so no mock-backed flight or hotel can
reach a persisted trip.  ``_mock_restaurants`` was deleted in the
final mock-leak closeout — ``search_restaurants`` runs canonical Google
Places fail-closed and never had a mock-backed live caller.  Until a
provider-backed Flights/Hotels v1 lands, these helpers must be:

- explicitly marked as legacy via the ``__legacy_product_mock__`` attribute
  (``is_legacy_product_mock(fn)`` and ``LEGACY_PRODUCT_MOCK_FUNCTIONS``);
- runtime-blockable via the ``BLOCK_LEGACY_PRODUCT_MOCK`` env flag so an
  operator can fail-closed in production without a redeploy;
- traceable via the ``legacy_product_mock`` structured log channel so we can
  measure leakage rate in production logs before/after the v1B migration.

Do not extend or grow new mock fixtures.  All new place data must flow
through ``/ai/concierge/search`` and the canonical display contract.
"""

import hashlib
import logging
import json
import math
import os
import random
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

try:
    import httpx as httpx
except ImportError:  # pragma: no cover — httpx is in requirements.txt
    httpx = None  # type: ignore[assignment]

from supabase import Client

from app.models.search import (
    BookingOption,
    FlightResult,
    FlightSearchRequest,
    HotelResult,
    HotelSearchRequest,
    RestaurantResult,
    RestaurantSearchRequest,
    RoundTripFlightPair,
)

CACHE_TABLE = "research_cache"
logger = logging.getLogger(__name__)
CACHE_TTL_HOURS = 1


# ---------------------------------------------------------------------------
# Product Surface Pruning v1A — legacy mock quarantine seam
# ---------------------------------------------------------------------------

# Operator-flippable production guard.  When this env var is truthy, the four
# legacy mock generators below return an empty list instead of fabricating
# product data.  This is the safe production switch the v1B migration plan
# uses to verify each frontend caller can survive without mock data before
# the route is removed.
_LEGACY_PRODUCT_MOCK_BLOCK_ENV = "BLOCK_LEGACY_PRODUCT_MOCK"


def _truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _legacy_product_mock_blocked() -> bool:
    """Return True when the operator has set the production block flag."""
    return _truthy(os.getenv(_LEGACY_PRODUCT_MOCK_BLOCK_ENV))


def _mark_legacy_product_mock(fn: "Callable[..., Any]") -> "Callable[..., Any]":
    """Tag a callable as a legacy product-surface mock fixture.

    The ``__legacy_product_mock__`` attribute is read by
    ``is_legacy_product_mock`` and the v1A regression tests so the module's
    quarantine surface can be enumerated without string-matching function
    names.  Callers should not rely on this attribute for runtime decisions —
    use the explicit ``_legacy_product_mock_blocked()`` check instead.
    """
    setattr(fn, "__legacy_product_mock__", True)
    return fn


def is_legacy_product_mock(fn: "Callable[..., Any]") -> bool:
    """Public predicate: True iff ``fn`` is a legacy mock fixture.

    Used by ``backend/tests/test_product_surface_pruning_v1a.py`` to assert the
    quarantine surface stays in sync with this module.
    """
    return bool(getattr(fn, "__legacy_product_mock__", False))


def _log_legacy_product_mock_event(
    *,
    event: str,
    namespace: str,
    location: str,
    requested_count: int,
    returned_count: int,
) -> None:
    """Structured telemetry for legacy mock emission and blocking.

    Two events:

    - ``legacy_product_mock_blocked`` — the operator set
      ``BLOCK_LEGACY_PRODUCT_MOCK`` and we returned an empty list instead of
      fabricated data.
    - ``legacy_product_mock_emitted`` — mock data was returned to the caller.
      Useful as a leakage rate gauge while v1B migrates frontend surfaces.

    Both events use the ``legacy_product_mock.<event>`` log key so they can
    be grep'd from a single Railway query.
    """
    logger.warning(
        "[legacy_product_mock.%s] namespace=%s location=%s requested=%d returned=%d",
        event,
        namespace,
        location,
        requested_count,
        returned_count,
    )


# Cache namespaces whose ``research_cache`` rows can only have come from the
# legacy mock fixtures.  ``restaurants`` is intentionally **excluded**: it is
# served by the canonical Google Places provider with fail-closed semantics
# and already has its own stale-mock cache eviction in ``search_restaurants``.
_LEGACY_MOCK_DEPENDENT_NAMESPACES: frozenset = frozenset({
    "flights",
    "hotels",
})

# Per-row ``source`` attributions that positively identify a cached row as
# coming from a real, non-mock provider.  Cached rows whose every entry is in
# this set are trusted under ``BLOCK_LEGACY_PRODUCT_MOCK``; everything else
# (mock, missing, mixed) fails closed.
_CANONICAL_CACHE_SOURCES: frozenset = frozenset({
    "google_places",
})


def _suppress_legacy_mock_cache(
    namespace: str,
    cached: Optional[List[Dict[str, Any]]],
) -> bool:
    """Decide whether a cached row set must be suppressed under the v1A
    operator block.

    The cache-side companion to the per-fixture block in ``_mock_*``.  When
    ``BLOCK_LEGACY_PRODUCT_MOCK`` is truthy the cache itself can still hold a
    legacy mock payload from before the flag was flipped, and a naive
    ``cache hit → return`` would silently keep emitting fabricated data.

    Returns True when the operator flag is on AND the namespace is in
    ``_LEGACY_MOCK_DEPENDENT_NAMESPACES`` AND the cached rows are not
    unambiguously attributed to a canonical (non-mock) provider.  In other
    words: under the flag, only positively-identified non-mock cache rows
    are allowed through; ambiguous or mock rows fail closed.
    """
    if not _legacy_product_mock_blocked():
        return False
    if namespace not in _LEGACY_MOCK_DEPENDENT_NAMESPACES:
        return False
    if not cached:
        return False
    return not all(
        item.get("source") in _CANONICAL_CACHE_SOURCES for item in cached
    )


# Known city centres for coordinate generation
_CITY_CENTERS: Dict[str, tuple] = {
    "honolulu": (21.3069, -157.8583),
    "waikiki": (21.2814, -157.8369),
    "new york": (40.7128, -74.0060),
    "paris": (48.8566, 2.3522),
    "london": (51.5074, -0.1278),
    "tokyo": (35.6762, 139.6503),
    "sydney": (-33.8688, 151.2093),
    "los angeles": (34.0522, -118.2437),
    "miami": (25.7617, -80.1918),
    "chicago": (41.8781, -87.6298),
    "san francisco": (37.7749, -122.4194),
    "barcelona": (41.3851, 2.1734),
    "rome": (41.9028, 12.4964),
    "amsterdam": (52.3676, 4.9041),
    "dubai": (25.2048, 55.2708),
    "singapore": (1.3521, 103.8198),
    "bali": (-8.4095, 115.1889),
    "cancun": (21.1619, -86.8515),
    "bangkok": (13.7563, 100.5018),
    "istanbul": (41.0082, 28.9784),
    "prague": (50.0755, 14.4378),
    "vienna": (48.2082, 16.3738),
    "berlin": (52.5200, 13.4050),
    "madrid": (40.4168, -3.7038),
    "lisbon": (38.7223, -9.1393),
    "athens": (37.9838, 23.7275),
    "cairo": (30.0444, 31.2357),
    "cape town": (-33.9249, 18.4241),
    "mexico city": (19.4326, -99.1332),
    "toronto": (43.6532, -79.3832),
    "vancouver": (49.2827, -123.1207),
    "seoul": (37.5665, 126.9780),
    "beijing": (39.9042, 116.4074),
    "shanghai": (31.2304, 121.4737),
    "mumbai": (19.0760, 72.8777),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cache_key(namespace: str, query: Dict[str, Any]) -> str:
    """Return a stable SHA-256 fingerprint for a search query."""
    canonical = json.dumps({"ns": namespace, **query}, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# Proximity clustering helpers
# ---------------------------------------------------------------------------

def _get_city_center(location: str) -> tuple:
    city = location.split(",")[0].strip().lower()
    for key, coords in _CITY_CENTERS.items():
        if key in city or city in key:
            return coords
    h = hashlib.md5(city.encode()).digest()
    lat = 35.0 + (h[0] - 128) / 20.0
    lng = -80.0 + (h[1] - 128) / 5.0
    return lat, lng


def _spread_coordinates(center_lat: float, center_lng: float, index: int, total: int, max_radius_km: float = 2.5) -> tuple:
    golden_angle = 2.399963  # ~137.5° in radians
    radius_km = max_radius_km * math.sqrt((index + 0.5) / max(total, 1))
    angle = index * golden_angle
    lat_offset = (radius_km / 111.0) * math.cos(angle)
    lng_offset = (radius_km / (111.0 * math.cos(math.radians(center_lat)))) * math.sin(angle)
    return round(center_lat + lat_offset, 6), round(center_lng + lng_offset, 6)


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(max(0.0, min(1.0, a))))


def _compute_hotel_location_intelligence(
    hotel_lat: float,
    hotel_lng: float,
    center_lat: float,
    center_lng: float,
    num_attractions: int = 8,
) -> tuple:
    """Return (location_score, proximity_label, area_label) for a hotel.

    Simulates proximity to the top N attractions spread around the city center.
    """
    total_dist_km = 0.0
    for i in range(num_attractions):
        att_lat, att_lng = _spread_coordinates(center_lat, center_lng, i, num_attractions, max_radius_km=1.5)
        total_dist_km += _haversine_km(hotel_lat, hotel_lng, att_lat, att_lng)
    avg_km = total_dist_km / num_attractions

    # Walking speed ~4 km/h → 15 min/km
    avg_minutes = avg_km * 15.0
    location_score = round(max(0.0, min(100.0, 100.0 - avg_km * 25.0)), 1)

    mins_rounded = max(1, round(avg_minutes))
    proximity_label = f"{mins_rounded} min from top attractions"

    if location_score >= 78:
        area_label = "In Best Area"
    elif location_score >= 55:
        area_label = "Close to Best Area"
    else:
        area_label = "Far from action"

    return location_score, proximity_label, area_label, round(avg_km, 2)


# ---------------------------------------------------------------------------
# Mock data generators
# ---------------------------------------------------------------------------

def _mock_flights(req: FlightSearchRequest) -> List[FlightResult]:
    """Generate realistic-looking flight options for the requested route.

    Legacy product-surface mock fixture (Product Surface Pruning v1A).  The
    ``BLOCK_LEGACY_PRODUCT_MOCK`` env flag short-circuits this helper to an
    empty list so production operators can fail-closed before the v1B
    migration replaces ``/search/flights`` callers.
    """
    if _legacy_product_mock_blocked():
        _log_legacy_product_mock_event(
            event="blocked",
            namespace="flights",
            location=f"{(req.origin or req.destination or '?')!s}",
            requested_count=req.passengers or 1,
            returned_count=0,
        )
        return []

    airlines = [
        ("AA", "American Airlines"),
        ("UA", "United Airlines"),
        ("DL", "Delta Air Lines"),
        ("B6", "JetBlue"),
        ("AS", "Alaska Airlines"),
    ]
    cabin_multipliers = {
        "economy": 1.0,
        "premium_economy": 1.9,
        "business": 4.5,
        "first": 7.0,
    }
    cabin_mul = cabin_multipliers.get(req.cabin_class, 1.0)
    base_price = random.uniform(180, 650) * req.passengers * cabin_mul

    results: List[FlightResult] = []
    for i, (code, name) in enumerate(random.sample(airlines, k=len(airlines))):
        dep_hour = random.randint(5, 21)
        duration = random.randint(90, 480)
        dep_dt = datetime.combine(req.departure_date, __import__("datetime").time(dep_hour, random.choice([0, 15, 30, 45])), tzinfo=timezone.utc)
        arr_dt = dep_dt + timedelta(minutes=duration)
        price = round(base_price * random.uniform(0.85, 1.25), 2)
        points_estimate = int(price * random.uniform(70, 130))  # ~100 pts/USD earned

        # Award redemption cost — varies 40–100 pts/USD so cpp spans ~1.0–2.5
        pts_per_dollar = random.uniform(40, 100)
        points_cost = int(price * pts_per_dollar)
        cpp = round((price * 100) / points_cost, 2) if points_cost > 0 else 0.0
        recommendation_tag = "Good Points Value" if cpp >= 2.0 else "Better with Cash"

        direct_url = f"https://book.example.com/flights/{code.lower()}/{req.origin.lower()}/{req.destination.lower()}"
        flight_options = [
            BookingOption(provider="airline_direct", url=direct_url),
            BookingOption(provider="google_flights", url=f"https://book.example.com/flights/google/{req.origin.lower()}-{req.destination.lower()}"),
            BookingOption(provider="kayak", url=f"https://book.example.com/flights/kayak/{req.origin.lower()}-{req.destination.lower()}"),
            BookingOption(provider="chase_portal", url=f"https://book.example.com/flights/chase/{req.origin.lower()}-{req.destination.lower()}"),
            BookingOption(provider="amex_travel", url=f"https://book.example.com/flights/amex/{req.origin.lower()}-{req.destination.lower()}"),
        ]
        results.append(
            FlightResult(
                id=f"{code}-{uuid4().hex[:8].upper()}",
                price=price,
                points_estimate=points_estimate,
                rating=round(random.uniform(3.2, 4.9), 1),
                location=f"{req.origin} → {req.destination}",
                booking_url=direct_url,
                source="mock",
                booking_options=flight_options,
                airline=name,
                flight_number=f"{code}{random.randint(100, 9999)}",
                origin=req.origin.upper(),
                destination=req.destination.upper(),
                departure_time=dep_dt,
                arrival_time=arr_dt,
                duration_minutes=duration,
                stops=random.choices([0, 1, 2], weights=[55, 35, 10])[0],
                cabin_class=req.cabin_class,
                points_cost=points_cost,
                cpp=cpp,
                recommendation_tag=recommendation_tag,
            )
        )

    results.sort(key=lambda r: r.price or 0)
    _log_legacy_product_mock_event(
        event="emitted",
        namespace="flights",
        location=f"{(req.origin or req.destination or '?')!s}",
        requested_count=req.passengers or 1,
        returned_count=len(results),
    )
    return results, "ok" if results else "empty"


def _mock_hotels(req: HotelSearchRequest) -> List[HotelResult]:
    """Generate realistic hotel options for the requested location and dates.

    Legacy product-surface mock fixture (Product Surface Pruning v1A).  See
    module docstring for the quarantine seam.  Honors the
    ``BLOCK_LEGACY_PRODUCT_MOCK`` env flag.
    """
    if _legacy_product_mock_blocked():
        _log_legacy_product_mock_event(
            event="blocked",
            namespace="hotels",
            location=req.location,
            requested_count=req.guests or 1,
            returned_count=0,
        )
        return []

    nights = (req.check_out - req.check_in).days or 1
    hotel_templates = [
        ("Grand Hyatt {loc}", 5, ["pool", "spa", "gym", "restaurant", "concierge"]),
        ("Marriott {loc} Downtown", 4, ["gym", "restaurant", "business center", "parking"]),
        ("Hilton {loc} Garden Inn", 3, ["gym", "free breakfast", "free parking", "wifi"]),
        ("Airbnb Entire Apt · {loc}", None, ["kitchen", "washer", "wifi", "self check-in"]),
        ("citizenM {loc}", 4, ["rooftop bar", "gym", "canteen", "24h check-in"]),
        ("Aloft {loc}", 3, ["pool", "gym", "bar", "bike rentals"]),
    ]
    city = req.location.split(",")[0].strip().title()
    center_lat, center_lng = _get_city_center(req.location)
    total_hotels = len(hotel_templates)

    results: List[HotelResult] = []
    for idx, (tpl_name, stars, amenities) in enumerate(random.sample(hotel_templates, k=total_hotels)):
        name = tpl_name.format(loc=city)
        nightly = round(random.uniform(80, 550), 2)
        if req.max_price:
            nightly = min(nightly, req.max_price)
        total = round(nightly * nights, 2)
        points = int(total * random.uniform(80, 120))

        # Assign coordinates: spread hotels around the city center at varying distances
        hotel_lat, hotel_lng = _spread_coordinates(center_lat, center_lng, idx, total_hotels, max_radius_km=3.0)

        # Compute location intelligence relative to top attractions cluster
        location_score, proximity_label, area_label, distance_to_best_area = _compute_hotel_location_intelligence(
            hotel_lat, hotel_lng, center_lat, center_lng
        )

        name_slug = name.lower().replace(" ", "-").replace("·", "").replace("  ", "-")
        loc_slug = req.location.lower().replace(" ", "-").replace(",", "")
        direct_url = f"https://book.example.com/hotels/{name_slug}"
        hotel_options = [
            BookingOption(provider="booking_com", url=f"https://book.example.com/hotels/booking/{name_slug}"),
            BookingOption(provider="expedia", url=f"https://book.example.com/hotels/expedia/{name_slug}"),
            BookingOption(provider="hotels_com", url=f"https://book.example.com/hotels/hotels-com/{name_slug}"),
            BookingOption(provider="chase_portal", url=f"https://book.example.com/hotels/chase/{loc_slug}"),
            BookingOption(provider="amex_travel", url=f"https://book.example.com/hotels/amex/{loc_slug}"),
        ]
        results.append(
            HotelResult(
                id=f"htl-{uuid4().hex[:10]}",
                price=total,
                points_estimate=points,
                rating=round(random.uniform(3.0, 5.0), 1),
                location=req.location,
                booking_url=direct_url,
                source="mock",
                booking_options=hotel_options,
                name=name,
                check_in=req.check_in,
                check_out=req.check_out,
                nights=nights,
                stars=float(stars) if stars else None,
                amenities=amenities,
                price_per_night=nightly,
                lat=hotel_lat,
                lng=hotel_lng,
                location_score=location_score,
                proximity_label=proximity_label,
                area_label=area_label,
                distance_to_best_area=distance_to_best_area,
            )
        )

    results.sort(key=lambda r: r.price or 0)
    _log_legacy_product_mock_event(
        event="emitted",
        namespace="hotels",
        location=req.location,
        requested_count=req.guests or 1,
        returned_count=len(results),
    )
    return results


def _compute_restaurant_ai_score(
    rating: float,
    num_reviews: int,
    price_level: int,
    sentiment: Optional[float] = None,
) -> float:
    """Compute AI value score 0–100 from rating, review volume, price level, and optional sentiment."""
    rating_score = (rating / 5.0) * 100
    review_score = min(100.0, (math.log1p(num_reviews) / math.log1p(500_000)) * 100)
    price_value = max(0.0, (4 - price_level) / 4.0 * 100)
    if sentiment is not None:
        raw = rating_score * 0.40 + review_score * 0.30 + price_value * 0.15 + sentiment * 100 * 0.15
    else:
        raw = rating_score * 0.45 + review_score * 0.35 + price_value * 0.20
    return round(min(100.0, max(0.0, raw)), 1)


def _compute_restaurant_tags(
    ai_score: float,
    rating: float,
    num_reviews: int,
    price_level: int,
) -> list:
    """Assign human-readable tags based on score, rating, popularity, and price level."""
    tags: list = []
    if ai_score >= 80:
        tags.append("Must Try")
    if price_level >= 3 and rating >= 4.5:
        tags.append("Fine Dining")
    if num_reviews >= 20_000 and price_level <= 2:
        tags.append("Local Favorite")
    if price_level <= 1 and rating >= 4.0:
        tags.append("Budget Friendly")
    return tags


# ``_mock_restaurants`` was deleted in the final mock-leak closeout PR.
# Rationale: ``SearchService.search_restaurants`` runs the canonical Google
# Places provider with fail-closed semantics (no provider key → empty list),
# and no live caller routed through the mock fixture.  The do-not-resurrect
# guard lives in ``backend/tests/test_product_surface_pruning_v1a.py``.


# ---------------------------------------------------------------------------
# Google Places live restaurant provider
# ---------------------------------------------------------------------------

_GOOGLE_PLACES_SEARCH_ENDPOINT = "https://places.googleapis.com/v1/places:searchText"

# Field mask for restaurant search — includes price and type fields not in the
# verification mask used by GooglePlacesService.
_RESTAURANT_SEARCH_FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.businessStatus",
    "places.types",
    "places.rating",
    "places.userRatingCount",
    "places.googleMapsUri",
    "places.regularOpeningHours",
    "places.priceLevel",
    "places.primaryType",
])

# Google Places (New API) priceLevel enum → integer 0–4
_PRICE_LEVEL_MAP: Dict[str, int] = {
    "PRICE_LEVEL_FREE": 0,
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
}

# Google Places primaryType / types → human-readable cuisine label
_GOOGLE_TYPE_TO_CUISINE: Dict[str, str] = {
    "japanese_restaurant": "Japanese",
    "sushi_restaurant": "Sushi",
    "ramen_restaurant": "Ramen",
    "chinese_restaurant": "Chinese",
    "italian_restaurant": "Italian",
    "pizza_restaurant": "Pizza",
    "mexican_restaurant": "Mexican",
    "indian_restaurant": "Indian",
    "thai_restaurant": "Thai",
    "french_restaurant": "French",
    "mediterranean_restaurant": "Mediterranean",
    "greek_restaurant": "Greek",
    "spanish_restaurant": "Spanish",
    "american_restaurant": "American",
    "hamburger_restaurant": "Burgers",
    "seafood_restaurant": "Seafood",
    "steak_house": "Steakhouse",
    "korean_restaurant": "Korean",
    "vietnamese_restaurant": "Vietnamese",
    "middle_eastern_restaurant": "Middle Eastern",
    "vegetarian_restaurant": "Vegetarian",
    "brunch_restaurant": "Brunch",
    "fast_food_restaurant": "Fast Food",
    "cafe": "Café",
    "coffee_shop": "Coffee",
    "bakery": "Bakery",
    "bar": "Bar",
}


def _fetch_restaurants_google_places(
    req: RestaurantSearchRequest,
    api_key: str,
    *,
    timeout: float = 8.0,
) -> tuple[List["RestaurantResult"], str]:
    """Query Google Places Text Search for real restaurants in a destination.

    Returns an empty list on any error (fail-closed). Never returns mock data.
    Sets source="google_places" on every result so cache and frontend guards can
    distinguish real provider results from the rejected "mock" source value.
    """
    if not api_key:
        return [], "config_missing"
    if httpx is None:
        logger.warning("[search_restaurants] httpx not installed; Google Places provider disabled")
        return [], "unavailable"

    location = (req.location or "").strip()
    if req.cuisine:
        query = f"{req.cuisine.strip()} restaurants in {location}"
    else:
        query = f"restaurants in {location}"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": _RESTAURANT_SEARCH_FIELD_MASK,
    }
    body = {"textQuery": query, "maxResultCount": 20}

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(_GOOGLE_PLACES_SEARCH_ENDPOINT, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("[search_restaurants] Google Places request failed: %s", exc)
        return [], "error"

    raw_places = list(data.get("places") or [])
    results: List[RestaurantResult] = []

    for place in raw_places:
        # Only surface open, operational restaurants.
        if place.get("businessStatus") != "OPERATIONAL":
            continue
        place_id = place.get("id")
        if not place_id:
            continue

        display_name = place.get("displayName") or {}
        name = (display_name.get("text") if isinstance(display_name, dict) else str(display_name or "")).strip()
        if not name:
            continue

        formatted_address = (place.get("formattedAddress") or "").strip()
        location_data = place.get("location") or {}
        lat = location_data.get("latitude") if isinstance(location_data, dict) else None
        lng = location_data.get("longitude") if isinstance(location_data, dict) else None

        rating = place.get("rating")
        num_reviews = place.get("userRatingCount")
        google_maps_uri = (place.get("googleMapsUri") or "").strip() or None

        # Price level: New API returns string enum; guard against int from old API.
        price_level_raw = place.get("priceLevel")
        if isinstance(price_level_raw, int):
            price_level = max(0, min(4, price_level_raw))
        elif isinstance(price_level_raw, str):
            price_level = _PRICE_LEVEL_MAP.get(price_level_raw, 2)
        else:
            price_level = 2

        # Cuisine: prefer primaryType, fall through types list.
        primary_type = (place.get("primaryType") or "").strip()
        types = list(place.get("types") or [])
        cuisine = _GOOGLE_TYPE_TO_CUISINE.get(primary_type)
        if not cuisine:
            for t in types:
                cuisine = _GOOGLE_TYPE_TO_CUISINE.get(t)
                if cuisine:
                    break
        cuisine = cuisine or "Restaurant"

        # Opening hours: use first weekday description line.
        hours_data = place.get("regularOpeningHours") or {}
        weekday_desc = hours_data.get("weekdayDescriptions") or []
        opening_hours = weekday_desc[0] if weekday_desc else None

        ai_score = None
        if rating is not None and num_reviews is not None:
            ai_score = _compute_restaurant_ai_score(rating, num_reviews, price_level)
        tags = _compute_restaurant_tags(ai_score or 0.0, rating or 0.0, num_reviews or 0, price_level)

        # Canonical Maps link: prefer googleMapsUri, fallback to place_id URL.
        booking_url = google_maps_uri or f"https://www.google.com/maps/place/?q=place_id:{place_id}"

        results.append(RestaurantResult(
            id=f"gp-{place_id}",
            price=None,
            points_estimate=None,
            rating=rating,
            location=req.location,
            booking_url=booking_url,
            source="google_places",
            booking_options=[],
            name=name,
            cuisine=cuisine,
            address=formatted_address or req.location,
            ai_score=ai_score,
            tags=tags,
            num_reviews=num_reviews,
            opening_hours=opening_hours,
            price_level=price_level,
            sentiment=None,
            provider_place_id=place_id,
            google_maps_uri=google_maps_uri,
            place_id=place_id,
            source_status="ok",
            cache_status="miss",
            verification_status="verified",
            lat=lat,
            lng=lng,
        ))

    # Cuisine filter: apply only when a cuisine was requested AND it doesn't drop all results.
    if req.cuisine and results:
        cuisine_lower = req.cuisine.lower()
        filtered = [r for r in results if r.cuisine and cuisine_lower in r.cuisine.lower()]
        if filtered:
            results = filtered
        # If every result would be filtered out, return all (cuisine label mismatch, not absence).

    results.sort(key=lambda r: r.ai_score or 0.0, reverse=True)
    return results, "ok" if results else "empty"


# ---------------------------------------------------------------------------
# Product Surface Pruning v1A — legacy mock registry
# ---------------------------------------------------------------------------

# Tag the remaining legacy mock generators so the v1A regression suite can
# enumerate the quarantined surface without string-matching identifiers.
# v1D removed ``_mock_attractions``; the final mock-leak closeout removed
# ``_mock_restaurants`` (orphan — ``search_restaurants`` runs canonical
# Google Places fail-closed).  Only flights and hotels remain quarantined,
# preserved for a future provider-backed Flights/Hotels v1.
_mark_legacy_product_mock(_mock_flights)
_mark_legacy_product_mock(_mock_hotels)

# Public, ordered registry of every legacy product-surface mock fixture in
# this module.  ``backend/tests/test_product_surface_pruning_v1a.py`` reads
# from this registry to enforce the quarantine envelope; new mock fixtures
# must either be added here (and explicitly classified in
# ``backend/app/routes/search.py``) or implemented through the canonical
# AI Concierge display contract instead.
LEGACY_PRODUCT_MOCK_FUNCTIONS: tuple = (
    _mock_flights,
    _mock_hotels,
)


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class SearchService:
    def __init__(self, db: Client) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public search methods
    # ------------------------------------------------------------------

    def search_flights(self, req: FlightSearchRequest) -> List[FlightResult]:
        origins = req.all_origins
        destinations = req.all_destinations

        if not origins or not destinations:
            return []

        if len(origins) == 1 and len(destinations) == 1:
            # Fast path: single airport pair with cache
            sub_req = FlightSearchRequest(
                origin=origins[0],
                destination=destinations[0],
                departure_date=req.departure_date,
                return_date=req.return_date,
                passengers=req.passengers,
                cabin_class=req.cabin_class,
            )
            query = sub_req.model_dump(mode="json")
            key = _cache_key("flights", query)
            cached = self._get_cache(key)
            if cached and _suppress_legacy_mock_cache("flights", cached):
                logger.warning(
                    "[legacy_product_mock.cache_blocked] namespace=flights cached_rows=%d — discarding suspect cache",
                    len(cached),
                )
                cached = None
            if cached:
                return [FlightResult(**item) for item in cached]
            results = _mock_flights(sub_req)
            if not _legacy_product_mock_blocked():
                self._set_cache(key, source="mock", query=query, results=[r.model_dump(mode="json") for r in results])
            return results

        # Multi-airport: cartesian product of all origin × destination pairs
        all_results: List[FlightResult] = []
        for origin in origins:
            for destination in destinations:
                sub_req = FlightSearchRequest(
                    origin=origin,
                    destination=destination,
                    departure_date=req.departure_date,
                    return_date=req.return_date,
                    passengers=req.passengers,
                    cabin_class=req.cabin_class,
                )
                query = sub_req.model_dump(mode="json")
                key = _cache_key("flights", query)
                cached = self._get_cache(key)
                if cached and _suppress_legacy_mock_cache("flights", cached):
                    logger.warning(
                        "[legacy_product_mock.cache_blocked] namespace=flights cached_rows=%d — discarding suspect cache",
                        len(cached),
                    )
                    cached = None
                if cached:
                    all_results.extend([FlightResult(**item) for item in cached])
                else:
                    results = _mock_flights(sub_req)
                    if not _legacy_product_mock_blocked():
                        self._set_cache(key, source="mock", query=query, results=[r.model_dump(mode="json") for r in results])
                    all_results.extend(results)

        # Deduplicate by (airline, rounded price, duration)
        seen: set = set()
        deduped: List[FlightResult] = []
        for r in all_results:
            dedup_key = (r.airline, round(r.price or 0, 0), r.duration_minutes, r.origin, r.destination)
            if dedup_key not in seen:
                seen.add(dedup_key)
                deduped.append(r)

        # Sort by price asc, then cpp desc
        deduped.sort(key=lambda r: (r.price or 0, -(r.cpp or 0)))
        return deduped

    def search_round_trip_flights(self, req: FlightSearchRequest) -> List[RoundTripFlightPair]:
        """Fetch outbound + return flights and return ranked pairs.

        Requires ``req.return_date`` to be set. Swaps origin/destination for the
        return leg and uses ``return_date`` as the departure date.
        """
        if not req.return_date:
            return []

        outbound_flights = self.search_flights(req)

        return_req = FlightSearchRequest(
            origin_airports=req.destination_airports,
            origin=req.destination,
            destination_airports=req.origin_airports,
            destination=req.origin,
            departure_date=req.return_date,
            passengers=req.passengers,
            cabin_class=req.cabin_class,
        )
        return_flights = self.search_flights(return_req)

        pairs: List[RoundTripFlightPair] = []
        for outbound in outbound_flights:
            for ret in return_flights:
                total_price = (outbound.price or 0.0) + (ret.price or 0.0)
                total_points = (outbound.points_cost or 0) + (ret.points_cost or 0)
                combined_cpp = round((total_price * 100) / total_points, 2) if total_points > 0 else 0.0
                pairs.append(RoundTripFlightPair(
                    id=f"rt-{outbound.id}-{ret.id}",
                    outbound=outbound,
                    return_flight=ret,
                    total_price=round(total_price, 2),
                    total_points=total_points,
                    combined_cpp=combined_cpp,
                    total_duration_minutes=outbound.duration_minutes + ret.duration_minutes,
                ))

        # Rank: combined CPP desc, total price asc, total duration asc
        pairs.sort(key=lambda p: (-p.combined_cpp, p.total_price, p.total_duration_minutes))
        return pairs

    def search_hotels(self, req: HotelSearchRequest) -> List[HotelResult]:
        query = req.model_dump(mode="json")
        key = _cache_key("hotels", query)
        cached = self._get_cache(key)
        if cached and _suppress_legacy_mock_cache("hotels", cached):
            logger.warning(
                "[legacy_product_mock.cache_blocked] namespace=hotels location=%s cached_rows=%d — discarding suspect cache",
                req.location, len(cached),
            )
            cached = None
        if cached:
            return [HotelResult(**item) for item in cached]

        results = _mock_hotels(req)
        if not _legacy_product_mock_blocked():
            self._set_cache(key, source="mock", query=query, results=[r.model_dump(mode="json") for r in results])
        return results

    def search_restaurants(self, req: RestaurantSearchRequest) -> List[RestaurantResult]:
        query = req.model_dump(mode="json")
        key = _cache_key("restaurants", query)
        cached = self._get_cache(key)

        # Discard stale mock cache entries — mock data must never reach the live API.
        if cached and all(item.get("source") == "mock" for item in cached):
            logger.info(
                "[search_restaurants] location=%s cuisine=%s cache_status=mock_bypass — discarding stale mock cache",
                req.location, req.cuisine,
            )
            cached = None

        if cached:
            raw_count = len(cached)
            results = []
            for item in cached:
                r = RestaurantResult(**item)
                if r.ai_score is None and r.rating is not None and r.num_reviews is not None:
                    price_level = r.price_level if r.price_level is not None else 2
                    r.ai_score = _compute_restaurant_ai_score(r.rating, r.num_reviews, price_level, r.sentiment)
                r.cache_status = "hit"
                r.source_status = r.source_status or "ok"
                r.verification_status = "verified" if (r.google_maps_uri or r.provider_place_id or r.place_id) else "unverified"
                results.append(r)
            verified_count = sum(1 for r in results if r.verification_status == "verified")
            logger.info(
                "[search_restaurants] location=%s cuisine=%s cache_status=hit raw_candidates=%d verified_candidates=%d returned=%d source_status=ok",
                req.location, req.cuisine, raw_count, verified_count, len(results),
            )
            return results

        # Cache miss — call the live Google Places provider when configured.
        api_key = os.getenv("GOOGLE_PLACES_API_KEY", "")
        provider_configured = bool(api_key)
        logger.info(
            "[search_restaurants] location=%s cuisine=%s cache_status=miss provider_configured=%s",
            req.location, req.cuisine, provider_configured,
        )

        if not provider_configured:
            logger.info(
                "[search_restaurants] location=%s cuisine=%s source_status=no_provider raw_candidates=0 verified_candidates=0 returned=0",
                req.location, req.cuisine,
            )
            return []

        results, provider_status = _fetch_restaurants_google_places(req, api_key)
        raw_candidates = len(results)
        verified_candidates = sum(
            1 for r in results if r.provider_place_id or r.google_maps_uri or r.place_id
        )
        source_status = provider_status

        if results:
            self._set_cache(
                key,
                source="google_places",
                query=query,
                results=[r.model_dump(mode="json") for r in results],
            )

        logger.info(
            "[search_restaurants] location=%s cuisine=%s cache_status=miss provider_configured=True raw_candidates=%d verified_candidates=%d returned=%d source_status=%s",
            req.location, req.cuisine, raw_candidates, verified_candidates, len(results), source_status,
        )
        return results

    # ------------------------------------------------------------------
    # search_clusters / get_best_area / _cluster_places / _AREA_NAMES /
    # _walkability_label / _avg_distance_label were deleted in Product
    # Surface Cleanup v1C (deletion variant).  The /search/clusters and
    # /search/best-area routes were orphaned after PR #289 removed the
    # grouped/Areas view and Best Area card; deletion is structural.
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _get_cache(self, key: str) -> Optional[List[Dict[str, Any]]]:
        """Return cached payload if it exists and has not expired."""
        try:
            now = _now_utc().isoformat()
            result = (
                self.db.table(CACHE_TABLE)
                .select("payload, expires_at")
                .eq("cache_key", key)
                .limit(1)
                .execute()
            )
            if not result.data:
                return None
            row = result.data[0]
            expires_at = row.get("expires_at")
            if expires_at and expires_at < now:
                return None
            payload = row["payload"]
            return payload.get("results")
        except Exception:
            # Cache miss on any error — regenerate fresh results
            return None

    def _set_cache(
        self,
        key: str,
        source: str,
        query: Dict[str, Any],
        results: List[Dict[str, Any]],
    ) -> None:
        """Upsert a cache entry; overwrites any existing row with the same key."""
        try:
            expires_at = (_now_utc() + timedelta(hours=CACHE_TTL_HOURS)).isoformat()
            record = {
                "cache_key": key,
                "source": source,
                "query": query,
                "payload": {"results": results},
                "expires_at": expires_at,
            }
            # Upsert: insert or update on conflict of cache_key
            self.db.table(CACHE_TABLE).upsert(record, on_conflict="cache_key").execute()
        except Exception:
            # Cache write failure is non-fatal — results are already returned
            pass
