# AI Repo Operating System — Travel Concierge

This repo uses an AI Repo Operating System so ChatGPT can give Claude short task briefs while Claude performs the repeated engineering workflow automatically.

## Goal
Turn Claude from a prompt executor into a repo-aware engineering partner that plans, audits, tests, delegates independent review, summarizes, and stops at the right boundary.

## Default human/agent loop

1. PK states product goal, issue, screenshot, logs, or validation result.
2. ChatGPT chooses severity, model, scope, and gives Claude a short task brief.
3. Claude reads `CLAUDE.md`, this OS, and only the smallest relevant supporting docs.
4. Claude runs the relevant focused skills or commands before coding.
5. Claude builds one focused PR, runs tests, delegates read-only review to applicable reviewer agents, self-audits, updates handoff only when meaningful, and uses the PR template.
6. ChatGPT reviews the actual PR diff and evidence.
7. Codex is used only for surgical blockers, merge-gate exceptions, or targeted audits.
8. PK does UI/runtime validation only when the product-visible behavior requires it.

## OS v2 upgrades

OS v2 adds three automation layers on top of v1:

1. **Focused skills** under `.claude/skills/*/SKILL.md` so Claude can invoke smaller task-specific routines instead of skimming one broad checklist.
2. **Advisory hooks** through `.claude/settings.json` + `.claude/hooks/ai_os_advisory.py`. These only print reminders and exit successfully; they do not block tools or change app behavior.
3. **Read-only reviewer agents** under `.claude/agents/*.md` so Claude can delegate independent contract, test, latency, place-authority, and evidence/prose review before PR summary.

## Required sequence for non-trivial tasks

Before coding:

1. Classify severity using `docs/ai/ISSUE_SEVERITY_ROUTING.md`.
2. Run or apply `task-planner`.
3. Identify changed contracts and likely downstream consumers.
4. Run or apply `test-selector`.
5. Read `docs/ai/KNOWN_FAILURE_MODES.md` for this repo.

Before PR summary:

1. Run or apply `contract-audit`.
2. Run or apply `runtime-gate` / `latency-gate` if runtime/provider/LLM/db behavior changed.
3. Run or apply `claim-safety-gate` if user-visible text/data/actions/evidence changed.
4. Delegate to applicable read-only reviewer agents when the PR touches shared contracts, provider/runtime behavior, visible prose, or card authority.
5. Run or apply `pre-pr-self-audit`.
6. Fill `.github/pull_request_template.md` honestly through `pr-summary`.

## Reviewer delegation guide

Use reviewer agents for independent evidence, not code edits.

- `contract-auditor`: changed contracts, consumers, missed connected files.
- `test-strategist`: smallest sufficient tests and adversarial invariant coverage.
- `pr-reviewer`: final PR evidence vs checklist.
- `place-authority-reviewer`: Google Places canonical authority and enrichment limits.
- `latency-reviewer`: provider/fanout/LLM/cache/db route-budget risks.
- `evidence-prose-reviewer`: evidence atoms, writer-visible facts, notes, and claim-safety leakage.

Reviewer agents should return blockers/risks/evidence only. The builder remains responsible for implementation.

## Advisory hooks

Hooks are reminders only in OS v2:

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
Use `.claude/agents/*.md` for independent review without bloating builder context.

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
