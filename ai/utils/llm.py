"""
LLM Client — thin async wrapper around the Anthropic API.

Provides a consistent interface for all AI interactions in the Travel Concierge App.
Centralizes error handling, JSON extraction, and model configuration so individual
agent modules can focus on their domain logic.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

import anthropic


DEFAULT_MODEL = os.getenv("AI_MODEL", "claude-sonnet-4-6")
DEFAULT_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "4096"))


class LLMClient:
    """Async wrapper around the Anthropic API for agent pipeline use."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = anthropic.AsyncAnthropic(api_key=key) if key else None
        self.model = model
        self.max_tokens = max_tokens

    async def ask(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.3,
    ) -> str:
        """Send a prompt and return the raw text response."""
        if self._client is None:
            return ""
        try:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                kwargs["system"] = system
            msg = await self._client.messages.create(**kwargs)
            return msg.content[0].text if msg.content else ""
        except Exception:
            return ""

    async def ask_json(
        self,
        prompt: str,
        system: Optional[str] = None,
    ) -> dict[str, Any]:
        """Send a prompt and attempt to parse the response as JSON.

        Falls back to an empty dict on parse failure or API error.
        """
        text = await self.ask(prompt, system=system)
        return self._extract_json(text)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        """Try multiple strategies to extract a JSON object from text.

        Strategy order:
        1. Direct JSON parse of stripped text
        2. Extract from markdown code fences (```json ... ```)
        3. Find first {...} block via regex
        """
        text = text.strip()

        # 1. Direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Code fence extraction
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 3. First {...} block
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        return {}


def clamp(value: Any, lo: float, hi: float) -> float:
    """Clamp a numeric value to [lo, hi]. Returns lo on conversion error."""
    try:
        return max(lo, min(float(value), hi))
    except (TypeError, ValueError):
        return lo
