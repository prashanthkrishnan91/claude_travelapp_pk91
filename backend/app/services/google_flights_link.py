"""Google Flights tfs= URL builder — best-effort, undocumented API.

Verified against real Google Flights tfs= samples (2026-05-13):
  - 5 single-airport samples (SEA/LAX/JFK routes, 1–3 pax, one-way/round-trip)
  - 3 city-group samples (NYC/LAX/CHI groups, mode 3 encoding)

The tfs= parameter is a base64url-encoded protobuf binary.

  Outer message fields:
    field 1  (varint):          28  — constant
    field 2  (varint):           2  — always 2 (same for one-way and round-trip)
    field 3  (submessage):    legs  — outbound leg; repeated for round-trip
    [field 3  repeated]            — return leg (round-trip only, airports reversed)
    field 8  (varint, repeated): 1  — one entry per adult passenger (economy marker)
    field 9  (varint):           1  — always 1
    field 14 (varint):           1  — constant
    field 16 (submessage):   price  — price constraint (max uint64 = no limit)
    field 19 (varint):    2 or 1  — 2 = one-way; 1 = round-trip

  Airport encoding modes (field 1 of airport submessage):
    mode 1: raw IATA code fallback (field 1 = 1)
    mode 2: individual airport via Google MID place token (field 1 = 2)
    mode 3: city/airport-group via Google MID place token (field 1 = 3)

  City-group tokens (mode 3, verified from real fixtures):
    NYC group (/m/02_286):   JFK, LGA, EWR
    LAX group (/m/030qb3t):  LAX, BUR
    CHI group (/m/01_d4):    ORD, MDW
    These tokens are city/airport-group MIDs. Passing origin_group_token
    or destination_group_token explicitly activates mode-3 encoding.

  Passenger count encoding (verified):
    1 pax → 40 01 48 01  (field_8=1 × 1, then field_9=1)
    2 pax → 40 01 40 01 48 01
    3 pax → 40 01 40 01 40 01 48 01
    Field 9 is always 1 regardless of passenger count.

  tfu= query parameter: NOT required. Constant value in real URLs,
    not functionally required. Generated URLs omit it.

  tcfs= query parameter: NOT included. Present in some real round-trip
    city-group URLs alongside mode-2 encoding; our approach uses mode-3
    without tcfs= (verified to produce correct URLs in F1–F3 fixtures).

IMPORTANT: This format is undocumented and may change without notice.
Treat as best-effort link-out; always fail gracefully to None.
"""
from __future__ import annotations

import base64
from datetime import date
from typing import Optional

# Known Google MID place tokens for individual airports (mode 2).
# Airports NOT in this dict fall back to raw IATA encoding (mode 1).
_AIRPORT_PLACE_TOKENS: dict[str, str] = {
    "SEA": "/m/0d9jr",
}

# Verified city/airport-group tokens (mode 3).
# Decoded from real Google Flights tfs= fixtures (2026-05-13).
# Only three cities are verified; do not fabricate entries.
_CITY_GROUP_TOKENS: dict[str, str] = {
    "NYC": "/m/02_286",     # New York — JFK, LGA, EWR
    "LAX": "/m/030qb3t",    # Los Angeles — LAX, BUR (and others)
    "CHI": "/m/01_d4",      # Chicago — ORD, MDW
}

# Reverse map: any IATA in a verified city group → city group token.
# Used to auto-select city-group encoding when multiple airports are requested.
_IATA_TO_CITY_GROUP_TOKEN: dict[str, str] = {
    "JFK": "/m/02_286", "LGA": "/m/02_286", "EWR": "/m/02_286",
    "LAX": "/m/030qb3t", "BUR": "/m/030qb3t",
    "ORD": "/m/01_d4", "MDW": "/m/01_d4",
}

_GOOGLE_FLIGHTS_BASE = "https://www.google.com/travel/flights/search"


def get_city_group_token(iata: str) -> Optional[str]:
    """Return the verified city-group token for a given IATA, or None.

    Returns a value only for airports in the three verified city groups
    (NYC, LAX, CHI). All other airports return None and will use their
    individual airport encoding (mode 2 MID or mode 1 IATA fallback).
    """
    return _IATA_TO_CITY_GROUP_TOKEN.get(iata.upper())


def _encode_varint(value: int) -> bytes:
    """Encode a non-negative integer as a protobuf varint."""
    if value < 0:
        value = value & 0xFFFFFFFFFFFFFFFF
    buf = []
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            buf.append(byte | 0x80)
        else:
            buf.append(byte)
            break
    return bytes(buf)


def _tag(field_num: int, wire_type: int) -> bytes:
    return _encode_varint((field_num << 3) | wire_type)


def _field_varint(field_num: int, value: int) -> bytes:
    return _tag(field_num, 0) + _encode_varint(value)


def _field_bytes(field_num: int, data: bytes) -> bytes:
    return _tag(field_num, 2) + _encode_varint(len(data)) + data


def _field_string(field_num: int, value: str) -> bytes:
    return _field_bytes(field_num, value.encode("utf-8"))


def _encode_airport(iata: str, group_token: Optional[str] = None) -> bytes:
    """Encode an airport in the correct protobuf mode.

    Mode 3 (city group): used when group_token is provided.
    Mode 2 (individual airport MID): used for known airports in _AIRPORT_PLACE_TOKENS.
    Mode 1 (raw IATA fallback): used for all other airports.
    """
    if group_token:
        return _field_varint(1, 3) + _field_string(2, group_token)
    token = _AIRPORT_PLACE_TOKENS.get(iata.upper())
    if token:
        return _field_varint(1, 2) + _field_string(2, token)
    return _field_varint(1, 1) + _field_string(2, iata.upper())


def _encode_leg(
    departure_date_str: str,
    origin: str,
    destination: str,
    origin_group_token: Optional[str] = None,
    destination_group_token: Optional[str] = None,
) -> bytes:
    return (
        _field_string(2, departure_date_str)
        + _field_bytes(13, _encode_airport(origin, origin_group_token))
        + _field_bytes(14, _encode_airport(destination, destination_group_token))
    )


def build_google_flights_url(
    *,
    origin: str,
    destination: str,
    departure_date: Optional[date],
    return_date: Optional[date] = None,
    passengers: int = 1,
    origin_group_token: Optional[str] = None,
    destination_group_token: Optional[str] = None,
) -> Optional[str]:
    """Build a Google Flights search URL for one-way or round-trip queries.

    Returns None on invalid inputs so callers never surface a broken link.

    origin_group_token / destination_group_token: when provided, activates
      mode-3 (city/airport-group) encoding for the respective airport.
      Use get_city_group_token() to look up verified tokens.
      Only pass these when the search was made against a multi-airport city
      group; single-IATA searches must use the default individual encoding.

    Passenger count: each adult = one repeated field 8 = 1 entry (verified).
    One-way vs round-trip: field 2 is always 2; field 19 = 2 one-way / 1 round-trip.
    Round-trip: two field 3 legs, second leg has airports reversed.
    tfu= and tcfs= query params: NOT included (not functionally required).
    """
    origin = (origin or "").upper().strip()
    destination = (destination or "").upper().strip()
    if len(origin) != 3 or not origin.isalpha():
        return None
    if len(destination) != 3 or not destination.isalpha():
        return None
    if departure_date is None:
        return None
    passengers = max(int(passengers or 1), 1)

    try:
        dep_str = departure_date.isoformat()
    except Exception:
        return None

    is_round_trip = return_date is not None
    if is_round_trip:
        try:
            ret_str = return_date.isoformat()
        except Exception:
            return None

    # Price constraint: no upper limit (max uint64)
    price_msg = _field_varint(1, 0xFFFFFFFFFFFFFFFF)

    # Passenger encoding: one field_8=1 per adult, then field_9=1 (always 1).
    pax_bytes = _field_varint(8, 1) * passengers + _field_varint(9, 1)

    outbound_leg = _encode_leg(
        dep_str, origin, destination,
        origin_group_token, destination_group_token,
    )

    if is_round_trip:
        return_leg = _encode_leg(
            ret_str, destination, origin,
            destination_group_token, origin_group_token,  # airports + tokens swapped
        )
        outer = (
            _field_varint(1, 28)
            + _field_varint(2, 2)               # always 2 (verified)
            + _field_bytes(3, outbound_leg)
            + _field_bytes(3, return_leg)        # repeated field 3 = return leg
            + pax_bytes
            + _field_varint(14, 1)
            + _field_bytes(16, price_msg)
            + _field_varint(19, 1)              # round-trip: field 19 = 1
        )
    else:
        outer = (
            _field_varint(1, 28)
            + _field_varint(2, 2)               # always 2 (verified)
            + _field_bytes(3, outbound_leg)
            + pax_bytes
            + _field_varint(14, 1)
            + _field_bytes(16, price_msg)
            + _field_varint(19, 2)              # one-way: field 19 = 2
        )

    tfs = base64.urlsafe_b64encode(outer).rstrip(b"=").decode("ascii")
    return f"{_GOOGLE_FLIGHTS_BASE}?tfs={tfs}"


__all__ = [
    "build_google_flights_url",
    "get_city_group_token",
    "_AIRPORT_PLACE_TOKENS",
    "_CITY_GROUP_TOKENS",
    "_IATA_TO_CITY_GROUP_TOKEN",
]
