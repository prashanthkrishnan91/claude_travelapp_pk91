# Journey Desk Closeout + My Trips Visual Refresh — Plan

**Last updated:** 2026-05-26
**Status:** Plan / audit only. **No behavior or visual change is authorized by this doc.**
**Owner relationship:** Extends `JOURNEY_DESK_ITINERARY_PARITY_PLAN.md` (parity matrix stays the authority for legacy-tab removal). This doc adds the *cleanup closeout* view and the *My Trips / trip-detail visual* assessment that the parity plan does not cover.
**Source-inspected (this pass):** `frontend/src/app/trips/page.tsx`, `frontend/src/app/trips/[id]/page.tsx`, `TripBrief.tsx`, `TripBuilder.tsx`, `TripIdeasPanel.tsx`, `IdeasTray.tsx`, `AddToDayDrawer.tsx`, `Dayboard.tsx`, `ExpandedDayPanel.tsx`, `MapFoldOut.tsx`, `lib/tripBriefFacts.ts`, `lib/hotelStaySpans.ts`.
**Aligns with:** `docs/product/DESIGN_IMPLEMENTATION_CONTRACT.md`, `docs/ai/design/PRIVATE_TRAVEL_ATELIER_DIRECTION.md`, `docs/product/NORTH_STAR.md`.

---

## 0. What recently shipped (truth state going in)

These are merged and form the baseline this plan reasons about:

- Brief is **read-only** and renders a grouped summary of fixed scheduled facts (Flights / Stays / Timed) with a disclosure for full detail (`TripBrief.tsx` + `lib/tripBriefFacts.ts`).
- **Itinerary owns editing and day placement.** ExpandedDay now also has per-item **Remove** (two-step confirm) and non-destructive **Back to Ideas** via `unplaceItemToIdeas` — i.e. parity Slice 1 is **done**, not pending.
- Hotels support **check-in/check-out stay spans**; build-added hotels anchor to the matching check-in day; intermediate/checkout days show read-only markers (`lib/hotelStaySpans.ts`).
- Restaurant `reservationTime` and activity `entryTime` metadata exist and render as facts.
- **Ideas tab** (`TripIdeasPanel`) is canonical idea management; **IdeasTray** is quick placement only; **Build** is an internal add/search surface omitted from mobile nav.
- Move / Back to Ideas uses the safe `unplaceItemToIdeas` path everywhere in Journey Desk (the legacy `moveIdeaToTripIdeas` orphan gap is avoided by JD surfaces).

---

## 1. Current IA ownership map

| Surface | File | Role today | Editing? | Visual world |
|---|---|---|---|---|
| **Brief** | `TripBrief.tsx` | Read-only at-a-glance: grouped fixed facts (Flights/Stays/Timed) + disclosure + "still to decide" count + one Review-ideas action. | None. | Paper (Journey Desk v1). |
| **Itinerary** (legacy) | `ItineraryDayColumn.tsx` via `TripBuilder` `itinerary` workspace | Full structured day editing: remove, move-to-ideas, drag/reorder, Suggest Timing, Plan My Day, travel hints, compare, add-note, Add Day. | **Full.** | Paper card surfaces, but the `TripBuilder` chrome around it still has orphan dark panels (see §4). |
| **Ideas tab** | `TripIdeasPanel.tsx` | **Canonical** idea management: status, note editing, search/filter/sort, per-vertical grouping, assign-to-day, remove. | Idea-level. | Paper (polished #482). |
| **IdeasTray** | `IdeasTray.tsx` | **Quick placement only**: Add to Day / Keep as Maybe / note preview / Map / Google Flights / Manage in Ideas / Remove. | Placement + remove. | Paper drawer/sheet. |
| **Build** (internal) | `TripBuilder.tsx` candidate panels | Provider search + add-to-itinerary (flights/hotels/dining/attractions). | Adds candidates to a target day. | **Omitted from mobile nav**; reached via Add-to-Day handoff + desktop column. |
| **Dayboard** | `Dayboard.tsx` | Read-only collapsed day cards (10-sec read) + per-day Add-to-Day "+" + Trip-map link. | None. | Paper. |
| **ExpandedDay** | `ExpandedDayPanel.tsx` | Selected-day workspace: grouped items (Morning/Afternoon/Evening/Logistics/Anytime) + calm decision strip + per-item Remove/Back-to-Ideas + Add-from-Ideas + Edit-in-Itinerary. | Remove + unplace only (deeper edits delegate to legacy). | Paper. |
| **MapFoldOut** | `MapFoldOut.tsx` | Trip/Day/Ideas lens, real pins, Move/Back-to-Ideas/Remove, honest map-ready list. | Placement/unplace/remove via durable writes. | Framed "atlas" panel (paper-framed map). |
| **My Trips list / trip cards** | `app/trips/page.tsx` (`JourneyCard`, `ContinuePlanningHero`, `TripSection`, `PlanningToolsStrip`, `EmptyDashboard`, `EditModal`, `DeleteModal`) | List of trips: continue-planning hero, active/past grids, planning-tools strip, edit/delete. | Edit/delete trip metadata. | Paper, but **plain** — Folio Slice 2 surfaces only, no signature primitives (see §4). |

**Locked IA (do not drift):** Brief = overview/read-only · Itinerary = structured day editing · Ideas tab = idea management · IdeasTray = quick placement · Build = internal add/search · Dayboard/ExpandedDay = read + light JD-native actions · MapFoldOut = spatial lens · My Trips = trip shelf/list.

---

## 2. Cleanup opportunities

### Safe to clean up now (no parity risk, no behavior change)
- **Stale parity-plan status.** `JOURNEY_DESK_ITINERARY_PARITY_PLAN.md` still lists Slice 1 (ExpandedDay Remove + Back-to-Ideas) as the *next* PR, but it merged (#485). Doc truth-fix only — see §6.
- **Toast token drift.** Both `app/trips/page.tsx` and `app/trips/[id]/page.tsx` toasts use `bg-ds-onyx text-ds-text` dark tokens on otherwise paper routes. As a transient floating overlay this is *allowed* (Folio §20 rule 4), but it is inconsistent with the paper world and is a cheap, low-risk visual-consistency candidate (a later visual PR, not a behavior change).
- **Cover action-token review (cosmetic only).** The trip-detail cover is intentionally cinematic and correctly uses cream `text-ds-text*` tokens; no change needed. Worth *documenting* as correct so a future cleanup doesn't "fix" it into invisibility.

### Must remain (parity not proven — keep as-is)
- **Legacy Itinerary tab and all its editing affordances.** Drag/reorder + `position` persistence (`handleDragEnd`), Add Day for date-less trips (`createDay`), Suggest Timing apply, Plan My Day, compare, add-note, day-part override — these still have **no full Journey Desk destination** (parity Slices 2–5 not built). Removal is gated to parity-plan Slice 6.
- **Build internal surface.** Still the only provider-search + add path; Add-to-Day depends on it. Keep.
- **Ideas tab as canonical management.** IdeasTray is placement-first by design; do not fold the tab into the tray.

### Must NOT be moved into Brief
- Brief is read-only and must stay read-only. Do **not** migrate editing, placement, day-part controls, timing, or idea-status management into Brief. Do not duplicate Itinerary/Ideas/IdeasTray functionality there. Brief summarizes; it never edits.

---

## 3. Legacy / demote decisions

- **Build in primary nav:** Already correct — Build is **omitted from `WORKSPACE_TABS`** (mobile) and reached only via the Add-to-Day handoff + desktop column. No further demotion needed; it is preserved internally. **Recommendation: leave as-is.** Do not surface Build as a primary tab; do not delete it.
- **Stale labels / tabs / routes:** None found in the My Trips / trip-detail routes. Desktop/mobile nav labels were already standardized (Home/Discover cleanup). Mobile workspace tabs are Brief/Itinerary/Ideas — coherent. **No route is stale.**
- **Duplicate controls:** No duplicate idea launchers remain (the old "Ideas tray N" pill was removed; Brief "Review ideas" is the single entry). Edit/Delete appear in two places — the My Trips card row *and* the trip-detail cover overflow — but these are different scopes (shelf-level vs in-trip) and are not a true duplicate. **No duplicate-control removal required now.** Note only: the My Trips card inline pencil/trash row reads slightly "admin/dashboard"; that is a *visual* concern for §4, not a control-duplication cleanup.

**Net:** there is **no destructive cleanup** that PR 1 should perform. The "cleanup" PR is doc-truth + (optionally) the toast token consistency nudge — explicitly non-destructive.

---

## 4. My Trips visual refresh assessment

### What currently feels older than Concierge / Saved / Journey Desk
The My Trips list (`app/trips/page.tsx`) already adopted Folio **Slice 2** paper surfaces (`folio-paper-card`, `folio-paper-panel`, `btn-marine`, `folio-muted-label`, `folio-cover-tab`). But compared to the newer rooms (Concierge Salon, Explore Observatory, Saved Private Folio, and the Journey Desk cinematic cover) it is **paper-but-plain**:

- **No editorial serif.** Titles/destinations use sans `font-semibold`. The Atelier rule is "at least one editorial serif element on every screen"; the trip shelf has none. The newer rooms lead with Fraunces.
- **No signature Folio primitives.** No issue masthead, no folio serial, no italic editorial caption, no mapline, no large serif numeral. The cards read as a generic paper list, not a "shelf of personal travel volumes."
- **Card chrome feels admin-ish.** Inline pencil/trash icons on every `JourneyCard` and the hero pull the eye toward management rather than the destination — closer to a dashboard row than a kept volume (Dashboard guidance §26: "trip covers feel like the cover of a personal travel volume," not a KPI row).
- **No cinematic punctuation.** Trip detail has a cinematic cover; the list has zero cinema, so the two surfaces don't feel like the same product yet. (Note: the *list* should stay mostly paper — cinema is rare punctuation, not the list chrome.)

The **trip-detail body** is mostly modern (Journey Desk v1: paper Brief/Dayboard/ExpandedDay + cinematic cover). The remaining old seam there is the **legacy `TripBuilder` chrome** — `CollapsiblePanel` still uses `bg-ds-carbon`/`bg-ds-onyx` (orphan dark panels on a paper page; tracked as Atelier Slice 5 open question). That is the oldest in-trip surface.

### Which surfaces need refresh first (priority)
1. **My Trips list cards** — `JourneyCard` + `ContinuePlanningHero` (the trip shelf is the first impression and the plainest surface).
2. **My Trips supporting chrome** — page masthead, empty state, planning-tools strip, edit/delete modals (carry the same Folio language through).
3. **Trip-detail legacy `TripBuilder` orphan dark panels** — paper-correctness pass on `CollapsiblePanel` (separate, lower-priority; overlaps Atelier Slice 5).

### Design-system direction: Paper Folio vs Cinematic Atelier
- **My Trips list = Paper Folio (paper world).** It is list/shelf chrome and must stay paper per the dual-world contract. Apply the **signature Folio primitives**: editorial serif titles, folio serial as quiet metadata, one italic caption line where real data supports it, issue-masthead treatment for the shelf heading. Marine ink stays the primary action accent; brass is foil-only.
- **Cinematic Atelier = rare punctuation only.** At most the **Continue Planning hero** may carry a single framed cinema plate (a "current issue" cover moment). Do **not** convert the active/past grids or the whole list to dark cinema.
- Trip-detail cover already correctly *is* the cinema punctuation; keep it.

### What to avoid (so we do not start another broad redesign loop)
- **No route / IA / app-shell changes.** Visual only. Do not re-architect My Trips into a new layout system.
- **No behavior changes** to trip CRUD, status grouping (`getTripStatusGroup`), continue-planning selection, or any data fetch.
- **No foundation-only PR that ships invisible CSS.** Every visual PR here must produce *visible* adoption on a named surface (no "primitive added but not used").
- **No cinema everywhere.** Keep cinema rare; the list is paper.
- **No new fonts, no new animation library, no new dependencies.**
- **Do not touch** `TripBuilder` editing behavior, autocomplete portal, round-trip leg logic, or any provider/search/map path.

---

## 5. Recommended PR sequence (max 4)

> All PRs below are **future** work. This doc authorizes none of them to be coded.

### PR 1 — Cleanup closeout (safe, non-destructive) — **this PR**
- **Functional outcome:** Documentation truth-fix only. Establishes this plan; corrects stale parity-plan status; records correct vs. drifted tokens. No app behavior or visual change.
- **Files likely touched:** `docs/ai/design/JOURNEY_DESK_CLOSEOUT_AND_MY_TRIPS_VISUAL_PLAN.md` (this file), `docs/ai/design/JOURNEY_DESK_ITINERARY_PARITY_PLAN.md` (status line), `docs/ai/HANDOFF.md` (truth-state).
- **Do-not-touch:** all frontend components, backend, SQL, providers, routes; do not remove/hide/demote any legacy surface.
- **Validation:** AI readiness gate; docs-only (no app tests).
- **Risk level:** **Very low** (docs only).

### PR 2 — My Trips list visual refresh (Paper Folio) — **first visible modernization**
- **Functional outcome:** `JourneyCard` + `ContinuePlanningHero` + shelf masthead + empty state adopt signature Folio primitives (editorial serif title, folio serial metadata, optional one-line italic caption from real trip data, demoted/quieter edit-delete affordances). No data or behavior change.
- **Files likely touched:** `app/trips/page.tsx`, `globals.css` (folio primitives if a new class is genuinely needed), one targeted test file. Possibly `components/ui/Folio.tsx` if a shared primitive is reused.
- **Do-not-touch:** trip CRUD handlers, `getTripStatusGroup`/`pickContinuePlanning`, data fetch, routes, providers, backend, SQL; no cinema on the grids.
- **Validation:** reduced-motion check; mobile + desktop; Tier 1 targeted source-scan/visual test; manual smoke (open list → open a trip). Screenshots via Vercel preview.
- **Risk level:** **Low–Medium** (visual, single route).

### PR 3 — Continue-Planning cinematic moment + trip-card cohesion
- **Functional outcome:** the Continue Planning hero gains a single framed cinema plate ("current issue" cover) consistent with the trip-detail cover, and the active/past grids get final paper-cohesion polish. Cinema stays rare (hero only).
- **Files likely touched:** `app/trips/page.tsx`, `globals.css`, test.
- **Do-not-touch:** grids stay paper; no behavior change; no new deps.
- **Validation:** reduced-motion (ambient drift gated), contrast AA on the cinema plate, mobile/desktop, Tier 1; Vercel screenshots.
- **Risk level:** **Low–Medium**.

### PR 4 — Trip-detail legacy `TripBuilder` paper-correctness pass
- **Functional outcome:** convert the orphan `bg-ds-carbon`/`bg-ds-onyx` `CollapsiblePanel` chrome to paper-world tokens so the in-trip Build/Itinerary chrome matches the Journey Desk. Visual only.
- **Files likely touched:** `TripBuilder.tsx` (class/token swaps only), `globals.css`, test.
- **Do-not-touch:** all `TripBuilder` editing behavior, drag/reorder, search, add paths, round-trip logic; no provider/search/map change.
- **Validation:** reduced-motion; verify no `text-ds-text*` (cream) on paper backgrounds; unified-folio-cinema-architecture guardrail green; Tier 1–2; Vercel screenshots.
- **Risk level:** **Medium** (touches a large, behavior-rich file even though only tokens change — keep strictly to class swaps).

**Sequencing note:** PR 2 is the highest-value first modernization. PR 4 overlaps Atelier Slice 5 / the parity plan's "keep legacy" constraint — it is *visual-only* and must not alter any Itinerary editing behavior; it does **not** count as parity-plan Slice 6 (legacy removal stays gated).

---

## 6. Docs truth-state actions (PR 1)

- **This file:** created as the closeout + visual plan owner.
- **`JOURNEY_DESK_ITINERARY_PARITY_PLAN.md`:** mark Slice 1 as **merged (#485)** so the sequence reflects current truth; the rest of the matrix is unchanged and still authoritative for legacy removal.
- **`HANDOFF.md`:** add a compact pointer that the next planned direction is My Trips / trip-detail visual modernization (Paper Folio), governed by this doc. Replace/summarize — do not append history.

**Out of scope for every PR in this plan:** backend, SQL, providers, MapTiler, Google Places, routing, search APIs; fake data; duplicating functionality into Brief; overloading IdeasTray; removing/hiding/demoting legacy surfaces (gated to parity-plan Slice 6).
</content>
</invoke>
