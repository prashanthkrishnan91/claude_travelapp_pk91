"""
Travel Concierge AI Layer

Reusable AI infrastructure for the Travel Concierge App:

Subpackages:
    utils/       — LLM client, state objects, settings

Quick start:

    from ai.utils.config import get_ai_settings
    from ai.utils.llm import LLMClient
    from ai.utils.state import PipelineState, AgentResult

    settings = get_ai_settings()
    settings.validate()

    client = LLMClient(api_key=settings.anthropic_api_key, model=settings.model)
"""
