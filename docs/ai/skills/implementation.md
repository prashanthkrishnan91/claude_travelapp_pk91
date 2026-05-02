# Skill: Focused Implementation

Use this skill for a scoped feature or multi-file change that is too large for a tiny bugfix but not broad enough for architecture planning.

## Model
Claude Sonnet for focused multi-file implementation. Codex may be used if the task is <=3 files, mostly mechanical, or primarily tests/refactor.

## Scope rules
- One deliverable per PR.
- Prefer 1-3 primary files; avoid more than 6 without explicit budget approval.
- Do not combine 3+ of: bug fix, UI refactor, persistence/idempotency, history/log display, analytics/performance, tests, docs, migration/schema, multiple workflows/screens.
- If the task combines 3+ categories, split using `docs/ai/PROMPT_LIBRARY.md` complex refactor split gate.

## Required prompt elements
- Primary edit target(s)
- Test target(s)
- Fallback reads only if blocked
- Discovery budget
- Timeout budget for Medium/High work
- HANDOFF.md update instruction
- Stop-after-PR instruction for Medium-High/High work

## Required output
```md
Root cause/plan:
Files changed:
Tests:
Risks:
Supabase SQL: Yes/No
HANDOFF.md edited: Yes/No + reason
README.md edited: Yes/No + reason
```
