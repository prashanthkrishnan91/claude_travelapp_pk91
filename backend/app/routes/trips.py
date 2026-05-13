import logging
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, wait as _futures_wait
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, field_validator as pydantic_field_validator

logger = logging.getLogger(__name__)

# Maximum wall-clock seconds the three provider searches (flights, round-trip,
# hotels) may collectively take.  After this deadline _futures_wait returns and
# we proceed with whatever finished; executor.shutdown(wait=False) is then
# called so the route handler is NOT blocked waiting for slow threads — their
# HTTP calls will time out on their own (Duffel cap: 8s per call).
_SEARCH_BUDGET_SECONDS = 15.0


def _safe_future_result(fut, done_set, default):
    """Return fut's result if it's in done_set, else default.

    Catches all exceptions so a provider error never propagates past the
    collection step.  Only call on futures that are known to have completed
    (i.e., in done_set from futures_wait).
    """
    if fut is None or fut not in done_set:
        return default
    try:
        return fut.result()
    except Exception:
        return default

from app.contracts.flights import (
    MOCK_BOOKING_HOST as _CONTRACT_MOCK_BOOKING_HOST,
    is_mock_derived_flight as _contract_is_mock_derived_flight,
)
from app.core.deps import DB, CurrentUserID
from app.models import Trip, TripCreate, TripUpdate, ItineraryItem
from app.models.itinerary import ItineraryItemDirectCreate, ItineraryItemType
from app.models.search import ExploreSnapshot, FlightResult, FlightSearchRequest, HotelResult, HotelSearchRequest, RestaurantSearchRequest, RoundTripFlightPair
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

# ---------------------------------------------------------------------------
# Mock-derived detection — fail-closed guard for /trips/create-with-search
# ---------------------------------------------------------------------------

# Sentinel substring stamped into every ``_mock_*`` booking URL in
# ``backend/app/services/search.py``.  Any URL containing this host is, by
# construction, fabricated and must never be persisted.  Sourced from the
# Flights Product Contract v1 module so the value lives in one place.
_MOCK_BOOKING_HOST = _CONTRACT_MOCK_BOOKING_HOST


def _is_mock_flight(flight: FlightResult) -> bool:
    """True if a flight row came from ``_mock_flights`` (or any future mock
    fixture that follows the same source/booking-URL convention).

    Delegates to ``app.contracts.flights.is_mock_derived_flight`` — the
    single source of truth for the Flights Product Contract v1 mock
    detection rules.  Kept as a thin wrapper to preserve the existing import
    surface used by ``backend/tests/test_create_with_search_fail_closed.py``.
    """
    return _contract_is_mock_derived_flight(flight)


def _is_mock_hotel(hotel: HotelResult) -> bool:
    if (hotel.source or "").lower() in {"mock", "demo", "fixture"}:
        return True
    if hotel.booking_url and _MOCK_BOOKING_HOST in hotel.booking_url:
        return True
    for opt in hotel.booking_options or []:
        if opt.url and _MOCK_BOOKING_HOST in opt.url:
            return True
    return False


def _any_mock_derived(
    flights: List[FlightResult],
    hotels: List[HotelResult],
    pairs: List[RoundTripFlightPair],
) -> bool:
    """Return True if any flight, hotel, or round-trip leg looks mock-derived.

    Used to fail closed *before* a trip or any itinerary item is persisted,
    so fabricated booking URLs (``book.example.com``) and ``source="mock"``
    rows can never reach ``itinerary_items.details``.
    """
    if any(_is_mock_flight(f) for f in flights):
        return True
    if any(_is_mock_hotel(h) for h in hotels):
        return True
    for pair in pairs:
        if _is_mock_flight(pair.outbound) or _is_mock_flight(pair.return_flight):
            return True
    return False


class TripCreateWithSearch(BaseModel):
    origin_city: str
    origin_airports: Optional[List[str]] = None
    destination_city: str
    destination_airports: Optional[List[str]] = None
    start_date: date
    end_date: date
    title: Optional[str] = None
    travelers: int = 1

    @pydantic_field_validator("travelers", mode="before")
    @classmethod
    def _sanitize_travelers(cls, value):
        try:
            n = int(value)
        except (TypeError, ValueError):
            return 1
        return max(1, n)


class TripWithResults(Trip):
    """Trip creation response with AI-scored flight + hotel candidates and seeding status."""
    flights: List[FlightResult] = []
    hotels: List[HotelResult] = []
    round_trip_pairs: List[RoundTripFlightPair] = []
    # Per-vertical seeding counts — harvested from provider, persisted to DB.
    # Allows the frontend to know what was found without a separate /items fetch.
    seeding_status: dict = {}


@router.get("", response_model=List[Trip])
def list_trips(db: DB, user_id: CurrentUserID) -> List[Trip]:
    """Return all trips belonging to the authenticated user."""
    return TripsService(db).list_trips(user_id)


@router.post("", response_model=Trip, status_code=status.HTTP_201_CREATED)
def create_trip(payload: TripCreate, db: DB, user_id: CurrentUserID) -> Trip:
    """Create a new trip. user_id is always taken from the JWT."""
    trip = TripsService(db).create_trip(payload.model_copy(update={"user_id": user_id}))
    if trip.start_date and trip.end_date:
        ItineraryService(db).ensure_trip_days(trip.id, trip.start_date, trip.end_date, user_id)
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
        ItineraryService(db).ensure_trip_days(trip.id, trip.start_date, trip.end_date, user_id)
    return trip


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(trip_id: UUID, db: DB, user_id: CurrentUserID) -> None:
    """Delete a trip and all its itinerary data (cascades via DB)."""
    TripsService(db).delete_trip(trip_id, user_id)


@router.get("/{trip_id}/items", response_model=List[ItineraryItem])
def list_trip_items(trip_id: UUID, db: DB, user_id: CurrentUserID) -> List[ItineraryItem]:
    """Return all itinerary items for a trip regardless of day assignment."""
    TripsService(db).get_trip(trip_id, user_id)
    return ItineraryService(db).list_items_by_trip(trip_id)


@router.get("/{trip_id}/ideas", response_model=List[ItineraryItem])
def list_trip_ideas(trip_id: UUID, db: DB, user_id: CurrentUserID) -> List[ItineraryItem]:
    """Return unscheduled itinerary items (saved concierge ideas not yet assigned to a day)."""
    TripsService(db).get_trip(trip_id, user_id)
    return ItineraryService(db).list_unscheduled_items(trip_id)


@router.get("/{trip_id}/explore-snapshot", response_model=Optional[ExploreSnapshot])
def get_explore_snapshot(trip_id: UUID, db: DB, user_id: CurrentUserID) -> Optional[ExploreSnapshot]:
    """Return persisted Explore candidate snapshot for Attractions and Restaurants, or null when absent."""
    snapshot = TripsService(db).get_explore_snapshot(trip_id, user_id)
    if not snapshot:
        return None
    return ExploreSnapshot(**snapshot)


@router.put("/{trip_id}/explore-snapshot", status_code=status.HTTP_204_NO_CONTENT)
def save_explore_snapshot(trip_id: UUID, payload: ExploreSnapshot, db: DB, user_id: CurrentUserID) -> None:
    """Persist Explore candidate snapshot for the trip. Overwrites previous snapshot."""
    TripsService(db).save_explore_snapshot(trip_id, user_id, payload.model_dump(mode="json"))


@router.post("/create-with-search", response_model=TripWithResults, status_code=status.HTTP_201_CREATED)
def create_trip_with_search(payload: TripCreateWithSearch, db: DB, user_id: CurrentUserID) -> TripWithResults:
    """Unified concierge flow: resolve airports → search all four verticals → AI-score → create trip.

    Verticals seeded concurrently: flights (one-way), round-trip pairs, hotels,
    attractions, restaurants.  A per-vertical seeding_status dict is returned so
    the frontend knows what was harvested and persisted without a follow-up fetch.

    Flight searches use only the primary (first) airport per city to prevent the
    origin×destination cross-product from exceeding the provider budget.
    """
    t_total_start = time.perf_counter()

    # Step 1: Resolve airports
    origin_airports = payload.origin_airports or _resolve_city(payload.origin_city)
    dest_airports = payload.destination_airports or _resolve_city(payload.destination_city)

    if not dest_airports:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not resolve destination city '{payload.destination_city}' to airport codes.",
        )

    logger.info(
        "[create_with_search.timing] phase=airport_resolution origin_airports=%d destination_airports=%d elapsed_ms=%d",
        len(origin_airports),
        len(dest_airports),
        int((time.perf_counter() - t_total_start) * 1000),
    )

    search_svc = SearchService(db)

    # Step 2: Build provider requests.
    #
    # Flights — use ONLY the primary (first) airport for each city.
    # Passing the full multi-airport list causes search_flights to iterate every
    # origin×destination pair sequentially.  For Tokyo (NRT + HND) that doubles
    # the Duffel call count, and for rt_fut it quadruples it, routinely blowing
    # past the 15-second budget.  The primary airport covers the dominant route;
    # the full multi-airport path is still available from the standalone
    # /search/flights endpoint.
    flight_req: Optional[FlightSearchRequest] = None
    rt_req: Optional[FlightSearchRequest] = None
    if origin_airports and dest_airports:
        _primary_origin = origin_airports[0]
        _primary_dest = dest_airports[0]
        flight_req = FlightSearchRequest(
            origin=_primary_origin,
            destination=_primary_dest,
            departure_date=payload.start_date,
            passengers=payload.travelers,
            cabin_class="economy",
        )
        rt_req = FlightSearchRequest(
            origin=_primary_origin,
            destination=_primary_dest,
            departure_date=payload.start_date,
            return_date=payload.end_date,
            passengers=payload.travelers,
            cabin_class="economy",
        )

    hotel_req = HotelSearchRequest(
        location=payload.destination_city,
        check_in=payload.start_date,
        check_out=payload.end_date,
        guests=payload.travelers,
    )
    restaurant_req = RestaurantSearchRequest(
        location=payload.destination_city,
    )

    # Step 3: Submit all five provider searches concurrently.
    #
    # IMPORTANT — do NOT use `with ThreadPoolExecutor(...) as pool:` here.
    # The context-manager calls shutdown(wait=True) on exit which blocks the
    # route regardless of the budget.  Instead call shutdown(wait=False) after
    # collecting results so the route returns immediately; any still-running
    # Duffel threads will self-terminate when their HTTP timeout fires (≤8s).
    t_search_start = time.perf_counter()
    flights: List[FlightResult] = []
    round_trip_pairs: List[RoundTripFlightPair] = []
    hotels: List[HotelResult] = []
    attractions: List[dict] = []
    restaurants: List = []

    _executor = ThreadPoolExecutor(max_workers=5)
    try:
        f_fut = _executor.submit(search_svc.search_flights, flight_req) if flight_req else None
        rt_fut = _executor.submit(search_svc.search_round_trip_flights, rt_req) if rt_req else None
        h_fut = _executor.submit(search_svc.search_hotels, hotel_req)
        att_fut = _executor.submit(search_svc.search_attractions, payload.destination_city)
        rest_fut = _executor.submit(search_svc.search_restaurants, restaurant_req)

        _live = [f for f in (f_fut, rt_fut, h_fut, att_fut, rest_fut) if f is not None]
        _done, _not_done = _futures_wait(_live, timeout=_SEARCH_BUDGET_SECONDS)

        flights = _safe_future_result(f_fut, _done, [])
        round_trip_pairs = _safe_future_result(rt_fut, _done, [])
        hotels = _safe_future_result(h_fut, _done, [])
        attractions = _safe_future_result(att_fut, _done, [])
        restaurants = _safe_future_result(rest_fut, _done, [])
    finally:
        _executor.shutdown(wait=False, cancel_futures=True)

    t_search_ms = int((time.perf_counter() - t_search_start) * 1000)
    logger.info(
        "[create_with_search.timing] phase=provider_search "
        "flights=%d rt_pairs=%d hotels=%d attractions=%d restaurants=%d "
        "elapsed_ms=%d timed_out=%d",
        len(flights), len(round_trip_pairs), len(hotels),
        len(attractions), len(restaurants),
        t_search_ms, len(_not_done),
    )

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

    # Fail-closed guard: refuse to persist mock-derived rows.
    # Attractions and restaurants come from Google Places (source="google_places")
    # so they are not checked here — this guard is specific to the legacy mock
    # fixtures for flights/hotels.
    if _any_mock_derived(flights_sorted, hotels_sorted, round_trip_pairs):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "provider_unavailable",
                "message": (
                    "Flights and hotels are temporarily unavailable because "
                    "provider-backed search is not enabled yet. Create a "
                    "blank trip and add items manually."
                ),
            },
        )

    # Step 5: Create trip (always, even when provider results are empty)
    t_trip_start = time.perf_counter()
    title = (payload.title.strip() if payload.title and payload.title.strip() else f"{payload.destination_city} Trip")
    trip = TripsService(db).create_trip(
        TripCreate(
            user_id=user_id,
            title=title,
            destination=payload.destination_city,
            origin=payload.origin_city if payload.origin_city else None,
            start_date=payload.start_date,
            end_date=payload.end_date,
            travelers=payload.travelers,
            status="planned",
        ).model_copy(update={"user_id": user_id})
    )
    t_trip_create_ms = int((time.perf_counter() - t_trip_start) * 1000)
    logger.info("[create_with_search.timing] phase=trip_create elapsed_ms=%d", t_trip_create_ms)

    itinerary_svc = ItineraryService(db)
    t_ensure_days_start = time.perf_counter()
    if trip.start_date and trip.end_date:
        itinerary_svc.ensure_trip_days(trip.id, trip.start_date, trip.end_date, user_id)
    logger.info(
        "[create_with_search.timing] phase=ensure_trip_days elapsed_ms=%d",
        int((time.perf_counter() - t_ensure_days_start) * 1000),
    )

    # Step 6: Persist all four verticals as trip-level itinerary items.
    # Each vertical is persisted independently so a failure in one does not
    # discard completed results from another.  Errors are logged at WARNING
    # (not silently swallowed) so they appear in Railway logs.
    seeding: dict = {}

    # 6a — Flights (one-way)
    t_persist_flights_start = time.perf_counter()
    _flights_persisted = 0
    for idx, flight in enumerate(flights_sorted[:10]):
        try:
            itinerary_svc.create_trip_item(ItineraryItemDirectCreate(
                trip_id=trip.id,
                item_type=ItineraryItemType.FLIGHT,
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
            ), user_id)
            _flights_persisted += 1
        except Exception as _exc:
            logger.warning("[create_with_search.persist] vertical=flight idx=%d error=%s", idx, _exc)

    seeding["flights"] = {"harvested": len(flights_sorted), "persisted": _flights_persisted}
    logger.info("[create_with_search.timing] phase=persist_flights harvested=%d persisted=%d elapsed_ms=%d", len(flights_sorted), _flights_persisted, int((time.perf_counter() - t_persist_flights_start) * 1000))

    # 6b — Hotels
    t_persist_hotels_start = time.perf_counter()
    _hotels_persisted = 0
    for idx, hotel in enumerate(hotels_sorted[:10]):
        try:
            itinerary_svc.create_trip_item(ItineraryItemDirectCreate(
                trip_id=trip.id,
                item_type=ItineraryItemType.HOTEL,
                title=hotel.name,
                location=hotel.location,
                cash_price=hotel.price_per_night if hotel.price_per_night else None,
                position=idx,
                details={
                    "name": hotel.name,
                    "location": hotel.location,
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
            ), user_id)
            _hotels_persisted += 1
        except Exception as _exc:
            logger.warning("[create_with_search.persist] vertical=hotel idx=%d error=%s", idx, _exc)

    seeding["hotels"] = {"harvested": len(hotels_sorted), "persisted": _hotels_persisted}
    logger.info("[create_with_search.timing] phase=persist_hotels harvested=%d persisted=%d elapsed_ms=%d", len(hotels_sorted), _hotels_persisted, int((time.perf_counter() - t_persist_hotels_start) * 1000))

    # 6c — Round-trip pairs
    t_persist_round_trip_pairs_start = time.perf_counter()
    _rt_persisted = 0
    for idx, pair in enumerate(round_trip_pairs[:5]):
        try:
            outbound_ai = _compute_flight_ai_score(pair.outbound)
            itinerary_svc.create_trip_item(ItineraryItemDirectCreate(
                trip_id=trip.id,
                item_type=ItineraryItemType.FLIGHT,
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
            ), user_id)
            _rt_persisted += 1
        except Exception as _exc:
            logger.warning("[create_with_search.persist] vertical=round_trip idx=%d error=%s", idx, _exc)

    seeding["round_trip_pairs"] = {"harvested": len(round_trip_pairs), "persisted": _rt_persisted}
    logger.info("[create_with_search.timing] phase=persist_round_trip_pairs harvested=%d persisted=%d elapsed_ms=%d", len(round_trip_pairs), _rt_persisted, int((time.perf_counter() - t_persist_round_trip_pairs_start) * 1000))

    # 6d — Attractions (Google Places verified, OPERATIONAL only)
    t_persist_attractions_start = time.perf_counter()
    # Seeded as ACTIVITY items.  These are addable via Google Maps URI — no fake
    # booking URLs, no mock rows, no invented data.
    _attractions_persisted = 0
    for idx, att in enumerate(attractions):
        try:
            itinerary_svc.create_trip_item(ItineraryItemDirectCreate(
                trip_id=trip.id,
                item_type=ItineraryItemType.ACTIVITY,
                title=att["name"],
                location=att.get("address") or payload.destination_city,
                position=2000 + idx,
                details={
                    "name": att["name"],
                    "address": att.get("address"),
                    "rating": att.get("rating"),
                    "num_reviews": att.get("num_reviews"),
                    "google_maps_uri": att.get("google_maps_uri"),
                    "booking_url": att.get("booking_url"),
                    "lat": att.get("lat"),
                    "lng": att.get("lng"),
                    "types": att.get("types", []),
                    "source": "google_places",
                    "source_kind": "creation_seed",
                    "place_id": att.get("place_id"),
                },
            ), user_id)
            _attractions_persisted += 1
        except Exception as _exc:
            logger.warning("[create_with_search.persist] vertical=attraction idx=%d error=%s", idx, _exc)

    seeding["attractions"] = {"harvested": len(attractions), "persisted": _attractions_persisted}
    logger.info("[create_with_search.timing] phase=persist_attractions harvested=%d persisted=%d elapsed_ms=%d", len(attractions), _attractions_persisted, int((time.perf_counter() - t_persist_attractions_start) * 1000))

    # 6e — Restaurants (Google Places verified, OPERATIONAL only)
    t_persist_restaurants_start = time.perf_counter()
    # Seeded as MEAL items.  Same contract as attractions — canonical Maps URI
    # only, no fabricated rates or booking links.
    _restaurants_persisted = 0
    for idx, rest in enumerate(restaurants[:8]):
        try:
            itinerary_svc.create_trip_item(ItineraryItemDirectCreate(
                trip_id=trip.id,
                item_type=ItineraryItemType.MEAL,
                title=rest.name,
                location=rest.address or payload.destination_city,
                position=3000 + idx,
                details={
                    "name": rest.name,
                    "address": rest.address,
                    "cuisine": rest.cuisine,
                    "rating": rest.rating,
                    "num_reviews": rest.num_reviews,
                    "price_level": rest.price_level,
                    "google_maps_uri": rest.google_maps_uri,
                    "booking_url": rest.booking_url,
                    "lat": rest.lat,
                    "lng": rest.lng,
                    "ai_score": float(rest.ai_score or 0) if rest.ai_score is not None else None,
                    "tags": rest.tags,
                    "source": "google_places",
                    "source_kind": "creation_seed",
                    "place_id": rest.place_id,
                },
            ), user_id)
            _restaurants_persisted += 1
        except Exception as _exc:
            logger.warning("[create_with_search.persist] vertical=restaurant idx=%d error=%s", idx, _exc)

    seeding["restaurants"] = {"harvested": len(restaurants), "persisted": _restaurants_persisted}
    logger.info("[create_with_search.timing] phase=persist_restaurants harvested=%d persisted=%d elapsed_ms=%d", len(restaurants), _restaurants_persisted, int((time.perf_counter() - t_persist_restaurants_start) * 1000))

    t_total_ms = int((time.perf_counter() - t_total_start) * 1000)
    logger.info(
        "[create_with_search.timing] phase=total "
        "flights_harvested=%d flights_persisted=%d "
        "hotels_harvested=%d hotels_persisted=%d "
        "attractions_harvested=%d attractions_persisted=%d "
        "restaurants_harvested=%d restaurants_persisted=%d "
        "rt_pairs_harvested=%d rt_pairs_persisted=%d "
        "elapsed_ms=%d",
        seeding["flights"]["harvested"], seeding["flights"]["persisted"],
        seeding["hotels"]["harvested"], seeding["hotels"]["persisted"],
        seeding["attractions"]["harvested"], seeding["attractions"]["persisted"],
        seeding["restaurants"]["harvested"], seeding["restaurants"]["persisted"],
        seeding["round_trip_pairs"]["harvested"], seeding["round_trip_pairs"]["persisted"],
        t_total_ms,
    )

    return TripWithResults(
        **trip.model_dump(),
        flights=flights_sorted,
        hotels=hotels_sorted,
        round_trip_pairs=round_trip_pairs[:5],
        seeding_status=seeding,
    )
