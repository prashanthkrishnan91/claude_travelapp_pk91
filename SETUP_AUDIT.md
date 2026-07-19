# SETUP_AUDIT — How you actually work in Claude Code, and the highest-leverage fixes

**Scope:** both repos (`claude_financetracker_pk91`, `claude_travelapp_pk91`), their `.claude/` config, global `~/.claude` skills/hooks, `docs/ai/` ledgers (191 + 181 commits, ~365 USAGE_LEDGER rows, 29 MISS_LEDGER entries), the last 60 PRs per repo via the GitHub API, and the scheduled-trigger history.
**Constraint honored:** every recommendation below is executable in the browser — file edits committed through Claude Code sessions, plus in-session actions. Nothing requires a terminal.

---

## A. Top findings, ranked by estimated time/token savings

| # | Finding | Evidence (pattern observed) | Est. saving | Decision |
|---|---------|------------------------------|-------------|----------|
| 1 | **~1 in 5 commits is post-push PR-compliance repair.** The readiness gate catches problems *after* push, so every miss costs a CI cycle + a session turn. | Finance: 16 "retrigger CI" commits + 20 ledger-fix commits = ~36/191 commits (19%). Travel: 20 retrigger + 17 ledger commits, ~26% of commits carry no product change. MISS_LEDGER prices single incidents at "Two wasted CI cycles; ~15-min delay" (#350) and records the same body-heading mistake 4× (#381, #394, #420, #517) *after* it was promoted to KNOWN_FAILURE_MODES. The identical "commit the ledger row with the code" lesson is written ≥11× in the finance USAGE_LEDGER. | 1–2 session turns per PR; the single biggest recurring cost | **NEW SKILL `ship-pr`** (Cluster 1) |
| 2 | **Mandatory read-first files have bloated into a per-session context tax.** | Travel `HANDOFF.md` is **1,007 lines** of appended per-PR history (~80 PRs) despite the CLAUDE.md rule "no historical PR log; replace/summarize, never append". Travel `USAGE_LEDGER.md` is **287 KB** — too large for the Read tool ("exceeds maximum allowed size"); finance's is 184 KB (~78K tokens). Yet 92% of finance rows and all recent travel rows carry `unavailable` in every numeric token column — the 26-column schema's actual payload is prose. | ~10–15K tokens *every session* (HANDOFF is the first listed anchor), plus unreadable-audit-trail risk | **FIX** (Cluster 2) |
| 3 | **Patch loops run far past the written "escalate after two patches" rule.** | Finance ETF-provider saga: ~22 PRs (#415–#433, #443–#451) until PR #447 — literally titled "stop provider patch loop" — encoded a decision matrix; its body: "Without a decision matrix encoding this, future sessions would re-investigate the same dead end." Travel: PR #499 ran v1→v1.1→v1.2→v1.3→v1.4→revert (6 attempts); the same lat/lng metadata gap was then re-fixed in #501, #504, #508, #521, #530. PR #474 took 3 successive semantic audits on one function. | The two largest token sinks on record | **FIX `failure-recovery` skill + dead-end registry** (Cluster 3) |
| 4 | **19 of 21 repo skills have no YAML frontmatter, so they can never auto-fire** — their loaded "description" is just a title ("AI Repo OS Skill", "Skill: prompt-intake"). The same gate content also exists in 4 layers (CLAUDE.md → command → standalone skill → ai-repo-os section). | Verified by `grep -L '^---'`: only `miss-ledger-update` and `workflow-retrospective` have frontmatter. Travel artifacts show zero evidence of `test-selector`, `contract-audit`, `latency-gate`, `claim-safety-gate`, `prompt-lint`, or `tool-failure-triage` ever firing, while every rule that stuck was a CI script (MISS_LEDGER: "Promotion target: ai_pr_readiness_check.py"). `task-planner`/`test-selector` skills are verbatim copies of ai-repo-os sections. | Skills start firing at the right moments; less listing noise (every name currently appears 2–4×) | **FIX** (Cluster 4) |
| 5 | **PR babysitting polls hourly for days.** Each check-in is a full session wake-up. | Trigger history: ~20 one-shot `send_later` re-arms. Travel PR #533 was polled hourly across **8+ days** (Jul 10 → Jul 18); PR #526 checked three consecutive nights with "nothing changed, re-arm silently". | Dozens of wasted session wake-ups per open PR | **CONVERT TO AUTOMATION** (Cluster 5) |
| 6 | **Vercel-only ESLint failures keep breaking PRs because lint never runs before push.** | MISS_LEDGER 2026-05-26 (#488): "third PR where a Vercel-only ESLint failure required a follow-up commit"; root cause recorded: "node_modules are absent locally so `npm run lint` cannot run." Promotion to KNOWN_FAILURE_MODES did not stop it. | 1 failed deploy + 1 follow-up commit per occurrence | **FIX** — folded into `ship-pr` step 5 (Cluster 1) |
| 7 | **33 reviewer-agent files, zero recorded value.** | Both repos' `AGENT_EFFECTIVENESS_LEDGER.md` still read "_None yet — seed after the first meaningful use._" after ~2 months and ~160 PRs. MISS_LEDGER "What caught it" fields credit CI gates, tests, and PK review — never a reviewer agent. What actually reviews PRs is fresh-context "reviewer audit" sessions (USAGE_LEDGER #526, #531 rows). | Removes a dead mandate + per-session agent-list noise | **FIX** (Cluster 6) |
| 8 | **The stop-hook advisory fires on every turn, including trivial Q&A; two enforcement hooks are dead code.** | `ai_os_advisory.py` stop mode unconditionally appends "run /pre-pr-self-audit and /pr-summary" on *every* Stop. `ai_pr_readiness_stop.sh` and `dangerous_action_guard.sh` exist in both repos but are wired to nothing and env-gated off. Travel's advisory docstring still says "OS v2". | Small per-turn noise reduction; removes misleading dead code | **FIX** (Cluster 7) |
| 9 | Fresh-chat rule vs 46% same-chat reality. | Travel ledger: 98 new-chat vs 82 same-chat; finance 33 same-chat rows. | — | **NOTHING** (Cluster 8 — see why) |

---

## B. Per-cluster decisions with ready-to-apply content

### Cluster 1 — PR packaging churn → **NEW SKILL: `ship-pr`**

**Pattern observed:** the gate is *reactive*. Sessions push, CI fails on a missing ledger row or a `**Severity:**`-style heading, then commit "retrigger CI" fixes (finance: `320cce6`, `85d4b96`, `17b1f1f`, `dad1d17` + 12 more; travel: `2f60144`, `00211ef` + 18 more). Also: `check_sections()` silently skips when run without `--pr-body-file`, producing a false local PASS (recorded root cause of #394 and #420).

**Apply:** create `.claude/skills/ship-pr/SKILL.md` in **both repos** with exactly this content:

```markdown
---
name: ship-pr
description: Use whenever finished work is ready to become a pull request, or the user says "open a PR", "push this", "ship it". Assembles the complete PR package — body from the template file, USAGE_LEDGER row, HANDOFF update, lint, readiness check — in ONE commit and ONE push, validating the body BEFORE pushing so the CI readiness gate passes on its first run.
---

# ship-pr — single-pass PR packaging

Why this exists: across the last ~370 commits in this account's two repos, roughly 1 in 5
commits was post-push compliance repair (missing USAGE_LEDGER rows, PR bodies missing exact
template headings, empty "retrigger CI" commits). This skill moves every check before the
first push. Follow the steps in order; do not reorder or skip.

## Steps

1. **Body from file, never from memory.** Read `.github/pull_request_template.md` and copy it
   verbatim into a scratch file (`pr_body.md`). Keep every `## Heading` exactly as written —
   CI matches exact substrings (`## Summary`, `## Severity`, `## Validation`,
   `SQL / env / providers / UI`, `AI usage note`, `AI PR readiness`). Never convert headings
   to `**bold**` inline form (this exact mistake failed CI on PRs #381, #394, #420, #517).
2. **Fill every section honestly.** In the remote/browser environment token data is never
   available — write `source: unavailable — remote env has no ccusage/statusline`. Never
   leave template scaffolding or empty flag values in the body (travel PR #531 shipped
   `--pr  --prompt-id  --phase  --model ` verbatim).
3. **USAGE_LEDGER row goes in the SAME commit as the code.** Key it by branch name; use
   `#TBD` for the PR number for now. Deferring the row to a follow-up commit is the single
   most repeated miss on record (37 remedial commits across both repos).
4. **HANDOFF.md update in the same commit** — replace or summarize the current-state section.
   Never append a new dated entry (history lives in git).
5. **Lint before commit when any JS/TS file changed.** If `node_modules` is absent, run
   `npm ci` once, then `npm run lint`. Vercel-only ESLint failures (`prefer-const`,
   `no-unused-vars`) have broken at least 3 PRs because lint was skipped pre-push. If install
   is impossible in this session, state that explicitly under Validation.
6. **Run the gate against the real body BEFORE pushing:**
   `python3 scripts/workflow/ai_pr_readiness_check.py --pr-body-file pr_body.md --base-ref origin/main`
   Never run it without `--pr-body-file`: section checks are silently skipped and report a
   false PASS (recorded root cause of the #394/#420 CI failures).
7. Fix everything it reports, amend the single commit, and re-run until PASS.
8. **One push. Create the PR** with the validated body text.
9. Immediately replace `#TBD` with the real PR number in USAGE_LEDGER and push that one
   bounded follow-up commit. This is the only permitted post-open commit in this flow — and
   note that editing the PR body via the GitHub API does NOT re-run an already-queued CI
   check; only a push re-triggers it, so batch any body fix with this commit.

## Stop condition

The PR is open with a first-run green readiness check. Do not start the next slice and do
not add further commits unless CI or a reviewer reports a concrete failure.
```

**Companion CLAUDE.md edit (both repos), section "PR Readiness Gate (hard rules)":**

Before:
```
Before opening or updating any Level 1+ PR, run `python3 scripts/workflow/ai_pr_readiness_check.py`.
```
After:
```
Open every PR via the `ship-pr` skill: body copied verbatim from the template file, USAGE_LEDGER row + HANDOFF update in the same commit as the code, and `python3 scripts/workflow/ai_pr_readiness_check.py --pr-body-file <body file> --base-ref origin/main` run to PASS before the first push. Never run the check without `--pr-body-file` — it silently skips section checks and reports a false PASS.
```

---

### Cluster 2 — Per-session context tax → **FIX (three exact edits)**

**Pattern observed:** CLAUDE.md lists `docs/ai/HANDOFF.md` as the *first* read-first anchor. Travel's is 1,007 lines of appended per-PR history back to PR #451 — directly violating its own "replace, never append" rule — so every fresh chat (the mandated default) pays ~10–15K tokens before reading any code. Both USAGE_LEDGERs are prose diaries: finance has 47 rows with `unknown`/`#TBD`/`#pending` PR numbers and 170/184 rows with zero token data; travel's file cannot even be opened by the Read tool.

**2a. Truncate travel `docs/ai/HANDOFF.md`** to this skeleton (≤150 lines; everything below the cut is recoverable from git history — delete it, don't archive it into another file the anchors list points at):

```markdown
# HANDOFF — current state only (hard cap: 150 lines)

## Active work
- <current slice, branch, PR # if open, next concrete step>

## Blocked / waiting on user
- <manual actions: SQL to run, env vars, approvals>

## Landmines (things a fresh session must know)
- <top 5–8 only; link docs/ai/DEAD_ENDS.md for dead ends>

## Recently merged (last 3 PRs, one line each — delete older lines when adding)
- #NNN — <one line>
```

**2b. Archive + slim both USAGE_LEDGERs.** Rename the current file to `docs/ai/USAGE_LEDGER_ARCHIVE_2026H1.md` (one-time browser file operation) and start `docs/ai/USAGE_LEDGER.md` fresh with this schema — the gate's `check_ledger()` only requires the file to change and to contain a `|`-delimited data row, so this is CI-safe with **no script change**:

```markdown
# USAGE_LEDGER (slim schema, 2026-07 →)

Archived history: docs/ai/USAGE_LEDGER_ARCHIVE_2026H1.md

| Date | PR | Branch | Level | Chat | Follow-ups | Waste | Lesson (≤25 words) |
|------|----|--------|-------|------|------------|-------|--------------------|
```

Rationale: the 26-column token-accounting schema carries no token data ~92% of the time ("source: unavailable" on nearly every PR — the remote env has no ccusage). Keep the four columns that demonstrably get used for decisions (Chat, Follow-ups, Waste, Lesson) and cap the prose that made the file unreadable.

**2c. CLAUDE.md anchor line (both repos):**

Before:
```
- `docs/ai/HANDOFF.md` — compact current state only (no historical PR log; replace/summarize, never append)
```
After:
```
- `docs/ai/HANDOFF.md` — compact current state only, hard cap 150 lines; if it exceeds the cap, truncate it in your current PR before doing anything else (history lives in git, not in this file)
```

**Optional 2d (do only as its own PR, template + gate script together):** the PR template's "AI PR readiness" section is ritual — evidence: "Model: configured session model" (placeholder, #523), "Waste classification: none" and "next efficiency improvement: none" on nearly every PR. To slim it, in `scripts/workflow/ai_pr_readiness_check.py` change:

```python
PR_BODY_REQUIRED = [
    "## Summary",
    "## Severity",
    "## Validation",
    "SQL / env / providers / UI",
    "AI usage note",
    "AI PR readiness",
]
```
to
```python
PR_BODY_REQUIRED = [
    "## Summary",
    "## Severity",
    "## Validation",
    "SQL / env / providers / UI",
    "AI usage note",
]
```
and
```python
USAGE_METADATA_FIELDS = [
    "Usage ledger row",
    "Prompt ID",
    "Model",
    "Chat strategy",
    "Main token drivers",
    "Waste classification",
    "Follow-up count",
]
```
to
```python
USAGE_METADATA_FIELDS = [
    "Usage ledger row",
    "Chat strategy",
    "Follow-up count",
]
```
then delete the "## AI PR readiness" block from `.github/pull_request_template.md` and fold `Usage ledger row / Chat strategy / Follow-up count` lines into the "AI usage note" section. ~20 lines of ritual removed from every future PR body (current median body: ~760 words).

---

### Cluster 3 — Patch loops → **FIX: replace `failure-recovery` skill + seed a dead-end registry**

**Pattern observed:** the "after two related patches, escalate" rule existed in CLAUDE.md throughout both loops and was violated because nothing operationalizes the *moment* of the second failure. What finally broke the finance loop was writing dead ends down (PR #447's decision matrix). Travel's v1.2 lesson states the fix pattern verbatim: "when a preview validation fails and a frontend patch doesn't move the needle, query the actual persisted row before patching again."

**Apply: replace `.claude/skills/failure-recovery/SKILL.md` in both repos with:**

```markdown
---
name: failure-recovery
description: Use the moment a SECOND fix attempt on the same bug or seam has failed, before writing any third patch — and before investigating any provider, data source, or approach that may have been tried before. Forces evidence-first diagnosis and consults/updates docs/ai/DEAD_ENDS.md so no dead end is investigated twice.
---

# failure-recovery — stop the loop at two

The two largest recorded token sinks in this account were patch loops: a ~22-PR provider
saga (finance #415–#451, ended only by PR #447 "stop provider patch loop") and a 6-attempt
fix chain plus revert inside one PR (travel #499), whose bug class then recurred in 4 more
PRs. Both ran past the written two-patch rule. This skill is the enforcement.

## On the second failed attempt (mandatory)

1. STOP writing patches. State explicitly: "Two attempts failed — switching to
   evidence-first diagnosis."
2. Get ground truth from the failing layer before forming the next hypothesis:
   - data bug → query the actual persisted row (Supabase MCP), don't infer from code
   - runtime bug → pull the actual log line (railway-logs / Vercel runtime logs) and write
     down the failure seam (log key or test name)
   - UI bug → render and screenshot BEFORE the next change, not after the PR opens
3. Re-diagnose across the full path (frontend → API → persistence), not just the layer the
   last patch touched. The travel #499 loop patched the frontend twice while the bug was in
   a lossy backend intermediate shape.
4. Check `docs/ai/DEAD_ENDS.md`. If the approach or provider is listed, do not
   re-investigate — choose a different approach or stop and report to the user.
5. Write attempt three only against named evidence (log key, row value, screenshot), as a
   full-plumbing fix — never another guess at the same layer.

## After any loop ends (success, revert, or abandonment)

Append one row to `docs/ai/DEAD_ENDS.md`:

| Date | Area | Approach tried | Why it is a dead end | Proof (PR/log) |

## User-reported regressions

If the user reports a preview regression tied to a specific commit: surgical revert first,
investigate after (the #499 revert lesson: "prefer surgical revert over arguing intent").
```

**Seed `docs/ai/DEAD_ENDS.md`:**

Finance:
```markdown
# DEAD_ENDS — approaches proven not to work. Check before investigating; append after abandoning.

| Date | Area | Approach tried | Why it is a dead end | Proof |
|------|------|----------------|----------------------|-------|
| 2026-05 | ETF holdings data | SEC NPORT resolver | CIK limitation — wrong/missing CIKs for target ETFs | PR #447 matrix, Stage 9M (d9002db) |
| 2026-05 | ETF holdings data | Alpha Vantage | No as-of date; classified supplemental-only | PR #431 (9F.3c) |
| 2026-05 | ETF holdings data | FMP | HTTP 402 — paywalled at required tier | PR #433 (9F.4b) |
```

Travel:
```markdown
# DEAD_ENDS — approaches proven not to work. Check before investigating; append after abandoning.

| Date | Area | Approach tried | Why it is a dead end | Proof |
|------|------|----------------|----------------------|-------|
| 2026-06 | Itinerary metadata | Patching individual add-to-itinerary handlers one at a time | Lossy intermediate card shapes silently drop place identity; every handler patched alone regresses another path (fixed 5× separately) | PRs #501, #504, #508, #521, #530 |
| 2026-05 | Plan My Day fixes | Frontend-only patches for persistence-shaped bugs | Two frontend patches failed before querying the persisted row found the backend root cause | PR #499 v1.1/v1.2 ledger rows |
```

**Companion CLAUDE.md edit (both repos), add one line to Core rules directly after the "After one failed patch, reclassify..." bullet:**
```
- Before investigating any provider/data-source/approach, check `docs/ai/DEAD_ENDS.md`; after abandoning one, append a row (see `failure-recovery`).
```

---

### Cluster 4 — Skills can't auto-fire; 4-layer duplication → **FIX**

**Pattern observed:** with no frontmatter, the harness surfaces only file titles ("AI Repo OS Skill"), so skills fire only when you type the slash command — which the ledgers show almost never happens for the gate skills, while CLAUDE.md prose restates their content and gets violated anyway. Meanwhile `task-planner`, `test-selector`, `pr-summary`, `pre-pr-self-audit`, `claim-safety-gate`/`runtime-gate`, and `contract-audit` skills are verbatim or near-verbatim copies of `ai-repo-os` SKILL.md sections, *and* have command-file wrappers pointing at those same sections.

**Apply in both repos:**

1. **Delete these duplicate standalone skills** (the slash commands remain and point at `ai-repo-os`, so nothing is lost): `.claude/skills/task-planner/`, `test-selector/`, `pr-summary/`, `pre-pr-self-audit/`, `claim-safety-gate/`, `runtime-gate/`, `contract-audit/`. That removes 7 of 21 listing entries per repo (14 across both).
2. **Add frontmatter to every kept skill.** Format: `--- / name: X / description: <when to use, starting with "Use when">, / ---` at the top of each SKILL.md. Exact descriptions:

| Skill | `description:` |
|---|---|
| ai-repo-os | Use for any non-trivial implementation, bug fix, or PR — the consolidated OS v4 gates (task planning, test selection, contract audit, claim safety, PR summary) in one file. |
| prompt-intake | Use when a new task arrives and before any coding — classifies the task (level, roadmap stage, patch vs slice) and routes it. |
| roadmap-check | Use before starting implementation or product work — verifies the task maps to the active roadmap stage and build queue item. |
| tool-failure-triage | Use when a command, test, or log check fails — classifies tooling failure vs app bug before any patching. |
| workflow-retrospective | (keep existing frontmatter) |
| miss-ledger-update | (keep existing frontmatter) |
| failure-recovery | (new version above already has it) |
| ship-pr | (new skill above already has it) |
| idea-triage | Use when the user dumps ideas or feature thoughts — triages them into docs/product/IDEA_INBOX.md without starting work. |
| progress-report | Use when the user asks where the project stands or what's next. |
| build-queue-update | Use after a roadmap decision or a merged meaningful PR — updates docs/product/BUILD_QUEUE.md. |
| product-retrospective | Use after a product-stage PR merges — captures product learning. |
| feature-contract | Use before coding any Level 2/3 feature — writes the slice contract. |
| golden-scenarios | Use before coding any Level 2/3 feature — selects the golden scenarios the change must not break. |
| prompt-lint | Use before committing a prompt to docs/ai/PROMPT_LIBRARY.md. |

3. **Fix the two divergent copies drifting silently:** travel's `ai_os_advisory.py` docstring still says "AI Repo OS v2" (finance says v4; CLAUDE.md forbids stale OS labels) — change `v2` → `v4` when touching Cluster 7.

---

### Cluster 5 — PR babysitting polls hourly for days → **CONVERT TO AUTOMATION**

**Pattern observed:** ~20 one-shot `send_later` triggers, each re-arming hourly per PR per session. PR #533 was polled hourly across 8+ days; #526 three consecutive nights with the recorded instruction "if nothing changed, re-arm silently". Every firing wakes a full session with full repo context.

**Apply (two parts):**

**5a. Policy line in both CLAUDE.md files** (append to "Core rules"):
```
- PR watching: rely on the PR-activity event subscription for comments/CI failures. Schedule at most ONE time-based check-in, no sooner than 4 hours out; after 24 hours with no change, stop re-arming, post one status summary, and end the watch. Never poll hourly.
```

**5b. Replace per-PR chains with one sweep Routine** (create once, in any session, by asking Claude to create it — ready-to-paste spec):

- **Name:** `open-pr-sweep`
- **Schedule:** cron `0 */12 * * *` (every 12 hours; hourly granularity is what the current chains use and it demonstrably never pays off overnight)
- **Mode:** fresh session per fire
- **Prompt:**
  ```
  Sweep ALL open pull requests in prashanthkrishnan91/claude_financetracker_pk91 and
  prashanthkrishnan91/claude_travelapp_pk91 in one pass. For each open PR: check CI status,
  mergeability, and unresolved review comments. Fix small confident CI failures directly on
  the PR branch; for anything ambiguous, leave one comment summarizing the blocker instead
  of guessing. If a PR has been green and unreviewed for >48h, add a one-line nudge comment.
  Do not create new PRs. If there are no open PRs, exit immediately without output.
  ```

This turns N-PRs × 24-checks/day into 2 sweeps/day total, and the event subscription still delivers comments and CI failures in real time. (Also worth adopting: merge your own gate-green PRs promptly — 114 of the last 120 PRs merged anyway, and open PRs are what feed the polling habit.)

---

### Cluster 6 — Reviewer-agent roster with zero recorded value → **FIX**

**Pattern observed:** both `AGENT_EFFECTIVENESS_LEDGER.md` files still contain "_None yet — seed after the first meaningful use._" after ~160 PRs. No MISS_LEDGER "What caught it" field ever credits a reviewer agent; the catches that work are CI gates, tests, and fresh-context audit sessions. A rule that has never once been followed in two months is not a rule — it's noise.

**Apply in both repos:**

1. **CLAUDE.md, "Agent governance" section** —
   Before:
   ```
   Follow `docs/ai/AGENT_ROUTER.md`. Do not run every agent by default. Park new external agent ideas in `docs/ai/AGENT_INTAKE_REGISTRY.md`. Record reviewer-agent usefulness in `docs/ai/AGENT_EFFECTIVENESS_LEDGER.md` only when the signal is meaningful.
   ```
   After:
   ```
   Follow `docs/ai/AGENT_ROUTER.md`. Do not run every agent by default. For Level 2/3 PRs, the required reviewer is a fresh-context audit session (or subagent) against the diff — that is what has caught real blockers. Park new external agent ideas in `docs/ai/AGENT_INTAKE_REGISTRY.md`.
   ```
2. **Delete** `docs/ai/AGENT_EFFECTIVENESS_LEDGER.md` (both repos) and its row in the CLAUDE.md anchors list if present.
3. **Prune agents** to the ones `AGENT_ROUTER.md` routes for real gates. Keep per repo: `pr-reviewer`, `contract-auditor`, `reality-checker`, plus the two domain guards (finance: `policy-authority-reviewer`, `sql-runtime-reviewer`; travel: `place-authority-reviewer`, `latency-reviewer`). Delete the other ~11 per repo (`premium-delight-reviewer`, `accessibility-reviewer`, `performance-benchmarker`, `evidence-collector`, `eval-scenario-reviewer`, `prompt-intake-reviewer`, `prompt-quality-reviewer`, `roadmap-guardian`, `test-strategist`, `workflow-retrospective-reviewer`, etc.) — they duplicate skills/commands that already exist and have never produced a recorded catch. Update `AGENT_ROUTER.md` to match.

---

### Cluster 7 — Hook spam and dead hooks → **FIX**

**Pattern observed:** `ai_os_advisory.py` stop mode appends the same reminder on **every** Stop, with no work detection — per-turn noise that trains you to ignore it (and no ledger entry ever credits it with a catch). Two other hooks (`ai_pr_readiness_stop.sh`, `dangerous_action_guard.sh`) are present in both repos but wired to nothing and env-gated off — dead code implying protection that doesn't exist.

**Apply in both repos — `.claude/hooks/ai_os_advisory.py`, stop mode:**

Before:
```python
reminders.append("AI OS advisory: before stopping on non-trivial work, run /pre-pr-self-audit and /pr-summary using the PR template.")
```
After:
```python
import subprocess
dirty = subprocess.run(
    ["git", "status", "--porcelain"], capture_output=True, text=True
).stdout.strip()
if dirty:
    reminders.append(
        "AI OS advisory: uncommitted changes present — if this is PR work, "
        "finish via the ship-pr skill (single-pass PR packaging)."
    )
```
Also: change travel's docstring "AI Repo OS v2" → "v4", and **delete** `ai_pr_readiness_stop.sh` (superseded by ship-pr's pre-push check) and `dangerous_action_guard.sh` (never wired; the DANGEROUS_ACTION_GUARD.md doc remains the consulted source) from both `.claude/hooks/` directories.

---

### Cluster 8 — Fresh-chat rule vs 46% same-chat → **NOTHING**

Travel: 98 new-chat vs 82 same-chat; finance: 33 same-chat rows. Not worth changing: the ledger shows most same-chat rows are legitimate open-PR audit patches, which the rule explicitly permits ("Same chat only for: open-PR patches or tightly adjacent safe continuation"). The harmful subset — same-chat *loop continuation* — is exactly what Cluster 3's failure-recovery fix interrupts at the second failed patch. Adding a chat-strategy enforcement mechanism would create a new compliance ritual of the kind Clusters 1–2 exist to remove. Same verdict for the one recorded model-routing miss (#379 p02: Opus on a Level 1 patch) — single occurrence, no pattern.

---

## C. Do these three first

1. **Add `ship-pr` (Cluster 1) + its CLAUDE.md line, both repos.** It attacks the single largest measured waste (~1 in 5 commits is compliance repair) and absorbs the Vercel-lint fix. One session, two small PRs.
2. **Truncate travel HANDOFF.md and archive both USAGE_LEDGERs (Cluster 2a/2b) + the 150-line cap rule (2c).** This is a pure deletion that pays ~10K+ tokens back on *every* future session, with zero CI risk (the gate's ledger check is schema-agnostic).
3. **Adopt the PR-watching policy + `open-pr-sweep` routine (Cluster 5) and delete the habit of hourly re-arms.** Biggest saving outside the repos themselves: PR #533 alone consumed 8+ days of hourly session wake-ups.

Everything else (skill frontmatter, agent pruning, hook fixes, template slimming) is worthwhile but second-order; batch each as a small workflow PR when convenient.

---

*Method note: signals were gathered by four parallel read-only subagents (finance ledgers/git history, travel ledgers/git history, `.claude` + global config inventory, GitHub PR history for the last 60 PRs per repo) plus a scan of the scheduled-trigger history, then clustered. Every finding above cites the artifact it came from; token-saving estimates are derived from the repos' own recorded costs (MISS_LEDGER delay entries, commit counts, file sizes) rather than generic heuristics.*
