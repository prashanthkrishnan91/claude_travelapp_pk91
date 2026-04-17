"""Smart day planning — selects top attractions and restaurants for a trip day."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.core.deps import DB
from app.models.plan import (
    DayPlanRequest,
    DayPlanResponse,
    PlannedAttraction,
    PlannedRestaurant,
)
from app.models.search import AttractionSearchRequest, RestaurantSearchRequest
from app.services import TripsService
from app.services.search import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plan", tags=["plan"])


@router.post("/day", response_model=DayPlanResponse)
def plan_day(payload: DayPlanRequest, db: DB) -> DayPlanResponse:
    """Generate a smart day plan: top 3 attractions + 1 lunch + 1 dinner restaurant."""
    trip = TripsService(db).get_trip(payload.trip_id)
    destination = trip.destination

    search = SearchService(db)
    attractions = search.search_attractions(AttractionSearchRequest(location=destination))
    restaurants = search.search_restaurants(RestaurantSearchRequest(location=destination))

    if len(restaurants) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Not enough restaurant data for this destination.",
        )

    top_attractions = sorted(attractions, key=lambda a: a.ai_score or 0, reverse=True)[:3]

    sorted_restaurants = sorted(restaurants, key=lambda r: r.ai_score or 0, reverse=True)
    lunch = sorted_restaurants[0]
    # Pick dinner with a different cuisine for variety
    dinner = next(
        (r for r in sorted_restaurants[1:] if r.cuisine != lunch.cuisine),
        sorted_restaurants[1],
    )

    return DayPlanResponse(
        trip_id=payload.trip_id,
        day_number=payload.day_number,
        destination=destination,
        attractions=[
            PlannedAttraction(
                id=a.id,
                name=a.name,
                category=a.category,
                description=a.description,
                location=a.location,
                address=a.address,
                rating=a.rating,
                num_reviews=a.num_reviews,
                duration_minutes=a.duration_minutes,
                ai_score=a.ai_score,
                tags=a.tags,
                price_level=a.price_level,
                opening_hours=a.opening_hours,
                booking_url=a.booking_url,
            )
            for a in top_attractions
        ],
        lunch=PlannedRestaurant(
            id=lunch.id,
            name=lunch.name,
            cuisine=lunch.cuisine,
            location=lunch.location,
            address=lunch.address,
            rating=lunch.rating,
            num_reviews=lunch.num_reviews,
            ai_score=lunch.ai_score,
            tags=lunch.tags,
            price_level=lunch.price_level,
            opening_hours=lunch.opening_hours,
            booking_url=lunch.booking_url,
        ),
        dinner=PlannedRestaurant(
            id=dinner.id,
            name=dinner.name,
            cuisine=dinner.cuisine,
            location=dinner.location,
            address=dinner.address,
            rating=dinner.rating,
            num_reviews=dinner.num_reviews,
            ai_score=dinner.ai_score,
            tags=dinner.tags,
            price_level=dinner.price_level,
            opening_hours=dinner.opening_hours,
            booking_url=dinner.booking_url,
        ),
    )
