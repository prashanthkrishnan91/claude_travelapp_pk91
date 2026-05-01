# Skill: Bugfix / Small Behavior Correction

Use this skill for focused defects, broken flows, regressions, and small behavior corrections.

## Model
Codex preferred.

## Scope rules
- One bug or one behavior correction per prompt.
- Prefer 1-2 primary edit files.
- No UI redesign unless the bug is visual and localized.
- No broad refactor.
- No new architecture.
- If the fix starts touching persistence + UI + history/analytics, split it.

## Required reads
1. `CLAUDE.md`
2. `docs/ai/HANDOFF.md`
3. The primary file(s) named in the prompt
4. Focused tests only, if named

## Required output
```md
Root cause:
Fix:
Files changed:
Tests:
Supabase SQL: Yes/No
HANDOFF.md edited: Yes/No + reason
README.md edited: Yes/No + reason
```

## Handoff rule
Update `docs/ai/HANDOFF.md` when behavior changes, persistence changes, API behavior changes, or the bug was significant enough to affect future work.
