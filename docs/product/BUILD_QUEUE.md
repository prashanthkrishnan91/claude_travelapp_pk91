# Build Queue

The active product queue. Every meaningful implementation PR should map to one item here.

Update via `.claude/skills/build-queue-update/SKILL.md` after meaningful roadmap decisions or merged PRs. Keep updates concise.

## Now

- **Stage 3.5 Slice 4 — Paper World Remaining Surfaces.** Convert `TripBuilder` CollapsiblePanel from dark boutique to paper world. Explore + Saved remain dark cinematic (cinema punctuation rule). Optionally: Concierge trip-context panel result cards. Hard stops: no PR #431 logic paths, no provider/API/SQL/behavior changes. Run `feature-contract` + `golden-scenarios` before coding (Level 2 requirement).

## Next

- Stage 4 — AI destination intelligence entry contract (after Wife-Wow design foundation is merged).
- Stage 2B or later: Real hotel offer rates (requires provider-backed Hotel Offer contract + explicit Provider Registry re-approval).
- Optional: Trip-workspace Explore parity (reuse Explore's canonical Flights search and hotel discovery inside `TripBuilder`) — accepted open gap, schedule separately if needed.

## Completed

- **Stage 3.5 Slice 3 — Paper Planning Objects (2026-05-18, merged PR #436).** `ItineraryItemCard`, `TripBuilderForm`, `OptimizeTripModal`, `DayPlanModal` converted from dark boutique to paper world (`folio-paper-panel/item/header`, `bg-ds-bone/linen`, `border-ds-hairline`, `text-ds-folio-ink*`, `btn-marine`, `btn-folio-ghost`). New `.folio-paper-item`, `.btn-folio-ghost`, `--ds-paper-elevation-1/2` in `globals.css`. 46 new contract tests. **2510 total tests, 0 failures.** No backend/SQL/provider/env/behavior changes.

- **Stage 3.5 Phase 2B — Concierge shared helpers + trip-context polish (2026-05-16, merged PR #399).** `cardHelpers.ts` created (shared `hasClosedSignal`/`canShowGoogleVerifiedBadge`/`pickCardMeta`, 12-field scan including `card.raw`). `AIConciergePanel` uses `Card.Identity`/`Card.Trust`/`Card.Why` named slots, 44px touch targets, full ds-token palette. 953 tests, 950 pass.

- **Stage 3 exit — functionally complete (2026-05-14).** Stage 3 v1/v2/v3 shipped. Stage 3 is accepted as functionally unblocked for current private-use scope. Saved-list board reorganization/edit is an accepted open gap (not required before design foundation). Trip-workspace search parity with Explore is an accepted open gap (schedule separately). Canonical provider routing contract locked (see below). Next: Wife-Wow design system foundation.

  **Canonical Explore provider routing contract (durable — do not regress):**
  - Hotels → `POST /search/hotels` → `SearchService.search_hotels` → Google Places `HotelProvider`
  - Attractions → `POST /search/attractions` → `SearchService.search_attraction_results` → Google Places Text Search
  - Restaurants → `POST /search/restaurants` → Google Places
  - Flights → `canonical_flight_search` helper → Duffel → Google Flights `SEARCH_REDIRECT` link-out
  - AI Concierge (`/ai/concierge/search`) is **not** the backend for default Explore. It is the explicit Tavily/live-research path only, gated by `ALLOW_LIVE_RESEARCH_CALLS`.
  - Hotel "Compare prices" CTA → deterministic `google.com/travel/hotels` URL (`buildHotelCompareUrl`). Stays Google Hotels — not Booking.com. Guest count defaults to Google's behavior for now.

- **Stage 3 pre-design utility — hotel compare link-out v1 + Create Trip from Saved autocomplete parity**: `HotelExploreFlow` hotel cards gain a deterministic "Compare prices" CTA linking to `google.com/travel/hotels` search (no rates, no OTA, no booking). `compareLink` stored in saved-item payload metadata (future-friendly, no price fields). `CreateTripFromSavedModal` replaces plain Origin/Destination text inputs with `CityAutocomplete` matching `TripBuilderForm` UX; resolved city/country/IATA chips; manual IATA fallback preserved; airport arrays forwarded to `createTripWithSearch`. No backend/SQL/env changes. 42 + 45 + 20 + 123 tests pass. (2026-05-14)

- **Stage 3 exit blocker — Unified trip-creation flight seeding with canonical Explore Flights**: New `app/services/canonical_flight_search.py` wraps `get_flight_provider()` and returns canonical `FlightItineraryOffer` rows. Both `/explore/flights` and `/trips/create-with-search` call this single helper, so trip creation no longer shows 0 flights while Explore Flights returns offers. Legacy `SearchService.search_flights` / `search_round_trip_flights` calls removed from create-with-search; round-trip is encoded via `return_date` on one canonical request. Flight offers persist as unscheduled Trip Ideas (`day_id: null`, `item_type=flight`) with Google Flights `SEARCH_REDIRECT` link-out details and no booking/order/payment fields. Primary-airport latency cap preserved. Ignav remains disabled, no Duffel orders. Test updates in `test_create_with_search_seeding_contract.py` + `test_create_with_search_fail_closed.py` + `test_create_with_search_timing_logs.py`. No SQL, no provider/env changes. Stage 3 exit still pending live validation. (2026-05-13)
- **Stage 3 exit blocker — Create Trip from Saved uses full create-with-search seeding**: `CreateTripFromSavedModal` renders Origin field for all four verticals and requires it for submit. `createTripFromSavedItem` (api.ts) now calls `createTripWithSearch` so the new trip receives full flight/hotel/attraction/restaurant candidates; the selected saved item is then seeded as an unscheduled Trip Ideas item (`day_id: null`) with `source: "saved_item"` provenance. Helper throws when origin/destination/dates are missing — no silent fallback to a destination-only shell. Navigates to `/trips/{id}`. 28 tests pass in `create-trip-from-saved.test.mjs`; 141 across related saved-flow bundles. No new backend route, no SQL, no provider/env changes, no TripBuilder/ResultActionSheet refactor. Stage 3 exit still pending live validation. (2026-05-13)
- **Stage 3 exit cleanup — honest Explore/Saved UI + docs**: `ExploreShell` no longer renders stale "Coming soon" badges for Flights/Hotels/Attractions; descriptions corrected (Flights = search-only with Google Flights link-out, no booking; Hotels = discovery-only verified hotels, no rates/availability). `ResultActionSheet` removed disabled "Coming soon" Add/Create actions; expanded section now shows "Save first to add or create a trip from Saved." before save and a `Manage in Saved` link to `/saved` after save. Save/Unsave unchanged. No direct Explore → Add/Create trip wiring. No `TripBuilder` refactor. New `stage3-exit-cleanup.test.mjs` structural tests; `saved-items-action-wiring.test.mjs` updated accordingly. No backend / SQL / provider / env changes. (2026-05-13)
- **Stage 3 v3 — Create Trip from Saved Item**: SavedShell adds "Create Trip" per card (all four verticals); `CreateTripFromSavedModal` always shown with prefill per contract; flight one-way defaults `endDate` to `departureDate`; hotel hides both dates if either missing; restaurant/attraction dates user-entered; missing destination requires user input. `createTripFromSavedItem` composes `POST /trips` + `POST /itinerary/items` (`day_id: null`). Flights seeded via dedicated safe-details path — no booking/rate/price fields. Navigates to `/trips/{id}` on success. 25 new structural tests. 491 frontend tests pass. No backend. No SQL. No TripBuilder/tripCandidates/ResultActionSheet changes. (2026-05-13)
- **Stage 3 v1 — Saved Lists Foundation**: `/saved` route + `SavedShell`; items fetched via `listSavedItems()`, grouped by vertical (Restaurants / Attractions / Hotels / Flights), compact cards from `displaySnapshot`/`searchContext`, remove via `deleteSavedItem()`, empty/loading/error states, Explore link in empty state. "Saved" in Sidebar + MobileNav (drawer + tab bar). 46 new structural tests. No SQL. No provider change. (2026-05-12)
- **Stage 2A Slice 5C — Hotels Discovery Live**: `HotelExploreFlow` rewritten from deferred state to live; calls `callConciergeSearch(null, query, undefined, destination)` (tripless Concierge); renders `UnifiedHotelResult` discovery cards (stars, rating, area, maps link, why note, `ResultActionSheet`); normalized `originalPayload` for saved-item display snapshots (address, googleMapsUri, search context; no price/rate/booking fields); no rates/prices/availability. 26 new hotel structural tests + 5 updated global Explore tests. No SQL. No backend change. (2026-05-12)
- **Flights v1 — Ignav Live Cash Search + Link-Out**: Ignav promoted to `LINK_OUT`/`production_allowed=True`. `IgnavFlightProvider.search_flights()` live (httpx, one-way + round-trip, parallel booking links). `POST /explore/flights` route. `FlightExploreFlow` live (FlightCard, ResultActionSheet save, unavailable/error states). 57 backend + 20 frontend new tests. No SQL. No points. (2026-05-12)
- **Flights Provider Contract + Skyscanner/Ignav Scaffold**: Normalized `FlightItineraryOffer` contract, Skyscanner (PENDING) + Ignav (EVALUATION) registry entries, adapter shells (fail-closed), TS types, 68 backend + 23 frontend tests. No SQL. No UI change. (2026-05-12)
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
