from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import Field, model_validator

from .base import ORMBase, TimestampedBase


class TripStatus(str, Enum):
    DRAFT = "draft"
    RESEARCHING = "researching"
    PLANNED = "planned"
    BOOKED = "booked"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TripBase(ORMBase):
    title: str
    destination: str
    origin: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    travelers: int = Field(1, ge=1)
    budget_cash: Optional[Decimal] = None
    budget_currency: str = "USD"
    status: TripStatus = TripStatus.DRAFT
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class TripCreate(TripBase):
    user_id: Optional[UUID] = None


class TripUpdate(ORMBase):
    title: Optional[str] = None
    destination: Optional[str] = None
    origin: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    travelers: Optional[int] = Field(None, ge=1)
    budget_cash: Optional[Decimal] = None
    budget_currency: Optional[str] = None
    status: Optional[TripStatus] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Trip(TripBase, TimestampedBase):
    user_id: UUID
