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
- `<examples>` — only when they reduce ambiguity.

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

## Coverage-first review prompts

For audits / reviews:

- First pass: list every plausible issue, even low confidence.
- Second pass: classify severity and confidence.
- Final pass: decide blockers vs non-blockers.

Do not ask reviewers to report only blockers at the start.

## Ask / Plan before Code

For Level 2/3 features, produce or verify the feature contract and capability-slice plan first. Then code the coherent slice. If the contract is unclear, stop and propose the split.

## Travel-specific prompt note

When a slice touches addable cards, enrichment, semantic Concierge behavior, AI Concierge card fields, mock/sample data, or latency, name the relevant safety pack(s) from `docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md` (Travel section). The pack owns the rules — the prompt does not need to re-state them.

## Required usage footer for non-trivial prompts

Add this block verbatim at the end of any non-trivial Travel implementation prompt:

```
Usage ledger: If tooling exists, save a baseline before work; before opening/updating the PR, append one sanitized row to docs/ai/USAGE_LEDGER.md with the actual PR number if available, prompt ID, phase, model, chat strategy, repo area, main drivers, waste classification, follow-up count, and delta fields when available. If tooling is unavailable, still append a manual row with those metadata fields and mark token/delta fields unavailable. Do not claim usage is tracked unless docs/ai/USAGE_LEDGER.md is actually changed in the PR. Keep raw .ai/usage files uncommitted.

Usage discipline: Keep discovery narrow; do not run broad repo scans, parallel agents, or full suites unless focused validation fails or this prompt explicitly asks for them.
```
