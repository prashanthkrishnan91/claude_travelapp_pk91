# Claude Instructions — Travel Concierge

## Operating mode

Browser/mobile Claude + Codex workflow. No CLI-only hooks, swarms, background agents, or local terminal assumptions unless user explicitly says CLI is available.

Primary objective: every Claude/Codex token must move the fix forward. No filler, no broad repo exploration, no speculative rewrites.

## Required memory files

Before planning or coding, use the smallest needed subset of:

1. `docs/ai/HANDOFF.md` — current state and next likely task
2. `docs/ai/PROMPT_LIBRARY.md` — prompt/task shape
3. `docs/ai/CLAUDE_WORKFLOW_KIT.md` — stable project rules
4. `README.md` — only for public/setup/user-facing context

Do not restate these files. Use them.

## Project stack

- Frontend: Next.js 15, React 19, TypeScript, Tailwind 4
- Backend: FastAPI
- Database/Auth: Supabase
- Hosting: Vercel frontend, Railway backend

## Zero-waste work rules

- Every sentence in the response must be useful for diagnosis, implementation, verification, or merge decision.
- Do only the requested task.
- Read only the hot files required for the task.
- Do not scan the whole repo unless the task is impossible without it.
- Prefer smallest safe patch.
- Do not refactor unrelated code.
- Do not repeat known architecture unless it affects the fix.
- Never expose secrets or `.env` contents.
- Always state whether Supabase SQL is required.
- Update `README.md` only when user-visible behavior, setup, migration, or architecture changes.

## Mandatory handoff automation

For every implementation, bug fix, refactor, UI change, migration, architecture change, workflow change, or prompt-system change, edit `docs/ai/HANDOFF.md` in the same PR/commit. This is a required deliverable.

The task is incomplete if `docs/ai/HANDOFF.md` should change and was not edited.

`docs/ai/HANDOFF.md` must include:

- Last change
- Files touched
- Behavior change
- Known issues
- Next likely task
- Debug notes

Never ask the user to update HANDOFF manually. Update it yourself.

## Required final response

Use this exact compact format:

```md
Root cause/plan:
Files changed:
Tests:
Risks:
Supabase SQL: Yes/No
HANDOFF.md edited: Yes/No + reason
README.md edited: Yes/No + reason
```

## AI Concierge invariants

- Google Places is canonical for existence, operational status, address, rating, review count, and addability.
- Yelp and Foursquare are enrichment only.
- Tavily/editorial/social sources are evidence only.
- Only Google-verified operational places are addable.
- User-facing cards: title, category/subtitle, compact meta, one-line why, collapsed More/Less details.
- `display.displayWhy`, `supportingDetails.whyPick`, and top-level `whyPick` must stay aligned.
- No debug metadata, provider internals, source leakage, or raw snippets in user-facing card copy.

## Chat strategy

- Codex: bug fixes, audits, smaller implementation.
- Sonnet: focused implementation.
- Opus: planning only; produce compact spec, then stop.
- New feature/fix: new chat.
