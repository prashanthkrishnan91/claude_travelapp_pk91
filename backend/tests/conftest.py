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

# app.core stubs
for mod_name in ["app.core", "app.core.config", "app.core.deps"]:
    if mod_name not in sys.modules:
        pkg = types.ModuleType(mod_name)
        sys.modules[mod_name] = pkg

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
