# ai-pr-readiness

Run the AI PR Readiness Gate before opening or updating any Level 1+ PR.

## What it checks

- `docs/ai/USAGE_LEDGER.md` updated, or usage explicitly marked unavailable with reason
- PR body does not claim usage tracking unless the ledger actually changed
- PR body contains all required sections and usage metadata anchors
- Runtime/production changes include failure-seam evidence
- Design overhaul PRs classify scope: foundation-only / visible adoption / polish
- No patch exhaustion (>=3 follow-ups) without escalation note
- Dependency/migration/env changes include justification

## Local command

```bash
python3 scripts/workflow/ai_pr_readiness_check.py --warn-only
```

With a PR body file:
```bash
python3 scripts/workflow/ai_pr_readiness_check.py --pr-body-file pr_body.txt
```

Self-test:
```bash
python3 scripts/workflow/ai_pr_readiness_check.py --self-test
```

## Before opening a PR

1. Run the checker and fix any hard failures.
2. Update `docs/ai/USAGE_LEDGER.md` — or mark usage explicitly unavailable with reason.
3. Fill the `## AI PR readiness` block in the PR body.
4. Do not write "Usage ledger row: committed" unless `docs/ai/USAGE_LEDGER.md` was actually changed in this PR.

## When the checker fails

Hard failures must be resolved before opening/updating the PR.
Warnings are advisory — resolve before merge when practical.
CI runs the checker without `--warn-only` on every PR.
