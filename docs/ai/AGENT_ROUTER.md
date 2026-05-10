# Agent Router — Travel

Select relevant reviewer agents. Do not run every agent by default.

## Principles

- Use only relevant agents.
- Builder implements; agents review.
- Reviewer agents return evidence/blockers/risks, not code edits.
- Do not run every agent by default.
- Prefer fewer high-signal reviewers over many generic reviewers.

## Default routing

- `roadmap-guardian` — product direction, build queue, scope creep, roadmap alignment.
- `contract-auditor` — shared contracts, API, data, frontend ↔ backend boundaries.
- `test-strategist` — non-trivial implementation / test strategy.
- `pr-reviewer` — meaningful PRs before merge.
- `workflow-retrospective-reviewer` — workflow miss or OS promotion candidate.
- `reality-checker` — high-risk, release-readiness, user-facing, or "is this really done?" PRs.
- `evidence-collector` — when proof is scattered across tests/logs/screenshots/runtime/PR evidence.
- `premium-delight-reviewer` — design sprint, wife-wow, premium UX, product polish.
- `accessibility-reviewer` — UI / design / mobile / card / form / navigation changes.
- `performance-benchmarker` — latency, runtime, provider, cache, route, bundle, responsiveness claims.

## Phase routing

- Pre-coding: `roadmap-guardian`, `prompt-intake-reviewer`.
- During implementation: route only when changes touch the agent's domain.
- Pre-PR-summary: `pr-reviewer`, `reality-checker` (if user-visible or release-adjacent), `evidence-collector` (if multi-source proof).
- Post-merge / failed validation: `workflow-retrospective-reviewer`.

## Travel-specific routing

- `place-authority-reviewer` — addable cards, source authority, provider evidence.
- `latency-reviewer` — AI Concierge provider/fanout/cache/route changes.
- `evidence-prose-reviewer` — notes, reasons, copy, evidence, prose.
- `premium-delight-reviewer` — Wife Wow Design Sprint and Discover/Saved/Trip UX.
- `roadmap-guardian` — all Stage 2+ product shifts.

## Anti-patterns

- Running every agent on every PR.
- Using reviewer agents to write code.
- Ignoring agent recommendations because the PR is small.
- Adding new reviewer agents without recording effectiveness in `AGENT_EFFECTIVENESS_LEDGER.md`.
- Importing external agent libraries wholesale.
