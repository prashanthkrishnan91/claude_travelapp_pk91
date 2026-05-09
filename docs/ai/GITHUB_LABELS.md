# GitHub Labels — AI Workflow

Use these labels to make PR state obvious across ChatGPT, Claude, Codex, and PK.

## Recommended labels

- `ai:needs-chatgpt-review` — PR needs ChatGPT diff/evidence review before merge.
- `ai:needs-claude-update` — PR needs Claude follow-up on the same branch.
- `ai:merge-ok-after-ci` — PR can merge after required checks pass.
- `ai:runtime-validation-needed` — Railway/Vercel/Supabase/runtime evidence is required.
- `ai:no-ui-validation-yet` — UI validation is intentionally deferred because product-visible behavior did not change.
- `severity:level-0` — tiny/docs/test-only/safe change.
- `severity:level-1` — focused bug/fix/small implementation.
- `severity:level-2` — cross-contract/root-cause/full plumbing fix.
- `severity:level-3` — architecture split/spec required before implementation.

## OS v3 docs-only labels

- `ai:miss-ledger-needed` — PR identified a workflow miss that should be recorded in `docs/ai/MISS_LEDGER.md`.
- `ai:workflow-retro-needed` — PR is meaningful enough to require a workflow retrospective.
- `ai:os-promotion-candidate` — PR proposes promoting a recurring miss to a precise OS surface.
- `ai:deployment-cost-risk` — PR carries notable deployment/build-cost risk that should be classified.

These OS v3 entries are documentation-only label names. Do not create labels via API as part of OS v3.

## Usage rules

- Label by current PR need, not aspiration.
- Remove stale labels after follow-up updates.
- Use `ai:runtime-validation-needed` only when local tests cannot prove the production behavior.
- Use `ai:no-ui-validation-yet` to prevent unnecessary manual UI checks after backend-only/internal PRs.
