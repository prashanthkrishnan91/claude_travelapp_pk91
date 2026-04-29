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

Output:
- plan
- files
- tests

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

---

## 4. PR Review (Codex)

Input:
PR summary

Output:
- risks
- missing tests
- edge cases
