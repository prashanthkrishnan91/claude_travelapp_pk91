# Tool Failure Taxonomy — Travel

When a command, test, log fetch, API call, build, deployment check, or tool call fails, classify it before patching.

## Categories

- App bug
- Test bug
- Fixture / data issue
- Environment issue
- Tooling issue
- Permission / access issue
- Network / provider issue
- Expected limitation
- Insufficient evidence

## Required response

For any failure, report:

- What failed.
- Evidence.
- Category.
- Whether user-facing behavior is affected.
- Whether this blocks merge.
- Safest next action.

## Rules

- Do not patch app code for a tooling failure.
- Do not ignore failed tests without classification.
- Do not claim runtime success without runtime evidence.
- Do not ask PK for manual validation until cheaper repo / log / test evidence is exhausted.
- If access is missing, state exactly what evidence is unavailable.

## Examples

- A `pytest` failure that reproduces against the production data path → `App bug`. Patch app, not test.
- A `pytest` failure that only fires under a fixture missing from CI → `Fixture / data issue`. Fix fixture or skip with reason.
- A `railway-logs` fetch returning 401 → `Permission / access issue`. State what evidence is unavailable; do not infer runtime behavior.
- A Google Places query timing out under heavy fanout → `Network / provider issue` or `Expected limitation`. Confirm before claiming app bug.
- A failed Vercel preview that only changed docs → `Tooling issue` or `Environment issue`. Do not patch app behavior.
