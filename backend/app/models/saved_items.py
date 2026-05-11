"""Pydantic models for the saved_items table (Stage 2A Slice 2)."""

from typing import Any, Dict, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

SavedItemVertical = Literal["restaurant", "attraction", "hotel", "flight"]
SavedItemStatus = Literal["active", "deleted"]

VALID_VERTICALS: frozenset = frozenset({"restaurant", "attraction", "hotel", "flight"})


class SavedItemCreate(BaseModel):
    vertical: SavedItemVertical
    display_name: str
    provider: Optional[str] = None
    # Place-based identity (Google Places — restaurants, attractions, hotels)
    provider_place_id: Optional[str] = None
    # Generic offer/itinerary/entity identity (flights, non-place providers)
    provider_item_id: Optional[str] = None
    display_snapshot: Dict[str, Any] = Field(default_factory=dict)
    search_context: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("display_name")
    @classmethod
    def display_name_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("display_name must not be blank")
        return v.strip()


class SavedItem(BaseModel):
    id: UUID
    user_id: UUID
    vertical: SavedItemVertical
    display_name: str
    provider: Optional[str] = None
    provider_place_id: Optional[str] = None
    provider_item_id: Optional[str] = None
    display_snapshot: Dict[str, Any] = Field(default_factory=dict)
    search_context: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    status: SavedItemStatus = "active"
    created_at: str
    updated_at: str
