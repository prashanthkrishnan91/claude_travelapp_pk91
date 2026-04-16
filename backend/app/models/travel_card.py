from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import Field

from .base import ORMBase, TimestampedBase


class TravelCardBase(ORMBase):
    card_key: str = Field(..., examples=["amex_gold", "bilt", "venture_x"])
    display_name: str
    issuer: str
    currency: str = "USD"
    points_balance: int = 0
    point_value_cpp: Optional[Decimal] = Field(None, description="User's cents-per-point valuation")
    is_primary: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TravelCardCreate(TravelCardBase):
    user_id: Optional[UUID] = None


class TravelCardUpdate(ORMBase):
    display_name: Optional[str] = None
    issuer: Optional[str] = None
    currency: Optional[str] = None
    points_balance: Optional[int] = None
    point_value_cpp: Optional[Decimal] = None
    is_primary: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class TravelCard(TravelCardBase, TimestampedBase):
    user_id: UUID
