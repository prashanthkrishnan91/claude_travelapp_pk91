# AI Usage Ledger — Travel Concierge

Purpose: calibrate future ChatGPT → Claude/Codex prompt estimates using observed usage, not optimism.

Keep this short. Record only meaningful prompts or surprising cost events.

| Date | Work type | Model | Expected usage | Actual usage | Extra cost | Files/PR | Lesson |
|---|---|---:|---:|---:|---:|---|---|
| 2026-04-29 | UI foundation PR | Sonnet | underestimated | ~43% before merge / ~51% lifecycle | unknown | PR #168, 15 changed files | Full-app UI foundation prompts are High unless capped; must split or cap file count. |
| 2026-04-29 | whyPick evidence implementation | Sonnet | not estimated | ~12% session | $0.84 extra in one related run | PR #166, 4 files | Evidence extraction with 1 primary file + focused tests is Medium; discovery budget required. |
| 2026-04-29 | whyPick pre-merge audit | Sonnet | not estimated | extra usage after session exhausted | ~$0.72 | PR #166 audit | Deep Sonnet audits are too expensive; use Codex cheap merge gate first. |

## Current calibration

- Codex small bug/audit: Low expected usage.
- Sonnet one-primary-file implementation: Medium, roughly 6–12% session.
- Sonnet UI foundation with 8+ files: Medium-High to High, roughly 20–50% lifecycle.
- Post-PR Sonnet continuation can add 5–10%; stop the Claude chat after PR.

## Required fields for future entries

- Prompt type
- Model
- Predicted usage
- Actual before/after session %
- Extra cost if shown
- Files changed / PR number
- What caused overrun or savings
