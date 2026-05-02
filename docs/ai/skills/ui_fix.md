# Skill: UI Fix / Visual Polish

Use this skill for a capped visual pass: dark-mode readability, card consistency, layout polish, mobile usability, or one premium UI surface.

## Model
- Codex for visual bug fixes, small CSS/class cleanup, or merge gates.
- Sonnet only for a focused multi-file UI implementation with a strict UI budget.

## Required UI budget
Every UI prompt must include, outside the copyable prompt block:

```md
UI budget:
- Phase:
- Max files:
- Primary surfaces:
- Forbidden surfaces:
- Stop condition:
- Decision:
```

## Scope rules
- One page/screen or one component family at a time.
- Full-app UI upgrades default to SPLIT.
- Sonnet UI implementation max scope: 6 files unless explicitly approved by Code Committee.
- No backend/API/business-logic changes during UI-only work.
- If visual surfaces are unknown, run `docs/ai/skills/discovery.md` first.

## Required output
```md
Visual goal:
Files changed:
Screens/surfaces touched:
Forbidden surfaces respected: Yes/No
Tests/build:
Supabase SQL: No
HANDOFF.md edited: Yes/No + reason
```
