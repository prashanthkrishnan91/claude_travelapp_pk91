"""AI concierge service — loads trip context and calls Claude for recommendations."""

import json
import logging
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.core.config import get_settings
from app.models.concierge import ConciergeResponse, Suggestion
from app.models.search import AttractionSearchRequest, RestaurantSearchRequest
from app.services.search import SearchService

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a premium travel concierge. "
    'Respond ONLY with valid JSON matching exactly: '
    '{"response": "<string>", "suggestions": [{"type": "attraction" or "restaurant", "name": "<string>", "reason": "<string>"}]}. '
    "Keep recommendations concise and actionable. No markdown, no extra keys."
)


class ConciergeService:
    def __init__(self, db: Client) -> None:
        self._db = db
        self._settings = get_settings()

    def answer(self, trip_id: UUID, user_query: str, user_id: UUID) -> ConciergeResponse:
        context = self._load_context(trip_id, user_id)
        prompt = self._build_prompt(context, user_query)
        raw = self._call_claude(prompt)
        return self._parse_response(raw)

    # ------------------------------------------------------------------
    # Context loading
    # ------------------------------------------------------------------

    def _load_context(self, trip_id: UUID, user_id: UUID) -> dict:
        trip = self._fetch_trip(trip_id)
        items = self._fetch_itinerary_items(trip_id)
        destination = trip.get("destination", "")
        search = SearchService(self._db)
        attractions = search.search_attractions(AttractionSearchRequest(location=destination))
        restaurants = search.search_restaurants(RestaurantSearchRequest(location=destination))
        best_area = self._derive_best_area(search, destination)
        preferences = self._fetch_preferences(user_id)
        return {
            "trip": trip,
            "items": items,
            "attractions": attractions[:5],
            "restaurants": restaurants[:5],
            "best_area": best_area,
            "preferences": preferences,
        }

    def _fetch_trip(self, trip_id: UUID) -> dict:
        res = self._db.table("trips").select("id,destination,start_date,end_date,title").eq("id", str(trip_id)).execute()
        if not res.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
        return res.data[0]

    def _fetch_itinerary_items(self, trip_id: UUID) -> list:
        days_res = self._db.table("itinerary_days").select("id").eq("trip_id", str(trip_id)).execute()
        if not days_res.data:
            return []
        day_ids = [d["id"] for d in days_res.data]
        items_res = self._db.table("itinerary_items").select("title,item_type,description,location,start_time").in_("day_id", day_ids).execute()
        return items_res.data or []

    def _derive_best_area(self, search: SearchService, destination: str) -> str:
        from app.models.search import HotelSearchRequest
        hotels = search.search_hotels(HotelSearchRequest(origin="", destination=destination, check_in="", check_out="", travelers=1))
        labels = [h.area_label for h in hotels if h.area_label]
        if not labels:
            return destination
        return max(set(labels), key=labels.count)

    def _fetch_preferences(self, user_id: UUID) -> dict:
        try:
            res = self._db.table("users").select("preferences").eq("id", str(user_id)).execute()
            if res.data and res.data[0].get("preferences"):
                return res.data[0]["preferences"]
        except Exception:
            pass
        return {}

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_prompt(self, ctx: dict, user_query: str) -> str:
        trip = ctx["trip"]
        city = trip.get("destination", "Unknown")
        start = trip.get("start_date", "")
        end = trip.get("end_date", "")
        dates = f"{start} to {end}" if start and end else start or "TBD"

        items_text = "\n".join(
            f"- [{i.get('item_type', 'item')}] {i.get('title', '')} {('@ ' + i['location']) if i.get('location') else ''}"
            for i in ctx["items"]
        ) or "No items yet."

        attractions_text = "\n".join(
            f"- {a.name} ({a.category}) — rating {a.rating}"
            for a in ctx["attractions"]
        ) or "None available."

        restaurants_text = "\n".join(
            f"- {r.name} ({r.cuisine}) — rating {r.rating}"
            for r in ctx["restaurants"]
        ) or "None available."

        prefs = ctx["preferences"]
        prefs_section = ""
        if prefs:
            parts = []
            if prefs.get("preferred_airlines"):
                airlines = ", ".join(prefs["preferred_airlines"])
                parts.append(f"Preferred airlines: {airlines}")
            if prefs.get("seat_class"):
                parts.append(f"Seat class: {prefs['seat_class']}")
            if prefs.get("hotel_class"):
                parts.append(f"Hotel stars: {prefs['hotel_class']}")
            if parts:
                prefs_section = "User preferences:\n" + "\n".join(parts) + "\n"

        best_area = ctx["best_area"]
        return (
            "You are a premium travel concierge.\n\n"
            f"Trip:\n  Destination: {city}\n  Dates: {dates}\n\n"
            f"Itinerary:\n{items_text}\n\n"
            f"Top attractions:\n{attractions_text}\n\n"
            f"Top restaurants:\n{restaurants_text}\n\n"
            f"Best area: {best_area}\n"
            + prefs_section
            + f"\nUser request:\n{user_query}\n\n"
            "Respond with clear recommendations, a structured plan if relevant, and concise reasoning."
        )

    # ------------------------------------------------------------------
    # Claude API call
    # ------------------------------------------------------------------

    def _call_claude(self, prompt: str) -> str:
        api_key = self._settings.anthropic_api_key
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI concierge is not configured (missing ANTHROPIC_API_KEY)",
            )
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="anthropic package not installed",
            )
        except Exception as exc:
            logger.error("Claude API error: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI service error: {type(exc).__name__}",
            )

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(self, raw: str) -> ConciergeResponse:
        try:
            data = json.loads(raw)
            suggestions = [
                Suggestion(type=s["type"], name=s["name"], reason=s["reason"])
                for s in data.get("suggestions", [])
                if s.get("type") in ("attraction", "restaurant")
            ]
            return ConciergeResponse(response=data.get("response", raw), suggestions=suggestions)
        except (json.JSONDecodeError, KeyError, TypeError):
            logger.warning("Claude response was not valid JSON — returning raw text")
            return ConciergeResponse(response=raw, suggestions=[])
