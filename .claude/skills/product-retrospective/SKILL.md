# Skill: product-retrospective

## Purpose

After product-stage PRs, check whether the work moved the product forward.

## Inputs

- Recent PR diff and summary.
- `docs/product/ROADMAP.md`
- `docs/product/BUILD_QUEUE.md`
- `docs/product/RELEASE_GATES.md`
- `docs/product/PRODUCT_HEALTH.md`
- `docs/product/DECISION_LOG.md`

## Output

- Roadmap stage advanced: Yes / No.
- Visible product progress: Yes / No.
- Rework introduced: Yes / No.
- Patch rabbit-hole risk: Low / Medium / High.
- Queue update needed: Yes / No.
- Decision log needed: Yes / No.
- Product health update needed: Yes / No.

## Rules

- Keep output concise.
- Do not propose product direction changes; surface signals only.
- Recommend, do not edit. Edits go through `build-queue-update` or `DECISION_LOG` updates.
