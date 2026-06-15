"""Coordinate preservation tests for the fast dynamic place search path.

Verifies the fix for the coordinate ingress gap where fast_dynamic_place_search
requested places.location from Google but did not parse latitude/longitude
into GoogleVerification, causing Concierge-added items to lack routeable coords.

Coverage:
1. _to_card with location dict preserves lat and lng in google_verification.
2. _to_card without location returns honest None lat/lng (no fabrication).
3. _to_card with partial location (latitude only) returns lat only — no lng.
4. lat/lng are finite numbers, not strings or booleans.
5. All other GoogleVerification fields (place_id, address, maps_uri) remain intact.
6. Legacy addConciergeItemToTrip payload shape (reason-only) is safe — a structural
   assertion that ConciergeSuggestion only carries name/type/reason and no coords.
7. No route optimization, geocoding, or provider symbols in fast_dynamic_place_search.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

import pytest

from app.services.fast_dynamic_place_search import (
    FastDynamicPlaceSearch,
    ParsedPlaceQuery,
    _OPERATIONAL,
    parse_place_query,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_place_with_location(
    *,
    lat: Optional[float] = 41.8781,
    lng: Optional[float] = -87.6298,
    place_id: str = "ChIJ7cv00DwsDogRAMDACa2m4K8",
    name: str = "Chicago Tapas Co.",
    address: str = "123 N Michigan Ave, Chicago, IL 60601, USA",
    maps_uri: str = "https://maps.google.com/?cid=12345",
) -> Dict[str, Any]:
    place: Dict[str, Any] = {
        "id": place_id,
        "displayName": {"text": name},
        "types": ["restaurant", "food"],
        "rating": 4.5,
        "userRatingCount": 320,
        "businessStatus": _OPERATIONAL,
        "formattedAddress": address,
        "googleMapsUri": maps_uri,
        "websiteUri": None,
        "priceLevel": None,
    }
    location: Dict[str, Any] = {}
    if lat is not None:
        location["latitude"] = lat
    if lng is not None:
        location["longitude"] = lng
    place["location"] = location
    return place


def _make_place_no_location(*, name: str = "No-Coord Place") -> Dict[str, Any]:
    return {
        "id": "pid_no_loc",
        "displayName": {"text": name},
        "types": ["restaurant"],
        "rating": 4.0,
        "userRatingCount": 100,
        "businessStatus": _OPERATIONAL,
        "formattedAddress": "Unknown, City",
        "googleMapsUri": "https://maps.google.com/?q=test",
        "websiteUri": None,
        "priceLevel": None,
    }


def _tapas_parsed() -> ParsedPlaceQuery:
    return parse_place_query("tapas bar", "Chicago")


def _make_svc() -> FastDynamicPlaceSearch:
    return FastDynamicPlaceSearch.__new__(FastDynamicPlaceSearch)


# ── 1. Coordinates present — preserved in GoogleVerification ─────────────────


class TestCoordinatePreservation:
    def test_lat_extracted_from_location_dict(self) -> None:
        svc = _make_svc()
        place = _make_place_with_location(lat=41.8781, lng=-87.6298)
        card = svc._to_card(place, parsed=_tapas_parsed())
        assert card is not None
        assert card.google_verification is not None
        assert card.google_verification.lat == pytest.approx(41.8781)

    def test_lng_extracted_from_location_dict(self) -> None:
        svc = _make_svc()
        place = _make_place_with_location(lat=41.8781, lng=-87.6298)
        card = svc._to_card(place, parsed=_tapas_parsed())
        assert card is not None
        assert card.google_verification is not None
        assert card.google_verification.lng == pytest.approx(-87.6298)

    def test_lat_lng_are_floats_not_strings(self) -> None:
        svc = _make_svc()
        place = _make_place_with_location(lat=48.8566, lng=2.3522)
        card = svc._to_card(place, parsed=_tapas_parsed())
        assert card is not None
        gv = card.google_verification
        assert gv is not None
        assert isinstance(gv.lat, float), f"lat must be float, got {type(gv.lat)}"
        assert isinstance(gv.lng, float), f"lng must be float, got {type(gv.lng)}"

    def test_negative_lat_lng_preserved(self) -> None:
        svc = _make_svc()
        place = _make_place_with_location(lat=-33.8688, lng=151.2093)
        card = svc._to_card(place, parsed=parse_place_query("seafood", "Sydney"))
        assert card is not None
        gv = card.google_verification
        assert gv is not None
        assert gv.lat == pytest.approx(-33.8688)
        assert gv.lng == pytest.approx(151.2093)


# ── 2. No location — honest null (no fabrication) ─────────────────────────────


class TestNoCoordinatesFabrication:
    def test_no_location_key_yields_none_lat(self) -> None:
        svc = _make_svc()
        place = _make_place_no_location()
        card = svc._to_card(place, parsed=_tapas_parsed())
        assert card is not None
        gv = card.google_verification
        assert gv is not None
        assert gv.lat is None, "must not fabricate lat when location absent"

    def test_no_location_key_yields_none_lng(self) -> None:
        svc = _make_svc()
        place = _make_place_no_location()
        card = svc._to_card(place, parsed=_tapas_parsed())
        assert card is not None
        gv = card.google_verification
        assert gv is not None
        assert gv.lng is None, "must not fabricate lng when location absent"

    def test_empty_location_dict_yields_none_lat_lng(self) -> None:
        svc = _make_svc()
        place = _make_place_no_location()
        place["location"] = {}
        card = svc._to_card(place, parsed=_tapas_parsed())
        assert card is not None
        gv = card.google_verification
        assert gv is not None
        assert gv.lat is None
        assert gv.lng is None


# ── 3. Partial location — no fabrication for missing axis ────────────────────


class TestPartialLocation:
    def test_latitude_only_no_lng(self) -> None:
        svc = _make_svc()
        place = _make_place_with_location(lat=41.8781, lng=None)
        card = svc._to_card(place, parsed=_tapas_parsed())
        assert card is not None
        gv = card.google_verification
        assert gv is not None
        assert gv.lat == pytest.approx(41.8781)
        assert gv.lng is None, "must not fabricate lng when only lat present"

    def test_longitude_only_no_lat(self) -> None:
        svc = _make_svc()
        place = _make_place_with_location(lat=None, lng=-87.6298)
        card = svc._to_card(place, parsed=_tapas_parsed())
        assert card is not None
        gv = card.google_verification
        assert gv is not None
        assert gv.lat is None, "must not fabricate lat when only lng present"
        assert gv.lng == pytest.approx(-87.6298)


# ── 4. Other GoogleVerification fields remain intact ─────────────────────────


class TestGoogleVerificationIntegrity:
    def test_provider_place_id_preserved(self) -> None:
        svc = _make_svc()
        place = _make_place_with_location(place_id="ChIJexpected123")
        card = svc._to_card(place, parsed=_tapas_parsed())
        assert card is not None
        assert card.google_verification is not None
        assert card.google_verification.provider_place_id == "ChIJexpected123"

    def test_formatted_address_preserved(self) -> None:
        svc = _make_svc()
        expected_addr = "456 W Oak St, Chicago, IL 60610, USA"
        place = _make_place_with_location(address=expected_addr)
        card = svc._to_card(place, parsed=_tapas_parsed())
        assert card is not None
        assert card.google_verification is not None
        assert card.google_verification.formatted_address == expected_addr

    def test_google_maps_uri_preserved(self) -> None:
        svc = _make_svc()
        expected_uri = "https://maps.google.com/?cid=999"
        place = _make_place_with_location(maps_uri=expected_uri)
        card = svc._to_card(place, parsed=_tapas_parsed())
        assert card is not None
        assert card.google_verification is not None
        assert card.google_verification.google_maps_uri == expected_uri

    def test_confidence_is_high_when_place_id_present(self) -> None:
        svc = _make_svc()
        place = _make_place_with_location()
        card = svc._to_card(place, parsed=_tapas_parsed())
        assert card is not None
        assert card.google_verification is not None
        assert card.google_verification.confidence == "high"

    def test_provider_is_google_places(self) -> None:
        svc = _make_svc()
        place = _make_place_with_location()
        card = svc._to_card(place, parsed=_tapas_parsed())
        assert card is not None
        gv = card.google_verification
        assert gv is not None
        assert gv.provider == "google_places"


# ── 5. Legacy ConciergeSuggestion — reason-only, no coord fields ─────────────


class TestLegacyConciergeSuggestionContract:
    def test_concierge_suggestion_interface_is_reason_only(self) -> None:
        """The legacy ConciergeSuggestion type carries only name/type/reason.
        addConciergeItemToTrip writes only { reason }, which is safe because
        no googleVerification or coordinate data ever flows through this path.
        """
        import ast
        import pathlib

        api_src = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "lib" / "api.ts"
        )
        if not api_src.exists():
            pytest.skip("frontend api.ts not found from backend test runner")

        text = api_src.read_text()
        # ConciergeSuggestion must NOT have lat/lng or googleVerification
        idx = text.find("export interface ConciergeSuggestion")
        assert idx != -1, "ConciergeSuggestion must exist in api.ts"
        block = text[idx : idx + 300]
        assert "lat" not in block, "ConciergeSuggestion must not have lat field"
        assert "lng" not in block, "ConciergeSuggestion must not have lng field"
        assert "googleVerification" not in block, (
            "ConciergeSuggestion must not have googleVerification field"
        )

    def test_add_concierge_item_to_trip_writes_only_reason(self) -> None:
        import pathlib
        api_src = (
            pathlib.Path(__file__).parent.parent.parent
            / "frontend" / "src" / "lib" / "api.ts"
        )
        if not api_src.exists():
            pytest.skip("frontend api.ts not found from backend test runner")

        text = api_src.read_text()
        # Find the addConciergeItemToTrip function body
        idx = text.find("export async function addConciergeItemToTrip(")
        assert idx != -1
        body = text[idx : idx + 400]
        # Must write reason
        assert "reason" in body, "addConciergeItemToTrip must write reason"
        # Must NOT write lat/lng — legacy path must stay simple
        assert "lat" not in body, (
            "addConciergeItemToTrip must not write lat (no coords in ConciergeSuggestion)"
        )
        assert "lng" not in body, (
            "addConciergeItemToTrip must not write lng (no coords in ConciergeSuggestion)"
        )


# ── 6. No route optimization / geocoding symbols ─────────────────────────────


class TestNoForbiddenSymbols:
    def _src(self) -> str:
        import pathlib
        p = (
            pathlib.Path(__file__).parent.parent
            / "app" / "services" / "fast_dynamic_place_search.py"
        )
        return p.read_text()

    def test_no_route_optimization_symbols(self) -> None:
        src = self._src()
        forbidden = [
            "DirectionsAPI",
            "DistanceMatrix",
            "RoutesAPI",
            "optimizeRoute",
            "routeOptimiz",
            "reorder_items",
            "OptimizeDay",
        ]
        for symbol in forbidden:
            assert symbol not in src, (
                f"fast_dynamic_place_search must not reference {symbol!r}"
            )

    def test_no_geocoding_calls(self) -> None:
        src = self._src()
        geocode_patterns = ["geocode(", "geocoding", "Geocoding", "reverse_geocode"]
        for pat in geocode_patterns:
            assert pat not in src, (
                f"fast_dynamic_place_search must not geocode — found {pat!r}"
            )

    def test_coordinate_extraction_is_from_google_response_only(self) -> None:
        src = self._src()
        # The lat/lng extraction must come from the location dict from Google's response
        assert '"latitude"' in src or "'latitude'" in src, (
            "lat must be extracted from Google's location.latitude field"
        )
        assert '"longitude"' in src or "'longitude'" in src, (
            "lng must be extracted from Google's location.longitude field"
        )
