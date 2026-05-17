# UI Baseline

Last updated: 2026-05-17 (Phase 8C)

## Purpose

Tracks the state of the design system and UI primitive layer so future prompts and PRs can reason accurately about what exists and what has been adopted.

---

## Stage 3.5 Phase 8C — Itinerary ItemCard Chapter-Style Editorial Polish — SHIPPED (2026-05-17)

**Stage 3.5 · Wife-Wow design system — `ItineraryItemCard.tsx` · Trip-story chapter-entry card**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/trips/ItineraryItemCard.tsx` | **Editorial transformation.** Root changed from `<div>` to `<article data-testid="itinerary-item-card">` for semantic chapter-entry identity. `TYPE_LABELS` map added: flight→Flight, hotel→Stay, activity→Activity, meal→Dining, transit→Transit, note→Note. New **entry header row**: type icon (existing, moved inside content) + Overline type label (`text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-text-tertiary`, `data-testid="item-type-overline"`) on left; action cluster (move-to-ideas, compare, timeline, booking, remove) on right. Title promoted from `text-xs font-semibold` to `text-[13px] font-semibold` with `data-testid="item-title"`. Flight/hotel/activity/meal type-specific sections gain `pt-1 border-t border-ds-pen-stroke/40` hairline top separator for editorial rhythm. Padding increased `p-2`→`p-3`. All behavior preserved exactly: round-trip one-card rendering (`itinerary-roundtrip-flight` testid, both legs via `renderLeg`), Google Flights link-out (`itinerary-google-flights-cta`, `-my-3.5 py-3.5` touch target), DnD sortable, compare toggle, move-to-ideas conditional, timeline editor, booking checklist. No `rgba()`, no raw hex, no legacy palette classes. `var(--ds-accent-subtle)` inline style for icon/button backgrounds. |
| `frontend/tests/itinerary-chapter-editorial.test.mjs` | **NEW.** 63 Phase 8C contract tests: TYPE_LABELS map, item-type-overline testid, Overline typography role (tracking/uppercase/10px/semibold), title prominence, article semantic element, itinerary-item-card testid, no raw hex/rgba/legacy palette, ds-token surface classes, semantic button/link actions, no card-level onClick navigation, no fake/mock/sample data, no backend imports, all preserved actions (remove/compare/move-to-ideas/booking/timeline/DnD), round-trip one-card rendering, Google Flights link-out contract (URL fields, testid, aria-label, touch target, rel), mobile-safe layout (flex-shrink-0, min-h-[44px], -m-3 p-3, -m-3.5 p-3.5), day column behavior preservation. |
| `frontend/package.json` | Added `itinerary-chapter-editorial.test.mjs` to test script. |

### Test results
- **1025 tests, 0 failures** (was 962; +63 new Phase 8C chapter editorial contract tests)
- All pre-existing tests continue to pass (including all itinerary-card-finalized-display, trip-flight-cards-canonical, hotel-itinerary-display, itinerary-timeline, trip-planning-card-tokens, trip-canvas-day-system tests)

### Design contract alignment

- **Chapter entry, not generic card:** Each itinerary item opens with an Overline type identity line (FLIGHT/STAY/ACTIVITY/DINING/TRANSIT/NOTE) + the type icon. The item title is the headline. Type-specific details (route legs, check-in dates, rating, cuisine) follow with a hairline separator. The card reads top-down like a chapter entry, not a tile with an icon bolted on.
- **Editorial type labels:** `TYPE_LABELS` maps backend `ItemType` values to editorially meaningful labels. Hotel → "Stay" (not "Hotel"), meal → "Dining" (not "Meal"). This aligns with the travel-chapter register.
- **Promoted title:** `text-[13px] font-semibold` vs old `text-xs font-semibold` — one step up in the typography ladder, enough to feel like a headline without competing with the day-column chapter heading.
- **Hairline rhythm:** Type-specific sections (flight route, hotel stay span, activity rating, dining details) gain `pt-1 border-t border-ds-pen-stroke/40` — a subtle visual separator that gives each block its own editorial space.
- **More breathing:** `p-3` (vs `p-2`) gives the card slightly more interior breathing, matching the editorial register of day-column chapter headers above.
- **Semantic element:** `<article>` is the correct HTML semantic for a self-contained chapter entry in a trip's itinerary.
- **Overline type role exact:** `text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-text-tertiary` — matches Design Bible Overline type role exactly (§4.4).
- **Action cluster unchanged in behavior:** All actions (remove, compare, move-to-ideas, timeline, booking, drag) are unchanged in handler wiring. They now live in the overline row's right side for cleaner layout.

### Invariant confirmations
- No backend files; no API/search/provider/Tavily/cache/Supabase/env changes.
- No Google Flights URL generation changes; no Duffel provider changes.
- No new fonts, route rewrites, or data model changes.
- No new booking behavior; no fake data.
- Round-trip one-card rendering: preserved (`itinerary-roundtrip-flight` testid, `renderLeg(outboundLeg)` + `renderLeg(returnLeg)` in single card).
- Google Flights link-out: preserved (`itinerary-google-flights-cta` testid, `aria-label="Search on Google Flights"`, canonical URL fields, `-my-3.5 py-3.5` touch target).
- All TripBuilder logic, add-to-day behavior, ItineraryDayColumn, and AI Concierge panel unchanged.

### Accessibility / motion note
- No new motion, gradients, glass blur, or animations introduced in Phase 8C. The dragging state uses `opacity-60 scale-95 backdrop-blur-md` inherited from Phase 3 (pre-existing). No reduced-motion accommodation required for new Phase 8C changes. All interactive elements use `focus-visible:ring-2 focus-visible:ring-ds-accent` inherited patterns; no new interactive patterns added.

---

## Stage 3.5 Phase 8B — Trip Detail Travel Chapter + Planning Canvas Overhaul — SHIPPED (2026-05-16)

**Stage 3.5 · Wife-Wow design system — `/trips/[id]` trip detail surface · Travel-chapter cover + advisor briefing**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/app/trips/[id]/page.tsx` | **Major redesign.** Removed: `DESTINATION_GRADIENTS`/`DEFAULT_GRADIENT`/`getDestinationGradient` (raw hex gradients), `destination-bg`/`destination-overlay` divs, `PageHeader` import+usage, inline tripContext header strip. New **TripChapterCover** `<section>` with: `data-testid="trip-chapter-cover"`, `aria-labelledby="chapter-destination-heading"`, back "My Journeys" Link, Overline "Travel Chapter", `<h1 id>` with real `trip.destination`, italic tripContext vibe, `CalendarDays text-ds-accent` dates row, day-count caption. Action cluster (`data-testid="chapter-actions"`) with 4 semantic buttons: AI Concierge (`COVER_PRIMARY`), Optimize, Edit Trip, Delete (`COVER_DANGER`) — all `min-h-[44px]`, `focus-visible:outline-ds-accent`. Modal dialogs updated from `bg-white/text-slate-*/border-slate-*` to `bg-ds-onyx/text-ds-text/border-ds-pen-stroke`. All `ds-elevation-4` for modals. Loading state updated to editorial chapter cover skeleton. All behavior (edit/delete/optimize/concierge/trip-builder/add-to-day) preserved. |
| `frontend/src/components/trips/TripReadinessCockpit.tsx` | **Advisor briefing transformation.** Removed: score indicator (`coveredCount/signals.length` fraction), "Trip Briefing" overline text → changed to "Concierge Notes", "Day Coverage" section overline label, "Next Step" overline label, "Also try" section label. Kept: all `data-testid` attributes, `aria-labelledby/id` pairing, all callbacks (onOpenConcierge/onOpenOptimize/onOpenEdit), all signal keys/itemType checks, all copy ("Looks like…"/"Still needs…"), day pills with `aria-label`, `role="list"`, signal grid. Signal grid changed from `items-start gap-2.5` to `items-center gap-2.5`. Next-step description now has `italic` for advisor tone. Day coverage summary phrase changed from "have plans" to "days planned". Planning tools strip: "Also try" label removed; links remain. |
| `frontend/tests/trip-chapter-overhaul.test.mjs` | **NEW.** 70 Phase 8B contract tests: chapter cover section/h1/aria structure, Overline pattern, destination-as-heading, trip-title-subtitle, context vibe italic, dates/day-count row, back link to /trips, action cluster testids, all 4 semantic buttons, min-h-[44px] via constant, focus-visible outline, no card-level onClick on section, ds-token coverage, no raw hex (no DESTINATION_GRADIENTS/destination-bg), no bg-white/text-slate/border-slate/sky-500 in modals, no PageHeader import, no fake/mock data, no backend/provider imports, preserved TripReadinessCockpit/TripBuilder/AIConciergePanel/OptimizeTripModal, chapter-before-cockpit ordering, cockpit-before-builder ordering, preserved callbacks, advisor briefing structure (Concierge Notes overline, no score, no DAY COVERAGE/NEXT STEP/ALSO TRY labels, italic next-step, honest signal copy). |
| `frontend/package.json` | Added `trip-chapter-overhaul.test.mjs` to test script. |

### Test results
- **962 tests, 0 failures** (was 892; +70 new Phase 8B chapter overhaul contract tests)
- All pre-existing tests continue to pass (including trip-canvas-day-system, trip-readiness-cockpit)

### Design contract alignment

- **Travel chapter, not dashboard:** `/trips/[id]` now opens with a `<section>` editorial chapter cover rather than a PageHeader + context widget + toolbar. Destination is the large `<h1>` heading, trip title is a subtitle, context vibe is italic caption prose. No score tiles, no progress rings, no KPI indicators.
- **Destination identity:** `trip.destination` is now the primary h1 heading. The old colorful OTA-style destination-gradient backgrounds (raw hex, conflict with Design Bible dark-mode system) are removed. The page uses the dark ink-ladder system consistently.
- **Advisor briefing:** TripReadinessCockpit "Concierge Notes" overline + adaptive h2 headline. No score fraction. Day pills remain (contextual at-a-glance), but the "DAY COVERAGE" dashboard label is gone. Signals present as natural advisor observations. Next-step prose is italic. No labels ("NEXT STEP", "ALSO TRY") that read like productivity UI chrome.
- **Semantic actions:** All 4 actions (AI Concierge, Optimize, Edit Trip, Delete) are real `<button>` elements with explicit `onClick`, `data-testid`, `min-h-[44px]`, `focus-visible:outline-ds-accent`. Arranged naturally within the chapter cover — not a toolbar.
- **Modal ds-tokens:** Edit and Delete modals updated from `bg-white/text-slate-*/border-slate-*/ring-sky-500` to `bg-ds-onyx/text-ds-text/border-ds-pen-stroke/ring-ds-accent`.
- **Mobile:** Cover, advisor briefing, and planning canvas stack cleanly. Action cluster wraps with `flex-wrap`. No horizontal overflow risk.

### Invariant confirmations
- No backend files; no API/search/provider/Tavily/cache/Supabase/env changes.
- No Google Flights URL changes; no Duffel provider changes.
- No new fonts, route rewrites, or data model changes.
- No new booking behavior; no fake data.
- All TripBuilder logic, add-to-day behavior, itinerary item cards, and AI Concierge panel unchanged.

---

## Stage 3.5 Phase 8A — Private Atelier Home + Journey Shelf — SHIPPED (2026-05-16)

**Stage 3.5 · Wife-Wow design system — `/` home + `/trips` My Journeys surfaces · Atelier-home transformation + travel-volume journey shelf**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/dashboard/DashboardClient.tsx` | **Major redesign.** Removed 4 KPI stat cards (Total Trips, Upcoming, Travel Cards, Total Points), RecentTrips, QuickActions, PointsSummary, DealsFeed. New layout: (1) `AtelierGreeting` — editorial time-based greeting + real `summary.tripCount` shelf count, Overline "Private Travel Concierge"; (2) `ConciergeEntry` — primary ds-elevation-2 card with Sparkles icon, "AI Travel Concierge" h2, description, `Open Concierge` link with 44px target + focus-visible ring; (3) `ContinuePlanningStrip` — most-active trip card using real `getTripStatusGroup`/`STATUS_PRIORITY` sort, with `Link href=/trips/${trip.id}`, `TripStatusBadge`, destination + dates from real data; (4) `JourneyShelfTeaser` — `Link href=/trips` with real `summary.tripCount`, "Browse your full journey shelf" copy; (5) `EmptyAtelierHome` — editorial empty state with Plan a Trip + Open Concierge CTAs; (6) `AtelierPlanningStrip` — 2-column Explore + Saved Ideas grid. All ds-* tokens, `bg-ds-accent-subtle`, `text-ds-accent`, focus-visible rings, no legacy colors. `fetchDealsFeed`/`fetchCards` calls removed. |
| `frontend/src/app/trips/page.tsx` | **Visual upgrade.** `JourneyCard` redesigned as travel-volume cover: destination (`trip.destination`) is now the large `text-lg font-semibold` hero text; trip title is the `<Link href=/trips/${trip.id}>` subtitle (semantic navigation); status badge at top; card-footer has date+travelers + "Open →" Link (44px); edit/delete buttons with aria-labels preserved; MapPin icon removed (destination text is the identity). `ContinuePlanningHero` elevated: destination is now an editorial overline above the trip title `<h2>`; action footer separated with `border-t`. Page header gains editorial "Your Travel Shelf" overline above "My Journeys" h1. All existing function names, props, interfaces, and modals unchanged. |
| `frontend/src/app/page.tsx` | Metadata title changed from `"Dashboard"` to `"Home"`. |
| `frontend/tests/atelier-home-journey-shelf.test.mjs` | **NEW.** 56 Phase 8A contract tests: atelier-greeting/concierge-entry/atelier-home testids, time-based greeting, real tripCount, no KPI imports, ds-token contract, no legacy colors, no card-level onClick nav, no fake data, focus-visible rings, ConciergeEntry semantic Link, ContinuePlanningStrip real trip id link, JourneyShelfTeaser /trips link, AtelierPlanningStrip Explore/Saved links, JourneyCard destination-as-hero, travel-volume footer, editorial overline in page header, preserved create/edit/delete/open affordances, no backend/provider imports. |
| `frontend/package.json` | Added `atelier-home-journey-shelf.test.mjs` to test script. |

### Test results
- **892 tests, 0 failures** (was 836; +56 new Phase 8A atelier home + journey shelf contract tests)
- All pre-existing tests continue to pass

### Design contract alignment

- **Private atelier home:** `/` no longer leads with KPI stat tiles. It opens with a time-based editorial greeting using real trip count, then positions the AI Concierge as the primary planning instrument (elevation-2 card, prominent CTA). Secondary: continue-planning strip (real data), journey shelf teaser, discovery tools. No fake personalization, no user name invented, no fabricated stats.
- **Journey shelf:** `/trips` JourneyCard now reads destination as the large editorial title (like the front of a travel volume). Status is a quiet overline marker. Trip title is the semantic navigation link. Dates and traveler count anchor the footer. The card communicates "this is a travel place" not "this is a SaaS record."
- **Concierge elevation:** Concierge is now the lead CTA on the home page — not buried in a "Quick Actions" grid. This matches Design Bible Addendum §1 (private atelier) and Design Bible §26 (AI launch pill).
- **Editorial greeting:** "Good morning/afternoon/evening." + "{N} trips on your shelf." — all real data (time of day + `summary.tripCount`). No invented name, no fake stat.
- **Token contract:** No raw hex, no legacy `cream-*`/`brand-*`/`violet-*`/`emerald-*`/`amber-*` colors in changed files. All surfaces use ds-* tokens. `bg-ds-accent-subtle` on icon wrappers. `text-ds-accent` on accent elements. `border-ds-pen-stroke` / `bg-ds-carbon` / `bg-ds-onyx` on surfaces.
- **Semantic navigation:** All navigation via real `<Link href>` or `<button onClick>`. No `onClick={() => router.push}` patterns. No card-level click-only navigation.
- **Touch targets:** `min-h-[44px]` on all primary CTAs and action buttons. `min-w-[44px]` on icon-only buttons.
- **Accessibility:** `focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2` on all interactive elements. `aria-label` on icon-only buttons. `aria-hidden="true"` on decorative icons. `aria-busy="true"` on loading skeleton.
- **Mobile:** 2-column discovery strip (Explore + Saved). EmptyAtelierHome uses `flex-col sm:flex-row` for stacked-then-side-by-side CTAs. JourneyCard grid `md:grid-cols-2 xl:grid-cols-3` for responsive shelf.

### Invariant confirmations
- No backend files, no API/search/provider/Tavily/cache changes.
- No Supabase SQL, no new env vars, no new dependencies.
- No new fonts, no route rewrites, no data model changes.
- No new booking behavior, no fake data.
- All existing edit/delete/create/open affordances preserved on `/trips`.

---

## Stage 3.5 Phase 7 — Trip Readiness / Review Cockpit — SHIPPED (2026-05-16)

**Stage 3.5 · Wife-Wow design system — Trip detail `trips/[id]` surface · Premium trip-planning intelligence cockpit**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/trips/TripReadinessCockpit.tsx` | **NEW.** `<section aria-labelledby>` root with 5 zones: (1) header bar — Overline "Trip Briefing" + `<h2>` headline + N/4 score indicator; (2) day coverage strip — filled/empty day pills (`bg-ds-accent` / `border-ds-pen-stroke`) with `role="list"` + per-pill `aria-label`; (3) signal grid — 4 category signals (Flights/Stay/Dining/Activities) with `bg-[var(--ds-accent-subtle)]` icon ring when present; (4) next-step footer — contextual CTA prioritised dates→flights→hotel→empty days→all good, real `<button>` callbacks + `<Link>` routes; (5) planning tools strip — Explore / Saved Ideas / AI Concierge links. All ds-* tokens. `min-h-[44px]` on action buttons. `focus-visible:outline-ds-accent` on all interactives. `aria-hidden="true"` on all icons. |
| `frontend/src/app/trips/[id]/page.tsx` | Import + conditional render of `TripReadinessCockpit` (guarded by `trip !== null`) between `PageHeader` and `TripBuilder`. Props: `trip`, `itineraryDays`, `onOpenConcierge`, `onOpenOptimize`, `onOpenEdit`. |
| `frontend/tests/trip-readiness-cockpit.test.mjs` | **NEW.** 65 static/contract tests: semantic section/h2 structure, data-testid contract, ds-* token coverage, Overline pattern, aria-hidden icons, 44px touch targets, focus-visible rings, real Link/button elements only, no card-level onClick, no backend imports, no fake data, signal key coverage, empty-data defensive handling, page integration wiring. |
| `frontend/package.json` | Added `trip-readiness-cockpit.test.mjs` to test script. |

### Test results
- **836 tests, 0 failures** (was 771; +65 new Phase 7 readiness cockpit contract tests)
- All pre-existing tests continue to pass

### Design contract alignment

- **Editorial advisory tone:** Overline "Trip Briefing" + `<h2>` headline copy adapts to data density ("Start by adding your travel dates" / "Good progress — a few gaps to fill" / "Your trip is looking well-planned"). Reads like a private advisor's briefing, not a SaaS checklist.
- **Dark tone surface:** Root `bg-ds-onyx border-ds-pen-stroke shadow-[var(--ds-elevation-2)]` — correct ink-ladder elevation above body.
- **Footer tonal shift:** Next-step area uses `bg-ds-carbon` — one step darker, creates editorial anchor at bottom of section.
- **Signal icons:** Present = `bg-[var(--ds-accent-subtle)] text-ds-accent` round icon; missing = `border-ds-pen-stroke text-ds-text-tertiary` empty ring. Clear visual grammar without traffic-light colors.
- **Day coverage pills:** Filled = `bg-ds-accent text-ds-text-inverse`; empty = `border-ds-pen-stroke text-ds-text-tertiary`. Compact at `w-7 h-7`. Adaptive summary text.
- **Overline labels:** All section labels use exact `text-[10px] font-semibold uppercase tracking-[0.1em]` Overline pattern.
- **Next-step CTAs:** Primary = `bg-ds-accent text-ds-text-inverse`; secondary = `border-ds-pen-stroke text-ds-text-secondary hover:bg-ds-carbon`. Real `<button>` for callbacks, `<Link>` for routes.
- **Accessibility:** Full semantic structure — `<section aria-labelledby>`, `<h2 id>`, `role="list"` on day pills, `role="listitem"` on each pill, `aria-label` on pills and icon-only button, `aria-hidden` on all decorative icons.
- **Touch targets:** `min-h-[44px]` on action buttons. Planning tools strip links are text links (not primary actions).
- **No card-level click-only navigation:** Root `<section>` has no `onClick`. All navigation via real `<button>` or `<Link>`. Confirmed by contract test.

### Invariant confirmations
- No backend files; no API/search/provider/Tavily/cache changes.
- No Supabase SQL; no new env vars; no new dependencies.
- No new fonts; no route rewrites; no data model changes.
- No new booking behavior; no fake data.
- Existing TripBuilder, ItineraryDayColumn, ItineraryItemCard, AIConciergePanel behavior fully preserved.

---

## Stage 3.5 Phase 5 — TripBuilder Command Surface — SHIPPED (2026-05-16)

**Stage 3.5 · Wife-Wow design system — TripBuilder left-panel search + CandidatePanel command center**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/trips/TripBuilder.tsx` | CandidatePanel: removed `accentColor` prop, root → `rounded-2xl border border-ds-pen-stroke bg-ds-onyx shadow-[var(--ds-elevation-1)]`, toggle button `min-h-[44px] px-4 py-3`, count badge → styled pill with `var(--ds-accent-subtle)` bg + `text-ds-accent border-ds-pen-stroke`. Activities section: `.card p-3` → `rounded-2xl border border-ds-pen-stroke bg-ds-onyx shadow-[var(--ds-elevation-1)]` with ds-token header row. Compare bar: `shadow-2xl` → `shadow-[var(--ds-elevation-4)]`, added Overline "Compare" label + `tracking-[0.1em]`, dots `w-2 h-2` → `w-1.5 h-1.5`. DragOverlay + toast: `shadow-2xl` → `shadow-[var(--ds-elevation-3)]`. Right panel header: "Itinerary" plain h2 → Overline "Your Itinerary" + item count as `text-ds-text-tertiary`. Target day selector: bare select → `bg-ds-carbon rounded-xl border-ds-pen-stroke` container with Overline "Add to" label. Add Day button: `btn-ghost` → explicit ds-token button with `min-h-[44px]`. Explore header: `tracking-wider` → `tracking-[0.1em]`. Planning cockpit header: new `destination` + selected day context above SummaryBar. Flight sub-labels: `tracking-[0.08em]` → `tracking-[0.1em]`, added `px-1 pb-1` / `pt-2 pb-1`. Filter-empty copy: "No X match..." → "Nothing matches the current filters — try widening the selection." |
| `frontend/tests/tripbuilder-command-surface.test.mjs` | NEW. 32 static/contract tests: no legacy classes, ds-token coverage, Overline tracking, planning cockpit header, compare bar, Add Day touch target, behavior preservation. |
| `frontend/package.json` | Added `tripbuilder-command-surface.test.mjs` to test script. |

### Test results
- **724 tests, 0 failures** (was 692; +32 new Phase 5 command surface contract tests)
- All pre-existing tests continue to pass

### Design contract alignment

- **CandidatePanel chrome:** Full ds-token card pattern; count badge is a styled pill with accent-subtle bg. No legacy `.card` class.
- **Overline type role:** All section/area labels use exact `text-[10px] font-semibold uppercase tracking-[0.1em]` Overline pattern.
- **Planning cockpit header:** Destination + selected day context above SummaryBar — clear command center orientation.
- **Compare bar:** Elevation-4 shadow, Overline "Compare" label, smaller dots. More editorial, less dashboard.
- **Target day selector:** Contained in `bg-ds-carbon rounded-xl border-ds-pen-stroke` with "Add to" Overline label. Clear context of which day will receive additions.
- **Add Day button:** Explicit ds-token button with `min-h-[44px]` touch target. No legacy `btn-ghost`.
- **Behaviors preserved:** DnD, compare, Google Flights link-out, round-trip one-card rendering, GSAP `candidate-card` class, hotel/attraction/restaurant/flight add-to-itinerary all unchanged.

### Invariant confirmations
- No backend files; no API/search/provider/Tavily/cache changes.
- No Supabase SQL; no new env vars; no new dependencies.
- No new fonts; no route rewrites; no data model changes.
- No new booking behavior; no fake data.

---

## Stage 3.5 Phase 4 — Trip Detail Planning Canvas / Itinerary Day System — SHIPPED (2026-05-16)

**Stage 3.5 · Wife-Wow design system — Trip planning canvas · Day-column hierarchy and empty-state redesign**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/trips/ItineraryDayColumn.tsx` | Full ds-* migration: all `slate-*`/`amber-*`/`sky-*`/`violet-*` classes removed. Day column root → `bg-ds-onyx border-ds-pen-stroke shadow-[var(--ds-elevation-2)]`. Chapter header: zero-padded number marker (`bg-ds-accent` when selected), `Day N` title in `text-ds-text`, date as Overline (`text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-text-tertiary`). Day-part colors: morning=`text-ds-accent`, afternoon=`text-ds-text-secondary`, evening=`text-ds-accent-muted`, unscheduled=`text-ds-text-tertiary`. Expanded body bg → `var(--ds-midnight-ink)` (ink-ladder depth). All action buttons: `min-h-[44px] min-w-[44px]` touch targets + `focus-visible:outline-ds-accent`. Empty-day invitation: editorial "Day N / Drag items here or use + Add" with `border-dashed border-ds-pen-stroke` (normal) and `border-ds-accent/60 + var(--ds-accent-subtle)` bg (drag-over). Travel connectors → `bg-ds-pen-stroke`/`text-ds-text-tertiary`/`text-ds-warning`. SuggestionsReviewPanel → `bg-ds-carbon border-ds-pen-stroke`. DayTravelHintBar → `bg-ds-carbon border-ds-pen-stroke`. Show all/less → `border-ds-pen-stroke bg-ds-carbon text-ds-text-secondary`. |
| `frontend/src/app/trips/[id]/page.tsx` | Trip context header: `bg-brand-600/15 border-brand-500/30 text-brand-300` → `border-ds-pen-stroke text-ds-accent bg-[var(--ds-accent-subtle)]`. `text-cream-300` → `text-ds-text`. Toast: `bg-slate-800 text-white` → `bg-ds-onyx border-ds-pen-stroke text-ds-text shadow-[var(--ds-elevation-2)]`. Back link + loading state → `text-ds-text-tertiary hover:text-ds-text`. Loading card → `border-ds-pen-stroke bg-ds-onyx rounded-lg`. |
| `frontend/src/components/trips/TripBuilder.tsx` | No-days empty state: `.card p-8` → `rounded-lg border border-ds-pen-stroke bg-ds-onyx p-8`. |
| `frontend/tests/trip-canvas-day-system.test.mjs` | 57 new static/contract tests: ds-token coverage, 44px touch targets, focus rings, Overline tracking, empty-state editorial design, selected-day accent, behavior contract preservation, trip detail page legacy removal, TripBuilder no-days state. |
| `frontend/package.json` | Added `trip-canvas-day-system.test.mjs` to test script. |

### Test results
- **692 tests, 0 failures** (was 614; +57 new Phase 4 day-canvas contract tests + carried through from previous phases)
- All pre-existing tests continue to pass

### Design contract alignment

- **Chapter hierarchy:** Day columns have chapter-style headers: zero-padded number marker, "Day N" title, Overline date. Editorial weight, not dashboard chrome.
- **Ink-ladder elevation:** Expanded body uses `var(--ds-midnight-ink)` (darker than `bg-ds-onyx` card shell) — correct depth relationship per Design Bible §8 ink-ladder.
- **Day-part Overline labels:** `text-[10px] font-semibold uppercase tracking-[0.1em]` — matches Overline type role exactly.
- **Empty-day invitation:** No utilitarian "No plans yet." Editorial invitation with actionable "+ Add" inline link. Dashed border with accent on drag-over.
- **Touch targets:** All header action buttons at `min-w-[44px] min-h-[44px]`. Inline empty-state + Add link is a button with focus-visible ring.
- **Selected state:** `border-ds-accent/40 ring-ds-accent/20` on column root. Number marker: `bg-ds-accent text-ds-text-inverse`. Header: `bg-ds-carbon`.
- **Travel connectors:** Subdued — `bg-ds-pen-stroke` divider, `text-ds-text-tertiary` for distance/time, `text-ds-warning/70` for far-apart alert.
- **No legacy classes:** Zero `slate-*`, `amber-*`, `sky-*`, `violet-*` in ItineraryDayColumn. Zero `brand-*`, `cream-*` in trip detail page shell.
- **Behavior preserved:** DnD droppable, SortableContext, isExpanded, PREVIEW_ITEM_LIMIT, handleSuggestTimeline, handleApplyTimeline, onPlanDay, onUpdateTimeline, onMoveItemToIdeas, itemOverrides all unchanged.

### Invariant confirmations
- No backend files, no API/provider/Tavily/cache changes, no Supabase SQL.
- No new dependencies, no new fonts, no route rewrites, no data model changes.
- No new booking behavior, no fake data, no new animation library.
- Pre-existing TypeScript errors in TripBuilder.tsx (missing module types): unchanged, pre-existing.

---

## Stage 3.5 Phase 3 — Trip Planning Card System Breadth — SHIPPED (2026-05-16)

**Stage 3.5 · Wife-Wow design system — Trip planning surfaces · Card variant breadth**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/trips/ItineraryItemCard.tsx` | Full ds-* migration: root bg/border/shadow → `bg-ds-onyx border-ds-pen-stroke shadow-[var(--ds-elevation-1)]`. All typeConfig icons → unified `text-ds-accent` + inline `var(--ds-accent-subtle)`. All text colors → ds-text-*/ds-text-tertiary. Google Flights link → `text-ds-text-secondary hover:text-ds-accent`. Remove button hover → `text-ds-warning`. Hotel area badges → `text-ds-trust-verified`/`text-ds-caution` + inline rgba. Timeline input → `bg-ds-carbon border-ds-pen-stroke`. Focus rings on all interactive elements. |
| `frontend/src/components/trips/TripIdeasPanel.tsx` | Full ds-* migration: IdeaCard border/bg → `border-ds-pen-stroke bg-ds-onyx`. Status options, filter chips, inputs, selects, buttons → ds-* tokens. Panel header/active count/Add to Day button → ds-accent. Show more/less → `border-ds-pen-stroke bg-ds-onyx text-ds-text-secondary`. |
| `frontend/src/components/trips/SearchResultCard.tsx` | Migrated to `Card tone="dark" as="article"`. Uses `Card.Identity` + `Card.Meta` slots. Category icon → unified `text-ds-accent` + inline accent-subtle. Compare/add buttons → ds-* tokens. Area badges → `text-ds-trust-verified`/`text-ds-caution` + inline rgba. Tags → `bg-ds-carbon text-ds-text-tertiary border-ds-pen-stroke`. |
| `frontend/src/components/trips/TripBuilder.tsx` | PREMIUM_CARD_BASE/SECONDARY_CTA/PRIMARY_CTA → ds-* tokens (candidate-card class preserved). AiScoreBadge → ds-trust-verified/ds-caution with inline rgba bg. SortControl/FilterPills active → `bg-ds-accent text-ds-text-inverse`. All card components (FlightCandidateCard, FlightLegRow, RoundTripFlightCard, HotelCandidateCard, AttractionCandidateCard, RestaurantCandidateCard) → ds-* tokens. RecTag/AttractionTag/RestaurantTag → unified `text-ds-accent border-ds-pen-stroke` + inline accent-subtle. Top pick badges (Best Pick/Best Pair/Top Hotel/Top Pick) → `bg-ds-accent text-ds-text-inverse`. Compare bar → `bg-ds-onyx border-ds-pen-stroke`. Toast → ds-* tokens. CandidatePanel section icons → `text-ds-accent`. Explore toggle → `bg-ds-carbon`/`bg-ds-onyx`. SummaryBar → `bg-ds-onyx border-ds-pen-stroke`. |
| `frontend/src/components/explore/FlightExploreFlow.tsx` | FlightCard → `Card tone="dark" as="article"`. All flight card, leg row, empty/error/unavailable states → ds-* tokens. Search form icon residuals → `text-ds-text-tertiary`. |
| `frontend/tests/trip-planning-card-tokens.test.mjs` | 24 new token-coverage tests verifying ds-* adoption and no-legacy-class invariants across all 5 migrated files. |
| `frontend/package.json` | Added `trip-planning-card-tokens.test.mjs` to the test script. |

### Test results
- **614 tests, 0 failures** (was 590; +24 new Phase 3 token coverage tests)
- All pre-existing tests continue to pass

### Design contract alignment

- **Dark tone cards:** All trip-planning card surfaces use `tone="dark"` or equivalent `bg-ds-onyx border-ds-pen-stroke` treatment.
- **Token alignment:** No raw hex, no legacy `cream-*`/`brand-*`/`dark-*`/`sky-*`/`violet-*`/`emerald-*`/`rose-*`/`amber-*`/`slate-*`/`white/` classes in any migrated card or helper function.
- **Unified accent:** All tag badges, icons, and active states use `text-ds-accent` (sandstone gold).
- **Semantic status:** Trust indicators (`text-ds-trust-verified`), caution (`text-ds-caution`), warning (`text-ds-warning`) — no raw color for semantic signals.
- **Inline accent-subtle:** `var(--ds-accent-subtle)` used as inline style for bg since not in `@theme`.
- **Focus rings:** `focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2` on all interactive elements.
- **44px touch targets:** Preserved on all buttons/links/drag handles.
- **candidate-card class:** Preserved in PREMIUM_CARD_BASE for GSAP querySelector targeting.
- **All existing actions preserved exactly:** DnD drag/drop, add-to-itinerary, compare, Google Flights link-out, round-trip add, hotel/attraction/restaurant add, remove, save/unsave, sort, filter.

### Invariant confirmations

- No backend files, no API/provider/Tavily/cache changes, no Supabase SQL.
- No new dependencies, no new fonts, no route rewrites, no data model changes.
- No new booking behavior, no fake data.
- Pre-existing 3 FlightCard test failures: unchanged (outside this scope).

---

## Stage 3.5 Phase 2A — AI Concierge Flagship Visual Breakthrough — SHIPPED (2026-05-15)

**Stage 3.5 · Wife-Wow design system — AI Concierge `/concierge` surface · Card-first flagship canvas**
**Behavior change:** Converts `/concierge` from a placeholder page to a live standalone AI Concierge route using the existing `/ai/concierge/search` backend contract (`callConciergeSearch(null, query)`). No backend/API/provider contract changes. Frontend route behavior changes from placeholder → live search.

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/app/concierge/page.tsx` | Route replaced: was a placeholder ("AI Concierge coming soon"), now imports and renders `ConciergePage`. Server component with Metadata. |
| `frontend/src/components/concierge/ConciergePage.tsx` | NEW. Full-page client component: editorial header (Overline "Private Travel Concierge" + Display S headline), card-first result canvas, sticky composer at bottom. Uses `Card tone="dark"` primitive for result cards. `TrustStrip confidence={...}` (actual backend `googleVerification.confidence`) where `canShowGoogleVerifiedBadge` passes — no fabricated `sourceCount`. Cards render `pickCardCategory`, `pickCardReason`, `sanitizeWhyPick`, `pickCardMeta`, map/source links from canonical `googleVerification.googleMapsUri`. All business logic reuses `cardPresentation.js` and `refinementInterpreter.js` unchanged. Refinement chips (Show only casual, Compare top 2, Find cheaper nearby / Find more like these) from existing interpreter. Empty state: 4 editorial prompt chips. Loading: "Searching · Verifying · Composing" typeset breadcrumb + spinner. Error: named constraint + "Try again" link. No add-to-day / save-to-ideas (no trip context on standalone page). `callConciergeSearch(null, query, requestId)` — tripId=null per existing API contract. |
| `frontend/src/components/layout/Sidebar.tsx` | Added `{ label: "Concierge", href: "/concierge", icon: Sparkles }` to `primaryLinks` (after Explore). Desktop sidebar navigation now exposes the Concierge surface. |
| `frontend/src/components/layout/MobileNav.tsx` | Added `{ label: "Concierge", href: "/concierge", icon: Sparkles }` to `links` (slide-out drawer). Mobile navigation drawer now exposes the Concierge surface. |

### Design contract alignment

- **Dark mode surface:** `bg-ds-midnight` body (via AppShell), `Card tone="dark"` for result cards (`bg-ds-onyx border-ds-pen-stroke text-ds-text`).
- **Tonal hierarchy (§9):** Midnight Ink body → Onyx Velvet cards and composer → Carbon Mist button backgrounds.
- **Card-first hierarchy (§25):** No chat bubbles. User queries are silent state only. Result cards are the visual hero.
- **Editorial composition:** Overline + Display S header. Cards use Body L name, Overline category, Body S meta. Concierge note uses Body S with Accent Subtle left-border.
- **Sticky composer:** `position: sticky; bottom: 0` within the main scroll context. Textarea with resize-on-content. 44×44px minimum send button with accent gold background.
- **Loading state (§11):** "Searching · Verifying · Composing" typeset breadcrumb — honest static treatment (no fake stage progression since pipeline timing not exposed to frontend).
- **Empty state (§11):** Editorial invitation with 4 themed prompt chips. Not "Ask me anything."
- **Error state (§11):** Named constraint message (`text-ds-warning`) + "Try again" retry action.
- **Trust strip (§23):** `TrustStrip confidence={...}` only when `canShowGoogleVerifiedBadge` passes (OPERATIONAL + high/medium confidence + providerPlaceId). `confidence` value is read directly from `googleVerification.confidence` on the backend payload — never hardcoded. `sourceCount` never fabricated. `verified` prop never set (OPERATIONAL status is not the same as the "Verified by Google" explicit confirmation contract).
- **Token alignment:** No raw hex. No legacy `emerald-*`, `amber-*`, `cream-*`, `slate-*`, `white/` classes. All surfaces use `ds-*` Tailwind utilities or `var(--ds-*)` inline styles.
- **Spacing:** All padding/margin/gap via `var(--ds-space-*)` CSS variables.
- **Typography:** All font-size/line-height via `var(--ds-type-*-size)` / `var(--ds-type-*-leading)` CSS variables.
- **Accessibility:** All interactive elements have `focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2`. `aria-label` on map/source links. `role="status"` on loading state. `role="alert"` on error state. `aria-live="polite"` on result canvas.
- **Mobile:** Composer `position: sticky; bottom: 0` — always visible on scroll. Textarea auto-resizes. Touch target ≥44px on all interactive elements.
- **Motion:** `card-lift` for card hover (120ms/200ms via existing motion tokens). `transition-colors duration-[120ms]` on buttons. `animate-spin` on Loader2 icons. No transforms >400ms. No typewriter, no glow, no parallax.
- **Reduced-motion:** Global `@media (prefers-reduced-motion: reduce)` rule governs all transitions (Phase 0).

### Invariant confirmations

- No provider, search, API, Tavily, backend, or SQL files changed.
- No new dependencies added.
- No route rewrites — `/concierge` route preserved.
- `AIConciergePanel.tsx` unchanged — trip-panel add/save behavior fully preserved.
- `lib/concierge/cardPresentation.js`, `refinementInterpreter.js`, `types.ts`, `priceFormatter.js` unchanged.
- `lib/api.ts` unchanged — `callConciergeSearch(null, ...)` pre-existing API contract.
- All card action handlers, addability gate, verification gate, map/source link derivation preserved from existing library functions.
- No add-to-day / save-to-ideas on standalone page — these require a `tripId` and belong to the trip-panel flow. Discovery surface only.

### Visual tradeoffs for later phases

- Standalone page has no add-to-trip/save-to-ideas (requires trip context). To add a found place to a trip, user navigates to My Trips and uses the AI Concierge panel there.
- Conversation history: standalone page maintains session state in component state only (no persistence). Persistent history requires a tripId. This is the correct scope boundary.
- No left conversation rail (Design Bible §25): standalone page uses a simpler header-only layout. The rail is scoped to the trip-panel variant and can be added in a future Phase 2B when trip context is present.
- Area comparison table from AIConciergePanel not ported — this is a trip-specific feature and complex to slot correctly without a trip context.
- Orchestration helpers (`hasClosedSignal`, `canShowGoogleVerifiedBadge`, `pickCardMeta`) are re-implemented in `ConciergePage.tsx` with identical logic because `AIConciergePanel.tsx` does not export them. Phase 2B should consolidate shared concierge presentation helpers into a shared module.

---

## Stage 3.5 Phase 1C — Saved Ideas Paper/Scrapbook Adoption — SHIPPED (2026-05-15)

**Stage 3.5 · Wife-Wow design system — Saved Ideas `/saved` surface · Paper/scrapbook warm-paper tone**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/app/globals.css` | Added `.card-paper` CSS modifier class: `box-shadow: none` for base; `card-lift` hover on paper = `translateY(-2px)` + no shadow + `border-color: var(--ds-linen)` (luminance-only lift, §8 contract). |
| `frontend/src/components/ui/Card.tsx` | Paper TONE_CLASSES adds `card-paper` to suppress dark shadow on paper cards. Added `"data-testid"?: string` to `CardProps` for test-compatible usage. |
| `frontend/src/components/saved/SavedShell.tsx` | `SavedItemCard` adopts `Card tone="paper" as="article" className="card-lift p-4"` with `Card.Identity` slot for icon + content row. Vertical icon: `bg-ds-accent-subtle` (inline style) + `text-ds-accent`. Title: `text-ds-text-inverse`. Secondary text: `text-ds-slate`. Rating star: `text-ds-accent fill-current`. Tags: `border-ds-hairline text-ds-slate`. Action buttons: `bg-ds-bone hover:bg-ds-linen` / `hover:bg-ds-hairline`. Error: `text-ds-warning`. Success: `text-ds-trust` icon + `text-ds-text-inverse`. Section header icon: `text-ds-accent-muted`. Section label: `text-ds-text-inverse`. SavedShell container: `bg-ds-linen rounded-2xl` (linen album on midnight ink body). Empty/loading/error states updated to paper-mode colors. All action handlers, grouping, ordering, payloads, and behavior unchanged. |

### Design contract alignment

- **Paper tone adopted:** `SavedShell` container = `bg-ds-linen` (aged-paper album). `SavedItemCard` = `Card tone="paper"` (warm paper, §9 — Saved Ideas paper mode).
- **Tonal hierarchy (§9):** Midnight Ink body → Linen album container → Warm Paper cards. Surface mode changes at route level.
- **Card.Identity slot:** Icon + content flex row. Vertical icon bg = `var(--ds-accent-subtle)`. Icon color = `text-ds-accent`. All text in ink-paper tones.
- **Paper elevation (§8):** `.card-paper` suppresses dark box-shadow. Hover = luminance-only (border to linen, 2px lift, no shadow). No drop-shadows on paper surface.
- **Token alignment:** No raw hex in changed files. No legacy `cream-*`, `brand-*`, `amber-*`, `rose-*`, `white/` classes in saved cards. All colors via `ds-*` Tailwind utilities or `var(--ds-*)` inline style.
- **Accessibility:** All interactive elements retain `focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2`. Icon containers `aria-hidden="true"`. Semantic `as="article"` on card root.
- **Motion:** `card-lift` class used; `.card-paper.card-lift` override governs paper hover (120ms/200ms via existing motion tokens). No new animations.
- **Reduced-motion:** Global `@media (prefers-reduced-motion: reduce)` rule still governs (shipped Phase 0).

### Invariant confirmations

- No provider, search, API, Tavily, flight, hotel, or backend files changed.
- No Supabase SQL required.
- No new dependencies added.
- No route, auth/session, or data contract changes.
- All action handlers (deleteSavedItem, addSavedItemToTrip, createTrip, router.push, onRemove, onCreateTrip) preserved exactly.
- All payloads, verticals, grouping, ordering, and filter behavior unchanged.
- Add-to-trip, create-trip, delete/remove, filter, open/maps-link, and navigation unchanged.

### Limitation note

`--ds-accent-subtle` (rgba alpha) is defined in `:root` but not wired into `@theme`. Icon background in `SavedItemCard` uses `style={{ backgroundColor: "var(--ds-accent-subtle)" }}` directly. Empty-state icon uses `bg-ds-bone` (paper surface step) as a simpler paper-appropriate alternative within test char-window constraints. Both are acceptable paper-mode treatments.

---

## Stage 3.5 Phase 1B — Explore Result-Card Adoption — SHIPPED (2026-05-15)

**Stage 3.5 · Wife-Wow design system — Explore result cards · Restaurants, Hotels, Attractions**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/explore/RestaurantExploreFlow.tsx` | `RestaurantCard` adopts `Card` primitive (dark tone, article element, card-lift). Icon → `ds-accent-subtle` bg + `ds-accent` text. Title → `text-ds-text`. Category/address → `text-ds-text-tertiary`. Google Maps link → `bg-ds-carbon` / hover `bg-ds-pen-stroke`. Rating star → `text-ds-accent fill-current`. Review count → `text-ds-text-tertiary`. Tags → `border-ds-pen-stroke text-ds-text-tertiary`. TrustStrip rendered when Google Place source (`providerPlaceId`/`placeId`). Skeleton → Card primitive + `bg-ds-pen-stroke` bars. Empty/idle text → `text-ds-text-tertiary`. Error → `text-ds-warning`. |
| `frontend/src/components/explore/HotelExploreFlow.tsx` | `HotelCard` adopts `Card` primitive (dark tone). Same icon/text token treatment. TrustStrip rendered when `googlePlaceId` present. Compare prices link → `text-ds-accent` + `ds-accent-subtle` bg (inline style). All legacy `violet-*` / `amber-*` / `cream-*` replaced. |
| `frontend/src/components/explore/AttractionExploreFlow.tsx` | `AttractionCard` adopts `Card` primitive (dark tone). Same icon/text treatment. TrustStrip on `googlePlaceId`. Legacy `blue-*` / `amber-*` / `cream-*` replaced. |
| `frontend/src/components/explore/ResultActionSheet.tsx` | Save button idle: `bg-ds-carbon text-ds-text-tertiary`. Save button saved: `ds-accent-subtle` bg (inline) + `text-ds-accent`. More button: `bg-ds-carbon text-ds-text-tertiary`. Expanded links: `bg-ds-carbon text-ds-text-secondary`. Error: `text-ds-warning`. Outer `mt-2` removed (spacing now from `Card.Actions className="mt-3"`). All save/unsave/expand handlers preserved exactly. |

### Design contract alignment

- **Card primitive adopted:** All 3 Explore result card types wrap with `<Card tone="dark" as="article" className="card-lift">`. Card.Identity, Card.Trust, Card.Meta, Card.Actions slots used.
- **TrustStrip adopted:** Rendered with `sourceCount={1}` where Google Place ID confirms Google Places provenance. `verified` prop intentionally omitted — OPERATIONAL status not explicitly confirmed in frontend payload (contract §23 compliance).
- **Token alignment:** All card surfaces reference `--ds-*` tokens. No raw hex in card renderers. Icon bg uses `style={{ backgroundColor: "var(--ds-accent-subtle)" }}` (CSS var direct, not Tailwind wiring since `--color-ds-accent-subtle` not yet in `@theme`). Rating accent unified to `text-ds-accent` (sandstone gold) across all card types.
- **Forbidden patterns removed:** Legacy `amber-*`, `violet-*`, `blue-*`, `cream-*`, `rose-*`, `white/[.0X]` color utilities removed from result cards.
- **Accessibility:** All interactive elements (Maps link, Compare prices, Save, More) have `focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2`. Semantic `as="article"` on card root. Icon containers marked `aria-hidden="true"`.
- **Motion:** `card-lift` hover class preserved (translateY -2px, within motion contract). `transition-colors` used on interactive elements (120ms via global css). No new animation added.
- **Reduced-motion:** Global `@media (prefers-reduced-motion: reduce)` rule in `@layer base` governs all transitions (shipped Phase 0).

### Invariant confirmations

- No provider, search, API, Tavily, flight, hotel, or backend files changed.
- No Supabase SQL required.
- No new dependencies added.
- No route, auth/session, or data contract changes.
- Search form fields (MapPin, Calendar, Tag icons) retain legacy `text-cream-500` — search forms are explicitly out of scope.
- All action handlers (save, unsave, expand, Manage in Saved link) preserved exactly.
- Add-to-trip, save, maps, compare-prices payloads and routes unchanged.

### Limitation note

`--ds-accent-subtle` (rgba alpha) is defined in `:root` but not wired into `@theme`. Icon backgrounds and compare-prices/save-saved button backgrounds use `style={{ backgroundColor: "var(--ds-accent-subtle)" }}` directly. Adding `--color-ds-accent-subtle` to `@theme` is a logical Phase 1B+ follow-up if Tailwind utility is needed broadly.

---

## Stage 3.5 Phase 1A — App Shell & Navigation Frame — SHIPPED (2026-05-15)

**Stage 3.5 · Wife-Wow design system — first visible surface adoption · Shared shell/navigation only**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/app/globals.css` | Body bg → `var(--ds-midnight-ink)` (solid, replaces purple gradient). Body/heading color → `var(--ds-text-primary)`. `.nav-item` → ds-text-tertiary color + ds-accent-subtle active state + ds-accent active color + color-mix hover bg + focus-visible sandstone ring. `.nav-section-label` → Overline token (10px, 600, 0.1em, uppercase). |
| `frontend/src/components/layout/AppShell.tsx` | Removed 3 forbidden glow blobs (radial-gradient ambient blobs). Removed GSAP card entrance animation (420ms exceeded 400ms hard limit). Loading state → `bg-ds-midnight text-ds-text-tertiary`. Removed `text-cream-100` from main content wrapper. |
| `frontend/src/components/layout/Sidebar.tsx` | Replaced `.glass` with `bg-ds-onyx` (ink-ladder elevation). `border-white/[.07]` → `border-ds-pen-stroke`. Brand mark → `bg-ds-carbon text-ds-accent`. Section labels → `.nav-section-label`. User avatar → `bg-ds-carbon text-ds-accent`. All text → ds-text tokens. Sign-out hover → `text-ds-warning`. |
| `frontend/src/components/layout/MobileNav.tsx` | Same glass→onyx treatment for top bar, drawer, bottom tab bar. Brand marks → ds tokens. Tab active state → `text-ds-accent`. "New Trip" FAB → `bg-ds-accent text-ds-text-inverse`. Drawer slide → 200ms (ds-duration-standard). Menu toggle focus ring. |
| `frontend/src/components/layout/PageHeader.tsx` | `text-cream-100` → `text-ds-text`. `text-cream-500` → `text-ds-text-tertiary`. |

### Design contract alignment

- **Forbidden patterns removed:** Glow blobs (§31 "No glow pulses"), GSAP animation >400ms (§7 hard limit), glass on navigation (§8 "No glass on … navigation").
- **Ink-ladder elevation applied:** Body = midnight ink, nav/sidebar = onyx velvet, brand marks = carbon mist (two steps up).
- **Token alignment:** All nav colors reference `--ds-*` tokens. No raw hex in changed files. No legacy `brand-*`, `cream-*`, `dark-*` classes in shell.
- **Accessibility:** Focus ring added to all nav items (2px sandstone-gold, 2px offset). Touch targets preserved. Reduced-motion global rule still governs.
- **Motion:** Nav transitions use `--ds-duration-standard` (200ms) and `--ds-duration-fast` (120ms) via token vars.

### Invariant confirmations

- No provider, search, API, Tavily, flight, hotel, saved-trip, or backend files changed.
- No Supabase SQL required.
- No new dependencies added (GSAP still in package.json for TripBuilder; no new packages).
- No route, auth/session, or card action behavior changes.
- No new design tokens (`.nav-section-label` uses existing `--ds-type-overline-*` tokens).

### Limitation note

Glass class (`.glass`) is retained in `globals.css` because `TripBuilder.tsx` still references it. Its removal from shell components is the scope-correct change for this phase. TripBuilder glass removal is deferred to the TripBuilder/Itinerary surface adoption phase.

---

## Design Foundation Phase 0 — SHIPPED (2026-05-14)

**Stage 3.5 · Wife-Wow design system foundation · Design Bible v1.0 Phase 0**

### What shipped

| File | Description |
|---|---|
| `frontend/src/app/globals.css` | Design token `:root` block (`--ds-*`) + semantic `@theme` wiring (`--color-ds-*: var(--ds-*)`) + global reduced-motion safety rule |
| `frontend/tailwind.config.ts` | Minimal Tailwind v4 config; theme tokens live in CSS, not JS |
| `frontend/src/components/ui/Card.tsx` | Composable Card primitive shell (root + 7 named slots: Identity, Trust, Media, Why, Meta, Actions, Caveat) |
| `frontend/src/components/ui/TrustStrip.tsx` | TrustStrip primitive (verified, sourceCount, confidence, caveat) |

### Token categories added

All values are Design Bible v1.0 §4 exact. Named palette tokens are defined first; semantic aliases reference them.

**Dark surface tokens**

| Token | Name | Hex |
|---|---|---|
| `--ds-midnight-ink` | Midnight Ink | `#0B1320` |
| `--ds-onyx-velvet` | Onyx Velvet | `#0F1A2C` |
| `--ds-carbon-mist` | Carbon Mist | `#1A2538` |
| `--ds-pen-stroke` | Pen Stroke | `#22324A` |

**Warm paper surface tokens**

| Token | Name | Hex |
|---|---|---|
| `--ds-warm-paper` | Warm Paper | `#FAF7F0` |
| `--ds-bone` | Bone | `#F1ECE0` |
| `--ds-linen` | Linen | `#E6DECB` |
| `--ds-hairline` | Hairline | `#D9D2C2` |

**Named palette tokens**

| Token | Name | Hex |
|---|---|---|
| `--ds-sandstone-gold` | Sandstone Gold | `#E0B888` |
| `--ds-ember-brass` | Ember Brass / Brass | `#C5944D` |
| `--ds-pearl-cream` | Pearl Cream | `#F2EBDD` |
| `--ds-cream` | Cream | `#E8E2D4` |
| `--ds-mist` | Mist | `#9AA4B2` |
| `--ds-verified-sage` | Verified Sage | `#88A899` |
| `--ds-caution-amber` | Caution Amber | `#E8B26B` |
| `--ds-whisper-coral` | Whisper Coral | `#D88478` |
| `--ds-slate` | Slate | `#4A5568` |
| `--ds-ink-paper` | Ink Paper | `#1F2530` |

**Semantic role aliases** (reference named tokens):
- Text: `--ds-text-primary` → Pearl Cream, `--ds-text-secondary` → Cream, `--ds-text-tertiary` → Mist, `--ds-text-inverse` → Ink Paper
- Accent: `--ds-accent` → Sandstone Gold, `--ds-accent-muted` → Ember Brass
- Trust: `--ds-trust-verified` → Verified Sage, `--ds-trust-partial` → Caution Amber
- Caution / warning: `--ds-caution` → Caution Amber, `--ds-warning` → Whisper Coral

**Elevation tokens** — four shadow stack levels (`--ds-elevation-1` through `--ds-elevation-4`)

**Motion tokens** — fast/standard/slow durations + standard/decelerate/accelerate easings (`--ds-duration-*`, `--ds-easing-*`)

**Spacing scale tokens — Design Bible v1.0 §4 complete**

| Token | px |
|---|---|
| `--ds-space-1` | 4px |
| `--ds-space-2` | 8px |
| `--ds-space-3` | 12px |
| `--ds-space-4` | 16px |
| `--ds-space-5` | 20px |
| `--ds-space-6` | 24px |
| `--ds-space-8` | 32px |
| `--ds-space-10` | 40px |
| `--ds-space-12` | 48px |
| `--ds-space-16` | 64px |

**Typography role tokens — Design Bible v1.0 §4.4 complete**

| Token prefix | Size / Line-height | Weight | Notes |
|---|---|---|---|
| `--ds-type-display-xl-*` | 64px / 68px | 700 | tracking −0.03em |
| `--ds-type-display-l-*` | 44px / 50px | 700 | tracking −0.025em |
| `--ds-type-display-m-*` | 32px / 38px | 700 | tracking −0.02em |
| `--ds-type-display-s-*` | 24px / 30px | 600 | tracking −0.015em |
| `--ds-type-body-l-*` | 18px / 28px | 400 | |
| `--ds-type-body-*` | 15px / 24px | 400 | |
| `--ds-type-body-s-*` | 13px / 20px | 400 | |
| `--ds-type-caption-*` | 12px / 16px | 400 | |
| `--ds-type-overline-*` | 10px / 14px | 600 | `text-transform: uppercase`, tracking 0.1em |
| `--ds-type-mono-*` | 12px / 16px | 400 | monospace role |
| `--ds-type-quote-*` | 18px / 28px | 400 | `font-style: italic` |

Backward-compatible aliases preserved: `--ds-type-display-*`, `--ds-type-heading-*`, `--ds-type-subheading-*`, `--ds-type-label-*` (reference the new named tokens above).

### Tailwind wiring

All `--color-ds-*` entries in `@theme` read from `var(--ds-*)`. No raw hex in `@theme` for design-token entries. Generates Tailwind utilities including: `bg-ds-midnight`, `bg-ds-onyx`, `bg-ds-paper`, `text-ds-text`, `text-ds-trust`, `text-ds-caution`, `border-ds-pen-stroke`, `border-ds-hairline`, `text-ds-accent`, `text-ds-accent-deep`, etc. Existing `--color-*` palette entries and all existing utility classes are unchanged.

### Primitive token usage

- `Card.tsx` dark tone uses: `bg-ds-onyx border-ds-pen-stroke text-ds-text`
- `Card.tsx` paper tone uses: `bg-ds-paper border-ds-hairline text-ds-text-inverse`
- `TrustStrip.tsx` verified uses: `text-ds-trust` (Verified Sage)
- `TrustStrip.tsx` high confidence uses: `text-ds-trust`
- `TrustStrip.tsx` medium confidence uses: `text-ds-caution` (Caution Amber)
- `TrustStrip.tsx` low confidence / caveat uses: `text-ds-text-tertiary` (Mist)
- No legacy `emerald-*`, `amber-*`, `cream-*`, `dark-*`, or raw `white/` classes in new primitives.

### Surface adoption

**None.** No existing surface (Explore, TripBuilder, Saved, AI Concierge, nav, login) has adopted the Card primitive or new design tokens. The primitives are available for future Phase 1+ slices. Existing screens are visually unchanged.

### Reduced-motion

Global `@media (prefers-reduced-motion: reduce)` rule in `@layer base` suppresses all animation/transition durations. This satisfies Design Bible v1.0 §4.13.

---

## References

- **Design Implementation Contract v1:** `docs/product/DESIGN_IMPLEMENTATION_CONTRACT.md` (exact implementation reference for all design PRs — token values, primitive contracts, visual rules, forbidden patterns, self-audit checks, map styling/interaction, state patterns, accessibility/responsive rules, microinteractions, detail panel/sheet/drawer rules, premium form controls, source/date discipline, future-only ideas guardrails)
- Design Bible v1.0: `artifacts/Travel_Concierge_Design_Bible.pdf` (§04 Visual System, §08 Card Design System, §11 Phase 0, §12 Guardrails, §13 First recommended implementation slice)
- Design Bible Addendum v1.1: `docs/product/DESIGN_BIBLE_ADDENDUM_V1_1.md` (§1 private atelier, §5 constraint-first feasibility UX, §6 Phase 0 scope confirmation)
- Roadmap: Stage 3.5 — Wife-Wow design system foundation (`docs/product/ROADMAP.md`)

---

## Pre-Phase 0 baseline (reference only)

Before Phase 0, the UI layer consisted of:
- Tailwind v4 with `@theme` color palette (`--color-sky-*`, `--color-slate-*`, `--color-cream-*`, `--color-dark-*`, `--color-brand-*`, etc.)
- Shared CSS component classes in `globals.css` (`.card`, `.btn-primary`, `.btn-gold`, `.btn-ghost`, `.btn-emerald`, `.input`, `.select`, `.badge-*`, `.skeleton`, `.nav-item`, etc.)
- Four `/ui` components: `CityAutocomplete`, `EmptyState`, `Skeleton`, `StatCard`, `TrustStatusBadge`
- No design token semantic layer
- No composable Card primitive
- No TrustStrip primitive
- No reduced-motion global rule
