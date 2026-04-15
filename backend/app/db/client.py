"""Supabase client singleton exposed as a FastAPI dependency."""

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_supabase() -> Client:
    """Return a cached Supabase client for the lifetime of the process.

    The service-role key is preferred so the backend can bypass RLS when
    needed.  Swap for the anon key (and rely on RLS policies) once row-level
    security is fully configured.
    """
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)
