# Build Queue

The active product queue. Every meaningful implementation PR should map to one item here.

Update via `.claude/skills/build-queue-update/SKILL.md` after meaningful roadmap decisions or merged PRs. Keep updates concise.

## Now

- **Flights v1 — Cash Live/Link-Out**: Implement flight search (origin, destination, dates, passengers, cabin, one-way/round-trip) backed by a live cash provider (Skyscanner Live Prices preferred, requires confirmed API key). Cards with AI scoring, cash price from provider, deep-link to book, provenance fields, `ResultActionSheet` save, and `POST /itinerary/items` add-to-trip. Fail-closed polished unavailable state when no key present. Provider Registry entry + gated adapter required first. Contract locked in DECISION_LOG 2026-05-12. Points/award track separately gated.

## Next

- Stage 3 v3 candidate: Create Trip from Saved Item (needs its own contract PR — deferred until Flights v1 ships and flight cards are saveable/addable).
- Stage 2B or later: Real hotel offer rates (requires provider-backed Hotel Offer contract + explicit Provider Registry re-approval).

## Completed

- **Stage 3 v1 — Saved Lists Foundation**: `/saved` route + `SavedShell`; items fetched via `listSavedItems()`, grouped by vertical (Restaurants / Attractions / Hotels / Flights), compact cards from `displaySnapshot`/`searchContext`, remove via `deleteSavedItem()`, empty/loading/error states, Explore link in empty state. "Saved" in Sidebar + MobileNav (drawer + tab bar). 46 new structural tests. No SQL. No provider change. (2026-05-12)
- **Stage 2A Slice 5C — Hotels Discovery Live**: `HotelExploreFlow` rewritten from deferred state to live; calls `callConciergeSearch(null, query, undefined, destination)` (tripless Concierge); renders `UnifiedHotelResult` discovery cards (stars, rating, area, maps link, why note, `ResultActionSheet`); normalized `originalPayload` for saved-item display snapshots (address, googleMapsUri, search context; no price/rate/booking fields); no rates/prices/availability. 26 new hotel structural tests + 5 updated global Explore tests. No SQL. No backend change. (2026-05-12)
- **Provider Registry v1 + Explore Provider Scope Reset**: `provider_registry.py` as central provider policy; Brave/Serper/Duffel/Amadeus/Foursquare disabled; `live_research` + `flights_provider` + `hotels_provider` + `duffel_stays` gated through registry; 58 tests. No SQL. No UI change. (2026-05-12)
- Stage 2A Slice 5B — Hotel Offer contract + Duffel Stays scaffold: `HotelOffer` dataclass, `DuffelStaysProvider` (disabled by default, no live calls), `HotelDiscoveryCard`/`HotelOffer` TS types, 38 new tests. No SQL. No UI rates. (2026-05-12)
- Stage 2A Slice 5A — Hotels Discovery (scope-locked): decision-only PR locking Hotels as discovery-only in Stage 2A. (2026-05-11)
- Stage 2A Slice 4 — Attractions Vertical Live: `AttractionExploreFlow` rewritten from deferred state to live; calls `callConciergeSearch(null, query, undefined, destination)` (tripless Concierge); renders `UnifiedAttractionResult` cards with `ResultActionSheet`. (2026-05-11)
- Stage 2A Slice 3 — Trip-Optional AI Concierge: `trip_id` optional in `ConciergeRequest`/`ConciergeSearchRequest`; service/route guard `_fetch_trip`+`_save_message`; frontend `callConcierge`/`callConciergeSearch` accept `tripId: string | null` + `destination`. No SQL migration. (2026-05-11)
- Stage 2A Slice 2 — Unified Result Actions v1 + saved_items foundation: `saved_items` migration (005), `SavedItemsService`, `/saved-items` route (POST/GET/DELETE), `ResultActionSheet` (Save live; Add to Trip / Create Trip deferred), wired into `RestaurantExploreFlow`. (2026-05-11)
- Stage 2A Slice 1 — Global Explore Shell v1: `/explore` route, 4-vertical entry grid, Restaurants live (Google Places), Attractions/Hotels/Flights deferred with polished states, `ExploreResultContext` action-ready type, nav links in Sidebar + MobileNav. (2026-05-11)
- Stage 1 → Stage 2 transition: discovery-first architecture audit + Stage 2A contract. See `docs/product/STAGE_2A_CONTRACT.md`. (2026-05-11)

## Later

- AI destination intelligence.
- Road-trip mode.
- Deal intelligence.
- Points intelligence.
- Travel Watchtower.

## Blocked

- _none recorded_

## Validation Needed

- _none recorded_

## Design Pause Candidates

- Wife Wow Design Sprint after Discover + Saved + core trip flows are stable.

## Do Not Build Yet

See `docs/product/DO_NOT_BUILD_YET.md`. Highlights:

- auto-booking
- noisy alerts
- scraping-heavy deal infrastructure
- public social/community features
- full design sprint before Wife Wow Readiness Gate
