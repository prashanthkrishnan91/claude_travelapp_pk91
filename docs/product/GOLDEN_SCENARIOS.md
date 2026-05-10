# Golden Scenarios — Travel

Product invariants future PRs can reuse. Not exhaustive tests — these are the things that must keep working.

Use `.claude/skills/golden-scenarios/SKILL.md` to select 3-7 relevant scenarios per slice.

## Seed scenarios

1. User can open the app and get value without creating a trip.
2. User can search / discover travel ideas without a trip.
3. User can save a result to a list.
4. User can add a saved item to an existing trip.
5. AI Concierge returns Google-verified addable cards for place asks.
6. No mock / sample / prototype copy leaks into user-facing surfaces.
7. No unsupported visible claims (no fake waterfront views, fake awards, fake hours, fake availability).
8. Mobile browsing / saving remains usable.

## Rules

- Level 2+ implementation prompts should include 3-7 relevant golden scenarios.
- Golden scenarios are not exhaustive tests; they are product invariants.
- If a PR breaks a golden scenario intentionally, the PR must explain why and update `docs/product/ROADMAP.md` and `docs/product/DECISION_LOG.md`.
- New scenarios are added when the roadmap advances a stage; do not bloat this file with edge cases.
