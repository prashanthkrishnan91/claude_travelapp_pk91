"""Hotels Product Contract v1 — durable real-data / user-entered lodging surface.

Why this module exists
----------------------
Through PR #298 the user-facing flight path moved off ``_mock_flights`` and
onto the typed ``FlightProvider`` seam.  ``_mock_hotels`` in
``backend/app/services/search.py`` is the last live mock-backed product
surface: it fabricates rows with ``source="mock"`` and ``book.example.com``
booking URLs.  PR #295 added a fail-closed guard at
``/trips/create-with-search`` that blocks those rows from being persisted,
but the legacy ``/search/hotels`` route still emits them.

Hotels Product Contract v1 codifies the invariants the provider-backed
Hotels v1 PR has to honor.  It mirrors the structure of
``backend/app/contracts/flights.py`` so callers can reason about the two
surfaces consistently.

Important product distinction
-----------------------------
Google Places (the v1 lodging discovery provider) returns operational
lodging entities — name, address, rating, Google Maps URI — but it does
NOT return true nightly rates, room availability, cancellation policy, or
bookable inventory.  This contract therefore distinguishes:

- **lodging discovery result** — a real, operational hotel/lodging entity
  surfaced from a place provider; safe to add to a trip as a saved place
  but not a bookable rate.
- **bookable hotel offer** — a true hotel rate/availability offer from a
  rates provider (Booking.com Demand API, Amadeus Hotels, etc.).  Hotels
  v1 does NOT cover this surface.  ``HotelOfferKind`` documents the
  partition explicitly so future PRs cannot silently elevate a discovery
  result into a fabricated rate.

This module never calls a provider, does not depend on a real API key,
and adds zero LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Optional


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------


class HotelSource(str, Enum):
    """Allowed values for ``HotelResult.source`` once Hotels v1 ships."""

    PROVIDER_BACKED = "provider_backed"
    USER_ENTERED = "user_entered"


# Concrete ``HotelResult.source`` strings the contract recognises as
# provider-backed lodging discovery sources.  Extending it requires a
# matching adapter and an explicit test in
# ``backend/tests/test_hotels_product_contract_v1.py``.
PROVIDER_BACKED_SOURCE_VALUES: frozenset = frozenset({
    "google_places",
    "booking_com",
    "amadeus_hotels",
    "expedia",
    "hotels_com",
    "provider_backed",
})

USER_ENTERED_SOURCE_VALUES: frozenset = frozenset({
    "user_entered",
    "manual",
})

ALLOWED_SOURCE_VALUES: frozenset = (
    PROVIDER_BACKED_SOURCE_VALUES | USER_ENTERED_SOURCE_VALUES
)

DISALLOWED_SOURCES: frozenset = frozenset({
    "mock",
    "demo",
    "fixture",
    "sample",
    "placeholder",
})

# Sentinel substring stamped into every legacy ``_mock_hotels`` booking
# URL.  Mirrors ``backend/app/contracts/flights.py::MOCK_BOOKING_HOST`` so
# both surfaces share the same fabricated-host vocabulary.
MOCK_BOOKING_HOST: str = "book.example.com"

FABRICATED_BOOKING_HOSTS: frozenset = frozenset({
    MOCK_BOOKING_HOST,
    "example.com",
    "example.org",
})


# ---------------------------------------------------------------------------
# Lodging discovery vs bookable rate — explicit partition
# ---------------------------------------------------------------------------


class HotelOfferKind(str, Enum):
    """Partition between lodging discovery and bookable rate offer.

    ``DISCOVERY`` — provider returned a real lodging entity (name,
    address, rating, place id) but did NOT return a nightly rate or
    availability.  Safe to surface as "found this place" and to add to a
    trip as a lodging card; NOT safe to display as a bookable rate.

    ``BOOKABLE_OFFER`` — provider returned a true rate / availability
    offer with verified pricing.  Hotels v1 does NOT cover this kind;
    a future Hotels v2 (Booking.com Demand API or Amadeus Hotels) will.
    """

    DISCOVERY = "discovery"
    BOOKABLE_OFFER = "bookable_offer"


# ---------------------------------------------------------------------------
# Source status — provider seam returns this instead of raising.
# ---------------------------------------------------------------------------


class HotelSourceStatus(str, Enum):
    """Typed health marker the hotel provider seam returns alongside rows.

    ``OK`` — provider returned at least one persistable row.
    ``EMPTY`` — provider returned zero rows for a valid query (no error).
    ``UNAVAILABLE`` — provider not configured (no API key / disabled flag).
    ``ERROR`` — provider call failed (timeout, 5xx, parse error).

    ``UNAVAILABLE`` and ``ERROR`` MUST surface to the UI as a fail-closed
    "unavailable" state.  They MUST NOT be silently coerced to ``EMPTY``,
    and they MUST NOT trigger a fake-row fallback.
    """

    OK = "ok"
    EMPTY = "empty"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Persistability
# ---------------------------------------------------------------------------


# Required fields a hotel row must carry to be persistable.  Names match
# ``backend/app/models/search.py::HotelResult`` so the predicate uses
# ``getattr`` without re-deriving a schema.  ``check_in``/``check_out``/
# ``nights`` are trip metadata derived from request dates and must be
# present, but are not provider availability claims.  ``price_per_night``
# is required by the wire model as a float — discovery-only adapters
# emit ``0.0`` to honor the "do not invent nightly rates" rule.
REQUIRED_PERSIST_FIELDS: tuple = (
    "source",
    "name",
    "location",
    "check_in",
    "check_out",
    "nights",
)


@dataclass(frozen=True)
class PersistabilityFailure:
    """Why a hotel row failed the contract.  Human-readable + machine-keyed."""

    code: str
    field: Optional[str]
    message: str


def _has_fabricated_host(url: Optional[str]) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return any(host in lowered for host in FABRICATED_BOOKING_HOSTS)


def _booking_options_iter(hotel: Any) -> Iterable[Any]:
    return list(getattr(hotel, "booking_options", None) or [])


def check_persistable_hotel(hotel: Any) -> Optional[PersistabilityFailure]:
    """Return ``None`` if ``hotel`` is persistable, else a typed failure."""
    source_raw = getattr(hotel, "source", None)
    source = (str(source_raw) if source_raw is not None else "").strip().lower()

    if not source:
        return PersistabilityFailure(
            code="missing_source", field="source",
            message="hotel.source is required",
        )

    if source in DISALLOWED_SOURCES:
        return PersistabilityFailure(
            code="disallowed_source", field="source",
            message=f"hotel.source={source!r} is mock/demo/fixture",
        )

    if source not in ALLOWED_SOURCE_VALUES:
        return PersistabilityFailure(
            code="unrecognised_source", field="source",
            message=(
                f"hotel.source={source!r} is not in the Hotels Product "
                f"Contract v1 allowed list"
            ),
        )

    primary_url = getattr(hotel, "booking_url", None)
    if _has_fabricated_host(primary_url):
        return PersistabilityFailure(
            code="fabricated_booking_url", field="booking_url",
            message=f"booking_url uses fabricated host: {primary_url!r}",
        )

    for opt in _booking_options_iter(hotel):
        opt_url = getattr(opt, "url", None) or (
            opt.get("url") if isinstance(opt, dict) else None
        )
        if _has_fabricated_host(opt_url):
            return PersistabilityFailure(
                code="fabricated_booking_option_url", field="booking_options[].url",
                message=f"booking_options carries fabricated host: {opt_url!r}",
            )

    for fname in REQUIRED_PERSIST_FIELDS:
        if getattr(hotel, fname, None) in (None, ""):
            return PersistabilityFailure(
                code="missing_required_field", field=fname,
                message=f"hotel.{fname} is required for persistence",
            )

    return None


def is_persistable_hotel(hotel: Any) -> bool:
    """True iff ``hotel`` satisfies Hotels Product Contract v1."""
    return check_persistable_hotel(hotel) is None


def is_mock_derived_hotel(hotel: Any) -> bool:
    """True iff ``hotel`` is mock/demo/fabricated (legacy fail-closed gate).

    Mirror of ``app.contracts.flights.is_mock_derived_flight``.
    ``backend/app/routes/trips.py::_is_mock_hotel`` may delegate to this
    so the persistence-guard rules live in one place.
    """
    source_raw = getattr(hotel, "source", None)
    source = (str(source_raw) if source_raw is not None else "").strip().lower()
    if source in DISALLOWED_SOURCES:
        return True
    if _has_fabricated_host(getattr(hotel, "booking_url", None)):
        return True
    for opt in _booking_options_iter(hotel):
        opt_url = getattr(opt, "url", None) or (
            opt.get("url") if isinstance(opt, dict) else None
        )
        if _has_fabricated_host(opt_url):
            return True
    return False


class HotelContractViolation(ValueError):
    """Raised by ``assert_persistable_hotel`` on contract failure."""

    def __init__(self, failure: PersistabilityFailure) -> None:
        super().__init__(failure.message)
        self.failure = failure


def assert_persistable_hotel(hotel: Any) -> None:
    failure = check_persistable_hotel(hotel)
    if failure is not None:
        raise HotelContractViolation(failure)


# ---------------------------------------------------------------------------
# Provider seam reference type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HotelProviderUnavailable:
    """Typed unavailable state returned by ``NullHotelProvider``."""

    status: HotelSourceStatus
    reason: str

    def __post_init__(self) -> None:
        if self.status not in {HotelSourceStatus.UNAVAILABLE, HotelSourceStatus.ERROR}:
            raise ValueError(
                "HotelProviderUnavailable.status must be UNAVAILABLE or ERROR"
            )


__all__ = [
    "ALLOWED_SOURCE_VALUES",
    "DISALLOWED_SOURCES",
    "FABRICATED_BOOKING_HOSTS",
    "HotelContractViolation",
    "HotelOfferKind",
    "HotelProviderUnavailable",
    "HotelSource",
    "HotelSourceStatus",
    "MOCK_BOOKING_HOST",
    "PROVIDER_BACKED_SOURCE_VALUES",
    "PersistabilityFailure",
    "REQUIRED_PERSIST_FIELDS",
    "USER_ENTERED_SOURCE_VALUES",
    "assert_persistable_hotel",
    "check_persistable_hotel",
    "is_mock_derived_hotel",
    "is_persistable_hotel",
]
