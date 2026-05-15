#!/usr/bin/env bash
# AI PR Readiness advisory hook — opt-in only.
# Enable: export AI_PR_READINESS_CHECK_ON_STOP=1 in your shell profile.
# This hook is intentionally fail-soft and non-blocking.
# It never auto-commits and never exposes .ai/usage files.
# To configure: add this path under hooks.Stop in .claude/settings.local.json

if [[ "${AI_PR_READINESS_CHECK_ON_STOP:-0}" != "1" ]]; then
  exit 0
fi

SCRIPT="scripts/workflow/ai_pr_readiness_check.py"
[[ ! -f "$SCRIPT" ]] && exit 0

echo "--- AI PR Readiness Gate (advisory, warn-only) ---"
python3 "$SCRIPT" --warn-only --base-ref "main" 2>/dev/null || true
echo "--- End AI PR Readiness Gate ---"

exit 0
