"""In-memory mock Supabase client.

Used when SUPABASE_URL / SUPABASE_ANON_KEY are not configured so that the
entire application can run in development or CI without a real Supabase
project.  Data is stored in module-level dicts keyed by table name and
reset every time the process restarts.
"""

from __future__ import annotations

import copy
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("travel_concierge.mock_db")

# Thread-safe in-process store --------------------------------------------------
_lock = threading.Lock()
_store: Dict[str, List[Dict[str, Any]]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _deep(obj: Any) -> Any:
    return copy.deepcopy(obj)


# ---------------------------------------------------------------------------
# Fluent query-builder that mimics the postgrest-py QueryRequestBuilder
# ---------------------------------------------------------------------------

class _Result:
    def __init__(self, data: List[Dict[str, Any]]) -> None:
        self.data = data


class _QueryBuilder:
    """Minimal fluent builder that mirrors the subset of postgrest API used by
    the app's services.  Only .select / .eq / .order / .limit / .or_ / .insert
    / .update / .delete / .upsert / .execute are implemented.
    """

    def __init__(self, table: str, method: str = "select") -> None:
        self._table = table
        self._method = method          # select | insert | update | delete | upsert
        self._filters: List[tuple] = []  # (field, value)
        self._or_filter: Optional[str] = None
        self._order: List[tuple] = []   # (field, desc)
        self._limit_val: Optional[int] = None
        self._payload: Optional[Any] = None
        self._on_conflict: Optional[str] = None

    # ---- Filter helpers -------------------------------------------------------

    def select(self, _cols: str = "*") -> "_QueryBuilder":
        return self

    def eq(self, field: str, value: Any) -> "_QueryBuilder":
        self._filters.append((field, value))
        return self

    def or_(self, condition: str) -> "_QueryBuilder":
        self._or_filter = condition
        return self

    def order(self, field: str, desc: bool = False) -> "_QueryBuilder":
        self._order.append((field, desc))
        return self

    def limit(self, n: int) -> "_QueryBuilder":
        self._limit_val = n
        return self

    def insert(self, data: Dict[str, Any]) -> "_QueryBuilder":
        self._method = "insert"
        self._payload = data
        return self

    def update(self, data: Dict[str, Any]) -> "_QueryBuilder":
        self._method = "update"
        self._payload = data
        return self

    def delete(self) -> "_QueryBuilder":
        self._method = "delete"
        return self

    def upsert(self, data: Dict[str, Any], on_conflict: str = "") -> "_QueryBuilder":
        self._method = "upsert"
        self._payload = data
        self._on_conflict = on_conflict
        return self

    # ---- Execution ------------------------------------------------------------

    def _match(self, row: Dict[str, Any]) -> bool:
        """Return True when all eq-filters match the row."""
        for field, value in self._filters:
            if str(row.get(field, "")) != str(value):
                return False
        return True

    def execute(self) -> _Result:
        with _lock:
            table = _store.setdefault(self._table, [])

            if self._method == "select":
                rows = [_deep(r) for r in table if self._match(r)]
                # or_ filter: skip for now (deals endpoint uses it but fallback to all)
                for field, is_desc in self._order:
                    rows.sort(key=lambda r: (r.get(field) or ""), reverse=is_desc)
                if self._limit_val is not None:
                    rows = rows[: self._limit_val]
                return _Result(rows)

            elif self._method == "insert":
                row = _deep(self._payload)
                if "id" not in row or not row["id"]:
                    row["id"] = str(uuid.uuid4())
                if "created_at" not in row:
                    row["created_at"] = _now()
                if "updated_at" not in row:
                    row["updated_at"] = _now()
                table.append(row)
                logger.debug("mock_db INSERT %s → %s", self._table, row["id"])
                return _Result([_deep(row)])

            elif self._method == "update":
                updated = []
                for row in table:
                    if self._match(row):
                        row.update(_deep(self._payload))
                        row["updated_at"] = _now()
                        updated.append(_deep(row))
                return _Result(updated)

            elif self._method == "upsert":
                row = _deep(self._payload)
                conflict_key = self._on_conflict
                if conflict_key and conflict_key in row:
                    # Find existing row by conflict key
                    conflict_val = row[conflict_key]
                    existing = next((r for r in table if r.get(conflict_key) == conflict_val), None)
                    if existing:
                        existing.update(row)
                        existing["updated_at"] = _now()
                        return _Result([_deep(existing)])
                # No conflict match → insert
                if "id" not in row or not row["id"]:
                    row["id"] = str(uuid.uuid4())
                if "created_at" not in row:
                    row["created_at"] = _now()
                row["updated_at"] = _now()
                table.append(row)
                return _Result([_deep(row)])

            elif self._method == "delete":
                before = len(table)
                table[:] = [r for r in table if not self._match(r)]
                logger.debug("mock_db DELETE %s — removed %d rows", self._table, before - len(table))
                return _Result([])

            return _Result([])


# ---------------------------------------------------------------------------
# Public mock client
# ---------------------------------------------------------------------------

class MockSupabaseClient:
    """Drop-in replacement for supabase.Client for dev/test environments."""

    def table(self, name: str) -> _QueryBuilder:
        return _QueryBuilder(name)


def get_mock_client() -> MockSupabaseClient:
    logger.warning(
        "Using in-memory MockSupabaseClient — data is NOT persisted. "
        "Set SUPABASE_URL and SUPABASE_ANON_KEY to use a real database."
    )
    return MockSupabaseClient()
