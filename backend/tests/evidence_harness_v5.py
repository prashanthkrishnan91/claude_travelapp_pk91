"""Evidence harness v5 — Production note quality v2: tighter rating/review rejection.

Validates:
1. All PR #252 production bad-note patterns are rejected/repaired (Fix A)
2. Taprooms-with-view: 8/8 validated, no rating-led notes, every card addresses view honestly
3. Izakayas: 8/8 validated, no review-volume-primary notes, izakaya/menu/style anchors used
4. Breweries near the river: Northman remains validated, modifier_status=confirmed_listing_context
5. Harness prints exact visible notes for all three queries

Pass criteria (all must hold):
  - 8/8 accepted for all three queries
  - final_note_omitted_count=0, deterministic_visible_count=0
  - No rating/review-primary notes (including indirect phrasings)
  - Northman modifier_status=confirmed_listing_context
  - taprooms-with-view notes all address view as verified or explicitly unverified
  - izakaya notes use concept/menu/style fit, not review-volume rank

Run:
  cd backend && python -m tests.evidence_harness_v5
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import shared fixtures from v4 harness
from tests.evidence_harness_v4 import (
    _BREWERY_8_NORTHMAN,
    _TAPROOM_8_DATA,
    _IZAKAYA_8_DATA,
    _make_entity,
    _make_enrichment,
    _build_enrichment_map_for,
    _build_cards_for_query,
    _compute_modifier_status,
    _RIVER_TERMS,
    _VIEW_TERMS,
)

# ── PR #252 production bad notes — must all be rejected ──────────────────────
# These exact phrasings appeared in production logs and should now be caught
# by the strengthened _QUALITY_THIN_RE patterns.

PR252_BAD_NOTES = [
    ("notably high ratings", "Goose Island is notable for its notably high ratings (4.8★) in Chicago."),
    ("high engagement",      "This taproom draws consistently high engagement (4.8★, 1,028 reviews) citywide."),
    ("strongest review volume", "Revolution Brewing has the strongest review volume (1,144) in this set."),
    ("smaller review count", "Cruz Blanca carries a smaller review count (313) compared to peers here."),
    ("steady review volume", "Empirical Brewery shows a steady review volume (282) for its Foster Ave taproom."),
    ("lightest review footprint", "Pilot Project has the lightest review footprint (110) of the eight cards."),
]


# ── v5 mock notes: use quality notes that ALSO exercise the new gate patterns ─

def _brewery_v5_pass1_notes() -> Dict[str, Optional[str]]:
    """All 8 pass. Notes do NOT use any rating/review-primary phrasing."""
    return {
        "1": "Goose Island Brewhouse on Clybourn Ave is Chicago's heritage craft brewery, home to the Bourbon County stout series with confirmed outdoor patio seating.",
        "2": "Forbidden Root on Chicago Ave pairs botanical herb-forward beers with a full gastropub kitchen — a combination rarely found at standard taprooms.",
        "3": "Metropolitan Brewing specializes in German-style lagers and is situated on the North Branch of the Chicago River — the editorial listing confirms the river connection.",
        "4": "The verified Google listing places Northman on the Riverwalk, making it the strongest river-context beer stop in this set; verify seating and views on-site.",
        "5": "Revolution Brewing operates one of Chicago's largest independent taprooms on Milwaukee Ave with outdoor seating and group-friendly capacity.",
        "6": "Half Acre Beer Company on Lincoln Ave focuses on small-batch experimental styles and limited releases, drawing an enthusiast crowd to its neighborhood taproom.",
        "7": "Empirical Brewery on Foster Ave offers outdoor patio seating alongside a rotating fermentation-forward tap program.",
        "8": "Cruz Blanca Brewery on Randolph Street brings a Mexican-inspired craft beer program to the West Loop food corridor.",
    }


def _taproom_v5_pass1_notes() -> Dict[str, Optional[str]]:
    """All 8 pass. Each note addresses view honestly (confirmed or not) with a venue-specific reason."""
    return {
        "1": "Corridor Brewery & Provisions on Southport Ave is a Lakeview taproom offering hazy IPAs alongside wood-fired food — outdoor patio is confirmed but a scenic view is not verified from listing data.",
        "2": "Spiteful Brewing on Berteau Ave is an Avondale taproom known for aggressively hoppy beers and punk-aesthetic branding; an outdoor view is not confirmed from the listing.",
        "3": "Dovetail Brewery on Belle Plaine Ave specializes in European-style lagers and farmhouse ales — an unusual niche in Chicago's IPA-heavy craft scene; no view is confirmed from listing data.",
        "4": "Hopewell Brewing Company on Milwaukee Ave is a Logan Square neighborhood taproom serving rotating sessionable IPAs and saisons; a scenic view is not confirmed from the listing.",
        "5": "Lagunitas Brewing Chicago on Washtenaw Ave operates a destination-scale taproom with a confirmed outdoor beer garden and live music events — the most amenity-rich option here.",
        "6": "Begyle Brewing on Cuyler Ave is a North Side community taproom with confirmed backyard outdoor seating; a scenic view is not verified from listing data.",
        "7": "Moody Tongue Brewing Company on Wabash Ave focuses on culinary-inspired beers using distinctive ingredients like yuzu and lemongrass — a specialty not found at standard taprooms; no view confirmed.",
        "8": "Pilot Project Brewing on Jefferson Street runs a collaborative incubator that rotates guest-brewer beers seasonally — a format unique in Chicago's taproom scene; no view is confirmed from the listing.",
    }


def _izakaya_v5_pass1_notes() -> Dict[str, Optional[str]]:
    """All 8 pass. Notes use izakaya/menu/style/concept fit — no review-volume primary."""
    return {
        "1": "Gaijin on Lake Street is a modern izakaya pairing Japanese street food with natural wines — an unusual combination in Chicago's Japanese restaurant landscape.",
        "2": "Izakaya Mita in Bucktown offers traditional Japanese grilled skewers and sake in a late-night shared-plates format designed for groups.",
        "3": "Sushi-san on Grand Ave is a high-volume River North sushi destination known for hand rolls and curated sake-pairing menus — an izakaya-adjacent format.",
        "4": "Ramen Takeya in Fulton Market pairs its noodle program with an izakaya-adjacent small-plates menu, bridging ramen bar and shared-dishes dining.",
        "5": "Arami on Chicago Ave in West Town is known for seasonal omakase menus and a deep sake selection — closer to Japanese fine dining than a casual izakaya.",
        "6": "Yūgen on Randolph Street offers an upscale multi-course Japanese tasting menu in the West Loop, bridging izakaya tradition with a chef-driven approach.",
        "7": "Tanuki in Fulton Market is a sake bar with rotating Japanese small plates and a whisky selection, functioning as an izakaya-style drinking destination.",
        "8": "Izakaya Shinya on Broadway serves grilled meats, sake cocktails, and late-night ramen until 2am — the most izakaya-faithful late-night format in this set.",
    }


# ── Table renderer (same structure as v4 but with exact-note column) ──────────

_COLS = [
    ("query",                  30),
    ("card_index",              5),
    ("card_title",             28),
    ("evidence_adequacy",      10),
    ("modifier_status",        26),
    ("displayWhyValidated",    17),
    ("visible_concierge_note", 80),
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


def _table_title(title: str) -> str:
    return f"\n{'=' * 210}\n  {title}\n{'=' * 210}"


# ── Rating/review-primary detection patterns (mirrors _QUALITY_THIN_RE) ───────
_RATING_PRIMARY_PATTERNS = [
    r"\bhighest[\s-]rated\b",
    r"\bmost[\s-]reviewed\b",
    r"\breview\s+base\b",
    r"\bsmallest\s+review\b",
    r"\bsmaller\s+review\b",
    r"\bsolid\s+mid[\s-]tier\b",
    r"\bstrong\s+flagship\s+choice\b",
    r"\bnotably\s+high\s+ratings?\b",
    r"\bhigh\s+engagement\b",
    r"\breview\s+volume\b",
    r"\breview\s+footprint\b",
    r"\breview\s+count\b",
    r"\bfeedback\s+volume\b",
    r"\bsteady\s+review\b",
    r"\blightest\s+review\b",
    r"\bcarr(?:y|ies|ying|ied)\s+review\b",
    r"\bstrongest\s+review\b",
]


def _has_rating_primary(note: str) -> bool:
    note_lower = note.lower()
    return any(re.search(pat, note_lower, re.IGNORECASE) for pat in _RATING_PRIMARY_PATTERNS)


def _note_addresses_view(note: str) -> bool:
    """Check that the note either confirms view evidence OR explicitly says view not confirmed."""
    note_lower = note.lower()
    confirmed = any(t in note_lower for t in ("outdoor", "patio", "beer garden", "confirmed", "outdoor seating"))
    denied = any(t in note_lower for t in (
        "not confirmed", "not verified", "not verif", "unconfirmed", "no view",
        "view is not", "view cannot", "cannot be verified",
    ))
    return confirmed or denied


def _run_scenario(
    query: str,
    data: List[Dict],
    notes_pass1: Dict[str, Optional[str]],
) -> Tuple[List[Dict[str, str]], Any, Any]:
    from app.concierge.batched_reason_builder import build_reasons_with_retry

    enrichment_map = _build_enrichment_map_for(data, query)
    cards_data, frame = _build_cards_for_query(query, "Chicago", data, enrichment_map)

    call_count = 0

    def mock_llm(prompt, timeout, model=""):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return json.dumps(notes_pass1)
        return json.dumps({str(i + 1): None for i in range(len(cards_data))})

    _ENABLE = patch("app.concierge.batched_reason_builder._flag_enabled", return_value=True)
    with _ENABLE, patch("app.concierge.batched_reason_builder._call_llm", side_effect=mock_llm):
        reasons, result_meta = build_reasons_with_retry(cards_data, frame)

    rows = []
    for i, (entity, evidence, _score, _det) in enumerate(cards_data, 1):
        cr = reasons.get(str(i))
        adequacy = getattr(evidence, "evidence_adequacy", "THIN")
        _user_mod, mod_status = _compute_modifier_status(entity, frame)
        validated = cr.validated if cr else False
        note = cr.note if (cr and cr.validated) else ""
        rows.append({
            "query": query[:30],
            "card_index": str(i),
            "card_title": entity.name[:28],
            "evidence_adequacy": adequacy,
            "modifier_status": mod_status[:26],
            "displayWhyValidated": str(validated),
            "visible_concierge_note": note,
        })
    return rows, result_meta, frame


def main():
    errors: List[str] = []
    total_validated = 0
    total_cards = 0

    # ── Table 1: Breweries near the river ────────────────────────────────────
    print(_table_title("Table 1 — Breweries near the river (8 cards, Northman must be confirmed_listing_context)"))
    rows1, meta1, _frame1 = _run_scenario(
        "breweries near the river", _BREWERY_8_NORTHMAN, _brewery_v5_pass1_notes()
    )
    print(_sep())
    print(_header())
    print(_sep())
    for row in rows1:
        print(_row(row))
        if row["displayWhyValidated"] == "True":
            total_validated += 1
    print(_sep())
    total_cards += len(rows1)
    print(
        f"  Telemetry: accepted={meta1.accepted_count}/{meta1.final_card_count} "
        f"omitted={meta1.final_note_omitted_count} deterministic={meta1.deterministic_visible_count} "
        f"success={meta1.success}"
    )

    # Northman assertions
    northman_row = next((r for r in rows1 if "Northman" in r["card_title"]), None)
    if northman_row:
        if northman_row["displayWhyValidated"] != "True":
            errors.append("Table 1: Northman NOT validated — Riverwalk safe-evidence contract violated")
        if northman_row["modifier_status"] != "confirmed_listing_context":
            errors.append(
                f"Table 1: Northman modifier_status={northman_row['modifier_status']!r} "
                f"(expected confirmed_listing_context)"
            )
    # All 8 validated
    for r in rows1:
        if r["displayWhyValidated"] != "True":
            errors.append(f"Table 1: card {r['card_index']} ({r['card_title']!r}) NOT validated")
    # No rating-primary notes
    for r in rows1:
        if _has_rating_primary(r["visible_concierge_note"]):
            errors.append(
                f"Table 1: card {r['card_index']} has rating-primary note: {r['visible_concierge_note']!r}"
            )
    if meta1.final_note_omitted_count != 0:
        errors.append(f"Table 1: final_note_omitted_count={meta1.final_note_omitted_count} (expected 0)")
    if meta1.deterministic_visible_count != 0:
        errors.append(f"Table 1: deterministic_visible_count={meta1.deterministic_visible_count} (expected 0)")

    # ── Table 2: Taprooms with a view ────────────────────────────────────────
    print(_table_title("Table 2 — Taprooms with a view (8 cards, each note must address view honestly)"))
    rows2, meta2, _frame2 = _run_scenario(
        "taprooms with a view", _TAPROOM_8_DATA, _taproom_v5_pass1_notes()
    )
    print(_sep())
    print(_header())
    print(_sep())
    for row in rows2:
        print(_row(row))
        if row["displayWhyValidated"] == "True":
            total_validated += 1
    print(_sep())
    total_cards += len(rows2)
    print(
        f"  Telemetry: accepted={meta2.accepted_count}/{meta2.final_card_count} "
        f"omitted={meta2.final_note_omitted_count} deterministic={meta2.deterministic_visible_count} "
        f"success={meta2.success}"
    )

    for r in rows2:
        if r["displayWhyValidated"] != "True":
            errors.append(f"Table 2: card {r['card_index']} ({r['card_title']!r}) NOT validated")
        if _has_rating_primary(r["visible_concierge_note"]):
            errors.append(
                f"Table 2: card {r['card_index']} has rating-primary note: {r['visible_concierge_note']!r}"
            )
        if r["displayWhyValidated"] == "True" and not _note_addresses_view(r["visible_concierge_note"]):
            errors.append(
                f"Table 2: card {r['card_index']} note does not address view (confirmed or denied): "
                f"{r['visible_concierge_note']!r}"
            )
    if meta2.final_note_omitted_count != 0:
        errors.append(f"Table 2: final_note_omitted_count={meta2.final_note_omitted_count} (expected 0)")
    if meta2.deterministic_visible_count != 0:
        errors.append(f"Table 2: deterministic_visible_count={meta2.deterministic_visible_count} (expected 0)")

    # ── Table 3: Izakayas ────────────────────────────────────────────────────
    print(_table_title("Table 3 — Izakayas (8 cards, notes must use concept/menu/style, not review volume)"))
    rows3, meta3, _frame3 = _run_scenario(
        "izakayas", _IZAKAYA_8_DATA, _izakaya_v5_pass1_notes()
    )
    print(_sep())
    print(_header())
    print(_sep())
    for row in rows3:
        print(_row(row))
        if row["displayWhyValidated"] == "True":
            total_validated += 1
    print(_sep())
    total_cards += len(rows3)
    print(
        f"  Telemetry: accepted={meta3.accepted_count}/{meta3.final_card_count} "
        f"omitted={meta3.final_note_omitted_count} deterministic={meta3.deterministic_visible_count} "
        f"success={meta3.success}"
    )

    for r in rows3:
        if r["displayWhyValidated"] != "True":
            errors.append(f"Table 3: card {r['card_index']} ({r['card_title']!r}) NOT validated")
        if _has_rating_primary(r["visible_concierge_note"]):
            errors.append(
                f"Table 3: card {r['card_index']} has rating-primary note: {r['visible_concierge_note']!r}"
            )
    if meta3.final_note_omitted_count != 0:
        errors.append(f"Table 3: final_note_omitted_count={meta3.final_note_omitted_count} (expected 0)")
    if meta3.deterministic_visible_count != 0:
        errors.append(f"Table 3: deterministic_visible_count={meta3.deterministic_visible_count} (expected 0)")

    # Izakaya venue-head check
    from app.concierge.frame_extractor import extract_frame
    from app.concierge.ranker import rank_entities_with_stats
    from app.concierge.place_entity_layer import PlaceEntity
    iz_frame = extract_frame("izakayas", "Chicago")
    dummy_entities = [PlaceEntity(
        place_id="iz_test", name="Izakaya Test",
        types=["japanese_restaurant"], primary_type="japanese_restaurant",
        rating=4.5, user_rating_count=500, business_status="OPERATIONAL",
        formatted_address="100 W Test St, Chicago, IL",
        google_maps_uri="https://maps.google.com/?cid=1",
        website_uri=None, price_level=None, lat=41.88, lng=-87.63,
        source_query="izakayas Chicago",
    )]
    _, stats = rank_entities_with_stats(dummy_entities, iz_frame)
    if not stats.concept_is_recognized:
        errors.append("Izakaya venue_head_recognized=False — izakaya must be in SYNONYM_SETS")
    else:
        print("  Izakaya venue_head_recognized=True ✓")

    # ── PR #252 bad-note rejection proof ─────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("  PR #252 bad-note rejection proof")
    print(f"{'=' * 70}")
    from app.concierge.batched_reason_builder import _assess_quality
    from app.concierge.ranker import MinimalEvidenceBundle
    _default_entity = _make_entity(
        "Test Taproom", "pid_test", ["brewery"], 4.5, 600,
        "100 W Fulton St, Chicago, IL", "breweries Chicago"
    )
    thin_ev = MinimalEvidenceBundle(entity=_default_entity, evidence_adequacy="THIN")
    for pattern_name, bad_note in PR252_BAD_NOTES:
        ok, reason = _assess_quality(bad_note, thin_ev)
        status = "REJECTED ✓" if not ok else "PASSED (FAIL)"
        print(f"  [{status}] pattern={pattern_name!r} reason={reason!r}")
        if ok:
            errors.append(
                f"PR #252 bad note NOT rejected: pattern={pattern_name!r} note={bad_note!r}"
            )

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\nSummary: {total_validated}/{total_cards} validated")

    if errors:
        print("\nFAILURES:")
        for e in errors:
            print(f"  FAIL: {e}")
        sys.exit(1)

    print(
        "\nHarness v5 PASSED (STRICT): all 8/8 cards validated per table, "
        "final_note_omitted_count=0, deterministic_visible_count=0, "
        "Northman modifier_status=confirmed_listing_context, "
        "no rating/review-primary notes, taproom view addressed honestly, "
        "izakaya concept/menu anchors used, all PR #252 bad notes rejected"
    )


if __name__ == "__main__":
    main()
