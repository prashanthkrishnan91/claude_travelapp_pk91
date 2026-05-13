"""Google Flights tfs= URL builder — best-effort, undocumented API.

Reverse-engineered from a known-good golden URL:
  SEA→LAX, 2026-06-17, one-way, 1 passenger, economy class

The tfs= parameter is a base64url-encoded protobuf binary. The structure
was decoded by inspecting the 64-byte binary of the golden URL:

  Outer message fields:
    field 1 (varint): 28          — constant
    field 2 (varint): 2           — trip type (2 = one-way)
    field 3 (submessage): legs    — departure date + origin + destination
    field 8 (varint): 1           — cabin class (1 = economy)
    field 9 (varint): passengers  — passenger count
    field 14 (varint): 1          — constant
    field 16 (submessage): price  — price constraint (max uint64 = no limit)
    field 19 (varint): 2          — constant

  Legs submessage:
    field 2 (string): "YYYY-MM-DD"
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


def build_google_flights_url(
    *,
    origin: str,
    destination: str,
    departure_date: Optional[date],
    passengers: int = 1,
) -> Optional[str]:
    """Build a Google Flights search URL for the given one-way query.

    Returns None on invalid inputs so callers never surface a broken link.
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
        date_str = departure_date.isoformat()
    except Exception:
        return None

    # Price constraint: no upper limit (max uint64)
    price_msg = _field_varint(1, 0xFFFFFFFFFFFFFFFF)

    legs_msg = (
        _field_string(2, date_str)
        + _field_bytes(13, _encode_airport(origin))
        + _field_bytes(14, _encode_airport(destination))
    )

    outer = (
        _field_varint(1, 28)
        + _field_varint(2, 2)
        + _field_bytes(3, legs_msg)
        + _field_varint(8, 1)
        + _field_varint(9, passengers)
        + _field_varint(14, 1)
        + _field_bytes(16, price_msg)
        + _field_varint(19, 2)
    )

    tfs = base64.urlsafe_b64encode(outer).rstrip(b"=").decode("ascii")
    return f"{_GOOGLE_FLIGHTS_BASE}?tfs={tfs}"


__all__ = ["build_google_flights_url", "_AIRPORT_PLACE_TOKENS"]
