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
    "scripts/workflow/ai_pr_readiness_check.py",
    ".github/workflows/ai-pr-readiness.yml",
    "docs/ai/DANGEROUS_ACTION_GUARD.md",
    ".claude/hooks/dangerous_action_guard.sh",
]

PR_TEMPLATE_ANCHORS = [
    "## Summary",
    "## Severity",
    "## Validation",
    "## AI usage note",
    "## AI PR readiness",
    "## Self-audit",
    "Usage ledger row",
    "Waste classification",
]

SELF_AUDIT_ANCHORS = [
    "Repository PR template used exactly: Yes/No",
    "Scope stayed within requested files/behavior: Yes/No",
]

USAGE_LEDGER_ANCHORS = [
    "Date",
    "PR / Branch",
    "Level",
    "Chat",
    "Follow-ups",
    "Waste",
    "Lesson",
]

USAGE_LEDGER_HEADER = "| Date | PR / Branch | Level | Chat | Follow-ups | Waste | Lesson |"
USAGE_LEDGER_ARCHIVE_REF = "USAGE_LEDGER_ARCHIVE_2026H1.md"

SNAPSHOT_SCRIPT_ANCHORS = [
    "--append-ledger",
    "--prompt-id",
    "--phase",
    "--delta-from-baseline",
]

PROMPT_USAGE_FOOTER_ANCHORS = [
    "Usage ledger: If tooling exists",
    "Usage discipline: Keep discovery narrow",
]

CLAUDE_MD_READINESS_ANCHORS = [
    "ai_pr_readiness_check.py",
]

USAGE_TRACKING_ENFORCEMENT_ANCHORS = [
    "Ledger claim enforcement",
    "ai_pr_readiness_check.py",
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
        raise AssertionError("docs/ai/AI_USAGE_TRACKING.md does not document USAGE_LEDGER.md")
    assert_anchors(text, USAGE_TRACKING_ENFORCEMENT_ANCHORS, "AI_USAGE_TRACKING.md enforcement")


def check_snapshot_script_references_ledger() -> None:
    script_path = ROOT / "scripts/ai/usage_snapshot.sh"
    if not script_path.exists():
        raise AssertionError("scripts/ai/usage_snapshot.sh is missing")
    text = read_text(script_path)
    assert_anchors(text, SNAPSHOT_SCRIPT_ANCHORS, "usage_snapshot.sh")


def check_usage_ledger_columns() -> None:
    ledger_path = ROOT / "docs/ai/USAGE_LEDGER.md"
    if not ledger_path.exists():
        raise AssertionError("docs/ai/USAGE_LEDGER.md is missing")
    text = read_text(ledger_path)
    assert_anchors(text, USAGE_LEDGER_ANCHORS, "USAGE_LEDGER.md")

    if USAGE_LEDGER_HEADER not in text:
        raise AssertionError(
            f"docs/ai/USAGE_LEDGER.md missing exact seven-column header: {USAGE_LEDGER_HEADER}"
        )

    if USAGE_LEDGER_ARCHIVE_REF not in text:
        raise AssertionError(
            f"docs/ai/USAGE_LEDGER.md missing archive reference to {USAGE_LEDGER_ARCHIVE_REF}"
        )

    data_rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|") or "---" in s or s == USAGE_LEDGER_HEADER:
            continue
        cells = s.strip("|").split("|")
        if len(cells) < 2:
            continue
        data_rows.append((s, cells))

    if not data_rows:
        raise AssertionError("docs/ai/USAGE_LEDGER.md has no substantive data row")

    for row_text, cells in data_rows:
        if len(cells) != 7:
            raise AssertionError(
                f"docs/ai/USAGE_LEDGER.md data row does not have exactly seven columns "
                f"({len(cells)} found): {row_text}"
            )


def check_gitignore_excludes_ai_usage() -> None:
    gitignore_path = ROOT / ".gitignore"
    if not gitignore_path.exists():
        raise AssertionError(".gitignore is missing")
    text = read_text(gitignore_path)
    if ".ai/usage" not in text:
        raise AssertionError(".gitignore does not exclude .ai/usage/ (raw snapshots must remain local)")


def check_claude_md_references_readiness_checker() -> None:
    claude_path = ROOT / "CLAUDE.md"
    if not claude_path.exists():
        raise AssertionError("CLAUDE.md is missing")
    text = read_text(claude_path)
    assert_anchors(text, CLAUDE_MD_READINESS_ANCHORS, "CLAUDE.md readiness checker reference")


def check_prompt_standard_usage_footer() -> None:
    for path_str in ["docs/ai/PROMPT_ENGINEERING_STANDARD.md", "docs/ai/PROMPT_LIBRARY.md"]:
        path = ROOT / path_str
        if not path.exists():
            continue
        text = read_text(path)
        missing = [a for a in PROMPT_USAGE_FOOTER_ANCHORS if a not in text]
        if missing:
            raise AssertionError(
                f"{path_str} missing required usage footer anchor(s): {', '.join(missing)}"
            )


def check_readiness_hook_or_doc() -> None:
    hook = ROOT / ".claude/hooks/ai_pr_readiness_stop.sh"
    gate_doc = ROOT / "docs/ai/AI_PR_READINESS_GATE.md"
    if not hook.exists() and not gate_doc.exists():
        raise AssertionError(
            "Neither .claude/hooks/ai_pr_readiness_stop.sh nor docs/ai/AI_PR_READINESS_GATE.md found."
        )


OPEN_PR_SWEEP_SKILL_PATH = ".claude/skills/open-pr-sweep/SKILL.md"
OPEN_PR_SWEEP_COMMAND_PATH = ".claude/commands/open-pr-sweep.md"
OPEN_PR_SWEEP_REPO_SCOPE = "prashanthkrishnan91/claude_travelapp_pk91"
OPEN_PR_SWEEP_GUARD_ANCHORS = [
    "Immutable guard",
    "read-only and reporting-only",
]
OPEN_PR_SWEEP_PROHIBITED_ANCHORS = [
    "edit files or branches",
    "create commits or push",
    "patch CI failures",
    "comment on PRs or review threads",
    "approve or request changes",
    "add/remove labels or reviewers",
    "merge, close, or reopen PRs",
    "rerun, cancel, or dispatch workflows",
    "create another PR",
    "schedule or re-arm another watcher",
]
CLAUDE_MD_NO_HOURLY_POLLING_ANCHOR = "no hourly or per-PR polling chains"


def check_open_pr_sweep_contract() -> None:
    skill_path = ROOT / OPEN_PR_SWEEP_SKILL_PATH
    command_path = ROOT / OPEN_PR_SWEEP_COMMAND_PATH
    if not skill_path.exists():
        raise AssertionError(f"Missing required file: {OPEN_PR_SWEEP_SKILL_PATH}")
    if not command_path.exists():
        raise AssertionError(f"Missing required file: {OPEN_PR_SWEEP_COMMAND_PATH}")

    command_text = read_text(command_path)
    if OPEN_PR_SWEEP_SKILL_PATH not in command_text:
        raise AssertionError(
            f"{OPEN_PR_SWEEP_COMMAND_PATH} does not point to {OPEN_PR_SWEEP_SKILL_PATH}"
        )

    skill_text = read_text(skill_path)
    if OPEN_PR_SWEEP_REPO_SCOPE not in skill_text:
        raise AssertionError(
            f"{OPEN_PR_SWEEP_SKILL_PATH} missing exact Travel repository scope: {OPEN_PR_SWEEP_REPO_SCOPE}"
        )
    assert_anchors(skill_text, OPEN_PR_SWEEP_GUARD_ANCHORS, "open-pr-sweep read-only/reporting-only guard")
    assert_anchors(skill_text, OPEN_PR_SWEEP_PROHIBITED_ANCHORS, "open-pr-sweep prohibited mutation category")

    claude_md_text = read_text(ROOT / "CLAUDE.md")
    if CLAUDE_MD_NO_HOURLY_POLLING_ANCHOR not in claude_md_text:
        raise AssertionError(
            f"CLAUDE.md missing no-hourly-polling rule anchor: {CLAUDE_MD_NO_HOURLY_POLLING_ANCHOR}"
        )


def check_dangerous_action_guard() -> None:
    guard_doc = ROOT / "docs/ai/DANGEROUS_ACTION_GUARD.md"
    guard_hook = ROOT / ".claude/hooks/dangerous_action_guard.sh"
    if not guard_doc.exists():
        raise AssertionError("docs/ai/DANGEROUS_ACTION_GUARD.md missing")
    if not guard_hook.exists():
        raise AssertionError(".claude/hooks/dangerous_action_guard.sh missing")
    hook_text = read_text(guard_hook)
    if "DANGEROUS_ACTION_GUARD" not in hook_text:
        raise AssertionError("dangerous_action_guard.sh does not reference DANGEROUS_ACTION_GUARD env var")


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
    check_usage_ledger_columns()
    check_gitignore_excludes_ai_usage()
    check_claude_md_references_readiness_checker()
    check_prompt_standard_usage_footer()
    check_readiness_hook_or_doc()
    check_dangerous_action_guard()
    check_open_pr_sweep_contract()

    print("✅ Travel workflow certification v4.1 checks passed (lightweight, structural, workflow-only).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
