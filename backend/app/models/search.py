"""Search request and normalized result models for flights, hotels, and attractions."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from .base import ORMBase


# ------------------------------------------------------------------
# Booking option — one provider link attached to a result or item
# ------------------------------------------------------------------

class BookingOption(BaseModel):
    """A single bookable link with provider label and deep-link URL."""

    provider: str = Field(..., description="Provider identifier, e.g. booking_com, chase_portal")
    url: str = Field(..., description="Deep-link URL to complete the booking")


# ------------------------------------------------------------------
# Normalized result — every search type maps into this shape
# ------------------------------------------------------------------

class SearchResult(BaseModel):
    """Normalized result returned for every search type."""

    id: str = Field(..., description="Provider-supplied or synthetic identifier")
    price: Optional[float] = Field(None, description="Cash price in USD")
    points_estimate: Optional[int] = Field(None, description="Estimated points cost")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Rating on a 0–5 scale")
    location: str = Field(..., description="Human-readable location string")
    booking_url: str = Field(..., description="Primary deep-link URL (first booking option)")
    source: str = Field(..., description="Data provider: mock | amadeus | google_flights | booking_com | viator")
    booking_options: List[BookingOption] = Field(default_factory=list, description="All available booking options with provider labels")


# ------------------------------------------------------------------
# Flight models
# ------------------------------------------------------------------

class FlightSearchRequest(BaseModel):
    # Single-airport form (legacy / direct IATA input)
    origin: Optional[str] = Field(None, min_length=3, max_length=3, description="IATA origin airport code")
    destination: Optional[str] = Field(None, min_length=3, max_length=3, description="IATA destination airport code")
    # Multi-airport form (city autocomplete resolves to a list)
    origin_airports: Optional[List[str]] = Field(None, description="Multiple origin IATA codes")
    destination_airports: Optional[List[str]] = Field(None, description="Multiple destination IATA codes")
    departure_date: date
    return_date: Optional[date] = None
    passengers: int = Field(1, ge=1, le=9)
    cabin_class: str = Field("economy", pattern="^(economy|premium_economy|business|first)$")

    @property
    def all_origins(self) -> List[str]:
        if self.origin_airports:
            return [c.upper() for c in self.origin_airports]
        return [self.origin.upper()] if self.origin else []

    @property
    def all_destinations(self) -> List[str]:
        if self.destination_airports:
            return [c.upper() for c in self.destination_airports]
        return [self.destination.upper()] if self.destination else []


class FlightResult(SearchResult):
    airline: str
    flight_number: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    stops: int = 0
    cabin_class: str
    points_cost: int = Field(0, description="Points required to book via award redemption")
    cpp: float = Field(0.0, description="Cents per point redemption value")
    recommendation_tag: str = Field("Better with Cash", description="Value recommendation tag")
    ai_score: Optional[float] = Field(None, description="AI-computed value score 0–100")
    decision: str = Field("Cash Better", description="Points Better | Cash Better")
    tags: List[str] = Field(default_factory=list, description="Multi-tag classification e.g. Best Value, Non-stop, Cheapest")
    savings_vs_best: Optional[float] = Field(None, description="Price delta vs cheapest option in dataset (positive = costs more)")
    explanation: str = Field("", description="One-line decision context shown to user")


class RoundTripFlightPair(BaseModel):
    """A paired outbound + return flight combination with combined pricing."""

    id: str
    outbound: FlightResult
    return_flight: FlightResult
    total_price: float = Field(..., description="Sum of outbound + return cash prices in USD")
    total_points: int = Field(..., description="Sum of outbound + return points costs")
    combined_cpp: float = Field(..., description="Cents per point for the combined pair")
    total_duration_minutes: int = Field(..., description="Sum of outbound + return flight durations")


# ------------------------------------------------------------------
# Hotel models
# ------------------------------------------------------------------

class HotelSearchRequest(BaseModel):
    location: str = Field(..., min_length=2, description="City, region, or address")
    check_in: date
    check_out: date
    guests: int = Field(1, ge=1, le=20)
    max_price: Optional[float] = Field(None, gt=0, description="Maximum nightly rate in USD")


class HotelResult(SearchResult):
    name: str
    check_in: date
    check_out: date
    nights: int
    stars: Optional[float] = Field(None, ge=1, le=5)
    amenities: List[str] = Field(default_factory=list)
    price_per_night: float
    ai_score: Optional[float] = Field(None, description="AI-computed value score 0–100")
    recommendation_tag: str = Field("Consider", description="Value recommendation tag")
    tags: List[str] = Field(default_factory=list, description="Multi-tag classification e.g. Best Value, Luxury Pick, Budget Friendly")
    savings_vs_best: Optional[float] = Field(None, description="Price/night delta vs cheapest option in dataset")
    explanation: str = Field("", description="One-line decision context shown to user")


# ------------------------------------------------------------------
# Attraction models
# ------------------------------------------------------------------

class AttractionSearchRequest(BaseModel):
    location: str = Field(..., min_length=2, description="City or region to search in")
    category: Optional[str] = Field(
        None,
        description="Filter by category: museums | outdoor | food | nightlife | tours | shopping",
    )
    date: Optional[date] = None


class AttractionResult(SearchResult):
    name: str
    category: str
    description: str
    duration_minutes: Optional[int] = None
    address: str
    ai_score: Optional[float] = Field(None, description="AI-computed relevance score 0–100")
    tags: List[str] = Field(default_factory=list, description="Tags: Must Visit, Highly Rated, Hidden Gem, Tourist Favorite")
    num_reviews: Optional[int] = Field(None, description="Number of user reviews")
    opening_hours: Optional[str] = Field(None, description="Opening hours summary")
    price_level: Optional[int] = Field(None, ge=0, le=4, description="Price level 0=free, 1=inexpensive, 2=moderate, 3=expensive, 4=very expensive")
    lat: Optional[float] = Field(None, description="Latitude coordinate")
    lng: Optional[float] = Field(None, description="Longitude coordinate")


# ------------------------------------------------------------------
# Restaurant models
# ------------------------------------------------------------------

class RestaurantSearchRequest(BaseModel):
    location: str = Field(..., min_length=2, description="City or region to search in")
    cuisine: Optional[str] = Field(None, description="Filter by cuisine type")
    date: Optional[date] = None


class RestaurantResult(SearchResult):
    name: str
    cuisine: str
    address: str
    ai_score: Optional[float] = Field(None, description="AI-computed value score 0–100")
    tags: List[str] = Field(default_factory=list, description="Tags: Local Favorite, Fine Dining, Budget Friendly, Must Try")
    num_reviews: Optional[int] = Field(None, description="Number of user reviews")
    opening_hours: Optional[str] = Field(None, description="Opening hours summary")
    price_level: Optional[int] = Field(None, ge=0, le=4, description="Price level 0=free, 1=inexpensive, 2=moderate, 3=expensive, 4=very expensive")
    sentiment: Optional[float] = Field(None, ge=0, le=1, description="Sentiment score 0–1 derived from review analysis")
    lat: Optional[float] = Field(None, description="Latitude coordinate")
    lng: Optional[float] = Field(None, description="Longitude coordinate")


# ------------------------------------------------------------------
# Proximity cluster models
# ------------------------------------------------------------------

class ClusterSearchRequest(BaseModel):
    location: str = Field(..., min_length=2, description="City or region to cluster places for")
    radius_km: float = Field(1.5, ge=0.5, le=5.0, description="Cluster radius in kilometres")


class PlaceInCluster(BaseModel):
    id: str
    name: str
    place_type: str = Field(..., description="attraction | restaurant")
    category: str
    address: str
    rating: Optional[float] = None
    ai_score: Optional[float] = None
    tags: List[str] = Field(default_factory=list)
    lat: float
    lng: float
    booking_url: str
    booking_options: List[BookingOption] = Field(default_factory=list)


class LocationCluster(BaseModel):
    cluster_id: str
    area_name: str
    label: str = Field(..., description="Walkable cluster | 5 min apart | 10 min apart")
    center_lat: float
    center_lng: float
    places: List[PlaceInCluster]


# ------------------------------------------------------------------
# Generic cache wrapper stored in research_cache
# ------------------------------------------------------------------

class SearchCacheEntry(ORMBase):
    id: UUID
    cache_key: str
    source: str
    query: Dict[str, Any]
    payload: Dict[str, Any]
    expires_at: Optional[datetime] = None
    created_at: datetime
