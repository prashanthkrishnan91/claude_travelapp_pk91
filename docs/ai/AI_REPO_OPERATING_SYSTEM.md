# AI Repo Operating System — Travel Concierge

This repo uses an AI Repo Operating System so ChatGPT can give Claude short task briefs while Claude performs the repeated engineering workflow automatically.

## Goal
Turn Claude from a prompt executor into a repo-aware engineering partner that plans, audits, tests, delegates independent review, summarizes, learns from misses, and stops at the right boundary.

## Default human/agent loop

1. PK states product goal, issue, screenshot, logs, or validation result.
2. ChatGPT chooses severity, model, scope, and gives Claude a short task brief in OS v2/v3/v4 work-order format.
3. Claude reads `CLAUDE.md`, this OS, and only the smallest relevant supporting docs.
4. Claude runs the relevant focused skills or commands before coding.
5. Claude builds one focused PR, runs tests, delegates read-only review to applicable reviewer agents, self-audits, updates handoff only when meaningful, and uses the PR template.
6. ChatGPT reviews the actual PR diff and evidence.
7. Codex is used only for surgical blockers, merge-gate exceptions, or targeted audits.
8. PK does UI/runtime validation only when the product-visible behavior requires it.
9. After meaningful PRs or failed validation, Claude runs the workflow retrospective and recommends MISS_LEDGER/promotion updates if any.

## OS v2 upgrades

OS v2 adds three automation layers on top of v1:

1. **Focused skills** under `.claude/skills/*/SKILL.md` so Claude can invoke smaller task-specific routines instead of skimming one broad checklist.
2. **Advisory hooks** through `.claude/settings.json` + `.claude/hooks/ai_os_advisory.py`. These only print reminders and exit successfully; they do not block tools or change app behavior.
3. **Read-only reviewer agents** under `.claude/agents/*.md` so Claude can delegate independent contract, test, latency, place-authority, and evidence/prose review before PR summary.

## OS v3 upgrades

OS v3 adds a self-learning workflow loop on top of OS v2.

- After meaningful PRs, run the workflow retrospective via `.claude/skills/workflow-retrospective/SKILL.md` and `docs/ai/WORKFLOW_RETROSPECTIVE.md`.
- After misses, record entries in `docs/ai/MISS_LEDGER.md` via `.claude/skills/miss-ledger-update/SKILL.md`.
- Promote lessons to `KNOWN_FAILURE_MODES`, `TEST_SELECTOR`, `PR_REVIEW_CHECKLIST`, `FAILURE_RECOVERY`, `PROMPT_BRIEF_TEMPLATE`, hooks, reviewer agents, or `CLAUDE.md` only when repeated or severe — see the promotion ladder in `docs/ai/OS_LEARNING_PROTOCOL.md`.
- Claude must not bloat the OS after one isolated miss.
- ChatGPT still owns final workflow architecture judgment.

## OS v4 upgrades — Product Roadmap Control Plane and Agent Governance

OS v4 adds a Product Roadmap Control Plane and reviewer-agent governance on top of OS v3. OS v3 decides how Claude works; Product OS decides what to build next and why.

- Every meaningful implementation PR should map to:
  - the product north star (`docs/product/NORTH_STAR.md`)
  - a roadmap stage (`docs/product/ROADMAP.md`)
  - a build queue item (`docs/product/BUILD_QUEUE.md`)
  - a release gate or validation need (`docs/product/RELEASE_GATES.md`) when applicable
- Ideas go to `docs/product/IDEA_INBOX.md` instead of hijacking active work.
- Progress reports use `docs/product/PROGRESS_REPORT_TEMPLATE.md` and the `progress-report` skill.
- The `roadmap-guardian` reviewer agent checks direction and scope creep.
- The `agent-curator` reviewer evaluates external agent libraries without importing wholesale.
- `docs/ai/AGENT_ROUTER.md` prevents all-agent default behavior.
- `docs/ai/AGENT_INTAKE_REGISTRY.md` parks future external agent patterns.
- `docs/ai/AGENT_EFFECTIVENESS_LEDGER.md` prevents reviewer bloat.
- A small Certification Agent Pack (`reality-checker`, `evidence-collector`, `premium-delight-reviewer`, `accessibility-reviewer`, `performance-benchmarker`) is available; route via `AGENT_ROUTER`, do not run by default.

Default OS v4 routing for incoming tasks:

- "Where are we?" → `progress-report` skill.
- "What next?" → `roadmap-check` skill + `BUILD_QUEUE`.
- Idea dump → `idea-triage` skill → `IDEA_INBOX`.
- Implementation / bug fix / product change → `prompt-intake` then `roadmap-check`.
- Workflow / product roadmap update → `prompt-intake` then `build-queue-update` if queue moves.

## Required sequence for non-trivial tasks

Before coding:

1. Run or apply `prompt-intake` (OS v4) to classify the task.
2. Classify severity using `docs/ai/ISSUE_SEVERITY_ROUTING.md`.
3. Run or apply `roadmap-check` if the task is implementation or product-direction work.
4. Run or apply `task-planner`.
5. Identify changed contracts and likely downstream consumers.
6. Run or apply `test-selector`.
7. Read `docs/ai/KNOWN_FAILURE_MODES.md` for this repo.

Before PR summary for Level 1+:

1. Run or apply `contract-audit`.
2. Run or apply `runtime-gate` / `latency-gate` if runtime/provider/LLM/db behavior changed.
3. Run or apply `claim-safety-gate` if user-visible text/data/actions/evidence changed.
4. Delegate to applicable read-only reviewer agents per `docs/ai/AGENT_ROUTER.md`.
5. Run or apply `pre-pr-self-audit`.
6. Fill `.github/pull_request_template.md` honestly through `pr-summary`. Include whether a workflow retrospective and a product retrospective are needed.

After PR summary or failed validation:

- Run `workflow-retrospective` if the PR is meaningful or validation failed.
- Run `product-retrospective` if the PR was product-stage work.
- Use `miss-ledger-update` only if a workflow/product-process miss occurred.
- Use `build-queue-update` only if the queue meaningfully moved.

## Reviewer delegation guide

Use reviewer agents for independent evidence, not code edits. Route via `docs/ai/AGENT_ROUTER.md`. Do not run every agent by default.

Common defaults:

- `roadmap-guardian`: product direction and scope creep.
- `contract-auditor`: changed contracts, consumers, missed connected files.
- `test-strategist`: smallest sufficient tests and adversarial invariant coverage.
- `pr-reviewer`: final PR evidence vs checklist.
- `place-authority-reviewer`: Google Places canonical authority and enrichment limits.
- `latency-reviewer`: provider/fanout/LLM/cache/db route-budget risks.
- `evidence-prose-reviewer`: evidence atoms, writer-visible facts, notes, and claim-safety leakage.
- `workflow-retrospective-reviewer`: OS v3 misses, repeated patterns, and promotion targets.
- Certification pack (route only when applicable): `reality-checker`, `evidence-collector`, `premium-delight-reviewer`, `accessibility-reviewer`, `performance-benchmarker`.
- `agent-curator`: when evaluating external agent ideas / libraries.
- `prompt-intake-reviewer`: when prompt classification or OS drift is suspected.

Reviewer agents should return blockers/risks/evidence only. The builder remains responsible for implementation.

## Advisory hooks

Hooks are reminders only in OS v2/v3/v4:

- provider/runtime edits remind `/latency-gate`
- evidence/prose edits remind `/claim-safety-gate`
- UI/client contract edits remind `/contract-audit`
- SQL/env/settings edits remind manual action fields
- Stop reminds `/pre-pr-self-audit` and `/pr-summary`

Do not treat hook reminders as proof. They are prompts to run the relevant skill or reviewer.

## What belongs in the task prompt

Keep future prompts short. Include only:

- repo
- task/goal
- severity or suspected severity
- success criteria
- hard scope boundaries
- screenshots/log excerpts only if needed
- required validation target, if any
- the OS v4 default line: "Use OS v4. Run prompt-intake and roadmap-check before coding when applicable, run applicable focused skills, delegate via AGENT_ROUTER, and include workflow + product retrospectives if the PR is meaningful or validation fails."

Do not paste the full coding principles, repo invariants, test rules, or PR format. They live here.

## What must stay repo-native

- Coding principles: `docs/ai/EXECUTION_PRINCIPLES.md`
- Severity routing: `docs/ai/ISSUE_SEVERITY_ROUTING.md`
- Known failures: `docs/ai/KNOWN_FAILURE_MODES.md`
- Test routing: `docs/ai/TEST_SELECTOR.md`
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
- Product OS: `docs/product/*`

## Claude automation layers

### Layer 1 — Context files
`AGENTS.md`, `CLAUDE.md`, and this OS manual define the repo contract.

### Layer 2 — Focused skills
Use `.claude/skills/*/SKILL.md` for reusable procedures Claude can invoke when context matches.

### Layer 3 — Slash commands
Use `.claude/commands/*.md` as explicit human-triggered shortcuts or aliases to skills.

### Layer 4 — Advisory hooks
Use `.claude/settings.json` + `.claude/hooks/ai_os_advisory.py` as non-blocking reminders.

### Layer 5 — Read-only reviewer agents
Use `.claude/agents/*.md` for independent review without bloating builder context. Route via `AGENT_ROUTER`.

### Layer 6 — Self-learning loop (OS v3)
Use the workflow-retrospective skill, miss-ledger-update skill, and workflow-retrospective-reviewer agent to record misses and promote lessons under the OS_LEARNING_PROTOCOL ladder.

### Layer 7 — Product Roadmap Control Plane (OS v4)
Use `docs/product/*` plus the OS v4 skills (`prompt-intake`, `roadmap-check`, `idea-triage`, `build-queue-update`, `progress-report`, `product-retrospective`) and the `roadmap-guardian` agent to keep product direction repo-native.

## Travel-specific invariants

- Google Places is canonical for addable cards.
- Enrichment providers cannot mint cards.
- No keyword patching as a substitute for semantic behavior.
- No deterministic fallback visible notes.
- Evidence must be writer-safe before it reaches prose.
- Total request-path latency matters more than local provider timeout.

## Stop rules

Stop and ask for a split if:

- The fix touches three or more unrelated skill areas.
- A second related patch would be needed.
- Durable architecture exceeds the stated scope.
- Required runtime evidence is unavailable.
- The implementation would violate a product invariant.
- The PR has no clear roadmap stage or build queue item, and is not a justified blocker.
