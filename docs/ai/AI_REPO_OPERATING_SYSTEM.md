# AI Repo Operating System — Travel Concierge (OS v4 consolidated)

This repo uses an AI Repo Operating System so ChatGPT can give Claude short task briefs while Claude performs the repeated engineering workflow automatically.

## Goal
Turn Claude from a prompt executor into a repo-aware engineering partner that plans, audits, tests, delegates independent review, summarizes, learns from misses, and stops at the right boundary — by carrying only the task delta in prompts and pulling repeated process from the repo.

## Default human/agent loop

1. PK states product goal, issue, screenshot, logs, or validation result.
2. ChatGPT chooses severity, model, scope, the relevant **safety pack(s)** and **build archetype**, and gives Claude a short task brief in OS v4 work-order format.
3. Claude reads `CLAUDE.md`, this OS, and only the smallest relevant supporting docs.
4. Claude runs the relevant focused skill(s) and reviewer agent(s) for the changed domain — not all of them.
5. Claude builds one coherent **capability slice** per PR, runs the appropriate **test tier** from `docs/ai/TEST_ROUTING.md`, self-audits, updates handoff, and uses the PR template.
6. ChatGPT reviews the actual PR diff and evidence.
7. Codex is used for surgical blockers, merge-gate exceptions, or targeted audits.
8. PK does UI/runtime validation only when product-visible behavior or deployment state requires it.
9. After meaningful PRs or failed validation, Claude runs the workflow retrospective and recommends MISS_LEDGER / promotion updates if any.

## OS v4 — Prompt Compression and Capability Slice Control (consolidation)

This is the consolidation that resolves the prompt-bloat / micro-phasing miss. It is part of OS v4. Do **not** introduce a v4.2 or v5 label.

### Default prompt shape

Every prompt to Claude is a work order in this shape:

```
<task_delta>
The specific change. Two to six lines.
</task_delta>

<safety_packs>
Named packs from docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md. The packs own their rules; do not paste them.
</safety_packs>

<build_archetype>
One archetype name from docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md.
</build_archetype>

<anchor_files>
Files Claude must read first. Keep small.
</anchor_files>

<acceptance_evidence>
The exact evidence that proves the slice is done.
</acceptance_evidence>

<stop_condition>
When to stop instead of expanding scope.
</stop_condition>
```

Optional sections only when they materially help: `<logs>`, `<runtime_evidence>`, `<ui_budget>`, `<sql_manual_actions>`, `<examples>`.

### What belongs in the prompt vs repo-native

- **In the prompt:** task delta, named safety pack(s), build archetype, anchor files, acceptance evidence, stop condition.
- **Repo-native (do not paste into the prompt):** OS rules, skills list, reviewer agents list, generic project invariants, generic "do not" lists, PR summary fields, exhaustive read-first lists, severity ladder, learning protocol, product roadmap control plane.

The safety packs in `docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md` own anything that would otherwise be repeated.

### Batch-vs-split decision gate

Batch into one capability slice when:

- the work is one coherent capability or pipeline seam (Concierge / Discover / Saved / Trip / provider)
- it shares the same contract / invariant set
- it shares the same test evidence
- there is no unrelated migration / runtime / UI / provider expansion
- batching reduces rework and repeated validation

Split when:

- the contract is unclear inside the current slice
- the work crosses unrelated skill areas
- this is the second patch on the same area after a previous failure
- there is SQL / runtime / manual-action risk
- it expands provider / LLM behavior
- it is a large UI redesign across many surfaces
- the durable fix exceeds the current capability slice

Do **not** split simply because the slice contains related code, contract, tests, and docs; those belong together.

### Meaningful progress standard

- Prefer capability slices that visibly or architecturally advance the roadmap.
- Avoid six micro-phases when one guarded backend slice is safe.
- Avoid endless Travel cleanup patches; group by pipeline seam or product surface (Concierge cards, Discover, Saved, Trip Builder, provider).
- A coherent backend-only scaffold (disabled, gated) is meaningful progress; do not avoid it because it is not user-visible.

### Test tier hierarchy

Use the smallest sufficient tier per `docs/ai/TEST_ROUTING.md`:

- **Tier 0:** changed-file adjacent (default, includes pure helpers).
- **Tier 1:** product contract / regression bundle (AI Concierge card contract, Flights/Hotels provider, mock/fail-closed safety, OptimizeTripModal fail-closed, TripBuilder add-to-trip).
- **Tier 2:** broader smoke at milestone or shared-route boundaries.
- **Tier 3:** full backend suite (`pytest tests/`) only for release checkpoints, shared infrastructure, test infrastructure, broad model/schema risk, suspicious failures, or explicit merge-gate request.

Runtime validation is required only when deployment or user-visible behavior changes.

Every PR summary must state **test tier used**, **why it was sufficient**, and whether the full suite was skipped or run with explicit reason.

## What OS v4 already absorbed

OS v4 is the only operating system label. It absorbs:

- **OS v2:** focused skills under `.claude/skills/*/SKILL.md`, advisory hooks, read-only reviewer agents.
- **OS v3:** workflow retrospective, MISS_LEDGER, promotion ladder.
- **Product Roadmap Control Plane:** north star, roadmap, build queue, idea inbox, release gates, progress report, product retrospective.
- **Prompt Engineering Control Layer:** standard, library, prompt-lint, feature-contract, golden-scenarios, tool-failure-triage.
- **Consolidation (this section):** prompt compression, safety packs and archetypes, capability slices, batch-vs-split gate, test tier hierarchy.

There is no v4.2 or v5. Future improvements extend OS v4 in place.

## Required sequence for non-trivial tasks

Before coding:

1. `prompt-intake` to classify the task and confirm safety pack + archetype.
2. Severity via `docs/ai/ISSUE_SEVERITY_ROUTING.md`.
3. `roadmap-check` if implementation or product-direction work.
4. For Level 2/3 features: `feature-contract` + `golden-scenarios`.
5. `task-planner`.
6. Identify changed contracts and likely downstream consumers.
7. Pick test tier from `docs/ai/TEST_ROUTING.md`.
8. Read `docs/ai/KNOWN_FAILURE_MODES.md`.

Before PR summary for Level 1+:

1. `contract-audit`.
2. `runtime-gate` / `latency-gate` if runtime/provider/LLM/db behavior changed.
3. `claim-safety-gate` if user-visible text/data/actions/evidence changed.
4. Reviewer agents per `AGENT_ROUTER.md`. For Level 2+ features include `eval-scenario-reviewer`.
5. `pre-pr-self-audit`.
6. `pr-summary` → fill `.github/pull_request_template.md` honestly. State test tier and reason. State whether workflow + product retrospectives are needed.

When something fails: `tool-failure-triage` before patching.

After PR summary or failed validation:

- `workflow-retrospective` if the PR is meaningful or validation failed.
- `product-retrospective` if it was product-stage work.
- `miss-ledger-update` only if a workflow/product-process miss occurred.
- `build-queue-update` only if the queue meaningfully moved.

## Reviewer delegation guide

Use reviewer agents for independent evidence, not code edits. Route via `docs/ai/AGENT_ROUTER.md`. Prefer fewer high-signal reviewers over many generic ones. Reviewer agents must not bloat builder context.

## Advisory hooks

Hooks are reminders only:

- provider/runtime edits remind `/latency-gate`
- evidence/prose edits remind `/claim-safety-gate`
- UI/client contract edits remind `/contract-audit`
- SQL/env/settings edits remind manual action fields
- Stop reminds `/pre-pr-self-audit` and `/pr-summary`

## What belongs in the task prompt

Keep prompts compressed. Use the work-order shape above. The prompt names safety packs and the build archetype; the OS owns the rest.

Do not paste full coding principles, repo invariants, test rules, or PR format. They live here and in the safety packs.

## What must stay repo-native

- Coding principles: `docs/ai/EXECUTION_PRINCIPLES.md`
- Severity routing: `docs/ai/ISSUE_SEVERITY_ROUTING.md`
- Known failures: `docs/ai/KNOWN_FAILURE_MODES.md`
- Test routing: `docs/ai/TEST_ROUTING.md` (default test router)
- Definition of done: `docs/ai/DEFINITION_OF_DONE.md`
- Failure recovery: `docs/ai/FAILURE_RECOVERY.md`
- Runtime evidence: `docs/ai/RUNTIME_EVIDENCE.md`
- Manual actions: `docs/ai/MANUAL_ACTIONS_CHECKLIST.md`
- Learning protocol: `docs/ai/OS_LEARNING_PROTOCOL.md`
- Miss ledger: `docs/ai/MISS_LEDGER.md`
- Workflow retrospective: `docs/ai/WORKFLOW_RETROSPECTIVE.md`
- Agent router: `docs/ai/AGENT_ROUTER.md`
- Agent intake registry: `docs/ai/AGENT_INTAKE_REGISTRY.md`
- Agent effectiveness ledger: `docs/ai/AGENT_EFFECTIVENESS_LEDGER.md`
- Prompt engineering standard: `docs/ai/PROMPT_ENGINEERING_STANDARD.md`
- Tool failure taxonomy: `docs/ai/TOOL_FAILURE_TAXONOMY.md`
- Safety packs and build archetypes: `docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md`
- Product OS: `docs/product/*`

## Travel-specific invariants (owned by safety packs)

These are enforced via named packs in `docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md` (Travel section). Prompts reference the pack name and do **not** re-list the rules.

- Google Places Addable Authority Pack: Google Places is canonical for addable cards.
- Enrichment Evidence Only Pack: Yelp / Foursquare / editorial sources are enrichment / evidence only — they cannot mint addable cards.
- Semantic Concierge Behavior Pack: no keyword patching as a substitute for semantic behavior.
- AI Concierge Card Contract Pack: card fields aligned (`display.displayWhy`, `supportingDetails.whyPick`, top-level `whyPick`).
- No Mock/Sample Visible Data Pack: no mock / sample / prototype / unsupported visible claims; no visible deterministic fallback notes.
- Latency Budget Pack: total request-path latency matters more than local provider timeout.

## Stop rules

Stop and ask for a split if:

- The fix touches three or more **unrelated** skill areas.
- A second related patch on the same area would be needed.
- Durable architecture exceeds the stated scope.
- Required runtime evidence is unavailable.
- The implementation would violate a product invariant (named safety pack).
- The PR has no clear roadmap stage or build queue item, and is not a justified blocker.
- The Feature Slice Contract is unclear and cannot be made clear within the current slice.

Do not split a coherent capability slice merely because it includes related tests, docs, or contract work.
