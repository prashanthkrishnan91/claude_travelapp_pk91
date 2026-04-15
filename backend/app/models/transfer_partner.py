from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import Field

from .base import ORMBase, TimestampedBase


class PartnerType(str, Enum):
    AIRLINE = "airline"
    HOTEL = "hotel"


class TransferPartnerBase(ORMBase):
    card_key: str
    partner_key: str
    partner_name: str
    partner_type: PartnerType
    transfer_ratio: Decimal = Field(Decimal("1.0"), description="1.0 = 1:1")
    min_transfer: int = 1000
    transfer_bonus: Optional[Decimal] = Field(None, description="e.g. 0.25 for +25%")
    notes: Optional[str] = None
    is_active: bool = True


class TransferPartnerCreate(TransferPartnerBase):
    pass


class TransferPartnerUpdate(ORMBase):
    partner_name: Optional[str] = None
    partner_type: Optional[PartnerType] = None
    transfer_ratio: Optional[Decimal] = None
    min_transfer: Optional[int] = None
    transfer_bonus: Optional[Decimal] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class TransferPartner(TransferPartnerBase, TimestampedBase):
    pass
