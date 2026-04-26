"""Concierge request logging helpers with basic PII redaction."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Iterable
from uuid import UUID, uuid4

from app.concierge.contracts import ConciergeTypedResponse
from app.concierge.router import RouteDecision

logger = logging.getLogger(__name__)

INTENT_CLASSIFIER_VERSION = "router_v2.1"
PIPELINE_VERSION = "concierge_typed_v2"

_EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\d)")


def redact_prompt(prompt: str) -> str:
    """Mask obvious emails and phone numbers before persistence."""
    value = prompt or ""
    value = _EMAIL_RE.sub("[redacted_email]", value)
    value = _PHONE_RE.sub("[redacted_phone]", value)
    return value


def _as_sources(response: ConciergeTypedResponse) -> list[str]:
    if response.response_type == "place_recommendations":
        return list(response.sources or [])
    if response.response_type == "trip_advice":
        return [citation.url for citation in response.citations if citation.url]
    return []


def _token_counts(response: ConciergeTypedResponse) -> tuple[int | None, int | None, str | None]:
    metadata: Dict[str, Any] = getattr(response, "metadata", {}) or {}
    usage = metadata.get("llm_usage") if isinstance(metadata, dict) else {}
    if not isinstance(usage, dict):
        usage = {}
    return usage.get("tokens_in"), usage.get("tokens_out"), usage.get("model")


def persist_concierge_request_log(
    *,
    db: Any,
    user_id: UUID,
    prompt: str,
    decision: RouteDecision,
    response: ConciergeTypedResponse,
    latency_ms: int,
    request_id: UUID | None = None,
) -> UUID:
    """Persist concierge observability record to Supabase."""
    row_id = request_id or uuid4()
    tokens_in, tokens_out, model = _token_counts(response)
    row = {
        "request_id": str(row_id),
        "user_id": str(user_id),
        "prompt": redact_prompt(prompt),
        "response_type": response.response_type,
        "stage1_prior": decision.stage1_prior,
        "intent_confidence": decision.stage2_confidence,
        "intent_classifier_version": INTENT_CLASSIFIER_VERSION,
        "sources_used": _as_sources(response),
        "llm_model": model,
        "llm_tokens_in": tokens_in,
        "llm_tokens_out": tokens_out,
        "latency_ms": int(latency_ms),
        "pipeline_version": PIPELINE_VERSION,
    }

    try:
        db.table("concierge_request_log").insert(row).execute()
    except Exception:
        logger.exception("concierge.request_log.persist_failed request_id=%s", row_id)
    return row_id


def request_log_event(
    *,
    request_id: UUID,
    prompt: str,
    decision: RouteDecision,
    response: ConciergeTypedResponse,
    latency_ms: int,
    sources_used: Iterable[str],
    llm_tokens_in: int | None,
    llm_tokens_out: int | None,
) -> None:
    """Emit structured app logs for each concierge request."""
    logger.info(
        "concierge.request request_id=%s prompt=%r stage1_prior=%s intent_classifier_version=%s intent_confidence=%.4f response_type=%s latency_ms=%d sources_used=%s llm_tokens_in=%s llm_tokens_out=%s",
        request_id,
        redact_prompt(prompt),
        decision.stage1_prior,
        INTENT_CLASSIFIER_VERSION,
        decision.stage2_confidence,
        response.response_type,
        latency_ms,
        list(sources_used),
        llm_tokens_in,
        llm_tokens_out,
    )
