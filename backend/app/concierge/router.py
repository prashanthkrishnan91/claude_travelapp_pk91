"""Two-stage prompt router for Concierge typed responses."""

import logging
import re
from typing import Dict, Literal

from pydantic import BaseModel

ResponseType = Literal["place_recommendations", "trip_advice", "unsupported"]

logger = logging.getLogger(__name__)

_PLACE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bhotel(s)?\b",
        r"\brestaurant(s)?\b",
        r"\bcafe(s)?\b",
        r"\bbrunch\b",
        r"\bbar(s)?\b",
        r"\bwhere to eat\b",
        r"\bbest .* in .*\b",
        r"\bthings to do\b",
        r"\battraction(s)?\b",
        r"\bneighborhood(s)?\b",
        r"\barea to stay\b",
        r"\bcompare\b",
    ]
]

_ADVICE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bpoints\b",
        r"\bcash\b",
        r"\bmiles\b",
        r"\breward(s)?\b",
        r"\btransfer partner(s)?\b",
        r"\bcard strategy\b",
        r"\bredeem\b",
        r"\baward flight(s)?\b",
        r"\bbooking timing\b",
        r"\binsurance\b",
        r"\bcancel(lation)? policy\b",
        r"\bbudget\b",
        r"\bvisa\b",
    ]
]


class RouteDecision(BaseModel):
    response_type: ResponseType
    stage1_prior: Dict[str, float]
    stage2_confidence: float
    code: str | None = None


def _score(prompt: str, patterns: list[re.Pattern], base: float) -> float:
    hits = sum(1 for pat in patterns if pat.search(prompt))
    if hits == 0:
        return base
    return base + (0.22 * hits)


def route_prompt(prompt: str, confidence_threshold: float = 0.55) -> RouteDecision:
    text = (prompt or "").strip()
    if not text:
        prior = {
            "place_recommendations": 0.05,
            "trip_advice": 0.05,
            "unsupported": 0.90,
        }
        logger.info("concierge.router.stage1_prior prior=%s prompt=%r", prior, prompt)
        return RouteDecision(
            response_type="unsupported",
            stage1_prior=prior,
            stage2_confidence=0.9,
            code="empty_prompt",
        )

    text_low = text.lower()
    if any(tok in text_low for tok in ("points", "miles", "cash", "redeem", "transfer partner", "award flight", "card strategy")):
        prior = {"place_recommendations": 0.1, "trip_advice": 0.8, "unsupported": 0.1}
        return RouteDecision(response_type="trip_advice", stage1_prior=prior, stage2_confidence=0.8)

    place_score = _score(text, _PLACE_PATTERNS, base=0.18)
    advice_score = _score(text, _ADVICE_PATTERNS, base=0.2)
    unsupported_score = 0.2

    total = place_score + advice_score + unsupported_score
    prior = {
        "place_recommendations": round(place_score / total, 4),
        "trip_advice": round(advice_score / total, 4),
        "unsupported": round(unsupported_score / total, 4),
    }
    logger.info("concierge.router.stage1_prior prior=%s prompt=%r", prior, prompt)

    best_type = max(prior, key=prior.get)
    confidence = prior[best_type]

    if confidence < confidence_threshold:
        return RouteDecision(
            response_type="unsupported",
            stage1_prior=prior,
            stage2_confidence=confidence,
            code="low_confidence",
        )

    return RouteDecision(
        response_type=best_type,  # type: ignore[arg-type]
        stage1_prior=prior,
        stage2_confidence=confidence,
    )
