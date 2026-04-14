"""
AI layer configuration for the Travel Concierge App.

All values are loaded from environment variables. Copy .env.example to .env
and populate before running locally.

Required environment variables:
    ANTHROPIC_API_KEY     — Anthropic API key for Claude

Optional environment variables:
    AI_MODEL              — Claude model ID (default: claude-sonnet-4-6)
    AI_MAX_TOKENS         — Max tokens per response (default: 4096)
    AI_TEMPERATURE        — Default sampling temperature (default: 0.3)
    AI_CONCURRENCY_LIMIT  — Max concurrent LLM calls (default: 6)
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional


class AISettings:
    """Immutable AI layer settings loaded from the environment."""

    def __init__(self) -> None:
        # --- LLM ---
        self.anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
        self.model: str = os.getenv("AI_MODEL", "claude-sonnet-4-6")
        self.max_tokens: int = int(os.getenv("AI_MAX_TOKENS", "4096"))
        self.temperature: float = float(os.getenv("AI_TEMPERATURE", "0.3"))
        self.concurrency_limit: int = int(os.getenv("AI_CONCURRENCY_LIMIT", "6"))

        # --- Memory / persistence ---
        self.memory_dir: str = os.getenv(
            "CLAUDE_FLOW_MEMORY_DIR",
            ".claude-flow/data",
        )

        # --- Debug ---
        self.debug: bool = os.getenv("AI_DEBUG", "false").lower() == "true"
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")

    def validate(self) -> None:
        """Raise ValueError if required settings are missing."""
        if not self.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file or environment."
            )


@lru_cache(maxsize=1)
def get_ai_settings() -> AISettings:
    """Return the cached AISettings singleton."""
    return AISettings()
