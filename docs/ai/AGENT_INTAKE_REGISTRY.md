# Agent Intake Registry — Travel

A parking lot for useful external agent repos, agent ideas, or patterns PK finds later.

## Rules

- Do not import external agents wholesale.
- Record source, useful pattern, risk, and decision.
- Promote only if the pattern solves a recurring repo / workflow / product problem.
- Prefer adapting patterns to OS v4 over copying text.
- Keep rejected ideas so PK does not need to remember later.

## Entry template

```
## YYYY-MM-DD — <source or idea>
Source:
What it offers:
Potentially useful patterns:
Risks / why not copy wholesale:
Decision: parked / rejected / promoted / needs research
Promotion target:
Follow-up trigger:
Notes:
```

## Entries

## 2026-05-09 — msitarzewski/agency-agents
Source:
https://github.com/msitarzewski/agency-agents
What it offers:
Large library of specialized agents across product, design, testing, engineering, marketing, and operations.
Potentially useful patterns:
- Reality Checker / proof-first skeptical review
- Evidence Collector / proof inventory
- Performance Benchmarker
- Accessibility Auditor
- Product/design reviewers for premium UX and wife-wow readiness
- Strong agent templates with mission, rules, deliverables, and success metrics
Risks / why not copy wholesale:
- Too many agents creates routing noise.
- Many roles are irrelevant to private Travel/Finance apps.
- Personality-heavy agents can become verbose.
- Generic agents do not know repo-specific invariants.
- Our OS v3/v4 has targeted workflow, product, and trust rules.
Decision:
Promoted selectively into a small Certification Agent Pack:
- reality-checker
- evidence-collector
- premium-delight-reviewer
- accessibility-reviewer
- performance-benchmarker
Promotion target:
`.claude/agents/*`, `docs/ai/AGENT_ROUTER.md`
Follow-up trigger:
If PK shares another agent repo, add a new registry entry and decide parked / rejected / promoted. Do not install by default.
