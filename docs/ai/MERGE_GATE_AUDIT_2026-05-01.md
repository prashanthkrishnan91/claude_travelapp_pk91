# Merge-gate audit — PR fix: editable card points + account identity/sign-out

- Reviewed commit: `1f4cc38d838a89552d0c8f2eed8fa3e64a8f3df0`
- Audit date: 2026-05-01 UTC
- Verdict: NEEDS FIXES (input validation gap on edit path)

## Blocking findings
1. Edit-card submit path can send invalid numeric values (`NaN`) because it converts string to `Number(...)` without finite check; `type="number"` is client-side only and can still be bypassed or produce empty/invalid states. Existing create path has the same gap, but this PR introduces/extends the risk in editable balances.

## Non-blocking findings
- Sidebar/mobile identity and sign-out wiring are correctly connected to Supabase auth and login redirect.
- No SQL/schema changes were introduced in this commit.

## Validation commands run
- `node --test frontend/tests/cards-and-account.test.mjs`
- `node --test frontend/tests/trip-ideas.test.mjs`
- `node --test frontend/tests/itinerary-timeline.test.mjs`
