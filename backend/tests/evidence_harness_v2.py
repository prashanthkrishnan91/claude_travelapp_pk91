"""Evidence harness for Reasoning Reliability v2.

Prints human-readable evidence tables covering all five scenarios:
  Table 1: Full success             — 6/6 validated from pass 1
  Table 2: Partial first-pass       — 1/6 from pass 1, retry recovers 5/6
  Table 3: Timeout + fallback       — primary silent, fallback fills all
  Table 4: Bad-template repair      — validator rejects pass-1 note, retry repairs
  Table 5: Target query matrix      — 7 REQUIRED target queries × top-3 cards

Required target queries (Table 5):
  1. izakayas
  2. izakayas with waterfront views
  3. izakayas on Fulton Street
  4. best breweries
  5. best waterfront breweries
  6. breweries near the river
  7. taprooms with a view

Run:
  cd backend && python -m tests.evidence_harness_v2
"""

from __future__ import annotations

import json
import sys
import os
from typing import Dict, List, Optional, Tuple
from unittest.mock import patch

# ── ensure app is importable ─────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── The exact 7 required target queries — must not be changed ────────────────
REQUIRED_TARGET_QUERIES: List[str] = [
    "izakayas",
    "izakayas with waterfront views",
    "izakayas on Fulton Street",
    "best breweries",
    "best waterfront breweries",
    "breweries near the river",
    "taprooms with a view",
]

# ── shared fixtures ──────────────────────────────────────────────────────────

def _make_entity(
    name: str,
    place_id: str,
    types: List[str],
    rating: float,
    review_count: int,
    address: str,
    source_query: str,
):
    from app.concierge.place_entity_layer import PlaceEntity
    return PlaceEntity(
        place_id=place_id,
        name=name,
        types=types,
        primary_type=types[0],
        rating=rating,
        user_rating_count=review_count,
        business_status="OPERATIONAL",
        formatted_address=address,
        google_maps_uri="https://maps.google.com/?cid=1",
        website_uri=None,
        price_level=None,
        lat=41.88,
        lng=-87.63,
        source_query=source_query,
    )


# ── Brewery fixture data (used by Tables 1–4) ─────────────────────────────────

_BREWERY_NAMES = [
    "The Northman Beer & Cider Garden",
    "Forbidden Root Restaurant & Brewery",
    "Goose Island Brewhouse",
    "Half Acre Beer Company",
    "Revolution Brewing",
    "Empirical Brewery",
]
_BREWERY_RATINGS = [4.7, 4.6, 4.5, 4.6, 4.7, 4.4]
_BREWERY_REVIEWS = [1344, 1958, 802, 750, 2100, 430]
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
            types=["brewery"],
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


# ── Quality notes for Tables 1–4 (no generic filler) ─────────────────────────

def _full_success_notes() -> Dict[str, str]:
    """Notes for Table 1: all six breweries, card-specific and differentiated."""
    return {
        "1": "The Northman Beer & Cider Garden specializes in craft ciders alongside ales, an unusual combination that makes it a standout for cider fans within Chicago's brewery circuit.",
        "2": "Forbidden Root is Chicago's botanical brewery, pairing herb-forward beers with a full kitchen in a West Town location that draws both food and beer crowds.",
        "3": "Goose Island Brewhouse is the flagship production facility and tasting room for the Goose Island brand, with the most comprehensive tap rotation of any location.",
        "4": "Half Acre focuses on small-batch experimental brewing from its Lincoln Square base, with limited releases that draw a knowledgeable local crowd.",
        "5": "Revolution Brewing operates one of Chicago's largest purpose-built taprooms with a steady seasonal IPA program and one of the highest review volumes of any city brewery.",
        "6": "Empirical Brewery focuses on hyper-local distribution from its Bowmanville base, with a compact taproom that leans into experimental fermentation styles.",
    }


def _retry_notes_for_cards_2_to_6() -> Dict[str, str]:
    """Notes for Table 2 retry pass: five cards returned in the retry subset (re-indexed 1–5)."""
    return {
        "1": "Forbidden Root blends botanical brewing with a gastropub kitchen, a distinctive pairing that sets it apart from conventional Chicago taprooms.",
        "2": "Goose Island Brewhouse is the flagship production-brewery location for Goose Island, with a broader tap list than the satellite locations.",
        "3": "Half Acre's taproom emphasizes small-batch releases over volume, drawing a knowledgeable crowd looking for experimental styles.",
        "4": "Revolution Brewing is a Northwest Side anchor with a large-format taproom and a steady seasonal IPA program widely cited as among the city's most consistent.",
        "5": "Empirical Brewery keeps its distribution hyper-local and its taproom compact, specializing in experimental fermentation styles unavailable at mainstream breweries.",
    }


def _fallback_notes_for_4_cards() -> Dict[str, str]:
    """Notes for Table 3 fallback pass: four brewery cards via fallback model."""
    return {
        "1": "The Northman Beer & Cider Garden offers an unusually deep cider selection alongside craft ales, setting it apart from standard taprooms in the city.",
        "2": "Forbidden Root's botanical brewing approach and full-menu gastropub format distinguish it from standard taprooms, making it a genuine dining destination.",
        "3": "Goose Island Brewhouse anchors the Clybourn Corridor as both a heritage brewery location and a tap-list destination, with the deepest Goose Island portfolio rotation.",
        "4": "Half Acre is a Lincoln Square taproom that hosts some of Chicago's most sought-after small-batch releases, with a tighter format that rewards repeat visits.",
    }


def _repair_notes_for_3_cards() -> Dict[str, str]:
    """Notes for Table 4 retry repair: three brewery cards after template rejection."""
    return {
        "1": "The Northman Beer & Cider Garden is one of the few Chicago taprooms with a serious cider program alongside craft ales, positioning it for cider enthusiasts.",
        "2": "Forbidden Root's botanical brewing approach and full-menu gastropub format distinguish it from standard taprooms, making it a destination rather than just a stop.",
        "3": "Goose Island Brewhouse anchors the Clybourn Corridor as a heritage brewery location with the deepest rotation across the Goose Island portfolio.",
    }


# ── Table renderer ────────────────────────────────────────────────────────────

_COLS = [
    ("scenario",              24),
    ("query",                 34),
    ("card_index",             5),
    ("card_title",            36),
    ("rating",                 6),
    ("review_count",           8),
    ("displayWhyValidated",   18),
    ("displayWhySource",      30),
    ("attemptCount",           8),
    ("modelUsed",             28),
    ("retryUsed",              9),
    ("fallbackModelUsed",     14),
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


def _run_brewery_scenario(
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


# ── Table 1: Full success ─────────────────────────────────────────────────────

def table1_full_success() -> List[Dict[str, str]]:
    notes = _full_success_notes()
    llm_json = json.dumps(notes)

    def mock_llm(prompt, timeout, model=""):
        return llm_json

    return _run_brewery_scenario("full_success", "breweries near the river", 6, mock_llm)


# ── Table 2: Partial first-pass, retry fills misses ───────────────────────────

def table2_partial_retry() -> List[Dict[str, str]]:
    pass1_response = json.dumps({
        "1": "The Northman Beer & Cider Garden is a celebrated Avondale spot known for its extensive cider and beer selection."
    })
    retry_response = json.dumps(_retry_notes_for_cards_2_to_6())

    call_count = 0

    def mock_llm(prompt, timeout, model=""):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return pass1_response
        return retry_response

    return _run_brewery_scenario("partial_retry", "breweries near the river", 6, mock_llm)


# ── Table 3: Primary timeout, fallback model fills all ────────────────────────

def table3_timeout_fallback() -> List[Dict[str, str]]:
    from app.concierge.batched_reason_builder import _PRIMARY_MODEL, _FALLBACK_MODEL

    fallback_response = json.dumps(_fallback_notes_for_4_cards())

    def mock_llm(prompt, timeout, model=""):
        resolved_model = model or _PRIMARY_MODEL
        if resolved_model == _PRIMARY_MODEL:
            return None  # simulate timeout / no response
        if resolved_model == _FALLBACK_MODEL:
            return fallback_response
        return None

    return _run_brewery_scenario("timeout_fallback", "breweries near the river", 4, mock_llm)


# ── Table 4: Bad-template repair via retry ────────────────────────────────────

def table4_bad_template_repair() -> List[Dict[str, str]]:
    names = _BREWERY_NAMES[:3]

    bad_notes = {str(i + 1): f"{names[i]} — 4.5★ from 900 reviews." for i in range(3)}
    repair_response = json.dumps(_repair_notes_for_3_cards())

    call_count = 0

    def mock_llm(prompt, timeout, model=""):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return json.dumps(bad_notes)
        return repair_response

    return _run_brewery_scenario("bad_template_repair", "breweries near the river", 3, mock_llm)


# ── Table 5: Required target query matrix ────────────────────────────────────

# Venue cards for each required query (3 cards each).
# Addresses chosen so "izakayas on Fulton Street" cards get
# location_modifier_not_confirmed:Fulton Street in their evidence bundles.
_TARGET_CARD_DATA: Dict[str, List[Tuple[str, str, List[str], float, int]]] = {
    # (name, address, types, rating, review_count)
    "izakayas": [
        ("Izakaya Shinya",       "200 N Green St, Chicago, IL",    ["japanese_restaurant"], 4.6, 900),
        ("Gaijin",               "2239 N Western Ave, Chicago, IL", ["japanese_restaurant"], 4.5, 740),
        ("En Hakkinen",          "1505 N Wells St, Chicago, IL",    ["japanese_restaurant"], 4.4, 580),
    ],
    "izakayas with waterfront views": [
        ("Izakaya Shinya",       "200 N Green St, Chicago, IL",    ["japanese_restaurant"], 4.6, 900),
        ("Gaijin",               "2239 N Western Ave, Chicago, IL", ["japanese_restaurant"], 4.5, 740),
        ("En Hakkinen",          "1505 N Wells St, Chicago, IL",    ["japanese_restaurant"], 4.4, 580),
    ],
    "izakayas on Fulton Street": [
        ("Izakaya Shinya",       "200 N Green St, Chicago, IL",    ["japanese_restaurant"], 4.6, 900),
        ("Gaijin",               "2239 N Western Ave, Chicago, IL", ["japanese_restaurant"], 4.5, 740),
        ("En Hakkinen",          "1505 N Wells St, Chicago, IL",    ["japanese_restaurant"], 4.4, 580),
    ],
    "best breweries": [
        ("Goose Island Brewhouse",   "1800 N Clybourn Ave, Chicago, IL", ["brewery"], 4.5, 802),
        ("Half Acre Beer Company",   "4257 N Lincoln Ave, Chicago, IL",  ["brewery"], 4.6, 750),
        ("Revolution Brewing",       "2323 N Milwaukee Ave, Chicago, IL",["brewery"], 4.7, 2100),
    ],
    "best waterfront breweries": [
        ("Goose Island Brewhouse",   "1800 N Clybourn Ave, Chicago, IL", ["brewery"], 4.5, 802),
        ("Half Acre Beer Company",   "4257 N Lincoln Ave, Chicago, IL",  ["brewery"], 4.6, 750),
        ("Revolution Brewing",       "2323 N Milwaukee Ave, Chicago, IL",["brewery"], 4.7, 2100),
    ],
    "breweries near the river": [
        ("Goose Island Brewhouse",   "1800 N Clybourn Ave, Chicago, IL", ["brewery"], 4.5, 802),
        ("Half Acre Beer Company",   "4257 N Lincoln Ave, Chicago, IL",  ["brewery"], 4.6, 750),
        ("Revolution Brewing",       "2323 N Milwaukee Ave, Chicago, IL",["brewery"], 4.7, 2100),
    ],
    "taprooms with a view": [
        ("Goose Island Taproom",  "1800 N Clybourn Ave, Chicago, IL", ["brewery"], 4.5, 802),
        ("Half Acre Taproom",     "4257 N Lincoln Ave, Chicago, IL",  ["brewery"], 4.6, 750),
        ("Empirical Taproom",     "1801 W Foster Ave, Chicago, IL",   ["brewery"], 4.4, 430),
    ],
}

# Crafted LLM notes — each must pass validate_reason() for its query+evidence.
# Rules:
#   - No waterfront/river-view/view claims unless followed by negation caveat.
#   - "izakayas on Fulton Street" notes must NOT claim to be on Fulton Street
#     (the evidence bundles set location_modifier_not_confirmed:Fulton Street).
#   - No generic filler: no "well-regarded", "strong local following",
#     "Chicago institution", "consistent quality" as the sole differentiator.
#   - Each note must include a concrete differentiator, an honest caveat,
#     or a specific fit to the query that helps the traveler choose.
_TARGET_NOTES: Dict[str, Dict[str, str]] = {
    "izakayas": {
        "1": "Izakaya Shinya on Green Street is a Japanese restaurant whose name and category both point directly to izakaya-style dining, with a menu focused on skewers and small plates.",
        "2": "Gaijin is listed as a Japanese restaurant whose menu signals align closely to izakaya-style small plates and skewers.",
        "3": "En Hakkinen offers Japanese small plates and a compact menu consistent with izakaya-style dining in Chicago.",
    },
    "izakayas with waterfront views": {
        "1": "Izakaya Shinya's name and Japanese-restaurant category both align with the izakaya request; waterfront proximity cannot be confirmed from the available address data.",
        "2": "Gaijin is a Japanese-restaurant type match for this izakaya request; waterfront positioning cannot be confirmed from listing data, but the category aligns with izakaya-style dining.",
        "3": "En Hakkinen carries izakaya-style signals in both name and category; a waterfront view cannot be verified from listing data, so approach it as an izakaya pick rather than a riverside seat.",
    },
    "izakayas on Fulton Street": {
        "1": "Izakaya Shinya's Japanese-restaurant type and name align with this izakaya request; the address shows Green Street, not Fulton Street, so it's the closest verified option nearby.",
        "2": "Gaijin's Japanese-restaurant type aligns with this izakaya request; the address confirms Western Avenue, not Fulton Street, so it's the closest verified izakaya-style option available.",
        "3": "En Hakkinen carries izakaya-style signals in name and category; not on Fulton Street per the address data, but a solid candidate for izakaya dining in this part of the city.",
    },
    "best breweries": {
        "1": "Goose Island Brewhouse is the flagship tap-room for one of Chicago's most distributed craft labels, with the broadest rotation across the Goose Island portfolio.",
        "2": "Half Acre focuses on small-batch experimental brewing from its Lincoln Square base, with limited releases that draw a knowledgeable local crowd.",
        "3": "Revolution Brewing operates one of Chicago's largest purpose-built taprooms, with a strong seasonal IPA program and one of the highest review volumes of any city brewery.",
    },
    "best waterfront breweries": {
        "1": "Goose Island Brewhouse is an established Chicago taproom with a wide tap rotation; waterfront proximity is not verified from available data, so plan for the beer selection rather than a river view.",
        "2": "One of Chicago's highest-review-count breweries; waterfront access cannot be confirmed from listing data, but the tap quality and neighborhood location make it a worthwhile visit.",
        "3": "Revolution Brewing is one of Chicago's largest independent breweries; waterfront seating cannot be confirmed from the available address, but the tap quality and review volume are well-supported.",
    },
    "breweries near the river": {
        "1": "Goose Island Brewhouse anchors the Clybourn Corridor with a comprehensive tap list covering core seasonals and limited releases, a worthwhile stop for beer exploration.",
        "2": "Half Acre is a Lincoln Square taproom prizing small-batch releases over volume, one of Chicago's more consistent neighborhood brewing destinations.",
        "3": "Revolution Brewing brings a large-format taproom and citywide distribution from its Northwest Side base, with a well-established seasonal rotation.",
    },
    "taprooms with a view": {
        "1": "Goose Island Taproom on Clybourn Ave is a well-reviewed brewery taproom; a scenic view cannot be structurally confirmed from listing data, but the tap quality and review volume are well-supported.",
        "2": "Half Acre on Lincoln Ave is an established neighborhood taproom with a consistent small-batch release program; an outdoor or elevated view is not confirmed from the listing, so plan for the beer.",
        "3": "Empirical Taproom on Foster Ave focuses on local distribution and experimental fermentation; a confirmed scenic view cannot be verified from available data, but it's a distinctive taproom option.",
    },
}


def _make_target_cards(query: str) -> Tuple[list, object]:
    from app.concierge.frame_extractor import extract_frame
    from app.concierge.ranker import RankScore, build_evidence_bundle
    from app.concierge.safe_reason_builder import build_safe_reason

    frame = extract_frame(query, "Chicago")
    card_defs = _TARGET_CARD_DATA[query]
    cards_data = []
    for i, (name, addr, types, rating, reviews) in enumerate(card_defs):
        entity = _make_entity(
            name=name,
            place_id=f"pid_tq_{hash(query) % 9999}_{i}",
            types=types,
            rating=rating,
            review_count=reviews,
            address=addr,
            source_query=query,
        )
        score = RankScore(total=0.75, subtype_fit=0.90, geo_fit=0.5)
        ev = build_evidence_bundle(entity, frame, score)
        det = build_safe_reason(entity, ev, frame, score)
        cards_data.append((entity, ev, score, det))
    return cards_data, frame


def table5_target_query_matrix() -> List[Dict[str, str]]:
    from app.concierge.batched_reason_builder import build_reasons_with_retry

    all_rows = []
    _ENABLE_FLAG = patch("app.concierge.batched_reason_builder._flag_enabled", return_value=True)

    for query in REQUIRED_TARGET_QUERIES:
        cards_data, frame = _make_target_cards(query)
        notes_for_query = _TARGET_NOTES[query]
        llm_json = json.dumps(notes_for_query)

        def mock_llm(prompt, timeout, model="", _j=llm_json):
            return _j

        with _ENABLE_FLAG, patch(
            "app.concierge.batched_reason_builder._call_llm", side_effect=mock_llm
        ):
            reasons, _ = build_reasons_with_retry(cards_data, frame)

        for i, (entity, _ev, _score, _det) in enumerate(cards_data):
            cr = reasons.get(str(i + 1))
            all_rows.append(
                {
                    "scenario": "target_query_matrix",
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

    total = len(rows)
    validated = sum(1 for r in rows if r["displayWhyValidated"] == "True")
    omitted = total - validated
    print(f"\n  Summary: {validated}/{total} validated, {omitted} omitted\n")


# ── Assertion helpers (used by tests) ────────────────────────────────────────

_GENERIC_FILLER_RE = __import__("re").compile(
    r"\b(well[-\s]regarded|strong local following|chicago institution"
    r"|consistent quality|devoted craft.beer following"
    r"|loyal neighborhood following)\b",
    __import__("re").IGNORECASE,
)

_NAME_RATING_TEMPLATE_RE = __import__("re").compile(
    r"^[A-Za-z0-9'''\-&, ()]{3,120}\s*[—–\-]{1,3}\s*\d{1,2}[\d.]*\s*★",
    __import__("re").IGNORECASE | __import__("re").UNICODE,
)

_UNSUPPORTED_VIEW_RE = __import__("re").compile(
    r"\b(waterfront|riverwalk|river\s*walk|river\s*view|lake\s*view|water\s*view"
    r"|rooftop\s+view|panoramic)\b",
    __import__("re").IGNORECASE,
)

_NEGATION_RE = __import__("re").compile(
    r"\b(not confirmed|cannot be|cannot verify|not verified|not directly"
    r"|is not|isn't|doesn't)\b",
    __import__("re").IGNORECASE,
)


def assert_success_path_quality(rows: List[Dict[str, str]], table_label: str) -> None:
    """Raise AssertionError if any success-path row violates quality rules."""
    for row in rows:
        note = row.get("visible_concierge_note", "")
        validated = row.get("displayWhyValidated", "")
        idx = row.get("card_index", "?")
        title = row.get("card_title", "?")
        loc = f"[{table_label} card={idx} title={title!r}]"

        if validated != "True":
            # Non-validated cards are excluded from the response — omitted is acceptable.
            continue

        assert note, f"{loc} success-path card has empty visible_concierge_note (NOTE OMITTED)"

        assert not _NAME_RATING_TEMPLATE_RE.match(note), (
            f"{loc} note is a name+rating template: {note!r}"
        )

        if _GENERIC_FILLER_RE.search(note):
            raise AssertionError(
                f"{loc} note contains generic filler: {note!r}"
            )

        view_match = _UNSUPPORTED_VIEW_RE.search(note)
        if view_match:
            claim = view_match.group(0)
            start = view_match.start()
            window_start = max(0, start - 80)
            window_end = min(len(note), start + 80)
            context = note[window_start:window_end]
            assert _NEGATION_RE.search(context), (
                f"{loc} note makes unsupported view/waterfront claim {claim!r} without negation: {note!r}"
            )


def assert_table5_uses_required_queries(rows: List[Dict[str, str]]) -> None:
    """Raise AssertionError if Table 5 is missing any required target query."""
    seen = set(row["query"] for row in rows)
    # Queries are truncated to 34 chars in the row dict
    required_truncated = {q[:34] for q in REQUIRED_TARGET_QUERIES}
    missing = required_truncated - seen
    assert not missing, f"Table 5 is missing required target queries: {missing}"
    unexpected = seen - required_truncated
    assert not unexpected, f"Table 5 contains unexpected queries: {unexpected}"


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    print("\nReasoning Reliability v2 — Evidence Harness")
    print("=" * 130)

    all_ok = True

    try:
        rows1 = table1_full_success()
        _print_table("Table 1: Full Success — 6/6 validated from pass 1 (primary model)", rows1)
        assert_success_path_quality(rows1, "Table1")
        print("  [QUALITY CHECK PASSED] Table 1")
    except Exception as e:
        print(f"\n[ERROR] Table 1: {e}")
        import traceback; traceback.print_exc()
        all_ok = False

    try:
        rows2 = table2_partial_retry()
        _print_table("Table 2: Partial First-Pass — 1/6 pass 1, retry recovers 5/6", rows2)
        assert_success_path_quality(rows2, "Table2")
        print("  [QUALITY CHECK PASSED] Table 2")
    except Exception as e:
        print(f"\n[ERROR] Table 2: {e}")
        import traceback; traceback.print_exc()
        all_ok = False

    try:
        rows3 = table3_timeout_fallback()
        _print_table("Table 3: Timeout + Fallback Recovery — primary silent, fallback fills all", rows3)
        assert_success_path_quality(rows3, "Table3")
        print("  [QUALITY CHECK PASSED] Table 3")
    except Exception as e:
        print(f"\n[ERROR] Table 3: {e}")
        import traceback; traceback.print_exc()
        all_ok = False

    try:
        rows4 = table4_bad_template_repair()
        _print_table("Table 4: Bad-Template Repair — validator rejects pass-1, retry repairs", rows4)
        assert_success_path_quality(rows4, "Table4")
        print("  [QUALITY CHECK PASSED] Table 4")
    except Exception as e:
        print(f"\n[ERROR] Table 4: {e}")
        import traceback; traceback.print_exc()
        all_ok = False

    try:
        rows5 = table5_target_query_matrix()
        _print_table(
            "Table 5: Required Target Query Matrix — 7 queries × top-3 cards\n"
            "  Queries: izakayas | izakayas with waterfront views | izakayas on Fulton Street\n"
            "           best breweries | best waterfront breweries | breweries near the river\n"
            "           taprooms with a view",
            rows5,
        )
        assert_table5_uses_required_queries(rows5)
        assert_success_path_quality(rows5, "Table5")
        print("  [QUALITY CHECK PASSED] Table 5")
    except Exception as e:
        print(f"\n[ERROR] Table 5: {e}")
        import traceback; traceback.print_exc()
        all_ok = False

    if all_ok:
        print("\nEvidence harness complete — all quality checks passed.\n")
    else:
        print("\nEvidence harness complete — QUALITY CHECKS FAILED (see errors above).\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
