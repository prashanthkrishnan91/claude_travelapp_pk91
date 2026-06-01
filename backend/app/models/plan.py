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
    # Trip Item Metadata Parity v1.2: forward routeable coordinates from the
    # underlying AttractionResult / ClusterPlaceInput so that day-plan-accepted
    # places carry lat/lng into the persisted itinerary item. Without these,
    # `addAttractionToDay` writes `lat: null` and `computeAdjacentHints` emits
    # the honest fallback even when the source actually has coordinates.
    lat: Optional[float] = None
    lng: Optional[float] = None
    # Plan My Day Place Resolution v1: carry canonical Google place identity so
    # day-plan-accepted places match the Build/Concierge routeable metadata
    # contract (place_id + google_maps_uri) and so missing coordinates can be
    # resolved via the existing Google Places details path before persistence.
    place_id: Optional[str] = None
    google_maps_uri: Optional[str] = None


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
    # See PlannedAttraction.lat/lng — same routeable-metadata-parity contract.
    lat: Optional[float] = None
    lng: Optional[float] = None
    # Plan My Day Place Resolution v1 — see PlannedAttraction.place_id.
    place_id: Optional[str] = None
    google_maps_uri: Optional[str] = None


class DayPlanResponse(BaseModel):
    trip_id: UUID
    day_number: int
    destination: str
    attractions: List[PlannedAttraction]
    lunch: PlannedRestaurant
    dinner: PlannedRestaurant
