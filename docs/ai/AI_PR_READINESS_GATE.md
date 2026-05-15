# AI PR Readiness Gate

Lightweight structural checker that runs locally and in CI to catch missing usage evidence, scope drift, weak validation, patch exhaustion, and design/runtime ambiguity before PRs are considered ready.

## Purpose

Move the workflow from "remember the rules" to "repo enforces the rules." The checker verifies objective, structural properties of a PR — it does not grade prompts subjectively.

## Local command

```bash
# Advisory mode (warnings only, no hard fail):
python3 scripts/workflow/ai_pr_readiness_check.py --warn-only

# Full check with PR body file:
python3 scripts/workflow/ai_pr_readiness_check.py --pr-body-file pr_body.txt

# CI mode (reads PR body from GitHub Actions event JSON):
python3 scripts/workflow/ai_pr_readiness_check.py \
  --github-event-path "$GITHUB_EVENT_PATH" \
  --base-ref "origin/main"

# JSON output (clean JSON only, no text before it):
python3 scripts/workflow/ai_pr_readiness_check.py --format json

# Self-test:
python3 scripts/workflow/ai_pr_readiness_check.py --self-test
```

## CI behavior

`.github/workflows/ai-pr-readiness.yml` runs on every pull_request event. It hard-fails on structural misses. Level 0 / docs-only PRs may pass `--allow-no-ledger` but must document why no ledger row applies.

## Hard failures vs warnings

**Hard failures** (exit 1) — must be fixed before opening/updating the PR:
- Level 1+ PR does not change `USAGE_LEDGER.md` (even if usage tooling is unavailable)
- PR body claims usage tracking but `USAGE_LEDGER.md` was not changed
- Production/runtime PR lacks failure-seam evidence
- Design overhaul PR missing scope classification
- Visual transformation claimed without screenshot and not classified foundation-only
- Follow-up count >=3 without escalation note
- Committed `.env` / secrets file detected

**Warnings** (advisory) — resolve before merge when practical:
- Missing usage metadata fields
- UI files changed without screenshot/UI validation note
- Full suite claimed without justification
- Same-chat used for production/debug loops
- Subagent fan-out for Level 1 work
- CLAUDE.md over 200-line budget
- PR size exceeds soft limits
- Env template files committed (verify placeholders only)

## Usage ledger enforcement

The key invariants:
1. **PR body usage claims must match committed ledger state.** If you claim "usage tracked", the ledger row must exist.
2. **Level 1+ PRs must commit a ledger row.** Even if token/delta tooling is unavailable, the row itself is mandatory with metadata fields (phase, prompt ID, model, chat strategy, drivers, waste) filled and numeric fields marked `unavailable`.
3. **"Usage unavailable" is not a ledger-row exemption.** It marks token/delta values as unavailable, not the row. Only Level 0 docs-only PRs are exempt from the ledger requirement.

Usage claim patterns that hard-fail if ledger is not updated:
- `Usage ledger row: committed`
- `Usage ledger row: yes`
- `Usage ledger: committed`
- `Usage ledger updated: Yes`
- `see docs/ai/USAGE_LEDGER.md`
- `see usage ledger`
- `ledger row: committed`

Fallback if tooling is unavailable: append a manual row to `docs/ai/USAGE_LEDGER.md` with all metadata fields filled and token/delta fields marked `unavailable`.

## Context / same-chat rules

- Fresh chat is the default for new PRs, new slices, new blockers
- Same-chat only for open-PR patches or tightly adjacent safe continuation
- Follow-up count > 1 in same-chat triggers a warning
- Same-chat + production/debug triggers a warning

## Design / runtime gates

**Design:** PRs touching design-system files or mentioning design overhaul must classify scope. Foundation-only must plan visible adoption. "Visual transformation" without UI validation and not classified foundation-only = hard fail.

**Runtime:** PRs referencing production/runtime/cache must include failure-seam evidence. Symptom patches without root cause evidence trigger a warning or fail. Workflow-only PRs are exempt (the PR template's section header contains the word "runtime" and should not trigger this gate).

## Dangerous actions

Before any covered action, Claude must pause and confirm with the user. See `docs/ai/DANGEROUS_ACTION_GUARD.md` for the full list of covered actions and rules.

Opt-in local advisory hook: `.claude/hooks/dangerous_action_guard.sh` (set `DANGEROUS_ACTION_GUARD=1` to enable).

Covered actions include:
- `rm -rf` / destructive deletes
- Touching `.env` / secrets / token files
- `git push --force`, `git reset --hard`, `git branch -D`
- Production deploy commands (`railway deploy`, `vercel --prod`)
- Migration execution (`supabase db push`, `alembic upgrade`)
- Broad file rewrites without targeted review

## Optional local hook

`.claude/hooks/ai_pr_readiness_stop.sh` runs the checker in advisory mode when enabled.

Enable:
```bash
export AI_PR_READINESS_CHECK_ON_STOP=1   # add to ~/.zshrc or ~/.bashrc
```

The hook never auto-commits, never blocks coding, and never exposes `.ai/usage` files.

## What to do when it fails

1. Read the specific failure message.
2. Ledger failures: run `bash scripts/ai/usage_snapshot.sh --append-ledger ...` or add a manual row to `docs/ai/USAGE_LEDGER.md`.
3. Missing PR body sections: fill the `## AI PR readiness` block in the PR body.
4. Runtime/design failures: add the required evidence or classification to the PR body.
5. Re-run the checker to confirm all hard failures are resolved.
