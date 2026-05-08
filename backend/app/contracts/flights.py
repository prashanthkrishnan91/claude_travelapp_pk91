"""Flights Product Contract v1 — durable real-data/user-entered surface.

Why this module exists
----------------------
Up to PR #296 the legacy ``_mock_flights`` helper in
``backend/app/services/search.py`` could fabricate flight rows with
``source="mock"`` and ``book.example.com`` booking URLs.  PR #295 added a
fail-closed guard at ``/trips/create-with-search`` and at
``OptimizeTripModal`` so those rows can no longer be persisted or shown as
real bookable inventory.  The legacy mock is now quarantined but not yet
replaced.

Flights Product Contract v1 codifies the invariants the next provider-backed
Flights v1 PR has to honor.  It is intentionally:

- transport-agnostic (no FastAPI/Supabase imports);
- pydantic-free at the contract surface (the wire model
  ``backend/app/models/search.py::FlightResult`` already exists; the contract
  validates instances of it without redefining the schema);
- decision-only — it does not call providers, hit a cache, or persist rows.

Scope of v1
-----------
1. Allowed flight data sources (``FlightSource``).
2. Disallowed source markers and the ``book.example.com`` booking-host
   sentinel (``DISALLOWED_SOURCES``, ``MOCK_BOOKING_HOST``).
3. Required fields a flight must carry to be persistable
   (``REQUIRED_PERSIST_FIELDS``).
4. Round-trip leg type (``FlightLeg``) and day mapping helpers
   (``outbound_day_index``, ``return_day_index``, ``leg_day_index``).
5. Source status enum (``FlightSourceStatus``) the provider seam returns
   in lieu of an exception so unavailable / error states stay typed.
6. Persistability predicate (``is_persistable_flight``,
   ``assert_persistable_flight``) — the single source of truth that backs
   ``backend/app/routes/trips.py::_is_mock_flight``.
7. Provider seam reference type (``FlightProviderUnavailable``) — see
   ``backend/app/services/flights_provider.py`` for the runtime seam.

This module never calls a provider, does not depend on a real API key, and
adds zero LLM calls.  It is the bridge from the urgent mock-cleanup track
to the upcoming provider-backed Flights v1 product track.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any, Iterable, Optional


# ---------------------------------------------------------------------------
# Sources — provider-backed and user-entered are the only allowed shapes.
# Everything else is mock/demo/sample/fixture/placeholder and must fail
# closed at the persistence boundary.
# ---------------------------------------------------------------------------


class FlightSource(str, Enum):
    """Allowed values for ``FlightResult.source`` once Flights v1 ships.

    The contract is a positive list: only sources in this enum are eligible
    for persistence.  ``provider_backed`` is a generic umbrella; concrete
    providers (e.g. ``amadeus``, ``duffel``, ``google_flights``) map onto it
    via ``ALLOWED_SOURCE_VALUES``.  ``user_entered`` covers manual entry.
    """

    PROVIDER_BACKED = "provider_backed"
    USER_ENTERED = "user_entered"


# Concrete ``FlightResult.source`` strings the contract recognises as
# provider-backed.  The list is conservative: extending it requires adding a
# matching provider seam adapter and an explicit test in
# ``test_flights_product_contract_v1.py``.
PROVIDER_BACKED_SOURCE_VALUES: frozenset = frozenset({
    "amadeus",
    "duffel",
    "google_flights",
    "kiwi",
    "skyscanner",
    "provider_backed",
})

USER_ENTERED_SOURCE_VALUES: frozenset = frozenset({
    "user_entered",
    "manual",
})

ALLOWED_SOURCE_VALUES: frozenset = (
    PROVIDER_BACKED_SOURCE_VALUES | USER_ENTERED_SOURCE_VALUES
)

# Source markers explicitly disallowed for persistence.  Mirrors the legacy
# fixture vocabulary in ``backend/app/services/search.py``; new mock-like
# markers must be added here, not silently allowed through.
DISALLOWED_SOURCES: frozenset = frozenset({
    "mock",
    "demo",
    "fixture",
    "sample",
    "placeholder",
})

# Sentinel substring stamped into every legacy ``_mock_flights`` /
# ``_mock_hotels`` booking URL.  Any URL containing this host is, by
# construction, fabricated and must never be persisted or rendered as
# real bookable inventory.
MOCK_BOOKING_HOST: str = "book.example.com"

# Additional sentinels for fabricated/demo booking domains.  The set is
# intentionally narrow — adding entries is fine; removing entries requires a
# matching test update.
FABRICATED_BOOKING_HOSTS: frozenset = frozenset({
    MOCK_BOOKING_HOST,
    "example.com",
    "example.org",
})


# ---------------------------------------------------------------------------
# Source status — the provider seam returns this instead of raising so
# unavailable / error / empty cases stay typed and observable.
# ---------------------------------------------------------------------------


class FlightSourceStatus(str, Enum):
    """Typed health marker the provider seam returns alongside its rows.

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
# Round-trip leg type and day mapping
# ---------------------------------------------------------------------------


class FlightLeg(str, Enum):
    """Round-trip leg classification.

    The wire model ``RoundTripFlightPair`` already separates ``outbound``
    from ``return_flight``.  ``FlightLeg`` is the canonical string the rest
    of the system uses when persisting a single leg into ``itinerary_items``
    via the frontend ``addRoundTripOutboundToDay`` /
    ``addRoundTripReturnToDay`` helpers (see ``frontend/src/lib/api.ts``).
    """

    OUTBOUND = "outbound"
    RETURN = "return"


def outbound_day_index() -> int:
    """Day index the outbound leg maps to.

    Day 1 in product copy is index ``0`` in the zero-based ``trip_days``
    list.  Centralising this here means the provider PR cannot accidentally
    reintroduce a "first day with capacity" heuristic that could place the
    outbound leg on Day 2.
    """
    return 0


def return_day_index(num_days: int) -> int:
    """Day index the return leg maps to, for a trip of ``num_days`` days.

    Returns the final day's zero-based index.  ``num_days`` is the total
    number of trip days (``end_date - start_date + 1``).  A one-day trip
    collapses both legs onto the same day, which matches the product
    behaviour for a same-day round trip.
    """
    if num_days <= 0:
        raise ValueError("num_days must be >= 1")
    return num_days - 1


def leg_day_index(leg: FlightLeg, num_days: int) -> int:
    """Map a leg to its zero-based day index.

    Centralises the ``outbound → Day 1`` / ``return → final day`` invariant
    so future providers / persistence callers cannot drift.
    """
    if leg is FlightLeg.OUTBOUND:
        return outbound_day_index()
    if leg is FlightLeg.RETURN:
        return return_day_index(num_days)
    raise ValueError(f"unknown leg: {leg!r}")


def trip_num_days(start: date, end: date) -> int:
    """Inclusive day count for a trip from ``start`` to ``end``."""
    if end < start:
        raise ValueError("end < start")
    return (end - start).days + 1


# ---------------------------------------------------------------------------
# Persistability — single source of truth for "is this flight a real,
# user-readable, bookable row".
# ---------------------------------------------------------------------------


# Required fields a flight row must carry to be persistable.  Names match the
# wire model ``backend/app/models/search.py::FlightResult`` so the predicate
# can use ``getattr`` without re-deriving a schema.
REQUIRED_PERSIST_FIELDS: tuple = (
    "source",
    "airline",
    "origin",
    "destination",
    "departure_time",
    "arrival_time",
)


@dataclass(frozen=True)
class PersistabilityFailure:
    """Why a flight row failed the contract.  Human-readable + machine-keyed."""

    code: str
    field: Optional[str]
    message: str


def _has_fabricated_host(url: Optional[str]) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return any(host in lowered for host in FABRICATED_BOOKING_HOSTS)


def _booking_options_iter(flight: Any) -> Iterable[Any]:
    return list(getattr(flight, "booking_options", None) or [])


def check_persistable_flight(flight: Any) -> Optional[PersistabilityFailure]:
    """Return ``None`` if ``flight`` is persistable, else a typed failure.

    Trip persistence callers should use ``is_persistable_flight`` /
    ``assert_persistable_flight`` for the boolean / raise variants.  This
    helper exposes the structured failure for telemetry and tests.
    """
    source_raw = getattr(flight, "source", None)
    source = (str(source_raw) if source_raw is not None else "").strip().lower()

    if not source:
        return PersistabilityFailure(
            code="missing_source", field="source",
            message="flight.source is required",
        )

    if source in DISALLOWED_SOURCES:
        return PersistabilityFailure(
            code="disallowed_source", field="source",
            message=f"flight.source={source!r} is mock/demo/fixture",
        )

    if source not in ALLOWED_SOURCE_VALUES:
        return PersistabilityFailure(
            code="unrecognised_source", field="source",
            message=(
                f"flight.source={source!r} is not in the Flights Product "
                f"Contract v1 allowed list"
            ),
        )

    primary_url = getattr(flight, "booking_url", None)
    if _has_fabricated_host(primary_url):
        return PersistabilityFailure(
            code="fabricated_booking_url", field="booking_url",
            message=f"booking_url uses fabricated host: {primary_url!r}",
        )

    for opt in _booking_options_iter(flight):
        opt_url = getattr(opt, "url", None) or (
            opt.get("url") if isinstance(opt, dict) else None
        )
        if _has_fabricated_host(opt_url):
            return PersistabilityFailure(
                code="fabricated_booking_option_url", field="booking_options[].url",
                message=f"booking_options carries fabricated host: {opt_url!r}",
            )

    for fname in REQUIRED_PERSIST_FIELDS:
        if getattr(flight, fname, None) in (None, ""):
            return PersistabilityFailure(
                code="missing_required_field", field=fname,
                message=f"flight.{fname} is required for persistence",
            )

    return None


def is_persistable_flight(flight: Any) -> bool:
    """True iff ``flight`` satisfies Flights Product Contract v1."""
    return check_persistable_flight(flight) is None


def is_mock_derived_flight(flight: Any) -> bool:
    """True iff ``flight`` is mock/demo/fabricated (legacy fail-closed gate).

    This is the predicate ``backend/app/routes/trips.py::_is_mock_flight``
    delegates to.  It is intentionally narrower than
    ``not is_persistable_flight``: a flight missing ``airline`` is not
    persistable, but it is also not "mock-derived".  Callers that need to
    block mocks specifically (e.g. PR #295's persistence guard) use this;
    callers that need full contract validation use
    ``is_persistable_flight``.
    """
    source_raw = getattr(flight, "source", None)
    source = (str(source_raw) if source_raw is not None else "").strip().lower()
    if source in DISALLOWED_SOURCES:
        return True
    if _has_fabricated_host(getattr(flight, "booking_url", None)):
        return True
    for opt in _booking_options_iter(flight):
        opt_url = getattr(opt, "url", None) or (
            opt.get("url") if isinstance(opt, dict) else None
        )
        if _has_fabricated_host(opt_url):
            return True
    return False


class FlightContractViolation(ValueError):
    """Raised by ``assert_persistable_flight`` on contract failure.

    Carries the structured ``PersistabilityFailure`` so callers can map onto
    HTTP status / log fields without parsing the message.
    """

    def __init__(self, failure: PersistabilityFailure) -> None:
        super().__init__(failure.message)
        self.failure = failure


def assert_persistable_flight(flight: Any) -> None:
    failure = check_persistable_flight(flight)
    if failure is not None:
        raise FlightContractViolation(failure)


# ---------------------------------------------------------------------------
# Provider seam reference type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FlightProviderUnavailable:
    """Typed unavailable state returned by ``NullFlightProvider``.

    The runtime seam lives in ``backend/app/services/flights_provider.py``;
    this dataclass is re-exported here so contract callers don't need a
    second import.  ``status`` is one of ``UNAVAILABLE`` / ``ERROR``.
    ``reason`` is a human-readable string for logs/UI copy.
    """

    status: FlightSourceStatus
    reason: str

    def __post_init__(self) -> None:
        if self.status not in {FlightSourceStatus.UNAVAILABLE, FlightSourceStatus.ERROR}:
            raise ValueError(
                "FlightProviderUnavailable.status must be UNAVAILABLE or ERROR"
            )


# Public re-export surface for the v1 regression test suite.
__all__ = [
    "ALLOWED_SOURCE_VALUES",
    "DISALLOWED_SOURCES",
    "FABRICATED_BOOKING_HOSTS",
    "FlightContractViolation",
    "FlightLeg",
    "FlightProviderUnavailable",
    "FlightSource",
    "FlightSourceStatus",
    "MOCK_BOOKING_HOST",
    "PROVIDER_BACKED_SOURCE_VALUES",
    "PersistabilityFailure",
    "REQUIRED_PERSIST_FIELDS",
    "USER_ENTERED_SOURCE_VALUES",
    "assert_persistable_flight",
    "check_persistable_flight",
    "is_mock_derived_flight",
    "is_persistable_flight",
    "leg_day_index",
    "outbound_day_index",
    "return_day_index",
    "trip_num_days",
]
