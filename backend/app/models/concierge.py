"""Pydantic models for the AI concierge endpoint."""

from typing import List, Literal, Optional
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


# ── Retrieval-first models ────────────────────────────────────────────────────

INTENT_MICHELIN_RESTAURANTS = "michelin_restaurants"
INTENT_RESTAURANTS = "restaurants"
INTENT_ATTRACTIONS = "attractions"
INTENT_HOTELS = "hotels"
INTENT_ITINERARY_HELP = "itinerary_help"
INTENT_AREA_ADVICE = "area_advice"
INTENT_REWARDS_HELP = "rewards_help"
INTENT_GENERAL = "general"


class UnifiedRestaurantResult(BaseModel):
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
    ai_score: Optional[float] = None
    tags: List[str] = []


class ConciergeSearchRequest(BaseModel):
    trip_id: UUID
    user_query: str


class ConciergeSearchResponse(BaseModel):
    response: str
    intent: str
    restaurants: List[UnifiedRestaurantResult] = []
    suggestions: List[Suggestion] = []
