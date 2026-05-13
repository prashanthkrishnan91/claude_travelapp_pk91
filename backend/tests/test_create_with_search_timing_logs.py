import os
from pathlib import Path


def test_create_with_search_emits_required_timing_phases():
    src = Path(__file__).resolve().parents[1] / "app" / "routes" / "trips.py"
    text = src.read_text()
    required = [
        "phase=airport_resolution",
        "phase=provider_search",
        "phase=trip_create",
        "phase=ensure_trip_days",
        "phase=persist_flights",
        "phase=persist_hotels",
        "phase=persist_attractions",
        "phase=persist_restaurants",
        "phase=total",
    ]
    for phase in required:
        assert phase in text, f"missing timing phase log: {phase}"
