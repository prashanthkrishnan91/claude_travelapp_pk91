# Travel Concierge — Design Bible Addendum v1.1

**Status:** Design contract addendum · pre-implementation
**Date:** 2026-05-14
**Extends:** `artifacts/Travel_Concierge_Design_Bible.pdf` (Design Bible v1.0)
**Roadmap stage:** Stage 3.5 — Wife-Wow design system foundation
**Build queue item:** Wife-Wow design system foundation

## What this is

A short, opinionated sharpening of Design Bible v1.0 before Phase 0 implementation. It does **not** rewrite or replace the Bible. v1.0 stays fully authoritative — every guardrail, token, primitive, anti-pattern, and phased roadmap is unchanged. This addendum only adds emotional-architecture and UX-grammar guidance that future Stage 3.5+ prompts should cite alongside the Bible.

This addendum changes **no scope**. Phase 0 is still tokens + Card primitive shell + TrustStrip only (see §6 below).

## v1.0 stays authoritative on

Phase 0 first (tokens + Card primitive shell + TrustStrip only); no backend / SQL / provider / search / API / Tavily / flight / hotel / saved-trip behavior changes; no all-in-one redesign PR; no raw hex in components; no fake trust signals; no chatbot avatar, typing dots, confetti, fake urgency, neon glow, or crypto gradients; verified card as atomic unit; evidence as the brand; Midnight Ink / Warm Paper tonal duality; Card primitive + TrustStrip system; reduced-motion requirement. Where this addendum and v1.0 ever appear to differ, **v1.0 wins**.

---

## 1. Private atelier / belonging layer

**New design principle: "Private atelier, not private dashboard."**

Travel Concierge should feel like a private travel atelier or member-club concierge — a room that remembers you — not a productivity dashboard. This sharpens v1.0 §3.1 (candle-lit atelier tone) and §3.8 (never a SaaS dashboard) into a positive, testable principle.

Concretely, when those surfaces are designed:
- **Dashboard greeting** reads like a concierge who knows you ("Good evening, Prashanth. Three trips on your shelf."), not a stats header.
- **Saved ideas** feel like a kept scrapbook, not a list view.
- **Trip covers** feel like the cover of a personal travel volume.
- **Memory pill** feels like the concierge recalling context, not a filter chip.

This is "remembered and personal" via real, consensual data only — never fabricated personalization. It does not authorize new personalization data, new memory persistence, or new backend fields. It reuses v1.0 §10 opt-in behaviors and §6.6 memory rules.

## 2. Concierge Search Bar grammar

Luxury search controls must be **standardized across surfaces** — Explore, trip creation, saved-trip creation, hotels, flights, and future surfaces — so search feels like one concierge instrument, not many borrowed forms.

The shared search grammar consistently supports, in this order:
- destination
- dates
- guests / passengers
- intent
- one primary CTA

Date pickers, dropdowns, passenger/guest selectors, city autocomplete, and chips must become **premium components**, not browser-default form controls. They live in the Card/primitive token system, follow v1.0 §4 tokens and §5 motion, and pass v1.0 §4.13 accessibility (44×44 hit area, focus ring, reduced-motion).

**Constraint: beauty must not slow task completion.** A more beautiful selector that adds taps, modal hops, or latency fails this addendum. This extends v1.0 A5 ("design is a force multiplier, not a justification for regressions") to search controls specifically.

This is grammar guidance for future phases. It does **not** authorize Stage 3.5 to build the search components, change routes, or alter any search/provider behavior.

## 3. Trip-as-story / travel chapter model

Trip detail should feel like a **travel chapter**, not a project-management board. This sharpens v1.0 §7.4 ("reading-room layout") and §7.8 ("days are not boxes").

- Trip covers, itinerary days, saved ideas, notes, hotels, flights, and restaurants should feel **editorially connected** — one continuous story, not a wall of equal-weight SaaS widgets.
- **Day sections read like chapters**: a typeset chapter header, evidence-grounded cards inside, hairline separation — not a uniform grid of tiles.
- Hierarchy comes from editorial weight (a day's headline pick leads), not from KPI tiles, progress rings, or completion percentages (still forbidden per v1.0 §3.8).

No data model, persistence, or tab-route changes — this is visual + IA grammar only, consistent with v1.0 §7.4 guardrail.

## 4. Future experience-lane IA

When the product is ready, future Explore should evolve beyond rigid vertical chrome (Restaurants / Attractions / Hotels / Flights tabs) into **curated experience lanes**:

- Stay
- Eat
- See
- Wander
- Unwind
- After dark
- Worth the splurge
- Luxury for less

This is **future IA guidance only.** It is explicitly **not** authorized for Stage 3.5. It does not change routes, providers, vertical behavior, or the canonical Explore provider routing contract in `docs/product/BUILD_QUEUE.md`. The Stage 3 exit routing/provider guardrails are fully preserved. Treat this section as direction for a later roadmap stage, recorded here so design foundation work does not accidentally hard-code chrome that blocks it.

## 5. Constraint-first planning / feasibility UX

**New design principle: "Beauty should expose feasibility, not hide it."**

A beautiful trip view that hides whether the plan actually works is a failure. The UI should make useful constraints **visible beautifully** — when, and only when, supporting data already exists:

- distance from hotel
- arrival time vs. first-night plans
- restaurant timing
- route / travel-time hints
- weather-sensitive alternatives
- saved-place clustering by neighborhood

These render as typeset, caption-grade, hairline treatments (consistent with v1.0 §5.6 travel-time hints and §8.7 travel-time chip) — never alarmist badges.

**Do not invent feasibility claims.** This is bound by v1.0 §9.10 (unsupported claims) and §9.9 (missing details): render distance, timing, route, weather, and clustering **only** when the backend already supplies the data. When data is absent, the field is omitted — no "—", no estimate, no client-side guess. This section adds **no** new backend data or computation; it is presentation grammar for data the product already exposes.

## 6. Phase 0 confirmation

Phase 0 scope is **unchanged** from Design Bible v1.0 §13. For the avoidance of doubt, Stage 3.5 Phase 0 is exactly:

- design tokens (color, type, spacing, elevation, motion) in `globals.css`
- Tailwind variable wiring (`var(--token)`, no raw hex)
- Card primitive shell (`Card.tsx`, composable slots, no variants wired)
- TrustStrip primitive (`TrustStrip.tsx`)
- `docs/ai/UI_BASELINE.md` update (note token foundation shipped + link to Bible)
- `docs/ai/HANDOFF.md` update ("Design Foundation Phase 0" entry)

No visible redesign. No new fonts. No new animation library. No surface adopts the Card primitive or new search components. No backend, no SQL. This addendum does **not** add anything to Phase 0.

## 7. Prompting impact

Future Stage 3.5+ implementation prompts should cite **both** the main Design Bible **and** this addendum, e.g.:

> Implements Design Bible v1.0 §13 Phase 0 + §8 Card shell; emotional architecture per Design Bible Addendum v1.1 §1, §5.

This addendum sharpens **emotional architecture and UX grammar** — how surfaces should *feel* and how search/trip/feasibility patterns should be *structured*. It does **not** expand Phase 0 scope, and it does not relax any v1.0 §12 guardrail or Stop Condition. When a prompt's task and this addendum's guidance conflict with a v1.0 guardrail, the v1.0 guardrail controls and the work is split or stopped.
