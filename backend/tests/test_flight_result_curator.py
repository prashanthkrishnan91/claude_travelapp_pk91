from datetime import datetime, timedelta

from app.models.search import FlightResult
from app.services.flight_result_curator import curate_flight_results


def _row(idx: int, *, price: float, stops: int, duration: int, dep_hour: int = 9, airline: str = "Air A", flight_number: str = "AA100") -> FlightResult:
    dep = datetime(2026, 7, 1, dep_hour, 0)
    return FlightResult(
        id=f"f{idx}",
        price=price,
        location="JFK→LAX",
        booking_url=f"https://book.real/{idx}",
        source="duffel",
        booking_options=[],
        airline=airline,
        flight_number=flight_number,
        origin="JFK",
        destination="LAX",
        departure_time=dep,
        arrival_time=dep + timedelta(minutes=duration),
        duration_minutes=duration,
        stops=stops,
        cabin_class="economy",
    )


def test_dedupes_same_itinerary_keeps_cheapest():
    a = _row(1, price=600, stops=0, duration=350)
    b = a.model_copy(update={"id": "f2", "price": 499})
    curated, summary = curate_flight_results([a, b])
    assert summary.raw_count == 2
    assert summary.deduped_count == 1
    assert curated[0].price == 499


def test_ranking_prefers_nonstop_reasonable_over_absurd_cheap_long():
    good = _row(1, price=450, stops=0, duration=360)
    absurd = _row(2, price=300, stops=2, duration=1600, dep_hour=5, flight_number="AA200")
    curated, _ = curate_flight_results([absurd, good])
    assert curated[0].id == "f1"


def test_preserves_value_onestop_when_good():
    nonstop = _row(1, price=700, stops=0, duration=350, flight_number="AA100")
    onestop_value = _row(2, price=420, stops=1, duration=420, flight_number="AA200")
    curated, _ = curate_flight_results([nonstop, onestop_value])
    ids = [r.id for r in curated]
    assert "f1" in ids
    assert "f2" in ids


def test_caps_and_stable_ordering():
    rows = [_row(i, price=500 + i, stops=0, duration=300 + i, dep_hour=(i % 10), flight_number=f"AA{i}") for i in range(1, 30)]
    curated1, _ = curate_flight_results(rows)
    curated2, _ = curate_flight_results(rows)
    assert len(curated1) == 12
    assert [r.id for r in curated1] == [r.id for r in curated2]
