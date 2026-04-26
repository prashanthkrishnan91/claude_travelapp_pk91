"""Tests for concierge typed contract + router v2."""

import os
import sys
from types import SimpleNamespace
import types
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from pydantic import TypeAdapter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

deps_mod = sys.modules.get("app.core.deps")
if deps_mod is None:
    deps_mod = types.ModuleType("app.core.deps")
    sys.modules["app.core.deps"] = deps_mod
setattr(deps_mod, "DB", object)
setattr(deps_mod, "CurrentUserID", object)

routes_pkg = types.ModuleType("app.routes")
routes_pkg.__path__ = [os.path.join(os.path.dirname(__file__), "..", "app", "routes")]
sys.modules["app.routes"] = routes_pkg

from app.concierge.contracts import (
    ConciergeTypedResponse,
    PlaceRecommendationsResponse,
    TripAdviceResponse,
    UnsupportedResponse,
)
from app.concierge.router import route_prompt
from app.models.concierge import ConciergeSearchRequest
from app.routes.ai import build_typed_concierge_response

FAKE_TRIP_ID = UUID("00000000-0000-0000-0000-000000000001")
FAKE_USER_ID = UUID("00000000-0000-0000-0000-000000000002")


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("best hotels in Chicago", "place_recommendations"),
        ("points vs cash ideas for Tokyo", "trip_advice"),
        ("Michelin restaurants in Honolulu", "place_recommendations"),
        ("things to do in Rome", "place_recommendations"),
        ("best area to stay in Paris", "place_recommendations"),
        ("hidden gem restaurants in Berlin", "place_recommendations"),
        ("family-friendly attractions in London", "place_recommendations"),
        ("nightlife bars in Barcelona", "place_recommendations"),
        ("", "unsupported"),
        ("hi", "unsupported"),
        ("hola", "unsupported"),
        ("bonjour", "unsupported"),
        ("visa requirements for japan", "trip_advice"),
        ("best way to redeem miles to Europe", "trip_advice"),
        ("card strategy for award flights", "trip_advice"),
        ("restaurants", "place_recommendations"),
        ("hotels", "place_recommendations"),
        ("????", "unsupported"),
        ("Tell me something cool", "unsupported"),
        ("Budget tips for summer travel", "trip_advice"),
        ("Compare points transfer partners", "trip_advice"),
        (
            "I need ideas for where to stay, what to eat, and what attractions are worth it in Chicago next month",
            "place_recommendations",
        ),
    ],
)
def test_route_prompt_fixtures(prompt: str, expected: str):
    decision = route_prompt(prompt, confidence_threshold=0.5)
    assert decision.response_type == expected
    assert decision.response_type in {"place_recommendations", "trip_advice", "unsupported"}


def test_route_prompt_returns_low_confidence_code_when_threshold_not_met():
    decision = route_prompt("maybe", confidence_threshold=0.95)
    assert decision.response_type == "unsupported"
    assert decision.code == "low_confidence"


def test_contract_round_trip_for_all_variants():
    adapter = TypeAdapter(ConciergeTypedResponse)

    place_payload = PlaceRecommendationsResponse(
        response="Top picks for Chicago.",
        intent="hotels",
        retrieval_used=True,
        source_status="none",
        restaurants=[],
        attractions=[],
        hotels=[],
        research_sources=[],
        areas=[],
        area_comparisons=[],
        suggestions=[],
        sources=[],
        warnings=[],
    )
    advice_payload = TripAdviceResponse(
        response="Use points when cpp is higher than your cash benchmark.",
        advice_sections=[{"heading": "Framework", "body_markdown": "Use CPP math."}],
        citations=[{"label": "Guide", "url": "https://example.com"}],
    )
    unsupported_payload = UnsupportedResponse(code="low_confidence", message="Needs clarification")

    for payload in (place_payload, advice_payload, unsupported_payload):
        dumped = payload.model_dump(mode="json")
        reparsed = adapter.validate_python(dumped)
        assert reparsed.response_type == payload.response_type


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("best hotels in Chicago", "place_recommendations"),
        ("points vs cash ideas", "trip_advice"),
        ("...", "unsupported"),
    ],
)
def test_concierge_search_integration_returns_typed_response(prompt: str, expected: str):
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query=prompt)
    fake_search_response = PlaceRecommendationsResponse(
        response="placeholder",
        intent="hotels",
        retrieval_used=True,
        source_status="none",
        restaurants=[],
        attractions=[],
        hotels=[],
        research_sources=[],
        areas=[],
        area_comparisons=[],
        suggestions=[],
        sources=[],
        warnings=[],
    )

    mock_service = MagicMock()
    mock_service.search.return_value = fake_search_response

    with patch("app.routes.ai.get_settings", return_value=SimpleNamespace(concierge_router_v2=True, concierge_router_v2_confidence_threshold=0.55, trip_advice_builder_enabled=True)), patch(
        "app.routes.ai.ConciergeService", return_value=mock_service
    ):
        result = build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    assert result.response_type == expected


@pytest.mark.parametrize(
    "prompt",
    [
        "points vs cash ideas",
        "should I use miles or cash for business class to Tokyo",
        "compare points transfer partners",
        "card strategy for award flights using miles",
        "booking timing for award flights with points",
    ],
)
def test_trip_advice_prompts_return_structured_sections(prompt: str):
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query=prompt)
    mock_service = MagicMock()

    with patch("app.routes.ai.get_settings", return_value=SimpleNamespace(concierge_router_v2=True, concierge_router_v2_confidence_threshold=0.55, trip_advice_builder_enabled=True)):
        result = build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    assert result.response_type == "trip_advice"
    assert len(result.advice_sections) >= 2
    assert len(result.advice_sections) <= 4
    assert all(section.heading.strip() for section in result.advice_sections)
    assert all(section.body_markdown.strip() for section in result.advice_sections)


def test_trip_advice_disabled_flag_returns_unsupported():
    payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query="points vs cash ideas")
    mock_service = MagicMock()

    with patch("app.routes.ai.get_settings", return_value=SimpleNamespace(concierge_router_v2=True, concierge_router_v2_confidence_threshold=0.55, trip_advice_builder_enabled=False)):
        result = build_typed_concierge_response(mock_service, payload, FAKE_USER_ID)

    assert result.response_type == "unsupported"
    assert result.code == "trip_advice_disabled"
