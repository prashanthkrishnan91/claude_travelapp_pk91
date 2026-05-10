# Skill: idea-triage

## Purpose

When PK dumps ideas, classify them without turning them into immediate implementation.

## Inputs

- The ideas in user message.
- `docs/product/ROADMAP.md`
- `docs/product/BUILD_QUEUE.md`
- `docs/product/IDEA_INBOX.md`
- `docs/product/DO_NOT_BUILD_YET.md`

## Output (per idea)

- Idea summary:
- Repo:
- Product layer:
- Near / mid / long:
- Dependency:
- Risk:
- Decision: Now / Next / Later / Do Not Build Yet / Needs Research / Duplicate.
- Suggested destination file/section.

## Rules

- Capture ideas without derailing the current slice.
- Do not implement from Idea Inbox without explicit roadmap promotion.
- If an idea matches `DO_NOT_BUILD_YET`, mark it accordingly and stop.
- If an idea is already in BUILD_QUEUE or IDEA_INBOX, mark it Duplicate.
- Keep output concise.
