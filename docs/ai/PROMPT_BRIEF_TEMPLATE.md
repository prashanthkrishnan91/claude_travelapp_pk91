# Prompt Brief Template

Use this after the AI Repo Operating System is installed. Do not paste long repeated repo rules.

All future Travel/Finance/future-repo coding prompts must use the OS v3/v4 work-order format below unless explicitly generating an architecture/spec prompt.

## Required default line for all prompts

> Use OS v4. Run prompt-intake and roadmap-check before coding when applicable, run applicable focused skills, delegate via AGENT_ROUTER, and include workflow + product retrospectives if the PR is meaningful or validation fails.

## Standard OS v3 prompt block (legacy)

```text
Repo:
<owner/name>

Task:
<one focused feature/fix/workflow goal>

Severity:
Level <0/1/2/3> because <reason>.

Success criteria:
- <observable outcome>
- <product/workflow invariant preserved>
- <evidence expected>

Scope boundaries:
- No unrelated refactors.
- No SQL unless explicitly required.
- No runtime changes unless explicitly required.
- Stop and propose a split if the durable fix exceeds scope.

Use OS v3.
Run applicable focused skills before coding.
Delegate to applicable read-only reviewer agents before PR summary.
Include workflow retrospective if this is Level 1+ or if validation fails.
Open one focused PR.
Stop after PR summary.
```

## Standard OS v4 work-order format

```text
Repo:
<owner/name>

Task:
<one focused feature/fix/workflow/product goal>

Task type:
<implementation / bug fix / PR review / workflow update / product roadmap update / runtime / SQL / UI / architecture / failed validation / prompt-generation / idea triage / progress report>

Roadmap stage:
<from docs/product/ROADMAP.md>

Build queue item:
<from docs/product/BUILD_QUEUE.md, or "none / justified blocker">

Why now:
<one or two sentences>

What this unlocks:
<observable user/product outcome>

What this must not expand into:
<scope creep guardrails>

Severity:
Level <0/1/2/3> because <reason>.

Success criteria:
- <observable outcome>
- <product/workflow invariant preserved>
- <evidence expected>

Scope boundaries:
- No unrelated refactors.
- No SQL unless explicitly required.
- No runtime changes unless explicitly required.
- Stop and propose a split if the durable fix exceeds scope.

Required OS skills:
<prompt-intake, roadmap-check, task-planner, contract-audit, test-selector, runtime-gate, claim-safety-gate, pre-pr-self-audit, pr-summary, etc.>

Required reviewer agents:
<routed via docs/ai/AGENT_ROUTER.md, e.g. roadmap-guardian, contract-auditor, pr-reviewer, reality-checker if release-adjacent>

Validation expectations:
<UI / runtime / SQL / none + why>

Workflow retrospective:
<Yes/No + reason>

Stop condition:
<one focused PR; stop after PR summary>

Use OS v4.
```

## Concise prompt for progress report

```text
Use OS v4 progress-report. Produce concise project progress report from Product OS docs and handoff.
```

## Concise prompt for idea triage

```text
Use OS v4 idea-triage. Capture the following ideas into IDEA_INBOX without implementing them.
<idea list>
```

## Optional advanced lines

Add one or both only when relevant:

- For Medium/High effort work, use `/cost` if usage grows, use `/compact` before context quality degrades, and invoke only relevant reviewer agents.
- If this is a follow-up after PR review or failed validation, classify whether it is a product bug, workflow miss, OS drift, or evidence gap before coding.

## Optional add-ons

Add only when needed:

- Screenshots or exact UI regression notes.
- Runtime log excerpts or certification results.
- Manual validation target.
- Required feature flag/env condition.
- Specific files to inspect first.

## Anti-patterns

- Do not paste every coding principle.
- Do not repeat all Travel invariants unless the task is risky.
- Do not ask for broad discovery when a targeted skill is enough.
- Do not combine unrelated backend, UI, provider, SQL, and docs work in one prompt.
- Do not generate prompts in a non-OS-v3/v4 format for coding tasks.
- Do not request bulk repo/workflow edits via file-by-file connector commits; batch them in one Sonnet branch/PR.
- Do not bypass roadmap mapping for implementation prompts; if no roadmap mapping exists, flag it before coding.
