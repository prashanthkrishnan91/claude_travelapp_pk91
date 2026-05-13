#!/usr/bin/env bash
# scripts/ai/usage_snapshot.sh
#
# Manual command: capture a lightweight AI usage snapshot before opening a PR.
# Run: bash scripts/ai/usage_snapshot.sh [OPTIONS]
#
# What it does:
# - Calls `npx ccusage@latest session --json` for session token/cost data.
# - Falls back gracefully if ccusage, npx, jq, or python3 are unavailable.
# - Writes a safe JSON snapshot to .ai/usage/ (gitignored, never committed).
#   JSON is built via `jq -n --arg` (preferred) or python3 env-var pass (fallback).
#   If neither is available, snapshot writing is skipped; the usage note still prints.
# - Prints a compact usage note to paste into the PR body.
# - Prints a sanitized Markdown ledger row for docs/ai/USAGE_LEDGER.md.
# - With --append-ledger, appends the ledger row to docs/ai/USAGE_LEDGER.md.
#
# CLI flags:
#   --pr <number-or-url>      PR number or URL (ledger row)
#   --session-url <url>       Claude session URL (ledger row)
#   --model <name>            Model name (e.g. claude-sonnet-4-6)
#   --chat-strategy <value>   same-chat | new-chat | unknown
#   --repo-area <text>        Repo area/stage (e.g. workflow/docs)
#   --main-drivers <text>     What consumed tokens
#   --follow-up-patches <n>   Number of follow-up patches required
#   --efficiency-lesson <t>   One-line efficiency lesson
#   --append-ledger           Append row to docs/ai/USAGE_LEDGER.md
#   --help                    Print this help
#
# This script is NOT run automatically. It is a manual step before opening a PR.
# Optional automatic execution at Claude Code session end requires:
#   AI_USAGE_SNAPSHOT_ON_STOP=1 (set in your shell/env, not committed)

# ── Defaults ──────────────────────────────────────────────────────────────────
OPT_PR="unknown"
OPT_SESSION_URL="unknown"
OPT_MODEL="unknown"
OPT_CHAT_STRATEGY="unknown"
OPT_REPO_AREA="unknown"
OPT_MAIN_DRIVERS="unknown"
OPT_FOLLOW_UP_PATCHES="0"
OPT_EFFICIENCY_LESSON="n/a"
OPT_APPEND_LEDGER=false

# ── Argument parsing ───────────────────────────────────────────────────────────
print_help() {
  printf 'Usage: bash scripts/ai/usage_snapshot.sh [OPTIONS]\n\n'
  printf 'Options:\n'
  printf '  --pr <number-or-url>      PR number or URL (ledger row)\n'
  printf '  --session-url <url>       Claude session URL (ledger row)\n'
  printf '  --model <name>            Model name (e.g. claude-sonnet-4-6)\n'
  printf '  --chat-strategy <value>   same-chat | new-chat | unknown\n'
  printf '  --repo-area <text>        Repo area/stage (e.g. workflow/docs)\n'
  printf '  --main-drivers <text>     What consumed tokens\n'
  printf '  --follow-up-patches <n>   Number of follow-up patches\n'
  printf '  --efficiency-lesson <t>   One-line efficiency lesson\n'
  printf '  --append-ledger           Append row to docs/ai/USAGE_LEDGER.md\n'
  printf '  --help                    Print this help\n'
  exit 0
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --pr)                 OPT_PR="${2:-unknown}"; shift 2 ;;
    --session-url)        OPT_SESSION_URL="${2:-unknown}"; shift 2 ;;
    --model)              OPT_MODEL="${2:-unknown}"; shift 2 ;;
    --chat-strategy)      OPT_CHAT_STRATEGY="${2:-unknown}"; shift 2 ;;
    --repo-area)          OPT_REPO_AREA="${2:-unknown}"; shift 2 ;;
    --main-drivers)       OPT_MAIN_DRIVERS="${2:-unknown}"; shift 2 ;;
    --follow-up-patches)  OPT_FOLLOW_UP_PATCHES="${2:-0}"; shift 2 ;;
    --efficiency-lesson)  OPT_EFFICIENCY_LESSON="${2:-n/a}"; shift 2 ;;
    --append-ledger)      OPT_APPEND_LEDGER=true; shift ;;
    --help|-h)            print_help ;;
    *) printf 'Unknown flag: %s\nRun with --help for usage.\n' "$1" >&2; exit 1 ;;
  esac
done

# ── Environment ────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SNAPSHOT_DIR="${CLAUDE_PROJECT_DIR:-.}/.ai/usage"
LEDGER_FILE="$REPO_ROOT/docs/ai/USAGE_LEDGER.md"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%s")
DATE_ONLY=$(date -u +"%Y-%m-%d" 2>/dev/null || echo "unknown")
REPO=$(git remote get-url origin 2>/dev/null | sed 's|.*/||;s|\.git$||' || echo "unknown")
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
DIFF_STATS=$(git diff --stat HEAD 2>/dev/null | tail -1 || echo "unavailable")

mkdir -p "$SNAPSHOT_DIR" 2>/dev/null || true

# ── Attempt ccusage ────────────────────────────────────────────────────────────
CCUSAGE_JSON=""
CCUSAGE_SOURCE="unavailable"

if command -v npx >/dev/null 2>&1; then
  CCUSAGE_JSON=$(npx ccusage@latest session --json 2>/dev/null || true)
  if [ -n "$CCUSAGE_JSON" ]; then
    CCUSAGE_SOURCE="ccusage"
  fi
fi

# ── Build snapshot filename ────────────────────────────────────────────────────
SAFE_TS=$(printf '%s' "$TIMESTAMP" | tr ':' '-')
SAFE_BRANCH=$(printf '%s' "$BRANCH" | tr '/' '-' | tr ' ' '_')
SNAPSHOT_FILE="$SNAPSHOT_DIR/${SAFE_TS}-${SAFE_BRANCH}.json"

# ── Write raw snapshot (gitignored, never committed) ───────────────────────────
# JSON is never built by raw string interpolation.
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
# If neither jq nor python3: snapshot skipped, usage note and ledger row still print

# ── Extract token fields (defensive; unavailable for missing fields) ────────────
INPUT_TOKENS="unavailable"
OUTPUT_TOKENS="unavailable"
CACHE_READ_TOKENS="unavailable"
CACHE_WRITE_TOKENS="unavailable"
TOTAL_TOKENS="unavailable"
ESTIMATED_COST="unavailable"

if [ -n "$CCUSAGE_JSON" ] && command -v jq >/dev/null 2>&1; then
  _jq_type=$(printf '%s\n' "$CCUSAGE_JSON" | jq -r 'type' 2>/dev/null || echo "unknown")
  if [ "$_jq_type" = "array" ]; then
    INPUT_TOKENS=$(printf '%s\n' "$CCUSAGE_JSON" | jq -r '[.[].inputTokens // 0] | add // "unavailable"' 2>/dev/null || echo "unavailable")
    OUTPUT_TOKENS=$(printf '%s\n' "$CCUSAGE_JSON" | jq -r '[.[].outputTokens // 0] | add // "unavailable"' 2>/dev/null || echo "unavailable")
    CACHE_READ_TOKENS=$(printf '%s\n' "$CCUSAGE_JSON" | jq -r '[.[].cacheReadTokens // 0] | add // "unavailable"' 2>/dev/null || echo "unavailable")
    CACHE_WRITE_TOKENS=$(printf '%s\n' "$CCUSAGE_JSON" | jq -r '[.[].cacheWriteTokens // 0] | add // "unavailable"' 2>/dev/null || echo "unavailable")
    TOTAL_TOKENS=$(printf '%s\n' "$CCUSAGE_JSON" | jq -r '[.[].totalTokens // 0] | add // "unavailable"' 2>/dev/null || echo "unavailable")
    ESTIMATED_COST=$(printf '%s\n' "$CCUSAGE_JSON" | jq -r '[.[].totalCost // 0] | add | if . then "$\(.* 100 | round / 100)" else "unavailable" end' 2>/dev/null || echo "unavailable")
  elif [ "$_jq_type" = "object" ]; then
    INPUT_TOKENS=$(printf '%s\n' "$CCUSAGE_JSON" | jq -r '.inputTokens // "unavailable"' 2>/dev/null || echo "unavailable")
    OUTPUT_TOKENS=$(printf '%s\n' "$CCUSAGE_JSON" | jq -r '.outputTokens // "unavailable"' 2>/dev/null || echo "unavailable")
    CACHE_READ_TOKENS=$(printf '%s\n' "$CCUSAGE_JSON" | jq -r '.cacheReadTokens // "unavailable"' 2>/dev/null || echo "unavailable")
    CACHE_WRITE_TOKENS=$(printf '%s\n' "$CCUSAGE_JSON" | jq -r '.cacheWriteTokens // "unavailable"' 2>/dev/null || echo "unavailable")
    TOTAL_TOKENS=$(printf '%s\n' "$CCUSAGE_JSON" | jq -r '.totalTokens // "unavailable"' 2>/dev/null || echo "unavailable")
    ESTIMATED_COST=$(printf '%s\n' "$CCUSAGE_JSON" | jq -r 'if .totalCost then "$\(.totalCost)" else "unavailable" end' 2>/dev/null || echo "unavailable")
  fi
fi

# ── Sanitized ledger row ───────────────────────────────────────────────────────
LEDGER_ROW="| $DATE_ONLY | $OPT_PR | $OPT_REPO_AREA | $OPT_SESSION_URL | $OPT_MODEL | $OPT_CHAT_STRATEGY | $CCUSAGE_SOURCE | $INPUT_TOKENS | $OUTPUT_TOKENS | $CACHE_READ_TOKENS | $CACHE_WRITE_TOKENS | $TOTAL_TOKENS | $ESTIMATED_COST | $OPT_MAIN_DRIVERS | $OPT_FOLLOW_UP_PATCHES | $OPT_EFFICIENCY_LESSON |"

# ── Print usage note ───────────────────────────────────────────────────────────
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

# ── Print sanitized ledger row ─────────────────────────────────────────────────
printf '=== Sanitized Ledger Row (for docs/ai/USAGE_LEDGER.md) ===\n'
printf '%s\n' "$LEDGER_ROW"
printf '=== End Ledger Row ===\n\n'

# ── Append ledger row if requested ────────────────────────────────────────────
if "$OPT_APPEND_LEDGER"; then
  if [ ! -f "$LEDGER_FILE" ]; then
    printf 'WARNING: %s not found — ledger row not appended.\n' "$LEDGER_FILE" >&2
    printf 'Paste the row above manually into docs/ai/USAGE_LEDGER.md.\n' >&2
  else
    printf '%s\n' "$LEDGER_ROW" >> "$LEDGER_FILE"
    printf 'Ledger row appended to %s\n' "$LEDGER_FILE"
  fi
fi
