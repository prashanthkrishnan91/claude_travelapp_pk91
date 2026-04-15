"""Compare endpoint — POST /compare scores and ranks multiple travel options."""

from fastapi import APIRouter

from app.models.value_score import (
    CompareRequest,
    CompareResponse,
    CompareResult,
    ItemV2,
    ValueEngineV2Request,
)
from app.services.value_engine_v2 import ValueEngineV2

router = APIRouter(prefix="/compare", tags=["compare"])

_engine = ValueEngineV2()


@router.post("", response_model=CompareResponse)
def compare_items(payload: CompareRequest) -> CompareResponse:
    """Score and rank 2–10 travel options side-by-side.

    Each item is scored using the V2 engine with the provided user preferences.
    Results are returned in the same order as the input items.

    **Output per item**
    - `name`, `type`, `price`, `points` — identifying fields
    - `cpp` — base cents-per-point (null when points_cost is 0)
    - `value_score` — composite 0–100 score
    - `tags` — e.g. "Best Value", "Best Points", "Luxury Pick"
    - `recommendation_reason` — human-readable explanation
    """
    results: list[CompareResult] = []
    for item_input in payload.items:
        req = ValueEngineV2Request(
            item=ItemV2(
                item_type=item_input.item_type,
                name=item_input.name,
                cash_price=item_input.cash_price,
                points_cost=item_input.points_cost,
                rating=item_input.rating,
                layovers=item_input.layovers,
            ),
            user_preferences=payload.user_preferences,
        )
        scored = _engine.score(req)
        results.append(
            CompareResult(
                id=item_input.id,
                name=item_input.name,
                type=item_input.item_type,
                price=item_input.cash_price,
                points=item_input.points_cost,
                cpp=scored.cpp,
                value_score=scored.value_score,
                tags=scored.tags,
                recommendation_reason=scored.recommendation_reason,
            )
        )
    return CompareResponse(results=results)
