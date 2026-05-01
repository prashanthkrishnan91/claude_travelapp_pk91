# Skill: Workflow Update

Use this skill for changes to AI workflow files, prompt rules, usage ledgers, handoff policy, or repo-local skill files.

## Model
Codex preferred.

## Scope rules
- Docs/workflow only unless explicitly requested.
- Keep `CLAUDE.md` thin; route to detailed files instead of duplicating full rules.
- Put reusable rules in `docs/ai/PROMPT_LIBRARY.md` or `docs/ai/skills/*.md`.
- Put current project state in `docs/ai/HANDOFF.md`.
- Put observed usage data in `docs/ai/USAGE_LEDGER.md`.
- Do not update `README.md` unless public setup, public behavior, or architecture changed materially.

## Required output
```md
Workflow change:
Files changed:
Why this reduces usage/rework:
Behavior/app code touched: Yes/No
Supabase SQL: No
README.md edited: Yes/No + reason
```
