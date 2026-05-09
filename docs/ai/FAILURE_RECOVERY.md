# Failure Recovery — Travel Concierge

Use this whenever a PR, prompt, runtime validation, or UI test exposes a miss.

## Patch exhaustion rule

- After one failed patch: reclassify severity and restate the root cause hypothesis.
- After two related patches: stop patching. Move to full plumbing analysis or split plan.
- Do not stack local fixes when the failure is a contract, provider, routing, or product-invariant problem.

## If tests pass but product behavior fails

1. Write or identify an adversarial test that would have caught the miss.
2. Audit producer and consumer contracts.
3. Check runtime evidence if the issue involves production providers, latency, auth, cache, or deployment.
4. Fix the root cause, not the visible symptom.

## If runtime evidence is missing

- Do not guess.
- Use the `railway-logs` personal skill if available.
- If logs are insufficient because the app does not emit the right evidence, propose observability before claiming validation.

## If UI validation finds a regression

- Classify whether the regression is UI-only, API contract, backend data, or runtime/provider behavior.
- Do not patch UI if the backend contract is wrong.
- Do not patch backend if the frontend mapper dropped valid fields.

## Workflow miss recovery (OS v3)

- If the failure is caused by a workflow/prompt/process miss, run `.claude/skills/workflow-retrospective/SKILL.md`.
- If repeated, update `docs/ai/MISS_LEDGER.md` and recommend a promotion target via the ladder in `docs/ai/OS_LEARNING_PROTOCOL.md`.
- Do not immediately add broad rules from a one-off failure.
- If the failure involved deployment/build-cost usage, classify deployment-cost risk and update `MISS_LEDGER.md`.

## Escalate when

- Google card authority is compromised.
- Verified cards are dropped after backend success.
- Notes/prose contain unsupported claims.
- Route latency cannot be proven from local tests.
- A fix requires three or more skill areas.
