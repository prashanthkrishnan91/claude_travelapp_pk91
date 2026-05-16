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
