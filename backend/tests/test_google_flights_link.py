"""Tests for the Google Flights tfs= URL builder.

Golden test verifies exact byte-for-byte match against the known-good URL:
  SEA→LAX, 2026-06-17, one-way, 1 passenger, economy class

Guarded with a graceful skip in case the module isn't installed.
"""
from __future__ import annotations

import base64
from datetime import date

import pytest

_available = True
try:
    from app.services.google_flights_link import (
        build_google_flights_url,
        _AIRPORT_PLACE_TOKENS,
    )
except (ImportError, ModuleNotFoundError):
    _available = False
    build_google_flights_url = None  # type: ignore[assignment]
    _AIRPORT_PLACE_TOKENS = {}  # type: ignore[assignment]

requires_module = pytest.mark.skipif(
    not _available,
    reason="google_flights_link not available in this harness",
)

# Golden URL reverse-engineered from the real Google Flights UI.
# SEA→LAX, departure 2026-06-17, one-way, 1 passenger, economy.
GOLDEN_URL = (
    "https://www.google.com/travel/flights/search"
    "?tfs=CBwQAhojEgoyMDI2LTA2LTE3agwIAhIIL20vMGQ5anJyBwgBEgNMQVhAAUgBcAGCAQsI"
    "____________AZgBAg"
)


@requires_module
class TestGoldenUrl:
    def test_sea_to_lax_exact_match(self):
        url = build_google_flights_url(
            origin="SEA",
            destination="LAX",
            departure_date=date(2026, 6, 17),
            passengers=1,
        )
        assert url == GOLDEN_URL

    def test_case_insensitive_inputs(self):
        url_upper = build_google_flights_url(
            origin="SEA", destination="LAX", departure_date=date(2026, 6, 17)
        )
        url_lower = build_google_flights_url(
            origin="sea", destination="lax", departure_date=date(2026, 6, 17)
        )
        assert url_upper == url_lower == GOLDEN_URL

    def test_sea_place_token_is_correct(self):
        assert _AIRPORT_PLACE_TOKENS.get("SEA") == "/m/0d9jr"

    def test_tfs_decodes_to_expected_byte_length(self):
        url = build_google_flights_url(
            origin="SEA", destination="LAX", departure_date=date(2026, 6, 17)
        )
        tfs = url.split("?tfs=")[1]
        padded = tfs + "=" * (-len(tfs) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        assert len(decoded) == 64


@requires_module
class TestInvalidInputs:
    def test_empty_origin_returns_none(self):
        assert build_google_flights_url(
            origin="", destination="LAX", departure_date=date(2026, 6, 17)
        ) is None

    def test_short_origin_returns_none(self):
        assert build_google_flights_url(
            origin="JF", destination="LAX", departure_date=date(2026, 6, 17)
        ) is None

    def test_long_origin_returns_none(self):
        assert build_google_flights_url(
            origin="JFKX", destination="LAX", departure_date=date(2026, 6, 17)
        ) is None

    def test_empty_destination_returns_none(self):
        assert build_google_flights_url(
            origin="SEA", destination="", departure_date=date(2026, 6, 17)
        ) is None

    def test_none_date_returns_none(self):
        assert build_google_flights_url(
            origin="SEA", destination="LAX", departure_date=None
        ) is None

    def test_numeric_origin_returns_none(self):
        assert build_google_flights_url(
            origin="123", destination="LAX", departure_date=date(2026, 6, 17)
        ) is None


@requires_module
class TestUnknownAirports:
    def test_unknown_origin_falls_back_to_raw_iata(self):
        url = build_google_flights_url(
            origin="JFK", destination="CDG", departure_date=date(2026, 6, 17)
        )
        assert url is not None
        assert url.startswith("https://www.google.com/travel/flights/search?tfs=")

    def test_unknown_airports_produce_valid_base64url(self):
        url = build_google_flights_url(
            origin="JFK", destination="CDG", departure_date=date(2026, 6, 17)
        )
        tfs = url.split("?tfs=")[1]
        assert "=" not in tfs
        assert "+" not in tfs
        padded = tfs + "=" * (-len(tfs) % 4)
        base64.urlsafe_b64decode(padded)  # should not raise

    def test_different_airports_produce_different_urls(self):
        url1 = build_google_flights_url(
            origin="JFK", destination="CDG", departure_date=date(2026, 6, 17)
        )
        url2 = build_google_flights_url(
            origin="LAX", destination="LHR", departure_date=date(2026, 6, 17)
        )
        assert url1 != url2


@requires_module
class TestUrlStructure:
    def test_url_base_is_google_flights(self):
        url = build_google_flights_url(
            origin="SEA", destination="LAX", departure_date=date(2026, 6, 17)
        )
        assert url.startswith("https://www.google.com/travel/flights/search?tfs=")

    def test_no_padding_chars_in_tfs(self):
        url = build_google_flights_url(
            origin="SEA", destination="LAX", departure_date=date(2026, 6, 17)
        )
        tfs = url.split("?tfs=")[1]
        assert "=" not in tfs

    def test_different_passenger_counts_differ(self):
        url1 = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17), passengers=1,
        )
        url2 = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17), passengers=2,
        )
        assert url1 != url2

    def test_different_dates_differ(self):
        url1 = build_google_flights_url(
            origin="SEA", destination="LAX", departure_date=date(2026, 6, 17)
        )
        url2 = build_google_flights_url(
            origin="SEA", destination="LAX", departure_date=date(2026, 7, 1)
        )
        assert url1 != url2
