# Claude Personal Skills Routing Guide

This repo is used from browser/mobile Claude + Codex, not a local Claude Code CLI setup. Personal Claude skills may be available in the user's Claude app, but prompts must not depend on them being installed unless the user explicitly confirms they are available in that session.

Use personal skills as optional accelerators. The repo-local files in `docs/ai/skills/` remain the source of truth for workflow rules.

## Best skills to use often

| Personal skill | When to invoke it | Repo-local companion |
|---|---|---|
| `systematic-debugging` | Repro, root cause, regression, logs, broken behavior | `docs/ai/skills/bugfix.md` |
| `railway-logs` | Railway/deployment/runtime logs, crashes, recent errors, 4xx/5xx responses, provider failures, backend/UI disagreement, auth/cache/persistence mismatches | `docs/ai/skills/bugfix.md` or `merge_gate.md` |
| `verification-before-completion` | Before Claude says a task is done; force tests/build/manual verification notes | `docs/ai/skills/merge_gate.md` |
| `receiving-code-review` | Claude receives Codex/ChatGPT review feedback and must make a minimal fix | `docs/ai/skills/bugfix.md` |
| `requesting-code-review` | Claude opens a PR and should prepare a concise review packet | `docs/ai/skills/merge_gate.md` |
| `executing-plans` | Implement an already-approved focused plan | `docs/ai/skills/implementation.md` |
| `writing-plans` | Plan only; no code yet; useful before risky feature work | `docs/ai/PROMPT_LIBRARY.md` design section |
| `test-driven-development` | Changes with clear expected behavior or regression tests | `docs/ai/skills/bugfix.md` or `implementation.md` |
| `frontend-design` | Focused UI polish with known surface and strict UI budget | `docs/ai/skills/ui_fix.md` |
| `ui-ux-pro-max` | Higher-polish design direction; use sparingly for capped UI passes | `docs/ai/skills/ui_fix.md` |

## Railway log usage

Use `railway-logs` when a prompt says any of: "fetch the logs", "check the Railway logs", "show me recent errors", "pull the last 200 logs filtered for 500 errors", "why is my app crashing?", "check the deployment", or similar runtime-log language.

Default runtime evidence pattern:

```md
Use the `railway-logs` personal skill if available. Check recent Railway logs for this repo before coding, focusing on 4xx/5xx errors, crashes, provider failures, auth/cache/persistence mismatches, and request/response shape issues. Summarize only relevant evidence in the final report. Do not ask the user to paste Railway logs unless the skill is unavailable.
```

Use log evidence to classify severity. Backend logs disagreeing with UI behavior, data existing in logs but disappearing in UI, or symptoms crossing frontend/backend/API/cache/provider/persistence should usually trigger Level 2 full plumbing analysis instead of another patch.

## Use sparingly

| Personal skill | Use only when |
|---|---|
| `brainstorming` | Product ideation before implementation; not inside code PR prompts |
| `subagent-driven-development` | The task is large enough to split into explorer/reviewer/implementer roles |
| `dispatching-parallel-agents` | Only when Claude can actually run isolated agents; otherwise simulate with separate chats |
| `finishing-a-development-...` | End-of-PR checklist only; do not let it expand scope |
| `doc-coauthoring` | Public docs or substantial internal docs need rewriting |
| `web-artifacts-builder` | Building standalone artifacts, not normal app features |
| `skill-creator` / `writing-skills` | Updating workflow skills themselves |

## Usually avoid for these repos

| Personal skill | Reason |
|---|---|
| `using-git-worktrees` | User is browser/mobile only; no CLI worktree workflow |
| `mcp-builder` | Not relevant unless the user explicitly starts an MCP project |
| `graphify` | Useful only for diagrams; not normal feature work |
| Unknown design-system skills (`ckmdesign`, `dbs-framework`, `ckmdesign-system`, `ckmui-styling`) | Use only if the user explicitly wants those systems and the skill is active |

## Prompt pattern

When a personal skill is useful, mention one skill by name and pair it with one repo-local skill:

```md
Use the `systematic-debugging` personal skill if available.
Also follow `docs/ai/skills/bugfix.md` and `docs/ai/HANDOFF.md`.
```

For runtime issues, `railway-logs` may be paired with one primary work skill:

```md
Use `railway-logs` if available to fetch current runtime evidence. Follow `docs/ai/skills/bugfix.md`.
```

Do not stack many personal skills in one prompt. More skill names can increase confusion and token use. One primary skill is the default; two is the maximum when one is runtime evidence and one is implementation/verification.

## Token-saving rule

Prefer this:

```md
Use `systematic-debugging` if available. Follow `docs/ai/skills/bugfix.md`.
```

Instead of pasting a full debugging checklist into every prompt.

For runtime evidence, prefer this:

```md
Use `railway-logs` if available; check recent errors before coding.
```

Instead of asking the user to paste exported Railway JSON.

## Safety rule

Personal skills do not replace project invariants, budget gates, UI budget, Supabase SQL labeling, HANDOFF updates, or stop-after-PR instructions.
