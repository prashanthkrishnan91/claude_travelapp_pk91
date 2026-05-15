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

# Self-test:
python3 scripts/workflow/ai_pr_readiness_check.py --self-test
```

## CI behavior

`.github/workflows/ai-pr-readiness.yml` runs on every pull_request event. It hard-fails on structural misses. Level 0 / docs-only PRs may pass `--allow-no-ledger` but must document why no ledger row applies.

## Hard failures vs warnings

**Hard failures** (exit 1) — must be fixed before opening/updating the PR:
- Level 1+ PR does not change `USAGE_LEDGER.md` and does not mark usage unavailable
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

## Usage ledger enforcement

The key invariant: **PR body usage claims must match committed ledger state.**

- PR body says "usage tracked" + `USAGE_LEDGER.md` not changed = hard fail
- Level 1+ PR with product/workflow code + no ledger update + no unavailable note = hard fail
- Tooling unavailable: manual row still required with metadata; token/delta fields marked unavailable
- Exact per-prompt deltas require a baseline before work starts; if missed, mark unavailable

## Context / same-chat rules

- Fresh chat is the default for new PRs, new slices, new blockers
- Same-chat only for open-PR patches or tightly adjacent safe continuation
- Follow-up count > 1 in same-chat triggers a warning
- Same-chat + production/debug triggers a warning

## Design / runtime gates

**Design:** PRs touching design-system files or mentioning design overhaul must classify scope. Foundation-only must plan visible adoption. "Visual transformation" without UI validation and not classified foundation-only = hard fail.

**Runtime:** PRs referencing production/runtime/cache must include failure-seam evidence. Symptom patches without root cause evidence trigger a warning or fail.

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
