from typing import List
from uuid import UUID

from fastapi import APIRouter, status

from app.core.deps import DB, CurrentUserID
from app.models import Trip, TripCreate, TripUpdate
from app.services import TripsService

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
def get_trip(trip_id: UUID, db: DB) -> Trip:
    """Fetch a single trip by ID."""
    return TripsService(db).get_trip(trip_id)


@router.patch("/{trip_id}", response_model=Trip)
def update_trip(trip_id: UUID, payload: TripUpdate, db: DB) -> Trip:
    """Partially update a trip."""
    return TripsService(db).update_trip(trip_id, payload)


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(trip_id: UUID, db: DB) -> None:
    """Delete a trip and all its itinerary data (cascades via DB)."""
    TripsService(db).delete_trip(trip_id)
