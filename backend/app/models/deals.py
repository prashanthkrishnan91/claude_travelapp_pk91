"""Models for the Deals Feed endpoint."""

from typing import List

from pydantic import BaseModel, Field


class DealFeedItem(BaseModel):
    """A single high-value deal surfaced from the research cache."""

    item_id: str = Field(..., description="Source item ID from the research cache")
    title: str = Field(..., description="Display name of the deal")
    description: str = Field(..., description="Short description or value summary")
    value_score: int = Field(..., ge=0, le=100, description="Composite value score 0–100")
    tags: List[str] = Field(default_factory=list, description='e.g. "Best Value", "Best Points"')


class DealsFeedResponse(BaseModel):
    """Response envelope for GET /deals/feed."""

    deals: List[DealFeedItem]
