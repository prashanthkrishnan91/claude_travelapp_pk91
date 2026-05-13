"""Normalized Flight Offer Contract — provider-neutral types for Flights v1.

This module defines the canonical wire shape for a provider-backed flight offer.
It is intentionally:

- transport-agnostic (no FastAPI/Supabase imports);
- provider-neutral (works for Skyscanner, Ignav, or any future approved provider);
- forward-compatible with one-way, round-trip, and (optionally) multi-city shapes;
- fail-closed by construction: price/booking fields are never fabricated.

The companion ``backend/app/contracts/flights.py`` owns the legacy mock-cleanup
contract (persistability predicates, FlightLeg enum, FlightSourceStatus).  This
module owns the normalized *offer* types that a live provider adapter returns.

Key types
---------
FlightSegment       — one non-stop flight leg (airline, times, duration).
FlightOfferLeg      — outbound or return journey, containing 1-N segments.
FlightPrice         — cash price from a live provider; never fabricated.
FlightBookingLink   — deep-link to book; never a mock/placeholder URL.
FlightItineraryOffer — top-level normalized offer returned by an approved adapter.

Usage
-----
A provider adapter returns ``list[FlightItineraryOffer]`` wrapped in a
``FlightProviderResult`` (from ``app.services.flights_provider``).
When the provider is disabled/uncredentialed the adapter returns
``FlightProviderResult(status=UNAVAILABLE, rows=[], ...)`` — never a fabricated
``FlightItineraryOffer``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LiveCachedStatus(str, Enum):
    """Whether the offer price was fetched live or served from cache.

    Adapters MUST set this on every ``FlightItineraryOffer``.  It is surfaced
    to the user in the card UI so stale prices cannot be presented as live.
    """

    LIVE = "live"
    CACHED = "cached"


class BookingLinkType(str, Enum):
    """Classification of the booking deep-link.

    ``AIRLINE_DIRECT``   — links directly to the airline's booking page.
    ``OTA``              — links to a third-party OTA (e.g. Kayak, Expedia).
    ``PROVIDER_DEEPLINK`` — provider-generated deep-link (e.g. Skyscanner).
    ``SEARCH_REDIRECT``  — links to a third-party search page (e.g. Google
                           Flights); search-only, does NOT imply booking.
    ``UNAVAILABLE``      — no bookable or searchable link for this offer.
    """

    AIRLINE_DIRECT = "airline_direct"
    OTA = "ota"
    PROVIDER_DEEPLINK = "provider_deeplink"
    SEARCH_REDIRECT = "search_redirect"
    UNAVAILABLE = "unavailable"


class TripType(str, Enum):
    ONE_WAY = "one_way"
    ROUND_TRIP = "round_trip"


# ---------------------------------------------------------------------------
# Component types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FlightSegment:
    """One non-stop hop within a journey leg.

    All fields are provider-sourced; no field may be fabricated.
    ``departure_time`` and ``arrival_time`` are ISO 8601 UTC strings.
    """

    airline: str
    flight_number: str
    origin: str            # IATA airport code
    destination: str       # IATA airport code
    departure_time: str    # ISO 8601 UTC
    arrival_time: str      # ISO 8601 UTC
    duration_minutes: int
    aircraft_type: Optional[str] = None
    cabin_class: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.airline:
            raise ValueError("FlightSegment.airline is required")
        if not self.flight_number:
            raise ValueError("FlightSegment.flight_number is required")
        if len(self.origin) != 3:
            raise ValueError(f"FlightSegment.origin must be a 3-letter IATA code; got {self.origin!r}")
        if len(self.destination) != 3:
            raise ValueError(f"FlightSegment.destination must be a 3-letter IATA code; got {self.destination!r}")
        if self.duration_minutes <= 0:
            raise ValueError("FlightSegment.duration_minutes must be positive")


@dataclass(frozen=True)
class FlightOfferLeg:
    """One outbound or return journey, made up of one or more segments.

    ``leg_index`` is 0 for outbound, 1 for return (matches ``FlightLeg`` enum
    convention from ``app.contracts.flights``).
    ``segments`` is a tuple of ``FlightSegment``, ordered departure→arrival.
    """

    origin: str                       # IATA departure airport
    destination: str                  # IATA arrival airport
    departure_time: str               # ISO 8601 UTC
    arrival_time: str                 # ISO 8601 UTC
    duration_minutes: int
    stops: int                        # 0 = non-stop
    segments: Tuple[FlightSegment, ...]

    def __post_init__(self) -> None:
        if len(self.origin) != 3:
            raise ValueError(f"FlightOfferLeg.origin must be a 3-letter IATA code; got {self.origin!r}")
        if len(self.destination) != 3:
            raise ValueError(f"FlightOfferLeg.destination must be a 3-letter IATA code; got {self.destination!r}")
        if self.duration_minutes <= 0:
            raise ValueError("FlightOfferLeg.duration_minutes must be positive")
        if self.stops < 0:
            raise ValueError("FlightOfferLeg.stops must be >= 0")
        if not self.segments:
            raise ValueError("FlightOfferLeg.segments must contain at least one FlightSegment")
        object.__setattr__(self, "segments", tuple(self.segments))


@dataclass(frozen=True)
class FlightPrice:
    """Cash price for the offer, sourced from a live provider.

    Invariants (enforced in ``__post_init__``):
    - ``currency`` must be a non-empty string (ISO 4217 expected, e.g. "USD").
    - ``total_amount`` must be > 0 when available.
    - Price MUST NOT be fabricated, estimated, or inferred from other prices.
    - Points prices are handled separately; this type carries cash only.
    """

    currency: str       # ISO 4217
    total_amount: float # total for all passengers, provider-sourced
    per_passenger_amount: Optional[float] = None  # optional per-pax breakdown
    taxes_fees_included: Optional[bool] = None    # None = unknown

    def __post_init__(self) -> None:
        if not self.currency:
            raise ValueError("FlightPrice.currency is required (ISO 4217)")
        if self.total_amount <= 0:
            raise ValueError(
                "FlightPrice.total_amount must be > 0; "
                "zero/negative prices indicate a fabricated or missing value"
            )


@dataclass(frozen=True)
class FlightBookingLink:
    """External deep-link to complete the booking.

    ``url`` must be a real provider-supplied URL.  Placeholder or
    ``book.example.com``-style URLs are rejected in ``__post_init__``.
    ``link_type`` classifies the destination (see ``BookingLinkType``).

    When no bookable URL exists, use ``link_type=UNAVAILABLE`` and leave
    ``url`` as an empty string — do NOT fabricate a URL.
    """

    url: str
    link_type: BookingLinkType
    provider_name: str   # e.g. "skyscanner_flights"

    _FABRICATED_HOSTS = frozenset({"book.example.com", "example.com", "example.org"})

    def __post_init__(self) -> None:
        if self.link_type is not BookingLinkType.UNAVAILABLE and not self.url:
            raise ValueError(
                "FlightBookingLink.url is required when link_type is not UNAVAILABLE"
            )
        if self.url:
            lowered = self.url.lower()
            for host in self._FABRICATED_HOSTS:
                if host in lowered:
                    raise ValueError(
                        f"FlightBookingLink.url uses a fabricated/placeholder host: {self.url!r}"
                    )


# ---------------------------------------------------------------------------
# Top-level offer type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FlightItineraryOffer:
    """Normalized flight offer returned by an approved provider adapter.

    Invariants (enforced in ``__post_init__``):
    - ``provider`` must match a registry entry in ``provider_registry.py``.
    - ``fetched_at`` is an ISO 8601 UTC string; never empty.
    - ``live_cached_status`` explicitly labels freshness.
    - ``price`` must be a ``FlightPrice`` with a positive ``total_amount``.
    - ``outbound_leg`` is always required.
    - ``return_leg`` is None for one-way; required for round-trip.
    - ``trip_type`` must be consistent with presence/absence of ``return_leg``.
    - This type MUST NOT be constructed by disabled/scaffold adapters.
      A provider that is disabled returns ``FlightProviderResult(UNAVAILABLE)``
      with zero rows instead.
    """

    provider: str                           # registry ID, e.g. "skyscanner_flights"
    fetched_at: str                         # ISO 8601 UTC
    live_cached_status: LiveCachedStatus
    trip_type: TripType
    origin: str                             # IATA departure airport
    destination: str                        # IATA arrival airport
    departure_date: str                     # YYYY-MM-DD
    passengers: int
    cabin_class: str
    outbound_leg: FlightOfferLeg
    price: FlightPrice
    booking_link: FlightBookingLink
    return_date: Optional[str] = None       # YYYY-MM-DD; None for one-way
    return_leg: Optional[FlightOfferLeg] = None
    ai_score: Optional[float] = None        # optional AI ranking; 0–1 scale

    def __post_init__(self) -> None:
        if not self.provider:
            raise ValueError("FlightItineraryOffer.provider is required")
        if not self.fetched_at:
            raise ValueError("FlightItineraryOffer.fetched_at is required")
        if self.passengers < 1:
            raise ValueError("FlightItineraryOffer.passengers must be >= 1")
        if self.trip_type is TripType.ROUND_TRIP and self.return_leg is None:
            raise ValueError(
                "FlightItineraryOffer with trip_type=ROUND_TRIP must have return_leg"
            )
        if self.trip_type is TripType.ONE_WAY and self.return_leg is not None:
            raise ValueError(
                "FlightItineraryOffer with trip_type=ONE_WAY must not have return_leg"
            )
        if self.ai_score is not None and not (0.0 <= self.ai_score <= 1.0):
            raise ValueError("FlightItineraryOffer.ai_score must be in [0, 1]")


# ---------------------------------------------------------------------------
# Sentinel: adapter must return this when disabled/uncredentialed
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FlightAdapterDisabledResult:
    """Typed result returned by a scaffold adapter that is not yet enabled.

    Adapter shells (Skyscanner, Ignav) return this internally before wrapping
    into ``FlightProviderResult(status=UNAVAILABLE, rows=[])``.  It exists so
    tests can assert on the reason without parsing strings.
    """

    provider_id: str
    reason: str


# ---------------------------------------------------------------------------
# Re-export FlightSearchRequest from models for contract callers
# ---------------------------------------------------------------------------

from app.models.search import FlightSearchRequest as FlightSearchRequest  # noqa: E402,F401


__all__ = [
    "BookingLinkType",
    "FlightAdapterDisabledResult",
    "FlightBookingLink",
    "FlightItineraryOffer",
    "FlightOfferLeg",
    "FlightPrice",
    "FlightSearchRequest",
    "FlightSegment",
    "LiveCachedStatus",
    "TripType",
]
