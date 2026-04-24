import re
import unicodedata
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.deps import DB, CurrentUserID
from app.models import Trip, TripCreate, TripUpdate, ItineraryItem
from app.models.itinerary import ItineraryItemDirectCreate
from app.models.search import FlightResult, FlightSearchRequest, HotelResult, HotelSearchRequest, RoundTripFlightPair
from app.services import TripsService
from app.services.itinerary import ItineraryService
from app.services.search import SearchService

router = APIRouter(prefix="/trips", tags=["trips"])

# ---------------------------------------------------------------------------
# City → airport resolution (inline copy from resolve route)
# ---------------------------------------------------------------------------

_CITY_AIRPORT_MAP = [
    {"city": "New York", "country": "US", "airports": ["JFK", "LGA", "EWR"]},
    {"city": "Los Angeles", "country": "US", "airports": ["LAX", "BUR", "LGB", "ONT", "SNA"]},
    {"city": "Chicago", "country": "US", "airports": ["ORD", "MDW"]},
    {"city": "San Francisco", "country": "US", "airports": ["SFO", "OAK", "SJC"]},
    {"city": "Seattle", "country": "US", "airports": ["SEA", "PAE"]},
    {"city": "Miami", "country": "US", "airports": ["MIA", "FLL", "PBI"]},
    {"city": "Boston", "country": "US", "airports": ["BOS"]},
    {"city": "Washington DC", "country": "US", "airports": ["DCA", "IAD", "BWI"]},
    {"city": "Dallas", "country": "US", "airports": ["DFW", "DAL"]},
    {"city": "Atlanta", "country": "US", "airports": ["ATL"]},
    {"city": "Denver", "country": "US", "airports": ["DEN"]},
    {"city": "Las Vegas", "country": "US", "airports": ["LAS"]},
    {"city": "Phoenix", "country": "US", "airports": ["PHX", "AZA"]},
    {"city": "Houston", "country": "US", "airports": ["IAH", "HOU"]},
    {"city": "Orlando", "country": "US", "airports": ["MCO", "SFB"]},
    {"city": "Minneapolis", "country": "US", "airports": ["MSP"]},
    {"city": "Detroit", "country": "US", "airports": ["DTW"]},
    {"city": "Portland", "country": "US", "airports": ["PDX"]},
    {"city": "San Diego", "country": "US", "airports": ["SAN"]},
    {"city": "Nashville", "country": "US", "airports": ["BNA"]},
    {"city": "Austin", "country": "US", "airports": ["AUS"]},
    {"city": "Charlotte", "country": "US", "airports": ["CLT"]},
    {"city": "New Orleans", "country": "US", "airports": ["MSY"]},
    {"city": "Salt Lake City", "country": "US", "airports": ["SLC"]},
    {"city": "Tampa", "country": "US", "airports": ["TPA"]},
    {"city": "Kansas City", "country": "US", "airports": ["MCI"]},
    {"city": "Philadelphia", "country": "US", "airports": ["PHL"]},
    {"city": "Pittsburgh", "country": "US", "airports": ["PIT"]},
    {"city": "Raleigh", "country": "US", "airports": ["RDU"]},
    {"city": "Indianapolis", "country": "US", "airports": ["IND"]},
    {"city": "Columbus", "country": "US", "airports": ["CMH"]},
    {"city": "Cleveland", "country": "US", "airports": ["CLE"]},
    {"city": "Honolulu", "country": "US", "airports": ["HNL"]},
    {"city": "Anchorage", "country": "US", "airports": ["ANC"]},
    {"city": "Toronto", "country": "CA", "airports": ["YYZ", "YTZ"]},
    {"city": "Vancouver", "country": "CA", "airports": ["YVR"]},
    {"city": "Montreal", "country": "CA", "airports": ["YUL"]},
    {"city": "Calgary", "country": "CA", "airports": ["YYC"]},
    {"city": "London", "country": "GB", "airports": ["LHR", "LGW", "LCY", "STN", "LTN"]},
    {"city": "Manchester", "country": "GB", "airports": ["MAN"]},
    {"city": "Edinburgh", "country": "GB", "airports": ["EDI"]},
    {"city": "Dublin", "country": "IE", "airports": ["DUB"]},
    {"city": "Paris", "country": "FR", "airports": ["CDG", "ORY"]},
    {"city": "Nice", "country": "FR", "airports": ["NCE"]},
    {"city": "Frankfurt", "country": "DE", "airports": ["FRA"]},
    {"city": "Munich", "country": "DE", "airports": ["MUC"]},
    {"city": "Berlin", "country": "DE", "airports": ["BER"]},
    {"city": "Amsterdam", "country": "NL", "airports": ["AMS"]},
    {"city": "Zurich", "country": "CH", "airports": ["ZRH"]},
    {"city": "Geneva", "country": "CH", "airports": ["GVA"]},
    {"city": "Barcelona", "country": "ES", "airports": ["BCN"]},
    {"city": "Madrid", "country": "ES", "airports": ["MAD"]},
    {"city": "Rome", "country": "IT", "airports": ["FCO", "CIA"]},
    {"city": "Milan", "country": "IT", "airports": ["MXP", "LIN", "BGY"]},
    {"city": "Venice", "country": "IT", "airports": ["VCE"]},
    {"city": "Lisbon", "country": "PT", "airports": ["LIS"]},
    {"city": "Stockholm", "country": "SE", "airports": ["ARN", "BMA"]},
    {"city": "Copenhagen", "country": "DK", "airports": ["CPH"]},
    {"city": "Oslo", "country": "NO", "airports": ["OSL"]},
    {"city": "Helsinki", "country": "FI", "airports": ["HEL"]},
    {"city": "Istanbul", "country": "TR", "airports": ["IST", "SAW"]},
    {"city": "Athens", "country": "GR", "airports": ["ATH"]},
    {"city": "Vienna", "country": "AT", "airports": ["VIE"]},
    {"city": "Prague", "country": "CZ", "airports": ["PRG"]},
    {"city": "Budapest", "country": "HU", "airports": ["BUD"]},
    {"city": "Dubai", "country": "AE", "airports": ["DXB", "DWC"]},
    {"city": "Abu Dhabi", "country": "AE", "airports": ["AUH"]},
    {"city": "Doha", "country": "QA", "airports": ["DOH"]},
    {"city": "Tel Aviv", "country": "IL", "airports": ["TLV"]},
    {"city": "Tokyo", "country": "JP", "airports": ["NRT", "HND"]},
    {"city": "Osaka", "country": "JP", "airports": ["KIX", "ITM"]},
    {"city": "Seoul", "country": "KR", "airports": ["ICN", "GMP"]},
    {"city": "Beijing", "country": "CN", "airports": ["PEK", "PKX"]},
    {"city": "Shanghai", "country": "CN", "airports": ["PVG", "SHA"]},
    {"city": "Hong Kong", "country": "HK", "airports": ["HKG"]},
    {"city": "Taipei", "country": "TW", "airports": ["TPE", "TSA"]},
    {"city": "Singapore", "country": "SG", "airports": ["SIN"]},
    {"city": "Bangkok", "country": "TH", "airports": ["BKK", "DMK"]},
    {"city": "Kuala Lumpur", "country": "MY", "airports": ["KUL"]},
    {"city": "Jakarta", "country": "ID", "airports": ["CGK"]},
    {"city": "Manila", "country": "PH", "airports": ["MNL"]},
    {"city": "Bali", "country": "ID", "airports": ["DPS"]},
    {"city": "Hanoi", "country": "VN", "airports": ["HAN"]},
    {"city": "Ho Chi Minh City", "country": "VN", "airports": ["SGN"]},
    {"city": "Phuket", "country": "TH", "airports": ["HKT"]},
    {"city": "Mumbai", "country": "IN", "airports": ["BOM"]},
    {"city": "Delhi", "country": "IN", "airports": ["DEL"]},
    {"city": "Bengaluru", "country": "IN", "airports": ["BLR"]},
    {"city": "Sydney", "country": "AU", "airports": ["SYD"]},
    {"city": "Melbourne", "country": "AU", "airports": ["MEL"]},
    {"city": "Brisbane", "country": "AU", "airports": ["BNE"]},
    {"city": "Perth", "country": "AU", "airports": ["PER"]},
    {"city": "Auckland", "country": "NZ", "airports": ["AKL"]},
    {"city": "Mexico City", "country": "MX", "airports": ["MEX"]},
    {"city": "Cancun", "country": "MX", "airports": ["CUN"]},
    {"city": "Buenos Aires", "country": "AR", "airports": ["EZE", "AEP"]},
    {"city": "Sao Paulo", "country": "BR", "airports": ["GRU", "CGH"]},
    {"city": "Rio de Janeiro", "country": "BR", "airports": ["GIG", "SDU"]},
    {"city": "Santiago", "country": "CL", "airports": ["SCL"]},
    {"city": "Lima", "country": "PE", "airports": ["LIM"]},
    {"city": "Bogota", "country": "CO", "airports": ["BOG"]},
    {"city": "Cairo", "country": "EG", "airports": ["CAI"]},
    {"city": "Cape Town", "country": "ZA", "airports": ["CPT"]},
    {"city": "Johannesburg", "country": "ZA", "airports": ["JNB"]},
    {"city": "Nairobi", "country": "KE", "airports": ["NBO"]},
]


def _norm(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]", "", ascii_str).strip()


def _resolve_city(city: str) -> List[str]:
    """Resolve a city name to IATA airport codes. Falls back to treating input as an IATA code."""
    q = _norm(city)
    for entry in _CITY_AIRPORT_MAP:
        city_norm = _norm(entry["city"])
        if city_norm.startswith(q) or q in city_norm:
            return entry["airports"]
    # Direct IATA code
    stripped = city.strip().upper()
    if len(stripped) == 3 and stripped.isalpha():
        return [stripped]
    return []


# ---------------------------------------------------------------------------
# AI scoring helpers
# ---------------------------------------------------------------------------

def _compute_flight_ai_score(flight: FlightResult) -> float:
    cpp = flight.cpp or 0.0
    price = float(flight.price or 0.0)
    rating = float(flight.rating or 3.5)
    stops = flight.stops or 0

    cpp_component = min(100.0, (cpp / 3.0) * 100.0)
    price_component = max(0.0, 100.0 - (price / 8.0))
    rating_component = (rating / 5.0) * 100.0
    convenience_component = 100.0 if stops == 0 else (70.0 if stops == 1 else 40.0)

    return round(
        0.35 * cpp_component
        + 0.30 * price_component
        + 0.20 * rating_component
        + 0.15 * convenience_component,
        1,
    )


def _flight_recommendation_tag(cpp: float, ai_score: float) -> str:
    if cpp >= 2.0:
        return "Points Better"
    if ai_score >= 65.0:
        return "Best Value"
    return "Cash Better"


def _compute_hotel_ai_score(hotel: HotelResult) -> float:
    price_per_night = float(hotel.price_per_night or 0.0)
    rating = float(hotel.rating or 3.5)
    amenities_count = len(hotel.amenities or [])

    price_component = max(0.0, 100.0 - (price_per_night / 5.0))
    rating_component = (rating / 5.0) * 100.0
    amenities_component = min(100.0, amenities_count * 20.0)

    return round(
        0.40 * price_component
        + 0.40 * rating_component
        + 0.20 * amenities_component,
        1,
    )


def _hotel_recommendation_tag(hotel: HotelResult, ai_score: float) -> str:
    rating = float(hotel.rating or 0.0)
    if ai_score >= 70.0:
        return "Best Value"
    if rating >= 4.5:
        return "Great Rating"
    if hotel.price_per_night < 120.0:
        return "Budget Pick"
    return "Consider"


def _enrich_flights_with_intelligence(flights: List[FlightResult]) -> None:
    """Dataset-aware decision intelligence: tags, decision, savings_vs_best, explanation."""
    if not flights:
        return

    prices = [float(f.price or 0.0) for f in flights]
    cpps = [float(f.cpp or 0.0) for f in flights]
    scores = [float(f.ai_score or 0.0) for f in flights]

    min_price = min(prices)
    avg_price = sum(prices) / len(prices)
    avg_cpp = sum(cpps) / len(cpps) if any(c > 0 for c in cpps) else 0.0
    top20_threshold = sorted(scores, reverse=True)[max(0, int(len(scores) * 0.2) - 1)]
    cheapest_nonstop = min((f.price or 0.0 for f in flights if f.stops == 0), default=None)

    for flight in flights:
        price = float(flight.price or 0.0)
        cpp = float(flight.cpp or 0.0)
        ai_score = float(flight.ai_score or 0.0)
        stops = flight.stops or 0

        flight.decision = "Points Better" if cpp >= 2.0 else "Cash Better"

        tags: List[str] = []
        if len(flights) > 1 and ai_score >= top20_threshold:
            tags.append("Best Value")
        if cpp >= 2.0:
            tags.append("High CPP")
        if stops == 0:
            tags.append("Non-stop")
        if price <= min_price * 1.02:
            tags.append("Cheapest")
        flight.tags = tags[:3]

        flight.savings_vs_best = round(price - min_price, 2)

        savings_vs_avg = round(avg_price - price)
        if price <= min_price * 1.02:
            flight.explanation = "Cheapest option available"
        elif cheapest_nonstop is not None and stops == 0 and price <= cheapest_nonstop * 1.02:
            flight.explanation = "Cheapest non-stop option"
        elif cpp >= 2.0 and avg_cpp > 0:
            pct = round(((cpp - avg_cpp) / avg_cpp) * 100)
            flight.explanation = f"{cpp:.1f} CPP — {pct}% better than average"
        elif savings_vs_avg >= 50:
            flight.explanation = f"Saves ${savings_vs_avg} vs similar flights"
        elif price > avg_price * 1.2:
            flight.explanation = f"${round(price - min_price)} more than cheapest option"
        else:
            stop_str = "Non-stop" if stops == 0 else f"{stops} stop{'s' if stops > 1 else ''}"
            flight.explanation = f"{stop_str} · ${round(price)}"


def _enrich_hotels_with_intelligence(hotels: List[HotelResult]) -> None:
    """Dataset-aware decision intelligence: tags, savings_vs_best, explanation."""
    if not hotels:
        return

    prices = [float(h.price_per_night or 0.0) for h in hotels]
    ratings = [float(h.rating or 0.0) for h in hotels]
    scores = [float(h.ai_score or 0.0) for h in hotels]

    avg_price = sum(prices) / len(prices)
    min_price = min(prices)
    top_rating = max(ratings) if ratings else 0.0
    top20_threshold = sorted(scores, reverse=True)[max(0, int(len(scores) * 0.2) - 1)]

    value_scores = [
        (float(h.rating or 0.0)) / max(float(h.price_per_night or 1.0), 1.0)
        for h in hotels
    ]
    max_value_score = max(value_scores) if value_scores else 0.0

    for i, hotel in enumerate(hotels):
        price = float(hotel.price_per_night or 0.0)
        rating = float(hotel.rating or 0.0)
        ai_score = float(hotel.ai_score or 0.0)
        stars = float(hotel.stars or 0.0)
        v_score = value_scores[i]

        tags: List[str] = []
        if max_value_score > 0 and v_score >= max_value_score * 0.9:
            tags.append("Best Value")
        if stars >= 4.0 and price >= avg_price * 1.2:
            tags.append("Luxury Pick")
        if price <= avg_price * 0.75:
            tags.append("Budget Friendly")
        if top_rating > 0 and rating >= top_rating * 0.97:
            tags.append("Top Rated")
        if len(hotels) > 1 and ai_score >= top20_threshold and "Best Value" not in tags:
            tags.append("Best Value")
        hotel.tags = tags[:3]

        hotel.savings_vs_best = round(price - min_price, 2)

        savings_vs_avg = round(avg_price - price)
        if "Luxury Pick" in tags:
            hotel.explanation = "Luxury feel at mid-range price" if price <= avg_price * 1.5 else "Premium stay with top amenities"
        elif "Best Value" in tags and max_value_score > 0 and v_score >= max_value_score * 0.9:
            hotel.explanation = "Best value hotel in area"
        elif "Top Rated" in tags:
            hotel.explanation = "Top-rated for this price range"
        elif savings_vs_avg >= 30:
            hotel.explanation = f"Saves ${savings_vs_avg}/night vs average"
        elif price > avg_price * 1.2:
            hotel.explanation = f"${round(price - min_price)} more per night than cheapest"
        else:
            hotel.explanation = f"${round(price)}/night · ★{rating:.1f}"


# ---------------------------------------------------------------------------
# Request / response models for create-with-search
# ---------------------------------------------------------------------------

class TripCreateWithSearch(BaseModel):
    origin_city: str
    origin_airports: Optional[List[str]] = None
    destination_city: str
    destination_airports: Optional[List[str]] = None
    start_date: date
    end_date: date
    title: Optional[str] = None


class TripWithResults(Trip):
    """Trip creation response with AI-scored flight + hotel candidates."""
    flights: List[FlightResult] = []
    hotels: List[HotelResult] = []
    round_trip_pairs: List[RoundTripFlightPair] = []


@router.get("", response_model=List[Trip])
def list_trips(db: DB, user_id: CurrentUserID) -> List[Trip]:
    """Return all trips belonging to the authenticated user."""
    return TripsService(db).list_trips(user_id)


@router.post("", response_model=Trip, status_code=status.HTTP_201_CREATED)
def create_trip(payload: TripCreate, db: DB, user_id: CurrentUserID) -> Trip:
    """Create a new trip. user_id is always taken from the JWT."""
    trip = TripsService(db).create_trip(payload.model_copy(update={"user_id": user_id}))
    if trip.start_date and trip.end_date:
        ItineraryService(db).ensure_trip_days(trip.id, trip.start_date, trip.end_date)
    return trip


@router.get("/{trip_id}", response_model=Trip)
def get_trip(trip_id: UUID, db: DB, user_id: CurrentUserID) -> Trip:
    """Fetch a single trip by ID — must belong to the authenticated user."""
    return TripsService(db).get_trip(trip_id, user_id)


@router.patch("/{trip_id}", response_model=Trip)
def update_trip(trip_id: UUID, payload: TripUpdate, db: DB, user_id: CurrentUserID) -> Trip:
    """Partially update a trip — must belong to the authenticated user."""
    trip = TripsService(db).update_trip(trip_id, payload, user_id)
    if trip.start_date and trip.end_date:
        ItineraryService(db).ensure_trip_days(trip.id, trip.start_date, trip.end_date)
    return trip


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(trip_id: UUID, db: DB, user_id: CurrentUserID) -> None:
    """Delete a trip and all its itinerary data (cascades via DB)."""
    TripsService(db).delete_trip(trip_id, user_id)


@router.get("/{trip_id}/items", response_model=List[ItineraryItem])
def list_trip_items(trip_id: UUID, db: DB, user_id: CurrentUserID) -> List[ItineraryItem]:
    """Return all itinerary items for a trip regardless of day assignment."""
    return ItineraryService(db).list_items_by_trip(trip_id)


@router.post("/create-with-search", response_model=TripWithResults, status_code=status.HTTP_201_CREATED)
def create_trip_with_search(payload: TripCreateWithSearch, db: DB, user_id: CurrentUserID) -> TripWithResults:
    """Unified concierge flow: resolve airports → search flights + hotels → AI-score → create trip."""
    # Step 1: Resolve airports
    origin_airports = payload.origin_airports or _resolve_city(payload.origin_city)
    dest_airports = payload.destination_airports or _resolve_city(payload.destination_city)

    if not dest_airports:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not resolve destination city '{payload.destination_city}' to airport codes.",
        )

    # Step 2: Search flights (skip gracefully if origin unknown)
    search_svc = SearchService(db)
    flights: List[FlightResult] = []
    if origin_airports:
        try:
            flight_req = FlightSearchRequest(
                origin_airports=origin_airports if len(origin_airports) > 1 else None,
                origin=origin_airports[0] if len(origin_airports) == 1 else None,
                destination_airports=dest_airports if len(dest_airports) > 1 else None,
                destination=dest_airports[0] if len(dest_airports) == 1 else None,
                departure_date=payload.start_date,
                passengers=1,
                cabin_class="economy",
            )
            flights = search_svc.search_flights(flight_req)
        except Exception:
            flights = []

    # Step 3: Search round-trip flight pairs (outbound + return)
    round_trip_pairs: List[RoundTripFlightPair] = []
    if origin_airports:
        try:
            rt_req = FlightSearchRequest(
                origin_airports=origin_airports if len(origin_airports) > 1 else None,
                origin=origin_airports[0] if len(origin_airports) == 1 else None,
                destination_airports=dest_airports if len(dest_airports) > 1 else None,
                destination=dest_airports[0] if len(dest_airports) == 1 else None,
                departure_date=payload.start_date,
                return_date=payload.end_date,
                passengers=1,
                cabin_class="economy",
            )
            round_trip_pairs = search_svc.search_round_trip_flights(rt_req)
        except Exception:
            round_trip_pairs = []

    # Step 3b: Search hotels
    hotels: List[HotelResult] = []
    try:
        hotel_req = HotelSearchRequest(
            location=payload.destination_city,
            check_in=payload.start_date,
            check_out=payload.end_date,
            guests=1,
        )
        hotels = search_svc.search_hotels(hotel_req)
    except Exception:
        hotels = []

    # Step 4: AI scoring — individual scores first, then dataset-aware intelligence
    for flight in flights:
        flight.ai_score = _compute_flight_ai_score(flight)
        flight.recommendation_tag = _flight_recommendation_tag(flight.cpp or 0.0, flight.ai_score)

    for hotel in hotels:
        hotel.ai_score = _compute_hotel_ai_score(hotel)
        hotel.recommendation_tag = _hotel_recommendation_tag(hotel, hotel.ai_score)

    _enrich_flights_with_intelligence(flights)
    _enrich_hotels_with_intelligence(hotels)

    flights_sorted = sorted(flights, key=lambda f: f.ai_score or 0.0, reverse=True)
    hotels_sorted = sorted(hotels, key=lambda h: h.ai_score or 0.0, reverse=True)

    # Step 5: Create trip
    title = payload.title or f"{payload.destination_city} Trip"
    trip = TripsService(db).create_trip(
        TripCreate(
            user_id=user_id,
            title=title,
            destination=payload.destination_city,
            origin=payload.origin_city if payload.origin_city else None,
            start_date=payload.start_date,
            end_date=payload.end_date,
            status="planned",
        ).model_copy(update={"user_id": user_id})
    )
    itinerary_svc = ItineraryService(db)
    if trip.start_date and trip.end_date:
        itinerary_svc.ensure_trip_days(trip.id, trip.start_date, trip.end_date)

    # Step 6: Persist flight + hotel candidates as trip-level itinerary items
    for idx, flight in enumerate(flights_sorted[:10]):
        try:
            itinerary_svc.create_trip_item(ItineraryItemDirectCreate(
                trip_id=trip.id,
                item_type="flight",
                title=f"{flight.airline} {flight.flight_number}",
                start_time=flight.departure_time,
                end_time=flight.arrival_time,
                cash_price=flight.price,
                points_price=flight.points_cost,
                cpp_value=flight.cpp,
                position=idx,
                details={
                    "airline": flight.airline,
                    "flight_number": flight.flight_number,
                    "origin": flight.origin,
                    "destination": flight.destination,
                    "departure_time": flight.departure_time.isoformat(),
                    "arrival_time": flight.arrival_time.isoformat(),
                    "duration_minutes": flight.duration_minutes,
                    "stops": flight.stops,
                    "cabin_class": flight.cabin_class,
                    "price": float(flight.price or 0),
                    "points_cost": flight.points_cost,
                    "cpp": float(flight.cpp or 0),
                    "ai_score": float(flight.ai_score or 0),
                    "recommendation_tag": flight.recommendation_tag,
                    "decision": flight.decision,
                    "tags": flight.tags,
                    "savings_vs_best": flight.savings_vs_best,
                    "explanation": flight.explanation,
                    "booking_url": flight.booking_url,
                    "booking_options": [
                        {"provider": o.provider, "url": o.url}
                        for o in flight.booking_options
                    ],
                },
            ))
        except Exception:
            pass

    for idx, hotel in enumerate(hotels_sorted[:10]):
        try:
            itinerary_svc.create_trip_item(ItineraryItemDirectCreate(
                trip_id=trip.id,
                item_type="hotel",
                title=hotel.name,
                location=hotel.location,
                cash_price=hotel.price_per_night,
                position=idx,
                details={
                    "name": hotel.name,
                    "location": hotel.location,
                    "price_per_night": float(hotel.price_per_night or 0),
                    "total_price": float(hotel.price or 0),
                    "rating": hotel.rating,
                    "stars": hotel.stars,
                    "amenities": hotel.amenities,
                    "check_in": hotel.check_in.isoformat(),
                    "check_out": hotel.check_out.isoformat(),
                    "nights": hotel.nights,
                    "ai_score": float(hotel.ai_score or 0),
                    "recommendation_tag": hotel.recommendation_tag,
                    "tags": hotel.tags,
                    "savings_vs_best": hotel.savings_vs_best,
                    "explanation": hotel.explanation,
                    "booking_url": hotel.booking_url,
                    "booking_options": [
                        {"provider": o.provider, "url": o.url}
                        for o in hotel.booking_options
                    ],
                    "lat": hotel.lat,
                    "lng": hotel.lng,
                    "location_score": hotel.location_score,
                    "proximity_label": hotel.proximity_label,
                    "area_label": hotel.area_label,
                },
            ))
        except Exception:
            pass

    # Step 7: Persist top round-trip pairs as trip-level itinerary items
    for idx, pair in enumerate(round_trip_pairs[:5]):
        try:
            outbound_ai = _compute_flight_ai_score(pair.outbound)
            itinerary_svc.create_trip_item(ItineraryItemDirectCreate(
                trip_id=trip.id,
                item_type="flight",
                title=f"{pair.outbound.airline} {pair.outbound.flight_number} + {pair.return_flight.airline} {pair.return_flight.flight_number}",
                start_time=pair.outbound.departure_time,
                end_time=pair.return_flight.arrival_time,
                cash_price=pair.total_price,
                points_price=pair.total_points,
                cpp_value=pair.combined_cpp,
                position=1000 + idx,
                details={
                    "is_round_trip": True,
                    "pair_id": pair.id,
                    "cabin_class": pair.outbound.cabin_class,
                    "total_price": pair.total_price,
                    "total_points": pair.total_points,
                    "combined_cpp": pair.combined_cpp,
                    "total_duration_minutes": pair.total_duration_minutes,
                    "ai_score": float(outbound_ai),
                    "outbound": {
                        "airline": pair.outbound.airline,
                        "flight_number": pair.outbound.flight_number,
                        "origin": pair.outbound.origin,
                        "destination": pair.outbound.destination,
                        "departure_time": pair.outbound.departure_time.isoformat(),
                        "arrival_time": pair.outbound.arrival_time.isoformat(),
                        "duration_minutes": pair.outbound.duration_minutes,
                        "stops": pair.outbound.stops,
                        "price": float(pair.outbound.price or 0),
                        "points_cost": pair.outbound.points_cost,
                        "cpp": float(pair.outbound.cpp or 0),
                        "booking_url": pair.outbound.booking_url,
                    },
                    "return_flight": {
                        "airline": pair.return_flight.airline,
                        "flight_number": pair.return_flight.flight_number,
                        "origin": pair.return_flight.origin,
                        "destination": pair.return_flight.destination,
                        "departure_time": pair.return_flight.departure_time.isoformat(),
                        "arrival_time": pair.return_flight.arrival_time.isoformat(),
                        "duration_minutes": pair.return_flight.duration_minutes,
                        "stops": pair.return_flight.stops,
                        "price": float(pair.return_flight.price or 0),
                        "points_cost": pair.return_flight.points_cost,
                        "cpp": float(pair.return_flight.cpp or 0),
                        "booking_url": pair.return_flight.booking_url,
                    },
                },
            ))
        except Exception:
            pass

    return TripWithResults(
        **trip.model_dump(),
        flights=flights_sorted,
        hotels=hotels_sorted,
        round_trip_pairs=round_trip_pairs[:5],
    )
