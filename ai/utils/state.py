"""
Shared state objects for the multi-agent pipeline.

These dataclasses are intentionally domain-agnostic — extend them
with travel-specific fields as the pipeline develops.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AgentResult:
    """Output produced by a single agent node in the pipeline.

    Stores the raw output, a quality signal, and any structured
    data the agent extracted for downstream consumption.
    """

    agent_name: str
    task: str

    # Core outputs
    output: str = ""                          # Human-readable summary
    structured: dict[str, Any] = field(default_factory=dict)  # Parsed JSON payload
    success: bool = True
    error: Optional[str] = None

    # Quality signals
    confidence: float = 1.0                   # 0.0 .. 1.0
    tokens_used: int = 0
    latency_ms: float = 0.0


@dataclass
class PipelineState:
    """Graph-wide state passed between agent nodes in a pipeline run.

    Add domain-specific fields (e.g. itinerary, booking_details) as
    new agents are introduced.
    """

    run_id: str
    user_id: str
    task: str

    # Accumulated agent results keyed by agent name
    results: dict[str, AgentResult] = field(default_factory=dict)

    # Shared context blob — agents can read/write arbitrary data here
    context: dict[str, Any] = field(default_factory=dict)

    # Pipeline-level metadata
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    status: str = "running"     # running | completed | failed

    def add_result(self, result: AgentResult) -> None:
        """Accumulate an agent result and update pipeline metrics."""
        self.results[result.agent_name] = result
        self.total_tokens += result.tokens_used
        self.total_latency_ms += result.latency_ms
        if not result.success:
            self.status = "failed"

    @property
    def is_successful(self) -> bool:
        return self.status != "failed" and all(r.success for r in self.results.values())

    def to_summary(self) -> dict[str, Any]:
        """Return a concise summary suitable for API responses or memory storage."""
        return {
            "run_id": self.run_id,
            "task": self.task,
            "status": self.status,
            "agents_run": list(self.results.keys()),
            "total_tokens": self.total_tokens,
            "total_latency_ms": round(self.total_latency_ms, 1),
            "successful": self.is_successful,
        }
