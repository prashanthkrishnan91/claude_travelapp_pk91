"""SavedItemsService — user-scoped save backing for Explore verticals.

Stage 2A Slice 2. Handles create (idempotent for provider-identity items),
list (active only), and soft-delete for the current user.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.core.supabase_retry import supabase_execute as _supabase_execute
from app.models.saved_items import SavedItem, SavedItemCreate

SAVED_ITEMS_TABLE = "saved_items"
logger = logging.getLogger(__name__)


class SavedItemsService:
    def __init__(self, db: Client) -> None:
        self.db = db

    def create(self, payload: SavedItemCreate, user_id: UUID) -> SavedItem:
        """Persist a saved item.

        Idempotent when provider + provider_place_id is present: returns the
        existing active row rather than inserting a duplicate.
        """
        if payload.provider and payload.provider_place_id:
            existing = self._find_active(
                user_id, payload.vertical, payload.provider, payload.provider_place_id
            )
            if existing:
                return existing

        row = {
            "user_id": str(user_id),
            "vertical": payload.vertical,
            "display_name": payload.display_name,
            "provider": payload.provider,
            "provider_place_id": payload.provider_place_id,
            "display_snapshot": payload.display_snapshot,
            "search_context": payload.search_context,
            "provenance": payload.provenance,
            "status": "active",
        }
        result = _supabase_execute(
            lambda: self.db.table(SAVED_ITEMS_TABLE).insert(row).execute(),
            context="saved_items.create",
        )
        return SavedItem(**result.data[0])

    def list_active(self, user_id: UUID, vertical: Optional[str] = None) -> List[SavedItem]:
        query = (
            self.db.table(SAVED_ITEMS_TABLE)
            .select("*")
            .eq("user_id", str(user_id))
            .eq("status", "active")
            .order("created_at", desc=True)
        )
        if vertical:
            query = query.eq("vertical", vertical)
        result = _supabase_execute(lambda: query.execute(), context="saved_items.list")
        return [SavedItem(**row) for row in result.data]

    def delete(self, item_id: UUID, user_id: UUID) -> None:
        """Soft-delete: set status='deleted'. 404 if not found or not owned."""
        self._ensure_owned(item_id, user_id)
        _supabase_execute(
            lambda: (
                self.db.table(SAVED_ITEMS_TABLE)
                .update({"status": "deleted"})
                .eq("id", str(item_id))
                .eq("user_id", str(user_id))
                .execute()
            ),
            context="saved_items.delete",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_active(
        self, user_id: UUID, vertical: str, provider: str, provider_place_id: str
    ) -> Optional[SavedItem]:
        result = _supabase_execute(
            lambda: (
                self.db.table(SAVED_ITEMS_TABLE)
                .select("*")
                .eq("user_id", str(user_id))
                .eq("vertical", vertical)
                .eq("provider", provider)
                .eq("provider_place_id", provider_place_id)
                .eq("status", "active")
                .limit(1)
                .execute()
            ),
            context="saved_items._find_active",
        )
        if result.data:
            return SavedItem(**result.data[0])
        return None

    def _ensure_owned(self, item_id: UUID, user_id: UUID) -> None:
        result = _supabase_execute(
            lambda: (
                self.db.table(SAVED_ITEMS_TABLE)
                .select("id")
                .eq("id", str(item_id))
                .eq("user_id", str(user_id))
                .eq("status", "active")
                .limit(1)
                .execute()
            ),
            context="saved_items._ensure_owned",
        )
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Saved item {item_id} not found",
            )
