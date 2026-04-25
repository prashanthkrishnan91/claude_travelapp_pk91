"""AI concierge service — loads trip context and calls Claude for recommendations."""

import json
import logging
import re
from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID
from uuid import uuid4

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
    INTENT_NIGHTLIFE,
    INTENT_PLAN_DAY,
    INTENT_RESTAURANTS,
    INTENT_REWARDS_HELP,
    INTENT_ROMANTIC,
    SOURCE_CURATED_STATIC,
    SOURCE_APP_DATABASE,
    SOURCE_LIVE_SEARCH,
    SOURCE_NONE,
    SOURCE_SAMPLE_DATA,
    SOURCE_UNAVAILABLE,
    ConciergeResponse,
    ConciergeMessage,
    ConciergeSearchResponse,
    Suggestion,
    UnifiedAttractionResult,
    UnifiedAreaComparisonResult,
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
MESSAGES_TABLE = "concierge_messages"
_MISSING_MESSAGES_TABLE_HINT = (
    "concierge_messages table missing; apply migration 002_concierge_messages.sql "
    "and reload Supabase schema cache."
)

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
    INTENT_LUXURY_VALUE, INTENT_ROMANTIC, INTENT_FAMILY_FRIENDLY, INTENT_NIGHTLIFE,
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
    "drinks",
)
_NIGHTLIFE_PAT = _kw_pattern(
    "cocktail", "cocktails", "bar", "bars", "wine bar", "brewery", "rooftop bar",
    "speakeasy", "nightlife", "nearby drinks", "after dinner drinks", "night out",
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
_DAY_NUMBER_PAT = re.compile(r"\bday\s*\d+\b", re.IGNORECASE)
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
_COMPARE_SPLIT_PAT = re.compile(r"\b(?:vs\.?|versus)\b", re.IGNORECASE)


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

    def search(
        self, trip_id: UUID, user_query: str, user_id: UUID, client_message_id: Optional[str] = None
    ) -> ConciergeSearchResponse:
        trip = self._fetch_trip(trip_id, user_id)
        request_id = (client_message_id or "").strip() or str(uuid4())
        self._save_message(trip_id, "user", user_query, client_message_id=request_id)
        destination = trip.get("destination", "")
        intent = self._detect_intent(user_query)

        restaurants: List[UnifiedRestaurantResult] = []
        attractions: List[UnifiedAttractionResult] = []
        hotels: List[UnifiedHotelResult] = []
        areas: List[str] = []
        area_comparisons: List[UnifiedAreaComparisonResult] = []
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
                raw_rest = search_svc.search_restaurants(RestaurantSearchRequest(location=destination))
                source_status = self._infer_source_status(raw_rest)
                restaurants = [
                    self._to_unified_restaurant(r, intent=intent, limited_coverage=source_status == SOURCE_SAMPLE_DATA)
                    for r in raw_rest[:6]
                ]
                sources.append("Local restaurant database")
            else:
                sources.append("Michelin Guide (curated reference data)")
            retrieval_used = True

        elif intent in {INTENT_RESTAURANTS, INTENT_HIDDEN_GEMS, INTENT_LUXURY_VALUE,
                        INTENT_ROMANTIC, INTENT_FAMILY_FRIENDLY}:
            raw_rest = search_svc.search_restaurants(RestaurantSearchRequest(location=destination))
            source_status = self._infer_source_status(raw_rest)
            restaurants = [
                self._to_unified_restaurant(r, intent=intent, limited_coverage=source_status == SOURCE_SAMPLE_DATA)
                for r in raw_rest[:6]
            ]
            sources.append("Restaurant search database")
            retrieval_used = True

        elif intent == INTENT_NIGHTLIFE:
            restaurants = self._sample_nightlife_results(destination)
            if restaurants:
                source_status = SOURCE_SAMPLE_DATA
                sources.append("Sample bar research data · verify hours and current status before booking.")
                retrieval_used = True
            else:
                source_status = SOURCE_UNAVAILABLE
                warnings.append(
                    f"No bar/nightlife cards are available yet for {destination}. "
                    "Try specific neighborhoods, hotel concierge recommendations, or recent local roundups."
                )
                sources.append("Nightlife data unavailable")
                retrieval_used = False

        elif intent in _ATTRACTION_INTENTS:
            raw_attr = search_svc.search_attractions(AttractionSearchRequest(location=destination))
            source_status = self._infer_source_status(raw_attr)
            is_day_request = intent == INTENT_PLAN_DAY or bool(_DAY_NUMBER_PAT.search(user_query))
            attractions = [
                self._to_unified_attraction(
                    a,
                    destination=destination,
                    limited_coverage=source_status == SOURCE_SAMPLE_DATA,
                    is_day_request=is_day_request,
                )
                for a in raw_attr[:6]
            ]
            sources.append("Attraction search database")
            retrieval_used = True
            if intent == INTENT_PLAN_DAY:
                raw_rest = search_svc.search_restaurants(RestaurantSearchRequest(location=destination))
                restaurants = [
                    self._to_unified_restaurant(r, intent=INTENT_RESTAURANTS, limited_coverage=source_status == SOURCE_SAMPLE_DATA)
                    for r in raw_rest[:4]
                ]

        elif intent == INTENT_HOTELS:
            try:
                check_in = date.fromisoformat(trip.get("start_date", "")) if trip.get("start_date") else date.today()
            except (ValueError, TypeError):
                check_in = date.today()
            check_out = check_in + timedelta(days=1)
            raw_hotels = search_svc.search_hotels(
                HotelSearchRequest(location=destination, check_in=check_in, check_out=check_out, guests=1)
            )
            source_status = self._infer_source_status(raw_hotels)
            hotels = [self._to_unified_hotel(h, limited_coverage=source_status == SOURCE_SAMPLE_DATA) for h in raw_hotels[:6]]
            sources.append("Hotel search database")
            retrieval_used = bool(hotels)

        elif intent in {INTENT_BEST_AREA, INTENT_AREA_ADVICE}:
            best = self._derive_best_area(search_svc, destination, trip)
            if best:
                areas = [best]
            raw_attr = search_svc.search_attractions(AttractionSearchRequest(location=destination))
            extra = list({a.location for a in raw_attr[:10] if a.location and a.location != best})
            areas += extra[:4]
            source_status = self._infer_source_status(raw_attr)
            sources.append("Neighborhood analysis")
            retrieval_used = bool(areas)

        elif intent == INTENT_COMPARE:
            compare_areas = self._extract_compared_areas(user_query)
            if not compare_areas:
                compare_areas = self._default_compare_areas(destination)
            area_comparisons = self._build_area_comparisons(destination, compare_areas)
            areas = [item.area for item in area_comparisons]
            source_status = SOURCE_CURATED_STATIC if area_comparisons else SOURCE_NONE
            sources.append("Neighborhood comparison reference data")
            retrieval_used = True

        elif intent == INTENT_GENERAL_DESTINATION:
            raw_attr = search_svc.search_attractions(AttractionSearchRequest(location=destination))
            raw_rest = search_svc.search_restaurants(RestaurantSearchRequest(location=destination))
            source_status = self._infer_source_status([*raw_attr, *raw_rest])
            attractions = [
                self._to_unified_attraction(a, destination=destination, limited_coverage=source_status == SOURCE_SAMPLE_DATA)
                for a in raw_attr[:4]
            ]
            restaurants = [
                self._to_unified_restaurant(r, intent=INTENT_RESTAURANTS, limited_coverage=source_status == SOURCE_SAMPLE_DATA)
                for r in raw_rest[:3]
            ]
            sources.append("Destination research database")
            retrieval_used = True

        system_prompt = _RETRIEVAL_SYSTEM_PROMPT if retrieval_used else _SYSTEM_PROMPT
        prompt = self._build_search_prompt(
            trip, user_query, intent, restaurants, attractions, hotels, areas, warnings, area_comparisons
        )
        raw = self._call_claude(prompt, system_prompt=system_prompt)
        base = self._parse_response(raw)
        concise_response = self._concise_response(base.response, intent)

        response = ConciergeSearchResponse(
            response=concise_response,
            intent=intent,
            retrieval_used=retrieval_used,
            source_status=source_status,
            restaurants=restaurants,
            attractions=attractions,
            hotels=hotels,
            areas=areas,
            area_comparisons=area_comparisons,
            suggestions=base.suggestions,
            sources=sources,
            warnings=warnings,
        )
        self._save_message(
            trip_id,
            "assistant",
            response.response,
            structured_results=response.model_dump(mode="json"),
            client_message_id=f"{request_id}:assistant",
        )
        return response

    def list_messages(self, trip_id: UUID, user_id: UUID) -> List[ConciergeMessage]:
        self._fetch_trip(trip_id, user_id)
        try:
            rows = (
                self._db.table(MESSAGES_TABLE)
                .select("id,trip_id,client_message_id,role,content,structured_results,created_at")
                .eq("trip_id", str(trip_id))
                .order("created_at")
                .execute()
            )
            return [ConciergeMessage(**row) for row in (rows.data or [])]
        except Exception as exc:
            if self._is_missing_messages_table_error(exc):
                logger.warning(_MISSING_MESSAGES_TABLE_HINT)
                return []
            logger.exception("Failed to load concierge message history")
            raise

    # ------------------------------------------------------------------
    # Intent detection
    # ------------------------------------------------------------------

    def _detect_intent(self, user_query: str) -> str:
        q = user_query.lower()

        if _PLAN_DAY_PAT.search(q) or _DAY_NUMBER_PAT.search(q):
            return INTENT_PLAN_DAY
        if _MICHELIN_PAT.search(q):
            return INTENT_MICHELIN_RESTAURANTS
        if _HIDDEN_GEMS_PAT.search(q):
            return INTENT_HIDDEN_GEMS
        if _NIGHTLIFE_PAT.search(q):
            return INTENT_NIGHTLIFE
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
        if _COMPARE_PAT.search(q):
            return INTENT_COMPARE
        if _REWARDS_PAT.search(q):
            return INTENT_REWARDS_HELP
        return INTENT_GENERAL

    def _sample_nightlife_results(self, destination: str) -> List[UnifiedRestaurantResult]:
        city = (destination or "").lower()
        if not city.startswith("chicago"):
            return []
        picks = [
            {
                "name": "The Violet Hour",
                "category": "Cocktail Bar",
                "area": "Wicker Park",
                "rating": 9.0,
                "tags": ["Cocktails", "Date Night", "Classic"],
                "why": "Known for polished classic cocktails and a calm, conversation-friendly vibe.",
                "status": "closed",
                "last_verified_at": "2026-04-20",
                "verification_note": "Known closures should not be recommended in sample/static mode.",
            },
            {
                "name": "Kumiko",
                "category": "Speakeasy",
                "area": "West Loop",
                "rating": 9.2,
                "tags": ["Japanese-inspired", "Cocktails", "Reservations"],
                "why": "Precision cocktails and thoughtful tasting menus make this a top splurge pick.",
                "status": "open",
                "last_verified_at": None,
                "verification_note": "Static sample profile; verify current hours and status.",
            },
            {
                "name": "Cindy's Rooftop",
                "category": "Rooftop Bar",
                "area": "Loop",
                "rating": 8.7,
                "tags": ["Rooftop", "Views", "Group Friendly"],
                "why": "Panoramic skyline and lake views; easy option for pre- or post-dinner drinks.",
                "status": "unknown",
                "last_verified_at": None,
                "verification_note": "Static sample profile; verify current hours and status.",
            },
            {
                "name": "Three Dots and a Dash",
                "category": "Cocktail Bar",
                "area": "River North",
                "rating": 8.8,
                "tags": ["Tiki", "Nightlife", "Late Night"],
                "why": "Lively underground tiki bar with strong group energy and creative rum drinks.",
                "status": "unknown",
                "last_verified_at": None,
                "verification_note": "Static sample profile; verify current hours and status.",
            },
            {
                "name": "Webster's Wine Bar",
                "category": "Wine Bar",
                "area": "Logan Square",
                "rating": 8.6,
                "tags": ["Wine", "Cozy", "Neighborhood Favorite"],
                "why": "Excellent by-the-glass list for a lower-key night focused on wine and conversation.",
                "status": "unknown",
                "last_verified_at": None,
                "verification_note": "Static sample profile; verify current hours and status.",
            },
            {
                "name": "Revolution Brewing Taproom",
                "category": "Brewery",
                "area": "Logan Square",
                "rating": 8.4,
                "tags": ["Craft Beer", "Casual", "Group Friendly"],
                "why": "Best for local craft beer flights and relaxed hangouts after dinner.",
                "status": "unknown",
                "last_verified_at": None,
                "verification_note": "Static sample profile; verify current hours and status.",
            },
        ]
        cards: List[UnifiedRestaurantResult] = []
        for pick in picks:
            if pick.get("status") == "closed":
                continue
            maps_query = f"{pick['name']} {pick['area']} Chicago".replace(" ", "+")
            last_verified = pick.get("last_verified_at")
            verification_bits = []
            if last_verified:
                verification_bits.append(f"Last reviewed {last_verified}")
            if pick.get("verification_note"):
                verification_bits.append(str(pick["verification_note"]))
            cards.append(
                UnifiedRestaurantResult(
                    name=pick["name"],
                    source="Sample bar research data · verify hours and current status before booking.",
                    cuisine=pick["category"],
                    neighborhood=pick["area"],
                    rating=pick["rating"],
                    summary=(
                        f"{pick['why']} "
                        "Sample bar research data · verify hours and current status before booking."
                        + (f" {' '.join(verification_bits)}." if verification_bits else "")
                    ),
                    maps_link=f"https://maps.google.com/?q={maps_query}",
                    tags=pick["tags"],
                )
            )
        return cards

    def _extract_compared_areas(self, user_query: str) -> List[str]:
        q = (user_query or "").strip()
        if not q:
            return []
        if "compare" in q.lower():
            cleaned = re.sub(r"^\s*compare\s+", "", q, flags=re.IGNORECASE).strip()
            parts = [p.strip(" .?!,") for p in _COMPARE_SPLIT_PAT.split(cleaned) if p.strip()]
            if len(parts) >= 2:
                return parts[:2]
        parts = [p.strip(" .?!,") for p in _COMPARE_SPLIT_PAT.split(q) if p.strip()]
        if len(parts) >= 2:
            return parts[:2]
        return []

    def _default_compare_areas(self, destination: str) -> List[str]:
        city = (destination or "").lower()
        if city.startswith("chicago"):
            return ["River North", "West Loop"]
        if destination:
            return [f"{destination} City Center", f"{destination} Old Town"]
        return ["Area A", "Area B"]

    def _build_area_comparisons(self, destination: str, areas: List[str]) -> List[UnifiedAreaComparisonResult]:
        city = (destination or "").lower()
        chicago_profiles = {
            "river north": UnifiedAreaComparisonResult(
                area="River North",
                vibe="Energetic downtown core with nightlife, riverfront access, and polished high-rise feel.",
                best_for="First-time visitors wanting walkable dining and late-night options.",
                pros=["Largest concentration of bars and restaurants", "Easy rides to Loop and Magnificent Mile"],
                cons=["Can feel crowded and louder at night", "Hotels and drinks often price at a premium"],
                logistics="10–20 minutes to major sights by foot or short rides; strong transit coverage.",
                value_signal="Higher nightly rates and cocktail pricing than most neighborhoods.",
                recommendation="Best if nightlife and convenience matter more than quiet streets or budget."
            ),
            "west loop": UnifiedAreaComparisonResult(
                area="West Loop",
                vibe="Trend-forward dining district with converted warehouse blocks and design-heavy venues.",
                best_for="Food-focused travelers who want destination restaurants and a stylish base.",
                pros=["Exceptional restaurant density", "Great access to Fulton Market dining scene"],
                cons=["Fewer classic tourist landmarks in immediate walking range", "Peak dinner hours can be hectic"],
                logistics="Fast ride to Loop attractions; very walkable for restaurants and bars.",
                value_signal="Mid-to-high pricing, but often better value than River North luxury corridors.",
                recommendation="Best if top-tier dining is your priority and you do not need tourist sights at your doorstep."
            ),
        }
        results: List[UnifiedAreaComparisonResult] = []
        for area in areas[:2]:
            key = area.lower()
            if city.startswith("chicago") and key in chicago_profiles:
                results.append(chicago_profiles[key])
                continue
            results.append(
                UnifiedAreaComparisonResult(
                    area=area,
                    vibe=f"Distinct local area within {destination or 'the city'}; verify current block-by-block feel.",
                    best_for="Travelers choosing between location convenience and neighborhood character.",
                    pros=["Can reduce commute time if aligned to your itinerary", "Often offers a unique local atmosphere"],
                    cons=["Tradeoffs vary by exact block and time of day", "Pricing and transit convenience can vary a lot"],
                    logistics="Compare transit lines and walk times to your must-do spots before booking.",
                    value_signal="Check live hotel/short-stay rates because value shifts by season and events.",
                    recommendation="Choose the area that best matches your nightly plans and morning logistics."
                )
            )
        return results

    # ------------------------------------------------------------------
    # Result converters
    # ------------------------------------------------------------------

    def _infer_source_status(self, records: List[object]) -> str:
        if not records:
            return SOURCE_NONE
        sources = [str(getattr(item, "source", "")).lower() for item in records]
        if sources and all(src == "mock" for src in sources):
            return SOURCE_SAMPLE_DATA
        if any(src in {"live", "live_search", "api", "provider"} for src in sources):
            return SOURCE_LIVE_SEARCH
        return SOURCE_APP_DATABASE

    def _to_unified_restaurant(self, r, intent: str = INTENT_RESTAURANTS, limited_coverage: bool = False) -> UnifiedRestaurantResult:
        name = getattr(r, "name", "Restaurant")
        location = getattr(r, "location", "") or ""
        cuisine = getattr(r, "cuisine", "Restaurant")
        tags = list(getattr(r, "tags", []) or [])
        ai_score = getattr(r, "ai_score", None)
        michelin_status = getattr(r, "michelin_status", None)
        maps_query = f"{name} {location}".strip().replace(" ", "+")
        rating = getattr(r, "rating", None)
        rating_10 = round(rating * 2, 1) if rating is not None else None
        num_reviews = getattr(r, "num_reviews", None)
        price_level = getattr(r, "price_level", None)
        sentiment = getattr(r, "sentiment", None)

        price_text = None
        if price_level is not None:
            if price_level <= 1:
                price_text = "budget-friendly"
            elif price_level == 2:
                price_text = "mid-range"
            else:
                price_text = "splurge-level"

        review_signal = ""
        if rating_10 is not None:
            review_signal = f"{rating_10}/10 rating"
            if num_reviews:
                review_signal += f" across {num_reviews:,} reviews"
        elif num_reviews:
            review_signal = f"{num_reviews:,} reviews"

        occasion_fit = None
        if intent in {INTENT_ROMANTIC, INTENT_LUXURY_VALUE}:
            occasion_fit = "well suited for a special dinner"
        elif intent == INTENT_FAMILY_FRIENDLY:
            occasion_fit = "a practical pick for a relaxed group meal"
        elif intent == INTENT_HIDDEN_GEMS:
            occasion_fit = "a stronger local-style option than tourist-heavy picks"
        elif tags:
            occasion_fit = f"best if you want {tags[0].lower()}"

        summary_parts = [f"{name} is a strong {cuisine} option"]
        if location:
            summary_parts.append(f"in {location}")
        if review_signal:
            summary_parts.append(f"with a {review_signal}")
        if price_text:
            summary_parts.append(f"at a {price_text} price point")
        if michelin_status:
            summary_parts.append(f"and Michelin status ({michelin_status})")
        summary = " ".join(summary_parts).strip()
        if occasion_fit:
            summary += f"; {occasion_fit}"
        if sentiment and sentiment > 0.9 and "reviews" not in summary:
            summary += "; guest sentiment is very positive"
        if limited_coverage:
            summary += ", though source coverage is limited so verify hours and reservation links."
        else:
            summary += "."

        # Use first non-maps booking option URL
        booking_link = None
        booking_options = getattr(r, "booking_options", None) or []
        if booking_options:
            for opt in booking_options:
                url = getattr(opt, "url", None)
                if url and "maps" not in url:
                    booking_link = url
                    break
        else:
            for candidate in ("booking_url", "source_url", "url"):
                candidate_url = getattr(r, candidate, None)
                if candidate_url and "maps" not in candidate_url:
                    booking_link = candidate_url
                    break

        return UnifiedRestaurantResult(
            name=name,
            source="Restaurant database",
            michelin_status=michelin_status,
            cuisine=cuisine,
            neighborhood=location,
            rating=rating_10,
            review_count=num_reviews,
            summary=summary,
            maps_link=f"https://maps.google.com/?q={maps_query}",
            booking_link=booking_link,
            ai_score=ai_score,
            tags=tags[:4],
        )

    def _to_unified_attraction(
        self,
        a,
        destination: str = "",
        limited_coverage: bool = False,
        is_day_request: bool = False,
    ) -> UnifiedAttractionResult:
        name = getattr(a, "name", "Attraction")
        location = getattr(a, "location", "") or ""
        category = getattr(a, "category", "attraction")
        tags = list(getattr(a, "tags", []) or [])
        ai_score = getattr(a, "ai_score", None)
        rating = getattr(a, "rating", None)
        maps_query = f"{name} {location}".strip().replace(" ", "+")
        rating_10 = round(rating * 2, 1) if rating is not None else None
        description = getattr(a, "description", None)
        duration = getattr(a, "duration_minutes", None)
        price_level = getattr(a, "price_level", None)

        if description:
            extra = []
            if duration:
                h, m = divmod(duration, 60)
                extra.append(f"~{h}h visit" if h >= 1 else f"~{m} min visit")
            if price_level == 0:
                extra.append("free entry")
            if extra:
                description = description.rstrip(".") + ". " + " · ".join(extra)
        else:
            desc_parts = []
            if rating_10 is not None:
                if rating_10 >= 8.5:
                    desc_parts.append("highly rated attraction")
                elif rating_10 >= 7.0:
                    desc_parts.append(f"well-reviewed ({rating_10}/10)")
            if duration:
                h, m = divmod(duration, 60)
                desc_parts.append(f"plan ~{h}h" if h >= 1 else f"~{m} min visit")
            if price_level == 0:
                desc_parts.append("free entry")
            elif price_level == 1:
                desc_parts.append("low-cost entry")
            description = " · ".join(desc_parts) if desc_parts else None

        city_lower = (destination or "").lower()
        if city_lower.startswith("chicago"):
            description = (description or "").replace("harbour", "riverfront").replace("Harbour", "Riverfront")

        reason_parts = [f"{name} fits as a {category.replace('_', ' ')} stop"]
        if is_day_request:
            reason_parts.append("for Day 2-style pacing")
        if location:
            reason_parts.append(f"around {location}")
        if rating_10 is not None:
            reason_parts.append(f"with a {rating_10}/10 rating")
        if duration:
            reason_parts.append(f"and about {duration} minutes on site")
        reason = " ".join(reason_parts).strip()
        if limited_coverage:
            reason += "; source coverage is limited, so verify name, hours, and booking details."
        elif reason:
            reason += "."

        return UnifiedAttractionResult(
            name=name,
            source="Attraction database",
            category=category,
            description=reason or description,
            neighborhood=location,
            rating=rating_10,
            review_count=getattr(a, "num_reviews", None),
            address=getattr(a, "address", None),
            maps_link=f"https://maps.google.com/?q={maps_query}",
            ai_score=ai_score,
            tags=tags[:4],
        )

    def _to_unified_hotel(self, h, limited_coverage: bool = False) -> UnifiedHotelResult:
        name = getattr(h, "name", "Hotel")
        location = getattr(h, "location", "") or ""
        tags = list(getattr(h, "tags", []) or [])
        ai_score = getattr(h, "ai_score", None)
        maps_query = f"{name} {location}".strip().replace(" ", "+")
        area = getattr(h, "area_label", None)
        stars = getattr(h, "stars", None)
        price = getattr(h, "price_per_night", None)
        rating = getattr(h, "rating", None)
        rating_10 = round(rating * 2, 1) if rating is not None else None
        proximity_label = getattr(h, "proximity_label", None)
        savings = getattr(h, "savings_vs_best", None)
        tags = tags[:4]

        reason_parts = []
        # Location signal
        if area and "best" in area.lower():
            reason_parts.append("centrally located near top attractions")
        elif proximity_label:
            reason_parts.append(proximity_label.lower())
        elif area and area not in ("City", "Unknown", ""):
            reason_parts.append(f"located in {area}")
        # Star class signal
        if stars:
            s = int(round(stars))
            if s >= 5:
                reason_parts.append("5-star luxury class")
            elif s == 4:
                reason_parts.append("4-star upscale property")
            elif s == 3:
                reason_parts.append("3-star comfortable stay")
        # Price/value signal
        if price:
            if savings is not None and savings < -40:
                reason_parts.append(f"great value at ${int(price)}/night (below avg)")
            elif "Best Value" in tags or "Budget Friendly" in tags:
                reason_parts.append(f"strong value at ${int(price)}/night")
            elif price < 150:
                reason_parts.append(f"budget-friendly at ${int(price)}/night")
            elif price < 300:
                reason_parts.append(f"mid-range at ${int(price)}/night")
            else:
                reason_parts.append(f"premium at ${int(price)}/night")
        # Rating signal
        if rating_10 is not None:
            if rating_10 >= 9.0:
                reason_parts.append("outstanding guest reviews")
            elif rating_10 >= 8.0:
                reason_parts.append(f"highly rated ({rating_10}/10)")
            elif rating_10 >= 7.0:
                reason_parts.append(f"solid guest rating ({rating_10}/10)")
        # Tradeoff caveat from tags
        if "Far from action" in (area or ""):
            reason_parts.append("note: farther from city center")

        reason = "; ".join(reason_parts) if reason_parts else None
        if reason:
            reason = reason[0].upper() + reason[1:]
            if limited_coverage:
                reason += "; limited source coverage, verify amenities and live rates."

        # Booking URL — use a non-maps URL different from the map link
        booking_url = None
        booking_options = getattr(h, "booking_options", None) or []
        if booking_options:
            for opt in booking_options:
                url = getattr(opt, "url", None)
                if url and "maps" not in url:
                    booking_url = url
                    break
        else:
            for candidate in ("booking_url", "source_url", "url"):
                candidate_url = getattr(h, candidate, None)
                if candidate_url and "maps" not in candidate_url:
                    booking_url = candidate_url
                    break

        return UnifiedHotelResult(
            name=name,
            source="Hotel search",
            area_label=area,
            stars=stars,
            rating=rating_10,
            price_per_night=price,
            maps_link=f"https://maps.google.com/?q={maps_query}",
            booking_url=booking_url,
            reason=reason,
            ai_score=ai_score,
            tags=tags,
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
        area_comparisons: List[UnifiedAreaComparisonResult] = None,
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
            if intent == INTENT_MICHELIN_RESTAURANTS:
                source_label = "Michelin Guide"
            elif intent == INTENT_NIGHTLIFE:
                source_label = "sample nightlife data"
            else:
                source_label = "restaurant database"
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
            elif intent == INTENT_NIGHTLIFE:
                parts.append(
                    "\nIMPORTANT: These nightlife cards are already retrieved — do not say nightlife data was unavailable.\n\n"
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
        if area_comparisons:
            parts.append("Structured neighborhood comparison data:\n")
            for item in area_comparisons[:4]:
                parts.append(
                    f"- {item.area}: vibe={item.vibe} | best_for={item.best_for} | "
                    f"pros={'; '.join(item.pros)} | cons={'; '.join(item.cons)} | "
                    f"logistics={item.logistics} | value={item.value_signal} | verdict={item.recommendation}\n"
                )
            parts.append("\n")

        has_data = any([restaurants, attractions, hotels, areas, area_comparisons])
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
        elif intent == INTENT_COMPARE:
            parts.append(
                "\nIn 'response': structure as a direct side-by-side comparison. "
                "Extract the two things being compared from the user query. "
                "Format: '[Option A]: [2-3 key signals — vibe, best for, tradeoff]. "
                "[Option B]: [2-3 key signals]. "
                "Verdict: [one clear recommendation with who it suits best].' "
                "Be specific and decision-focused. Max 5 sentences total. No markdown. "
                "Do not reference restaurant cards unless the user explicitly asks for places."
            )
        elif intent == INTENT_HOTELS:
            parts.append(
                "\nIn 'response': open with a concise summary (1 sentence). "
                "Call out best value pick and best luxury/location pick by name. "
                "Note any relevant tradeoffs (location vs price). "
                "Max 2 sentences. Cards carry the detail — keep response brief."
            )
        else:
            parts.append(
                "\nIn 'response': start with a concise 1-sentence recommendation summary. "
                "Optionally add a second sentence for best overall / best value / top splurge. "
                "Keep it under 2 sentences — cards carry the detail."
            )

        return "".join(parts)

    def _save_message(
        self,
        trip_id: UUID,
        role: str,
        content: str,
        structured_results: Optional[dict] = None,
        client_message_id: Optional[str] = None,
    ) -> None:
        try:
            payload = {
                "trip_id": str(trip_id),
                "client_message_id": client_message_id,
                "role": role,
                "content": content.strip(),
                "structured_results": structured_results,
            }
            if client_message_id:
                existing = (
                    self._db.table(MESSAGES_TABLE)
                    .select("id")
                    .eq("client_message_id", client_message_id)
                    .limit(1)
                    .execute()
                )
                if existing.data:
                    self._db.table(MESSAGES_TABLE).update(payload).eq("id", existing.data[0]["id"]).execute()
                    return
                self._db.table(MESSAGES_TABLE).insert(payload).execute()
            else:
                self._db.table(MESSAGES_TABLE).insert(payload).execute()
        except Exception as exc:
            if self._is_missing_messages_table_error(exc):
                logger.warning(_MISSING_MESSAGES_TABLE_HINT)
                return
            if self._is_duplicate_message_error(exc):
                logger.info("Ignoring duplicate concierge message for client_message_id=%s", client_message_id)
                return
            logger.warning("Failed to persist concierge message: %s", exc)

    def _is_duplicate_message_error(self, exc: Exception) -> bool:
        code = str(getattr(exc, "code", "") or "").upper()
        if code in {"23505", "409"}:
            return True
        text = str(exc).lower()
        return "duplicate key value" in text or "unique constraint" in text

    def _is_missing_messages_table_error(self, exc: Exception) -> bool:
        code = str(getattr(exc, "code", "") or "").upper()
        if code == "PGRST205":
            return True
        text = str(exc).lower()
        return (
            "pgrst205" in text
            or "schema cache" in text
            or "could not find the table" in text
            or "concierge_messages" in text and "not found" in text
            or "relation" in text and "concierge_messages" in text and "does not exist" in text
        )

    def _concise_response(self, text: str, intent: str = "") -> str:
        cleaned = re.sub(r"\s+", " ", (text or "").strip())
        if not cleaned:
            return "I found strong options that match your request."
        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        # Keep summaries compact; cards carry detail.
        limit = 2
        short = " ".join(sentences[:limit]).strip()
        return short if short else cleaned[:400]

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
