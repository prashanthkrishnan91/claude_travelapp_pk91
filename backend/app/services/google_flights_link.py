"""Google Flights tfs= URL builder — best-effort, undocumented API.

Reverse-engineered from a known-good golden URL:
  SEA→LAX, 2026-06-17, one-way, 1 passenger, economy class

The tfs= parameter is a base64url-encoded protobuf binary. The structure
was decoded by inspecting the 64-byte binary of the golden URL:

  Outer message fields:
    field 1 (varint): 28          — constant
    field 2 (varint): 2=one-way / 1=round-trip
    field 3 (submessage): legs    — departure date + origin + destination
    [field 3 repeated]            — return leg (round-trip only)
    field 8 (varint): 1           — cabin class (1 = economy)
    field 9 (varint): passengers  — best-guess passenger count field;
                                    see KNOWN LIMITATION below.
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

KNOWN LIMITATION — passenger count encoding (2026-05-13):
  Field 9 is set to the adult passenger count based on reverse-engineering
  the single golden URL (1 passenger → field 9 = 1). However, production
  smoke test confirmed that Google Flights does NOT show the correct visible
  passenger count when field 9 > 1. The correct multi-passenger encoding
  requires a real 2-passenger Google Flights tfs= URL to decode. Until that
  sample is available, passenger count >1 is structurally encoded in field 9
  but its visible effect in Google Flights is UNVERIFIED.

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

    One-way (return_date=None): field 2 = 2, one legs submessage.
      The SEA→LAX 2026-06-17 1-pax golden URL is preserved exactly.

    Round-trip (return_date provided): field 2 = 1, two legs submessages.
      The return leg encodes destination→origin with return_date.

    Passenger count: encoded in field 9 (see module-level KNOWN LIMITATION).
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

    outbound_leg = _encode_leg(dep_str, origin, destination)

    if is_round_trip:
        return_leg = _encode_leg(ret_str, destination, origin)
        outer = (
            _field_varint(1, 28)
            + _field_varint(2, 1)                   # round-trip
            + _field_bytes(3, outbound_leg)
            + _field_bytes(3, return_leg)
            + _field_varint(8, 1)
            + _field_varint(9, passengers)
            + _field_varint(14, 1)
            + _field_bytes(16, price_msg)
            + _field_varint(19, 2)
        )
    else:
        outer = (
            _field_varint(1, 28)
            + _field_varint(2, 2)                   # one-way (golden URL preserved)
            + _field_bytes(3, outbound_leg)
            + _field_varint(8, 1)
            + _field_varint(9, passengers)
            + _field_varint(14, 1)
            + _field_bytes(16, price_msg)
            + _field_varint(19, 2)
        )

    tfs = base64.urlsafe_b64encode(outer).rstrip(b"=").decode("ascii")
    return f"{_GOOGLE_FLIGHTS_BASE}?tfs={tfs}"


__all__ = ["build_google_flights_url", "_AIRPORT_PLACE_TOKENS"]
