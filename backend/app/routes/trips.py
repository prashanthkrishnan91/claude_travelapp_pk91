from typing import List
from uuid import UUID

from fastapi import APIRouter, status

from app.core.deps import DB, CurrentUserID
from app.models import Trip, TripCreate, TripUpdate, ItineraryItem
from app.services import TripsService
from app.services.itinerary import ItineraryService

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("", response_model=List[Trip])
def list_trips(db: DB, user_id: CurrentUserID) -> List[Trip]:
    """Return all trips belonging to the authenticated user."""
    return TripsService(db).list_trips(user_id)


@router.post("", response_model=Trip, status_code=status.HTTP_201_CREATED)
def create_trip(payload: TripCreate, db: DB, user_id: CurrentUserID) -> Trip:
    """Create a new trip. user_id is always taken from the JWT."""
    return TripsService(db).create_trip(payload.model_copy(update={"user_id": user_id}))


@router.get("/{trip_id}", response_model=Trip)
def get_trip(trip_id: UUID, db: DB, user_id: CurrentUserID) -> Trip:
    """Fetch a single trip by ID — must belong to the authenticated user."""
    return TripsService(db).get_trip(trip_id, user_id)


@router.patch("/{trip_id}", response_model=Trip)
def update_trip(trip_id: UUID, payload: TripUpdate, db: DB, user_id: CurrentUserID) -> Trip:
    """Partially update a trip — must belong to the authenticated user."""
    return TripsService(db).update_trip(trip_id, payload, user_id)


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(trip_id: UUID, db: DB, user_id: CurrentUserID) -> None:
    """Delete a trip and all its itinerary data (cascades via DB)."""
    TripsService(db).delete_trip(trip_id, user_id)


@router.get("/{trip_id}/items", response_model=List[ItineraryItem])
def list_trip_items(trip_id: UUID, db: DB, user_id: CurrentUserID) -> List[ItineraryItem]:
    """Return all itinerary items for a trip regardless of day assignment."""
    return ItineraryService(db).list_items_by_trip(trip_id)
