# Claude Code — RuFlo V3

## Stack
Vercel (serverless) · Supabase (DB) · Python/JS frontend

## Code Graph
Auto-loaded — never re-read raw source for structural questions; graph is rebuilt automatically after code edits.
@graphify-out/GRAPH_REPORT.md
@graphify-out/wiki/index.md

## Core Rules
- Do only what was asked — nothing more, nothing less
- Read only files needed for the task; never index `node_modules/`, `.next/`, `venv/`, `*.csv`, `*.pdf`
- Output only diffs/snippets — never full files unless asked
- Prefer editing existing files; never create files unless strictly required
- Never save to root — use `/src`, `/tests`, `/docs`, `/config`, `/scripts`, `/examples`
- Always read a file before editing it
- Always run tests after code changes; verify build before committing
- Never hardcode API keys, credentials, or commit `.env` files
- Always validate user input and sanitize file paths at system boundaries
- Run `npx @claude-flow/cli@latest security scan` after security-related changes
- Max 2 fix attempts before asking the user what to try next
- After each feature/bug fix, prompt: "Run /compact before next task."
- No conversational filler. Plan → Code → Verify.

## Workflow
- Tasks >2 steps: write plan to `tasks/todo.md`, await approval, then execute
- One objective at a time — log unrelated bugs to `tasks/todo.md`, do NOT fix mid-task
- Never mark done without running tests or diffing behavior — show proof
- After any user correction, log the pattern in `tasks/lessons.md`; review at session start

## Skill Loading (load only when task matches — no preloading)

| Task Type | Skill |
|---|---|
| UI / layout / components | `/mnt/skills/user/frontend-design/SKILL.md` |
| New feature (design phase) | `/mnt/skills/user/brainstorming/SKILL.md` |
| Writing implementation spec | `/mnt/skills/user/writing-plans/SKILL.md` |
| Executing a written plan | `/mnt/skills/user/executing-plans/SKILL.md` |
| 2+ independent parallel tasks | `/mnt/skills/user/dispatching-parallel-agents/SKILL.md` |
| Bug investigation | `/mnt/skills/user/systematic-debugging/SKILL.md` |
| New feature (implementation) | `/mnt/skills/user/test-driven-development/SKILL.md` |
| About to claim task complete | `/mnt/skills/user/verification-before-completion/SKILL.md` |
| Word / PDF / Excel output | `/mnt/skills/public/{docx\|pdf\|xlsx}/SKILL.md` |

## Architecture
- Domain-Driven Design with bounded contexts
- Typed interfaces for all public APIs
- TDD London School (mock-first) for new code
- Event sourcing for state changes
- Input validation at system boundaries

**Config**: topology `hierarchical-mesh` · maxAgents `15` · memory `hybrid` · HNSW `on` · Neural `on`

## Build & Test
```bash
npm run build  # build
npm test       # test
npm run lint   # lint
```

## Concurrency — 1 message = all related operations
- Batch ALL file reads/writes/edits in one message
- Batch ALL Bash commands in one message
- Spawn ALL agents in one message via Agent tool

## Swarm
- Init swarm with CLI tools for complex tasks; Agent tool does the actual work — call BOTH in ONE message
- Use hierarchical topology; maxAgents 6–8; specialized strategy; `raft` consensus
- Shared memory namespace for all agents; run checkpoints via `post-task` hooks
- Set `run_in_background: true` for all Agent calls
- After spawning, STOP — do not poll or check status; review ALL results before proceeding

## 3-Tier Model Routing (ADR-026)

| Tier | Handler | Use Cases |
|---|---|---|
| 1 | Agent Booster WASM (<1ms, $0) | Simple transforms — use Edit tool directly, skip LLM |
| 2 | Haiku (~500ms) | Low complexity (<30%) |
| 3 | Sonnet/Opus (2–5s) | Complex reasoning, architecture, security (>30%) |
