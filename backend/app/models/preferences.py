"""Pydantic models for user_preferences and transfer_bonuses DB tables."""

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UserPreferences(BaseModel):
    model_config = {"from_attributes": True}

    user_id: UUID
    preferred_airlines: List[str] = Field(default_factory=list)
    preferred_hotels: List[str] = Field(default_factory=list)
    max_layovers: int = 2
    seat_class: str = "economy"
    hotel_class: int = Field(3, ge=1, le=5)
    cpp_baseline: float = Field(1.8, gt=0)
    created_at: datetime
    updated_at: datetime


class UserPreferencesCreate(BaseModel):
    user_id: UUID
    preferred_airlines: List[str] = Field(default_factory=list)
    preferred_hotels: List[str] = Field(default_factory=list)
    max_layovers: int = Field(2, ge=0)
    seat_class: str = "economy"
    hotel_class: int = Field(3, ge=1, le=5)
    cpp_baseline: float = Field(1.8, gt=0)


class UserPreferencesUpdate(BaseModel):
    preferred_airlines: Optional[List[str]] = None
    preferred_hotels: Optional[List[str]] = None
    max_layovers: Optional[int] = Field(None, ge=0)
    seat_class: Optional[str] = None
    hotel_class: Optional[int] = Field(None, ge=1, le=5)
    cpp_baseline: Optional[float] = Field(None, gt=0)


class TransferBonus(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    issuer: str
    partner: str
    bonus_percent: int = Field(..., ge=0)
    start_date: date
    end_date: date
    created_at: datetime
    updated_at: datetime


class TransferBonusCreate(BaseModel):
    issuer: str
    partner: str
    bonus_percent: int = Field(..., ge=0)
    start_date: date
    end_date: date
