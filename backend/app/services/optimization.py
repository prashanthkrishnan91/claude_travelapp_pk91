"""Trip Optimization Engine — scores and ranks all flight × hotel combinations.

Scoring methodology
-------------------
Flight score (0–100):
    75% ValueEngineV2 score  (CPP, cash/points advantage, preference, convenience/stops)
    25% duration score       (shorter flight → higher score)

Hotel score (0–100):
    70% ValueEngineV2 score  (CPP, cash/points advantage, rating, preference)
    30% location score       (proximity to best area, 0–100; 50 when unknown)

Rewards efficiency (0–100):
    Average of each item's adjusted-CPP-to-baseline ratio mapped onto 0–100 curve.
    Both "Points Better" + high CPP → near 100; no points data → neutral 50.

Trip score (0–100):
    40% flight score + 40% hotel score + 20% rewards efficiency
"""

from typing import List, Optional, Tuple

from app.models.optimization import (
    FlightInput,
    HotelInput,
    TripOption,
    TripOptimizationRequest,
    TripOptimizationResponse,
)
from app.models.value_score import (
    ItemV2,
    TransferBonusV2,
    UserCardV2,
    UserPreferencesV2,
    ValueEngineV2Request,
    ValueEngineV2Result,
)
from app.services.value_engine_v2 import ValueEngineV2

# Trip-level weights
_WEIGHT_FLIGHT = 0.40
_WEIGHT_HOTEL = 0.40
_WEIGHT_REWARDS = 0.20

# Duration scoring: score is 100 at or below this threshold, then decays
_DURATION_EXCELLENT_MIN = 90
_DURATION_PENALTY_PER_MIN = 0.08  # points lost per minute above threshold

# Location score when not provided
_LOCATION_SCORE_NEUTRAL = 50.0


# ---------------------------------------------------------------------------
# Per-item scoring helpers
# ---------------------------------------------------------------------------

def _score_flight(
    flight: FlightInput,
    user_cards: List[UserCardV2],
    prefs: UserPreferencesV2,
    transfer_bonuses: List[TransferBonusV2],
    engine: ValueEngineV2,
) -> Tuple[float, ValueEngineV2Result]:
    """Return (composite flight_score 0–100, V2 result)."""
    req = ValueEngineV2Request(
        item=ItemV2(
            item_type="flight",
            name=flight.airline,
            cash_price=flight.price,
            points_cost=flight.points_cost,
            layovers=flight.stops,
            rating=flight.rating,
            seat_class=flight.cabin_class,
        ),
        user_cards=user_cards,
        user_preferences=prefs,
        transfer_bonuses=transfer_bonuses,
    )
    v2_result = engine.score(req)

    # Shorter duration → higher score; no penalty below threshold
    excess_min = max(0, flight.duration_minutes - _DURATION_EXCELLENT_MIN)
    duration_score = max(0.0, min(100.0, 100.0 - excess_min * _DURATION_PENALTY_PER_MIN))

    composite = 0.75 * v2_result.value_score + 0.25 * duration_score
    return round(min(100.0, max(0.0, composite)), 2), v2_result


def _score_hotel(
    hotel: HotelInput,
    user_cards: List[UserCardV2],
    prefs: UserPreferencesV2,
    transfer_bonuses: List[TransferBonusV2],
    engine: ValueEngineV2,
) -> Tuple[float, ValueEngineV2Result]:
    """Return (composite hotel_score 0–100, V2 result)."""
    req = ValueEngineV2Request(
        item=ItemV2(
            item_type="hotel",
            name=hotel.name,
            cash_price=hotel.price,
            points_cost=hotel.points_estimate,
            rating=hotel.rating,
            hotel_class=int(hotel.stars) if hotel.stars else None,
        ),
        user_cards=user_cards,
        user_preferences=prefs,
        transfer_bonuses=transfer_bonuses,
    )
    v2_result = engine.score(req)

    loc_score = hotel.location_score if hotel.location_score is not None else _LOCATION_SCORE_NEUTRAL
    composite = 0.70 * v2_result.value_score + 0.30 * loc_score
    return round(min(100.0, max(0.0, composite)), 2), v2_result


def _rewards_efficiency(
    flight_v2: ValueEngineV2Result,
    hotel_v2: ValueEngineV2Result,
    baseline: float,
) -> float:
    """Combined rewards efficiency 0–100 from adjusted CPP vs baseline ratio."""

    def _eff(v2: ValueEngineV2Result) -> float:
        cpp = v2.adjusted_cpp
        if cpp is None or cpp <= 0:
            return 50.0  # neutral — no points data
        ratio = cpp / baseline
        if ratio >= 2.0:
            return 100.0
        if ratio >= 1.0:
            return 50.0 + 50.0 * (ratio - 1.0)
        return max(0.0, 50.0 * ratio)

    return round((_eff(flight_v2) + _eff(hotel_v2)) / 2.0, 2)


# ---------------------------------------------------------------------------
# Summary generation
# ---------------------------------------------------------------------------

def _generate_summary(
    flight: FlightInput,
    hotel: HotelInput,
    total_cost: float,
    rewards_efficiency: float,
    flight_v2: ValueEngineV2Result,
    hotel_v2: ValueEngineV2Result,
    is_cheapest: bool,
    is_top_ranked: bool,
) -> str:
    """One-line human-readable summary for a trip option."""
    f_tags = set(flight_v2.tags)
    h_tags = set(hotel_v2.tags)

    has_best_value = "Best Value" in f_tags or "Best Value" in h_tags
    has_luxury = "Luxury Pick" in h_tags or (hotel.stars is not None and hotel.stars >= 4.5)
    has_best_points = "Best Points" in f_tags or "Best Points" in h_tags
    has_sweet_spot = "Sweet Spot" in f_tags or "Sweet Spot" in h_tags
    points_better_both = (
        flight_v2.decision == "Points Better" and hotel_v2.decision == "Points Better"
    )
    high_rewards = rewards_efficiency >= 75
    central_hotel = hotel.location_score is not None and hotel.location_score >= 70

    if is_top_ranked and has_best_value and central_hotel:
        return "Best overall value with high CPP and central hotel"
    if is_top_ranked and has_best_value:
        return "Best overall value combining strong flight and hotel scores"
    if is_cheapest:
        short_flight = flight.duration_minutes < 300
        suffix = " and short flight" if short_flight else ""
        return f"Cheapest trip with solid hotel{suffix}"
    if has_luxury and (has_best_points or has_sweet_spot or points_better_both):
        return "Luxury option with great rewards redemption"
    if has_luxury:
        return "Luxury option with premium hotel and comfortable flight"
    if has_best_points or high_rewards:
        return "Strong rewards value with efficient points redemption across flight and hotel"
    return "Balanced option with good value across flight, hotel, and rewards"


# ---------------------------------------------------------------------------
# Internal combination holder
# ---------------------------------------------------------------------------

class _TripCombo:
    __slots__ = (
        "flight", "hotel", "flight_score", "hotel_score",
        "rewards_efficiency", "total_value_score", "flight_v2", "hotel_v2",
    )

    def __init__(
        self,
        flight: FlightInput,
        hotel: HotelInput,
        flight_score: float,
        hotel_score: float,
        rewards_eff: float,
        flight_v2: ValueEngineV2Result,
        hotel_v2: ValueEngineV2Result,
    ) -> None:
        self.flight = flight
        self.hotel = hotel
        self.flight_score = flight_score
        self.hotel_score = hotel_score
        self.rewards_efficiency = rewards_eff
        self.flight_v2 = flight_v2
        self.hotel_v2 = hotel_v2
        self.total_value_score = round(
            _WEIGHT_FLIGHT * flight_score
            + _WEIGHT_HOTEL * hotel_score
            + _WEIGHT_REWARDS * rewards_eff,
            2,
        )


# ---------------------------------------------------------------------------
# Public service
# ---------------------------------------------------------------------------

class TripOptimizationEngine:
    """Scores all flight × hotel pairs and returns the top 3 ranked options."""

    def optimize(self, req: TripOptimizationRequest) -> TripOptimizationResponse:
        engine = ValueEngineV2()
        prefs = req.user_preferences

        # Pre-score flights and hotels independently (O(n+m) V2 calls)
        scored_flights: List[Tuple[FlightInput, float, ValueEngineV2Result]] = [
            (f, *_score_flight(f, req.user_cards, prefs, req.transfer_bonuses, engine))
            for f in req.flights
        ]
        scored_hotels: List[Tuple[HotelInput, float, ValueEngineV2Result]] = [
            (h, *_score_hotel(h, req.user_cards, prefs, req.transfer_bonuses, engine))
            for h in req.hotels
        ]

        # Generate all combinations and compute trip scores
        combos: List[_TripCombo] = [
            _TripCombo(
                flight=f,
                hotel=h,
                flight_score=fs,
                hotel_score=hs,
                rewards_eff=_rewards_efficiency(fv2, hv2, prefs.cpp_baseline),
                flight_v2=fv2,
                hotel_v2=hv2,
            )
            for f, fs, fv2 in scored_flights
            for h, hs, hv2 in scored_hotels
        ]

        combos.sort(key=lambda c: c.total_value_score, reverse=True)
        top: List[_TripCombo] = combos[:3]

        if not top:
            return TripOptimizationResponse(best_options=[])

        min_cost = min(c.flight.price + c.hotel.price for c in top)
        top_score = top[0].total_value_score

        best_options: List[TripOption] = []
        for rank, combo in enumerate(top, start=1):
            total_cost = round(combo.flight.price + combo.hotel.price, 2)
            total_points = combo.flight.points_cost + combo.hotel.points_estimate
            is_cheapest = total_cost == min_cost
            is_top_ranked = combo.total_value_score == top_score

            summary = _generate_summary(
                flight=combo.flight,
                hotel=combo.hotel,
                total_cost=total_cost,
                rewards_efficiency=combo.rewards_efficiency,
                flight_v2=combo.flight_v2,
                hotel_v2=combo.hotel_v2,
                is_cheapest=is_cheapest,
                is_top_ranked=is_top_ranked,
            )

            best_options.append(
                TripOption(
                    rank=rank,
                    flight=combo.flight,
                    hotel=combo.hotel,
                    total_cost=total_cost,
                    total_points=total_points,
                    flight_score=combo.flight_score,
                    hotel_score=combo.hotel_score,
                    rewards_efficiency=combo.rewards_efficiency,
                    total_value_score=combo.total_value_score,
                    summary=summary,
                )
            )

        return TripOptimizationResponse(best_options=best_options)
