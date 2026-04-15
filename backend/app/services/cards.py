from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.models import TravelCard, TravelCardCreate, TravelCardUpdate

TABLE = "travel_cards"


class CardsService:
    def __init__(self, db: Client) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def list_cards(self, user_id: UUID) -> List[TravelCard]:
        result = (
            self.db.table(TABLE)
            .select("*")
            .eq("user_id", str(user_id))
            .order("is_primary", desc=True)
            .order("created_at")
            .execute()
        )
        return [TravelCard(**row) for row in result.data]

    def get_card(self, card_id: UUID) -> TravelCard:
        result = (
            self.db.table(TABLE)
            .select("*")
            .eq("id", str(card_id))
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Card {card_id} not found",
            )
        return TravelCard(**result.data[0])

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def create_card(self, payload: TravelCardCreate) -> TravelCard:
        result = (
            self.db.table(TABLE)
            .insert(payload.model_dump(mode="json"))
            .execute()
        )
        return TravelCard(**result.data[0])

    def update_card(self, card_id: UUID, payload: TravelCardUpdate) -> TravelCard:
        data = payload.model_dump(mode="json", exclude_none=True)
        if not data:
            return self.get_card(card_id)
        result = (
            self.db.table(TABLE)
            .update(data)
            .eq("id", str(card_id))
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Card {card_id} not found",
            )
        return TravelCard(**result.data[0])

    def delete_card(self, card_id: UUID) -> None:
        self.db.table(TABLE).delete().eq("id", str(card_id)).execute()
