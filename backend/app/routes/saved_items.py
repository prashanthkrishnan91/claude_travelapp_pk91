"""Routes for saved_items — /saved-items (Stage 2A Slice 2)."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import DB, CurrentUserID
from app.models.saved_items import SavedItem, SavedItemCreate, SavedItemNoteUpdate, SavedItemVertical
from app.services.saved_items import SavedItemsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/saved-items", tags=["saved-items"])


@router.post("", response_model=SavedItem, status_code=201)
def create_saved_item(
    payload: SavedItemCreate,
    db: DB,
    user_id: CurrentUserID,
) -> SavedItem:
    """Save an item for the current user. Idempotent for provider-identity rows."""
    svc = SavedItemsService(db)
    return svc.create(payload, user_id)


@router.get("", response_model=List[SavedItem])
def list_saved_items(
    db: DB,
    user_id: CurrentUserID,
    vertical: Optional[SavedItemVertical] = Query(default=None),
) -> List[SavedItem]:
    """List active saved items for the current user, optionally filtered by vertical."""
    svc = SavedItemsService(db)
    return svc.list_active(user_id, vertical=vertical)


@router.patch("/{item_id}/note", response_model=SavedItem)
def update_saved_item_note(
    item_id: UUID,
    payload: SavedItemNoteUpdate,
    db: DB,
    user_id: CurrentUserID,
) -> SavedItem:
    """Update only the note field of a saved item owned by the current user.

    Accepts { note: string | null }. An empty or whitespace note clears to null.
    Returns the updated saved item. 404 if not found or not owned by this user.
    """
    svc = SavedItemsService(db)
    return svc.update_note(item_id, payload, user_id)


@router.delete("/{item_id}", status_code=204)
def delete_saved_item(
    item_id: UUID,
    db: DB,
    user_id: CurrentUserID,
) -> None:
    """Soft-delete a saved item owned by the current user."""
    svc = SavedItemsService(db)
    svc.delete(item_id, user_id)
