"""Google Routes adapter tests — Route Planning v1 PR 3.

Governed by Route Planning v1 Contract ADR (PR #509).

All tests use mocked HTTP; no real Google calls are made.

Proves:
- No provider call when flag=False.
- No provider call when key missing.
- No provider call when fewer than 2 valid stops.
- No provider call when >10 valid stops (v1 hard cap → 422).
- No provider call for unsupported-only stops.
- No provider call when ownership fails.
- Successful path makes exactly one mocked ComputeRoutes call.
- Request payload preserves manual stop order.
- Request payload uses lat/lng only; no address/geocoding fields.
- Request does not include optimize_waypoint_order, computeRouteMatrix,
  traffic-aware, route optimization, or alternatives fields.
- Tight field mask (routes.legs.duration,routes.legs.distanceMeters) is used.
- Response maps real mocked duration/distance only.
- Estimates empty on provider HTTP error.
- Estimates empty when provider returns no routes.
- No fabricated or haversine-derived duration values.
- provider_call_count=1 on successful call; 0 on early-return paths.
- Endpoint ownership gate: no provider call before ownership verified.
"""
from __future__ import annotations

import json
from typing import List
from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from app.models.route_estimate import RouteEstimateRequest, RouteableStop
from app.services.google_routes_adapter import (
    MAX_ROUTABLE_STOPS,
    AdapterResult,
    LegEstimate,
    _parse_duration_seconds,
    call_compute_routes,
)


# ── helpers ──────────────────────────────────────────────────────────────────


def _stop(item_id: str, lat: float = 25.775, lng: float = -80.190) -> RouteableStop:
    return RouteableStop(item_id=item_id, title=f"Stop {item_id}", item_type="activity", lat=lat, lng=lng)


def _stops(*ids: str) -> List[RouteableStop]:
    base_lat = 25.775
    return [_stop(id_, lat=base_lat + i * 0.01) for i, id_ in enumerate(ids)]


def _mock_client(status_code: int = 200, body: dict | None = None) -> MagicMock:
    """Return a mock httpx.Client whose .post() returns the given response."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = status_code
    mock_response.json.return_value = body or {}

    if status_code >= 400:
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=mock_response,
        )
    else:
        mock_response.raise_for_status.return_value = None

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = mock_response
    return mock_client


def _success_body(*leg_durations_distances: tuple[str, int]) -> dict:
    """Build a ComputeRoutes-style success response with per-leg data."""
    legs = [{"duration": dur, "distanceMeters": dist} for dur, dist in leg_durations_distances]
    return {"routes": [{"legs": legs}]}


def _settings(enabled: bool, key: str = "") -> MagicMock:
    s = MagicMock()
    s.route_estimate_v1_enabled = enabled
    s.google_routes_api_key = key
    return s


def _svc():
    import app.services.route_estimate as svc
    return svc


# ── adapter unit tests ────────────────────────────────────────────────────────


class TestDurationParsing:
    def test_parses_seconds_suffix(self):
        assert _parse_duration_seconds("300s") == 300

    def test_parses_plain_int(self):
        assert _parse_duration_seconds("600") == 600

    def test_parses_with_whitespace(self):
        assert _parse_duration_seconds(" 45s ") == 45

    def test_returns_zero_on_invalid(self):
        assert _parse_duration_seconds("bad") == 0

    def test_returns_zero_on_empty(self):
        assert _parse_duration_seconds("") == 0


class TestAdapterMaxStopsCap:
    def test_max_routable_stops_is_10(self):
        assert MAX_ROUTABLE_STOPS == 10

    def test_exactly_10_stops_allowed_by_adapter(self):
        stops = _stops(*[str(i) for i in range(10)])
        client = _mock_client(200, _success_body(*[("600s", 5000)] * 9))
        result = call_compute_routes(stops, "fake-key", http_client=client)
        assert result.provider_call_count == 1

    def test_adapter_makes_exactly_one_call_for_10_stops(self):
        stops = _stops(*[str(i) for i in range(10)])
        client = _mock_client(200, _success_body(*[("600s", 5000)] * 9))
        call_compute_routes(stops, "fake-key", http_client=client)
        assert client.post.call_count == 1


class TestAdapterNoCallWhenServiceGateFails:
    """Service-layer gate prevents adapter from being called for bad preconditions."""

    def test_no_call_when_flag_false(self, monkeypatch):
        svc = _svc()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        with patch.object(svc, "call_compute_routes") as mock_call:
            resp = svc.compute_route_estimate(
                RouteEstimateRequest(stops=_stops("a", "b")),
                uuid4(), uuid4(),
            )
            assert mock_call.call_count == 0
            assert resp.status == "disabled"

    def test_no_call_when_key_missing(self, monkeypatch):
        svc = _svc()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True, key=""))
        with patch.object(svc, "call_compute_routes") as mock_call:
            resp = svc.compute_route_estimate(
                RouteEstimateRequest(stops=_stops("a", "b")),
                uuid4(), uuid4(),
            )
            assert mock_call.call_count == 0
            assert resp.status == "not_configured"

    def test_no_call_when_fewer_than_2_valid_stops(self, monkeypatch):
        svc = _svc()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True, key="somekey"))
        with patch.object(svc, "call_compute_routes") as mock_call:
            with pytest.raises(Exception):
                svc.compute_route_estimate(
                    RouteEstimateRequest(stops=_stops("a")),
                    uuid4(), uuid4(),
                )
            assert mock_call.call_count == 0

    def test_no_call_for_unsupported_only_stops(self, monkeypatch):
        svc = _svc()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True, key="somekey"))
        flight_stops = [
            RouteableStop(item_id="f1", title="F1", item_type="flight", lat=25.0, lng=-80.0),
            RouteableStop(item_id="f2", title="F2", item_type="hotel", lat=25.1, lng=-80.1),
        ]
        with patch.object(svc, "call_compute_routes") as mock_call:
            with pytest.raises(Exception):
                svc.compute_route_estimate(
                    RouteEstimateRequest(stops=flight_stops),
                    uuid4(), uuid4(),
                )
            assert mock_call.call_count == 0

    def test_no_call_when_more_than_10_valid_stops(self, monkeypatch):
        svc = _svc()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True, key="somekey"))
        too_many = _stops(*[str(i) for i in range(11)])
        with patch.object(svc, "call_compute_routes") as mock_call:
            with pytest.raises(Exception):
                svc.compute_route_estimate(
                    RouteEstimateRequest(stops=too_many),
                    uuid4(), uuid4(),
                )
            assert mock_call.call_count == 0

    def test_no_call_when_ownership_fails(self, monkeypatch):
        svc = _svc()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True, key="somekey"))
        db_mock = MagicMock()
        # Ownership check returns no rows → 404
        db_mock.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        with patch.object(svc, "call_compute_routes") as mock_call:
            with pytest.raises(Exception):
                svc.compute_route_estimate(
                    RouteEstimateRequest(stops=_stops("a", "b")),
                    uuid4(), uuid4(),
                    user_id=uuid4(),
                    db=db_mock,
                )
            assert mock_call.call_count == 0

    def test_provider_call_count_zero_on_flag_disabled(self, monkeypatch):
        svc = _svc()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(False))
        resp = svc.compute_route_estimate(
            RouteEstimateRequest(stops=_stops("a", "b")),
            uuid4(), uuid4(),
        )
        assert resp.metadata.get("provider_call_count", 0) == 0

    def test_provider_call_count_zero_on_key_missing(self, monkeypatch):
        svc = _svc()
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True, key=""))
        resp = svc.compute_route_estimate(
            RouteEstimateRequest(stops=_stops("a", "b")),
            uuid4(), uuid4(),
        )
        assert resp.metadata.get("provider_call_count", 0) == 0


class TestAdapterSuccessfulPath:
    def _run_with_mock(self, stops, http_body):
        """Helper: run the adapter directly with a mock HTTP client."""
        client = _mock_client(200, http_body)
        return call_compute_routes(stops, "fake-key", http_client=client), client

    def test_successful_call_returns_provider_call_count_1(self):
        stops = _stops("a", "b")
        result, _ = self._run_with_mock(stops, _success_body(("300s", 2000)))
        assert result.provider_call_count == 1

    def test_successful_call_returns_estimates(self):
        stops = _stops("a", "b")
        result, _ = self._run_with_mock(stops, _success_body(("300s", 2000)))
        assert len(result.estimates) == 1

    def test_single_leg_duration_mapped(self):
        stops = _stops("a", "b")
        result, _ = self._run_with_mock(stops, _success_body(("300s", 2000)))
        assert result.estimates[0].duration_seconds == 300

    def test_single_leg_distance_mapped(self):
        stops = _stops("a", "b")
        result, _ = self._run_with_mock(stops, _success_body(("300s", 2000)))
        assert result.estimates[0].distance_meters == 2000

    def test_from_item_id_set(self):
        stops = _stops("stop1", "stop2")
        result, _ = self._run_with_mock(stops, _success_body(("300s", 2000)))
        assert result.estimates[0].from_item_id == "stop1"

    def test_to_item_id_set(self):
        stops = _stops("stop1", "stop2")
        result, _ = self._run_with_mock(stops, _success_body(("300s", 2000)))
        assert result.estimates[0].to_item_id == "stop2"

    def test_order_index_set(self):
        stops = _stops("a", "b", "c")
        result, _ = self._run_with_mock(stops, _success_body(("300s", 2000), ("400s", 3000)))
        assert result.estimates[0].order_index == 0
        assert result.estimates[1].order_index == 1

    def test_provider_field_is_google_routes(self):
        stops = _stops("a", "b")
        result, _ = self._run_with_mock(stops, _success_body(("300s", 2000)))
        assert result.estimates[0].provider == "google_routes"

    def test_source_field_is_google_routes(self):
        stops = _stops("a", "b")
        result, _ = self._run_with_mock(stops, _success_body(("300s", 2000)))
        assert result.estimates[0].source == "google_routes"

    def test_estimated_field_true(self):
        stops = _stops("a", "b")
        result, _ = self._run_with_mock(stops, _success_body(("300s", 2000)))
        assert result.estimates[0].estimated is True

    def test_makes_exactly_one_http_call(self):
        stops = _stops("a", "b")
        result, client = self._run_with_mock(stops, _success_body(("300s", 2000)))
        assert client.post.call_count == 1

    def test_three_stops_returns_two_legs(self):
        stops = _stops("a", "b", "c")
        result, _ = self._run_with_mock(stops, _success_body(("300s", 2000), ("500s", 4000)))
        assert len(result.estimates) == 2
        assert result.estimates[0].from_item_id == "a"
        assert result.estimates[0].to_item_id == "b"
        assert result.estimates[1].from_item_id == "b"
        assert result.estimates[1].to_item_id == "c"

    def test_no_error_reason_on_success(self):
        stops = _stops("a", "b")
        result, _ = self._run_with_mock(stops, _success_body(("300s", 2000)))
        assert result.error_reason is None


class TestAdapterRequestPayload:
    """Verify the exact ComputeRoutes request body and headers."""

    def _capture_request(self, stops, extra_stops=None):
        client = _mock_client(200, _success_body(*[("300s", 2000)] * (len(stops) - 1)))
        call_compute_routes(stops, "test-api-key", http_client=client)
        return client.post.call_args

    def test_url_is_compute_routes(self):
        stops = _stops("a", "b")
        call_args = self._capture_request(stops)
        url = call_args[0][0]
        assert "computeRoutes" in url
        assert "routeMatrix" not in url.lower()

    def test_api_key_in_header(self):
        stops = _stops("a", "b")
        call_args = self._capture_request(stops)
        headers = call_args.kwargs.get("headers", {})
        assert headers.get("X-Goog-Api-Key") == "test-api-key"

    def test_field_mask_in_header(self):
        stops = _stops("a", "b")
        call_args = self._capture_request(stops)
        headers = call_args.kwargs.get("headers", {})
        mask = headers.get("X-Goog-FieldMask", "")
        assert "routes.legs.duration" in mask
        assert "routes.legs.distanceMeters" in mask

    def test_travel_mode_is_drive(self):
        stops = _stops("a", "b")
        call_args = self._capture_request(stops)
        body = call_args.kwargs.get("json", {})
        assert body.get("travelMode") == "DRIVE"

    def test_no_compute_alternative_routes(self):
        stops = _stops("a", "b")
        call_args = self._capture_request(stops)
        body = call_args.kwargs.get("json", {})
        assert body.get("computeAlternativeRoutes") is False

    def test_routing_preference_traffic_unaware(self):
        stops = _stops("a", "b")
        call_args = self._capture_request(stops)
        body = call_args.kwargs.get("json", {})
        assert body.get("routingPreference") == "TRAFFIC_UNAWARE"

    def test_no_optimize_waypoint_order_field(self):
        stops = _stops("a", "b")
        call_args = self._capture_request(stops)
        body = call_args.kwargs.get("json", {})
        assert "optimizeWaypointOrder" not in body

    def test_no_route_optimization_field(self):
        stops = _stops("a", "b")
        call_args = self._capture_request(stops)
        body_str = json.dumps(call_args.kwargs.get("json", {}))
        assert "routeOptimization" not in body_str
        assert "optimizeWaypointOrder" not in body_str

    def test_origin_is_first_stop_latlng(self):
        stops = _stops("a", "b", "c")
        call_args = self._capture_request(stops)
        body = call_args.kwargs.get("json", {})
        origin_latlng = body["origin"]["location"]["latLng"]
        assert origin_latlng["latitude"] == stops[0].lat
        assert origin_latlng["longitude"] == stops[0].lng

    def test_destination_is_last_stop_latlng(self):
        stops = _stops("a", "b", "c")
        call_args = self._capture_request(stops)
        body = call_args.kwargs.get("json", {})
        dest_latlng = body["destination"]["location"]["latLng"]
        assert dest_latlng["latitude"] == stops[-1].lat
        assert dest_latlng["longitude"] == stops[-1].lng

    def test_intermediates_are_middle_stops_in_order(self):
        stops = _stops("a", "b", "c")
        call_args = self._capture_request(stops)
        body = call_args.kwargs.get("json", {})
        ints = body.get("intermediates", [])
        assert len(ints) == 1
        assert ints[0]["location"]["latLng"]["latitude"] == stops[1].lat

    def test_no_address_field_in_origin(self):
        stops = _stops("a", "b")
        call_args = self._capture_request(stops)
        body = call_args.kwargs.get("json", {})
        origin = body.get("origin", {})
        assert "address" not in origin
        assert "placeId" not in origin

    def test_no_address_field_in_destination(self):
        stops = _stops("a", "b")
        call_args = self._capture_request(stops)
        body = call_args.kwargs.get("json", {})
        dest = body.get("destination", {})
        assert "address" not in dest
        assert "placeId" not in dest

    def test_two_stops_no_intermediates_field(self):
        stops = _stops("a", "b")
        call_args = self._capture_request(stops)
        body = call_args.kwargs.get("json", {})
        assert "intermediates" not in body

    def test_order_preserved_first_stop_is_origin(self):
        """Stops must NOT be reordered; first stop always maps to origin."""
        s1 = _stop("first", lat=25.0, lng=-80.0)
        s2 = _stop("second", lat=26.0, lng=-81.0)
        client = _mock_client(200, _success_body(("300s", 2000)))
        call_compute_routes([s1, s2], "key", http_client=client)
        body = client.post.call_args.kwargs["json"]
        assert body["origin"]["location"]["latLng"]["latitude"] == 25.0
        assert body["destination"]["location"]["latLng"]["latitude"] == 26.0


class TestAdapterErrorHandling:
    def test_http_4xx_returns_empty_estimates(self):
        stops = _stops("a", "b")
        client = _mock_client(400, {})
        result = call_compute_routes(stops, "fake-key", http_client=client)
        assert result.estimates == []

    def test_http_4xx_returns_provider_call_count_1(self):
        stops = _stops("a", "b")
        client = _mock_client(400, {})
        result = call_compute_routes(stops, "fake-key", http_client=client)
        assert result.provider_call_count == 1

    def test_http_4xx_has_error_reason(self):
        stops = _stops("a", "b")
        client = _mock_client(400, {})
        result = call_compute_routes(stops, "fake-key", http_client=client)
        assert result.error_reason is not None
        assert "400" in result.error_reason

    def test_http_5xx_returns_empty_estimates(self):
        stops = _stops("a", "b")
        client = _mock_client(500, {})
        result = call_compute_routes(stops, "fake-key", http_client=client)
        assert result.estimates == []

    def test_empty_routes_returns_empty_estimates(self):
        stops = _stops("a", "b")
        client = _mock_client(200, {"routes": []})
        result = call_compute_routes(stops, "fake-key", http_client=client)
        assert result.estimates == []
        assert result.provider_call_count == 1

    def test_empty_routes_has_error_reason(self):
        stops = _stops("a", "b")
        client = _mock_client(200, {"routes": []})
        result = call_compute_routes(stops, "fake-key", http_client=client)
        assert result.error_reason == "no_routes_returned"

    def test_empty_legs_returns_empty_estimates(self):
        stops = _stops("a", "b")
        client = _mock_client(200, {"routes": [{"legs": []}]})
        result = call_compute_routes(stops, "fake-key", http_client=client)
        assert result.estimates == []
        assert result.error_reason == "no_legs_returned"

    def test_timeout_returns_empty_estimates(self):
        stops = _stops("a", "b")
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.side_effect = httpx.TimeoutException("timed out")
        result = call_compute_routes(stops, "fake-key", http_client=mock_client)
        assert result.estimates == []
        assert result.error_reason == "timeout"
        assert result.provider_call_count == 1

    def test_no_haversine_fallback_on_error(self):
        """No fabricated duration/distance when provider fails."""
        stops = _stops("a", "b")
        client = _mock_client(500, {})
        result = call_compute_routes(stops, "fake-key", http_client=client)
        assert result.estimates == []


class TestServiceWithRealAdapter:
    """Test the service → adapter integration with mocked HTTP."""

    def _db_with_trip(self, trip_id):
        """Return a DB mock that confirms ownership for trip_id."""
        db_mock = MagicMock()
        db_mock.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": str(trip_id)}
        ]
        return db_mock

    def test_successful_path_status_is_success(self, monkeypatch):
        svc = _svc()
        trip_id = uuid4()
        user_id = uuid4()
        db_mock = self._db_with_trip(trip_id)
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True, key="real-key"))
        http_body = _success_body(("300s", 2000))
        with patch("app.services.route_estimate.call_compute_routes") as mock_call:
            mock_call.return_value = AdapterResult(
                estimates=[LegEstimate("a", "b", 2000, 300, 0)],
                provider_call_count=1,
            )
            resp = svc.compute_route_estimate(
                RouteEstimateRequest(stops=_stops("a", "b")),
                trip_id, uuid4(), user_id=user_id, db=db_mock,
            )
        assert resp.status == "success"

    def test_successful_path_estimates_non_empty(self, monkeypatch):
        svc = _svc()
        trip_id = uuid4()
        user_id = uuid4()
        db_mock = self._db_with_trip(trip_id)
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True, key="real-key"))
        with patch("app.services.route_estimate.call_compute_routes") as mock_call:
            mock_call.return_value = AdapterResult(
                estimates=[LegEstimate("a", "b", 2000, 300, 0)],
                provider_call_count=1,
            )
            resp = svc.compute_route_estimate(
                RouteEstimateRequest(stops=_stops("a", "b")),
                trip_id, uuid4(), user_id=user_id, db=db_mock,
            )
        assert len(resp.estimates) == 1

    def test_successful_path_provider_call_count_1(self, monkeypatch):
        svc = _svc()
        trip_id = uuid4()
        user_id = uuid4()
        db_mock = self._db_with_trip(trip_id)
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True, key="real-key"))
        with patch("app.services.route_estimate.call_compute_routes") as mock_call:
            mock_call.return_value = AdapterResult(
                estimates=[LegEstimate("a", "b", 2000, 300, 0)],
                provider_call_count=1,
            )
            resp = svc.compute_route_estimate(
                RouteEstimateRequest(stops=_stops("a", "b")),
                trip_id, uuid4(), user_id=user_id, db=db_mock,
            )
        assert resp.metadata.get("provider_call_count") == 1

    def test_provider_error_returns_provider_error_status(self, monkeypatch):
        svc = _svc()
        trip_id = uuid4()
        user_id = uuid4()
        db_mock = self._db_with_trip(trip_id)
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True, key="real-key"))
        with patch("app.services.route_estimate.call_compute_routes") as mock_call:
            mock_call.return_value = AdapterResult(
                estimates=[],
                provider_call_count=1,
                error_reason="http_error_500",
            )
            resp = svc.compute_route_estimate(
                RouteEstimateRequest(stops=_stops("a", "b")),
                trip_id, uuid4(), user_id=user_id, db=db_mock,
            )
        assert resp.status == "provider_error"
        assert resp.estimates == []

    def test_provider_error_call_count_in_metadata(self, monkeypatch):
        svc = _svc()
        trip_id = uuid4()
        user_id = uuid4()
        db_mock = self._db_with_trip(trip_id)
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True, key="real-key"))
        with patch("app.services.route_estimate.call_compute_routes") as mock_call:
            mock_call.return_value = AdapterResult(
                estimates=[],
                provider_call_count=1,
                error_reason="timeout",
            )
            resp = svc.compute_route_estimate(
                RouteEstimateRequest(stops=_stops("a", "b")),
                trip_id, uuid4(), user_id=user_id, db=db_mock,
            )
        assert resp.metadata.get("provider_call_count") == 1

    def test_adapter_receives_stops_in_caller_order(self, monkeypatch):
        svc = _svc()
        trip_id = uuid4()
        user_id = uuid4()
        db_mock = self._db_with_trip(trip_id)
        monkeypatch.setattr(svc, "get_settings", lambda: _settings(True, key="real-key"))
        s1 = _stop("first", lat=10.0, lng=20.0)
        s2 = _stop("second", lat=30.0, lng=40.0)
        s3 = _stop("third", lat=50.0, lng=60.0)
        captured = {}
        def fake_call(valid_stops, api_key, **kwargs):
            captured["stops"] = valid_stops
            return AdapterResult(
                estimates=[
                    LegEstimate("first", "second", 1000, 100, 0),
                    LegEstimate("second", "third", 2000, 200, 1),
                ],
                provider_call_count=1,
            )
        with patch("app.services.route_estimate.call_compute_routes", side_effect=fake_call):
            svc.compute_route_estimate(
                RouteEstimateRequest(stops=[s1, s2, s3]),
                trip_id, uuid4(), user_id=user_id, db=db_mock,
            )
        assert [s.item_id for s in captured["stops"]] == ["first", "second", "third"]


class TestAdapterModuleNoBadSymbols:
    def _adapter_source(self) -> str:
        import app.services.google_routes_adapter as adapter
        return open(adapter.__file__).read()

    def test_url_is_compute_routes_not_matrix(self):
        import app.services.google_routes_adapter as adapter
        assert "routeMatrix" not in adapter._ROUTES_URL
        assert "computeRoutes" in adapter._ROUTES_URL

    def test_optimize_waypoint_order_absent_from_body(self):
        # optimizeWaypointOrder must not be set in the request body constructor
        src = self._adapter_source().lower()
        assert "optimizewaypointorder" not in src

    def test_no_haversine_in_adapter(self):
        assert "haversine" not in self._adapter_source().lower()

    def test_no_address_lookup_calls(self):
        # Adapter must not perform address lookups; only lat/lng used
        src = self._adapter_source().lower()
        assert "geocode" not in src

    def test_traffic_unaware_is_the_routing_preference(self):
        import app.services.google_routes_adapter as adapter
        src = open(adapter.__file__).read()
        assert "TRAFFIC_UNAWARE" in src
