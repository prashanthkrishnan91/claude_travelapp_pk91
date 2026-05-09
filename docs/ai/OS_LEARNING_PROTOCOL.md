# OS Learning Protocol — Travel Concierge

## OS v3 goal

Self-learning workflow loop. The repo OS records workflow misses, classifies whether they are one-off or repeated, and promotes lessons only when evidence justifies it. Anti-bloat is a non-negotiable constraint.

## When to learn

- Every meaningful PR runs a short workflow retrospective via `.claude/skills/workflow-retrospective/SKILL.md`.
- Classify any of these and route to the ledger:
  - failed validation
  - repeated Claude miss
  - ChatGPT catch
  - Codex rescue
  - UI regression
  - runtime evidence gap
  - SQL/env miss
  - deployment-cost miss
  - prompt-format miss

## Promotion ladder

- **One miss** → record in `docs/ai/MISS_LEDGER.md`. Do not update other surfaces yet.
- **Two similar misses** → update one precise target: `KNOWN_FAILURE_MODES.md`, `TEST_SELECTOR.md`, `PR_REVIEW_CHECKLIST.md`, `FAILURE_RECOVERY.md`, `PROMPT_BRIEF_TEMPLATE.md`, or a reviewer agent checklist.
- **Three similar misses** → add or promote an advisory hook reminder.
- **Repeated high-severity miss** → recommend a required reviewer or stronger stop/split rule.
- Hard-blocking hooks remain out of scope unless explicitly approved later.

## Learning targets

- `docs/ai/KNOWN_FAILURE_MODES.md`
- `docs/ai/TEST_SELECTOR.md`
- `docs/ai/PR_REVIEW_CHECKLIST.md`
- `docs/ai/FAILURE_RECOVERY.md`
- `docs/ai/PROMPT_BRIEF_TEMPLATE.md`
- `.github/pull_request_template.md`
- `.claude/skills/*`
- `.claude/agents/*`
- `.claude/hooks/ai_os_advisory.py`
- `CLAUDE.md` only if the rule is foundational and short

## Anti-bloat rules

- Do not update many files for one isolated miss.
- Do not add broad vague rules.
- Prefer one precise checklist item over long prose.
- If a lesson is task-specific and unlikely to recur, record it only in `MISS_LEDGER.md`.
- If unsure, do not promote; ask for ChatGPT review in PR summary.

## Travel-specific catches

OS v3 self-learning should specifically catch:

- non-v2/v3 prompt formatting
- over-hardening notes/prose
- keyword patching as substitute for open-language semantic behavior
- missed downstream card contracts (`display.displayWhy`, `supportingDetails.whyPick`, top-level `whyPick`)
- latency claims without route-level evidence
- source authority errors (enrichment minting cards, editorial source-name-only facts leaking to visible prose)
- deployment storm from file-by-file workflow/docs commits
