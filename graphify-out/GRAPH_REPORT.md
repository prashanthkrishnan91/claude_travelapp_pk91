# Code Graph Report

Auto-generated knowledge graph for `claude_travelapp_pk91`.

## Stats

| Metric | Value |
|--------|-------|
| Nodes | 316 |
| Edges | 1524 |
| Files | 72 |
| Languages | python, javascript, typescript, tsx |
| Last updated | 2026-04-15 |
| Branch | claude/build-code-graph-ZjEMy |
| Commit | 59691be0dd0c |

## Communities (12)

| Community | Size | Description |
|-----------|------|-------------|
| app-page | 6 | App-level page routing |
| core-settings | 4 | Core configuration and settings |
| dashboard-points | 5 | Dashboard and points/rewards UI |
| layout-active | 5 | Layout components and active state |
| lib-fetch | 22 | Data fetching library utilities |
| models-itinerary | 61 | Itinerary domain models (largest) |
| routes-item | 26 | API route handlers and item management |
| services-component | 56 | Service layer and UI components |
| trips-page | 6 | Trip listing page |
| trips-step | 17 | Trip creation step flow |
| ui-empty | 4 | UI empty/placeholder states |
| utils-ask | 25 | Utility functions and AI prompt helpers |

## Graph Location

Raw graph database: `.code-review-graph/graph.db`
Wiki pages: `.code-review-graph/wiki/` (also mirrored to `graphify-out/wiki/`)

## Usage

```bash
# Query the graph
code-review-graph status

# Incremental update after file changes
code-review-graph update --skip-flows

# Rebuild from scratch
code-review-graph build

# Regenerate wiki
code-review-graph wiki
```

## MCP Tools Available

Use `mcp__code-review-graph__*` tools for structural queries:
- `semantic_search_nodes` — find functions/classes by name or keyword
- `query_graph` — trace callers, callees, imports, tests
- `get_impact_radius` — blast radius of a change
- `detect_changes` — risk-scored analysis of changed files
- `get_architecture_overview` — high-level codebase structure
- `get_review_context` — token-efficient source snippets for review
