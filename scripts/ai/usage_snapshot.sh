#!/usr/bin/env bash
# scripts/ai/usage_snapshot.sh
#
# Manual command: capture AI usage snapshots before/after a prompt for PR/delta auditing.
# Run: bash scripts/ai/usage_snapshot.sh [OPTIONS]
#
# Per-prompt delta workflow:
#   # 1. Before Claude work — save baseline:
#   bash scripts/ai/usage_snapshot.sh --save-baseline before-pr-123
#
#   # 2. After Claude work — capture delta and append ledger row:
#   bash scripts/ai/usage_snapshot.sh --pr 123 --prompt-id initial --phase initial \
#     --delta-from-baseline .ai/usage/baseline-before-pr-123.json \
#     --repo-area workflow/docs --model claude-sonnet-4-6 \
#     --main-drivers "anchor reads, file writes" --append-ledger
#
#   # 3. Follow-up patch delta linked to original PR:
#   bash scripts/ai/usage_snapshot.sh --pr 124 --prompt-id patch-1 --phase follow-up \
#     --linked-pr 123 --delta-from-baseline .ai/usage/baseline-before-patch1.json \
#     --waste-classification preventable-follow-up --append-ledger
#
# What it does:
# - Calls `npx ccusage@latest session --json` for session token/cost data.
# - Handles ccusage shapes: {sessions/totals}, {data/summary}, single object, bare array.
# - Falls back gracefully if ccusage, npx, jq, or python3 are unavailable.
# - Writes a raw JSON snapshot to .ai/usage/ (gitignored, never committed).
# - Saves numeric totals to .ai/usage/baseline-<name>.json when --save-baseline is used.
# - Computes per-prompt token delta when --delta-from-baseline is provided.
# - Prints a compact usage note for the PR body.
# - Prints a sanitized 26-column Markdown ledger row for docs/ai/USAGE_LEDGER.md.
# - With --append-ledger, appends the ledger row to docs/ai/USAGE_LEDGER.md.
#
# CLI flags:
#   --pr <number-or-url>             PR number or URL
#   --session-url <url>              Claude session URL
#   --model <name>                   Model name (e.g. claude-sonnet-4-6)
#   --chat-strategy <value>          same-chat | new-chat | unknown
#   --repo-area <text>               Repo area/stage (e.g. workflow/docs)
#   --prompt-id <text>               Prompt/patch ID (e.g. initial, patch-1, patch-2)
#   --phase <value>                  initial | follow-up | audit | merge-gate | backfill | unknown
#   --linked-pr <number-or-url>      Original PR this follow-up belongs to
#   --main-drivers <text>            What consumed tokens
#   --follow-up-patches <n>          Number of follow-up patches required
#   --waste-classification <value>   none | preventable-follow-up | necessary-follow-up | exploration | unknown
#   --efficiency-lesson <text>       One-line efficiency lesson
#   --save-baseline <name>           Save current totals to .ai/usage/baseline-<name>.json
#   --delta-from-baseline <path>     Compute per-prompt delta from this baseline file
#   --append-ledger                  Append sanitized row to docs/ai/USAGE_LEDGER.md
#   --help                           Print this help
#
# This script is NOT run automatically. It is a manual step before opening a PR.
# Optional automatic execution at Claude Code session end requires:
#   AI_USAGE_SNAPSHOT_ON_STOP=1 (set in your shell/env, not committed)

# ── Defaults ────────────────────────────────────────────────────────────────
OPT_PR="unknown"
OPT_SESSION_URL="unknown"
OPT_MODEL="unknown"
OPT_CHAT_STRATEGY="unknown"
OPT_REPO_AREA="unknown"
OPT_PROMPT_ID="unknown"
OPT_PHASE="unknown"
OPT_LINKED_PR="n/a"
OPT_MAIN_DRIVERS="unknown"
OPT_FOLLOW_UP_PATCHES="0"
OPT_WASTE_CLASSIFICATION="unknown"
OPT_EFFICIENCY_LESSON="n/a"
OPT_SAVE_BASELINE=""
OPT_DELTA_FROM_BASELINE=""
OPT_APPEND_LEDGER=false

# ── Argument parsing ───────────────────────────────────────────────────────────
print_help() {
  printf 'Usage: bash scripts/ai/usage_snapshot.sh [OPTIONS]\n\n'
  printf 'Per-prompt delta workflow:\n'
  printf '  1. Before work: --save-baseline before-pr-N\n'
  printf '  2. After work:  --pr N --prompt-id initial --phase initial \\\n'
  printf '                  --delta-from-baseline .ai/usage/baseline-before-pr-N.json \\\n'
  printf '                  --append-ledger\n\n'
  printf 'Options:\n'
  printf '  --pr <number-or-url>             PR number or URL\n'
  printf '  --session-url <url>              Claude session URL\n'
  printf '  --model <name>                   Model (e.g. claude-sonnet-4-6)\n'
  printf '  --chat-strategy <value>          same-chat | new-chat | unknown\n'
  printf '  --repo-area <text>               Repo area/stage\n'
  printf '  --prompt-id <text>               Prompt/patch ID (e.g. initial, patch-1)\n'
  printf '  --phase <value>                  initial | follow-up | audit | merge-gate | backfill | unknown\n'
  printf '  --linked-pr <number-or-url>      Original PR this follow-up belongs to\n'
  printf '  --main-drivers <text>            What consumed tokens\n'
  printf '  --follow-up-patches <n>          Number of follow-up patches\n'
  printf '  --waste-classification <value>   none | preventable-follow-up | necessary-follow-up | exploration | unknown\n'
  printf '  --efficiency-lesson <text>       One-line efficiency lesson\n'
  printf '  --save-baseline <name>           Save totals to .ai/usage/baseline-<name>.json\n'
  printf '  --delta-from-baseline <path>     Compute delta from this baseline file\n'
  printf '  --append-ledger                  Append row to docs/ai/USAGE_LEDGER.md\n'
  printf '  --help                           Print this help\n'
  exit 0
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --pr)                    OPT_PR="${2:-unknown}"; shift 2 ;;
    --session-url)           OPT_SESSION_URL="${2:-unknown}"; shift 2 ;;
    --model)                 OPT_MODEL="${2:-unknown}"; shift 2 ;;
    --chat-strategy)         OPT_CHAT_STRATEGY="${2:-unknown}"; shift 2 ;;
    --repo-area)             OPT_REPO_AREA="${2:-unknown}"; shift 2 ;;
    --prompt-id)             OPT_PROMPT_ID="${2:-unknown}"; shift 2 ;;
    --phase)                 OPT_PHASE="${2:-unknown}"; shift 2 ;;
    --linked-pr)             OPT_LINKED_PR="${2:-n/a}"; shift 2 ;;
    --main-drivers)          OPT_MAIN_DRIVERS="${2:-unknown}"; shift 2 ;;
    --follow-up-patches)     OPT_FOLLOW_UP_PATCHES="${2:-0}"; shift 2 ;;
    --waste-classification)  OPT_WASTE_CLASSIFICATION="${2:-unknown}"; shift 2 ;;
    --efficiency-lesson)     OPT_EFFICIENCY_LESSON="${2:-n/a}"; shift 2 ;;
    --save-baseline)         OPT_SAVE_BASELINE="${2:-}"; shift 2 ;;
    --delta-from-baseline)   OPT_DELTA_FROM_BASELINE="${2:-}"; shift 2 ;;
    --append-ledger)         OPT_APPEND_LEDGER=true; shift ;;
    --help|-h)               print_help ;;
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
SAFE_TS=$(printf '%s' "$TIMESTAMP" | tr ':' '-')
SAFE_BRANCH=$(printf '%s' "$BRANCH" | tr '/' '-' | tr ' ' '_')
SNAPSHOT_FILE="$SNAPSHOT_DIR/${SAFE_TS}-${SAFE_BRANCH}.json"

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

# ── Normalize ccusage JSON (defensive; handles all known shapes) ──────────────
# Shapes handled: {sessions:[...],totals:{...}}, {data:[...],summary:{...}},
#                 single session object, bare array of sessions.
# Produces a flat object with numeric fields (0 for missing). Returns "null" on failure.
_CCUSAGE_NORMALIZED="null"
if [ -n "$CCUSAGE_JSON" ] && command -v jq >/dev/null 2>&1; then
  _CCUSAGE_NORMALIZED=$(printf '%s\n' "$CCUSAGE_JSON" | jq -c '
    def norm_obj:
      { inputTokens:         (.inputTokens // 0),
        outputTokens:        (.outputTokens // 0),
        cacheReadTokens:     (.cacheReadTokens // 0),
        cacheCreationTokens: (.cacheCreationTokens // .cacheWriteTokens // 0),
        totalTokens:         (.totalTokens // 0),
        totalCost:           (.totalCost // .costUSD // 0) };
    def sum_arr:
      { inputTokens:         ([.[].inputTokens // 0] | add // 0),
        outputTokens:        ([.[].outputTokens // 0] | add // 0),
        cacheReadTokens:     ([.[].cacheReadTokens // 0] | add // 0),
        cacheCreationTokens: ([.[] | (.cacheCreationTokens // .cacheWriteTokens // 0)] | add // 0),
        totalTokens:         ([.[].totalTokens // 0] | add // 0),
        totalCost:           ([.[] | (.totalCost // .costUSD // 0)] | add // 0) };
    if   type == "array"  then sum_arr
    elif type == "object" then
      if   .totals   != null then (.totals   | norm_obj)
      elif .summary  != null then (.summary  | norm_obj)
      elif .sessions != null then (.sessions | sum_arr)
      elif .data     != null then (.data     | sum_arr)
      else norm_obj
      end
    else null
    end
  ' 2>/dev/null || echo "null")
fi

# ── Extract token fields ─────────────────────────────────────────────────────────
INPUT_TOKENS="unavailable"
OUTPUT_TOKENS="unavailable"
CACHE_READ_TOKENS="unavailable"
CACHE_CREATION_TOKENS="unavailable"
TOTAL_TOKENS="unavailable"
ESTIMATED_COST="unavailable"

if [ "$_CCUSAGE_NORMALIZED" != "null" ] && command -v jq >/dev/null 2>&1; then
  _in=$(printf '%s\n' "$_CCUSAGE_NORMALIZED" | jq -r '.inputTokens' 2>/dev/null || true)
  _out=$(printf '%s\n' "$_CCUSAGE_NORMALIZED" | jq -r '.outputTokens' 2>/dev/null || true)
  _cr=$(printf '%s\n' "$_CCUSAGE_NORMALIZED" | jq -r '.cacheReadTokens' 2>/dev/null || true)
  _cc=$(printf '%s\n' "$_CCUSAGE_NORMALIZED" | jq -r '.cacheCreationTokens' 2>/dev/null || true)
  _tot=$(printf '%s\n' "$_CCUSAGE_NORMALIZED" | jq -r '.totalTokens' 2>/dev/null || true)
  _cost=$(printf '%s\n' "$_CCUSAGE_NORMALIZED" | jq -r '.totalCost' 2>/dev/null || true)
  [ -n "$_in"   ] && [ "$_in"   != "null" ] && INPUT_TOKENS="$_in"
  [ -n "$_out"  ] && [ "$_out"  != "null" ] && OUTPUT_TOKENS="$_out"
  [ -n "$_cr"   ] && [ "$_cr"   != "null" ] && CACHE_READ_TOKENS="$_cr"
  [ -n "$_cc"   ] && [ "$_cc"   != "null" ] && CACHE_CREATION_TOKENS="$_cc"
  [ -n "$_tot"  ] && [ "$_tot"  != "null" ] && TOTAL_TOKENS="$_tot"
  if [ -n "$_cost" ] && [ "$_cost" != "null" ]; then
    ESTIMATED_COST="\$$_cost"
  fi
fi

# ── Save baseline if requested ───────────────────────────────────────────────────
if [ -n "$OPT_SAVE_BASELINE" ]; then
  BASELINE_SAVE_PATH="$SNAPSHOT_DIR/baseline-${OPT_SAVE_BASELINE}.json"
  if [ "$_CCUSAGE_NORMALIZED" != "null" ] && command -v jq >/dev/null 2>&1; then
    printf '%s\n' "$_CCUSAGE_NORMALIZED" | jq --arg ts "$TIMESTAMP" '. + {_savedAt: $ts}' \
      > "$BASELINE_SAVE_PATH" 2>/dev/null \
      && printf 'Baseline saved: %s\n' "$BASELINE_SAVE_PATH" \
      || printf 'WARNING: baseline save failed (check %s is writable)\n' "$SNAPSHOT_DIR" >&2
  else
    printf 'WARNING: ccusage data unavailable — baseline not saved.\n' >&2
  fi
fi

# ── Compute per-prompt delta from baseline ──────────────────────────────────────
DELTA_INPUT="unavailable"
DELTA_OUTPUT="unavailable"
DELTA_CACHE_READ="unavailable"
DELTA_CACHE_CREATION="unavailable"
DELTA_TOTAL="unavailable"
DELTA_COST="unavailable"

if [ -n "$OPT_DELTA_FROM_BASELINE" ]; then
  if [ ! -f "$OPT_DELTA_FROM_BASELINE" ]; then
    printf 'WARNING: baseline file not found: %s — delta fields set to unavailable.\n' "$OPT_DELTA_FROM_BASELINE" >&2
  elif [ "$_CCUSAGE_NORMALIZED" = "null" ]; then
    printf 'WARNING: current ccusage unavailable — delta fields set to unavailable.\n' >&2
  elif command -v jq >/dev/null 2>&1; then
    _BASELINE_JSON=$(cat "$OPT_DELTA_FROM_BASELINE" 2>/dev/null || echo "null")
    if [ -n "$_BASELINE_JSON" ] && [ "$_BASELINE_JSON" != "null" ]; then
      _DELTA=$(jq -n \
        --argjson cur  "$_CCUSAGE_NORMALIZED" \
        --argjson base "$_BASELINE_JSON" \
        '
        def diff(a; b):
          if (a | type) == "number" and (b | type) == "number" then a - b
          else "unavailable" end;
        {
          dIn:   diff($cur.inputTokens;         $base.inputTokens),
          dOut:  diff($cur.outputTokens;        $base.outputTokens),
          dCR:   diff($cur.cacheReadTokens;     $base.cacheReadTokens),
          dCC:   diff($cur.cacheCreationTokens; $base.cacheCreationTokens),
          dTot:  diff($cur.totalTokens;         $base.totalTokens),
          dCost: diff($cur.totalCost;           $base.totalCost)
        }
        ' 2>/dev/null || echo "null")
      if [ -n "$_DELTA" ] && [ "$_DELTA" != "null" ]; then
        DELTA_INPUT=$(printf '%s\n' "$_DELTA" | jq -r '.dIn'   2>/dev/null || echo "unavailable")
        DELTA_OUTPUT=$(printf '%s\n' "$_DELTA" | jq -r '.dOut'  2>/dev/null || echo "unavailable")
        DELTA_CACHE_READ=$(printf '%s\n' "$_DELTA" | jq -r '.dCR'   2>/dev/null || echo "unavailable")
        DELTA_CACHE_CREATION=$(printf '%s\n' "$_DELTA" | jq -r '.dCC'   2>/dev/null || echo "unavailable")
        DELTA_TOTAL=$(printf '%s\n' "$_DELTA" | jq -r '.dTot'  2>/dev/null || echo "unavailable")
        _dc=$(printf '%s\n' "$_DELTA" | jq -r '.dCost' 2>/dev/null || echo "")
        if [ -n "$_dc" ] && [ "$_dc" != "null" ] && [ "$_dc" != "unavailable" ]; then
          DELTA_COST="\$$_dc"
        fi
      fi
    fi
  fi
fi

# ── Write raw snapshot (gitignored, never committed) ───────────────────────────
# JSON is never built by raw string interpolation.
SNAPSHOT_WRITTEN=false

if command -v jq >/dev/null 2>&1; then
  jq -n \
    --arg ts             "$TIMESTAMP" \
    --arg repo           "$REPO" \
    --arg branch         "$BRANCH" \
    --arg diff_stats     "$DIFF_STATS" \
    --arg ccusage_source "$CCUSAGE_SOURCE" \
    --argjson ccusage    "${CCUSAGE_JSON:-null}" \
    '{timestamp:$ts,repo:$repo,branch:$branch,diff_stats:$diff_stats,ccusage_source:$ccusage_source,ccusage:$ccusage}' \
    > "$SNAPSHOT_FILE" 2>/dev/null && SNAPSHOT_WRITTEN=true
elif command -v python3 >/dev/null 2>&1; then
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

# ── Sanitized ledger row (26 columns) ───────────────────────────────────────────────
# Date|PR|PromptID|Phase|LinkedPR|Area|Session|Model|Chat|Source|
# In|Out|CacheRead|CacheCreate|Total|Cost|
# ΔIn|ΔOut|ΔCacheRead|ΔCacheCreate|ΔTotal|ΔCost|Waste|Drivers|FollowUp|Lesson
LEDGER_ROW="| $DATE_ONLY | $OPT_PR | $OPT_PROMPT_ID | $OPT_PHASE | $OPT_LINKED_PR | $OPT_REPO_AREA | $OPT_SESSION_URL | $OPT_MODEL | $OPT_CHAT_STRATEGY | $CCUSAGE_SOURCE | $INPUT_TOKENS | $OUTPUT_TOKENS | $CACHE_READ_TOKENS | $CACHE_CREATION_TOKENS | $TOTAL_TOKENS | $ESTIMATED_COST | $DELTA_INPUT | $DELTA_OUTPUT | $DELTA_CACHE_READ | $DELTA_CACHE_CREATION | $DELTA_TOTAL | $DELTA_COST | $OPT_WASTE_CLASSIFICATION | $OPT_MAIN_DRIVERS | $OPT_FOLLOW_UP_PATCHES | $OPT_EFFICIENCY_LESSON |"

# ── Print usage note ───────────────────────────────────────────────────────────
printf '\n=== AI Usage Note ===\n'
printf 'Timestamp:    %s\n' "$TIMESTAMP"
printf 'Repo:         %s\n' "$REPO"
printf 'Branch:       %s\n' "$BRANCH"
printf 'Diff stats:   %s\n' "$DIFF_STATS"
printf 'Usage source: %s\n' "$CCUSAGE_SOURCE"

if [ -n "$CCUSAGE_JSON" ] && command -v jq >/dev/null 2>&1; then
  printf 'Session:  in=%-10s out=%-10s cacheR=%-10s cacheC=%-10s total=%-10s cost=%s\n' \
    "$INPUT_TOKENS" "$OUTPUT_TOKENS" "$CACHE_READ_TOKENS" "$CACHE_CREATION_TOKENS" \
    "$TOTAL_TOKENS" "$ESTIMATED_COST"
  if [ "$DELTA_TOTAL" != "unavailable" ]; then
    printf 'Delta:    in=%-10s out=%-10s total=%-10s cost=%s\n' \
      "$DELTA_INPUT" "$DELTA_OUTPUT" "$DELTA_TOTAL" "$DELTA_COST"
  fi
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
