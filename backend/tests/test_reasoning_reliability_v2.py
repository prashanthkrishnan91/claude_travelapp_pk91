"""Tests for Reasoning Reliability v2 — three-pass orchestrator.

Acceptance criteria covered:
1. Full success: all cards get validated LLM notes in pass 1.
2. Partial first-pass, retry fills misses: 1/6 from pass 1 → retry recovers 5/6.
3. Primary model timeout, fallback model succeeds: all cards reasoned via fallback.
4. Bad template returned by LLM, retry repairs: validator rejects → retry produces valid note.
5. All attempts fail: zero display-ready cards, controlled failure, no deterministic notes.
6. Legacy field suppression: displayWhyValidated=false → frontend returns "" not legacy text.
7. Target query matrix: 7 queries × top 3 cards, all validated.
8. Telemetry assertions for all scenarios.
9. Frontend contract: pickCardReason gating.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch


# ── Shared fixtures ──────────────────────────────────────────────────────────

def _make_entity(
    name="Test Brewery",
    place_id="pid_test",
    types=None,
    rating=4.5,
    review_count=900,
    address="100 W Riverwalk Dr, Chicago, IL",
    maps_uri="https://maps.google.com/?cid=1",
    source_query="breweries near the river Chicago",
):
    from app.concierge.place_entity_layer import PlaceEntity
    return PlaceEntity(
        place_id=place_id,
        name=name,
        types=types or ["brewery"],
        primary_type=types[0] if types else "brewery",
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


def _make_brewery_cards(n=6, query="breweries near the river", destination="Chicago"):
    from app.concierge.frame_extractor import extract_frame
    from app.concierge.ranker import RankScore, build_evidence_bundle
    from app.concierge.safe_reason_builder import build_safe_reason

    names = [
        "The Northman Beer & Cider Garden",
        "Forbidden Root Restaurant & Brewery",
        "Goose Island Brewhouse",
        "Half Acre Beer Company",
        "Revolution Brewing",
        "Empirical Brewery",
    ]
    ratings = [4.7, 4.6, 4.5, 4.6, 4.7, 4.4]
    reviews = [1344, 1958, 802, 750, 2100, 430]
    pids = [f"pid_{i}" for i in range(n)]
    addrs = [
        "3291 N Milwaukee Ave, Chicago, IL",
        "1746 W Chicago Ave, Chicago, IL",
        "1800 N Clybourn Ave, Chicago, IL",
        "4257 N Lincoln Ave, Chicago, IL",
        "2323 N Milwaukee Ave, Chicago, IL",
        "1801 W Foster Ave, Chicago, IL",
    ]

    frame = extract_frame(query, destination)
    cards_data = []
    for i in range(n):
        entity = _make_entity(
            name=names[i],
            place_id=pids[i],
            rating=ratings[i],
            review_count=reviews[i],
            address=addrs[i],
            source_query=f"brewery Chicago near river",
        )
        score = RankScore(total=0.75, subtype_fit=0.90, geo_fit=0.6)
        ev = build_evidence_bundle(entity, frame, score)
        det = build_safe_reason(entity, ev, frame, score)
        cards_data.append((entity, ev, score, det))
    return cards_data, frame


def _valid_notes_for(n: int, names: list) -> dict:
    """Produce valid LLM-style notes for n brewery cards."""
    templates = [
        "{name} focuses on craft ciders and ales with a lively neighborhood atmosphere near Avondale.",
        "{name} blends botanical brewing with a gastropub menu, a strong pick for adventurous beer fans.",
        "{name} is the flagship Goose Island location with a wide tap list and proximity to Lincoln Park.",
        "{name} is a Logan Square taproom known for experimental small-batch releases and a laid-back vibe.",
        "{name} is a Northwest Side powerhouse with a massive taproom and year-round seasonal programs.",
        "{name} is a Bowmanville taproom that emphasizes local distribution and experimental batches.",
    ]
    result = {}
    for i in range(n):
        note = templates[i % len(templates)].format(name=names[i % len(names)])
        result[str(i + 1)] = note
    return result


# ══════════════════════════════════════════════════════════════════════════════
# 1. FULL SUCCESS — all cards reasoned in pass 1
# ══════════════════════════════════════════════════════════════════════════════

_ENABLE_FLAG = patch("app.concierge.batched_reason_builder._flag_enabled", return_value=True)


class TestFullSuccess:
    """All 6 cards get validated LLM notes from the primary model in pass 1."""

    def test_all_cards_validated_pass1(self):
        from app.concierge.batched_reason_builder import (
            build_reasons_with_retry, SOURCE_PRIMARY, SOURCE_RETRY, SOURCE_FALLBACK, SOURCE_OMITTED
        )
        cards_data, frame = _make_brewery_cards(6)
        names = [e.name for e, *_ in cards_data]
        llm_json = json.dumps(_valid_notes_for(6, names))

        with _ENABLE_FLAG, patch("app.concierge.batched_reason_builder._call_llm", return_value=llm_json):
            reasons, result = build_reasons_with_retry(cards_data, frame)

        assert result.accepted_count == 6, f"Expected 6, got {result.accepted_count}"
        assert result.final_note_omitted_count == 0
        assert result.deterministic_visible_count == 0
        assert result.retry_recovered_count == 0
        assert result.fallback_model_used_count == 0
        assert result.success is True
        # All cards validated with primary source
        for i in range(1, 7):
            cr = reasons[str(i)]
            assert cr.validated is True, f"Card {i} not validated"
            assert cr.note, f"Card {i} has empty note"
            assert cr.source == SOURCE_PRIMARY, f"Card {i} source={cr.source}"
            assert cr.retry_used is False
            assert cr.fallback_model_used is False

    def test_telemetry_full_success(self):
        from app.concierge.batched_reason_builder import build_reasons_with_retry, SOURCE_PRIMARY
        cards_data, frame = _make_brewery_cards(6)
        names = [e.name for e, *_ in cards_data]
        llm_json = json.dumps(_valid_notes_for(6, names))

        with _ENABLE_FLAG, patch("app.concierge.batched_reason_builder._call_llm", return_value=llm_json):
            reasons, result = build_reasons_with_retry(cards_data, frame)

        # Required telemetry contract for success scenario
        assert result.success is True
        assert result.accepted_count == 6
        assert result.deterministic_visible_count == 0
        assert result.final_note_omitted_count == 0
        assert result.visible_note_source_counts.get(SOURCE_PRIMARY, 0) == 6

    def test_no_note_omitted_in_success_path(self):
        """No card in the success path should have an empty note."""
        from app.concierge.batched_reason_builder import build_reasons_with_retry
        cards_data, frame = _make_brewery_cards(6)
        names = [e.name for e, *_ in cards_data]
        llm_json = json.dumps(_valid_notes_for(6, names))

        with _ENABLE_FLAG, patch("app.concierge.batched_reason_builder._call_llm", return_value=llm_json):
            reasons, result = build_reasons_with_retry(cards_data, frame)

        for idx_str, cr in reasons.items():
            assert cr.note != "", f"Card {idx_str} has empty note in success path"


# ══════════════════════════════════════════════════════════════════════════════
# 2. PARTIAL FIRST-PASS — retry fills misses
# ══════════════════════════════════════════════════════════════════════════════

class TestPartialFirstPassRetryFills:
    """Pass 1 returns valid note for only 1 of 6; retry (pass 2) fills the other 5."""

    def test_retry_recovers_missing_cards(self):
        from app.concierge.batched_reason_builder import (
            build_reasons_with_retry, SOURCE_PRIMARY, SOURCE_RETRY
        )
        cards_data, frame = _make_brewery_cards(6)
        names = [e.name for e, *_ in cards_data]

        # Pass 1 returns only card 1 with a valid note (cards 2-6 are missing from JSON)
        pass1_response = json.dumps({"1": (
            "The Northman Beer & Cider Garden is a celebrated Avondale spot "
            "known for its extensive cider and beer selection."
        )})
        # Pass 2 (retry) provides the remaining 5 cards — the subset is [1..5] in the retry call
        retry_notes = {
            str(i + 1): f"{names[i + 1]} is a well-regarded Chicago brewery with a distinctive tap list and loyal neighborhood following."
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

        with _ENABLE_FLAG, patch("app.concierge.batched_reason_builder._call_llm", side_effect=mock_llm):
            reasons, result = build_reasons_with_retry(cards_data, frame)

        assert result.accepted_count == 6, f"Expected 6, got {result.accepted_count}"
        assert result.retry_recovered_count >= 1, "Expected at least some retry recovery"
        assert result.final_note_omitted_count == 0
        assert result.deterministic_visible_count == 0
        assert result.fallback_model_used_count == 0
        # Card 1 came from pass 1
        assert reasons["1"].source == SOURCE_PRIMARY
        assert reasons["1"].retry_used is False
        # Cards 2-6 came from retry
        for i in range(2, 7):
            cr = reasons[str(i)]
            assert cr.validated is True, f"Card {i} not validated after retry"
            assert cr.note, f"Card {i} has empty note after retry"

    def test_telemetry_partial_then_retry(self):
        from app.concierge.batched_reason_builder import build_reasons_with_retry
        cards_data, frame = _make_brewery_cards(3)
        names = [e.name for e, *_ in cards_data]

        pass1 = json.dumps({"1": f"{names[0]} is a celebrated North Side taproom known for rotating seasonal ales."})
        pass2 = json.dumps({
            "1": f"{names[1]} blends craft brewing with a botanical menu, a strong pick for adventurous beer fans.",
            "2": f"{names[2]} is the flagship Goose Island location with a wide tap list near Clybourn Corridor.",
        })

        call_count = 0
        def mock_llm(prompt, timeout, model=""):
            nonlocal call_count
            call_count += 1
            return pass1 if call_count == 1 else pass2

        with _ENABLE_FLAG, patch("app.concierge.batched_reason_builder._call_llm", side_effect=mock_llm):
            reasons, result = build_reasons_with_retry(cards_data, frame)

        assert result.success is True
        assert result.accepted_count == 3
        assert result.retry_recovered_count >= 1
        assert result.deterministic_visible_count == 0
        assert result.final_note_omitted_count == 0


# ══════════════════════════════════════════════════════════════════════════════
# 3. PRIMARY MODEL TIMEOUT — fallback model succeeds
# ══════════════════════════════════════════════════════════════════════════════

class TestPrimaryTimeoutFallbackSucceeds:
    """Primary model times out (no response). Fallback model fills all cards."""

    def test_fallback_fills_all_after_primary_timeout(self):
        from app.concierge.batched_reason_builder import (
            build_reasons_with_retry, SOURCE_FALLBACK, _PRIMARY_MODEL, _FALLBACK_MODEL
        )
        cards_data, frame = _make_brewery_cards(4)
        names = [e.name for e, *_ in cards_data]

        fallback_notes = {
            str(i + 1): f"{names[i]} is a Chicago institution with a devoted craft-beer following and consistent quality."
            for i in range(4)
        }
        fallback_json = json.dumps(fallback_notes)

        def mock_llm(prompt, timeout, model=""):
            resolved_model = model or _PRIMARY_MODEL
            if resolved_model == _PRIMARY_MODEL:
                return None  # simulate timeout
            return fallback_json  # fallback model succeeds

        with _ENABLE_FLAG, patch("app.concierge.batched_reason_builder._call_llm", side_effect=mock_llm):
            reasons, result = build_reasons_with_retry(cards_data, frame)

        assert result.accepted_count == 4
        assert result.fallback_model_used_count >= 1
        assert result.final_note_omitted_count == 0
        assert result.deterministic_visible_count == 0

        for idx_str, cr in reasons.items():
            assert cr.validated is True, f"Card {idx_str} not validated"
            assert cr.note, f"Card {idx_str} has empty note"
            assert cr.fallback_model_used is True, f"Card {idx_str} should have fallback_model_used=True"
            assert cr.source == SOURCE_FALLBACK, f"Card {idx_str} source={cr.source}"

    def test_telemetry_primary_timeout_fallback_success(self):
        from app.concierge.batched_reason_builder import build_reasons_with_retry, _PRIMARY_MODEL
        cards_data, frame = _make_brewery_cards(3)
        names = [e.name for e, *_ in cards_data]

        fallback_json = json.dumps({
            str(i + 1): f"{names[i]} is a well-regarded craft brewery in Chicago with a reliable neighborhood following."
            for i in range(3)
        })

        def mock_llm(prompt, timeout, model=""):
            resolved_model = model or _PRIMARY_MODEL
            if resolved_model == _PRIMARY_MODEL:
                return None
            return fallback_json

        with _ENABLE_FLAG, patch("app.concierge.batched_reason_builder._call_llm", side_effect=mock_llm):
            reasons, result = build_reasons_with_retry(cards_data, frame)

        assert result.success is True
        assert result.accepted_count == 3
        assert result.deterministic_visible_count == 0
        assert result.final_note_omitted_count == 0
        assert result.fallback_model_used_count >= 1
        # visible_note_source_counts must contain only LLM/evidence-grounded sources
        for source in result.visible_note_source_counts:
            assert "omitted" not in source
            assert "deterministic" not in source


# ══════════════════════════════════════════════════════════════════════════════
# 4. BAD TEMPLATE RETURNED BY LLM — retry repairs
# ══════════════════════════════════════════════════════════════════════════════

class TestBadTemplateRetryRepairs:
    """LLM returns rejected template; retry produces valid note."""

    def test_template_rejected_retry_accepted(self):
        from app.concierge.batched_reason_builder import build_reasons_with_retry, SOURCE_PRIMARY, SOURCE_RETRY
        cards_data, frame = _make_brewery_cards(3)
        names = [e.name for e, *_ in cards_data]

        # Pass 1: card 1 returns a banned name+rating template; cards 2-3 valid
        bad_template = f"{names[0]} on the Riverwalk on Riverwalk — 4.7★ from 1,344 reviews."
        pass1 = json.dumps({
            "1": bad_template,
            "2": f"{names[1]} blends botanical brewing with a gastropub menu, a strong pick for adventurous fans.",
            "3": f"{names[2]} is the flagship Goose Island location with a wide tap list near Lincoln Park.",
        })
        # Pass 2 (retry): card 1 is retried and returns a valid note
        pass2 = json.dumps({
            "1": f"{names[0]} is celebrated for its cider-focused program and lively Avondale neighborhood vibe.",
        })

        call_count = 0
        def mock_llm(prompt, timeout, model=""):
            nonlocal call_count
            call_count += 1
            return pass1 if call_count == 1 else pass2

        with _ENABLE_FLAG, patch("app.concierge.batched_reason_builder._call_llm", side_effect=mock_llm):
            reasons, result = build_reasons_with_retry(cards_data, frame)

        # All 3 cards must have validated notes
        assert result.accepted_count == 3
        assert result.final_note_omitted_count == 0
        assert result.deterministic_visible_count == 0
        # Card 1 came from retry (template was rejected in pass 1)
        cr1 = reasons["1"]
        assert cr1.validated is True
        assert cr1.retry_used is True
        assert cr1.source == SOURCE_RETRY
        assert bad_template not in cr1.note
        # Cards 2-3 came from pass 1
        assert reasons["2"].source == SOURCE_PRIMARY
        assert reasons["3"].source == SOURCE_PRIMARY

    def test_name_rating_template_is_rejected_by_validator(self):
        """The validator must reject a pure name+rating template."""
        from app.concierge.reason_validator import validate_reason
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, build_evidence_bundle

        entity = _make_entity(name="The Northman Beer & Cider Garden", rating=4.7, review_count=1344)
        frame = extract_frame("breweries near the river", "Chicago")
        score = RankScore(total=0.75, subtype_fit=0.90, geo_fit=0.6)
        ev = build_evidence_bundle(entity, frame, score)

        template = "The Northman Beer & Cider Garden on the Riverwalk on Riverwalk — 4.7★ from 1,344 reviews."
        is_valid, rejection = validate_reason(template, frame, ev)
        assert is_valid is False, "Name+rating template must be rejected"
        assert rejection, "Rejection reason must be non-empty"


# ══════════════════════════════════════════════════════════════════════════════
# 5. ALL ATTEMPTS FAIL — controlled failure, zero display-ready cards
# ══════════════════════════════════════════════════════════════════════════════

class TestAllAttemptsFail:
    """All model calls time out or return invalid. No cards should be returned."""

    def test_all_timeouts_zero_validated_cards(self):
        from app.concierge.batched_reason_builder import build_reasons_with_retry, SOURCE_OMITTED

        cards_data, frame = _make_brewery_cards(3)

        with _ENABLE_FLAG, patch("app.concierge.batched_reason_builder._call_llm", return_value=None):
            reasons, result = build_reasons_with_retry(cards_data, frame)

        assert result.success is False
        assert result.accepted_count == 0
        assert result.deterministic_visible_count == 0
        assert result.final_note_omitted_count == 3
        # No validated cards
        for idx_str, cr in reasons.items():
            assert cr.validated is False, f"Card {idx_str} should not be validated when all fail"
            assert cr.note == "", f"Card {idx_str} should have empty note"
            assert cr.source == SOURCE_OMITTED, f"Card {idx_str} source should be omitted"

    def test_all_invalid_responses_zero_validated_cards(self):
        from app.concierge.batched_reason_builder import build_reasons_with_retry

        cards_data, frame = _make_brewery_cards(3)
        # Return invalid JSON that won't parse
        with _ENABLE_FLAG, patch("app.concierge.batched_reason_builder._call_llm", return_value="not json at all"):
            reasons, result = build_reasons_with_retry(cards_data, frame)

        assert result.success is False
        assert result.accepted_count == 0
        assert result.deterministic_visible_count == 0
        for cr in reasons.values():
            assert cr.validated is False

    def test_all_fail_no_deterministic_visible_notes(self):
        """Even when all LLM attempts fail, deterministic notes must not appear."""
        from app.concierge.batched_reason_builder import build_reasons_with_retry

        cards_data, frame = _make_brewery_cards(3)
        with _ENABLE_FLAG, patch("app.concierge.batched_reason_builder._call_llm", return_value=None):
            reasons, result = build_reasons_with_retry(cards_data, frame)

        assert result.deterministic_visible_count == 0
        for cr in reasons.values():
            # note must be empty (not deterministic text)
            assert cr.note == ""


# ══════════════════════════════════════════════════════════════════════════════
# 6. LEGACY FIELD SUPPRESSION — frontend pickCardReason
# ══════════════════════════════════════════════════════════════════════════════

class TestLegacyFieldSuppression:
    """pickCardReason must not use legacy fields when display object is present."""

    def _run_pick(self, card: dict) -> str:
        import sys, types
        # Simulate JS pickCardReason logic in Python for unit-testing
        display = card.get("display")
        if display is not None:
            why_validated = display.get("displayWhyValidated")
            display_why = display.get("displayWhy") or ""
            if why_validated is True and len(display_why) >= 12:
                return display_why
            return ""  # validated=false or empty — no fallback
        # Legacy path
        supporting = card.get("supportingDetails") or {}
        return supporting.get("whyPick") or card.get("whyPick") or card.get("primaryReason") or ""

    def test_validated_display_renders_note(self):
        card = {
            "display": {
                "displayWhy": "The Northman is a celebrated Avondale taproom with an extensive cider program.",
                "displayWhyValidated": True,
                "displayWhySource": "llm_evidence_pack_v2_primary",
            },
            "supportingDetails": {"whyPick": "BAD LEGACY TEXT"},
            "whyPick": "BAD LEGACY TEXT",
            "primaryReason": "BAD LEGACY TEXT",
        }
        note = self._run_pick(card)
        assert note == "The Northman is a celebrated Avondale taproom with an extensive cider program."

    def test_unvalidated_display_returns_empty(self):
        """When displayWhyValidated=False, no note is rendered even if legacy fields have text."""
        card = {
            "display": {
                "displayWhy": "The Northman Beer & Cider Garden — 4.7★ from 1,344 reviews.",
                "displayWhyValidated": False,
                "displayWhySource": "omitted",
            },
            "supportingDetails": {"whyPick": "LEGACY TEXT THAT SHOULD NOT APPEAR"},
            "whyPick": "ALSO SHOULD NOT APPEAR",
            "primaryReason": "NOR THIS",
        }
        note = self._run_pick(card)
        assert note == "", f"Expected empty, got: {note!r}"

    def test_missing_display_falls_through_to_legacy(self):
        """Without a display object, legacy fallback works (non-semantic cards)."""
        card = {
            "supportingDetails": {"whyPick": "A legacy note that should appear."},
        }
        note = self._run_pick(card)
        assert note == "A legacy note that should appear."

    def test_display_why_too_short_returns_empty(self):
        card = {
            "display": {
                "displayWhy": "Short",
                "displayWhyValidated": True,
            },
        }
        note = self._run_pick(card)
        assert note == ""

    def test_display_why_none_returns_empty(self):
        card = {
            "display": {
                "displayWhy": None,
                "displayWhyValidated": True,
            },
        }
        note = self._run_pick(card)
        assert note == ""

    def test_legacy_fields_with_bad_text_cannot_render_for_semantic_card(self):
        """whyPick, supportingDetails.whyPick, primaryReason all have bad text.
        A semantic card (display present) with displayWhyValidated=False
        must return "" regardless of what legacy fields contain."""
        card = {
            "display": {
                "displayWhy": "",
                "displayWhyValidated": False,
                "displayWhySource": "omitted",
            },
            "supportingDetails": {
                "whyPick": "The Northman Beer & Cider Garden on the Riverwalk — 4.7★ from 1,344 reviews."
            },
            "whyPick": "Forbidden Root Restaurant & Brewery on Chicago Avenue — 4.6★ from 1,958 reviews.",
            "primaryReason": "Goose Island Brewhouse — 4.5★.",
        }
        note = self._run_pick(card)
        assert note == ""


# ══════════════════════════════════════════════════════════════════════════════
# 7. TARGET QUERY MATRIX — 7 queries, top 3 cards, all validated
# ══════════════════════════════════════════════════════════════════════════════

class TestTargetQueryMatrix:
    """All 7 acceptance queries must produce validated notes when LLM succeeds."""

    TARGET_QUERIES = [
        "izakayas",
        "izakayas with waterfront views",
        "izakayas on Fulton Street",
        "best breweries",
        "best waterfront breweries",
        "breweries near the river",
        "taprooms with a view",
    ]

    def _mock_llm_for_query(self, query: str, n: int):
        """Return a mock LLM response with n valid notes for the given query.

        Notes must pass the validator:
        - No unsupported waterfront/river/view claims
        - No location modifier falsely confirmed
        - No name+rating template structure
        - No generic boilerplate
        """
        notes = {}
        for i in range(1, n + 1):
            if "waterfront" in query or "river" in query or "view" in query:
                # Honest caveat: mention that the waterfront/view cannot be confirmed
                notes[str(i)] = (
                    f"Place {i} is a highly-rated local establishment; "
                    f"no waterfront setting is confirmed from the Google listing data."
                )
            elif "Fulton" in query:
                # Do NOT mention "Fulton" — avoids triggering modifier_confirmed validator
                notes[str(i)] = (
                    f"Place {i} is a well-regarded Japanese dining option in the West Loop "
                    f"neighborhood with a strong local following and consistent quality."
                )
            else:
                notes[str(i)] = (
                    f"Place {i} is a celebrated Chicago establishment with a loyal neighborhood "
                    f"following and a consistent tap list of locally brewed craft options."
                )
        return json.dumps(notes)

    def _make_cards_for_query(self, query: str, n: int = 3):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason

        types_map = {
            "izakaya": ["japanese_restaurant"],
            "brewery": ["brewery"],
            "taproom": ["brewery", "bar"],
        }
        concept = "izakaya" if "izakaya" in query else "brewery"
        entity_types = types_map.get(concept, ["restaurant"])

        frame = extract_frame(query, "Chicago")
        cards_data = []
        for i in range(n):
            entity = _make_entity(
                name=f"Test Place {i + 1}",
                place_id=f"pid_{i}",
                types=entity_types,
                source_query=f"{concept} Chicago",
            )
            score = RankScore(total=0.75, subtype_fit=0.85, geo_fit=0.5)
            ev = build_evidence_bundle(entity, frame, score)
            det = build_safe_reason(entity, ev, frame, score)
            cards_data.append((entity, ev, score, det))
        return cards_data, frame

    def test_query_matrix_all_validated(self):
        from app.concierge.batched_reason_builder import build_reasons_with_retry

        for query in self.TARGET_QUERIES:
            cards_data, frame = self._make_cards_for_query(query, n=3)
            llm_json = self._mock_llm_for_query(query, n=3)

            with _ENABLE_FLAG, patch("app.concierge.batched_reason_builder._call_llm", return_value=llm_json):
                reasons, result = build_reasons_with_retry(cards_data, frame)

            assert result.accepted_count == 3, (
                f"Query '{query}': expected 3 accepted, got {result.accepted_count}. "
                f"failure_reason={result.failure_reason}"
            )
            assert result.final_note_omitted_count == 0, (
                f"Query '{query}': expected 0 omitted, got {result.final_note_omitted_count}"
            )
            assert result.deterministic_visible_count == 0, (
                f"Query '{query}': deterministic_visible_count must be 0"
            )
            for i in range(1, 4):
                cr = reasons[str(i)]
                assert cr.validated is True, f"Query '{query}' card {i} not validated"
                assert cr.note, f"Query '{query}' card {i} has empty note"

    def test_query_matrix_no_note_omitted(self):
        """No card in the query matrix should have NOTE OMITTED in success path."""
        from app.concierge.batched_reason_builder import build_reasons_with_retry

        for query in self.TARGET_QUERIES:
            cards_data, frame = self._make_cards_for_query(query, n=3)
            llm_json = self._mock_llm_for_query(query, n=3)

            with _ENABLE_FLAG, patch("app.concierge.batched_reason_builder._call_llm", return_value=llm_json):
                reasons, result = build_reasons_with_retry(cards_data, frame)

            for i in range(1, 4):
                cr = reasons[str(i)]
                # "NOTE OMITTED" must never appear in a success-path result
                assert cr.note != "", f"Query '{query}' card {i}: NOTE OMITTED in success path"
                assert "NOTE OMITTED" not in cr.note


# ══════════════════════════════════════════════════════════════════════════════
# 8. DISPLAY CONTRACT — display_why_validated in model + _entity_to_card
# ══════════════════════════════════════════════════════════════════════════════

class TestDisplayContract:
    """ConciergeDisplayFields has display_why_validated; _entity_to_card sets it."""

    def test_concierge_display_fields_has_validated(self):
        from app.models.concierge import ConciergeDisplayFields
        f = ConciergeDisplayFields(
            display_name="Test", display_category="Brewery", display_why="",
            display_why_validated=True, display_why_source="llm_evidence_pack_v2_primary",
        )
        assert f.display_why_validated is True
        assert f.display_why_source == "llm_evidence_pack_v2_primary"

    def test_display_why_validated_defaults_to_false(self):
        from app.models.concierge import ConciergeDisplayFields
        f = ConciergeDisplayFields(
            display_name="Test", display_category="Brewery", display_why=""
        )
        assert f.display_why_validated is False

    def test_entity_to_card_sets_validated_true(self):
        from app.concierge.semantic_retrieval import _entity_to_card
        from app.concierge.frame_extractor import extract_frame

        entity = _make_entity()
        frame = extract_frame("breweries near the river", "Chicago")
        note = "This North Side taproom is known for its rotating seasonal ales and approachable atmosphere."

        card = _entity_to_card(
            entity, note, frame,
            reason_source="llm_evidence_pack_v2_primary",
            reason_validated=True,
        )
        assert card is not None
        assert card.display is not None
        assert card.display.display_why_validated is True
        assert card.display.display_why_source == "llm_evidence_pack_v2_primary"
        assert card.display.display_why == note

    def test_entity_to_card_defaults_validated_false(self):
        from app.concierge.semantic_retrieval import _entity_to_card
        from app.concierge.frame_extractor import extract_frame

        entity = _make_entity()
        frame = extract_frame("breweries near the river", "Chicago")

        card = _entity_to_card(entity, "", frame)
        assert card is not None
        assert card.display is not None
        assert card.display.display_why_validated is False

    def test_add_to_day_save_maps_ratings_preserved(self):
        """Non-note card fields must remain intact when display_why_validated is set."""
        from app.concierge.semantic_retrieval import _entity_to_card
        from app.concierge.frame_extractor import extract_frame

        entity = _make_entity(rating=4.7, review_count=1344)
        frame = extract_frame("breweries near the river", "Chicago")
        note = "Celebrated Avondale taproom known for its extensive cider and craft beer program."

        card = _entity_to_card(entity, note, frame,
                               reason_source="llm_evidence_pack_v2_primary",
                               reason_validated=True)

        assert card is not None
        assert card.rating == 4.7
        assert card.review_count == 1344
        assert card.google_verification is not None
        assert card.google_verification.provider_place_id == "pid_test"
        assert card.maps_link is not None
        assert card.display.addability == "addable"


# ══════════════════════════════════════════════════════════════════════════════
# 9. REASONING ORCHESTRATOR — ReasoningResultV2 contract
# ══════════════════════════════════════════════════════════════════════════════

class TestReasoningResultV2Contract:
    """ReasoningResultV2 telemetry must accurately reflect orchestrator behavior."""

    def test_result_v2_attributes(self):
        from app.concierge.batched_reason_builder import ReasoningResultV2
        r = ReasoningResultV2(final_card_count=6)
        assert r.deterministic_visible_count == 0
        assert r.accepted_count == 0
        assert r.success is False

    def test_flag_disabled_returns_all_omitted(self):
        from app.concierge.batched_reason_builder import build_reasons_with_retry

        cards_data, frame = _make_brewery_cards(3)
        with patch("app.concierge.batched_reason_builder._flag_enabled", return_value=False):
            reasons, result = build_reasons_with_retry(cards_data, frame)

        assert result.success is False
        assert result.final_note_omitted_count == 3
        assert result.deterministic_visible_count == 0
        for cr in reasons.values():
            assert cr.validated is False

    def test_card_reason_attributes(self):
        from app.concierge.batched_reason_builder import CardReason, SOURCE_PRIMARY
        cr = CardReason(note="Test note", source=SOURCE_PRIMARY, validated=True,
                        attempt_count=1, model_used="claude-haiku-4-5-20251001")
        assert cr.validated is True
        assert cr.retry_used is False
        assert cr.fallback_model_used is False
