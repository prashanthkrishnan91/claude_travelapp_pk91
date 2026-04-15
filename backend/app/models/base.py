from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    """Base model for rows read from Supabase."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TimestampedBase(ORMBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
