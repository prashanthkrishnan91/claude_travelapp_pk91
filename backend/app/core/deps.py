"""FastAPI dependency providers used across all routes."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from supabase import Client

from app.core.auth import verify_token
from app.db.client import get_supabase

logger = logging.getLogger(__name__)


def get_current_user_id(authorization: Annotated[str, Header()] = "") -> UUID:
    """Validate Supabase JWT (ES256/JWKS) and return the caller's user ID.

    Expects:
        Authorization: Bearer <supabase_access_token>
    """
    if not authorization.startswith("Bearer "):
        logger.warning("Auth failed: missing or malformed Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:]
    # verify_token raises HTTPException on any failure and logs the outcome.
    payload = verify_token(token)

    user_id_str = payload.get("sub")
    if not user_id_str:
        logger.warning("Auth failed: token payload missing 'sub' claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = UUID(user_id_str)
    logger.info("Request authenticated — user_id=%s", user_id)
    return user_id


# Convenient type aliases for route signatures
DB = Annotated[Client, Depends(get_supabase)]
CurrentUserID = Annotated[UUID, Depends(get_current_user_id)]
