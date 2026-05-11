# AI Usage Tracking

Lightweight workflow for capturing Claude session usage in PR summaries.
No product code is touched. All raw data is gitignored and stays local.

## Quick start

```bash
bash scripts/ai/usage_snapshot.sh
```

Copy the printed `**Usage note:**` line into the PR body's **AI usage note** field.

## How it works

1. The script calls `npx ccusage@latest --json` to read session token/cost data from the local Claude usage database (`~/.claude/`).
2. It captures repo, branch, timestamp, and `git diff --stat` for context.
3. A raw JSON snapshot is written to `.ai/usage/` (gitignored — never committed).
4. A compact human-readable note is printed to stdout for pasting into the PR body.

## Fallback behaviour (fails soft)

| Missing tool | Behaviour |
|---|---|
| `npx` / Node not installed | `ccusage` skipped; source reported as `unavailable` |
| `ccusage` returns no data | Source reported as `unavailable`; fallback hints printed |
| `jq` not installed | Raw ccusage JSON saved to snapshot; parsing skipped |
| `.ai/usage/` not writable | Snapshot write silently skipped; note still printed |

Fallback options when ccusage is unavailable:
- Claude Code status line shows a live session token count — use that as `source: statusline`.
- Estimate from task scope (small/medium/large) as `source: manual`.

## SessionEnd hook (optional)

The repo's `.claude/settings.json` includes a non-invasive `Stop` hook that runs `usage_snapshot.sh` automatically at the end of each Claude Code session. The hook writes to `.ai/usage/` only; it does not add context to the conversation or block the session.

To disable the hook, remove the usage_snapshot entry from `.claude/settings.json`.

## Limitations

- `ccusage` reads the local Claude usage DB (`~/.claude/`). It is not available in CI, web-only Claude sessions, or on machines without Claude Code CLI installed.
- Usage data is session-level, not per-prompt. One Claude Code chat session ≈ one PR, so session-level is sufficient.
- Cost figures from ccusage reflect API-level pricing and may not match subscription billing.

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
