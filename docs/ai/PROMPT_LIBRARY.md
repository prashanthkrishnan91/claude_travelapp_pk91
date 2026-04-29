# Prompt Library (Token Optimized)

## Copy rule

When ChatGPT gives the user a Claude/Codex prompt:

- Put `Model:` and `Chat:` OUTSIDE the copyable prompt block.
- The copyable prompt block must contain only text intended to paste into Claude/Codex.
- Do not include explanatory notes inside the prompt block.

---

## 1. Design (Opus)
Use for architecture only

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

Files:
[file1, file2]

Constraints:
- no refactors
- minimal patch

MANDATORY:
- Update docs/ai/HANDOFF.md in the same change

Output:
- plan
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

Files:
[file1]

MANDATORY:
- If bug fix changes behavior, update docs/ai/HANDOFF.md

---

## 4. PR Review (Codex)

Input:
PR summary

Output:
- risks
- missing tests
- edge cases
- required HANDOFF.md updates
