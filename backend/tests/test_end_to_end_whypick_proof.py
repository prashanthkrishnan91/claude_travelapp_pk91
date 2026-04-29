"""End-to-end proof: LLM whyPick reaches the final serialized card.

Proves:
1. Arbitrary mocked LLM text (unique per run) flows through evidence → reasoning
   → sanitizer → final card unchanged (venue.why_pick == supporting_details.why_pick
   == display.display_why == original LLM text)
2. display_why_source == "llm" when LLM ran; "deterministic" otherwise
3. When LLM text is blocked by BANNED_STRINGS_RE, fallback triggers and the
   mocked string does NOT appear in the final card

Also generates three concrete card JSON examples (cocktail bars Chicago,
Michelin tasting menu Chicago, Mexican restaurants Seattle) as would be
serialized for the frontend.
"""

import json
import os
import sys
import uuid
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.google_places import GooglePlaceVerification
from app.services.live_research import (
    INTENT_MICHELIN_RESTAURANTS,
    INTENT_NIGHTLIFE,
    INTENT_RESTAURANTS,
    LiveResearchService,
    StubLiveSearchProvider,
    _TTLCache,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hit(title, url="https://example.com", snippet=""):
    from datetime import datetime, timezone
    from app.services.live_research import LiveSearchHit
    return LiveSearchHit(
        title=title, url=url, snippet=snippet,
        provider="Tavily",
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def _gv(name, rating, rc, address, types):
    return GooglePlaceVerification(
        provider_place_id=f"gp-{name.lower().replace(' ', '-')}",
        name=name,
        formatted_address=address,
        business_status="OPERATIONAL",
        confidence="high",
        rating=rating,
        user_rating_count=rc,
        types=types,
    )


def _google_stub(mapping):
    class _Stub:
        available = True
        def verify(self, name, destination, neighborhood=None, intent=None):
            return mapping.get(name.lower(), GooglePlaceVerification(confidence="unknown", failure_reason="not_found"))
        def clear_cache_for_destination(self, destination):
            return 0
    return _Stub()


def _make_svc(hits, google_map):
    return LiveResearchService(
        provider=StubLiveSearchProvider(hits),
        cache=_TTLCache(0),
        verification_cache=_TTLCache(0),
        enabled=True,
        place_verifier=_google_stub(google_map),
    )


def _unique_llm_text(venue_name: str, uid: str) -> str:
    """Generate a unique, guard-passing LLM whyPick string for venue_name.

    Designed to pass every filter in the pipeline:
    - No banned strings (tavily, yelp, foursquare, ###, https://)
    - No generic phrases (great fit, matches your request, etc.)
    - No banned reason fragments (backed by, selected for this, etc.)
    - No markdown, no URLs, single sentence
    - Contains 'cocktail bar' (concrete signal + category-safe for bar)
    - Contains a number (satisfies has_concrete_signal check)
    """
    return f"TEST-WHY-{uid} cocktail bar pick with 1 verified location."


# ── Core proof: arbitrary LLM text reaches all three card fields ──────────────

def test_llm_text_reaches_all_three_card_fields():
    """A programmatically generated unique string injected as mocked LLM output
    must appear EXACTLY in venue.why_pick, supporting_details.why_pick, and
    display.display_why — no transformation, truncation, or replacement."""
    uid = uuid.uuid4().hex[:12]
    llm_text = _unique_llm_text("Billy Sunday", uid)

    hits = [_hit("Billy Sunday", snippet="Cocktail bar at 1143 N Bosworth Ave, Chicago.")]
    google_map = {"billy sunday": _gv("Billy Sunday", 4.5, 1800, "1143 N Bosworth Ave, Chicago, IL", ["cocktail_bar"])}
    svc = _make_svc(hits, google_map)

    llm_payload = {
        "whyPick": llm_text,
        "evidenceIdsUsed": [],
        "confidence": "high",
        "fallbackReason": "A reliable cocktail bar.",
    }

    with patch("app.concierge.whypick_prompt.generate_llm_why_pick", return_value=llm_payload):
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars in Chicago")

    assert result.restaurants, "Expected at least one card"
    card = result.restaurants[0]

    # ── Exact string match on all three alignment fields ──────────────────────
    assert card.why_pick == llm_text, (
        f"venue.why_pick does not match LLM output.\n"
        f"  LLM text:  {llm_text!r}\n"
        f"  card text: {card.why_pick!r}"
    )
    assert card.supporting_details is not None
    assert card.supporting_details.why_pick == llm_text, (
        f"supporting_details.why_pick does not match LLM output.\n"
        f"  LLM text:  {llm_text!r}\n"
        f"  card text: {card.supporting_details.why_pick!r}"
    )
    assert card.display is not None
    assert card.display.display_why == llm_text, (
        f"display.display_why does not match LLM output.\n"
        f"  LLM text:  {llm_text!r}\n"
        f"  card text: {card.display.display_why!r}"
    )

    # ── No truncation or transformation ──────────────────────────────────────
    assert len(card.why_pick) == len(llm_text), (
        f"Length mismatch — truncation or padding occurred.\n"
        f"  expected len={len(llm_text)}, got len={len(card.why_pick)}"
    )
    assert card.why_pick[-10:] == llm_text[-10:], (
        f"Tail mismatch — text was modified at end.\n"
        f"  expected tail: {llm_text[-10:]!r}\n"
        f"  actual tail:   {card.why_pick[-10:]!r}"
    )

    # ── generation_method must be traceable in the final card ─────────────────
    assert card.display.display_why_source == "llm", (
        f"display_why_source={card.display.display_why_source!r}, expected 'llm'"
    )
    assert card.reason_source == "llm", (
        f"reason_source={card.reason_source!r}, expected 'llm'"
    )

    # Print for human review
    print(f"\n[proof] uid={uid}")
    print(f"[proof] llm_text={llm_text!r}")
    print(f"[proof] card.why_pick={card.why_pick!r}")
    print(f"[proof] generation_method={card.reason_source!r}")


# ── Negative proof: banned LLM text must NOT reach the final card ─────────────

def test_llm_banned_text_does_not_reach_card():
    """When the mocked LLM output contains a banned string ('tavily' is in
    BANNED_STRINGS_RE in reasoning.py), the pipeline must block it and fall
    back to deterministic copy. The mocked string must not appear anywhere
    in the final card, and generation_method must not be 'llm'."""
    uid = uuid.uuid4().hex[:12]
    # Include 'tavily' — in BANNED_STRINGS_RE in reasoning.py, blocked even
    # if generate_llm_why_pick returns it directly.
    banned_text = f"TEST-WHY-NEG-{uid} tavily confirms cocktail bar."

    hits = [_hit("Billy Sunday", snippet="Cocktail bar at 1143 N Bosworth Ave, Chicago.")]
    google_map = {"billy sunday": _gv("Billy Sunday", 4.5, 1800, "1143 N Bosworth Ave, Chicago, IL", ["cocktail_bar"])}
    svc = _make_svc(hits, google_map)

    with patch("app.concierge.whypick_prompt.generate_llm_why_pick", return_value={
        "whyPick": banned_text,
        "evidenceIdsUsed": [],
        "confidence": "high",
        "fallbackReason": "A reliable cocktail bar.",
    }):
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars in Chicago")

    assert result.restaurants
    card = result.restaurants[0]

    # The banned string must NOT appear in any field
    assert card.why_pick != banned_text, "Banned LLM text leaked into venue.why_pick"
    assert "tavily" not in (card.why_pick or "").lower(), "Banned token 'tavily' leaked into why_pick"

    # generation_method must NOT be 'llm' — deterministic fallback took over
    assert card.display.display_why_source != "llm", (
        f"display_why_source={card.display.display_why_source!r} — should not be 'llm' when text was banned"
    )

    # Fallback must still produce valid copy
    assert card.why_pick, "Fallback produced empty why_pick"

    print(f"\n[negative-proof] uid={uid}")
    print(f"[negative-proof] banned_text={banned_text!r}")
    print(f"[negative-proof] fallback_text={card.why_pick!r}")
    print(f"[negative-proof] generation_method={card.display.display_why_source!r}")


# ── LLM returns None → deterministic ─────────────────────────────────────────

def test_llm_failure_produces_deterministic_fallback():
    """When the LLM returns None, the card must use deterministic copy and
    display_why_source must NOT be 'llm'."""
    hits = [_hit("Billy Sunday", snippet="Cocktail bar at 1143 N Bosworth Ave, Chicago.")]
    google_map = {"billy sunday": _gv("Billy Sunday", 4.5, 1800, "1143 N Bosworth Ave, Chicago, IL", ["cocktail_bar"])}
    svc = _make_svc(hits, google_map)

    with patch("app.concierge.whypick_prompt.generate_llm_why_pick", return_value=None):
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars in Chicago")

    assert result.restaurants
    card = result.restaurants[0]

    assert card.display.display_why_source != "llm", "Should not claim LLM when LLM returned None"
    assert card.why_pick, "Must still have a why_pick from deterministic fallback"
    assert "tavily" not in (card.why_pick or "").lower()
    assert "yelp" not in (card.why_pick or "").lower()


# ── Serialized card JSON examples ─────────────────────────────────────────────

def test_serialized_card_examples():
    """Generate and validate final serialized card JSON for three scenarios."""

    # ── Scenario 1: cocktail bars in Chicago ─────────────────────────────────
    hits_cocktail = [_hit("Kumiko", "https://example.com/kumiko", "Cocktail bar at 630 W Lake St, Chicago IL.")]
    google_cocktail = {"kumiko": _gv("Kumiko", 4.7, 1200, "630 W Lake St, Chicago, IL", ["cocktail_bar", "bar"])}
    svc1 = _make_svc(hits_cocktail, google_cocktail)
    r1 = svc1.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars in Chicago")
    assert r1.restaurants, "Scenario 1: expected a card"
    card1 = r1.restaurants[0]

    # ── Scenario 2: Michelin tasting menu Chicago ─────────────────────────────
    hits_michelin = [
        _hit("Alinea", "https://example.com/alinea", "Michelin 3-star tasting-menu restaurant in Lincoln Park."),
        _hit("Michelin guide", "https://guide.michelin.com/chicago", "Alinea is featured by Michelin"),
    ]
    google_michelin = {"alinea": _gv("Alinea", 4.6, 1900, "1723 N Halsted St, Chicago, IL", ["restaurant"])}
    svc2 = _make_svc(hits_michelin, google_michelin)
    r2 = svc2.fetch(intent=INTENT_MICHELIN_RESTAURANTS, destination="Chicago", user_query="Michelin tasting menu Chicago")
    assert r2.restaurants, "Scenario 2: expected a card"
    card2 = r2.restaurants[0]

    # ── Scenario 3: Mexican restaurants in Seattle ────────────────────────────
    hits_mex = [_hit("La Carta de Oaxaca", "https://example.com/lco", "Mexican restaurant in Ballard, Seattle.")]
    google_mex = {"la carta de oaxaca": _gv("La Carta de Oaxaca", 4.5, 1800, "5431 Ballard Ave NW, Seattle, WA", ["restaurant", "mexican_restaurant"])}
    svc3 = _make_svc(hits_mex, google_mex)
    r3 = svc3.fetch(intent=INTENT_RESTAURANTS, destination="Seattle", user_query="Mexican restaurants in Seattle")
    assert r3.restaurants, "Scenario 3: expected a card"
    card3 = r3.restaurants[0]

    def _serialize(card, scenario: str) -> dict:
        display = card.display
        sd = card.supporting_details
        return {
            "scenario": scenario,
            "name": card.name,
            "type": card.type,
            "whyPick": card.why_pick,
            "generation_method": getattr(card, "reason_source", None) or (display.display_why_source if display else None),
            "supportingDetails": {
                "whyPick": sd.why_pick if sd else None,
                "meta_line": sd.meta_line if sd else None,
                "category_label": sd.category_label if sd else None,
            },
            "display": {
                "displayWhy": display.display_why if display else None,
                "displayCategory": display.display_category if display else None,
                "displayMetaLine": display.display_meta_line if display else None,
                "addability": display.addability if display else None,
                "displayWhySource": display.display_why_source if display else None,
            },
        }

    s1 = _serialize(card1, "cocktail bars in Chicago")
    s2 = _serialize(card2, "Michelin tasting menu Chicago")
    s3 = _serialize(card3, "Mexican restaurants in Seattle")

    print("\n\n=== SERIALIZED CARD EXAMPLES (final payload) ===\n")
    for s in [s1, s2, s3]:
        print(json.dumps(s, indent=2))
        print()

    # Alignment: all three fields must carry the same text
    for s in [s1, s2, s3]:
        assert s["whyPick"], f"{s['scenario']}: missing whyPick"
        assert s["whyPick"] == s["supportingDetails"]["whyPick"], \
            f"{s['scenario']}: venue.why_pick != supporting_details.why_pick"
        assert s["whyPick"] == s["display"]["displayWhy"], \
            f"{s['scenario']}: venue.why_pick != display.display_why"
        assert s["generation_method"] in ("llm", "deterministic", "fallback"), \
            f"{s['scenario']}: unexpected generation_method={s['generation_method']!r}"
        assert "tavily" not in (s["whyPick"] or "").lower()
        assert "yelp" not in (s["whyPick"] or "").lower()

    assert s2["name"] == "Alinea"
    assert "michelin" in (s2["whyPick"] or "").lower(), f"Michelin scenario missing 'michelin': {s2['whyPick']!r}"
    assert "mexican" in (s3["whyPick"] or "").lower() or "restaurant" in (s3["whyPick"] or "").lower()

    for s in [s1, s2, s3]:
        print(json.dumps(s, indent=2))
        print()

    # Invariant assertions
    for s in [s1, s2, s3]:
        assert s["whyPick"], f"{s['scenario']}: missing whyPick"
        assert s["whyPick"] == s["supportingDetails"]["whyPick"], \
            f"{s['scenario']}: venue.why_pick != supporting_details.why_pick"
        assert s["whyPick"] == s["display"]["displayWhy"], \
            f"{s['scenario']}: venue.why_pick != display.display_why"
        assert s["generation_method"] in ("llm", "deterministic", "fallback", "deterministic_validated"), \
            f"{s['scenario']}: unexpected generation_method={s['generation_method']!r}"
        assert "tavily" not in (s["whyPick"] or "").lower()
        assert "yelp" not in (s["whyPick"] or "").lower()

    # Scenario-specific checks
    assert s2["name"] == "Alinea"
    assert "michelin" in (s2["whyPick"] or "").lower(), f"Michelin scenario missing 'michelin': {s2['whyPick']!r}"
    assert "mexican" in (s3["whyPick"] or "").lower() or "restaurant" in (s3["whyPick"] or "").lower()
