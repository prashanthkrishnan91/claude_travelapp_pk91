# Skill: prompt-lint

## Purpose

Lint a prompt before PK copy-pastes it or before Claude starts coding.

## Inputs

- The proposed prompt text.
- `docs/ai/PROMPT_ENGINEERING_STANDARD.md`
- `docs/ai/PROMPT_LIBRARY.md`
- `docs/ai/AGENT_ROUTER.md`
- `docs/product/ROADMAP.md`
- `docs/product/BUILD_QUEUE.md`

## Output

- Prompt ready: Yes / No.
- Missing source files.
- Missing roadmap / build queue mapping.
- Missing feature contract (if Level 2+).
- Missing golden scenarios (if Level 2+).
- Missing validation.
- Scope creep risk.
- Old-format prompt risk.
- Agent overuse risk.
- Suggested corrected prompt outline.

## Rules

- Use for important prompts.
- Keep output concise.
- Do not rewrite everything unless asked; suggest the smallest fix.
- If prompt is unsafe for blind copy / paste, say so explicitly.
