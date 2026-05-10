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
6. Can this task safely **batch** adjacent steps into one capability slice, or is the proposed split actually reducing risk?
7. Is this split reducing risk, or just slowing progress?
8. Are tests **tiered correctly** per `docs/ai/TEST_ROUTING.md`, instead of full-suite or default unit-test ceremony?
9. Have generic constraints been replaced by a **named safety pack** from `docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md`?
10. Is the **build archetype** named?
11. Is acceptance evidence specific (test bundle / snapshot / Concierge card field / screenshot)?
12. Is the stop condition explicit?
13. HANDOFF.md required inside PR? **Update by replacing/summarizing, not appending.**
14. README excluded unless public/setup changed?
15. Mobile-safe copy block?
16. Usage estimate included?
17. For PR review: cheap merge gate first, deep audit only if suspicious?
18. Budget gate: can this be split/downgraded to avoid extra usage? If extra usage may be needed, did the Code Committee approve it?
19. For UI work: did the UI budget gate approve the scope?
20. After heavy Claude PR: does the prompt tell user to stop that Claude session and review elsewhere?
21. Does any Medium/High prompt include a timeout/checkpoint rule?
22. For complex refactors: did the split gate reduce the task to one coherent **capability slice** (not a micro-phase)?

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
Backend-only Scaffold Pack, No Visible Behavior Change Pack, AI Concierge Card Contract Pack (if Concierge-adjacent), Test Tier Pack.
</safety_packs>

<build_archetype>
disabled-promotion-scaffold
</build_archetype>

<anchor_files>
[Primary backend files. No UI files.]
</anchor_files>

<acceptance_evidence>
[Tier 1 contract bundle green per TEST_ROUTING.md. Visible surfaces unchanged. Flag/gate verified off.]
</acceptance_evidence>

<stop_condition>
Do not flip visibility. Do not change card contract shape. If promotion is requested, propose a follow-up shadow-to-visible-governance slice.
</stop_condition>
```

### 3. Runtime Bug / Sev 1 Full Plumbing Fix

```
<task_delta>
Fix [symptom] root cause across [seam]. Restore [behavior] end-to-end.
</task_delta>

<safety_packs>
Runtime/API Contract Pack, Evidence/Claim Safety Pack, Latency Budget Pack (if latency-sensitive), Test Tier Pack, [domain pack].
</safety_packs>

<build_archetype>
full-plumbing-root-cause-fix
</build_archetype>

<anchor_files>
[Files implicated by the trace.]
</anchor_files>

<runtime_evidence>
[Railway log excerpt, provider response, snapshot diff. Inline only the relevant lines.]
</runtime_evidence>

<acceptance_evidence>
[Specific Tier 1 bundle from TEST_ROUTING.md previously failing now passes. Runtime trace shows fix. No regression in adjacent surfaces.]
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
No Mock/Sample Visible Data Pack, AI Concierge Card Contract Pack (if Concierge cards), No Visible Behavior Change Pack (visual-only), Test Tier Pack.
</safety_packs>

<build_archetype>
UI-surface-pass
</build_archetype>

<ui_budget>
Phase: [one page / one component]
Max files: [n]
Primary surfaces: [screens/components]
Forbidden surfaces: [what not to touch]
Stop condition: [when to stop instead of expanding]
Decision: APPROVE
</ui_budget>

<anchor_files>
[Primary UI files only.]
</anchor_files>

<acceptance_evidence>
[Screenshot diff. Visual merge gate. No backend/API/business-logic change. Concierge card field contract preserved.]
</acceptance_evidence>

<stop_condition>
Do not exceed max files. No backend changes. If primary surfaces are unknown, stop and request a Codex surface map.
</stop_condition>
```

### 5. PR Merge Gate (cheap, Codex preferred)

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

<anchor_files>
PR diff and changed files only.
</anchor_files>

<acceptance_evidence>
Merge recommendation: MERGE / DO NOT MERGE; blocking issues only; tests run + results (state TEST_ROUTING.md tier); Supabase SQL Yes/No; HANDOFF.md edited Yes/No; up to 3 non-blocking follow-ups.
</acceptance_evidence>

<stop_condition>
Do not fix; report. Do not run broad discovery. If a blocker is found, stop and report.
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

<anchor_files>
[Workflow docs to change.]
</anchor_files>

<acceptance_evidence>
Docs read cleanly; named gates exist; references to safety packs / archetypes / TEST_ROUTING.md are correct; HANDOFF.md updated by replacing/summarizing (not appending).
</acceptance_evidence>

<stop_condition>
No product code changes. Do not introduce new OS version labels (e.g., v4.2 / v5).
</stop_condition>
```

## HANDOFF update guidance

`docs/ai/HANDOFF.md` is current state only — not a historical log. Every prompt that touches HANDOFF must follow these rules:

- The PR's HANDOFF edit replaces or summarizes the affected section. It does **not** append a new dated entry per PR.
- Recent meaningful PRs section lists at most 5–10 lines, one-liners only. Older entries roll out as new ones roll in.
- If HANDOFF.md is approaching ~500 lines, the prompt must include a compaction step **before** adding any new content.
- Resolved risks / closed issues are removed, not preserved.
- Durable historical detail belongs in `docs/ai/MISS_LEDGER.md` or `docs/product/DECISION_LOG.md`, not in HANDOFF.

This matches the `Handoff maintenance rule` in `docs/ai/AI_REPO_OPERATING_SYSTEM.md` and the read-first anchor in `CLAUDE.md`.

## Budget gate

Default monthly budget target: ChatGPT Plus + Claude Pro only. Avoid extra usage.

Before any prompt likely to be Medium-High or High usage:

1. Try Codex first if task is bug fix, audit, refactor, or <=3 primary files.
2. Prefer one coherent capability slice; split only on the explicit batch-vs-split criteria.
3. Limit primary edit targets to the smallest set the slice needs.
4. Move logs/examples into compact `<runtime_evidence>` only when they materially help.
5. Exclude README unless public/setup behavior changed.
6. Use cheap merge gate before any deep audit.
7. Defer non-blocking improvements to a follow-up list, not the current prompt.

## UI budget gate

Any prompt containing UI / visual / design / premium / polish / redesign / theme / layout / aesthetic must include a `<ui_budget>` block (see template 4). Hard rules:

- Full-app UI upgrades default to SPLIT.
- Sonnet UI implementation max scope: 6 files unless Code Committee explicitly approves more.
- If primary UI files are unknown, run Codex surface map first; do not use Sonnet discovery.
- Page-specific UI polish targets one page/screen at a time.
- UI merge gates use Codex by default and read diff only.
- No prompt may say "make the whole app premium" without max files + phase boundary.

## Extra usage approval gate

If extra usage may be required, do not present the prompt until the Code Committee review is complete (Need / Cheapest path / Risk of not doing / Estimated usage / Extra usage risk / Decision). Default decision is REJECT unless blocking, security/data-loss, or rework-avoiding.

## Usage estimate rule

Every prompt must include outside the copy block:

- Expected session usage: Low / Medium / High
- Expected extra cost risk: Low / Medium / High
- Why: one sentence

## Discovery budget rule

When paths are known, the prompt should specify:

- no find/grep/glob for initial exploration
- read primary anchor + tests first
- fallback files only if blocked, and state why
- focused tests only per `docs/ai/TEST_ROUTING.md`; broader tier only if focused tests fail for unknown reasons

## Timeout / continue budget rule

For Medium/High prompts include:

- checkpoint before time/context limit
- max two continues, then fresh chat with checkpoint summary
- do not start broad new discovery after a continue

## Session stop rule

Any prompt expected to create a Medium-High/High PR must include a final instruction: "After opening the PR, stop. Do not propose the next implementation prompt."
