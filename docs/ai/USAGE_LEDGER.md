# USAGE_LEDGER — slim schema, July 2026 onward

Archived history: `docs/ai/USAGE_LEDGER_ARCHIVE_2026H1.md`

| Date | PR / Branch | Level | Chat | Follow-ups | Waste | Lesson |
|------|-------------|-------|------|------------|-------|--------|
| 2026-07-19 | claude/context-tax-reduction-cluster-2-65e2xb | 0 | new-chat | 0 | none | Archiving instead of appending is what actually pays back the read-first tax — HANDOFF's context cost came from history, not current-state content. |
| 2026-07-19 | claude/context-tax-reduction-cluster-2-65e2xb (PR #536 CI fix) | 0 | same-chat | 1 | necessary-follow-up | `certify_v4_1.py` hard-asserted the old 26-column ledger's field names; a schema-replacement PR must also update anchor-checking scripts, not just the readiness gate. |

Rules:
- One row per PR.
- PR number may remain unavailable when the row is committed before PR creation; use the stable branch name.
- `Lesson` maximum 25 words.
- Do not store unavailable token-accounting columns.
- Do not append narrative paragraphs.
- Historical detail belongs in git and the archive.
