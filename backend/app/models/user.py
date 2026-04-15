from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import EmailStr, Field

from .base import ORMBase, TimestampedBase


class UserBase(ORMBase):
    email: EmailStr
    full_name: Optional[str] = None
    home_airport: Optional[str] = Field(None, max_length=8)
    home_currency: str = "USD"
    preferences: Dict[str, Any] = Field(default_factory=dict)


class UserCreate(UserBase):
    id: UUID  # must match auth.users.id


class UserUpdate(ORMBase):
    full_name: Optional[str] = None
    home_airport: Optional[str] = None
    home_currency: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class User(UserBase, TimestampedBase):
    pass
