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
