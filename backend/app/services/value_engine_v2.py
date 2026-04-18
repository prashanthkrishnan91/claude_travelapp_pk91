"""Value Engine V2 — personalized CPP + value scoring with user preferences and transfer bonuses.

Scoring methodology (V2)
------------------------
Base CPP:
    cpp = (cash_price × 100) / points_cost

Adjusted CPP (best available transfer bonus applied):
    adjusted_points = points_cost / (1 + bonus_percent / 100)
    adjusted_cpp    = (cash_price × 100) / adjusted_points

Cash scenario:
    earn_value           = cash_price × earn_rate          (points earned if paying cash)
    effective_cash_cost  = cash_price − (earn_value × cpp_baseline / 100)

Opportunity cost (earn loss when using points instead of cash):
    opportunity_cost = cash_price × earn_rate × cpp_baseline / 100

Decision (CPP-based):
    adjusted_cpp > cpp_baseline  → "Points Better"
    adjusted_cpp ≤ cpp_baseline  → "Cash Better"

value_score (0–100) — weighted composite:
    • CPP component         (40 %): nonlinear curve — penalises below baseline,
                                    rapidly rewards above, capped at 2× baseline
    • Cash/points advantage (25 %): effective_cash_cost vs redemption_value
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
    • "Points Better"       → decision == "Points Better"
    • "Cash Better"         → decision == "Cash Better"
    • "High Opportunity Cost" → redemption_value exceeds effective_cash_cost by 30%+

Output fields:
    decision, cpp, adjusted_cpp, effective_cash_cost, opportunity_cost,
    best_card, transfer_partner, recommendation_reason
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
_DECISION_THRESHOLD = 0.15         # 15 % relative advantage required to declare a clear winner
_SWEET_SPOT_CPP_MULTIPLIER = 2.0   # adjusted_cpp must exceed baseline × this to earn "Sweet Spot"
_SWEET_SPOT_CONFIDENCE_BOOST = 15  # bonus added to confidence when "Sweet Spot" fires
_POOR_REDEMPTION_RATING_FLOOR = 3.5  # rating below this surfaces a "lower rating" tradeoff


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


def _best_card_for_points(
    user_cards: List[UserCardV2],
    item_name: str,
    transfer_bonuses: List[TransferBonusV2],
) -> Optional[str]:
    """Return card_key with the best transfer bonus for this item; fall back to highest earn rate."""
    best_bonus = 0
    best_card: Optional[str] = None
    for card in user_cards:
        for bonus in transfer_bonuses:
            if (
                bonus.issuer.lower() == card.issuer.lower()
                and bonus.partner.lower() == item_name.lower()
                and bonus.bonus_percent > best_bonus
            ):
                best_bonus = bonus.bonus_percent
                best_card = card.card_key
    if best_card:
        return best_card
    if user_cards:
        return max(user_cards, key=lambda c: c.earn_rate or 0).card_key
    return None


def _best_card_for_cash(user_cards: List[UserCardV2]) -> Optional[str]:
    """Return card_key with the highest earn rate for cash spending."""
    if not user_cards:
        return None
    return max(user_cards, key=lambda c: c.earn_rate or 0).card_key


def _best_transfer_partner_name(
    user_cards: List[UserCardV2],
    item_name: str,
    transfer_bonuses: List[TransferBonusV2],
) -> Optional[str]:
    """Return the partner name with the best active bonus for this item, or None."""
    issuers = {c.issuer.lower() for c in user_cards}
    best_bonus = 0
    best_partner: Optional[str] = None
    for bonus in transfer_bonuses:
        if (
            bonus.issuer.lower() in issuers
            and bonus.partner.lower() == item_name.lower()
            and bonus.bonus_percent > best_bonus
        ):
            best_bonus = bonus.bonus_percent
            best_partner = bonus.partner
    return best_partner


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


def _determine_decision(adjusted_cpp: Optional[float], baseline: float, points_cost: int) -> str:
    """Return 'Points Better' or 'Cash Better' based on adjusted CPP vs user's baseline."""
    if points_cost == 0 or adjusted_cpp is None:
        return "Cash Better"
    return "Points Better" if adjusted_cpp > baseline else "Cash Better"


def _compute_confidence(
    adjusted_cpp: Optional[float],
    baseline: float,
) -> int:
    """0–100 confidence in the recommendation.

    Two signals blended 60/40:
    1. Decisiveness (|cpp_ratio − 1|): ≥30 % → 100, 15–30 % → 60–99, <15 % → 0–59
    2. CPP strength:                   ≥1.5× baseline → 100, at baseline → 50, below → 0–49
    """
    cpp_ratio = (adjusted_cpp / baseline) if adjusted_cpp is not None else 1.0
    abs_diff = abs(cpp_ratio - 1.0)

    if abs_diff >= 0.30:
        decisiveness = 100
    elif abs_diff >= _DECISION_THRESHOLD:
        decisiveness = round(60 + (abs_diff - _DECISION_THRESHOLD) / _DECISION_THRESHOLD * 39)
    else:
        decisiveness = round(abs_diff / _DECISION_THRESHOLD * 59)

    if cpp_ratio >= 1.5:
        cpp_signal = 100
    elif cpp_ratio >= 1.0:
        cpp_signal = round(50 + (cpp_ratio - 1.0) / 0.5 * 50)
    else:
        cpp_signal = round(max(0.0, cpp_ratio * 50))

    return max(0, min(100, round(decisiveness * 0.6 + cpp_signal * 0.4)))


def _compute_tradeoffs(
    item: ItemV2,
    prefs: UserPreferencesV2,
    adjusted_cpp: Optional[float],
    redemption_value: Optional[float],
    effective_cash_cost: Optional[float],
    excess_layovers: int,
    is_flight: bool,
) -> List[str]:
    """Build a list of 'why not' strings surfacing notable downsides."""
    tradeoffs: List[str] = []

    # Excess layovers
    if excess_layovers > 0 and is_flight:
        pref_label = "nonstop" if prefs.max_layovers == 0 else f"{prefs.max_layovers} layover(s)"
        tradeoffs.append(
            f"Requires {item.layovers} layover(s) vs your preference for {pref_label}"
        )

    # Below-par rating
    if item.rating is not None and item.rating < _POOR_REDEMPTION_RATING_FLOOR:
        tradeoffs.append(f"Lower rating ({item.rating}/5) than alternatives")

    # High redemption cost (points worth more than effective cash price)
    if (
        redemption_value is not None
        and effective_cash_cost is not None
        and effective_cash_cost > 0
        and redemption_value > effective_cash_cost * 1.3
    ):
        tradeoffs.append("High opportunity cost for points usage")

    # Poor redemption: CPP below user baseline while redeeming points
    if adjusted_cpp is not None and adjusted_cpp < prefs.cpp_baseline and item.points_cost > 0:
        tradeoffs.append("Points value below your baseline")

    return tradeoffs


def _build_reason(
    item: ItemV2,
    prefs: UserPreferencesV2,
    adjusted_cpp: Optional[float],
    bonus_pct: int,
    best_earn: float,
    preferred: bool,
    excess_layovers: int,
    is_flight: bool,
    decision: str,
    effective_cash_cost: Optional[float],
    opportunity_cost: Optional[float],
) -> str:
    """Compose a specific, actionable explanation matching the task reason examples."""
    parts: List[str] = []

    if decision == "Points Better":
        if adjusted_cpp is not None:
            if bonus_pct > 0:
                # e.g. "2.4 CPP with 20% transfer bonus — strong redemption"
                parts.append(
                    f"{adjusted_cpp:.1f} CPP with {bonus_pct}% transfer bonus — strong redemption"
                )
            else:
                vs = "above" if adjusted_cpp >= prefs.cpp_baseline else "below"
                parts.append(
                    f"{adjusted_cpp:.2f}¢/pt vs your {prefs.cpp_baseline:.1f}¢ baseline ({vs})"
                )
        # Earn loss note — e.g. "Using points loses $90 in potential rewards"
        if opportunity_cost is not None and opportunity_cost >= 1.0:
            parts.append(f"Using points loses ${opportunity_cost:.0f} in potential rewards")
    else:  # Cash Better
        # e.g. "Better to pay cash and earn 3x points"
        earn_label = f"{int(best_earn)}x" if best_earn == int(best_earn) else f"{best_earn}x"
        parts.append(f"Better to pay cash and earn {earn_label} points")
        if effective_cash_cost is not None and item.cash_price > 0:
            parts.append(f"Effective cost ${effective_cash_cost:.2f} after rewards")

    # Preference match
    if preferred:
        kind = "airline" if is_flight else "hotel"
        parts.append(f"Matches your {kind} preference ({item.name})")

    # Layover note
    if excess_layovers > 0:
        parts.append(f"{item.layovers} layover(s) exceeds your max of {prefs.max_layovers}")

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

        # 2. Best matching transfer bonus → adjusted CPP via adjusted_points
        bonus_pct = _best_bonus_pct(req.user_cards, item.name, req.transfer_bonuses)
        adjusted_cpp: Optional[float] = None
        if cpp is not None and item.points_cost > 0:
            adjusted_points = item.points_cost / (1 + bonus_pct / 100)
            adjusted_cpp = round((item.cash_price * 100) / adjusted_points, 4)

        # 3. Cash vs points economics
        best_earn = _best_earn_rate(req.user_cards)
        earn_back_fraction = best_earn * prefs.cpp_baseline / 100
        effective_cash_cost: Optional[float] = None
        opportunity_cost: Optional[float] = None   # earn loss when using points
        redemption_value: Optional[float] = None   # value of points redeemed (internal)
        if item.cash_price > 0:
            effective_cash_cost = round(item.cash_price * (1.0 - earn_back_fraction), 4)
        if item.points_cost > 0 and item.cash_price > 0:
            opportunity_cost = round(item.cash_price * best_earn * prefs.cpp_baseline / 100, 4)
            redemption_value = round(item.points_cost * prefs.cpp_baseline / 100, 4)

        # 4. Decision: CPP vs user baseline
        decision = _determine_decision(adjusted_cpp, prefs.cpp_baseline, item.points_cost)

        # Best card and transfer partner for this decision
        if decision == "Points Better":
            best_card = _best_card_for_points(req.user_cards, item.name, req.transfer_bonuses)
            transfer_partner = _best_transfer_partner_name(req.user_cards, item.name, req.transfer_bonuses)
        else:
            best_card = _best_card_for_cash(req.user_cards)
            transfer_partner = None

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
        eff_cash_for_score = effective_cash_cost if effective_cash_cost is not None else item.cash_price
        rdem_val_for_score = redemption_value if redemption_value is not None else 0.0
        cash_adv_comp = (
            _cash_vs_points_component(eff_cash_for_score, rdem_val_for_score, item.cash_price)
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
        tags.append(decision)  # "Points Better" or "Cash Better"
        if (
            redemption_value is not None
            and effective_cash_cost is not None
            and effective_cash_cost > 0
            and redemption_value > effective_cash_cost * 1.3
        ):
            tags.append("High Opportunity Cost")

        # Poor Redemption: points redeemed below user's CPP baseline
        if adjusted_cpp is not None and adjusted_cpp < prefs.cpp_baseline and item.points_cost > 0:
            tags.append("Poor Redemption")

        # Sweet Spot: CPP > 2× baseline AND item matches user preference
        sweet_spot = (
            adjusted_cpp is not None
            and adjusted_cpp > prefs.cpp_baseline * _SWEET_SPOT_CPP_MULTIPLIER
            and preferred
        )
        if sweet_spot:
            tags.append("Sweet Spot")

        # 9. Confidence
        confidence = _compute_confidence(adjusted_cpp, prefs.cpp_baseline)
        if sweet_spot:
            confidence = min(100, confidence + _SWEET_SPOT_CONFIDENCE_BOOST)

        # 10. Tradeoffs
        tradeoffs = _compute_tradeoffs(
            item=item,
            prefs=prefs,
            adjusted_cpp=adjusted_cpp,
            redemption_value=redemption_value,
            effective_cash_cost=effective_cash_cost,
            excess_layovers=excess_layovers,
            is_flight=is_flight,
        )

        # 11. Recommendation reason
        reason = _build_reason(
            item=item,
            prefs=prefs,
            adjusted_cpp=adjusted_cpp,
            bonus_pct=bonus_pct,
            best_earn=best_earn,
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
            decision=decision,
            confidence=confidence,
            tags=tags,
            recommendation_reason=reason,
            tradeoffs=tradeoffs,
            effective_cash_cost=effective_cash_cost,
            opportunity_cost=opportunity_cost,
            best_card=best_card,
            transfer_partner=transfer_partner,
        )

    def score_batch(self, requests: List[ValueEngineV2Request]) -> List[ValueEngineV2Result]:
        """Score a list of travel options, preserving input order."""
        return [self.score(req) for req in requests]
