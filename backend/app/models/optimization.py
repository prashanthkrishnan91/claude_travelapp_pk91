"""Models for the Trip Optimization Engine."""

from typing import List, Optional

from pydantic import BaseModel, Field

from .value_score import TransferBonusV2, UserCardV2, UserPreferencesV2


class FlightInput(BaseModel):
    """Flight candidate submitted for optimization scoring."""

    id: str
    airline: str
    flight_number: str
    price: float = Field(..., ge=0, description="Cash price in USD")
    points_cost: int = Field(0, ge=0, description="Points required to book via award")
    cpp: float = Field(0.0, description="Cents per point for this flight")
    duration_minutes: int = Field(..., ge=0)
    stops: int = Field(0, ge=0)
    cabin_class: str = Field("economy", description="economy|premium_economy|business|first")
    rating: Optional[float] = Field(None, ge=0, le=5)
    decision: str = Field("Cash Better", description="Points Better | Cash Better")
    tags: List[str] = Field(default_factory=list)
    explanation: str = ""


class HotelInput(BaseModel):
    """Hotel candidate submitted for optimization scoring."""

    id: str
    name: str
    price: float = Field(..., ge=0, description="Total cash price for the full stay in USD")
    price_per_night: float = Field(..., ge=0)
    nights: int = Field(1, ge=1)
    points_estimate: int = Field(0, ge=0, description="Estimated points cost for the stay")
    rating: Optional[float] = Field(None, ge=0, le=5)
    stars: Optional[float] = Field(None, ge=1, le=5)
    location_score: Optional[float] = Field(None, ge=0, le=100, description="Proximity score to top area")
    area_label: Optional[str] = Field(None, description="e.g. 'In Best Area', 'Near Top Attractions'")
    tags: List[str] = Field(default_factory=list)
    explanation: str = ""


class TripOptimizationRequest(BaseModel):
    """Full input for the trip optimization engine."""

    flights: List[FlightInput] = Field(..., min_length=1, max_length=50)
    hotels: List[HotelInput] = Field(..., min_length=1, max_length=50)
    user_cards: List[UserCardV2] = Field(default_factory=list)
    user_preferences: UserPreferencesV2 = Field(default_factory=UserPreferencesV2)
    transfer_bonuses: List[TransferBonusV2] = Field(default_factory=list)


class TripOption(BaseModel):
    """A ranked flight + hotel combination with composite scoring breakdown."""

    rank: int = Field(..., ge=1, le=3, description="1 = best")
    flight: FlightInput
    hotel: HotelInput
    total_cost: float = Field(..., description="flight.price + hotel.price in USD")
    total_points: int = Field(..., description="flight.points_cost + hotel.points_estimate")
    flight_score: float = Field(..., ge=0, le=100, description="Composite flight score 0–100")
    hotel_score: float = Field(..., ge=0, le=100, description="Composite hotel score 0–100")
    rewards_efficiency: float = Field(..., ge=0, le=100, description="Points/CPP efficiency score 0–100")
    total_value_score: float = Field(..., ge=0, le=100, description="Weighted trip score (40/40/20)")
    summary: str = Field(..., description="One-line human-readable summary for this option")


class TripOptimizationResponse(BaseModel):
    """Top 3 trip combinations ranked by total value score."""

    best_options: List[TripOption]
