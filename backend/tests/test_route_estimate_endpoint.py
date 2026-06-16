"""Route estimate endpoint tests — Route Planning v1 PR 2.

Governed by Route Planning v1 Contract ADR (PR #509).

Proves:
- Feature flag default False → disabled response.
- Missing env does not break import/startup.
- Enabled flag returns not_configured / provider_not_implemented (no live call).
- google_routes is read from provider registry but never called.
- Invalid lat/lng rejected by Pydantic input validation.
- Fewer than 2 valid stops rejected.
- Flights, hotels, notes excluded with reason.
- Valid activity/meal stops preserve manual order in response metadata.
- No estimates or travel times are fabricated.
- No route optimization / reorder / geocoding / haversine symbols introduced.
"""
from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.route_estimate import (
    ACCEPTED_ITEM_TYPES,
    RouteableStop,
    RouteEstimateRequest,
)
from app.services.provider_registry import is_provider_active


# ── helpers ──────────────────────────────────────────────────────────────────


def _stop(item_id: str, item_type: str = "activity", lat: float = 25.775, lng: float = -80.190) -> RouteableStop:
    return RouteableStop(item_id=item_id, title=f"Stop {item_id}", item_type=item_type, lat=lat, lng=lng)


def _req(*stops: RouteableStop) -> RouteEstimateRequest:
    return RouteEstimateRequest(stops=list(stops))


def _settings(enabled: bool) -> MagicMock:
    s = MagicMock()
    s.route_estimate_v1_enabled = enabled
    return s


def _svc_mod():
    import app.services.route_estimate as svc
    return svc


# ── feature flag disabled (default) ──────────────────────────────────────────


class TestFeatureFlagDisabled:
    def test_flag_false_returns_disabled_status(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        resp = svc.compute_route_estimate(_req(_stop("a"), _stop("b")), uuid4(), uuid4())
        assert resp.status == "disabled"

    def test_flag_false_returns_feature_flag_disabled_reason(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        resp = svc.compute_route_estimate(_req(_stop("a"), _stop("b")), uuid4(), uuid4())
        assert resp.reason == "feature_flag_disabled"

    def test_flag_false_provider_is_google_routes(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        resp = svc.compute_route_estimate(_req(_stop("a"), _stop("b")), uuid4(), uuid4())
        assert resp.provider == "google_routes"

    def test_flag_false_estimates_empty(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        resp = svc.compute_route_estimate(_req(_stop("a"), _stop("b")), uuid4(), uuid4())
        assert resp.estimates == []

    def test_flag_false_message_is_user_safe(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        resp = svc.compute_route_estimate(_req(_stop("a"), _stop("b")), uuid4(), uuid4())
        assert len(resp.message) > 0


# ── missing env does not break startup ───────────────────────────────────────


class TestMissingEnvDoesNotBreakStartup:
    def test_service_import_succeeds_without_flag_env(self, monkeypatch):
        monkeypatch.delenv("ROUTE_ESTIMATE_V1_ENABLED", raising=False)
        import app.services.route_estimate  # noqa: F401 — must not raise


# ── enabled flag → provider_not_implemented ───────────────────────────────────


class TestEnabledFlagProviderNotImplemented:
    def test_enabled_returns_not_configured(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        resp = svc.compute_route_estimate(_req(_stop("a"), _stop("b")), uuid4(), uuid4())
        assert resp.status == "not_configured"

    def test_enabled_returns_provider_not_implemented_reason(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        resp = svc.compute_route_estimate(_req(_stop("a"), _stop("b")), uuid4(), uuid4())
        assert resp.reason == "provider_not_implemented"

    def test_enabled_provider_is_google_routes(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        resp = svc.compute_route_estimate(_req(_stop("a"), _stop("b")), uuid4(), uuid4())
        assert resp.provider == "google_routes"

    def test_enabled_estimates_empty(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        resp = svc.compute_route_estimate(_req(_stop("a"), _stop("b")), uuid4(), uuid4())
        assert resp.estimates == []


# ── provider registry consulted but not called ───────────────────────────────


class TestGoogleRoutesReadButNotCalled:
    def test_google_routes_inactive_in_registry(self):
        assert not is_provider_active("google_routes")

    def test_enabled_response_references_google_routes_provider(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        resp = svc.compute_route_estimate(_req(_stop("a"), _stop("b")), uuid4(), uuid4())
        assert resp.provider == "google_routes"

    def test_no_http_call_symbols_in_service(self):
        svc = _svc_mod()
        forbidden = ("requests.get", "requests.post", "httpx.get", "httpx.post", "aiohttp", "urllib.request")
        source = open(svc.__file__).read()
        for sym in forbidden:
            assert sym not in source, f"Provider call pattern {sym!r} must not appear in service"


# ── input validation: lat/lng ranges ─────────────────────────────────────────


class TestLatLngValidation:
    def test_lat_above_90_rejected(self):
        with pytest.raises(Exception):
            RouteableStop(item_id="x", title="X", item_type="activity", lat=91.0, lng=0.0)

    def test_lat_below_minus_90_rejected(self):
        with pytest.raises(Exception):
            RouteableStop(item_id="x", title="X", item_type="activity", lat=-91.0, lng=0.0)

    def test_lng_above_180_rejected(self):
        with pytest.raises(Exception):
            RouteableStop(item_id="x", title="X", item_type="activity", lat=0.0, lng=181.0)

    def test_lng_below_minus_180_rejected(self):
        with pytest.raises(Exception):
            RouteableStop(item_id="x", title="X", item_type="activity", lat=0.0, lng=-181.0)

    def test_valid_lat_lng_accepted(self):
        s = RouteableStop(item_id="ok", title="OK", item_type="activity", lat=25.775, lng=-80.190)
        assert s.lat == 25.775
        assert s.lng == -80.190

    def test_boundary_lat_90_accepted(self):
        s = RouteableStop(item_id="ok", title="OK", item_type="activity", lat=90.0, lng=0.0)
        assert s.lat == 90.0

    def test_boundary_lng_minus_180_accepted(self):
        s = RouteableStop(item_id="ok", title="OK", item_type="activity", lat=0.0, lng=-180.0)
        assert s.lng == -180.0


# ── minimum 2 valid stops required ───────────────────────────────────────────


class TestMinimumStopsRequired:
    def test_zero_stops_rejected(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        with pytest.raises(Exception):
            svc.compute_route_estimate(RouteEstimateRequest(stops=[]), uuid4(), uuid4())

    def test_one_valid_stop_rejected(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        with pytest.raises(Exception):
            svc.compute_route_estimate(_req(_stop("a")), uuid4(), uuid4())

    def test_one_activity_plus_one_flight_rejected(self, monkeypatch):
        """Flight is excluded, leaving only 1 valid stop → rejected."""
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        with pytest.raises(Exception):
            svc.compute_route_estimate(_req(_stop("a"), _stop("flt1", "flight")), uuid4(), uuid4())

    def test_two_valid_activity_stops_accepted(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        resp = svc.compute_route_estimate(_req(_stop("a"), _stop("b")), uuid4(), uuid4())
        assert resp is not None

    def test_one_activity_one_meal_accepted(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        resp = svc.compute_route_estimate(_req(_stop("a"), _stop("m1", "meal")), uuid4(), uuid4())
        assert resp.metadata.get("valid_stop_count") == 2


# ── unsupported item types excluded ──────────────────────────────────────────


class TestUnsupportedItemTypesExcluded:
    def _excluded_ids(self, resp) -> list:
        return [e["item_id"] for e in resp.metadata.get("excluded_stops", [])]

    def test_flight_excluded_with_reason(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        resp = svc.compute_route_estimate(
            _req(_stop("a"), _stop("b"), _stop("flt1", "flight")), uuid4(), uuid4()
        )
        assert "flt1" in self._excluded_ids(resp)

    def test_hotel_excluded_with_reason(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        resp = svc.compute_route_estimate(
            _req(_stop("a"), _stop("b"), _stop("htl1", "hotel")), uuid4(), uuid4()
        )
        assert "htl1" in self._excluded_ids(resp)

    def test_note_excluded_with_reason(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        resp = svc.compute_route_estimate(
            _req(_stop("a"), _stop("b"), _stop("note1", "note")), uuid4(), uuid4()
        )
        assert "note1" in self._excluded_ids(resp)

    def test_excluded_stop_has_non_empty_reason(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        resp = svc.compute_route_estimate(
            _req(_stop("a"), _stop("b"), _stop("flt1", "flight")), uuid4(), uuid4()
        )
        excluded = {e["item_id"]: e for e in resp.metadata.get("excluded_stops", [])}
        assert "flt1" in excluded
        assert len(excluded["flt1"]["reason"]) > 0

    def test_excluded_count_in_metadata(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        resp = svc.compute_route_estimate(
            _req(_stop("a"), _stop("b"), _stop("flt1", "flight"), _stop("htl1", "hotel")),
            uuid4(), uuid4(),
        )
        assert resp.metadata.get("excluded_stop_count") == 2


# ── manual order preserved ────────────────────────────────────────────────────


class TestManualOrderPreserved:
    def test_valid_stop_count_in_metadata(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        resp = svc.compute_route_estimate(_req(_stop("a"), _stop("b"), _stop("c")), uuid4(), uuid4())
        assert resp.metadata.get("valid_stop_count") == 3

    def test_stop_order_preserved_flag_true(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        resp = svc.compute_route_estimate(_req(_stop("a"), _stop("b")), uuid4(), uuid4())
        assert resp.metadata.get("stop_order_preserved") is True


# ── no fabricated data ────────────────────────────────────────────────────────


class TestNoFabricatedData:
    def test_estimates_always_empty_when_enabled(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True))
        resp = svc.compute_route_estimate(_req(_stop("a"), _stop("b")), uuid4(), uuid4())
        assert resp.estimates == []

    def test_estimates_always_empty_when_disabled(self, monkeypatch):
        svc = _svc_mod()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        resp = svc.compute_route_estimate(_req(_stop("a"), _stop("b")), uuid4(), uuid4())
        assert resp.estimates == []


# ── no forbidden symbols ──────────────────────────────────────────────────────


class TestNoForbiddenSymbols:
    def _source(self) -> str:
        svc = _svc_mod()
        return open(svc.__file__).read().lower()

    def test_no_optimize_day_in_service(self):
        assert "optimize_day" not in self._source()

    def test_no_reorder_in_service(self):
        assert "reorder" not in self._source()

    def test_no_route_optimization_in_service(self):
        assert "route_optimization" not in self._source()

    def test_no_geocode_in_service(self):
        assert "geocode" not in self._source()

    def test_no_haversine_in_service(self):
        assert "haversine" not in self._source()

    def test_accepted_item_types_correct(self):
        assert "activity" in ACCEPTED_ITEM_TYPES
        assert "meal" in ACCEPTED_ITEM_TYPES
        assert "flight" not in ACCEPTED_ITEM_TYPES
        assert "hotel" not in ACCEPTED_ITEM_TYPES
        assert "note" not in ACCEPTED_ITEM_TYPES
