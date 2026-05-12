"""Pytest configuration — mock heavy dependencies so unit tests run without full stack."""

import os
import sys
import types
from unittest.mock import MagicMock

# Stub modules that require the full installed stack, before any app imports
for mod_name in ["fastapi", "supabase", "anthropic"]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# fastapi sub-attributes used in source files
import fastapi as _fa
_fa.HTTPException = type("HTTPException", (Exception,), {"__init__": lambda self, status_code=400, detail="": None})
_fa.status = MagicMock()
_fa.status.HTTP_404_NOT_FOUND = 404
_fa.status.HTTP_503_SERVICE_UNAVAILABLE = 503
_fa.status.HTTP_502_BAD_GATEWAY = 502

# app.core stubs — make app.core a proper package (with __path__) so submodule
# imports like app.core.cost_guardrails resolve from disk without error.
_core_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "core")
for mod_name in ["app.core", "app.core.config", "app.core.deps"]:
    if mod_name not in sys.modules:
        pkg = types.ModuleType(mod_name)
        sys.modules[mod_name] = pkg

_core_pkg = sys.modules["app.core"]
_core_pkg.__path__ = [_core_dir]
_core_pkg.__package__ = "app.core"
_core_pkg.__file__ = os.path.join(_core_dir, "__init__.py")

_settings_mock = MagicMock()
_settings_mock.anthropic_api_key = "test-key"
sys.modules["app.core.config"].get_settings = lambda: _settings_mock

# Stub app.services so importing app.services.concierge works directly
# but without triggering services/__init__.py (which imports fastapi-dependent services)
_backend_dir = os.path.dirname(os.path.dirname(__file__))  # backend/
_services_dir = os.path.join(_backend_dir, "app", "services")

_services_pkg = types.ModuleType("app.services")
_services_pkg.__path__ = [_services_dir]  # real path so submodule imports work
_services_pkg.__package__ = "app.services"
_services_pkg.__file__ = os.path.join(_services_dir, "__init__.py")
sys.modules["app.services"] = _services_pkg

# Stub app.models so submodule imports like app.models.search work without
# running app/models/__init__.py (which imports User → pydantic.EmailStr).
_models_dir = os.path.join(_backend_dir, "app", "models")
_models_pkg = types.ModuleType("app.models")
_models_pkg.__path__ = [_models_dir]
_models_pkg.__package__ = "app.models"
_models_pkg.__file__ = os.path.join(_models_dir, "__init__.py")
sys.modules["app.models"] = _models_pkg

# Stub app.contracts the same way so app.contracts.flight_offer imports directly.
_contracts_dir = os.path.join(_backend_dir, "app", "contracts")
_contracts_pkg = types.ModuleType("app.contracts")
_contracts_pkg.__path__ = [_contracts_dir]
_contracts_pkg.__package__ = "app.contracts"
_contracts_pkg.__file__ = os.path.join(_contracts_dir, "__init__.py")
sys.modules["app.contracts"] = _contracts_pkg
