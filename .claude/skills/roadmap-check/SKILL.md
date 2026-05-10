# Skill: roadmap-check

## Purpose

Before meaningful work, verify the task maps to product roadmap and build queue.

## Inputs

- The task brief (goal, severity, context).
- `docs/product/NORTH_STAR.md`
- `docs/product/ROADMAP.md`
- `docs/product/BUILD_QUEUE.md`
- `docs/product/RELEASE_GATES.md`
- `docs/product/DO_NOT_BUILD_YET.md`
- `docs/product/PRODUCT_HEALTH.md`

## Output

- Roadmap stage:
- Build queue item:
- Why now:
- What this unlocks:
- What this must not expand into:
- Blocker or scope-creep classification: justified blocker / scope creep / aligned / unclear.
- Recommended route: proceed / defer / split / add to idea inbox.

## Rules

- Do not allow random exciting ideas to hijack active build unless they become an explicit Now item.
- If no roadmap mapping exists, flag it.
- If the task is a critical blocker, allow it but require why it blocks the current stage.
- Keep output concise.

## Travel-specific checks

- Does this move the app toward discovery-first and wife-wow readiness?
- Is this premature deals / points / alerts / design work?
- Does it preserve the current stage focus?
