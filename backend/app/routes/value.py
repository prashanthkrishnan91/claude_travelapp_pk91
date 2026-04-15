"""Value scoring endpoints — /value/score and /value/score/batch."""

from fastapi import APIRouter

from app.models.value_score import (
    BatchValueScoreRequest,
    BatchValueScoreResponse,
    ValueScoreRequest,
    ValueScoreResult,
)
from app.services.value_engine import ValueEngine

router = APIRouter(prefix="/value", tags=["value"])

_engine = ValueEngine()


@router.post("/score", response_model=ValueScoreResult)
def score_item(payload: ValueScoreRequest) -> ValueScoreResult:
    """Compute CPP, value_score, and tags for a single travel option.

    **Inputs**
    - `cash_price` — cash cost in USD
    - `points_estimate` — estimated points required
    - `transfer_partners` — number of transfer partners available (default 0)
    - `rating` — 0–5 quality rating (optional)
    - `location` — human-readable location string (optional, reserved for future geo-scoring)

    **Outputs**
    - `cpp` — cents-per-point (`cash_price × 100 / points_estimate`); `null` when `points_estimate` is 0
    - `value_score` — composite score 0–100 (weighted: CPP 60 %, rating 25 %, partners 15 %)
    - `tags` — applicable labels: `"Best Value"`, `"Best Points"`, `"Luxury Pick"`
    """
    return _engine.score(payload)


@router.post("/score/batch", response_model=BatchValueScoreResponse)
def score_batch(payload: BatchValueScoreRequest) -> BatchValueScoreResponse:
    """Score up to 50 travel options in a single request.

    Results are returned in the same order as the input `items` list.
    """
    return BatchValueScoreResponse(results=_engine.score_batch(payload.items))
