# Claude Instructions — Travel Concierge

Use this repo through a browser/mobile Claude + Codex workflow unless the user explicitly says CLI is available.

Before work, read only the smallest needed subset of:

1. `docs/ai/HANDOFF.md` — current state
2. `docs/ai/PROMPT_LIBRARY.md` — workflow, budget, prompt, UI, and review rules
3. `docs/ai/UI_BASELINE.md` — UI baseline and known visual costs when doing UI work
4. `docs/ai/CLAUDE_WORKFLOW_KIT.md` — stable project constraints only when needed
5. `README.md` — public/setup context only when needed

Core rules:

- No broad discovery. Read primary target files first; fallback reads only if blocked.
- Smallest safe patch. No unrelated refactors.
- Update `docs/ai/HANDOFF.md` in the same PR for any implementation, bug fix, UI change, architecture change, migration, or workflow change.
- State Supabase SQL requirement in every PR summary.
- Stop after opening any Medium-High/High usage PR. Do not propose the next implementation prompt.

Project invariants:

- Google Places is canonical for addable places.
- Yelp/Foursquare are enrichment only.
- Editorial/web sources are evidence only.
- AI Concierge card fields must stay aligned: `display.displayWhy`, `supportingDetails.whyPick`, and top-level `whyPick`.
- No backend/API/business-logic changes during UI-only work.

Final response format:

```md
Root cause/plan:
Files changed:
Tests:
Risks:
Supabase SQL: Yes/No
HANDOFF.md edited: Yes/No + reason
README.md edited: Yes/No + reason
```
