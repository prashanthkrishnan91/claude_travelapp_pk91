from fastapi import APIRouter
from pydantic import BaseModel

from app.core.deps import DB, CurrentUserID

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class DashboardSummary(BaseModel):
    trip_count: int
    card_count: int
    itinerary_count: int


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: DB, user_id: CurrentUserID) -> DashboardSummary:
    """Return counts of trips, cards, and itinerary items for the authenticated user."""
    trips_result = (
        db.table("trips")
        .select("id", count="exact")
        .eq("user_id", str(user_id))
        .execute()
    )
    trip_count = trips_result.count or 0

    cards_result = (
        db.table("travel_cards")
        .select("id", count="exact")
        .eq("user_id", str(user_id))
        .execute()
    )
    card_count = cards_result.count or 0

    trip_ids_result = (
        db.table("trips")
        .select("id")
        .eq("user_id", str(user_id))
        .execute()
    )
    trip_ids = [row["id"] for row in trip_ids_result.data]

    itinerary_count = 0
    if trip_ids:
        items_result = (
            db.table("itinerary_items")
            .select("id", count="exact")
            .in_("trip_id", trip_ids)
            .execute()
        )
        itinerary_count = items_result.count or 0

    return DashboardSummary(
        trip_count=trip_count,
        card_count=card_count,
        itinerary_count=itinerary_count,
    )
