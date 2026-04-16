import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, status

logger = logging.getLogger(__name__)

from app.core.deps import DB
from app.models import (
    BookingOption,
    ItineraryDay,
    ItineraryDayCreate,
    ItineraryDayUpdate,
    ItineraryItem,
    ItineraryItemCreate,
    ItineraryItemDirectCreate,
    ItineraryItemUpdate,
)
from app.services import ItineraryService
from app.services.booking import generate_booking_links

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


@router.post(
    "/items",
    response_model=ItineraryItem,
    status_code=status.HTTP_201_CREATED,
)
def create_trip_item(payload: ItineraryItemDirectCreate, db: DB) -> ItineraryItem:
    """Add a trip-level item (e.g. a saved flight) without requiring a specific day."""
    logger.info("[create_trip_item] body: %s", payload.model_dump(mode="json"))
    return ItineraryService(db).create_trip_item(payload)


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


@router.get("/items/{item_id}/booking-links", response_model=List[BookingOption])
def get_booking_links(item_id: UUID, db: DB) -> List[BookingOption]:
    """Generate booking deep-links for an itinerary item.

    Returns provider-labelled URLs pre-filled with the item's type, title,
    location, and dates.  Existing booking options stored on the item are
    returned first, followed by any additional generated links.
    """
    item = ItineraryService(db).get_item(item_id)
    stored: List[BookingOption] = []
    if item.details and "booking_options" in item.details:
        stored = [BookingOption(**opt) for opt in item.details["booking_options"]]

    generated = generate_booking_links(item)
    # Merge: stored options first, then generated ones not already present
    seen_providers = {opt.provider for opt in stored}
    merged = stored + [opt for opt in generated if opt.provider not in seen_providers]
    return merged
