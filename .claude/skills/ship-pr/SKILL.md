---
name: ship-pr
description: Use whenever finished work is ready to become a pull request, or the user says "open a PR", "push this", "ship it". Assembles the complete PR package — body from the template file, USAGE_LEDGER row, HANDOFF update, lint, readiness check — in ONE commit and ONE push, validating the body BEFORE pushing so the CI readiness gate passes on its first run.
---

# ship-pr — single-pass PR packaging

Why this exists: `SETUP_AUDIT.md` found that roughly 1 in 5 commits in this account's repos
was post-push compliance repair (missing USAGE_LEDGER rows, PR bodies missing exact template
headings, empty "retrigger CI" commits). This skill moves every check before the first push.
Follow the steps in order; do not reorder or skip.

## Steps

1. **Body from file, never from memory.** Read `.github/pull_request_template.md` and copy it
   verbatim into a scratch file (e.g. `/tmp/pr_body.md`). Keep every `## Heading` exactly as
   written — CI matches exact substrings (`## Summary`, `## Severity`, `## Validation`,
   `SQL / env / providers / UI`, `AI usage note`, `AI PR readiness`). Never convert headings to
   `**bold**` inline form — that exact mistake has failed CI before.
2. **Fill every section honestly.** In a remote/browser environment token data is never
   available — write `source: unavailable — remote env has no ccusage/statusline`. Never leave
   template scaffolding or empty flag values in the body.
3. **USAGE_LEDGER row goes in the SAME commit as the code.** Key the row by branch name (or
   another stable identifier available before the PR exists) — not a placeholder like `#TBD`.
   `scripts/workflow/ai_pr_readiness_check.py` does not require a numeric PR number in the
   ledger; it only requires a substantive data row exists. It is acceptable, and expected, for
   the PR-number field to stay unavailable in the committed row — do not schedule a follow-up
   commit solely to backfill it. Deferring the row itself to a follow-up commit is a separate,
   repeatedly-observed miss — don't do that either.
4. **HANDOFF.md update in the same commit** — replace or summarize the current-state section.
   Never append a new dated entry (history lives in git).
5. **Lint before commit when any JS/TS frontend file changed.** Run lint from the actual
   frontend package (this repo has no root `package.json`; the frontend package lives under
   `frontend/`). If `frontend/node_modules` is absent, run `npm --prefix frontend ci` once,
   then `npm --prefix frontend run lint`. If installation is impossible, state that explicitly
   under Validation instead of skipping silently.
6. **Run the gate against the real body BEFORE pushing:**
   `python3 scripts/workflow/ai_pr_readiness_check.py --pr-body-file <body file> --base-ref origin/main`
   Never run it without `--pr-body-file`: section checks are silently skipped and report a
   false PASS.
7. Fix everything it reports, amend the single commit, and re-run until PASS (warnings are
   advisory; hard failures must be resolved).
8. **One push. Create the PR** with the validated body text.

## Stop condition

The PR is open with a first-run green readiness check. Do not start the next slice and do not
add further commits unless CI or a reviewer reports a concrete failure. Do not add a
post-open commit to replace a PR-number placeholder — none is required.
