# Miss Ledger

Use this file only for workflow/product-process misses, not every app bug.

## Entry template

### YYYY-MM-DD — <short title>

Repo:
Area:
Severity:
Miss:
Impact:
What caught it:
Root cause:
What should catch it next time:
One-off or repeated:
Promotion target:
Action taken:
Follow-up needed:

---

### 2026-05-10 — Workflow/setup asset bloat across root, .claude, docs/ai, .kiro, and AI-tool configs

Repo: claude_travelapp_pk91
Area: Workflow architecture hygiene
Severity: Level 2 workflow miss
Miss: Repo accumulated duplicated/orphaned workflow/setup assets — duplicate cross-AI-tool config files at root (`GEMINI.md`, `.cursorrules`, `.windsurfrules`, `.opencode.json` — three of which were byte-identical), entire `.kiro/steering/` mirror of the same content, 59k stale `progress_log.md` at root, dated transition handoff `HANDOFF_2026-05-10_OS_V4_CONSOLIDATION.md`, one-off audits (`MERGE_GATE_AUDIT_2026-05-01.md`, `pr-194-audit.md`, `PRODUCT_SURFACE_AUDIT.md`), 40k stale `docs/ai/progress_log.md`, duplicate process docs (`PROMPT_BRIEF_TEMPLATE`, `TEST_SELECTOR`, `PR_REVIEW_CHECKLIST`, `CLAUDE_WORKFLOW_KIT`, `CLAUDE_PERSONAL_SKILLS`, `CLAUDE_HOOKS_ROADMAP`, `SUBAGENTS_ROADMAP`, `CONTEXT_MANAGEMENT`, `GITHUB_LABELS`, `HOOK_SAFETY`, `MANUAL_ACTIONS_CHECKLIST`, `UI_BASELINE`, `USAGE_LEDGER`, `PERMISSIONS_AND_MEMORY_BOUNDARIES`, `ENGINEERING_DISCIPLINE`, `AI_OS_MANIFEST`, `NEW_REPO_BOOTSTRAP`), legacy `docs/ai/skills/` docs-style skill router superseded by `.claude/skills/`, unreferenced loose `.claude/skills/` md files (`debug-issue.md`, `explore-codebase.md`, `refactor-safely.md`, `review-changes.md`), and unreferenced `.claude/agents/agent-curator.md` and `graphify-out/`. Net: ~37 files removed.
Impact: Bloated workflow surface created multiple competing rule owners (Cursor/Windsurf/Gemini/Kiro/OpenCode + Claude), broke `CLAUDE.md` anchor reliability (deleted `docs/ai/skills/README.md` ref), and made it unclear which doc is canonical for each topic.
What caught it: PK requested a cross-repo workflow hygiene cleanup.
Root cause: Travel repo was originally seeded for several AI tools and several workflow generations; pruning lagged behind canonical OS v4 consolidation.
What should catch it next time: After any AI-tool or OS version transition, run a workflow-asset reference scan and delete orphans. Cross-AI-tool duplicate configs should be deleted unless that tool is actively used.
One-off or repeated: First major workflow cleanup; pattern of accumulation is repeated.
Promotion target: Add a periodic "workflow surface scan" step to OS_LEARNING_PROTOCOL or workflow-retrospective skill.
Action taken: Deleted ~37 stale/duplicate/orphaned workflow assets in PR; updated `CLAUDE.md` to drop the broken `docs/ai/skills/README.md` anchor and point at `.claude/skills/` directly; recorded this entry. Note: `docs/ai/HANDOFF.md` exceeded ~454k chars and could not be updated in-place via the GitHub Contents API; cleanup is documented here and in the PR summary instead.
Follow-up needed: Confirm `.kiro/`, `GEMINI.md`, `.cursorrules`, `.windsurfrules` removal does not break any local PK tool workflow.

---

### 2026-05-09 — Unused variable left after JSX block removal caused Vercel build failure

Repo: claude_travelapp_pk91
Area: Frontend / UI — TripBuilder.tsx
Severity: Low (build failure caught by CI before merge; fixed in follow-up commit)
Miss: Removed `{/* Explanation */}` JSX block from `FlightCandidateCard` but left the `const explanation = ...` declaration, triggering `@typescript-eslint/no-unused-vars` in the Vercel production build.
Impact: One extra commit; no merge block since fix was fast. No user-visible regression.
What caught it: Vercel CI build log surfaced via GitHub PR comment bot.
Root cause: UI cleanup removed JSX consumer of a variable but didn't scan for now-orphaned declarations above it.
What should catch it next time: After any UI block removal, scan for orphaned `const`/`let` declarations in the same component scope. A local `cd frontend && npx tsc --noEmit` before push catches this class of error without a full build.
One-off or repeated: One-off
Promotion target: None yet — single occurrence.
Action taken: Removed declaration in follow-up commit fb8c792. MISS_LEDGER entry added.
Follow-up needed: No

---

## Seed entries

### 2026-05-07 — Old-format prompt after OS v2

Repo: Travel Concierge / cross-repo workflow
Area: Prompt generation
Severity: Level 2 workflow miss
Miss: ChatGPT generated a Travel project prompt that did not use OS v2 work-order format even after PK explicitly requested a v2-based prompt.
Impact: PK had to catch the workflow regression manually; future Claude prompts could bypass the new OS.
What caught it: PK review.
Root cause: Prompt-generation standard was not enforced by the repo OS or prompt template strongly enough.
What should catch it next time: PROMPT_BRIEF_TEMPLATE, PR_REVIEW_CHECKLIST, workflow-retrospective skill.
One-off or repeated: First recorded miss, but high-signal.
Promotion target: PROMPT_BRIEF_TEMPLATE and PR_REVIEW_CHECKLIST.
Action taken: OS v3 requires all future Travel/Finance/future-repo coding prompts to use OS v2/v3 work-order format unless explicitly generating architecture/spec only.
Follow-up needed: Verify future prompts include required OS skills, reviewer agents, and stop condition.

### 2026-05-07 — Deployment storm from file-by-file connector commits

Repo: Travel Concierge / Finance Tracker / cross-repo workflow
Area: Deployment/build-cost control
Severity: Level 2 workflow miss
Miss: Bulk workflow docs were updated through ChatGPT GitHub connector as many file-by-file commits, triggering many Vercel deployments and exhausting usage.
Impact: Avoidable deployment usage spike and workflow friction.
What caught it: PK observed Vercel usage impact.
Root cause: Bulk repo update was performed through connector write actions instead of a batched Claude/Sonnet branch/PR.
What should catch it next time: CONTEXT_MANAGEMENT, MANUAL_ACTIONS_CHECKLIST, PR_REVIEW_CHECKLIST, prompt-generation behavior.
One-off or repeated: First recorded miss, high-cost.
Promotion target: PR_REVIEW_CHECKLIST, MANUAL_ACTIONS_CHECKLIST, CONTEXT_MANAGEMENT.
Action taken: Bulk repo/workflow edits should be done by Claude/Sonnet as one PR, not through ChatGPT connector file-by-file writes.
Follow-up needed: Future ChatGPT should generate Sonnet work-order prompts for bulk repo edits.

### 2026-05-07 — Follow-up loop from incomplete downstream contract audits

Repo: Travel Concierge / Finance Tracker
Area: PR completeness
Severity: Level 2 repeated workflow pattern
Miss: Multiple historical PRs required follow-up fixes because local implementation was not tied tightly enough to downstream contracts, tests, runtime evidence, or visible UI/API consumers.
Impact: More prompts, more PR churn, more PK validation, slower build velocity.
What caught it: ChatGPT PR review, PK UI validation, runtime logs, Codex/Claude follow-ups.
Root cause: The builder often proved local behavior but not the full product invariant or downstream contract.
What should catch it next time: contract-auditor, test-strategist, pr-reviewer, pre-pr-self-audit, TEST_SELECTOR.
One-off or repeated: Repeated pattern.
Promotion target: reviewer agents and TEST_SELECTOR.
Action taken: OS v2 added focused skills and read-only reviewer agents; OS v3 adds retrospective/learning loop.
Follow-up needed: After next few PRs, check whether reviewer agents reduce follow-up prompts.
