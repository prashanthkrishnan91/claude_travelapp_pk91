"""Place Details Provider — fetches Google Places Details for top-N ranked cards.

Fetches editorial_summary, review_snippets, and amenity flags (serves_beer,
outdoor_seating, live_music, good_for_groups) from the Google Places API v1
place-details endpoint.

Designed for post-ranking enrichment of the top N cards only (budget-gated).
Uses concurrent.futures for parallel card fetching with individual timeouts.
Falls back to None for any card that fails — enrichment is always optional.

No httpx dependency: uses urllib.request so it works in the test environment.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_DETAILS_ENDPOINT = "https://places.googleapis.com/v1/places/{place_id}"

# Fields we want from the Place Details API.
# Budget-conscious: only request fields useful for LLM reasoning.
_DETAILS_FIELD_MASK = ",".join([
    "editorialSummary",
    "reviews",
    "servesBeer",
    "servesWine",
    "servesCocktails",
    "outdoorSeating",
    "liveMusic",
    "goodForGroups",
])

# Safety limits
_MAX_REVIEW_SNIPPET_LEN = 120
_MAX_REVIEW_SNIPPETS = 2
_DEFAULT_TIMEOUT = 3.0
_DEFAULT_BUDGET_N = 4   # enrich at most top-N cards per turn


@dataclass
class PlaceDetailsResult:
    """Enrichment data from Google Place Details for one card."""
    place_id: str
    editorial_summary: Optional[str] = None
    review_snippets: List[str] = field(default_factory=list)
    serves_beer: Optional[bool] = None
    serves_wine: Optional[bool] = None
    serves_cocktails: Optional[bool] = None
    outdoor_seating: Optional[bool] = None
    live_music: Optional[bool] = None
    good_for_groups: Optional[bool] = None

    def has_differentiating_content(self) -> bool:
        """True when at least one specific differentiator was returned."""
        return bool(
            self.editorial_summary
            or self.review_snippets
            or self.serves_beer is not None
            or self.outdoor_seating is not None
            or self.live_music is not None
        )


def fetch_place_details(
    place_id: str,
    api_key: str,
    timeout: float = _DEFAULT_TIMEOUT,
) -> Optional[PlaceDetailsResult]:
    """Fetch Place Details for one place_id. Returns None on any error."""
    if not place_id or not api_key:
        return None

    url = _DETAILS_ENDPOINT.format(place_id=place_id)
    params = f"?fields={_DETAILS_FIELD_MASK}"
    full_url = url + params

    try:
        req = urllib.request.Request(
            full_url,
            headers={
                "X-Goog-Api-Key": api_key,
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        logger.debug("place_details: fetch_failed place_id=%s error=%s", place_id, exc)
        return None
    except Exception as exc:
        logger.debug("place_details: unexpected_error place_id=%s error=%s", place_id, exc)
        return None

    return _parse_details(place_id, raw)


def _parse_details(place_id: str, raw: dict) -> PlaceDetailsResult:
    """Parse raw API response into PlaceDetailsResult."""
    editorial_summary: Optional[str] = None
    es = raw.get("editorialSummary")
    if isinstance(es, dict):
        editorial_summary = (es.get("text") or "").strip() or None
    elif isinstance(es, str):
        editorial_summary = es.strip() or None

    # Review snippets: first N non-empty review texts
    review_snippets: List[str] = []
    for rv in (raw.get("reviews") or []):
        if len(review_snippets) >= _MAX_REVIEW_SNIPPETS:
            break
        if not isinstance(rv, dict):
            continue
        text_obj = rv.get("text") or rv.get("originalText") or {}
        text = (text_obj.get("text") if isinstance(text_obj, dict) else text_obj) or ""
        text = str(text).strip()
        if len(text) >= 20:
            review_snippets.append(text[:_MAX_REVIEW_SNIPPET_LEN])

    def _bool(key: str) -> Optional[bool]:
        v = raw.get(key)
        return bool(v) if v is not None else None

    return PlaceDetailsResult(
        place_id=place_id,
        editorial_summary=editorial_summary,
        review_snippets=review_snippets,
        serves_beer=_bool("servesBeer"),
        serves_wine=_bool("servesWine"),
        serves_cocktails=_bool("servesCocktails"),
        outdoor_seating=_bool("outdoorSeating"),
        live_music=_bool("liveMusic"),
        good_for_groups=_bool("goodForGroups"),
    )


def enrich_top_cards(
    entities: "List[Any]",
    api_key: str,
    budget_n: int = _DEFAULT_BUDGET_N,
    timeout: float = _DEFAULT_TIMEOUT,
) -> Dict[str, PlaceDetailsResult]:
    """Fetch Place Details for the top-N entities in parallel.

    Args:
        entities: List of PlaceEntity (or any object with .place_id).
        api_key:  Google Places API key.
        budget_n: Maximum number of cards to enrich.
        timeout:  Per-card HTTP timeout in seconds.

    Returns:
        Dict mapping place_id → PlaceDetailsResult for cards that succeeded.
        Empty dict when API key is absent or all fetches fail.
    """
    if not api_key or not entities:
        return {}

    top = entities[:budget_n]
    results: Dict[str, PlaceDetailsResult] = {}

    with ThreadPoolExecutor(max_workers=min(budget_n, 4)) as pool:
        futures = {
            pool.submit(fetch_place_details, e.place_id, api_key, timeout): e.place_id
            for e in top
        }
        for fut in as_completed(futures, timeout=timeout + 1.0):
            place_id = futures[fut]
            try:
                detail = fut.result()
                if detail is not None:
                    results[place_id] = detail
            except Exception as exc:
                logger.debug("place_details: future_error place_id=%s error=%s", place_id, exc)

    logger.info(
        "place_details: enriched %d/%d cards budget_n=%d",
        len(results), len(top), budget_n,
    )
    return results
