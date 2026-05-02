# Skill: Cheap Merge Gate

Use this skill before merging normal PRs.

## Model
Codex preferred.

## Purpose
Find blocking merge risks cheaply before spending Sonnet usage on deep audit.

## Discovery budget
- Read PR diff and changed files only.
- Do not run broad repo search.
- Do not generate exploratory scripts.
- Run focused tests only if they are named or obvious from the changed files.
- If a blocker is found, stop and report it. Do not fix it in the same pass.

## Output only
```md
Merge recommendation: MERGE / DO NOT MERGE
Blocking issues:
Tests run:
Supabase SQL: Yes/No
HANDOFF.md edited: Yes/No
README.md edited: Yes/No
Non-blocking follow-ups: max 3 bullets
```

## Escalation
Use Sonnet deep audit only if this gate finds a specific suspicious risk that requires deeper reasoning.
