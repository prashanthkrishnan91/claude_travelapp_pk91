from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.models import Trip, TripCreate, TripUpdate

TABLE = "trips"


class TripsService:
    def __init__(self, db: Client) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def list_trips(self, user_id: UUID) -> List[Trip]:
        result = (
            self.db.table(TABLE)
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )
        return [Trip(**row) for row in result.data]

    def get_trip(self, trip_id: UUID, user_id: Optional[UUID] = None) -> Trip:
        query = self.db.table(TABLE).select("*").eq("id", str(trip_id))
        if user_id is not None:
            query = query.eq("user_id", str(user_id))
        result = query.limit(1).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trip {trip_id} not found",
            )
        return Trip(**result.data[0])

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def create_trip(self, payload: TripCreate) -> Trip:
        result = (
            self.db.table(TABLE)
            .insert(payload.model_dump(mode="json"))
            .execute()
        )
        return Trip(**result.data[0])

    def update_trip(self, trip_id: UUID, payload: TripUpdate, user_id: Optional[UUID] = None) -> Trip:
        data = payload.model_dump(mode="json", exclude_none=True)
        if not data:
            return self.get_trip(trip_id, user_id)
        query = self.db.table(TABLE).update(data).eq("id", str(trip_id))
        if user_id is not None:
            query = query.eq("user_id", str(user_id))
        result = query.execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trip {trip_id} not found",
            )
        return Trip(**result.data[0])

    def delete_trip(self, trip_id: UUID, user_id: Optional[UUID] = None) -> None:
        query = self.db.table(TABLE).delete().eq("id", str(trip_id))
        if user_id is not None:
            query = query.eq("user_id", str(user_id))
        query.execute()
