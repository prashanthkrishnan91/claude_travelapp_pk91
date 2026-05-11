# Claude Instructions — Travel Concierge

Use this repo through a browser/mobile Claude + Codex workflow unless the user explicitly says CLI is available.

## Prompt Compression and Capability Slices (OS v4 consolidated)

This is the controlling rule for how prompts arrive in this repo and how Claude scopes work. It resolves the contradiction between earlier OS guidance ("short prompts, repeated process is repo-native") and an older prompt standard that implied every prompt must repeat every rule, every agent, every file, and every PR field.

A prompt to Claude must carry only the **task delta**:

- the specific task being requested
- chosen safety pack(s) and build archetype name(s) from `docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md`
- anchor files to read first
- acceptance evidence (what proves it is done)
- stop condition (when to stop instead of expanding)

A prompt **must not** paste:

- repeated OS rules from this file or `AI_REPO_OPERATING_SYSTEM.md`
- the PR summary template
- exhaustive lists of skills or reviewer agents
- generic project invariants
- generic "do not" lists
- exhaustive read-first file lists

The reusable safety packs and build archetypes own anything the prompt would otherwise repeat. The PR template owns PR fields. `AGENT_ROUTER.md` owns reviewer routing. `TEST_ROUTING.md` owns test tier choice.

### Capability slice over micro-patch

Default to one coherent **capability slice** per PR, not a string of micro-phases.

Split only for a real reason:

- contract is unclear and cannot be made clear inside one slice
- the task crosses unrelated skill areas
- a previous patch on the same area already failed (escalation)
- migration / runtime / SQL / manual-action risk
- provider / LLM behavior expansion
- large UI redesign across many surfaces
- the durable fix exceeds the current capability slice

Do **not** split simply because a task includes related tests, docs, contract, and code; if those belong to one coherent capability, ship one slice. Avoid endless Travel cleanup patches — group by pipeline seam (Concierge / Discover / Saved / Trip / provider) or product surface.

### Prompt-compression gate (hard)

Before a prompt is used:

- if the prompt is mostly repeated workflow / process language, it fails the gate and must be rewritten
- normal implementation prompts target **<700–1,200 words**, excluding logs/data that materially help
- any longer prompt must justify why the repeated context cannot be made repo-native

This gate applies to ChatGPT-generated prompts and to anything PK pastes into Claude.

## AI Repo Operating System v4 — what governs

OS v4 is the active operating system. It absorbs OS v2 (focused skills, advisory hooks, reviewer agents) and OS v3 (self-learning loop), and now consolidates prompt compression, safety packs, capability slices, batch-vs-split, and tiered tests. Do not introduce v4.2 or v5 labels — extend OS v4 in place.

For every non-trivial implementation, bug fix, UI change, provider/runtime change, migration, PR review, or workflow update:

1. Read `docs/ai/AI_REPO_OPERATING_SYSTEM.md` (consolidated OS v4).
2. Read `docs/ai/KNOWN_FAILURE_MODES.md`.
3. Pick the relevant **safety pack(s)** and **build archetype** from `docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md`.
4. Use the relevant focused skill(s) only — not all of them.
5. Use a reviewer agent only when the change touches its domain (see `docs/ai/AGENT_ROUTER.md`).
6. Use `docs/ai/TEST_ROUTING.md` as the **default test router**. Do not run the full backend suite for ordinary PRs.
7. Treat `.claude/hooks/ai_os_advisory.py` reminders as advisory.
8. Fill `.github/pull_request_template.md` honestly.
9. Stop and propose a split only when the durable fix genuinely exceeds the current capability slice (see criteria above).

## Self-learning loop

For Level 1+ PRs or any failed validation, run `.claude/skills/workflow-retrospective/SKILL.md` against `docs/ai/WORKFLOW_RETROSPECTIVE.md`. If a workflow miss occurred, recommend or add a concise entry to `docs/ai/MISS_LEDGER.md`. Do not promote one-off misses into broad rules — follow the promotion ladder in `docs/ai/OS_LEARNING_PROTOCOL.md`.

## Product Roadmap Control Plane

OS v4 routes product decisions before/around coding:

- `prompt-intake` to classify any meaningful task
- `roadmap-check` for implementation / product prompts
- `progress-report` when PK asks where we are
- `idea-triage` for idea dumps → `docs/product/IDEA_INBOX.md`
- `build-queue-update` after meaningful roadmap decisions or merged PRs
- `product-retrospective` after product-stage PRs

Every meaningful PR should state its roadmap stage and build queue item.

## Agent governance

Follow `docs/ai/AGENT_ROUTER.md`. Do not run every agent by default. Park new external agent ideas in `docs/ai/AGENT_INTAKE_REGISTRY.md`. Record reviewer-agent usefulness in `docs/ai/AGENT_EFFECTIVENESS_LEDGER.md` only when the signal is meaningful.

## Read-first anchors (smallest sufficient subset)

Read only what the task needs. Common anchors:

- `docs/ai/HANDOFF.md` — compact current state only (no historical PR log; replace/summarize, never append)
- `docs/ai/AI_REPO_OPERATING_SYSTEM.md` — consolidated OS v4
- `docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md` — reusable contracts the OS owns
- `docs/ai/KNOWN_FAILURE_MODES.md` — project-specific failure patterns
- `docs/ai/TEST_ROUTING.md` — default test router (Tier 0–3)
- `docs/ai/PROMPT_LIBRARY.md` — compact prompt templates
- `docs/ai/PROMPT_ENGINEERING_STANDARD.md` — compressed prompt structure
- `docs/ai/ISSUE_SEVERITY_ROUTING.md` — patch vs full-plumbing vs split
- `docs/ai/EXECUTION_PRINCIPLES.md` — surgical changes
- `docs/ai/ROOT_CAUSE_QUALITY_BAR.md` — root-cause quality bar
- `docs/ai/AGENT_ROUTER.md` — reviewer routing
- `.claude/skills/` — canonical Claude-native skills (each has SKILL.md)
- `docs/product/NORTH_STAR.md`, `docs/product/ROADMAP.md`, `docs/product/BUILD_QUEUE.md` — product control plane
- `docs/product/FEATURE_SLICE_CONTRACT.md`, `docs/product/GOLDEN_SCENARIOS.md` — Level 2+ feature work
- `docs/ai/TOOL_FAILURE_TAXONOMY.md` — when commands/tests/log checks fail

Useful command aliases (call only when relevant): `/test-selector`, `/contract-audit`, `/latency-gate`, `/claim-safety-gate`, `/pre-pr-self-audit`, `/pr-summary`, `/update-handoff`, `/workflow-retrospective`, `/miss-ledger-update`, `/prompt-intake`, `/roadmap-check`, `/idea-triage`, `/progress-report`, `/build-queue-update`.

## Core rules

- Default to one coherent capability slice; split only on the criteria above.
- Default test routing follows `docs/ai/TEST_ROUTING.md`. Every PR summary states **test tier used** and **why this tier was sufficient**. If the full suite is run, include the explicit reason; if skipped, list the targeted bundles/tests that replaced it.
- No broad discovery. Read primary target files first; fallback only if blocked.
- Classify severity using `ISSUE_SEVERITY_ROUTING.md` before choosing patch / full-plumbing / split.
- After one failed patch, reclassify. After two related patches, escalate to full plumbing analysis or split plan.
- On a tool/test/log failure, run `tool-failure-triage` and classify before patching. Do not patch app code for a tooling failure.
- When runtime evidence matters, use the `railway-logs` personal Claude skill if available (Railway errors, crashes, 4xx/5xx, provider failures, auth/cache/persistence mismatches, backend-vs-UI disagreement). Summarize only the relevant evidence.
- Smallest safe patch within the chosen capability slice. No unrelated refactors.
- For non-trivial work, state assumptions and success criteria before coding.
- Every changed line must trace to the task.
- Fix root causes, not symptoms.
- Use repo-local skills, safety packs, and archetypes instead of repeating large instruction blocks in prompts.
- Personal Claude skills are accelerators only; they do not replace repo rules, budget gates, or product invariants.
- Major design transformation must wait until `docs/ai/DESIGN_VISION.md` timing gate is satisfied.
- Update `docs/ai/HANDOFF.md` in the same PR for any implementation, bug fix, UI change, architecture change, migration, or workflow change. Update by **replacing or summarizing**, not appending. Keep the file under ~500 lines; if it would exceed that, compact first.
- State Supabase SQL requirement in every PR summary.
- Stop after opening any Medium-High/High usage PR. Do not propose the next implementation prompt.
- Every meaningful implementation PR must state its roadmap stage and build queue item from `docs/product/`.
- Do not run every reviewer agent by default; use `AGENT_ROUTER.md`.
- For Level 2/3 implementation, run `feature-contract` and `golden-scenarios` before coding.
- Important generated prompts run through `prompt-lint` / `prompt-quality-reviewer` before blind-copy.
- Coverage-first audits for review prompts.
- Every PR summary must include a compact AI usage note. Run `bash scripts/ai/usage_snapshot.sh` before opening a PR and paste the output line into the **AI usage note** field. Keep Level 1/2 PR summaries concise and do not invent long-form sections unless Level 3 or explicitly requested. See `docs/ai/AI_USAGE_TRACKING.md`.

## Project invariants

Travel-specific safety lives in named packs in `docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md` (Travel section): Google Places Addable Authority Pack, Enrichment Evidence Only Pack, Semantic Concierge Behavior Pack, AI Concierge Card Contract Pack, No Mock/Sample Visible Data Pack, Latency Budget Pack. Prompts should reference the pack name; they should not re-list the rules.

The PR template owns required PR fields. Final response format remains as defined by `pr-summary` and `.github/pull_request_template.md`.
