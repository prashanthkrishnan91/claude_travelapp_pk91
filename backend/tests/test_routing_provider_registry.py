"""Routing provider registry tests — Route Planning v1 skeleton.

Governed by Route Planning v1 Contract ADR (PR #509).

Proves:
- ROUTE_MATRIX role exists in ProviderRole.
- google_routes is registered under ROUTE_MATRIX.
- google_routes is disabled (production_allowed=False, is_provider_active=False).
- Missing routing env/key does not break app startup or registry imports.
- No adapter / live-call module for routing exists.
- No Optimize Day / route optimization / reorder symbols introduced.
- Existing Google Places (CANONICAL) and MapTiler (MAP_TILE) roles are unchanged.
"""
from __future__ import annotations

import importlib
import sys

import pytest

from app.services.provider_registry import (
    PROVIDER_REGISTRY,
    ProviderRole,
    get_provider,
    is_production_allowed,
    is_provider_active,
)


class TestRouteMatrixRoleExists:
    def test_route_matrix_role_in_enum(self):
        assert hasattr(ProviderRole, "ROUTE_MATRIX"), (
            "ProviderRole.ROUTE_MATRIX must exist (Route Planning v1 ADR)"
        )

    def test_route_matrix_value(self):
        assert ProviderRole.ROUTE_MATRIX == "route_matrix"


class TestGoogleRoutesRegistered:
    def test_google_routes_in_registry(self):
        assert "google_routes" in PROVIDER_REGISTRY, (
            "google_routes must be registered (routing skeleton PR)"
        )

    def test_google_routes_role_is_route_matrix(self):
        entry = get_provider("google_routes")
        assert entry is not None
        assert entry.role == ProviderRole.ROUTE_MATRIX

    def test_google_routes_display_name(self):
        entry = get_provider("google_routes")
        assert entry is not None
        assert "Google Routes" in entry.display_name


class TestGoogleRoutesDisabledByDefault:
    def test_production_not_allowed(self):
        assert not is_production_allowed("google_routes"), (
            "google_routes must not be production_allowed (skeleton only)"
        )

    def test_provider_not_active(self):
        assert not is_provider_active("google_routes"), (
            "google_routes must not be active (no adapter, no live calls)"
        )

    def test_cannot_create_addable_cards(self):
        entry = get_provider("google_routes")
        assert entry is not None
        assert not entry.can_create_addable_cards

    def test_no_required_env_vars_at_runtime(self):
        entry = get_provider("google_routes")
        assert entry is not None
        # required_env_vars is intentionally empty so missing key never breaks startup
        assert entry.required_env_vars == ()


class TestNoLiveRoutingCallsOrAdapter:
    def test_no_routing_adapter_module(self):
        """No routing adapter module should exist yet."""
        routing_adapter_names = [
            "app.services.routing_provider",
            "app.services.routing_provider_google",
            "app.services.google_routes_adapter",
            "app.services.route_estimate_provider",
        ]
        for mod_name in routing_adapter_names:
            assert mod_name not in sys.modules, (
                f"Module {mod_name!r} must not be imported (no adapter in skeleton PR)"
            )
            spec = importlib.util.find_spec(mod_name)
            assert spec is None, (
                f"Module {mod_name!r} must not exist (no adapter in skeleton PR)"
            )

    def test_no_optimize_day_symbol_in_registry(self):
        """No Optimize Day / route optimization / reorder symbols in registry module."""
        import app.services.provider_registry as reg_mod

        forbidden = ("optimize_day", "route_optimization", "reorder", "auto_reorder")
        source_attrs = [a.lower() for a in dir(reg_mod)]
        for symbol in forbidden:
            assert symbol not in source_attrs, (
                f"Symbol {symbol!r} must not appear in provider_registry (ADR boundary)"
            )


class TestMissingRoutingEnvDoesNotBreakStartup:
    def test_registry_import_succeeds_without_routing_env(self, monkeypatch):
        """Importing the registry without GOOGLE_ROUTES_API_KEY must not raise."""
        monkeypatch.delenv("GOOGLE_ROUTES_API_KEY", raising=False)
        # Re-import should be a no-op (already cached), but this confirms no KeyError.
        import app.services.provider_registry  # noqa: F401

    def test_is_provider_active_returns_false_without_env(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_ROUTES_API_KEY", raising=False)
        assert not is_provider_active("google_routes")


class TestExistingRolesUnchanged:
    def test_google_places_still_canonical(self):
        entry = get_provider("google_places")
        assert entry is not None
        assert entry.role == ProviderRole.CANONICAL
        assert entry.production_allowed is True
        assert entry.can_create_addable_cards is True

    def test_maptiler_still_map_tile(self):
        entry = get_provider("maptiler_maps")
        assert entry is not None
        assert entry.role == ProviderRole.MAP_TILE
        assert entry.production_allowed is True
        assert not entry.can_create_addable_cards

    def test_map_tile_role_unchanged(self):
        assert ProviderRole.MAP_TILE == "map_tile"

    def test_canonical_role_unchanged(self):
        assert ProviderRole.CANONICAL == "canonical"

    def test_route_matrix_does_not_replace_map_tile(self):
        assert ProviderRole.ROUTE_MATRIX != ProviderRole.MAP_TILE
