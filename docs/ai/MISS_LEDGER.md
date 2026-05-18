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

### 2026-05-18 — PR #436: empty trigger commit not pushed before session ended

Repo: claude_travelapp_pk91
Area: Workflow enforcement / CI trigger discipline
Severity: Level 1 (minor delay; fixed in resumed session)
Miss: After updating the PR body to fix the AI PR Readiness Check runtime gate, an empty commit was composed locally (`git commit --allow-empty`) to retrigger CI with the updated body. The session ended (context limit) before the push completed. In the resumed session, `git status` showed "Your branch is ahead of origin by 1 commit" — the push had not happened. The CI "failure" at 13:19 UTC was from a prior trigger, not from the empty commit.
Impact: CI appeared still failing after the body fix; one session cycle wasted re-diagnosing.
What caught it: `git status` check at the start of the resumed session showing branch ahead of origin by 1.
Root cause: Session ended mid-task (pre-push). No verification step that the push was received by origin before concluding CI would retrigger.
What should catch it next time: After any `git push` (including empty commits), always verify with `git status` that the branch is not ahead of origin (i.e., `git log --oneline -1 origin/<branch>` matches local HEAD). Do not rely on CI starting as proof of push.
One-off or repeated: One-off (session boundary race).
Promotion target: MISS_LEDGER only.
Action taken: Pushed the empty commit at session resume; CI passed on that run.
Follow-up needed: None.

---

### 2026-05-17 — PR #420: test file created but not wired into npm test script

Repo: claude_travelapp_pk91
Area: Test wiring / package.json test script
Severity: Level 1 (pre-merge catch; no production impact)
Miss: `itinerary-day-mobile-redesign-8l.test.mjs` was created and committed in the 8L PR but not added to the explicit file list in `frontend/package.json`. The `npm test` command uses an explicit file list (not a glob), so new test files must be manually appended. The PR body claimed "1715 tests, 0 failures" — the 63 new tests were never running; the real count after wiring was 1778.
Impact: PR body overstated test coverage; new 8L contract tests were not executed by CI or local `npm test`. Caught pre-merge via a follow-up task.
What caught it: External review noting the test file was not in package.json.
Root cause: `frontend/package.json` uses an explicit file list (not a glob pattern like `tests/**/*.test.mjs`). Each new test file requires a manual addition. This was overlooked during initial implementation.
What should catch it next time: Whenever creating a new test file in `frontend/tests/`, immediately add it to the `npm test` script in `package.json` in the same commit. Run `npm test` locally and verify the new test file's describe block appears in output before pushing.
One-off or repeated: One-off so far; the explicit-list pattern is a latent risk every time a test file is added.
Promotion target: `docs/ai/KNOWN_FAILURE_MODES.md` — add "new test file not wired into package.json npm test script" as a known failure mode.
Action taken: Added `tests/itinerary-day-mobile-redesign-8l.test.mjs` to `package.json` npm test script; test count corrected to 1778 in PR body and HANDOFF.md.
Follow-up needed: None — fixed before merge.

---

### 2026-05-17 — PR #420: PR body used `###` headings → CI hard-fail on required `##` section check

Repo: claude_travelapp_pk91
Area: Workflow enforcement / PR readiness gate
Severity: Level 2 gate failure (required follow-up commit + trigger commit)
Miss: PR #420 body used `### Summary`, `### Changes`, etc. (3-hash) instead of `## Summary`, `## Severity`, etc. (2-hash). The readiness checker does substring matching: `"## summary"` is NOT a substring of `"### summary"` because the third `#` replaces the space. All 6 required anchors (`## Summary`, `## Severity`, `## Validation`, `SQL / env / providers / UI`, `AI usage note`, `AI PR readiness`) were absent. Additionally, `docs/ai/USAGE_LEDGER.md` was not updated, causing a second hard failure (Level 1+ PR must commit a ledger row). Local readiness check passed because body was None (no `--github-event-path`), so `check_sections()` was skipped entirely.
Impact: CI red on first two pushes; required a USAGE_LEDGER commit, a PR body update, and an empty trigger commit.
What caught it: GitHub webhook CI failure notification.
Root cause: Third repeated occurrence of PR body composed from memory rather than from `.github/pull_request_template.md`. MISS_LEDGER had two prior entries for the same root cause; the promotion to `KNOWN_FAILURE_MODES.md` did not prevent recurrence.
What should catch it next time: (1) Always start PR body from `.github/pull_request_template.md` verbatim. (2) Run readiness check with an actual body file: `python3 scripts/workflow/ai_pr_readiness_check.py --pr-body-file /tmp/body.txt --base-ref origin/main`. (3) Commit USAGE_LEDGER row in the same initial commit as code changes.
One-off or repeated: **Repeated** (third occurrence). Root cause identical to 2026-05-16 PR #394 and PR #397 entries.
Promotion target: `docs/ai/KNOWN_FAILURE_MODES.md` — strengthen existing entry; note that `### headings` silently fail the `##` substring check.
Action taken: Added USAGE_LEDGER row; updated PR body with all required `##`-level sections; pushed trigger commit; CI passed.
Follow-up needed: None — fixed before merge.

---

### 2026-05-16 — PR #397: PR body composed from scratch → same CI hard-fail as PR #394

Repo: claude_travelapp_pk91
Area: Workflow enforcement / PR readiness gate
Severity: Level 2 gate failure (required fix commit + re-run)
Miss: PR #397 body missing `## Severity`, `## Validation`, `SQL / env / providers / UI` — same as the 2026-05-16 PR #394 entry. PR body authored from scratch instead of from `.github/pull_request_template.md`.
Impact: CI AI PR Readiness Check red on first push; required a PR body edit and new trigger commit.
What caught it: CI failure on `AI PR Readiness Check` job.
Root cause: Repeated: PR body generated from memory rather than from the template, even after the same miss was recorded for PR #394.
What should catch it next time: The `pr-summary` skill must explicitly state "start from `.github/pull_request_template.md` verbatim — do not compose from scratch." Same rule added to `docs/ai/KNOWN_FAILURE_MODES.md`.
One-off or repeated: **Repeated** (second occurrence — same root cause as 2026-05-16 PR #394 entry).
Promotion target: `docs/ai/KNOWN_FAILURE_MODES.md` — add explicit entry for "PR body composed from scratch → CI section failures." (Two-miss threshold reached.)
Action taken: Edited PR body to add all required sections; pushed trigger commit; CI passed on second run.
Follow-up needed: Promotion applied to `KNOWN_FAILURE_MODES.md` in same commit as this ledger entry.

---

### 2026-05-16 — PR body sections missing → CI hard-fail despite local PASS

Repo: claude_travelapp_pk91
Area: Workflow enforcement / PR readiness gate
Severity: Level 2 gate failure (blocked merge until patched)
Miss: PR #394 body was missing `## Severity`, `## Validation`, and `SQL / env / providers / UI` anchors, plus runtime failure-seam evidence. Local `ai_pr_readiness_check.py` passed because without `--github-event-path` the body is None and `check_sections()` is skipped. CI reads the real body from the GitHub event JSON and enforces all required sections as hard failures.
Impact: CI red on first push; required a follow-up PR body update and new commit to rerun CI.
What caught it: Reviewer listed the exact missing anchors; CI log confirmed 4 hard failures.
Root cause: PR body generated from memory rather than from the PR template. Local checker silently skips section checks when no body file/event path is provided, creating a false PASS signal that doesn't match CI behavior.
What should catch it next time: (1) Always write PR bodies from `.github/pull_request_template.md` — do not compose from scratch. (2) Run `python3 scripts/workflow/ai_pr_readiness_check.py --pr-body-file <file>` locally using an actual body file before pushing, not the no-arg form. (3) Add `## Severity` and `## Validation` with `SQL / env / providers / UI` to the PR template as named anchors so they cannot be accidentally omitted.
One-off or repeated: One-off for this PR; the CI-vs-local divergence is a latent risk for every PR.
Promotion target: `.github/pull_request_template.md` — add explicit `## Severity` and `## Validation` sections; `docs/ai/KNOWN_FAILURE_MODES.md` — note CI-vs-local checker divergence.
Action taken: Added missing sections to PR body; added failure-seam evidence; pushed fix commit.
Follow-up needed: Update `.github/pull_request_template.md` to include `## Severity`, `## Validation`, and `SQL / env / providers / UI` as first-class sections.

---

### 2026-05-15 — AI PR Readiness Gate v1 permitted Level 1+ PRs to skip ledger rows by claiming "usage unavailable"

Repo: claude_travelapp_pk91
Area: Workflow enforcement / usage tracking
Severity: Level 2 readiness gate miss
Miss: The initial S-grade readiness checker allowed Level 1+ PRs to skip committing a ledger row by writing "Usage unavailable — [reason]" in the PR body. This left no durable audit trail for those PRs; tooling unavailability should mean token/delta values are unavailable, not that the ledger row can be skipped.
Impact: Incomplete audit trail; some Level 1+ PRs have no ledger rows, breaking the assumption that every non-trivial PR has a committed row.
What caught it: Workflow review flagged that the exemption was too broad and inconsistent with the intent that Level 1+ PRs must always have ledger rows.
Root cause: Initial gate implementation conflated two concepts: (1) tooling unavailable → numeric fields marked unavailable; (2) usage unavailable → entire row skipped. These should have been separate.
What should catch it next time: `scripts/workflow/ai_pr_readiness_check.py` (Check A, strict mode) now requires Level 1+ PRs to change `docs/ai/USAGE_LEDGER.md` regardless of tooling availability. Token/delta fields may be marked `unavailable`, but the row must exist. Updated `AI_USAGE_TRACKING.md` and `AI_PR_READINESS_GATE.md` to clarify the distinction.
One-off or repeated: One-off implementation issue, caught during initial gate rollout.
Promotion target: `scripts/workflow/ai_pr_readiness_check.py` (strict ledger enforcement), `AI_USAGE_TRACKING.md` (clarified "unavailable" semantics), `AI_PR_READINESS_GATE.md` (hard-failure documentation).
Action taken: Updated `ai_pr_readiness_check.py` to enforce strict ledger requirement for Level 1+. Clarified docs. Updated PR template options. Added self-tests proving the enforcement.
Follow-up needed: Consider backfilling missing ledger rows for Level 1+ PRs that claimed "unavailable" and skipped the ledger.

---

### 2026-05-15 — Usage-ledger instruction repeatedly omitted from generated prompts

Repo: cross-repo
Area: Prompt generation / usage tracking
Severity: Level 2 repeated workflow miss
Miss: Prompts frequently omitted the usage-ledger instruction, resulting in no baseline capture before work and no committed ledger row after. PR bodies then claimed usage tracking without a committed ledger row.
Impact: Incomplete audit trail; readiness checker now enforces the claim-vs-reality mismatch at CI time.
What caught it: Pattern identified across multiple PRs during OS v4 S-grade enforcement review.
Root cause: Usage-ledger instruction was a CLAUDE.md reminder, not a repo-enforced contract. No CI check existed to detect claim-vs-reality mismatch.
What should catch it next time: `scripts/workflow/ai_pr_readiness_check.py` (Check A) hard-fails if PR body claims usage tracked but `docs/ai/USAGE_LEDGER.md` not changed. Usage footer required in PROMPT_ENGINEERING_STANDARD.md and PROMPT_LIBRARY.md templates.
One-off or repeated: Repeated pattern — promoted to gate rule.
Promotion target: ai_pr_readiness_check.py (Check A), PROMPT_ENGINEERING_STANDARD.md, PROMPT_LIBRARY.md.
Action taken: Added readiness checker, CI workflow, usage footer to prompt standards; updated CLAUDE.md hard rules.
Follow-up needed: No.

---

### 2026-05-15 — Same-chat continuation became expensive in production/debug loops

Repo: cross-repo
Area: Chat strategy / cost control
Severity: Level 2 repeated workflow miss
Miss: Same-chat was used for production debugging and multi-PR sequences, causing session context to grow large. Fresh chat was the stated default but not enforced.
Impact: Elevated token burn; session context carried prior-PR content into new slices.
What caught it: Pattern identified in ledger rows with high cumulative costs and multiple same-chat follow-up rows.
Root cause: Fresh-chat rule existed in CLAUDE.md prose but was not checked by any gate.
What should catch it next time: `scripts/workflow/ai_pr_readiness_check.py` (Checks G/H) warns on same-chat + production/debug and on follow-up count > 1 in same-chat.
One-off or repeated: Repeated — promoted to gate rule.
Promotion target: ai_pr_readiness_check.py (Checks G, H), CLAUDE.md PR Readiness Gate.
Action taken: Readiness checker checks G and H added; CLAUDE.md updated.
Follow-up needed: No.

---

### 2026-05-15 — Runtime fixes patched symptoms before proving the failure seam

Repo: cross-repo
Area: Runtime debugging / root-cause quality
Severity: Level 2 repeated workflow miss
Miss: Production-adjacent PRs described symptoms and applied patches without failure-seam evidence (exact log key, test that previously failed, reproduction boundary).
Impact: Follow-up PRs required; ledger showed preventable-follow-up waste.
What caught it: Pattern identified during OS v4 S-grade enforcement review.
Root cause: Runtime validation section in PR template existed but no gate enforced failure-seam evidence when runtime keywords appeared.
What should catch it next time: `scripts/workflow/ai_pr_readiness_check.py` (Check E) hard-fails if PR body references production/runtime/cache without failure-seam evidence.
One-off or repeated: Repeated — promoted to gate rule.
Promotion target: ai_pr_readiness_check.py (Check E).
Action taken: Check E added to readiness checker.
Follow-up needed: No.

---

### 2026-05-15 — Design-overhaul foundation work did not lead to visible adoption

Repo: cross-repo
Area: Design / UI workflow
Severity: Level 2 workflow miss
Miss: Design PRs shipped invisible infrastructure without classifying as foundation-only or planning visible adoption. Some PRs claimed "visual transformation" but changed only CSS token wiring.
Impact: Multiple foundation PRs accumulated without visible user-facing change.
What caught it: Pattern identified during OS v4 S-grade enforcement review.
Root cause: No classification requirement existed in the PR template for design overhaul scope.
What should catch it next time: `scripts/workflow/ai_pr_readiness_check.py` (Check F) requires scope classification and hard-fails if visual transformation is claimed without UI validation and not classified foundation-only.
One-off or repeated: Repeated — promoted to gate rule.
Promotion target: ai_pr_readiness_check.py (Check F).
Action taken: Check F added; AI_PR_READINESS_GATE.md documents the design gate.
Follow-up needed: No.

---

### 2026-05-15 — Patch loops continued after repeated misses instead of forcing escalation

Repo: cross-repo
Area: PR workflow / patch exhaustion
Severity: Level 2 repeated workflow miss
Miss: After two related follow-up patches, additional patches continued without fresh-chat escalation or full-plumbing analysis. The reclassification rule existed in CLAUDE.md but was not checked.
Impact: Patch loops accumulated preventable-follow-up waste; root cause remained undiagnosed.
What caught it: Pattern identified during OS v4 S-grade enforcement review.
Root cause: Patch exhaustion rule was instruction-only in CLAUDE.md; no CI check enforced it.
What should catch it next time: `scripts/workflow/ai_pr_readiness_check.py` (Check H) hard-fails on follow-up count >= 3 without escalation note; warns at count 2.
One-off or repeated: Repeated — promoted to gate rule.
Promotion target: ai_pr_readiness_check.py (Check H).
Action taken: Check H added to readiness checker.
Follow-up needed: No.

---

### 2026-05-15 — GitHub Actions merge-ref race condition caused stale git diff in diff-based CI (PR #381)

Repo: claude_travelapp_pk91
Area: CI workflow / git
Severity: Level 2 workflow miss — cost 3 extra CI debug cycles
Miss: `actions/checkout@v4` for `pull_request` events defaults to checking out `refs/pull/{n}/merge` (a synthetic merge commit GitHub pre-computes). When a new push arrives, GitHub may not update the merge ref before CI starts. A diff-based check (`git diff origin/main...HEAD`) against this stale merge commit sees an outdated file list — in this case missing `USAGE_LEDGER.md` even though it was committed to the branch. The readiness checker then reported it as unchanged, causing a spurious USAGE_LEDGER failure.
Impact: 3 spurious CI failures; 2 extra commits; ~20 min delay diagnosing an infrastructure issue, not an app issue.
What caught it: Noticed that CI completed in 4 seconds (very fast), implying HEAD was far behind the branch. Local `git log` confirmed the discrepancy. Fixed by pinning checkout to `github.event.pull_request.head.sha`.
Root cause: Default checkout ref for `pull_request` CI is the merge ref, not the branch HEAD. Any diff-based CI script that uses `git diff base...HEAD` is vulnerable when the merge ref lags the branch.
What should catch it next time: Any new CI workflow that does diff-based file inspection must use `ref: ${{ github.event.pull_request.head.sha }}` + `git fetch origin main` — not the default checkout. This pattern is now in `.github/workflows/ai-pr-readiness.yml`. Document in KNOWN_FAILURE_MODES.md.
One-off or repeated: One-off for this repo, but architectural pattern affects any diff-based CI.
Promotion target: `docs/ai/KNOWN_FAILURE_MODES.md` — "CI workflow failures" section.
Action taken: `.github/workflows/ai-pr-readiness.yml` updated (commit `ec19647`). KNOWN_FAILURE_MODES.md updated. This ledger entry added.
Follow-up needed: No.

---

### 2026-05-15 — PR body section headers used bold inline instead of `##` headers, failing CI substring check (PR #381)

Repo: claude_travelapp_pk91
Area: PR workflow / ai_pr_readiness_check
Severity: Level 2 workflow miss
Miss: Initial PR body for #381 used `**Severity:** Level 2` (bold inline) instead of `## Severity` (markdown header). The readiness checker requires exact substrings `"## Severity"`, `"## Validation"`, etc. Using `**SectionName:**` fails silently — the section content is present, but the gate string doesn't match.
Impact: One extra CI failure cycle; required a full PR body rewrite.
What caught it: CI check output showing missing section. Local repro with `--pr-body-file` reproduced immediately.
Root cause: The PR template file uses `## SectionName` headers throughout, but when filling it in quickly the `##` was dropped in favor of bold inline labels. No reminder in the template itself warns against this substitution.
What should catch it next time: Added HTML comment at top of `.github/pull_request_template.md` warning that `## Section` headers must be preserved exactly.
One-off or repeated: Second occurrence (#378 ledger row was first).
Promotion target: `.github/pull_request_template.md`.
Action taken: PR template updated with format-compliance note. This ledger entry added.
Follow-up needed: No.

---

### 2026-05-15 — PR body not tested locally before push caused 3 CI readiness iterations (PR #379)

Repo: claude_travelapp_pk91
Area: PR workflow / ai_pr_readiness_check
Severity: Level 2 workflow miss (repeated — same lesson as #378 ledger row)
Miss: PR body for #379 (Phase 1C Saved Ideas) was never run through `ai_pr_readiness_check.py --pr-body-file` locally before pushing. Required 3 CI iterations to fix three independent failures: (1) missing `## Summary` and `## Validation` exact substrings (`"## UI validation"` does not contain `"## validation"`); (2) `"provider"` in `"SQL / env / providers / UI"` triggers runtime gate — requires `"runtime validation"` in body to satisfy `has_evidence`; (3) `"Wife-Wow"` in build queue item line matched `DESIGN_BODY_RE wife.?wow` — requires `"screenshot"` or `"ui validation"` in body when not `"foundation-only"`. Additional timing trap: CI reads PR body from `GITHUB_EVENT_PATH` event snapshot at push time — updating body via API after a push does NOT affect the already-queued CI run; body must be updated BEFORE the trigger push.
Impact: 3 empty/CI-trigger commits on the branch; 2 extra CI cycles; ~15 min delay.
What caught it: Each CI run output; local repro with `--pr-body-file` diagnosed all failures in one pass.
Root cause: The `--pr-body-file` local dry-run step existed in PR docs but was not treated as a hard pre-push gate. #378 ledger row noted the same lesson but it wasn't reinforced in the PR template.
What should catch it next time: Add a one-line checklist item to `.github/pull_request_template.md`: `- [ ] Ran \`python3 scripts/workflow/ai_pr_readiness_check.py --pr-body-file /tmp/body.txt --base-ref origin/main\` locally before pushing.`
One-off or repeated: Second miss of same pattern (#378 ledger row captured the first). Promoting per two-miss rule.
Promotion target: `.github/pull_request_template.md` — add local-dry-run checklist item.
Action taken: This ledger entry added. PR template update below.
Follow-up needed: Update `.github/pull_request_template.md` with the local dry-run reminder.

---

### 2026-05-10 — Project source/test/docs hygiene gaps after workflow cleanup

Repo: claude_travelapp_pk91
Area: Project hygiene (root-to-leaf source, tests, docs)
Severity: Level 2 hygiene miss
Miss: After OS v4 workflow cleanup, project-level scaffolding lingered: a root `ai/` package not imported anywhere, a `scripts/design_bible/` PDF generator and the `artifacts/Travel_Concierge_Design_Bible.pdf` it produced (no references in active docs/scripts/CI), and stale `docs/ai/PRODUCT_SURFACE_AUDIT.md` / `docs/ai/progress_log.md` references in `docs/ai/LEGACY_FLIGHTS_HOTELS_STRATEGY.md` (those files were already deleted in the workflow cleanup PR). 11 frontend tests live outside the configured `npm test` scripts and 1 PDF in `docs/ai/specs/` is unreferenced — both flagged for follow-up rather than deleted.
Impact: Wasted tokens, misleading anchors for future Claude/Codex runs, and no repeatable check that would have caught this before the workflow cleanup PR closed.
What caught it: PK requested a project-only source/test/docs cleanup with an ongoing hygiene audit.
Root cause: Project-level cleanup is run ad hoc and scoped narrowly; without a reusable audit, project surface drifts back into clutter even when workflow surface is cleaned.
What should catch it next time: `scripts/repo_hygiene_audit.py` (report-only) plus the policy in `docs/ai/REPO_HYGIENE.md`. Run before cleanup PRs and after major phase completions.
One-off or repeated: First *project-level* hygiene cleanup after workflow cleanup; pattern of accumulation is repeated.
Promotion target: `docs/ai/REPO_HYGIENE.md` and `docs/ai/HANDOFF.md` handoff-maintenance rule (already updated).
Action taken: Deleted `ai/`, `scripts/design_bible/`, `artifacts/Travel_Concierge_Design_Bible.pdf`. Repaired stale doc references. Added `scripts/repo_hygiene_audit.py` and `docs/ai/REPO_HYGIENE.md`. README "Current focus" section repointed at canonical roadmap docs instead of dated PR notes.
Follow-up needed: Triage the 11 frontend orphan tests (wire into `npm test` or delete) and decide whether `docs/ai/specs/conversational_context_v1.pdf` is canonical or removable, in a focused follow-up PR.

---

### 2026-05-10 — Workflow/setup asset bloat across root, .claude, docs/ai, .kiro, and AI-tool configs

Repo: claude_travelapp_pk91
Area: Workflow architecture hygiene
Severity: Level 2 workflow miss
Miss: Repo accumulated duplicated/orphaned workflow/setup assets — duplicate cross-AI-tool config files at root (`GEMINI.md`, `.cursorrules`, `.windsurfrules`, `.opencode.json` — three of which were byte-identical), entire `.kiro/steering/` mirror of the same content, 59k stale `progress_log.md` at root, dated transition handoff `HANDOFF_2026-05-10_OS_V4_CONSOLIDATION.md`, one-off audits (`MERGE_GATE_AUDIT_2026-05-01.md`, `pr-194-audit.md`, `PRODUCT_SURFACE_AUDIT.md`), 40k stale `docs/ai/progress_log.md`, duplicate process docs, legacy `docs/ai/skills/` docs-style skill router superseded by `.claude/skills/`, unreferenced loose `.claude/skills/` md files, and unreferenced `.claude/agents/agent-curator.md` and `graphify-out/`. Net: ~37 files removed.
Impact: Bloated workflow surface created multiple competing rule owners, broke `CLAUDE.md` anchor reliability, and made it unclear which doc is canonical for each topic.
What caught it: PK requested a cross-repo workflow hygiene cleanup.
Root cause: Travel repo was originally seeded for several AI tools and several workflow generations; pruning lagged behind canonical OS v4 consolidation.
What should catch it next time: After any AI-tool or OS version transition, run a workflow-asset reference scan and delete orphans.
One-off or repeated: First major workflow cleanup; pattern of accumulation is repeated.
Promotion target: Add a periodic "workflow surface scan" step to OS_LEARNING_PROTOCOL or workflow-retrospective skill.
Action taken: Deleted ~37 stale/duplicate/orphaned workflow assets in PR; updated `CLAUDE.md`; recorded this entry.
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
What should catch it next time: PROMPT_LIBRARY / PROMPT_ENGINEERING_STANDARD, `.github/pull_request_template.md`, workflow-retrospective skill.
One-off or repeated: First recorded miss, but high-signal.
Promotion target: PROMPT_LIBRARY / PROMPT_ENGINEERING_STANDARD and `.github/pull_request_template.md`.
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
What should catch it next time: SAFETY_PACKS_AND_ARCHETYPES (Latency Budget Pack), `.github/pull_request_template.md` (manual actions / SQL / env fields), prompt-generation behavior.
One-off or repeated: First recorded miss, high-cost.
Promotion target: `.github/pull_request_template.md` and SAFETY_PACKS_AND_ARCHETYPES.
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
What should catch it next time: contract-auditor, test-strategist, pr-reviewer, pre-pr-self-audit, TEST_ROUTING.
One-off or repeated: Repeated pattern.
Promotion target: reviewer agents and TEST_ROUTING.
Action taken: OS v2 added focused skills and read-only reviewer agents; OS v3 adds retrospective/learning loop.
Follow-up needed: After next few PRs, check whether reviewer agents reduce follow-up prompts.
