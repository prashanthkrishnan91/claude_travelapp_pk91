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

If any check fails, rewrite before showing the user.

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
Use only for architecture.

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

## 3. Debug (Codex)

Task:
[bug]

Expected:
[short]

Actual:
[short]

Logs:
[paste]

Primary file:
[file1]

Discovery budget:
- no broad search unless primary file does not contain the bug

MANDATORY:
- If bug fix changes behavior, update docs/ai/HANDOFF.md

---

## 4. PR Review — default cheap merge gate (Codex preferred)

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

## 5. PR Review — deep audit (Sonnet only if suspicious)

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
