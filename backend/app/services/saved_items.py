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
from app.models.saved_items import VALID_VERTICALS, SavedItem, SavedItemCreate

SAVED_ITEMS_TABLE = "saved_items"
logger = logging.getLogger(__name__)


class SavedItemsService:
    def __init__(self, db: Client) -> None:
        self.db = db

    def create(self, payload: SavedItemCreate, user_id: UUID) -> SavedItem:
        """Persist a saved item.

        Idempotent when a provider identity is present:
        - provider + provider_place_id → place-based dedup (restaurants/attractions/hotels)
        - provider + provider_item_id  → offer/itinerary dedup (flights, non-place)
        Returns the existing active row rather than inserting a duplicate.
        """
        if payload.provider and payload.provider_place_id:
            existing = self._find_by_place(
                user_id, payload.vertical, payload.provider, payload.provider_place_id
            )
            if existing:
                return existing

        if payload.provider and payload.provider_item_id:
            existing = self._find_by_item(
                user_id, payload.vertical, payload.provider, payload.provider_item_id
            )
            if existing:
                return existing

        row = {
            "user_id": str(user_id),
            "vertical": payload.vertical,
            "display_name": payload.display_name,
            "provider": payload.provider,
            "provider_place_id": payload.provider_place_id,
            "provider_item_id": payload.provider_item_id,
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
        if vertical is not None and vertical not in VALID_VERTICALS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid vertical '{vertical}'. Must be one of: {sorted(VALID_VERTICALS)}",
            )
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

    def _find_by_place(
        self, user_id: UUID, vertical: str, provider: str, provider_place_id: str
    ) -> Optional[SavedItem]:
        """Dedup lookup for place-based identity (Google Places)."""
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
            context="saved_items._find_by_place",
        )
        if result.data:
            return SavedItem(**result.data[0])
        return None

    def _find_by_item(
        self, user_id: UUID, vertical: str, provider: str, provider_item_id: str
    ) -> Optional[SavedItem]:
        """Dedup lookup for non-place identity (flights, offer IDs)."""
        result = _supabase_execute(
            lambda: (
                self.db.table(SAVED_ITEMS_TABLE)
                .select("*")
                .eq("user_id", str(user_id))
                .eq("vertical", vertical)
                .eq("provider", provider)
                .eq("provider_item_id", provider_item_id)
                .eq("status", "active")
                .limit(1)
                .execute()
            ),
            context="saved_items._find_by_item",
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
