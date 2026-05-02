# Skill: Supabase Change / Migration Gate

Use this skill for any task that may touch Supabase schema, RLS, SQL migrations, auth policies, persistence contracts, or JSONB storage semantics.

## Model
Codex for small SQL/migration audits or focused fixes. Sonnet only for larger persistence implementation with explicit budget approval.

## Scope rules
- State clearly whether Supabase SQL is required.
- If SQL is required, list exact migration file names and manual SQL steps.
- Do not mix schema migration with broad UI redesign.
- Keep migration + backend contract changes in one focused PR when possible.
- Frontend display polish should be a separate PR unless the migration is useless without minimal UI surfacing.

## Required output
```md
Persistence change:
Migration required: Yes/No
Migration files:
Manual Supabase SQL steps:
Backend/API files:
Frontend files:
Tests:
Rollback risk:
HANDOFF.md edited: Yes/No + reason
README.md edited: Yes/No + reason
```
