"""Travel distance endpoint — haversine-based time estimates between locations."""

import math
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/travel", tags=["travel"])


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(max(0.0, min(1.0, a))))


class LocationPoint(BaseModel):
    id: str
    lat: float
    lng: float


class TravelLeg(BaseModel):
    from_id: str
    to_id: str
    distance_km: float
    walk_minutes: int
    drive_minutes: int


class TravelDistanceRequest(BaseModel):
    points: List[LocationPoint]


class TravelDistanceResponse(BaseModel):
    legs: List[TravelLeg]
    total_distance_km: float
    total_walk_minutes: int
    total_drive_minutes: int


@router.post("/distance", response_model=TravelDistanceResponse)
def calculate_travel_distance(req: TravelDistanceRequest) -> TravelDistanceResponse:
    """Calculate haversine distance and estimated travel times between consecutive points."""
    legs: List[TravelLeg] = []
    for i in range(len(req.points) - 1):
        a = req.points[i]
        b = req.points[i + 1]
        dist_km = _haversine_km(a.lat, a.lng, b.lat, b.lng)
        walk_min = max(1, round((dist_km / 5.0) * 60))   # 5 km/h walking
        drive_min = max(1, round((dist_km / 30.0) * 60))  # 30 km/h city driving
        legs.append(
            TravelLeg(
                from_id=a.id,
                to_id=b.id,
                distance_km=round(dist_km, 2),
                walk_minutes=walk_min,
                drive_minutes=drive_min,
            )
        )
    total_dist = round(sum(leg.distance_km for leg in legs), 2)
    total_walk = sum(leg.walk_minutes for leg in legs)
    total_drive = sum(leg.drive_minutes for leg in legs)
    return TravelDistanceResponse(
        legs=legs,
        total_distance_km=total_dist,
        total_walk_minutes=total_walk,
        total_drive_minutes=total_drive,
    )
