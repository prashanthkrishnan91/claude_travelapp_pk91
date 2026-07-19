#!/usr/bin/env bash
# scripts/ai/backfill_usage_ledger.sh
#
# RETIRED: active-ledger backfill.
#
# The slim docs/ai/USAGE_LEDGER.md schema (Date | PR / Branch | Level | Chat |
# Follow-ups | Waste | Lesson) is a one-row-per-PR *decision* log. Local ccusage
# session history cannot honestly populate it — a session has no knowledge of
# which PR/branch it belonged to, what severity level the work was, what chat
# strategy was used, or what the waste/lesson decision was. Backfilling
# placeholder rows from session data would misrepresent them as real decision
# rows, so this script no longer writes to docs/ai/USAGE_LEDGER.md.
#
# Historical detailed rows committed before this schema change remain preserved,
# unmodified, in docs/ai/USAGE_LEDGER_ARCHIVE_2026H1.md. This script does not
# append to that archive either — it is a frozen historical record, not a live
# target.
#
# Raw per-session ccusage history remains local only, via
# scripts/ai/usage_snapshot.sh (writes to .ai/usage/, gitignored, never
# committed).
#
# Usage:
#   bash scripts/ai/backfill_usage_ledger.sh [OPTIONS]
#
# Options:
#   --since YYYY-MM-DD   Accepted for backward compatibility; ignored (no-op).
#   --until YYYY-MM-DD   Accepted for backward compatibility; ignored (no-op).
#   --append-ledger      Fails closed — active-ledger backfill is retired.
#   --help                Print this help

OPT_APPEND_LEDGER=false

print_help() {
  printf 'Usage: bash scripts/ai/backfill_usage_ledger.sh [OPTIONS]\n\n'
  printf 'RETIRED: this script no longer writes to docs/ai/USAGE_LEDGER.md.\n'
  printf 'The slim ledger is a one-row-per-PR decision log; ccusage session\n'
  printf 'history cannot honestly populate PR/branch, level, chat strategy,\n'
  printf 'waste, or lesson fields, so no placeholder rows are generated.\n\n'
  printf 'Historical rows remain in docs/ai/USAGE_LEDGER_ARCHIVE_2026H1.md.\n'
  printf 'Raw per-session data stays local via scripts/ai/usage_snapshot.sh.\n\n'
  printf 'Options:\n'
  printf '  --since YYYY-MM-DD   Accepted for backward compatibility; ignored (no-op)\n'
  printf '  --until YYYY-MM-DD   Accepted for backward compatibility; ignored (no-op)\n'
  printf '  --append-ledger      Fails closed — active-ledger backfill is retired\n'
  printf '  --help                Print this help\n'
  exit 0
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --since)         shift 2 ;;
    --until)         shift 2 ;;
    --append-ledger) OPT_APPEND_LEDGER=true; shift ;;
    --help|-h)       print_help ;;
    *) printf 'Unknown flag: %s\nRun with --help for usage.\n' "$1" >&2; exit 1 ;;
  esac
done

if "$OPT_APPEND_LEDGER"; then
  printf 'ERROR: --append-ledger is retired.\n' >&2
  printf 'docs/ai/USAGE_LEDGER.md is a slim one-row-per-PR decision log; local\n' >&2
  printf 'ccusage session history has no PR/branch, level, chat strategy, waste,\n' >&2
  printf 'or lesson data to honestly populate it with. No row was appended to\n' >&2
  printf 'either docs/ai/USAGE_LEDGER.md or docs/ai/USAGE_LEDGER_ARCHIVE_2026H1.md.\n' >&2
  printf 'Historical rows remain preserved, unmodified, in the archive.\n' >&2
  exit 1
fi

printf 'Active-ledger backfill is retired. Nothing to do.\n'
printf 'Historical rows: docs/ai/USAGE_LEDGER_ARCHIVE_2026H1.md (unmodified).\n'
printf 'Raw session snapshots: scripts/ai/usage_snapshot.sh (local, gitignored).\n'
exit 0
