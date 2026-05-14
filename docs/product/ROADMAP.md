# Travel Concierge — Roadmap

Staged roadmap with entry/exit gates. This is not a backlog. It is the product spine.

For live work, see `docs/product/BUILD_QUEUE.md`.
For gates, see `docs/product/RELEASE_GATES.md`.

## Stage 1 — Stabilize current product spine

- Goal: existing trip + AI Concierge surfaces work without catastrophic failure.
- Why it matters: nothing premium can ship on a broken foundation.
- Entry criteria: discovery-first shift identified.
- Exit gate: Product Spine Stability Gate passes (no catastrophic failures, basic add/save/trip flows usable).
- Example build slices: AI Concierge regression fixes, mock/sample leakage removal, Google Places authority enforcement, broken add/save/trip flows.
- Do not expand into: design sprint, deals, points, alerts, road trips, or new verticals.

## Stage 2 — Open app before trip exists

- Goal: the app is useful with no trip created.
- Why it matters: Discover-first is the whole product thesis.
- Entry criteria: Stage 1 exit gate passed.
- Exit gate: Discovery-First Gate passes (global Explore shell works, unified result actions live).
- Example build slices: global Explore shell, unified result actions (save / add to trip / create trip), trip-optional surfaces.
- Do not expand into: saved-list ML ranking, AI destination intelligence, or design sprint.

## Stage 3 — Saved lists / boards ✓ FUNCTIONALLY EXITED (2026-05-14)

- Goal: Travel Idea / Saved Item becomes a first-class root object.
- Why it matters: ideas need a home that does not require a trip.
- Entry criteria: Stage 2 exit gate passed.
- Exit gate: Saved Lists Gate passes.
- Status: **Functionally unblocked for private-use scope.** v1 (Saved Lists Foundation), v2 (Add to Trip), v3 (Create Trip from Saved) shipped. Board reorganization/edit is an accepted open gap. Trip-workspace search parity is an accepted open gap. PRs #366–#370 resolved all Stage 3 exit blockers.
- Example build slices: saved list data model, list views, board organization, save-from-anywhere actions.
- Do not expand into: AI ranking, social sharing, or notifications.

## Stage 3.5 — Wife-Wow design system foundation (ACTIVE NEXT)

- Goal: design tokens, visual primitives, premium surface language, shared components, and vertical result-card visual foundation.
- Why it matters: the product is functionally unblocked; premium feel is the next unlock for wife-wow readiness.
- Entry criteria: Stage 3 functionally exited.
- Exit gate: Wife Wow Readiness Gate passes (see RELEASE_GATES.md).
- Hard stops for this stage: no provider/search behavior changes, no API route changes, no Tavily/live-research changes, no flight/hotel/saved-trip behavior changes.
- Example build slices: design tokens, app shell / surface language, shared buttons/cards/forms/actions, vertical result-card visual foundation.
- Do not expand into: new feature surfaces, route changes, or provider work during the design foundation.

## Stage 4 — AI destination intelligence

- Goal: trustworthy AI recommendations grounded in the place graph.
- Why it matters: makes Discover useful at the level of intent, not keywords.
- Entry criteria: Stage 3.5 design foundation merged; AI Concierge stable.
- Exit gate: AI destination quality matches trusted-card bar.
- Example build slices: preference-aware destination cards, semantic intent surfaces, evidence-backed reasons.
- Do not expand into: deals, points, social, or alerts.

## Stage 5 — Road trip mode

- Goal: multi-stop, route-aware planning beyond single-destination trips.
- Why it matters: a major use case PK has explicitly called out.
- Entry criteria: Stage 4 exit gate passed.
- Exit gate: Road trip mode demonstrably useful end-to-end.
- Example build slices: route input, stop sequencing, time/budget constraints.
- Do not expand into: real-time traffic optimization, deals, or auto-booking.

## Stage 6 — Wife Wow Design Sprint

- Goal: premium, emotionally satisfying experience across Discover, Saved, and Trip flows.
- Why it matters: this is the moment the app stops being functional and starts being lovable.
- Entry criteria: Wife Wow Readiness Gate passes (see RELEASE_GATES.md).
- Exit gate: Design Sprint Exit Gate passes.
- Example build slices: visual system, motion polish, empty/loading/error states, copy tone, hero moments.
- Do not expand into: new feature surfaces during the sprint.

## Stage 7 — Deal intelligence

- Goal: trustworthy deal awareness across saved interests.
- Why it matters: turns saved travel ideas into actionable opportunity.
- Entry criteria: Wife Wow gate passed; saved + AI destination layers stable.
- Exit gate: Deal/Points Readiness Gate (deal half) passes.
- Example build slices: deal source model, deal cards, deal-to-saved-item linkage.
- Do not expand into: scraping-heavy infrastructure, public deal feed, or noisy alerts.

## Stage 8 — Points intelligence

- Goal: useful answers for award/transfer questions across saved travel ideas.
- Why it matters: a recurring high-value PK request ("I have 20k Amex points — what can they do?").
- Entry criteria: Stage 7 source/data foundation usable.
- Exit gate: Deal/Points Readiness Gate (points half) passes.
- Example build slices: points/transfer-partner source model, points-to-destination mapping, plain-English answers.
- Do not expand into: live booking, partner API integrations, or transfer execution.

## Stage 9 — Travel Watchtower / alerts

- Goal: rare, actionable alerts about saved interests.
- Why it matters: the app earns long-term attention only if alerts are signal, not noise.
- Entry criteria: deal + points sources stable; saved-item taxonomy reliable.
- Exit gate: Watchtower Alert Readiness Gate passes.
- Example build slices: trigger model, suppression rules, alert delivery surface.
- Do not expand into: high-frequency push, scraping fragility, or generic news.
