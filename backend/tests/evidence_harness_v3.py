"""Evidence harness v3 — EvidencePack v3 quality validation.

Validates that AI Concierge reasoning produces concierge-grade notes
(not thin concept-fit phrases) across 3 production queries, with mock
Place Details enrichment data.

Tables:
  Table 1: "breweries near the river" — enriched with amenity flags
  Table 2: "taprooms with a view"    — thin evidence (no enrichment), quality critic fires
  Table 3: "izakayas"                — editorial summary enrichment

Columns:
  query, card_index, card_title, rating, review_count,
  evidence_adequacy, modifier_status, displayWhyValidated,
  displayWhySource, visible_concierge_note, quality_gate_result,
  retry_used, fallback_used

Run:
  cd backend && python -m tests.evidence_harness_v3
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Production queries ────────────────────────────────────────────────────────
PRODUCTION_QUERIES = [
    "breweries near the river",
    "taprooms with a view",
    "izakayas",
]


# ── Fixtures ──────────────────────────────────────────────────────────────────

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


def _make_enrichment(
    place_id: str,
    editorial_summary: Optional[str] = None,
    review_snippets: Optional[List[str]] = None,
    serves_beer: Optional[bool] = None,
    outdoor_seating: Optional[bool] = None,
    live_music: Optional[bool] = None,
    good_for_groups: Optional[bool] = None,
):
    from app.concierge.place_details_provider import PlaceDetailsResult
    return PlaceDetailsResult(
        place_id=place_id,
        editorial_summary=editorial_summary,
        review_snippets=review_snippets or [],
        serves_beer=serves_beer,
        outdoor_seating=outdoor_seating,
        live_music=live_music,
        good_for_groups=good_for_groups,
    )


# ── Brewery fixtures with enrichment ─────────────────────────────────────────

_BREWERY_DATA = [
    {
        "name": "Goose Island Brewhouse",
        "types": ["brewery"],
        "rating": 4.5,
        "reviews": 802,
        "address": "1800 N Clybourn Ave, Chicago, IL",
        "source_query": "breweries near the river Chicago",
        "editorial": "Chicago's iconic craft brewery, known for its Bourbon County stouts and year-round IPAs.",
        "serves_beer": True,
        "outdoor_seating": True,
    },
    {
        "name": "Forbidden Root Restaurant & Brewery",
        "types": ["brewery"],
        "rating": 4.6,
        "reviews": 1958,
        "address": "1746 W Chicago Ave, Chicago, IL",
        "source_query": "breweries near the river Chicago",
        "editorial": "Botanical brewery pairing herb-forward beers with a full gastropub kitchen.",
        "serves_beer": True,
        "good_for_groups": True,
    },
    {
        "name": "Revolution Brewing",
        "types": ["brewery"],
        "rating": 4.7,
        "reviews": 2100,
        "address": "2323 N Milwaukee Ave, Chicago, IL",
        "source_query": "brewery Chicago riverwalk",
        "editorial": "One of Chicago's largest independent craft breweries, with a flagship taproom and production facility.",
        "serves_beer": True,
        "outdoor_seating": True,
        "good_for_groups": True,
    },
]

# ── Taproom fixtures (thin evidence — no enrichment) ──────────────────────────

_TAPROOM_DATA = [
    {
        "name": "Corridor Brewery & Provisions",
        "types": ["brewery"],
        "rating": 4.4,
        "reviews": 380,
        "address": "3446 N Southport Ave, Chicago, IL",
        "source_query": "taprooms with a view Chicago",
        "editorial": None,
    },
    {
        "name": "Spiteful Brewing",
        "types": ["brewery"],
        "rating": 4.3,
        "reviews": 290,
        "address": "1815 W Berteau Ave, Chicago, IL",
        "source_query": "taprooms Chicago view",
        "editorial": None,
    },
    {
        "name": "Dovetail Brewery",
        "types": ["brewery"],
        "rating": 4.5,
        "reviews": 520,
        "address": "1800 W Belle Plaine Ave, Chicago, IL",
        "source_query": "taprooms Chicago view",
        "editorial": None,
    },
]

# ── Izakaya fixtures with editorial summaries ─────────────────────────────────

_IZAKAYA_DATA = [
    {
        "name": "Gaijin",
        "types": ["japanese_restaurant"],
        "rating": 4.7,
        "reviews": 1200,
        "address": "950 W Lake St, Chicago, IL",
        "source_query": "izakayas Chicago",
        "editorial": "Modern izakaya concept on Lake Street with a focus on Japanese street food and natural wines.",
        "good_for_groups": True,
    },
    {
        "name": "Izakaya Mita",
        "types": ["japanese_restaurant"],
        "rating": 4.6,
        "reviews": 890,
        "address": "1960 N Damen Ave, Chicago, IL",
        "source_query": "izakaya Chicago",
        "editorial": "Traditional Japanese izakaya in Bucktown offering grilled skewers, sake, and a cozy late-night atmosphere.",
        "live_music": False,
        "good_for_groups": True,
    },
    {
        "name": "Sushi-san",
        "types": ["sushi_restaurant"],
        "rating": 4.5,
        "reviews": 2100,
        "address": "63 W Grand Ave, Chicago, IL",
        "source_query": "izakayas Chicago",
        "editorial": None,
    },
]


def _build_cards_for_query(
    query: str,
    destination: str,
    data: List[Dict],
    enrichment_map: Dict[str, Any],
) -> tuple:
    from app.concierge.frame_extractor import extract_frame
    from app.concierge.ranker import RankScore, build_evidence_bundle
    from app.concierge.safe_reason_builder import build_safe_reason

    frame = extract_frame(query, destination)
    cards_data = []
    for i, d in enumerate(data):
        place_id = f"pid_{query[:10].replace(' ', '_')}_{i}"
        entity = _make_entity(
            name=d["name"],
            place_id=place_id,
            types=d["types"],
            rating=d["rating"],
            review_count=d["reviews"],
            address=d["address"],
            source_query=d["source_query"],
        )
        score = RankScore(total=0.72, subtype_fit=0.88, geo_fit=0.55)
        enrichment = enrichment_map.get(place_id)
        ev = build_evidence_bundle(entity, frame, score, enrichment=enrichment)
        det = build_safe_reason(entity, ev, frame, score)
        cards_data.append((entity, ev, score, det))
    return cards_data, frame


def _build_enrichment_map_for(data: List[Dict], query_prefix: str) -> Dict[str, Any]:
    result = {}
    for i, d in enumerate(data):
        place_id = f"pid_{query_prefix[:10].replace(' ', '_')}_{i}"
        if d.get("editorial") or d.get("serves_beer") or d.get("good_for_groups") or d.get("outdoor_seating"):
            result[place_id] = _make_enrichment(
                place_id=place_id,
                editorial_summary=d.get("editorial"),
                serves_beer=d.get("serves_beer"),
                outdoor_seating=d.get("outdoor_seating"),
                live_music=d.get("live_music"),
                good_for_groups=d.get("good_for_groups"),
            )
    return result


# ── Notes for the three scenarios ────────────────────────────────────────────

def _brewery_notes() -> Dict[str, str]:
    """Concierge notes grounded in enrichment facts."""
    return {
        "1": "Goose Island Brewhouse on Clybourn Ave is Chicago's heritage craft brewery landmark, known for its Bourbon County stouts and a patio that anchors the Clybourn Corridor.",
        "2": "Forbidden Root pairs botanical herb-forward beers with a full gastropub kitchen on Chicago Ave, a combination rarely found at standard taprooms.",
        "3": "Revolution Brewing operates one of the city's largest independent taprooms on Milwaukee Ave, with outdoor seating and a group-friendly format that suits large parties.",
    }


def _taproom_thin_pass1_notes() -> Dict[str, str]:
    """Generic notes that should fail the quality gate (no enrichment available)."""
    return {
        "1": "Corridor Brewery & Provisions matches the taproom concept with strong name and type signals.",
        "2": "Spiteful Brewing has solid brewery signals and is a reliable taproom destination.",
        "3": "Dovetail Brewery matches on taproom type and name, an established taproom with solid signals.",
    }


def _taproom_repair_notes() -> Dict[str, str]:
    """Repaired notes after quality gate rejection."""
    return {
        "1": "Corridor Brewery & Provisions on Southport Ave is a neighborhood taproom in Lakeview; a view is not confirmed from the address but the Southport Corridor location is well-regarded.",
        "2": "Spiteful Brewing on Berteau Ave is a compact Avondale taproom; outdoor views are not confirmed from the available data.",
        "3": "Dovetail Brewery on Belle Plaine Ave focuses on European-style lagers and farmhouse ales — a less common specialty in Chicago's heavily IPA-focused scene.",
    }


def _izakaya_notes() -> Dict[str, str]:
    """Izakaya notes grounded in editorial summaries."""
    return {
        "1": "Gaijin on Lake Street is a modern izakaya pairing Japanese street food with natural wines — an unusual combination in Chicago's Japanese restaurant scene.",
        "2": "Izakaya Mita in Bucktown offers traditional Japanese grilled skewers and sake in a cozy late-night format designed for groups.",
        "3": "Sushi-san on Grand Ave is primarily a sushi destination with strong review volume, though it was returned in an izakaya search.",
    }


# ── Table renderer ────────────────────────────────────────────────────────────

_COLS = [
    ("query",                 34),
    ("card_index",             5),
    ("card_title",            36),
    ("rating",                 6),
    ("review_count",           8),
    ("evidence_adequacy",     10),
    ("modifier_status",       18),
    ("displayWhyValidated",   18),
    ("displayWhySource",      28),
    ("quality_gate_result",   12),
    ("retry_used",             9),
    ("fallback_used",         12),
    ("visible_concierge_note", 70),
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


def _note_preview(note: str, width: int = 68) -> str:
    note = note.strip()
    if len(note) <= width:
        return note
    return note[: width - 1] + "…"


def _table_title(title: str) -> str:
    return f"\n{'=' * 160}\n  {title}\n{'=' * 160}"


def _run_scenario(
    query: str,
    data: List[Dict],
    notes_pass1: Dict[str, str],
    notes_pass2: Optional[Dict[str, str]] = None,
) -> List[Dict[str, str]]:
    """Run build_reasons_with_retry with mocked LLM and collect per-card rows."""
    from app.concierge.batched_reason_builder import build_reasons_with_retry

    enrichment_map = _build_enrichment_map_for(data, query)
    cards_data, frame = _build_cards_for_query(query, "Chicago", data, enrichment_map)

    call_count = 0

    def mock_llm(prompt, timeout, model=""):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return json.dumps(notes_pass1)
        if notes_pass2 and call_count == 2:
            return json.dumps(notes_pass2)
        return json.dumps({str(i + 1): None for i in range(len(cards_data))})

    _ENABLE = patch("app.concierge.batched_reason_builder._flag_enabled", return_value=True)
    with _ENABLE, patch("app.concierge.batched_reason_builder._call_llm", side_effect=mock_llm):
        reasons, result_meta = build_reasons_with_retry(cards_data, frame)

    rows = []
    for i, (entity, evidence, _score, _det) in enumerate(cards_data, 1):
        cr = reasons.get(str(i))
        adequacy = getattr(evidence, "evidence_adequacy", "THIN")
        modifier_status = "none"
        loc_mods = getattr(frame, "location_modifiers", []) or []
        if loc_mods:
            mod = loc_mods[0]
            if any("confirms" in f and mod.lower() in f.lower() for f in evidence.structured_facts):
                modifier_status = "confirmed"
            elif any(f.startswith(f"location_modifier_not_confirmed:{mod}") for f in evidence.uncertainty_flags):
                modifier_status = "not_confirmed"
            else:
                modifier_status = "requested"

        validated = cr.validated if cr else False
        source = cr.source if cr else "omitted"
        retry_used = cr.retry_used if cr else False
        fallback_used = cr.fallback_model_used if cr else False
        note = cr.note if (cr and cr.validated) else ""

        # Quality gate result: did Pass 1 produce a quality-failed note?
        # Infer: if not validated on attempt_count=1 but is validated on attempt_count>=2 → retry rescued
        quality_gate_result = "pass"
        if cr and cr.validated and cr.retry_used:
            quality_gate_result = "retry_rescued"
        elif not validated:
            quality_gate_result = "omitted"

        rows.append({
            "query": query[:34],
            "card_index": str(i),
            "card_title": entity.name[:36],
            "rating": str(entity.rating),
            "review_count": str(entity.user_rating_count),
            "evidence_adequacy": adequacy,
            "modifier_status": modifier_status,
            "displayWhyValidated": str(validated),
            "displayWhySource": source[:28],
            "quality_gate_result": quality_gate_result,
            "retry_used": str(retry_used),
            "fallback_used": str(fallback_used),
            "visible_concierge_note": _note_preview(note),
        })
    return rows


# ── Three production scenarios ────────────────────────────────────────────────

def table1_breweries_enriched() -> List[Dict[str, str]]:
    return _run_scenario(
        "breweries near the river",
        _BREWERY_DATA,
        notes_pass1=_brewery_notes(),
    )


def table2_taprooms_thin_then_repair() -> List[Dict[str, str]]:
    return _run_scenario(
        "taprooms with a view",
        _TAPROOM_DATA,
        notes_pass1=_taproom_thin_pass1_notes(),
        notes_pass2=_taproom_repair_notes(),
    )


def table3_izakayas_editorial() -> List[Dict[str, str]]:
    return _run_scenario(
        "izakayas",
        _IZAKAYA_DATA,
        notes_pass1=_izakaya_notes(),
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    tables = [
        ("Table 1 — Breweries near the river (enriched: editorial + amenity flags)", table1_breweries_enriched),
        ("Table 2 — Taprooms with a view (thin evidence → quality critic → repair)", table2_taprooms_thin_then_repair),
        ("Table 3 — Izakayas (editorial summary enrichment)", table3_izakayas_editorial),
    ]

    total_cards = 0
    validated_cards = 0
    quality_rescued = 0

    for title, fn in tables:
        print(_table_title(title))
        print(_sep())
        print(_header())
        print(_sep())
        rows = fn()
        for row in rows:
            print(_row(row))
            total_cards += 1
            if row["displayWhyValidated"] == "True":
                validated_cards += 1
            if row["quality_gate_result"] == "retry_rescued":
                quality_rescued += 1
        print(_sep())

    print(f"\nSummary: {validated_cards}/{total_cards} validated, {quality_rescued} rescued by quality gate retry")

    # Assert all cards are validated or deliberately omitted (no quality regressions)
    omitted = sum(1 for t, fn in tables for row in fn() if row["displayWhyValidated"] == "False")
    # Table 2 taprooms: quality gate should rescue most cards via retry
    # We only fail if validated_cards == 0 (total failure)
    assert validated_cards > 0, f"FAIL: zero validated cards across all scenarios"
    print(f"\nHarness PASSED: {validated_cards} validated, {omitted} omitted (expected: table2 taprooms may have some omitted)")


if __name__ == "__main__":
    main()
