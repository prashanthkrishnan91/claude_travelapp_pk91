"""Supabase JWKS-based JWT verification (ES256).

Fetches the public key set from Supabase once and caches it in memory.
All token verification goes through ``verify_token``; the FastAPI
dependency lives in ``deps.py``.
"""

import logging
import time

import requests
from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt

logger = logging.getLogger(__name__)

JWKS_URL = (
    "https://hgzggeatqtozwdouknek.supabase.co/auth/v1/.well-known/jwks.json"
)
SUPABASE_ISSUER = "https://hgzggeatqtozwdouknek.supabase.co/auth/v1"
SUPABASE_AUDIENCE = "authenticated"

# Module-level cache — populated on first use, never refreshed during the
# lifetime of the process (keys rotate rarely; restart clears the cache).
_jwks_cache: dict | None = None


def _fetch_jwks() -> dict:
    """Fetch JWKS from Supabase with one automatic retry."""
    for attempt in range(2):
        try:
            resp = requests.get(JWKS_URL, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            logger.info("JWKS fetched successfully (%d key(s))", len(data.get("keys", [])))
            return data
        except Exception as exc:
            if attempt == 0:
                logger.warning("JWKS fetch failed (attempt 1/2), retrying in 1 s: %s", exc)
                time.sleep(1)
            else:
                logger.error("JWKS fetch failed after retry: %s", exc)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Auth service unavailable: cannot retrieve JWKS. Please try again shortly.",
                ) from exc
    # Unreachable, but satisfies type checkers.
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="JWKS unavailable")


def get_jwks() -> dict:
    """Return the cached JWKS, fetching from Supabase on first call."""
    global _jwks_cache
    if _jwks_cache is None:
        _jwks_cache = _fetch_jwks()
    return _jwks_cache


def verify_token(token: str) -> dict:
    """Verify *token* against Supabase JWKS and return the decoded payload.

    Verifies:
    - Signature using ES256
    - ``iss`` == ``SUPABASE_ISSUER``
    - ``aud`` == ``SUPABASE_AUDIENCE``

    Raises ``HTTPException(401)`` on any verification failure.
    """
    jwks = get_jwks()
    try:
        payload: dict = jwt.decode(
            token,
            jwks,
            algorithms=["ES256"],
            issuer=SUPABASE_ISSUER,
            audience=SUPABASE_AUDIENCE,
        )
        user_id = payload.get("sub", "<unknown>")
        logger.info("Token validated — user_id=%s", user_id)
        return payload
    except ExpiredSignatureError:
        logger.warning("Token validation failed: token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as exc:
        logger.warning("Token validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )
