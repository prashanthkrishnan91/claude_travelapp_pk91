"""Value scoring endpoints — /value/score (V2) and /value/score/batch (V1)."""

from fastapi import APIRouter

from app.models.value_score import (
    BatchValueScoreRequest,
    BatchValueScoreResponse,
    ValueEngineV2Request,
    ValueEngineV2Result,
)
from app.services.value_engine import ValueEngine
from app.services.value_engine_v2 import ValueEngineV2

router = APIRouter(prefix="/value", tags=["value"])

_engine_v1 = ValueEngine()
_engine_v2 = ValueEngineV2()


@router.post("/score", response_model=ValueEngineV2Result)
def score_item(payload: ValueEngineV2Request) -> ValueEngineV2Result:
    """Compute personalized CPP, adjusted CPP, value_score, tags, and recommendation reason.

    **Inputs**
    - `item` — flight or hotel with cash price, points cost, rating, layovers, seat/hotel class
    - `user_cards` — the user's cards (issuer + points balance); used to match transfer bonuses
    - `user_preferences` — preferred airlines/hotels, max layovers, seat class, hotel class, CPP baseline
    - `transfer_bonuses` — active issuer → partner bonuses (sourced from `transfer_bonuses` table)

    **Scoring logic**
    1. Base CPP = `cash_price × 100 / points_cost`
    2. Adjusted CPP = base CPP × `(1 + best_bonus_percent / 100)`
    3. CPP component (40 %): nonlinear curve — penalises below baseline, rapidly rewards above, capped at 2×
    4. Cash/points advantage (25 %): effective cash cost vs points opportunity cost
    5. Rating component (15 %): `rating / 5 × 100` (neutral 50 when unknown)
    6. Preference component (10 %): 100 if preferred airline/hotel, else 50
    7. Convenience component (10 %): layover score; −30 per excess layover

    **Outputs**
    - `cpp` — base cents-per-point before bonuses
    - `adjusted_cpp` — CPP after best available transfer bonus (via adjusted_points = points / (1 + bonus%))
    - `value_score` — composite score 0–100
    - `tags` — e.g. `"Best Value"`, `"Points Better"`, `"Cash Better"`, `"+25% Transfer Bonus"`
    - `recommendation_reason` — e.g. "2.4 CPP with 20% transfer bonus — strong redemption"
    - `decision` — `"Points Better"` or `"Cash Better"` (CPP vs user baseline)
    - `effective_cash_cost` — cash price minus earn-back rewards (USD)
    - `opportunity_cost` — earn value lost by using points instead of cash (USD)
    - `best_card` — card key giving best value for the recommended decision
    - `transfer_partner` — partner name for best bonus, or null
    """
    return _engine_v2.score(payload)


@router.post("/score/batch", response_model=BatchValueScoreResponse)
def score_batch(payload: BatchValueScoreRequest) -> BatchValueScoreResponse:
    """Score up to 50 travel options in a single request (V1 — basic CPP scoring).

    Results are returned in the same order as the input `items` list.
    """
    return BatchValueScoreResponse(results=_engine_v1.score_batch(payload.items))
