"""Narrow retry helper for transient Supabase/PostgREST HTTP/2 transport errors.

Supabase uses HTTP/2 via httpcore/httpx. Under load the connection pool can
emit `RemoteProtocolError: <ConnectionTerminated>` for in-flight requests that
race against a keep-alive closure.  These are transient and safe to retry once
or twice with a short exponential back-off.

What is retried:
- httpcore.RemoteProtocolError / httpx.RemoteProtocolError
- Any exception whose type name or message contains "RemoteProtocolError"
  or "ConnectionTerminated"

What is NOT retried (propagates immediately):
- fastapi.HTTPException (auth, not-found, RLS errors)
- Any other application-level exception (validation, data bugs)

Usage::

    result = supabase_execute(
        lambda: self.db.table("trips").select("*").eq("id", str(trip_id)).execute(),
        context="trips.get_trip",
    )
"""

import logging
import time

logger = logging.getLogger(__name__)

_MAX_DEFAULT_RETRIES = 2
_BASE_DELAY_SECONDS = 0.1


def _is_transient(exc: Exception) -> bool:
    """Return True for transient PostgREST/httpcore transport errors only."""
    # Check type hierarchy by name (avoids hard import of httpcore/httpx)
    for klass in type(exc).__mro__:
        name = klass.__qualname__
        if "RemoteProtocolError" in name or "ConnectionTerminated" in name:
            return True
    # Also check exception message for nested causes
    msg = str(exc)
    return "RemoteProtocolError" in msg or "ConnectionTerminated" in msg


def supabase_execute(execute_fn, *, context: str = "", max_retries: int = _MAX_DEFAULT_RETRIES):
    """Call execute_fn() with bounded retry on transient Supabase transport errors.

    Parameters
    ----------
    execute_fn:
        Zero-argument callable that ends with a supabase `.execute()` call and
        returns its result.
    context:
        Short label included in retry log lines (e.g. "itinerary.list_days").
    max_retries:
        Maximum number of additional attempts after the first failure (default 2).
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return execute_fn()
        except Exception as exc:
            # Never retry application-level HTTP exceptions (404, 403, 422…)
            try:
                from fastapi import HTTPException as _HTTPException
                if isinstance(exc, _HTTPException):
                    raise
            except ImportError:
                pass

            if _is_transient(exc):
                last_exc = exc
                logger.warning(
                    "[supabase_retry] transient_error attempt=%d/%d context=%s exc=%s",
                    attempt + 1,
                    max_retries + 1,
                    context,
                    exc,
                )
                if attempt < max_retries:
                    time.sleep(_BASE_DELAY_SECONDS * (2 ** attempt))
                    continue
            # Non-transient errors propagate immediately without retry
            raise

    # All retries exhausted — raise the last transient error
    raise last_exc  # type: ignore[misc]
