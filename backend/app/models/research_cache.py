from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import Field

from .base import ORMBase


class ResearchCacheBase(ORMBase):
    cache_key: str
    source: str = Field(..., examples=["amadeus", "google_flights", "claude", "manual"])
    query: Dict[str, Any]
    payload: Dict[str, Any]
    expires_at: Optional[datetime] = None


class ResearchCacheCreate(ResearchCacheBase):
    pass


class ResearchCache(ResearchCacheBase):
    id: UUID
    created_at: datetime
