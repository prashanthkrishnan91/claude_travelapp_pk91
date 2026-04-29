"""End-to-end proof: LLM whyPick reaches the final serialized card.

Proves:
1. Mocked LLM text flows through evidence → reasoning → sanitizer → final card
   (venue.why_pick == supporting_details.why_pick == display.display_why == LLM text)
2. display_why_source == "llm" when LLM ran; "deterministic" or "fallback" otherwise
3. When validation fails, fallback triggers and generation_method == deterministic

Also generates three concrete card JSON examples (cocktail bars Chicago,
Michelin tasting menu Chicago, Mexican restaurants Seattle) as would be
serialized for the frontend.
"""

import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.concierge import GoogleVerification, SourceEvidence
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


_LLM_TEXT = "Billy Sunday is a cocktail bar in West Town with deep review volume, a solid evening pick."


# ── Core proof: LLM text reaches all three card fields ───────────────────────

def test_llm_text_reaches_all_three_card_fields():
    """Mocked LLM output must appear in venue.why_pick, supporting_details.why_pick,
    and display.display_why unchanged."""
    hits = [_hit("Billy Sunday", snippet="Cocktail bar at 1143 N Bosworth Ave, Chicago.")]
    google_map = {"billy sunday": _gv("Billy Sunday", 4.5, 1800, "1143 N Bosworth Ave, Chicago, IL", ["cocktail_bar"])}
    svc = _make_svc(hits, google_map)

    llm_payload = {
        "whyPick": _LLM_TEXT,
        "evidenceIdsUsed": [],
        "confidence": "high",
        "fallbackReason": "A reliable cocktail bar.",
    }

    with patch("app.concierge.whypick_prompt.generate_llm_why_pick", return_value=llm_payload):
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars in Chicago")

    assert result.restaurants, "Expected at least one card"
    card = result.restaurants[0]

    # All three alignment fields must carry the LLM text
    assert card.why_pick == _LLM_TEXT, f"venue.why_pick mismatch: {card.why_pick!r}"
    assert card.supporting_details is not None
    assert card.supporting_details.why_pick == _LLM_TEXT, f"supporting_details.why_pick mismatch: {card.supporting_details.why_pick!r}"
    assert card.display is not None
    assert card.display.display_why == _LLM_TEXT, f"display.display_why mismatch: {card.display.display_why!r}"

    # generation_method must be traceable in the final card
    assert card.display.display_why_source == "llm", f"display_why_source: {card.display.display_why_source!r}"
    assert card.reason_source == "llm", f"reason_source: {card.reason_source!r}"


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
    # Deterministic text must not contain banned strings
    assert "tavily" not in (card.why_pick or "").lower()
    assert "yelp" not in (card.why_pick or "").lower()


def test_llm_validation_fail_uses_deterministic_not_llm_text():
    """When LLM returns text with a banned string (tavily), reasoning.py's BANNED_STRINGS_RE
    catches it before it reaches the card, and the deterministic fallback is used instead."""
    hits = [_hit("Billy Sunday", snippet="Cocktail bar at 1143 N Bosworth Ave, Chicago.")]
    google_map = {"billy sunday": _gv("Billy Sunday", 4.5, 1800, "1143 N Bosworth Ave, Chicago, IL", ["cocktail_bar"])}
    svc = _make_svc(hits, google_map)

    # "tavily" is in BANNED_STRINGS_RE in reasoning.py — blocked even if generate_llm_why_pick returns it
    bad_llm_payload = {
        "whyPick": "Tavily research confirms this is a top cocktail bar.",
        "evidenceIdsUsed": [],
        "confidence": "high",
        "fallbackReason": "A reliable cocktail bar.",
    }

    with patch("app.concierge.whypick_prompt.generate_llm_why_pick", return_value=bad_llm_payload):
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars in Chicago")

    assert result.restaurants
    card = result.restaurants[0]

    # The banned LLM text must NOT appear in the final card
    assert "tavily" not in (card.why_pick or "").lower(), "Banned LLM text leaked into final card"
    assert card.display.display_why_source != "llm", "display_why_source should not be 'llm' when LLM text was banned"


# ── Serialized card JSON examples ─────────────────────────────────────────────
#
# These are the exact JSON structures the frontend receives.
# Run with: pytest -s tests/test_end_to_end_whypick_proof.py::test_serialized_card_examples
#
def test_serialized_card_examples():
    """Generate and validate final serialized card JSON for three scenarios."""
    import json

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

    # ── Build compact serialized output for each card ─────────────────────────
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

    # Print for human review
    print("\n\n=== SERIALIZED CARD EXAMPLES (final payload) ===\n")
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
