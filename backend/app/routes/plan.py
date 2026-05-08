"""Smart day planning — selects top attractions and restaurants for a trip day.

Internal Attraction Mock Dependency Cleanup v1D
-----------------------------------------------
``POST /plan/day`` previously synthesised attraction rows from the legacy
``_mock_attractions`` fixture via ``SearchService.search_attractions``.
The mock-backed attraction surface has been retired (PRs #287–#292), and
this endpoint now fails closed for attractions: the no-cluster path
returns an empty ``attractions`` list rather than fabricating cards.

Restaurants remain canonical (Google Places via
``SearchService.search_restaurants``).  When ``payload.places`` carries
cluster places (a canonical seam fed by the trip itinerary), those
attractions are still surfaced — so the cluster-driven flow is unchanged.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.core.deps import DB
from app.models.plan import (
    ClusterPlaceInput,
    DayPlanRequest,
    DayPlanResponse,
    PlannedAttraction,
    PlannedRestaurant,
)
from app.models.search import RestaurantSearchRequest
from app.services import TripsService
from app.services.search import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plan", tags=["plan"])


@router.post("/day", response_model=DayPlanResponse)
def plan_day(payload: DayPlanRequest, db: DB) -> DayPlanResponse:
    """Generate a smart day plan: lunch + dinner from canonical restaurants,
    plus any cluster-supplied attractions.

    When ``cluster_id`` and ``places`` are provided the plan is built from
    those cluster places (canonical seam).  Without cluster places the
    endpoint fails closed for attractions — there is no canonical
    attraction provider here and ``_mock_attractions`` was retired.
    """
    trip = TripsService(db).get_trip(payload.trip_id)
    destination = trip.destination

    if payload.places:
        return _plan_from_cluster(payload, destination, db)

    search = SearchService(db)
    restaurants = search.search_restaurants(RestaurantSearchRequest(location=destination))

    if len(restaurants) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Not enough restaurant data for this destination.",
        )

    sorted_restaurants = sorted(restaurants, key=lambda r: r.ai_score or 0, reverse=True)
    lunch = sorted_restaurants[0]
    dinner = next(
        (r for r in sorted_restaurants[1:] if r.cuisine != lunch.cuisine),
        sorted_restaurants[1],
    )

    return DayPlanResponse(
        trip_id=payload.trip_id,
        day_number=payload.day_number,
        destination=destination,
        attractions=[],
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


def _plan_from_cluster(
    payload: DayPlanRequest,
    destination: str,
    db,
) -> DayPlanResponse:
    """Build a DayPlanResponse from cluster places provided in the request."""
    places = payload.places or []

    cluster_attractions = sorted(
        [p for p in places if p.place_type == "attraction"],
        key=lambda p: p.ai_score or p.rating or 0,
        reverse=True,
    )[:3]

    cluster_restaurants = sorted(
        [p for p in places if p.place_type == "restaurant"],
        key=lambda p: p.ai_score or p.rating or 0,
        reverse=True,
    )

    if not cluster_restaurants:
        fallback = SearchService(db).search_restaurants(
            RestaurantSearchRequest(location=destination)
        )
        cluster_restaurants = [
            ClusterPlaceInput(
                id=r.id,
                name=r.name,
                place_type="restaurant",
                category=r.cuisine,
                address=r.address,
                rating=r.rating,
                ai_score=r.ai_score,
                tags=r.tags,
                booking_url=r.booking_url or "",
            )
            for r in sorted(fallback, key=lambda r: r.ai_score or 0, reverse=True)[:2]
        ]

    lunch = cluster_restaurants[0]
    dinner = (
        next((r for r in cluster_restaurants[1:] if r.category != lunch.category), cluster_restaurants[0])
        if len(cluster_restaurants) > 1
        else cluster_restaurants[0]
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
                description="",
                location=destination,
                address=a.address,
                rating=a.rating,
                ai_score=a.ai_score,
                tags=a.tags,
                booking_url=a.booking_url or "",
            )
            for a in cluster_attractions
        ],
        lunch=PlannedRestaurant(
            id=lunch.id,
            name=lunch.name,
            cuisine=lunch.category,
            location=destination,
            address=lunch.address,
            rating=lunch.rating,
            ai_score=lunch.ai_score,
            tags=lunch.tags,
            booking_url=lunch.booking_url or "",
        ),
        dinner=PlannedRestaurant(
            id=dinner.id,
            name=dinner.name,
            cuisine=dinner.category,
            location=destination,
            address=dinner.address,
            rating=dinner.rating,
            ai_score=dinner.ai_score,
            tags=dinner.tags,
            booking_url=dinner.booking_url or "",
        ),
    )
