# Prompt Brief Template

Use this after the AI Repo Operating System is installed. Do not paste long repeated repo rules.

```text
Repo: prashanthkrishnan91/claude_travelapp_pk91

Task:
<one focused feature/fix>

Severity:
Level <0/1/2/3> because <reason>.

Success criteria:
- <observable outcome>
- <product invariant preserved>
- <test/runtime evidence expected>

Scope boundaries:
- Do not <explicit non-goal>.
- No unrelated refactors.

Use the repo AI Repo Operating System.
Run applicable skills/commands before PR summary.
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
