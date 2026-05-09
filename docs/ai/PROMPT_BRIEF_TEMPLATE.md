# Prompt Brief Template

Use this after the AI Repo Operating System is installed. Do not paste long repeated repo rules.

All future Travel/Finance/future-repo coding prompts must use the OS v2/v3 work-order format below unless explicitly generating an architecture/spec prompt.

## Required default line for all prompts

> Use OS v3. Run applicable focused skills, delegate to applicable read-only reviewer agents, and include workflow retrospective if the PR is meaningful or if validation fails.

## Standard OS v3 prompt block

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
- Do not generate prompts in a non-OS-v2/v3 format for coding tasks.
- Do not request bulk repo/workflow edits via file-by-file connector commits; batch them in one Sonnet branch/PR.
