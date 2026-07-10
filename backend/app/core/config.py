from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "Travel Concierge API"
    debug: bool = False
    log_level: str = "INFO"

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # OpenWeather
    openweather_api_key: str = ""

    # Live Research providers (used by concierge live-research layer)
    tavily_api_key: str = ""
    brave_search_api_key: str = ""
    serper_api_key: str = ""
    live_research_enabled: bool = True
    # Production hard kill switch: ALLOW_LIVE_RESEARCH_CALLS=false blocks all
    # Tavily/Serper/Brave/editorial calls from every Concierge path.
    # Takes precedence over live_research_enabled; live_research.py also reads
    # this directly via _live_research_calls_allowed() for legacy paths.
    allow_live_research_calls: bool = True
    live_research_cache_ttl_seconds: int = 1800
    live_research_timeout_seconds: float = 6.0
    concierge_router_v2: bool = False
    concierge_router_v2_confidence_threshold: float = 0.55
    trip_advice_builder_enabled: bool = False
    # PR 2: feature-flagged refine_previous card reuse for top_n, best_one, compare.
    # Default OFF. Enable in safe env after manual wife-test validation.
    concierge_context_v1_enabled: bool = False
    research_engine_require_google_verification: bool = False
    # PR fast-dynamic: feature-flagged fast pipeline for place searches.
    # Default OFF. Enable after validation.
    concierge_fast_dynamic_place_search_v1_enabled: bool = False
    # PR semantic-retrieval-v1: open-vocabulary semantic retrieval pipeline.
    # Default OFF. When ON, replaces fast_dynamic for new_search place asks.
    # Rollback: set CONCIERGE_SEMANTIC_RETRIEVAL_V1_ENABLED=false.
    concierge_semantic_retrieval_v1_enabled: bool = False
    yelp_api_key: str = ""
    foursquare_api_key: str = ""

    # Google Places — required gate for promoting article-research candidates
    # to addable concierge cards. Without this key, candidates remain as
    # research_source only.
    google_places_api_key: str = ""

    # Route Planning v1 — flag-gated route-estimate endpoint.
    # Default False. Rollback: set ROUTE_ESTIMATE_V1_ENABLED=false or omit the var.
    # Missing env var does not break startup (pydantic default=False handles it).
    route_estimate_v1_enabled: bool = False

    # Route Planning v1 — Google Routes adapter API key.
    # Optional; missing → fail-closed (not_configured). Does not break startup.
    # Server-side only; never exposed to the frontend. Used by google_routes_adapter.
    google_routes_api_key: str = ""

    # AI Route Planning v1 — PR A: read-only route-quality diagnostic.
    # Default False. Rollback: set ROUTE_QUALITY_DIAGNOSTIC_V1_ENABLED=false or omit.
    # No LLM call, no provider call, no itinerary write on any path — flag only
    # gates whether the diagnostic is computed at all.
    route_quality_diagnostic_v1_enabled: bool = False

    # AI Route Planning v1 — PR C: explicit user-approved reorder-proposal
    # apply contract. Default False. Rollback: set
    # ROUTE_REORDER_PROPOSAL_V1_ENABLED=false or omit.
    # No LLM call, no AI-generated suggestion, no auto-reorder. Writes only
    # the exact order the caller confirmed, only after ownership + item-set +
    # stale-order validation, only via the existing itinerary item position
    # field.
    route_reorder_proposal_v1_enabled: bool = False

    # AI Route Planning v1 — proposal generation triggered from "Plan My Day".
    # Default False. Rollback: set AI_ROUTE_REORDER_PROPOSAL_V1_ENABLED=false
    # or omit. Gates the read-only /route-reorder-proposal/generate endpoint
    # only — the apply write path stays governed by
    # route_reorder_proposal_v1_enabled above. Requires ANTHROPIC_API_KEY
    # (existing REASONING provider) and google_routes_api_key (existing
    # ROUTE_MATRIX provider); missing either fails closed to "unavailable",
    # never a guess.
    ai_route_reorder_proposal_v1_enabled: bool = False

    # Cost-control guardrails for expensive AI/search routes
    guardrail_ai_concierge_requests: int = 6
    guardrail_ai_concierge_window_seconds: int = 60
    guardrail_ai_concierge_dedupe_seconds: int = 8
    guardrail_ai_timeline_requests: int = 10
    guardrail_ai_timeline_window_seconds: int = 60
    guardrail_ai_timeline_dedupe_seconds: int = 5
    guardrail_search_requests: int = 20
    guardrail_search_window_seconds: int = 60
    guardrail_search_dedupe_seconds: int = 3

    # CORS
    cors_allow_all: bool = True
    cors_origins: List[str] = []

    @property
    def supabase_key(self) -> str:
        """Use service role key when available, fall back to anon key."""
        return self.supabase_service_role_key or self.supabase_anon_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
