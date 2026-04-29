# Claude Workflow Kit — Travel Concierge

Purpose: make Claude browser/mobile usage dramatically cheaper by giving Claude stable, current, reusable context instead of re-explaining the project in every chat.

This file is designed to be uploaded to the **Travel Concierge Claude Project knowledge** and kept in the repo as the source of truth.

## Core rule

Do not use Claude as a repo explorer. Use Claude as an implementer that receives a compact state pack.

Your expensive Claude usage is usually caused by:

1. repeated project background in every prompt,
2. asking Claude to rediscover state from the whole repo,
3. stale `.claude`/automation files competing with current app reality,
4. large multi-turn Sonnet/Opus chats,
5. browser/mobile workflow using CLI-oriented Claude Code hooks that do not actually run in your workflow.

## Correct model routing

| Task | Tool/model | Chat strategy |
|---|---|---|
| Small bug fix with clear evidence | Codex | New chat per PR/branch |
| Focused implementation touching 1–5 files | Claude Sonnet | New Claude Project chat |
| Large feature architecture / roadmap | Claude Opus | One planning chat only, produce compact spec, then stop |
| Review PR summary before merge | ChatGPT or Codex | Same review thread if short; new chat if previous chat is bloated |
| Prompt compression / handoff | ChatGPT | Same project chat |
| UI copy / summarization | Haiku if available, otherwise ChatGPT | New short chat only if needed |

Default: use **Sonnet**, not Opus. Opus is for reusable planning artifacts, not iterative coding on Pro.

## Claude Project instructions

Paste this into the Travel Concierge Claude Project instructions:

```md
You are working on my Travel Concierge app. Be aggressively token-efficient.

Use the repo knowledge files first. Do not restate project background unless it changed.
Use only the hot surfaces and state pack I provide unless the task truly requires broader inspection.
Prefer structured JSON evidence from debug endpoints over screenshots or broad repo exploration.

Return in this order:
1. Root cause or implementation plan
2. Exact files to change
3. Minimal patch outline
4. Tests/checks to run
5. Risks / rollback notes

Do not add unrelated refactors. Do not redesign unrelated areas. Do not introduce new framework patterns unless necessary.
When implementing, update docs/ai/HANDOFF.md and README.md only if the PR changes user-visible behavior, architecture, setup, or debugging workflow.
```

## Canonical stack

- Frontend: Next.js 15.3.8, React 19, TypeScript, Tailwind 4, GSAP, @dnd-kit.
- Backend: FastAPI Python middleware.
- Database/Auth: Supabase.
- Frontend hosting: Vercel.
- Backend hosting: Railway.
- Source directories:
  - Frontend: `frontend/`
  - Backend: `backend/`
  - Frontend concierge tests: `frontend/tests/concierge-renderers.test.mjs`
  - Backend tests: `backend/tests/`

## Current hot surfaces

Use these first before broad repo reading.

### AI Concierge / live research

- `backend/app/routes/ai.py` — debug trace and AI-facing diagnostics.
- `backend/app/services/live_research.py` — live provider pipeline, Google gate, evidence intake.
- `backend/app/services/concierge.py` — service orchestration and response sanitization.
- `backend/app/concierge/evidence.py` — structured evidence normalization.
- `backend/app/concierge/whypick_prompt.py` — why-pick LLM prompt/validation if present.
- `backend/app/concierge/reasoning.py` — deterministic/LLM why-pick orchestration.
- `frontend/src/components/trips/AIConciergePanel.tsx` — main concierge UI/cards.
- `frontend/tests/concierge-renderers.test.mjs` — frontend renderer regression tests.

### Trip creation / itinerary

- `frontend/src/components/trips/`
- `frontend/src/app/`
- `backend/app/routes/`
- `backend/app/services/`

## Debug state pack rule

For AI Concierge bugs, do not paste the whole repo story. Paste:

1. user query,
2. city/destination,
3. expected result,
4. actual result,
5. debug trace JSON from `/ai/concierge/debug-trace`,
6. one screenshot only if the rendered UI is the problem.

## Browser/mobile prompt shell

Use this stable shell for Sonnet/Codex. Keeping the shell stable improves reuse and reduces repeated thinking.

```md
Repo: prashanthkrishnan91/claude_travelapp_pk91
Mode: focused implementation
Model: Sonnet for feature/fix, Codex for small bug/audit
Chat: new chat

Task:
[one paragraph]

Expected behavior:
[one paragraph]

Actual behavior:
[one paragraph]

State pack:
[paste compact JSON/logs/screenshot notes]

Relevant hot surfaces:
- [file]
- [file]
- [file]

Constraints:
- Smallest safe patch.
- Do not refactor unrelated systems.
- Preserve Google Places as canonical source of truth for addable places.
- Editorial/blog/social sources are evidence-only, never addable.
- Yelp/Foursquare are enrichment-only.
- Addable cards must stay clean: title, category/subtitle, compact meta, one-line why, More/Less details.
- Update docs/ai/HANDOFF.md and README.md only if behavior/setup changes.

Deliverables:
1. Root cause / plan
2. Files changed
3. Tests run
4. PR summary with Supabase SQL required / not required
```

## Acceptance criteria for concierge work

- Google Places remains canonical for existence, operational status, and addability.
- Only operational Google-matched places are addable.
- Editorial/listicle/social sources never become addable cards.
- Card metadata does not expose debug fields such as evidence counts, source checked text, internal provider scores, or raw source snippets.
- Why-pick text is one polished sentence, venue-specific, and not a generic template unless deterministic fallback is explicitly expected.
- Expanded card details contain rating/address/source detail without duplicating the visible summary.
- Tests cover the exact card rendering and at least one representative backend case.

## Hooks, skills, agents, orchestration recommendation

For your current browser/mobile-only workflow, do **not** invest in new CLI hooks, claude-flow swarms, or multi-agent terminal orchestration. They are real Claude Code features, but they only pay off when you run Claude Code in a terminal/CLI environment.

The useful equivalent for you is repo-side reusable documentation plus debug endpoints:

- Claude Project knowledge = stable memory/cache.
- `docs/ai/HANDOFF.md` = continuity between short chats.
- debug trace endpoint = compact evidence pack.
- stable prompt shell = less repeated prompt overhead.
- Codex = smaller surgical patches and PR audits.
- Sonnet = implementation.
- Opus = occasional spec only.

## Weekly maintenance checklist

After every meaningful PR:

1. Update `docs/ai/HANDOFF.md` with what changed, why, files touched, tests, and next likely task.
2. Update README only if user-visible behavior, setup, migrations, or architecture changed.
3. Remove stale claims from old `.claude` docs if they conflict with current stack.
4. Start the next Claude implementation in a new chat using the browser/mobile prompt shell.
