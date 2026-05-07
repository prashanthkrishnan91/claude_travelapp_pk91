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
- `.claude/skills/*/SKILL.md`
- `.claude/commands/*.md`

## Replace per repo

- product mission
- non-negotiable invariants
- known failure modes
- test selector mappings
- runtime evidence sources
- SQL/env/deploy manual actions
- design/product north star

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
10. After two repeated failures, add the failure to `KNOWN_FAILURE_MODES.md`.

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

Use the repo AI Operating System.
Run required skills/commands before PR summary.
Open one focused PR.
Stop after PR summary.
```
