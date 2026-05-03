# Issue Severity Routing Gate

Use this gate before generating Claude/Codex prompts for bugs, regressions, broken flows, or suspicious behavior.

The goal is to choose the right move: tiny patch, focused root-cause fix, full plumbing analysis, or split plan. Do not default to Codex patching when the symptoms suggest an integration or end-to-end flow issue.

## Severity levels

### Level 0 — Tiny patch

Use when all are true:

- Root cause is obvious.
- One file or one small component is implicated.
- No persistence, auth, provider, cache, or cross-screen flow is involved.
- No prior patch failed for this same issue.

Route:

- Model: Codex.
- Skill: `docs/ai/skills/bugfix.md`.
- Merge gate: optional for trivial docs/UI copy; otherwise cheap Codex gate.

Examples:

- Typo/copy issue.
- One class causing dark-on-dark text.
- Button label or disabled state wrong when logic is already correct.

### Level 1 — Focused root-cause fix

Use when:

- The issue has a likely root cause in one subsystem.
- It may touch 1-3 files.
- Tests can be focused.
- The end-to-end flow is understandable without broad architecture work.

Route:

- Model: Codex for mechanical fixes; Sonnet for nuanced multi-file implementation.
- Skill: `docs/ai/skills/bugfix.md` or `docs/ai/skills/implementation.md`.
- Require `docs/ai/ROOT_CAUSE_QUALITY_BAR.md`.

Examples:

- API mapper misses one field.
- Snapshot hydration order is wrong.
- A route validates ownership in one path but not another.

### Level 2 — Full plumbing analysis + fix

Use when any are true:

- A patch already failed or revealed another symptom.
- The same issue has required two or more patches or audits.
- Symptoms cross frontend/backend/API/cache/provider/persistence boundaries.
- Logs disagree with UI behavior.
- Data exists in backend but disappears in frontend.
- A feature works until refresh, reload, auth change, cache hit, or move between screens.
- User-facing flow is blocked and likely requires tracing the full path.
- Removing UI would hide the problem instead of fixing it.

Route:

- Model: Sonnet for one-pass full plumbing analysis + scoped fix.
- Codex may do a read-only map first only if primary files are unknown.
- Skill: `docs/ai/skills/implementation.md` plus `docs/ai/ROOT_CAUSE_QUALITY_BAR.md`.
- Include timeout budget and stop-after-PR if Medium-High/High.
- Do one merge gate after the integrated fix, not after every speculative micro-patch.

Required prompt language:

```md
This is not a patch request. Perform full plumbing analysis across the named end-to-end flow, identify the root cause, and implement the complete scoped fix. Do not remove UI or suppress errors to make the symptom disappear. If the durable fix exceeds this scope, stop and propose the split.
```

### Level 3 — Split plan before implementation

Use when:

- The durable fix requires 3+ categories from the complex refactor split gate.
- Schema/auth/provider/business logic/UI/history/analytics are all involved.
- The agent would need to redesign multiple workflows or screens.
- The scope is likely High usage or timeout-prone.

Route:

- Model: Opus or Sonnet for planning only, with budget review; Codex for repository map if needed.
- No implementation in the planning prompt.
- Produce 2-4 PR split with tests and SQL notes.

## Patch exhaustion rule

After one failed patch on the same bug, reclassify severity before generating another patch.

After two related patches, stop patching. Escalate to Level 2 full plumbing analysis or Level 3 split plan.

## Merge-gate batching rule

Do not run a merge audit after every speculative patch when the underlying issue is unresolved. For Level 2 issues, prefer:

1. One full plumbing analysis + scoped fix PR.
2. One cheap merge gate on the integrated PR.
3. Deep audit only if the merge gate finds a specific suspicious risk.

## Required output from project chat before giving a prompt

When a user reports a bug or broken flow, the project chat should state:

```md
Severity classification: Level 0 / 1 / 2 / 3
Reason:
Recommended next move: patch / focused root-cause fix / full plumbing analysis / split plan
Model:
Why not the cheaper/smaller route:
```

Then generate the prompt using the chosen route.
