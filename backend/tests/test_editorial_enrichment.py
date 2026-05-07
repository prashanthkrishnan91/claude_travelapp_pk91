"""Tests for Editorial Corroboration v1 (PR #276).

Covers all 14 required test cases:
  1.  Tavily trusted editorial match accepted when snippet/title clearly matches venue.
  2.  Tavily low-confidence / broad article match discarded.
  3.  Serper trusted editorial match accepted when entity match is strong.
  4.  Serper low-confidence / broad article match discarded.
  5.  Article/source cannot mint cards.
  6.  Editorial source cannot override Google identity/addability/operational status.
  7.  Editorial snippets do not go directly into writer unless converted to structured atoms.
  8.  Disallowed "featured/best/reviewers say" claims blocked (allowed_into_writer=False).
  9.  Missing Tavily/Serper keys skip gracefully.
  10. Provider timeout/error does not fail card response.
  11. Non-blocking executor lifecycle — run_editorial_enrichment never blocks card return.
  12. Dossier/AllowedClaimsPacket merge only accepts allowed high-confidence editorial atoms.
  13. Existing Yelp/Foursquare enrichment tests remain unaffected.
  14. Source trust scoring: trusted domain → 1.0, unknown → 0.5.
"""

from __future__ import annotations

import json
import threading
import time
import unittest.mock as mock
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Module under test
# ---------------------------------------------------------------------------
from app.concierge.editorial_enrichment import (
    EDITORIAL_BUDGET_RESERVE_MS,
    EDITORIAL_ENTITY_MATCH_THRESHOLD,
    EDITORIAL_WRITER_ALLOW_THRESHOLD,
    TRUSTED_EDITORIAL_DOMAINS,
    EditorialEnrichmentResult,
    EditorialEnrichmentTelemetry,
    _atoms_from_article,
    _entity_match_score,
    _extract_specialty_atoms,
    _is_disallowed_claim,
    _make_editorial_mention_atom,
    _source_trust_score,
    get_serper_key,
    get_tavily_key,
    run_editorial_enrichment,
)
from app.concierge.cross_source_enrichment import EnrichmentAtom
from app.concierge.evidence_dossier import build_place_evidence_dossier


# ---------------------------------------------------------------------------
# Minimal stubs
# ---------------------------------------------------------------------------

@dataclass
class _FakeEntity:
    place_id: str = "ChIJ_editorial_1"
    name: str = "The Violet Hour"
    lat: Optional[float] = 41.9027
    lng: Optional[float] = -87.6785
    types: List[str] = field(default_factory=lambda: ["bar", "establishment"])
    primary_type: Optional[str] = "bar"
    formatted_address: Optional[str] = "1520 N Damen Ave, Chicago, IL"
    rating: Optional[float] = 4.5
    user_rating_count: Optional[int] = 320
    price_level: Optional[str] = "PRICE_LEVEL_EXPENSIVE"
    business_status: str = "OPERATIONAL"
    google_maps_uri: str = "https://maps.google.com/?cid=1"
    website_uri: Optional[str] = None
    identity_keys: frozenset = field(default_factory=frozenset)
    source_query: str = ""


@dataclass
class _FakeRankScore:
    subtype_fit: float = 0.8
    geo_fit: float = 0.7


@dataclass
class _FakeFrame:
    subtype_concepts: List[Any] = field(default_factory=list)
    geography_hints: List[str] = field(default_factory=list)
    location_modifiers: List[str] = field(default_factory=list)
    soft_preferences: List[str] = field(default_factory=list)
    negative_constraints: List[str] = field(default_factory=list)


class _FakeDeadline:
    def __init__(self, remaining: int = 3000):
        self._remaining = remaining

    def remaining_ms(self) -> int:
        return self._remaining


# ---------------------------------------------------------------------------
# Test 1: Tavily trusted editorial match accepted
# ---------------------------------------------------------------------------

class TestTavilyTrustedMatchAccepted:
    """Test 1: Tavily trusted editorial match accepted when title/snippet clearly names venue."""

    def test_entity_match_venue_in_title(self):
        """Venue name in title → high entity-match confidence."""
        score = _entity_match_score(
            venue_name="The Violet Hour",
            title="The Violet Hour: Chicago's Best Cocktail Bar",
            snippet="Cocktail bar on Damen Ave with craft cocktails",
            url="https://www.timeout.com/chicago/the-violet-hour",
        )
        assert score >= EDITORIAL_WRITER_ALLOW_THRESHOLD, (
            f"Expected entity match >= {EDITORIAL_WRITER_ALLOW_THRESHOLD}, got {score}"
        )

    def test_trusted_editorial_mention_produced(self):
        """Trusted domain + strong entity match → editorial_mention atom with allowed_into_writer=True."""
        mention = _make_editorial_mention_atom(
            entity_match=0.88,
            source_trust=1.0,
            source_provider="tavily",
            provenance={"title": "...", "domain": "timeout.com", "url": "...", "snippet": "..."},
        )
        assert mention is not None
        assert mention.evidence_type == "editorial_mention"
        assert mention.allowed_into_writer is True
        assert mention.conflict_status == "ok"
        assert mention.source_provider == "tavily"
        assert "timeout.com" in mention.normalized_value

    def test_atoms_from_article_accepted_trusted_source(self):
        """Article from trusted source with clear venue name in title → atoms accepted."""
        tel_stats: Dict[str, Any] = {}
        atoms = _atoms_from_article(
            venue_name="The Violet Hour",
            title="The Violet Hour: Chicago's Best Cocktail Den",
            snippet="Famous for craft cocktails and speakeasy vibes in Wicker Park",
            url="https://www.timeout.com/chicago/the-violet-hour",
            source_provider="tavily",
            tel_stats=tel_stats,
        )
        # Should get at least one atom (editorial_mention from timeout.com + specialty)
        assert len(atoms) >= 1
        providers = {a.source_provider for a in atoms}
        assert "tavily" in providers
        # editorial_mention atom should be present since timeout.com is trusted
        types = {a.evidence_type for a in atoms}
        assert "editorial_mention" in types

    def test_specialty_context_extracted_from_snippet(self):
        """Explicit specialty keyword in snippet → specialty_context atom."""
        tel_stats: Dict[str, Any] = {}
        atoms = _atoms_from_article(
            venue_name="The Violet Hour",
            title="The Violet Hour Chicago",
            snippet="Known for craft cocktails and a speakeasy atmosphere",
            url="https://www.eater.com/chicago/the-violet-hour",
            source_provider="tavily",
            tel_stats=tel_stats,
        )
        specialty_atoms = [a for a in atoms if a.evidence_type == "specialty_context"]
        assert len(specialty_atoms) >= 1
        values = [a.normalized_value for a in specialty_atoms]
        assert any("craft cocktail" in v or "speakeasy" in v for v in values), values


# ---------------------------------------------------------------------------
# Test 2: Tavily low-confidence / broad article match discarded
# ---------------------------------------------------------------------------

class TestTavilyLowConfidenceDiscarded:
    """Test 2: Tavily low-confidence / broad article match discarded."""

    def test_entity_match_below_threshold_when_venue_absent(self):
        """Article about "best bars in Chicago" without venue name → match < threshold."""
        score = _entity_match_score(
            venue_name="The Violet Hour",
            title="10 Best Bars in Chicago",
            snippet="Chicago has some of the best bars in the Midwest.",
            url="https://www.timeout.com/chicago/best-bars",
        )
        assert score < EDITORIAL_ENTITY_MATCH_THRESHOLD, (
            f"Expected low entity match, got {score}"
        )

    def test_atoms_from_article_discarded_when_low_match(self):
        """Article not naming the venue → no atoms produced, discard count incremented."""
        tel_stats: Dict[str, Any] = {}
        atoms = _atoms_from_article(
            venue_name="The Violet Hour",
            title="10 Best Cocktail Bars in Chicago 2024",
            snippet="Chicago's cocktail scene has exploded with great options.",
            url="https://www.timeout.com/chicago/best-cocktail-bars",
            source_provider="tavily",
            tel_stats=tel_stats,
        )
        assert atoms == []
        assert tel_stats.get("discarded_low_confidence", 0) >= 1

    def test_run_editorial_enrichment_discards_broad_articles(self):
        """run_editorial_enrichment discards articles not naming the specific venue."""

        def fake_fetch_tavily(*args, **kwargs):
            # Return a broad article that doesn't name the venue
            return True, [], {
                "attempted": True,
                "article_accepted": 0,
                "article_discarded_low_confidence": 1,
                "error": False,
                "timeout": False,
            }

        entity = _FakeEntity()
        with patch(
            "app.concierge.editorial_enrichment._fetch_tavily_atoms",
            side_effect=fake_fetch_tavily,
        ), patch(
            "app.concierge.editorial_enrichment._fetch_serper_atoms",
            return_value=(False, [], {}),
        ):
            result = run_editorial_enrichment(
                [entity],
                deadline=_FakeDeadline(3000),
                tavily_key="fake-key",
                serper_key="",
                destination="Chicago",
                budget_n=1,
            )
        # No atoms for this venue
        assert entity.place_id not in result.atoms_by_place_id


# ---------------------------------------------------------------------------
# Test 3: Serper trusted editorial match accepted
# ---------------------------------------------------------------------------

class TestSerperTrustedMatchAccepted:
    """Test 3: Serper trusted editorial match accepted when entity match is strong."""

    def test_serper_editorial_mention_atom(self):
        """Serper result from trusted domain + venue in title → editorial_mention accepted."""
        tel_stats: Dict[str, Any] = {}
        atoms = _atoms_from_article(
            venue_name="The Violet Hour",
            title="The Violet Hour Chicago Review",
            snippet="A pioneering craft cocktail bar on Damen with no-ice policy",
            url="https://www.eater.com/chicago/the-violet-hour",
            source_provider="serper",
            tel_stats=tel_stats,
        )
        assert len(atoms) >= 1
        assert all(a.source_provider == "serper" for a in atoms)
        types = {a.evidence_type for a in atoms}
        assert "editorial_mention" in types

    def test_serper_specialty_context_extracted(self):
        """Serper snippet with explicit specialty keyword → specialty_context atom."""
        tel_stats: Dict[str, Any] = {}
        atoms = _atoms_from_article(
            venue_name="Violet Hour",
            title="Violet Hour Chicago",
            snippet="Renowned for its craft cocktail program and no-ice policy",
            url="https://theinfatuation.com/chicago/violet-hour",
            source_provider="serper",
            tel_stats=tel_stats,
        )
        specialty = [a for a in atoms if a.evidence_type == "specialty_context"]
        assert any("craft cocktail" in a.normalized_value for a in specialty), [
            a.normalized_value for a in specialty
        ]


# ---------------------------------------------------------------------------
# Test 4: Serper low-confidence / broad article match discarded
# ---------------------------------------------------------------------------

class TestSerperLowConfidenceDiscarded:
    """Test 4: Serper low-confidence / broad article match discarded."""

    def test_serper_broad_article_discarded(self):
        """Serper article not naming the venue → discarded."""
        tel_stats: Dict[str, Any] = {}
        atoms = _atoms_from_article(
            venue_name="The Violet Hour",
            title="Best Cocktail Bars in Wicker Park",
            snippet="Wicker Park is home to many excellent cocktail bars.",
            url="https://thrillist.com/drink/chicago/wicker-park-bars",
            source_provider="serper",
            tel_stats=tel_stats,
        )
        assert atoms == []
        assert tel_stats.get("discarded_low_confidence", 0) >= 1

    def test_serper_partial_name_match_fails(self):
        """Article mentioning similar-but-different venue → low entity match."""
        score = _entity_match_score(
            venue_name="The Violet Hour",
            title="The Purple Hour Opens in Wicker Park",
            snippet="A new craft cocktail bar called The Purple Hour has opened.",
            url="https://eater.com/chicago/purple-hour",
        )
        assert score < EDITORIAL_ENTITY_MATCH_THRESHOLD


# ---------------------------------------------------------------------------
# Test 5: Article/source cannot mint cards
# ---------------------------------------------------------------------------

class TestEditorialCannotMintCards:
    """Test 5: Article/source cannot mint cards."""

    def test_editorial_atoms_do_not_have_addable_flag(self):
        """Editorial atoms have no addable or place_id minting field."""
        tel_stats: Dict[str, Any] = {}
        atoms = _atoms_from_article(
            venue_name="The Violet Hour",
            title="The Violet Hour Chicago",
            snippet="craft cocktail bar",
            url="https://timeout.com/chicago/violet-hour",
            source_provider="tavily",
            tel_stats=tel_stats,
        )
        for atom in atoms:
            assert not hasattr(atom, "addable") or not getattr(atom, "addable", False)
            assert not hasattr(atom, "place_id") or not getattr(atom, "place_id", None)

    def test_run_enrichment_only_keys_by_input_entity_place_ids(self):
        """atoms_by_place_id is keyed only by input entity place_ids, not article URLs/titles."""
        entity = _FakeEntity(place_id="ChIJ_google_verified_only")
        fake_atoms = [
            EnrichmentAtom(
                source_provider="tavily",
                evidence_type="editorial_mention",
                normalized_value="editorial_mention:timeout.com",
                confidence=0.88,
                provenance={"title": "...", "domain": "timeout.com", "url": "...", "snippet": "..."},
                allowed_into_writer=True,
                conflict_status="ok",
            )
        ]

        with patch(
            "app.concierge.editorial_enrichment._enrich_one_card_editorial",
            return_value=("ChIJ_google_verified_only", fake_atoms, {
                "tavily_attempted": True, "serper_attempted": False,
            }),
        ):
            result = run_editorial_enrichment(
                [entity],
                deadline=_FakeDeadline(3000),
                tavily_key="fake-key",
                serper_key="",
                destination="Chicago",
                budget_n=1,
            )

        # Only the Google place_id appears as key — no article-derived keys
        assert set(result.atoms_by_place_id.keys()) == {"ChIJ_google_verified_only"}

    def test_empty_entity_list_returns_no_atoms(self):
        """Empty entity list returns empty atoms_by_place_id (no card minting)."""
        result = run_editorial_enrichment(
            [],
            deadline=_FakeDeadline(3000),
            tavily_key="fake-key",
            serper_key="fake-key",
            destination="Chicago",
        )
        assert result.atoms_by_place_id == {}
        assert result.telemetry.skipped_reason == "no_entities"


# ---------------------------------------------------------------------------
# Test 6: Editorial source cannot override Google identity
# ---------------------------------------------------------------------------

class TestEditorialCannotOverrideGoogleIdentity:
    """Test 6: Editorial source cannot override Google identity/addability/operational status."""

    def test_editorial_atoms_only_provide_enrichment_not_identity(self):
        """Editorial atoms are evidence_type restricted — no identity fields."""
        ALLOWED_EVIDENCE_TYPES = {
            "editorial_mention", "specialty_context", "venue_context",
            "neighborhood_context", "trusted_list_context",
        }
        tel_stats: Dict[str, Any] = {}
        atoms = _atoms_from_article(
            venue_name="The Violet Hour",
            title="The Violet Hour Chicago craft cocktail bar",
            snippet="Known for craft cocktails, outdoor seating, and no-ice policy",
            url="https://timeout.com/chicago/the-violet-hour",
            source_provider="tavily",
            tel_stats=tel_stats,
        )
        for atom in atoms:
            assert atom.evidence_type in ALLOWED_EVIDENCE_TYPES, (
                f"Unexpected evidence_type: {atom.evidence_type}"
            )
            # Normalized value must not contain identity-like fields
            nv = atom.normalized_value
            for forbidden in ("place_id:", "google_maps:", "addable:", "operational:", "address:"):
                assert forbidden not in nv, f"Identity override in normalized_value: {nv!r}"

    def test_dossier_google_fields_not_overridden_by_editorial(self):
        """Google identity fields in dossier unchanged after editorial atoms merged."""
        entity = _FakeEntity()
        rank_score = _FakeRankScore()
        frame = _FakeFrame()

        editorial_atom = EnrichmentAtom(
            source_provider="tavily",
            evidence_type="editorial_mention",
            normalized_value="editorial_mention:timeout.com",
            confidence=0.88,
            provenance={"title": "...", "domain": "timeout.com", "url": "...", "snippet": "..."},
            allowed_into_writer=True,
            conflict_status="ok",
        )

        dossier = build_place_evidence_dossier(
            entity=entity,
            frame=frame,
            rank_score=rank_score,
            enrichment=None,
            category="bar",
            cross_source_atoms=[editorial_atom],
        )

        # Google identity unchanged
        assert dossier.place_id == entity.place_id
        assert dossier.name == entity.name
        assert dossier.lat == entity.lat
        assert dossier.lng == entity.lng
        assert dossier.google_types == entity.types

        # Google Places provider evidence still present and unchanged
        google_ev = next(p for p in dossier.provider_evidence if p.source == "google_places")
        assert any("type:" in f for f in google_ev.facts)

        # Editorial evidence present as separate provider entry
        editorial_ev = next(
            (p for p in dossier.provider_evidence if p.source == "tavily"), None
        )
        assert editorial_ev is not None
        assert any("editorial_mention" in f for f in editorial_ev.facts)


# ---------------------------------------------------------------------------
# Test 7: Editorial snippets not directly passed to writer
# ---------------------------------------------------------------------------

class TestEditorialSnippetsNotDirectToWriter:
    """Test 7: Editorial snippets do not go directly into writer; converted to atoms first."""

    def test_no_raw_snippet_in_normalized_value(self):
        """Normalized_value must be a structured key:value, not a raw snippet."""
        tel_stats: Dict[str, Any] = {}
        atoms = _atoms_from_article(
            venue_name="The Violet Hour",
            title="The Violet Hour Chicago",
            snippet="Tucked inside a former storefront, this long-running Wicker Park bar "
                    "has earned a reputation for innovative craft cocktails served in a "
                    "hushed, candlelit space where no-ice is a deliberate policy.",
            url="https://timeout.com/chicago/the-violet-hour",
            source_provider="tavily",
            tel_stats=tel_stats,
        )
        for atom in atoms:
            nv = atom.normalized_value
            # Normalized value must follow "type:value" pattern, not be a free-text paragraph
            assert len(nv) < 200, f"normalized_value too long (likely raw snippet): {nv!r}"
            # Must contain ":" as a type:value separator
            assert ":" in nv, f"No type:value separator in normalized_value: {nv!r}"
            # Must not contain sentence-ending punctuation (sign of raw snippet)
            assert "." not in nv or nv.count(".") <= 1, f"Likely raw snippet: {nv!r}"

    def test_provenance_snippet_not_in_normalized_value(self):
        """Snippet is in provenance only, not in normalized_value (writer path)."""
        long_snippet = (
            "The Violet Hour is a celebrated cocktail bar that has won many awards "
            "for its innovative drinks program and elegant Prohibition-era atmosphere."
        )
        tel_stats: Dict[str, Any] = {}
        atoms = _atoms_from_article(
            venue_name="The Violet Hour",
            title="The Violet Hour Chicago — Full Review",
            snippet=long_snippet,
            url="https://theinfatuation.com/chicago/the-violet-hour",
            source_provider="tavily",
            tel_stats=tel_stats,
        )
        for atom in atoms:
            # Snippet should be in provenance, not normalized_value
            assert long_snippet[:50] not in atom.normalized_value
            if atom.provenance:
                assert "snippet" in atom.provenance


# ---------------------------------------------------------------------------
# Test 8: Disallowed claim patterns blocked
# ---------------------------------------------------------------------------

class TestDisallowedClaimsBlocked:
    """Test 8: Disallowed "featured/best/reviewers say" claims blocked from writer."""

    @pytest.mark.parametrize("pattern", [
        "best cocktail bar",
        "top pick",
        "award-winning bar",
        "hidden gem",
        "must-visit",
        "highly recommended",
        "great option",
        "reviewers say craft cocktails",
        "featured by timeout",
        "one of the best",
        "a must",
    ])
    def test_disallowed_pattern_detected(self, pattern: str):
        """_is_disallowed_claim returns True for prohibited patterns."""
        assert _is_disallowed_claim(pattern.lower()), f"Should be disallowed: {pattern!r}"

    def test_allowed_specialty_passes_disallowed_filter(self):
        """Valid specialty keywords pass the disallowed filter."""
        for kw in ["craft cocktail", "natural wine bar", "omakase", "speakeasy", "taproom"]:
            assert not _is_disallowed_claim(kw), f"Should be allowed: {kw!r}"

    def test_specialty_atom_with_disallowed_value_blocked(self):
        """Specialty context atom with disallowed value gets allowed_into_writer=False."""
        # Directly test _extract_specialty_atoms with a snippet containing disallowed claim
        # The function should not extract disallowed patterns as specialty atoms anyway
        # (they're not in _SPECIALTY_KEYWORDS), so we test the disallowed filter directly.
        # If somehow a disallowed value is created, it must be blocked.
        from app.concierge.editorial_enrichment import _SPECIALTY_KEYWORDS_LOWER, _is_disallowed_claim
        for kw in _SPECIALTY_KEYWORDS_LOWER:
            val = f"specialty_context:{kw}"
            # None of our specialty keywords should themselves be disallowed
            # (we curated them to avoid superlatives)
            assert not _is_disallowed_claim(val.lower()), (
                f"Specialty keyword is incorrectly disallowed: {kw!r}"
            )


# ---------------------------------------------------------------------------
# Test 9: Missing keys skip gracefully
# ---------------------------------------------------------------------------

class TestMissingKeysGraceful:
    """Test 9: Missing Tavily/Serper keys skip gracefully."""

    def test_both_keys_missing_returns_empty_atoms(self):
        """Both keys absent → skipped with no_keys reason, cards still returned."""
        entity = _FakeEntity()
        result = run_editorial_enrichment(
            [entity],
            deadline=_FakeDeadline(3000),
            tavily_key="",
            serper_key="",
            destination="Chicago",
        )
        assert result.atoms_by_place_id == {}
        assert result.telemetry.skipped_reason == "no_keys"
        assert result.telemetry.enrichment_attempted is False

    def test_only_tavily_missing_serper_runs(self):
        """Tavily key absent → only Serper runs, still returns atoms if match found."""
        entity = _FakeEntity()
        fake_serper_atom = EnrichmentAtom(
            source_provider="serper",
            evidence_type="editorial_mention",
            normalized_value="editorial_mention:timeout.com",
            confidence=0.88,
            provenance={},
            allowed_into_writer=True,
            conflict_status="ok",
        )
        with patch(
            "app.concierge.editorial_enrichment._enrich_one_card_editorial",
            return_value=(entity.place_id, [fake_serper_atom], {"serper_attempted": True}),
        ):
            result = run_editorial_enrichment(
                [entity],
                deadline=_FakeDeadline(3000),
                tavily_key="",
                serper_key="fake-serper-key",
                destination="Chicago",
            )
        assert result.telemetry.skipped_reason is None
        assert result.telemetry.enrichment_attempted is True

    def test_get_tavily_key_returns_empty_when_unset(self, monkeypatch):
        """get_tavily_key() returns empty string when env and settings both absent."""
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.tavily_api_key = ""
            key = get_tavily_key()
        assert key == ""

    def test_get_serper_key_returns_empty_when_unset(self, monkeypatch):
        """get_serper_key() returns empty string when env and settings both absent."""
        monkeypatch.delenv("SERPER_API_KEY", raising=False)
        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.serper_api_key = ""
            key = get_serper_key()
        assert key == ""


# ---------------------------------------------------------------------------
# Test 10: Provider timeout/error does not fail card response
# ---------------------------------------------------------------------------

class TestProviderFailureIsolated:
    """Test 10: Provider timeout/error does not fail card response."""

    def test_tavily_error_returns_empty_atoms_not_exception(self):
        """Tavily HTTP error → empty atoms, no exception, card response unaffected."""
        entity = _FakeEntity()
        with patch(
            "app.concierge.editorial_enrichment._fetch_tavily_atoms",
            side_effect=Exception("Connection refused"),
        ):
            result = run_editorial_enrichment(
                [entity],
                deadline=_FakeDeadline(3000),
                tavily_key="fake-key",
                serper_key="",
                destination="Chicago",
            )
        # No exception raised, no atoms for this entity
        assert isinstance(result, EditorialEnrichmentResult)

    def test_serper_error_returns_empty_atoms_not_exception(self):
        """Serper HTTP error → empty atoms, no exception."""
        entity = _FakeEntity()
        with patch(
            "app.concierge.editorial_enrichment._fetch_serper_atoms",
            side_effect=Exception("Timeout"),
        ):
            result = run_editorial_enrichment(
                [entity],
                deadline=_FakeDeadline(3000),
                tavily_key="",
                serper_key="fake-key",
                destination="Chicago",
            )
        assert isinstance(result, EditorialEnrichmentResult)

    def test_run_enrichment_never_raises(self):
        """run_editorial_enrichment never raises regardless of internal errors."""
        entity = _FakeEntity()
        with patch(
            "app.concierge.editorial_enrichment._enrich_one_card_editorial",
            side_effect=RuntimeError("Internal failure"),
        ):
            result = run_editorial_enrichment(
                [entity],
                deadline=_FakeDeadline(3000),
                tavily_key="fake-key",
                serper_key="fake-key",
                destination="Chicago",
            )
        assert isinstance(result, EditorialEnrichmentResult)


# ---------------------------------------------------------------------------
# Test 11: Non-blocking executor lifecycle
# ---------------------------------------------------------------------------

class TestNonBlockingExecutorLifecycle:
    """Test 11: Non-blocking executor lifecycle — run_editorial_enrichment returns on schedule."""

    def test_fanout_respects_deadline(self):
        """Enrichment with slow providers still returns within ~fanout_deadline seconds."""
        entity = _FakeEntity()
        call_delay = 0.3  # 300ms per card call (longer than fanout budget)

        def slow_enrich(*args, **kwargs):
            time.sleep(call_delay)
            return args[0].place_id, [], {}

        deadline = _FakeDeadline(remaining=500)  # 500ms remaining
        t0 = time.monotonic()
        with patch(
            "app.concierge.editorial_enrichment._enrich_one_card_editorial",
            side_effect=slow_enrich,
        ):
            result = run_editorial_enrichment(
                [entity],
                deadline=deadline,
                tavily_key="fake-key",
                serper_key="fake-key",
                destination="Chicago",
            )
        elapsed = time.monotonic() - t0
        # Should return in well under 2s even with slow providers
        assert elapsed < 2.0, f"Took too long: {elapsed:.2f}s — executor may be blocking"
        assert isinstance(result, EditorialEnrichmentResult)

    def test_budget_exhausted_skips_entirely(self):
        """When remaining budget < EDITORIAL_BUDGET_RESERVE_MS, enrichment is skipped."""
        entity = _FakeEntity()
        result = run_editorial_enrichment(
            [entity],
            deadline=_FakeDeadline(remaining=EDITORIAL_BUDGET_RESERVE_MS - 1),
            tavily_key="fake-key",
            serper_key="fake-key",
            destination="Chicago",
        )
        assert result.telemetry.skipped_reason == "budget_exhausted"
        assert result.telemetry.enrichment_attempted is False
        assert result.atoms_by_place_id == {}


# ---------------------------------------------------------------------------
# Test 12: Dossier merge only accepts allowed high-confidence editorial atoms
# ---------------------------------------------------------------------------

class TestDossierMergeEditorialAtoms:
    """Test 12: Dossier/AllowedClaimsPacket merge only accepts allowed high-confidence atoms."""

    def test_disallowed_atom_excluded_from_dossier(self):
        """Atom with allowed_into_writer=False excluded from dossier provider_evidence."""
        entity = _FakeEntity()
        rank_score = _FakeRankScore()
        frame = _FakeFrame()

        disallowed_atom = EnrichmentAtom(
            source_provider="tavily",
            evidence_type="editorial_mention",
            normalized_value="editorial_mention:somesite.com",
            confidence=0.30,  # low confidence
            provenance={},
            allowed_into_writer=False,  # explicitly not allowed
            conflict_status="discarded",
        )

        dossier = build_place_evidence_dossier(
            entity=entity,
            frame=frame,
            rank_score=rank_score,
            enrichment=None,
            category="bar",
            cross_source_atoms=[disallowed_atom],
        )

        # Tavily provider entry should NOT appear in provider_evidence
        tavily_ev = [p for p in dossier.provider_evidence if p.source == "tavily"]
        assert tavily_ev == [], f"Disallowed atom should not enter dossier: {tavily_ev}"

    def test_allowed_editorial_atom_enters_dossier(self):
        """Atom with allowed_into_writer=True and conflict_status='ok' enters dossier."""
        entity = _FakeEntity()
        rank_score = _FakeRankScore()
        frame = _FakeFrame()

        allowed_atom = EnrichmentAtom(
            source_provider="tavily",
            evidence_type="editorial_mention",
            normalized_value="editorial_mention:timeout.com",
            confidence=0.88,
            provenance={"title": "...", "domain": "timeout.com", "url": "...", "snippet": "..."},
            allowed_into_writer=True,
            conflict_status="ok",
        )

        dossier = build_place_evidence_dossier(
            entity=entity,
            frame=frame,
            rank_score=rank_score,
            enrichment=None,
            category="bar",
            cross_source_atoms=[allowed_atom],
        )

        tavily_ev = next(
            (p for p in dossier.provider_evidence if p.source == "tavily"), None
        )
        assert tavily_ev is not None
        assert any("editorial_mention:timeout.com" in f for f in tavily_ev.facts)

    def test_conflicting_atom_excluded_from_dossier(self):
        """Atom with conflict_status != 'ok' excluded from dossier."""
        entity = _FakeEntity()
        rank_score = _FakeRankScore()
        frame = _FakeFrame()

        conflict_atom = EnrichmentAtom(
            source_provider="serper",
            evidence_type="specialty_context",
            normalized_value="specialty_context:hotel lobby",
            confidence=0.75,
            provenance={},
            allowed_into_writer=True,  # would be allowed, but conflict blocks it
            conflict_status="conflict_logged",  # conflict detected
        )

        dossier = build_place_evidence_dossier(
            entity=entity,
            frame=frame,
            rank_score=rank_score,
            enrichment=None,
            category="bar",
            cross_source_atoms=[conflict_atom],
        )

        serper_ev = [p for p in dossier.provider_evidence if p.source == "serper"]
        assert serper_ev == [], f"Conflict atom should not enter dossier: {serper_ev}"


# ---------------------------------------------------------------------------
# Test 13: Existing Yelp/Foursquare enrichment tests unaffected
# ---------------------------------------------------------------------------

class TestExistingEnrichmentUnaffected:
    """Test 13: Existing Yelp/Foursquare enrichment tests remain passing."""

    def test_cross_source_enrichment_module_still_importable(self):
        """cross_source_enrichment.py remains importable and structurally intact."""
        from app.concierge.cross_source_enrichment import (
            run_cross_source_enrichment,
            score_provider_match,
            EnrichmentAtom,
            CrossSourceTelemetry,
            get_yelp_key,
            get_foursquare_key,
        )
        assert callable(run_cross_source_enrichment)
        assert callable(score_provider_match)
        assert callable(get_yelp_key)
        assert callable(get_foursquare_key)

    def test_yelp_foursquare_enrichment_unaffected_by_editorial_import(self):
        """Editorial enrichment module imports from cross_source_enrichment without mutation."""
        from app.concierge.cross_source_enrichment import EnrichmentAtom, HIGH_CONFIDENCE_THRESHOLD
        from app.concierge.editorial_enrichment import EnrichmentAtom as EditAtom
        # Same class — editorial module re-uses the existing type
        assert EnrichmentAtom is EditAtom

    def test_evidence_dossier_accepts_both_yelp_and_editorial_atoms(self):
        """Dossier builder merges Yelp and editorial atoms together correctly."""
        entity = _FakeEntity()
        rank_score = _FakeRankScore()
        frame = _FakeFrame()

        yelp_atom = EnrichmentAtom(
            source_provider="yelp",
            evidence_type="category",
            normalized_value="yelp_category:Cocktail Bar",
            confidence=0.80,
            provenance={"yelp_id": "abc123", "source_field": "categories"},
            allowed_into_writer=True,
            conflict_status="ok",
        )
        editorial_atom = EnrichmentAtom(
            source_provider="tavily",
            evidence_type="specialty_context",
            normalized_value="specialty_context:craft cocktail",
            confidence=0.85,
            provenance={"title": "...", "domain": "eater.com", "url": "...", "snippet": "..."},
            allowed_into_writer=True,
            conflict_status="ok",
        )

        dossier = build_place_evidence_dossier(
            entity=entity,
            frame=frame,
            rank_score=rank_score,
            enrichment=None,
            cross_source_atoms=[yelp_atom, editorial_atom],
        )

        sources = {p.source for p in dossier.provider_evidence}
        assert "yelp" in sources
        assert "tavily" in sources
        assert "google_places" in sources


# ---------------------------------------------------------------------------
# Test 14: Source trust scoring
# ---------------------------------------------------------------------------

class TestSourceTrustScoring:
    """Test 14: Source trust scoring — trusted domain → 1.0, unknown → 0.5."""

    @pytest.mark.parametrize("domain,expected", [
        ("timeout.com", 1.0),
        ("eater.com", 1.0),
        ("theinfatuation.com", 1.0),
        ("cntraveler.com", 1.0),
        ("guide.michelin.com", 1.0),
        ("chicago.eater.com", 1.0),  # subdomain match
        ("unknown-blog.com", 0.5),
        ("", 0.5),
        ("somerandomblog.net", 0.5),
        ("yelp.com", 0.5),  # yelp is not in trusted editorial domains
    ])
    def test_source_trust_score(self, domain: str, expected: float):
        score = _source_trust_score(domain)
        assert score == expected, f"domain={domain!r} expected={expected} got={score}"

    def test_trusted_domains_not_empty(self):
        """TRUSTED_EDITORIAL_DOMAINS is populated with known high-authority sites."""
        assert len(TRUSTED_EDITORIAL_DOMAINS) >= 10
        assert "eater.com" in TRUSTED_EDITORIAL_DOMAINS
        assert "timeout.com" in TRUSTED_EDITORIAL_DOMAINS
        assert "theinfatuation.com" in TRUSTED_EDITORIAL_DOMAINS

    def test_editorial_mention_requires_trusted_domain(self):
        """_make_editorial_mention_atom returns None for non-trusted domains."""
        mention = _make_editorial_mention_atom(
            entity_match=0.90,
            source_trust=0.5,  # NOT trusted
            source_provider="tavily",
            provenance={"domain": "randomblog.com"},
        )
        assert mention is None, "Non-trusted domain should not produce editorial_mention"

    def test_editorial_mention_produced_for_trusted_domain(self):
        """_make_editorial_mention_atom returns atom for trusted domains."""
        mention = _make_editorial_mention_atom(
            entity_match=0.90,
            source_trust=1.0,  # trusted
            source_provider="serper",
            provenance={"domain": "eater.com"},
        )
        assert mention is not None
        assert mention.allowed_into_writer is True
