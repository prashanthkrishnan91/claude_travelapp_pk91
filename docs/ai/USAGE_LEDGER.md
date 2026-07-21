# USAGE_LEDGER — slim schema, July 2026 onward

Archived history: `docs/ai/USAGE_LEDGER_ARCHIVE_2026H1.md`

| Date | PR / Branch | Level | Chat | Follow-ups | Waste | Lesson |
|------|-------------|-------|------|------------|-------|--------|
| 2026-07-19 | claude/context-tax-reduction-cluster-2-65e2xb | 0 | new-chat | 1 | preventable-follow-up | Schema-replacement PRs must audit every downstream reader/writer (certify script, snapshot/backfill tools, docs), not only the readiness gate. |
| 2026-07-19 | claude/analytics-interview-dossier-becb4g | 0 | new-chat | 0 | none | Repo-wide dossier synthesis via five parallel read-only subagents kept main context small; docs-only PRs still ship through full template body. |
| 2026-07-21 | claude/travel-open-pr-sweep-2mpsdo | 0 | new-chat | 1 | preventable-follow-up | Semantic audit caught the sweep's single-state reporting rule could suppress concurrent CI/review/conflict blockers on one PR. |

Rules:
- One row per PR.
- PR number may remain unavailable when the row is committed before PR creation; use the stable branch name.
- `Lesson` maximum 25 words.
- Do not store unavailable token-accounting columns.
- Do not append narrative paragraphs.
- Historical detail belongs in git and the archive.
