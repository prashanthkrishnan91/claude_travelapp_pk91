# Skill: Discovery / Surface Map

Use this skill when the primary files or visual surfaces are unknown.

## Model
Codex preferred.

## Purpose
Map the smallest useful set of files before implementation. Do not fix during discovery unless the user explicitly asked for a tiny obvious fix.

## Rules
- Read `CLAUDE.md` and `docs/ai/HANDOFF.md` first.
- Read only files needed to identify the target surface.
- Do not run broad repo scans unless targeted reads fail.
- Do not make implementation changes in a map pass.
- Return file paths, likely owner components, risks, and the recommended next skill.

## Output
```md
Findings:
Primary files:
Likely tests:
Risks:
Recommended next skill:
Supabase SQL likely: Yes/No
```
