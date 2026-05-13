# AI Usage Ledger

Committed, sanitized audit trail of Claude token/cost usage by PR and session.

## Purpose

A future auditor can pull this file from GitHub and understand token/cost burn by PR/session without needing local raw snapshots. Raw `.ai/usage/*.json` files stay local and gitignored.

## Privacy rule

Never commit to this ledger:
- Raw `.ai/usage/*.json` snapshots
- Prompts or conversation content
- Secrets, env values, or API keys
- Local Claude DB data (`~/.claude/`)

This file contains only sanitized session-level summaries.

## Two-layer model

| Layer | Location | Committed? | Purpose |
|---|---|---|---|
| Raw snapshots | `.ai/usage/*.json` | No (gitignored) | Local debugging, full token detail |
| Sanitized ledger | `docs/ai/USAGE_LEDGER.md` | Yes | Auditable PR/session-level history |

PR usage notes in the PR body are not sufficient for workflow audits — they are too lossy once the PR is merged. This ledger is the durable audit source.

## Ledger columns

| Column | Description |
|---|---|
| Date | ISO date of the session (YYYY-MM-DD) |
| PR | PR number or `unknown` |
| Repo area / stage | e.g. `workflow/docs`, `backend/concierge`, `frontend/trip` |
| Claude session | Session URL or `unknown` |
| Model | e.g. `claude-sonnet-4-6`, `claude-opus-4-7` |
| Chat strategy | `same-chat`, `new-chat`, or `unknown` |
| Source | `ccusage`, `statusline`, `manual`, or `unavailable` |
| Input tok | Input tokens from ccusage, or `unavailable` |
| Output tok | Output tokens from ccusage, or `unavailable` |
| Cache read | Cache read tokens from ccusage, or `unavailable` |
| Cache write | Cache write tokens from ccusage, or `unavailable` |
| Total tok | Total tokens from ccusage, or `unavailable` |
| Est. cost | Estimated cost from ccusage, or `unavailable` |
| Main drivers | What consumed tokens (e.g. broad discovery, many iterations) |
| Follow-up patches | Number of follow-up PRs required |
| Efficiency lesson | One-line lesson for future sessions |

## Ledger table

| Date | PR | Repo area / stage | Claude session | Model | Chat strategy | Source | Input tok | Output tok | Cache read | Cache write | Total tok | Est. cost | Main drivers | Follow-up patches | Efficiency lesson |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| YYYY-MM-DD | #000 | workflow/docs | unknown | claude-sonnet-4-6 | same-chat | manual | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | template row — replace with real data | 0 | n/a |

## Adding a row for the current PR

Run `usage_snapshot.sh` with ledger flags and paste the printed row into the table above:

```bash
bash scripts/ai/usage_snapshot.sh \
  --pr <PR-number> \
  --model <model-name> \
  --chat-strategy same-chat \
  --repo-area "workflow/docs" \
  --main-drivers "anchor reads, file writes" \
  --follow-up-patches 0 \
  --efficiency-lesson "narrow anchor reads next time"
```

To append automatically instead of pasting manually, add `--append-ledger`.

If ccusage is unavailable, token fields show `unavailable` — that is acceptable. Accurate unknowns are better than false values.

## Backfilling prior sessions

When exact PR mapping is unknown:

```bash
bash scripts/ai/backfill_usage_ledger.sh --since YYYY-MM-DD
```

Prints candidate rows with `unknown` PR mapping. Append only with `--append-ledger`.
Do not guess PR numbers — mark as `unknown`.

## Audit guidance

Use this ledger plus GitHub PR history to diagnose token burn:
- High input tokens, low output → over-broad discovery reads.
- High follow-up patches → unclear contracts or scope at PR time.
- Recurring efficiency lessons → candidate for `docs/ai/MISS_LEDGER.md` promotion.
