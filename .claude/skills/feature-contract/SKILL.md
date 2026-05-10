# Skill: feature-contract

## Purpose

Generate or verify a Feature Slice Contract before coding bigger work.

## Inputs

- The task brief.
- `docs/product/FEATURE_SLICE_CONTRACT.md`
- `docs/product/ROADMAP.md`
- `docs/product/BUILD_QUEUE.md`
- `docs/product/RELEASE_GATES.md`
- `docs/product/GOLDEN_SCENARIOS.md`

## Output

- Feature Slice Contract (filled in or verified):
- Missing contract fields:
- Split recommendation: Yes / No.
- Golden scenarios selected:
- Validation expectations:
- Stop / split triggers:

## Rules

- Use for Level 2 / Level 3 implementation.
- Do not code until the contract is clear.
- Keep contract concise; no narrative paragraphs.
- If the task is a tiny fix, say "contract not required" and exit.
- If the contract reveals scope creep, recommend split rather than padding the contract.
