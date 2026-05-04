"""Unit tests for ContinuationResultPool (app.concierge.result_pool)."""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Minimal stubs so imports work without full stack
import types
from unittest.mock import MagicMock

for _mod in ["fastapi", "supabase", "anthropic"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from app.concierge.result_pool import ContinuationResultPool, _GLOBAL_CONTINUATION_POOL

TRIP_A = "trip-aaa-001"
TRIP_B = "trip-bbb-002"
CANONICAL = "mexican restaurants"


def _card(name: str) -> Dict[str, Any]:
    return {
        "name": name,
        "google_verification": {
            "provider": "google_places",
            "business_status": "OPERATIONAL",
            "provider_place_id": f"pid-{name.lower()}",
            "google_maps_uri": f"https://maps.google.com/?cid={name.lower()}",
            "name": name,
            "formatted_address": f"123 {name} St, Chicago IL",
        },
    }


def _buckets(restaurants: List[str] = (), attractions: List[str] = (), hotels: List[str] = ()) -> Dict[str, List]:
    return {
        "restaurants": [_card(n) for n in restaurants],
        "attractions": [_card(n) for n in attractions],
        "hotels": [_card(n) for n in hotels],
    }


@pytest.fixture(autouse=True)
def _fresh_pool():
    pool = ContinuationResultPool(ttl_seconds=60)
    return pool


def test_store_and_pop_returns_cards(_fresh_pool) -> None:
    _fresh_pool.store(TRIP_A, CANONICAL, _buckets(restaurants=["Taco1", "Taco2"]))
    result = _fresh_pool.pop(TRIP_A, CANONICAL)
    assert result is not None
    buckets, total = result
    assert total == 2
    names = {c["name"] for c in buckets["restaurants"]}
    assert names == {"Taco1", "Taco2"}


def test_pop_clears_entry(_fresh_pool) -> None:
    _fresh_pool.store(TRIP_A, CANONICAL, _buckets(restaurants=["Taco1"]))
    _fresh_pool.pop(TRIP_A, CANONICAL)
    # Second pop must return None
    assert _fresh_pool.pop(TRIP_A, CANONICAL) is None


def test_pop_miss_returns_none(_fresh_pool) -> None:
    assert _fresh_pool.pop(TRIP_A, CANONICAL) is None


def test_pop_expired_returns_none() -> None:
    pool = ContinuationResultPool(ttl_seconds=0)
    pool.store(TRIP_A, CANONICAL, _buckets(restaurants=["X"]))
    time.sleep(0.01)  # ensure expired
    assert pool.pop(TRIP_A, CANONICAL) is None


def test_different_trip_ids_isolated(_fresh_pool) -> None:
    _fresh_pool.store(TRIP_A, CANONICAL, _buckets(restaurants=["TacoA"]))
    _fresh_pool.store(TRIP_B, CANONICAL, _buckets(restaurants=["TacoB"]))
    result_a = _fresh_pool.pop(TRIP_A, CANONICAL)
    result_b = _fresh_pool.pop(TRIP_B, CANONICAL)
    assert result_a is not None and result_b is not None
    names_a = {c["name"] for c in result_a[0]["restaurants"]}
    names_b = {c["name"] for c in result_b[0]["restaurants"]}
    assert names_a == {"TacoA"}
    assert names_b == {"TacoB"}


def test_different_canonical_queries_isolated(_fresh_pool) -> None:
    _fresh_pool.store(TRIP_A, "mexican restaurants", _buckets(restaurants=["Taco"]))
    _fresh_pool.store(TRIP_A, "italian restaurants", _buckets(restaurants=["Pizza"]))
    mex = _fresh_pool.pop(TRIP_A, "mexican restaurants")
    ita = _fresh_pool.pop(TRIP_A, "italian restaurants")
    assert mex is not None and ita is not None
    assert {c["name"] for c in mex[0]["restaurants"]} == {"Taco"}
    assert {c["name"] for c in ita[0]["restaurants"]} == {"Pizza"}


def test_clear_removes_all_entries_for_trip(_fresh_pool) -> None:
    _fresh_pool.store(TRIP_A, "mexican restaurants", _buckets(restaurants=["Taco"]))
    _fresh_pool.store(TRIP_A, "italian restaurants", _buckets(restaurants=["Pizza"]))
    _fresh_pool.store(TRIP_B, "cocktail bars", _buckets(restaurants=["Bar"]))
    _fresh_pool.clear(TRIP_A)
    assert _fresh_pool.pop(TRIP_A, "mexican restaurants") is None
    assert _fresh_pool.pop(TRIP_A, "italian restaurants") is None
    # TRIP_B pool must be unaffected
    assert _fresh_pool.pop(TRIP_B, "cocktail bars") is not None


def test_pool_size_reflects_stored_entries(_fresh_pool) -> None:
    assert _fresh_pool.pool_size() == 0
    _fresh_pool.store(TRIP_A, CANONICAL, _buckets(restaurants=["X"]))
    assert _fresh_pool.pool_size() == 1
    _fresh_pool.store(TRIP_B, CANONICAL, _buckets(restaurants=["Y"]))
    assert _fresh_pool.pool_size() == 2
    _fresh_pool.pop(TRIP_A, CANONICAL)
    assert _fresh_pool.pool_size() == 1


def test_canonical_query_normalised_case_insensitive(_fresh_pool) -> None:
    _fresh_pool.store(TRIP_A, "Mexican Restaurants", _buckets(restaurants=["Taco"]))
    result = _fresh_pool.pop(TRIP_A, "mexican restaurants")
    assert result is not None


def test_store_overwrites_existing_entry(_fresh_pool) -> None:
    _fresh_pool.store(TRIP_A, CANONICAL, _buckets(restaurants=["OldCard"]))
    _fresh_pool.store(TRIP_A, CANONICAL, _buckets(restaurants=["NewCard"]))
    result = _fresh_pool.pop(TRIP_A, CANONICAL)
    assert result is not None
    names = {c["name"] for c in result[0]["restaurants"]}
    assert names == {"NewCard"}
    assert "OldCard" not in names
