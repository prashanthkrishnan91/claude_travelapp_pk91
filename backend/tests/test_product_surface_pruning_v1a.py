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
    AttractionSearchRequest,
    FlightSearchRequest,
    HotelSearchRequest,
    RestaurantSearchRequest,
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


def test_block_flag_blocks_mock_attractions(block_flag_on, caplog):
    caplog.set_level(logging.WARNING)
    out = search_service._mock_attractions(AttractionSearchRequest(location="Paris"))
    assert out == []
    assert any(
        "[legacy_product_mock.blocked]" in rec.getMessage()
        and "namespace=attractions" in rec.getMessage()
        for rec in caplog.records
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


def test_block_flag_blocks_mock_restaurants(block_flag_on, caplog):
    caplog.set_level(logging.WARNING)
    out = search_service._mock_restaurants(RestaurantSearchRequest(location="Paris"))
    assert out == []
    assert any(
        "[legacy_product_mock.blocked]" in rec.getMessage()
        and "namespace=restaurants" in rec.getMessage()
        for rec in caplog.records
    )


def test_unblocked_emit_emits_leak_telemetry(block_flag_off, caplog):
    """When the operator has not flipped the flag, mocks still emit results
    but the ``legacy_product_mock.emitted`` event must be logged so leakage
    rate is observable in production."""
    caplog.set_level(logging.WARNING)
    out = search_service._mock_attractions(AttractionSearchRequest(location="Paris"))
    assert len(out) > 0
    matching = [
        rec
        for rec in caplog.records
        if "[legacy_product_mock.emitted]" in rec.getMessage()
        and "namespace=attractions" in rec.getMessage()
    ]
    assert matching, "Unblocked mock emission must log a structured leak event"
    # Returned count is encoded in the log line so log scraping can chart
    # leakage rate over time.
    assert any(f"returned={len(out)}" in rec.getMessage() for rec in matching)


# ---------------------------------------------------------------------------
# 2. Legacy mock registry stays in sync with reality
# ---------------------------------------------------------------------------


def test_legacy_product_mock_registry_lists_all_four_helpers():
    names = sorted(fn.__name__ for fn in search_service.LEGACY_PRODUCT_MOCK_FUNCTIONS)
    assert names == sorted(
        ["_mock_flights", "_mock_hotels", "_mock_attractions", "_mock_restaurants"]
    )


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
    expected = {
        "/search/flights",
        "/search/round-trip-flights",
        "/search/hotels",
        "/search/attractions",
        "/search/clusters",
        "/search/best-area",
    }
    missing = expected - search_routes.LEGACY_PRODUCT_MOCK_DEPENDENT_ROUTES
    assert not missing, f"LEGACY_PRODUCT_MOCK_DEPENDENT_ROUTES is missing: {missing}"


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
    pathlib.PurePosixPath("frontend/src/lib/api.ts"),
    pathlib.PurePosixPath("frontend/src/components/trips/TripBuilder.tsx"),
    pathlib.PurePosixPath("frontend/src/components/trips/OptimizeTripModal.tsx"),
    # Test fixtures that exercise the legacy callers are explicitly allowed.
    pathlib.PurePosixPath("frontend/tests/explore-hydration.test.mjs"),
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
    after stripping benign Google Maps URL fragments."""
    cleaned = text
    for benign in _BENIGN_SEARCH_SUBSTRINGS:
        cleaned = cleaned.replace(benign, "")
    return any(token in cleaned for token in _LEGACY_SEARCH_TOKENS)


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
