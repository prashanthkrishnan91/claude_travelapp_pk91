#!/usr/bin/env bash
# Dangerous Action Guard — opt-in advisory scaffold.
# Set DANGEROUS_ACTION_GUARD=1 to enable.
# This hook is advisory only: prints a warning to stderr and always exits 0.
# Never blocks builds, tests, or ordinary commands.
# See docs/ai/DANGEROUS_ACTION_GUARD.md for covered actions and rules.

[[ "${DANGEROUS_ACTION_GUARD:-0}" == "1" ]] || exit 0

TOOL_INPUT="${CLAUDE_TOOL_INPUT:-}"

DESTRUCTIVE_PATTERNS=(
    "rm -rf"
    "reset --hard"
    "push --force"
    "push -f "
    "branch -D"
    "checkout -- "
    "restore \\."
    "clean -f"
    "railway deploy"
    "vercel --prod"
    "supabase db push"
    "alembic upgrade"
    "flyway migrate"
)

for pattern in "${DESTRUCTIVE_PATTERNS[@]}"; do
    if echo "$TOOL_INPUT" | grep -qi "$pattern"; then
        echo "[DANGEROUS_ACTION_GUARD] Advisory: command matches '$pattern'." >&2
        echo "[DANGEROUS_ACTION_GUARD] Pause and confirm with the user before proceeding." >&2
        echo "[DANGEROUS_ACTION_GUARD] See docs/ai/DANGEROUS_ACTION_GUARD.md" >&2
        break
    fi
done

exit 0
