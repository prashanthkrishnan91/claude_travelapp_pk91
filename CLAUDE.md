# Claude Instructions — Travel Concierge

Use this repo through a browser/mobile Claude + Codex workflow unless the user explicitly says CLI is available.

## AI Repo Operating System v2

For every non-trivial implementation, bug fix, UI change, provider/runtime change, migration, PR review, or workflow update, use the repo AI Operating System before coding:

1. Read `docs/ai/AI_REPO_OPERATING_SYSTEM.md`.
2. Read `docs/ai/KNOWN_FAILURE_MODES.md`.
3. Use focused skills in `.claude/skills/*/SKILL.md` for planning, contract audit, test selection, runtime/latency gates, claim-safety, self-audit, PR summary, and failure recovery.
4. Use read-only reviewer agents in `.claude/agents/*.md` for independent contract, test, place-authority, latency, evidence/prose, and PR review when applicable.
5. Treat `.claude/hooks/ai_os_advisory.py` reminders as advisory prompts to run the relevant skill or reviewer, not as proof.
6. Fill `.github/pull_request_template.md` honestly before PR summary.
7. Stop and propose a split if the durable fix exceeds scope.

Do not paste repeated workflow rules into every prompt. The short prompt should define the task, severity, success criteria, and scope; the repo OS owns the repeated process.

## AI Repo Operating System v3 — self-learning loop

For Level 1+ PRs or any failed validation, run `.claude/skills/workflow-retrospective/SKILL.md` against `docs/ai/WORKFLOW_RETROSPECTIVE.md`.

If a workflow miss occurred, recommend or add a concise entry to `docs/ai/MISS_LEDGER.md` via `.claude/skills/miss-ledger-update/SKILL.md`. Do not promote one-off misses into broad rules — follow the promotion ladder in `docs/ai/OS_LEARNING_PROTOCOL.md`.

All Travel/Finance/future-repo coding prompts must use OS v2/v3 work-order format unless explicitly generating architecture/spec only. For bulk repo/workflow edits, batch changes in one branch/PR; do not use file-by-file connector-style commits.

Before work, read only the smallest needed subset of:

1. `docs/ai/HANDOFF.md` — current state
2. `docs/ai/AI_REPO_OPERATING_SYSTEM.md` — required non-trivial task workflow
3. `docs/ai/KNOWN_FAILURE_MODES.md` — project-specific ways AI PRs fail
4. `docs/ai/TEST_SELECTOR.md` — changed area to required tests
5. `docs/ai/PROMPT_LIBRARY.md` — workflow, budget, prompt, UI, and review rules
6. `docs/ai/ISSUE_SEVERITY_ROUTING.md` — choose patch vs focused root-cause fix vs full plumbing analysis vs split plan
7. `docs/ai/EXECUTION_PRINCIPLES.md` — think-before-coding, simplicity-first, surgical changes, and goal-driven execution for every prompt
8. `docs/ai/ROOT_CAUSE_QUALITY_BAR.md` — bounded root-cause quality bar for bugs, regressions, complex features, and reviews
9. `docs/ai/skills/README.md` — task-specific workflow skill router
10. `docs/ai/CLAUDE_PERSONAL_SKILLS.md` — optional personal Claude skill routing when a prompt names a personal skill, including runtime log retrieval with `railway-logs`
11. `docs/ai/DESIGN_VISION.md` — long-term aspirational UI direction and timing gate when doing major design work
12. `docs/ai/UI_BASELINE.md` — UI baseline and known visual costs when doing UI work
13. `docs/ai/CLAUDE_WORKFLOW_KIT.md` — stable project constraints only when needed
14. `README.md` — public/setup context only when needed

Use one primary workflow skill when it matches the task:

- `.claude/skills/ai-repo-os/SKILL.md` — default non-trivial task planner, audit, test, and PR evidence workflow
- `.claude/skills/task-planner/SKILL.md` — severity, assumptions, success criteria, contracts, stop/split plan
- `.claude/skills/contract-audit/SKILL.md` — changed contracts and downstream consumers
- `.claude/skills/test-selector/SKILL.md` — smallest sufficient tests and adversarial invariant coverage
- `.claude/skills/runtime-gate/SKILL.md` — provider/runtime/latency evidence
- `.claude/skills/claim-safety-gate/SKILL.md` — visible text/data/evidence safety
- `.claude/skills/pre-pr-self-audit/SKILL.md` — acceptance criteria to file/function/test/evidence mapping
- `.claude/skills/pr-summary/SKILL.md` — PR template evidence
- `.claude/skills/failure-recovery/SKILL.md` — failed patch/review/runtime recovery
- `.claude/skills/workflow-retrospective/SKILL.md` — OS v3 retrospective after meaningful PRs or failed validation
- `.claude/skills/miss-ledger-update/SKILL.md` — OS v3 ledger entry for workflow/product-process misses
- `docs/ai/skills/discovery.md` — map unknown files or visual surfaces before implementation
- `docs/ai/skills/bugfix.md` — focused bug fix or small behavior correction
- `docs/ai/skills/ui_fix.md` — capped UI polish or visual consistency pass
- `docs/ai/skills/implementation.md` — focused multi-file feature implementation
- `docs/ai/skills/merge_gate.md` — cheap PR review before merge
- `docs/ai/skills/workflow_update.md` — workflow/documentation updates
- `docs/ai/skills/supabase_change.md` — any Supabase SQL, schema, RLS, auth, or persistence-contract change

Useful command aliases:

- `/test-selector`
- `/contract-audit`
- `/latency-gate`
- `/claim-safety-gate`
- `/pre-pr-self-audit`
- `/pr-summary`
- `/update-handoff`

Core rules:

- Default test-routing policy: follow `docs/ai/TEST_ROUTING.md`; do not run full `pytest tests/` by default for ordinary PRs.
- Every PR summary must include **Test tier used** and **Why this tier was sufficient**. If full suite is run, include the explicit reason; if skipped, list targeted bundles/tests that replaced it.
- No broad discovery. Read primary target files first; fallback reads only if blocked.
- Classify issue severity before choosing Codex patch, Sonnet full plumbing analysis, or split plan.
- Do not keep patching after failed patches. After one failed patch, reclassify. After two related patches, escalate to full plumbing analysis or split plan.
- When runtime evidence matters, use the `railway-logs` personal Claude skill if available before coding. This applies to Railway/deployment errors, crashes, recent errors, 4xx/5xx responses, provider failures, auth/cache/persistence mismatches, and cases where backend logs disagree with UI behavior. Summarize only relevant evidence; do not ask the user to paste Railway JSON/logs unless the skill is unavailable.
- Smallest safe patch. No unrelated refactors.
- For non-trivial work, state assumptions and success criteria before coding.
- Every changed line must trace to the task.
- Fix root causes, not symptoms. Do not hide broken behavior, remove UI, or add brittle glue code when the end-to-end flow is fixable within scope.
- Use repo-local workflow skills instead of repeating large instruction blocks in prompts.
- Personal Claude skills are optional accelerators only; they do not replace repo rules, budget gates, or project invariants.
- Major design transformation must wait until `docs/ai/DESIGN_VISION.md` timing gate is satisfied; do small UI fixes only when needed before then.
- If a task needs three or more skill types, split it before implementation.
- Update `docs/ai/HANDOFF.md` in the same PR for any implementation, bug fix, UI change, architecture change, migration, or workflow change.
- State Supabase SQL requirement in every PR summary.
- Stop after opening any Medium-High/High usage PR. Do not propose the next implementation prompt.

Project invariants:

- Google Places is canonical for addable places.
- Yelp/Foursquare are enrichment only.
- Editorial/web sources are evidence only.
- AI Concierge card fields must stay aligned: `display.displayWhy`, `supportingDetails.whyPick`, and top-level `whyPick`.
- No backend/API/business-logic changes during UI-only work.

Final response format:

```md
Severity classification: Level 0/1/2/3, when applicable
Root cause/plan:
Files changed:
Tests:
Risks:
Supabase SQL: Yes/No
HANDOFF.md edited: Yes/No + reason
README.md edited: Yes/No + reason
```
