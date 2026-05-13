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
from app.contracts.flight_offer import (
    BookingLinkType,
    FlightItineraryOffer,
    TripType,
)
from app.contracts.flights import FlightSourceStatus
from app.core.deps import DB, CurrentUserID
from app.models import Trip, TripCreate, TripUpdate, ItineraryItem
from app.models.itinerary import ItineraryItemDirectCreate, ItineraryItemType
from app.models.search import ExploreSnapshot, FlightResult, FlightSearchRequest, HotelResult, HotelSearchRequest, RestaurantSearchRequest, RoundTripFlightPair
from app.services import TripsService
from app.services.canonical_flight_search import (
    CanonicalFlightSearchResult,
    canonical_flight_search,
)
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


def _parse_offer_iso(value: Optional[str]):
    """Parse an ISO 8601 string from a canonical offer into a naive datetime.

    Returns None on parse failure.  Used to populate ``start_time`` / ``end_time``
    on the persisted flight item.  Naive datetimes match the existing
    ``ItineraryItemBase`` shape used by every other persisted item.
    """
    from datetime import datetime as _dt
    if not value:
        return None
    try:
        v = value
        if v.endswith("Z"):
            v = v[:-1] + "+00:00"
        dt = _dt.fromisoformat(v)
        if dt.tzinfo is not None:
            dt = dt.astimezone(tz=None).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def _serialize_offer_leg(leg) -> dict:
    return {
        "origin": leg.origin,
        "destination": leg.destination,
        "departure_time": leg.departure_time,
        "arrival_time": leg.arrival_time,
        "duration_minutes": leg.duration_minutes,
        "stops": leg.stops,
        "segments": [
            {
                "airline": s.airline,
                "flight_number": s.flight_number,
                "origin": s.origin,
                "destination": s.destination,
                "departure_time": s.departure_time,
                "arrival_time": s.arrival_time,
                "duration_minutes": s.duration_minutes,
                "cabin_class": s.cabin_class,
            }
            for s in leg.segments
        ],
    }


def _offer_to_flight_item(
    offer: FlightItineraryOffer,
    *,
    trip_id,
    position: int,
) -> ItineraryItemDirectCreate:
    """Deterministic mapper: canonical FlightItineraryOffer → flight Trip Idea.

    Persists with ``day_id = None`` so the offer appears as an unscheduled
    Trip Idea, never auto-scheduled to a day.  Preserves the canonical
    Google Flights SEARCH_REDIRECT link (search-only, not booking) and never
    includes booking/order/payment fields.
    """
    ob = offer.outbound_leg
    rt = offer.return_leg
    first_seg = ob.segments[0]
    airline = first_seg.airline or "Flight"
    flight_no = first_seg.flight_number or ""

    if rt is not None:
        title = f"{airline} {flight_no} {ob.origin}→{ob.destination} · return {rt.origin}→{rt.destination}".strip()
    else:
        title = f"{airline} {flight_no} {ob.origin}→{ob.destination}".strip()

    start_dt = _parse_offer_iso(ob.departure_time)
    end_dt = _parse_offer_iso(rt.arrival_time if rt is not None else ob.arrival_time)

    booking_link = offer.booking_link
    google_url: Optional[str] = None
    if booking_link.link_type is BookingLinkType.SEARCH_REDIRECT and booking_link.url:
        google_url = booking_link.url

    details: dict = {
        "kind": "flight_offer",
        "provider": offer.provider,
        "source": offer.provider,
        "source_kind": "creation_seed",
        "trip_type": offer.trip_type.value,
        "origin": offer.origin,
        "destination": offer.destination,
        "departure_date": offer.departure_date,
        "return_date": offer.return_date,
        "passengers": offer.passengers,
        "cabin_class": offer.cabin_class,
        "live_cached_status": offer.live_cached_status.value,
        "fetched_at": offer.fetched_at,
        "airline": airline,
        "flight_number": flight_no,
        "stops": ob.stops,
        "duration_minutes": ob.duration_minutes,
        "departure_time": ob.departure_time,
        "arrival_time": ob.arrival_time,
        "cash_price": float(offer.price.total_amount),
        "currency": offer.price.currency,
        "outbound_leg": _serialize_offer_leg(ob),
        "return_leg": _serialize_offer_leg(rt) if rt is not None else None,
        "google_flights_search_url": google_url,
        "booking_link": {
            "url": booking_link.url,
            "link_type": booking_link.link_type.value,
            "provider_name": booking_link.provider_name,
            "kind": "search_redirect_only",
        },
    }

    return ItineraryItemDirectCreate(
        trip_id=trip_id,
        day_id=None,  # Trip Idea — unscheduled until the user assigns it.
        item_type=ItineraryItemType.FLIGHT,
        title=title,
        start_time=start_dt,
        end_time=end_dt,
        cash_price=float(offer.price.total_amount),
        cash_currency=offer.price.currency,
        position=position,
        details=details,
    )


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
    # Flights — canonical provider search, exactly the same path Explore Flights
    # uses.  Single primary airport per city to preserve the latency cap (the
    # cross-product over multi-airport groups blows the 15-second budget).  The
    # canonical Duffel provider handles round-trip natively when ``return_date``
    # is set; we do NOT keep the legacy two-call outbound/return SearchService
    # pairing that could diverge from Explore Flights.
    flight_req: Optional[FlightSearchRequest] = None
    if origin_airports and dest_airports:
        _primary_origin = origin_airports[0]
        _primary_dest = dest_airports[0]
        flight_req = FlightSearchRequest(
            origin=_primary_origin,
            destination=_primary_dest,
            departure_date=payload.start_date,
            return_date=payload.end_date if payload.end_date and payload.end_date > payload.start_date else None,
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
    flight_offers: List[FlightItineraryOffer] = []
    flight_search_status: str = FlightSourceStatus.UNAVAILABLE.value
    flight_search_reason: str = ""
    hotels: List[HotelResult] = []
    attractions: List[dict] = []
    restaurants: List = []

    _executor = ThreadPoolExecutor(max_workers=4)
    try:
        f_fut = _executor.submit(canonical_flight_search, flight_req) if flight_req else None
        h_fut = _executor.submit(search_svc.search_hotels, hotel_req)
        att_fut = _executor.submit(search_svc.search_attractions, payload.destination_city)
        rest_fut = _executor.submit(search_svc.search_restaurants, restaurant_req)

        _live = [f for f in (f_fut, h_fut, att_fut, rest_fut) if f is not None]
        _done, _not_done = _futures_wait(_live, timeout=_SEARCH_BUDGET_SECONDS)

        _flight_result: Optional[CanonicalFlightSearchResult] = _safe_future_result(f_fut, _done, None)
        if _flight_result is not None:
            flight_offers = list(_flight_result.offers)
            flight_search_status = _flight_result.status.value
            flight_search_reason = _flight_result.reason or ""
        hotels = _safe_future_result(h_fut, _done, [])
        attractions = _safe_future_result(att_fut, _done, [])
        restaurants = _safe_future_result(rest_fut, _done, [])
    finally:
        _executor.shutdown(wait=False, cancel_futures=True)

    # Legacy SearchService flight rows are no longer produced here — the canonical
    # provider (Duffel) is the single source of truth for visible flight cards.
    flights: List[FlightResult] = []
    round_trip_pairs: List[RoundTripFlightPair] = []

    t_search_ms = int((time.perf_counter() - t_search_start) * 1000)
    logger.info(
        "[create_with_search.timing] phase=provider_search "
        "flight_offers=%d flight_status=%s flight_reason=%s "
        "hotels=%d attractions=%d restaurants=%d "
        "elapsed_ms=%d timed_out=%d",
        len(flight_offers), flight_search_status, flight_search_reason,
        len(hotels), len(attractions), len(restaurants),
        t_search_ms, len(_not_done),
    )

    # Step 4: AI scoring — hotels still use the legacy SearchService path.
    # Flight offers carry their own provider-sourced ranking; no points/CPP
    # scoring is applied to canonical offers in this slice.
    for hotel in hotels:
        hotel.ai_score = _compute_hotel_ai_score(hotel)
        hotel.recommendation_tag = _hotel_recommendation_tag(hotel, hotel.ai_score)

    _enrich_hotels_with_intelligence(hotels)

    flights_sorted: List[FlightResult] = []
    hotels_sorted = sorted(hotels, key=lambda h: h.ai_score or 0.0, reverse=True)

    # Fail-closed guard: refuse to persist mock-derived rows.
    # Canonical flight offers come from the registered FlightProvider seam and
    # cannot be mock-derived (FlightItineraryOffer + FlightBookingLink reject
    # fabricated hosts at construction time), so only hotels are screened here.
    if _any_mock_derived([], hotels_sorted, []):
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

    # 6a — Flights (canonical FlightItineraryOffer from active provider)
    t_persist_flights_start = time.perf_counter()
    _flights_persisted = 0
    for idx, offer in enumerate(flight_offers[:10]):
        try:
            itinerary_svc.create_trip_item(
                _offer_to_flight_item(offer, trip_id=trip.id, position=idx),
                user_id,
            )
            _flights_persisted += 1
        except Exception as _exc:
            logger.warning("[create_with_search.persist] vertical=flight idx=%d error=%s", idx, _exc)

    seeding["flights"] = {
        "harvested": len(flight_offers),
        "persisted": _flights_persisted,
        "status": flight_search_status,
        "reason": flight_search_reason or None,
    }
    logger.info(
        "[create_with_search.timing] phase=persist_flights harvested=%d persisted=%d status=%s elapsed_ms=%d",
        len(flight_offers), _flights_persisted, flight_search_status,
        int((time.perf_counter() - t_persist_flights_start) * 1000),
    )

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

    # 6c — Round-trip pairs (RETIRED)
    # Canonical FlightItineraryOffer rows already carry a `return_leg` when the
    # provider returned a round-trip itinerary, so a second pairing pass would
    # be a divergent third pathway.  Kept zeroed for response-shape compat.
    seeding["round_trip_pairs"] = {"harvested": 0, "persisted": 0}

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
        "elapsed_ms=%d",
        seeding["flights"]["harvested"], seeding["flights"]["persisted"],
        seeding["hotels"]["harvested"], seeding["hotels"]["persisted"],
        seeding["attractions"]["harvested"], seeding["attractions"]["persisted"],
        seeding["restaurants"]["harvested"], seeding["restaurants"]["persisted"],
        t_total_ms,
    )

    return TripWithResults(
        **trip.model_dump(),
        flights=flights_sorted,
        hotels=hotels_sorted,
        round_trip_pairs=[],
        seeding_status=seeding,
    )
