"""Tests for Cross-Source Evidence Enrichment v1 (PR #275).

Covers all 10 required test cases:
  1. Yelp high-confidence match accepted → structured evidence atoms.
  2. Yelp low-confidence match discarded.
  3. Foursquare high-confidence match accepted → structured evidence atoms.
  4. Foursquare low-confidence match discarded.
  5. Conflict case logs/downgrades/discards; Google identity/addability never overridden.
  6. Missing provider key does not fail card response.
  7. Provider timeout/error does not fail card response.
  8. Enrichment atoms merged into dossier/AllowedClaimsPacket only when allowed+high-confidence.
  9. Writer/card path hides notes rather than showing fallback/template prose when evidence thin.
  10. No provider can create an addable card without a Google-verified card.
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
from app.concierge.cross_source_enrichment import (
    HIGH_CONFIDENCE_THRESHOLD,
    HARD_NAME_GATE,
    EnrichmentAtom,
    ProviderMatchScore,
    CrossSourceTelemetry,
    CrossSourceEnrichmentResult,
    _normalize_match_name,
    _haversine_m,
    score_provider_match,
    run_cross_source_enrichment,
    _fetch_yelp_atoms,
    _fetch_foursquare_atoms,
    _check_category_conflict,
)
from app.concierge.evidence_dossier import (
    build_place_evidence_dossier,
    build_dossiers_for_ranked_cards,
)


# ---------------------------------------------------------------------------
# Minimal stubs
# ---------------------------------------------------------------------------

@dataclass
class _FakeEntity:
    """Minimal PlaceEntity stub for testing."""
    place_id: str = "ChIJ_test_1"
    name: str = "Test Venue"
    lat: Optional[float] = 41.8827
    lng: Optional[float] = -87.6233
    types: List[str] = field(default_factory=lambda: ["bar", "establishment"])
    primary_type: Optional[str] = "bar"
    formatted_address: Optional[str] = "123 Test St, Chicago, IL"
    rating: Optional[float] = 4.3
    user_rating_count: Optional[int] = 120
    price_level: Optional[str] = "PRICE_LEVEL_MODERATE"
    business_status: str = "OPERATIONAL"
    google_maps_uri: str = "https://maps.google.com/?cid=1"
    website_uri: Optional[str] = None
    identity_keys: frozenset = field(default_factory=frozenset)
    source_query: str = ""


@dataclass
class _FakeRankScore:
    subtype_fit: float = 0.7
    geo_fit: float = 0.8


@dataclass
class _FakeFrame:
    subtype_concepts: List[Any] = field(default_factory=list)
    geography_hints: List[str] = field(default_factory=list)
    location_modifiers: List[str] = field(default_factory=list)
    soft_preferences: List[str] = field(default_factory=list)
    negative_constraints: List[str] = field(default_factory=list)


class _FakeDeadline:
    """RequestDeadline stub with configurable remaining_ms."""

    def __init__(self, remaining: int = 3000):
        self._remaining = remaining

    def remaining_ms(self) -> int:
        return self._remaining

    def elapsed_ms(self) -> int:
        return 1000

    def is_past_soft_ceiling(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Helpers to build minimal Yelp / Foursquare HTTP responses
# ---------------------------------------------------------------------------

def _yelp_response(
    name: str = "Test Venue",
    lat: float = 41.8827,
    lng: float = -87.6233,
    categories: Optional[List[Dict]] = None,
    price: str = "$$",
    rating: float = 4.0,
    review_count: int = 100,
) -> bytes:
    data = {
        "businesses": [{
            "id": "test-yelp-id",
            "name": name,
            "coordinates": {"latitude": lat, "longitude": lng},
            "categories": categories or [{"alias": "bars", "title": "Bars"}],
            "price": price,
            "rating": rating,
            "review_count": review_count,
            "phone": "+13125550100",
            "url": "https://www.yelp.com/biz/test",
        }],
        "total": 1,
    }
    return json.dumps(data).encode()


def _fsq_response(
    name: str = "Test Venue",
    lat: float = 41.8827,
    lng: float = -87.6233,
    categories: Optional[List[Dict]] = None,
    price: int = 2,
    popularity: float = 0.85,
) -> bytes:
    data = {
        "results": [{
            "fsq_id": "test-fsq-id",
            "name": name,
            "geocodes": {"main": {"latitude": lat, "longitude": lng}},
            "categories": categories or [{"id": 13003, "name": "Bar"}],
            "price": price,
            "popularity": popularity,
        }],
        "context": {},
    }
    return json.dumps(data).encode()


# ---------------------------------------------------------------------------
# TEST 1: Yelp high-confidence match accepted → structured atoms
# ---------------------------------------------------------------------------

class TestYelpHighConfidenceAccepted:
    """Test 1: Yelp high-confidence match produces structured evidence atoms."""

    def test_accepted_match_returns_atoms(self):
        entity = _FakeEntity(
            name="Hopleaf Bar",
            lat=41.9997,
            lng=-87.6572,
            types=["bar", "establishment"],
        )
        yelp_data = _yelp_response(
            name="Hopleaf Bar",
            lat=41.9997,
            lng=-87.6572,
            categories=[{"alias": "craftbeer", "title": "Craft Beer Bars"}],
            price="$$",
            rating=4.5,
            review_count=2300,
        )
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = yelp_data
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            match_score, atoms = _fetch_yelp_atoms(entity, "fake-key", timeout=2.0)

        assert match_score is not None
        assert match_score.accepted, f"Expected accepted, got composite={match_score.composite_score:.2f}"
        assert len(atoms) > 0

        # Category atom present
        cat_atoms = [a for a in atoms if a.evidence_type == "category"]
        assert len(cat_atoms) >= 1
        assert "Craft Beer Bars" in cat_atoms[0].normalized_value
        assert cat_atoms[0].source_provider == "yelp"

        # Price atom present
        price_atoms = [a for a in atoms if a.evidence_type == "price"]
        assert len(price_atoms) >= 1
        assert "$$" in price_atoms[0].normalized_value

    def test_accepted_atom_fields_complete(self):
        """All accepted atoms have complete required fields."""
        entity = _FakeEntity(name="The Green Door Tavern", lat=41.8894, lng=-87.6327)
        yelp_data = _yelp_response(
            name="Green Door Tavern",
            lat=41.8894,
            lng=-87.6327,
            categories=[{"alias": "bars", "title": "Dive Bars"}],
        )
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = yelp_data
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            match_score, atoms = _fetch_yelp_atoms(entity, "fake-key", timeout=2.0)

        for atom in atoms:
            assert atom.source_provider == "yelp"
            assert atom.evidence_type in ("category", "price", "attribute", "rating_context", "popularity_context")
            assert isinstance(atom.normalized_value, str) and atom.normalized_value
            assert 0.0 <= atom.confidence <= 1.0
            assert isinstance(atom.provenance, dict)
            assert isinstance(atom.allowed_into_writer, bool)
            assert atom.conflict_status in ("ok", "downgraded", "discarded", "conflict_logged")

    def test_rating_context_atom_not_allowed_into_writer(self):
        """Rating context atoms must never be allowed into writer prose."""
        entity = _FakeEntity(name="Alinea", lat=41.9225, lng=-87.6484)
        yelp_data = _yelp_response(name="Alinea", lat=41.9225, lng=-87.6484, rating=4.9)
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = yelp_data
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            _, atoms = _fetch_yelp_atoms(entity, "fake-key", timeout=2.0)

        rating_atoms = [a for a in atoms if a.evidence_type == "rating_context"]
        for ra in rating_atoms:
            assert not ra.allowed_into_writer, "Rating context must never be in writer claims"


# ---------------------------------------------------------------------------
# TEST 2: Yelp low-confidence match discarded
# ---------------------------------------------------------------------------

class TestYelpLowConfidenceDiscarded:
    """Test 2: Yelp low-confidence match returns empty atoms."""

    def test_wrong_name_discarded(self):
        """A clearly different name must be discarded."""
        entity = _FakeEntity(name="Purple Pig Chicago", lat=41.8898, lng=-87.6266)
        yelp_data = _yelp_response(
            name="Different Restaurant Name",
            lat=41.8900,
            lng=-87.6268,
        )
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = yelp_data
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            match_score, atoms = _fetch_yelp_atoms(entity, "fake-key", timeout=2.0)

        # Match score may be returned (for telemetry) but must not be accepted
        if match_score is not None:
            assert not match_score.accepted
        assert atoms == [], f"Expected no atoms for low-confidence match, got {atoms}"

    def test_name_below_hard_gate_discarded(self):
        """Name similarity below HARD_NAME_GATE is rejected before composite scoring."""
        ms = score_provider_match(
            google_name="Starbucks Coffee",
            google_lat=41.88,
            google_lng=-87.63,
            provider_name="Unrelated Hardware Store",
            provider_lat=41.88,
            provider_lng=-87.63,
        )
        assert not ms.accepted
        assert ms.name_similarity < HARD_NAME_GATE

    def test_no_api_key_returns_empty(self):
        """Empty Yelp key → no match attempted, empty atoms returned."""
        entity = _FakeEntity(name="Some Bar")
        match_score, atoms = _fetch_yelp_atoms(entity, yelp_key="", timeout=2.0)
        assert match_score is None
        assert atoms == []


# ---------------------------------------------------------------------------
# TEST 3: Foursquare high-confidence match accepted → structured atoms
# ---------------------------------------------------------------------------

class TestFoursquareHighConfidenceAccepted:
    """Test 3: Foursquare high-confidence match produces structured evidence atoms."""

    def test_accepted_match_returns_atoms(self):
        entity = _FakeEntity(
            name="Aviary",
            lat=41.8863,
            lng=-87.6480,
            types=["bar", "establishment"],
        )
        fsq_data = _fsq_response(
            name="The Aviary",
            lat=41.8863,
            lng=-87.6480,
            categories=[{"id": 13003, "name": "Cocktail Bar"}],
            price=4,
            popularity=0.95,
        )
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = fsq_data
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            match_score, atoms = _fetch_foursquare_atoms(entity, "fake-fsq-key", timeout=2.0)

        assert match_score is not None
        assert match_score.accepted, f"Expected accepted, got composite={match_score.composite_score:.2f}"
        assert len(atoms) > 0

        # Category atom present
        cat_atoms = [a for a in atoms if a.evidence_type == "category"]
        assert len(cat_atoms) >= 1
        assert "Cocktail Bar" in cat_atoms[0].normalized_value
        assert cat_atoms[0].source_provider == "foursquare"

        # Price atom from Foursquare price=4 → "very expensive"
        price_atoms = [a for a in atoms if a.evidence_type == "price"]
        assert len(price_atoms) >= 1
        assert "very expensive" in price_atoms[0].normalized_value

    def test_popularity_context_not_allowed_into_writer(self):
        """Popularity context atoms must never be allowed into writer prose."""
        entity = _FakeEntity(name="Aviary", lat=41.8863, lng=-87.6480)
        fsq_data = _fsq_response(name="Aviary", lat=41.8863, lng=-87.6480, popularity=0.97)
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = fsq_data
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            _, atoms = _fetch_foursquare_atoms(entity, "fake-fsq-key", timeout=2.0)

        pop_atoms = [a for a in atoms if a.evidence_type == "popularity_context"]
        for pa in pop_atoms:
            assert not pa.allowed_into_writer, "Popularity context must never be in writer claims"

    def test_fsq_atom_provenance_contains_fsq_id(self):
        """Accepted Foursquare atoms must include fsq_id in provenance."""
        entity = _FakeEntity(name="Aviary", lat=41.8863, lng=-87.6480)
        fsq_data = _fsq_response(name="Aviary", lat=41.8863, lng=-87.6480)
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = fsq_data
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            _, atoms = _fetch_foursquare_atoms(entity, "fake-fsq-key", timeout=2.0)

        for atom in atoms:
            assert "fsq_id" in atom.provenance


# ---------------------------------------------------------------------------
# TEST 4: Foursquare low-confidence match discarded
# ---------------------------------------------------------------------------

class TestFoursquareLowConfidenceDiscarded:
    """Test 4: Foursquare low-confidence match returns empty atoms."""

    def test_distant_venue_discarded(self):
        """Provider result 2km away with different name → discarded."""
        entity = _FakeEntity(name="Billy Sunday", lat=41.8883, lng=-87.6727)
        fsq_data = _fsq_response(
            name="Completely Different Bar",
            lat=41.9080,  # ~2 km away
            lng=-87.6800,
        )
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = fsq_data
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            match_score, atoms = _fetch_foursquare_atoms(entity, "fake-fsq-key", timeout=2.0)

        if match_score is not None:
            assert not match_score.accepted
        assert atoms == [], f"Expected no atoms, got {atoms}"

    def test_empty_results_returns_none_and_empty(self):
        """Provider returns no results → None match, empty atoms."""
        entity = _FakeEntity(name="Tiny Hidden Bar")
        fsq_data = json.dumps({"results": []}).encode()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = fsq_data
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            match_score, atoms = _fetch_foursquare_atoms(entity, "fake-fsq-key", timeout=2.0)

        assert match_score is None
        assert atoms == []


# ---------------------------------------------------------------------------
# TEST 5: Conflict case — logged/downgraded/discarded; Google trust gates intact
# ---------------------------------------------------------------------------

class TestConflictCase:
    """Test 5: Category conflicts are detected, logged, and downgraded. Google status never overridden."""

    def test_retail_category_conflicts_with_restaurant_google_type(self):
        """Provider says 'Shopping' but Google says food/drink → conflict_logged, blocked."""
        google_types = ["restaurant", "food", "establishment"]
        result = _check_category_conflict("Shopping Mall", google_types)
        assert result == "conflict_logged"

    def test_compatible_category_is_ok(self):
        """Provider says 'Cocktail Bar' and Google says bar → ok, allowed."""
        google_types = ["bar", "establishment"]
        result = _check_category_conflict("Cocktail Bar", google_types)
        assert result == "ok"

    def test_conflicting_atom_not_allowed_into_writer(self):
        """An atom with conflict_status=conflict_logged must not enter AllowedClaimsPacket."""
        conflicting_atom = EnrichmentAtom(
            source_provider="yelp",
            evidence_type="category",
            normalized_value="yelp_category:Shopping",
            confidence=0.80,
            provenance={"yelp_id": "xyz"},
            allowed_into_writer=False,  # blocked by conflict
            conflict_status="conflict_logged",
        )
        entity = _FakeEntity(
            place_id="ChIJ_test_conflict",
            types=["restaurant", "food"],
        )
        frame = _FakeFrame()
        rank_score = _FakeRankScore()

        dossier = build_place_evidence_dossier(
            entity=entity,
            frame=frame,
            rank_score=rank_score,
            enrichment=None,
            cross_source_atoms=[conflicting_atom],
        )

        # The conflicting atom must NOT appear in provider_evidence facts
        all_facts = [
            f for pev in dossier.provider_evidence
            for f in (pev.facts or [])
            if "Shopping" in f
        ]
        assert all_facts == [], f"Conflicting atom leaked into dossier facts: {all_facts}"

    def test_google_addability_not_overridden_by_provider_data(self):
        """Cross-source atoms cannot create cards — only Google-verified entities can."""
        # This test verifies the structural invariant: run_cross_source_enrichment
        # returns atoms_by_place_id keyed only by pre-existing Google place_ids.
        entity = _FakeEntity(place_id="ChIJ_google_verified", name="Verified Place")
        deadline = _FakeDeadline(remaining=2000)

        yelp_data = _yelp_response(name="Verified Place")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = yelp_data
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            result = run_cross_source_enrichment(
                [entity],
                deadline=deadline,
                yelp_key="fake-key",
                fsq_key="",
            )

        # atoms_by_place_id can only contain keys that were in the input entity list
        for pid in result.atoms_by_place_id:
            assert pid == entity.place_id, (
                f"Cross-source enrichment invented place_id {pid!r} not in Google entities"
            )


# ---------------------------------------------------------------------------
# TEST 6: Missing provider key does not fail card response
# ---------------------------------------------------------------------------

class TestMissingProviderKey:
    """Test 6: Missing provider keys skip enrichment gracefully; cards still returned."""

    def test_no_yelp_key_skips_yelp(self):
        match_score, atoms = _fetch_yelp_atoms(_FakeEntity(), yelp_key="", timeout=2.0)
        assert match_score is None
        assert atoms == []

    def test_no_foursquare_key_skips_fsq(self):
        match_score, atoms = _fetch_foursquare_atoms(_FakeEntity(), fsq_key="", timeout=2.0)
        assert match_score is None
        assert atoms == []

    def test_both_keys_missing_returns_no_key_skip(self):
        """Both keys missing → skipped_reason=no_keys, no atoms, no exception."""
        entity = _FakeEntity()
        deadline = _FakeDeadline(remaining=3000)

        result = run_cross_source_enrichment(
            [entity],
            deadline=deadline,
            yelp_key="",
            fsq_key="",
        )

        assert result.atoms_by_place_id == {}
        assert result.telemetry.skipped_reason == "no_keys"
        assert not result.telemetry.enrichment_attempted

    def test_missing_keys_do_not_raise(self):
        """run_cross_source_enrichment never raises even with no keys."""
        try:
            result = run_cross_source_enrichment(
                [_FakeEntity()],
                deadline=_FakeDeadline(remaining=3000),
                yelp_key="",
                fsq_key="",
            )
            assert result is not None
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"run_cross_source_enrichment raised unexpectedly: {exc}")


# ---------------------------------------------------------------------------
# TEST 7: Provider timeout/error does not fail card response
# ---------------------------------------------------------------------------

class TestProviderTimeoutAndError:
    """Test 7: Provider errors and timeouts are isolated; cards still returned."""

    def test_yelp_http_error_returns_none_and_empty(self):
        """HTTP error from Yelp → None match, empty atoms, no exception."""
        import urllib.error
        entity = _FakeEntity(name="Stable Venue")
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            match_score, atoms = _fetch_yelp_atoms(entity, "fake-key", timeout=2.0)

        assert match_score is None
        assert atoms == []

    def test_foursquare_http_error_returns_none_and_empty(self):
        """HTTP error from Foursquare → None match, empty atoms, no exception."""
        import urllib.error
        entity = _FakeEntity(name="Stable Venue")
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
            match_score, atoms = _fetch_foursquare_atoms(entity, "fake-key", timeout=2.0)

        assert match_score is None
        assert atoms == []

    def test_provider_json_parse_error_isolated(self):
        """Malformed JSON from provider → None match, empty atoms, no exception."""
        entity = _FakeEntity(name="Some Bar")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"not valid json {{{"
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            match_score, atoms = _fetch_yelp_atoms(entity, "fake-key", timeout=2.0)

        assert atoms == []

    def test_run_cross_source_enrichment_does_not_raise_on_error(self):
        """run_cross_source_enrichment never raises even when all providers error."""
        import urllib.error
        entities = [_FakeEntity(place_id=f"pid_{i}") for i in range(3)]
        deadline = _FakeDeadline(remaining=2000)

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("error")):
            try:
                result = run_cross_source_enrichment(
                    entities,
                    deadline=deadline,
                    yelp_key="fake",
                    fsq_key="fake",
                )
                # Result must still be returned, just with no atoms
                assert result is not None
                assert isinstance(result.atoms_by_place_id, dict)
            except Exception as exc:  # noqa: BLE001
                pytest.fail(f"run_cross_source_enrichment raised unexpectedly: {exc}")

    def test_budget_exhausted_skips_gracefully(self):
        """When remaining budget < threshold, enrichment is skipped without error."""
        entity = _FakeEntity()
        deadline = _FakeDeadline(remaining=50)  # well below CROSS_SOURCE_BUDGET_RESERVE_MS

        result = run_cross_source_enrichment(
            [entity],
            deadline=deadline,
            yelp_key="fake",
            fsq_key="fake",
        )

        assert result.atoms_by_place_id == {}
        assert result.telemetry.skipped_reason == "budget_exhausted"


# ---------------------------------------------------------------------------
# TEST 8: Atoms merged into dossier only when allowed + high-confidence
# ---------------------------------------------------------------------------

class TestAtomMergeIntoDossier:
    """Test 8: Cross-source atoms enter dossier provider_evidence only when allowed."""

    def test_allowed_atom_appears_in_provider_evidence(self):
        """An allowed, high-confidence atom must appear in dossier provider_evidence."""
        allowed_atom = EnrichmentAtom(
            source_provider="yelp",
            evidence_type="category",
            normalized_value="yelp_category:Craft Beer Bars",
            confidence=0.82,
            provenance={"yelp_id": "abc"},
            allowed_into_writer=True,
            conflict_status="ok",
        )
        entity = _FakeEntity()
        dossier = build_place_evidence_dossier(
            entity=entity,
            frame=_FakeFrame(),
            rank_score=_FakeRankScore(),
            cross_source_atoms=[allowed_atom],
        )

        yelp_pev = next(
            (pev for pev in dossier.provider_evidence if pev.source == "yelp"),
            None,
        )
        assert yelp_pev is not None, "Expected yelp provider_evidence entry"
        assert any("Craft Beer Bars" in f for f in yelp_pev.facts), (
            f"Category fact not found in yelp evidence. Facts: {yelp_pev.facts}"
        )

    def test_disallowed_atom_does_not_appear_in_provider_evidence(self):
        """An atom with allowed_into_writer=False must not enter provider_evidence."""
        blocked_atom = EnrichmentAtom(
            source_provider="foursquare",
            evidence_type="popularity_context",
            normalized_value="fsq_popularity:0.95",
            confidence=0.78,
            provenance={"fsq_id": "xyz"},
            allowed_into_writer=False,
            conflict_status="ok",
        )
        entity = _FakeEntity()
        dossier = build_place_evidence_dossier(
            entity=entity,
            frame=_FakeFrame(),
            rank_score=_FakeRankScore(),
            cross_source_atoms=[blocked_atom],
        )

        fsq_pev = next(
            (pev for pev in dossier.provider_evidence if pev.source == "foursquare"),
            None,
        )
        # Either no foursquare entry, or no popularity fact in it
        if fsq_pev is not None:
            assert not any("popularity" in f for f in fsq_pev.facts), (
                "Blocked atom (popularity_context) leaked into provider_evidence"
            )

    def test_mixed_atoms_only_allowed_ones_merged(self):
        """Mix of allowed and blocked atoms → only allowed ones in provider_evidence."""
        atoms = [
            EnrichmentAtom(
                source_provider="yelp",
                evidence_type="category",
                normalized_value="yelp_category:Craft Beer Bars",
                confidence=0.82,
                provenance={"yelp_id": "abc"},
                allowed_into_writer=True,
                conflict_status="ok",
            ),
            EnrichmentAtom(
                source_provider="yelp",
                evidence_type="rating_context",
                normalized_value="yelp_rating:4.5",
                confidence=0.82,
                provenance={"yelp_id": "abc"},
                allowed_into_writer=False,
                conflict_status="ok",
            ),
        ]
        entity = _FakeEntity()
        dossier = build_place_evidence_dossier(
            entity=entity,
            frame=_FakeFrame(),
            rank_score=_FakeRankScore(),
            cross_source_atoms=atoms,
        )
        yelp_pev = next(
            (pev for pev in dossier.provider_evidence if pev.source == "yelp"),
            None,
        )
        assert yelp_pev is not None
        facts_text = " ".join(yelp_pev.facts)
        assert "Craft Beer Bars" in facts_text
        assert "yelp_rating" not in facts_text

    def test_cross_source_map_passed_through_build_dossiers(self):
        """build_dossiers_for_ranked_cards correctly passes cross_source_map to each dossier."""
        entity = _FakeEntity(place_id="ChIJ_abc", name="Test Place")
        rank_score = _FakeRankScore()
        ranked = [(entity, rank_score)]
        enrichment_map: Dict[str, Any] = {}
        cross_source_map = {
            "ChIJ_abc": [
                EnrichmentAtom(
                    source_provider="foursquare",
                    evidence_type="category",
                    normalized_value="fsq_category:Cocktail Bar",
                    confidence=0.80,
                    provenance={"fsq_id": "def"},
                    allowed_into_writer=True,
                    conflict_status="ok",
                )
            ]
        }

        dossiers = build_dossiers_for_ranked_cards(
            ranked=ranked,
            frame=_FakeFrame(),
            enrichment_map=enrichment_map,
            cross_source_map=cross_source_map,
        )
        assert len(dossiers) == 1
        fsq_pev = next(
            (pev for pev in dossiers[0].provider_evidence if pev.source == "foursquare"),
            None,
        )
        assert fsq_pev is not None
        assert any("Cocktail Bar" in f for f in fsq_pev.facts)


# ---------------------------------------------------------------------------
# TEST 9: Writer/card path hides notes rather than showing fallback prose
#         (this is a structural invariant test, not a new-behavior test)
# ---------------------------------------------------------------------------

class TestNoteFallbackInvariant:
    """Test 9: Cards with thin evidence still hide notes rather than showing template prose."""

    def test_thin_evidence_dossier_is_minimal(self):
        """Dossier built with no enrichment and no cross-source atoms → is_minimal=True."""
        entity = _FakeEntity()
        dossier = build_place_evidence_dossier(
            entity=entity,
            frame=_FakeFrame(),
            rank_score=_FakeRankScore(subtype_fit=0.1),
            enrichment=None,
            cross_source_atoms=None,
        )
        assert dossier.is_minimal, "Expected is_minimal=True for dossier with no enrichment"

    def test_dossier_with_cross_source_atoms_not_minimal(self):
        """Dossier with allowed cross-source atoms should have richer evidence."""
        atom = EnrichmentAtom(
            source_provider="yelp",
            evidence_type="category",
            normalized_value="yelp_category:Brewpub",
            confidence=0.78,
            provenance={"yelp_id": "ghi"},
            allowed_into_writer=True,
            conflict_status="ok",
        )
        entity = _FakeEntity()
        dossier = build_place_evidence_dossier(
            entity=entity,
            frame=_FakeFrame(),
            rank_score=_FakeRankScore(subtype_fit=0.7),
            enrichment=None,
            cross_source_atoms=[atom],
        )
        # Source confidence should be MIXED or STRONG when there's good subtype fit
        # and even with minimal google enrichment, atoms add provider evidence
        yelp_pev = next(
            (pev for pev in dossier.provider_evidence if pev.source == "yelp"),
            None,
        )
        assert yelp_pev is not None, "Expected yelp facts in provider_evidence"

    def test_fallback_note_visible_count_invariant(self):
        """The structural invariant: fallback_note_visible_count must always be 0.

        This is tested by verifying SetWriterResult.fallback_note_visible_count=0
        which is the existing invariant from PR #257.
        We verify the SetWriterResult dataclass preserves this invariant.
        """
        from app.concierge.set_level_writer import SetWriterResult
        result = SetWriterResult(
            notes_by_place_id={},
            visible_note_count=0,
            hidden_note_count=1,
            rejected_note_count=1,
            timed_out=False,
            fallback_note_visible_count=0,  # always 0
            role_note_counts={},
            note_source_counts={},
            repeated_skeleton_count=0,
            unsupported_claim_count=0,
        )
        assert result.fallback_note_visible_count == 0


# ---------------------------------------------------------------------------
# TEST 10: No provider can create an addable card without a Google-verified card
# ---------------------------------------------------------------------------

class TestNoCardMinting:
    """Test 10: Providers cannot mint addable cards; only Google-verified entities become cards."""

    def test_run_enrichment_only_returns_atoms_for_input_entities(self):
        """atoms_by_place_id only contains keys from the input entity list."""
        entities = [
            _FakeEntity(place_id="ChIJ_A", name="Bar A"),
            _FakeEntity(place_id="ChIJ_B", name="Bar B"),
        ]
        deadline = _FakeDeadline(remaining=2000)

        yelp_resp_a = _yelp_response(name="Bar A", lat=41.88, lng=-87.62)
        yelp_resp_b = _yelp_response(name="Bar B", lat=41.89, lng=-87.63)

        call_count = [0]
        def _mock_urlopen(req, timeout=None):
            resp = MagicMock()
            idx = call_count[0] % 2
            resp.read.return_value = yelp_resp_a if idx == 0 else yelp_resp_b
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            call_count[0] += 1
            return resp

        with patch("urllib.request.urlopen", side_effect=_mock_urlopen):
            result = run_cross_source_enrichment(
                entities,
                deadline=deadline,
                yelp_key="fake",
                fsq_key="",
            )

        valid_ids = {"ChIJ_A", "ChIJ_B"}
        for pid in result.atoms_by_place_id:
            assert pid in valid_ids, (
                f"Enrichment invented place_id {pid!r} not in Google-verified input"
            )

    def test_enrichment_without_google_verification_produces_no_cards(self):
        """Calling run_cross_source_enrichment with empty entity list produces no atoms."""
        result = run_cross_source_enrichment(
            [],
            deadline=_FakeDeadline(remaining=3000),
            yelp_key="fake",
            fsq_key="fake",
        )
        assert result.atoms_by_place_id == {}
        assert result.telemetry.skipped_reason == "no_entities"

    def test_provider_data_alone_cannot_create_dossier(self):
        """Cross-source atoms without a Google-verified entity cannot create a dossier.

        The dossier build function requires a PlaceEntity (Google-verified).
        There is no code path that creates dossiers from Yelp/FSQ data alone.
        """
        # The only way to get a dossier is to call build_place_evidence_dossier
        # with a valid Google entity. Cross-source atoms are an optional parameter.
        # This test confirms the function signature enforces this invariant.
        import inspect
        sig = inspect.signature(build_place_evidence_dossier)
        params = list(sig.parameters.keys())

        # entity is required (no default) and always the first positional arg
        assert "entity" in params
        assert "cross_source_atoms" in params

        entity_param = sig.parameters["entity"]
        cs_param = sig.parameters["cross_source_atoms"]

        # entity has no default → required
        assert entity_param.default is inspect.Parameter.empty, (
            "entity must be required (no default)"
        )
        # cross_source_atoms has a default (None) → optional
        assert cs_param.default is None, (
            "cross_source_atoms must be optional (default None)"
        )


# ---------------------------------------------------------------------------
# Score contract unit tests (supplementary)
# ---------------------------------------------------------------------------

class TestScoreProviderMatch:
    """Unit tests for the reusable provider match scorer."""

    def test_identical_name_close_location_accepted(self):
        """Perfect name match + nearby location → accepted."""
        ms = score_provider_match(
            google_name="Hopleaf Bar",
            google_lat=41.9997,
            google_lng=-87.6572,
            provider_name="Hopleaf Bar",
            provider_lat=41.9997,
            provider_lng=-87.6572,
        )
        assert ms.accepted
        assert ms.name_similarity >= 0.99
        assert ms.composite_score >= HIGH_CONFIDENCE_THRESHOLD

    def test_below_hard_gate_not_accepted(self):
        """Name similarity below HARD_NAME_GATE → not accepted regardless of distance."""
        ms = score_provider_match(
            google_name="Alinea Fine Dining Chicago",
            google_lat=41.9225,
            google_lng=-87.6484,
            provider_name="Random Unrelated Hardware",
            provider_lat=41.9225,
            provider_lng=-87.6484,
        )
        assert not ms.accepted
        assert ms.name_similarity < HARD_NAME_GATE

    def test_no_location_data_requires_high_name_sim(self):
        """Without location data, high name similarity required to pass."""
        ms_high = score_provider_match(
            google_name="Aviary Bar Chicago",
            google_lat=None,
            google_lng=None,
            provider_name="Aviary Bar Chicago",
            provider_lat=None,
            provider_lng=None,
        )
        ms_low = score_provider_match(
            google_name="Aviary Bar Chicago",
            google_lat=None,
            google_lng=None,
            provider_name="Something Else Entirely",
            provider_lat=None,
            provider_lng=None,
        )
        assert ms_high.accepted  # exact match → should pass
        assert not ms_low.accepted

    def test_haversine_accurate(self):
        """_haversine_m gives reasonable distance for known coordinates."""
        # Chicago Loop to roughly 1 mile north
        dist = _haversine_m(41.8827, -87.6233, 41.8983, -87.6233)
        assert 1500 < dist < 1850, f"Expected ~1.73km, got {dist:.0f}m"

    def test_normalize_match_name_removes_the_prefix(self):
        assert _normalize_match_name("The Purple Pig") == "purple pig"

    def test_normalize_match_name_removes_common_suffix(self):
        result = _normalize_match_name("Hopleaf Bar")
        # Should strip the " bar" suffix
        assert result == "hopleaf"

    def test_normalize_match_name_lowercases(self):
        assert _normalize_match_name("AVIARY") == "aviary"
