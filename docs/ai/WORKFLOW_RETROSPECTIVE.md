# Workflow Retrospective — Travel Concierge

A standard lightweight retrospective Claude runs after meaningful PRs or failed validation.

## When to run

- Level 1+ implementation
- Level 2/3 workflow, architecture, provider, policy, SQL, runtime, deployment/build, or UI change
- any failed validation
- any follow-up after PR review
- any prompt-format miss
- any Codex rescue

## When not to run

- typo-only
- tiny docs-only
- pure formatting
- comment-only changes with no workflow implication

## Retrospective questions

- Did the task use OS v2/v3 work-order format?
- Did Claude use required focused skills?
- Did Claude delegate to applicable read-only reviewer agents?
- Did advisory hooks create useful reminders or noise?
- Did the PR summary include enough evidence?
- Was Codex needed?
- Was UI validation correctly classified?
- Was runtime/SQL/deployment validation correctly classified?
- Did PK or ChatGPT catch something the OS should catch next time?
- Should this create a `MISS_LEDGER` entry?
- Should this promote to `KNOWN_FAILURE_MODES`, `TEST_SELECTOR`, `PR_REVIEW_CHECKLIST`, reviewer agent, skill, hook, or prompt template?

## Output format

```text
Workflow retrospective:
- OS work-order format used:
- OS skills used:
- Reviewer agents used:
- Hooks triggered:
- Evidence quality:
- Manual follow-up needed:
- Codex needed:
- UI validation correctly classified:
- Runtime/SQL/deployment validation correctly classified:
- Miss ledger entry needed: Yes/No
- Promotion recommended: Yes/No
- Promotion target:
- Reason:
```
