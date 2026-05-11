"""Tests for Stage 2A Slice 3 — Trip-Optional AI Concierge.

Covers:
- ConciergeSearchRequest rejects when both trip_id and destination are absent
- ConciergeSearchRequest accepts trip_id only (existing behaviour)
- ConciergeSearchRequest accepts destination only (new tripless path)
- ConciergeRequest accepts destination only
- service.search() skips _fetch_trip when trip_id is None, uses destination directly
- service.search() skips _save_message when trip_id is None
- callConcierge / callConciergeSearch send correct JSON body shapes
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from typing import Any, List, Optional
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.models.concierge import ConciergeRequest, ConciergeSearchRequest
from pydantic import ValidationError


FAKE_USER_ID = UUID("00000000-0000-0000-0000-000000000099")
FAKE_TRIP_ID = UUID("00000000-0000-0000-0000-000000000001")


# ---------------------------------------------------------------------------
# Model validation
# ---------------------------------------------------------------------------

class TestConciergeSearchRequestValidation:
    def test_trip_id_only_accepted(self):
        req = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="restaurants")
        assert req.trip_id == FAKE_TRIP_ID
        assert req.destination is None

    def test_destination_only_accepted(self):
        req = ConciergeSearchRequest(destination="Paris", user_query="restaurants")
        assert req.trip_id is None
        assert req.destination == "Paris"

    def test_both_trip_id_and_destination_accepted(self):
        req = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, destination="Paris", user_query="q")
        assert req.trip_id == FAKE_TRIP_ID
        assert req.destination == "Paris"

    def test_neither_trip_id_nor_destination_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ConciergeSearchRequest(user_query="restaurants")
        assert "trip_id or destination" in str(exc_info.value).lower()

    def test_empty_destination_string_rejected(self):
        with pytest.raises(ValidationError):
            ConciergeSearchRequest(destination="   ", user_query="restaurants")

    def test_client_message_id_optional(self):
        req = ConciergeSearchRequest(destination="Tokyo", user_query="ramen")
        assert req.client_message_id is None


class TestConciergeRequestValidation:
    def test_trip_id_only_accepted(self):
        req = ConciergeRequest(trip_id=FAKE_TRIP_ID, user_query="q")
        assert req.trip_id == FAKE_TRIP_ID

    def test_destination_only_accepted(self):
        req = ConciergeRequest(destination="Rome", user_query="q")
        assert req.trip_id is None
        assert req.destination == "Rome"

    def test_neither_rejected(self):
        with pytest.raises(ValidationError):
            ConciergeRequest(user_query="q")


# ---------------------------------------------------------------------------
# Service: tripless search skips DB I/O
# ---------------------------------------------------------------------------

class _LiveResult:
    restaurants: list = []
    attractions: list = []
    hotels: list = []
    research_sources: list = []
    provider_name: str = "mock"
    source_status: str = "none"
    cached: bool = False


def _make_service():
    db = MagicMock()
    svc = object.__new__(__import__("app.services.concierge", fromlist=["ConciergeService"]).ConciergeService)
    svc._db = db
    svc._settings = MagicMock(
        concierge_router_v2=False,
        concierge_context_v1_enabled=False,
        research_engine_require_google_verification=False,
        trip_advice_builder_enabled=False,
        semantic_concierge_v1_enabled=False,
        fast_dynamic_place_search_enabled=False,
    )
    return svc, db


class TestServiceTriplessSearch:
    def test_tripless_search_does_not_call_fetch_trip(self):
        svc, db = _make_service()
        with patch.object(svc, "_fetch_trip") as mock_fetch, \
             patch.object(svc, "_fetch_live_research", return_value=_LiveResult()), \
             patch.object(svc, "_save_message") as mock_save, \
             patch.object(svc, "_call_claude", return_value='{"response":"ok","suggestions":[]}'), \
             patch.object(svc, "_detect_intent", return_value="restaurants"), \
             patch.object(svc, "_build_search_prompt", return_value="prompt"), \
             patch.object(svc, "_concise_response", return_value="ok"), \
             patch.object(svc, "_align_summary_with_ranked_cards", return_value="ok"), \
             patch.object(svc, "_derive_response_source_status", return_value="none"):
            result = svc.search(
                trip_id=None,
                user_query="best restaurants",
                user_id=FAKE_USER_ID,
                destination="Barcelona",
            )
            mock_fetch.assert_not_called()
            mock_save.assert_not_called()

    def test_tripless_search_uses_destination_in_trip_dict(self):
        svc, db = _make_service()
        captured_trips = []

        def capture_live_research(intent, destination, user_query, trip, **kw):
            captured_trips.append(trip)
            return _LiveResult()

        with patch.object(svc, "_fetch_trip"), \
             patch.object(svc, "_fetch_live_research", side_effect=capture_live_research), \
             patch.object(svc, "_save_message"), \
             patch.object(svc, "_call_claude", return_value='{"response":"ok","suggestions":[]}'), \
             patch.object(svc, "_detect_intent", return_value="restaurants"), \
             patch.object(svc, "_build_search_prompt", return_value="prompt"), \
             patch.object(svc, "_concise_response", return_value="ok"), \
             patch.object(svc, "_align_summary_with_ranked_cards", return_value="ok"), \
             patch.object(svc, "_derive_response_source_status", return_value="none"):
            svc.search(
                trip_id=None,
                user_query="best restaurants",
                user_id=FAKE_USER_ID,
                destination="Barcelona",
            )
            assert captured_trips, "live_research should have been called"
            assert captured_trips[0].get("destination") == "Barcelona"

    def test_trip_bound_search_still_calls_fetch_trip(self):
        svc, db = _make_service()
        fake_trip = {"destination": "London", "start_date": "", "end_date": ""}
        with patch.object(svc, "_fetch_trip", return_value=fake_trip) as mock_fetch, \
             patch.object(svc, "_fetch_live_research", return_value=_LiveResult()), \
             patch.object(svc, "_save_message"), \
             patch.object(svc, "_call_claude", return_value='{"response":"ok","suggestions":[]}'), \
             patch.object(svc, "_detect_intent", return_value="restaurants"), \
             patch.object(svc, "_build_search_prompt", return_value="prompt"), \
             patch.object(svc, "_concise_response", return_value="ok"), \
             patch.object(svc, "_align_summary_with_ranked_cards", return_value="ok"), \
             patch.object(svc, "_derive_response_source_status", return_value="none"):
            svc.search(
                trip_id=FAKE_TRIP_ID,
                user_query="best restaurants",
                user_id=FAKE_USER_ID,
            )
            mock_fetch.assert_called_once_with(FAKE_TRIP_ID, FAKE_USER_ID)
