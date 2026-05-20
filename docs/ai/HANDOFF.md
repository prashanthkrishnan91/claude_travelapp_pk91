# HANDOFF — Current Repo State

Last updated: 2026-05-20 (Atelier Room System v1 patch-2 — PR #451 open, branch claude/review-travel-app-docs-afJmb)

## Purpose

This file is **current operational state**, not a historical log. It must stay compact — loaded each session. Do not append PR-by-PR history. Replace or summarize when something changes.

## Current product stage

**Stage 3 exit complete. Active: Stage 3.5 — Atelier Room System v1 + Private Salon (PR #451, open)**

### Home baseline (merged)
- **PR #448** — Atelier Atrium: edge-to-edge cinematic home, world DNA system, AppShell route-aware wrapper, DashboardClient full atrium composition, WorldScenery/Mist/Atmosphere/Glass primitives, silent navigation (AtelierNavArtifact), contained scenery, physical archive shelf.
- **PR #449** — Bottom dead-space fix (Level 1): `overflow: clip` on `.atelier-atrium-content`, `min-height: 0` on `.home-edge-bleed`, `flex: none` on `.atelier-atrium-neutral`. Home is clean and non-scrollable past content.

### PR #451 open (this branch)
**Atelier Room System v1 — AI Concierge Private Salon**

Changes on branch:
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

**Test count:** 2991 total, 0 failures.  
**No backend / SQL / provider / env / Supabase / API / route / data-contract changes.**

### Next step after PR #451 merges
Apply Atelier Room System to Explore (Observatory room) or Saved (Gallery room) — next visible adoption slice using the same room shell primitives.

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

- 2026-05-20 — **PR #451 OPEN** — Atelier Room System v1 + Private Salon (Concierge). See above.
- 2026-05-20 — **PR #449 MERGED** — Home dead-space fix (overflow: clip + min-height: 0 + flex: none).
- 2026-05-20 — **PR #448 MERGED** — Atelier Atrium full cinematic home (world DNA, AppShell escape hatch, silent nav, contained scenery, physical archive).
- 2026-05-18 — **PR #441 MERGED** — Unified Folio/Cinema UI Architecture. `Folio.tsx` canonical primitives (FolioPage/Panel/Card/SectionHeader/Input/Chip/Button + Cinema variants). Real adoption in DashboardClient, TripIdeasPanel, ItineraryDayColumn, TripBuilder, trips/page.tsx, SearchResultCard. 2692 tests, 0 failures.
- 2026-05-18 — **PR #440 MERGED** — Visual Rescue (screenshot-led CSS value corrections). `folio-concierge-chip` added. 30 tests.
