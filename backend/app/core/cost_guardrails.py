"""In-memory per-user guardrails for expensive provider-backed endpoints."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status


@dataclass(frozen=True)
class GuardrailRule:
    requests: int
    window_seconds: int
    dedupe_seconds: int


class UserCostGuardrails:
    """Simple process-local user rate limits + short duplicate request cooldowns."""

    def __init__(self) -> None:
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._last_fingerprint: dict[tuple[str, str], tuple[str, float]] = {}
        self._lock = threading.Lock()

    def enforce(
        self,
        *,
        endpoint_key: str,
        user_id: UUID,
        rule: GuardrailRule,
        dedupe_payload: dict[str, Any] | None = None,
    ) -> None:
        now = time.monotonic()
        user_key = str(user_id)
        bucket_key = (endpoint_key, user_key)

        fingerprint = self._fingerprint(dedupe_payload) if dedupe_payload else None

        with self._lock:
            if fingerprint and rule.dedupe_seconds > 0:
                prev = self._last_fingerprint.get(bucket_key)
                if prev:
                    prev_fp, prev_ts = prev
                    if prev_fp == fingerprint and (now - prev_ts) < rule.dedupe_seconds:
                        retry_after = max(1, int(rule.dedupe_seconds - (now - prev_ts)))
                        self._raise_429(
                            message="Duplicate request detected. Please wait before retrying the same search.",
                            retry_after_seconds=retry_after,
                        )
                self._last_fingerprint[bucket_key] = (fingerprint, now)

            history = self._events[bucket_key]
            floor = now - rule.window_seconds
            while history and history[0] <= floor:
                history.popleft()

            if len(history) >= rule.requests:
                retry_after = max(1, int(rule.window_seconds - (now - history[0])))
                self._raise_429(
                    message="Too many expensive requests in a short window. Please wait and try again.",
                    retry_after_seconds=retry_after,
                )

            history.append(now)

    @staticmethod
    def _fingerprint(payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _raise_429(*, message: str, retry_after_seconds: int) -> None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "rate_limited",
                "message": message,
                "retry_after_seconds": retry_after_seconds,
            },
        )


guardrails = UserCostGuardrails()
