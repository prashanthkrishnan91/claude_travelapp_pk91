"""FastAPI dependency providers used across all routes."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from supabase import Client

from app.db.client import get_supabase


def get_current_user_id(x_user_id: Annotated[str, Header()]) -> UUID:
    """Extract the caller's user ID from the X-User-ID request header.

    This is a lightweight stand-in until JWT / Supabase Auth is wired up.
    Pass a valid UUID string in the header:
        X-User-ID: <uuid>
    """
    try:
        return UUID(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="X-User-ID header must be a valid UUID",
        )


# Convenient type aliases for route signatures
DB = Annotated[Client, Depends(get_supabase)]
CurrentUserID = Annotated[UUID, Depends(get_current_user_id)]
