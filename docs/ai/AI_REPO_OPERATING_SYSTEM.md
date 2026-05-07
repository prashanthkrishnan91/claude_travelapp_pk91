# AI Repo Operating System — Travel Concierge

This repo uses an AI Repo Operating System so ChatGPT can give Claude short task briefs while Claude performs the repeated engineering workflow automatically.

## Goal
Turn Claude from a prompt executor into a repo-aware engineering partner that plans, audits, tests, summarizes, and stops at the right boundary.

## Default human/agent loop

1. PK states product goal, issue, screenshot, logs, or validation result.
2. ChatGPT chooses severity, model, scope, and gives Claude a short task brief.
3. Claude reads `CLAUDE.md`, this OS, and only the smallest relevant supporting docs.
4. Claude runs the relevant project skills or commands before coding.
5. Claude builds one focused PR, runs tests, self-audits, updates handoff only when meaningful, and uses the PR template.
6. ChatGPT reviews the actual PR diff and evidence.
7. Codex is used only for surgical blockers, merge-gate exceptions, or targeted audits.
8. PK does UI/runtime validation only when the product-visible behavior requires it.

## Required sequence for non-trivial tasks

Before coding:

1. Classify severity using `docs/ai/ISSUE_SEVERITY_ROUTING.md`.
2. State assumptions, success criteria, out-of-scope, and stop/split conditions.
3. Identify changed contracts and likely downstream consumers.
4. Use `docs/ai/TEST_SELECTOR.md` to choose the smallest sufficient test suite.
5. Read `docs/ai/KNOWN_FAILURE_MODES.md` for this repo.

Before PR summary:

1. Run contract audit.
2. Run latency gate if runtime/provider/LLM/db behavior changed.
3. Run claim-safety gate if user-visible text/data/actions/evidence changed.
4. Run pre-PR self-audit.
5. Fill `.github/pull_request_template.md` honestly.

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

### Layer 2 — Skills
Use `.claude/skills/*/SKILL.md` for reusable procedures Claude can invoke when context matches.

### Layer 3 — Slash commands
Use `.claude/commands/*.md` as explicit human-triggered shortcuts or aliases to skills.

### Layer 4 — Hooks roadmap
Hooks are planned in `docs/ai/CLAUDE_HOOKS_ROADMAP.md`. Wave 1 is documentation/skills only; hooks should start advisory, not blocking.

### Layer 5 — Subagents roadmap
Reviewer subagents are planned in `docs/ai/SUBAGENTS_ROADMAP.md`; add them only after skills/commands prove useful.

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
