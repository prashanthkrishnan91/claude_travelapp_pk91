#!/usr/bin/env python3
"""Lightweight structural certification checks for Travel AI Repo OS v4.1 workflow surface."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_ANCHOR_FILES = [
    ".github/pull_request_template.md",
    "docs/ai/AI_REPO_OPERATING_SYSTEM.md",
    ".claude/settings.json",
    "docs/ai/USAGE_LEDGER.md",
]

PR_TEMPLATE_ANCHORS = [
    "## Summary",
    "## Severity",
    "## Validation",
    "## AI usage note",
    "## Self-audit",
    "Usage ledger updated",
]

SELF_AUDIT_ANCHORS = [
    "Repository PR template used exactly: Yes/No",
    "Scope stayed workflow-only (no product code): Yes/No",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assert_file_exists(path: str) -> None:
    full_path = ROOT / path
    if not full_path.exists():
        raise AssertionError(f"Missing required anchor file: {path}")


def assert_anchors(text: str, anchors: list[str], label: str) -> None:
    missing = [anchor for anchor in anchors if anchor not in text]
    if missing:
        joined = ", ".join(missing)
        raise AssertionError(f"Missing {label} anchor(s): {joined}")


def check_settings_read_deny() -> None:
    settings_path = ROOT / ".claude/settings.json"
    data = json.loads(read_text(settings_path))

    permissions = data.get("permissions")
    if not isinstance(permissions, dict):
        return

    deny = permissions.get("deny")
    if not isinstance(deny, list):
        return

    required_entries = {"Read(./.env)", "Read(./.env.*)"}
    missing = sorted(entry for entry in required_entries if entry not in deny)
    if missing:
        raise AssertionError(f"Missing .env read-deny rule(s) in .claude/settings.json: {', '.join(missing)}")


def check_advisory_hook_safety_if_configured() -> None:
    settings_data = json.loads(read_text(ROOT / ".claude/settings.json"))
    hooks = settings_data.get("hooks")
    if not isinstance(hooks, dict):
        return

    stop_hooks = hooks.get("Stop")
    if not isinstance(stop_hooks, list):
        return

    for stop_hook in stop_hooks:
        if not isinstance(stop_hook, dict):
            continue
        hook_defs = stop_hook.get("hooks")
        if not isinstance(hook_defs, list):
            continue
        for hook_def in hook_defs:
            if not isinstance(hook_def, dict):
                continue
            command = str(hook_def.get("command", ""))
            if ".claude/hooks/ai_os_advisory.py" in command:
                hook_path = ROOT / ".claude/hooks/ai_os_advisory.py"
                if not hook_path.exists():
                    raise AssertionError("Advisory hook is configured but .claude/hooks/ai_os_advisory.py is missing")
                hook_text = read_text(hook_path)
                if "raise SystemExit(main())" not in hook_text:
                    raise AssertionError("Advisory hook safety check failed: expected clean SystemExit(main()) entrypoint")
                return


def check_usage_tracking_documents_ledger() -> None:
    tracking_path = ROOT / "docs/ai/AI_USAGE_TRACKING.md"
    if not tracking_path.exists():
        raise AssertionError("docs/ai/AI_USAGE_TRACKING.md is missing")
    text = read_text(tracking_path)
    if "USAGE_LEDGER.md" not in text:
        raise AssertionError("docs/ai/AI_USAGE_TRACKING.md does not document USAGE_LEDGER.md (two-layer model missing)")


def check_snapshot_script_references_ledger() -> None:
    script_path = ROOT / "scripts/ai/usage_snapshot.sh"
    if not script_path.exists():
        raise AssertionError("scripts/ai/usage_snapshot.sh is missing")
    text = read_text(script_path)
    if "--append-ledger" not in text:
        raise AssertionError("scripts/ai/usage_snapshot.sh does not reference --append-ledger (ledger append behavior missing)")


def check_gitignore_excludes_ai_usage() -> None:
    gitignore_path = ROOT / ".gitignore"
    if not gitignore_path.exists():
        raise AssertionError(".gitignore is missing")
    text = read_text(gitignore_path)
    if ".ai/usage" not in text:
        raise AssertionError(".gitignore does not exclude .ai/usage/ (raw snapshots must remain local)")


def main() -> int:
    for file_path in REQUIRED_ANCHOR_FILES:
        assert_file_exists(file_path)

    template_text = read_text(ROOT / ".github/pull_request_template.md")
    assert_anchors(template_text, PR_TEMPLATE_ANCHORS, "PR template")
    assert_anchors(template_text, SELF_AUDIT_ANCHORS, "self-audit")

    check_settings_read_deny()
    check_advisory_hook_safety_if_configured()
    check_usage_tracking_documents_ledger()
    check_snapshot_script_references_ledger()
    check_gitignore_excludes_ai_usage()

    print("✅ Travel workflow certification v4.1 checks passed (lightweight, structural, workflow-only).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
