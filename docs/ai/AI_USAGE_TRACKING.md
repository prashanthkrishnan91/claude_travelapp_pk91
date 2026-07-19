# AI Usage Tracking

Lightweight workflow for capturing Claude session usage in PR summaries and a committed audit ledger.
No product code is touched. All raw data is gitignored and stays local.

## Two-layer model

| Layer | Location | Committed? | Purpose |
|---|---|---|---|
| Raw snapshots | `.ai/usage/*.json` | No (gitignored) | Local debugging, full token detail |
| Slim decision ledger | `docs/ai/USAGE_LEDGER.md` | Yes | One row per PR: Date, PR/Branch, Level, Chat, Follow-ups, Waste, Lesson |
| Archived history | `docs/ai/USAGE_LEDGER_ARCHIVE_2026H1.md` | Yes (frozen) | Full pre-2026-07 detailed rows, preserved unmodified |

**PR usage notes in the PR body are not sufficient for workflow audits.** They are too lossy once the PR is merged. The committed ledger (`docs/ai/USAGE_LEDGER.md`) is the durable audit source — a slim one-row-per-PR decision log, not a token-accounting log.

## Ledger claim enforcement

The readiness checker (`scripts/workflow/ai_pr_readiness_check.py`) enforces that PR body usage claims match committed ledger state:

- If a PR body says "usage tracked", "usage ledger updated", or "see usage ledger" but `docs/ai/USAGE_LEDGER.md` did not change in the PR, the checker hard-fails.
- **Level 1+ PRs must commit a slim decision row** (Date, PR/Branch, Level, Chat, Follow-ups, Waste, Lesson) — the slim schema carries no token/delta columns at all, so there is nothing to mark `unavailable` there; token/delta detail belongs in the local snapshot and the PR-body usage note instead.
- Level 0 docs-only PRs may skip ledger rows entirely.
- Same-chat continuation must be reflected in the ledger row with `Chat: same-chat`.
- The readiness check runs in CI (`.github/workflows/ai-pr-readiness.yml`) and locally via `python3 scripts/workflow/ai_pr_readiness_check.py`.
- `scripts/workflow/certify_v4_1.py` separately verifies the ledger's structural shape: the exact seven-column header exists, at least one substantive data row exists, every data row has exactly seven cells, and the archive is referenced.

## Quick start (manual — preferred)

```bash
bash scripts/ai/usage_snapshot.sh \
  --pr <N-or-branch> --level <0-3> \
  --chat-strategy new-chat --follow-up-patches 0 \
  --waste-classification none \
  --efficiency-lesson "one-line lesson, max 25 words" \
  --append-ledger
```

Copy the printed `**Usage note:**` line into the PR body's **AI usage note** field. Raw token/cost detail, prompt ID, phase, model, and linked-PR context stay in the local snapshot (`.ai/usage/`) and in that PR-body usage note — they are no longer written to the committed ledger.

This script is **not run automatically**. No network calls or package execution happen unless you invoke it.

## CLI flags

| Flag | Written to committed ledger row? | Description |
|---|---|---|
| `--pr <number-or-branch>` | Yes, as `PR / Branch` (defaults to current git branch) | PR number, URL, or branch name |
| `--level <0-3>` | Yes, as `Level` (default `unavailable`) | Severity level |
| `--chat-strategy <value>` | Yes, as `Chat` | `same-chat` \| `new-chat` \| `unknown` |
| `--follow-up-patches <n>` | Yes, as `Follow-ups` | Number of follow-up patches required |
| `--waste-classification <value>` | Yes, as `Waste` | `none` \| `preventable-follow-up` \| `necessary-follow-up` \| `exploration` \| `unknown` |
| `--efficiency-lesson <text>` | Yes, as `Lesson` (max 25 words — warns if exceeded) | One-line efficiency lesson |
| `--session-url <url>` | No — local snapshot / PR usage note only | Claude session URL |
| `--model <name>` | No — local snapshot / PR usage note only | Model name (e.g. `claude-sonnet-4-6`) |
| `--repo-area <text>` | No — local snapshot / PR usage note only | Repo area / stage |
| `--prompt-id <text>` | No — local snapshot / PR usage note only | Prompt/patch ID |
| `--phase <value>` | No — local snapshot / PR usage note only | `initial` \| `follow-up` \| `audit` \| `merge-gate` \| `backfill` \| `unknown` |
| `--linked-pr <number-or-url>` | No — local snapshot / PR usage note only | Original PR this follow-up belongs to |
| `--main-drivers <text>` | No — local snapshot / PR usage note only | What consumed tokens |
| `--save-baseline <name>` | No | Save current totals to `.ai/usage/baseline-<name>.json` |
| `--delta-from-baseline <path>` | No | Compute per-prompt delta from this baseline file |
| `--append-ledger` | — | Append the 7-column row to `docs/ai/USAGE_LEDGER.md` |
| `--help` | — | Print usage |

The flags marked "local snapshot / PR usage note only" remain accepted for backward compatibility — existing invocations do not break — but none of them are written to the committed ledger row anymore.

## How it works

1. Calls `npx ccusage@latest session --json` to read session token/cost data.
2. Normalizes the ccusage response.
3. If `--save-baseline <name>`: saves numeric totals to `.ai/usage/baseline-<name>.json` (gitignored).
4. If `--delta-from-baseline <path>`: loads baseline and computes per-prompt delta.
5. Writes a raw JSON snapshot to `.ai/usage/` (gitignored, never committed).
6. Prints a compact usage note for the PR body.
7. Prints a sanitized seven-column Markdown ledger row (Date, PR/Branch, Level, Chat, Follow-ups, Waste, Lesson).
8. When `--append-ledger` is passed, appends the row to `docs/ai/USAGE_LEDGER.md`.

**JSON is never built by raw string interpolation** — values are passed via `jq --arg`/`--argjson` or Python env vars.

## Fallback behaviour (fails soft)

| Missing tool | Behaviour |
|---|---|
| `npx` / Node not installed | `ccusage` skipped; source reported as `unavailable` in the local snapshot/usage note |
| `ccusage session` returns no data | Source reported as `unavailable`; fallback hints printed |
| `jq` not installed | Falls back to `python3` for snapshot writing; ledger row still printed |
| `jq` and `python3` both absent | Snapshot writing skipped; usage note and ledger row still printed |
| `.ai/usage/` not writable | Snapshot write silently skipped; note still printed |
| `docs/ai/USAGE_LEDGER.md` not found | `--append-ledger` warns and skips; row still printed to stdout |
| Baseline file missing | Delta fields set to `unavailable` in the local snapshot/usage note; warning printed |
| `--efficiency-lesson` exceeds 25 words | Warning printed to stderr; trim before committing |

Fallback options when ccusage is unavailable: Claude Code status line (`source: statusline`) or manual estimate (`source: manual`).

## Backfill — retired

`scripts/ai/backfill_usage_ledger.sh` no longer appends to `docs/ai/USAGE_LEDGER.md`. Local ccusage session history has no PR/branch, level, chat-strategy, waste, or lesson data, so it cannot honestly populate the slim one-row-per-PR decision schema — the script does not invent placeholder decision rows from session data. `--append-ledger` now fails closed with an explanation instead of writing anything, to either the active ledger or the archive.

Historical rows committed before this schema change remain preserved, unmodified, in `docs/ai/USAGE_LEDGER_ARCHIVE_2026H1.md`. Raw per-session ccusage history stays local only, captured on demand via `scripts/ai/usage_snapshot.sh`.

## Optional Stop hook (explicit opt-in only)

The repo's `.claude/settings.json` includes a `Stop` hook entry that runs `usage_snapshot.sh` **only** when `AI_USAGE_SNAPSHOT_ON_STOP=1` is set in your local environment. By default it is a **complete no-op**.

```bash
export AI_USAGE_SNAPSHOT_ON_STOP=1   # add to your ~/.zshrc or ~/.bashrc
```

## Limitations

- `ccusage` reads the local Claude usage DB (`~/.claude/`). Not available in CI or web-only Claude sessions.
- Usage data is session-level, not per-prompt. Per-prompt deltas require explicit before/after baseline captures, and live only in the local snapshot / PR usage note — never in the committed ledger.
- Cost figures from ccusage reflect API-level pricing and may differ from subscription billing.
- Raw snapshots and baseline files are never committed. `.ai/usage/` is gitignored.

## Usage note format (required in every PR)

```
**Usage note:** Low/Medium/High; source: ccusage/statusline/manual/unavailable;
main drivers: [e.g. large context reads, many tool calls];
justified: yes/partially/no;
next efficiency improvement: [fill]
```
