# DEAD_ENDS — Travel dead-end registry

Durable record of approaches proven not to work. Check this file before investigating a
previously attempted provider, data source, or approach; append a row only after evidence
proves an approach is abandoned or ineffective.

| Date | Area | Approach tried | Why it is a dead end | Proof |
|------|------|----------------|----------------------|-------|
| 2026-06 | Itinerary metadata | Patching individual add-to-itinerary handlers separately | Lossy intermediate card shapes dropped place identity and caused repeated regressions | PRs #501, #504, #508, #521, #530 |
| 2026-05 | Plan My Day | Frontend-only patches for persistence-shaped bugs | Two frontend attempts failed before inspecting the persisted row exposed the backend root cause | PR #499 v1.1/v1.2 ledger history |

## Rules

- Check before investigating a previously attempted provider, data source, or approach.
- Add a row only when an approach is evidence-proven failed or abandoned — no speculative entries.
- Never record a successful solution as a dead end.
- Do not add a duplicate row for the same approach and proof.
- History and detail remain in the linked PR/log evidence, not in this file.
