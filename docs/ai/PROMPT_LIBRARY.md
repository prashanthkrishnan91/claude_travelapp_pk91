# Prompt Library (Token Optimized)

## Copy rule

When ChatGPT gives the user a Claude/Codex prompt:

- Put `Model:`, `Chat:`, and `Usage estimate:` OUTSIDE the copyable prompt block.
- The copyable prompt block must contain only text intended to paste into Claude/Codex.
- Do not include explanatory notes inside the prompt block.

## Prompt reviewer gate

Before giving any Claude/Codex prompt, ChatGPT must silently check:

1. Is this the cheapest capable model?
2. Is this a new chat or same chat, and why?
3. Can repo memory replace repeated context?
4. Is the file list limited to likely hot surfaces?
5. Are constraints compressed instead of repeated?
6. Is plan-only mode truly necessary, or can it implement in one pass?
7. Is HANDOFF.md update required inside the PR?
8. Is README.md explicitly excluded unless public/setup behavior changed?
9. Is the copy block mobile-safe with no model/chat/usage metadata?
10. Is there a usage estimate before the prompt?

If a prompt fails any check, rewrite it before showing the user.

## Usage estimate rule

Every Claude/Codex prompt must include an estimate outside the copy block:

- Expected session usage: Low / Medium / High
- Expected extra cost risk: Low / Medium / High
- Why: one sentence

Do not claim exact token or cost certainty. Estimate based on prompt size, number of files, task complexity, model choice, likely repo exploration, and whether tests/builds are required.

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
