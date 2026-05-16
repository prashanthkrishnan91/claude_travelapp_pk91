"""Tests: Global ALLOW_LIVE_RESEARCH_CALLS kill switch for semantic_retrieval_v1.

Follow-up to PR #396. Production used ALLOW_LIVE_RESEARCH_CALLS=false but
editorial enrichment still attempted Tavily calls because Step 5.56 did not
check the kill switch before entering the editorial path.

Coverage:
A. Kill switch inactive (env var absent): editorial skipped for all 5 required queries.
B. Kill switch skips: editorial_skipped_reason=allow_live_research_calls_false in telemetry log.
C. Kill switch skips: tavily_attempted=0 / serper_attempted=0 in telemetry log.
D. Google Places fanout (execute_fanout) still runs when kill switch is active.
E. run_editorial_enrichment is never called when kill switch is active.
F. Kill switch true (env=1): existing selectivity/natural-feature skip still works.
G. Config mapping: ALLOW_LIVE_RESEARCH_CALLS=false -> settings.allow_live_research_calls=False.
   ALLOW_LIVE_RESEARCH_CALLS not set -> settings.allow_live_research_calls=True (default).
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_raw_place(
    *,
    name: str,
    place_id: str,
    types: List[str],
    maps_uri: str,
    rating: float = 4.3,
    review_count: int = 400,
    primary_type: Optional[str] = None,
    lat: float = 47.60,
    lng: float = -122.33,
) -> Dict[str, Any]:
    return {
        "id": place_id,
        "displayName": {"text": name},
        "types": types,
        "primaryType": primary_type or types[0],
        "formattedAddress": "Test City, WA 98101",
        "rating": rating,
        "userRatingCount": review_count,
        "businessStatus": "OPERATIONAL",
        "googleMapsUri": maps_uri,
        "websiteUri": None,
        "priceLevel": "PRICE_LEVEL_MODERATE",
        "location": {"latitude": lat, "longitude": lng},
    }


def _bar_places() -> List[Dict[str, Any]]:
    return [
        _make_raw_place(
            name="Tavern Hall Sports Bar",
            place_id="ChIJ_sports1",
            types=["bar", "food", "restaurant"],
            maps_uri="https://maps.google.com/?cid=801",
            rating=4.4, review_count=600,
        ),
        _make_raw_place(
            name="Big Screen Sports Lounge",
            place_id="ChIJ_sports2",
            types=["bar", "night_club"],
            maps_uri="https://maps.google.com/?cid=802",
            rating=4.2, review_count=450,
        ),
        _make_raw_place(
            name="The Field Sports Bar",
            place_id="ChIJ_sports3",
            types=["bar", "food"],
            maps_uri="https://maps.google.com/?cid=803",
            rating=4.1, review_count=300,
        ),
    ]


def _cocktail_places() -> List[Dict[str, Any]]:
    return [
        _make_raw_place(
            name="Pike Place Cocktail Room",
            place_id="ChIJ_cock1",
            types=["cocktail_bar", "bar"],
            maps_uri="https://maps.google.com/?cid=901",
            rating=4.6, review_count=800,
        ),
        _make_raw_place(
            name="The Market Bar",
            place_id="ChIJ_cock2",
            types=["bar", "food"],
            maps_uri="https://maps.google.com/?cid=902",
            rating=4.3, review_count=350,
        ),
    ]


def _attraction_places() -> List[Dict[str, Any]]:
    return [
        _make_raw_place(
            name="Space Needle",
            place_id="ChIJ_space1",
            types=["tourist_attraction", "point_of_interest"],
            maps_uri="https://maps.google.com/?cid=701",
            rating=4.7, review_count=5000,
        ),
        _make_raw_place(
            name="Pike Place Market",
            place_id="ChIJ_pike1",
            types=["tourist_attraction", "food_market"],
            maps_uri="https://maps.google.com/?cid=702",
            rating=4.6, review_count=3000,
        ),
        _make_raw_place(
            name="Chihuly Garden and Glass",
            place_id="ChIJ_chi1",
            types=["tourist_attraction", "museum"],
            maps_uri="https://maps.google.com/?cid=703",
            rating=4.8, review_count=2500,
        ),
    ]


def _beach_places() -> List[Dict[str, Any]]:
    return [
        _make_raw_place(
            name="South Beach Miami",
            place_id="ChIJ_beach1",
            types=["beach", "natural_feature", "park"],
            maps_uri="https://maps.google.com/?cid=601",
            rating=4.5, review_count=4000,
        ),
        _make_raw_place(
            name="Crandon Park Beach",
            place_id="ChIJ_beach2",
            types=["beach", "park", "public_beach"],
            maps_uri="https://maps.google.com/?cid=602",
            rating=4.4, review_count=1200,
        ),
    ]


def _viewpoint_places() -> List[Dict[str, Any]]:
    return [
        _make_raw_place(
            name="Trocadéro Gardens Viewpoint",
            place_id="ChIJ_view1",
            types=["scenic_viewpoint", "tourist_attraction", "viewpoint"],
            maps_uri="https://maps.google.com/?cid=501",
            rating=4.7, review_count=3000,
        ),
        _make_raw_place(
            name="Pont d'Iéna Terrace",
            place_id="ChIJ_view2",
            types=["scenic_viewpoint", "viewpoint", "natural_feature"],
            maps_uri="https://maps.google.com/?cid=502",
            rating=4.5, review_count=1800,
        ),
    ]


def _mock_fanout(places: List[Dict[str, Any]]):
    """Return a side_effect for execute_fanout that yields one ProviderQueryResult per query."""
    from app.concierge.provider_executor import ProviderQueryResult

    def _execute(queries, api_key, timeout=5.0, hard_cap=4, max_results_per_query=15, **kwargs):
        return [
            ProviderQueryResult(query=q, places=places[:], latency_ms=60)
            for q in queries
        ]

    return _execute


def _all_validated_reasons(cards_data, frame, **kwargs):
    """Mock for build_reasons_with_retry: validates every card."""
    from app.concierge.batched_reason_builder import (
        CardReason, ReasoningResultV2, SOURCE_PRIMARY, _PRIMARY_MODEL,
    )
    n = len(cards_data)
    reasons = {
        str(i + 1): CardReason(
            note="A respected establishment with consistent quality.",
            source=SOURCE_PRIMARY,
            validated=True,
            attempt_count=1,
            model_used=_PRIMARY_MODEL,
        )
        for i in range(n)
    }
    result = ReasoningResultV2(
        attempted=True,
        success=True,
        accepted_count=n,
        final_card_count=n,
        deterministic_visible_count=0,
        final_note_omitted_count=0,
        model=_PRIMARY_MODEL,
        visible_note_source_counts={SOURCE_PRIMARY: n},
    )
    return reasons, result


_MOCK_VALID_REASONS = patch(
    "app.concierge.batched_reason_builder.build_reasons_with_retry",
    side_effect=_all_validated_reasons,
)

# ── Kill-switch-off tests (A/B/C/D/E) ─────────────────────────────────────────


class TestKillSwitchOff:
    """ALLOW_LIVE_RESEARCH_CALLS not set → kill switch active → no editorial calls."""

    def _run_with_kill_switch_off(
        self,
        *,
        user_query: str,
        destination: str,
        places: List[Dict[str, Any]],
        vertical: str = "restaurants",
        monkeypatch,
        caplog,
    ):
        """Helper: run pipeline with kill switch off, return (result, fanout_call_count)."""
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1

        monkeypatch.delenv("ALLOW_LIVE_RESEARCH_CALLS", raising=False)

        fanout_mock = MagicMock(side_effect=_mock_fanout(places))
        editorial_mock = MagicMock(name="run_editorial_enrichment_should_not_be_called")

        with (
            _MOCK_VALID_REASONS,
            patch("app.concierge.provider_executor.execute_fanout", fanout_mock),
            patch("app.concierge.editorial_enrichment.run_editorial_enrichment", editorial_mock),
            caplog.at_level(logging.INFO, logger="app.concierge.semantic_retrieval"),
        ):
            result = run_semantic_retrieval_v1(
                user_query=user_query,
                destination=destination,
                api_key="fake_google_key",
                vertical=vertical,
            )

        return result, fanout_mock, editorial_mock

    def test_kill_switch_best_beaches_miami(self, monkeypatch, caplog):
        """Kill switch off: 'best beaches in Miami' editorial skipped, reason=allow_live_research_calls_false."""
        result, fanout_mock, editorial_mock = self._run_with_kill_switch_off(
            user_query="best beaches in Miami",
            destination="Miami",
            places=_beach_places(),
            vertical="attractions",
            monkeypatch=monkeypatch,
            caplog=caplog,
        )

        # Editorial enrichment never called
        assert editorial_mock.call_count == 0, (
            f"run_editorial_enrichment must not be called when ALLOW_LIVE_RESEARCH_CALLS is absent; "
            f"was called {editorial_mock.call_count} times"
        )
        # Google Places fanout still ran
        assert fanout_mock.call_count > 0, "execute_fanout (Google Places) must still run"
        # Kill switch log present
        assert "editorial_skipped_reason=allow_live_research_calls_false" in caplog.text, (
            "Expected editorial_skipped_reason=allow_live_research_calls_false in log"
        )
        assert "tavily_attempted=0" in caplog.text
        assert "serper_attempted=0" in caplog.text

    def test_kill_switch_sunset_points_eiffel_tower(self, monkeypatch, caplog):
        """Kill switch off: 'sunset points with Eiffel tower view' editorial skipped."""
        result, fanout_mock, editorial_mock = self._run_with_kill_switch_off(
            user_query="sunset points with Eiffel tower view",
            destination="Paris",
            places=_viewpoint_places(),
            vertical="attractions",
            monkeypatch=monkeypatch,
            caplog=caplog,
        )

        assert editorial_mock.call_count == 0, (
            "run_editorial_enrichment must not be called when kill switch is active"
        )
        assert fanout_mock.call_count > 0, "Google Places fanout must still run"
        assert "editorial_skipped_reason=allow_live_research_calls_false" in caplog.text

    def test_kill_switch_sports_bars_seattle(self, monkeypatch, caplog):
        """Kill switch off: 'sports bars in Seattle' editorial skipped."""
        result, fanout_mock, editorial_mock = self._run_with_kill_switch_off(
            user_query="sports bars in Seattle",
            destination="Seattle",
            places=_bar_places(),
            vertical="restaurants",
            monkeypatch=monkeypatch,
            caplog=caplog,
        )

        assert editorial_mock.call_count == 0, (
            "run_editorial_enrichment must not be called for sports bars query when kill switch active"
        )
        assert fanout_mock.call_count > 0, "Google Places fanout must still run"
        assert "editorial_skipped_reason=allow_live_research_calls_false" in caplog.text
        assert "tavily_attempted=0" in caplog.text
        assert "serper_attempted=0" in caplog.text

    def test_kill_switch_cocktail_bars_pike_place(self, monkeypatch, caplog):
        """Kill switch off: 'cocktail bars near Pike Place' editorial skipped."""
        result, fanout_mock, editorial_mock = self._run_with_kill_switch_off(
            user_query="cocktail bars near Pike Place",
            destination="Seattle",
            places=_cocktail_places(),
            vertical="restaurants",
            monkeypatch=monkeypatch,
            caplog=caplog,
        )

        assert editorial_mock.call_count == 0, (
            "run_editorial_enrichment must not be called for cocktail bars query when kill switch active"
        )
        assert fanout_mock.call_count > 0, "Google Places fanout must still run"
        assert "editorial_skipped_reason=allow_live_research_calls_false" in caplog.text

    def test_kill_switch_top_attractions_seattle(self, monkeypatch, caplog):
        """Kill switch off: 'top attractions in Seattle' editorial skipped.

        This is the critical case: 'top attractions' triggers qualitative_ranking_intent
        in should_run_editorial so editorial WOULD be attempted when the kill switch
        is active. The kill switch must fire first.
        """
        result, fanout_mock, editorial_mock = self._run_with_kill_switch_off(
            user_query="top attractions in Seattle",
            destination="Seattle",
            places=_attraction_places(),
            vertical="attractions",
            monkeypatch=monkeypatch,
            caplog=caplog,
        )

        assert editorial_mock.call_count == 0, (
            "'top attractions' normally triggers editorial (qualitative_ranking_intent); "
            "kill switch must block it before that gate is reached. "
            f"editorial was called {editorial_mock.call_count} times"
        )
        assert fanout_mock.call_count > 0, "Google Places fanout must still run"
        assert "editorial_skipped_reason=allow_live_research_calls_false" in caplog.text
        assert "tavily_attempted=0" in caplog.text
        assert "serper_attempted=0" in caplog.text
        assert "brave_attempted=0" in caplog.text

    def test_kill_switch_false_value_blocks_editorial(self, monkeypatch, caplog):
        """ALLOW_LIVE_RESEARCH_CALLS=false (explicit) blocks editorial."""
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1

        monkeypatch.setenv("ALLOW_LIVE_RESEARCH_CALLS", "false")

        editorial_mock = MagicMock(name="should_not_be_called")
        with (
            _MOCK_VALID_REASONS,
            patch("app.concierge.provider_executor.execute_fanout", side_effect=_mock_fanout(_bar_places())),
            patch("app.concierge.editorial_enrichment.run_editorial_enrichment", editorial_mock),
            caplog.at_level(logging.INFO, logger="app.concierge.semantic_retrieval"),
        ):
            run_semantic_retrieval_v1(
                user_query="sports bars in Seattle",
                destination="Seattle",
                api_key="fake_key",
            )

        assert editorial_mock.call_count == 0
        assert "editorial_skipped_reason=allow_live_research_calls_false" in caplog.text

    def test_kill_switch_zero_value_blocks_editorial(self, monkeypatch, caplog):
        """ALLOW_LIVE_RESEARCH_CALLS=0 blocks editorial."""
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1

        monkeypatch.setenv("ALLOW_LIVE_RESEARCH_CALLS", "0")

        editorial_mock = MagicMock(name="should_not_be_called")
        with (
            _MOCK_VALID_REASONS,
            patch("app.concierge.provider_executor.execute_fanout", side_effect=_mock_fanout(_cocktail_places())),
            patch("app.concierge.editorial_enrichment.run_editorial_enrichment", editorial_mock),
            caplog.at_level(logging.INFO, logger="app.concierge.semantic_retrieval"),
        ):
            run_semantic_retrieval_v1(
                user_query="cocktail bars near Pike Place",
                destination="Seattle",
                api_key="fake_key",
            )

        assert editorial_mock.call_count == 0
        assert "editorial_skipped_reason=allow_live_research_calls_false" in caplog.text


# ── Kill-switch-on tests (F) ───────────────────────────────────────────────────


class TestKillSwitchOn:
    """ALLOW_LIVE_RESEARCH_CALLS=1 → kill switch inactive → existing gating behavior preserved."""

    def test_natural_feature_beach_still_skips_editorial_via_selectivity(self, monkeypatch, caplog):
        """Kill switch ON, beach query: editorial still skipped via natural_feature_no_editorial_value (PR #396)."""
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1

        monkeypatch.setenv("ALLOW_LIVE_RESEARCH_CALLS", "1")

        editorial_mock = MagicMock(name="should_not_be_called_for_beach")
        with (
            _MOCK_VALID_REASONS,
            patch("app.concierge.provider_executor.execute_fanout", side_effect=_mock_fanout(_beach_places())),
            patch("app.concierge.editorial_enrichment.run_editorial_enrichment", editorial_mock),
            # Prevent Supabase mock from returning a truthy MagicMock as a fake cache hit,
            # which would short-circuit the selectivity gate before it can fire.
            patch("app.concierge.evidence_cache._EVIDENCE_ATOM_CACHE.get", return_value=None),
            patch("app.concierge.evidence_cache._SUPABASE_EVIDENCE_CACHE.get", return_value=None),
            caplog.at_level(logging.INFO, logger="app.concierge.semantic_retrieval"),
        ):
            run_semantic_retrieval_v1(
                user_query="best beaches in Miami",
                destination="Miami",
                api_key="fake_key",
                vertical="attractions",
            )

        # Natural-feature selectivity gate (PR #396) must still fire when kill switch is ON
        assert editorial_mock.call_count == 0, (
            "Beach queries should still skip editorial via PR #396 selectivity gate "
            "when ALLOW_LIVE_RESEARCH_CALLS=1"
        )
        # Log reason must NOT be allow_live_research_calls_false
        assert "allow_live_research_calls_false" not in caplog.text, (
            "When ALLOW_LIVE_RESEARCH_CALLS=1, kill switch log must not appear"
        )
        # PR #396 natural_feature_no_editorial_value reason must appear
        assert "natural_feature_no_editorial_value" in caplog.text, (
            "PR #396 natural-feature skip must still fire when kill switch is ON"
        )

    def test_sports_bars_skips_via_selectivity_low_editorial_value(self, monkeypatch, caplog):
        """Kill switch ON, sports bars: editorial skipped via low_editorial_value_simple_category."""
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1

        monkeypatch.setenv("ALLOW_LIVE_RESEARCH_CALLS", "1")

        editorial_mock = MagicMock(name="sports_bars_selectivity_check")
        with (
            _MOCK_VALID_REASONS,
            patch("app.concierge.provider_executor.execute_fanout", side_effect=_mock_fanout(_bar_places())),
            patch("app.concierge.editorial_enrichment.run_editorial_enrichment", editorial_mock),
            caplog.at_level(logging.INFO, logger="app.concierge.semantic_retrieval"),
        ):
            run_semantic_retrieval_v1(
                user_query="sports bars in Seattle",
                destination="Seattle",
                api_key="fake_key",
            )

        # Kill switch log must NOT appear
        assert "allow_live_research_calls_false" not in caplog.text
        # Selectivity gate fires (low editorial value for plain subtype query)
        assert editorial_mock.call_count == 0, (
            "Plain sports-bars query skips editorial via selectivity gate, not kill switch"
        )

    def test_top_attractions_attempts_editorial_when_kill_switch_on(self, monkeypatch, caplog):
        """Kill switch ON, 'top attractions': editorial IS attempted (qualitative ranking intent)."""
        from app.concierge.semantic_retrieval import run_semantic_retrieval_v1
        from app.concierge.editorial_enrichment import (
            EditorialEnrichmentResult, EditorialEnrichmentTelemetry,
        )

        monkeypatch.setenv("ALLOW_LIVE_RESEARCH_CALLS", "1")
        # Ensure Tavily key is absent so run_editorial_enrichment returns empty quickly
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("SERPER_API_KEY", raising=False)

        empty_result = EditorialEnrichmentResult(
            atoms_by_place_id={},
            telemetry=EditorialEnrichmentTelemetry(enrichment_attempted=True),
            elapsed_ms=5,
        )
        editorial_mock = MagicMock(return_value=empty_result)

        with (
            _MOCK_VALID_REASONS,
            patch("app.concierge.provider_executor.execute_fanout", side_effect=_mock_fanout(_attraction_places())),
            patch("app.concierge.editorial_enrichment.run_editorial_enrichment", editorial_mock),
            patch("app.concierge.editorial_enrichment.get_tavily_key", return_value=""),
            patch("app.concierge.editorial_enrichment.get_serper_key", return_value=""),
            # Prevent Supabase mock from returning a truthy MagicMock as a fake cache hit,
            # which would skip the editorial call entirely via the evidence cache path.
            patch("app.concierge.evidence_cache._EVIDENCE_ATOM_CACHE.get", return_value=None),
            patch("app.concierge.evidence_cache._SUPABASE_EVIDENCE_CACHE.get", return_value=None),
            caplog.at_level(logging.INFO, logger="app.concierge.semantic_retrieval"),
        ):
            run_semantic_retrieval_v1(
                user_query="top attractions in Seattle",
                destination="Seattle",
                api_key="fake_key",
                vertical="attractions",
            )

        # Kill switch must NOT fire
        assert "allow_live_research_calls_false" not in caplog.text, (
            "Kill switch must not fire when ALLOW_LIVE_RESEARCH_CALLS=1"
        )
        # Editorial IS called (qualitative ranking intent) — but with empty keys, produces nothing
        assert editorial_mock.call_count == 1, (
            "'top attractions' triggers qualitative_ranking_intent; editorial must be attempted "
            "when ALLOW_LIVE_RESEARCH_CALLS=1"
        )


# ── Config mapping tests (G) ───────────────────────────────────────────────────

def _fresh_settings_cls():
    """Load the real Settings class from config.py, bypassing conftest's sys.modules stub.

    conftest.py pre-registers app.core.config as an empty types.ModuleType so that
    get_settings() is controlled in tests. That stub has no Settings class. Loading
    config.py under a throwaway module name bypasses the stub and lets us test the
    real pydantic-settings field mapping.
    """
    import importlib.util
    import pathlib
    p = pathlib.Path(__file__).resolve().parent.parent / "app" / "core" / "config.py"
    spec = importlib.util.spec_from_file_location("_ks_real_config", str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Settings


class TestConfigMapping:
    """ALLOW_LIVE_RESEARCH_CALLS env var maps to Settings.allow_live_research_calls."""

    def test_allow_live_research_calls_false_maps_to_settings(self, monkeypatch):
        """ALLOW_LIVE_RESEARCH_CALLS=false → settings.allow_live_research_calls=False."""
        monkeypatch.setenv("ALLOW_LIVE_RESEARCH_CALLS", "false")
        Settings = _fresh_settings_cls()
        settings = Settings()
        assert settings.allow_live_research_calls is False, (
            f"Expected allow_live_research_calls=False when env=false, "
            f"got {settings.allow_live_research_calls!r}"
        )

    def test_allow_live_research_calls_true_maps_to_settings(self, monkeypatch):
        """ALLOW_LIVE_RESEARCH_CALLS=true → settings.allow_live_research_calls=True."""
        monkeypatch.setenv("ALLOW_LIVE_RESEARCH_CALLS", "true")
        Settings = _fresh_settings_cls()
        settings = Settings()
        assert settings.allow_live_research_calls is True

    def test_allow_live_research_calls_default_is_true(self, monkeypatch):
        """When ALLOW_LIVE_RESEARCH_CALLS is absent, settings.allow_live_research_calls defaults True."""
        monkeypatch.delenv("ALLOW_LIVE_RESEARCH_CALLS", raising=False)
        Settings = _fresh_settings_cls()
        settings = Settings()
        assert settings.allow_live_research_calls is True, (
            "Default allow_live_research_calls must be True for backwards compat"
        )

    def test_allow_live_research_calls_zero_maps_to_false(self, monkeypatch):
        """ALLOW_LIVE_RESEARCH_CALLS=0 → settings.allow_live_research_calls=False."""
        monkeypatch.setenv("ALLOW_LIVE_RESEARCH_CALLS", "0")
        Settings = _fresh_settings_cls()
        settings = Settings()
        assert settings.allow_live_research_calls is False

    def test_allow_live_research_calls_field_exists_in_settings(self):
        """Settings model has allow_live_research_calls field (canonical kill switch)."""
        import pathlib
        candidates = [
            pathlib.Path("backend/app/core/config.py"),
            pathlib.Path("app/core/config.py"),
        ]
        config_src = None
        for p in candidates:
            if p.exists():
                config_src = p.read_text()
                break
        assert config_src is not None, "Could not find app/core/config.py"
        assert "allow_live_research_calls: bool = True" in config_src, (
            "Settings must declare allow_live_research_calls: bool = True "
            "(maps ALLOW_LIVE_RESEARCH_CALLS env → Settings for canonical kill switch)"
        )

    def test_live_research_calls_allowed_helper_returns_false_without_env(self, monkeypatch):
        """_live_research_calls_allowed() returns False when ALLOW_LIVE_RESEARCH_CALLS not set."""
        monkeypatch.delenv("ALLOW_LIVE_RESEARCH_CALLS", raising=False)

        from app.services.live_research import _live_research_calls_allowed
        assert _live_research_calls_allowed() is False, (
            "_live_research_calls_allowed() must return False when ALLOW_LIVE_RESEARCH_CALLS is absent"
        )

    def test_live_research_calls_allowed_helper_true_with_env(self, monkeypatch):
        """_live_research_calls_allowed() returns True when ALLOW_LIVE_RESEARCH_CALLS=1."""
        monkeypatch.setenv("ALLOW_LIVE_RESEARCH_CALLS", "1")

        from app.services.live_research import _live_research_calls_allowed
        assert _live_research_calls_allowed() is True
