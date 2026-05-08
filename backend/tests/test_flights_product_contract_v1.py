"""Flights Product Contract v1 — invariant regression suite.

These tests prove the contract module + provider seam + persistence guards
hold the line declared in ``backend/app/contracts/flights.py``.  They MUST
NOT make network calls, hit Supabase, or boot FastAPI: the contract is
transport-agnostic by design.

Coverage:

1. mock/demo/sample/book.example.com flight rows cannot be persisted
2. unavailable provider state fails closed with typed shape
3. outbound leg maps to Day 1 (zero-based 0)
4. return leg maps to final trip day (zero-based num_days-1)
5. partial round-trip data does not invent the missing leg
6. provider seam returns typed unavailable state without fake rows
7. existing fail-closed behaviour from PR #295 remains intact (cross-check)
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.contracts.flights import (
    ALLOWED_SOURCE_VALUES,
    DISALLOWED_SOURCES,
    FABRICATED_BOOKING_HOSTS,
    FlightContractViolation,
    FlightLeg,
    FlightProviderUnavailable,
    FlightSourceStatus,
    MOCK_BOOKING_HOST,
    REQUIRED_PERSIST_FIELDS,
    assert_persistable_flight,
    check_persistable_flight,
    is_mock_derived_flight,
    is_persistable_flight,
    leg_day_index,
    outbound_day_index,
    return_day_index,
    trip_num_days,
)
from app.services.flights_provider import (
    FlightProviderResult,
    NullFlightProvider,
    get_flight_provider,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _flight(**overrides):
    from app.models.search import BookingOption, FlightResult  # noqa: WPS433
    base = dict(
        id="f1",
        price=499.0,
        rating=4.5,
        location="JFK→CDG",
        booking_url="https://amadeus.example/flights/AA100",
        source="amadeus",
        booking_options=[],
        airline="American Airlines",
        flight_number="AA100",
        origin="JFK",
        destination="CDG",
        departure_time=datetime(2026, 6, 1, 9, 0),
        arrival_time=datetime(2026, 6, 1, 21, 0),
        duration_minutes=720,
        stops=0,
        cabin_class="economy",
    )
    base.update(overrides)
    if "booking_options_raw" in base:
        base["booking_options"] = [
            BookingOption(**opt) for opt in base.pop("booking_options_raw")
        ]
    return FlightResult(**base)


# ---------------------------------------------------------------------------
# 1. Disallowed sources / fabricated hosts cannot be persisted
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_source", sorted(DISALLOWED_SOURCES))
def test_mock_marker_blocks_persistence(bad_source):
    f = _flight(source=bad_source)
    assert is_mock_derived_flight(f) is True
    assert is_persistable_flight(f) is False
    failure = check_persistable_flight(f)
    assert failure is not None
    assert failure.code == "disallowed_source"


def test_book_example_primary_url_blocks_persistence():
    f = _flight(
        source="amadeus",
        booking_url=f"https://{MOCK_BOOKING_HOST}/flights/aa/jfk/cdg",
    )
    assert is_mock_derived_flight(f) is True
    failure = check_persistable_flight(f)
    assert failure is not None
    assert failure.code == "fabricated_booking_url"


def test_book_example_in_options_blocks_persistence():
    f = _flight(
        source="amadeus",
        booking_url="https://amadeus.example/x",
        booking_options_raw=[
            {"provider": "kayak", "url": f"https://{MOCK_BOOKING_HOST}/y"},
        ],
    )
    assert is_mock_derived_flight(f) is True
    failure = check_persistable_flight(f)
    assert failure is not None
    assert failure.code == "fabricated_booking_option_url"


def test_assert_persistable_raises_typed_violation():
    with pytest.raises(FlightContractViolation) as excinfo:
        assert_persistable_flight(_flight(source="mock"))
    assert excinfo.value.failure.code == "disallowed_source"
    assert excinfo.value.failure.field == "source"


def test_unrecognised_source_blocks_persistence():
    f = _flight(source="some_random_provider_we_didnt_audit")
    assert is_persistable_flight(f) is False
    failure = check_persistable_flight(f)
    assert failure.code == "unrecognised_source"


@pytest.mark.parametrize("good_source", sorted(ALLOWED_SOURCE_VALUES))
def test_allowed_sources_pass_when_clean(good_source):
    f = _flight(source=good_source, booking_url="https://example-airline.test/x")
    # example-airline.test is not in fabricated hosts; "amadeus.example/" was
    # safe for the default helper because "example.com"/"example.org" are.
    assert is_persistable_flight(f) is True
    assert is_mock_derived_flight(f) is False


def test_user_entered_with_no_booking_url_is_persistable():
    # Manual entry: user types airline + flight number without a booking link.
    f = _flight(source="user_entered", booking_url="")
    # Note: booking_url is required="" by pydantic? FlightResult.booking_url is
    # str (required).  An empty string is allowed by pydantic but not a host
    # collision; the contract treats empty URLs as "no fabricated host", and
    # all required fields are present.
    assert is_persistable_flight(f) is True


# ---------------------------------------------------------------------------
# 2 & 6. Provider seam returns typed unavailable state
# ---------------------------------------------------------------------------


def test_null_provider_returns_typed_unavailable():
    from app.models.search import FlightSearchRequest  # noqa: WPS433
    provider = NullFlightProvider()
    result = provider.search_flights(FlightSearchRequest(
        origin="JFK", destination="CDG", departure_date=date(2026, 6, 1),
    ))
    assert isinstance(result, FlightProviderResult)
    assert result.status is FlightSourceStatus.UNAVAILABLE
    assert result.rows == []
    assert result.reason  # non-empty human reason


def test_null_provider_unavailable_dataclass():
    unavailable = NullFlightProvider().unavailable()
    assert isinstance(unavailable, FlightProviderUnavailable)
    assert unavailable.status is FlightSourceStatus.UNAVAILABLE
    assert unavailable.reason


def test_default_flight_provider_is_null():
    # Until Flights v1 lands, the default registry must NOT bind a real
    # adapter or the legacy mock.
    provider = get_flight_provider()
    assert isinstance(provider, NullFlightProvider)


def test_provider_unavailable_rejects_ok_status():
    with pytest.raises(ValueError):
        FlightProviderUnavailable(status=FlightSourceStatus.OK, reason="bad")


# ---------------------------------------------------------------------------
# FlightProviderResult invariant enforcement
# ---------------------------------------------------------------------------


def test_provider_result_unavailable_with_rows_is_rejected():
    clean = _flight(source="amadeus", booking_url="https://amadeus.example/x")
    with pytest.raises(ValueError, match="must carry zero rows"):
        FlightProviderResult(
            status=FlightSourceStatus.UNAVAILABLE,
            rows=[clean],
            reason="bug",
        )


def test_provider_result_error_with_rows_is_rejected():
    clean = _flight(source="amadeus", booking_url="https://amadeus.example/x")
    with pytest.raises(ValueError, match="must carry zero rows"):
        FlightProviderResult(
            status=FlightSourceStatus.ERROR,
            rows=[clean],
            reason="upstream 500",
        )


def test_provider_result_empty_with_rows_is_rejected():
    clean = _flight(source="amadeus", booking_url="https://amadeus.example/x")
    with pytest.raises(ValueError, match="must carry zero rows"):
        FlightProviderResult(status=FlightSourceStatus.EMPTY, rows=[clean])


def test_provider_result_ok_with_mock_source_is_rejected():
    bad = _flight(source="mock", booking_url="https://amadeus.example/x")
    with pytest.raises(ValueError, match="Flights Product Contract"):
        FlightProviderResult(status=FlightSourceStatus.OK, rows=[bad])


def test_provider_result_ok_with_book_example_url_is_rejected():
    bad = _flight(
        source="amadeus",
        booking_url=f"https://{MOCK_BOOKING_HOST}/flights/aa/jfk/cdg",
    )
    with pytest.raises(ValueError, match="Flights Product Contract"):
        FlightProviderResult(status=FlightSourceStatus.OK, rows=[bad])


def test_provider_result_ok_with_clean_provider_row_is_accepted():
    clean = _flight(source="amadeus", booking_url="https://amadeus.example/x")
    result = FlightProviderResult(status=FlightSourceStatus.OK, rows=[clean])
    assert result.status is FlightSourceStatus.OK
    assert result.rows == [clean]


def test_provider_result_empty_with_no_rows_is_accepted():
    result = FlightProviderResult(status=FlightSourceStatus.EMPTY)
    assert result.status is FlightSourceStatus.EMPTY
    assert result.rows == []


def test_provider_result_ok_with_zero_rows_is_rejected():
    """OK + zero rows is a contract bug: callers must use EMPTY instead."""
    with pytest.raises(ValueError, match="EMPTY"):
        FlightProviderResult(status=FlightSourceStatus.OK, rows=[])


# ---------------------------------------------------------------------------
# 3 & 4. Round-trip leg → day mapping
# ---------------------------------------------------------------------------


def test_outbound_maps_to_day_one():
    assert outbound_day_index() == 0
    assert leg_day_index(FlightLeg.OUTBOUND, num_days=7) == 0
    # Day 1 invariant must not depend on trip length.
    for n in (1, 2, 7, 30):
        assert leg_day_index(FlightLeg.OUTBOUND, num_days=n) == 0


def test_return_maps_to_final_day():
    assert return_day_index(7) == 6
    assert leg_day_index(FlightLeg.RETURN, num_days=7) == 6
    # Same-day round trip collapses both legs onto day 0.
    assert leg_day_index(FlightLeg.RETURN, num_days=1) == 0


def test_trip_num_days_inclusive():
    assert trip_num_days(date(2026, 6, 1), date(2026, 6, 7)) == 7
    assert trip_num_days(date(2026, 6, 1), date(2026, 6, 1)) == 1


def test_return_day_index_rejects_zero():
    with pytest.raises(ValueError):
        return_day_index(0)
    with pytest.raises(ValueError):
        trip_num_days(date(2026, 6, 7), date(2026, 6, 1))


# ---------------------------------------------------------------------------
# 5. Partial round-trip data does not invent the missing leg
# ---------------------------------------------------------------------------


def test_partial_round_trip_does_not_invent_return_leg():
    """The contract has no helper that fabricates a missing leg.

    This test guards against future code that might try to "complete" a
    one-way result into a round-trip pair.  We assert that the public
    contract surface contains no such helper.
    """
    import app.contracts.flights as contract  # noqa: WPS433
    forbidden_names = {
        "synthesize_return", "infer_return", "fabricate_return",
        "default_return_leg", "fill_missing_leg",
    }
    public = {n for n in dir(contract) if not n.startswith("_")}
    assert not (forbidden_names & public), (
        f"contract leaked leg-fabricating helper(s): {forbidden_names & public}"
    )


def test_partial_round_trip_provider_result_keeps_status_typed():
    """When only the outbound leg is available, the seam must not pad with
    a fake return; callers see ``OK`` (with one row) or ``EMPTY`` and decide
    UI copy.  This test pins the seam shape — no implicit pairing."""
    from app.models.search import FlightSearchRequest  # noqa: WPS433
    provider = NullFlightProvider()
    # Ask for a round-trip; the null seam returns UNAVAILABLE without inventing
    # legs.  A real adapter has the same contract.
    result = provider.search_flights(FlightSearchRequest(
        origin="JFK", destination="CDG",
        departure_date=date(2026, 6, 1), return_date=date(2026, 6, 7),
    ))
    assert result.rows == []
    assert result.status is FlightSourceStatus.UNAVAILABLE


# ---------------------------------------------------------------------------
# 7. Existing fail-closed behaviour (PR #295) — cross-check via delegate
# ---------------------------------------------------------------------------


def test_trips_route_is_mock_flight_delegates_to_contract():
    """The trips-route helper must delegate to the contract — otherwise
    the persistence guard could drift from the canonical predicate."""
    # Bypass app.routes.__init__.py (imports heavy ai.py deps) and load the
    # trips module directly from disk — same trick the
    # ``test_create_with_search_fail_closed.py`` suite uses.
    import importlib.util  # noqa: WPS433
    import os  # noqa: WPS433
    import sys  # noqa: WPS433
    import types  # noqa: WPS433
    from unittest.mock import MagicMock  # noqa: WPS433

    if "app.routes" not in sys.modules:
        pkg = types.ModuleType("app.routes")
        pkg.__path__ = [
            os.path.join(os.path.dirname(__file__), "..", "app", "routes")
        ]
        sys.modules["app.routes"] = pkg
    deps = sys.modules.setdefault("app.core.deps", types.ModuleType("app.core.deps"))
    if not hasattr(deps, "DB"):
        deps.DB = object
    if not hasattr(deps, "CurrentUserID"):
        deps.CurrentUserID = object
    services_pkg = sys.modules.get("app.services")
    if services_pkg is not None:
        import app.services.trips as _t  # noqa: WPS433
        import app.services.itinerary as _i  # noqa: WPS433
        import app.services.search as _s  # noqa: WPS433
        services_pkg.TripsService = _t.TripsService
        services_pkg.ItineraryService = _i.ItineraryService
        services_pkg.SearchService = _s.SearchService

    spec = importlib.util.spec_from_file_location(
        "app.routes._trips_isolated",
        os.path.join(
            os.path.dirname(__file__), "..", "app", "routes", "trips.py"
        ),
    )
    trips_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trips_module)
    _is_mock_flight = trips_module._is_mock_flight

    mock = _flight(source="mock", booking_url="https://book.example.com/x")
    clean = _flight(source="amadeus", booking_url="https://amadeus.example/x")

    assert _is_mock_flight(mock) is True
    assert _is_mock_flight(clean) is False
    # Delegation: behaviour must match the contract module directly.
    assert _is_mock_flight(mock) == is_mock_derived_flight(mock)
    assert _is_mock_flight(clean) == is_mock_derived_flight(clean)


# ---------------------------------------------------------------------------
# Contract surface stability
# ---------------------------------------------------------------------------


def test_required_persist_fields_includes_leg_essentials():
    for name in ("source", "airline", "origin", "destination",
                 "departure_time", "arrival_time"):
        assert name in REQUIRED_PERSIST_FIELDS


def test_mock_booking_host_is_in_fabricated_hosts():
    assert MOCK_BOOKING_HOST in FABRICATED_BOOKING_HOSTS
