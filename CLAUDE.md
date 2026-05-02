# Claude Instructions — Travel Concierge

Use this repo through a browser/mobile Claude + Codex workflow unless the user explicitly says CLI is available.

Before work, read only the smallest needed subset of:

1. `docs/ai/HANDOFF.md` — current state
2. `docs/ai/PROMPT_LIBRARY.md` — workflow, budget, prompt, UI, and review rules
3. `docs/ai/skills/README.md` — task-specific workflow skill router
4. `docs/ai/CLAUDE_PERSONAL_SKILLS.md` — optional personal Claude skill routing when a prompt names a personal skill
5. `docs/ai/DESIGN_VISION.md` — long-term aspirational UI direction and timing gate when doing major design work
6. `docs/ai/UI_BASELINE.md` — UI baseline and known visual costs when doing UI work
7. `docs/ai/CLAUDE_WORKFLOW_KIT.md` — stable project constraints only when needed
8. `README.md` — public/setup context only when needed

Use one primary workflow skill when it matches the task:

- `docs/ai/skills/discovery.md` — map unknown files or visual surfaces before implementation
- `docs/ai/skills/bugfix.md` — focused bug fix or small behavior correction
- `docs/ai/skills/ui_fix.md` — capped UI polish or visual consistency pass
- `docs/ai/skills/implementation.md` — focused multi-file feature implementation
- `docs/ai/skills/merge_gate.md` — cheap PR review before merge
- `docs/ai/skills/workflow_update.md` — workflow/documentation updates
- `docs/ai/skills/supabase_change.md` — any Supabase SQL, schema, RLS, auth, or persistence-contract change

Core rules:

- No broad discovery. Read primary target files first; fallback reads only if blocked.
- Smallest safe patch. No unrelated refactors.
- Use repo-local workflow skills instead of repeating large instruction blocks in prompts.
- Personal Claude skills are optional accelerators only; they do not replace repo rules, budget gates, or project invariants.
- Major design transformation must wait until `docs/ai/DESIGN_VISION.md` timing gate is satisfied; do small UI fixes only when needed before then.
- If a task needs three or more skill types, split it before implementation.
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
