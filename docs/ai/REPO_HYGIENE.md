# Repo Hygiene

Lightweight, repeatable check that keeps the Travel Concierge repo clean over time so future Claude/Codex runs don't waste tokens on dead paths or get misled by stale docs.

## Run

```bash
python scripts/repo_hygiene_audit.py
```

The audit is **report-only**. It never deletes files. Output is a Markdown report with these sections:

- Summary
- Hard blockers
- Cleanup candidates
- Test hygiene findings
- Progress/handoff findings
- Docs/artifact findings
- Recommended next cleanup PR

## When to run

- Before opening any cleanup-style PR.
- After completing a major phase or large refactor.
- After any test-suite expansion.
- After any workflow/OS transition (e.g., archetype additions, agent additions).

## What it checks

1. **Banned obsolete surfaces.** Paths that were intentionally removed must not come back: `.claude-flow/`, `.kiro/`, `graphify-out/`, cross-AI-tool configs (`GEMINI.md`, `.cursorrules`, `.windsurfrules`, `.opencode.json`), historical one-off audits (`PRODUCT_SURFACE_AUDIT.md`, `MERGE_GATE_AUDIT_*`, dated `HANDOFF_*` files), and any `progress_log.md`. Reintroducing one of these is a **hard blocker** (exit code 1).
2. **Banned production-visible tokens.** Tokens like `book.example.com` must not appear under `frontend/src/`. Hard blocker.
3. **Progress/handoff discipline.**
   - Soft warning when `docs/ai/HANDOFF.md` exceeds ~500 lines or `docs/ai/MISS_LEDGER.md` exceeds ~800.
   - Hard blocker when either exceeds the byte threshold (raw-dump territory).
   - Warns when raw-dump markers (PR body dumps, transcripts, large logs) appear inside either file.
4. **Test hygiene.**
   - Counts backend test files and runs `pytest --collect-only` when pytest is available.
   - Lists any backend test files not collected.
   - Flags tests that import obvious legacy/removed modules.
   - Reports the largest backend test files for attention.
   - For frontend tests, parses `frontend/package.json` and lists test files outside the configured `npm test` / `npm run test:*` scripts.
5. **Source/reference hygiene.** Generated / cache / build directories accidentally committed are flagged as cleanup candidates (they are also gitignored, so usually only a problem if a directory was added before the ignore).
6. **Docs / artifact hygiene.** PDFs in `artifacts/` / `docs/` that are not referenced by any other tracked text file are listed as orphan PDF artifacts.

## What it does **not** do

- It does not delete files.
- It does not fail CI on cleanup candidates — only on banned legacy paths or oversized raw-dump handoff/miss-ledger files.
- It does not flag every unreferenced source file. Source-import auditing is too noisy for an automated gate; the audit deliberately focuses on durable, repeatable checks.

## How to use the output

- **Hard blockers** → fix before merging the current PR.
- **Cleanup candidates / test findings / docs findings** → bundle into the next focused cleanup PR. Don't fix everything at once; one capability slice per PR per OS v4.
- **Progress/handoff findings** → compress `docs/ai/HANDOFF.md` and/or `docs/ai/MISS_LEDGER.md` in the same PR that triggered the bloat. Replace, do not append.

## Policy: how to keep the repo small

- Default to one capability slice per PR.
- Keep `docs/ai/HANDOFF.md` as **current state**, not a history log. Replace or summarize, never append.
- Keep `docs/ai/MISS_LEDGER.md` for workflow/process misses only — not every app bug.
- For deep historical detail, link to canonical artifacts in `artifacts/` rather than copying their content.
- Treat `docs/ai/specs/`, `artifacts/`, `backend/db/migrations/`, and active SQL/architecture docs as canonical — preserve them or compress in place; do not delete blindly.
- Generated artifacts (PDFs, build output) should be regenerated on demand, not committed unless they are canonical references.

## Exit codes

- `0` — no hard blockers (cleanup-only signals are fine to ship in a follow-up).
- `1` — at least one hard blocker.
