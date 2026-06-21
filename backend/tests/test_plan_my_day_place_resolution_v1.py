"""Plan My Day Place Resolution v1 — canonical place resolution at the
``/plan/day`` boundary.

Problem (follow-up to PR #499): Plan My Day could create itinerary items with
display address/rating/category but no lat/lng or canonical place identity, so
travel hints fell back to "Add location details to improve travel hints."

Fix: ``PlannedAttraction`` / ``PlannedRestaurant`` (and ``AttractionResult``)
now carry canonical Google place identity (``place_id`` + ``google_maps_uri``),
the ``/plan/day`` route forwards that identity, and a best-effort
``_resolve_day_plan_coords`` step resolves place-like recommendations missing
coordinates via the **existing** Google Places details path
(``SearchService.resolve_place_details``) before the response is returned.

Never fabricates: when resolution fails the item keeps an honest
coordinate-less fallback (display address/category/rating preserved). Items
that already have coordinates are not re-resolved (no extra provider calls).
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace

from app.models import plan as plan_models
from app.models import search as search_models
from app.routes import plan as plan_routes


def _read_search_service_src() -> str:
    import os
    here = os.path.dirname(__file__)
    path = os.path.join(here, "..", "app", "services", "search.py")
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# 1. Canonical place identity fields on the wire models.
# ---------------------------------------------------------------------------

def test_planned_attraction_has_place_identity_fields():
    fields = plan_models.PlannedAttraction.model_fields
    assert "place_id" in fields
    assert "google_maps_uri" in fields


def test_planned_restaurant_has_place_identity_fields():
    fields = plan_models.PlannedRestaurant.model_fields
    assert "place_id" in fields
    assert "google_maps_uri" in fields


def test_attraction_result_has_place_identity_fields():
    fields = search_models.AttractionResult.model_fields
    assert "place_id" in fields
    assert "google_maps_uri" in fields
    assert "provider_place_id" in fields


def test_place_identity_fields_default_none_never_fabricated():
    pa = plan_models.PlannedAttraction(
        id="attr-x",
        name="Some Park",
        category="park",
        description="",
        location="Miami",
        address="123 Anywhere",
    )
    dumped = pa.model_dump()
    assert dumped["place_id"] is None
    assert dumped["google_maps_uri"] is None
    assert dumped["lat"] is None
    assert dumped["lng"] is None


# ---------------------------------------------------------------------------
# 2. Route forwards identity + runs resolution in both paths (source scan).
# ---------------------------------------------------------------------------

def test_plan_route_forwards_attraction_place_identity():
    src = inspect.getsource(plan_routes)
    assert "place_id=a.place_id" in src
    assert "google_maps_uri=a.google_maps_uri" in src


def test_plan_route_forwards_restaurant_place_identity():
    src = inspect.getsource(plan_routes)
    assert "place_id=lunch.place_id" in src
    assert "place_id=dinner.place_id" in src
    assert "google_maps_uri=lunch.google_maps_uri" in src
    assert "google_maps_uri=dinner.google_maps_uri" in src


def test_plan_route_runs_resolution_in_both_paths():
    src = inspect.getsource(plan_routes)
    # Resolution is invoked on both the canonical-search and cluster paths.
    assert src.count("_resolve_day_plan_coords(") >= 2


def test_search_result_path_sets_place_identity():
    """search_attraction_results must stamp the real place_id + maps uri."""
    src = inspect.getsource(plan_routes)
    # Defensive: route no longer drops identity on the AttractionResult branch.
    assert "place_id=a.place_id" in src


# ---------------------------------------------------------------------------
# 3. _place_id_of — explicit field first, then gp- prefix fallback.
# ---------------------------------------------------------------------------

def test_place_id_of_prefers_explicit_field():
    item = SimpleNamespace(place_id="ChIJexplicit", id="gp-ChIJother")
    assert plan_routes._place_id_of(item) == "ChIJexplicit"


def test_place_id_of_strips_gp_prefix():
    item = SimpleNamespace(place_id=None, id="gp-ChIJfrost123")
    assert plan_routes._place_id_of(item) == "ChIJfrost123"


def test_place_id_of_returns_none_without_identity():
    item = SimpleNamespace(place_id=None, id="cluster-row-7")
    assert plan_routes._place_id_of(item) is None


# ---------------------------------------------------------------------------
# 4. _resolve_day_plan_coords — fills only on success, never fabricates.
# ---------------------------------------------------------------------------

class _FakeSearch:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def resolve_place_details(self, place_id):
        self.calls.append(place_id)
        return self.mapping.get(place_id)


def _response_with(attraction):
    restaurant = plan_models.PlannedRestaurant(
        id="r-1", name="Cafe", cuisine="Cafe", location="Miami", address="addr",
        lat=25.0, lng=-80.0, place_id="ChIJcafe",
    )
    return plan_models.DayPlanResponse(
        trip_id="00000000-0000-0000-0000-000000000000",
        day_number=1,
        destination="Miami",
        attractions=[attraction],
        lunch=restaurant,
        dinner=restaurant,
    )


def test_resolve_fills_missing_coords_from_details():
    attraction = plan_models.PlannedAttraction(
        id="gp-ChIJfrost", name="Frost Museum", category="museum",
        description="", location="Miami", address="1101 Biscayne Blvd",
        place_id="ChIJfrost",
    )
    resp = _response_with(attraction)
    fake = _FakeSearch({"ChIJfrost": {
        "lat": 25.7853, "lng": -80.1864,
        "google_maps_uri": "https://maps.google.com/?cid=frost",
        "address": "1101 Biscayne Blvd",
    }})
    plan_routes._resolve_day_plan_coords(resp, fake)
    assert resp.attractions[0].lat == 25.7853
    assert resp.attractions[0].lng == -80.1864
    assert resp.attractions[0].google_maps_uri == "https://maps.google.com/?cid=frost"


def test_resolve_keeps_honest_fallback_on_failure():
    attraction = plan_models.PlannedAttraction(
        id="gp-ChIJnoloc", name="Mystery Place", category="landmark",
        description="", location="Miami", address="somewhere",
        place_id="ChIJnoloc",
    )
    resp = _response_with(attraction)
    fake = _FakeSearch({})  # resolution returns None
    plan_routes._resolve_day_plan_coords(resp, fake)
    assert resp.attractions[0].lat is None
    assert resp.attractions[0].lng is None
    # Display metadata preserved — only the honest fallback, no fabrication.
    assert resp.attractions[0].address == "somewhere"
    assert resp.attractions[0].category == "landmark"


def test_resolve_skips_items_that_already_have_coords():
    attraction = plan_models.PlannedAttraction(
        id="gp-ChIJhascoords", name="Bayfront Park", category="park",
        description="", location="Miami", address="301 Biscayne Blvd",
        lat=25.7753, lng=-80.1864, place_id="ChIJhascoords",
    )
    resp = _response_with(attraction)
    fake = _FakeSearch({"ChIJhascoords": {"lat": 0.0, "lng": 0.0}})
    plan_routes._resolve_day_plan_coords(resp, fake)
    # Already-coord item is not re-resolved → no provider call for it.
    assert "ChIJhascoords" not in fake.calls
    assert resp.attractions[0].lat == 25.7753


def test_resolve_skips_items_without_place_identity():
    attraction = plan_models.PlannedAttraction(
        id="cluster-row", name="Unknown", category="landmark",
        description="", location="Miami", address="addr",
    )
    resp = _response_with(attraction)
    fake = _FakeSearch({"anything": {"lat": 1.0, "lng": 2.0}})
    plan_routes._resolve_day_plan_coords(resp, fake)
    assert resp.attractions[0].lat is None
    assert fake.calls == []


# ---------------------------------------------------------------------------
# 5. resolve_place_details — reuses existing Google Places provider, fails
#    closed, never fabricates (source-scan; full provider import needs the
#    FastAPI service chain only available in CI).
# ---------------------------------------------------------------------------

def test_resolve_place_details_reuses_existing_google_places_provider():
    src = _read_search_service_src()
    assert "def resolve_place_details" in src
    # Same provider family + same API key env — no new provider architecture.
    assert "_GOOGLE_PLACES_DETAILS_ENDPOINT" in src
    assert 'os.getenv("GOOGLE_PLACES_API_KEY"' in src


def test_resolve_place_details_fails_closed_without_key_or_httpx():
    src = _read_search_service_src()
    body = src.split("def resolve_place_details", 1)[1].split("\n    def ", 1)[0]
    assert "if not api_key or httpx is None:" in body
    assert "return None" in body


def test_resolve_place_details_never_fabricates_missing_coords():
    src = _read_search_service_src()
    body = src.split("def resolve_place_details", 1)[1].split("\n    def ", 1)[0]
    # Returns None when the details response lacks a real location.
    assert "if lat is None or lng is None:" in body


def test_search_attraction_results_stamps_place_identity():
    src = _read_search_service_src()
    body = src.split("def search_attraction_results", 1)[1].split("\n    def ", 1)[0]
    assert "place_id=place_id" in body
    assert "google_maps_uri=place.get" in body


# ---------------------------------------------------------------------------
# 6. Coordinate pass-through — lat/lng persisted in both plan route paths.
#    Acceptance criteria: "Plan My Day attraction/restaurant with lat/lng
#    persists canonical coords."
# ---------------------------------------------------------------------------

def test_plan_route_forwards_attraction_lat_lng():
    """Non-cluster path passes attraction lat/lng into PlannedAttraction."""
    src = inspect.getsource(plan_routes)
    assert "lat=a.lat" in src
    assert "lng=a.lng" in src


def test_plan_route_forwards_restaurant_lat_lng():
    """Non-cluster path passes lunch/dinner lat/lng into PlannedRestaurant."""
    src = inspect.getsource(plan_routes)
    assert "lat=lunch.lat" in src
    assert "lng=lunch.lng" in src
    assert "lat=dinner.lat" in src
    assert "lng=dinner.lng" in src


def test_cluster_path_does_not_forward_null_island_coords():
    """Cluster path guards against 0.0 default — no null-island coordinates."""
    src = inspect.getsource(plan_routes)
    assert "lat=(a.lat if a.lat else None)" in src
    assert "lng=(a.lng if a.lng else None)" in src


def test_search_attraction_results_stamps_lat_lng():
    """search_attraction_results stamps lat/lng from the place dict."""
    src = _read_search_service_src()
    body = src.split("def search_attraction_results", 1)[1].split("\n    def ", 1)[0]
    assert 'lat=place.get("lat")' in body
    assert 'lng=place.get("lng")' in body
