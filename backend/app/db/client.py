"""Supabase client singleton exposed as a FastAPI dependency.

Falls back to an in-memory mock client when Supabase credentials are not
configured so the app can run in development / CI without a real project.
"""

import logging
from functools import lru_cache

from app.core.config import get_settings

logger = logging.getLogger("travel_concierge.db")


@lru_cache
def get_supabase():
    """Return a cached DB client for the lifetime of the process.

    Priority:
    1. Real Supabase client when SUPABASE_URL + a key are set.
    2. In-memory MockSupabaseClient otherwise (dev/CI fallback).

    The service-role key is preferred so the backend can bypass RLS when
    needed.  Swap for the anon key (and rely on RLS policies) once row-level
    security is fully configured.
    """
    settings = get_settings()

    if settings.supabase_url and settings.supabase_key:
        try:
            from supabase import create_client
            client = create_client(settings.supabase_url, settings.supabase_key)
            logger.info("Supabase client initialised → %s", settings.supabase_url[:40])
            return client
        except Exception as exc:
            logger.warning("Supabase client creation failed (%s) — falling back to mock DB.", exc)

    from app.db.mock import get_mock_client
    return get_mock_client()
