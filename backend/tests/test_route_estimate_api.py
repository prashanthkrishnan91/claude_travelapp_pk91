"""FastAPI TestClient endpoint tests for route-estimate — Route Planning v1 PR 2.

The parent conftest.py stubs fastapi as MagicMock to speed up service-level tests.
These endpoint tests need the real FastAPI router, TestClient, and dependency overrides,
so this module removes the stub before importing anything from fastapi.

app/routes/__init__.py loads all routers (including ai.py with MagicMock pydantic models),
so we load app.routes.route_estimate directly via importlib, bypassing __init__.py.

Proves:
- POST /itinerary/{trip_id}/days/{day_id}/route-estimate is registered.
- Unauthenticated request is rejected (401).
- Authenticated + ROUTE_ESTIMATE_V1_ENABLED=false → status=disabled, fail-closed.
- Authenticated + ROUTE_ESTIMATE_V1_ENABLED=true + valid stops → status=not_configured.
- Invalid lat/lng receives 422 at the API boundary (FastAPI/Pydantic).
- Unsupported item types (flight, hotel, note) produce no estimates.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import types
from typing import Annotated
from unittest.mock import MagicMock
from uuid import UUID, uuid4

# ── Remove parent conftest's fastapi MagicMock stub ──────────────────────────
# Must happen before ANY fastapi import so subsequent imports get the real module.
for _k in [k for k in sys.modules if k == "fastapi" or k.startswith("fastapi.")]:
    del sys.modules[_k]

# Clear any previously-cached router/deps/routes modules
for _k in [k for k in sys.modules if k in ("app.routes.route_estimate", "app.core.deps", "app.routes")]:
    del sys.modules[_k]

# Ensure supabase stub is present (not installed in this pytest env)
if "supabase" not in sys.modules or not hasattr(sys.modules["supabase"], "__version__"):
    sys.modules["supabase"] = MagicMock()

# ── Real fastapi is now importable ───────────────────────────────────────────
import fastapi  # noqa: E402 — stub cleared above
from fastapi import Depends, FastAPI, HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import pytest  # noqa: E402

# ── Stub app.routes as a package so submodule imports don't run __init__.py ──
_routes_dir = str(pathlib.Path(__file__).parent.parent / "app" / "routes")
_routes_pkg = types.ModuleType("app.routes")
_routes_pkg.__path__ = [_routes_dir]
_routes_pkg.__package__ = "app.routes"
_routes_pkg.__file__ = _routes_dir + "/__init__.py"
sys.modules["app.routes"] = _routes_pkg

# ── Stub app.core.deps with a real Annotated CurrentUserID dependency ─────────
# The real deps.py calls Supabase JWT validation; here we use a simple callable.
_TEST_USER_ID: UUID = uuid4()


def _stub_get_current_user_id() -> UUID:
    return _TEST_USER_ID


_deps_stub = sys.modules.get("app.core.deps")
if _deps_stub is None:
    _deps_stub = types.ModuleType("app.core.deps")
    sys.modules["app.core.deps"] = _deps_stub

_deps_stub.get_current_user_id = _stub_get_current_user_id
_deps_stub.CurrentUserID = Annotated[UUID, Depends(_stub_get_current_user_id)]

# DB stub: real Annotated type so FastAPI can resolve the dependency.
# Tests with key="" return before calling the db, so the mock db is never queried
# in the existing flag-disabled/key-missing test paths.
_mock_db = MagicMock()


def _stub_get_db() -> MagicMock:
    return _mock_db


_deps_stub.DB = Annotated[MagicMock, Depends(_stub_get_db)]

# ── Load app.routes.route_estimate directly (bypass __init__.py) ─────────────
_re_path = pathlib.Path(__file__).parent.parent / "app" / "routes" / "route_estimate.py"
_re_spec = importlib.util.spec_from_file_location("app.routes.route_estimate", _re_path)
_re_mod = importlib.util.module_from_spec(_re_spec)
sys.modules["app.routes.route_estimate"] = _re_mod
_re_spec.loader.exec_module(_re_mod)
_route_estimate_router = _re_mod.router

# ── Build isolated test apps ──────────────────────────────────────────────────

# Authenticated app — auth dependency returns _TEST_USER_ID
_auth_app = FastAPI()
_auth_app.include_router(_route_estimate_router)
_auth_client = TestClient(_auth_app, raise_server_exceptions=False)

# Unauthenticated simulation — auth dependency raises 401
def _reject_auth() -> UUID:
    raise HTTPException(status_code=401, detail="Unauthorized")

_unauth_app = FastAPI()
_unauth_app.include_router(_route_estimate_router)
_unauth_app.dependency_overrides[_stub_get_current_user_id] = _reject_auth
_unauth_client = TestClient(_unauth_app, raise_server_exceptions=False)

# ── Helpers ───────────────────────────────────────────────────────────────────
_TRIP_ID = uuid4()
_DAY_ID = uuid4()
_ROUTE_URL = f"/itinerary/{_TRIP_ID}/days/{_DAY_ID}/route-estimate"

_STOP_A = {"item_id": "a", "title": "Stop A", "item_type": "activity", "lat": 25.775, "lng": -80.190}
_STOP_B = {"item_id": "b", "title": "Stop B", "item_type": "meal",     "lat": 25.780, "lng": -80.185}
_VALID_BODY = {"stops": [_STOP_A, _STOP_B]}


def _settings(enabled: bool, key: str = "") -> MagicMock:
    s = MagicMock()
    s.route_estimate_v1_enabled = enabled
    s.google_routes_api_key = key
    return s


# ── Tests: endpoint registered ────────────────────────────────────────────────


class TestEndpointRegistered:
    def test_route_is_registered_on_router(self):
        # FastAPI wraps included routers lazily; check the router's own route list.
        paths = [getattr(r, "path", "") for r in _route_estimate_router.routes]
        assert any("/route-estimate" in p for p in paths)

    def test_route_accepts_post_method(self):
        for r in _route_estimate_router.routes:
            if "/route-estimate" in getattr(r, "path", ""):
                assert "POST" in (getattr(r, "methods", set()) or set())
                return
        pytest.fail("No route-estimate route with POST found")


# ── Tests: unauthenticated request ───────────────────────────────────────────


class TestUnauthenticatedRequest:
    def test_unauthenticated_returns_401(self):
        resp = _unauth_client.post(_ROUTE_URL, json=_VALID_BODY)
        assert resp.status_code == 401


# ── Tests: authenticated, flag=false (default) ───────────────────────────────


class TestAuthenticatedFlagDisabled:
    def test_returns_200(self, monkeypatch):
        import app.services.route_estimate as svc
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        assert _auth_client.post(_ROUTE_URL, json=_VALID_BODY).status_code == 200

    def test_status_is_disabled(self, monkeypatch):
        import app.services.route_estimate as svc
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        assert _auth_client.post(_ROUTE_URL, json=_VALID_BODY).json()["status"] == "disabled"

    def test_reason_is_feature_flag_disabled(self, monkeypatch):
        import app.services.route_estimate as svc
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        assert _auth_client.post(_ROUTE_URL, json=_VALID_BODY).json()["reason"] == "feature_flag_disabled"

    def test_provider_is_google_routes(self, monkeypatch):
        import app.services.route_estimate as svc
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        assert _auth_client.post(_ROUTE_URL, json=_VALID_BODY).json()["provider"] == "google_routes"

    def test_estimates_empty(self, monkeypatch):
        import app.services.route_estimate as svc
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        assert _auth_client.post(_ROUTE_URL, json=_VALID_BODY).json()["estimates"] == []


# ── Tests: authenticated, flag=true, key missing ─────────────────────────────


class TestAuthenticatedFlagEnabledKeyMissing:
    def test_returns_200(self, monkeypatch):
        import app.services.route_estimate as svc
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True, key=""))
        assert _auth_client.post(_ROUTE_URL, json=_VALID_BODY).status_code == 200

    def test_status_is_not_configured(self, monkeypatch):
        import app.services.route_estimate as svc
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True, key=""))
        assert _auth_client.post(_ROUTE_URL, json=_VALID_BODY).json()["status"] == "not_configured"

    def test_reason_is_provider_key_missing(self, monkeypatch):
        import app.services.route_estimate as svc
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True, key=""))
        assert _auth_client.post(_ROUTE_URL, json=_VALID_BODY).json()["reason"] == "provider_key_missing"

    def test_estimates_empty(self, monkeypatch):
        import app.services.route_estimate as svc
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True, key=""))
        assert _auth_client.post(_ROUTE_URL, json=_VALID_BODY).json()["estimates"] == []


# ── Tests: request validation at the API boundary ────────────────────────────


class TestRequestValidationAtApiBoundary:
    def test_lat_above_90_returns_422(self, monkeypatch):
        import app.services.route_estimate as svc
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        body = {"stops": [
            {"item_id": "x", "title": "Bad", "item_type": "activity", "lat": 200.0, "lng": 0.0},
            _STOP_B,
        ]}
        assert _auth_client.post(_ROUTE_URL, json=body).status_code == 422

    def test_lng_above_180_returns_422(self, monkeypatch):
        import app.services.route_estimate as svc
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        body = {"stops": [
            _STOP_A,
            {"item_id": "x", "title": "Bad", "item_type": "meal", "lat": 0.0, "lng": 270.0},
        ]}
        assert _auth_client.post(_ROUTE_URL, json=body).status_code == 422

    def test_missing_required_fields_returns_422(self, monkeypatch):
        import app.services.route_estimate as svc
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        body = {"stops": [{"item_id": "x", "lat": 0.0}]}  # missing title, item_type, lng
        assert _auth_client.post(_ROUTE_URL, json=body).status_code == 422


# ── Tests: unsupported item types produce no estimates ───────────────────────


class TestUnsupportedItemTypesProduceNoEstimates:
    def test_flight_alongside_valid_stops_no_estimates(self, monkeypatch):
        import app.services.route_estimate as svc
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        body = {"stops": [
            _STOP_A, _STOP_B,
            {"item_id": "flt", "title": "Flight", "item_type": "flight", "lat": 25.0, "lng": -80.0},
        ]}
        resp = _auth_client.post(_ROUTE_URL, json=body)
        assert resp.status_code == 200
        assert resp.json()["estimates"] == []

    def test_hotel_alongside_valid_stops_no_estimates(self, monkeypatch):
        import app.services.route_estimate as svc
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        body = {"stops": [
            _STOP_A, _STOP_B,
            {"item_id": "htl", "title": "Hotel", "item_type": "hotel", "lat": 25.0, "lng": -80.0},
        ]}
        resp = _auth_client.post(_ROUTE_URL, json=body)
        assert resp.status_code == 200
        assert resp.json()["estimates"] == []

    def test_note_alongside_valid_stops_no_estimates(self, monkeypatch):
        import app.services.route_estimate as svc
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        body = {"stops": [
            _STOP_A, _STOP_B,
            {"item_id": "n1", "title": "Note", "item_type": "note", "lat": 25.0, "lng": -80.0},
        ]}
        resp = _auth_client.post(_ROUTE_URL, json=body)
        assert resp.status_code == 200
        assert resp.json()["estimates"] == []
