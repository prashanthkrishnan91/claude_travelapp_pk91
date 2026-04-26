"""Typed response contracts for Concierge API endpoints."""

from typing import Annotated, Any, Dict, List, Literal, Union

from pydantic import BaseModel, Field

from app.models.concierge import ConciergeSearchResponse, Suggestion


class PlaceRecommendationsResponse(ConciergeSearchResponse):
    response_type: Literal["place_recommendations"] = "place_recommendations"


class TripAdviceResponse(BaseModel):
    response_type: Literal["trip_advice"] = "trip_advice"
    response: str
    suggestions: List[Suggestion] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UnsupportedResponse(BaseModel):
    response_type: Literal["unsupported"] = "unsupported"
    code: str
    message: str


ConciergeTypedResponse = Annotated[
    Union[PlaceRecommendationsResponse, TripAdviceResponse, UnsupportedResponse],
    Field(discriminator="response_type"),
]
