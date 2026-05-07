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

## Usage rules

- Label by current PR need, not aspiration.
- Remove stale labels after follow-up updates.
- Use `ai:runtime-validation-needed` only when local tests cannot prove the production behavior.
- Use `ai:no-ui-validation-yet` to prevent unnecessary manual UI checks after backend-only/internal PRs.
