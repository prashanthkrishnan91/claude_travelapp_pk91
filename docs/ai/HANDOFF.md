# HANDOFF — Current Repo State

Last updated: 2026-05-20 (Atelier Room System v1 patch-1 — PR #451 open, branch claude/review-travel-app-docs-afJmb; PR body updated: visible adoption scope confirmed)

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
- **`globals.css` — ATELIER ROOM SYSTEM section** (7 new CSS primitives):
  - `.atelier-salon-room` — `isolation: isolate` (stacking context for WorldAtmosphere z-index:-1)
  - `.atelier-salon-room-header` + `::before` — brass entry separator
  - `.atelier-salon-starter-chip` — brass-inflected prompt chip treatment with reduced-motion guard
  - `.atelier-salon-invitation` + `::before` — empty-state threshold with wider brass separator
  - `.atelier-salon-composer-surface` + `::before` — desk boundary brass hairline with reduced-motion guard
  - `.atelier-salon-user-turn` — brass-tinted left-border for transcript query annotations

- **`ConciergePage.tsx`** — salon room adoption:
  - Imports: `WorldAtmosphere`, `applyRoom`, `pickWorldFromDestination`, `worldStyleVars`
  - `salonWorld = applyRoom(pickWorldFromDestination(destination), "salon")` via useMemo
  - Outer div: `atelier-salon-room` class + `worldStyleVars(salonWorld)` style + `data-world-location` attribute
  - `<WorldAtmosphere />` as first child (destination-aware ambient blob coloring)
  - Header: `atelier-salon-room-header` class + brass separator
  - Empty state: `atelier-salon-invitation` class + overline typography on chip label
  - Result canvas: `px-4 sm:px-6` mobile breathing room
  - Prompt chips: `atelier-salon-starter-chip` added alongside `folio-concierge-chip`
  - User turn markers: `atelier-salon-user-turn` (brass left border)
  - Composer: `atelier-salon-composer-surface` (brass desk threshold line)

- **`tests/atelier-salon-room-v1.test.mjs`** — 42 contract tests (32 original + 10 Section D patch-1)
- **`frontend/package.json`** — test wired into npm test

All existing testids, folio-cinema-desk, folio-cinema-composer, folio-concierge-chip, Starting points copy, callConciergeSearch, all behavior (search, save, maps, refinement, transcript) preserved. Home not regressed.

**Test count:** 2977 total, 0 failures.  
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
