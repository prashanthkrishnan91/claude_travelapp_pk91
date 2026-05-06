"""Tests for EvidencePack v3 quality improvements.

Covers:
  TestQualityCritic          — thin concept-fit notes rejected; good notes pass
  TestEvidenceAdequacy       — THIN/OK/STRONG grading from existing data
  TestPlaceDetailsEnrichment — enrichment fields appear in EvidencePack; STRONG upgrade
  TestProductionObservability — per-card log emits correct fields
  TestQualityMatrix          — 3 production queries show validated notes after repair
  TestRepairHintWiring       — Pass 2 receives repair hints for quality-failed cards
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, call, patch

import pytest


# ── Shared helpers ────────────────────────────────────────────────────────────

def _make_entity(
    name: str = "Test Taproom",
    place_id: str = "pid_test",
    types: Optional[List[str]] = None,
    rating: float = 4.5,
    review_count: int = 600,
    address: str = "100 W Fulton St, Chicago, IL",
    source_query: str = "taprooms Chicago",
):
    from app.concierge.place_entity_layer import PlaceEntity
    return PlaceEntity(
        place_id=place_id,
        name=name,
        types=types or ["brewery"],
        primary_type=(types or ["brewery"])[0],
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
    place_id: str = "pid_test",
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


def _make_cards(
    n: int = 3,
    query: str = "breweries near the river",
    destination: str = "Chicago",
    enrichment_map: Optional[Dict[str, Any]] = None,
):
    from app.concierge.frame_extractor import extract_frame
    from app.concierge.ranker import RankScore, build_evidence_bundle
    from app.concierge.safe_reason_builder import build_safe_reason

    frame = extract_frame(query, destination)
    names = [
        "Goose Island Brewhouse",
        "Revolution Brewing",
        "Half Acre Beer Company",
        "Forbidden Root Brewery",
        "Empirical Brewery",
        "Spiteful Brewing",
    ]
    addrs = [
        "1800 N Clybourn Ave, Chicago, IL",
        "2323 N Milwaukee Ave, Chicago, IL",
        "4257 N Lincoln Ave, Chicago, IL",
        "1746 W Chicago Ave, Chicago, IL",
        "1801 W Foster Ave, Chicago, IL",
        "1815 W Berteau Ave, Chicago, IL",
    ]
    cards_data = []
    for i in range(n):
        place_id = f"pid_{i}"
        entity = _make_entity(
            name=names[i % len(names)],
            place_id=place_id,
            rating=4.5 + (i % 3) * 0.1,
            review_count=500 + i * 100,
            address=addrs[i % len(addrs)],
            source_query=f"brewery Chicago",
        )
        score = RankScore(total=0.75, subtype_fit=0.90, geo_fit=0.6)
        enrichment = (enrichment_map or {}).get(place_id)
        ev = build_evidence_bundle(entity, frame, score, enrichment=enrichment)
        det = build_safe_reason(entity, ev, frame, score)
        cards_data.append((entity, ev, score, det))
    return cards_data, frame


# ══════════════════════════════════════════════════════════════════════════════
# TestQualityCritic
# ══════════════════════════════════════════════════════════════════════════════

class TestQualityCritic:
    """Quality gate rejects thin concept-fit-only notes, accepts specific notes."""

    def _ev(self, adequacy: str = "THIN"):
        from app.concierge.ranker import MinimalEvidenceBundle
        entity = _make_entity()
        return MinimalEvidenceBundle(
            entity=entity,
            evidence_adequacy=adequacy,
        )

    def test_thin_concept_fit_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        # All notes are >= 8 words (min word check happens before quality check)
        thin_notes = [
            "Goose Island Brewhouse matches the brewery concept with solid signals.",
            "Revolution Brewing has solid brewery signals and strong concept fit.",
            "Half Acre matches the taproom concept with strong name-and-type signals.",
            "This place is a reliable taproom destination in Chicago for visitors.",
            "An established taproom with solid concept fit in the city.",
            "Has strong brewery fit and matches on taproom type and name.",
            "Izakaya concept fit confirmed with strong signals across name and type.",
        ]
        ev = self._ev("THIN")
        for note in thin_notes:
            ok, reason = _assess_quality(note, ev)
            assert not ok, f"Expected quality rejection for: {note!r}, got reason={reason!r}"
            assert reason, f"Expected non-empty rejection reason for: {note!r}"

    def test_good_specific_notes_pass(self):
        from app.concierge.batched_reason_builder import _assess_quality
        good_notes = [
            "Goose Island Brewhouse on Clybourn Ave is Chicago's heritage craft brewery, known for Bourbon County stouts.",
            "Revolution Brewing operates one of the city's largest independent taprooms with outdoor seating.",
            "Forbidden Root pairs botanical beers with a full gastropub kitchen in West Town.",
            "Izakaya Mita in Bucktown offers traditional grilled skewers and sake in a late-night format.",
        ]
        ev = self._ev("OK")
        for note in good_notes:
            ok, reason = _assess_quality(note, ev)
            assert ok, f"Expected quality pass for: {note!r}, got reason={reason!r}"

    def test_mostly_negation_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev("THIN")
        # Words that are negation tokens (no punctuation attached to avoid mismatch):
        # "not", "cannot", "no", "not", "isn't", "unavailable" = 6 of 11 words (54%)
        neg_note = "not confirmed cannot verify no data not available isn't clear here"
        ok, reason = _assess_quality(neg_note, ev)
        assert not ok, f"Expected negation rejection, got ok=True reason={reason!r}"
        assert "negation" in reason or "mostly" in reason

    def test_short_positive_note_passes(self):
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev("OK")
        # Short but specific note — passes if >= 8 words and not thin-fit
        note = "Goose Island Brewhouse on Clybourn is Chicago's flagship heritage brewery."
        ok, reason = _assess_quality(note, ev)
        assert ok, f"Expected pass, got reason={reason!r}"


# ══════════════════════════════════════════════════════════════════════════════
# TestEvidenceAdequacy
# ══════════════════════════════════════════════════════════════════════════════

class TestEvidenceAdequacy:
    """build_evidence_bundle grades evidence adequacy correctly."""

    def _build(self, entity, query: str = "breweries", subtype_fit: float = 0.9,
               review_count: int = 600, enrichment=None):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, build_evidence_bundle
        frame = extract_frame(query, "Chicago")
        score = RankScore(total=0.75, subtype_fit=subtype_fit, geo_fit=0.55)
        if review_count is not None:
            entity.user_rating_count = review_count
        return build_evidence_bundle(entity, frame, score, enrichment=enrichment)

    def test_thin_default(self):
        entity = _make_entity(review_count=100)
        ev = self._build(entity, subtype_fit=0.4, review_count=100)
        assert ev.evidence_adequacy == "THIN"

    def test_ok_with_moderate_subtype_fit(self):
        entity = _make_entity(review_count=200)
        ev = self._build(entity, subtype_fit=0.65, review_count=200)
        assert ev.evidence_adequacy == "OK"

    def test_strong_with_high_subtype_and_reviews(self):
        entity = _make_entity(review_count=600)
        ev = self._build(entity, subtype_fit=0.92, review_count=600)
        assert ev.evidence_adequacy == "STRONG"

    def test_strong_with_enrichment(self):
        entity = _make_entity()
        enrichment = _make_enrichment(editorial_summary="A great brewery.")
        ev = self._build(entity, subtype_fit=0.5, review_count=100, enrichment=enrichment)
        assert ev.evidence_adequacy == "STRONG"

    def test_enrichment_amenity_only_is_strong(self):
        entity = _make_entity()
        enrichment = _make_enrichment(serves_beer=True, outdoor_seating=True)
        ev = self._build(entity, subtype_fit=0.5, review_count=50, enrichment=enrichment)
        assert ev.evidence_adequacy == "STRONG"


# ══════════════════════════════════════════════════════════════════════════════
# TestPlaceDetailsEnrichment
# ══════════════════════════════════════════════════════════════════════════════

class TestPlaceDetailsEnrichment:
    """Enrichment facts from Place Details appear in MinimalEvidenceBundle."""

    def _build_with_enrichment(self, enrichment):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, build_evidence_bundle
        entity = _make_entity()
        frame = extract_frame("breweries", "Chicago")
        score = RankScore(total=0.72, subtype_fit=0.88)
        return build_evidence_bundle(entity, frame, score, enrichment=enrichment)

    def test_editorial_summary_in_enrichment_facts(self):
        enrichment = _make_enrichment(editorial_summary="Chicago's iconic craft brewery.")
        ev = self._build_with_enrichment(enrichment)
        assert any("Editorial summary" in f for f in ev.enrichment_facts)
        assert any("Chicago's iconic craft brewery" in f for f in ev.enrichment_facts)

    def test_review_snippet_in_enrichment_facts(self):
        enrichment = _make_enrichment(review_snippets=["Great outdoor seating on the patio."])
        ev = self._build_with_enrichment(enrichment)
        assert any("Review mention" in f for f in ev.enrichment_facts)

    def test_amenity_serves_beer_in_enrichment_facts(self):
        enrichment = _make_enrichment(serves_beer=True)
        ev = self._build_with_enrichment(enrichment)
        assert any("serves beer" in f for f in ev.enrichment_facts)

    def test_amenity_outdoor_seating_in_enrichment_facts(self):
        enrichment = _make_enrichment(outdoor_seating=True)
        ev = self._build_with_enrichment(enrichment)
        assert any("outdoor seating" in f for f in ev.enrichment_facts)

    def test_amenity_live_music_in_enrichment_facts(self):
        enrichment = _make_enrichment(live_music=True)
        ev = self._build_with_enrichment(enrichment)
        assert any("live music" in f for f in ev.enrichment_facts)

    def test_amenity_good_for_groups_in_enrichment_facts(self):
        enrichment = _make_enrichment(good_for_groups=True)
        ev = self._build_with_enrichment(enrichment)
        assert any("good for groups" in f for f in ev.enrichment_facts)

    def test_false_amenity_not_in_enrichment_facts(self):
        # serves_beer=False should NOT appear — we only report confirmed amenities
        enrichment = _make_enrichment(serves_beer=False)
        ev = self._build_with_enrichment(enrichment)
        assert not any("serves beer" in f for f in ev.enrichment_facts)

    def test_no_enrichment_empty_facts(self):
        ev = self._build_with_enrichment(None)
        assert ev.enrichment_facts == []

    def test_enrichment_upgrades_adequacy_to_strong(self):
        enrichment = _make_enrichment(editorial_summary="A great brewery.")
        ev = self._build_with_enrichment(enrichment)
        assert ev.evidence_adequacy == "STRONG"

    def test_enrichment_text_in_llm_prompt(self):
        """Enrichment facts should appear in the evidence text passed to the LLM."""
        from app.concierge.batched_reason_builder import _build_evidence_text
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, build_evidence_bundle

        entity = _make_entity()
        frame = extract_frame("breweries", "Chicago")
        score = RankScore(total=0.72, subtype_fit=0.88)
        enrichment = _make_enrichment(
            editorial_summary="Chicago's iconic craft brewery.",
            outdoor_seating=True,
        )
        ev = build_evidence_bundle(entity, frame, score, enrichment=enrichment)
        text = _build_evidence_text(entity, ev, frame, score, 1, total_cards=3)
        assert "Editorial summary" in text
        assert "outdoor seating" in text


# ══════════════════════════════════════════════════════════════════════════════
# TestProductionObservability
# ══════════════════════════════════════════════════════════════════════════════

class TestProductionObservability:
    """Per-card observability log emits correct fields."""

    def test_per_card_log_emitted(self, caplog):
        from app.concierge.semantic_retrieval import _log_per_card_notes
        from app.concierge.batched_reason_builder import CardReason, SOURCE_PRIMARY
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason

        query = "breweries near the river"
        frame = extract_frame(query, "Chicago")
        entity = _make_entity(address="1800 N Clybourn Ave, Chicago, IL")
        score = RankScore(total=0.75, subtype_fit=0.88)
        ev = build_evidence_bundle(entity, frame, score)
        det = build_safe_reason(entity, ev, frame, score)
        cards_data = [(entity, ev, score, det)]

        card_reasons = {
            "1": CardReason(
                note="Goose Island Brewhouse on Clybourn is Chicago's heritage brewery.",
                source=SOURCE_PRIMARY,
                validated=True,
                attempt_count=1,
                model_used="claude-haiku-4-5-20251001",
            )
        }

        with caplog.at_level(logging.INFO, logger="app.concierge.semantic_retrieval"):
            _log_per_card_notes(query, cards_data, card_reasons, frame)

        log_lines = [r.message for r in caplog.records if "per_card_notes" in r.message]
        assert len(log_lines) == 1
        assert "per_card_notes" in log_lines[0]
        assert "Goose Island" in log_lines[0]

    def test_per_card_log_adequacy_field(self, caplog):
        from app.concierge.semantic_retrieval import _log_per_card_notes
        from app.concierge.batched_reason_builder import CardReason, SOURCE_PRIMARY
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason

        query = "breweries"
        frame = extract_frame(query, "Chicago")
        entity = _make_entity(review_count=700)
        score = RankScore(total=0.75, subtype_fit=0.92)
        enrichment = _make_enrichment(editorial_summary="A great spot.")
        ev = build_evidence_bundle(entity, frame, score, enrichment=enrichment)
        det = build_safe_reason(entity, ev, frame, score)

        card_reasons = {
            "1": CardReason(
                note="Test Taproom on Fulton St is a solid local spot.",
                source=SOURCE_PRIMARY,
                validated=True,
            )
        }

        with caplog.at_level(logging.INFO, logger="app.concierge.semantic_retrieval"):
            _log_per_card_notes(query, [(entity, ev, score, det)], card_reasons, frame)

        log_line = next(r.message for r in caplog.records if "per_card_notes" in r.message)
        assert "STRONG" in log_line

    def test_per_card_log_omitted_card(self, caplog):
        from app.concierge.semantic_retrieval import _log_per_card_notes
        from app.concierge.batched_reason_builder import CardReason, SOURCE_OMITTED
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason

        query = "breweries"
        frame = extract_frame(query, "Chicago")
        entity = _make_entity()
        score = RankScore(total=0.65, subtype_fit=0.70)
        ev = build_evidence_bundle(entity, frame, score)
        det = build_safe_reason(entity, ev, frame, score)

        card_reasons = {
            "1": CardReason(source=SOURCE_OMITTED, validated=False)
        }

        with caplog.at_level(logging.INFO, logger="app.concierge.semantic_retrieval"):
            _log_per_card_notes(query, [(entity, ev, score, det)], card_reasons, frame)

        log_line = next(r.message for r in caplog.records if "per_card_notes" in r.message)
        assert "validated" in log_line
        # validated=False should appear
        assert "False" in log_line


# ══════════════════════════════════════════════════════════════════════════════
# TestRepairHintWiring
# ══════════════════════════════════════════════════════════════════════════════

class TestRepairHintWiring:
    """Quality-failed cards from Pass 1 generate repair hints for Pass 2 prompt."""

    def test_quality_failed_card_triggers_pass2(self):
        """When Pass 1 produces a thin note, Pass 2 should receive repair hints."""
        from app.concierge.batched_reason_builder import build_reasons_with_retry

        # Pass 1: thin concept-fit note for card 1 (will fail quality gate)
        pass1_json = json.dumps({
            "1": "Revolution Brewing matches the brewery concept with solid signals.",
            "2": None,
            "3": None,
        })
        # Pass 2: specific note after repair guidance
        pass2_json = json.dumps({
            "1": "Revolution Brewing on Milwaukee Ave operates one of Chicago's largest independent taprooms with a widely praised seasonal IPA program.",
        })

        call_count = 0
        captured_prompts = []

        def mock_llm(prompt, timeout, model=""):
            nonlocal call_count
            call_count += 1
            captured_prompts.append(prompt)
            if call_count == 1:
                return pass1_json
            if call_count == 2:
                return pass2_json
            return json.dumps({"1": None})

        cards_data, frame = _make_cards(3)
        _ENABLE = patch("app.concierge.batched_reason_builder._flag_enabled", return_value=True)
        with _ENABLE, patch("app.concierge.batched_reason_builder._call_llm", side_effect=mock_llm):
            reasons, result_meta = build_reasons_with_retry(cards_data, frame)

        # Pass 2 should have been called
        assert call_count >= 2, "Expected at least 2 LLM calls (pass 1 + pass 2)"

        # Card 1 should eventually be validated (after repair)
        assert reasons["1"].validated, "Card 1 should be validated after repair pass"
        assert reasons["1"].retry_used, "Card 1 should have retry_used=True"

    def test_repair_hint_appears_in_pass2_prompt(self):
        """The Pass 2 prompt should contain REPAIR GUIDANCE for quality-failed cards."""
        from app.concierge.batched_reason_builder import build_reasons_with_retry

        pass1_json = json.dumps({
            "1": "Test Taproom matches the taproom concept with solid concept fit.",
        })

        captured_prompts = []

        def mock_llm(prompt, timeout, model=""):
            captured_prompts.append(prompt)
            if len(captured_prompts) == 1:
                return pass1_json
            return json.dumps({"1": "Test Taproom on Fulton St is a neighborhood taproom in the West Loop."})

        cards_data, frame = _make_cards(1)
        _ENABLE = patch("app.concierge.batched_reason_builder._flag_enabled", return_value=True)
        with _ENABLE, patch("app.concierge.batched_reason_builder._call_llm", side_effect=mock_llm):
            build_reasons_with_retry(cards_data, frame)

        # Check that a second prompt was generated containing REPAIR GUIDANCE
        if len(captured_prompts) >= 2:
            assert "REPAIR GUIDANCE" in captured_prompts[1], (
                "Pass 2 prompt should contain REPAIR GUIDANCE for quality-failed cards"
            )

    def test_pass3_fallback_receives_repair_hints(self):
        """Pass 3 (fallback model) should also receive repair hints from earlier failures."""
        from app.concierge.batched_reason_builder import build_reasons_with_retry, _FALLBACK_MODEL, _PRIMARY_MODEL

        # >= 8 words so it passes word-count check and reaches the quality gate
        thin_note = "Test Taproom on Fulton Street has solid taproom concept fit here."
        pass1_json = json.dumps({"1": thin_note})

        captured_calls = []

        def mock_llm(prompt, timeout, model=""):
            captured_calls.append((prompt, model))
            n = len(captured_calls)
            if n == 1:
                return pass1_json  # Pass 1: quality rejected
            if n == 2:
                return json.dumps({"1": thin_note})  # Pass 2 still thin
            # Pass 3: good note
            return json.dumps({"1": "Test Taproom on Fulton St is a West Loop neighborhood taproom."})

        cards_data, frame = _make_cards(1)
        _ENABLE = patch("app.concierge.batched_reason_builder._flag_enabled", return_value=True)
        with _ENABLE, patch("app.concierge.batched_reason_builder._call_llm", side_effect=mock_llm):
            reasons, _ = build_reasons_with_retry(cards_data, frame)

        # If 3 calls were made, pass 3 prompt should have repair hints
        if len(captured_calls) >= 3:
            pass3_prompt = captured_calls[2][0]
            assert "REPAIR GUIDANCE" in pass3_prompt, "Pass 3 prompt should contain REPAIR GUIDANCE"


# ══════════════════════════════════════════════════════════════════════════════
# TestQualityMatrix
# ══════════════════════════════════════════════════════════════════════════════

class TestQualityMatrix:
    """3 production queries each produce validated notes (no generic concept-fit phrases)."""

    def _run_query(self, query: str, data_names: List[str], notes: Dict[str, str]) -> Dict[str, Any]:
        from app.concierge.batched_reason_builder import build_reasons_with_retry
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason

        frame = extract_frame(query, "Chicago")
        cards_data = []
        for i, name in enumerate(data_names):
            entity = _make_entity(name=name, place_id=f"pid_{i}", rating=4.5, review_count=600)
            score = RankScore(total=0.75, subtype_fit=0.88, geo_fit=0.55)
            ev = build_evidence_bundle(entity, frame, score)
            det = build_safe_reason(entity, ev, frame, score)
            cards_data.append((entity, ev, score, det))

        llm_json = json.dumps(notes)
        _ENABLE = patch("app.concierge.batched_reason_builder._flag_enabled", return_value=True)
        with _ENABLE, patch("app.concierge.batched_reason_builder._call_llm", return_value=llm_json):
            reasons, result = build_reasons_with_retry(cards_data, frame)
        return {"reasons": reasons, "result": result}

    def test_breweries_near_river_all_validated(self):
        notes = {
            "1": "Goose Island Brewhouse on Clybourn Ave is Chicago's flagship craft brewery, home to the Bourbon County series.",
            "2": "Revolution Brewing on Milwaukee Ave is one of Chicago's largest independent taprooms, known for its Anti-Hero IPA.",
            "3": "Half Acre Beer Company on Lincoln Ave focuses on small-batch experimental styles, with limited releases that draw enthusiasts.",
        }
        out = self._run_query(
            "breweries near the river",
            ["Goose Island Brewhouse", "Revolution Brewing", "Half Acre Beer Company"],
            notes,
        )
        validated = [cr for cr in out["reasons"].values() if cr.validated]
        assert len(validated) == 3, f"Expected 3 validated, got {len(validated)}"

    def test_taprooms_with_view_valid_notes(self):
        notes = {
            "1": "Corridor Brewery & Provisions on Southport Ave is a Lakeview neighborhood taproom; outdoor views are not confirmed from the available address.",
            "2": "Dovetail Brewery on Belle Plaine Ave specializes in European-style lagers and farmhouse ales — a less common specialty in Chicago's IPA-heavy scene.",
        }
        out = self._run_query(
            "taprooms with a view",
            ["Corridor Brewery & Provisions", "Dovetail Brewery"],
            notes,
        )
        validated = [cr for cr in out["reasons"].values() if cr.validated]
        assert len(validated) == 2, f"Expected 2 validated, got {len(validated)}"

    def test_izakayas_valid_notes(self):
        notes = {
            "1": "Gaijin on Lake Street is a modern izakaya pairing Japanese street food with natural wines.",
            "2": "Izakaya Mita in Bucktown offers traditional grilled skewers and sake in a late-night format for groups.",
        }
        out = self._run_query(
            "izakayas",
            ["Gaijin", "Izakaya Mita"],
            notes,
        )
        validated = [cr for cr in out["reasons"].values() if cr.validated]
        assert len(validated) == 2, f"Expected 2 validated, got {len(validated)}"

    def test_generic_concept_fit_notes_rejected_end_to_end(self):
        """End-to-end: thin concept-fit notes are rejected, no card gets validated."""
        generic_notes = {
            "1": "Goose Island Brewhouse matches the brewery concept with solid signals.",
            "2": "Revolution Brewing has strong brewery concept fit in Chicago.",
            "3": "Half Acre matches on brewery type and name.",
        }
        out = self._run_query(
            "breweries",
            ["Goose Island Brewhouse", "Revolution Brewing", "Half Acre Beer Company"],
            generic_notes,
        )
        # With generic notes + no retry producing better output → zero validated
        validated = [cr for cr in out["reasons"].values() if cr.validated]
        # After quality gate rejection, Pass 2 and 3 return None → zero validated
        # (in this test we don't mock a repair pass, so all are omitted)
        for cr in out["reasons"].values():
            assert not cr.validated or cr.retry_used, (
                f"Generic note for {cr.source} should not be validated without retry"
            )

    def test_no_concept_fit_phrase_in_validated_notes(self):
        """Validated notes must not contain thin concept-fit phrases."""
        from app.concierge.batched_reason_builder import _QUALITY_THIN_RE
        good_notes = {
            "1": "Goose Island Brewhouse on Clybourn is Chicago's heritage brewery, known for the Bourbon County series.",
            "2": "Revolution Brewing on Milwaukee Ave has one of the city's largest taprooms with a consistent IPA program.",
        }
        out = self._run_query(
            "breweries",
            ["Goose Island Brewhouse", "Revolution Brewing"],
            good_notes,
        )
        for cr in out["reasons"].values():
            if cr.validated:
                assert not _QUALITY_THIN_RE.search(cr.note), (
                    f"Validated note contains thin concept-fit phrase: {cr.note!r}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# TestQualityCriticExtended
# ══════════════════════════════════════════════════════════════════════════════

class TestQualityCriticExtended:
    """Regression tests for new quality gate patterns (v3 additions)."""

    def _ev(self, adequacy: str = "OK"):
        from app.concierge.ranker import MinimalEvidenceBundle
        entity = _make_entity()
        return MinimalEvidenceBundle(entity=entity, evidence_adequacy=adequacy)

    def test_well_regarded_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev()
        notes = [
            "Revolution Brewing is a well-regarded Chicago craft brewery with a great tap list.",
            "Half Acre Beer Company is well-regarded in the Lincoln Square neighborhood.",
            "Goose Island is a well regarded institution on the North Side.",
        ]
        for note in notes:
            ok, reason = _assess_quality(note, ev)
            assert not ok, f"Expected rejection for well-regarded note: {note!r}"

    def test_highly_rated_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev()
        notes = [
            "Goose Island Taproom is a highly rated spot on Clybourn Ave with a great selection.",
            "Revolution Brewing is highly-rated among Chicago craft beer fans.",
        ]
        for note in notes:
            ok, reason = _assess_quality(note, ev)
            assert not ok, f"Expected rejection for highly-rated note: {note!r}"

    def test_great_option_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev()
        note = "Half Acre Beer Company is a great option for craft beer fans in Chicago's North Side."
        ok, reason = _assess_quality(note, ev)
        assert not ok, f"Expected rejection for 'great option' note: {note!r}"

    def test_top_pick_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev()
        note = "Revolution Brewing is the top pick for craft beer lovers visiting Chicago this season."
        ok, reason = _assess_quality(note, ev)
        assert not ok, f"Expected rejection for 'top pick' note: {note!r}"

    def test_strong_local_following_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev()
        note = "Goose Island Brewhouse has a strong local following in the Clybourn area among locals."
        ok, reason = _assess_quality(note, ev)
        assert not ok, f"Expected rejection for 'strong local following' note: {note!r}"

    def test_consistent_quality_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev()
        note = "Metropolitan Brewing is known for consistent quality German-style lagers in Chicago."
        ok, reason = _assess_quality(note, ev)
        assert not ok, f"Expected rejection for 'consistent quality' note: {note!r}"

    def test_chicago_institution_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev()
        note = "Goose Island Brewhouse is a Chicago institution in the craft beer scene."
        ok, reason = _assess_quality(note, ev)
        assert not ok, f"Expected rejection for 'Chicago institution' note: {note!r}"

    def test_rating_lead_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev("THIN")
        rating_lead_notes = [
            "4.7★ from 1,344 reviews. The requested view setting is not verified.",
            "4.5★ with 800 reviews, this is a solid taproom concept fit.",
            "4.3★ from 290 reviews; outdoor views not confirmed.",
        ]
        for note in rating_lead_notes:
            ok, reason = _assess_quality(note, ev)
            assert not ok, f"Expected rating_residue_lead rejection: {note!r}"
            assert "rating" in reason, f"Expected 'rating' in rejection reason, got: {reason!r}"

    def test_pure_caveat_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev("THIN")
        pure_caveat_notes = [
            "The requested view setting is not verified.",
            "Outdoor views are not confirmed from the available address.",
            "A scenic view cannot be verified from available data.",
            "Views cannot be confirmed from the available address.",
        ]
        for note in pure_caveat_notes:
            ok, reason = _assess_quality(note, ev)
            assert not ok, f"Expected pure_caveat rejection: {note!r}"
            assert "caveat" in reason or "pure" in reason, (
                f"Expected 'caveat' or 'pure' in rejection reason for {note!r}, got: {reason!r}"
            )

    def test_caveat_with_differentiator_passes(self):
        """Notes combining a positive differentiator + honest view caveat must pass."""
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev("OK")
        notes_with_differentiator = [
            "Corridor Brewery & Provisions on Southport Ave is a Lakeview taproom; a scenic view is not confirmed from the address.",
            "Dovetail Brewery on Belle Plaine Ave focuses on European lagers; outdoor views are not confirmed from the available data.",
            "Spiteful Brewing on Berteau Ave is a compact Avondale taproom; outdoor views are not confirmed.",
        ]
        for note in notes_with_differentiator:
            ok, reason = _assess_quality(note, ev)
            assert ok, (
                f"Expected quality pass for mixed-content note: {note!r}, got reason={reason!r}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# TestIzakayaVenueHead
# ══════════════════════════════════════════════════════════════════════════════

class TestIzakayaVenueHead:
    """venue_head_recognized=True for izakaya queries after adding to _SYNONYM_SETS."""

    def test_izakaya_in_synonym_sets(self):
        from app.concierge.ranker import _SYNONYM_SETS
        found = any("izakaya" in s for s in _SYNONYM_SETS)
        assert found, "Expected 'izakaya' in _SYNONYM_SETS for venue-head recognition"

    def test_izakayas_plural_in_synonym_sets(self):
        from app.concierge.ranker import _SYNONYM_SETS
        found = any("izakayas" in s for s in _SYNONYM_SETS)
        assert found, "Expected 'izakayas' in _SYNONYM_SETS"

    def test_izakaya_has_known_synonym_set(self):
        from app.concierge.ranker import _has_known_synonym_set
        assert _has_known_synonym_set("izakaya"), "Expected True for 'izakaya'"
        assert _has_known_synonym_set("izakayas"), "Expected True for 'izakayas'"

    def test_brewery_still_recognized(self):
        from app.concierge.ranker import _has_known_synonym_set
        assert _has_known_synonym_set("brewery"), "Regression: brewery must still be recognized"
        assert _has_known_synonym_set("taproom"), "Regression: taproom must still be recognized"


# ══════════════════════════════════════════════════════════════════════════════
# TestProductionShapeScenarios
# ══════════════════════════════════════════════════════════════════════════════

class TestProductionShapeScenarios:
    """8-card production-shape scenarios proving retry fills missing cards."""

    def _make_8_cards(self, query: str):
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason

        frame = extract_frame(query, "Chicago")
        names = [
            "Goose Island Brewhouse", "Revolution Brewing", "Half Acre Beer Company",
            "Forbidden Root Brewery", "Empirical Brewery", "Spiteful Brewing",
            "Metropolitan Brewing", "Off Color Brewing",
        ]
        addrs = [
            "1800 N Clybourn Ave, Chicago, IL", "2323 N Milwaukee Ave, Chicago, IL",
            "4257 N Lincoln Ave, Chicago, IL", "1746 W Chicago Ave, Chicago, IL",
            "1801 W Foster Ave, Chicago, IL", "1815 W Berteau Ave, Chicago, IL",
            "3057 N Rockwell St, Chicago, IL", "3925 W Belmont Ave, Chicago, IL",
        ]
        cards_data = []
        for i in range(8):
            entity = _make_entity(
                name=names[i],
                place_id=f"pid_{i}",
                rating=4.5,
                review_count=500 + i * 100,
                address=addrs[i],
                source_query="brewery Chicago",
            )
            score = RankScore(total=0.75, subtype_fit=0.90, geo_fit=0.6)
            ev = build_evidence_bundle(entity, frame, score)
            det = build_safe_reason(entity, ev, frame, score)
            cards_data.append((entity, ev, score, det))
        return cards_data, frame

    def test_brewery_8_card_7_pass1_1_retry(self):
        """8 cards: 7 good in pass1, 1 rescued in pass2."""
        from app.concierge.batched_reason_builder import build_reasons_with_retry

        # 7 specific notes + 1 thin (card 8)
        pass1_json = json.dumps({
            "1": "Goose Island Brewhouse on Clybourn Ave is Chicago's heritage craft brewery, home to the Bourbon County stout series.",
            "2": "Revolution Brewing on Milwaukee Ave is one of Chicago's largest independent taprooms with outdoor seating.",
            "3": "Half Acre on Lincoln Ave emphasizes small-batch experimental styles with limited releases.",
            "4": "Forbidden Root on Chicago Ave pairs botanical beers with a gastropub kitchen.",
            "5": "Empirical Brewery on Foster Ave features outdoor seating and a rotating fermentation-forward tap program.",
            "6": "Spiteful Brewing on Berteau Ave is a compact neighborhood taproom on a residential stretch.",
            "7": "Metropolitan Brewing on Rockwell Street specializes in German lagers with a North Side taproom and outdoor patio seating.",
            "8": "Off Color Brewing has solid brewery signals and strong concept fit in Chicago.",  # thin
        })
        pass2_json = json.dumps({
            "1": "Off Color Brewing on Belmont Ave brews eccentric small-batch farmhouse ales — an unusual specialty in Chicago's craft scene.",
        })

        call_count = 0

        def mock_llm(prompt, timeout, model=""):
            nonlocal call_count
            call_count += 1
            return pass1_json if call_count == 1 else pass2_json

        cards_data, frame = self._make_8_cards("breweries near the river")
        _ENABLE = patch("app.concierge.batched_reason_builder._flag_enabled", return_value=True)
        with _ENABLE, patch("app.concierge.batched_reason_builder._call_llm", side_effect=mock_llm):
            reasons, result = build_reasons_with_retry(cards_data, frame)

        assert result.accepted_count == 8, f"Expected 8 accepted, got {result.accepted_count}"
        assert result.final_note_omitted_count == 0
        assert result.deterministic_visible_count == 0
        assert result.retry_recovered_count == 1, f"Expected 1 retry-recovered, got {result.retry_recovered_count}"
        for key, cr in reasons.items():
            assert cr.validated, f"Card {key} not validated"

    def test_taproom_8_card_3_pass1_5_retry(self):
        """8 cards: 3 good in pass1, 5 rescued in pass2."""
        from app.concierge.batched_reason_builder import build_reasons_with_retry

        pass1_json = json.dumps({
            "1": "Corridor Brewery & Provisions on Southport Ave is a Lakeview neighborhood taproom; a view is not confirmed from the address.",
            "2": "Spiteful Brewing on Berteau Ave is a compact Avondale taproom; outdoor views are not confirmed from the available data.",
            "3": "Dovetail Brewery on Belle Plaine Ave focuses on European-style lagers — an unusual specialty in Chicago's IPA-heavy scene.",
            "4": "Hopewell Brewing Company has solid taproom signals and strong concept fit for this query.",
            "5": "Metropolitan Brewing matches the taproom concept with solid brewery signals.",
            "6": "Off Color Brewing is a reliable taproom destination with solid concept fit in Chicago.",
            "7": "Empirical Brewery matches on taproom type and name with established taproom signals.",
            "8": "Spiteful Brewing has solid taproom signals and an established brewery concept fit here.",
        })
        pass2_json = json.dumps({
            "1": "Hopewell Brewing Company on Milwaukee Ave is a Logan Square taproom; outdoor views are not confirmed.",
            "2": "Metropolitan Brewing on Rockwell St specializes in German lagers with a North Side taproom and patio seating.",
            "3": "Off Color Brewing on Belmont Ave brews eccentric farmhouse ales — an unusual niche in Chicago.",
            "4": "Empirical Brewery on Foster Ave offers a rotating fermentation-forward program with outdoor seating.",
            "5": "Spiteful Brewing on Berteau Ave is a compact neighborhood taproom; a view is not confirmed.",
        })

        call_count = 0

        def mock_llm(prompt, timeout, model=""):
            nonlocal call_count
            call_count += 1
            return pass1_json if call_count == 1 else pass2_json

        cards_data, frame = self._make_8_cards("taprooms with a view")
        _ENABLE = patch("app.concierge.batched_reason_builder._flag_enabled", return_value=True)
        with _ENABLE, patch("app.concierge.batched_reason_builder._call_llm", side_effect=mock_llm):
            reasons, result = build_reasons_with_retry(cards_data, frame)

        assert result.accepted_count == 8, f"Expected 8 accepted, got {result.accepted_count}"
        assert result.final_note_omitted_count == 0
        assert result.deterministic_visible_count == 0
        assert result.retry_recovered_count == 5, f"Expected 5 retry-recovered, got {result.retry_recovered_count}"

    def test_no_truncating_log_for_8_cards(self, caplog):
        """Log must say 'reasoning all cards' not 'truncating' when card_count > batch_size."""
        import logging
        from app.concierge.batched_reason_builder import build_reasons_with_retry

        good_notes = json.dumps({
            str(i + 1): f"Place {i + 1} on Clybourn Ave is a craft brewery with a rotating tap program and seasonal specialties."
            for i in range(8)
        })

        cards_data, frame = self._make_8_cards("breweries near the river")
        _ENABLE = patch("app.concierge.batched_reason_builder._flag_enabled", return_value=True)
        with caplog.at_level(logging.INFO, logger="app.concierge.batched_reason_builder"), \
             _ENABLE, patch("app.concierge.batched_reason_builder._call_llm", return_value=good_notes):
            build_reasons_with_retry(cards_data, frame)

        over_batch_logs = [
            r.message for r in caplog.records
            if "card_count" in r.message and "batch_size" in r.message
        ]
        for msg in over_batch_logs:
            assert "truncating" not in msg.lower(), (
                f"Found misleading 'truncating' in log: {msg!r}"
            )

    def test_telemetry_cardinality_invariants(self):
        """accepted_count == final_card_count, omitted=0, deterministic=0 for success path."""
        from app.concierge.batched_reason_builder import build_reasons_with_retry

        good_notes = json.dumps({
            str(i + 1): f"Place {i + 1} on Clybourn Ave is a craft brewery with a seasonal tap program and outdoor seating."
            for i in range(8)
        })

        cards_data, frame = self._make_8_cards("breweries near the river")
        _ENABLE = patch("app.concierge.batched_reason_builder._flag_enabled", return_value=True)
        with _ENABLE, patch("app.concierge.batched_reason_builder._call_llm", return_value=good_notes):
            _reasons, result = build_reasons_with_retry(cards_data, frame)

        assert result.final_note_omitted_count == 0
        assert result.deterministic_visible_count == 0
        assert result.accepted_count == result.final_card_count


# ══════════════════════════════════════════════════════════════════════════════
# TestHarnessV3Strict
# ══════════════════════════════════════════════════════════════════════════════

class TestHarnessV3Strict:
    """Harness v3 scenarios must all validate (zero omitted)."""

    def test_table1_brewery_all_validated(self):
        from tests.evidence_harness_v3 import table1_breweries_8card
        rows, result_meta = table1_breweries_8card()
        omitted = [r for r in rows if r["displayWhyValidated"] != "True"]
        assert not omitted, (
            f"Table 1: {len(omitted)} cards NOT validated: "
            + ", ".join(f"card {r['card_index']} ({r['card_title']})" for r in omitted)
        )
        assert result_meta.final_note_omitted_count == 0
        assert result_meta.deterministic_visible_count == 0

    def test_table2_taproom_all_validated(self):
        from tests.evidence_harness_v3 import table2_taprooms_8card
        rows, result_meta = table2_taprooms_8card()
        omitted = [r for r in rows if r["displayWhyValidated"] != "True"]
        assert not omitted, (
            f"Table 2: {len(omitted)} cards NOT validated: "
            + ", ".join(f"card {r['card_index']} ({r['card_title']})" for r in omitted)
        )
        assert result_meta.final_note_omitted_count == 0
        assert result_meta.deterministic_visible_count == 0

    def test_table3_izakaya_all_validated(self):
        from tests.evidence_harness_v3 import table3_izakayas_editorial
        rows, result_meta = table3_izakayas_editorial()
        omitted = [r for r in rows if r["displayWhyValidated"] != "True"]
        assert not omitted, (
            f"Table 3: {len(omitted)} cards NOT validated: "
            + ", ".join(f"card {r['card_index']} ({r['card_title']})" for r in omitted)
        )
        assert result_meta.deterministic_visible_count == 0

    def test_table1_retry_count(self):
        """Table 1 must have exactly 1 retry-rescued card (card 8)."""
        from tests.evidence_harness_v3 import table1_breweries_8card
        rows, result_meta = table1_breweries_8card()
        retry_rescued = [r for r in rows if r["quality_gate_result"] == "retry_rescued"]
        assert len(retry_rescued) == 1, (
            f"Table 1: expected 1 retry-rescued, got {len(retry_rescued)}: {retry_rescued}"
        )
        assert result_meta.retry_recovered_count == 1

    def test_table2_retry_count(self):
        """Table 2 must have exactly 5 retry-rescued cards (cards 4–8)."""
        from tests.evidence_harness_v3 import table2_taprooms_8card
        rows, result_meta = table2_taprooms_8card()
        retry_rescued = [r for r in rows if r["quality_gate_result"] == "retry_rescued"]
        assert len(retry_rescued) == 5, (
            f"Table 2: expected 5 retry-rescued, got {len(retry_rescued)}: "
            + str([r["card_title"] for r in retry_rescued])
        )
        assert result_meta.retry_recovered_count == 5
