"""Search endpoints — /search/flights, /search/hotels, /search/attractions."""

from typing import List

from fastapi import APIRouter

from app.core.deps import DB
from app.models.search import (
    AttractionResult,
    AttractionSearchRequest,
    FlightResult,
    FlightSearchRequest,
    HotelResult,
    HotelSearchRequest,
)
from app.services.search import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/flights", response_model=List[FlightResult])
def search_flights(payload: FlightSearchRequest, db: DB) -> List[FlightResult]:
    """Search for available flights.

    Returns a list of flight options normalised to a consistent schema
    (price, points_estimate, rating, location, booking_url, source) plus
    flight-specific fields. Results are cached in Supabase for 1 hour.
    """
    return SearchService(db).search_flights(payload)


@router.post("/hotels", response_model=List[HotelResult])
def search_hotels(payload: HotelSearchRequest, db: DB) -> List[HotelResult]:
    """Search for available hotels.

    Returns a list of hotel options normalised to a consistent schema plus
    hotel-specific fields (name, stars, amenities, price_per_night, etc.).
    Results are cached in Supabase for 1 hour.
    """
    return SearchService(db).search_hotels(payload)


@router.post("/attractions", response_model=List[AttractionResult])
def search_attractions(payload: AttractionSearchRequest, db: DB) -> List[AttractionResult]:
    """Search for attractions, tours, and activities.

    Returns a list of attraction options normalised to a consistent schema plus
    attraction-specific fields (category, description, duration_minutes, address).
    Results are cached in Supabase for 1 hour.
    """
    return SearchService(db).search_attractions(payload)
