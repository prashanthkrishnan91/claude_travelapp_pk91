# Prompt Engineering Standard — Travel (compressed)

## Core principle

A good prompt is a **work order carrying only the task-specific delta**. Repeated rules, agents, files, invariants, and PR fields are repo-native — they live in `CLAUDE.md`, `AI_REPO_OPERATING_SYSTEM.md`, `SAFETY_PACKS_AND_ARCHETYPES.md`, `AGENT_ROUTER.md`, `TEST_ROUTING.md`, and the PR template. The prompt should not paste them.

This standard replaces the older "a good prompt contains everything" structure that asked every prompt to repeat task type, roadmap stage, source files, contract, success criteria, golden scenarios, scope boundaries, required OS skills, required reviewer agents, validation expectations, tool-failure behavior, PR summary requirements, and stop condition. That structure caused prompt bloat and tiny micro-PRs.

## Required default sections

```
<task_delta>
The specific change. Two to six lines. State what changes and why now.
</task_delta>

<repo_context>
One or two lines naming roadmap stage / build queue item, or pointing at the source-of-truth doc. Do not restate the roadmap.
</repo_context>

<safety_packs>
Named packs from docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md. The packs own their rules; do not paste them.
</safety_packs>

<build_archetype>
One archetype name from docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md.
</build_archetype>

<acceptance_evidence>
The exact evidence that proves the slice is done (test bundle name from TEST_ROUTING.md, runtime check, snapshot field, screenshot, Concierge card field).
</acceptance_evidence>

<stop_condition>
When to stop instead of expanding scope.
</stop_condition>
```

## Optional sections (only when they materially help)

- `<logs>` — relevant excerpt only.
- `<runtime_evidence>` — Railway / provider / cache / route evidence.
- `<ui_budget>` — phase, max files, primary surfaces, forbidden surfaces (only for UI work).
- `<sql_manual_actions>` — when SQL or manual deploy/Supabase actions are required.
- `<examples>` — only when they reduce ambiguity (expected JSON shape, accepted/rejected claim example, before/after card behavior).

## What this standard explicitly removes

A prompt is **not required** to include and should usually omit:

- the full PR summary fields (PR template owns them)
- exhaustive lists of OS skills (CLAUDE.md / OS doc own them)
- exhaustive lists of reviewer agents (AGENT_ROUTER.md owns them)
- generic project invariants (safety packs own them)
- generic "do not" lists (safety packs own them)
- exhaustive read-first file lists (read anchors only)
- severity ladder explanation (ISSUE_SEVERITY_ROUTING.md owns it)
- learning protocol prose (OS_LEARNING_PROTOCOL.md owns it)

If any of those genuinely apply to the slice, name the relevant doc — do not paste it.

## Safe for blind copy/paste — redefined

A prompt is safe for blind copy/paste when it is:

- **concise** — within the compression budget below
- **unambiguous** — one objective, named acceptance evidence, named stop condition
- **repo-native** — references safety packs, archetypes, and routing docs by name instead of repeating them
- **boilerplate-free** — no repeated workflow/process language
- **specific** — anchor files and acceptance evidence are exact

## Compression budget

- Normal implementation prompts: **<700–1,200 words**, excluding logs/data that materially help.
- A longer prompt must justify why the repeated context cannot be moved into a safety pack, archetype, or repo-native doc.
- A prompt that is mostly repeated workflow/process language **fails the gate** and must be rewritten.

## Examples

### Bad (bloated) prompt pattern

```
Repo: <repo>
Roadmap stage: <stage>
Build queue item: <item>
Source-of-truth files: <12 files>
[full feature contract template]
[full success criteria template]
[full golden scenarios block]
[paste of all OS skills]
[paste of all reviewer agents]
[paste of all repo invariants — Google Places canonical, enrichment-only providers, no keyword patching, AI Concierge card fields, no mock/sample data, latency rules ...]
[paste of all do-nots — no fabricated cards, no fake notes, no deterministic fallback notes ...]
[paste of full PR summary template]
[paste of full tool-failure taxonomy]
[paste of full validation expectations]
```

Result: ~3,000 words, prompt is mostly repeated rules, Claude over-guards and produces a tiny patch.

### Good (compressed) prompt pattern

```
<task_delta>
Fix Concierge card whyPick alignment so display.displayWhy, supportingDetails.whyPick, and top-level whyPick stay in sync after enrichment merge. Backend-only.
</task_delta>

<repo_context>
Roadmap: Stage 2 / build queue: "concierge whyPick alignment". See docs/product/BUILD_QUEUE.md.
</repo_context>

<safety_packs>
AI Concierge Card Contract Pack, Enrichment Evidence Only Pack, No Mock/Sample Visible Data Pack, Test Tier Pack.
</safety_packs>

<build_archetype>
capability-slice
</build_archetype>

<acceptance_evidence>
Tier 1 AI Concierge card contract bundle green (backend + frontend). Snapshot shows aligned fields. No visible UI copy change.
</acceptance_evidence>

<stop_condition>
Do not change addable-card source authority. Do not introduce a new provider. If alignment requires schema change, stop and propose a contract-consolidation slice.
</stop_condition>
```

Result: ~170 words, every line carries the task delta, packs and archetype carry the rest.

### When a longer prompt is justified

- A Sev 1 runtime bug that requires Railway log excerpts and provider response evidence inline.
- A migration with manual-action steps that must be inline in the prompt.
- A first-time pipeline seam where the contract must be sketched in the prompt because no contract doc exists yet.

In these cases the **extra** content is data/evidence, not repeated workflow rules.

## Coverage-first review prompts

For audits / reviews:

- First pass: list every plausible issue, even low confidence.
- Second pass: classify severity and confidence.
- Final pass: decide blockers vs non-blockers.

Do not ask reviewers to report only blockers at the start.

## Ask / Plan before Code

For Level 2/3 features, produce or verify the feature contract and capability-slice plan first. Then code the coherent slice. If the contract is unclear, stop and propose the split.

## Travel-specific prompt note

When a slice touches addable cards, enrichment, semantic Concierge behavior, AI Concierge card fields, mock/sample data, or latency, name the relevant safety pack(s) from `docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md` (Travel section). The pack owns the rules — the prompt does not need to re-state "Google Places canonical", "Yelp/Foursquare enrichment only", "no keyword patching", "card fields aligned", "no visible mock/sample", or "latency budget matters".
