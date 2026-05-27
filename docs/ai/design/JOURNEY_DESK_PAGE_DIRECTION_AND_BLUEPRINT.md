# Journey Desk — Trip Detail page direction & implementation blueprint

**Scope:** `/trips/[id]` (Trip Detail). Direction + prototype only — **no app code is implemented in this doc's PR.**
**Prototype:** [`docs/ai/concepts/journey-desk-prototype-v1.html`](../concepts/journey-desk-prototype-v1.html) (open in a browser; resize across 1024px).
**Reference for shell quality only:** My Journeys "The Reading Room" (PR #492, `frontend/src/app/trips/page.tsx`). **Trip Detail must stay Journey Desk, not Reading Room — do not copy the Reading Room identity.**
**Governs by:** Folio direction (`PRIVATE_TRAVEL_ATELIER_DIRECTION.md`), `DESIGN_IMPLEMENTATION_CONTRACT.md`, Journey Desk v1 lineage (`JOURNEY_DESK_V1_BLUEPRINT.md`).

---

## 1. Diagnosis — current Trip Detail IA / layout problems

Verified against `frontend/src/app/trips/[id]/page.tsx`, `AppShell.tsx`, `TripBuilder.tsx`, `TripReadinessCockpit.tsx`.

1. **No approved mood baseline.** Unlike Home/Concierge/Explore/Saved/My Journeys, Trip Detail never got a room-level mood. It renders on the **legacy padded shell** (`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`) with the **static SaaS Sidebar** — `isImmersiveRoom` in `AppShell.tsx:91` deliberately excludes `/trips/[id]`.
2. **Too narrow on laptop/desktop.** Three compounding squeezes: the static sidebar eats left width, the `max-w-7xl` shell caps the rest, and the Brief block is further pinned to `lg:max-w-4xl lg:mx-auto` (`page.tsx:421`) so it doesn't even use the width it has.
3. **Long vertical desktop scroll.** The page stacks **Cover → Brief → Dayboard (+inline ExpandedDay) → section rule → Trip Readiness disclosure**, and only *then* the wide `TripBuilder` (Build + Itinerary). Two full-width stacked regions = a long scroll before reaching the working surface.
4. **Sidebar is not floating.** Home, Saved, Concierge, My Journeys all use the floating `AtelierNavArtifact` + edge-to-edge `home-edge-bleed`. Trip Detail still shows the boxed SaaS sidebar — visually inconsistent with its siblings.
5. **Brief sits over inherited clutter.** Directly below the Brief/Dayboard is the `TripReadinessCockpit` collapsed disclosure labelled **"Trip readiness · concierge notes"** (`page.tsx:585–611`).
6. **Old Trip Readiness is no longer useful.** `deriveReadiness()` recomputes hasFlights/hasHotel/hasDining/activeDayCount — all of which the **Brief already states** (fixed flights/stays/timed facts + pending anchors) and the **Dayboard already states** ("N of M days planned"). It is duplicate signal, and on mobile it is pure noise.
7. **"Concierge notes" shows no real notes.** The cockpit's label promises concierge notes but the component only renders readiness chips + Concierge/Optimize/Edit action buttons. There is **no durable per-trip notes data source** feeding it — so the label over-claims.
8. **Build + Itinerary feel cramped & vertically stacked.** On desktop `TripBuilder` is `lg:flex-row` (Build `lg:w-80` | Itinerary `flex-1`) but it lives *below* the stacked Brief region inside the already-narrow shell, so the side-by-side never gets room to breathe.
9. **Mobile carries duplicate surfaces.** Mobile already separates Brief / Itinerary / Ideas into tabs (`WORKSPACE_TABS`, `page.tsx:68`). The Trip Readiness disclosure and the stacked desktop-oriented sections add scroll and redundancy on top of that tab IA.

---

## 2. Journey Desk page concept & mood (Decision 1)

**Concept:** Trip Detail is a **working drafting desk for one trip** — present-tense, a single plan laid out on a paper desk blotter. The cinematic trip cover is the desk's header plate; below it a **wide Paper Folio planning desk** holds the plan.

**Reading Room vs Journey Desk — the deliberate contrast:**

| | Reading Room (`/trips`) | Journey Desk (`/trips/[id]`) |
|---|---|---|
| Subject | Many trips — a bound **library** | **One** trip — a working **desk** |
| Tense | Retrospective, restful browsing | Present-tense, in-progress planning |
| Hero | Small monogram **edition plate** | Full-width cinematic **cover band** |
| Layout | Centered **shelf of volumes** + reference rail | **Plan rail + working surface** (two working zones) |
| Ambient | Pure brass/sandstone **warm** | **Marine-cool** tinted warm (a work surface, not a reading lamp) |
| Language | "The Folio Library", "volumes", "On the table / Bound" | "The Brief", "The Dayboard", "the working surface" |

**Same Folio world, different temperature.** Paper is still the default chrome; brass stays foil-only; marine ink is the primary action accent; **exactly one** cinematic punctuation (the cover band). The distinction is *ambient temperature + composition + cover treatment*, not a new color system. All values use existing `--ds-*` tokens.

---

## 3. Top cover vs Brief — content split (Decision 2)

**Cover band (cinematic, dark — identity + global trip actions only):**
- Back link to My Journeys
- "Travel Chapter" overline
- Destination `h1` (`chapter-destination-heading` preserved)
- Trip title subtitle (when distinct)
- Vibe / destination-context line (`tripContext.vibe · dateRange`)
- Date range + duration + travelers caption
- **One** primary action: **AI Concierge**; quiet icon overflow: Optimize / Edit / Delete (`chapter-action-*` preserved); a quiet **Trip map** link
- **No planning facts, no idea management, no day editing.**

**The Brief (paper, read-only summary):**
- Fixed scheduled facts from real data (`deriveTripBriefSummary`): Flights / Stays / Timed
- Pending essential anchors (Flights / Stay "still to choose")
- "N still to decide" + a single **Review ideas** action (→ Ideas surface / IdeasTray)
- **Read-only. No editing. No idea management. No day placement.** (unchanged contract)

---

## 4. Section disposition — keep / remove / hide / reframe

| Section | Today | Decision | Why |
|---|---|---|---|
| Trip cover (`trip-chapter-cover`) | cinematic dark | **Keep** — becomes the full-width cover band atop the stage | The one approved cinematic moment |
| The Brief (`TripBrief`) | paper panel | **Keep** — moves into desktop left plan rail; stays read-only | At-a-glance planning state |
| Dayboard (`Dayboard` + inline `ExpandedDayPanel`) | stacked | **Keep** — becomes the day spine in the plan rail (desktop) / Brief tab (mobile) | Day index/navigation |
| **Trip Readiness (`TripReadinessCockpit`)** | collapsed disclosure | **Remove from the page** | Decision 3 — duplicate of Brief + Dayboard; mobile noise. Unmount only; leave the file in the repo |
| **"Concierge notes" framing** | label on the cockpit | **Remove the label; do not replace with a notes artifact yet** | Decision 4 — no durable notes data source; introducing one would fabricate content (No Mock/Sample pack). Concierge stays on the cover |
| Itinerary (`TripBuilder` right panel) | below stacked Brief | **Keep** — becomes the wide working surface | Owns editing/day placement |
| Build (`TripBuilder` left panel) | permanent `lg:w-80` column | **Keep behavior; de-emphasize** — stays an internal add/search utility | Product direction: Build is a utility, not a primary destination |
| Ideas (`TripIdeasPanel`) | tab | **Keep** — canonical idea management | Unchanged ownership |
| IdeasTray / AddToDayDrawer | bottom sheet / drawer | **Keep** — quick placement only | Unchanged ownership |
| MapFoldOut | fold-out | **Keep** — opened from cover "Trip map" | Unchanged |

---

## 5. Desktop composition blueprint (≥1024px) (Decision 5)

```
┌──────────────────────────────────────────────────────────────────────┐
│  floating AtelierNavArtifact (left, in-app)   ·   edge-to-edge canvas  │
│  ┌────────────────────  jd-room-canvas (marine-cool warm desk)  ─────┐ │
│  │  ┌──────────────  jd-stage (floating paper folio, max-w 94rem) ─┐ │ │
│  │  │  ZONE A — COVER BAND (cinematic, full width)                 │ │ │
│  │  │  back · overline · destination · vibe · dates · actions      │ │ │
│  │  ├──────────────────────────────────────────────────────────────┤ │ │
│  │  │  ZONE B — PLANNING DESK (grid: 21rem | 1fr)                  │ │ │
│  │  │  ┌─ PLAN RAIL (sticky) ─┐  ┌─ WORKING SURFACE (flex-1) ────┐ │ │ │
│  │  │  │ The Brief (read-only)│  │ tabs: Itinerary | Ideas       │ │ │ │
│  │  │  │ ───────────────────  │  │ + Add-to-Day utility          │ │ │ │
│  │  │  │ The Dayboard         │  │                               │ │ │ │
│  │  │  │  day spine (cards)   │  │ Itinerary day columns         │ │ │ │
│  │  │  │  (selected → drives  │  │  (TripBuilder right panel;    │ │ │ │
│  │  │  │   working surface)   │  │   editing/placement here)     │ │ │ │
│  │  │  └──────────────────────┘  └───────────────────────────────┘ │ │ │
│  │  └──────────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

- **Shell:** `/trips/[id]` joins `isImmersiveRoom` with `data-atelier-shell="journey-desk"` → SaaS sidebar CSS-suppressed, floating `AtelierNavArtifact`, edge-to-edge `home-edge-bleed`. (My Journeys `/trips` stays `data-atelier-shell="trips"`; route match must be `/trips/[id]`, i.e. starts with `/trips/` and is not exactly `/trips`.)
- **Canvas:** new `.journey-desk-room-canvas` — mirrors `.trips-room-canvas` but a **marine-tinted** top ambient (cool work surface) instead of pure sandstone.
- **Stage:** new `.journey-desk-stage` — mirrors `.trips-shelf-stage` (warm paper folio, brass hairline, deep warm shadow) at **`max-width: 94rem`** (wider than Reading Room's 90rem — it holds a working surface).
- **Plan rail:** `grid-template-columns: 21rem minmax(0,1fr)`; rail is `position: sticky; top: 0`, recessed linen tone, hairline right border (mirrors `.trips-side-panel`). Holds Brief + Dayboard.
- **Working surface:** the existing `TripBuilder` right Itinerary panel, given the wide right zone. **Build stays as `TripBuilder`'s internal utility** (its existing `lg:w-80` left column) — *not* promoted to the desk, *not* a third desk column competing with the plan rail. Selected day in the rail drives the working surface (existing `selectedDayId`).
- **Result:** no separate full-width stacked Brief region; the working surface sits beside the plan, not a long scroll below it.

> Scope note: the *ideal* end-state turns Build into a right-docked drawer so the working surface is purely the Itinerary. That structural `TripBuilder` change is **sequenced as a follow-up** (see §8) to keep PR 1 low-risk and behavior-preserving.

---

## 6. Mobile composition blueprint (<1024px) (Decision 6)

- Same paper stage, **single column**, 1 cinematic cover band (compact).
- **Keep the existing 3-tab IA** (`Brief · Itinerary · Ideas`) — it already prevents duplication; do not add a 4th tab, do not re-stack desktop sections.
- **Brief tab** = read-only Brief + Dayboard day spine (+ inline ExpandedDay on day select).
- **Itinerary tab** = editing / day placement (TripBuilder itinerary workspace).
- **Ideas tab** = canonical idea management (TripIdeasPanel).
- **IdeasTray** (quick placement) and **AddToDayDrawer** slide up from the bottom; **MapFoldOut** is a bottom sheet from "Trip map".
- **Remove** the Trip Readiness disclosure entirely (it was the worst mobile offender).
- No new scroll, no duplicate sections, no readiness block.

---

## 7. Functional ownership (Decision 7 — preserved, no behavior change)

- **Cover** = identity + global trip actions (Concierge / Optimize / Edit / Delete / Trip map / back).
- **Brief** = read-only summary. No editing, no idea management, no day placement.
- **Itinerary** = editing / day placement / reorder / remove. (No behavior change.)
- **Ideas** = canonical idea management (status, notes, filter/sort).
- **IdeasTray** = quick placement only.
- **Build** = internal add/search utility (de-emphasized, not a primary destination).
- No itinerary, hotel stay-span, provider/search/map, or Brief-editing behavior changes anywhere.

---

## 8. Follow-up implementation prompt (one focused PR — DO NOT IMPLEMENT HERE)

> Copy the block below into a fresh Sonnet chat to implement **PR 1**. It is the foundational visible slice; the Build→drawer conversion is intentionally excluded and sequenced as PR 2.

```
Task: Implement Journey Desk PR 1 — Trip Detail (/trips/[id]) immersive shell + mood + desktop plan-desk framing.
Direction: docs/ai/design/JOURNEY_DESK_PAGE_DIRECTION_AND_BLUEPRINT.md + docs/ai/concepts/journey-desk-prototype-v1.html.
Safety pack: Folio paper-world rules + No Mock/Sample Visible Data pack (SAFETY_PACKS_AND_ARCHETYPES.md). Archetype: visible design adoption (frontend-only).
Roadmap: Stage 3.5 design adoption; build queue item = Journey Desk page direction.

Read first: frontend/src/app/trips/[id]/page.tsx, frontend/src/components/layout/AppShell.tsx,
frontend/src/app/trips/page.tsx (Reading Room shell — reference for shell QUALITY only, do NOT copy its identity),
frontend/src/app/globals.css (.trips-room-canvas / .trips-shelf-stage / .trips-reading-layout / .trips-side-panel / .journey-desk-cover).

Do exactly this:
1. AppShell.tsx: add `isTripDetailRoute = pathname.startsWith("/trips/") && pathname !== "/trips"`. Include it in `isImmersiveRoom`; render <AtelierNavArtifact /> for it (suppress <Sidebar/> like the other immersive rooms); set data-atelier-shell="journey-desk". Add the matching `.atelier-atmosphere-root[data-atelier-shell="journey-desk"] .folio-sidebar { display:none }` rule next to the existing trips/saved/explore/salon rules. Keep the isHomePage ternary + max-w-7xl branch intact (8J/atrium contracts).
2. globals.css: add `.journey-desk-room-canvas` (clone .trips-room-canvas but the top radial uses --ds-marine-ink ~14% instead of sandstone — the cool work-surface tint), `.journey-desk-stage` (clone .trips-shelf-stage at max-width:94rem), `.journey-desk-layout` (flex column; @media ≥1024px: grid-template-columns:21rem minmax(0,1fr); align-items:start), `.journey-desk-plan-rail` (≥1024px: position:sticky; top:0; border-right hairline; recessed linen tone — mirror .trips-side-panel). All under @layer components; reduced-motion safe (no new transitions needed).
3. page.tsx: wrap the whole trip-detail body in `.journey-desk-room-canvas > .journey-desk-stage`. Put the cover <section> as a full-width band at the top of the stage. Below it, on desktop, render `.journey-desk-layout` with the Brief + Dayboard (the existing `trip-mobile-panel-brief` content minus readiness) as `.journey-desk-plan-rail`, and the existing TripBuilder workspace as the right working surface. REMOVE the `lg:max-w-4xl lg:mx-auto` cap. Keep the existing mobile tab IA exactly as-is (Brief/Itinerary/Ideas), just hosted inside the new stage.
4. REMOVE the TripReadinessCockpit block (page.tsx ~585–611) and its `cockpitOpen` state, the import, and the "Trip readiness · concierge notes" toggle. Do NOT add a replacement notes artifact (no durable notes data source — would fabricate content). Leave TripReadinessCockpit.tsx in the repo unused.
5. Keep all handlers/props/testids on cover actions, Brief, Dayboard, TripBuilder, MapFoldOut, IdeasTray, AddToDayDrawer, AIConciergePanel unchanged.

Hard constraints: frontend-only. No SQL/backend/provider/search/map behavior change. No itinerary behavior change. No hotel stay-span change. No Brief editing. No idea-management duplication into Brief/IdeasTray. No TripBuilder internal restructure (Build stays its current internal left column — converting Build to a drawer is PR 2, out of scope). No new fonts/deps. Use only --ds-* tokens; brass foil-only; one cinematic surface (the cover). prefers-reduced-motion respected.

Acceptance evidence:
- /trips/[id] renders with the floating AtelierNavArtifact (no SaaS sidebar), edge-to-edge, on the marine-cool desk canvas with a wide floating paper stage.
- Desktop: cover band full width; Brief+Dayboard in a sticky left plan rail; Itinerary working surface beside it (not stacked below a narrow centered Brief); no max-w-4xl cap; visibly wider than before.
- Trip Readiness / "concierge notes" disclosure is gone; Concierge still opens from the cover.
- Mobile: same 3-tab IA, compact cover, no readiness block, no duplicate sections.
- It reads as Journey Desk (cover band + plan rail + working surface), NOT Reading Room (no shelf/volumes/edition-plate/"Elsewhere in the house").
Test tier: per TEST_ROUTING.md — add/extend a source-scan suite (shell route match, journey-desk CSS primitives present, readiness cockpit removed, ownership testids intact, mobile tab IA preserved). State test tier + why sufficient in the PR body.
Update docs/ai/HANDOFF.md (replace/summarize). Fill the PR template honestly (incl. Supabase SQL = none, AI usage note).
Stop after PR 1. Do NOT propose PR 2 in the same chat.
```

### Sequenced follow-ups (not in PR 1)
- **PR 2 — Build → right-docked utility drawer.** Convert `TripBuilder`'s permanent `lg:w-80` Build column into a right-docked drawer opened from the "Add" affordances, so the desktop working surface is purely the Itinerary. Touches `TripBuilder` structure → its own slice; preserve all search/placement/drag behavior.
- **PR 3 (deferred) — genuine travel-notes artifact.** Only once a durable per-trip notes data source exists. Until then, do not render a notes surface.

---

## 9. Stop condition

This deliverable ends at the prototype + blueprint + the PR 1 prompt above. **No app code is changed in this PR.** Implementation happens in a separate, fresh-chat PR per §8.
