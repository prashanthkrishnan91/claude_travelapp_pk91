# HANDOFF — Current Repo State

Last updated: 2026-05-10

## Purpose

This file is **current operational state**, not a historical log. It is meant to be loaded into context every session, so it must stay compact. Do not append PR-by-PR history. When something changes, replace or summarize the affected section instead of adding new entries.

## Current product stage

- Roadmap stage: Stage 1 → Stage 2 transition (stabilize core product spine → open-app-before-trip / discovery-first). See `docs/product/ROADMAP.md`.
- Active build queue item: product architecture audit for the discovery-first shift; stabilize AI Concierge / add / save / trip if any catastrophic failure remains. See `docs/product/BUILD_QUEUE.md`.
- Current north-star reminder: Discover → Search → Save → Plan → Optimize → Watch. The app must be useful before a trip exists. Wife-wow goal applies. See `docs/product/NORTH_STAR.md`.

## Current architecture / runtime state

- OS v4 is the canonical operating system. No v4.2 or v5 labels.
- Google Places is canonical for addable cards. Yelp / Foursquare / editorial are enrichment / evidence only and cannot mint addable cards.
- AI Concierge card field contract is the source of truth (`display.displayWhy`, `supportingDetails.whyPick`, top-level `whyPick`).
- Latency Budget Pack governs total request-path latency, not just local provider timeouts.
- For long architecture references, read `artifacts/travel_concierge_product_north_star_v3.md`, `artifacts/travel_concierge_v4_travel_os_addendum.md`, `artifacts/ai_concierge_semantic_place_intelligence.md`, and `artifacts/ai_concierge_semantic_place_intelligence_v2_amendment.md` rather than copying them here.
- Runtime workflow guardrails: advisory `.claude/hooks/ai_os_advisory.py` reminds about contract / claim-safety / latency / SQL / env paths. No blocking hooks.

## Recent meaningful PRs

Keep this section small. Only entries that affect future work; replace older lines as they age out.

- 2026-05-10 — workflow architecture hygiene completed (claude-flow stack, helpers, ~37 stale/duplicate workflow assets, root-surface clutter, cross-AI-tool configs all removed; canonical anchors are `.claude/skills/`, `docs/ai/TEST_ROUTING.md`, `docs/ai/PROMPT_LIBRARY.md`, `.github/pull_request_template.md`, `docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md`). Active docs/configs no longer reference deleted assets.
- 2026-05-09 — follow-up commit removed an orphaned `const explanation = ...` declaration in `FlightCandidateCard` after a JSX block removal; lint/build clean. (See `docs/ai/MISS_LEDGER.md` for durable record.)
- Earlier Concierge / provider / save-flow work has been folded into product source-of-truth docs and is no longer tracked PR-by-PR here. See `docs/product/DECISION_LOG.md` and `docs/ai/MISS_LEDGER.md` for durable records.

## Active invariants / safety packs to remember

Named packs in `docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md` (Travel section) own the rules. The packs themselves are the source of truth — do not paste their contents elsewhere:

- Google Places Addable Authority Pack
- Enrichment Evidence Only Pack
- Semantic Concierge Behavior Pack
- AI Concierge Card Contract Pack
- No Mock/Sample Visible Data Pack
- Latency Budget Pack
- Backend-only Scaffold Pack / No Visible Behavior Change Pack / Test Tier Pack (cross-cutting)

## Known risks / unresolved issues

- Discovery-first shift has not yet produced a global Explore shell or unified result actions — these are the next entry gates for Stage 2.
- Saved-list foundation is not built; ideas still need a non-trip home.
- AI destination intelligence, road trip mode, deal/points intelligence, and Travel Watchtower are deferred to later stages and must not be pre-built.

## Next recommended step

Produce the discovery-first product architecture audit (one capability slice or focused doc) that defines the entry gates for Stage 2. Use the OS v4 work-order shape and the AI Concierge Card Contract Pack + No Mock/Sample Visible Data Pack as relevant.

## Handoff maintenance rule

- This file is current state only. It is not an append-only log.
- Keep under ~250–500 lines. If it grows past that, **compact before adding** — summarize older sections, do not extend them.
- Every meaningful PR may update this file, but by **replacing or summarizing**, never by appending.
- Move durable historical detail to `docs/ai/MISS_LEDGER.md` (workflow/process misses) or `docs/product/DECISION_LOG.md` (product decisions). Do not preserve old noise just because it exists.
- Do not create new archive files for routine PRs. An archive is justified only when current-state value is being replaced and the original detail is still useful elsewhere.
- `CLAUDE.md`, `docs/ai/AI_REPO_OPERATING_SYSTEM.md`, and `docs/ai/PROMPT_LIBRARY.md` enforce this rule.
