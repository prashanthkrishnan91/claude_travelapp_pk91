from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.models import (
    ItineraryDay,
    ItineraryDayCreate,
    ItineraryDayUpdate,
    ItineraryItem,
    ItineraryItemCreate,
    ItineraryItemDirectCreate,
    ItineraryItemUpdate,
)

DAYS_TABLE = "itinerary_days"
ITEMS_TABLE = "itinerary_items"


class ItineraryService:
    def __init__(self, db: Client) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Days
    # ------------------------------------------------------------------

    def list_days(self, trip_id: UUID) -> List[ItineraryDay]:
        result = (
            self.db.table(DAYS_TABLE)
            .select("*")
            .eq("trip_id", str(trip_id))
            .order("day_number")
            .execute()
        )
        return [ItineraryDay(**row) for row in result.data]

    def get_day(self, day_id: UUID) -> ItineraryDay:
        result = (
            self.db.table(DAYS_TABLE)
            .select("*")
            .eq("id", str(day_id))
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Itinerary day {day_id} not found",
            )
        return ItineraryDay(**result.data[0])

    def create_day(self, payload: ItineraryDayCreate) -> ItineraryDay:
        result = (
            self.db.table(DAYS_TABLE)
            .insert(payload.model_dump(mode="json"))
            .execute()
        )
        return ItineraryDay(**result.data[0])

    def update_day(self, day_id: UUID, payload: ItineraryDayUpdate) -> ItineraryDay:
        data = payload.model_dump(mode="json", exclude_none=True)
        if not data:
            return self.get_day(day_id)
        result = (
            self.db.table(DAYS_TABLE)
            .update(data)
            .eq("id", str(day_id))
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Itinerary day {day_id} not found",
            )
        return ItineraryDay(**result.data[0])

    def delete_day(self, day_id: UUID) -> None:
        self.db.table(DAYS_TABLE).delete().eq("id", str(day_id)).execute()

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------

    def list_items_by_trip(self, trip_id: UUID) -> List[ItineraryItem]:
        result = (
            self.db.table(ITEMS_TABLE)
            .select("*")
            .eq("trip_id", str(trip_id))
            .order("position")
            .execute()
        )
        return [ItineraryItem(**row) for row in result.data]

    def list_items(self, day_id: UUID) -> List[ItineraryItem]:
        result = (
            self.db.table(ITEMS_TABLE)
            .select("*")
            .eq("day_id", str(day_id))
            .order("position")
            .execute()
        )
        return [ItineraryItem(**row) for row in result.data]

    def get_item(self, item_id: UUID) -> ItineraryItem:
        result = (
            self.db.table(ITEMS_TABLE)
            .select("*")
            .eq("id", str(item_id))
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Itinerary item {item_id} not found",
            )
        return ItineraryItem(**result.data[0])

    def create_item(self, payload: ItineraryItemCreate) -> ItineraryItem:
        result = (
            self.db.table(ITEMS_TABLE)
            .insert(payload.model_dump(mode="json"))
            .execute()
        )
        return ItineraryItem(**result.data[0])

    def create_trip_item(self, payload: ItineraryItemDirectCreate) -> ItineraryItem:
        data = payload.model_dump(mode="json", exclude_none=True)
        result = (
            self.db.table(ITEMS_TABLE)
            .insert(data)
            .execute()
        )
        return ItineraryItem(**result.data[0])

    def update_item(self, item_id: UUID, payload: ItineraryItemUpdate) -> ItineraryItem:
        data = payload.model_dump(mode="json", exclude_none=True)
        if not data:
            return self.get_item(item_id)
        result = (
            self.db.table(ITEMS_TABLE)
            .update(data)
            .eq("id", str(item_id))
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Itinerary item {item_id} not found",
            )
        return ItineraryItem(**result.data[0])

    def delete_item(self, item_id: UUID) -> None:
        self.db.table(ITEMS_TABLE).delete().eq("id", str(item_id)).execute()
