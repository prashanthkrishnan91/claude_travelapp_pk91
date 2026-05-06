"""Tests for EvidencePack v5: Tighter rating/review-primary rejection + modifier telemetry fix.

Covers:
  TestPR252BadNoteRejection   — exact PR #252 failing notes are rejected by quality gate
  TestRatingPrimaryV5         — new indirect rating/review phrasings all rejected
  TestModifierTelemetryV5     — modifier_status telemetry fix (confirmed_listing_context for Northman)
  TestTaproomViewQualityV5    — taprooms-with-view: 8/8 validated, view addressed honestly
  TestIzakayaQualityV5        — izakayas: 8/8 validated, no review-volume-primary notes
  TestHarnessV5Integration    — end-to-end: all three queries pass v5 harness criteria
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest


# ── Shared helpers ────────────────────────────────────────────────────────────

def _make_entity(
    name: str = "Test Taproom",
    place_id: str = "pid_test",
    types: Optional[List[str]] = None,
    rating: float = 4.5,
    review_count: int = 600,
    address: str = "100 W Fulton St, Chicago, IL",
    source_query: str = "breweries Chicago",
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


def _thin_ev(entity=None):
    from app.concierge.ranker import MinimalEvidenceBundle
    e = entity or _make_entity()
    return MinimalEvidenceBundle(entity=e, evidence_adequacy="THIN")


def _make_frame(query: str, destination: str = "Chicago"):
    from app.concierge.frame_extractor import extract_frame
    return extract_frame(query, destination)


def _make_bundle(entity, frame, subtype_fit: float = 0.88, enrichment=None):
    from app.concierge.ranker import RankScore, build_evidence_bundle
    score = RankScore(total=0.72, subtype_fit=subtype_fit, geo_fit=0.55)
    return build_evidence_bundle(entity, frame, score, enrichment=enrichment)


# ══════════════════════════════════════════════════════════════════════════════
# TestPR252BadNoteRejection
# ══════════════════════════════════════════════════════════════════════════════

class TestPR252BadNoteRejection:
    """Exact PR #252 production-failing notes must be rejected by the quality gate."""

    def _ev(self):
        return _thin_ev()

    def test_notably_high_ratings_rejected(self):
        """'notably high ratings (4.8★)' is a rating-primary note — must be rejected."""
        from app.concierge.batched_reason_builder import _assess_quality
        note = "Goose Island is notable for its notably high ratings (4.8★) in Chicago."
        ok, reason = _assess_quality(note, self._ev())
        assert not ok, f"Expected rejection for 'notably high ratings' note"
        assert reason, "Expected non-empty rejection reason"

    def test_high_engagement_rejected(self):
        """'draws consistently high engagement (4.8★, 1,028 reviews)' — must be rejected."""
        from app.concierge.batched_reason_builder import _assess_quality
        note = "This taproom draws consistently high engagement (4.8★, 1,028 reviews) citywide."
        ok, reason = _assess_quality(note, self._ev())
        assert not ok, f"Expected rejection for 'high engagement' note"

    def test_strongest_review_volume_rejected(self):
        """'strongest review volume (1,144)' — must be rejected."""
        from app.concierge.batched_reason_builder import _assess_quality
        note = "Revolution Brewing has the strongest review volume (1,144) in this set."
        ok, reason = _assess_quality(note, self._ev())
        assert not ok, f"Expected rejection for 'strongest review volume'"

    def test_smaller_review_count_rejected(self):
        """'smaller review count (313)' — must be rejected."""
        from app.concierge.batched_reason_builder import _assess_quality
        note = "Cruz Blanca carries a smaller review count (313) compared to peers here."
        ok, reason = _assess_quality(note, self._ev())
        assert not ok, f"Expected rejection for 'smaller review count'"

    def test_steady_review_volume_rejected(self):
        """'steady review volume (282)' — must be rejected."""
        from app.concierge.batched_reason_builder import _assess_quality
        note = "Empirical Brewery shows a steady review volume (282) for its Foster Ave taproom."
        ok, reason = _assess_quality(note, self._ev())
        assert not ok, f"Expected rejection for 'steady review volume'"

    def test_lightest_review_footprint_rejected(self):
        """'lightest review footprint (110)' — must be rejected."""
        from app.concierge.batched_reason_builder import _assess_quality
        note = "Pilot Project has the lightest review footprint (110) of the eight cards."
        ok, reason = _assess_quality(note, self._ev())
        assert not ok, f"Expected rejection for 'lightest review footprint'"


# ══════════════════════════════════════════════════════════════════════════════
# TestRatingPrimaryV5
# ══════════════════════════════════════════════════════════════════════════════

class TestRatingPrimaryV5:
    """New indirect rating/review phrasings — all must be rejected."""

    def _ev(self):
        return _thin_ev()

    def test_review_volume_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        note = "Goose Island has the largest review volume in this set, reflecting city-wide popularity."
        ok, reason = _assess_quality(note, self._ev())
        assert not ok, "Expected rejection for 'review volume'"

    def test_review_footprint_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        note = "Cruz Blanca has the smallest review footprint among these eight taprooms."
        ok, reason = _assess_quality(note, self._ev())
        assert not ok, "Expected rejection for 'review footprint'"

    def test_review_count_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        note = "Pilot Project carries a smaller review count than its peers in this set."
        ok, reason = _assess_quality(note, self._ev())
        assert not ok, "Expected rejection for 'review count'"

    def test_feedback_volume_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        note = "Revolution Brewing leads on feedback volume with over 2,100 user responses."
        ok, reason = _assess_quality(note, self._ev())
        assert not ok, "Expected rejection for 'feedback volume'"

    def test_carrying_review_volume_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        note = "Half Acre carries review volume typical of a well-established neighborhood taproom."
        ok, reason = _assess_quality(note, self._ev())
        assert not ok, "Expected rejection for 'carries review volume'"

    def test_good_differentiator_still_passes(self):
        """A note using concept/menu/specialty (not rating) still passes."""
        from app.concierge.batched_reason_builder import _assess_quality
        good_notes = [
            "Goose Island Brewhouse on Clybourn Ave is known for Bourbon County stouts and year-round IPAs.",
            "Izakaya Mita in Bucktown offers traditional grilled skewers and sake in a late-night format.",
            "Dovetail Brewery specializes in European-style lagers, an unusual niche in Chicago's IPA-heavy scene.",
        ]
        for note in good_notes:
            ok, reason = _assess_quality(note, self._ev())
            assert ok, f"Expected quality pass for note={note!r}, got reason={reason!r}"

    def test_rating_as_secondary_still_passes(self):
        """Rating as secondary context (after a real differentiator) still passes."""
        from app.concierge.batched_reason_builder import _assess_quality
        note = (
            "Goose Island Brewhouse on Clybourn Ave is Chicago's heritage craft brewery, "
            "known for Bourbon County stouts — it carries a 4.5★ rating across 802 reviews."
        )
        ok, reason = _assess_quality(note, self._ev())
        assert ok, f"Rating as secondary should pass, got reason={reason!r}"


# ══════════════════════════════════════════════════════════════════════════════
# TestModifierTelemetryV5
# ══════════════════════════════════════════════════════════════════════════════

class TestModifierTelemetryV5:
    """Production modifier_status telemetry correctly distinguishes confirmed_listing_context."""

    def test_northman_is_confirmed_listing_context(self):
        """Northman's name contains 'Riverwalk' → modifier_status=confirmed_listing_context."""
        from tests.evidence_harness_v4 import _compute_modifier_status
        entity = _make_entity(
            name="The Northman Beer & Cider Garden on the Riverwalk",
            address="Riverwalk, Chicago, IL",
        )
        frame = _make_frame("breweries near the river")
        _mod, status = _compute_modifier_status(entity, frame)
        assert status == "confirmed_listing_context", (
            f"Northman must be confirmed_listing_context, got {status!r}"
        )

    def test_regular_brewery_is_unknown_not_none(self):
        """For 'breweries near the river', a card without river terms → unknown (not none)."""
        from tests.evidence_harness_v4 import _compute_modifier_status
        entity = _make_entity(
            name="Goose Island Brewhouse",
            address="1800 N Clybourn Ave, Chicago, IL",
        )
        frame = _make_frame("breweries near the river")
        _mod, status = _compute_modifier_status(entity, frame)
        assert status == "unknown", (
            f"Non-river brewery for river query must be 'unknown', got {status!r}"
        )

    def test_izakaya_no_modifier_is_none(self):
        """'izakayas' query has no modifier → modifier_status=none."""
        from tests.evidence_harness_v4 import _compute_modifier_status
        entity = _make_entity(name="Gaijin", address="950 W Lake St, Chicago, IL")
        frame = _make_frame("izakayas")
        _mod, status = _compute_modifier_status(entity, frame)
        assert status == "none", f"No-modifier query must be 'none', got {status!r}"

    def test_taproom_view_without_view_name_is_unknown(self):
        """'taprooms with a view' — card without view in name → unknown or none (honest gap)."""
        from tests.evidence_harness_v4 import _compute_modifier_status
        entity = _make_entity(
            name="Spiteful Brewing",
            address="1815 W Berteau Ave, Chicago, IL",
        )
        frame = _make_frame("taprooms with a view")
        _mod, status = _compute_modifier_status(entity, frame)
        # "view" goes into ambiguity_flags, not geo_hints/location_modifiers → none
        assert status in ("none", "unknown"), (
            f"Taproom-with-view without view in name must be none/unknown, got {status!r}"
        )

    def test_northman_modifier_in_harness_row(self):
        """End-to-end: harness v5 Table 1 shows Northman as confirmed_listing_context."""
        from tests.evidence_harness_v5 import _run_scenario, _brewery_v5_pass1_notes
        from tests.evidence_harness_v4 import _BREWERY_8_NORTHMAN
        rows, meta, _ = _run_scenario(
            "breweries near the river", _BREWERY_8_NORTHMAN, _brewery_v5_pass1_notes()
        )
        northman = next((r for r in rows if "Northman" in r["card_title"]), None)
        assert northman is not None, "Northman card not found in Table 1"
        assert northman["modifier_status"] == "confirmed_listing_context", (
            f"Northman modifier_status={northman['modifier_status']!r} "
            f"(expected confirmed_listing_context)"
        )
        assert northman["displayWhyValidated"] == "True", "Northman must be validated"


# ══════════════════════════════════════════════════════════════════════════════
# TestTaproomViewQualityV5
# ══════════════════════════════════════════════════════════════════════════════

class TestTaproomViewQualityV5:
    """Taprooms-with-view: 8/8 validated, no rating-primary, every note addresses view."""

    def test_taprooms_8_of_8_validated(self):
        from tests.evidence_harness_v5 import _run_scenario, _taproom_v5_pass1_notes
        from tests.evidence_harness_v4 import _TAPROOM_8_DATA
        rows, meta, _ = _run_scenario(
            "taprooms with a view", _TAPROOM_8_DATA, _taproom_v5_pass1_notes()
        )
        assert meta.accepted_count == meta.final_card_count, (
            f"Table 2: accepted={meta.accepted_count} != final={meta.final_card_count}"
        )
        assert meta.final_note_omitted_count == 0
        assert meta.deterministic_visible_count == 0

    def test_taprooms_no_rating_primary_notes(self):
        from tests.evidence_harness_v5 import _run_scenario, _taproom_v5_pass1_notes, _has_rating_primary
        from tests.evidence_harness_v4 import _TAPROOM_8_DATA
        rows, _, _ = _run_scenario(
            "taprooms with a view", _TAPROOM_8_DATA, _taproom_v5_pass1_notes()
        )
        for row in rows:
            note = row["visible_concierge_note"]
            assert not _has_rating_primary(note), (
                f"Taproom card {row['card_index']} has rating-primary note: {note!r}"
            )

    def test_taprooms_all_notes_address_view(self):
        """Every validated taproom note either confirms view evidence or explicitly denies it."""
        from tests.evidence_harness_v5 import _run_scenario, _taproom_v5_pass1_notes, _note_addresses_view
        from tests.evidence_harness_v4 import _TAPROOM_8_DATA
        rows, _, _ = _run_scenario(
            "taprooms with a view", _TAPROOM_8_DATA, _taproom_v5_pass1_notes()
        )
        for row in rows:
            if row["displayWhyValidated"] == "True":
                note = row["visible_concierge_note"]
                assert _note_addresses_view(note), (
                    f"Taproom card {row['card_index']} note does not address view: {note!r}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# TestIzakayaQualityV5
# ══════════════════════════════════════════════════════════════════════════════

class TestIzakayaQualityV5:
    """Izakayas: 8/8 validated, no review-volume-primary notes."""

    def test_izakayas_8_of_8_validated(self):
        from tests.evidence_harness_v5 import _run_scenario, _izakaya_v5_pass1_notes
        from tests.evidence_harness_v4 import _IZAKAYA_8_DATA
        rows, meta, _ = _run_scenario(
            "izakayas", _IZAKAYA_8_DATA, _izakaya_v5_pass1_notes()
        )
        assert meta.accepted_count == meta.final_card_count, (
            f"Table 3: accepted={meta.accepted_count} != final={meta.final_card_count}"
        )
        assert meta.final_note_omitted_count == 0
        assert meta.deterministic_visible_count == 0

    def test_izakayas_no_review_volume_notes(self):
        from tests.evidence_harness_v5 import _run_scenario, _izakaya_v5_pass1_notes, _has_rating_primary
        from tests.evidence_harness_v4 import _IZAKAYA_8_DATA
        rows, _, _ = _run_scenario(
            "izakayas", _IZAKAYA_8_DATA, _izakaya_v5_pass1_notes()
        )
        for row in rows:
            note = row["visible_concierge_note"]
            assert not _has_rating_primary(note), (
                f"Izakaya card {row['card_index']} has rating/review-primary note: {note!r}"
            )

    def test_izakaya_venue_head_recognized(self):
        """venue_head_recognized=True for 'izakayas' query (unchanged from v4)."""
        from app.concierge.frame_extractor import extract_frame
        from app.concierge.ranker import rank_entities_with_stats
        from app.concierge.place_entity_layer import PlaceEntity
        frame = extract_frame("izakayas", "Chicago")
        dummy = [PlaceEntity(
            place_id="iz_test", name="Izakaya Test",
            types=["japanese_restaurant"], primary_type="japanese_restaurant",
            rating=4.5, user_rating_count=500, business_status="OPERATIONAL",
            formatted_address="100 Test St, Chicago, IL",
            google_maps_uri="https://maps.google.com/?cid=1",
            website_uri=None, price_level=None, lat=41.88, lng=-87.63,
            source_query="izakayas Chicago",
        )]
        _, stats = rank_entities_with_stats(dummy, frame)
        assert stats.concept_is_recognized, "izakaya must be recognized in SYNONYM_SETS"


# ══════════════════════════════════════════════════════════════════════════════
# TestHarnessV5Integration
# ══════════════════════════════════════════════════════════════════════════════

class TestHarnessV5Integration:
    """End-to-end harness v5: all three production queries pass all v5 criteria."""

    def test_brewery_river_all_validated(self):
        from tests.evidence_harness_v5 import _run_scenario, _brewery_v5_pass1_notes
        from tests.evidence_harness_v4 import _BREWERY_8_NORTHMAN
        rows, meta, _ = _run_scenario(
            "breweries near the river", _BREWERY_8_NORTHMAN, _brewery_v5_pass1_notes()
        )
        assert meta.accepted_count == 8
        assert meta.final_note_omitted_count == 0
        assert meta.deterministic_visible_count == 0
        assert all(r["displayWhyValidated"] == "True" for r in rows)

    def test_northman_confirmed_listing_context(self):
        from tests.evidence_harness_v5 import _run_scenario, _brewery_v5_pass1_notes
        from tests.evidence_harness_v4 import _BREWERY_8_NORTHMAN
        rows, _, _ = _run_scenario(
            "breweries near the river", _BREWERY_8_NORTHMAN, _brewery_v5_pass1_notes()
        )
        northman = next(r for r in rows if "Northman" in r["card_title"])
        assert northman["modifier_status"] == "confirmed_listing_context"
        assert northman["displayWhyValidated"] == "True"

    def test_taproom_view_all_validated(self):
        from tests.evidence_harness_v5 import _run_scenario, _taproom_v5_pass1_notes
        from tests.evidence_harness_v4 import _TAPROOM_8_DATA
        rows, meta, _ = _run_scenario(
            "taprooms with a view", _TAPROOM_8_DATA, _taproom_v5_pass1_notes()
        )
        assert meta.accepted_count == 8
        assert meta.final_note_omitted_count == 0
        assert all(r["displayWhyValidated"] == "True" for r in rows)

    def test_izakaya_all_validated(self):
        from tests.evidence_harness_v5 import _run_scenario, _izakaya_v5_pass1_notes
        from tests.evidence_harness_v4 import _IZAKAYA_8_DATA
        rows, meta, _ = _run_scenario(
            "izakayas", _IZAKAYA_8_DATA, _izakaya_v5_pass1_notes()
        )
        assert meta.accepted_count == 8
        assert meta.final_note_omitted_count == 0
        assert all(r["displayWhyValidated"] == "True" for r in rows)

    def test_all_pr252_bad_notes_rejected(self):
        """All six PR #252 production bad notes are rejected by the quality gate."""
        from app.concierge.batched_reason_builder import _assess_quality
        from app.concierge.ranker import MinimalEvidenceBundle
        from tests.evidence_harness_v5 import PR252_BAD_NOTES
        thin_ev = MinimalEvidenceBundle(entity=_make_entity(), evidence_adequacy="THIN")
        for pattern_name, bad_note in PR252_BAD_NOTES:
            ok, reason = _assess_quality(bad_note, thin_ev)
            assert not ok, (
                f"PR #252 bad note NOT rejected: pattern={pattern_name!r} note={bad_note!r}"
            )
