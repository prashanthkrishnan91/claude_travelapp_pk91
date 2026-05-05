"""Evidence harness for Reasoning Reliability v2.

Prints human-readable evidence tables covering all five scenarios:
  Table 1: Full success             — 6/6 validated from pass 1
  Table 2: Partial first-pass       — 1/6 from pass 1, retry recovers 5/6
  Table 3: Timeout + fallback       — primary silent, fallback fills all
  Table 4: Bad-template repair      — validator rejects pass-1 note, retry repairs
  Table 5: Target query matrix      — 7 queries × top-3 cards, all validated

Run:
  cd backend && python -m tests.evidence_harness_v2
"""

from __future__ import annotations

import json
import sys
import os
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

# ── ensure app is importable ─────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── shared fixtures ──────────────────────────────────────────────────────────

def _make_entity(
    name: str = "Test Brewery",
    place_id: str = "pid_test",
    types: Optional[List[str]] = None,
    rating: float = 4.5,
    review_count: int = 900,
    address: str = "100 W Riverwalk Dr, Chicago, IL",
    maps_uri: str = "https://maps.google.com/?cid=1",
    source_query: str = "breweries near the river Chicago",
):
    from app.concierge.place_entity_layer import PlaceEntity
    return PlaceEntity(
        place_id=place_id,
        name=name,
        types=types or ["brewery"],
        primary_type=(types[0] if types else "brewery"),
        rating=rating,
        user_rating_count=review_count,
        business_status="OPERATIONAL",
        formatted_address=address,
        google_maps_uri=maps_uri,
        website_uri=None,
        price_level=None,
        lat=41.88,
        lng=-87.63,
        source_query=source_query,
    )


_BREWERY_NAMES = [
    "The Northman Beer & Cider Garden",
    "Forbidden Root Restaurant & Brewery",
    "Goose Island Brewhouse",
    "Half Acre Beer Company",
    "Revolution Brewing",
    "Empirical Brewery",
]
_BREWERY_RATINGS  = [4.7, 4.6, 4.5, 4.6, 4.7, 4.4]
_BREWERY_REVIEWS  = [1344, 1958, 802, 750, 2100, 430]
_BREWERY_ADDRS = [
    "3291 N Milwaukee Ave, Chicago, IL",
    "1746 W Chicago Ave, Chicago, IL",
    "1800 N Clybourn Ave, Chicago, IL",
    "4257 N Lincoln Ave, Chicago, IL",
    "2323 N Milwaukee Ave, Chicago, IL",
    "1801 W Foster Ave, Chicago, IL",
]


def _make_brewery_cards(n: int = 6, query: str = "breweries near the river"):
    from app.concierge.frame_extractor import extract_frame
    from app.concierge.ranker import RankScore, build_evidence_bundle
    from app.concierge.safe_reason_builder import build_safe_reason

    frame = extract_frame(query, "Chicago")
    cards_data = []
    for i in range(n):
        entity = _make_entity(
            name=_BREWERY_NAMES[i % len(_BREWERY_NAMES)],
            place_id=f"pid_{i}",
            rating=_BREWERY_RATINGS[i % len(_BREWERY_RATINGS)],
            review_count=_BREWERY_REVIEWS[i % len(_BREWERY_REVIEWS)],
            address=_BREWERY_ADDRS[i % len(_BREWERY_ADDRS)],
            source_query="brewery Chicago near river",
        )
        score = RankScore(total=0.75, subtype_fit=0.90, geo_fit=0.6)
        ev = build_evidence_bundle(entity, frame, score)
        det = build_safe_reason(entity, ev, frame, score)
        cards_data.append((entity, ev, score, det))
    return cards_data, frame


def _valid_notes(n: int, names: List[str]) -> Dict[str, str]:
    templates = [
        "{name} focuses on craft ciders and ales with a lively Avondale neighborhood atmosphere.",
        "{name} blends botanical brewing with a gastropub menu, a strong pick for adventurous beer fans.",
        "{name} is the flagship Goose Island location with a wide tap list near Lincoln Park.",
        "{name} is a Logan Square taproom known for experimental small-batch releases and a laid-back vibe.",
        "{name} is a Northwest Side powerhouse with a massive taproom and year-round seasonal programs.",
        "{name} is a Bowmanville taproom that emphasizes local distribution and experimental batches.",
    ]
    return {str(i + 1): templates[i % len(templates)].format(name=names[i]) for i in range(n)}


# ── table renderer ───────────────────────────────────────────────────────────

_COLS = [
    ("scenario",             24),
    ("query",                34),
    ("card_index",            5),
    ("card_title",           36),
    ("rating",                6),
    ("review_count",          8),
    ("displayWhyValidated",  18),
    ("displayWhySource",     30),
    ("attemptCount",          8),
    ("modelUsed",            28),
    ("retryUsed",             9),
    ("fallbackModelUsed",    14),
    ("visible_concierge_note", 60),
]


def _header() -> str:
    parts = [name.ljust(width) for name, width in _COLS]
    return "| " + " | ".join(parts) + " |"


def _sep() -> str:
    parts = ["-" * width for _, width in _COLS]
    return "+-" + "-+-".join(parts) + "-+"


def _row(vals: Dict[str, str]) -> str:
    parts = []
    for name, width in _COLS:
        v = str(vals.get(name, ""))
        parts.append(v.ljust(width)[:width])
    return "| " + " | ".join(parts) + " |"


def _note_preview(note: str, width: int = 58) -> str:
    note = note.strip()
    if len(note) <= width:
        return note
    return note[: width - 1] + "…"


def _table_title(title: str) -> str:
    return f"\n{'=' * 130}\n  {title}\n{'=' * 130}"


def _run_scenario(
    scenario: str,
    query: str,
    n: int,
    mock_llm_fn,
) -> List[Dict[str, str]]:
    """Run build_reasons_with_retry with a mocked LLM and collect per-card rows."""
    from app.concierge.batched_reason_builder import build_reasons_with_retry

    cards_data, frame = _make_brewery_cards(n, query)

    _ENABLE_FLAG = patch("app.concierge.batched_reason_builder._flag_enabled", return_value=True)
    with _ENABLE_FLAG, patch(
        "app.concierge.batched_reason_builder._call_llm", side_effect=mock_llm_fn
    ):
        reasons, _ = build_reasons_with_retry(cards_data, frame)

    rows = []
    for i, (entity, _ev, _score, _det) in enumerate(cards_data):
        cr = reasons.get(str(i + 1))
        rows.append(
            {
                "scenario": scenario,
                "query": query[:34],
                "card_index": str(i + 1),
                "card_title": entity.name[:36],
                "rating": str(entity.rating),
                "review_count": str(entity.user_rating_count),
                "displayWhyValidated": str(cr.validated if cr else False),
                "displayWhySource": (cr.source if cr else "omitted")[:30],
                "attemptCount": str(cr.attempt_count if cr else 0),
                "modelUsed": (cr.model_used if cr else "")[:28],
                "retryUsed": str(cr.retry_used if cr else False),
                "fallbackModelUsed": str(cr.fallback_model_used if cr else False),
                "visible_concierge_note": _note_preview(cr.note if cr else ""),
            }
        )
    return rows


# ── Table 1: Full success ────────────────────────────────────────────────────

def table1_full_success() -> List[Dict[str, str]]:
    names = _BREWERY_NAMES[:6]
    llm_json = json.dumps(_valid_notes(6, names))

    call_count = 0
    def mock_llm(prompt, timeout, model=""):
        nonlocal call_count
        call_count += 1
        # Only called once — all 6 notes returned in pass 1
        return llm_json

    return _run_scenario("full_success", "breweries near the river", 6, mock_llm)


# ── Table 2: Partial first-pass, retry fills misses ──────────────────────────

def table2_partial_retry() -> List[Dict[str, str]]:
    names = _BREWERY_NAMES[:6]

    pass1_response = json.dumps({
        "1": (
            "The Northman Beer & Cider Garden is a celebrated Avondale spot "
            "known for its extensive cider and beer selection."
        )
    })
    # Retry subset has cards 2-6 from original, but the subset is re-indexed 1-5.
    retry_notes = {
        str(i + 1): (
            f"{names[i + 1]} is a well-regarded Chicago brewery with a distinctive "
            "tap list and loyal neighborhood following."
        )
        for i in range(5)
    }
    retry_response = json.dumps(retry_notes)

    call_count = 0
    def mock_llm(prompt, timeout, model=""):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return pass1_response
        return retry_response

    return _run_scenario("partial_retry", "breweries near the river", 6, mock_llm)


# ── Table 3: Primary timeout, fallback model fills all ───────────────────────

def table3_timeout_fallback() -> List[Dict[str, str]]:
    from app.concierge.batched_reason_builder import _PRIMARY_MODEL, _FALLBACK_MODEL

    names = _BREWERY_NAMES[:4]
    fallback_notes = {
        str(i + 1): (
            f"{names[i]} is a Chicago institution with a devoted craft-beer "
            "following and consistent quality."
        )
        for i in range(4)
    }
    fallback_json = json.dumps(fallback_notes)

    def mock_llm(prompt, timeout, model=""):
        resolved_model = model or _PRIMARY_MODEL
        if resolved_model == _PRIMARY_MODEL:
            return None   # timeout / no response
        if resolved_model == _FALLBACK_MODEL:
            return fallback_json
        return None

    return _run_scenario("timeout_fallback", "breweries near the river", 4, mock_llm)


# ── Table 4: Bad-template repair via retry ───────────────────────────────────

def table4_bad_template_repair() -> List[Dict[str, str]]:
    names = _BREWERY_NAMES[:3]

    # Pass 1 returns templates the validator will reject (name+rating+review count only)
    bad_notes = {
        str(i + 1): f"{names[i]} — 4.5★ from 900 reviews."
        for i in range(3)
    }
    # Retry provides genuinely useful notes
    repair_notes = {
        str(i + 1): (
            f"{names[i]} is a well-regarded Chicago taproom with a strong local following "
            "and rotating seasonal tap list."
        )
        for i in range(3)
    }

    call_count = 0
    def mock_llm(prompt, timeout, model=""):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return json.dumps(bad_notes)
        return json.dumps(repair_notes)

    return _run_scenario("bad_template_repair", "breweries near the river", 3, mock_llm)


# ── Table 5: Target query matrix ─────────────────────────────────────────────

_QUERY_MATRIX: List[Tuple[str, str, int, str]] = [
    ("breweries near the river",     "Chicago",     3, "brewery"),
    ("rooftop bars in the city",     "Chicago",     3, "bar"),
    ("best pizza spots",             "Chicago",     3, "restaurant"),
    ("romantic restaurants",         "Chicago",     3, "restaurant"),
    ("family-friendly attractions",  "Chicago",     3, "attraction"),
    ("hidden gems for locals",       "Chicago",     3, "restaurant"),
    ("best hotels near downtown",    "Chicago",     3, "hotel"),
]

_QUERY_CARD_NAMES: Dict[str, List[str]] = {
    "breweries near the river": [
        "The Northman Beer & Cider Garden", "Goose Island Brewhouse", "Half Acre Beer Company"
    ],
    "rooftop bars in the city": [
        "Cindy's Rooftop", "Raised - A Rooftop Bar", "The Lonesome Rose"
    ],
    "best pizza spots": [
        "Lou Malnati's Pizzeria", "Giordano's", "Pequod's Pizza"
    ],
    "romantic restaurants": [
        "Oriole", "Sepia", "Bavette's Bar & Boeuf"
    ],
    "family-friendly attractions": [
        "Shedd Aquarium", "Art Institute of Chicago", "Millennium Park"
    ],
    "hidden gems for locals": [
        "Giant", "Superkhana International", "Lost Lake"
    ],
    "best hotels near downtown": [
        "The Langham Chicago", "Viceroy Chicago", "Kimpton Gray Hotel"
    ],
}

_QUERY_VALID_NOTES: Dict[str, Dict[str, str]] = {
    "breweries near the river": {
        "1": "The Northman is an Avondale mainstay focused on ciders and ales with a lively outdoor garden.",
        "2": "Goose Island Brewhouse anchors the Clybourn Corridor with a broad tap list and pub-food menu.",
        "3": "Half Acre is a Logan Square staple prized for small-batch releases and an inviting taproom.",
    },
    "rooftop bars in the city": {
        "1": "Cindy's sits atop the Chicago Athletic Association with sweeping views of Millennium Park.",
        "2": "Raised offers a cocktail-forward rooftop experience twelve floors above the Loop.",
        "3": "The Lonesome Rose is a Wicker Park rooftop known for frozen margs and a lively weekend crowd.",
    },
    "best pizza spots": {
        "1": "Lou Malnati's is the gold standard for butter-crust deep-dish with multiple city locations.",
        "2": "Giordano's is the classic stuffed-pizza destination with a long legacy and consistent quality.",
        "3": "Pequod's caramelized-cheese crust has earned it a cult following among deep-dish devotees.",
    },
    "romantic restaurants": {
        "1": "Oriole is a West Loop destination celebrated for its intimate tasting-menu format and exceptional service.",
        "2": "Sepia occupies a converted 1890s print shop with warm lighting and an American-seasonal menu.",
        "3": "Bavette's is a moody River North chophouse favored for date nights and vintage cocktails.",
    },
    "family-friendly attractions": {
        "1": "Shedd Aquarium is a Lake Michigan institution with dolphin shows and beluga whale exhibits.",
        "2": "The Art Institute houses Grant Wood's American Gothic and Georges Seurat's Sunday on the Island.",
        "3": "Millennium Park is free year-round and anchored by Cloud Gate (The Bean) and the Crown Fountain.",
    },
    "hidden gems for locals": {
        "1": "Giant is a tiny Humboldt Park diner beloved for creative breakfast sandwiches and short lines.",
        "2": "Superkhana International serves refined Indian street food in a Logan Square dining room.",
        "3": "Lost Lake is a Humboldt Park tiki bar with house-made syrups and a lush, unpretentious vibe.",
    },
    "best hotels near downtown": {
        "1": "The Langham anchors the Michigan Avenue corridor with river views and Forbes Five-Star service.",
        "2": "Viceroy is a Gold Coast boutique hotel with a 1920s revival aesthetic and rooftop pool.",
        "3": "Kimpton Gray combines a historic LaSalle Street banking hall with contemporary design and a top-floor bar.",
    },
}


def _make_cards_for_query(query: str, destination: str, n: int, category: str):
    from app.concierge.frame_extractor import extract_frame
    from app.concierge.ranker import RankScore, build_evidence_bundle
    from app.concierge.safe_reason_builder import build_safe_reason

    frame = extract_frame(query, destination)
    names = _QUERY_CARD_NAMES.get(query, [f"Place {i+1}" for i in range(n)])[:n]
    ratings = [4.6, 4.5, 4.4][:n]
    reviews = [1200, 850, 600][:n]
    addrs = [
        "1 N Michigan Ave, Chicago, IL",
        "2 S Wabash Ave, Chicago, IL",
        "3 W Randolph St, Chicago, IL",
    ][:n]

    type_map = {
        "brewery": ["brewery"],
        "bar": ["bar"],
        "restaurant": ["restaurant"],
        "attraction": ["tourist_attraction"],
        "hotel": ["lodging"],
    }
    place_types = type_map.get(category, ["establishment"])

    cards_data = []
    for i in range(n):
        entity = _make_entity(
            name=names[i],
            place_id=f"pid_q{hash(query) % 1000}_{i}",
            types=place_types,
            rating=ratings[i],
            review_count=reviews[i],
            address=addrs[i],
            source_query=query,
        )
        score = RankScore(total=0.75, subtype_fit=0.85, geo_fit=0.5)
        ev = build_evidence_bundle(entity, frame, score)
        det = build_safe_reason(entity, ev, frame, score)
        cards_data.append((entity, ev, score, det))
    return cards_data, frame


def table5_query_matrix() -> List[Dict[str, str]]:
    from app.concierge.batched_reason_builder import build_reasons_with_retry

    all_rows = []
    _ENABLE_FLAG = patch("app.concierge.batched_reason_builder._flag_enabled", return_value=True)

    for query, destination, n, category in _QUERY_MATRIX:
        cards_data, frame = _make_cards_for_query(query, destination, n, category)
        notes_for_query = _QUERY_VALID_NOTES.get(query, {})
        llm_json = json.dumps(notes_for_query)

        def mock_llm(prompt, timeout, model="", _j=llm_json):
            return _j

        with _ENABLE_FLAG, patch(
            "app.concierge.batched_reason_builder._call_llm", side_effect=mock_llm
        ):
            reasons, _ = build_reasons_with_retry(cards_data, frame)

        names_list = _QUERY_CARD_NAMES.get(query, [])
        for i, (entity, _ev, _score, _det) in enumerate(cards_data):
            cr = reasons.get(str(i + 1))
            all_rows.append(
                {
                    "scenario": f"query_matrix",
                    "query": query[:34],
                    "card_index": str(i + 1),
                    "card_title": entity.name[:36],
                    "rating": str(entity.rating),
                    "review_count": str(entity.user_rating_count),
                    "displayWhyValidated": str(cr.validated if cr else False),
                    "displayWhySource": (cr.source if cr else "omitted")[:30],
                    "attemptCount": str(cr.attempt_count if cr else 0),
                    "modelUsed": (cr.model_used if cr else "")[:28],
                    "retryUsed": str(cr.retry_used if cr else False),
                    "fallbackModelUsed": str(cr.fallback_model_used if cr else False),
                    "visible_concierge_note": _note_preview(cr.note if cr else ""),
                }
            )
    return all_rows


# ── print utilities ──────────────────────────────────────────────────────────

def _print_table(title: str, rows: List[Dict[str, str]]) -> None:
    print(_table_title(title))
    print(_sep())
    print(_header())
    print(_sep())
    for row in rows:
        print(_row(row))
    print(_sep())

    # Summary
    total = len(rows)
    validated = sum(1 for r in rows if r["displayWhyValidated"] == "True")
    omitted = total - validated
    print(f"\n  Summary: {validated}/{total} validated, {omitted} omitted\n")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    print("\nReasoning Reliability v2 — Evidence Harness")
    print("=" * 130)

    try:
        rows1 = table1_full_success()
        _print_table("Table 1: Full Success — 6/6 validated from pass 1 (primary model)", rows1)
    except Exception as e:
        print(f"\n[ERROR] Table 1 failed: {e}")
        import traceback; traceback.print_exc()

    try:
        rows2 = table2_partial_retry()
        _print_table("Table 2: Partial First-Pass — 1/6 pass 1, retry recovers 5/6", rows2)
    except Exception as e:
        print(f"\n[ERROR] Table 2 failed: {e}")
        import traceback; traceback.print_exc()

    try:
        rows3 = table3_timeout_fallback()
        _print_table("Table 3: Timeout + Fallback Recovery — primary silent, fallback fills all", rows3)
    except Exception as e:
        print(f"\n[ERROR] Table 3 failed: {e}")
        import traceback; traceback.print_exc()

    try:
        rows4 = table4_bad_template_repair()
        _print_table("Table 4: Bad-Template Repair — validator rejects pass-1, retry repairs", rows4)
    except Exception as e:
        print(f"\n[ERROR] Table 4 failed: {e}")
        import traceback; traceback.print_exc()

    try:
        rows5 = table5_query_matrix()
        _print_table("Table 5: Target Query Matrix — 7 queries × top-3 cards", rows5)
    except Exception as e:
        print(f"\n[ERROR] Table 5 failed: {e}")
        import traceback; traceback.print_exc()

    print("\nEvidence harness complete.\n")


if __name__ == "__main__":
    main()
