# AI Usage Tracking

Lightweight workflow for capturing Claude session usage in PR summaries and a committed audit ledger.
No product code is touched. All raw data is gitignored and stays local.

## Two-layer model

| Layer | Location | Committed? | Purpose |
|---|---|---|---|
| Raw snapshots | `.ai/usage/*.json` | No (gitignored) | Local debugging, full token detail |
| Sanitized ledger | `docs/ai/USAGE_LEDGER.md` | Yes | Auditable PR/prompt-level history |

**PR usage notes in the PR body are not sufficient for workflow audits.** They are too lossy once the PR is merged. The committed ledger (`docs/ai/USAGE_LEDGER.md`) is the durable audit source.

## Ledger claim enforcement

The readiness checker (`scripts/workflow/ai_pr_readiness_check.py`) enforces that PR body usage claims match committed ledger state:

- If a PR body says "usage tracked", "usage ledger updated", or "see usage ledger" but `docs/ai/USAGE_LEDGER.md` did not change in the PR, the checker hard-fails.
- If `docs/ai/USAGE_LEDGER.md` is unchanged and usage is not explicitly marked unavailable with a reason, Level 1+ PRs hard-fail.
- If tooling is unavailable, a manual row is still required in `docs/ai/USAGE_LEDGER.md` with metadata fields filled and token/delta fields marked `unavailable`.
- Exact per-prompt deltas require saving a baseline before work. If the baseline was missed, mark delta fields `unavailable` honestly — do not fabricate values.
- Same-chat continuation must be reflected in the ledger row with `chat: same-chat`.
- The readiness check runs in CI (`.github/workflows/ai-pr-readiness.yml`) and locally via `python3 scripts/workflow/ai_pr_readiness_check.py`.

## Quick start (manual — preferred)

```bash
# Save baseline before Claude work:
bash scripts/ai/usage_snapshot.sh --save-baseline before-pr-N

# After Claude work — print delta + append ledger row:
bash scripts/ai/usage_snapshot.sh \
  --pr <N> --prompt-id initial --phase initial \
  --delta-from-baseline .ai/usage/baseline-before-pr-N.json \
  --model <model> --repo-area "area/stage" \
  --main-drivers "anchor reads" --waste-classification none \
  --append-ledger
```

Copy the printed `**Usage note:**` line into the PR body's **AI usage note** field.

This script is **not run automatically**. No network calls or package execution happen unless you invoke it.

## CLI flags

| Flag | Description |
|---|---|
| `--pr <number-or-url>` | PR number or URL |
| `--session-url <url>` | Claude session URL |
| `--model <name>` | Model name (e.g. `claude-sonnet-4-6`) |
| `--chat-strategy <value>` | `same-chat`, `new-chat`, or `unknown` |
| `--repo-area <text>` | Repo area / stage (e.g. `workflow/docs`) |
| `--prompt-id <text>` | Prompt/patch ID (e.g. `initial`, `patch-1`, `same-chat-pr-2`) |
| `--phase <value>` | `initial` \| `follow-up` \| `audit` \| `merge-gate` \| `backfill` \| `unknown` |
| `--linked-pr <number-or-url>` | Original PR this follow-up belongs to |
| `--main-drivers <text>` | What consumed tokens |
| `--follow-up-patches <n>` | Number of follow-up patches required |
| `--waste-classification <value>` | `none` \| `preventable-follow-up` \| `necessary-follow-up` \| `exploration` \| `unknown` |
| `--efficiency-lesson <text>` | One-line efficiency lesson |
| `--save-baseline <name>` | Save current totals to `.ai/usage/baseline-<name>.json` |
| `--delta-from-baseline <path>` | Compute per-prompt delta from this baseline file |
| `--append-ledger` | Append sanitized row to `docs/ai/USAGE_LEDGER.md` |
| `--help` | Print usage |

## How it works

1. Calls `npx ccusage@latest session --json` to read session token/cost data.
2. Normalizes the ccusage response.
3. If `--save-baseline <name>`: saves numeric totals to `.ai/usage/baseline-<name>.json` (gitignored).
4. If `--delta-from-baseline <path>`: loads baseline and computes per-prompt delta.
5. Writes a raw JSON snapshot to `.ai/usage/` (gitignored, never committed).
6. Prints a compact usage note for the PR body.
7. Prints a sanitized 26-column Markdown ledger row.
8. When `--append-ledger` is passed, appends the row to `docs/ai/USAGE_LEDGER.md`.

**JSON is never built by raw string interpolation** — values are passed via `jq --arg`/`--argjson` or Python env vars.

## Fallback behaviour (fails soft)

| Missing tool | Behaviour |
|---|---|
| `npx` / Node not installed | `ccusage` skipped; source reported as `unavailable` |
| `ccusage session` returns no data | Source reported as `unavailable`; fallback hints printed |
| `jq` not installed | Falls back to `python3` for snapshot writing; ledger row still printed |
| `jq` and `python3` both absent | Snapshot writing skipped; usage note and ledger row still printed |
| `.ai/usage/` not writable | Snapshot write silently skipped; note still printed |
| `docs/ai/USAGE_LEDGER.md` not found | `--append-ledger` warns and skips; row still printed to stdout |
| Baseline file missing | Delta fields set to `unavailable`; warning printed; ledger row still produced |

Fallback options when ccusage is unavailable: Claude Code status line (`source: statusline`) or manual estimate (`source: manual`). Token and delta fields will show `unavailable` — accurate unknowns are better than false values.

## Backfill

```bash
bash scripts/ai/backfill_usage_ledger.sh --since YYYY-MM-DD
```

Emits 26-column rows with `phase=backfill`, `prompt_id=unknown`, delta=`unavailable`.
Never guesses PR numbers or delta values — marks unknown ones honestly.

## Optional Stop hook (explicit opt-in only)

The repo's `.claude/settings.json` includes a `Stop` hook entry that runs `usage_snapshot.sh` **only** when `AI_USAGE_SNAPSHOT_ON_STOP=1` is set in your local environment. By default it is a **complete no-op**.

```bash
export AI_USAGE_SNAPSHOT_ON_STOP=1   # add to your ~/.zshrc or ~/.bashrc
```

## Limitations

- `ccusage` reads the local Claude usage DB (`~/.claude/`). Not available in CI or web-only Claude sessions.
- Usage data is session-level, not per-prompt. Per-prompt deltas require explicit before/after baseline captures.
- Cost figures from ccusage reflect API-level pricing and may differ from subscription billing.
- Raw snapshots and baseline files are never committed. `.ai/usage/` is gitignored.

## Usage note format (required in every PR)

```
**Usage note:** Low/Medium/High; source: ccusage/statusline/manual/unavailable;
main drivers: [e.g. large context reads, many tool calls];
justified: yes/partially/no;
next efficiency improvement: [fill]
```
