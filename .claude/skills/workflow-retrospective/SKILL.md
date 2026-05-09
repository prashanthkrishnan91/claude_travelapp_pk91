---
name: workflow-retrospective
description: Run a short retrospective after meaningful PRs or failed validation. Recommend MISS_LEDGER updates and promotion targets only when evidence justifies it.
---

# workflow-retrospective

## When to use

After Level 1+ implementation, Level 2/3 workflow/architecture/provider/policy/SQL/runtime/deployment/UI changes, failed validation, follow-ups after PR review, prompt-format misses, or Codex rescues.

Do not run for typo-only, tiny docs-only, pure formatting, or comment-only changes with no workflow implication.

## How to run

1. Read `docs/ai/WORKFLOW_RETROSPECTIVE.md`.
2. Produce the retrospective output exactly as defined there.
3. Recommend whether `docs/ai/MISS_LEDGER.md` should be updated.
4. Recommend a promotion target only when there is repeated or high-severity evidence (see `docs/ai/OS_LEARNING_PROTOCOL.md`).
5. Do not update OS files automatically unless the task explicitly instructs it.
6. Keep output concise. One screen.

## Anti-bloat

- One isolated miss → MISS_LEDGER only.
- Repeated miss → propose one precise target.
- Do not propose broad rule changes from a single PR.

## Extended checks (when warranted)

- Check token/cost discipline.
- Check reviewer-agent budget discipline.
- Check prompt-intake classification.
- Check subagent output quality.
- Check OS drift.
- Check whether `/compact`, `/cost`, `/review`, `/pr_comments`, `/doctor`, `/memory`, `/permissions`, or `/mcp` would have been useful.
- Check whether the task should have started in a new chat or stopped earlier.
- Keep output to one screen unless explicitly asked for a deep retrospective.
