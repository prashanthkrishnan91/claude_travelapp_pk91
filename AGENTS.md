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
