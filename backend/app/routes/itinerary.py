from typing import List
from uuid import UUID

from fastapi import APIRouter, status

from app.core.deps import DB
from app.models import (
    ItineraryDay,
    ItineraryDayCreate,
    ItineraryDayUpdate,
    ItineraryItem,
    ItineraryItemCreate,
    ItineraryItemUpdate,
)
from app.services import ItineraryService

router = APIRouter(prefix="/itinerary", tags=["itinerary"])


# ------------------------------------------------------------------
# Days  —  /itinerary/{trip_id}/days
# ------------------------------------------------------------------

@router.get("/{trip_id}/days", response_model=List[ItineraryDay])
def list_days(trip_id: UUID, db: DB) -> List[ItineraryDay]:
    """Return all itinerary days for a trip, ordered by day_number."""
    return ItineraryService(db).list_days(trip_id)


@router.post(
    "/{trip_id}/days",
    response_model=ItineraryDay,
    status_code=status.HTTP_201_CREATED,
)
def create_day(trip_id: UUID, payload: ItineraryDayCreate, db: DB) -> ItineraryDay:
    """Add an itinerary day to a trip."""
    return ItineraryService(db).create_day(payload)


@router.get("/{trip_id}/days/{day_id}", response_model=ItineraryDay)
def get_day(trip_id: UUID, day_id: UUID, db: DB) -> ItineraryDay:
    """Fetch a single itinerary day."""
    return ItineraryService(db).get_day(day_id)


@router.patch("/{trip_id}/days/{day_id}", response_model=ItineraryDay)
def update_day(
    trip_id: UUID, day_id: UUID, payload: ItineraryDayUpdate, db: DB
) -> ItineraryDay:
    """Partially update an itinerary day."""
    return ItineraryService(db).update_day(day_id, payload)


@router.delete(
    "/{trip_id}/days/{day_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_day(trip_id: UUID, day_id: UUID, db: DB) -> None:
    """Delete an itinerary day and all its items."""
    ItineraryService(db).delete_day(day_id)


# ------------------------------------------------------------------
# Items  —  /itinerary/{trip_id}/days/{day_id}/items
# ------------------------------------------------------------------

@router.get(
    "/{trip_id}/days/{day_id}/items", response_model=List[ItineraryItem]
)
def list_items(trip_id: UUID, day_id: UUID, db: DB) -> List[ItineraryItem]:
    """Return all items for a day, ordered by position."""
    return ItineraryService(db).list_items(day_id)


@router.post(
    "/{trip_id}/days/{day_id}/items",
    response_model=ItineraryItem,
    status_code=status.HTTP_201_CREATED,
)
def create_item(
    trip_id: UUID, day_id: UUID, payload: ItineraryItemCreate, db: DB
) -> ItineraryItem:
    """Add an item (flight, hotel, activity…) to an itinerary day."""
    return ItineraryService(db).create_item(payload)


@router.get("/items/{item_id}", response_model=ItineraryItem)
def get_item(item_id: UUID, db: DB) -> ItineraryItem:
    """Fetch a single itinerary item."""
    return ItineraryService(db).get_item(item_id)


@router.patch("/items/{item_id}", response_model=ItineraryItem)
def update_item(
    item_id: UUID, payload: ItineraryItemUpdate, db: DB
) -> ItineraryItem:
    """Partially update an itinerary item."""
    return ItineraryService(db).update_item(item_id, payload)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: UUID, db: DB) -> None:
    """Remove an itinerary item."""
    ItineraryService(db).delete_item(item_id)
