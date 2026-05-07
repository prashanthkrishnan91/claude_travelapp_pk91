# AGENTS.md — Travel Concierge

This is the portable entrypoint for Claude, Codex, ChatGPT-driven agents, and future AI coding tools. Keep it short; detailed procedures live in `docs/ai/` and `.claude/skills/`.

## Repo mission
Build a best-in-class AI travel concierge with open-language place understanding, Google-verified addable cards, fast response times, evidence-grounded reasoning, and premium user experience.

## Required operating system
For non-trivial work, follow `docs/ai/AI_REPO_OPERATING_SYSTEM.md`.

Permanent rules:

- Read `CLAUDE.md` first when using Claude Code.
- Use repo-local skills and commands instead of pasting long repeated instructions.
- Classify severity before implementation.
- State assumptions, success criteria, affected contracts, and stop/split conditions before coding.
- Audit downstream consumers before opening a PR.
- Use `.github/pull_request_template.md` for PR evidence.
- Update `docs/ai/HANDOFF.md` only for meaningful product, architecture, migration, workflow, or major bug-fix changes.

## Non-negotiable product invariants

- Google Places is canonical for addable cards, place identity, operational status, address, maps URL, and place_id.
- Yelp, Foursquare, Tavily, Serper, and editorial/web sources are enrichment/evidence only. They cannot mint addable cards.
- Avoid keyword patching for individual venue categories; preserve open-language semantic behavior.
- Do not expose internal diagnostics, raw evidence structures, or source-name-only facts to the user.
- Visible notes must be evidence-grounded, LLM-written under claim safety, or hidden.
- Do not add deterministic fallback visible notes.

## Default agent roles

- ChatGPT: product architect, prompt engineer, PR reviewer, workflow owner.
- Claude Sonnet: primary focused feature/fix builder.
- Claude Opus: architecture/spec/planning only.
- Codex: surgical blockers, focused audits, small tests/refactors, merge-gate exceptions.

## Stop condition
If the durable fix exceeds scope, stop and propose a split. Do not patch around a deeper architecture gap.

---

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
|------|----------|
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.
