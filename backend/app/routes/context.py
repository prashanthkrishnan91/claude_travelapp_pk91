from datetime import date
from typing import Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.deps import DB, CurrentUserID
from app.services import TripsService

router = APIRouter(prefix="/context", tags=["context"])

_VIBE_MAP = {
    "Clear": "Sunny skies",
    "Clouds": "Soft clouds",
    "Rain": "Cozy rain",
    "Drizzle": "Cozy rain",
    "Thunderstorm": "Electric skies",
    "Snow": "Winter wonderland",
    "Mist": "Misty air",
    "Fog": "Misty air",
    "Haze": "Hazy skies",
    "Smoke": "Hazy skies",
    "Dust": "Hazy skies",
    "Sand": "Hazy skies",
    "Squall": "Breezy weather",
    "Tornado": "Stormy skies",
}

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class TripContextResponse(BaseModel):
    city: str
    temp: Optional[int] = None
    condition: Optional[str] = None
    vibe: str
    date_range: Optional[str] = None


def _format_date_range(start: Optional[date], end: Optional[date]) -> Optional[str]:
    if not start:
        return None
    start_str = f"{_MONTHS[start.month - 1]} {start.day}"
    if not end:
        return start_str
    if start.month == end.month:
        return f"{start_str}–{end.day}"
    return f"{start_str}–{_MONTHS[end.month - 1]} {end.day}"


@router.get("/trip/{trip_id}", response_model=TripContextResponse)
def get_trip_context(
    trip_id: UUID,
    db: DB,
    user_id: CurrentUserID,
) -> TripContextResponse:
    trip = TripsService(db).get_trip(trip_id, user_id)

    city = trip.destination.split(",")[0].strip()
    date_range = _format_date_range(trip.start_date, trip.end_date)

    temp: Optional[int] = None
    condition: Optional[str] = None
    wind_speed: Optional[float] = None

    api_key = get_settings().openweather_api_key
    if api_key:
        try:
            resp = httpx.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": city, "appid": api_key, "units": "imperial"},
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                temp = round(data["main"]["temp"])
                condition = data["weather"][0]["main"]
                wind_speed = data.get("wind", {}).get("speed")
        except Exception:
            pass

    vibe_base = _VIBE_MAP.get(condition or "", "Clear skies")
    parts = [vibe_base]
    if temp is not None:
        parts.append(f"{temp}°F")
    if wind_speed is not None and wind_speed > 10:
        parts.append("Light breeze")
    vibe = " • ".join(parts)

    return TripContextResponse(
        city=city,
        temp=temp,
        condition=condition,
        vibe=vibe,
        date_range=date_range,
    )
