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


# ── Generate (AI Route Planning v1 — proposal generation) ──────────────────
#
# Governed by docs/ai/AI_ROUTE_PLANNING_V1_ADR.md. Read-only: generation never
# writes. The caller supplies the day's actual current order (as it knows it)
# so the server can detect a stale/mismatched request before doing any
# route-data or LLM work. A successful proposal is shaped to be handed
# straight to ``RouteReorderApplyRequest`` (current_order/proposed_order) —
# the same apply contract from PR C, unchanged.

ReorderProposalGenerateStatus = Literal["disabled", "unavailable", "success"]


class RouteReorderProposalGenerateRequest(BaseModel):
    """The caller's known current order for this day, used for staleness
    detection before any route-data or LLM work happens."""

    current_order: List[str] = Field(default_factory=list)


class RouteReorderProposalGenerateResponse(BaseModel):
    """Result of an AI route-reorder proposal generation attempt.

    ``status`` values:
    - ``"disabled"``: feature flag off.
    - ``"unavailable"``: no proposal could be honestly generated (too few
      routeable stops, stale current_order, route data unavailable, LLM
      unavailable, or a generated proposal failed validation). ``reason``
      carries the machine-readable cause; ``proposed_order`` is empty.
    - ``"success"``: ``proposed_order`` contains exactly the same item IDs as
      ``current_order`` (the full day, in position order), reordered only
      among the eligible activity/meal stops the model reasoned about.

    Never fabricates a travel time, distance, or location that wasn't
    already available from the app's existing route/coordinate data.
    """

    status: ReorderProposalGenerateStatus
    reason: str
    message: str
    day_id: str
    current_order: List[str] = Field(default_factory=list)
    proposed_order: List[str] = Field(default_factory=list)
    rationale: str = ""
    move_reasons: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
