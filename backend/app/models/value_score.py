"""Models for the Value Engine — inputs and outputs for scoring travel options."""

from typing import List, Optional

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
