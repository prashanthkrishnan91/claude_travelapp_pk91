# Prompt Library (Token Optimized)

## 1. Design (Opus)
Use for architecture only

Rules:
- max 2 examples
- no large JSON blocks
- no repeated explanation

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
- handoff update summary (exact text to write into HANDOFF.md)

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
