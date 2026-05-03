# Root-Cause Quality Bar

Use this rule for bugs, regressions, complex feature work, and PR reviews.

## Principle

Strive for perfection; settle for excellence. Fix the root cause once and well within the approved scope.

Do not patch symptoms, hide broken behavior, remove UI, add brittle glue code, or make the app merely appear to work when the real end-to-end flow is fixable.

## Bounded completeness

The standard is not "good enough." The standard is a complete, durable fix for the scoped PR.

Complete means:

- Understand the end-to-end flow before changing code.
- Identify the real root cause, not just the failing line.
- Preserve or improve the user experience instead of deleting broken capability.
- Add or update focused tests when behavior changes.
- Update handoff/progress docs when future work needs the context.
- Verify the fix through the most relevant focused test/build/manual checks available.

Bounded means:

- Do not expand into unrelated screens, architecture, polish, or features.
- Do not silently turn a scoped fix into a broad rewrite.
- If the real fix requires broader scope, stop and propose the split instead of shipping a workaround.

## Anti-patterns

Avoid these unless explicitly approved as a temporary emergency mitigation:

- Removing a UI affordance because the underlying flow is broken.
- Adding fallback data that masks missing backend/persistence wiring.
- Hardcoding values instead of fixing mapping, ownership, or contract issues.
- Catching and suppressing errors without fixing the cause.
- Adding duplicate state instead of reconciling the source of truth.
- Fixing only the screenshot while leaving the same bug elsewhere in the same scoped flow.
- Leaving obvious dangling threads that are directly part of the task and cheap to tie off.

## Required bugfix behavior

For bugfix/debug prompts, the agent must report:

```md
Root cause:
End-to-end flow checked:
Fix:
Why this is not a workaround:
Tests/verification:
Remaining risks or split needed:
```

## Required review behavior

For merge gates, review against this question:

> Does the PR solve the scoped problem end-to-end with tests/docs, or does it leave an avoidable dangling thread or symptom patch?

## Escalation rule

If the durable fix does not fit the approved budget/scope, do not ship a band-aid. Stop and propose:

1. Minimal safe mitigation, if needed.
2. Proper root-cause fix split.
3. Tests/verification required for the proper fix.

This rule does not override usage budgets. It raises the quality bar inside the budget and forces explicit split decisions when the real fix is larger.
