"""SearchService — fetch (or generate mock) results and cache them in Supabase.

Architecture
------------
1. Build a deterministic cache_key from the serialised query.
2. Check research_cache for a live hit (not expired).
3. On miss: call the appropriate _fetch_* method (currently returns realistic
   mock data; swap in real provider clients when API keys are available).
4. Persist the result set to research_cache with a configurable TTL.
5. Return the normalised result list to the route handler.
"""

import hashlib
import json
import math
import random
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from supabase import Client

from app.models.search import (
    AttractionResult,
    AttractionSearchRequest,
    BestAreaRecommendation,
    BestAreaRequest,
    BookingOption,
    ClusterCounts,
    ClusterSearchRequest,
    FlightResult,
    FlightSearchRequest,
    HotelResult,
    HotelSearchRequest,
    LocationCluster,
    PlaceInCluster,
    RestaurantResult,
    RestaurantSearchRequest,
    RoundTripFlightPair,
)

CACHE_TABLE = "research_cache"
CACHE_TTL_HOURS = 1

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

_AREA_NAMES = [
    "Central District", "Waterfront Area", "Old Town Quarter",
    "Market District", "Harbour Side", "Heritage Zone",
    "Arts Quarter", "Garden District", "Royal Mile Area",
    "Bay Area", "Cultural Zone", "Riverside Quarter",
    "Hilltop Area", "Beachfront Strip", "Historic Core",
]


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


def _cluster_places(places: List[Dict[str, Any]], radius_km: float) -> List[List[Dict[str, Any]]]:
    """Greedy radius-based clustering: seed on first unassigned, pull in neighbours within radius."""
    unassigned = list(range(len(places)))
    clusters: List[List[int]] = []
    while unassigned:
        seed_idx = unassigned[0]
        seed = places[seed_idx]
        cluster_indices = [seed_idx]
        remaining: List[int] = []
        for i in unassigned[1:]:
            p = places[i]
            if _haversine_km(seed["lat"], seed["lng"], p["lat"], p["lng"]) <= radius_km:
                cluster_indices.append(i)
            else:
                remaining.append(i)
        clusters.append(cluster_indices)
        unassigned = remaining
    return [[places[i] for i in cluster] for cluster in clusters]


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


def _avg_distance_label(cluster: List[Dict[str, Any]]) -> str:
    """Return average pairwise walking-time label for a cluster."""
    if len(cluster) < 2:
        return "Solo stop"
    total_dist = 0.0
    pairs = 0
    for i in range(len(cluster)):
        for j in range(i + 1, len(cluster)):
            total_dist += _haversine_km(cluster[i]["lat"], cluster[i]["lng"], cluster[j]["lat"], cluster[j]["lng"])
            pairs += 1
    avg_km = total_dist / pairs
    avg_min = round(avg_km * 15.0)  # walking ~4 km/h
    if avg_min <= 5:
        return "5 min apart"
    if avg_min <= 10:
        return "10 min apart"
    return f"{avg_min} min apart"


def _walkability_label(cluster: List[Dict[str, Any]]) -> str:
    if len(cluster) < 2:
        return "Solo stop"
    max_dist = 0.0
    for i in range(len(cluster)):
        for j in range(i + 1, len(cluster)):
            d = _haversine_km(cluster[i]["lat"], cluster[i]["lng"], cluster[j]["lat"], cluster[j]["lng"])
            if d > max_dist:
                max_dist = d
    if max_dist <= 0.5:
        return "Walkable cluster"
    if max_dist <= 1.0:
        return "5 min apart"
    return "10 min apart"


# ---------------------------------------------------------------------------
# Mock data generators
# ---------------------------------------------------------------------------

def _mock_flights(req: FlightSearchRequest) -> List[FlightResult]:
    """Generate realistic-looking flight options for the requested route."""
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
    return results


def _mock_hotels(req: HotelSearchRequest) -> List[HotelResult]:
    """Generate realistic hotel options for the requested location and dates."""
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
    return results


def _compute_attraction_ai_score(rating: float, num_reviews: int, category: str) -> float:
    """Compute AI relevance score 0–100 based on rating, review volume, and category."""
    rating_score = (rating / 5.0) * 100
    review_score = min(100.0, (math.log1p(num_reviews) / math.log1p(500_000)) * 100)
    popularity = rating_score * 0.6 + review_score * 0.4
    uniqueness_bonus = 8.0 if category in ("hidden_gems", "local_favorites") else 0.0
    raw = popularity * 0.9 + uniqueness_bonus * 0.1
    return round(min(100.0, max(0.0, raw)), 1)


def _compute_attraction_tags(ai_score: float, rating: float, num_reviews: int) -> List[str]:
    """Assign human-readable tags based on score, rating, and popularity."""
    tags: List[str] = []
    if ai_score >= 80:
        tags.append("Must Visit")
    if rating >= 4.7:
        tags.append("Highly Rated")
    elif rating >= 4.5 and "Must Visit" not in tags:
        tags.append("Top Rated")
    if num_reviews >= 50_000:
        tags.append("Tourist Favorite")
    elif num_reviews < 5_000 and ai_score >= 55:
        tags.append("Hidden Gem")
    return tags


def _mock_attractions(req: AttractionSearchRequest) -> List[AttractionResult]:
    """Generate realistic attraction options simulating Google Places data."""
    # (category, name_template, description, duration_min, base_reviews_range, price_level)
    ATTRACTION_POOL: List[tuple] = [
        # Top attractions / landmarks
        ("landmarks", "City Heritage Museum", "Discover the rich history and culture of the city through immersive exhibits and rare artefacts.", 120, (80_000, 400_000), 1),
        ("landmarks", "Grand Central Viewpoint", "Panoramic observation deck offering stunning 360° views of the skyline and harbour.", 60, (120_000, 500_000), 2),
        ("landmarks", "Historic Old Town District", "Stroll through cobblestone streets lined with centuries-old architecture and artisan shops.", 180, (200_000, 480_000), 0),
        ("landmarks", "National Cathedral", "Magnificent Gothic cathedral with intricate stained glass windows and guided tower climbs.", 90, (150_000, 400_000), 0),
        ("landmarks", "Royal Palace Gardens", "Sprawling royal gardens open to the public, featuring seasonal floral displays.", 120, (100_000, 350_000), 1),
        # Top attractions
        ("top_attractions", "Sunset Harbour Cruise", "90-minute evening boat cruise with panoramic views and complimentary drinks.", 90, (30_000, 150_000), 2),
        ("top_attractions", "Hop-On Hop-Off City Bus Tour", "Full-day pass covering 25+ must-see sites with live commentary in 10 languages.", 480, (60_000, 300_000), 2),
        ("top_attractions", "Underground City Caves Tour", "Expert-guided descent into ancient limestone caves with dramatic light shows.", 120, (20_000, 100_000), 2),
        ("top_attractions", "Street Food Night Market", "Authentic local street food stalls serving regional specialties from dusk till midnight.", 120, (40_000, 200_000), 1),
        ("top_attractions", "Sky Bridge Walk", "Walk across a glass-floored sky bridge suspended 200 m above the city centre.", 45, (50_000, 250_000), 3),
        # Nature / outdoor
        ("outdoor", "City Botanical Gardens", "Wander through 80 acres of curated gardens showcasing 5,000+ plant species.", 90, (70_000, 280_000), 1),
        ("outdoor", "Coastal Cliffs Hike", "Moderate 4-hour hike along dramatic sea cliffs with spectacular ocean vistas.", 240, (15_000, 80_000), 0),
        ("outdoor", "Sunrise Mountain Trek", "Early-morning guided trek rewarded with an unforgettable sunrise over the valley.", 300, (10_000, 60_000), 0),
        ("outdoor", "Waterfront Cycling Trail", "Scenic 10 km cycling path along the bay, bike rentals available at the trailhead.", 120, (25_000, 120_000), 1),
        # Museums
        ("museums", "Contemporary Art Gallery", "Award-winning gallery housing rotating exhibitions from world-renowned artists.", 120, (40_000, 200_000), 1),
        ("museums", "Science & Discovery Museum", "Interactive exhibits on space, technology, and the natural world — great for all ages.", 150, (55_000, 220_000), 2),
        ("museums", "Maritime Heritage Museum", "Explore centuries of seafaring history with restored ships and immersive dioramas.", 90, (20_000, 90_000), 1),
        # Food & culture
        ("food", "Culinary Walking Food Tour", "Expert-led 3-hour food tour sampling 10+ local dishes across vibrant neighbourhoods.", 180, (18_000, 85_000), 2),
        ("food", "Farm-to-Table Cooking Class", "Learn regional recipes hands-on with a professional chef using market-fresh ingredients.", 180, (8_000, 40_000), 3),
        ("food", "Rooftop Wine & Tapas Evening", "Curated sunset tasting of local wines paired with artisan small plates, city views included.", 150, (12_000, 60_000), 3),
        # Hidden gems / local favourites
        ("hidden_gems", "Secret Courtyard Art Walk", "Self-guided tour through hidden courtyards adorned with murals by local street artists.", 90, (2_000, 9_000), 0),
        ("hidden_gems", "Underground Jazz Speakeasy", "Intimate live jazz sessions in a vintage underground bar — reservation required.", 120, (3_000, 12_000), 2),
        ("local_favorites", "Morning Fishermen's Market", "Join locals at dawn for the freshest catch, prepared on-site by harbour-side vendors.", 60, (4_000, 18_000), 1),
        ("local_favorites", "Neighbourhood Artisan Fair", "Weekly craft market where local makers sell pottery, textiles, and handmade jewellery.", 90, (5_000, 20_000), 0),
    ]

    OPENING_HOURS = [
        "Daily 9:00 AM – 6:00 PM",
        "Mon–Sat 8:00 AM – 8:00 PM",
        "Daily 10:00 AM – 10:00 PM",
        "Tue–Sun 9:00 AM – 5:00 PM",
        "Daily 7:00 AM – 11:00 PM",
        "Wed–Mon 10:00 AM – 6:00 PM",
        "Daily (24 hours)",
        "Fri–Sun 6:00 PM – 2:00 AM",
    ]

    STREET_NAMES = ["Main St", "Market Ave", "Park Blvd", "Harbour Dr", "Cathedral Sq", "Heritage Lane", "Royal Walk", "Old Town Rd"]

    city = req.location.split(",")[0].strip().title()

    # Filter by category if provided
    valid_cats = {t[0] for t in ATTRACTION_POOL}
    if req.category and req.category in valid_cats:
        pool = [t for t in ATTRACTION_POOL if t[0] == req.category]
    else:
        pool = list(ATTRACTION_POOL)

    loc_slug = req.location.lower().replace(" ", "-").replace(",", "")
    results: List[AttractionResult] = []

    for cat, name_tpl, desc, dur, reviews_range, price_level in pool:
        name = f"{name_tpl} — {city}"
        rating = round(random.uniform(3.8, 4.95), 1)
        num_reviews = random.randint(*reviews_range)
        price = round(random.uniform(0, 80), 2) if price_level > 0 else 0.0
        points = int(price * random.uniform(80, 130)) if price > 0 else 0

        ai_score = _compute_attraction_ai_score(rating, num_reviews, cat)
        tags = _compute_attraction_tags(ai_score, rating, num_reviews)
        opening_hours = random.choice(OPENING_HOURS)
        address = f"{random.randint(1, 999)} {random.choice(STREET_NAMES)}, {city}"

        name_slug = name_tpl.lower().replace(" ", "-").replace("'", "").replace("&", "and")
        direct_url = f"https://book.example.com/attractions/{name_slug}"
        attraction_options = [
            BookingOption(provider="viator", url=f"https://book.example.com/attractions/viator/{name_slug}"),
            BookingOption(provider="getyourguide", url=f"https://book.example.com/attractions/gyg/{name_slug}"),
            BookingOption(provider="klook", url=f"https://book.example.com/attractions/klook/{loc_slug}"),
        ]
        results.append(
            AttractionResult(
                id=f"att-{uuid4().hex[:10]}",
                price=price if price > 0 else None,
                points_estimate=points if points > 0 else None,
                rating=rating,
                location=req.location,
                booking_url=direct_url,
                source="mock",
                booking_options=attraction_options,
                name=name,
                category=cat,
                description=desc,
                duration_minutes=dur,
                address=address,
                ai_score=ai_score,
                tags=tags,
                num_reviews=num_reviews,
                opening_hours=opening_hours,
                price_level=price_level,
            )
        )

    results.sort(key=lambda r: r.ai_score or 0, reverse=True)
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


def _mock_restaurants(req: RestaurantSearchRequest) -> List[RestaurantResult]:
    """Generate realistic restaurant options simulating Google Places data."""
    # (cuisine, name_template, description, price_level, reviews_range)
    RESTAURANT_POOL: List[tuple] = [
        ("Italian", "La Trattoria", "Authentic Neapolitan pizza and housemade pastas in a warm, family-run setting.", 2, (8_000, 60_000)),
        ("Japanese", "Sakura Sushi", "Omakase and à la carte sushi crafted with daily-sourced fish and aged rice.", 3, (12_000, 80_000)),
        ("Mexican", "El Mercado", "Vibrant cantina serving street-style tacos, mezcal cocktails, and mole negro.", 1, (15_000, 90_000)),
        ("French", "Bistro Le Marais", "Classic Parisian bistro with steak-frites, onion soup, and a curated wine list.", 3, (6_000, 40_000)),
        ("Indian", "Spice Route", "Regional Indian curries, tandoor grills, and house-made paneer from a family kitchen.", 1, (10_000, 55_000)),
        ("Mediterranean", "Olive & Sea", "Sun-drenched terrace dining with mezze platters, fresh seafood, and citrus desserts.", 2, (9_000, 50_000)),
        ("American", "The Smokehouse", "Slow-smoked BBQ ribs, pulled pork sandwiches, and craft beer on tap.", 1, (20_000, 120_000)),
        ("Thai", "Bangkok Garden", "Fragrant Thai curries, pad see ew, and refreshing mango sticky rice.", 1, (14_000, 75_000)),
        ("Steakhouse", "Prime Cut", "USDA Prime dry-aged steaks, lobster bisque, and classic sides in an upscale setting.", 4, (5_000, 35_000)),
        ("Seafood", "The Pier Kitchen", "Waterfront restaurant serving the morning's catch grilled simply with local produce.", 3, (7_000, 45_000)),
        ("Café", "Corner Brew Café", "Specialty single-origin coffee, avocado toasts, and freshly baked sourdough.", 1, (18_000, 100_000)),
        ("Vegetarian", "Garden Table", "Inventive plant-based dishes celebrating seasonal vegetables and global spices.", 2, (8_000, 45_000)),
    ]

    OPENING_HOURS = [
        "Daily 11:00 AM – 10:00 PM",
        "Mon–Sat 12:00 PM – 11:00 PM",
        "Daily 7:00 AM – 3:00 PM",
        "Tue–Sun 5:00 PM – 11:00 PM",
        "Daily 8:00 AM – 9:00 PM",
        "Wed–Mon 11:30 AM – 10:30 PM",
        "Daily 6:00 PM – 12:00 AM",
        "Mon–Fri 11:00 AM – 2:30 PM, 5:00 PM – 10:00 PM",
    ]

    STREET_NAMES = ["Main St", "Market Ave", "Harbour Dr", "Old Town Sq", "Vine St", "Bay Blvd", "Canal Walk", "High St"]

    city = req.location.split(",")[0].strip().title()
    loc_slug = req.location.lower().replace(" ", "-").replace(",", "")

    # Filter by cuisine if provided
    if req.cuisine:
        pool = [t for t in RESTAURANT_POOL if t[0].lower() == req.cuisine.lower()]
        if not pool:
            pool = list(RESTAURANT_POOL)
    else:
        pool = list(RESTAURANT_POOL)

    results: List[RestaurantResult] = []
    for cuisine, name_tpl, desc, price_level, reviews_range in pool:
        name = f"{name_tpl} {city}"
        rating = round(random.uniform(3.8, 4.95), 1)
        num_reviews = random.randint(*reviews_range)
        sentiment = round(random.uniform(0.70, 0.98), 2)
        price = round(random.uniform(10, 120), 2) if price_level > 0 else 0.0

        ai_score = _compute_restaurant_ai_score(rating, num_reviews, price_level, sentiment)
        tags = _compute_restaurant_tags(ai_score, rating, num_reviews, price_level)
        opening_hours = random.choice(OPENING_HOURS)
        address = f"{random.randint(1, 999)} {random.choice(STREET_NAMES)}, {city}"

        name_slug = name_tpl.lower().replace(" ", "-").replace("'", "").replace("&", "and")
        direct_url = f"https://maps.example.com/restaurants/{name_slug}-{loc_slug}"
        restaurant_options = [
            BookingOption(provider="google_maps", url=f"https://maps.example.com/restaurants/{name_slug}"),
            BookingOption(provider="opentable", url=f"https://book.example.com/restaurants/opentable/{name_slug}"),
            BookingOption(provider="yelp", url=f"https://book.example.com/restaurants/yelp/{name_slug}"),
        ]
        results.append(
            RestaurantResult(
                id=f"rst-{uuid4().hex[:10]}",
                price=price if price > 0 else None,
                points_estimate=None,
                rating=rating,
                location=req.location,
                booking_url=direct_url,
                source="mock",
                booking_options=restaurant_options,
                name=name,
                cuisine=cuisine,
                address=address,
                ai_score=ai_score,
                tags=tags,
                num_reviews=num_reviews,
                opening_hours=opening_hours,
                price_level=price_level,
                sentiment=sentiment,
            )
        )

    results.sort(key=lambda r: r.ai_score or 0, reverse=True)
    return results


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
            if cached:
                return [FlightResult(**item) for item in cached]
            results = _mock_flights(sub_req)
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
                if cached:
                    all_results.extend([FlightResult(**item) for item in cached])
                else:
                    results = _mock_flights(sub_req)
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
        if cached:
            return [HotelResult(**item) for item in cached]

        results = _mock_hotels(req)
        self._set_cache(key, source="mock", query=query, results=[r.model_dump(mode="json") for r in results])
        return results

    def search_attractions(self, req: AttractionSearchRequest) -> List[AttractionResult]:
        query = req.model_dump(mode="json")
        key = _cache_key("attractions", query)
        cached = self._get_cache(key)
        if cached:
            return [AttractionResult(**item) for item in cached]

        results = _mock_attractions(req)
        self._set_cache(key, source="mock", query=query, results=[r.model_dump(mode="json") for r in results])
        return results

    def search_restaurants(self, req: RestaurantSearchRequest) -> List[RestaurantResult]:
        query = req.model_dump(mode="json")
        key = _cache_key("restaurants", query)
        cached = self._get_cache(key)
        if cached:
            return [RestaurantResult(**item) for item in cached]

        results = _mock_restaurants(req)
        self._set_cache(key, source="mock", query=query, results=[r.model_dump(mode="json") for r in results])
        return results

    def search_clusters(self, req: ClusterSearchRequest) -> List[LocationCluster]:
        """Fetch all attractions + restaurants for a location and group them by proximity."""
        center_lat, center_lng = _get_city_center(req.location)

        attractions = self.search_attractions(AttractionSearchRequest(location=req.location))
        restaurants = self.search_restaurants(RestaurantSearchRequest(location=req.location))

        total = len(attractions) + len(restaurants)
        all_places: List[Dict[str, Any]] = []

        for i, a in enumerate(attractions):
            lat, lng = _spread_coordinates(center_lat, center_lng, i, total)
            all_places.append({
                "id": a.id,
                "name": a.name,
                "place_type": "attraction",
                "category": a.category,
                "address": a.address,
                "rating": a.rating,
                "ai_score": a.ai_score,
                "tags": a.tags,
                "lat": lat,
                "lng": lng,
                "booking_url": a.booking_url,
                "booking_options": [o.model_dump() for o in a.booking_options],
            })

        for i, r in enumerate(restaurants):
            lat, lng = _spread_coordinates(center_lat, center_lng, len(attractions) + i, total)
            all_places.append({
                "id": r.id,
                "name": r.name,
                "place_type": "restaurant",
                "category": r.cuisine,
                "address": r.address,
                "rating": r.rating,
                "ai_score": r.ai_score,
                "tags": r.tags,
                "lat": lat,
                "lng": lng,
                "booking_url": r.booking_url,
                "booking_options": [o.model_dump() for o in r.booking_options],
            })

        raw_clusters = _cluster_places(all_places, req.radius_km)

        result: List[LocationCluster] = []
        for idx, cluster in enumerate(raw_clusters):
            c_lat = sum(p["lat"] for p in cluster) / len(cluster)
            c_lng = sum(p["lng"] for p in cluster) / len(cluster)
            area_name = _AREA_NAMES[idx % len(_AREA_NAMES)]
            label = _walkability_label(cluster)
            avg_distance = _avg_distance_label(cluster)
            attraction_count = sum(1 for p in cluster if p["place_type"] == "attraction")
            restaurant_count = sum(1 for p in cluster if p["place_type"] == "restaurant")
            places = [PlaceInCluster(**p) for p in cluster]
            result.append(LocationCluster(
                cluster_id=f"cluster-{idx}",
                area_name=area_name,
                label=label,
                center_lat=round(c_lat, 6),
                center_lng=round(c_lng, 6),
                places=places,
                counts=ClusterCounts(attractions=attraction_count, restaurants=restaurant_count),
                avg_distance=avg_distance,
            ))

        return result

    def get_best_area(self, req: BestAreaRequest) -> Optional[BestAreaRecommendation]:
        """Score clusters by density, avg rating, walkability, and variety to find the best area."""
        clusters = self.search_clusters(ClusterSearchRequest(location=req.location, radius_km=req.radius_km))
        if not clusters:
            return None

        max_places = max(len(c.places) for c in clusters)

        # Pre-compute avg pairwise distances for walkability normalisation
        def _avg_pairwise_km(places: list) -> float:
            if len(places) < 2:
                return 0.0
            total, pairs = 0.0, 0
            for i in range(len(places)):
                for j in range(i + 1, len(places)):
                    total += _haversine_km(places[i].lat, places[i].lng, places[j].lat, places[j].lng)
                    pairs += 1
            return total / pairs

        avg_distances = [_avg_pairwise_km(c.places) for c in clusters]
        max_avg_dist = max(avg_distances) if avg_distances else 1.0

        scored = []
        for cluster, avg_dist_km in zip(clusters, avg_distances):
            # 35%: how many places relative to densest cluster
            density = len(cluster.places) / max(max_places, 1)

            # 30%: average rating normalised to 0-1
            ratings = [p.rating for p in cluster.places if p.rating is not None]
            avg_rating = (sum(ratings) / len(ratings) / 5.0) if ratings else 0.5

            # 20%: walkability — lower avg distance = more walkable
            walkability = 1.0 - (avg_dist_km / max(max_avg_dist, 0.001))

            # 15%: variety — balanced mix of attractions and restaurants
            att = sum(1 for p in cluster.places if p.place_type == "attraction")
            rest = sum(1 for p in cluster.places if p.place_type == "restaurant")
            total = att + rest
            variety = (2 * min(att, rest) / total) if total > 0 else 0.0

            score = density * 0.35 + avg_rating * 0.30 + walkability * 0.20 + variety * 0.15
            scored.append((score, cluster, avg_dist_km))

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best, best_avg_dist = scored[0]

        ratings = [p.rating for p in best.places if p.rating is not None]
        avg_r = sum(ratings) / len(ratings) if ratings else None
        att_count = sum(1 for p in best.places if p.place_type == "attraction")
        rest_count = sum(1 for p in best.places if p.place_type == "restaurant")

        parts = []
        if best.label == "Walkable cluster":
            parts.append("Most attractions within walking distance")
        elif best.label == "5 min apart":
            parts.append("Compact area, 5 min between spots")
        else:
            avg_walk_min = round(best_avg_dist * 15.0)
            parts.append(f"Places ~{avg_walk_min} min apart")
        if avg_r is not None and avg_r >= 4.0:
            parts.append(f"top-rated ({avg_r:.1f}★)")
        elif avg_r is not None:
            parts.append(f"avg rating {avg_r:.1f}★")
        if att_count > 0 and rest_count > 0:
            parts.append("best mix of sightseeing and dining")
        elif rest_count > 0:
            parts.append("top-rated dining")

        return BestAreaRecommendation(
            area_name=best.area_name,
            reason=" · ".join(parts),
            score=round(best_score * 100, 1),
            center_lat=best.center_lat,
            center_lng=best.center_lng,
            radius_km=req.radius_km,
            cluster_id=best.cluster_id,
        )

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
