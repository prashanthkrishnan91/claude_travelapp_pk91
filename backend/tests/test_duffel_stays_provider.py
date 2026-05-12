"""Duffel Stays provider scaffold — Slice 5B tests.

Covers:
- Disabled by default (DUFFEL_STAYS_ENABLED not set).
- Disabled when key present but flag absent.
- Returns UNAVAILABLE with no rows when instantiated (scaffold).
- build_duffel_stays_provider_from_env returns None when disabled.
- Constructor rejects empty access token.
- No mock data is returned under any flag combination.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.contracts.hotels import HotelSourceStatus
from app.models.search import HotelSearchRequest
from app.services.hotels_provider_duffel_stays import (
    DuffelStaysProvider,
    build_duffel_stays_provider_from_env,
    duffel_stays_enabled_from_env,
)


def _req() -> HotelSearchRequest:
    return HotelSearchRequest(
        location="Paris, France",
        check_in=date(2026, 9, 1),
        check_out=date(2026, 9, 5),
        guests=2,
    )


class TestDuffelStaysEnabledCheck:
    def test_disabled_when_no_env(self):
        assert not duffel_stays_enabled_from_env({})

    def test_disabled_when_key_only(self):
        assert not duffel_stays_enabled_from_env({"DUFFEL_STAYS_API_KEY": "tok_abc"})

    def test_disabled_when_flag_false(self):
        assert not duffel_stays_enabled_from_env(
            {"DUFFEL_STAYS_API_KEY": "tok_abc", "DUFFEL_STAYS_ENABLED": "0"}
        )

    def test_disabled_when_flag_false_word(self):
        assert not duffel_stays_enabled_from_env(
            {"DUFFEL_STAYS_API_KEY": "tok_abc", "DUFFEL_STAYS_ENABLED": "false"}
        )

    def test_disabled_when_key_missing_but_flag_true(self):
        assert not duffel_stays_enabled_from_env({"DUFFEL_STAYS_ENABLED": "1"})

    def test_enabled_when_key_and_flag(self):
        assert duffel_stays_enabled_from_env(
            {"DUFFEL_STAYS_API_KEY": "tok_abc", "DUFFEL_STAYS_ENABLED": "1"}
        )

    def test_enabled_when_key_and_flag_true_word(self):
        assert duffel_stays_enabled_from_env(
            {"DUFFEL_STAYS_API_KEY": "tok_abc", "DUFFEL_STAYS_ENABLED": "true"}
        )


class TestBuildFromEnv:
    def test_returns_none_when_disabled(self):
        assert build_duffel_stays_provider_from_env({}) is None

    def test_returns_none_when_key_only(self):
        assert build_duffel_stays_provider_from_env(
            {"DUFFEL_STAYS_API_KEY": "tok_abc"}
        ) is None

    def test_returns_provider_when_enabled(self):
        p = build_duffel_stays_provider_from_env(
            {"DUFFEL_STAYS_API_KEY": "tok_abc", "DUFFEL_STAYS_ENABLED": "1"}
        )
        assert isinstance(p, DuffelStaysProvider)


class TestDuffelStaysProviderScaffold:
    def test_constructor_rejects_empty_token(self):
        with pytest.raises(ValueError, match="access token"):
            DuffelStaysProvider(access_token="")

    def test_search_returns_unavailable(self):
        p = DuffelStaysProvider(access_token="tok_abc")
        result = p.search_hotels(_req())
        assert result.status is HotelSourceStatus.UNAVAILABLE
        assert result.rows == []

    def test_search_returns_no_rows(self):
        p = DuffelStaysProvider(access_token="tok_abc")
        result = p.search_hotels(_req())
        assert len(result.rows) == 0

    def test_search_reason_mentions_slice_5c(self):
        p = DuffelStaysProvider(access_token="tok_abc")
        result = p.search_hotels(_req())
        assert "5C" in result.reason or "5c" in result.reason.lower()

    def test_no_mock_data_returned(self):
        """Scaffold must never return rows regardless of input."""
        p = DuffelStaysProvider(access_token="tok_abc")
        for location in ["Paris", "Tokyo", "New York", "London"]:
            r = p.search_hotels(
                HotelSearchRequest(
                    location=location,
                    check_in=date(2026, 9, 1),
                    check_out=date(2026, 9, 5),
                    guests=1,
                )
            )
            assert r.rows == [], f"Expected no rows for {location!r}"
            assert r.status is HotelSourceStatus.UNAVAILABLE
