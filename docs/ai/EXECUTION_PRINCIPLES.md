# Execution Principles

Use these principles for every Claude and Codex prompt: planning, debugging, implementation, UI work, audits, and merge gates.

These principles are inspired by concise engineering guidance such as think-before-coding, simplicity-first, surgical changes, and goal-driven execution. They are adapted for this repo's browser/mobile Claude + Codex workflow.

## 1. Think before coding

Before changing code, state the working assumptions and success criteria when the task is non-trivial, ambiguous, or bug-related.

Required behavior:

- Identify what must be true for the task to be done.
- Name any ambiguity that could change the implementation.
- If ambiguity materially changes the fix, stop and ask or propose the split instead of guessing.
- For bugs, trace the end-to-end flow before patching the failing line.

## 2. Simplicity first

Prefer the smallest durable design that solves the real problem.

Required behavior:

- Use existing patterns before introducing new abstractions.
- Do not add new libraries, services, state stores, schema, or architecture unless required.
- Avoid cleverness when a clear boring solution is more maintainable.
- Do not over-generalize for hypothetical future needs.

## 3. Surgical changes

Every changed line should trace directly to the task.

Required behavior:

- Keep edits scoped to named files/surfaces where possible.
- Avoid unrelated formatting, cleanup, renames, or refactors.
- Do not touch backend/business logic during UI-only work.
- Do not touch UI during backend-only logic work unless required for a complete scoped fix.

## 4. Goal-driven execution

The output should be a finished scoped result, not a loose plan, partial patch, or workaround.

Required behavior:

- Implement the complete scoped fix with focused tests/verification.
- Update required docs when the change affects future handoff or project progress.
- Report what was verified and what remains risky.
- If the durable fix is larger than the approved scope, stop and propose a split instead of shipping a band-aid.

## 5. Bounded excellence

Strive for perfection; settle for excellence inside the approved scope.

Required behavior:

- Fix root causes, not symptoms.
- Do not hide broken behavior by removing UI or suppressing errors.
- Do not leave directly related dangling threads that are cheap to close.
- Do not expand into unrelated surfaces in the name of completeness.

## Prompt requirement

For non-trivial Claude/Codex prompts, include this line inside the copyable block:

```md
Execution principles: before coding, state assumptions and success criteria; keep changes simple and surgical; every changed line must trace to this task; fix the root cause, not a symptom; if the durable fix exceeds scope, stop and propose the split.
```
