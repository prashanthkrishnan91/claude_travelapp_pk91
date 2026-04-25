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
    live_research_cache_ttl_seconds: int = 1800
    live_research_timeout_seconds: float = 6.0

    # Google Places — required gate for promoting article-research candidates
    # to addable concierge cards. Without this key, candidates remain as
    # research_source only.
    google_places_api_key: str = ""

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
