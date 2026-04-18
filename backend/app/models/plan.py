from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class ClusterPlaceInput(BaseModel):
    id: str
    name: str
    place_type: str  # "attraction" | "restaurant"
    category: str
    address: str
    rating: Optional[float] = None
    ai_score: Optional[float] = None
    tags: List[str] = []
    lat: float = 0.0
    lng: float = 0.0
    booking_url: str = ""


class DayPlanRequest(BaseModel):
    trip_id: UUID
    day_number: int
    cluster_id: Optional[str] = None
    places: Optional[List[ClusterPlaceInput]] = None


class PlannedAttraction(BaseModel):
    id: str
    name: str
    category: str
    description: str
    location: str
    address: str
    rating: Optional[float] = None
    num_reviews: Optional[int] = None
    duration_minutes: Optional[int] = None
    ai_score: Optional[float] = None
    tags: List[str] = []
    price_level: Optional[int] = None
    opening_hours: Optional[str] = None
    booking_url: Optional[str] = None


class PlannedRestaurant(BaseModel):
    id: str
    name: str
    cuisine: str
    location: str
    address: str
    rating: Optional[float] = None
    num_reviews: Optional[int] = None
    ai_score: Optional[float] = None
    tags: List[str] = []
    price_level: Optional[int] = None
    opening_hours: Optional[str] = None
    booking_url: Optional[str] = None


class DayPlanResponse(BaseModel):
    trip_id: UUID
    day_number: int
    destination: str
    attractions: List[PlannedAttraction]
    lunch: PlannedRestaurant
    dinner: PlannedRestaurant
