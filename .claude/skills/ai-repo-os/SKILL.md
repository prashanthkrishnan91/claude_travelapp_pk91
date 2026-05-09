# AI Repo OS Skill

Use this skill for any non-trivial implementation, bug fix, UI change, provider/runtime change, PR review, workflow update, or handoff update.

## Load first

Read only the smallest needed subset of:

- `CLAUDE.md`
- `docs/ai/AI_REPO_OPERATING_SYSTEM.md`
- `docs/ai/KNOWN_FAILURE_MODES.md`
- `docs/ai/TEST_SELECTOR.md`
- `docs/ai/PR_REVIEW_CHECKLIST.md`
- `docs/ai/DEFINITION_OF_DONE.md`
- `docs/ai/MANUAL_ACTIONS_CHECKLIST.md`
- `docs/ai/OS_LEARNING_PROTOCOL.md`
- `docs/ai/MISS_LEDGER.md`
- `docs/ai/WORKFLOW_RETROSPECTIVE.md`

## Task planner

Before coding, state:

- severity level and why
- assumptions
- success criteria
- root cause hypothesis or architecture gap
- affected contracts
- likely downstream consumers
- out-of-scope
- stop/split conditions

Fail planning if the task requires three or more unrelated skill areas in one PR.

## Test selector

Use `docs/ai/TEST_SELECTOR.md`.

- Choose the smallest sufficient suite.
- Add or identify one adversarial test for the riskiest invariant.
- Explain skipped tests.

## Contract audit

List:

- changed outputs/contracts
- consumers
- behavior changes
- files intentionally not changed
- tests or rationale proving safety

Fail the audit if downstream consumers are not checked.

## Latency gate

Run when provider, fanout, LLM, DB, cache, or request-path behavior changes.

Check:

- new live calls
- local timeout
- total route/runtime impact
- fallback/skip behavior
- non-blocking executor lifecycle for request-path fanout

Fail if only local timeout is tested but total route impact is not considered.

## Claim-safety gate

Run when user-visible text, cards, actions, evidence, or LLM-visible prose changes.

Travel checks:

- Google Places remains canonical for addable cards.
- Enrichment cannot mint cards.
- Unsupported place claims are blocked or hidden.
- Source-name-only evidence cannot become visible filler.
- Internal diagnostics/raw evidence cannot reach UI/prose.

## Pre-PR self-audit

Before PR summary:

- Map every success criterion to file/function/test/evidence.
- Identify limitations and out-of-scope items.
- Confirm manual actions checklist.
- Confirm HANDOFF update yes/no and why.
- Fail self-audit if contract, latency, or claim-safety checks were skipped when applicable.

## PR summary

Use `.github/pull_request_template.md`.

- Do not overclaim.
- Include tests actually run.
- Call out known failures and whether they are pre-existing.
- State SQL/UI/env/provider/LLM/runtime impact.
- State user validation needed yes/no and why.
- Fill the AI workflow retrospective section when applicable: OS skills used, reviewer agents used, miss ledger entry needed yes/no, promotion target if any.
- Classify deployment/build-cost impact when relevant (Vercel deployment expected, preview build needed, deployment-cost risk, docs/workflow-only).

## OS v3 self-learning loop

For Level 1+ PRs, meaningful workflow/product changes, failed validation, Codex rescue, prompt-format miss, deployment/build-cost miss, or repeated follow-up loop:

- run or apply `.claude/skills/workflow-retrospective/SKILL.md`
- if a workflow/product-process miss occurred, run or apply `.claude/skills/miss-ledger-update/SKILL.md`
- use `.claude/agents/workflow-retrospective-reviewer.md` for independent read-only review when a promotion target is proposed
- promote lessons only through `docs/ai/OS_LEARNING_PROTOCOL.md`
- do not bloat the OS from one isolated miss
