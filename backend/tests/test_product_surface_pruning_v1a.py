"""Product Surface Pruning v1A — quarantine and caller-registry guards.

This file is the contract test for the v1A architecture rescue:

1. ``BLOCK_LEGACY_PRODUCT_MOCK`` env flag short-circuits every legacy mock
   fixture in ``backend/app/services/search.py`` to an empty list and emits
   structured ``[legacy_product_mock.blocked]`` telemetry.
2. Unblocked emission emits ``[legacy_product_mock.emitted]`` so production
   logs expose the leakage rate while v1B migrates the frontend callers.
3. Every legacy mock helper carries the ``__legacy_product_mock__`` marker so
   the registry stays in sync with reality.
4. ``LEGACY_PRODUCT_MOCK_DEPENDENT_ROUTES`` (in
   ``backend/app/routes/search.py``) is the single source of truth for
   which ``/search/*`` routes still depend on those fixtures, and the
   classification is exhaustive across the route file.
5. **Frontend caller registry** — only the files in
   ``_KNOWN_LEGACY_SEARCH_CALLERS`` are allowed to reference the legacy
   ``/search/{flights,hotels,attractions,best-area,clusters,round-trip-flights}``
   routes (or their typed helpers ``searchFlights`` / ``searchHotels`` / etc).
   Any new caller fails this test and forces an explicit decision.

Add new mock fixtures or new callers only by extending these registries
(after explicit classification in ``docs/ai/HANDOFF.md``).  No semantic
retrieval / ranking / note-writing changes belong in this file.
"""
from __future__ import annotations

import logging
import os
import pathlib
import sys
import types
from datetime import date
from unittest.mock import MagicMock

import pytest

# Stubs for the heavy stack so this test runs in the same environment as
# test_concierge_result_quality.py / test_concierge_context_resolver.py.
# Mirrors the conftest pattern that lets us import ``app.routes.*`` without
# pulling FastAPI's full dependency-injection chain.
for _mod in ["fastapi", "supabase", "anthropic"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

_core_path = os.path.join(os.path.dirname(__file__), "..", "app", "core")
_core_mod = sys.modules.get("app.core")
if _core_mod is None:
    _core_mod = types.ModuleType("app.core")
    sys.modules["app.core"] = _core_mod
if not hasattr(_core_mod, "__path__"):
    _core_mod.__path__ = [_core_path]

_deps_mod = sys.modules.get("app.core.deps")
if _deps_mod is None:
    _deps_mod = types.ModuleType("app.core.deps")
    sys.modules["app.core.deps"] = _deps_mod
if not hasattr(_deps_mod, "DB"):
    setattr(_deps_mod, "DB", object)
if not hasattr(_deps_mod, "CurrentUserID"):
    setattr(_deps_mod, "CurrentUserID", object)

if "app.routes" not in sys.modules:
    _routes_pkg = types.ModuleType("app.routes")
    _routes_pkg.__path__ = [
        os.path.join(os.path.dirname(__file__), "..", "app", "routes")
    ]
    sys.modules["app.routes"] = _routes_pkg

from app.models.search import (  # noqa: E402  (stubs above must run first)
    FlightSearchRequest,
    HotelSearchRequest,
)
from app.routes import search as search_routes  # noqa: E402
from app.services import search as search_service  # noqa: E402


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def block_flag_off(monkeypatch):
    monkeypatch.delenv(search_service._LEGACY_PRODUCT_MOCK_BLOCK_ENV, raising=False)
    yield


@pytest.fixture
def block_flag_on(monkeypatch):
    monkeypatch.setenv(search_service._LEGACY_PRODUCT_MOCK_BLOCK_ENV, "1")
    yield


# ---------------------------------------------------------------------------
# 1. Env flag block + telemetry
# ---------------------------------------------------------------------------


def test_block_flag_default_is_off(monkeypatch):
    """Without the env var, the operator block is off (preserves prior behavior)."""
    monkeypatch.delenv(search_service._LEGACY_PRODUCT_MOCK_BLOCK_ENV, raising=False)
    assert search_service._legacy_product_mock_blocked() is False


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1", True),
        ("true", True),
        ("True", True),
        ("yes", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("", False),
        ("nope", False),
    ],
)
def test_block_flag_parses_truthy_values(monkeypatch, raw: str, expected: bool):
    monkeypatch.setenv(search_service._LEGACY_PRODUCT_MOCK_BLOCK_ENV, raw)
    assert search_service._legacy_product_mock_blocked() is expected


def test_mock_attractions_helper_was_deleted_in_v1d():
    """v1D: ``_mock_attractions`` was removed entirely and must stay gone.

    ``SearchService.search_attractions`` was also deleted in v1D but has since
    been reintroduced as a real Google-Places-backed provider (Level 2 seeding
    fix, 2026-05-10) — it is NOT a mock fixture.  This test now asserts:

    1. The mock module-level helper ``_mock_attractions`` remains absent.
    2. The live ``search_attractions`` method, when present, must fail closed
       (return []) when the Google Places API key is absent — proving it is
       not a mock fixture that fabricates data.
    """
    assert not hasattr(search_service, "_mock_attractions"), (
        "_mock_attractions was deleted in v1D and must not be reintroduced; "
        "the canonical attraction surface is Google Places + /ai/concierge/search."
    )
    # search_attractions was re-added as a real Google Places provider.
    # The contract: it must fail closed (empty list) when the API key is absent.
    if hasattr(search_service.SearchService, "search_attractions"):
        import os
        import unittest.mock as _mock
        with _mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GOOGLE_PLACES_API_KEY", None)
            svc = search_service.SearchService(db=_mock.MagicMock())
            result = svc.search_attractions("Tokyo")
        assert result == [], (
            "search_attractions must return [] (fail closed) when "
            "GOOGLE_PLACES_API_KEY is absent — it must not fabricate data."
        )


def test_block_flag_blocks_mock_hotels(block_flag_on, caplog):
    caplog.set_level(logging.WARNING)
    out = search_service._mock_hotels(
        HotelSearchRequest(location="Paris", check_in=date(2026, 6, 1), check_out=date(2026, 6, 5))
    )
    assert out == []
    assert any(
        "[legacy_product_mock.blocked]" in rec.getMessage()
        and "namespace=hotels" in rec.getMessage()
        for rec in caplog.records
    )


def test_block_flag_blocks_mock_flights(block_flag_on, caplog):
    caplog.set_level(logging.WARNING)
    out = search_service._mock_flights(
        FlightSearchRequest(origin="LAX", destination="JFK", departure_date=date(2026, 6, 1))
    )
    assert out == []
    assert any(
        "[legacy_product_mock.blocked]" in rec.getMessage()
        and "namespace=flights" in rec.getMessage()
        for rec in caplog.records
    )


def test_mock_restaurants_helper_was_deleted_in_closeout():
    """Final mock-leak closeout: ``_mock_restaurants`` was removed entirely.
    ``SearchService.search_restaurants`` runs canonical Google Places with
    fail-closed semantics (no provider key → empty list); the mock fixture
    had no live caller and was deleted.  This guard prevents silent
    re-introduction (e.g. via a stray helper or merge mishap)."""
    assert not hasattr(search_service, "_mock_restaurants"), (
        "_mock_restaurants was deleted in the final mock-leak closeout and "
        "must not be reintroduced; the canonical restaurant surface is "
        "SearchService.search_restaurants → Google Places."
    )


def test_unblocked_emit_emits_leak_telemetry(block_flag_off, caplog):
    """When the operator has not flipped the flag, the remaining mock
    fixtures still emit results, but the ``legacy_product_mock.emitted``
    event must be logged so leakage rate is observable in production.

    Final mock-leak closeout: previously asserted on ``_mock_restaurants``
    (deleted as orphan); switched to ``_mock_hotels`` which is the
    quarantined helper still preserved for provider-backed Hotels v1.
    """
    from datetime import date as _date

    caplog.set_level(logging.WARNING)
    out = search_service._mock_hotels(
        HotelSearchRequest(
            location="Paris", check_in=_date(2026, 6, 1), check_out=_date(2026, 6, 5)
        )
    )
    assert len(out) > 0
    matching = [
        rec
        for rec in caplog.records
        if "[legacy_product_mock.emitted]" in rec.getMessage()
        and "namespace=hotels" in rec.getMessage()
    ]
    assert matching, "Unblocked mock emission must log a structured leak event"
    assert any("returned=" in rec.getMessage() for rec in matching)


# ---------------------------------------------------------------------------
# 2. Legacy mock registry stays in sync with reality
# ---------------------------------------------------------------------------


def test_legacy_product_mock_registry_lists_remaining_helpers():
    """v1D removed ``_mock_attractions``; the final mock-leak closeout
    removed ``_mock_restaurants`` (orphan).  The registry must reflect the
    remaining two quarantined fixtures (flights / hotels), preserved for a
    future provider-backed Flights/Hotels v1."""
    names = sorted(fn.__name__ for fn in search_service.LEGACY_PRODUCT_MOCK_FUNCTIONS)
    assert names == sorted(["_mock_flights", "_mock_hotels"])
    assert "_mock_attractions" not in names
    assert "_mock_restaurants" not in names


def test_every_registered_function_carries_marker():
    for fn in search_service.LEGACY_PRODUCT_MOCK_FUNCTIONS:
        assert search_service.is_legacy_product_mock(fn), (
            f"{fn.__name__} is in the registry but missing __legacy_product_mock__"
        )


def test_marker_does_not_leak_to_unrelated_callables():
    assert not search_service.is_legacy_product_mock(search_service.SearchService)
    assert not search_service.is_legacy_product_mock(search_service._cache_key)


def test_no_new_underscore_mock_fixture_added_silently():
    """Drift guard: any new top-level ``_mock_*`` callable in the module must
    be added to ``LEGACY_PRODUCT_MOCK_FUNCTIONS`` so the v1A regression
    surface stays exhaustive.  The intent is to force a deliberate
    classification decision before extending the legacy surface."""
    discovered = {
        name
        for name, obj in vars(search_service).items()
        if callable(obj) and name.startswith("_mock_")
    }
    registered = {fn.__name__ for fn in search_service.LEGACY_PRODUCT_MOCK_FUNCTIONS}
    missing = discovered - registered
    assert not missing, (
        "Found _mock_* helpers that are not in LEGACY_PRODUCT_MOCK_FUNCTIONS: "
        f"{sorted(missing)}"
    )


# ---------------------------------------------------------------------------
# 3. Route classification is exhaustive
# ---------------------------------------------------------------------------


def _route_paths_in_search_router() -> set[str]:
    """Parse ``backend/app/routes/search.py`` for every ``@router.post`` /
    ``@router.get`` declaration and return the prefixed ``/search/...``
    paths.  We read the source file rather than the live ``router.routes``
    list because the conftest mocks FastAPI's runtime, which leaves the
    in-memory router empty under test."""
    import re as _re

    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    src = (repo_root / "backend" / "app" / "routes" / "search.py").read_text(encoding="utf-8")
    pattern = _re.compile(r'@router\.(?:post|get|put|patch|delete)\(\s*"([^"]+)"')
    paths: set[str] = set()
    for match in pattern.finditer(src):
        sub_path = match.group(1)
        if not sub_path.startswith("/"):
            sub_path = "/" + sub_path
        paths.add("/search" + sub_path)
    return paths


def test_every_search_route_is_classified():
    """Either ``LEGACY_PRODUCT_MOCK_DEPENDENT_ROUTES`` or
    ``CANONICAL_PRODUCT_ROUTES`` must cover each ``/search/*`` route."""
    classified = (
        search_routes.LEGACY_PRODUCT_MOCK_DEPENDENT_ROUTES
        | search_routes.CANONICAL_PRODUCT_ROUTES
    )
    actual = _route_paths_in_search_router()
    unclassified = actual - classified
    assert not unclassified, (
        "New /search/* route(s) added without classification — extend "
        "LEGACY_PRODUCT_MOCK_DEPENDENT_ROUTES or CANONICAL_PRODUCT_ROUTES "
        f"in backend/app/routes/search.py: {sorted(unclassified)}"
    )


def test_classifications_do_not_overlap():
    overlap = (
        search_routes.LEGACY_PRODUCT_MOCK_DEPENDENT_ROUTES
        & search_routes.CANONICAL_PRODUCT_ROUTES
    )
    assert not overlap, f"A route cannot be both legacy and canonical: {overlap}"


def test_legacy_dependent_set_contains_known_mock_routes():
    """v1C deletion-variant: /search/attractions, /search/clusters, and
    /search/best-area were removed.  The remaining mock-backed routes
    (flights / hotels / round-trip-flights) must still be classified as
    legacy-dependent."""
    expected = {
        "/search/flights",
        "/search/round-trip-flights",
        "/search/hotels",
    }
    missing = expected - search_routes.LEGACY_PRODUCT_MOCK_DEPENDENT_ROUTES
    assert not missing, f"LEGACY_PRODUCT_MOCK_DEPENDENT_ROUTES is missing: {missing}"


# ---------------------------------------------------------------------------
# 3b. v1C deletion-variant: orphaned routes are gone and stay gone
# ---------------------------------------------------------------------------


_V1C_DELETED_ROUTES: frozenset = frozenset({
    "/search/attractions",
    "/search/clusters",
    "/search/best-area",
})


def test_v1c_deleted_routes_are_not_registered_in_route_source():
    """Product Surface Cleanup v1C — orphaned mock-backed routes were
    deleted from ``backend/app/routes/search.py``.  The route source must
    not register them again under any HTTP verb."""
    actual = _route_paths_in_search_router()
    resurrected = _V1C_DELETED_ROUTES & actual
    assert not resurrected, (
        "v1C-deleted routes were re-added to backend/app/routes/search.py: "
        f"{sorted(resurrected)}.  Do not restore mock-backed attraction / "
        "cluster / best-area handlers; the canonical seam is "
        "/ai/concierge/search."
    )


def test_v1c_deleted_routes_not_in_legacy_mock_dependent_registry():
    """Stale-entry guard — once a route is deleted, it must also be
    pruned from ``LEGACY_PRODUCT_MOCK_DEPENDENT_ROUTES``.  Otherwise the
    classification registry drifts away from the route source and the
    quarantine surface becomes a lie."""
    stale = _V1C_DELETED_ROUTES & search_routes.LEGACY_PRODUCT_MOCK_DEPENDENT_ROUTES
    assert not stale, (
        "Deleted v1C routes are still listed in LEGACY_PRODUCT_MOCK_DEPENDENT_ROUTES: "
        f"{sorted(stale)}.  Remove them — the route source no longer mounts these handlers."
    )


def test_v1c_deleted_routes_explicitly_tracked_as_deleted():
    """The route file ships an explicit ``DELETED_LEGACY_PRODUCT_ROUTES``
    "do not resurrect" set covering the v1C deletions.  This test wires
    that set to the same constant the regression suite uses so a future
    edit to the route file cannot silently shrink the deletion record."""
    assert hasattr(search_routes, "DELETED_LEGACY_PRODUCT_ROUTES"), (
        "backend/app/routes/search.py must export DELETED_LEGACY_PRODUCT_ROUTES "
        "as the structural record of v1C deletions."
    )
    missing = _V1C_DELETED_ROUTES - search_routes.DELETED_LEGACY_PRODUCT_ROUTES
    assert not missing, (
        "DELETED_LEGACY_PRODUCT_ROUTES must contain every v1C-deleted route: "
        f"missing {sorted(missing)}"
    )


def test_search_restaurants_is_canonical_not_legacy():
    """``/search/restaurants`` is fed by Google Places (real) with fail-closed
    semantics.  It must stay on the canonical side of the partition."""
    assert "/search/restaurants" in search_routes.CANONICAL_PRODUCT_ROUTES
    assert "/search/restaurants" not in search_routes.LEGACY_PRODUCT_MOCK_DEPENDENT_ROUTES


# ---------------------------------------------------------------------------
# 4. Frontend caller registry — leak-forward guard
# ---------------------------------------------------------------------------

# Files allowed to reference the legacy ``/search/*`` mock-backed routes or
# their typed wrappers.  This is the v1A snapshot of *current* callers; v1B
# migrates each entry off the legacy surface and removes it from this list.
#
# The list is intentionally minimal: anything not on it fails the test, which
# forces a deliberate decision (extend the v1B migration plan vs. add the
# caller and update this list) instead of silently widening the leak.
_KNOWN_LEGACY_SEARCH_CALLERS: frozenset = frozenset({
    # Still references the legacy `searchFlights` / `searchHotels` typed
    # wrappers (consumed by OptimizeTripModal — out of scope for v1B).
    pathlib.PurePosixPath("frontend/src/lib/api.ts"),
    # OptimizeTripModal still calls /search/flights and /search/hotels until
    # v1B-flights+hotels (or a real-provider follow-up) lands.
    pathlib.PurePosixPath("frontend/src/components/trips/OptimizeTripModal.tsx"),
    # Test fixtures that document the legacy surface or assert v1B
    # migration intent are explicitly allowed.
    pathlib.PurePosixPath("frontend/tests/explore-hydration.test.mjs"),
    # v1B migration regression fixture — asserts TripBuilder Explore no
    # longer calls `searchAttractions` / `searchClusters` / `fetchBestArea`.
    # The file references those tokens as `assert.doesNotMatch(...)` patterns.
    pathlib.PurePosixPath("frontend/tests/explore-concierge-migration.test.mjs"),
    # Fail-Closed UX v1 contract test — references `/search/flights` and
    # `/search/hotels` in a documentation comment explaining the mock-row
    # guard in OptimizeTripModal. No live caller; no v1B-equivalent
    # migration owed.
    pathlib.PurePosixPath("frontend/tests/fail-closed-flights-hotels.test.mjs"),
    # Hotels Product Contract v1 contract test — references
    # ``searchHotels`` in source-content assertions guarding the
    # discovery / has_real_rate markers.  No live caller; documents
    # the OptimizeTripModal discovery-only refusal.
    pathlib.PurePosixPath("frontend/tests/hotels-discovery-only.test.mjs"),
    # Flights v1 live search contract test — references ``/search/flights``
    # in a ``assert.doesNotMatch`` assertion proving ``searchFlightsExplore``
    # does NOT call the legacy route.  No live caller; documents migration intent.
    pathlib.PurePosixPath("frontend/tests/flights-ignav-live.test.mjs"),
})

# Tokens that mean "this file calls the legacy /search/* mock-backed surface".
# Distinct from ``/search/restaurants`` (canonical) and unrelated string
# literals like Google Maps URLs (``maps/search/...``) which are filtered
# below.
_LEGACY_SEARCH_TOKENS: tuple[str, ...] = (
    "/search/flights",
    "/search/round-trip-flights",
    "/search/hotels",
    "/search/attractions",
    "/search/clusters",
    "/search/best-area",
    "searchFlights",
    "searchHotels",
    "searchAttractions",
    "searchClusters",
    "fetchBestArea",
    "searchRoundTripFlights",
)

# Substrings that benignly contain ``/search/`` but are not API calls (e.g.
# Google Maps deep links that the frontend builds for "View on Maps" buttons).
_BENIGN_SEARCH_SUBSTRINGS: tuple[str, ...] = (
    "google.com/maps/search/",
)


def _file_uses_legacy_search_token(text: str) -> bool:
    """True if the file references the legacy ``/search/*`` mock surface
    after stripping benign Google Maps URL fragments.

    Camel-case typed wrappers are matched with a trailing-character guard so
    that ``searchAttractions`` does not match the canonical v1B migration
    helper ``searchAttractionsViaConcierge`` (and analogous future helpers
    like ``searchHotelsCanonical``).  Route literals (``/search/...``) are
    matched as plain substrings since they are unique to the legacy surface.
    """
    import re

    cleaned = text
    for benign in _BENIGN_SEARCH_SUBSTRINGS:
        cleaned = cleaned.replace(benign, "")
    for token in _LEGACY_SEARCH_TOKENS:
        if token.startswith("/"):
            if token in cleaned:
                return True
            continue
        # Camel-case wrapper: must NOT be followed by another identifier char,
        # so ``searchAttractionsViaConcierge`` is not flagged by ``searchAttractions``.
        pattern = re.escape(token) + r"(?![A-Za-z0-9_])"
        if re.search(pattern, cleaned):
            return True
    return False


def test_only_known_frontend_files_reference_legacy_search():
    """Walks ``frontend/`` and asserts only files in
    ``_KNOWN_LEGACY_SEARCH_CALLERS`` reference the legacy ``/search/*``
    routes or their typed wrappers.  Adding a new caller without updating
    this list fails the test and forces a v1B migration discussion."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    frontend_root = repo_root / "frontend"

    leaks: list[str] = []
    for path in frontend_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx", ".mjs"}:
            continue
        # node_modules and build artefacts are never source-of-truth.
        rel = path.relative_to(repo_root)
        rel_posix = pathlib.PurePosixPath(*rel.parts)
        if any(part in {"node_modules", ".next", "dist", "build"} for part in rel.parts):
            continue
        if rel_posix in _KNOWN_LEGACY_SEARCH_CALLERS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if _file_uses_legacy_search_token(text):
            leaks.append(str(rel_posix))

    assert not leaks, (
        "Unauthorized frontend caller of legacy /search/* mock-backed routes "
        "or their typed helpers (extend `_KNOWN_LEGACY_SEARCH_CALLERS` only "
        "alongside an explicit v1B migration entry):\n  - "
        + "\n  - ".join(sorted(leaks))
    )


def test_known_callers_actually_reference_legacy_tokens():
    """Drift guard in the other direction: every file in
    ``_KNOWN_LEGACY_SEARCH_CALLERS`` must really still contain a legacy
    token.  When v1B migrates a caller off the legacy surface, the entry
    must be removed from this list — not left behind."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    stale: list[str] = []
    for rel in _KNOWN_LEGACY_SEARCH_CALLERS:
        path = repo_root / pathlib.Path(*rel.parts)
        if not path.exists():
            stale.append(f"{rel} (file missing)")
            continue
        text = path.read_text(encoding="utf-8")
        if not _file_uses_legacy_search_token(text):
            stale.append(f"{rel} (file no longer references legacy /search/*)")
    assert not stale, (
        "Stale entries in `_KNOWN_LEGACY_SEARCH_CALLERS` — remove them when "
        "the caller has been migrated:\n  - " + "\n  - ".join(sorted(stale))
    )


# ---------------------------------------------------------------------------
# 5. AI Concierge canonical seam still present
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 5. Cache-side block — operator flag must fail closed even when the
#    research_cache already holds legacy mock-backed rows.
# ---------------------------------------------------------------------------


class _FakeSupabase:
    """Minimal Supabase client mock that returns a canned cache row.

    Mirrors the shape used by ``test_explore_snapshot.py`` so the
    cache-block tests exercise the real ``_get_cache`` / ``_set_cache``
    code paths without touching the network.
    """

    def __init__(self, cached_rows=None):
        self._cached_rows = cached_rows  # None → cache miss; list → cache hit
        self.upserts: list = []

    def table(self, _name):
        return self

    def select(self, *_):
        return self

    def eq(self, *_):
        return self

    def gt(self, *_):
        return self

    def order(self, *_):
        return self

    def limit(self, *_):
        return self

    def insert(self, *_):
        return self

    def upsert(self, payload, *args, **kwargs):
        self.upserts.append(payload)
        return self

    def execute(self):
        class _R:
            def __init__(self, data):
                self.data = data

        if self._cached_rows is None:
            return _R([])
        return _R([{"payload": {"results": self._cached_rows}, "expires_at": None}])


def _mock_hotel_cache_row(source: str = "mock") -> dict:
    return {
        "id": "hotel-cached-1",
        "name": "Cached Hotel",
        "location": "Paris",
        "booking_url": "https://example.com",
        "rating": 4.6,
        "stars": 4,
        "amenities": ["pool"],
        "check_in": "2026-06-01",
        "check_out": "2026-06-05",
        "nights": 4,
        "price": 800.0,
        "price_per_night": 200.0,
        "ai_score": 82.0,
        "source": source,
    }


def _mock_flight_cache_row(source: str = "mock") -> dict:
    return {
        "id": "flight-cached-1",
        "airline": "American Airlines",
        "flight_number": "AA42",
        "origin": "LAX",
        "destination": "JFK",
        "departure_time": "2026-06-01T10:00:00+00:00",
        "arrival_time": "2026-06-01T18:00:00+00:00",
        "duration_minutes": 480,
        "stops": 0,
        "cabin_class": "economy",
        "rating": 4.2,
        "price": 380.0,
        "points_estimate": 38000,
        "points_cost": 25000,
        "cpp": 1.52,
        "location": "LAX → JFK",
        "booking_url": "https://example.com",
        "source": source,
    }


def test_cached_legacy_mock_hotel_is_suppressed_when_flag_on(block_flag_on, caplog):
    caplog.set_level(logging.WARNING)
    db = _FakeSupabase(cached_rows=[_mock_hotel_cache_row("mock")])
    svc = search_service.SearchService(db)
    out = svc.search_hotels(
        HotelSearchRequest(
            location="Paris", check_in=date(2026, 6, 1), check_out=date(2026, 6, 5)
        )
    )
    assert out == [], (
        "Cached mock hotels must not leak under BLOCK_LEGACY_PRODUCT_MOCK"
    )
    assert any(
        "[legacy_product_mock.cache_blocked]" in rec.getMessage()
        and "namespace=hotels" in rec.getMessage()
        for rec in caplog.records
    )


def test_cached_legacy_mock_flight_is_suppressed_when_flag_on(block_flag_on, caplog):
    """Flights v1 wired ``SearchService.search_flights`` to the
    ``FlightProvider`` seam, which never consults ``research_cache``.  The
    legacy cache-block path therefore no longer fires for flights — we
    instead rely on the provider returning ``UNAVAILABLE`` (zero rows) by
    default.  Keep the empty-output assertion so cached mock rows still
    cannot leak under the operator flag."""
    caplog.set_level(logging.WARNING)
    db = _FakeSupabase(cached_rows=[_mock_flight_cache_row("mock")])
    svc = search_service.SearchService(db)
    out = svc.search_flights(
        FlightSearchRequest(origin="LAX", destination="JFK", departure_date=date(2026, 6, 1))
    )
    assert out == [], (
        "Cached mock flights must not leak under BLOCK_LEGACY_PRODUCT_MOCK"
    )


def test_cached_mock_hotel_is_filtered_by_contract_when_flag_off(block_flag_off, monkeypatch):
    """Hotels v1: ``SearchService.search_hotels`` no longer emits
    mock-attributed cache rows even when the operator flag is off.  The
    Hotels Product Contract v1 filter discards rows whose ``source`` is
    in ``DISALLOWED_SOURCES`` or whose booking URL uses a fabricated
    host, then falls back to the (default-Null) provider seam — which
    returns ``UNAVAILABLE`` and zero rows in the test env."""
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    from app.services.hotels_provider import reset_hotel_provider_cache
    reset_hotel_provider_cache()
    db = _FakeSupabase(cached_rows=[_mock_hotel_cache_row("mock")])
    svc = search_service.SearchService(db)
    out = svc.search_hotels(
        HotelSearchRequest(
            location="Paris", check_in=date(2026, 6, 1), check_out=date(2026, 6, 5)
        )
    )
    assert out == [], (
        "Mock-attributed cached hotels must be filtered by the Hotels "
        "Product Contract v1 even when the legacy block flag is off."
    )


def test_cached_canonical_hotel_is_not_suppressed_when_flag_on(block_flag_on):
    """Cached rows with a positive non-mock provider attribution
    (``source == "google_places"``) and a real Google Maps booking URL
    must be allowed through even under the operator flag — the block
    is a legacy-mock guard, not a kill switch on the entire cache."""
    canonical_row = _mock_hotel_cache_row("google_places")
    canonical_row["booking_url"] = (
        "https://www.google.com/maps/place/?q=place_id:ChIJpQ"
    )
    db = _FakeSupabase(cached_rows=[canonical_row])
    svc = search_service.SearchService(db)
    out = svc.search_hotels(
        HotelSearchRequest(
            location="Paris", check_in=date(2026, 6, 1), check_out=date(2026, 6, 5)
        )
    )
    assert len(out) == 1, (
        "Canonical-attributed cached rows must survive the legacy-mock block"
    )
    assert out[0].id == "hotel-cached-1"


def test_cached_ambiguous_source_hotels_fail_closed_when_flag_on(block_flag_on):
    """Cache rows that lack an unambiguous provider attribution fail
    closed under the operator flag — the v1A guard prefers an empty list
    over rendering potentially-fabricated product data."""
    ambiguous = _mock_hotel_cache_row("mock")
    ambiguous.pop("source", None)
    db = _FakeSupabase(cached_rows=[ambiguous])
    svc = search_service.SearchService(db)
    out = svc.search_hotels(
        HotelSearchRequest(
            location="Paris", check_in=date(2026, 6, 1), check_out=date(2026, 6, 5)
        )
    )
    assert out == [], (
        "Ambiguous cached rows on a legacy namespace must fail closed"
    )


def test_attractions_namespace_no_longer_in_legacy_guard():
    """v1D: the ``attractions`` cache namespace was removed from
    ``_LEGACY_MOCK_DEPENDENT_NAMESPACES`` because the mock-backed
    surface is gone.  The helper must not flag it under the operator
    block."""
    assert "attractions" not in search_service._LEGACY_MOCK_DEPENDENT_NAMESPACES
    assert search_service._suppress_legacy_mock_cache(
        "attractions",
        [{"source": "mock"}],
    ) is False


def test_search_restaurants_canonical_path_not_blocked_by_legacy_guard(block_flag_on):
    """``/search/restaurants`` is canonical (Google Places, fail-closed)
    and is **not** in ``_LEGACY_MOCK_DEPENDENT_NAMESPACES``.  Under the
    operator flag a cached restaurant row with a non-mock source must
    flow through unchanged.

    A cached row with ``source == "mock"`` is still discarded — but by
    the existing pre-PR guard inside ``search_restaurants``, not by the
    v1A legacy-namespace guard.  This test asserts the v1A guard does
    **not** itself block restaurants."""
    assert "restaurants" not in search_service._LEGACY_MOCK_DEPENDENT_NAMESPACES, (
        "/search/restaurants is canonical and must be excluded from the "
        "v1A legacy-namespace guard"
    )
    # Helper itself must return False for the restaurants namespace under
    # the flag, regardless of the cached row's source.
    assert search_service._suppress_legacy_mock_cache(
        "restaurants",
        [{"source": "mock"}],
    ) is False
    assert search_service._suppress_legacy_mock_cache(
        "restaurants",
        [{"source": "google_places"}],
    ) is False


def test_cache_write_is_skipped_when_block_flag_on(block_flag_on):
    """Tighten the fail-closed contract: when the operator flag is on we
    must not even write the empty mock result back to the cache,
    otherwise an ambiguous (zero-row, source=mock) entry could outlive
    the flag flip and confuse the next request.

    v1D: previously exercised via ``search_attractions`` which has been
    deleted; switched to ``search_hotels`` (same legacy-mock guard path).
    """
    db = _FakeSupabase(cached_rows=None)  # cache miss
    svc = search_service.SearchService(db)
    svc.search_hotels(
        HotelSearchRequest(
            location="Paris", check_in=date(2026, 6, 1), check_out=date(2026, 6, 5)
        )
    )
    assert db.upserts == [], (
        "Cache must not be written under BLOCK_LEGACY_PRODUCT_MOCK"
    )


def test_cache_write_skipped_when_provider_unavailable(block_flag_off, monkeypatch):
    """Hotels v1: ``SearchService.search_hotels`` no longer calls
    ``_mock_hotels`` and therefore never writes ``source="mock"`` rows
    back to ``research_cache``.  In the test env (no Google Places key)
    the provider returns ``UNAVAILABLE`` with zero rows, so no cache
    upsert is performed — fail-closed end-to-end."""
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    from app.services.hotels_provider import reset_hotel_provider_cache
    reset_hotel_provider_cache()
    db = _FakeSupabase(cached_rows=None)
    svc = search_service.SearchService(db)
    out = svc.search_hotels(
        HotelSearchRequest(
            location="Paris", check_in=date(2026, 6, 1), check_out=date(2026, 6, 5)
        )
    )
    assert out == []
    assert db.upserts == [], (
        "Provider-unavailable hotels must not write fabricated rows to cache"
    )


# ---------------------------------------------------------------------------
# 6. AI Concierge canonical seam still present
# ---------------------------------------------------------------------------


def test_ai_concierge_search_route_is_canonical_seam():
    """The canonical place-card endpoint remains available; v1A must not
    have accidentally removed or renamed it during the audit.

    We read the route file from disk because the conftest stubs FastAPI's
    runtime, leaving ``router.routes`` empty when imported under test.
    """
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    ai_routes_src = (repo_root / "backend" / "app" / "routes" / "ai.py").read_text(encoding="utf-8")
    assert '@router.post("/concierge/search"' in ai_routes_src, (
        "Canonical AI Concierge place-card endpoint must remain mounted at "
        "/ai/concierge/search."
    )
