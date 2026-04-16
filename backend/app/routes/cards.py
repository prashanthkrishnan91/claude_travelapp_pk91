from typing import List
from uuid import UUID

from fastapi import APIRouter, status

from app.core.deps import DB, CurrentUserID
from app.models import TravelCard, TravelCardCreate, TravelCardUpdate
from app.services import CardsService

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("", response_model=List[TravelCard])
def list_cards(db: DB, user_id: CurrentUserID) -> List[TravelCard]:
    """Return all travel cards belonging to the authenticated user.

    Primary cards are sorted first, then by creation date.
    """
    return CardsService(db).list_cards(user_id)


@router.post("", response_model=TravelCard, status_code=status.HTTP_201_CREATED)
def create_card(payload: TravelCardCreate, db: DB, user_id: CurrentUserID) -> TravelCard:
    """Register a new travel card for a user. user_id is always taken from the JWT."""
    return CardsService(db).create_card(payload.model_copy(update={"user_id": user_id}))


@router.get("/{card_id}", response_model=TravelCard)
def get_card(card_id: UUID, db: DB) -> TravelCard:
    """Fetch a single travel card by ID."""
    return CardsService(db).get_card(card_id)


@router.patch("/{card_id}", response_model=TravelCard)
def update_card(card_id: UUID, payload: TravelCardUpdate, db: DB) -> TravelCard:
    """Partially update a travel card (e.g. sync points balance)."""
    return CardsService(db).update_card(card_id, payload)


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(card_id: UUID, db: DB) -> None:
    """Remove a travel card."""
    CardsService(db).delete_card(card_id)
