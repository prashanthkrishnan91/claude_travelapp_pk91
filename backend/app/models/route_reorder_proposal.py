"""Route reorder-proposal models — AI Route Planning v1 PR C.

Governed by ``docs/ai/AI_ROUTE_PLANNING_V1_ADR.md`` (Section 9, PR C).

This module defines the explicit-confirmation apply contract only. No
LLM/AI-generated proposal exists anywhere in this PR — the caller (today, a
manual/internal test fixture; in a later PR, a user-reviewed suggestion)
always supplies both ``current_order`` and ``proposed_order`` for one day,
and the server verifies them before writing anything.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

# Closed vocabulary — a consumer must not depend on an undocumented status.
# A write failure mid-apply never surfaces here: it is fail-closed via a
# raised HTTPException (with best-effort rollback), never a response status.
ReorderApplyStatus = Literal["disabled", "rejected", "applied"]


class RouteReorderApplyRequest(BaseModel):
    """Apply payload for one day's reorder proposal.

    ``current_order`` and ``proposed_order`` are both required so the server
    can verify the preview the user confirmed still matches the day's actual
    persisted order (stale-order detection) and that the proposed order is
    exactly the same item set, never an add/remove/duplicate/cross-day move.
    """

    current_order: List[str] = Field(default_factory=list)
    proposed_order: List[str] = Field(default_factory=list)


class RouteReorderApplyResponse(BaseModel):
    """Result of an apply attempt.

    ``status`` values: ``"disabled"`` | ``"rejected"`` | ``"applied"``.
    ``order`` reflects the day's order after the attempt: the item set is
    unwritten (fail-closed) unless ``status == "applied"``.
    """

    status: ReorderApplyStatus
    reason: str
    message: str
    day_id: str
    order: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
