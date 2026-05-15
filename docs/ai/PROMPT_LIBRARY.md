# Prompt Library (compressed, OS v4)

All templates assume the OS v4 default work-order shape and the compression rules in `docs/ai/PROMPT_ENGINEERING_STANDARD.md`. Each template is short on purpose. Do not pad templates with repeated rules — name the safety pack(s) and build archetype instead.

Default test routing for every template is `docs/ai/TEST_ROUTING.md`. Do not run the full backend suite by default.

## Copy rule

When ChatGPT gives the user a Claude/Codex prompt:

- Put `Model:`, `Chat:`, and `Usage estimate:` OUTSIDE the copyable prompt block.
- The copyable prompt block must contain only text intended to paste into Claude/Codex.
- Do not include explanatory notes inside the prompt block.

## Prompt reviewer gate (compression-aware)

Before giving any Claude/Codex prompt, ChatGPT must silently check:

1. Cheapest capable model?
2. Correct new/same chat?
3. Repo memory instead of repeated context?
4. Minimal file scope (anchor files only)?
5. Compressed constraints — would this prompt still work if repeated workflow boilerplate were removed?
6. Can this task safely **batch** adjacent steps into one capability slice?
7. Is this split reducing risk, or just slowing progress?
8. Are tests **tiered correctly** per `docs/ai/TEST_ROUTING.md`?
9. Have generic constraints been replaced by a **named safety pack**?
10. Is the **build archetype** named?
11. Is acceptance evidence specific?
12. Is the stop condition explicit?
13. HANDOFF.md required inside PR? **Update by replacing/summarizing, not appending.**
14. README excluded unless public/setup changed?
15. Mobile-safe copy block?
16. Usage estimate included?
17. For PR review: cheap merge gate first, deep audit only if suspicious?
18. Budget gate: can this be split/downgraded to avoid extra usage?
19. For UI work: did the UI budget gate approve the scope?
20. After heavy Claude PR: does the prompt tell user to stop that Claude session?
21. Does any Medium/High prompt include a timeout/checkpoint rule?
22. For complex refactors: did the split gate reduce the task to one coherent **capability slice**?

If any check fails, rewrite before showing the user.

## Compact templates

### 1. Capability Slice Implementation

```
<task_delta>
[The slice. 2-6 lines.]
</task_delta>

<repo_context>
Roadmap: [stage] / build queue: [item].
</repo_context>

<safety_packs>
[Named packs.]
</safety_packs>

<build_archetype>
capability-slice
</build_archetype>

<anchor_files>
[1-3 primary files. Fallback reads only if blocked.]
</anchor_files>

<acceptance_evidence>
[Tier name from TEST_ROUTING.md + specific bundle. Specific snapshot/Concierge card/UI evidence.]
</acceptance_evidence>

<stop_condition>
[When to stop instead of expanding.]
</stop_condition>
```

### 2. Backend-only Scaffold / Promotion Gate

```
<task_delta>
Scaffold [feature] disabled behind [flag/contract]. No visible behavior change.
</task_delta>

<safety_packs>
Backend-only Scaffold Pack, No Visible Behavior Change Pack, Test Tier Pack.
</safety_packs>

<build_archetype>
disabled-promotion-scaffold
</build_archetype>

<acceptance_evidence>
[Tier 1 contract bundle green. Visible surfaces unchanged.]
</acceptance_evidence>

<stop_condition>
Do not flip visibility. Do not change card contract shape.
</stop_condition>
```

### 3. Runtime Bug / Sev 1 Full Plumbing Fix

```
<task_delta>
Fix [symptom] root cause across [seam]. Restore [behavior] end-to-end.
</task_delta>

<safety_packs>
Runtime/API Contract Pack, Evidence/Claim Safety Pack, Test Tier Pack, [domain pack].
</safety_packs>

<build_archetype>
full-plumbing-root-cause-fix
</build_archetype>

<runtime_evidence>
[Railway log excerpt, provider response, snapshot diff. Inline only the relevant lines.]
</runtime_evidence>

<acceptance_evidence>
[Specific Tier 1 bundle previously failing now passes. No regression.]
</acceptance_evidence>

<stop_condition>
Do not patch a symptom. If the durable fix exceeds this slice, stop and propose the split.
</stop_condition>
```

### 4. UI Surface Pass with Budget

```
<task_delta>
Polish [surface] under [phase].
</task_delta>

<safety_packs>
No Mock/Sample Visible Data Pack, AI Concierge Card Contract Pack, Test Tier Pack.
</safety_packs>

<build_archetype>
UI-surface-pass
</build_archetype>

<ui_budget>
Phase: [one page / one component]
Max files: [n]
Primary surfaces: [screens/components]
Forbidden surfaces: [what not to touch]
Decision: APPROVE
</ui_budget>

<acceptance_evidence>
[Screenshot diff. Visual merge gate. No backend/API/business-logic change.]
</acceptance_evidence>

<stop_condition>
Do not exceed max files. No backend changes.
</stop_condition>
```

### 5. PR Merge Gate

```
<task_delta>
Review PR [link] for merge.
</task_delta>

<safety_packs>
Evidence/Claim Safety Pack, [domain pack if relevant].
</safety_packs>

<build_archetype>
merge-gate
</build_archetype>

<acceptance_evidence>
Merge recommendation: MERGE / DO NOT MERGE; blocking issues only; tests run + results; SQL Yes/No; HANDOFF.md edited Yes/No.
</acceptance_evidence>

<stop_condition>
Do not fix; report. Do not run broad discovery.
</stop_condition>
```

### 6. Workflow Update

```
<task_delta>
Update [workflow doc(s)] to [resolve / clarify / consolidate].
</task_delta>

<safety_packs>
Workflow update only — no product code, no UI, no SQL.
</safety_packs>

<build_archetype>
workflow-update
</build_archetype>

<acceptance_evidence>
Docs read cleanly; named gates exist; HANDOFF.md updated by replacing/summarizing (not appending).
</acceptance_evidence>

<stop_condition>
No product code changes. Do not introduce new OS version labels.
</stop_condition>
```

## HANDOFF update guidance

`docs/ai/HANDOFF.md` is current state only — not a historical log. The PR's HANDOFF edit replaces or summarizes the affected section. If HANDOFF.md is approaching ~500 lines, compact first.

## Budget gate

Default monthly budget target: ChatGPT Plus + Claude Pro only. Avoid extra usage. Before any Medium-High/High usage prompt, try Codex first if the task is a bug fix, audit, refactor, or <=3 primary files.

## Required usage footer for non-trivial prompts

Add this block verbatim at the end of any non-trivial Travel implementation prompt:

```
Usage ledger: If tooling exists, save a baseline before work; before opening/updating the PR, append one sanitized row to docs/ai/USAGE_LEDGER.md with the actual PR number if available, prompt ID, phase, model, chat strategy, repo area, main drivers, waste classification, follow-up count, and delta fields when available. If tooling is unavailable, still append a manual row with those metadata fields and mark token/delta fields unavailable. Do not claim usage is tracked unless docs/ai/USAGE_LEDGER.md is actually changed in the PR. Keep raw .ai/usage files uncommitted.

Usage discipline: Keep discovery narrow; do not run broad repo scans, parallel agents, or full suites unless focused validation fails or this prompt explicitly asks for them.
```

## Session stop rule

Any prompt expected to create a Medium-High/High PR must include a final instruction: "After opening the PR, stop. Do not propose the next implementation prompt."
