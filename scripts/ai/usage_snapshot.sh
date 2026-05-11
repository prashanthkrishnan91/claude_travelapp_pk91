#!/usr/bin/env bash
# scripts/ai/usage_snapshot.sh
#
# Captures a lightweight AI usage snapshot for the current session/PR.
# - Tries `npx ccusage@latest --json` for session-level token/cost data.
# - Falls back gracefully if ccusage, npx, or jq are unavailable.
# - Writes raw snapshot to .ai/usage/ (gitignored — never committed).
# - Prints a compact usage note to paste into the PR body.
#
# Usage: bash scripts/ai/usage_snapshot.sh

SNAPSHOT_DIR="${CLAUDE_PROJECT_DIR:-.}/.ai/usage"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%s")
REPO=$(git remote get-url origin 2>/dev/null | sed 's|.*/||;s|\.git$||' || echo "unknown")
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
DIFF_STATS=$(git diff --stat HEAD 2>/dev/null | tail -1 || echo "unavailable")

mkdir -p "$SNAPSHOT_DIR" 2>/dev/null || true

# Attempt ccusage via npx
CCUSAGE_JSON=""
CCUSAGE_SOURCE="unavailable"

if command -v npx >/dev/null 2>&1; then
  CCUSAGE_JSON=$(npx ccusage@latest --json 2>/dev/null || true)
  if [ -n "$CCUSAGE_JSON" ]; then
    CCUSAGE_SOURCE="ccusage"
  fi
fi

# Build snapshot filename (safe chars only)
SAFE_TS=$(printf '%s' "$TIMESTAMP" | tr ':' '-')
SAFE_BRANCH=$(printf '%s' "$BRANCH" | tr '/' '-' | tr ' ' '_')
SNAPSHOT_FILE="$SNAPSHOT_DIR/${SAFE_TS}-${SAFE_BRANCH}.json"

# Write raw snapshot (best-effort; failures are non-fatal)
{
  printf '{\n'
  printf '  "timestamp": "%s",\n' "$TIMESTAMP"
  printf '  "repo": "%s",\n' "$REPO"
  printf '  "branch": "%s",\n' "$BRANCH"
  printf '  "diff_stats": "%s",\n' "$DIFF_STATS"
  printf '  "ccusage_source": "%s",\n' "$CCUSAGE_SOURCE"
  if [ -n "$CCUSAGE_JSON" ]; then
    printf '  "ccusage": %s\n' "$CCUSAGE_JSON"
  else
    printf '  "ccusage": null\n'
  fi
  printf '}\n'
} > "$SNAPSHOT_FILE" 2>/dev/null || true

# Print compact human-readable usage note
printf '\n=== AI Usage Note ===\n'
printf 'Timestamp:    %s\n' "$TIMESTAMP"
printf 'Repo:         %s\n' "$REPO"
printf 'Branch:       %s\n' "$BRANCH"
printf 'Diff stats:   %s\n' "$DIFF_STATS"
printf 'Usage source: %s\n' "$CCUSAGE_SOURCE"

if [ -n "$CCUSAGE_JSON" ] && command -v jq >/dev/null 2>&1; then
  printf 'Session usage (from ccusage):\n'
  printf '%s\n' "$CCUSAGE_JSON" | jq -r '
    if type == "array" then
      .[] | "  \(.date // "?")  in=\(.inputTokens // 0)  out=\(.outputTokens // 0)  cost=$\(.totalCost // "?")"
    elif type == "object" then
      "  in=\(.inputTokens // 0)  out=\(.outputTokens // 0)  cost=$\(.totalCost // "?")"
    else "  (unrecognized ccusage format — see raw snapshot)"
    end
  ' 2>/dev/null || printf '  (jq parse error — raw data in %s)\n' "$SNAPSHOT_FILE"
elif [ -n "$CCUSAGE_JSON" ]; then
  printf 'Usage data:   ccusage returned data (install jq for parsed view)\n'
else
  printf 'Usage data:   not available\n'
  printf '              Fallbacks:\n'
  printf '              1. npx ccusage@latest (install Node if needed)\n'
  printf '              2. Claude Code status line token count\n'
  printf '              3. Manual estimate from task scope\n'
fi

printf 'Snapshot:     %s\n' "$SNAPSHOT_FILE"
printf '=== End Usage Note ===\n\n'
printf 'Paste this line into the PR body (fill bracketed fields):\n'
printf '**Usage note:** Low/Medium/High; source: %s; main drivers: [fill]; justified: yes/partially/no; next efficiency improvement: [fill]\n\n' "$CCUSAGE_SOURCE"
