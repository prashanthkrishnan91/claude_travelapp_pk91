# Repo-local workflow skills

These files simulate Claude Code skills for the browser/mobile Claude + Codex workflow.

They are not CLI hooks, installed plugins, or true automatic subagents. They are small, task-specific instruction packs that prompts can reference to reduce repeated context.

## How to use

In a Claude/Codex prompt, reference only the skill needed for the task:

- `docs/ai/skills/discovery.md` — map unknown files or visual surfaces before implementation
- `docs/ai/skills/bugfix.md` — focused bug fix or small behavior correction
- `docs/ai/skills/ui_fix.md` — capped UI polish or visual consistency pass
- `docs/ai/skills/implementation.md` — focused multi-file feature implementation
- `docs/ai/skills/merge_gate.md` — cheap PR review before merge
- `docs/ai/skills/workflow_update.md` — workflow/documentation updates like this one
- `docs/ai/skills/supabase_change.md` — any change that may require Supabase SQL

## Rule

Use one primary skill per prompt. If a task needs three or more skill types, split it before implementation.
