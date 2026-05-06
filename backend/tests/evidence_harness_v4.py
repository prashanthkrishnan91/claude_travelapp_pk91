"""Evidence harness v4 — Modifier Evidence Contract v1 + Riverwalk safe-evidence.

Validates that AI Concierge reasoning correctly handles:
1. Cards whose verified Google name contains river/Riverwalk context (safe listing mention)
2. Notes that do NOT use rating/review-count as the primary differentiator
3. Per-card modifier evidence (user_modifier, modifier_status)
4. Production-shape 8/8 pass criteria for all three queries

Tables (all 8-card, production-shape):
  Table 1: "breweries near the river" — includes The Northman Beer & Cider Garden on the Riverwalk
  Table 2: "taprooms with a view"     — honest view caveats, no rating-primary notes
  Table 3: "izakayas"                 — 8 cards, venue_head_recognized=True, no rating-primary

Required columns:
  query, card_index, card_title, evidence_adequacy,
  user_modifier, modifier_status, displayWhyValidated,
  displayWhySource, visible_concierge_note, quality_gate_result,
  retry_used, fallback_used

Pass criteria (all must hold):
  - 8/8 validated per table (displayWhyValidated=True for all)
  - final_note_omitted_count=0 per table
  - deterministic_visible_count=0 per table
  - excluded_unvalidated_count=0 (no cards dropped)
  - No rating/review-primary notes
  - No unsupported view/river/waterfront scenic claims
  - Northman/Riverwalk card is validated with safe listing-context wording
  - Izakaya venue_head_recognized=True

Run:
  cd backend && python -m tests.evidence_harness_v4
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── River-context term lookup for modifier_status computation ─────────────────

_RIVER_TERMS = frozenset({
    "river", "riverwalk", "riverfront", "riverbank", "riverside",
    "waterfront", "lakefront", "chicago river",
})
_VIEW_TERMS = frozenset({
    "view", "rooftop", "panoramic", "scenic", "terrace", "overlook", "vista",
})


def _compute_modifier_status(entity: Any, frame: Any) -> Tuple[str, str]:
    """Compute (user_modifier, modifier_status) for a card.

    modifier_status values:
      confirmed_listing_context    — venue name contains the modifier term
      confirmed_address_or_name_context — venue address contains the modifier term
      unknown                      — modifier not verifiable from name/address
      contradicted                 — evidence contradicts the modifier
      none                         — no modifier requested
    """
    loc_mods = getattr(frame, "location_modifiers", []) or []
    geo_hints = getattr(frame, "geography_hints", []) or []
    modifier = ""
    if loc_mods:
        modifier = loc_mods[0]
    elif geo_hints:
        modifier = geo_hints[0]

    if not modifier:
        return "none", "none"

    mod_lower = modifier.lower()
    name_lower = (getattr(entity, "name", "") or "").lower()
    addr_lower = (getattr(entity, "formatted_address", "") or "").lower()

    # Choose which terms to check based on the modifier
    check_terms: frozenset
    if any(r in mod_lower for r in ("river", "waterfront", "riverwalk")):
        check_terms = _RIVER_TERMS
    elif "view" in mod_lower or "scenic" in mod_lower:
        check_terms = _VIEW_TERMS
    else:
        check_terms = frozenset(re.findall(r"[a-z]+", mod_lower))

    for term in check_terms:
        if term in name_lower:
            return modifier, "confirmed_listing_context"
    for term in check_terms:
        if term in addr_lower:
            return modifier, "confirmed_address_or_name_context"

    return modifier, "unknown"


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


# ── Table 1: 8-card brewery fixture with Northman ────────────────────────────
# Production log showed "The Northman Beer & Cider Garden on the Riverwalk"
# as card 4, validated=False, source=omitted, note=''. This fixture proves
# the fix: the card MUST be validated after the Riverwalk safe-evidence fix.

_BREWERY_8_NORTHMAN: List[Dict] = [
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
        # The card from production logs — was omitted (validated=False). Must now validate.
        "name": "The Northman Beer & Cider Garden on the Riverwalk",
        "types": ["bar", "brewery"],
        "rating": 4.4,
        "reviews": 1120,
        "address": "Riverwalk, Chicago, IL",
        "source_query": "breweries riverwalk Chicago",
        "editorial": None,
        "serves_beer": True,
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
        "editorial": "A neighborhood craft brewery focusing on small-batch experimental styles.",
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
        "name": "Cruz Blanca Brewery",
        "types": ["brewery"],
        "rating": 4.3,
        "reviews": 420,
        "address": "904 W Randolph St, Chicago, IL",
        "source_query": "brewery Chicago",
        "editorial": None,
        "serves_beer": True,
    },
]


# ── Table 2: 8-card taproom fixture (honest view caveats, no rating-primary) ─

_TAPROOM_8_DATA: List[Dict] = [
    {
        "name": "Corridor Brewery & Provisions",
        "types": ["brewery"],
        "rating": 4.4,
        "reviews": 380,
        "address": "3446 N Southport Ave, Chicago, IL",
        "source_query": "taprooms with a view Chicago",
        "editorial": "A Lakeview neighborhood taproom focused on hazy IPAs and wood-fired provisions.",
        "outdoor_seating": True,
    },
    {
        "name": "Spiteful Brewing",
        "types": ["brewery"],
        "rating": 4.3,
        "reviews": 290,
        "address": "1815 W Berteau Ave, Chicago, IL",
        "source_query": "taprooms Chicago view",
        "editorial": "An Avondale taproom known for aggressive hoppy beers and punk-themed branding.",
    },
    {
        "name": "Dovetail Brewery",
        "types": ["brewery"],
        "rating": 4.5,
        "reviews": 520,
        "address": "1800 W Belle Plaine Ave, Chicago, IL",
        "source_query": "taprooms Chicago view",
        "editorial": "Specializes in European-style lagers and farmhouse ales — unusual in Chicago's IPA-heavy scene.",
    },
    {
        "name": "Hopewell Brewing Company",
        "types": ["brewery"],
        "rating": 4.4,
        "reviews": 310,
        "address": "2760 N Milwaukee Ave, Chicago, IL",
        "source_query": "taprooms with a view Chicago",
        "editorial": "A Logan Square taproom serving rotating sessionable IPAs and saisons.",
    },
    {
        "name": "Lagunitas Brewing Chicago",
        "types": ["brewery"],
        "rating": 4.5,
        "reviews": 1200,
        "address": "1843 S Washtenaw Ave, Chicago, IL",
        "source_query": "taprooms Chicago view",
        "editorial": "A destination-scale taproom with a large outdoor beer garden and live music events.",
        "outdoor_seating": True,
        "live_music": True,
        "good_for_groups": True,
    },
    {
        "name": "Begyle Brewing",
        "types": ["brewery"],
        "rating": 4.4,
        "reviews": 280,
        "address": "1800 W Cuyler Ave, Chicago, IL",
        "source_query": "taprooms with a view Chicago",
        "editorial": "A North Side community taproom with a family-friendly tap room and backyard seating.",
        "outdoor_seating": True,
    },
    {
        "name": "Moody Tongue Brewing Company",
        "types": ["brewery"],
        "rating": 4.6,
        "reviews": 450,
        "address": "2515 S Wabash Ave, Chicago, IL",
        "source_query": "taprooms Chicago view",
        "editorial": "Culinary-inspired brewery using unique ingredients like yuzu and lemongrass in its beers.",
    },
    {
        "name": "Pilot Project Brewing",
        "types": ["brewery"],
        "rating": 4.3,
        "reviews": 190,
        "address": "2140 S Jefferson St, Chicago, IL",
        "source_query": "taprooms with a view Chicago",
        "editorial": "A collaborative incubator taproom that rotates guest-brewer beers on a seasonal schedule.",
    },
]


# ── Table 3: 8-card izakaya fixture ──────────────────────────────────────────

_IZAKAYA_8_DATA: List[Dict] = [
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
        "editorial": "High-volume River North sushi destination known for hand rolls and sake-pairing menus.",
    },
    {
        "name": "Ramen Takeya",
        "types": ["ramen_restaurant"],
        "rating": 4.4,
        "reviews": 680,
        "address": "819 W Fulton Market, Chicago, IL",
        "source_query": "izakaya Chicago",
        "editorial": "A Fulton Market noodle shop with a tight izakaya-adjacent small-plates menu alongside ramen.",
    },
    {
        "name": "Arami",
        "types": ["japanese_restaurant"],
        "rating": 4.6,
        "reviews": 940,
        "address": "1829 W Chicago Ave, Chicago, IL",
        "source_query": "izakayas Chicago",
        "editorial": "A West Town Japanese restaurant known for seasonal omakase and sake selections.",
    },
    {
        "name": "Yūgen",
        "types": ["japanese_restaurant"],
        "rating": 4.8,
        "reviews": 620,
        "address": "652 W Randolph St, Chicago, IL",
        "source_query": "izakaya Chicago",
        "editorial": "An upscale multi-course Japanese tasting menu restaurant in the West Loop.",
    },
    {
        "name": "Tanuki",
        "types": ["japanese_restaurant"],
        "rating": 4.3,
        "reviews": 410,
        "address": "1055 W Fulton Market, Chicago, IL",
        "source_query": "izakayas Chicago",
        "editorial": "A Fulton Market sake bar with a rotating menu of Japanese small plates and whisky selections.",
    },
    {
        "name": "Izakaya Shinya",
        "types": ["japanese_restaurant"],
        "rating": 4.5,
        "reviews": 1143,
        "address": "3901 N Broadway, Chicago, IL",
        "source_query": "izakaya Chicago",
        "editorial": "A Boystown izakaya serving grilled meats, sake cocktails, and ramen until 2am.",
        "good_for_groups": True,
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


# ── Table 1 mock notes: 8/8 validated including Northman ─────────────────────
# Card 4 (Northman) uses safe listing-context wording — "Riverwalk" is the venue name.

def _brewery_northman_pass1_notes() -> Dict[str, Optional[str]]:
    """All 8 cards pass on first try. Northman uses safe Riverwalk listing wording."""
    return {
        "1": "Goose Island Brewhouse on Clybourn Ave is Chicago's heritage craft brewery, home to the Bourbon County stout series with outdoor patio seating.",
        "2": "Forbidden Root on Chicago Ave pairs botanical herb-forward beers with a full gastropub kitchen — a combination rarely found at standard taprooms.",
        "3": "Metropolitan Brewing specializes in German-style lagers and is situated on the North Branch of the Chicago River — the editorial listing confirms the river connection.",
        "4": "The verified Google listing places Northman on the Riverwalk, making it the strongest river-context beer stop in this set; verify seating and views on-site.",
        "5": "Revolution Brewing operates one of Chicago's largest independent taprooms on Milwaukee Ave with outdoor seating and group-friendly capacity.",
        "6": "Half Acre Beer Company on Lincoln Ave focuses on small-batch experimental styles and limited releases, drawing an enthusiast crowd to its neighborhood taproom.",
        "7": "Empirical Brewery on Foster Ave offers outdoor patio seating alongside a rotating fermentation-forward tap program.",
        "8": "Cruz Blanca Brewery on Randolph Street brings a Mexican-inspired craft beer program to the West Loop food corridor.",
    }


# ── Table 2 mock notes: 8/8 validated, honest view caveats, no rating-primary ─

def _taproom_view_pass1_notes() -> Dict[str, Optional[str]]:
    """All 8 pass on first try. Honest view caveats, venue-specific differentiators."""
    return {
        "1": "Corridor Brewery & Provisions on Southport Ave is a Lakeview taproom offering hazy IPAs alongside wood-fired food — the outdoor patio is confirmed but a scenic view is not.",
        "2": "Spiteful Brewing on Berteau Ave is an Avondale taproom known for aggressively hoppy beers and punk-aesthetic branding; an outdoor view is not confirmed from the listing.",
        "3": "Dovetail Brewery on Belle Plaine Ave specializes in European-style lagers and farmhouse ales — an unusual niche in Chicago's IPA-heavy craft scene.",
        "4": "Hopewell Brewing Company on Milwaukee Ave is a Logan Square neighborhood taproom serving rotating sessionable IPAs and saisons; a view is not confirmed from the listing.",
        "5": "Lagunitas Brewing Chicago on Washtenaw Ave operates a destination-scale taproom with a confirmed outdoor beer garden and live music events — the most amenity-rich option here.",
        "6": "Begyle Brewing on Cuyler Ave is a North Side community taproom with confirmed backyard outdoor seating; a scenic view is not verified from listing data.",
        "7": "Moody Tongue Brewing Company on Wabash Ave focuses on culinary-inspired beers using distinctive ingredients like yuzu and lemongrass — a specialty not found at standard taprooms.",
        "8": "Pilot Project Brewing on Jefferson Street runs a collaborative incubator that rotates guest-brewer beers seasonally — a format unique in Chicago's taproom scene.",
    }


# ── Table 3 mock notes: 8/8 izakayas, no rating-primary ─────────────────────

def _izakaya_pass1_notes() -> Dict[str, Optional[str]]:
    """All 8 pass on first try. Venue-specific differentiators, no rating-primary."""
    return {
        "1": "Gaijin on Lake Street is a modern izakaya pairing Japanese street food with natural wines — an unusual combination in Chicago's Japanese restaurant landscape.",
        "2": "Izakaya Mita in Bucktown offers traditional Japanese grilled skewers and sake in a late-night format designed for groups.",
        "3": "Sushi-san on Grand Ave is a high-volume River North sushi destination known for hand rolls and curated sake-pairing menus.",
        "4": "Ramen Takeya in Fulton Market pairs its noodle program with an izakaya-adjacent small-plates menu — a hybrid format bridging ramen and bar snacks.",
        "5": "Arami on Chicago Ave in West Town is known for seasonal omakase menus and a deep sake selection — closer to Japanese fine dining than a standard izakaya.",
        "6": "Yūgen on Randolph Street offers an upscale multi-course Japanese tasting menu in the West Loop, bridging izakaya tradition with a chef-driven approach.",
        "7": "Tanuki in Fulton Market is a sake bar with rotating Japanese small plates and a whisky selection, functioning as an izakaya-style drinking destination.",
        "8": "Izakaya Shinya on Broadway serves grilled meats, sake cocktails, and late-night ramen until 2am — the most izakaya-faithful late-night format in this set.",
    }


# ── Table renderer ────────────────────────────────────────────────────────────

_COLS = [
    ("query",                  32),
    ("card_index",              5),
    ("card_title",             30),
    ("evidence_adequacy",      10),
    ("user_modifier",          10),
    ("modifier_status",        28),
    ("displayWhyValidated",    17),
    ("displayWhySource",       22),
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
    return f"\n{'=' * 186}\n  {title}\n{'=' * 186}"


def _run_scenario(
    query: str,
    data: List[Dict],
    notes_pass1: Dict[str, Optional[str]],
    notes_pass2: Optional[Dict[str, Optional[str]]] = None,
) -> Tuple[List[Dict[str, str]], Any, Any]:
    """Run build_reasons_with_retry with mocked LLM and collect per-card rows.

    Returns (rows, result_meta, frame).
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
        user_mod, mod_status = _compute_modifier_status(entity, frame)

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
            "query": query[:32],
            "card_index": str(i),
            "card_title": entity.name[:30],
            "evidence_adequacy": adequacy,
            "user_modifier": user_mod[:10],
            "modifier_status": mod_status[:28],
            "displayWhyValidated": str(validated),
            "displayWhySource": source[:22],
            "quality_gate_result": quality_gate_result,
            "retry_used": str(retry_used),
            "fallback_used": str(fallback_used),
            "visible_concierge_note": _note_preview(note),
        })
    return rows, result_meta, frame


# ── Three production scenarios ────────────────────────────────────────────────

def table1_breweries_northman() -> Tuple[List[Dict[str, str]], Any, Any]:
    return _run_scenario(
        "breweries near the river",
        _BREWERY_8_NORTHMAN,
        notes_pass1=_brewery_northman_pass1_notes(),
    )


def table2_taprooms_view() -> Tuple[List[Dict[str, str]], Any, Any]:
    return _run_scenario(
        "taprooms with a view",
        _TAPROOM_8_DATA,
        notes_pass1=_taproom_view_pass1_notes(),
    )


def table3_izakayas_8card() -> Tuple[List[Dict[str, str]], Any, Any]:
    return _run_scenario(
        "izakayas",
        _IZAKAYA_8_DATA,
        notes_pass1=_izakaya_pass1_notes(),
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    tables = [
        (
            "Table 1 — Breweries near the river (8 cards including Northman/Riverwalk)",
            table1_breweries_northman,
            {
                # Specific per-card assertions
                "northman_card_index": 4,  # 1-based
                "northman_must_validate": True,
                "northman_must_not_claim_views": True,
            },
        ),
        (
            "Table 2 — Taprooms with a view (8 cards, honest view caveats)",
            table2_taprooms_view,
            {},
        ),
        (
            "Table 3 — Izakayas (8 cards, venue_head_recognized=True)",
            table3_izakayas_8card,
            {},
        ),
    ]

    total_cards = 0
    validated_cards = 0
    errors: List[str] = []

    for title, fn, extra_asserts in tables:
        rows, result_meta, frame = fn()
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

        if result_meta.final_note_omitted_count != 0:
            errors.append(
                f"{title}: final_note_omitted_count={result_meta.final_note_omitted_count} (expected 0)"
            )
        if result_meta.deterministic_visible_count != 0:
            errors.append(
                f"{title}: deterministic_visible_count={result_meta.deterministic_visible_count} "
                "(expected 0, invariant violated)"
            )
        if result_meta.accepted_count != result_meta.final_card_count:
            errors.append(
                f"{title}: accepted_count={result_meta.accepted_count} != "
                f"final_card_count={result_meta.final_card_count}"
            )

        # Northman-specific assertions for Table 1
        if extra_asserts.get("northman_must_validate"):
            northman_idx = str(extra_asserts["northman_card_index"])
            northman_row = next((r for r in rows if r["card_index"] == northman_idx), None)
            if northman_row:
                if northman_row["displayWhyValidated"] != "True":
                    errors.append(
                        f"{title}: Northman card (index={northman_idx}) NOT validated — "
                        f"this violates the Riverwalk safe-evidence contract"
                    )
                elif extra_asserts.get("northman_must_not_claim_views"):
                    note = northman_row["visible_concierge_note"].lower()
                    bad_phrases = [
                        "river view", "riverfront view", "waterfront seating",
                        "scenic view", "panoramic", "waterfront dining",
                    ]
                    for phrase in bad_phrases:
                        if phrase in note:
                            errors.append(
                                f"{title}: Northman note contains unsupported scenic claim: "
                                f"'{phrase}' in note={northman_row['visible_concierge_note']!r}"
                            )

        # Check for rating-primary notes in taprooms and izakayas
        rating_primary_patterns = [
            r"\bhighest[\s-]rated\b",
            r"\bmost[\s-]reviewed\b",
            r"\breview\s+base\b",
            r"\bsmallest\s+review\b",
            r"\bsolid\s+mid[\s-]tier\b",
            r"\bstrong\s+flagship\s+choice\b",
        ]
        for r in rows:
            note = r["visible_concierge_note"].lower()
            for pattern in rating_primary_patterns:
                if re.search(pattern, note, re.IGNORECASE):
                    errors.append(
                        f"{title}: card {r['card_index']} note contains rating-primary "
                        f"pattern '{pattern}': {r['visible_concierge_note']!r}"
                    )

    print(f"\nSummary: {validated_cards}/{total_cards} validated")

    # Check izakaya venue-head recognition
    from app.concierge.frame_extractor import extract_frame
    from app.concierge.ranker import rank_entities_with_stats
    izakaya_frame = extract_frame("izakayas", "Chicago")
    # Build minimal entity list for venue-head check
    from app.concierge.place_entity_layer import PlaceEntity
    dummy_entities = [
        PlaceEntity(
            place_id="iz_test",
            name="Izakaya Test",
            types=["japanese_restaurant"],
            primary_type="japanese_restaurant",
            rating=4.5,
            user_rating_count=500,
            business_status="OPERATIONAL",
            formatted_address="100 W Test St, Chicago, IL",
            google_maps_uri="https://maps.google.com/?cid=1",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query="izakayas Chicago",
        )
    ]
    _, stats = rank_entities_with_stats(dummy_entities, izakaya_frame)
    if not stats.concept_is_recognized:
        errors.append(
            "Izakaya venue_head_recognized=False — izakaya must be in SYNONYM_SETS"
        )
    else:
        print("  Izakaya venue_head_recognized=True ✓")

    if errors:
        print("\nFAILURES:")
        for e in errors:
            print(f"  FAIL: {e}")
        sys.exit(1)

    print(
        "\nHarness v4 PASSED (STRICT): all 8/8 cards validated per table, "
        "final_note_omitted_count=0, deterministic_visible_count=0, "
        "Northman validated with safe Riverwalk wording, no rating-primary notes"
    )


if __name__ == "__main__":
    main()
