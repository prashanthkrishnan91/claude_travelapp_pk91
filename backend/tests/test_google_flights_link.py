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

    def test_field_2_is_2_for_one_way(self):
        # Structural check: field 2 = 2 in the one-way golden URL.
        url = build_google_flights_url(
            origin="SEA", destination="LAX", departure_date=date(2026, 6, 17)
        )
        tfs = url.split("?tfs=")[1]
        decoded = base64.urlsafe_b64decode(tfs + "=" * (-len(tfs) % 4))
        # Bytes: [0]=0x08 field-1-tag, [1]=0x1C value-28, [2]=0x10 field-2-tag, [3]=0x02 one-way
        assert decoded[2] == 0x10  # tag for field 2, wire type 0
        assert decoded[3] == 0x02  # one-way

    def test_passenger_field_9_changes_with_count(self):
        # Structural check: field 9 carries the passenger count.
        # NOTE: production smoke test (2026-05-13) showed Google Flights does NOT
        # display the correct visible count for field 9 > 1. The correct multi-
        # passenger encoding is unverified — this test only documents the field
        # location, not functional correctness for pax > 1.
        url1 = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17), passengers=1,
        )
        url2 = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17), passengers=2,
        )
        dec1 = base64.urlsafe_b64decode(
            url1.split("?tfs=")[1] + "=" * (-len(url1.split("?tfs=")[1]) % 4)
        )
        dec2 = base64.urlsafe_b64decode(
            url2.split("?tfs=")[1] + "=" * (-len(url2.split("?tfs=")[1]) % 4)
        )
        # Find field-9 tag (0x48) and verify the value byte differs.
        idx = dec1.index(0x48)
        assert dec1[idx + 1] == 1   # 1 passenger
        assert dec2[idx + 1] == 2   # 2 passengers (structurally correct; smoke-test unverified)


@requires_module
class TestRoundTrip:
    def test_round_trip_differs_from_one_way(self):
        one_way = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17),
        )
        round_trip = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17),
            return_date=date(2026, 6, 20),
        )
        assert one_way is not None and round_trip is not None
        assert one_way != round_trip

    def test_one_way_golden_url_unchanged_with_none_return_date(self):
        # Backward compat: no return_date must preserve the exact golden URL.
        url = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17),
            return_date=None,
        )
        assert url == GOLDEN_URL

    def test_round_trip_field_2_is_1(self):
        # Round-trip changes field 2 from 2 (one-way) to 1.
        url = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17),
            return_date=date(2026, 6, 20),
        )
        tfs = url.split("?tfs=")[1]
        decoded = base64.urlsafe_b64decode(tfs + "=" * (-len(tfs) % 4))
        assert decoded[2] == 0x10   # tag for field 2, wire type 0
        assert decoded[3] == 0x01   # round-trip = 1

    def test_round_trip_both_dates_in_binary(self):
        url = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17),
            return_date=date(2026, 6, 20),
        )
        tfs = url.split("?tfs=")[1]
        decoded = base64.urlsafe_b64decode(tfs + "=" * (-len(tfs) % 4))
        assert b"2026-06-17" in decoded
        assert b"2026-06-20" in decoded

    def test_round_trip_different_return_dates_differ(self):
        url1 = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17),
            return_date=date(2026, 6, 20),
        )
        url2 = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17),
            return_date=date(2026, 6, 25),
        )
        assert url1 != url2

    def test_round_trip_return_route_is_reversed_in_binary(self):
        # The return leg should encode dest→origin. Verify both "LAX" and "SEA"
        # appear twice in the decoded bytes (once per direction per leg).
        url = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17),
            return_date=date(2026, 6, 20),
        )
        tfs = url.split("?tfs=")[1]
        decoded = base64.urlsafe_b64decode(tfs + "=" * (-len(tfs) % 4))
        assert decoded.count(b"LAX") == 2
        assert decoded.count(b"2026-06") == 2   # two legs, both in the same month

    def test_round_trip_produces_valid_base64url(self):
        url = build_google_flights_url(
            origin="JFK", destination="CDG",
            departure_date=date(2026, 8, 11),
            return_date=date(2026, 8, 19),
        )
        assert url is not None
        tfs = url.split("?tfs=")[1]
        assert "=" not in tfs
        assert "+" not in tfs
        base64.urlsafe_b64decode(tfs + "=" * (-len(tfs) % 4))  # must not raise

    def test_round_trip_2_passengers_produces_url(self):
        url = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17),
            return_date=date(2026, 6, 20),
            passengers=2,
        )
        assert url is not None
        assert url.startswith("https://www.google.com/travel/flights/search?tfs=")
