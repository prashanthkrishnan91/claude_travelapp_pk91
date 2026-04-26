"""Regression + observability tests for concierge routing."""

import os
import random
import string
import sys
from types import SimpleNamespace
import types
from uuid import UUID

from unittest.mock import MagicMock, patch

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

from app.concierge.contracts import ConciergeTypedResponse, PlaceRecommendationsResponse
from app.concierge.logging import persist_concierge_request_log, redact_prompt
from app.concierge.router import route_prompt
from app.db.mock import get_mock_client
from app.models.concierge import ConciergeSearchRequest
from app.routes.ai import build_typed_concierge_response

FAKE_TRIP_ID = UUID("00000000-0000-0000-0000-000000000011")
FAKE_USER_ID = UUID("00000000-0000-0000-0000-000000000012")


REGRESSION_PROMPTS = [
    "best hotels in chicago",
    "top restaurants in austin",
    "bars in nashville",
    "where to eat in madrid",
    "best things to do in seattle",
    "attractions in boston",
    "best neighborhood to stay in lisbon",
    "area to stay in tokyo",
    "family friendly attractions in london",
    "nightlife bars in barcelona",
    "points vs cash to paris",
    "miles redemption strategy for japan",
    "best card strategy for award flights",
    "transfer partners for amex points",
    "booking timing for award flights",
    "travel insurance for italy",
    "cancellation policy for flights",
    "budget planning for switzerland",
    "visa requirements for vietnam",
    "redeem points for business class",
    "hello",
    "???",
    "tell me a joke",
    "i like turtles",
    "help",
    "hotels and restaurants in rome",
    "attractions and bars in miami",
    "cash or points for hawaii hotels",
    "restaurants",
    "points",
]


def _mock_place_response() -> PlaceRecommendationsResponse:
    return PlaceRecommendationsResponse(
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
        sources=["https://example.com/source"],
        warnings=[],
    )


def test_regression_suite_30_prompts_validates_response_schema():
    adapter = TypeAdapter(ConciergeTypedResponse)
    service = MagicMock()
    service.search.return_value = _mock_place_response()

    with patch(
        "app.routes.ai.get_settings",
        return_value=SimpleNamespace(
            concierge_router_v2=True,
            concierge_router_v2_confidence_threshold=0.55,
            trip_advice_builder_enabled=True,
        ),
    ):
        for prompt in REGRESSION_PROMPTS:
            payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query=prompt)
            response, decision = build_typed_concierge_response(service, payload, FAKE_USER_ID)
            validated = adapter.validate_python(response.model_dump(mode="json"))
            assert validated.response_type in {"place_recommendations", "trip_advice", "unsupported"}
            assert 0 <= decision.stage2_confidence <= 1


def _random_prompt(rng: random.Random) -> str:
    keyword_pool = [
        "hotel", "restaurant", "points", "cash", "miles", "visa", "budget", "museum", "bar", "flight",
    ]
    noise = "".join(rng.choice(string.ascii_letters + string.digits + "   ???!!!") for _ in range(rng.randint(3, 50)))
    words = [rng.choice(keyword_pool) for _ in range(rng.randint(0, 5))]
    return (" ".join(words) + " " + noise).strip()


def test_random_prompt_fuzz_100_never_crashes_and_validates_schema():
    rng = random.Random(20260426)
    adapter = TypeAdapter(ConciergeTypedResponse)
    service = MagicMock()
    service.search.return_value = _mock_place_response()

    with patch(
        "app.routes.ai.get_settings",
        return_value=SimpleNamespace(
            concierge_router_v2=True,
            concierge_router_v2_confidence_threshold=0.55,
            trip_advice_builder_enabled=True,
        ),
    ):
        for _ in range(100):
            prompt = _random_prompt(rng)
            payload = ConciergeSearchRequest(trip_id=FAKE_TRIP_ID, user_query=prompt)
            response, _ = build_typed_concierge_response(service, payload, FAKE_USER_ID)
            adapter.validate_python(response.model_dump(mode="json"))


def test_request_log_redacts_prompt_and_persists_supabase_row():
    db = get_mock_client()
    decision = route_prompt("best hotels in chicago", confidence_threshold=0.55)
    response = _mock_place_response()

    request_id = persist_concierge_request_log(
        db=db,
        user_id=FAKE_USER_ID,
        prompt="Email me at test@example.com or call 555-123-9876",
        decision=decision,
        response=response,
        latency_ms=123,
    )

    rows = db.table("concierge_request_log").select("*").eq("request_id", str(request_id)).execute().data
    assert len(rows) == 1
    row = rows[0]
    assert "test@example.com" not in row["prompt"]
    assert "555-123-9876" not in row["prompt"]
    assert "[redacted_email]" in row["prompt"]
    assert "[redacted_phone]" in row["prompt"]
    assert row["response_type"] == "place_recommendations"
    assert row["intent_classifier_version"]


def test_redact_prompt_noop_for_non_pii_text():
    assert redact_prompt("Best tacos in Austin") == "Best tacos in Austin"
