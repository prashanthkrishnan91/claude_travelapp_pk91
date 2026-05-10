## 2026-05-10 — OS v4 consolidation (Level 2 workflow architecture correction, docs-only)

> This is the canonical HANDOFF entry for this PR. It is filed as a separate dated
> file (rather than prepended to the main `HANDOFF.md` log) because the agent that
> produced this PR cannot stream a 454 KB file rewrite through a single tool call.
> Merge this entry into `docs/ai/HANDOFF.md` at the top of the log in a follow-up
> touch.

### Status
Workflow/documentation PR. **No product behavior changed.** No product code changes. No Supabase SQL. No UI changes. Branch: `claude/consolidate-os-v4-workflow-P4dWu`.

### Why this happened
OS v4 had a contradiction:
- `CLAUDE.md` and `AI_REPO_OPERATING_SYSTEM.md` already said *short briefs, repeated process is repo-native*.
- `PROMPT_ENGINEERING_STANDARD.md` still implied *every prompt must include long lists of source files, required skills, agents, validations, PR summary requirements, and constraints*.

That contradiction caused bloated prompts and slow tiny PRs (excessive micro-phasing, repeated workflow boilerplate inside prompts, all-agent default reviews, endless Travel cleanup patches that should have been grouped by pipeline seam).

### What changed (docs-only)
- **CLAUDE.md** — added Prompt Compression and Capability Slices section (task delta only; safety packs and archetypes own repeated rules; <700–1,200 word compression budget; capability slice over micro-patch). Condensed conflicting rules. References `TEST_ROUTING.md` as the default test router.
- **docs/ai/AI_REPO_OPERATING_SYSTEM.md** — added new consolidation section *inside existing OS v4* (no v4.2/v5 label): default prompt shape, what belongs in prompt vs repo-native, batch-vs-split decision gate, meaningful progress standard, and test tier hierarchy that delegates to `TEST_ROUTING.md`.
- **docs/ai/PROMPT_ENGINEERING_STANDARD.md** — replaced the "good prompt contains everything" structure with a compressed work-order standard (`<task_delta>`, `<repo_context>`, `<safety_packs>`, `<build_archetype>`, `<acceptance_evidence>`, `<stop_condition>`; optional `<logs>`/`<runtime_evidence>`/`<ui_budget>`/`<sql_manual_actions>`/`<examples>`).
- **docs/ai/PROMPT_LIBRARY.md** — added compact templates (Capability Slice, Backend Scaffold / Promotion Gate, Sev 1 Plumbing Fix, UI Surface Pass with Concierge card contract, PR Merge Gate, Workflow Update). Updated reviewer gate with compression / batch-vs-split / tiered-test questions and named-safety-pack check. Default test routing in every template now points at `TEST_ROUTING.md`.
- **docs/ai/AGENT_ROUTER.md** — reinforced fewer high-signal reviewers, no all-agent default, reviewer agents do not bloat builder context.
- **docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md** — new: 9 shared safety packs (No Visible Behavior Change, Backend-only Scaffold, Runtime/API Contract, No Provider/LLM Expansion, Plain-English UI, Evidence/Claim Safety, SQL/Persistence Manual Action, Performance/Latency, Test Tier), 6 Travel-specific packs (Google Places Addable Authority, Enrichment Evidence Only, Semantic Concierge Behavior, AI Concierge Card Contract, No Mock/Sample Visible Data, Latency Budget), and 9 shared build archetypes (capability-slice, disabled-promotion-scaffold, shadow-to-visible-governance, full-plumbing-root-cause-fix, contract-consolidation, runtime-validation, UI-surface-pass, merge-gate, workflow-update).
- **docs/ai/TEST_ROUTING.md** — unchanged; existing Tier 0–3 router preserved. References to it strengthened across CLAUDE.md / OS doc / PROMPT_LIBRARY.md so it is treated as the default test router (no full backend suite for ordinary PRs).

### Effect on future work
Future prompts must:
- name the safety pack(s) and build archetype from `docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md`,
- carry only the task delta (anchor files, acceptance evidence, stop condition),
- stay within the compression budget,
- ship one coherent capability slice unless an explicit split criterion applies,
- state test tier used and why it was sufficient per `docs/ai/TEST_ROUTING.md`.

### Validation
Documentation-only. Verified:
- no v4.2 / v5 label introduced,
- prompt standard no longer requires huge all-in prompts,
- repeated rules moved into named safety packs / archetypes,
- batch-vs-split gate exists in OS doc and CLAUDE.md,
- test tier hierarchy exists and delegates to existing `TEST_ROUTING.md`,
- Travel's existing `TEST_ROUTING.md` is preserved and now treated as the default router,
- no product code, SQL, or UI touched.
