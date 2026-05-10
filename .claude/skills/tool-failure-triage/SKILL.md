# Skill: tool-failure-triage

## Purpose

Classify failed commands / tools before implementation changes.

## Inputs

- The failure output / log / error.
- `docs/ai/TOOL_FAILURE_TAXONOMY.md`
- `docs/ai/RUNTIME_EVIDENCE.md`
- `docs/ai/KNOWN_FAILURE_MODES.md`

## Output

- Failure summary:
- Category (from `TOOL_FAILURE_TAXONOMY.md`):
- Evidence:
- Likely impact (user-facing yes / no):
- Blocker: Yes / No.
- Next action:

## Rules

- Use after failed tests, failed builds, failed log fetches, failed PR checks, failed provider / runtime calls.
- Do not patch before classification unless the failure is obvious and local.
- If access is missing, state exactly what evidence is unavailable rather than inferring.
- Cross-reference `KNOWN_FAILURE_MODES.md` to detect repeat failures.
