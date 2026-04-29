# Claude Instructions — Travel Concierge

## Operating mode

This repo is developed through Claude/Codex in browser or mobile app. Do not assume CLI-only hooks, background agents, swarms, or local terminal orchestration are available unless the user explicitly says they are using CLI.

Primary objective: preserve Claude Pro usage by using repo memory files and compact state packs instead of rediscovering the app.

## Required memory files

Before planning or coding, use these files as the current source of truth:

1. `docs/ai/CLAUDE_WORKFLOW_KIT.md`
2. `docs/ai/HANDOFF.md`
3. `docs/ai/PROMPT_LIBRARY.md`
4. `README.md` only when setup/user-facing behavior is relevant

Do not ignore these files. If the user gives a prompt that conflicts with them, point out the conflict briefly and follow the newest explicit user instruction.

## Project stack

- Frontend: Next.js 15, React 19, TypeScript, Tailwind 4
- Backend: FastAPI
- Database/Auth: Supabase
- Hosting: Vercel frontend, Railway backend

## Work rules

- Do only the requested task.
- Prefer smallest safe patch.
- Read only hot files relevant to the task.
- Do not scan the whole repo unless necessary.
- Do not add unrelated refactors.
- Never expose secrets or `.env` contents.
- Always state whether Supabase SQL is required.
- Update `docs/ai/HANDOFF.md` after meaningful code changes.
- Update `README.md` only when user-visible behavior, setup, migration, or architecture changes.

## Response format

Use this order:

1. Root cause or plan
2. Files changed / files to change
3. Tests/checks run or required
4. Risks / rollback notes
5. Supabase SQL required: Yes/No
6. Handoff update needed: Yes/No

## AI Concierge invariants

- Google Places is canonical for existence, operational status, address, rating, review count, and addability.
- Yelp and Foursquare are enrichment only.
- Tavily/editorial/social sources are evidence only.
- Only Google-verified operational places are addable.
- User-facing cards must stay clean: title, category/subtitle, compact meta, one-line why, collapsed More/Less details.
- `display.displayWhy`, `supportingDetails.whyPick`, and top-level `whyPick` must stay aligned.
- No debug metadata, provider internals, source leakage, or raw snippets in user-facing card copy.

## Chat strategy

- New feature/fix: new Claude/Codex chat.
- PR review: use Codex or ChatGPT unless implementation reasoning is needed.
- Opus: planning only, produce compact spec, then stop.
- Sonnet: focused implementation.
- Codex: bug fixes, audits, smaller implementation.
