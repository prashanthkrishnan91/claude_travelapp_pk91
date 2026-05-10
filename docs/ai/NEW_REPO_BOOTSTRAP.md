# New Repo Bootstrap — AI Repo Operating System

Use this file when creating the next personal app repo. The goal is to copy the reusable operating system without copying Travel-specific product rules.

## Copy into every new repo

- `AGENTS.md`
- `CLAUDE.md` OS section
- `.github/pull_request_template.md`
- `docs/ai/AI_REPO_OPERATING_SYSTEM.md`
- `docs/ai/TEST_SELECTOR.md`
- `docs/ai/PR_REVIEW_CHECKLIST.md`
- `docs/ai/DEFINITION_OF_DONE.md`
- `docs/ai/CONTEXT_MANAGEMENT.md`
- `docs/ai/FAILURE_RECOVERY.md`
- `docs/ai/RUNTIME_EVIDENCE.md`
- `docs/ai/MANUAL_ACTIONS_CHECKLIST.md`
- `docs/ai/PROMPT_BRIEF_TEMPLATE.md`
- `docs/ai/OS_LEARNING_PROTOCOL.md`
- `docs/ai/MISS_LEDGER.md`
- `docs/ai/WORKFLOW_RETROSPECTIVE.md`
- `docs/ai/HOOK_SAFETY.md`
- `docs/ai/PERMISSIONS_AND_MEMORY_BOUNDARIES.md`
- `docs/ai/AI_OS_MANIFEST.md`
- `docs/ai/AGENT_ROUTER.md`
- `docs/ai/AGENT_INTAKE_REGISTRY.md`
- `docs/ai/AGENT_EFFECTIVENESS_LEDGER.md`
- `docs/product/NORTH_STAR.md`
- `docs/product/ROADMAP.md`
- `docs/product/BUILD_QUEUE.md`
- `docs/product/IDEA_INBOX.md`
- `docs/product/DECISION_LOG.md`
- `docs/product/RELEASE_GATES.md`
- `docs/product/PRODUCT_HEALTH.md`
- `docs/product/DO_NOT_BUILD_YET.md`
- `docs/product/PROGRESS_REPORT_TEMPLATE.md`
- `.claude/skills/*/SKILL.md` (including `workflow-retrospective`, `miss-ledger-update`, `prompt-intake`, `roadmap-check`, `idea-triage`, `build-queue-update`, `progress-report`, `product-retrospective`)
- `.claude/commands/*.md` (including `prompt-intake.md`, `roadmap-check.md`, `idea-triage.md`, `progress-report.md`, `build-queue-update.md`)
- `.claude/agents/workflow-retrospective-reviewer.md`
- `.claude/agents/roadmap-guardian.md`
- `.claude/agents/prompt-intake-reviewer.md`
- `.claude/agents/agent-curator.md`

## Replace per repo

- product mission and north star
- non-negotiable invariants
- known failure modes
- test selector mappings
- runtime evidence sources
- SQL/env/deploy manual actions
- design/product roadmap and gates
- repo-specific catches in `OS_LEARNING_PROTOCOL.md` and the workflow-retrospective-reviewer agent
- repo-specific reviewer-agent budget defaults in `CONTEXT_MANAGEMENT.md` and `AGENT_ROUTER.md`

## Bootstrap checklist

1. Write one paragraph for the product north star.
2. Define canonical data sources and forbidden authority paths.
3. Define what must never leak to UI.
4. Map changed areas to tests.
5. Define when UI validation is required.
6. Define when runtime logs are required.
7. Add one PR template before the first AI feature PR.
8. Add skills/commands before scaling feature work.
9. Keep `CLAUDE.md` short; move procedures to skills/docs.
10. After two repeated failures, promote via the OS v3 ladder; otherwise keep entries in `MISS_LEDGER.md` only.
11. Install Product OS (NORTH_STAR, ROADMAP, BUILD_QUEUE, IDEA_INBOX, RELEASE_GATES, PROGRESS_REPORT_TEMPLATE) before scaling feature work.
12. Add `roadmap-guardian` agent and `progress-report` skill.
13. Add `AGENT_ROUTER.md` and `AGENT_INTAKE_REGISTRY.md` before adding more reviewer agents.
14. Do not import external agent libraries wholesale.

## OS v3 bootstrap notes

- Seed `MISS_LEDGER.md` with project-specific early misses after the first few PRs.
- Use OS v3 before scaling feature work.
- Install deployment/build-cost control language in `CLAUDE.md`, `MANUAL_ACTIONS_CHECKLIST.md`, and `PR_REVIEW_CHECKLIST.md` before the first workflow-heavy PR.
- For new repos using Vercel or similar preview-build systems, avoid file-by-file workflow commits; batch in one Sonnet-driven branch/PR.

## OS v4 bootstrap notes

- Use Product OS to stop idea sprawl from derailing active build.
- Seed `IDEA_INBOX.md` with PK ideas before they become implementation prompts.
- Wire `prompt-intake` and `roadmap-check` before the first feature-heavy PR.
- Default to fewer high-signal reviewer agents over many generic reviewers.

## OS v3 pinnacle bootstrap rules

- Add reviewer-agent budget discipline before scaling AI PR volume.
- Add built-in Claude command discipline before first large implementation.
- Do not enable hard-blocking hooks in a new repo until advisory hooks have proven useful.
- Do not connect MCP servers in a new repo until the need and security posture are clear.
- Install the OS manifest (`docs/ai/AI_OS_MANIFEST.md`) before the first major feature PR.
- Install `HOOK_SAFETY.md` and `PERMISSIONS_AND_MEMORY_BOUNDARIES.md` before any hooks or MCP additions.

## Default short prompt for any new repo

```text
Repo: <owner/name>

Task:
<focused feature/fix>

Severity:
Level <0/1/2/3> because <reason>.

Success criteria:
- <observable outcome 1>
- <observable outcome 2>
- <non-negotiable invariant>

Use OS v4.
Run prompt-intake and roadmap-check before coding when applicable.
Run applicable focused skills before coding.
Delegate via AGENT_ROUTER before PR summary.
Include workflow + product retrospectives if this is Level 1+ or if validation fails.
Open one focused PR.
Stop after PR summary.
```
