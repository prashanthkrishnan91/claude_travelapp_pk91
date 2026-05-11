#!/usr/bin/env bash
# scripts/ai/usage_snapshot.sh
#
# Manual command: capture a lightweight AI usage snapshot before opening a PR.
# Run: bash scripts/ai/usage_snapshot.sh
#
# What it does:
# - Calls `npx ccusage@latest session --json` for session token/cost data.
# - Falls back gracefully if ccusage, npx, jq, or python3 are unavailable.
# - Writes a safe JSON snapshot to .ai/usage/ (gitignored, never committed).
#   JSON is built via `jq -n --arg` (preferred) or python3 env-var pass (fallback).
#   If neither is available, snapshot writing is skipped; the usage note still prints.
# - Prints a compact usage note to paste into the PR body.
#
# This script is NOT run automatically. It is a manual step before opening a PR.
# Optional automatic execution at Claude Code session end requires:
#   AI_USAGE_SNAPSHOT_ON_STOP=1 (set in your shell/env, not committed)

SNAPSHOT_DIR="${CLAUDE_PROJECT_DIR:-.}/.ai/usage"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%s")
REPO=$(git remote get-url origin 2>/dev/null | sed 's|.*/||;s|\.git$||' || echo "unknown")
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
DIFF_STATS=$(git diff --stat HEAD 2>/dev/null | tail -1 || echo "unavailable")

mkdir -p "$SNAPSHOT_DIR" 2>/dev/null || true

# Attempt ccusage session report via npx
CCUSAGE_JSON=""
CCUSAGE_SOURCE="unavailable"

if command -v npx >/dev/null 2>&1; then
  CCUSAGE_JSON=$(npx ccusage@latest session --json 2>/dev/null || true)
  if [ -n "$CCUSAGE_JSON" ]; then
    CCUSAGE_SOURCE="ccusage"
  fi
fi

# Build snapshot filename (safe chars only)
SAFE_TS=$(printf '%s' "$TIMESTAMP" | tr ':' '-')
SAFE_BRANCH=$(printf '%s' "$BRANCH" | tr '/' '-' | tr ' ' '_')
SNAPSHOT_FILE="$SNAPSHOT_DIR/${SAFE_TS}-${SAFE_BRANCH}.json"

# Write snapshot safely: prefer jq (handles ccusage JSON), fallback python3 (metadata only),
# skip entirely if neither is available. Never interpolate raw strings into JSON manually.
SNAPSHOT_WRITTEN=false

if command -v jq >/dev/null 2>&1; then
  jq -n \
    --arg ts "$TIMESTAMP" \
    --arg repo "$REPO" \
    --arg branch "$BRANCH" \
    --arg diff_stats "$DIFF_STATS" \
    --arg ccusage_source "$CCUSAGE_SOURCE" \
    --argjson ccusage "${CCUSAGE_JSON:-null}" \
    '{timestamp:$ts,repo:$repo,branch:$branch,diff_stats:$diff_stats,ccusage_source:$ccusage_source,ccusage:$ccusage}' \
    > "$SNAPSHOT_FILE" 2>/dev/null && SNAPSHOT_WRITTEN=true
elif command -v python3 >/dev/null 2>&1; then
  # Pass values via env vars to avoid shell-interpolation injection in the Python string
  _TS="$TIMESTAMP" _REPO="$REPO" _BRANCH="$BRANCH" \
  _DIFF="$DIFF_STATS" _SRC="$CCUSAGE_SOURCE" \
  python3 -c "
import json, os
print(json.dumps({
    'timestamp': os.environ['_TS'],
    'repo': os.environ['_REPO'],
    'branch': os.environ['_BRANCH'],
    'diff_stats': os.environ['_DIFF'],
    'ccusage_source': os.environ['_SRC'],
    'ccusage': None,
}, indent=2))
" > "$SNAPSHOT_FILE" 2>/dev/null && SNAPSHOT_WRITTEN=true
fi
# If neither jq nor python3: snapshot skipped, usage note still prints below

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
  ' 2>/dev/null || printf '  (jq parse error — check %s)\n' "$SNAPSHOT_FILE"
elif [ -n "$CCUSAGE_JSON" ]; then
  printf 'Usage data:   ccusage returned data (install jq for parsed view)\n'
else
  printf 'Usage data:   not available\n'
  printf '              Fallbacks:\n'
  printf '              1. npx ccusage@latest session  (install Node if needed)\n'
  printf '              2. Claude Code status line token count\n'
  printf '              3. Manual estimate from task scope\n'
fi

if "$SNAPSHOT_WRITTEN"; then
  printf 'Snapshot:     %s\n' "$SNAPSHOT_FILE"
else
  printf 'Snapshot:     skipped (jq and python3 unavailable)\n'
fi
printf '=== End Usage Note ===\n\n'
printf 'Paste this line into the PR body (fill bracketed fields):\n'
printf '**Usage note:** Low/Medium/High; source: %s; main drivers: [fill]; justified: yes/partially/no; next efficiency improvement: [fill]\n\n' "$CCUSAGE_SOURCE"
