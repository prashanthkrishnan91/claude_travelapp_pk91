"""Models for the Value Engine — inputs and outputs for scoring travel options."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ValueScoreRequest(BaseModel):
    """Inputs required to compute a value score for a single travel option."""

    cash_price: float = Field(..., ge=0, description="Cash price in USD")
    points_estimate: int = Field(..., ge=0, description="Estimated points cost")
    transfer_partners: int = Field(0, ge=0, description="Number of transfer partners available")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Rating on a 0–5 scale")
    location: Optional[str] = Field(None, description="Human-readable location string")


class ValueScoreResult(BaseModel):
    """Computed value metrics for a travel option."""

    cpp: Optional[float] = Field(
        None,
        description="Cents per point — (cash_price × 100) / points_estimate; null when points_estimate is 0",
    )
    value_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Composite value score (0–100) weighting CPP, rating, and transfer partner availability",
    )
    tags: List[str] = Field(
        default_factory=list,
        description='Applicable quality tags: "Best Value", "Best Points", "Luxury Pick"',
    )


class BatchValueScoreRequest(BaseModel):
    """Score up to 50 travel options in a single request."""

    items: List[ValueScoreRequest] = Field(..., min_length=1, max_length=50)


class BatchValueScoreResponse(BaseModel):
    """Scored results returned in the same order as the input items."""

    results: List[ValueScoreResult]


# ---------------------------------------------------------------------------
# Value Engine V2 — personalized scoring models
# ---------------------------------------------------------------------------

class ItemV2(BaseModel):
    """A flight or hotel to be scored by Value Engine V2."""

    item_type: str = Field(..., description="'flight' or 'hotel'")
    name: str = Field(..., description="Airline or hotel brand name")
    cash_price: float = Field(..., ge=0, description="Cash price in USD")
    points_cost: int = Field(..., ge=0, description="Points required for this redemption")
    layovers: Optional[int] = Field(None, ge=0, description="Number of layovers (flights only)")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Quality rating 0–5")
    seat_class: Optional[str] = Field(None, description="Seat class: economy/business/first (flights only)")
    hotel_class: Optional[int] = Field(None, ge=1, le=5, description="Star rating 1–5 (hotels only)")


class UserCardV2(BaseModel):
    """A user's card provided as scoring context."""

    card_key: str
    issuer: str
    display_name: Optional[str] = Field(None, description="Human-readable card name for display")
    points_balance: int = Field(..., ge=0)
    point_value_cpp: Optional[float] = Field(None, ge=0, description="User's CPP valuation for this card")
    earn_rate: Optional[float] = Field(
        None, ge=0, description="Default earn multiplier (e.g. 3.0 for 3x, 5.0 for 5x)"
    )
    category_earn_rates: Optional[Dict[str, float]] = Field(
        None, description="Per-category earn rates keyed by 'travel', 'dining', 'other'"
    )


class UserPreferencesV2(BaseModel):
    """User travel preferences for V2 scoring context."""

    preferred_airlines: List[str] = Field(default_factory=list)
    preferred_hotels: List[str] = Field(default_factory=list)
    max_layovers: int = Field(2, ge=0, description="Maximum acceptable layovers")
    seat_class: str = Field("economy", description="Preferred seat class")
    hotel_class: int = Field(3, ge=1, le=5, description="Preferred hotel star rating")
    cpp_baseline: float = Field(1.8, gt=0, description="User's CPP baseline for value comparison")


class TransferBonusV2(BaseModel):
    """An active transfer bonus between an issuer and a loyalty partner."""

    issuer: str
    partner: str
    bonus_percent: int = Field(..., ge=0, description="Bonus percentage, e.g. 25 for +25%")


class BestCardRecommendation(BaseModel):
    """Card recommendation with category-specific earn rate and expected reward value."""

    card_key: str
    display_name: str
    earn_rate: float = Field(..., description="Category earn multiplier (e.g. 5.0 for 5x)")
    expected_points: int = Field(..., description="Expected points earned on this purchase")
    expected_value_usd: float = Field(
        ..., description="Dollar value of expected points at user's CPP baseline"
    )


class ValueEngineV2Request(BaseModel):
    """Full context for Value Engine V2 scoring."""

    item: ItemV2
    user_cards: List[UserCardV2] = Field(default_factory=list)
    user_preferences: UserPreferencesV2 = Field(default_factory=UserPreferencesV2)
    transfer_bonuses: List[TransferBonusV2] = Field(
        default_factory=list,
        description="Active transfer bonuses (sourced from transfer_bonuses table)",
    )


class ValueEngineV2Result(BaseModel):
    """V2 scoring result with adjusted CPP, value score, tags, recommendation reason, and decision."""

    cpp: Optional[float] = Field(None, description="Base cents-per-point before any bonus")
    adjusted_cpp: Optional[float] = Field(
        None, description="CPP after applying best available transfer bonus"
    )
    value_score: int = Field(..., ge=0, le=100, description="Composite value score 0–100")
    decision: str = Field(
        ..., description="Payment recommendation: 'Points Better' or 'Cash Better'"
    )
    confidence: int = Field(
        ..., ge=0, le=100,
        description="Confidence in the recommendation (0–100): high ≥70, medium 40–69, low <40",
    )
    tags: List[str] = Field(default_factory=list, description="Applicable quality labels")
    recommendation_reason: str = Field(..., description="Structured explanation of the score")
    tradeoffs: List[str] = Field(
        default_factory=list,
        description="'Why not' tradeoffs — layover penalties, poor CPP, high opportunity cost, etc.",
    )
    effective_cash_cost: Optional[float] = Field(
        None, description="Cash price after accounting for rewards earned (USD)"
    )
    opportunity_cost: Optional[float] = Field(
        None, description="Dollar value of points you'd earn by paying cash instead (earn loss when using points)"
    )
    best_card: Optional[BestCardRecommendation] = Field(
        None, description="Best card recommendation with earn rate and expected reward value"
    )
    transfer_partner: Optional[str] = Field(
        None, description="Transfer partner name used for the best bonus, or null if none applicable"
    )


# ---------------------------------------------------------------------------
# Compare models — POST /compare
# ---------------------------------------------------------------------------

class CompareItemInput(BaseModel):
    """A single item submitted for side-by-side comparison."""

    id: str = Field(..., description="Client-side ID for correlating results")
    name: str = Field(..., description="Display name of the item")
    item_type: str = Field(..., description="Item type: flight, hotel, activity, etc.")
    cash_price: float = Field(0, ge=0, description="Cash price in USD")
    points_cost: int = Field(0, ge=0, description="Points cost for redemption")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Quality rating 0–5")
    layovers: Optional[int] = Field(None, ge=0, description="Number of layovers (flights only)")


class CompareRequest(BaseModel):
    """Request body for POST /compare."""

    items: List[CompareItemInput] = Field(..., min_length=2, max_length=10)
    user_preferences: UserPreferencesV2 = Field(default_factory=UserPreferencesV2)


class CompareResult(BaseModel):
    """Scored result for a single compared item."""

    id: str
    name: str
    type: str
    price: float
    points: int
    cpp: Optional[float]
    value_score: int
    tags: List[str]
    recommendation_reason: str


class CompareResponse(BaseModel):
    """Response body for POST /compare."""

    results: List[CompareResult]
