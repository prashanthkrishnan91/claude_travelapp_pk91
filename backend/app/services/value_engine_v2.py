"""Value Engine V2 — personalized CPP + value scoring with user preferences and transfer bonuses.

Scoring methodology (V2)
------------------------
Base CPP:
    cpp = (cash_price × 100) / points_cost

Adjusted CPP (best available transfer bonus applied):
    bonus_multiplier = 1 + (best_bonus_percent / 100)
    adjusted_cpp = cpp × bonus_multiplier

value_score (0–100) — weighted composite:
    • CPP component       (60 %): min(100, adjusted_cpp / cpp_baseline × 100)
    • Rating component    (25 %): rating / 5.0 × 100  (neutral 50 when unknown)
    • Preference component(15 %): 100 if preferred airline/hotel, else 50 (neutral)

Deductions applied after weighting:
    • Layover penalty: −10 per layover exceeding user's max_layovers (flights only)

Tags (multiple can fire simultaneously):
    • "Best Value"         → value_score ≥ 70
    • "Best Points"        → adjusted_cpp ≥ 2.0
    • "Luxury Pick"        → rating ≥ 4.5
    • "Preferred Airline"  → flight name matches preferred_airlines
    • "Preferred Hotel"    → hotel name matches preferred_hotels
    • "+N% Transfer Bonus" → active bonus was applied
"""

from typing import List, Optional

from app.models.value_score import (
    ItemV2,
    TransferBonusV2,
    UserCardV2,
    UserPreferencesV2,
    ValueEngineV2Request,
    ValueEngineV2Result,
)

# ---------------------------------------------------------------------------
# Tunable constants
# ---------------------------------------------------------------------------

_BEST_VALUE_THRESHOLD = 70
_BEST_POINTS_CPP = 2.0
_LUXURY_RATING = 4.5

_WEIGHT_CPP = 0.60
_WEIGHT_RATING = 0.25
_WEIGHT_PREFERENCE = 0.15

_LAYOVER_PENALTY = 10  # score points deducted per excess layover


# ---------------------------------------------------------------------------
# Pure helper functions (stateless, easily unit-tested)
# ---------------------------------------------------------------------------

def _base_cpp(cash_price: float, points_cost: int) -> Optional[float]:
    """Return cents-per-point rounded to 4 dp, or None when points_cost is 0."""
    if not points_cost:
        return None
    return round((cash_price * 100) / points_cost, 4)


def _best_bonus_pct(
    user_cards: List[UserCardV2],
    item_name: str,
    transfer_bonuses: List[TransferBonusV2],
) -> int:
    """Return the highest active bonus_percent matching any user card issuer → item partner."""
    issuers = {c.issuer.lower() for c in user_cards}
    best = 0
    for bonus in transfer_bonuses:
        if bonus.issuer.lower() in issuers and bonus.partner.lower() == item_name.lower():
            best = max(best, bonus.bonus_percent)
    return best


def _is_preferred(item_name: str, preferred_list: List[str]) -> bool:
    """Return True if item_name fuzzy-matches any entry in preferred_list."""
    name_lower = item_name.lower()
    return any(
        p.lower() in name_lower or name_lower in p.lower()
        for p in preferred_list
    )


def _cpp_component(adjusted_cpp: Optional[float], baseline: float) -> float:
    """Normalise adjusted CPP to 0–100.  Returns 50 (neutral) when CPP is unknown."""
    if adjusted_cpp is None:
        return 50.0
    return min(100.0, (adjusted_cpp / baseline) * 100)


def _rating_component(rating: Optional[float]) -> float:
    """Normalise 0–5 rating to 0–100.  Returns 50 (neutral) when unknown."""
    if rating is None:
        return 50.0
    return (rating / 5.0) * 100


def _preference_component(preferred: bool) -> float:
    """100 when the item matches user preferences, 50 (neutral) otherwise."""
    return 100.0 if preferred else 50.0


def _build_reason(
    item: ItemV2,
    prefs: UserPreferencesV2,
    cpp: Optional[float],
    adjusted_cpp: Optional[float],
    bonus_pct: int,
    preferred: bool,
    excess_layovers: int,
    is_flight: bool,
) -> str:
    """Compose a human-readable explanation of the score."""
    parts: List[str] = []

    if adjusted_cpp is not None:
        vs_baseline = "above" if adjusted_cpp >= prefs.cpp_baseline else "below"
        parts.append(
            f"{adjusted_cpp:.2f}¢/pt adjusted CPP is {vs_baseline} your {prefs.cpp_baseline:.1f}¢ baseline"
        )
        if bonus_pct > 0 and cpp is not None:
            parts.append(f"+{bonus_pct}% transfer bonus applied (base {cpp:.2f}¢/pt)")

    if preferred:
        kind = "airline" if is_flight else "hotel"
        parts.append(f"{item.name} matches your preferred {kind}")

    if excess_layovers > 0:
        parts.append(
            f"{item.layovers} layover(s) exceeds your max of {prefs.max_layovers} "
            f"(−{excess_layovers * _LAYOVER_PENALTY} pts)"
        )

    if item.rating is not None:
        if item.rating >= 4.5:
            parts.append(f"Exceptional rating ({item.rating}/5)")
        elif item.rating >= 4.0:
            parts.append(f"Strong rating ({item.rating}/5)")

    if not parts:
        parts.append("Standard redemption — no standout value signals")

    return "; ".join(parts) + "."


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class ValueEngineV2:
    """Stateless V2 scoring service with user-preference personalisation."""

    def score(self, req: ValueEngineV2Request) -> ValueEngineV2Result:
        """Score a single travel option using user preferences and transfer bonuses."""
        item = req.item
        prefs = req.user_preferences
        is_flight = item.item_type.lower() == "flight"
        is_hotel = item.item_type.lower() == "hotel"

        # 1. Base CPP
        cpp = _base_cpp(item.cash_price, item.points_cost)

        # 2. Best matching transfer bonus
        bonus_pct = _best_bonus_pct(req.user_cards, item.name, req.transfer_bonuses)
        adjusted_cpp: Optional[float] = None
        if cpp is not None:
            adjusted_cpp = round(cpp * (1 + bonus_pct / 100), 4)

        # 3. Preference match
        preferred_list = (
            prefs.preferred_airlines if is_flight
            else prefs.preferred_hotels if is_hotel
            else []
        )
        preferred = _is_preferred(item.name, preferred_list)

        # 4. Weighted component scores
        cpp_comp = _cpp_component(adjusted_cpp, prefs.cpp_baseline)
        rating_comp = _rating_component(item.rating)
        pref_comp = _preference_component(preferred)

        raw = (
            cpp_comp * _WEIGHT_CPP
            + rating_comp * _WEIGHT_RATING
            + pref_comp * _WEIGHT_PREFERENCE
        )

        # 5. Layover penalty (flights only)
        excess_layovers = 0
        if is_flight and item.layovers is not None:
            excess_layovers = max(0, item.layovers - prefs.max_layovers)
        raw -= excess_layovers * _LAYOVER_PENALTY

        value_score = max(0, min(100, round(raw)))

        # 6. Tags
        tags: List[str] = []
        if value_score >= _BEST_VALUE_THRESHOLD:
            tags.append("Best Value")
        if adjusted_cpp is not None and adjusted_cpp >= _BEST_POINTS_CPP:
            tags.append("Best Points")
        if item.rating is not None and item.rating >= _LUXURY_RATING:
            tags.append("Luxury Pick")
        if is_flight and preferred:
            tags.append("Preferred Airline")
        if is_hotel and preferred:
            tags.append("Preferred Hotel")
        if bonus_pct > 0:
            tags.append(f"+{bonus_pct}% Transfer Bonus")

        # 7. Recommendation reason
        reason = _build_reason(
            item=item,
            prefs=prefs,
            cpp=cpp,
            adjusted_cpp=adjusted_cpp,
            bonus_pct=bonus_pct,
            preferred=preferred,
            excess_layovers=excess_layovers,
            is_flight=is_flight,
        )

        return ValueEngineV2Result(
            cpp=cpp,
            adjusted_cpp=adjusted_cpp,
            value_score=value_score,
            tags=tags,
            recommendation_reason=reason,
        )

    def score_batch(self, requests: List[ValueEngineV2Request]) -> List[ValueEngineV2Result]:
        """Score a list of travel options, preserving input order."""
        return [self.score(req) for req in requests]
