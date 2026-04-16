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
from app.models.search import FlightResult, FlightSearchRequest, HotelResult, HotelSearchRequest
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


@router.get("", response_model=List[Trip])
def list_trips(db: DB, user_id: CurrentUserID) -> List[Trip]:
    """Return all trips belonging to the authenticated user."""
    return TripsService(db).list_trips(user_id)


@router.post("", response_model=Trip, status_code=status.HTTP_201_CREATED)
def create_trip(payload: TripCreate, db: DB, user_id: CurrentUserID) -> Trip:
    """Create a new trip. user_id is always taken from the JWT."""
    return TripsService(db).create_trip(payload.model_copy(update={"user_id": user_id}))


@router.get("/{trip_id}", response_model=Trip)
def get_trip(trip_id: UUID, db: DB, user_id: CurrentUserID) -> Trip:
    """Fetch a single trip by ID — must belong to the authenticated user."""
    return TripsService(db).get_trip(trip_id, user_id)


@router.patch("/{trip_id}", response_model=Trip)
def update_trip(trip_id: UUID, payload: TripUpdate, db: DB, user_id: CurrentUserID) -> Trip:
    """Partially update a trip — must belong to the authenticated user."""
    return TripsService(db).update_trip(trip_id, payload, user_id)


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

    # Step 3: Search hotels
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

    # Step 4: AI scoring — compute scores and update tags, then sort
    for flight in flights:
        flight.ai_score = _compute_flight_ai_score(flight)
        flight.recommendation_tag = _flight_recommendation_tag(flight.cpp or 0.0, flight.ai_score)

    for hotel in hotels:
        hotel.ai_score = _compute_hotel_ai_score(hotel)
        hotel.recommendation_tag = _hotel_recommendation_tag(hotel, hotel.ai_score)

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

    # Step 6: Persist flight + hotel candidates as trip-level itinerary items
    itinerary_svc = ItineraryService(db)
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
                    "booking_url": hotel.booking_url,
                    "booking_options": [
                        {"provider": o.provider, "url": o.url}
                        for o in hotel.booking_options
                    ],
                },
            ))
        except Exception:
            pass

    return TripWithResults(
        **trip.model_dump(),
        flights=flights_sorted,
        hotels=hotels_sorted,
    )
