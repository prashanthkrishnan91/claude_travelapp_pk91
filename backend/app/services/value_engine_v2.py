"""Value Engine V2 — personalized CPP + value scoring with user preferences and transfer bonuses.

Scoring methodology (V2)
------------------------
Base CPP:
    cpp = (cash_price × 100) / points_cost

Adjusted CPP (best available transfer bonus applied):
    bonus_multiplier = 1 + (best_bonus_percent / 100)
    adjusted_cpp = cpp × bonus_multiplier

Cash vs Points:
    earn_back_fraction = best_earn_rate × cpp_baseline / 100
    effective_cash_cost = cash_price × (1 − earn_back_fraction)
    opportunity_cost = points_cost × cpp_baseline / 100

value_score (0–100) — weighted composite:
    • CPP component         (40 %): nonlinear curve — penalises below baseline,
                                    rapidly rewards above, capped at 2× baseline
    • Cash/points advantage (25 %): effective_cash_cost vs opportunity_cost
    • Rating component      (15 %): rating / 5.0 × 100  (neutral 50 when unknown)
    • Preference component  (10 %): 100 if preferred airline/hotel, else 50 (neutral)
    • Convenience component (10 %): layover score; −30 per excess layover

Tags (multiple can fire simultaneously):
    • "Best Value"          → value_score ≥ 70
    • "Best Points"         → adjusted_cpp ≥ 2.0
    • "Luxury Pick"         → rating ≥ 4.5
    • "Preferred Airline"   → flight name matches preferred_airlines
    • "Preferred Hotel"     → hotel name matches preferred_hotels
    • "+N% Transfer Bonus"  → active bonus was applied
    • "Points Better"       → decision == "Use Points"
    • "Cash Better"         → decision == "Pay Cash"
    • "High Opportunity Cost" → opportunity_cost exceeds effective_cash_cost by 30%+

Decision:
    "Use Points"  → points opportunity cost is ≥ 5% cheaper than effective cash cost
    "Pay Cash"    → effective cash cost is ≥ 5% cheaper than opportunity cost
    "Either"      → within 5% of each other
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

_WEIGHT_CPP = 0.40
_WEIGHT_CASH_ADV = 0.25
_WEIGHT_RATING = 0.15
_WEIGHT_PREFERENCE = 0.10
_WEIGHT_CONVENIENCE = 0.10

_LAYOVER_CONVENIENCE_PENALTY = 30  # component points deducted per excess layover (0–100 scale)
_DECISION_THRESHOLD = 0.05         # relative difference to declare a clear winner


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


def _best_earn_rate(user_cards: List[UserCardV2]) -> float:
    """Return the highest earn_rate multiplier across user cards (defaults to 1.0 if none set)."""
    rates = [c.earn_rate for c in user_cards if c.earn_rate is not None]
    return max(rates) if rates else 1.0


def _is_preferred(item_name: str, preferred_list: List[str]) -> bool:
    """Return True if item_name fuzzy-matches any entry in preferred_list."""
    name_lower = item_name.lower()
    return any(
        p.lower() in name_lower or name_lower in p.lower()
        for p in preferred_list
    )


def _cpp_component(adjusted_cpp: Optional[float], baseline: float) -> float:
    """Nonlinear CPP scoring with tiers.

    - Below baseline: penalised with a t^1.5 curve (0–50)
    - At baseline: neutral (50)
    - Baseline → 2× baseline: rapidly increasing via (t−1)^0.6 power curve (50→100)
    - Above 2× baseline: capped at 100
    Returns 50 (neutral) when CPP is unknown.
    """
    if adjusted_cpp is None:
        return 50.0
    t = adjusted_cpp / baseline  # ratio to baseline
    if t >= 2.0:
        return 100.0
    if t >= 1.0:
        # Rapidly increases from 50→100 as t goes 1→2.
        # At t=1.2 → ~66, t=1.5 → ~83, t=2.0 → 100.
        return min(100.0, 50.0 + 50.0 * ((t - 1.0) ** 0.6))
    # Below baseline: quadratic-ish penalty, 0 at t=0, 50 at t=1.
    return max(0.0, 50.0 * (t ** 1.5))


def _cash_vs_points_component(
    effective_cash_cost: float,
    opportunity_cost: float,
    cash_price: float,
) -> float:
    """Score 0–100 reflecting how much better points are vs paying cash.

    advantage = effective_cash_cost − opportunity_cost
    Positive → points are cheaper; Negative → cash is cheaper.
    Normalised as a fraction of cash_price, centred at 50.
    Returns 50 (neutral) when cash_price is 0 or points are unavailable.
    """
    if cash_price <= 0:
        return 50.0
    advantage = effective_cash_cost - opportunity_cost
    advantage_pct = advantage / cash_price  # roughly −1.0 to +1.0
    return max(0.0, min(100.0, 50.0 + advantage_pct * 50.0))


def _rating_component(rating: Optional[float]) -> float:
    """Normalise 0–5 rating to 0–100.  Returns 50 (neutral) when unknown."""
    if rating is None:
        return 50.0
    return (rating / 5.0) * 100


def _preference_component(preferred: bool) -> float:
    """100 when the item matches user preferences, 50 (neutral) otherwise."""
    return 100.0 if preferred else 50.0


def _convenience_component(excess_layovers: int) -> float:
    """0–100 score for travel convenience based on excess layovers."""
    return max(0.0, 100.0 - excess_layovers * _LAYOVER_CONVENIENCE_PENALTY)


def _determine_decision(
    effective_cash_cost: float,
    opportunity_cost: float,
    points_cost: int,
) -> str:
    """Return 'Use Points', 'Pay Cash', or 'Either'.

    Compares effective cash cost vs points opportunity cost.
    A ≥5% relative difference declares a clear winner.
    """
    if points_cost == 0:
        return "Pay Cash"
    denom = max(effective_cash_cost, opportunity_cost)
    if denom <= 0:
        return "Either"
    rel_diff = (effective_cash_cost - opportunity_cost) / denom
    if rel_diff >= _DECISION_THRESHOLD:
        return "Use Points"
    if rel_diff <= -_DECISION_THRESHOLD:
        return "Pay Cash"
    return "Either"


def _build_reason(
    item: ItemV2,
    prefs: UserPreferencesV2,
    cpp: Optional[float],
    adjusted_cpp: Optional[float],
    bonus_pct: int,
    preferred: bool,
    excess_layovers: int,
    is_flight: bool,
    decision: str,
    effective_cash_cost: Optional[float],
    opportunity_cost: Optional[float],
) -> str:
    """Compose a structured, specific explanation of the score."""
    parts: List[str] = []

    # CPP vs baseline
    if adjusted_cpp is not None:
        vs_baseline = "above" if adjusted_cpp >= prefs.cpp_baseline else "below"
        parts.append(
            f"{adjusted_cpp:.2f}¢/pt vs your {prefs.cpp_baseline:.1f}¢ baseline ({vs_baseline})"
        )
        if bonus_pct > 0 and cpp is not None:
            parts.append(f"+{bonus_pct}% transfer bonus active (base {cpp:.2f}¢/pt)")

    # Cash vs points outcome
    if effective_cash_cost is not None and opportunity_cost is not None:
        if decision == "Use Points":
            parts.append(
                f"Points outperform cash after accounting for rewards earning "
                f"(${opportunity_cost:.2f} opportunity cost vs ${effective_cash_cost:.2f} effective cash)"
            )
        elif decision == "Pay Cash":
            parts.append(
                f"Cash is more efficient — effective cost ${effective_cash_cost:.2f} "
                f"vs ${opportunity_cost:.2f} points opportunity cost"
            )
        else:
            parts.append(
                f"Points and cash offer comparable value "
                f"(${opportunity_cost:.2f} vs ${effective_cash_cost:.2f})"
            )

    # Preference match
    if preferred:
        kind = "airline" if is_flight else "hotel"
        parts.append(f"Matches your {kind} preference ({item.name})")

    # Layover note
    if excess_layovers > 0:
        parts.append(
            f"{item.layovers} layover(s) exceeds your max of {prefs.max_layovers}"
        )

    # Rating highlight
    if item.rating is not None:
        if item.rating >= 4.5:
            parts.append(f"Exceptional rating ({item.rating}/5)")
        elif item.rating >= 4.0:
            parts.append(f"Strong rating ({item.rating}/5)")

    if not parts:
        parts.append("Standard redemption — no standout value signals")

    return ". ".join(parts) + "."


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

        # 2. Best matching transfer bonus → adjusted CPP
        bonus_pct = _best_bonus_pct(req.user_cards, item.name, req.transfer_bonuses)
        adjusted_cpp: Optional[float] = None
        if cpp is not None:
            adjusted_cpp = round(cpp * (1 + bonus_pct / 100), 4)

        # 3. Cash vs points economics
        best_earn = _best_earn_rate(req.user_cards)
        earn_back_fraction = best_earn * prefs.cpp_baseline / 100
        effective_cash_cost: Optional[float] = None
        opportunity_cost: Optional[float] = None
        if item.cash_price > 0:
            effective_cash_cost = round(item.cash_price * (1.0 - earn_back_fraction), 4)
        if item.points_cost > 0:
            opportunity_cost = round(item.points_cost * prefs.cpp_baseline / 100, 4)

        # 4. Decision
        eff_cash = effective_cash_cost if effective_cash_cost is not None else item.cash_price
        opp_cost = opportunity_cost if opportunity_cost is not None else 0.0
        decision = _determine_decision(eff_cash, opp_cost, item.points_cost)

        # 5. Preference match
        preferred_list = (
            prefs.preferred_airlines if is_flight
            else prefs.preferred_hotels if is_hotel
            else []
        )
        preferred = _is_preferred(item.name, preferred_list)

        # 6. Excess layovers
        excess_layovers = 0
        if is_flight and item.layovers is not None:
            excess_layovers = max(0, item.layovers - prefs.max_layovers)

        # 7. Weighted component scores
        cpp_comp = _cpp_component(adjusted_cpp, prefs.cpp_baseline)
        cash_adv_comp = (
            _cash_vs_points_component(eff_cash, opp_cost, item.cash_price)
            if item.points_cost > 0
            else 50.0  # neutral when no points redemption available
        )
        rating_comp = _rating_component(item.rating)
        pref_comp = _preference_component(preferred)
        convenience_comp = _convenience_component(excess_layovers)

        raw = (
            cpp_comp * _WEIGHT_CPP
            + cash_adv_comp * _WEIGHT_CASH_ADV
            + rating_comp * _WEIGHT_RATING
            + pref_comp * _WEIGHT_PREFERENCE
            + convenience_comp * _WEIGHT_CONVENIENCE
        )
        value_score = max(0, min(100, round(raw)))

        # 8. Tags
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
        if decision == "Use Points":
            tags.append("Points Better")
        elif decision == "Pay Cash":
            tags.append("Cash Better")
        if (
            opportunity_cost is not None
            and effective_cash_cost is not None
            and effective_cash_cost > 0
            and opportunity_cost > effective_cash_cost * 1.3
        ):
            tags.append("High Opportunity Cost")

        # 9. Recommendation reason
        reason = _build_reason(
            item=item,
            prefs=prefs,
            cpp=cpp,
            adjusted_cpp=adjusted_cpp,
            bonus_pct=bonus_pct,
            preferred=preferred,
            excess_layovers=excess_layovers,
            is_flight=is_flight,
            decision=decision,
            effective_cash_cost=effective_cash_cost,
            opportunity_cost=opportunity_cost,
        )

        return ValueEngineV2Result(
            cpp=cpp,
            adjusted_cpp=adjusted_cpp,
            value_score=value_score,
            tags=tags,
            recommendation_reason=reason,
            decision=decision,
            effective_cash_cost=effective_cash_cost,
            opportunity_cost=opportunity_cost,
        )

    def score_batch(self, requests: List[ValueEngineV2Request]) -> List[ValueEngineV2Result]:
        """Score a list of travel options, preserving input order."""
        return [self.score(req) for req in requests]
