"""
Travel Concierge AI Layer

This package provides reusable AI infrastructure for the Travel Concierge App:

Subpackages:
    utils/       — LLM client, state objects, memory helper, task router, settings
    agents/      — Agent definitions (core + orchestration) as markdown specs
    skills/      — Skill definitions for SPARC methodology and stream-chain pipelines
    prompts/     — System prompts and domain-specific prompt variants
    hooks/       — Claude Flow hook command documentation and setup

Quick start:

    from ai.utils.config import get_ai_settings
    from ai.utils.llm import LLMClient
    from ai.utils.state import PipelineState, AgentResult

    settings = get_ai_settings()
    settings.validate()

    client = LLMClient(api_key=settings.anthropic_api_key, model=settings.model)
"""
