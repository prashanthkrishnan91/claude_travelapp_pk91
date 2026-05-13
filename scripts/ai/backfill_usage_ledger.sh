#!/usr/bin/env bash
# scripts/ai/backfill_usage_ledger.sh
#
# Backfill sanitized ledger rows from local ccusage session data.
# PR mapping is marked unknown when it cannot be proven — never guess.
#
# Usage:
#   bash scripts/ai/backfill_usage_ledger.sh [OPTIONS]
#
# Options:
#   --since YYYY-MM-DD   Include sessions on or after this date
#   --until YYYY-MM-DD   Include sessions on or before this date
#   --append-ledger      Append printed rows to docs/ai/USAGE_LEDGER.md
#   --help               Print this help
#
# Never commits raw JSON. Never guesses PR numbers.
# Review printed rows and fill in PR/model/repo-area before committing.

OPT_SINCE=""
OPT_UNTIL=""
OPT_APPEND_LEDGER=false

print_help() {
  printf 'Usage: bash scripts/ai/backfill_usage_ledger.sh [OPTIONS]\n\n'
  printf 'Options:\n'
  printf '  --since YYYY-MM-DD   Include sessions on or after this date\n'
  printf '  --until YYYY-MM-DD   Include sessions on or before this date\n'
  printf '  --append-ledger      Append rows to docs/ai/USAGE_LEDGER.md\n'
  printf '  --help               Print this help\n'
  exit 0
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --since)         OPT_SINCE="${2:-}"; shift 2 ;;
    --until)         OPT_UNTIL="${2:-}"; shift 2 ;;
    --append-ledger) OPT_APPEND_LEDGER=true; shift ;;
    --help|-h)       print_help ;;
    *) printf 'Unknown flag: %s\nRun with --help for usage.\n' "$1" >&2; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LEDGER_FILE="$REPO_ROOT/docs/ai/USAGE_LEDGER.md"

if ! command -v npx >/dev/null 2>&1; then
  printf 'npx not found — ccusage unavailable. Cannot backfill.\n' >&2
  exit 1
fi

CCUSAGE_JSON=$(npx ccusage@latest session --json 2>/dev/null || true)
if [ -z "$CCUSAGE_JSON" ]; then
  printf 'ccusage returned no data. Nothing to backfill.\n' >&2
  exit 0
fi

if ! command -v jq >/dev/null 2>&1; then
  printf 'jq not found — cannot parse ccusage output. Install jq to backfill.\n' >&2
  exit 1
fi

# Normalize to array
_type=$(printf '%s\n' "$CCUSAGE_JSON" | jq -r 'type' 2>/dev/null || echo "unknown")
if [ "$_type" = "object" ]; then
  CCUSAGE_JSON=$(printf '%s\n' "$CCUSAGE_JSON" | jq -c '[.]')
elif [ "$_type" != "array" ]; then
  printf 'Unrecognized ccusage output format. Cannot backfill.\n' >&2
  exit 1
fi

printf '\n=== Backfill Candidate Ledger Rows ===\n'
printf '# PR mapping is unknown — do not guess. Review and correct before committing.\n\n'

ROWS=$(printf '%s\n' "$CCUSAGE_JSON" | jq -r \
  --arg since "$OPT_SINCE" \
  --arg until "$OPT_UNTIL" \
  '.[] |
  select(
    (if $since != "" then (.date // "") >= $since else true end) and
    (if $until != "" then (.date // "") <= $until else true end)
  ) |
  "| \(.date // "unknown") | unknown | unknown | unknown | unknown | unknown | ccusage | \(.inputTokens // "unavailable") | \(.outputTokens // "unavailable") | \(.cacheReadTokens // "unavailable") | \(.cacheWriteTokens // "unavailable") | \(.totalTokens // "unavailable") | \(if .totalCost != null then "$\(.totalCost)" else "unavailable" end) | unknown | 0 | review-and-fill |"
  ' 2>/dev/null || true)

if [ -z "$ROWS" ]; then
  printf 'No sessions found in the specified date range.\n'
else
  printf '%s\n' "$ROWS"
fi

printf '\n=== End Backfill Rows ===\n'

if "$OPT_APPEND_LEDGER"; then
  if [ -z "$ROWS" ]; then
    printf 'No rows to append.\n'
  elif [ ! -f "$LEDGER_FILE" ]; then
    printf 'WARNING: %s not found — cannot append.\n' "$LEDGER_FILE" >&2
  else
    printf '%s\n' "$ROWS" >> "$LEDGER_FILE"
    printf 'Rows appended to %s\n' "$LEDGER_FILE"
    printf 'Review and correct PR/model/repo-area/efficiency-lesson before committing.\n'
  fi
fi
