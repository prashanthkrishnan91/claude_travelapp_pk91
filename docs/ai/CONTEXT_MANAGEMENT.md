# Context Management — Travel Concierge

Use this to avoid bloated Claude chats and degraded adherence.

## Start a new Claude chat when

- Starting a new phase, architecture slice, or Level 2/3 task.
- The current chat has already produced a PR and follow-up fix.
- The task touches multiple contracts or providers.
- Prior context includes stale assumptions or failed patches.
- A clean PR summary/audit is more valuable than chat continuity.

## Follow up in the same chat when

- The PR is open and the fix is a narrow reviewer change.
- The change is a typo, missed test, or small docs correction.
- Claude needs to update the same PR based on fresh ChatGPT review.

## Stop after PR summary when

- Usage is Medium-High or High.
- The PR is opened and self-audit is complete.
- Further work would belong to a new task or phase.

## Compacting rule

If compaction is needed, preserve only:

- current repo/branch/PR
- task goal and severity
- assumptions and success criteria
- files changed
- tests run/results
- known risks/limitations
- next required action
- current roadmap stage and build queue item (OS v4)

Do not preserve long implementation narration unless needed for review.

## OS v3 self-learning notes

- If a chat has produced a PR and a workflow miss is identified, record the retrospective in `docs/ai/MISS_LEDGER.md` before starting a new chat.
- Do not keep adding process fixes to a bloated implementation chat.
- For workflow upgrades that touch many files, use Claude/Sonnet to batch one branch and one PR. Do not use file-by-file connector edits.
- ChatGPT GitHub connector should be reserved for tiny/surgical edits, not bulk workflow/docs updates.

## OS v4 routing notes

- When user dumps ideas, route to `docs/product/IDEA_INBOX.md` via `idea-triage` skill, not immediate implementation.
- When user asks "where are we", use `progress-report` skill against `docs/product/*` and `docs/ai/HANDOFF.md`.
- When user asks "what next", use `roadmap-check` skill and `docs/product/BUILD_QUEUE.md`.
- If chat is bloated, preserve current roadmap stage, build queue item, PR, files changed, tests, blockers, and next action before compacting / new chat.

## Built-in Claude command discipline

- Use `/cost` for Medium/High work or when token usage seems unexpectedly high.
- Use `/compact` before long sessions degrade, preserving only the compacting rule fields.
- Prefer a new chat after a PR plus one follow-up, or after a failed patch loop.
- Use `/pr_comments` when responding to PR comments.
- Use `/review` only as a lightweight extra review, not as a replacement for OS reviewer agents.
- Use `/doctor` only for suspected Claude Code/tooling health issues.
- Use `/memory` carefully; repo OS docs should be the source of team-shared workflow truth.
- Use `/permissions` only to inspect/resolve tool access or safety issues.
- Use `/mcp` only to inspect configured MCP state; do not add servers unless a future approved task requires it.

## Pre-compact summary contract

Before `/compact`, preserve:

- repo
- branch
- PR number
- task goal
- severity
- assumptions
- success criteria
- files changed
- tests/checks run
- reviewer agents used
- unresolved blockers
- manual actions
- next required action
- whether workflow retrospective or `MISS_LEDGER` update is needed
- current roadmap stage and build queue item (OS v4)

## Reviewer-agent budget

- Do not run every reviewer on every PR.
- Choose reviewer agents based on changed contracts and risk via `docs/ai/AGENT_ROUTER.md`.
- Common default:
  - `roadmap-guardian` for product-direction or scope-creep risk
  - `contract-auditor` for shared contract/API/output changes
  - `test-strategist` for non-trivial test planning
  - `pr-reviewer` before merge on meaningful PRs
- Travel-specific reviewers only when their domain is touched:
  - `place-authority-reviewer` for addable card / source authority changes
  - `latency-reviewer` for provider/fanout/cache/route changes
  - `evidence-prose-reviewer` for notes/reasons/claims/copy/evidence changes
- Certification pack only when applicable:
  - `reality-checker` for release-readiness or "is this done?" PRs
  - `evidence-collector` for scattered-evidence PRs
  - `premium-delight-reviewer` for design-sprint and wife-wow surfaces
  - `accessibility-reviewer` for UI/design changes
  - `performance-benchmarker` for latency/responsiveness claims
- `workflow-retrospective-reviewer` only when a miss, failed validation, or promotion candidate exists.
