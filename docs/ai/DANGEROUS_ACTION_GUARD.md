# Dangerous Action Guard

Advisory scaffold to prevent accidental destructive operations in Claude-assisted workflows. Opt-in only — does not auto-block builds, tests, or ordinary commands.

## Purpose

Claude should pause and confirm with the user before any covered action. This document defines what counts as a covered action and how the guard is configured.

## Covered actions

| Category | Examples |
|---|---|
| Destructive deletes | `rm -rf`, `find ... -exec rm` |
| Raw env / secrets | Touching `.env`, `.env.local`, `.env.production`, token files |
| Destructive git | `git push --force`, `git reset --hard`, `git checkout .`, `git branch -D` |
| Production deploys | `railway deploy`, `vercel --prod`, deployment scripts |
| Migration execution | `supabase db push`, `alembic upgrade`, `flyway migrate` |
| Broad file rewrites | Overwriting many files without targeted diff review |

## Rules

- Pause and confirm with the user before any covered action.
- Never auto-commit or push without explicit approval.
- Never print secrets, tokens, or raw env values in output.
- This guard covers one-shot destructive operations only — ordinary tests, builds, and linters are never blocked.

## Local opt-in hook

Set `DANGEROUS_ACTION_GUARD=1` in your shell environment to enable the advisory hook at `.claude/hooks/dangerous_action_guard.sh`. The hook prints an advisory warning to stderr and always exits 0 — it never blocks the action.

```bash
export DANGEROUS_ACTION_GUARD=1   # add to ~/.zshrc or ~/.bashrc
```

## Certification

`scripts/workflow/certify_v4_1.py` verifies both this document and the hook script exist.

`scripts/workflow/ai_pr_readiness_check.py` check M warns if one of the pair (doc / hook) is missing.
