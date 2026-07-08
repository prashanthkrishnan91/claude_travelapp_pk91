# ADR — AI Route Planning v1 (Product + Contract)

Status: **Decision-only. No implementation in this PR.**
Date: 2026-07-08
Stage: 3.5 (design adoption) → forward-looking Journey Desk planning capability.
Decision type: Product + technical contract that gates a future capability slice.
Supersedes nothing. **Builds on** `docs/ai/ROUTE_PLANNING_V1_CONTRACT.md` (the
travel-time-preview foundation) and the inline route-connector UX shipped in
PR #519 / PR #521.

This ADR defines the **safe v1 contract for the *AI layer*** on top of the
already-shipped route foundation. It is deliberately separate from the
`ROUTE_PLANNING_V1_CONTRACT.md` provider/travel-time ADR: that document governs
*how the app estimates travel times*; this document governs *how AI is allowed to
talk about, and propose changes to, a day's route* — without ever silently
editing the itinerary.

## Context — what already shipped (the route foundation)

**Route Planning v1 foundation is closed.** None of the AI behavior in this ADR
may bypass or re-open any of it.

- **Google Routes backend foundation exists** (registry role `ROUTE_MATRIX`,
  flag-gated `route-estimate` endpoint, live `google_routes_adapter.py`,
  `production_allowed=False` / key-gated). Governed by
  `ROUTE_PLANNING_V1_CONTRACT.md`.
- **The separate "Check route" button/panel was removed** (PR #519).
  `CheckRoutePanel` no longer exists.
- **Inline itinerary connectors are the canonical route UI** — the between-card
  connector auto-renders `~N min drive · X.X km` when Google Routes returns a
  success leg, otherwise the honest haversine fallback.
- **PR #521** fixed Saved Items → itinerary metadata parity for **category** and
  **lat/lng**, so items added through the Saved Items path now carry canonical
  coordinates and category, feeding `extractItineraryCoordinates` and
  `hasRouteableCoordinates` correctly.
- Smoke testing for this track is done. The next track is **AI Route Planning
  v1**, and per repo rule it **must start with this ADR before any code**.

Net effect: the app can now honestly compute day-level travel times for the
current manual order and honestly report coordinate coverage. It has **no AI
layer** that interprets that data for the user. This ADR scopes that layer
narrowly and safely.

## Recommendation (read this first)

**PROCEED, but as a read-only, explain-first advisor — never an editor.**

1. AI Route Planning v1 is a **plain-English route-quality advisor**: it reads
   the day's eligible stops and the existing route/connector data and produces
   **explanations and non-binding suggestions** ("this day backtracks",
   "consider moving X before Y", "this stop has no location data").
2. **AI may not reorder, mutate, or auto-apply anything.** Every itinerary
   change stays a manual user action through the existing UI. Any future
   AI-proposed reorder requires an **explicit user approval action** and a
   **before/after** preview (a later slice, not v1).
3. **AI never fabricates travel times or distances.** It may only cite numbers
   that already came from the Google Routes foundation (or the honest fallback),
   and must say so. When data is missing, it says the data is missing.
4. **Inline connectors remain the canonical route UI.** v1 adds a lightweight,
   reviewable insight surface adjacent to them — **not** a new route panel, map
   line, or optimizer.

This ADR does not authorize implementation. It authorizes the **future PR
sequence** in [Implementation sequencing](#9-implementation-sequencing), each
independently gated by [Merge gates](#10-merge-gates-for-future-implementation).

---

## 1. Product definition

### What AI Route Planning v1 **is**

- An **AI advisor for route quality and day flow**, scoped to a **single day**.
- It **reads** the day's eligible itinerary stops (with their canonical
  coordinates and category from PR #521) and the **already-computed** route data
  behind the inline connectors, and returns:
  - a **plain-English assessment** of the day's flow ("mostly sequential" vs
    "notable backtracking"),
  - **specific, non-binding suggestions** the user can choose to act on,
  - **honest gaps** ("2 of 5 stops have no location data").
- It is **explain-first**: every statement it makes is traceable to real
  itinerary data or real provider output — never invented.

### What it **is not**

- ❌ Not an auto-optimizer. It never reorders the day.
- ❌ Not an editor. It never mutates itinerary items, dates, day assignment, or
  order without an explicit, separate user approval action.
- ❌ Not a travel-time source. It never produces a duration or distance the
  route foundation did not already compute.
- ❌ Not a new provider surface. It calls no new external API and adds no new
  Google Routes calls beyond what the existing foundation already performs.
- ❌ Not a UI rebuild. It does not replace inline connectors or add a separate
  route panel/map line in v1.

### Why it exists

Coordinate coverage and travel times are now honest and observable, but a user
still has to **interpret** them alone. "Day 3 has three stops that zig-zag
across the city" is obvious to a planner staring at a map, not to a user reading
a list. The temptation is to jump to "Optimize Day" (silent auto-reorder), which
this repo has repeatedly refused because it hides decisions from the user and
invites fabricated sequencing. This ADR chooses the honest middle: **AI explains
and proposes; the user decides and acts.**

### How it helps the user

- **Understand route quality** without reading a map — plain-English summary of
  how well the day flows.
- **Improve day flow deliberately** — concrete "consider moving X before Y"
  suggestions the user can accept or ignore, always through the existing manual
  reorder UI.
- **See honest gaps** — which stops lack location data, so the user can fix the
  data instead of trusting a misleading total.
- **Keep full control** — nothing changes unless the user changes it.

---

## 2. User-experience contract

- **Where it appears (conceptually):** adjacent to the **existing inline route
  connectors / day surface** in the Journey Desk day column — the same place the
  user already reads travel info. Not a new tab, drawer, or modal in v1. It is a
  lightweight, reviewable **insight surface** attached to the day the user is
  already looking at.
- **How users trigger it:** **explicit, user-initiated** ("Ask about this day's
  route" / "Review day flow"). Never on page load, never on day open, never on
  scroll, never on a timer. No AI call is made until the user asks.
- **What the AI may say:**
  - a plain-English quality read of the current order ("this day is mostly
    sequential" / "there's noticeable backtracking between stops 2 and 4"),
  - which stops are and are not location-eligible,
  - the **already-computed** segment/day travel figures, clearly attributed as
    provider estimates (or fallback), never re-derived by the AI.
- **What the AI may suggest:** non-binding, reviewable improvements — e.g.
  "consider moving X before Y to reduce backtracking", "this stop is missing
  coordinates; add a location to include it in route quality." Suggestions are
  **proposals, not actions.**
- **What requires explicit approval:** **any** change to itinerary order, day
  assignment, item data, or dates. AI never performs these. The user performs
  them through the existing manual UI, or (in a **later** slice) through an
  explicit "Apply this reorder" action that shows a before/after preview first.
- **What must never happen automatically:**
  - no auto-reorder / silent resequencing,
  - no background or on-load AI calls,
  - no itinerary mutation without an explicit user approval action,
  - no fabricated time/distance/sequence,
  - no hidden provider calls beyond the existing route foundation.

---

## 3. Data contract

- **Eligible stop types:** **only `activity` and `meal`** stops are considered
  for route reasoning — identical to the existing adjacency rule in
  `travelHints.ts` / `computeRouteReadiness` and the eligibility rule in
  `ROUTE_PLANNING_V1_CONTRACT.md §2`.
- **Excluded types:** **flights and hotels are not route stops in v1** (also
  notes). They are never treated as segment endpoints and are never sent for
  route reasoning. (A later spec may add them explicitly; until then they are
  out.)
- **Required fields per eligible stop:** a canonical **`lat`/`lng`** pair
  (validated via `hasRouteableCoordinates` / `readCanonicalLat`/`readCanonicalLng`
  in `tripItemMetadata.ts`, camelCase-first with snake_case fallback) and, where
  present, **`category`**. Both flow from the ingress paths hardened through
  PR #504/#506/#508 and **PR #521** (Saved Items parity).
- **Coordinate rules:** coordinates come **only** from canonical Google Places
  ingress already persisted on the item. **Never geocode from an address, never
  fabricate or interpolate a coordinate** (hard repo invariant — No Mock/Sample
  Visible Data + Enrichment Evidence Only packs).
- **Missing-coordinate behavior (handled honestly):** a stop without canonical
  coordinates is **named as missing** ("this stop has no location data"), **not
  silently dropped and routed around**. If fewer than 2 eligible stops have
  coordinates, AI route reasoning for the day is **not offered** (reuse the
  existing `RouteReadinessStatus` copy: "X of Y stops have location data. Add
  locations before route planning."). AI must never produce a day assessment or
  total that quietly excludes an un-located stop, because that would mislead.
- **Day-level scope:** v1 reasons about **one day at a time**, in the day's
  **current manual order only**. No multi-day or whole-trip reasoning.
- **How category and lat/lng metadata from #521 are used:** `lat`/`lng` gate
  eligibility and are the substrate for any route figure the foundation already
  computed; **`category`** may be used for *explanation only* (e.g. "three meals
  clustered at the end of the day") — never to invent a "better" ordering or to
  fabricate a travel figure. Category is descriptive context, not an optimizer
  input.

---

## 4. Provider contract

- **How Google Routes fits the future implementation:** AI Route Planning v1
  consumes the **existing** Google Routes foundation's output (the inline
  connector legs / `route-estimate` results) as **read-only input**. It defines
  **no new provider** and **no new provider role** — `ROUTE_MATRIX` /
  `google_routes` in `provider_registry.py` remains the single routing authority,
  governed by `ROUTE_PLANNING_V1_CONTRACT.md`.
- **When provider calls are allowed:** only through the **existing** route
  foundation, under its existing gates (flag on, key present, ownership verified,
  user-visible trigger, ≤ cap). AI Route Planning **adds no new call site** and
  must not trigger extra Google Routes requests as a side effect of an AI query.
  If a day already has connector/route data, AI reasons over it; if not, AI does
  **not** silently fire a provider call to obtain it.
- **How provider results are cached/bounded:** AI relies on the route
  foundation's existing caching and stop-cap discipline
  (`ROUTE_PLANNING_V1_CONTRACT.md §4–5`). AI introduces no new cache and must not
  cause a re-bill: re-asking about an unchanged day must not trigger new provider
  calls.
- **Cost guardrails:** no automatic AI-triggered provider calls; no background or
  speculative warming; no fan-out (one day, one reasoning pass per explicit user
  request). The LLM call itself is subject to the repo Latency Budget Pack —
  single, user-triggered, bounded input (one day's eligible stops), no
  per-connector or per-item LLM fan-out.
- **Failure behavior:** if route data is unavailable (flag off, key missing,
  provider error, <2 located stops), AI **says so honestly** and offers only what
  it can honestly say (e.g. coordinate-coverage gaps). It **never** fabricates a
  time/distance to fill the gap and never retry-storms the provider or the LLM.

---

## 5. AI contract

- **Inputs AI can receive:** the current day's **eligible** (`activity`/`meal`)
  stops with canonical `lat`/`lng` and `category`; the stops' **current manual
  order**; and the **already-computed** route/connector figures for that day (if
  present). Nothing else — no addresses to geocode, no cross-day state, no PII
  beyond the coordinates already stored.
- **Outputs AI can produce:** a plain-English day-flow assessment; named
  coordinate-coverage gaps; and **non-binding reorder/flow suggestions** phrased
  as proposals. Every claim must be attributable to a real input.
- **Prohibited outputs:**
  - **No fake times/distances** — AI may only restate figures the route
    foundation produced, attributed as estimates; it may never compute, guess,
    or interpolate a duration/distance.
  - **No unsourced claims** — no "this route is 20% faster", no invented
    congestion/opening-hours/weather facts, no ratings or place facts not present
    in the itinerary data.
  - **No itinerary mutation** — AI emits no write. It cannot reorder, reassign,
    edit dates/metadata, add, or delete items. It returns text/suggestions only.
  - **No silent exclusion** — it must not produce a total or assessment that
    quietly drops an un-located stop.
- **Explainability requirements:** every suggestion must state **why** in plain
  English and **on what basis** (e.g. "stops 2 and 4 are far apart in the current
  order" — grounded in real coordinates/route data). A suggestion the AI cannot
  ground must not be shown. The user must always be able to see the reason before
  deciding.

---

## 6. UI contract

- **Inline connectors remain canonical.** The between-card inline route
  connector is still the single source of route/travel display. AI Route
  Planning v1 does **not** replace, duplicate, or relocate it.
- **No separate route panel** (and no map line / polyline) unless a **later ADR**
  explicitly justifies one. The removed `CheckRoutePanel` is not resurrected.
- **Suggestions are lightweight and reviewable.** The insight surface is a small,
  honest, adjacent affordance (text assessment + named suggestions the user can
  read and act on manually) — not a heavy new workspace.
- **The first implementation slice avoids large UI rebuilds.** v1's frontend
  slice should be a **read-only insight surface** wired to existing day/connector
  data — no Journey Desk restructuring, no new tab/drawer, no map geometry.

---

## 7. Approval model

- **AI may propose (examples, non-binding):**
  - "This day has a lot of backtracking."
  - "Consider moving X before Y."
  - "This stop has missing coordinates."
- **AI may not directly reorder** or apply any change.
- **The user must click an explicit approval action** before any order (or other
  itinerary) change occurs. In v1 that action is simply the **existing manual
  reorder UI** — AI's suggestion is advice the user chooses to follow by hand.
- **Any future "apply this reorder" action** (a later slice, **not v1**) must:
  - be an explicit, clearly-labeled user action (never automatic),
  - **show a before/after preview** of the order change prior to applying,
  - write only on confirmation, and
  - never change anything the preview did not show.
- The UI must never imply the app will reorder anything on its own.

---

## 8. Not v1 (explicit exclusions)

- ❌ **No auto-optimization** / "Optimize Day" silent reorder.
- ❌ **No multi-day or whole-trip route optimization** — single day, current
  order only.
- ❌ **No hotel/flight routing** — flights and hotels are not route stops in v1.
- ❌ **No map route drawing** — no polylines, no drawn paths, no map geometry.
- ❌ **No background or on-load route checks** — every AI query is explicitly
  user-triggered.
- ❌ **No silent AI edits** — no itinerary mutation without an explicit user
  approval action.
- ❌ **No new provider** beyond the existing Google Routes foundation, and no new
  Google Routes call sites triggered by AI.
- ❌ **No generalized trip redesign** — v1 advises on one day's route quality; it
  does not re-plan the trip.

---

## 9. Implementation sequencing

Future recommendations only — **not authorized by this ADR**. Each is an
independent capability slice with its own readiness gate; do not collapse them.

1. **PR A — Route-quality diagnostic contract (backend/contract, flag-gated).**
   A read-only, flag-gated route-quality/day-flow diagnostic derived from the
   existing eligible stops + existing route data (e.g. a backtracking/coverage
   summary shape). No new provider call, no new Google Routes call site, no
   itinerary write. Tests: contract + eligibility + missing-coordinate + "no
   fabricated figures" assertions.

2. **PR B — Read-only route-insight surface (frontend), using existing inline
   connectors.** A lightweight, user-triggered insight affordance adjacent to the
   inline connectors that renders PR A's diagnostic in plain English. Read-only:
   no reorder, no write, no map line, no new panel. Tests: state coverage
   (offered / not-offered-when-<2-located / honest-gap), no-fabrication guards,
   plus visual proof.

3. **PR C — Explicit user-approved reorder-proposal contract (still no
   auto-apply).** Turns a suggestion into an **optional, explicit** "apply this
   reorder" action that shows a **before/after preview** and writes only on
   confirmation. Still no auto-optimization, still one day, still user-driven.
   Tests: approval-required, before/after-shown, no-write-without-confirm,
   nothing-changes-that-preview-didn't-show.

*(An optional PR D could add richer explanations or category-aware context, but
only within the same no-mutation / no-fabrication / user-approval boundaries.)*

---

## 10. Merge gates for future implementation

Before **any** AI Route Planning implementation PR may merge, all of the
following must be true and stated in the PR body:

- [ ] **Tests required** — contract + state coverage for the slice; no merge
      without them.
- [ ] **Visual proof required for any UI** — the read-only insight surface (PR B)
      and any approval UI (PR C) ship with screenshots / UI validation.
- [ ] **Provider evidence required before any runtime claim** — if a PR claims it
      reads live route data, name the failure seam (log key / test name) per repo
      runtime-evidence rules; no unproven "it works in production" claims.
- [ ] **No route mutation without approval tests** — any slice that can change
      order/data must prove, in tests, that nothing writes without an explicit
      user approval action and a shown before/after preview.
- [ ] **No merge if fake times or weak missing-coordinate handling** — tests must
      prove AI never fabricates a time/distance and never silently drops an
      un-located stop; the honest "X of Y stops have location data" path is
      exercised.
- [ ] **No new provider / no new Google Routes call site** introduced by the AI
      layer — verified against `provider_registry.py`; `ROUTE_MATRIX` remains the
      single routing authority.
- [ ] **Supabase SQL requirement stated** (expected: **none** — diagnostics are
      derived and ephemeral).
- [ ] **Latency Budget Pack honored** — user-triggered, single bounded LLM pass
      per request, no per-item fan-out, no background calls.

If any box cannot be checked, the AI layer stays off.

---

## Out of scope for this ADR (no production changes)

No production code, no package changes, no env vars added, no SQL, no new
provider, no new Google Routes call, no UI, no itinerary mutation, no
auto-reorder, no route map. Existing coordinate ingress paths (#504/#506/#508/
#521), the inline route-connector UX (#519), the Google Routes foundation, and
the Journey Desk layout are all untouched. The recently merged
background/atmosphere work is not touched. This is a decision-only document.
