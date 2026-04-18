"""Search endpoints — /search/flights, /search/hotels, /search/attractions."""

import logging
from typing import List

from fastapi import APIRouter

from app.core.deps import DB
from app.models.search import (
    AttractionResult,
    AttractionSearchRequest,
    BestAreaRecommendation,
    BestAreaRequest,
    ClusterSearchRequest,
    FlightResult,
    FlightSearchRequest,
    HotelResult,
    HotelSearchRequest,
    LocationCluster,
    RestaurantResult,
    RestaurantSearchRequest,
    RoundTripFlightPair,
)
from typing import Optional

from app.services.search import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/flights", response_model=List[FlightResult])
def search_flights(payload: FlightSearchRequest, db: DB) -> List[FlightResult]:
    """Search for available flights.

    Returns a list of flight options normalised to a consistent schema
    (price, points_estimate, rating, location, booking_url, source) plus
    flight-specific fields. Results are cached in Supabase for 1 hour.
    """
    logger.info(
        "[search_flights] received request: origin=%s destination=%s departure_date=%s passengers=%d cabin_class=%s",
        payload.origin,
        payload.destination,
        payload.departure_date,
        payload.passengers,
        payload.cabin_class,
    )
    return SearchService(db).search_flights(payload)


@router.post("/round-trip-flights", response_model=List[RoundTripFlightPair])
def search_round_trip_flights(payload: FlightSearchRequest, db: DB) -> List[RoundTripFlightPair]:
    """Search for round-trip flight pairs.

    Requires ``return_date`` in the payload. Returns pairs ranked by combined
    CPP (desc), total price (asc), and total duration (asc).
    """
    logger.info(
        "[search_round_trip_flights] origin=%s destination=%s departure=%s return=%s",
        payload.origin,
        payload.destination,
        payload.departure_date,
        payload.return_date,
    )
    return SearchService(db).search_round_trip_flights(payload)


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


@router.post("/restaurants", response_model=List[RestaurantResult])
def search_restaurants(payload: RestaurantSearchRequest, db: DB) -> List[RestaurantResult]:
    """Search for restaurants, cafes, and local dining options.

    Returns a list of dining options sorted by AI score (rating, review count,
    price level, sentiment). Covers restaurants, cafes, and local dining.
    Results are cached in Supabase for 1 hour.
    """
    logger.info("[search_restaurants] location=%s cuisine=%s", payload.location, payload.cuisine)
    return SearchService(db).search_restaurants(payload)


@router.post("/clusters", response_model=List[LocationCluster])
def search_clusters(payload: ClusterSearchRequest, db: DB) -> List[LocationCluster]:
    """Group attractions and restaurants by proximity.

    Returns location clusters where each cluster contains nearby attractions
    and restaurants. Each cluster includes an area name and a walkability label
    (e.g. 'Walkable cluster', '5 min apart').
    """
    logger.info("[search_clusters] location=%s radius_km=%.1f", payload.location, payload.radius_km)
    return SearchService(db).search_clusters(payload)


@router.post("/best-area", response_model=Optional[BestAreaRecommendation])
def get_best_area(payload: BestAreaRequest, db: DB) -> Optional[BestAreaRecommendation]:
    """Recommend the best neighborhood to stay for a destination.

    Scores clusters by density (40%), average rating (35%), and centrality (25%).
    Returns the top-scored cluster with a human-readable reason and composite score.
    """
    logger.info("[get_best_area] location=%s radius_km=%.1f", payload.location, payload.radius_km)
    return SearchService(db).get_best_area(payload)
