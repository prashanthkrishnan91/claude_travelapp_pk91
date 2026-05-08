"""Search endpoints — /search/flights, /search/hotels, /search/restaurants.

Product Surface Pruning v1A → v1C — route classification
--------------------------------------------------------
These routes predate the canonical AI Concierge display contract.  The
``LEGACY_PRODUCT_MOCK_DEPENDENT_ROUTES`` registry below is the single source
of truth for which routes still depend on the quarantined ``SearchService``
mock fixtures (see ``backend/app/services/search.py`` and
``docs/ai/HANDOFF.md``).

Classification (A=user-facing must preserve / B=migrate to AI Concierge /
C=internal/test/demo / D=dead / E=unclear):

- ``POST /search/flights`` — class A, mock-backed, called by
  ``OptimizeTripModal`` and ``/trips/create-with-search``.  Quarantined via
  ``BLOCK_LEGACY_PRODUCT_MOCK`` until a real provider lands.
- ``POST /search/round-trip-flights`` — class C, no direct frontend caller,
  invoked by ``/trips/create-with-search``.  Same quarantine path.
- ``POST /search/hotels`` — class A, mock-backed, called by
  ``OptimizeTripModal`` and ``/trips/create-with-search``.  Same quarantine
  path.
- ``POST /search/restaurants`` — class A, real Google Places provider,
  fail-closed when no API key.  Already canonical; **not** quarantined.

Routes deleted in v1C (Product Surface Cleanup deletion variant — orphaned
after PR #289 migrated TripBuilder Explore onto ``/ai/concierge/search``):

- ``POST /search/attractions`` — removed.  Frontend now uses
  ``searchAttractionsViaConcierge(...)`` against ``/ai/concierge/search``.
- ``POST /search/clusters`` — removed.  Grouped/Areas view was deleted in
  PR #289; no canonical replacement exists.
- ``POST /search/best-area`` — removed.  Best Area card was deleted in PR
  #289; no canonical replacement exists.

The ``/ai/concierge*`` family (see ``backend/app/routes/ai.py``) is the
canonical place-card surface and goes through
``backend/app/concierge/display_contract.py`` at the response boundary.
"""

import logging
from typing import List

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.cost_guardrails import GuardrailRule, guardrails
from app.core.deps import DB, CurrentUserID
from app.models.search import (
    FlightResult,
    FlightSearchRequest,
    HotelResult,
    HotelSearchRequest,
    RestaurantResult,
    RestaurantSearchRequest,
    RoundTripFlightPair,
)

from app.services.search import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


# ---------------------------------------------------------------------------
# Product Surface Pruning v1A/v1C — route classification registries
# ---------------------------------------------------------------------------

# Routes whose response data still depends (directly or transitively) on the
# legacy ``SearchService`` mock fixtures.  Keep this registry in sync with
# ``LEGACY_PRODUCT_MOCK_FUNCTIONS`` in ``backend/app/services/search.py``.
#
# v1C deletion variant (this file): /search/attractions, /search/clusters,
# and /search/best-area were removed.  Their entries must NOT reappear here;
# the v1A regression suite enforces that via a stale-entry guard test.
LEGACY_PRODUCT_MOCK_DEPENDENT_ROUTES: frozenset = frozenset({
    "/search/flights",
    "/search/round-trip-flights",
    "/search/hotels",
})

# Routes that are already canonical (do not depend on legacy mocks).  Listed
# here so the v1A regression tests can assert the partition is exhaustive.
CANONICAL_PRODUCT_ROUTES: frozenset = frozenset({
    "/search/restaurants",
})

# Routes deleted in v1C — kept here as an explicit "do not resurrect" list.
# The v1A regression suite asserts none of these reappear in the route source
# or in ``LEGACY_PRODUCT_MOCK_DEPENDENT_ROUTES``.
DELETED_LEGACY_PRODUCT_ROUTES: frozenset = frozenset({
    "/search/attractions",
    "/search/clusters",
    "/search/best-area",
})


@router.post("/flights", response_model=List[FlightResult])
def search_flights(payload: FlightSearchRequest, db: DB, user_id: CurrentUserID) -> List[FlightResult]:
    """Search for available flights.

    Returns a list of flight options normalised to a consistent schema
    (price, points_estimate, rating, location, booking_url, source) plus
    flight-specific fields. Results are cached in Supabase for 1 hour.
    """
    logger.info(
        "[search_flights] received request: origin=%s destination=%s departure_date=%s passengers=%d cabin_class=%s",
        payload.origin,
        payload.destination,
        payload.departure_date,
        payload.passengers,
        payload.cabin_class,
    )
    settings = get_settings()
    guardrails.enforce(
        endpoint_key="search.search_flights",
        user_id=user_id,
        rule=GuardrailRule(
            requests=settings.guardrail_search_requests,
            window_seconds=settings.guardrail_search_window_seconds,
            dedupe_seconds=settings.guardrail_search_dedupe_seconds,
        ),
        dedupe_payload={"origin": payload.origin, "destination": payload.destination, "departure_date": payload.departure_date, "return_date": payload.return_date},
    )
    return SearchService(db).search_flights(payload)


@router.post("/round-trip-flights", response_model=List[RoundTripFlightPair])
def search_round_trip_flights(payload: FlightSearchRequest, db: DB, user_id: CurrentUserID) -> List[RoundTripFlightPair]:
    """Search for round-trip flight pairs.

    Requires ``return_date`` in the payload. Returns pairs ranked by combined
    CPP (desc), total price (asc), and total duration (asc).
    """
    logger.info(
        "[search_round_trip_flights] origin=%s destination=%s departure=%s return=%s",
        payload.origin,
        payload.destination,
        payload.departure_date,
        payload.return_date,
    )
    settings = get_settings()
    guardrails.enforce(
        endpoint_key="search.search_round_trip_flights",
        user_id=user_id,
        rule=GuardrailRule(
            requests=settings.guardrail_search_requests,
            window_seconds=settings.guardrail_search_window_seconds,
            dedupe_seconds=settings.guardrail_search_dedupe_seconds,
        ),
        dedupe_payload={"origin": payload.origin, "destination": payload.destination, "departure_date": payload.departure_date, "return_date": payload.return_date},
    )
    return SearchService(db).search_round_trip_flights(payload)


@router.post("/hotels", response_model=List[HotelResult])
def search_hotels(payload: HotelSearchRequest, db: DB, user_id: CurrentUserID) -> List[HotelResult]:
    """Search for available hotels.

    Returns a list of hotel options normalised to a consistent schema plus
    hotel-specific fields (name, stars, amenities, price_per_night, etc.).
    Results are cached in Supabase for 1 hour.
    """
    settings = get_settings()
    guardrails.enforce(
        endpoint_key="search.search_hotels",
        user_id=user_id,
        rule=GuardrailRule(
            requests=settings.guardrail_search_requests,
            window_seconds=settings.guardrail_search_window_seconds,
            dedupe_seconds=settings.guardrail_search_dedupe_seconds,
        ),
        dedupe_payload={"location": payload.location, "check_in": payload.check_in, "check_out": payload.check_out},
    )
    return SearchService(db).search_hotels(payload)


@router.post("/restaurants", response_model=List[RestaurantResult])
def search_restaurants(payload: RestaurantSearchRequest, db: DB, user_id: CurrentUserID) -> List[RestaurantResult]:
    """Search for restaurants, cafes, and local dining options.

    Returns a list of dining options sorted by AI score (rating, review count,
    price level, sentiment). Covers restaurants, cafes, and local dining.
    Results are cached in Supabase for 1 hour.
    """
    logger.info("[search_restaurants] location=%s cuisine=%s", payload.location, payload.cuisine)
    settings = get_settings()
    guardrails.enforce(
        endpoint_key="search.search_restaurants",
        user_id=user_id,
        rule=GuardrailRule(
            requests=settings.guardrail_search_requests,
            window_seconds=settings.guardrail_search_window_seconds,
            dedupe_seconds=settings.guardrail_search_dedupe_seconds,
        ),
        dedupe_payload={"location": payload.location, "cuisine": payload.cuisine, "date": payload.date},
    )
    return SearchService(db).search_restaurants(payload)
