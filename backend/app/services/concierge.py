"""AI concierge service — loads trip context and calls Claude for recommendations."""

import json
import logging
import re
from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.core.config import get_settings
from app.models.concierge import (
    INTENT_AREA_ADVICE,
    INTENT_ATTRACTIONS,
    INTENT_BEST_AREA,
    INTENT_COMPARE,
    INTENT_FAMILY_FRIENDLY,
    INTENT_GENERAL,
    INTENT_GENERAL_DESTINATION,
    INTENT_HIDDEN_GEMS,
    INTENT_HOTELS,
    INTENT_LUXURY_VALUE,
    INTENT_MICHELIN_RESTAURANTS,
    INTENT_PLAN_DAY,
    INTENT_RESTAURANTS,
    INTENT_REWARDS_HELP,
    INTENT_ROMANTIC,
    SOURCE_CURATED_STATIC,
    SOURCE_LIVE_SEARCH,
    SOURCE_NONE,
    SOURCE_UNAVAILABLE,
    ConciergeResponse,
    ConciergeSearchResponse,
    Suggestion,
    UnifiedAttractionResult,
    UnifiedHotelResult,
    UnifiedRestaurantResult,
)
from app.models.search import (
    AttractionSearchRequest,
    HotelSearchRequest,
    RestaurantSearchRequest,
)
from app.services.search import SearchService

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a premium travel concierge. "
    'Respond ONLY with valid JSON matching exactly: '
    '{"response": "<string>", "suggestions": [{"type": "attraction" or "restaurant", "name": "<string>", "reason": "<string>"}]}. '
    "Keep recommendations concise and actionable. No markdown, no extra keys."
)

_RETRIEVAL_SYSTEM_PROMPT = (
    "You are a premium travel concierge and luxury researcher. "
    "Answer from retrieved results when available. "
    "Never tell the user to go search another site if retrieved results already answer the request. "
    'Respond ONLY with valid JSON matching exactly: '
    '{"response": "<string>", "suggestions": [{"type": "attraction" or "restaurant", "name": "<string>", "reason": "<string>"}]}. '
    "Response style: open with a concise recommendation summary, explain why each top pick fits the query, "
    "call out best overall / best value / luxury splurge when relevant, "
    "mention source limitations honestly. "
    "When Michelin restaurant results are provided, follow this structure in 'response': "
    "(1) Opening: 'Here are the top Michelin options in [CITY]'. "
    "(2) For each restaurant: '[Name] ([Michelin tier]) — [cuisine], [neighborhood]. [Why it fits].' "
    "(3) Close: 'Best overall: [name]. Best value: [name (Bib Gourmand or lowest tier)].' "
    "No markdown inside JSON strings, no extra keys."
)

# Intent sets for routing logic
_RESTAURANT_INTENTS = {
    INTENT_MICHELIN_RESTAURANTS, INTENT_RESTAURANTS, INTENT_HIDDEN_GEMS,
    INTENT_LUXURY_VALUE, INTENT_ROMANTIC, INTENT_FAMILY_FRIENDLY,
}
_ATTRACTION_INTENTS = {INTENT_ATTRACTIONS, INTENT_PLAN_DAY}


def _kw_pattern(*keywords: str) -> re.Pattern:
    """Compile keyword alternatives with word boundaries."""
    parts = sorted(keywords, key=len, reverse=True)
    return re.compile(
        r"\b(?:" + "|".join(re.escape(kw) for kw in parts) + r")\b",
        re.IGNORECASE,
    )


_MICHELIN_PAT = _kw_pattern(
    "michelin", "bib gourmand", "starred", "star restaurant", "star dining", "fine dining",
)
_HIDDEN_GEMS_PAT = _kw_pattern(
    "hidden gem", "hidden gems", "off the beaten", "local secret", "undiscovered", "under the radar",
)
_LUXURY_PAT = _kw_pattern(
    "luxury", "splurge", "high-end", "upscale", "best value", "value dining", "affordable fine",
)
_ROMANTIC_PAT = _kw_pattern(
    "romantic", "date night", "anniversary", "couple", "honeymoon", "special occasion",
)
_FAMILY_PAT = _kw_pattern(
    "family", "kids", "children", "child-friendly", "family-friendly",
)
_RESTAURANT_PAT = _kw_pattern(
    "restaurants", "restaurant", "dining", "dinner", "lunch", "breakfast", "brunch",
    "cuisine", "where to eat", "best places to eat", "tasting menu", "omakase", "eat",
)
_ATTRACTION_PAT = _kw_pattern(
    "attractions", "attraction", "museum", "museums", "tour", "sightseeing",
    "things to do", "activity", "activities", "visit", "see", "landmark", "landmarks",
)
_HOTEL_PAT = _kw_pattern(
    "hotels", "hotel", "accommodation", "where to stay", "hostel", "resort",
)
_PLAN_DAY_PAT = _kw_pattern(
    "itinerary", "plan my day", "schedule", "day trip", "day plan",
    "what should i do", "full day", "plan a day",
)
_COMPARE_PAT = _kw_pattern(
    "compare", "versus", " vs ", "which is better", "which should i",
)
_AREA_PAT = _kw_pattern(
    "neighborhood", "neighbourhood", "area", "district", "quarter",
    "best area", "best place to stay", "where to base",
)
_REWARDS_PAT = _kw_pattern(
    "points", "miles", "reward", "credit card", "loyalty", "cpp",
)


class ConciergeService:
    def __init__(self, db: Client) -> None:
        self._db = db
        self._settings = get_settings()

    # ------------------------------------------------------------------
    # Original answer() — unchanged for backward compatibility
    # ------------------------------------------------------------------

    def answer(self, trip_id: UUID, user_query: str, user_id: UUID, day_number: Optional[int] = None) -> ConciergeResponse:
        context = self._load_context(trip_id, user_id, day_number)
        prompt = self._build_prompt(context, user_query)
        raw = self._call_claude(prompt)
        return self._parse_response(raw)

    # ------------------------------------------------------------------
    # Retrieval-first search()
    # ------------------------------------------------------------------

    def search(self, trip_id: UUID, user_query: str, user_id: UUID) -> ConciergeSearchResponse:
        trip = self._fetch_trip(trip_id, user_id)
        destination = trip.get("destination", "")
        intent = self._detect_intent(user_query)

        restaurants: List[UnifiedRestaurantResult] = []
        attractions: List[UnifiedAttractionResult] = []
        hotels: List[UnifiedHotelResult] = []
        areas: List[str] = []
        source_status = SOURCE_NONE
        sources: List[str] = []
        warnings: List[str] = []
        retrieval_used = False

        search_svc = SearchService(self._db)

        if intent == INTENT_MICHELIN_RESTAURANTS:
            from app.services.michelin_retriever import MichelinRetriever
            restaurants, source_status = MichelinRetriever().fetch(destination, user_query)
            if source_status == SOURCE_UNAVAILABLE:
                warnings.append(
                    f"Michelin Guide data is not available for {destination}. "
                    "Showing general dining recommendations based on local search."
                )
                # Fall back to general search so the user still gets useful results
                raw_rest = search_svc.search_restaurants(RestaurantSearchRequest(location=destination))
                restaurants = [self._to_unified_restaurant(r) for r in raw_rest[:6]]
                source_status = SOURCE_LIVE_SEARCH
                sources.append("Local restaurant database")
            else:
                sources.append("Michelin Guide (curated reference data)")
            retrieval_used = True

        elif intent in {INTENT_RESTAURANTS, INTENT_HIDDEN_GEMS, INTENT_LUXURY_VALUE,
                        INTENT_ROMANTIC, INTENT_FAMILY_FRIENDLY}:
            raw_rest = search_svc.search_restaurants(RestaurantSearchRequest(location=destination))
            restaurants = [self._to_unified_restaurant(r) for r in raw_rest[:6]]
            source_status = SOURCE_LIVE_SEARCH
            sources.append("Restaurant search database")
            retrieval_used = True

        elif intent in _ATTRACTION_INTENTS:
            raw_attr = search_svc.search_attractions(AttractionSearchRequest(location=destination))
            attractions = [self._to_unified_attraction(a) for a in raw_attr[:6]]
            source_status = SOURCE_LIVE_SEARCH
            sources.append("Attraction search database")
            retrieval_used = True
            if intent == INTENT_PLAN_DAY:
                # Full-day planning benefits from restaurant options too
                raw_rest = search_svc.search_restaurants(RestaurantSearchRequest(location=destination))
                restaurants = [self._to_unified_restaurant(r) for r in raw_rest[:4]]

        elif intent == INTENT_HOTELS:
            try:
                check_in = date.fromisoformat(trip.get("start_date", "")) if trip.get("start_date") else date.today()
            except (ValueError, TypeError):
                check_in = date.today()
            check_out = check_in + timedelta(days=1)
            raw_hotels = search_svc.search_hotels(
                HotelSearchRequest(location=destination, check_in=check_in, check_out=check_out, guests=1)
            )
            hotels = [self._to_unified_hotel(h) for h in raw_hotels[:6]]
            source_status = SOURCE_LIVE_SEARCH
            sources.append("Hotel search database")
            retrieval_used = bool(hotels)

        elif intent in {INTENT_BEST_AREA, INTENT_AREA_ADVICE}:
            best = self._derive_best_area(search_svc, destination, trip)
            if best:
                areas = [best]
            raw_attr = search_svc.search_attractions(AttractionSearchRequest(location=destination))
            extra = list({a.location for a in raw_attr[:10] if a.location and a.location != best})
            areas += extra[:4]
            source_status = SOURCE_LIVE_SEARCH
            sources.append("Neighborhood analysis")
            retrieval_used = bool(areas)

        elif intent == INTENT_COMPARE:
            raw_attr = search_svc.search_attractions(AttractionSearchRequest(location=destination))
            raw_rest = search_svc.search_restaurants(RestaurantSearchRequest(location=destination))
            attractions = [self._to_unified_attraction(a) for a in raw_attr[:4]]
            restaurants = [self._to_unified_restaurant(r) for r in raw_rest[:4]]
            source_status = SOURCE_LIVE_SEARCH
            sources.append("Search database")
            retrieval_used = True

        elif intent == INTENT_GENERAL_DESTINATION:
            raw_attr = search_svc.search_attractions(AttractionSearchRequest(location=destination))
            raw_rest = search_svc.search_restaurants(RestaurantSearchRequest(location=destination))
            attractions = [self._to_unified_attraction(a) for a in raw_attr[:4]]
            restaurants = [self._to_unified_restaurant(r) for r in raw_rest[:3]]
            source_status = SOURCE_LIVE_SEARCH
            sources.append("Destination research database")
            retrieval_used = True

        system_prompt = _RETRIEVAL_SYSTEM_PROMPT if retrieval_used else _SYSTEM_PROMPT
        prompt = self._build_search_prompt(
            trip, user_query, intent, restaurants, attractions, hotels, areas, warnings
        )
        raw = self._call_claude(prompt, system_prompt=system_prompt)
        base = self._parse_response(raw)

        return ConciergeSearchResponse(
            response=base.response,
            intent=intent,
            retrieval_used=retrieval_used,
            source_status=source_status,
            restaurants=restaurants,
            attractions=attractions,
            hotels=hotels,
            areas=areas,
            suggestions=base.suggestions,
            sources=sources,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Intent detection
    # ------------------------------------------------------------------

    def _detect_intent(self, user_query: str) -> str:
        q = user_query.lower()

        if _MICHELIN_PAT.search(q):
            return INTENT_MICHELIN_RESTAURANTS
        if _HIDDEN_GEMS_PAT.search(q):
            return INTENT_HIDDEN_GEMS
        if _ROMANTIC_PAT.search(q):
            return INTENT_ROMANTIC
        if _FAMILY_PAT.search(q):
            return INTENT_FAMILY_FRIENDLY
        if _LUXURY_PAT.search(q):
            return INTENT_LUXURY_VALUE
        if _RESTAURANT_PAT.search(q):
            return INTENT_RESTAURANTS
        if _ATTRACTION_PAT.search(q):
            return INTENT_ATTRACTIONS
        if _AREA_PAT.search(q):
            return INTENT_BEST_AREA
        if _HOTEL_PAT.search(q):
            return INTENT_HOTELS
        if _PLAN_DAY_PAT.search(q):
            return INTENT_PLAN_DAY
        if _COMPARE_PAT.search(q):
            return INTENT_COMPARE
        if _REWARDS_PAT.search(q):
            return INTENT_REWARDS_HELP
        return INTENT_GENERAL

    # ------------------------------------------------------------------
    # Result converters
    # ------------------------------------------------------------------

    def _to_unified_restaurant(self, r) -> UnifiedRestaurantResult:
        maps_query = (r.name + " " + r.location).replace(" ", "+")
        return UnifiedRestaurantResult(
            name=r.name,
            source="Restaurant database",
            cuisine=r.cuisine,
            neighborhood=r.location,
            rating=round(r.rating * 2, 1) if r.rating is not None else None,
            review_count=getattr(r, "num_reviews", None),
            maps_link=f"https://maps.google.com/?q={maps_query}",
            ai_score=r.ai_score,
            tags=r.tags[:4] if r.tags else [],
        )

    def _to_unified_attraction(self, a) -> UnifiedAttractionResult:
        maps_query = (a.name + " " + a.location).replace(" ", "+")
        return UnifiedAttractionResult(
            name=a.name,
            source="Attraction database",
            category=a.category,
            description=getattr(a, "description", None),
            neighborhood=a.location,
            rating=round(a.rating * 2, 1) if a.rating is not None else None,
            review_count=getattr(a, "num_reviews", None),
            address=getattr(a, "address", None),
            maps_link=f"https://maps.google.com/?q={maps_query}",
            ai_score=a.ai_score,
            tags=a.tags[:4] if a.tags else [],
        )

    def _to_unified_hotel(self, h) -> UnifiedHotelResult:
        maps_query = (h.name + " " + h.location).replace(" ", "+")
        return UnifiedHotelResult(
            name=h.name,
            source="Hotel search",
            area_label=getattr(h, "area_label", None),
            stars=getattr(h, "stars", None),
            rating=round(h.rating * 2, 1) if h.rating is not None else None,
            price_per_night=getattr(h, "price_per_night", None),
            maps_link=f"https://maps.google.com/?q={maps_query}",
            ai_score=h.ai_score,
            tags=h.tags[:4] if h.tags else [],
        )

    # ------------------------------------------------------------------
    # Context loading
    # ------------------------------------------------------------------

    def _load_context(self, trip_id: UUID, user_id: UUID, day_number: Optional[int] = None) -> dict:
        trip = self._fetch_trip(trip_id, user_id)
        items = self._fetch_itinerary_items(trip_id, day_number)
        destination = trip.get("destination", "")
        search = SearchService(self._db)
        attractions = search.search_attractions(AttractionSearchRequest(location=destination))
        restaurants = search.search_restaurants(RestaurantSearchRequest(location=destination))
        best_area = self._derive_best_area(search, destination, trip)
        preferences = self._fetch_preferences(user_id)
        return {
            "trip": trip,
            "items": items,
            "attractions": attractions[:5],
            "restaurants": restaurants[:5],
            "best_area": best_area,
            "preferences": preferences,
            "day_number": day_number,
        }

    def _fetch_trip(self, trip_id: UUID, user_id: UUID) -> dict:
        res = (
            self._db.table("trips")
            .select("id,destination,start_date,end_date,title,user_id")
            .eq("id", str(trip_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
        return res.data[0]

    def _fetch_itinerary_items(self, trip_id: UUID, day_number: Optional[int] = None) -> list:
        query = self._db.table("itinerary_days").select("id,day_number").eq("trip_id", str(trip_id))
        if day_number is not None:
            query = query.eq("day_number", day_number)
        days_res = query.execute()
        if not days_res.data:
            return []
        day_ids = [d["id"] for d in days_res.data]
        items_res = (
            self._db.table("itinerary_items")
            .select("title,item_type,description,location,start_time")
            .in_("day_id", day_ids)
            .execute()
        )
        return items_res.data or []

    def _derive_best_area(self, search: SearchService, destination: str, trip: dict) -> str:
        try:
            check_in = date.fromisoformat(trip["start_date"]) if trip.get("start_date") else date.today()
        except (ValueError, TypeError):
            check_in = date.today()
        check_out = check_in + timedelta(days=1)
        hotels = search.search_hotels(
            HotelSearchRequest(location=destination, check_in=check_in, check_out=check_out, guests=1)
        )
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
        day_number = ctx.get("day_number")

        if day_number is not None:
            day_header = f"Planning scope: Day {day_number} only.\n"
            already_planned = (
                f"Already planned for Day {day_number}:\n{items_text}\n\n"
                "Rules:\n"
                "- Do NOT suggest anything already listed above.\n"
                "- Prioritise places close to existing locations to minimise travel.\n"
                "- Fit suggestions into logical gaps in the schedule.\n\n"
            )
        else:
            day_header = ""
            already_planned = f"Current itinerary:\n{items_text}\n\n"

        return (
            "You are a premium travel concierge.\n\n"
            f"Trip:\n  Destination: {city}\n  Dates: {dates}\n\n"
            + day_header
            + already_planned
            + f"Top attractions:\n{attractions_text}\n\n"
            f"Top restaurants:\n{restaurants_text}\n\n"
            f"Best area: {best_area}\n"
            + prefs_section
            + f"\nUser request:\n{user_query}\n\n"
            "Respond with clear recommendations, a structured plan if relevant, and concise reasoning."
        )

    def _build_search_prompt(
        self,
        trip: dict,
        user_query: str,
        intent: str,
        restaurants: List[UnifiedRestaurantResult],
        attractions: List[UnifiedAttractionResult] = None,
        hotels: List[UnifiedHotelResult] = None,
        areas: List[str] = None,
        warnings: List[str] = None,
    ) -> str:
        city = trip.get("destination", "Unknown")
        start = trip.get("start_date", "")
        end = trip.get("end_date", "")
        dates = f"{start} to {end}" if start and end else start or "TBD"

        parts = [f"Destination: {city} | Dates: {dates}\n\n"]

        if warnings:
            for w in warnings:
                parts.append(f"NOTE: {w}\n")
            parts.append("\n")

        if restaurants:
            source_label = "Michelin Guide" if intent == INTENT_MICHELIN_RESTAURANTS else "restaurant database"
            parts.append(f"Retrieved {len(restaurants)} restaurants from {source_label} for {city}:\n")
            for i, r in enumerate(restaurants[:8], 1):
                status_badge = f"[{r.michelin_status}]" if r.michelin_status else ""
                rating_str = f"Rating: {r.rating}/10" if r.rating else ""
                parts.append(
                    f"{i}. {r.name} {status_badge} — {r.cuisine}, {r.neighborhood or 'City Center'} | {rating_str}\n"
                    f"   {r.summary or ''}\n"
                )
            if intent == INTENT_MICHELIN_RESTAURANTS:
                parts.append(
                    "\nIMPORTANT: These are already retrieved — DO NOT tell the user to 'check Michelin Guide'.\n\n"
                )
            else:
                parts.append("\nIMPORTANT: These results are already retrieved — reference specific names.\n\n")

        if attractions:
            parts.append(f"Retrieved {len(attractions)} attractions in {city}:\n")
            for i, a in enumerate(attractions[:8], 1):
                rating_str = f"Rating: {a.rating}/10" if a.rating else ""
                parts.append(
                    f"{i}. {a.name} ({a.category}) | {rating_str}\n"
                    f"   {a.description or ''}\n"
                )
            parts.append("\n")

        if hotels:
            parts.append(f"Retrieved {len(hotels)} hotels in {city}:\n")
            for i, h in enumerate(hotels[:6], 1):
                price_str = f"${h.price_per_night:.0f}/night" if h.price_per_night else ""
                stars_str = f"{'★' * int(h.stars or 0)}" if h.stars else ""
                parts.append(
                    f"{i}. {h.name} {stars_str} | {price_str} | Area: {h.area_label or 'City'}\n"
                )
            parts.append("\n")

        if areas:
            parts.append(f"Top neighborhoods/areas in {city}: {', '.join(areas)}\n\n")

        has_data = any([restaurants, attractions, hotels, areas])
        if not has_data:
            parts.append(f"No specific results were retrieved. Provide general travel advice for {city}.\n\n")

        parts.append(f"User request: {user_query}\n")

        if intent == INTENT_MICHELIN_RESTAURANTS and restaurants:
            parts.append(
                f"\nIn 'response': open with 'Here are the top Michelin options in {city}', "
                "list each with Michelin tier and why it fits, "
                "close with 'Best overall: [name]. Best value: [name].' "
                "Use the exact restaurant names retrieved above."
            )
        else:
            parts.append(
                "\nIn 'response': start with a concise recommendation summary, "
                "explain why top picks fit the query, call out best overall / best value / luxury splurge, "
                "mention any data limitations honestly."
            )

        return "".join(parts)

    # ------------------------------------------------------------------
    # Claude API call
    # ------------------------------------------------------------------

    def _call_claude(self, prompt: str, system_prompt: Optional[str] = None) -> str:
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
                max_tokens=1500,
                system=system_prompt or _SYSTEM_PROMPT,
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
        def _normalize_response_text(value) -> str:
            if isinstance(value, str):
                return value.strip()
            if value is None:
                return ""
            return str(value).strip()

        def _coerce_payload(payload) -> Optional[dict]:
            if isinstance(payload, dict):
                return payload
            if isinstance(payload, str):
                text = payload.strip()
                if not text:
                    return None
                # Common model output format: fenced JSON block.
                fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
                candidate = fenced.group(1).strip() if fenced else text
                try:
                    decoded = json.loads(candidate)
                    if isinstance(decoded, dict):
                        return decoded
                except (json.JSONDecodeError, TypeError):
                    pass
                # Fallback: extract the first object-like region.
                start = candidate.find("{")
                end = candidate.rfind("}")
                if start != -1 and end != -1 and start < end:
                    try:
                        decoded = json.loads(candidate[start : end + 1])
                        if isinstance(decoded, dict):
                            return decoded
                    except (json.JSONDecodeError, TypeError):
                        return None
            return None

        try:
            data = _coerce_payload(raw)
            if not data:
                raise json.JSONDecodeError("invalid-json", raw, 0)

            response_text = _normalize_response_text(data.get("response", ""))

            # Guard against nested/stringified JSON in "response".
            nested = _coerce_payload(response_text)
            if nested and "response" in nested:
                data = nested
                response_text = _normalize_response_text(data.get("response", ""))

            suggestions = [
                Suggestion(type=s["type"], name=s["name"], reason=s["reason"])
                for s in data.get("suggestions", [])
                if s.get("type") in ("attraction", "restaurant")
            ]
            if not response_text:
                response_text = "I found results that match your request."
            return ConciergeResponse(response=response_text, suggestions=suggestions)
        except (json.JSONDecodeError, KeyError, TypeError):
            logger.warning("Claude response was not valid JSON — returning raw text")
            return ConciergeResponse(response=raw.strip(), suggestions=[])
