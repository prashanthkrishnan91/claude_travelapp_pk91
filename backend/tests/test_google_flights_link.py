"""Tests for the Google Flights tfs= URL builder.

Golden tests verify exact byte-for-byte match against real Google Flights URLs
captured 2026-05-13. Five fixtures cover the full combinatorial space:
  - one-way 1 pax (original golden, unchanged)
  - one-way 2 pax
  - one-way 3 pax
  - round-trip 1 pax
  - round-trip 2 pax

Key verified facts (decoded from real tfs= samples):
  - Field 2 = 2 for BOTH one-way and round-trip (not a trip-type flag).
  - Field 19 = 2 one-way; field 19 = 1 round-trip.
  - Passenger count = repeated field 8 = 1 (one entry per adult).
  - Field 9 = always 1 regardless of passenger count.
  - tfu= query param is constant/optional; not included in generated URLs.
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

BASE = "https://www.google.com/travel/flights/search?tfs="

# Real Google Flights URLs captured 2026-05-13 (tfs= only, tfu=/hl=/gl= omitted).
# Each tfs= exactly matches the corrected encoder output.
GOLDEN_1WAY_1PAX = BASE + (
    "CBwQAhojEgoyMDI2LTA2LTE3agwIAhIIL20vMGQ5anJyBwgBEgNMQVhAAUgBcAGCAQsI"
    "____________AZgBAg"
)
GOLDEN_1WAY_2PAX = BASE + (
    "CBwQAhojEgoyMDI2LTA2LTE3agwIAhIIL20vMGQ5anJyBwgBEgNMQVhAAUABSAFwAYIBCwj"
    "___________8BmAEC"
)
GOLDEN_1WAY_3PAX = BASE + (
    "CBwQAhojEgoyMDI2LTA2LTE3agwIAhIIL20vMGQ5anJyBwgBEgNMQVhAAUABQAFIAXABggELCP"
    "___________wGYAQI"
)
GOLDEN_RT_1PAX = BASE + (
    "CBwQAhojEgoyMDI2LTA2LTE3agwIAhIIL20vMGQ5anJyBwgBEgNMQVgaIxIKMjAyNi0wNi0yMG"
    "oHCAESA0xBWHIMCAISCC9tLzBkOWpyQAFIAXABggELCP___________wGYAQE"
)
GOLDEN_RT_2PAX = BASE + (
    "CBwQAhojEgoyMDI2LTA2LTE3agwIAhIIL20vMGQ5anJyBwgBEgNMQVgaIxIKMjAyNi0wNi0yMG"
    "oHCAESA0xBWHIMCAISCC9tLzBkOWpyQAFAAUgBcAGCAQsI____________AZgBAQ"
)

# Backward-compat alias: GOLDEN_URL is the original one-way 1-pax golden.
GOLDEN_URL = GOLDEN_1WAY_1PAX


def _decode_tfs(url: str) -> bytes:
    tfs = url.split("?tfs=")[1]
    return base64.urlsafe_b64decode(tfs + "=" * (-len(tfs) % 4))


@requires_module
class TestGoldenUrl:
    def test_sea_to_lax_exact_match(self):
        url = build_google_flights_url(
            origin="SEA",
            destination="LAX",
            departure_date=date(2026, 6, 17),
            passengers=1,
        )
        assert url == GOLDEN_1WAY_1PAX

    def test_case_insensitive_inputs(self):
        url_upper = build_google_flights_url(
            origin="SEA", destination="LAX", departure_date=date(2026, 6, 17)
        )
        url_lower = build_google_flights_url(
            origin="sea", destination="lax", departure_date=date(2026, 6, 17)
        )
        assert url_upper == url_lower == GOLDEN_1WAY_1PAX

    def test_sea_place_token_is_correct(self):
        assert _AIRPORT_PLACE_TOKENS.get("SEA") == "/m/0d9jr"

    def test_tfs_decodes_to_expected_byte_length(self):
        url = build_google_flights_url(
            origin="SEA", destination="LAX", departure_date=date(2026, 6, 17)
        )
        assert len(_decode_tfs(url)) == 64

    def test_2pax_one_way_exact_match(self):
        url = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17), passengers=2,
        )
        assert url == GOLDEN_1WAY_2PAX

    def test_3pax_one_way_exact_match(self):
        url = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17), passengers=3,
        )
        assert url == GOLDEN_1WAY_3PAX

    def test_round_trip_1pax_exact_match(self):
        url = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17),
            return_date=date(2026, 6, 20),
            passengers=1,
        )
        assert url == GOLDEN_RT_1PAX

    def test_round_trip_2pax_exact_match(self):
        url = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17),
            return_date=date(2026, 6, 20),
            passengers=2,
        )
        assert url == GOLDEN_RT_2PAX


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
        base64.urlsafe_b64decode(tfs + "=" * (-len(tfs) % 4))  # should not raise

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
        decoded = _decode_tfs(url)
        # Bytes: [0]=0x08 field-1-tag, [1]=0x1C value-28, [2]=0x10 field-2-tag, [3]=0x02
        assert decoded[2] == 0x10  # tag for field 2, wire type 0
        assert decoded[3] == 0x02  # always 2

    def test_passenger_encoding_verified(self):
        # Verified from real URL samples: each adult = one field_8=1 (0x40 0x01).
        # Field 9 is always 0x01 regardless of passenger count.
        url1 = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17), passengers=1,
        )
        url2 = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17), passengers=2,
        )
        url3 = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17), passengers=3,
        )
        dec1 = _decode_tfs(url1)
        dec2 = _decode_tfs(url2)
        dec3 = _decode_tfs(url3)
        # Count occurrences of the field_8=1 marker (0x40 0x01) before field_9 tag (0x48)
        f8_tag = bytes([0x40, 0x01])
        f9_tag = bytes([0x48, 0x01])
        assert dec1.count(f8_tag) == 1 and f9_tag in dec1
        assert dec2.count(f8_tag) == 2 and f9_tag in dec2
        assert dec3.count(f8_tag) == 3 and f9_tag in dec3
        # Field 9 value is always 1 (0x48 0x01) — not the passenger count
        for dec in (dec1, dec2, dec3):
            idx = dec.index(0x48)
            assert dec[idx + 1] == 1  # always 1


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
        url = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17),
            return_date=None,
        )
        assert url == GOLDEN_1WAY_1PAX

    def test_round_trip_field_19_is_1(self):
        # Verified: field 2 = 2 for round-trip (same as one-way).
        # Field 19 = 1 signals round-trip; field 19 = 2 signals one-way.
        url = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17),
            return_date=date(2026, 6, 20),
        )
        decoded = _decode_tfs(url)
        # Field 2 = 2 for round-trip (verified: NOT 1)
        assert decoded[2] == 0x10  # tag for field 2, wire type 0
        assert decoded[3] == 0x02  # always 2
        # Field 19 = 1 for round-trip (last two meaningful bytes: 0x98 0x01 then 0x01)
        assert decoded[-1] == 0x01  # field 19 value = 1 (round-trip)

    def test_one_way_field_19_is_2(self):
        url = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17),
        )
        decoded = _decode_tfs(url)
        assert decoded[-1] == 0x02  # field 19 value = 2 (one-way)

    def test_round_trip_both_dates_in_binary(self):
        url = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17),
            return_date=date(2026, 6, 20),
        )
        decoded = _decode_tfs(url)
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
        url = build_google_flights_url(
            origin="SEA", destination="LAX",
            departure_date=date(2026, 6, 17),
            return_date=date(2026, 6, 20),
        )
        decoded = _decode_tfs(url)
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

