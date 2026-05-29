"""Trip Item Metadata Parity v1.2 — day-plan route forwards routeable coordinates.

Failure seam discovered via Vercel preview + production DB inspection on PR #499:
three Build/Day-Plan items in Miami (Torch of Friendship, Miami Skyline View,
Phillip & Patricia Frost Museum of Science) were persisted with `details.lat`
and `details.lng` both `null`, even though the underlying provider results
(AttractionResult / ClusterPlaceInput) carry real coordinates.

Root cause: `PlannedAttraction` and `PlannedRestaurant` in
`backend/app/models/plan.py` had no `lat`/`lng` fields, so the `/plan/day`
response shape silently dropped coordinates. The frontend
`handlePlanAddAttraction` then called `addAttractionToDay` with
`attraction.lat == undefined`, which serialized to `lat: null` on the placed
item, and `computeAdjacentHints` emitted the "Add location details to
improve travel hints." fallback.

Fix: `PlannedAttraction` and `PlannedRestaurant` now carry optional `lat`
and `lng`, and `/plan/day` forwards them from the underlying provider rows.
Never fabricates: `0.0` defaults on `ClusterPlaceInput` are treated as
missing rather than written as (0,0).
"""
from __future__ import annotations

import inspect

from app.models import plan as plan_models
from app.routes import plan as plan_routes


def test_planned_attraction_has_lat_lng_fields():
    fields = plan_models.PlannedAttraction.model_fields
    assert "lat" in fields, "PlannedAttraction must carry routeable lat"
    assert "lng" in fields, "PlannedAttraction must carry routeable lng"


def test_planned_restaurant_has_lat_lng_fields():
    fields = plan_models.PlannedRestaurant.model_fields
    assert "lat" in fields, "PlannedRestaurant must carry routeable lat"
    assert "lng" in fields, "PlannedRestaurant must carry routeable lng"


def test_planned_attraction_lat_lng_optional_and_default_none():
    fields = plan_models.PlannedAttraction.model_fields
    lat_field = fields["lat"]
    lng_field = fields["lng"]
    # Optional with default None — never fabricates a coordinate.
    assert lat_field.default is None
    assert lng_field.default is None


def test_planned_restaurant_lat_lng_optional_and_default_none():
    fields = plan_models.PlannedRestaurant.model_fields
    assert fields["lat"].default is None
    assert fields["lng"].default is None


def test_plan_day_route_forwards_attraction_coords_from_attraction_result():
    """The AttractionResult → PlannedAttraction path must forward lat/lng."""
    src = inspect.getsource(plan_routes)
    # Inside the AttractionResult-based branch the PlannedAttraction
    # constructor must pass lat=a.lat and lng=a.lng.
    assert "lat=a.lat" in src, "PlannedAttraction must forward a.lat from AttractionResult"
    assert "lng=a.lng" in src, "PlannedAttraction must forward a.lng from AttractionResult"


def test_plan_day_route_forwards_restaurant_coords_from_restaurant_result():
    src = inspect.getsource(plan_routes)
    assert "lat=lunch.lat" in src, "lunch must forward RestaurantResult.lat"
    assert "lng=lunch.lng" in src, "lunch must forward RestaurantResult.lng"
    assert "lat=dinner.lat" in src, "dinner must forward RestaurantResult.lat"
    assert "lng=dinner.lng" in src, "dinner must forward RestaurantResult.lng"


def test_plan_day_cluster_path_treats_zero_coords_as_missing():
    """ClusterPlaceInput defaults lat/lng to 0.0 — a real (0,0) coordinate must
    not be fabricated for places that simply omitted coords on input."""
    src = inspect.getsource(plan_routes)
    # 0.0 → None guard must be present in the cluster-path constructors.
    assert "if a.lat else None" in src
    assert "if a.lng else None" in src
    assert "if lunch.lat else None" in src
    assert "if dinner.lng else None" in src


def test_plan_day_constructs_planned_attraction_with_real_coords():
    pa = plan_models.PlannedAttraction(
        id="attr-1",
        name="Maurice A. Ferré Park",
        category="park",
        description="",
        location="Miami",
        address="1075 Biscayne Blvd, Miami, FL 33132, USA",
        lat=25.78435829,
        lng=-80.1871918,
    )
    dumped = pa.model_dump()
    assert dumped["lat"] == 25.78435829
    assert dumped["lng"] == -80.1871918


def test_plan_day_planned_attraction_omits_coords_when_missing():
    """When the source has no coordinates, PlannedAttraction must serialize
    lat/lng as None — never fabricated (0,0) or geocoded from address."""
    pa = plan_models.PlannedAttraction(
        id="attr-2",
        name="Torch of Friendship",
        category="landmark",
        description="",
        location="Miami",
        address="301 Biscayne Blvd, Miami, FL 33132, USA",
    )
    dumped = pa.model_dump()
    assert dumped["lat"] is None
    assert dumped["lng"] is None
