# AI Usage Tracking

Lightweight workflow for capturing Claude session usage in PR summaries and a committed audit ledger.
No product code is touched. All raw data is gitignored and stays local.

## Two-layer model

| Layer | Location | Committed? | Purpose |
|---|---|---|---|
| Raw snapshots | `.ai/usage/*.json` | No (gitignored) | Local debugging, full token detail |
| Sanitized ledger | `docs/ai/USAGE_LEDGER.md` | Yes | Auditable PR/session-level history |

**PR usage notes in the PR body are not sufficient for workflow audits.** They are too lossy once the PR is merged. The committed ledger (`docs/ai/USAGE_LEDGER.md`) is the durable audit source.

## Quick start (manual — preferred)

```bash
# Print usage note + ledger row (no file changes):
bash scripts/ai/usage_snapshot.sh --pr <PR-number> --model <model> --repo-area "area/stage"

# Print usage note + append ledger row to docs/ai/USAGE_LEDGER.md:
bash scripts/ai/usage_snapshot.sh \
  --pr <PR-number> --model <model> --repo-area "area/stage" \
  --main-drivers "anchor reads" --follow-up-patches 0 \
  --efficiency-lesson "narrow reads" --append-ledger
```

Copy the printed `**Usage note:**` line into the PR body's **AI usage note** field.
Copy or confirm the `| ledger row |` was appended to `docs/ai/USAGE_LEDGER.md`.

This script is **not run automatically**. No network calls or package execution happen unless you invoke it.

## CLI flags

| Flag | Description |
|---|---|
| `--pr <number-or-url>` | PR number or URL (used in ledger row) |
| `--session-url <url>` | Claude session URL (used in ledger row) |
| `--model <name>` | Model name (e.g. `claude-sonnet-4-6`) |
| `--chat-strategy <value>` | `same-chat`, `new-chat`, or `unknown` |
| `--repo-area <text>` | Repo area / stage (e.g. `workflow/docs`) |
| `--main-drivers <text>` | What consumed tokens |
| `--follow-up-patches <n>` | Number of follow-up patches required |
| `--efficiency-lesson <text>` | One-line efficiency lesson |
| `--append-ledger` | Append sanitized row to `docs/ai/USAGE_LEDGER.md` |
| `--help` | Print usage |

## How it works

1. Calls `npx ccusage@latest session --json` to read session token/cost data from the local Claude usage database (`~/.claude/`).
2. Captures repo, branch, timestamp, and `git diff --stat` for context.
3. Writes a raw JSON snapshot to `.ai/usage/` using `jq -n --arg` (preferred) or `python3` env-var pass (fallback). If neither is available, snapshot writing is skipped and the usage note still prints.
4. Prints a compact human-readable usage note to stdout for pasting into the PR body.
5. Prints a sanitized Markdown ledger row for pasting into (or appending to) `docs/ai/USAGE_LEDGER.md`.
6. When `--append-ledger` is passed, appends the ledger row directly to `docs/ai/USAGE_LEDGER.md`.

**JSON is never built by raw string interpolation** — values are passed as typed arguments to `jq` or as environment variables to `python3`.

## Fallback behaviour (fails soft)

| Missing tool | Behaviour |
|---|---|
| `npx` / Node not installed | `ccusage` skipped; source reported as `unavailable` |
| `ccusage session` returns no data | Source reported as `unavailable`; fallback hints printed |
| `jq` not installed | Falls back to `python3` for snapshot writing |
| `jq` and `python3` both absent | Snapshot writing skipped; usage note and ledger row still printed |
| `.ai/usage/` not writable | Snapshot write silently skipped; note still printed |
| `docs/ai/USAGE_LEDGER.md` not found | `--append-ledger` warns and skips; row still printed to stdout |

Fallback options when ccusage is unavailable:
- Claude Code status line shows a live session token count — use that as `source: statusline`.
- Estimate from task scope (small/medium/large) as `source: manual`.
- Token fields in the ledger row will show `unavailable` — that is acceptable.

## Backfill

When you have recent Claude sessions without committed ledger rows:

```bash
bash scripts/ai/backfill_usage_ledger.sh --since YYYY-MM-DD
```

Prints candidate rows with `unknown` PR mapping. Use `--append-ledger` to append them.
Never guess PR numbers — mark unknown ones as `unknown`.

## Optional Stop hook (explicit opt-in only)

The repo's `.claude/settings.json` includes a `Stop` hook entry that runs `usage_snapshot.sh` **only** when `AI_USAGE_SNAPSHOT_ON_STOP=1` is set in your local environment. By default it is a **complete no-op** — no network calls, no package execution, no overhead.

To enable automatic capture at session end:
```bash
export AI_USAGE_SNAPSHOT_ON_STOP=1   # add to your ~/.zshrc or ~/.bashrc
```

The hook (when opted in):
- Writes to `.ai/usage/` only (gitignored)
- Does **not** add context to the Claude conversation
- Does **not** block the session
- Is completely silent if the env var is absent

To remove the hook entry entirely, delete the `usage_snapshot` command object from `.claude/settings.json`.

## Limitations

- `ccusage` reads the local Claude usage DB (`~/.claude/`). Not available in CI, web-only Claude sessions, or machines without Claude Code CLI.
- Usage data is session-level, not per-prompt. One Claude Code chat session ≈ one PR, which is sufficient for this workflow.
- Cost figures from ccusage reflect API-level pricing and may differ from subscription billing.
- Raw snapshots are never committed. `.ai/usage/` is gitignored.

## Usage note format (required in every PR)

```
**Usage note:** Low/Medium/High; source: ccusage/statusline/manual/unavailable;
main drivers: [e.g. large context reads, many tool calls];
justified: yes/partially/no;
next efficiency improvement: [e.g. narrow anchor reads, skip redundant tool calls]
```

**Usage level guide:**
- Low — routine small patch, few tool calls, short context
- Medium — multi-file change, several discovery reads, moderate tool calls
- High — broad discovery, large diffs, many iterations
