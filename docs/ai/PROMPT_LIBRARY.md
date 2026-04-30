# Prompt Library (Token Optimized)

## Copy rule

When ChatGPT gives the user a Claude/Codex prompt:

- Put `Model:`, `Chat:`, and `Usage estimate:` OUTSIDE the copyable prompt block.
- The copyable prompt block must contain only text intended to paste into Claude/Codex.
- Do not include explanatory notes inside the prompt block.

## Prompt reviewer gate

Before giving any Claude/Codex prompt, ChatGPT must silently check:

1. Cheapest capable model?
2. Correct new/same chat?
3. Repo memory instead of repeated context?
4. Minimal file scope?
5. Compressed constraints?
6. Plan-only truly needed?
7. HANDOFF.md required inside PR?
8. README excluded unless public/setup changed?
9. Mobile-safe copy block?
10. Usage estimate included?
11. Discovery budget included when paths are known?
12. For PR review: cheap merge gate first, deep audit only if suspicious?
13. Budget gate: can this be split/downgraded to avoid extra usage?
14. If extra usage may be needed, did the Code Committee approve it?
15. For UI work: did the UI budget gate approve the scope?
16. After heavy Claude PR: does the prompt tell user to stop that Claude session and review elsewhere?
17. Does any Medium/High prompt include a timeout/checkpoint rule?
18. For complex refactors: did the split gate reduce the task to one deliverable?

If any check fails, rewrite before showing the user.

## Complex refactor split gate

A prompt must be split if it combines 3+ of these in one task:

- bug fix
- UI refactor
- persistence/idempotency
- history/log display
- analytics/performance display
- tests
- documentation
- migration/schema work
- multiple workflows/screens

Default split order:

1. Logic correctness only (helpers/state semantics/persistence denominator)
2. UI separation only (cards/layout using corrected helpers)
3. History/analytics display only
4. Tests/docs/handoff finalization or cheap merge gate

For complex refactors, the first prompt should usually be Codex or Sonnet with max 1–2 primary files and one deliverable. Do not request full redesign + persistence + history + performance + docs in one prompt unless Code Committee explicitly approves High usage.

## Timeout / continue budget rule

Repeated "continue" after Claude stops or times out is expensive because the full accumulated chat, file reads, command output, and partial work remain in context and are resent on subsequent turns.

For Medium/High prompts, include:

```md
Timeout budget:
- If you are about to exceed time/context or cannot finish cleanly, stop after a checkpoint.
- Before stopping, write: files changed, tests run, current status, remaining steps, and whether a PR exists.
- Do not start broad new discovery after a continue.
- If resumed, continue only from the checkpoint and do not reread files already summarized.
- If two continues are needed, stop and ask the user to move the checkpoint summary to a fresh chat.
```

User-side rule: after two timeouts/continues, do not keep saying continue. Start fresh with Claude's checkpoint summary or bring it to ChatGPT for compression.

## Session stop rule

After any Medium-High or High usage Claude prompt creates a PR, do not continue implementation, audit, merge, or next-step planning in that Claude chat.

Required next step:

- Stop the Claude chat.
- Bring the PR summary, link, screenshots, or cost data back to ChatGPT/project workflow review.
- Use Codex cheap merge gate for PR review unless a blocker is found.
- Do not ask Sonnet for the next prompt in the same session.

Any prompt expected to create a Medium-High/High PR must include a final instruction: "After opening the PR, stop. Do not propose the next implementation prompt."

## Budget gate

Default monthly budget target: ChatGPT Plus + Claude Pro only. Avoid extra usage.

Before any prompt likely to be Medium-High or High usage:

1. Try Codex first if task is bug fix, audit, refactor, or <=3 primary files.
2. Split design from implementation only if it reduces total rework; otherwise one-pass implementation.
3. Limit primary edit targets to 1-2 files.
4. Move examples/logs into compact state packs.
5. Exclude README unless public/setup behavior changed.
6. Use cheap merge gate before any deep audit.
7. Defer non-blocking improvements to a follow-up list, not the current prompt.

## UI budget gate

Any prompt containing UI, visual, design-system, premium, boutique, polish, redesign, theme, layout, or aesthetic must include a UI budget outside the copy block.

UI budget format:

```md
UI budget:
- Phase: [map / foundation / one page / one component / merge gate]
- Max files: [number]
- Primary surfaces: [screens/components]
- Forbidden surfaces: [what not to touch]
- Stop condition: [when to stop instead of expanding]
- Decision: APPROVE / SPLIT / REJECT
```

Hard rules:

- Full-app UI upgrades default to SPLIT.
- Sonnet UI implementation max scope: 6 files unless Code Committee explicitly approves more.
- If primary UI files are unknown, run Codex surface map first; do not use Sonnet discovery.
- Page-specific UI polish must target one page/screen at a time.
- UI merge gates use Codex by default and read diff only.
- No prompt may say "make the whole app premium" without max files + phase boundary.

## Extra usage approval gate

If extra usage may be required, do not present the prompt until the Code Committee review is complete.

Code Committee review format:

```md
Budget review:
- Need: [why this task matters now]
- Cheapest path tried/available: [Codex / smaller scope / defer]
- Risk of not doing it: [short]
- Estimated usage: [Low/Medium/High + rough %]
- Extra usage risk: [Low/Medium/High]
- Decision: APPROVE / REJECT / SPLIT
```

Default decision is REJECT unless the task is blocking progress, preventing data loss/security issue, or avoiding larger rework.

## Usage estimate rule

Every prompt must include outside the copy block:

- Expected session usage: Low / Medium / High
- Expected extra cost risk: Low / Medium / High
- Why: one sentence

Estimate from prompt size, files, model, task complexity, likely exploration, and tests/builds. Do not claim certainty.

## Discovery budget rule

When paths are known:

```md
Discovery budget:
- Do not run find/grep/glob for initial exploration.
- Read only the primary edit target and listed test files first.
- Read fallback files only if blocked, and state why.
- Run focused tests only; do not run broad test discovery unless focused tests fail for unknown reasons.
```

---

## 1. Design (Opus)
Use only for architecture. Opus requires budget review unless the output is a reusable spec that prevents multiple Sonnet/Codex failures.

Rules:
- max 2 examples
- no large JSON blocks
- no repeated explanation
- produce reusable spec, then stop

---

## 2. Implementation (Sonnet)

Task:
[short]

State:
[logs/json]

Primary edit target:
[file1]

Test targets:
[test1, test2]

Fallback reads only if blocked:
[file2, file3]

Discovery budget:
- no find/grep/glob for initial exploration
- read primary + tests first
- fallback files only if blocked

Timeout budget:
- checkpoint before timing out
- max two continues, then fresh chat/checkpoint compression

Constraints:
- no refactors
- minimal patch

MANDATORY:
- Update docs/ai/HANDOFF.md in the same change
- If this is Medium-High/High usage, stop after PR and do not propose next prompt

Output:
- files
- tests
- handoff update summary

---

## 3. Debug / small implementation (Codex preferred)

Task:
[bug or small change]

Expected:
[short]

Actual:
[short]

Logs/state:
[paste]

Primary file:
[file1]

Discovery budget:
- no broad search unless primary file does not contain the issue

MANDATORY:
- If behavior changes, update docs/ai/HANDOFF.md

---

## 4. UI workflow

For UI work, never skip UI budget.

Preferred flow:

1. Codex map if primary visual surfaces are unknown.
2. Sonnet implements one capped phase.
3. Stop Sonnet chat after PR.
4. Codex cheap visual merge gate.
5. Subsequent page/component passes only if needed.

Implementation prompt must include:

- UI budget
- primary edit target(s)
- forbidden surfaces
- max files
- discovery budget
- timeout budget for Medium/High work
- HANDOFF.md update
- stop-after-PR instruction for Medium-High/High work

---

## 5. PR Review — default cheap merge gate (Codex preferred)

Use this first for normal pre-merge review.

Discovery budget:
- Read PR diff and changed files only.
- Do not run find/grep/glob.
- Do not generate exploratory scripts.
- Run focused tests only if they are named.
- If a blocker is found, stop and report it; do not fix it.

Output only:
- Merge recommendation: MERGE / DO NOT MERGE
- Blocking issues only
- Tests run + results
- Supabase SQL: Yes/No
- HANDOFF.md edited: Yes/No
- Non-blocking follow-ups, max 3 bullets

## 6. PR Review — deep audit (Sonnet only if suspicious)

Use only after cheap merge gate finds a specific suspected risk.

Input:
- one suspected risk
- relevant file/diff only

Discovery budget:
- inspect only files related to that risk
- no broad repo search
- no unrelated risk review

Output:
- blocking: Yes/No
- evidence
- minimal fix recommendation if blocking
- tests run
