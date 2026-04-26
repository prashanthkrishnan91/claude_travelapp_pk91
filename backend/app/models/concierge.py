"""Pydantic models for the AI concierge endpoint."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class ConciergeRequest(BaseModel):
    trip_id: UUID
    user_query: str
    day_number: Optional[int] = None


class Suggestion(BaseModel):
    type: Literal["attraction", "restaurant"]
    name: str
    reason: str


class ConciergeResponse(BaseModel):
    response: str
    suggestions: List[Suggestion]


# ── Intent constants ──────────────────────────────────────────────────────────

INTENT_MICHELIN_RESTAURANTS = "michelin_restaurants"
INTENT_RESTAURANTS = "restaurants"
INTENT_HIDDEN_GEMS = "hidden_gems"
INTENT_LUXURY_VALUE = "luxury_value"
INTENT_ROMANTIC = "romantic"
INTENT_FAMILY_FRIENDLY = "family_friendly"
INTENT_NIGHTLIFE = "nightlife"
INTENT_ATTRACTIONS = "attractions"
INTENT_HOTELS = "hotels"
INTENT_BEST_AREA = "best_area"
INTENT_PLAN_DAY = "plan_day"
INTENT_COMPARE = "compare"
INTENT_REWARDS_HELP = "rewards"
INTENT_GENERAL_DESTINATION = "general_destination_research"
INTENT_GENERAL = "general"

# Legacy aliases kept for backward compatibility
INTENT_ITINERARY_HELP = INTENT_PLAN_DAY
INTENT_AREA_ADVICE = INTENT_BEST_AREA

# ── Source status constants ───────────────────────────────────────────────────

SOURCE_CONFIRMED_MICHELIN = "confirmed_michelin"
SOURCE_CURATED_STATIC = "curated_static"
SOURCE_LIVE_SEARCH = "live_search"
SOURCE_APP_DATABASE = "app_database"
SOURCE_SAMPLE_DATA = "sample_data"
SOURCE_MIXED = "mixed"
SOURCE_UNAVAILABLE = "unavailable"
SOURCE_NONE = "none"

# ── Retrieval-first result models ─────────────────────────────────────────────

class GoogleVerification(BaseModel):
    """Normalized Google Places verification record attached to addable cards."""

    provider: Literal["google_places"] = "google_places"
    provider_place_id: Optional[str] = None
    name: Optional[str] = None
    formatted_address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    business_status: Optional[str] = None
    google_maps_uri: Optional[str] = None
    website_uri: Optional[str] = None
    rating: Optional[float] = None
    user_rating_count: Optional[int] = None
    types: List[str] = []
    confidence: Literal["high", "medium", "low", "unknown"] = "unknown"
    failure_reason: Optional[str] = None


class UnifiedRestaurantResult(BaseModel):
    type: Literal["verified_place"] = "verified_place"
    name: str
    source: str = "Michelin Guide"
    michelin_status: Optional[str] = None  # "3 Stars" | "2 Stars" | "1 Star" | "Bib Gourmand" | "Selected"
    cuisine: str
    neighborhood: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    summary: Optional[str] = None
    booking_link: Optional[str] = None
    maps_link: Optional[str] = None
    source_url: Optional[str] = None
    last_verified_at: Optional[str] = None
    confidence: Optional[Literal["high", "medium", "low", "unknown"]] = None
    ai_score: Optional[float] = None
    tags: List[str] = []
    verified_place: Optional[bool] = None
    google_verification: Optional[GoogleVerification] = None


class UnifiedAttractionResult(BaseModel):
    type: Literal["verified_place"] = "verified_place"
    name: str
    source: str = "Search"
    category: str
    description: Optional[str] = None
    neighborhood: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    address: Optional[str] = None
    maps_link: Optional[str] = None
    source_url: Optional[str] = None
    last_verified_at: Optional[str] = None
    confidence: Optional[Literal["high", "medium", "low", "unknown"]] = None
    ai_score: Optional[float] = None
    tags: List[str] = []
    verified_place: Optional[bool] = None
    google_verification: Optional[GoogleVerification] = None


class UnifiedHotelResult(BaseModel):
    type: Literal["verified_place"] = "verified_place"
    name: str
    source: str = "Search"
    area_label: Optional[str] = None
    stars: Optional[float] = None
    rating: Optional[float] = None
    price_per_night: Optional[float] = None
    maps_link: Optional[str] = None
    booking_url: Optional[str] = None
    source_url: Optional[str] = None
    last_verified_at: Optional[str] = None
    confidence: Optional[Literal["high", "medium", "low", "unknown"]] = None
    reason: Optional[str] = None
    ai_score: Optional[float] = None
    tags: List[str] = []
    verified_place: Optional[bool] = None
    google_verification: Optional[GoogleVerification] = None


class UnifiedResearchSourceResult(BaseModel):
    type: Literal["research_source"] = "research_source"
    title: str
    source: str = "Live search"
    source_type: Literal["article_listicle_blog_directory", "neighborhood_area", "generic_info_source"] = "generic_info_source"
    summary: Optional[str] = None
    source_url: Optional[str] = None
    neighborhood: Optional[str] = None
    last_verified_at: Optional[str] = None
    confidence: Optional[Literal["high", "medium", "low", "unknown"]] = None
    trip_addable: bool = False


class UnifiedAreaComparisonResult(BaseModel):
    area: str
    vibe: str
    best_for: str
    pros: List[str] = []
    cons: List[str] = []
    logistics: str
    value_signal: str
    recommendation: str
    source_url: Optional[str] = None
    last_verified_at: Optional[str] = None


# ── Request / Response ────────────────────────────────────────────────────────

class ConciergeSearchRequest(BaseModel):
    trip_id: UUID
    user_query: str
    client_message_id: Optional[str] = None


class ConciergeCacheClearRequest(BaseModel):
    trip_id: UUID
    destination: Optional[str] = None


class ConciergeCacheClearResponse(BaseModel):
    cleared: bool = True


class ConciergeSearchResponse(BaseModel):
    response: str
    intent: str
    retrieval_used: bool = False
    source_status: str = SOURCE_NONE
    cached: bool = False
    live_provider: Optional[str] = None
    restaurants: List[UnifiedRestaurantResult] = []
    attractions: List[UnifiedAttractionResult] = []
    hotels: List[UnifiedHotelResult] = []
    research_sources: List[UnifiedResearchSourceResult] = []
    areas: List[str] = []
    area_comparisons: List[UnifiedAreaComparisonResult] = []
    suggestions: List[Suggestion] = []
    sources: List[str] = []
    warnings: List[str] = []


class ConciergeMessage(BaseModel):
    id: UUID
    trip_id: UUID
    client_message_id: Optional[str] = None
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    structured_results: Optional[Dict[str, Any]] = None
    created_at: datetime
