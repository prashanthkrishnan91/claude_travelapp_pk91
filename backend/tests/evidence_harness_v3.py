"""Evidence harness v3 — EvidencePack v3 quality validation.

Validates that AI Concierge reasoning produces concierge-grade notes
(not thin concept-fit phrases) across 3 production queries, with
production-shape card counts and mock Place Details enrichment data.

Tables:
  Table 1: "breweries near the river" — 8 cards, pass1=7/8, retry fills 1/8
  Table 2: "taprooms with a view"    — 8 cards, pass1=3/8, retry fills 5/8
  Table 3: "izakayas"                — 3 cards, all pass1, STRONG editorial enrichment

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
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


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


# ── 8-card brewery fixtures (enriched with editorial summaries + amenity flags) ──

_BREWERY_8_DATA: List[Dict] = [
    {
        "name": "Goose Island Brewhouse",
        "types": ["brewery"],
        "rating": 4.5,
        "reviews": 802,
        "address": "1800 N Clybourn Ave, Chicago, IL",
        "source_query": "breweries near the river Chicago",
        "editorial": "Chicago's iconic craft brewery, known for Bourbon County stouts and year-round IPAs.",
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
        "editorial": "One of Chicago's largest independent craft breweries with a flagship taproom.",
        "serves_beer": True,
        "outdoor_seating": True,
        "good_for_groups": True,
    },
    {
        "name": "Half Acre Beer Company",
        "types": ["brewery"],
        "rating": 4.6,
        "reviews": 1200,
        "address": "4257 N Lincoln Ave, Chicago, IL",
        "source_query": "breweries near the river Chicago",
        "editorial": "A neighborhood craft brewery focusing on small-batch experimental styles and limited releases.",
        "serves_beer": True,
    },
    {
        "name": "Empirical Brewery",
        "types": ["brewery"],
        "rating": 4.4,
        "reviews": 650,
        "address": "1801 W Foster Ave, Chicago, IL",
        "source_query": "breweries near the river Chicago",
        "editorial": None,
        "serves_beer": True,
        "outdoor_seating": True,
    },
    {
        "name": "Metropolitan Brewing",
        "types": ["brewery"],
        "rating": 4.5,
        "reviews": 890,
        "address": "3057 N Rockwell St, Chicago, IL",
        "source_query": "brewery near river Chicago",
        "editorial": "A German lager-focused brewery on the North Branch of the Chicago River.",
        "serves_beer": True,
        "outdoor_seating": True,
    },
    {
        "name": "Cruz Blanca Brewery",
        "types": ["brewery"],
        "rating": 4.3,
        "reviews": 420,
        "address": "904 W Randolph St, Chicago, IL",
        "source_query": "brewery Chicago",
        "editorial": None,
        "serves_beer": True,
    },
    {
        "name": "Off Color Brewing",
        "types": ["brewery"],
        "rating": 4.4,
        "reviews": 380,
        "address": "3925 W Belmont Ave, Chicago, IL",
        "source_query": "breweries Chicago",
        # No editorial — thin evidence → triggers quality gate in pass1
    },
]


# ── 8-card taproom fixtures (no enrichment — thin evidence, quality critic fires) ──

_TAPROOM_8_DATA: List[Dict] = [
    {
        "name": "Corridor Brewery & Provisions",
        "types": ["brewery"],
        "rating": 4.4,
        "reviews": 380,
        "address": "3446 N Southport Ave, Chicago, IL",
        "source_query": "taprooms with a view Chicago",
    },
    {
        "name": "Spiteful Brewing",
        "types": ["brewery"],
        "rating": 4.3,
        "reviews": 290,
        "address": "1815 W Berteau Ave, Chicago, IL",
        "source_query": "taprooms Chicago view",
    },
    {
        "name": "Dovetail Brewery",
        "types": ["brewery"],
        "rating": 4.5,
        "reviews": 520,
        "address": "1800 W Belle Plaine Ave, Chicago, IL",
        "source_query": "taprooms Chicago view",
    },
    {
        "name": "Hopewell Brewing Company",
        "types": ["brewery"],
        "rating": 4.4,
        "reviews": 310,
        "address": "2760 N Milwaukee Ave, Chicago, IL",
        "source_query": "taprooms with a view Chicago",
    },
    {
        "name": "Lagunitas Brewing Chicago",
        "types": ["brewery"],
        "rating": 4.5,
        "reviews": 1200,
        "address": "1843 S Washtenaw Ave, Chicago, IL",
        "source_query": "taprooms Chicago view",
    },
    {
        "name": "Begyle Brewing",
        "types": ["brewery"],
        "rating": 4.4,
        "reviews": 280,
        "address": "1800 W Cuyler Ave, Chicago, IL",
        "source_query": "taprooms with a view Chicago",
    },
    {
        "name": "Moody Tongue Brewing Company",
        "types": ["brewery"],
        "rating": 4.6,
        "reviews": 450,
        "address": "2515 S Wabash Ave, Chicago, IL",
        "source_query": "taprooms Chicago view",
    },
    {
        "name": "Pilot Project Brewing",
        "types": ["brewery"],
        "rating": 4.3,
        "reviews": 190,
        "address": "2140 S Jefferson St, Chicago, IL",
        "source_query": "taprooms with a view Chicago",
    },
]


# ── Izakaya fixtures with editorial summaries ─────────────────────────────────

_IZAKAYA_DATA: List[Dict] = [
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
        "editorial": "Traditional Japanese izakaya in Bucktown offering grilled skewers, sake, and a late-night format.",
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


def _build_enrichment_map_for(data: List[Dict], query_prefix: str) -> Dict[str, Any]:
    result = {}
    for i, d in enumerate(data):
        place_id = f"pid_{query_prefix[:10].replace(' ', '_')}_{i}"
        if (d.get("editorial") or d.get("serves_beer") or d.get("good_for_groups")
                or d.get("outdoor_seating") or d.get("live_music")):
            result[place_id] = _make_enrichment(
                place_id=place_id,
                editorial_summary=d.get("editorial"),
                serves_beer=d.get("serves_beer"),
                outdoor_seating=d.get("outdoor_seating"),
                live_music=d.get("live_music"),
                good_for_groups=d.get("good_for_groups"),
            )
    return result


def _build_cards_for_query(
    query: str,
    destination: str,
    data: List[Dict],
    enrichment_map: Dict[str, Any],
) -> Tuple[list, Any]:
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


# ── Pass-1 and pass-2 notes for Table 1: 8-card breweries ────────────────────

def _brewery_8_pass1_notes() -> Dict[str, Optional[str]]:
    """7 specific notes + 1 thin note (card 8 — Off Color Brewing)."""
    return {
        "1": "Goose Island Brewhouse on Clybourn Ave is Chicago's heritage craft brewery landmark, home to the Bourbon County stout series with outdoor patio seating on the Clybourn Corridor.",
        "2": "Forbidden Root on Chicago Ave pairs botanical herb-forward beers with a gastropub kitchen — a combination rarely found at standard taprooms in the city.",
        "3": "Revolution Brewing operates one of the city's largest independent taprooms on Milwaukee Ave with outdoor seating, a flagship Anti-Hero IPA program, and group-friendly capacity.",
        "4": "Half Acre on Lincoln Ave emphasizes small-batch experimental styles and limited releases, drawing a knowledgeable crowd to its neighborhood taproom.",
        "5": "Empirical Brewery on Foster Ave offers outdoor patio seating alongside a rotating tap program focused on fermentation-forward styles.",
        "6": "Metropolitan Brewing on Rockwell Street specializes in German-style lagers and operates a North Side taproom with outdoor patio seating.",
        "7": "Cruz Blanca Brewery on Randolph Street offers a Mexican-inspired craft beer program in the West Loop food corridor.",
        "8": "Off Color Brewing has solid brewery signals and strong concept fit in Chicago.",  # thin → quality rejected
    }


def _brewery_8_repair_notes() -> Dict[str, Optional[str]]:
    """Pass-2 repair: subset index "1" maps to original card 8 (Off Color)."""
    return {
        "1": "Off Color Brewing on Belmont Ave brews eccentric small-batch styles including wild-fermented and farmhouse ales — an unusual specialty in Chicago's craft beer scene.",
    }


# ── Pass-1 and pass-2 notes for Table 2: 8-card taprooms ─────────────────────

def _taproom_8_pass1_notes() -> Dict[str, Optional[str]]:
    """3 specific notes + 5 thin notes (cards 4–8)."""
    return {
        "1": "Corridor Brewery & Provisions on Southport Ave is a Lakeview neighborhood taproom; a scenic view is not confirmed from the available address.",
        "2": "Spiteful Brewing on Berteau Ave is a compact Avondale taproom; outdoor views are not confirmed from the available data.",
        "3": "Dovetail Brewery on Belle Plaine Ave focuses on European-style lagers and farmhouse ales — an unusual specialty in Chicago's IPA-heavy craft scene.",
        "4": "Hopewell Brewing Company has solid taproom signals and strong concept fit for this query.",           # thin
        "5": "Lagunitas Brewing Chicago matches the taproom concept with solid brewery signals.",                  # thin
        "6": "Begyle Brewing matches on taproom type and name with established taproom signals.",                  # thin
        "7": "Moody Tongue Brewing has solid taproom signals and an established brewery concept fit.",             # thin
        "8": "Pilot Project Brewing is a reliable taproom destination with solid concept fit in Chicago.",         # thin
    }


def _taproom_8_repair_notes() -> Dict[str, Optional[str]]:
    """Pass-2 repair: subset indices 1–5 map to original cards 4–8."""
    return {
        "1": "Hopewell Brewing Company on Milwaukee Ave is a Logan Square neighborhood taproom; outdoor views are not confirmed from the available address data.",
        "2": "Lagunitas Brewing Chicago on Washtenaw Ave operates a destination-scale taproom; a river or outdoor view cannot be confirmed from the listing address.",
        "3": "Begyle Brewing on Cuyler Ave is a North Side community taproom; outdoor views are not verified from the available address.",
        "4": "Moody Tongue Brewing Company on Wabash Ave focuses on culinary-inspired beers with a distinctive ingredient-forward approach; a view is not confirmed from listing data.",
        "5": "Pilot Project Brewing on Jefferson Street is a collaborative incubator taproom that rotates guest brewer beers; an outdoor view is not verified from available listing data.",
    }


# ── Pass-1 notes for Table 3: izakayas ───────────────────────────────────────

def _izakaya_pass1_notes() -> Dict[str, Optional[str]]:
    """All 3 notes grounded in editorial summaries — all should pass pass1."""
    return {
        "1": "Gaijin on Lake Street is a modern izakaya pairing Japanese street food with natural wines — an unusual combination in Chicago's Japanese restaurant landscape.",
        "2": "Izakaya Mita in Bucktown offers traditional Japanese grilled skewers and sake in a late-night format designed for groups.",
        "3": "Sushi-san on Grand Ave is a high-volume sushi destination with strong review numbers; returned in an izakaya search due to category adjacency.",
    }


# ── Table renderer ────────────────────────────────────────────────────────────

_COLS = [
    ("query",                  34),
    ("card_index",              5),
    ("card_title",             30),
    ("rating",                  6),
    ("review_count",            8),
    ("evidence_adequacy",      10),
    ("modifier_status",        18),
    ("displayWhyValidated",    18),
    ("displayWhySource",       24),
    ("quality_gate_result",    14),
    ("retry_used",              9),
    ("fallback_used",          12),
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
    return note[:width - 1] + "…"


def _table_title(title: str) -> str:
    return f"\n{'=' * 172}\n  {title}\n{'=' * 172}"


def _run_scenario(
    query: str,
    data: List[Dict],
    notes_pass1: Dict[str, Optional[str]],
    notes_pass2: Optional[Dict[str, Optional[str]]] = None,
) -> Tuple[List[Dict[str, str]], Any]:
    """Run build_reasons_with_retry with mocked LLM and collect per-card rows.

    Returns (rows, result_meta) where result_meta is ReasoningResultV2.
    """
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

        quality_gate_result = "pass"
        if cr and cr.validated and cr.retry_used:
            quality_gate_result = "retry_rescued"
        elif not validated:
            quality_gate_result = "omitted"

        rows.append({
            "query": query[:34],
            "card_index": str(i),
            "card_title": entity.name[:30],
            "rating": str(entity.rating),
            "review_count": str(entity.user_rating_count),
            "evidence_adequacy": adequacy,
            "modifier_status": modifier_status,
            "displayWhyValidated": str(validated),
            "displayWhySource": source[:24],
            "quality_gate_result": quality_gate_result,
            "retry_used": str(retry_used),
            "fallback_used": str(fallback_used),
            "visible_concierge_note": _note_preview(note),
        })
    return rows, result_meta


# ── Three production scenarios ────────────────────────────────────────────────

def table1_breweries_8card() -> Tuple[List[Dict[str, str]], Any]:
    return _run_scenario(
        "breweries near the river",
        _BREWERY_8_DATA,
        notes_pass1=_brewery_8_pass1_notes(),
        notes_pass2=_brewery_8_repair_notes(),
    )


def table2_taprooms_8card() -> Tuple[List[Dict[str, str]], Any]:
    return _run_scenario(
        "taprooms with a view",
        _TAPROOM_8_DATA,
        notes_pass1=_taproom_8_pass1_notes(),
        notes_pass2=_taproom_8_repair_notes(),
    )


def table3_izakayas_editorial() -> Tuple[List[Dict[str, str]], Any]:
    return _run_scenario(
        "izakayas",
        _IZAKAYA_DATA,
        notes_pass1=_izakaya_pass1_notes(),
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    tables = [
        ("Table 1 — Breweries near the river (8 cards: pass1=7/8, retry=1/8)", table1_breweries_8card),
        ("Table 2 — Taprooms with a view (8 cards: pass1=3/8, retry=5/8)", table2_taprooms_8card),
        ("Table 3 — Izakayas (3 cards: all pass1, STRONG editorial enrichment)", table3_izakayas_editorial),
    ]

    total_cards = 0
    validated_cards = 0
    quality_rescued = 0
    errors: List[str] = []

    for title, fn in tables:
        rows, result_meta = fn()
        n = len(rows)
        total_cards += n

        print(_table_title(title))
        print(_sep())
        print(_header())
        print(_sep())
        for row in rows:
            print(_row(row))
            if row["displayWhyValidated"] == "True":
                validated_cards += 1
            if row["quality_gate_result"] == "retry_rescued":
                quality_rescued += 1
        print(_sep())

        # Telemetry summary
        print(
            f"  Telemetry: accepted={result_meta.accepted_count}/{result_meta.final_card_count} "
            f"omitted={result_meta.final_note_omitted_count} "
            f"deterministic={result_meta.deterministic_visible_count} "
            f"retry_recovered={result_meta.retry_recovered_count} "
            f"success={result_meta.success}"
        )

        # Strict per-table assertions
        omitted_in_table = [r for r in rows if r["displayWhyValidated"] != "True"]
        for r in omitted_in_table:
            errors.append(
                f"{title}: card {r['card_index']} ({r['card_title']!r}) NOT validated — "
                f"source={r['displayWhySource']} quality={r['quality_gate_result']}"
            )

        # Telemetry cardinality invariants
        if result_meta.final_note_omitted_count != 0:
            errors.append(
                f"{title}: final_note_omitted_count={result_meta.final_note_omitted_count} "
                f"(expected 0)"
            )
        if result_meta.deterministic_visible_count != 0:
            errors.append(
                f"{title}: deterministic_visible_count={result_meta.deterministic_visible_count} "
                f"(expected 0, invariant violated)"
            )
        if result_meta.accepted_count != result_meta.final_card_count:
            errors.append(
                f"{title}: accepted_count={result_meta.accepted_count} != "
                f"final_card_count={result_meta.final_card_count}"
            )

    print(
        f"\nSummary: {validated_cards}/{total_cards} validated, "
        f"{quality_rescued} rescued by quality gate retry"
    )

    if errors:
        print("\nFAILURES:")
        for e in errors:
            print(f"  FAIL: {e}")
        sys.exit(1)

    print(
        "\nHarness PASSED (STRICT): all cards validated, "
        "final_note_omitted_count=0, deterministic_visible_count=0"
    )


if __name__ == "__main__":
    main()
