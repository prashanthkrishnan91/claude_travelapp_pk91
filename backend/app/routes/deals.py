"""Deals feed endpoint — GET /deals/feed.

Scans the research cache, scores each result with ValueEngineV2, and returns
items where value_score >= 70 OR adjusted_cpp >= 2.0, personalised to the
calling user's preferences.
"""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter

from app.core.deps import DB, CurrentUserID
from app.models.deals import DealFeedItem, DealsFeedResponse
from app.models.value_score import ItemV2, UserPreferencesV2, ValueEngineV2Request
from app.services.value_engine_v2 import ValueEngineV2

router = APIRouter(prefix="/deals", tags=["deals"])

_engine = ValueEngineV2()

_HIGH_VALUE_SCORE = 70   # value_score threshold
_HIGH_CPP = 2.0          # adjusted CPP threshold (¢/pt)
_MAX_RESULTS = 20        # cap on returned deals


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_items(payload: object, cache_id: str) -> List[dict]:
    """Pull scorable dicts out of an arbitrary research_cache payload."""
    if isinstance(payload, list):
        raw_list = payload
    elif isinstance(payload, dict):
        raw_list = payload.get("results") or payload.get("items") or payload.get("data") or []
        if not raw_list:
            raw_list = [payload]
    else:
        return []

    items: List[dict] = []
    for i, raw in enumerate(raw_list):
        if not isinstance(raw, dict):
            continue

        title = raw.get("name") or raw.get("title") or ""
        if not title:
            continue

        items.append(
            {
                "item_id": raw.get("id") or f"{cache_id}_{i}",
                "title": title,
                "description": raw.get("description") or "",
                "cash_price": float(
                    raw.get("price")
                    or raw.get("cash_price")
                    or raw.get("price_per_night")
                    or 0
                ),
                "points_cost": int(
                    raw.get("points_estimate")
                    or raw.get("points_cost")
                    or raw.get("points_price")
                    or 0
                ),
                "rating": raw.get("rating"),
                "item_type": raw.get("type") or raw.get("item_type") or "activity",
                "layovers": raw.get("layovers"),
            }
        )
    return items


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.get("", response_model=DealsFeedResponse)
def get_deals_feed(db: DB, user_id: CurrentUserID) -> DealsFeedResponse:
    """Return personalised high-value deals from the research cache.

    **Filter logic**
    - value_score ≥ 70 **OR** adjusted_cpp ≥ 2.0 ¢/pt

    **Personalisation**
    - Scores are computed with the calling user's preferences (preferred airlines,
      hotels, CPP baseline).  Falls back to V2 defaults when no preferences are
      saved.

    Results are sorted by value_score descending, capped at 20 items.
    """
    # 1. Load user preferences (graceful fallback to defaults)
    try:
        prefs_row = (
            db.table("user_preferences")
            .select("*")
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        if prefs_row.data:
            row = prefs_row.data[0]
            prefs = UserPreferencesV2(
                preferred_airlines=row.get("preferred_airlines") or [],
                preferred_hotels=row.get("preferred_hotels") or [],
                max_layovers=row.get("max_layovers", 2),
                seat_class=row.get("seat_class", "economy"),
                hotel_class=row.get("hotel_class", 3),
                cpp_baseline=row.get("cpp_baseline", 1.8),
            )
        else:
            prefs = UserPreferencesV2()
    except Exception:
        prefs = UserPreferencesV2()

    # 2. Fetch unexpired research cache entries
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        cache_rows = (
            db.table("research_cache")
            .select("id, source, payload")
            .or_(f"expires_at.is.null,expires_at.gt.{now_iso}")
            .limit(200)
            .execute()
        )
    except Exception:
        return DealsFeedResponse(deals=[])

    # 3. Score and filter
    deals: List[DealFeedItem] = []

    for entry in cache_rows.data or []:
        raw_items = _extract_items(entry.get("payload", {}), entry["id"])

        for raw in raw_items:
            req = ValueEngineV2Request(
                item=ItemV2(
                    item_type=raw["item_type"],
                    name=raw["title"],
                    cash_price=raw["cash_price"],
                    points_cost=raw["points_cost"],
                    rating=raw["rating"],
                    layovers=raw.get("layovers"),
                ),
                user_preferences=prefs,
            )
            scored = _engine.score(req)

            high_value = scored.value_score >= _HIGH_VALUE_SCORE
            high_cpp = scored.adjusted_cpp is not None and scored.adjusted_cpp >= _HIGH_CPP

            if not (high_value or high_cpp):
                continue

            desc = raw["description"] or scored.recommendation_reason
            deals.append(
                DealFeedItem(
                    item_id=raw["item_id"],
                    title=raw["title"],
                    description=desc,
                    value_score=scored.value_score,
                    tags=scored.tags,
                )
            )

    # 4. Sort by value_score desc, cap results
    deals.sort(key=lambda d: d.value_score, reverse=True)
    return DealsFeedResponse(deals=deals[:_MAX_RESULTS])
