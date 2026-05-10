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
- **Two similar misses** → update one precise target: `KNOWN_FAILURE_MODES.md`, `TEST_ROUTING.md`, `.github/pull_request_template.md`, `FAILURE_RECOVERY.md`, `PROMPT_LIBRARY.md`, or a reviewer agent checklist.
- **Three similar misses** → add or promote an advisory hook reminder.
- **Repeated high-severity miss** → recommend a required reviewer or stronger stop/split rule.
- Hard-blocking hooks remain out of scope unless explicitly approved later.

## Learning targets

- `docs/ai/KNOWN_FAILURE_MODES.md`
- `docs/ai/TEST_ROUTING.md`
- `.github/pull_request_template.md`
- `docs/ai/FAILURE_RECOVERY.md`
- `docs/ai/PROMPT_LIBRARY.md` and `docs/ai/PROMPT_ENGINEERING_STANDARD.md`
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

## OS maturity scoring

After every workflow retrospective, optionally score the AI workflow on a 1–5 scale:

- Prompt efficiency: Did the task use a short OS v2/v3 work-order instead of a bulky prompt?
- Prompt intake quality: Did Claude classify the prompt correctly before coding?
- Planning quality: Did Claude state assumptions, success criteria, contracts, and stop/split conditions?
- Review coverage: Were only the relevant read-only reviewer agents used?
- Subagent output quality: Did reviewer agents return evidence, blockers, and risks in a usable format?
- Evidence quality: Were tests/runtime/SQL/deployment/UI validation correctly classified?
- Follow-up load: Did PK/ChatGPT/Codex need to catch something the OS should catch?
- Cost/deployment discipline: Were token usage, commits, preview builds, and validation work minimized?
- OS drift control: Did the task follow current OS v3 rather than older prompt/PR habits?

Promotion rule:

- Do not update OS files from one low score alone.
- If the same score category is weak twice, create a `MISS_LEDGER` entry or update one precise checklist.
- If the same score category is weak three times, consider an advisory hook or required reviewer.
- If the score is weak because of a high-severity miss, recommend ChatGPT review before promotion.

## Future hook promotion path

Hooks must progress gradually:

- Advisory reminder: default for new hooks.
- Required evidence reminder: after repeated misses, require PR summary to mention the relevant gate.
- Blocking hook: out of scope unless explicitly approved later.

Hard-blocking hooks are not allowed in OS v3.

## OS drift audit

OS drift means Claude, ChatGPT, or Codex follows older repo habits instead of current OS v3.

Check for:

- old bulky prompt style when OS v3 work-order format should be used
- PR summary missing retrospective fields
- Claude using only the old `ai-repo-os` router and skipping v3 learning
- running too many reviewer agents by default
- skipping reviewer agents when risk clearly requires them
- missing deployment/build-cost classification
- follow-up prompt needed because the OS process was not followed

If OS drift is observed:

- record in `MISS_LEDGER.md` if meaningful
- update only the narrow surface that should have caught it
- do not rewrite broad OS docs unless repeated
