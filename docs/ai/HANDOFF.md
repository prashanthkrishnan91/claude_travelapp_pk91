# HANDOFF — Current Repo State

Last updated: 2026-05-21 (Explore regression fixes: hotel compare-link dates + flight per-offer prices; Observatory v1 PR #460 merged)

## Purpose

This file is **current operational state**, not a historical log. It must stay compact — loaded each session. Do not append PR-by-PR history. Replace or summarize when something changes.

## Current product stage

**Stage 3.5 — design adoption across cinema-world rooms.** Stage 3 exit completed earlier (2026-05-14). The outside-trip Concierge (`/concierge`) is the Private Travel Salon (portal + fused desk + dossier + reveal). The outside-trip Explore (`/explore`) is now the **Observatory** (current branch). Next visible-adoption candidate: Saved (Gallery room).

### Explore Observatory v1 — /explore premium reskin (current branch)

Reskins the existing **vertical-first** Explore into the Atelier "Observatory" — same materials as the Salon (velvet canvas, brass hairlines, Fraunces italic, layered depth, "kept in your folio" save) but a distinct **wide meridian** silhouette. **No** universal cross-vertical search controller, **no** app-shell/nav change, **no** backend/API/provider/type/SQL change. Approved sources: `docs/ai/concepts/explore-observatory-concept-v1.1.html` + `docs/ai/design/EXPLORE_OBSERVATORY_PRODUCTION_BLUEPRINT.md`.
- **Immersive shell + Concierge-family composition (patch-1/2):** `/explore` shares the Concierge Salon's outside-trip framing — `AppShell` sets `data-atelier-shell="explore"` (CSS-suppresses the SaaS sidebar, mirroring salon), renders the floating `AtelierNavArtifact`, and uses the edge-to-edge `home-edge-bleed` wrapper. Composition matches the salon: a **light atelier outer field** (`.obs-field`, warm-paper canvas) with a **floating dark Observatory room** (`.obs-room.folio-cinema-lounge` — brass-edged rounded box + shadow) within it, clear field↔room separation. The `explore-home`/`explore-vertical-flow` testids + `folio-cinema-lounge` sit on the room div (8F window contracts). Landing hero is `.obs-meridian--hero`; hero copy is plain "Browse flights, hotels, restaurants, and attractions." (no internal trip-state language). The `isHomePage ? null : <Sidebar />` ternary + `max-w-7xl` branch untouched (8J/atrium contracts).
- **`ExploreShell.tsx`:** landing renders the `ObsMeridian` band (depth layers: scene/bloom/grain/horizon/vignette) as hero, then the four verticals as `.obs-vert-card` entry cards — **2×2 mobile / 4-up desktop**, clearly named, unclipped, ≥44px. Selecting one still drives local `setActive(vertical)` (no lifted destination state). Active view keeps the breadcrumb + `explore-instrument-header`, adds a compact `.obs-meridian--banner` showing **vertical identity/mood only** (never the typed destination). All testids preserved (`explore-home`, `explore-lounge-header`, `explore-vertical-grid`, `vertical-card-{id}`, `explore-vertical-flow`, `explore-lounge-breadcrumb`, `explore-instrument-header`).
- **Per-vertical flows:** Restaurants/Attractions/Hotels result cards wear the shared `.obs-card` frame + full-bleed `ObservatoryPlate` (token-built **typeset** editorial header — production result types carry **no photo field**, so no images; honest fallback only) + `.obs-card-body`; results header restyled to `.obs-index-head`. Save/Map/Source preserved exactly (`ResultActionSheet`, `googleMapsUri`, `TrustStrip`). **Hotels stay discovery-only — no prices/rates/availability; `hotel-compare-cta` preserved.** Flights keep the bespoke card (legs, `formatTime` no-UTC, live `offer.price`, `liveCachedStatus`, `CityAutocomplete`, booking-link logic, and all empty/unavailable/error states) and only gain the `.obs-card-frame` border.
- **`globals.css`:** new **EXPLORE OBSERVATORY** section (tokens/`color-mix` only, no raw hex); all new motion reduced-motion-guarded (merged into the final reduced-motion block).
- **Tests:** new `tests/explore-observatory.test.mjs` (42 assertions: CSS primitives, vertical-first shell, no-prototype-strings, hotels-no-price, flights-preserved). Historical Explore assertions that legitimately moved (`folio-cinema-tile`→`obs-vert-card`, grid, result-header styling) updated in place. **3065 tests, 0 failures; tsc/lint/next build clean.** Interactive browser preview not run (no headless browser in this environment) — validated via tests + production build + static review.

### Concierge Salon v2 — mobile-first discovery loop (current branch)

Evolves the merged PR #458 static salon into a discovery loop **without changing its silhouette** (integrated dark canvas · cinematic portal · attached dossier · fused desk · editorial invitations · floating nav). All changes in `ConciergePage.tsx` + `globals.css`; no backend/API/provider/SQL/AppShell.
- **Destination-aware portal:** new `.atelier-salon-portal-photo` layer paints the typed destination's **real** world-DNA mood image (`visualLayer.imageUrl` from `pickWorldFromDestination` — Unsplash for curated worlds, inline SVG scene for city/coast/mountain/desert, `none` → dusk-floor fallback for the Atelier house world) via `--world-portal-image`. `data-portal-destination` house/tuned hook; reduced-motion guarded. No fake destination facts.
- **Curated reveal:** each result section gets `.atelier-salon-reveal-head` (Fraunces italic **real**-count line "N places in {destination}" + small-caps note) and a `salonResultReveal` entrance (reduced-motion guarded).
- **Editorial cards:** `ConciergeResultCard` gains a decorative `.atelier-salon-card-plate` (3 gradient variants) + serial overline ("No. 01"). **Not a place photo** — the result types carry no image field anywhere; the plate is an honest editorial slip (matches the prototype's `.ed-plate`), making cards photo-forward/scannable on mobile without fabricating imagery.
- **Save-to-folio moment:** a `.atelier-salon-folio-toast` ("Slipped into your folio") fires on save success (`folioToast` state + auto-dismiss timer w/ unmount cleanup), behavior-safe atop the existing `saveItem` flow.
- **Mobile:** plate/reveal/toast tuned for phone (full-width centered toast, shorter plate). Tests: Section J (8 new). **3023 tests, 0 failures; tsc/lint/next build clean.** All testids + behavior preserved.
- **patch-1 (preview polish):** textarea shows a scrollbar only past the 120px cap (clean default single-line); scoped slim brass scrollbar on `.atelier-salon-panel-body` (no global restyle); mobile (`≤620px`) pre-search prompts become a horizontal swipe tray (`.atelier-salon-chip-grid` flex + scroll-snap, hidden scrollbar) instead of a tall vertical pile.
- **patch-2 (mobile one-screen fit):** phone (`≤620px`) pre-search state now fits the viewport without scroll — open-mode portal floor cut to `clamp(148px,21vh,196px)`, plus trimmed workbench margin/stage padding/hero copy spacing/desk→carousel gap. Desktop (`≥900px`) and the after-search tuned state are untouched; carousel + all six prompts preserved.

### Concierge Salon cinematic scene (PR #458, merged)

**`ConciergePage.tsx` + `globals.css` — the /concierge scene is a direct production port of the approved concept** (`docs/ai/concepts/concierge-salon-concept-v1.html`, blueprint `docs/ai/design/CONCIERGE_SALON_PRODUCTION_BLUEPRINT.md`):
- `.atelier-salon-workbench` is the **integrated salon canvas** — one dark, rounded, brass-edged object (`var(--ds-cinema-deep)` + lamp warmth) holding a desktop two-column grid: the dark stage (left, `.atelier-salon-main-panel`/`.atelier-salon-stage-panel`, transparent) and the paper dossier (`.atelier-salon-briefing-rail`) **attached on the right via `border-left`, no gap**. Desktop height is bounded to `calc(100svh - space-8)` with `overflow:hidden` so only the reveal canvas scrolls. Mobile collapses to the stage alone (dossier hidden).
- `.atelier-salon-portal` is the emotional centerpiece — layered `scene → tint → haze → bloom → grain → vignette` spans. The scene is the salon's signature **dusk composition** (violet/rose upper · warm peach-gold bloom band · deep navy/ink lower, in `rgb()` not hex), and a faint `.atelier-salon-portal-tint` layer paints `var(--world-scenery)` (overridden per typed destination via `pickWorldFromDestination`) so the window **tunes toward the place** through the real world-DNA pipeline — no hardcoded mood logic, no fake destinations.
- Dossier is an editorial "Briefing" object (serif italic title, roman-numeral items, tactile bottom badges) on bone paper, attached to the canvas via `border-left`. Invitations are two-line cards (italic Fraunces lead + small-caps intent hint via `PROMPT_HINTS`, click still only populates the query input).
- Scene hierarchy matches the concept via flex `order`: **portal (order 0) → fused desk (`.atelier-salon-desk`, order 2, directly under the portal) → reveal canvas (`.atelier-salon-panel-body`, order 3)**. The header lives inside `.atelier-salon-portal-copy`; invitations live in the reveal canvas beneath the desk. All stage copy uses light cinema tokens (`--ds-pearl-cream`/`--ds-cream`) over a guaranteed dark scrim, so it can never go dark-on-dark regardless of the tuned scene.
- `data-salon-mode` ("open" pre-search → portal grows, reveal canvas collapsed and non-scrolling; "tuned" post-search → portal collapses to a banner, reveal canvas becomes the only scroller). The composer is the fused desk (no longer a sticky-bottom app form); it stays put on desktop because it sits outside the internal scroller, and flows under the portal on mobile.
- Transcript/loading/header text flipped from dark `--world-ink` to light cinema tokens (the readability fix the prior attempts missed). Dossier rail given a tactile `--ds-bone` surface.
- Mobile: portal-first, compact, thumb-reachable desk; portal/banner heights clamped for short phones. All portal motion (drift, bloom, open↔tuned transition) is `prefers-reduced-motion` guarded.
- Tests: `tests/atelier-salon-room-v1.test.mjs` Section I (10 new) covers portal structure, world-DNA scene source, depth layers, open/tuned mode rules, in-scene header/invitations, light-on-dark copy, reduced-motion, and a no-fake-prototype-data guard. **3013 tests, 0 failures; `tsc --noEmit` clean; `next lint` clean.**
- **No backend / API / provider / SQL / auth / trip-data / AppShell changes.** All concierge behavior (search, refinement, transcript persistence, destination field, invitation-click populates input only, verified cards, save, off-trip add message, maps/source links, follow-up/refinement chips) and every existing testid/class preserved.

### Prior: Atelier Room System v1 (PR #451 merged)

### Home baseline (merged)
- **PR #448** — Atelier Atrium: edge-to-edge cinematic home, world DNA system, AppShell route-aware wrapper, DashboardClient full atrium composition, WorldScenery/Mist/Atmosphere/Glass primitives, silent navigation (AtelierNavArtifact), contained scenery, physical archive shelf.
- **PR #449** — Bottom dead-space fix (Level 1): `overflow: clip` on `.atelier-atrium-content`, `min-height: 0` on `.home-edge-bleed`, `flex: none` on `.atelier-atrium-neutral`. Home is clean and non-scrollable past content.

### PR #451 merged
**Atelier Room System v1 — AI Concierge Private Salon**

Changes on branch:
- **`globals.css` — patch-5 two-column workbench**:
  - `.atelier-salon-workbench` updated: `max-width: 72rem`, `flex-col` mobile / CSS grid `1fr 17rem` desktop ≥900px with `align-items: start`
  - `.atelier-salon-main-panel` — flex column, `overflow: hidden`, `border-radius: 16px`, brass border, soft shadow; `height: calc(100svh - var(--ds-space-10))` on desktop so results scroll inside panel
  - `.atelier-salon-panel-header` — `flex-shrink: 0` so header doesn't compress in flex panel
  - `.atelier-salon-panel-body` — `flex: 1; overflow-y: auto; min-height: 0; padding: var(--ds-space-4) var(--ds-space-5)` — the only scrollable region in desktop concierge
  - `.atelier-salon-briefing-rail` — hidden on mobile; sticky `top: ds-space-5` sidebar on desktop; brass border, `flex flex-col gap-4`
  - `.atelier-salon-briefing-header` / `.atelier-salon-briefing-item` / `.atelier-salon-briefing-footer` — briefing rail anatomy primitives

- **`ConciergePage.tsx` — patch-5 layout restructure**:
  - Workbench wrapper: `atelier-salon-workbench mx-auto` (CSS owns grid/flex, Tailwind owns centering)
  - All panel content wrapped in `atelier-salon-main-panel` div (header + mapline + main + composer)
  - Header: adds `atelier-salon-panel-header` class (keeps `atelier-salon-header-landing` for test E6)
  - `<main>` class: `atelier-salon-panel-body` — internal scroll on desktop panel
  - Composer: keeps `sticky z-10 concierge-sticky-bottom folio-cinema-composer atelier-salon-composer-surface` (preserves 8M tests); removes `marginTop: var(--ds-space-8)` (flex handles spacing)
  - Static `<aside className="atelier-salon-briefing-rail">` added with 6 capability items + 3 footer badges (no fake data, no fake counts)

- **`tests/atelier-salon-room-v1.test.mjs`** — 8 new Section H tests (68 total): main-panel defined + overflow:hidden, panel-body flex:1+overflow-y:auto, briefing-rail defined, ConciergePage uses all three

- **Test count:** 3003 total, 0 failures.  
- **No backend / SQL / provider / env / Supabase / API / route / data-contract changes.**

- **`AppShell.tsx`** *(patch-3)* — Concierge added to immersive shell:
  - `isSalonRoute = pathname === "/concierge"` — new route check
  - `data-atelier-shell="salon"` on `atelier-atmosphere-root` — CSS sidebar suppression hook
  - Second `{isSalonRoute && <AtelierNavArtifact />}` — floating nav for salon route
  - `home-edge-bleed` wrapper extended to `isHomePage || isSalonRoute` — edge-to-edge for both
  - F1/F2 test regex patterns (`isHomePage ? null : <Sidebar`, `isHomePage && <AtelierNavArtifact`) preserved unchanged

- **`globals.css` — ATELIER ROOM SYSTEM section** (15 CSS primitives total):
  - `.atelier-salon-room` — `isolation: isolate`
  - `.atelier-salon-room-header` + `::before` — brass entry separator
  - `.atelier-salon-starter-chip` + hover + reduced-motion — brass prompt chip treatment
  - `.atelier-salon-invitation` + `::before` — empty-state invitation threshold
  - `.atelier-salon-composer-surface` + `::before` + reduced-motion — brass desk hairline
  - `.atelier-salon-user-turn` — brass-tinted transcript annotation
  - `.atelier-salon-room.folio-cinema-desk` — strips card chrome for room-not-box reading
  - `.atelier-salon-header-landing` — cinematic top padding
  - `.atelier-salon-chip-grid` — 2-column desktop chip grid
  - `.atelier-salon-chip-grid .atelier-salon-starter-chip` — full-width grid cell chips
  - `.atelier-atmosphere-root[data-atelier-shell="salon"] .folio-sidebar { display:none !important }` *(patch-3)* — hides SaaS sidebar; `!important` beats `lg:flex` from @layer utilities
  - `.atelier-salon-page { background: var(--world-surface, --ds-warm-paper); min-height:100svh }` *(patch-3)* — light paper room shell; `--world-surface` is always a warm linen tone from worldData
  - `.folio-cinema-composer.folio-cinema-desk { padding:0 }` *(patch-3)* — prevents padding conflict when co-classed on sticky composer

- **`ConciergePage.tsx`** *(patch-3 architecture correction)*:
  - Outer div: `folio-cinema-desk` removed → `atelier-salon-page` added (light paper room, not dark box)
  - `data-scenery-tone` preserved; `worldStyleVars(salonWorld)` injects `--world-ink`, `--world-ink-mist`, `--world-surface`
  - Sticky composer: `folio-cinema-desk` added alongside `folio-cinema-composer` (dark instrument floats on light room; test B2 preserved)
  - Header h1 + subtitles: `text-ds-text*` classes removed; `color: var(--world-ink)` / `color: var(--world-ink-mist)` inline styles — dark ink readable on light paper
  - User turn: inline `borderColor` removed (let `atelier-salon-user-turn` brass handle it); text uses `var(--world-ink-mist)`
  - Loading state spans: world-ink / world-ink-mist inline styles
  - Result cards (`ConciergeResultCard` with `Card tone="dark"`) keep their own dark surface — `text-ds-text*` tokens inside cards remain correct

- **`tests/atelier-salon-room-v1.test.mjs`** — 56 contract tests (48 prior + 8 new Section F for patch-3 shell integration)
- **`frontend/package.json`** — test wired into npm test

All existing testids, folio-cinema-desk, folio-cinema-composer, folio-concierge-chip, Starting points copy, callConciergeSearch, all behavior (search, save, maps, refinement, transcript) preserved. Home not regressed.

**Test count (earlier patches):** 2991 total, 0 failures.  
**No backend / SQL / provider / env / Supabase / API / route / data-contract changes (any patch).**

### Explore regression fixes (current branch — post-Observatory)

Two Level 2 user-visible regressions fixed after PR #460 merged:

1. **Hotel compare-link dates:** `buildHotelCompareUrl` already appended `&checkin=`/`&checkout=` correctly; `buildContext` already used `lastForm?.checkIn` for the compare URL (not the fallback dates used for the API call). 4 new regression tests added to `hotel-explore-live.test.mjs` — now 31/31; wired into `npm test`.

2. **Flight per-offer prices:** Duffel adapter already maps each offer's `total_amount` independently. The `_search_booking_link` is shared (same Google Flights query URL) but prices are per-offer. Fixed two pre-existing source-code test failures in `flights-ignav-live.test.mjs`:  
   - Test 10: changed dynamic `data-testid` expression to always use `"flight-book-link"` (with `data-link-type` for redirect distinction).  
   - Test 15: changed comment wording that accidentally matched `points.*price` regex.  
   6 new regression tests added — now 32/32; wired into `npm test`.  
   Backend: 2 new tests in `test_duffel_flights_v1.py` proving distinct per-offer prices and that uncertified provider returns UNAVAILABLE.

**3134 frontend tests, 0 failures.** No backend suite run (no pytest in this environment).

### Next step
Regression fixes are the current branch. After PR merges, next visible-adoption slice: apply Room System treatment to Saved (Gallery room) using shared cinema-world primitives.

## Current architecture / runtime state

- OS v4 is the canonical operating system. No v4.2 or v5 labels.
- **Provider Registry v1** (`backend/app/services/provider_registry.py`) — single policy source for provider activation and addable-card authority. Duffel Flights: `LINK_OUT` + `production_allowed=True` (search-only, no booking). Ignav: DISABLED. Skyscanner: PENDING.
- Google Places is canonical for addable cards (only `can_create_addable_cards=True`). Yelp / Foursquare / editorial: enrichment only.
- Brave, Serper, Ignav, Duffel (stays), Amadeus, Foursquare: disabled/quarantined. Re-approval in registry required.
- AI Concierge card field contract: `display.displayWhy`, `supportingDetails.whyPick`, top-level `whyPick`.
- **Vertical-search (durable):** Explore Hotels → `searchHotelsExplore` → `POST /search/hotels` (Google Places). Explore Attractions → `searchAttractionsExplore` → `POST /search/attractions`. `/trips/create-with-search` shares same `SearchService`. AI Concierge (`/ai/concierge/search`) is NOT the backend for default Explore.
- **Create Trip from Saved:** requires resolved origin + destination airports. Plain saved strings are not resolved chips.
- **Round-trip flight add:** persists two standalone one-way items. `addRoundTripLegToDay` splits the offer; `normalizeIsoDate` resolves departure days.
- Latency Budget Pack governs total request-path latency.
- Runtime workflow guardrails: advisory `.claude/hooks/ai_os_advisory.py`. No blocking hooks.

## Recent meaningful PRs

- 2026-05-21 — **PR open (current branch)** — Explore regression fixes: hotel compare dates + flights per-offer prices. 2 backend tests, 10 frontend tests added, 2 pre-existing test failures fixed. 3134 tests, 0 failures.
- 2026-05-21 — **PR #460 MERGED** — Explore Observatory v1 (/explore premium reskin). 3065 tests, 0 failures.
- 2026-05-21 — **PR #451 MERGED** — Atelier Room System v1 + Private Salon (Concierge). Two-column desktop workbench (main panel + briefing rail), contained panel scroll, patch-5 CSS grid. 3003 tests, 0 failures.
- 2026-05-20 — **PR #449 MERGED** — Home dead-space fix (overflow: clip + min-height: 0 + flex: none).
- 2026-05-20 — **PR #448 MERGED** — Atelier Atrium full cinematic home (world DNA, AppShell escape hatch, silent nav, contained scenery, physical archive).
- 2026-05-18 — **PR #441 MERGED** — Unified Folio/Cinema UI Architecture. `Folio.tsx` canonical primitives (FolioPage/Panel/Card/SectionHeader/Input/Chip/Button + Cinema variants). Real adoption in DashboardClient, TripIdeasPanel, ItineraryDayColumn, TripBuilder, trips/page.tsx, SearchResultCard. 2692 tests, 0 failures.
- 2026-05-18 — **PR #440 MERGED** — Visual Rescue (screenshot-led CSS value corrections). `folio-concierge-chip` added. 30 tests.
