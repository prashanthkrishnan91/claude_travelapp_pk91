---
name: failure-recovery
description: Use when a fix attempt fails, and especially at the second failed related attempt on the same bug or seam — before writing a third patch, and before revisiting any provider, data source, or approach that may have been tried before.
---

# failure-recovery — stop the loop at two

## First failed attempt

- Reclassify severity (`docs/ai/ISSUE_SEVERITY_ROUTING.md`).
- Identify the missing evidence that would have caught it.
- Do not automatically escalate an isolated failure into a patch-loop declaration — one failure is not a loop.

## Second failed related attempt (mandatory)

1. STOP writing patches.
2. State explicitly: "Two attempts failed — switching to evidence-first diagnosis."
3. Gather evidence from the actual failing layer before forming attempt three:
   - **persistence/data**: inspect the actual persisted row or authoritative stored data — do not infer from code.
   - **runtime/API**: retrieve the actual log, response, error, or failing test and name the failure seam.
   - **UI**: capture the current rendered state and screenshot before another change.
   - **provider/data source**: retrieve the actual provider response/status and consult `docs/ai/DEAD_ENDS.md`.
   - **tool/test/log failure**: route through `tool-failure-triage` before changing app code.
4. Re-diagnose the complete relevant path (not just the layer the last patch touched) instead of repeating a change in the same layer.
5. Attempt three is permitted only against named evidence (log key, row value, screenshot, provider status) and must be classified as a full-plumbing fix or an explicit split plan — never another speculative micro-patch.

## Before revisiting a provider, data source, or approach

Check `docs/ai/DEAD_ENDS.md` first. If the approach or provider is already listed, do not reinvestigate it — choose a different approach or stop and report to the user.

## After a loop ends

Append one row to `docs/ai/DEAD_ENDS.md`:

- Record only approaches that were abandoned or proven ineffective.
- Never record the successful resolution itself as a dead end.
- Do not add a duplicate row for the same approach and proof.

## User-reported regression tied to a known commit

- Stop speculative follow-up patches.
- Prefer a bounded surgical revert to restore the last known-good behavior when the user has requested or authorized restoration.
- Otherwise, report the proposed revert and evidence rather than silently performing a destructive action.
