import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from uuid import uuid4

import pytest

_mod_path = Path(__file__).resolve().parents[1] / "app" / "core" / "cost_guardrails.py"
_spec = spec_from_file_location("cost_guardrails_module", _mod_path)
_mod = module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)

GuardrailRule = _mod.GuardrailRule
UserCostGuardrails = _mod.UserCostGuardrails


class LimitHit(Exception):
    def __init__(self, payload: dict):
        self.payload = payload


def _patch_raise(monkeypatch):
    def _raise(*, message: str, retry_after_seconds: int):
        raise LimitHit({"code": "rate_limited", "message": message, "retry_after_seconds": retry_after_seconds})

    monkeypatch.setattr(UserCostGuardrails, "_raise_429", staticmethod(_raise))


def test_user_under_limit(monkeypatch):
    _patch_raise(monkeypatch)
    g = UserCostGuardrails()
    rule = GuardrailRule(requests=3, window_seconds=60, dedupe_seconds=0)
    u = uuid4()
    g.enforce(endpoint_key="ai.concierge", user_id=u, rule=rule)
    g.enforce(endpoint_key="ai.concierge", user_id=u, rule=rule)


def test_same_user_rate_limited_after_threshold(monkeypatch):
    _patch_raise(monkeypatch)
    g = UserCostGuardrails()
    rule = GuardrailRule(requests=2, window_seconds=60, dedupe_seconds=0)
    u = uuid4()
    g.enforce(endpoint_key="ai.concierge", user_id=u, rule=rule)
    g.enforce(endpoint_key="ai.concierge", user_id=u, rule=rule)
    with pytest.raises(LimitHit) as exc:
        g.enforce(endpoint_key="ai.concierge", user_id=u, rule=rule)
    assert exc.value.payload["code"] == "rate_limited"
    assert "Too many" in exc.value.payload["message"]


def test_different_users_do_not_block_each_other(monkeypatch):
    _patch_raise(monkeypatch)
    g = UserCostGuardrails()
    rule = GuardrailRule(requests=1, window_seconds=60, dedupe_seconds=0)
    g.enforce(endpoint_key="search.hotels", user_id=uuid4(), rule=rule)
    g.enforce(endpoint_key="search.hotels", user_id=uuid4(), rule=rule)


def test_duplicate_request_triggers_cooldown_with_frontend_safe_shape(monkeypatch):
    _patch_raise(monkeypatch)
    g = UserCostGuardrails()
    rule = GuardrailRule(requests=10, window_seconds=60, dedupe_seconds=30)
    u = uuid4()
    payload = {"trip_id": "abc", "query": "rome food"}
    g.enforce(endpoint_key="ai.concierge_search", user_id=u, rule=rule, dedupe_payload=payload)
    with pytest.raises(LimitHit) as exc:
        g.enforce(endpoint_key="ai.concierge_search", user_id=u, rule=rule, dedupe_payload=payload)
    assert exc.value.payload["code"] == "rate_limited"
    assert "Duplicate request" in exc.value.payload["message"]
    assert isinstance(exc.value.payload["retry_after_seconds"], int)
