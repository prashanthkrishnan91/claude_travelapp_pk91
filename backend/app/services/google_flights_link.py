"""Google Flights tfs= URL builder — best-effort, undocumented API.

Verified against 5 real Google Flights tfs= samples (2026-05-13):
  URL-1: SEA→LAX, one-way,    2026-06-17, 1 pax, economy
  URL-2: SEA→LAX, one-way,    2026-06-17, 2 pax, economy
  URL-3: SEA→LAX, round-trip, 2026-06-17→2026-06-20, 1 pax, economy
  URL-4: SEA→LAX, round-trip, 2026-06-17→2026-06-20, 2 pax, economy
  URL-5: SEA→LAX, one-way,    2026-06-17, 3 pax, economy

The tfs= parameter is a base64url-encoded protobuf binary.

  Outer message fields:
    field 1  (varint):          28  — constant
    field 2  (varint):           2  — always 2 (same for both one-way and round-trip)
    field 3  (submessage):    legs  — outbound leg; repeated for round-trip
    [field 3  repeated]            — return leg (round-trip only, airports reversed)
    field 8  (varint, repeated): 1  — one entry per adult passenger (economy marker)
    field 9  (varint):           1  — always 1
    field 14 (varint):           1  — constant
    field 16 (submessage):   price  — price constraint (max uint64 = no limit)
    field 19 (varint):    2 or 1  — 2 = one-way; 1 = round-trip

  Passenger count encoding (verified from real URL samples):
    Each adult passenger = one field 8 = 1 entry.
    1 pax → 40 01 48 01  (field_8=1 × 1, then field_9=1)
    2 pax → 40 01 40 01 48 01
    3 pax → 40 01 40 01 40 01 48 01
    Field 9 is always 1 regardless of passenger count.

  One-way vs round-trip (verified from real URL samples):
    Both use field 2 = 2. The differentiator is field 19:
      field 19 = 2 → one-way
      field 19 = 1 → round-trip (also has a second field 3 return leg)

  tfu= query parameter: NOT required. The tfu=EgYIABAAGAA value present
    in multi-pax/round-trip real URLs is a constant added by the Google Flights
    UI regardless of passenger count or trip type; it is not functionally
    required for Google Flights to show the correct search.

  Legs submessage:
    field 2  (string): "YYYY-MM-DD"
    field 13 (submessage): origin airport
    field 14 (submessage): destination airport

  Airport submessage:
    field 1 (varint): 2 → Google MID; 1 → raw IATA fallback
    field 2 (string): place token or IATA code

IMPORTANT: This format is undocumented and may change without notice.
Treat as best-effort link-out; always fail gracefully to None.
"""
from __future__ import annotations

import base64
from datetime import date
from typing import Optional

# Known Google MID place tokens, reverse-engineered from the golden URL.
# Airports NOT in this dict fall back to raw IATA encoding (still linkable).
_AIRPORT_PLACE_TOKENS: dict[str, str] = {
    "SEA": "/m/0d9jr",
}

_GOOGLE_FLIGHTS_BASE = "https://www.google.com/travel/flights/search"


def _encode_varint(value: int) -> bytes:
    """Encode a non-negative integer as a protobuf varint (little-endian 7-bit groups)."""
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


def _encode_airport(iata: str) -> bytes:
    token = _AIRPORT_PLACE_TOKENS.get(iata.upper())
    if token:
        return _field_varint(1, 2) + _field_string(2, token)
    return _field_varint(1, 1) + _field_string(2, iata.upper())


def _encode_leg(departure_date_str: str, origin: str, destination: str) -> bytes:
    return (
        _field_string(2, departure_date_str)
        + _field_bytes(13, _encode_airport(origin))
        + _field_bytes(14, _encode_airport(destination))
    )


def build_google_flights_url(
    *,
    origin: str,
    destination: str,
    departure_date: Optional[date],
    return_date: Optional[date] = None,
    passengers: int = 1,
) -> Optional[str]:
    """Build a Google Flights search URL for one-way or round-trip queries.

    Returns None on invalid inputs so callers never surface a broken link.

    Passenger count: each adult = one repeated field 8 = 1 entry (verified).
    One-way vs round-trip: field 2 is always 2; field 19 = 2 one-way / 1 round-trip.
    Round-trip: two field 3 legs, second leg has airports reversed.
    tfu= query param: NOT included (constant in real URLs, not functionally required).
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
    # Verified against real 1/2/3-passenger URL samples.
    pax_bytes = _field_varint(8, 1) * passengers + _field_varint(9, 1)

    outbound_leg = _encode_leg(dep_str, origin, destination)

    if is_round_trip:
        return_leg = _encode_leg(ret_str, destination, origin)
        outer = (
            _field_varint(1, 28)
            + _field_varint(2, 2)               # always 2 (verified: same for round-trip)
            + _field_bytes(3, outbound_leg)
            + _field_bytes(3, return_leg)        # repeated field 3 = return leg
            + pax_bytes
            + _field_varint(14, 1)
            + _field_bytes(16, price_msg)
            + _field_varint(19, 1)              # round-trip marker: field 19 = 1
        )
    else:
        outer = (
            _field_varint(1, 28)
            + _field_varint(2, 2)               # always 2
            + _field_bytes(3, outbound_leg)
            + pax_bytes
            + _field_varint(14, 1)
            + _field_bytes(16, price_msg)
            + _field_varint(19, 2)              # one-way marker: field 19 = 2
        )

    tfs = base64.urlsafe_b64encode(outer).rstrip(b"=").decode("ascii")
    return f"{_GOOGLE_FLIGHTS_BASE}?tfs={tfs}"


__all__ = ["build_google_flights_url", "_AIRPORT_PLACE_TOKENS"]
