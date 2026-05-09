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
- `.claude/skills/*/SKILL.md` (including `workflow-retrospective` and `miss-ledger-update`)
- `.claude/commands/*.md`
- `.claude/agents/workflow-retrospective-reviewer.md`

## Replace per repo

- product mission
- non-negotiable invariants
- known failure modes
- test selector mappings
- runtime evidence sources
- SQL/env/deploy manual actions
- design/product north star
- repo-specific catches in `OS_LEARNING_PROTOCOL.md` and the workflow-retrospective-reviewer agent

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

## OS v3 bootstrap notes

- Seed `MISS_LEDGER.md` with project-specific early misses after the first few PRs.
- Use OS v3 before scaling feature work.
- Install deployment/build-cost control language in `CLAUDE.md`, `MANUAL_ACTIONS_CHECKLIST.md`, and `PR_REVIEW_CHECKLIST.md` before the first workflow-heavy PR.
- For new repos using Vercel or similar preview-build systems, avoid file-by-file workflow commits; batch in one Sonnet-driven branch/PR.

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

Use OS v3.
Run applicable focused skills before coding.
Delegate to applicable read-only reviewer agents before PR summary.
Include workflow retrospective if this is Level 1+ or if validation fails.
Open one focused PR.
Stop after PR summary.
```
