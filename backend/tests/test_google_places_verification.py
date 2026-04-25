"""Regression tests for the Google Places verification gate.

These tests cover the cases listed in the feature request:

- The Violet Hour with Google ``businessStatus == CLOSED_PERMANENTLY`` must
  not appear as an addable restaurant.
- The Violet Hour from a June 2025 article must become research_source only
  or be omitted when Google says it's closed.
- A valid operational venue (Kumiko, The Aviary) appears as addable when
  Google returns OPERATIONAL with a high/medium confidence match.
- No Google match means research_source only — never addable.
- Tavily/Serper/Brave alone never shows LIVE / Operational.
- Clear chat invalidates the Google verification cache.

The tests use a stub HTTP client so they never reach a real Google endpoint.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

# Allow imports from backend/app without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.models.concierge import (
    INTENT_NIGHTLIFE,
    INTENT_RESTAURANTS,
    SOURCE_LIVE_SEARCH,
)
from app.services.google_places import (
    CLOSED_PERMANENTLY,
    CLOSED_TEMPORARILY,
    OPERATIONAL,
    GooglePlacesService,
    GooglePlaceVerification,
    _GooglePlaceVerificationCache,
    _normalize_name,
    is_addable,
    reset_global_place_cache,
)
from app.services.live_research import (
    LiveResearchService,
    LiveSearchHit,
    StubLiveSearchProvider,
    _TTLCache,
    reset_global_cache,
)


# ── Stub HTTP client for the Google Places service ──────────────────────────


class _StubHTTPClient:
    """Drop-in replacement for the real ``_GooglePlacesHTTPClient``.

    ``responses`` is keyed by a *normalized candidate name* (lowercased,
    punctuation-stripped) so the stub can return different fixtures for
    different candidates inside a single ``verify_many`` call.
    """

    def __init__(
        self,
        responses: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        *,
        available: bool = True,
    ) -> None:
        self.available = available
        self._responses = {k.lower(): v for k, v in (responses or {}).items()}
        self.calls: List[str] = []

    def text_search(self, query: str) -> List[Dict[str, Any]]:
        self.calls.append(query)
        low = query.lower()
        for key, payload in self._responses.items():
            if key in low:
                return payload
        return []


def _operational_place(
    *,
    name: str,
    place_id: str,
    address: str,
    types: Optional[List[str]] = None,
    business_status: str = OPERATIONAL,
) -> Dict[str, Any]:
    return {
        "id": place_id,
        "displayName": {"text": name},
        "formattedAddress": address,
        "location": {"latitude": 41.8, "longitude": -87.6},
        "businessStatus": business_status,
        "types": types or ["restaurant", "bar", "establishment"],
        "rating": 4.6,
        "userRatingCount": 1234,
        "googleMapsUri": f"https://maps.google.com/?cid={place_id}",
        "websiteUri": f"https://example.com/{place_id}",
    }


# ── GooglePlacesService unit tests ──────────────────────────────────────────


class TestGooglePlacesServiceNormalization:
    def setup_method(self):
        reset_global_place_cache()

    def test_returns_unknown_when_provider_unavailable(self):
        client = _StubHTTPClient(available=False)
        svc = GooglePlacesService(client=client, cache=_GooglePlaceVerificationCache(0))
        result = svc.verify("Kumiko", "Chicago")
        assert result.matched is False
        assert result.confidence == "unknown"
        assert result.failure_reason == "provider_unavailable"
        assert is_addable(result) is False

    def test_no_match_marks_research_source_only(self):
        client = _StubHTTPClient(responses={"kumiko": []})
        svc = GooglePlacesService(client=client, cache=_GooglePlaceVerificationCache(0))
        result = svc.verify("Kumiko", "Chicago")
        assert result.matched is False
        assert result.failure_reason == "no_match"
        assert is_addable(result) is False

    def test_operational_match_with_address_evidence_is_addable(self):
        place = _operational_place(
            name="Kumiko",
            place_id="ChIJ-kumiko",
            address="630 W Lake St, Chicago, IL 60661, USA",
        )
        client = _StubHTTPClient(responses={"kumiko": [place]})
        svc = GooglePlacesService(client=client, cache=_GooglePlaceVerificationCache(0))
        result = svc.verify("Kumiko", "Chicago", neighborhood="West Loop")
        assert result.matched is True
        assert result.business_status == OPERATIONAL
        assert result.confidence in {"high", "medium"}
        assert is_addable(result) is True
        assert result.formatted_address.startswith("630 W Lake St")
        assert result.google_maps_uri
        assert result.types

    def test_closed_permanently_excluded_from_addable(self):
        place = _operational_place(
            name="The Violet Hour",
            place_id="ChIJ-violet",
            address="1520 N Damen Ave, Chicago, IL, USA",
            business_status=CLOSED_PERMANENTLY,
        )
        client = _StubHTTPClient(responses={"the violet hour": [place]})
        svc = GooglePlacesService(client=client, cache=_GooglePlaceVerificationCache(0))
        result = svc.verify("The Violet Hour", "Chicago", neighborhood="Wicker Park")
        assert result.matched is True
        assert result.business_status == CLOSED_PERMANENTLY
        assert is_addable(result) is False

    def test_closed_temporarily_also_excluded_from_addable(self):
        place = _operational_place(
            name="Some Bar",
            place_id="ChIJ-some",
            address="123 N Clark St, Chicago, IL, USA",
            business_status=CLOSED_TEMPORARILY,
        )
        client = _StubHTTPClient(responses={"some bar": [place]})
        svc = GooglePlacesService(client=client, cache=_GooglePlaceVerificationCache(0))
        result = svc.verify("Some Bar", "Chicago")
        assert result.business_status == CLOSED_TEMPORARILY
        assert is_addable(result) is False

    def test_weak_name_match_without_address_evidence_is_low_confidence(self):
        # Google returns a vaguely-named place that doesn't share tokens with
        # the candidate AND the address doesn't include the destination.
        place = _operational_place(
            name="Best Bars Roundup Magazine",
            place_id="ChIJ-mag",
            address="1 Editor's Way, New York, NY, USA",
            types=["news", "publisher"],
        )
        client = _StubHTTPClient(responses={"the violet hour": [place]})
        svc = GooglePlacesService(client=client, cache=_GooglePlaceVerificationCache(0))
        result = svc.verify("The Violet Hour", "Chicago")
        # Article publishers should be filtered as non-venue types.
        assert result.failure_reason == "non_venue_types"
        assert is_addable(result) is False

    def test_caches_both_match_and_no_match_results(self):
        place = _operational_place(
            name="Kumiko",
            place_id="ChIJ-kumiko",
            address="630 W Lake St, Chicago, IL, USA",
        )
        client = _StubHTTPClient(responses={"kumiko": [place]})
        svc = GooglePlacesService(client=client, cache=_GooglePlaceVerificationCache(60))
        first = svc.verify("Kumiko", "Chicago")
        second = svc.verify("Kumiko", "Chicago")
        assert first.provider_place_id == second.provider_place_id
        # Cache hit means we did not hit the stub a second time.
        assert len(client.calls) == 1

    def test_clear_cache_for_destination_drops_entries(self):
        place = _operational_place(
            name="Kumiko",
            place_id="ChIJ-kumiko",
            address="630 W Lake St, Chicago, IL, USA",
        )
        client = _StubHTTPClient(responses={"kumiko": [place]})
        cache = _GooglePlaceVerificationCache(60)
        svc = GooglePlacesService(client=client, cache=cache)
        svc.verify("Kumiko", "Chicago")
        cleared = svc.clear_cache_for_destination("Chicago")
        assert cleared == 1
        # Next verify makes a fresh HTTP call.
        svc.verify("Kumiko", "Chicago")
        assert len(client.calls) == 2

    def test_normalize_name_strips_diacritics_and_case(self):
        assert _normalize_name("Café Olé") == "cafe ole"
        assert _normalize_name("  the   Violet   Hour ") == "the violet hour"


# ── Live research integration with the gate ─────────────────────────────────


def _hit(title: str, url: str = "https://example.com", snippet: str = "") -> LiveSearchHit:
    from datetime import datetime, timezone
    return LiveSearchHit(
        title=title,
        url=url,
        snippet=snippet,
        provider="Tavily",
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def _build_live_svc(hits: List[LiveSearchHit], place_responses: Dict[str, List[Dict[str, Any]]]) -> LiveResearchService:
    provider = StubLiveSearchProvider(hits)
    google_client = _StubHTTPClient(responses=place_responses)
    place_verifier = GooglePlacesService(
        client=google_client,
        cache=_GooglePlaceVerificationCache(0),
    )
    return LiveResearchService(
        provider=provider,
        cache=_TTLCache(0),
        verification_cache=_TTLCache(0),
        place_verifier=place_verifier,
        enabled=True,
    )


class TestLiveResearchGooglePlacesGate:
    def setup_method(self):
        reset_global_cache()
        reset_global_place_cache()

    def test_violet_hour_closed_permanently_never_addable(self):
        article = _hit(
            "Best Cocktail Bars in Chicago",
            "https://example.com/best-bars",
            "1. The Violet Hour — Wicker Park speakeasy bar in Chicago.",
        )
        google_responses = {
            "the violet hour": [
                _operational_place(
                    name="The Violet Hour",
                    place_id="ChIJ-violet",
                    address="1520 N Damen Ave, Chicago, IL, USA",
                    business_status=CLOSED_PERMANENTLY,
                )
            ]
        }
        svc = _build_live_svc([article], google_responses)
        result = svc.fetch(
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="cocktail bars",
        )
        names = [r.name for r in result.restaurants]
        assert "The Violet Hour" not in names
        # No addable card carries an OPERATIONAL Google verification stamp
        # for The Violet Hour — closure must always win.
        for r in result.restaurants:
            if (r.name or "").lower() == "the violet hour":
                assert (
                    r.google_verification is None
                    or r.google_verification.business_status != OPERATIONAL
                )

    def test_violet_hour_from_june_2025_article_demoted_when_google_closed(self):
        article = _hit(
            "Chicago Nightlife — June 2025",
            "https://example.com/chicago-nightlife-june-2025",
            "1. The Violet Hour — Wicker Park speakeasy still pulling crowds.",
        )
        google_responses = {
            "the violet hour": [
                _operational_place(
                    name="The Violet Hour",
                    place_id="ChIJ-violet",
                    address="1520 N Damen Ave, Chicago, IL, USA",
                    business_status=CLOSED_PERMANENTLY,
                )
            ]
        }
        svc = _build_live_svc([article], google_responses)
        result = svc.fetch(
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="cocktail bars",
        )
        assert all((r.name or "").lower() != "the violet hour" for r in result.restaurants)
        # Card never carries a Google verification stamp.
        for r in result.restaurants:
            gv = r.google_verification
            if gv is not None:
                assert gv.business_status == OPERATIONAL

    def test_kumiko_operational_match_appears_addable(self):
        article = _hit(
            "Best Cocktail Bars in Chicago",
            "https://example.com/best-bars",
            "1. Kumiko — West Loop speakeasy bar in Chicago.",
        )
        google_responses = {
            "kumiko": [
                _operational_place(
                    name="Kumiko",
                    place_id="ChIJ-kumiko",
                    address="630 W Lake St, Chicago, IL, USA",
                    types=["restaurant", "bar", "establishment"],
                )
            ]
        }
        svc = _build_live_svc([article], google_responses)
        result = svc.fetch(
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="cocktail bars",
        )
        kumiko = next((r for r in result.restaurants if r.name == "Kumiko"), None)
        assert kumiko is not None
        assert kumiko.verified_place is True
        assert kumiko.google_verification is not None
        assert kumiko.google_verification.business_status == OPERATIONAL
        assert kumiko.google_verification.provider_place_id == "ChIJ-kumiko"
        assert kumiko.google_verification.confidence in {"high", "medium"}
        assert result.source_status == SOURCE_LIVE_SEARCH

    def test_aviary_operational_match_appears_addable(self):
        article = _hit(
            "Best Bars in Chicago",
            "https://example.com/best-bars",
            "1. The Aviary — avant-garde cocktail destination in West Loop, Chicago.",
        )
        google_responses = {
            "the aviary": [
                _operational_place(
                    name="The Aviary",
                    place_id="ChIJ-aviary",
                    address="955 W Fulton Market, Chicago, IL, USA",
                    types=["bar", "restaurant", "establishment"],
                )
            ]
        }
        svc = _build_live_svc([article], google_responses)
        result = svc.fetch(
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="cocktail bars",
        )
        names = [r.name for r in result.restaurants]
        assert "The Aviary" in names

    def test_no_google_match_demotes_to_research_source(self):
        article = _hit(
            "Top Chicago Bars",
            "https://example.com/top-bars",
            "1. Meadowlark — Logan Square cocktail bar in Chicago.",
        )
        # Google returns nothing for this name.
        svc = _build_live_svc([article], {"meadowlark": []})
        result = svc.fetch(
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="cocktail bars",
        )
        assert all(r.name != "Meadowlark" for r in result.restaurants)
        # Research_sources keeps the article so the user still sees research
        # context, but it is not addable.
        assert all(s.trip_addable is False for s in result.research_sources)

    def test_tavily_direct_hit_alone_is_not_addable_without_google(self):
        # Direct venue_place hit (Tavily-style) — without a Google match, the
        # gate strips it from restaurants and demotes to research_sources.
        direct = _hit(
            "Gus' Sip & Dip",
            "https://example.com/gus",
            "Cocktail bar at 123 N Clark St in River North, Chicago.",
        )
        svc = _build_live_svc([direct], {"gus' sip & dip": []})
        result = svc.fetch(
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="cocktail bars",
        )
        assert result.restaurants == []
        # Should still appear as research source for context.
        assert result.research_sources

    def test_tavily_hit_only_becomes_addable_after_google_operational(self):
        direct = _hit(
            "Kumiko",
            "https://example.com/kumiko",
            "Cocktail bar in West Loop, Chicago.",
        )
        google_responses = {
            "kumiko": [
                _operational_place(
                    name="Kumiko",
                    place_id="ChIJ-kumiko",
                    address="630 W Lake St, Chicago, IL, USA",
                )
            ]
        }
        svc = _build_live_svc([direct], google_responses)
        result = svc.fetch(
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="cocktail bars",
        )
        names = [r.name for r in result.restaurants]
        assert "Kumiko" in names
        kumiko = next(r for r in result.restaurants if r.name == "Kumiko")
        assert kumiko.google_verification is not None
        assert kumiko.google_verification.business_status == OPERATIONAL

    def test_low_confidence_match_kept_as_research_only(self):
        article = _hit(
            "Best Bars in Chicago",
            "https://example.com/best-bars",
            "1. Generic Spot — cocktail bar in Chicago.",
        )
        # Google returns a place with a name that barely shares tokens AND
        # without the destination in the address — should fall through the
        # confidence gate.
        google_responses = {
            "generic spot": [
                _operational_place(
                    name="Totally Different Place",
                    place_id="ChIJ-different",
                    address="Some Street, Brooklyn, NY, USA",
                    types=["restaurant", "establishment"],
                )
            ]
        }
        svc = _build_live_svc([article], google_responses)
        result = svc.fetch(
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="cocktail bars",
        )
        assert all(r.name != "Generic Spot" for r in result.restaurants)


class TestClearChatInvalidatesGoogleCache:
    def setup_method(self):
        reset_global_cache()
        reset_global_place_cache()

    def test_clear_cache_for_context_drops_google_verifications(self):
        place = _operational_place(
            name="Kumiko",
            place_id="ChIJ-kumiko",
            address="630 W Lake St, Chicago, IL, USA",
        )
        google_client = _StubHTTPClient(responses={"kumiko": [place]})
        place_verifier = GooglePlacesService(
            client=google_client,
            cache=_GooglePlaceVerificationCache(60),
        )
        provider = StubLiveSearchProvider(
            [
                _hit(
                    "Best Bars Chicago",
                    "https://example.com/best-bars",
                    "1. Kumiko — West Loop speakeasy bar in Chicago.",
                )
            ]
        )
        svc = LiveResearchService(
            provider=provider,
            cache=_TTLCache(60),
            verification_cache=_TTLCache(60),
            place_verifier=place_verifier,
            enabled=True,
        )

        first = svc.fetch(
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="bars",
        )
        assert any(r.name == "Kumiko" for r in first.restaurants)
        google_calls_after_first = len(google_client.calls)
        assert google_calls_after_first >= 1

        svc.clear_cache_for_context("Chicago")

        second = svc.fetch(
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="bars",
        )
        assert any(r.name == "Kumiko" for r in second.restaurants)
        # After clearing, the Google client must have been hit again — proving
        # the verification cache was invalidated.
        assert len(google_client.calls) > google_calls_after_first


# ── Frontend assertions ──────────────────────────────────────────────────────


class TestFrontendBadgeCopy:
    """Static checks on the AIConciergePanel — Tavily must never show LIVE /
    Operational and the badge label must read 'Google verified'.
    """

    def _read_panel(self) -> str:
        root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        panel_path = os.path.join(root, "frontend", "src", "components", "trips", "AIConciergePanel.tsx")
        with open(panel_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_badge_label_is_google_verified(self):
        src = self._read_panel()
        assert "Google verified" in src

    def test_legacy_live_badge_label_removed(self):
        src = self._read_panel()
        # The literal user-facing badge string ">Live<" must be gone.
        assert ">Live<" not in src

    def test_no_verified_today_freshness_string(self):
        src = self._read_panel()
        # Tavily freshness must say only "source checked" — never user-facing
        # "verified today" / "verified now" string literals.
        for forbidden in ('"verified today"', "'verified today'", '"verified now"', "'verified now'"):
            assert forbidden not in src

    def test_operational_badge_gated_on_google_verification(self):
        src = self._read_panel()
        assert "canShowGoogleVerifiedBadge" in src
        # Gate must require the Google match + OPERATIONAL.
        assert "OPERATIONAL" in src
