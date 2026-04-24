import logging
from datetime import date, timedelta
from typing import List, Optional
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
logger = logging.getLogger(__name__)


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

    def ensure_trip_days(
        self,
        trip_id: UUID,
        start_date: date,
        end_date: date,
    ) -> List[ItineraryDay]:
        if end_date < start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_date must be on or after start_date",
            )

        expected_count = (end_date - start_date).days + 1
        expected_numbers = set(range(1, expected_count + 1))
        logger.info("[trip-days] ensure start trip_id=%s expected=%s", trip_id, expected_count)

        existing_days = self.list_days(trip_id)
        existing_by_number = {day.day_number: day for day in existing_days}
        existing_numbers = sorted(existing_by_number.keys())
        logger.info("[trip-days] existing day_numbers=%s", existing_numbers)

        created_numbers: List[int] = []
        updated_numbers: List[int] = []
        for day_number in range(1, expected_count + 1):
            expected_date = start_date + timedelta(days=day_number - 1)
            if day_number in existing_by_number:
                existing_day = existing_by_number[day_number]
                updates = {}
                if existing_day.date != expected_date:
                    updates["date"] = expected_date
                if not existing_day.title:
                    updates["title"] = f"Day {day_number}"
                if updates:
                    self.update_day(existing_day.id, ItineraryDayUpdate(**updates))
                    updated_numbers.append(day_number)
                continue
            self.create_day(
                ItineraryDayCreate(
                    trip_id=trip_id,
                    day_number=day_number,
                    title=f"Day {day_number}",
                    date=expected_date,
                )
            )
            created_numbers.append(day_number)
        if created_numbers:
            logger.info("[trip-days] created missing day_numbers=%s", created_numbers)
        else:
            logger.info("[trip-days] created missing day_numbers=[]")
        if updated_numbers:
            logger.info("[trip-days] reconciled day dates=%s", updated_numbers)
        else:
            logger.info("[trip-days] reconciled day dates=[]")

        # Keep extra days only when they contain items; delete empty extras safely.
        for day in existing_days:
            if day.day_number in expected_numbers:
                continue
            items = self.list_items(day.id)
            if not items:
                self.delete_day(day.id)

        complete_days = self.list_days(trip_id)
        logger.info("[trip-days] complete count=%s", len(complete_days))
        return complete_days

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
        duplicate = self._find_duplicate_item(
            trip_id=payload.trip_id,
            title=payload.title,
            item_type=payload.item_type.value,
            day_id=payload.day_id,
        )
        if duplicate:
            return ItineraryItem(**duplicate)
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

    def _find_duplicate_item(self, trip_id: UUID, title: str, item_type: str, day_id: Optional[UUID]) -> Optional[dict]:
        query = (
            self.db.table(ITEMS_TABLE)
            .select("*")
            .eq("trip_id", str(trip_id))
            .eq("item_type", item_type)
            .limit(25)
        )
        if day_id:
            query = query.eq("day_id", str(day_id))
        else:
            query = query.is_("day_id", "null")
        existing = query.execute().data or []
        normalized_title = title.strip().lower()
        for row in existing:
            if (row.get("title") or "").strip().lower() == normalized_title:
                return row
        return None
