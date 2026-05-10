# Skill: progress-report

## Purpose

Generate the concise progress report PK can ask for anytime.

## Inputs (read only what's needed)

- `docs/product/NORTH_STAR.md`
- `docs/product/ROADMAP.md`
- `docs/product/BUILD_QUEUE.md`
- `docs/product/PRODUCT_HEALTH.md`
- `docs/product/RELEASE_GATES.md`
- `docs/ai/HANDOFF.md` if relevant.

## Output

Return the format defined in `docs/product/PROGRESS_REPORT_TEMPLATE.md`.

## Rules

- Keep it concise.
- Plain English.
- No deep technical narration.
- If the docs are stale, say so explicitly.
- Focus on confidence, where we are, what changed, what is next.
- Do not invent progress that is not supported by the docs.
