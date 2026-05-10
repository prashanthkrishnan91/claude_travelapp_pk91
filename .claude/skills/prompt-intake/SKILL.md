# Skill: prompt-intake

## Purpose

Before coding, classify the incoming task and choose the correct OS v4 path.

## Inputs

- The user prompt or task brief.
- `docs/ai/AI_REPO_OPERATING_SYSTEM.md`
- `docs/ai/AGENT_ROUTER.md`
- `docs/product/ROADMAP.md`
- `docs/product/BUILD_QUEUE.md`
- `docs/product/IDEA_INBOX.md`

## Output

- Task type:
  - implementation
  - bug fix
  - PR review
  - workflow update
  - product roadmap update
  - runtime / log investigation
  - SQL / migration
  - UI / design
  - architecture / spec only
  - failed validation / follow-up
  - prompt-generation task
  - idea triage
  - progress report
- Roadmap stage:
- Build queue item:
- Required focused skills:
- Required reviewer agents:
- Validation expectations:
- Workflow retrospective needed: Yes / No.
- Miss / idea / queue update needed: Yes / No.
- Stop condition:

## Rules

- If the user asks for a prompt, produce OS v4 work-order format unless architecture / spec-only explicitly requires more context.
- If this is idea dumping, run `idea-triage` rather than implementation.
- If this is "where are we," run `progress-report`.
- If this is "what next," run `roadmap-check` and the build queue.
- If classification is ambiguous, state the assumption and choose the safest narrow route.
- Keep output concise.
