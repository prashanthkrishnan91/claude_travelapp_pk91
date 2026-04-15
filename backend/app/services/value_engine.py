"""Value Engine — compute CPP, value_score, and tags for travel options.

Scoring methodology
-------------------
CPP (cents-per-point):
    cpp = (cash_price × 100) / points_estimate

    Industry benchmarks used for normalisation:
    • ≥ 2.0 cpp  → exceptional redemption
    • ≥ 1.5 cpp  → excellent  (reference ceiling for the CPP component)
    • ≥ 1.0 cpp  → good
    • ≥ 0.5 cpp  → fair
    •  < 0.5 cpp → poor

value_score (0–100) — weighted sum of three independent components:
    • CPP component     (60 %): min(100, cpp / 1.5 × 100)
    • Rating component  (25 %): rating / 5.0 × 100  (neutral 50 when unknown)
    • Partner component (15 %): 0 / 50 / 75 / 100 by partner-count bracket

Tags (applied independently; multiple can fire simultaneously):
    • "Best Value"  → value_score ≥ 70
    • "Best Points" → cpp ≥ 1.5
    • "Luxury Pick" → rating ≥ 4.5
"""

from typing import List, Optional

from app.models.value_score import ValueScoreRequest, ValueScoreResult

# ---------------------------------------------------------------------------
# Tunable constants
# ---------------------------------------------------------------------------

_CPP_REFERENCE = 1.5       # CPP that maps to a perfect 100 on the CPP component
_BEST_VALUE_THRESHOLD = 70  # Minimum value_score for the "Best Value" tag
_BEST_POINTS_CPP = 1.5      # Minimum CPP for the "Best Points" tag
_LUXURY_RATING = 4.5        # Minimum rating for the "Luxury Pick" tag

_WEIGHT_CPP = 0.60
_WEIGHT_RATING = 0.25
_WEIGHT_PARTNERS = 0.15


# ---------------------------------------------------------------------------
# Pure helper functions (stateless, easily unit-tested)
# ---------------------------------------------------------------------------

def compute_cpp(cash_price: float, points_estimate: int) -> Optional[float]:
    """Return cents-per-point rounded to 4 decimal places, or None when points_estimate is 0."""
    if not points_estimate:
        return None
    return round((cash_price * 100) / points_estimate, 4)


def cpp_component(cpp: Optional[float]) -> float:
    """Normalise CPP to a 0–100 sub-score.  Returns 50 (neutral) when CPP is unknown."""
    if cpp is None:
        return 50.0
    return min(100.0, (cpp / _CPP_REFERENCE) * 100)


def rating_component(rating: Optional[float]) -> float:
    """Normalise a 0–5 rating to a 0–100 sub-score.  Returns 50 (neutral) when unknown."""
    if rating is None:
        return 50.0
    return (rating / 5.0) * 100


def partner_component(num_partners: int) -> float:
    """Map transfer-partner count to a 0–100 sub-score using a bracketed scale."""
    if num_partners <= 0:
        return 0.0
    if num_partners == 1:
        return 50.0
    if num_partners == 2:
        return 75.0
    return 100.0


def compute_tags(cpp: Optional[float], value_score: int, rating: Optional[float]) -> List[str]:
    """Return the list of tags that apply to this result (order: value → points → luxury)."""
    tags: List[str] = []
    if value_score >= _BEST_VALUE_THRESHOLD:
        tags.append("Best Value")
    if cpp is not None and cpp >= _BEST_POINTS_CPP:
        tags.append("Best Points")
    if rating is not None and rating >= _LUXURY_RATING:
        tags.append("Luxury Pick")
    return tags


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class ValueEngine:
    """Stateless scoring service — no database dependency required."""

    def score(self, req: ValueScoreRequest) -> ValueScoreResult:
        """Score a single travel option and return CPP, value_score, and tags."""
        cpp = compute_cpp(req.cash_price, req.points_estimate)

        raw = (
            cpp_component(cpp) * _WEIGHT_CPP
            + rating_component(req.rating) * _WEIGHT_RATING
            + partner_component(req.transfer_partners) * _WEIGHT_PARTNERS
        )
        value_score = max(0, min(100, round(raw)))
        tags = compute_tags(cpp, value_score, req.rating)

        return ValueScoreResult(cpp=cpp, value_score=value_score, tags=tags)

    def score_batch(self, requests: List[ValueScoreRequest]) -> List[ValueScoreResult]:
        """Score a list of travel options, preserving input order."""
        return [self.score(req) for req in requests]
