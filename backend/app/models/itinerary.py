from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import Field

from .base import ORMBase, TimestampedBase


class ItineraryItemType(str, Enum):
    FLIGHT = "flight"
    HOTEL = "hotel"
    ACTIVITY = "activity"
    TRANSIT = "transit"
    MEAL = "meal"
    NOTE = "note"


class BestOption(str, Enum):
    CASH = "cash"
    POINTS = "points"


# --- Itinerary Days ------------------------------------------------

class ItineraryDayBase(ORMBase):
    day_number: int = Field(..., ge=1)
    date: Optional[date] = None
    title: Optional[str] = None
    summary: Optional[str] = None


class ItineraryDayCreate(ItineraryDayBase):
    trip_id: UUID


class ItineraryDayUpdate(ORMBase):
    day_number: Optional[int] = Field(None, ge=1)
    date: Optional[date] = None
    title: Optional[str] = None
    summary: Optional[str] = None


class ItineraryDay(ItineraryDayBase, TimestampedBase):
    trip_id: UUID


# --- Itinerary Items -----------------------------------------------

class ItineraryItemBase(ORMBase):
    item_type: ItineraryItemType
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    # Pricing
    cash_price: Optional[Decimal] = None
    cash_currency: str = "USD"
    points_price: Optional[int] = None
    points_card_key: Optional[str] = None
    points_partner_key: Optional[str] = None
    cpp_value: Optional[Decimal] = Field(None, description="Realized cents-per-point")
    best_option: Optional[BestOption] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    position: int = 0


class ItineraryItemCreate(ItineraryItemBase):
    day_id: UUID
    trip_id: UUID


class ItineraryItemUpdate(ORMBase):
    item_type: Optional[ItineraryItemType] = None
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    cash_price: Optional[Decimal] = None
    cash_currency: Optional[str] = None
    points_price: Optional[int] = None
    points_card_key: Optional[str] = None
    points_partner_key: Optional[str] = None
    cpp_value: Optional[Decimal] = None
    best_option: Optional[BestOption] = None
    details: Optional[Dict[str, Any]] = None
    position: Optional[int] = None


class ItineraryItem(ItineraryItemBase, TimestampedBase):
    day_id: UUID
    trip_id: UUID
