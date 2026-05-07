#!/usr/bin/env python3
"""Advisory Claude Code hook reminders for AI Repo OS v2.

This script is intentionally non-blocking. It prints reminders only and exits 0.
No product runtime code, secrets, network calls, or CI behavior are involved.
"""

import json
import sys
from pathlib import Path


def _load_payload() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def _file_path(payload: dict) -> str:
    tool_input = payload.get("tool_input") or {}
    value = tool_input.get("file_path") or tool_input.get("path") or ""
    return str(value).replace("\\", "/")


def _post_tool_use(path: str) -> list[str]:
    reminders: list[str] = []
    if not path:
        return reminders

    if "backend/app/concierge/" in path and any(key in path for key in ["provider", "enrichment", "semantic_retrieval", "cache"]):
        reminders.append("AI OS advisory: concierge runtime/provider path changed. Run /latency-gate and prove total route impact, not only local timeout.")

    if any(key in path for key in ["evidence_dossier", "set_level_writer", "claim", "reason", "editorial_enrichment", "cross_source_enrichment"]):
        reminders.append("AI OS advisory: evidence/prose path changed. Run /claim-safety-gate and audit writer-visible facts and UI/internal leakage.")

    if any(key in path for key in ["frontend", "components", "app/"]) and any(key in path.lower() for key in ["concierge", "card", "ai"]):
        reminders.append("AI OS advisory: visible Concierge UI/client path changed. Run /contract-audit and verify no diagnostic/raw evidence leakage.")

    if any(key in path.lower() for key in ["supabase", "migration", "schema", "sql"]):
        reminders.append("AI OS advisory: persistence/schema path changed. Fill Supabase SQL/manual-action fields in PR summary.")

    if path.endswith(".env") or "/env" in path.lower() or "settings" in Path(path).name.lower():
        reminders.append("AI OS advisory: env/settings path changed. State env/redeploy/rollback impact in PR summary.")

    return reminders


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    payload = _load_payload()
    reminders: list[str] = []

    if event == "post-tool-use":
        reminders.extend(_post_tool_use(_file_path(payload)))
    elif event == "stop":
        reminders.append("AI OS advisory: before stopping on non-trivial work, run /pre-pr-self-audit and /pr-summary using the PR template.")

    for reminder in reminders:
        print(reminder, file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
