"""Tests for EvidencePack v4: Modifier Evidence Contract v1 + Riverwalk safe-evidence.

Covers:
  TestRiverwalkSafeEvidence    — Riverwalk-name card validates; scenic claims still blocked
  TestLakeviewNeighborhood     — 'Lakeview' neighborhood name not falsely rejected
  TestRatingPrimaryRejection   — highest-rated, review-base, ordinal-rank notes rejected
  TestEvidenceAdequacyV4       — STRONG requires enrichment; rating+reviews = THIN/OK only
  TestModifierEvidenceContract — per-card modifier_status computed correctly
  TestHarnessV4Integration     — end-to-end: 8/8 validated for all three production queries
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

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


def _make_enrichment(
    place_id: str = "pid_test",
    editorial_summary: Optional[str] = None,
    serves_beer: Optional[bool] = None,
    outdoor_seating: Optional[bool] = None,
):
    from app.concierge.place_details_provider import PlaceDetailsResult
    return PlaceDetailsResult(
        place_id=place_id,
        editorial_summary=editorial_summary,
        review_snippets=[],
        serves_beer=serves_beer,
        outdoor_seating=outdoor_seating,
        live_music=None,
        good_for_groups=None,
    )


def _make_frame(query: str, destination: str = "Chicago"):
    from app.concierge.frame_extractor import extract_frame
    return extract_frame(query, destination)


def _make_bundle(entity, frame, subtype_fit: float = 0.88, enrichment=None):
    from app.concierge.ranker import RankScore, build_evidence_bundle
    score = RankScore(total=0.72, subtype_fit=subtype_fit, geo_fit=0.55)
    return build_evidence_bundle(entity, frame, score, enrichment=enrichment)


def _thin_ev(entity=None):
    from app.concierge.ranker import MinimalEvidenceBundle
    e = entity or _make_entity()
    return MinimalEvidenceBundle(entity=e, evidence_adequacy="THIN")


# ══════════════════════════════════════════════════════════════════════════════
# TestRiverwalkSafeEvidence
# ══════════════════════════════════════════════════════════════════════════════

class TestRiverwalkSafeEvidence:
    """Modifier Evidence Contract v1: Riverwalk in verified name is safe listing context."""

    def _northman_entity(self):
        return _make_entity(
            name="The Northman Beer & Cider Garden on the Riverwalk",
            address="Riverwalk, Chicago, IL",
            source_query="breweries riverwalk Chicago",
        )

    def _northman_bundle(self, query="breweries near the river"):
        entity = self._northman_entity()
        frame = _make_frame(query)
        return entity, frame, _make_bundle(entity, frame)

    def test_riverwalk_in_name_supports_listing_mention(self):
        """_evidence_supports_claim returns True when entity name contains 'Riverwalk'."""
        from app.concierge.reason_validator import _evidence_supports_claim
        from app.concierge.ranker import MinimalEvidenceBundle
        entity = self._northman_entity()
        ev = MinimalEvidenceBundle(entity=entity)
        # "Riverwalk" appears in entity.name → claim is supported
        assert _evidence_supports_claim("Riverwalk", ev) is True

    def test_riverwalk_listing_note_validates(self):
        """A note safely mentioning Riverwalk as a listing-name fact is accepted."""
        from app.concierge.reason_validator import validate_reason
        entity, frame, ev = self._northman_bundle()
        safe_note = (
            "The verified Google listing places Northman on the Riverwalk, "
            "making it the strongest river-context beer stop in this set; "
            "verify seating and views on-site."
        )
        is_valid, rejection = validate_reason(safe_note, frame, ev)
        assert is_valid, f"Expected valid Riverwalk listing note, got rejection={rejection!r}"

    def test_river_view_claim_still_rejected_for_northman(self):
        """Even for the Northman, 'river views' is still an unsupported scenic claim."""
        from app.concierge.reason_validator import validate_reason
        entity, frame, ev = self._northman_bundle()
        bad_note = "The Northman has beautiful river views from the patio seating area."
        is_valid, rejection = validate_reason(bad_note, frame, ev)
        assert not is_valid, "Expected rejection for unsupported 'river views' claim"
        assert "river" in rejection.lower() or "unsupported" in rejection.lower()

    def test_waterfront_seating_rejected_for_northman(self):
        """'Waterfront seating' is not in the entity name, so it must be rejected."""
        from app.concierge.reason_validator import validate_reason
        entity, frame, ev = self._northman_bundle()
        bad_note = (
            "The Northman offers great waterfront seating on the Riverwalk "
            "with stunning views of the Chicago River."
        )
        is_valid, rejection = validate_reason(bad_note, frame, ev)
        assert not is_valid, "Expected rejection for 'waterfront seating' unsupported claim"

    def test_riverwalk_negated_passes_without_entity_support(self):
        """'Riverwalk proximity is not confirmed' can pass even for a non-Riverwalk card."""
        from app.concierge.reason_validator import validate_reason
        entity = _make_entity(name="Half Acre Beer Company", address="4257 N Lincoln Ave, Chicago, IL")
        frame = _make_frame("breweries near the river")
        ev = _make_bundle(entity, frame)
        # "Riverwalk" in a negation context should still pass
        note = (
            "Half Acre Beer Company on Lincoln Ave focuses on small-batch styles; "
            "Riverwalk proximity is not confirmed from the listing address."
        )
        is_valid, rejection = validate_reason(note, frame, ev)
        assert is_valid, f"Expected valid for negated Riverwalk claim, got rejection={rejection!r}"

    def test_northman_card_validates_in_batch_orchestrator(self):
        """End-to-end: Northman card is validated (not omitted) by build_reasons_with_retry."""
        from app.concierge.batched_reason_builder import build_reasons_with_retry
        from app.concierge.ranker import RankScore, build_evidence_bundle
        from app.concierge.safe_reason_builder import build_safe_reason

        entity = self._northman_entity()
        frame = _make_frame("breweries near the river")
        score = RankScore(total=0.72, subtype_fit=0.88, geo_fit=0.65)
        ev = build_evidence_bundle(entity, frame, score)
        det = build_safe_reason(entity, ev, frame, score)
        cards_data = [(entity, ev, score, det)]

        riverwalk_note = (
            "The verified Google listing places Northman on the Riverwalk, "
            "making it the strongest river-context beer stop in this set; "
            "verify seating and views on-site."
        )

        def mock_llm(prompt, timeout, model=""):
            return json.dumps({"1": riverwalk_note})

        with patch("app.concierge.batched_reason_builder._flag_enabled", return_value=True), \
             patch("app.concierge.batched_reason_builder._call_llm", side_effect=mock_llm):
            reasons, result = build_reasons_with_retry(cards_data, frame)

        cr = reasons.get("1")
        assert cr is not None
        assert cr.validated, (
            f"Northman card must be validated. "
            f"final_note_omitted_count={result.final_note_omitted_count} "
            f"failure_reason={result.failure_reason!r}"
        )
        assert "riverwalk" in cr.note.lower()
        assert result.final_note_omitted_count == 0
        assert result.deterministic_visible_count == 0


# ══════════════════════════════════════════════════════════════════════════════
# TestLakeviewNeighborhood
# ══════════════════════════════════════════════════════════════════════════════

class TestLakeviewNeighborhood:
    """'Lakeview' (Chicago neighborhood) must not be treated as 'lake view' scenic claim."""

    def _lakeview_entity(self):
        return _make_entity(
            name="Corridor Brewery & Provisions",
            address="3446 N Southport Ave, Chicago, IL",
            source_query="taprooms with a view Chicago",
        )

    def test_lakeview_neighborhood_not_rejected(self):
        """A note mentioning 'Lakeview neighborhood taproom' must not be rejected."""
        from app.concierge.reason_validator import validate_reason
        entity = self._lakeview_entity()
        frame = _make_frame("taprooms with a view")
        ev = _make_bundle(entity, frame, enrichment=_make_enrichment(
            editorial_summary="A Lakeview neighborhood taproom focused on hazy IPAs.",
            outdoor_seating=True,
        ))
        note = (
            "Corridor Brewery on Southport Ave is a Lakeview neighborhood taproom "
            "offering hazy IPAs and outdoor patio seating — a view is not confirmed."
        )
        is_valid, rejection = validate_reason(note, frame, ev)
        assert is_valid, (
            f"'Lakeview neighborhood' must not be rejected as scenic claim. "
            f"Rejection: {rejection!r}"
        )

    def test_lake_view_scenic_still_rejected(self):
        """An unsupported 'lake view' scenic claim (with space) is still rejected."""
        from app.concierge.reason_validator import validate_reason
        entity = self._lakeview_entity()
        frame = _make_frame("taprooms with a view")
        ev = _make_bundle(entity, frame)
        note = "Corridor Brewery offers a beautiful lake view from the rooftop patio."
        is_valid, rejection = validate_reason(note, frame, ev)
        assert not is_valid, "Expected rejection for 'lake view' scenic claim with space"


# ══════════════════════════════════════════════════════════════════════════════
# TestRatingPrimaryRejection
# ══════════════════════════════════════════════════════════════════════════════

class TestRatingPrimaryRejection:
    """Quality gate rejects notes where rating/review count is the primary differentiator."""

    def _ev(self):
        return _thin_ev()

    def test_highest_rated_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev()
        note = "Goose Island is the highest-rated taproom in this set, with 4.8 stars."
        ok, reason = _assess_quality(note, ev)
        assert not ok, f"Expected rejection for highest-rated note, got ok=True"
        assert reason, "Expected non-empty rejection reason"

    def test_most_reviewed_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev()
        note = "Revolution Brewing is the most-reviewed brewery here with 2,100 Google reviews."
        ok, reason = _assess_quality(note, ev)
        assert not ok, f"Expected rejection for most-reviewed note, got ok=True"

    def test_review_base_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev()
        note = "Goose Island has the second-largest review base among all breweries here."
        ok, reason = _assess_quality(note, ev)
        assert not ok, f"Expected rejection for review-base note, got ok=True"

    def test_smallest_review_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev()
        note = "Pilot Project has the smallest review count here at 190 reviews."
        ok, reason = _assess_quality(note, ev)
        assert not ok, f"Expected rejection for smallest-review note, got ok=True"

    def test_solid_mid_tier_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev()
        note = "Spiteful Brewing is a solid mid-tier option at 4.3 stars in this set."
        ok, reason = _assess_quality(note, ev)
        assert not ok, f"Expected rejection for solid-mid-tier note, got ok=True"

    def test_established_reputation_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev()
        note = "Goose Island has an established reputation in Chicago's craft beer scene."
        ok, reason = _assess_quality(note, ev)
        assert not ok, f"Expected rejection for established-reputation note, got ok=True"

    def test_strong_flagship_choice_rejected(self):
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev()
        note = "Revolution Brewing is the strong flagship choice in Chicago's craft beer landscape."
        ok, reason = _assess_quality(note, ev)
        assert not ok, f"Expected rejection for strong-flagship-choice note, got ok=True"

    def test_specific_differentiator_passes(self):
        """A note with a real differentiator (not rating/review) passes quality gate."""
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev()
        good_notes = [
            "Goose Island Brewhouse on Clybourn is Chicago's heritage craft brewery, "
            "known for Bourbon County stouts and year-round IPAs with outdoor patio seating.",
            "Forbidden Root pairs botanical herb-forward beers with a full gastropub kitchen "
            "— a combination rarely found at standard taprooms.",
            "Dovetail Brewery on Belle Plaine specializes in European-style lagers and farmhouse "
            "ales, an unusual niche in Chicago's IPA-heavy craft scene.",
        ]
        for note in good_notes:
            ok, reason = _assess_quality(note, ev)
            assert ok, f"Expected quality pass for note={note!r}, got reason={reason!r}"

    def test_rating_as_secondary_passes(self):
        """Rating as secondary context (after a real differentiator) is allowed."""
        from app.concierge.batched_reason_builder import _assess_quality
        ev = self._ev()
        # Real differentiator first, rating as secondary context
        note = (
            "Goose Island Brewhouse on Clybourn Ave is Chicago's heritage craft brewery, "
            "known for Bourbon County stouts — it carries a 4.5★ rating across 802 reviews."
        )
        ok, reason = _assess_quality(note, ev)
        assert ok, f"Rating as secondary context should pass, got reason={reason!r}"

    def test_validator_rejects_consistent_crowd_draw(self):
        """Validator rejects 'consistent crowd draw' as generic boilerplate."""
        from app.concierge.reason_validator import validate_reason
        entity = _make_entity()
        frame = _make_frame("breweries")
        ev = _make_bundle(entity, frame)
        note = "Goose Island is a consistent crowd draw in Chicago's craft beer scene with many visitors."
        is_valid, rejection = validate_reason(note, frame, ev)
        assert not is_valid, f"Expected rejection for 'consistent crowd draw'"
        assert "boilerplate" in rejection or "generic" in rejection


# ══════════════════════════════════════════════════════════════════════════════
# TestEvidenceAdequacyV4
# ══════════════════════════════════════════════════════════════════════════════

class TestEvidenceAdequacyV4:
    """STRONG evidence requires enrichment, not just high subtype_fit + reviews."""

    def _build(self, entity, query="breweries", subtype_fit=0.88, enrichment=None):
        from app.concierge.ranker import RankScore, build_evidence_bundle
        frame = _make_frame(query)
        score = RankScore(total=0.75, subtype_fit=subtype_fit, geo_fit=0.55)
        return build_evidence_bundle(entity, frame, score, enrichment=enrichment)

    def test_high_subtype_and_high_reviews_without_enrichment_is_ok(self):
        """subtype_fit=0.92 + 600 reviews without enrichment is OK, not STRONG."""
        entity = _make_entity(review_count=600)
        ev = self._build(entity, subtype_fit=0.92)
        assert ev.evidence_adequacy == "OK", (
            f"Expected OK (not STRONG) for high subtype_fit + reviews without enrichment, "
            f"got {ev.evidence_adequacy!r}"
        )

    def test_very_high_reviews_without_enrichment_is_not_strong(self):
        """Even 5000 reviews + perfect subtype_fit without enrichment is OK, not STRONG."""
        entity = _make_entity(review_count=5000)
        ev = self._build(entity, subtype_fit=1.0)
        assert ev.evidence_adequacy in ("OK", "THIN"), (
            f"Rating/review count alone must never make evidence STRONG. Got {ev.evidence_adequacy!r}"
        )

    def test_editorial_summary_makes_strong(self):
        """An editorial summary from Place Details upgrades adequacy to STRONG."""
        entity = _make_entity()
        enrichment = _make_enrichment(editorial_summary="Known for Bourbon County stouts.")
        ev = self._build(entity, subtype_fit=0.5, enrichment=enrichment)
        assert ev.evidence_adequacy == "STRONG"

    def test_amenity_flags_make_strong(self):
        """Confirmed amenity flags from Place Details upgrade to STRONG."""
        entity = _make_entity()
        enrichment = _make_enrichment(serves_beer=True, outdoor_seating=True)
        ev = self._build(entity, subtype_fit=0.5, enrichment=enrichment)
        assert ev.evidence_adequacy == "STRONG"

    def test_low_subtype_no_enrichment_is_thin(self):
        """Low subtype_fit + no enrichment = THIN."""
        entity = _make_entity(review_count=50)
        ev = self._build(entity, subtype_fit=0.3)
        assert ev.evidence_adequacy == "THIN"

    def test_modifier_in_name_upgrades_to_ok(self):
        """Entity name containing a user-requested modifier term upgrades to OK."""
        entity = _make_entity(
            name="The Northman Beer & Cider Garden on the Riverwalk",
            address="Riverwalk, Chicago, IL",
            review_count=100,
        )
        # query with "river" geo hint
        ev = self._build(entity, query="breweries near the river", subtype_fit=0.88)
        # Should be OK because name contains "riverwalk" matching the "river" modifier
        assert ev.evidence_adequacy in ("OK", "STRONG"), (
            f"Northman name-contains-modifier should not be THIN, got {ev.evidence_adequacy!r}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TestModifierEvidenceContract
# ══════════════════════════════════════════════════════════════════════════════

class TestModifierEvidenceContract:
    """Per-card modifier_status is correctly computed from entity name/address."""

    def test_riverwalk_in_name_is_confirmed_listing_context(self):
        from tests.evidence_harness_v4 import _compute_modifier_status
        entity = _make_entity(
            name="The Northman Beer & Cider Garden on the Riverwalk",
            address="Riverwalk, Chicago, IL",
        )
        frame = _make_frame("breweries near the river")
        modifier, status = _compute_modifier_status(entity, frame)
        assert status == "confirmed_listing_context", (
            f"Expected confirmed_listing_context for Northman, got {status!r}"
        )

    def test_regular_brewery_is_unknown(self):
        from tests.evidence_harness_v4 import _compute_modifier_status
        entity = _make_entity(
            name="Goose Island Brewhouse",
            address="1800 N Clybourn Ave, Chicago, IL",
        )
        frame = _make_frame("breweries near the river")
        modifier, status = _compute_modifier_status(entity, frame)
        assert status == "unknown", f"Expected unknown for non-river brewery, got {status!r}"

    def test_taproom_view_modifier_status(self):
        from tests.evidence_harness_v4 import _compute_modifier_status
        entity = _make_entity(
            name="Spiteful Brewing",
            address="1815 W Berteau Ave, Chicago, IL",
        )
        frame = _make_frame("taprooms with a view")
        modifier, status = _compute_modifier_status(entity, frame)
        # "view" is an ambiguity_flag not a geo_hint/location_modifier for frame_extractor.
        # So no modifier is extracted → (none, none). This is correct — the note must
        # honestly state view is unconfirmed, not that a modifier was "confirmed".
        assert status in ("none", "unknown"), (
            f"Expected none or unknown for 'taprooms with a view' modifier, got {status!r}"
        )

    def test_no_modifier_query_is_none(self):
        from tests.evidence_harness_v4 import _compute_modifier_status
        entity = _make_entity(name="Gaijin", address="950 W Lake St, Chicago, IL")
        frame = _make_frame("izakayas")
        modifier, status = _compute_modifier_status(entity, frame)
        assert modifier == "none" and status == "none", (
            f"No-modifier query should give (none, none), got ({modifier!r}, {status!r})"
        )

    def test_metropolitan_brewing_river_in_address(self):
        """Metropolitan Brewing editorial says 'North Branch of the Chicago River'."""
        from tests.evidence_harness_v4 import _compute_modifier_status
        entity = _make_entity(
            name="Metropolitan Brewing",
            address="3057 N Rockwell St, Chicago, IL",
        )
        frame = _make_frame("breweries near the river")
        # Address doesn't contain "river" explicitly — check result is unknown
        modifier, status = _compute_modifier_status(entity, frame)
        # The address doesn't have "river" in it, only the editorial does
        assert modifier != "none", "Should have a modifier for this query"


# ══════════════════════════════════════════════════════════════════════════════
# TestHarnessV4Integration
# ══════════════════════════════════════════════════════════════════════════════

class TestHarnessV4Integration:
    """End-to-end harness v4: 8/8 validated for all three production queries."""

    def _run_table(self, fn):
        rows, result_meta, frame = fn()
        return rows, result_meta

    def test_table1_brewery_northman_all_validated(self):
        from tests.evidence_harness_v4 import table1_breweries_northman
        rows, meta = self._run_table(table1_breweries_northman)
        assert meta.accepted_count == meta.final_card_count, (
            f"Table 1: accepted={meta.accepted_count} != final={meta.final_card_count}"
        )
        assert meta.final_note_omitted_count == 0
        assert meta.deterministic_visible_count == 0
        assert all(r["displayWhyValidated"] == "True" for r in rows), (
            f"Table 1: not all cards validated: "
            + str([r for r in rows if r["displayWhyValidated"] != "True"])
        )

    def test_table1_northman_validated_not_omitted(self):
        """The Northman Beer & Cider Garden on the Riverwalk must be validated."""
        from tests.evidence_harness_v4 import table1_breweries_northman
        rows, meta = self._run_table(table1_breweries_northman)
        northman_row = next(r for r in rows if "Northman" in r["card_title"])
        assert northman_row["displayWhyValidated"] == "True", (
            f"Northman card NOT validated — production contract violated. "
            f"source={northman_row['displayWhySource']} quality={northman_row['quality_gate_result']}"
        )
        # Must be modifier_status=confirmed_listing_context
        assert northman_row["modifier_status"] == "confirmed_listing_context", (
            f"Northman modifier_status should be confirmed_listing_context, "
            f"got {northman_row['modifier_status']!r}"
        )

    def test_table1_northman_note_no_scenic_claim(self):
        """Northman note must not claim river views, waterfront seating, etc."""
        from tests.evidence_harness_v4 import table1_breweries_northman
        rows, _ = self._run_table(table1_breweries_northman)
        northman_row = next(r for r in rows if "Northman" in r["card_title"])
        note_lower = northman_row["visible_concierge_note"].lower()
        banned = [
            "river view", "riverfront view", "waterfront seating", "scenic view",
            "panoramic", "beautiful view", "stunning view",
        ]
        for phrase in banned:
            assert phrase not in note_lower, (
                f"Northman note contains unsupported scenic claim '{phrase}': "
                f"{northman_row['visible_concierge_note']!r}"
            )

    def test_table2_taprooms_all_validated(self):
        from tests.evidence_harness_v4 import table2_taprooms_view
        rows, meta = self._run_table(table2_taprooms_view)
        assert meta.accepted_count == meta.final_card_count, (
            f"Table 2: accepted={meta.accepted_count} != final={meta.final_card_count}"
        )
        assert meta.final_note_omitted_count == 0
        assert meta.deterministic_visible_count == 0

    def test_table2_no_rating_primary_notes(self):
        """Table 2 (taprooms with a view) must have no rating-primary notes."""
        import re
        from tests.evidence_harness_v4 import table2_taprooms_view
        rows, _ = self._run_table(table2_taprooms_view)
        rating_primary_patterns = [
            r"\bhighest[\s-]rated\b",
            r"\bmost[\s-]reviewed\b",
            r"\breview\s+base\b",
            r"\bsmallest\s+review\b",
        ]
        for row in rows:
            note = row["visible_concierge_note"].lower()
            for pattern in rating_primary_patterns:
                assert not re.search(pattern, note, re.IGNORECASE), (
                    f"Table 2 card {row['card_index']} has rating-primary pattern "
                    f"'{pattern}' in note: {row['visible_concierge_note']!r}"
                )

    def test_table3_izakayas_all_validated(self):
        from tests.evidence_harness_v4 import table3_izakayas_8card
        rows, meta = self._run_table(table3_izakayas_8card)
        assert meta.accepted_count == meta.final_card_count, (
            f"Table 3: accepted={meta.accepted_count} != final={meta.final_card_count}"
        )
        assert meta.final_note_omitted_count == 0
        assert meta.deterministic_visible_count == 0

    def test_table3_izakaya_venue_head_recognized(self):
        """venue_head_recognized=True for 'izakayas' query."""
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
        assert stats.concept_is_recognized, (
            "venue_head_recognized must be True for 'izakayas' — "
            "izakaya must be in SYNONYM_SETS"
        )

    def test_table3_no_rating_primary_notes(self):
        """Table 3 (izakayas) must have no rating-primary notes."""
        import re
        from tests.evidence_harness_v4 import table3_izakayas_8card
        rows, _ = self._run_table(table3_izakayas_8card)
        rating_primary_patterns = [
            r"\bhighest[\s-]rated\b",
            r"\bmost[\s-]reviewed\b",
            r"\breview\s+base\b",
            r"\bsolid\s+mid[\s-]tier\b",
        ]
        for row in rows:
            note = row["visible_concierge_note"].lower()
            for pattern in rating_primary_patterns:
                assert not re.search(pattern, note, re.IGNORECASE), (
                    f"Table 3 card {row['card_index']} has rating-primary pattern "
                    f"'{pattern}' in note: {row['visible_concierge_note']!r}"
                )
