# Feature Slice Contract — Travel

Use this template for any Level 2/3 feature slice. The contract must be clear before coding.

## Feature / slice name

## Roadmap alignment

- Roadmap stage:
- Build queue item:
- Why now:
- What this unlocks:
- What this must not expand into:

## User outcome

What the user can do after this ships.

## Product contract

- Entry point:
- User actions:
- Success state:
- Empty / loading / error states:
- Mobile considerations:

## Backend / API contract

- Routes / services touched:
- Payloads changed:
- Compatibility expectations:
- Source-of-truth data:

## Frontend / UI contract

- Screens / components touched:
- State handling:
- Visible copy:
- No-leakage requirements (no mock / sample / prototype / unsupported claim leakage):

## Data / persistence contract

- Tables / storage touched:
- Migration needed: Yes / No
- Idempotency / rollback considerations:

## Trust / safety contract

- Claims allowed:
- Claims forbidden:
- Source authority (Google Places canonical for addable cards):
- User-facing uncertainty handling:

## Performance contract

- Latency / budget expectations:
- Provider / LLM / cache considerations:
- Runtime evidence needed: Yes / No

## Golden scenarios

3-7 scenarios from `docs/product/GOLDEN_SCENARIOS.md` or this slice.

## Out of scope

## Stop / split triggers

- Contract changed mid-implementation.
- Slice grew beyond original scope.
- Required runtime / Google Places evidence is unavailable.
- Touches three or more unrelated skill areas.
