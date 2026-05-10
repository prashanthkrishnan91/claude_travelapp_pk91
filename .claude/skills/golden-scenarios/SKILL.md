# Skill: golden-scenarios

## Purpose

Select relevant golden scenarios for a task.

## Inputs

- The task brief.
- `docs/product/GOLDEN_SCENARIOS.md`
- `docs/product/ROADMAP.md`
- `docs/product/FEATURE_SLICE_CONTRACT.md` if used.

## Output

- Selected scenarios (3-7):
- Why each matters:
- Tests / evidence expected per scenario:
- Scenarios intentionally out of scope and why:

## Rules

- Use 3-7 scenarios. Avoid copying the entire list.
- Include repo-specific invariants (Google Places authority, no mock / sample leakage, no unsupported visible claims).
- If the slice is wife-wow / design-sprint adjacent, include premium polish + mobile usability scenarios.
- If a chosen scenario lacks evidence, flag it and recommend test or runtime evidence.
