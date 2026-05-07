"""Pydantic models for the AI concierge endpoint."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID



from pydantic import BaseModel


class ConciergeRequest(BaseModel):
    trip_id: UUID
    user_query: str
    day_number: Optional[int] = None


class Suggestion(BaseModel):
    type: Literal["attraction", "restaurant"]
    name: str
    reason: str


class ConciergeResponse(BaseModel):
    response: str
    suggestions: List[Suggestion]


# ── Intent constants ──────────────────────────────────────────────────────────

INTENT_MICHELIN_RESTAURANTS = "michelin_restaurants"
INTENT_RESTAURANTS = "restaurants"
INTENT_HIDDEN_GEMS = "hidden_gems"
INTENT_LUXURY_VALUE = "luxury_value"
INTENT_ROMANTIC = "romantic"
INTENT_FAMILY_FRIENDLY = "family_friendly"
INTENT_NIGHTLIFE = "nightlife"
INTENT_ATTRACTIONS = "attractions"
INTENT_HOTELS = "hotels"
INTENT_BEST_AREA = "best_area"
INTENT_PLAN_DAY = "plan_day"
INTENT_COMPARE = "compare"
INTENT_REWARDS_HELP = "rewards"
INTENT_GENERAL_DESTINATION = "general_destination_research"
INTENT_GENERAL = "general"

# Legacy aliases kept for backward compatibility
INTENT_ITINERARY_HELP = INTENT_PLAN_DAY
INTENT_AREA_ADVICE = INTENT_BEST_AREA

# ── Source status constants ───────────────────────────────────────────────────

SOURCE_CONFIRMED_MICHELIN = "confirmed_michelin"
SOURCE_CURATED_STATIC = "curated_static"
SOURCE_LIVE_SEARCH = "live_search"
SOURCE_APP_DATABASE = "app_database"
SOURCE_SAMPLE_DATA = "sample_data"
SOURCE_MIXED = "mixed"
SOURCE_UNAVAILABLE = "unavailable"
SOURCE_NONE = "none"

# ── Retrieval-first result models ─────────────────────────────────────────────

class SourceEvidence(BaseModel):
    """Structured evidence record from article/listicle extraction."""

    source_title: Optional[str] = None
    source_url: Optional[str] = None
    source_domain: Optional[str] = None
    source_rank: Optional[int] = None
    source_reason: Optional[str] = None
    source_evidence: Optional[str] = None
    source_category: Optional[str] = None
    neighborhood_hint: Optional[str] = None
    mention_count: int = 1


class GoogleVerification(BaseModel):
    """Normalized Google Places verification record attached to addable cards."""

    provider: Literal["google_places"] = "google_places"
    provider_place_id: Optional[str] = None
    name: Optional[str] = None
    formatted_address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    business_status: Optional[str] = None
    google_maps_uri: Optional[str] = None
    website_uri: Optional[str] = None
    rating: Optional[float] = None
    user_rating_count: Optional[int] = None
    types: List[str] = []
    confidence: Literal["high", "medium", "low", "unknown"] = "unknown"
    score: float = 0.0
    reason: Optional[str] = None
    failure_reason: Optional[str] = None


class VenueEnrichment(BaseModel):
    """Optional non-authoritative enrichment for already Google-verified places."""

    yelp_rating: Optional[float] = None
    yelp_review_count: Optional[int] = None
    yelp_review_excerpts: List[str] = []
    foursquare_categories: List[str] = []
    foursquare_tags: List[str] = []
    foursquare_popularity: Optional[float] = None




class ConciergeDisplayFields(BaseModel):
    """Canonical display contract for AI Concierge cards.

    Frontend should read these fields directly; no frontend-side reason
    generation is needed when this object is present.
    """
    display_name: str
    display_category: str
    display_meta_line: Optional[str] = None
    display_why: str
    display_source_summary: Optional[str] = None
    display_badges: List[str] = []
    addability: Literal["addable", "research_only", "closed"] = "addable"
    # Google-backed price display string — ready for UI, null when unavailable.
    # Formatted from priceRange first ("$10–20"), then priceLevel ("$$"), then null.
    display_price: Optional[str] = None
    # Debug trace fields — not shown in UI, used for pipeline observability
    display_category_source: Optional[str] = None  # "google_types" | "name_signal" | "intent_fallback"
    display_why_source: Optional[str] = None  # "llm_evidence_pack_v2_primary" | "llm_evidence_pack_v2_retry" | ...
    # Validated = True only when display_why was produced by the LLM/evidence-grounded path
    # and accepted by the validator. Frontend must NOT render Concierge Note when False.
    display_why_validated: bool = False


class PlaceSupportingDetails(BaseModel):
    rating: Optional[str] = None
    review_count: Optional[int] = None
    address: Optional[str] = None
    editorial_mentions: Optional[int] = None
    tags: List[str] = []
    # User-facing display fields (clean, never carry debug metadata).
    meta_line: Optional[str] = None
    why_pick: Optional[str] = None
    concierge_note: Optional[str] = None
    category_label: Optional[str] = None
    # Google-backed price signals — absent when Google didn't return them.
    price_level: Optional[str] = None   # e.g. "PRICE_LEVEL_MODERATE"
    price_range: Optional[Dict[str, Any]] = None  # Google PriceRange {startPrice, endPrice}


class UnifiedRestaurantResult(BaseModel):
    type: Literal["verified_place"] = "verified_place"
    name: str
    source: str = "Michelin Guide"
    michelin_status: Optional[str] = None  # "3 Stars" | "2 Stars" | "1 Star" | "Bib Gourmand" | "Selected"
    cuisine: Optional[str] = None
    neighborhood: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    summary: Optional[str] = None
    booking_link: Optional[str] = None
    maps_link: Optional[str] = None
    source_url: Optional[str] = None
    last_verified_at: Optional[str] = None
    confidence: Optional[Literal["high", "medium", "low", "unknown"]] = None
    ai_score: Optional[float] = None
    tags: List[str] = []
    verified_place: Optional[bool] = None
    verification_tier: Optional[Literal["primary", "secondary"]] = None
    google_verification: Optional[GoogleVerification] = None
    source_evidence: Optional[SourceEvidence] = None
    evidence: List[str] = []
    best_for_tags: List[str] = []
    evidence_count: int = 0
    source_badges: List[str] = []
    enrichment: Optional[VenueEnrichment] = None
    primary_reason: Optional[str] = None
    reason_source: Optional[str] = None
    why_pick: Optional[str] = None
    supporting_details: Optional[PlaceSupportingDetails] = None
    display: Optional[ConciergeDisplayFields] = None


class UnifiedAttractionResult(BaseModel):
    type: Literal["verified_place"] = "verified_place"
    name: str
    source: str = "Search"
    category: str
    description: Optional[str] = None
    neighborhood: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    address: Optional[str] = None
    maps_link: Optional[str] = None
    source_url: Optional[str] = None
    last_verified_at: Optional[str] = None
    confidence: Optional[Literal["high", "medium", "low", "unknown"]] = None
    ai_score: Optional[float] = None
    tags: List[str] = []
    verified_place: Optional[bool] = None
    verification_tier: Optional[Literal["primary", "secondary"]] = None
    google_verification: Optional[GoogleVerification] = None
    source_evidence: Optional[SourceEvidence] = None
    evidence: List[str] = []
    best_for_tags: List[str] = []
    evidence_count: int = 0
    source_badges: List[str] = []
    enrichment: Optional[VenueEnrichment] = None
    primary_reason: Optional[str] = None
    reason_source: Optional[str] = None
    why_pick: Optional[str] = None
    supporting_details: Optional[PlaceSupportingDetails] = None
    display: Optional[ConciergeDisplayFields] = None


class UnifiedHotelResult(BaseModel):
    type: Literal["verified_place"] = "verified_place"
    name: str
    source: str = "Search"
    area_label: Optional[str] = None
    stars: Optional[float] = None
    rating: Optional[float] = None
    price_per_night: Optional[float] = None
    maps_link: Optional[str] = None
    booking_url: Optional[str] = None
    source_url: Optional[str] = None
    last_verified_at: Optional[str] = None
    confidence: Optional[Literal["high", "medium", "low", "unknown"]] = None
    reason: Optional[str] = None
    ai_score: Optional[float] = None
    tags: List[str] = []
    verified_place: Optional[bool] = None
    verification_tier: Optional[Literal["primary", "secondary"]] = None
    google_verification: Optional[GoogleVerification] = None
    source_evidence: Optional[SourceEvidence] = None
    evidence: List[str] = []
    best_for_tags: List[str] = []
    evidence_count: int = 0
    source_badges: List[str] = []
    enrichment: Optional[VenueEnrichment] = None
    primary_reason: Optional[str] = None
    reason_source: Optional[str] = None
    why_pick: Optional[str] = None
    supporting_details: Optional[PlaceSupportingDetails] = None
    display: Optional[ConciergeDisplayFields] = None


class UnifiedResearchSourceResult(BaseModel):
    type: Literal["research_source"] = "research_source"
    title: str
    source: str = "Live search"
    source_type: Literal["article_listicle_blog_directory", "neighborhood_area", "generic_info_source"] = "generic_info_source"
    summary: Optional[str] = None
    source_url: Optional[str] = None
    neighborhood: Optional[str] = None
    last_verified_at: Optional[str] = None
    confidence: Optional[Literal["high", "medium", "low", "unknown"]] = None
    trip_addable: bool = False
    venues_discovered: int = 0


class UnifiedAreaComparisonResult(BaseModel):
    area: str
    vibe: str
    best_for: str
    pros: List[str] = []
    cons: List[str] = []
    logistics: str
    value_signal: str
    recommendation: str
    source_url: Optional[str] = None
    last_verified_at: Optional[str] = None


# ── Request / Response ────────────────────────────────────────────────────────

class ConciergeSearchRequest(BaseModel):
    trip_id: UUID
    user_query: str
    client_message_id: Optional[str] = None


class ConciergeCacheClearRequest(BaseModel):
    trip_id: UUID
    destination: Optional[str] = None


class ConciergeCacheClearResponse(BaseModel):
    cleared: bool = True


class ConciergeSearchResponse(BaseModel):
    response: str
    intent: str
    retrieval_used: bool = False
    source_status: str = SOURCE_NONE
    cached: bool = False
    live_provider: Optional[str] = None
    restaurants: List[UnifiedRestaurantResult] = []
    attractions: List[UnifiedAttractionResult] = []
    hotels: List[UnifiedHotelResult] = []
    research_sources: List[UnifiedResearchSourceResult] = []
    areas: List[str] = []
    area_comparisons: List[UnifiedAreaComparisonResult] = []
    suggestions: List[Suggestion] = []
    sources: List[str] = []
    warnings: List[str] = []
    # PR 2: additive optional context-reuse metadata. Populated only when
    # concierge_context_v1_enabled is ON and cards are reused from prior pool.
    turn_mode: Optional[str] = None
    context_reuse: Optional[Dict[str, Any]] = None


class ConciergeDebugRequest(BaseModel):
    """[DEV-ONLY] Request model for the concierge debug-trace endpoint."""
    user_query: str
    location: str
    limit: int = 10


class ConciergeMessage(BaseModel):
    id: UUID
    trip_id: UUID
    client_message_id: Optional[str] = None
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    structured_results: Optional[Dict[str, Any]] = None
    created_at: datetime
