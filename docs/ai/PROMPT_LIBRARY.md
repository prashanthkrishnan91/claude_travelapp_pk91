# Prompt Library (Token Optimized)

## Copy rule

When ChatGPT gives the user a Claude/Codex prompt:

- Put `Model:` and `Chat:` OUTSIDE the copyable prompt block.
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
9. Is the copy block mobile-safe with no model/chat metadata?

If a prompt fails any check, rewrite it before showing the user.

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
