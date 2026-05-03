# Engineering Discipline Rule

Use this rule for every Claude and Codex prompt: implementation, debugging, UI, audits, merge gates, docs, and planning.

This file distills the useful parts of public Karpathy-style Claude coding guidance into this repo's browser/mobile Claude + Codex workflow.

## Four rules

### 1. Think before coding

Do not silently guess.

- State assumptions before changing code.
- If multiple interpretations exist, surface the tradeoff.
- If the ambiguity affects implementation, stop and ask.
- Push back when the requested path is risky, overbuilt, or likely to waste usage.

### 2. Simplicity first

Use the minimum code that solves the scoped problem.

- No speculative features.
- No abstractions for one-off behavior.
- No configurability unless requested or already part of the pattern.
- No broad rewrites when a surgical fix works.
- If a solution can be much smaller and clearer, choose the smaller version.

### 3. Surgical changes

Every changed line must trace directly to the task.

- Do not refactor adjacent code unless required by the root-cause fix.
- Do not reformat unrelated files.
- Match existing project style.
- Clean up only unused code/imports created by this change.
- Mention unrelated dead code or risks; do not delete them unless asked.

### 4. Goal-driven execution

Convert the task into verifiable success criteria.

Before or during implementation, define:

- What success means.
- Which flow is being fixed or improved.
- Which focused tests/build/manual checks prove it.
- What remains out of scope.

For bugs, prefer: reproduce or identify the failing path, fix root cause, verify the flow.
For features, prefer: implement the scoped behavior, test the contract, update handoff/progress docs when required.

## Interaction with the root-cause rule

`docs/ai/ROOT_CAUSE_QUALITY_BAR.md` raises the quality bar for bugs and complex features. This file keeps all prompts disciplined so the agent does not overbuild, drift, or make unrelated changes while pursuing that quality bar.

The combined standard is:

> Small scope. Deep analysis. Simple design. Surgical patch. Verifiable result. No band-aids. No scope creep.

## Required agent behavior

For any non-trivial task, the agent should include in its final report:

```md
Assumptions:
Success criteria checked:
Files changed:
Why these changes are scoped:
Tests/verification:
Remaining risks or split needed:
```

For trivial one-line tasks, use judgment and keep the response compact.
