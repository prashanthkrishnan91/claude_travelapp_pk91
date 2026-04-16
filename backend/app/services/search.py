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
import random
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from supabase import Client

from app.models.search import (
    AttractionResult,
    AttractionSearchRequest,
    BookingOption,
    FlightResult,
    FlightSearchRequest,
    HotelResult,
    HotelSearchRequest,
)

CACHE_TABLE = "research_cache"
CACHE_TTL_HOURS = 1


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
    for i, (code, name) in enumerate(random.sample(airlines, k=min(4, len(airlines)))):
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

    results: List[HotelResult] = []
    for tpl_name, stars, amenities in random.sample(hotel_templates, k=min(5, len(hotel_templates))):
        name = tpl_name.format(loc=city)
        nightly = round(random.uniform(80, 550), 2)
        if req.max_price:
            nightly = min(nightly, req.max_price)
        total = round(nightly * nights, 2)
        points = int(total * random.uniform(80, 120))

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
            )
        )

    results.sort(key=lambda r: r.price or 0)
    return results


def _mock_attractions(req: AttractionSearchRequest) -> List[AttractionResult]:
    """Generate attraction options for the requested location."""
    category_pool = {
        "museums": [
            ("National Museum of Art", "Explore world-class permanent and rotating collections.", 120),
            ("History & Culture Center", "Immersive exhibits on local heritage and traditions.", 90),
            ("Science & Tech Museum", "Interactive science exhibits for all ages.", 150),
        ],
        "outdoor": [
            ("City Botanical Gardens", "Wander through 50+ acres of curated gardens.", 90),
            ("Waterfront Trail", "Scenic 5 km walking and cycling path along the bay.", 60),
            ("Summit Viewpoint Hike", "Moderate 3-hour hike with panoramic city views.", 180),
        ],
        "food": [
            ("Local Food Market Tour", "Guided 2-hour tour of the city's best street food stalls.", 120),
            ("Farm-to-Table Cooking Class", "Learn regional recipes with a professional chef.", 180),
            ("Wine & Tapas Evening", "Curated tasting of local wines paired with small plates.", 150),
        ],
        "tours": [
            ("Historic Walking Tour", "2-hour guided walk through the old town district.", 120),
            ("Hop-On Hop-Off Bus", "Full-day pass covering 20+ top attractions.", 480),
            ("Sunset Boat Cruise", "90-minute evening cruise with drinks included.", 90),
        ],
        "nightlife": [
            ("Jazz & Cocktail Bar", "Live jazz nightly from 9 PM with craft cocktails.", None),
            ("Rooftop Lounge", "City views and DJ sets at one of the top rooftop bars.", None),
        ],
        "shopping": [
            ("Old Town Market", "Open-air market with local crafts and souvenirs.", 60),
            ("Designer District Walk", "Self-guided tour of boutique and high-end shops.", 90),
        ],
    }

    chosen_categories = (
        [req.category] if req.category and req.category in category_pool
        else list(category_pool.keys())
    )

    pool: List[tuple] = []
    for cat in chosen_categories:
        for name, desc, dur in category_pool[cat]:
            pool.append((cat, name, desc, dur))

    sample = random.sample(pool, k=min(6, len(pool)))
    city = req.location.split(",")[0].strip().title()
    results: List[AttractionResult] = []

    for cat, name, desc, dur in sample:
        price = round(random.uniform(0, 120), 2)
        points = int(price * random.uniform(80, 130)) if price > 0 else 0

        name_slug = name.lower().replace(" ", "-").replace("&", "and")
        loc_slug = req.location.lower().replace(" ", "-").replace(",", "")
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
                rating=round(random.uniform(3.5, 5.0), 1),
                location=req.location,
                booking_url=direct_url,
                source="mock",
                booking_options=attraction_options,
                name=f"{name} — {city}",
                category=cat,
                description=desc,
                duration_minutes=dur,
                address=f"{random.randint(1, 999)} {random.choice(['Main St', 'Market Ave', 'Park Blvd', 'Harbor Dr'])}, {city}",
            )
        )

    results.sort(key=lambda r: r.rating or 0, reverse=True)
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
