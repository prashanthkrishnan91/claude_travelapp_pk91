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

If any check fails, rewrite before showing the user.

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

Constraints:
- no refactors
- minimal patch

MANDATORY:
- Update docs/ai/HANDOFF.md in the same change

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
3. Codex cheap visual merge gate.
4. Subsequent page/component passes only if needed.

Implementation prompt must include:

- UI budget
- primary edit target(s)
- forbidden surfaces
- max files
- discovery budget
- HANDOFF.md update

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
