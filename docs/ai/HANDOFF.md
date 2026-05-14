# HANDOFF — Current Repo State

Last updated: 2026-05-14

## Purpose

This file is **current operational state**, not a historical log. It is meant to be loaded into context every session, so it must stay compact. Do not append PR-by-PR history. When something changes, replace or summarize the affected section instead of adding new entries.

## Current product stage

- Roadmap stage: **Stage 3 — FUNCTIONALLY EXITED (2026-05-14).** Stage 3 v1/v2/v3 shipped. Accepted as functionally complete for private-use scope. Board reorganization/edit and trip-workspace search parity are accepted open gaps (schedule separately). **Active next: Wife-Wow design system foundation (Stage 3.5).**
- Flights v1 — Duffel search-only LIVE: `DUFFEL_FLIGHTS_ENABLED=1`, `DUFFEL_SCHEDULE_TRUST_CERTIFIED=1`, `DUFFEL_DEBUG=false`, `DUFFEL_BOOKING_ENABLED=0`. Each flight card shows "Search on Google Flights" (SEARCH_REDIRECT link-out, not booking). Duffel never creates orders. Ignav DISABLED.
- Active build queue item: **Wife-Wow design system foundation.** Design tokens / visual primitives, app shell / premium surface language, shared buttons/cards/forms/actions, vertical result-card visual foundation. Hard stops: no provider/search/API/Tavily changes, no flight/hotel/saved-trip behavior changes.
- Current north-star reminder: Discover → Search → Save → Plan → Optimize → Watch. The app must be useful before a trip exists. Wife-wow goal applies. See `docs/product/NORTH_STAR.md`.

## Current architecture / runtime state

- OS v4 is the canonical operating system. No v4.2 or v5 labels.
- **Provider Registry v1** (`backend/app/services/provider_registry.py`) is the single policy source of truth for provider activation, addable-card authority, and disabled/quarantined status. Duffel Flights is now `LINK_OUT` + `production_allowed=True` (Flights v1 active, search-only). Ignav is DISABLED (schedule trust not certified — production smoke test showed externally incorrect schedule times). Skyscanner remains PENDING (access rejected). Future provider additions must register policy + adapter + tests. See `docs/product/DECISION_LOG.md` 2026-05-12.
- Google Places is canonical for addable cards (the only `can_create_addable_cards=True` entry). Yelp / Foursquare / editorial are enrichment / evidence only and cannot mint addable cards. Foursquare is disabled; enrichment is covered by Yelp.
- Brave, Serper, Ignav (flights), Duffel (stays), Amadeus, and Foursquare are disabled/quarantined in the registry. They cannot activate in production even if API keys are present in env. Re-approval in the registry is required to re-enable any of them.
- Duffel Flights is now the active provider; Duffel Stays and Amadeus remain disabled. Ignav may be re-evaluated only after a separate manual schedule-trust certification pass.
- AI Concierge card field contract is the source of truth (`display.displayWhy`, `supportingDetails.whyPick`, top-level `whyPick`).
- **Vertical-search architecture (durable):** Explore and trip creation share canonical Google-Places-backed vertical search services. Explore Hotels → `searchHotelsExplore` → `POST /search/hotels` (`SearchService.search_hotels` → `HotelProvider` Google Places seam). Explore Attractions → `searchAttractionsExplore` → `POST /search/attractions` (`SearchService.search_attraction_results` → `search_attractions` Google Places Text Search). `/trips/create-with-search` seeds hotels/attractions via the same `SearchService` methods/mapping. `/search/restaurants` Google Places path unchanged; flights use the canonical `canonical_flight_search` helper. **The AI Concierge (`/ai/concierge/search`) is NOT the backend for default Explore** — default Explore Hotels/Attractions never call it. Tavily / live research is reserved for the explicit AI Concierge / concierge-note / deep-research path only, further gated by `ALLOW_LIVE_RESEARCH_CALLS`. The PR #368 `allow_live_research` / `allowLiveResearch` flag was a patch around wrong routing and has been fully removed (request model, routes, service, frontend signature).
- **Create Trip from Saved (durable):** create-with-search requires **resolved** origin AND destination airports. A plain saved destination string (e.g. "boise") is never a resolved chip — it stays visible/editable but submit is blocked until the user resolves it via `CityAutocomplete` or a valid IATA code.
- **Round-trip flight add (durable):** adding a canonical round-trip offer persists **one** scheduled flight item carrying full canonical details (legs, prices, Google Flights URL, provider provenance); `ItineraryItemCard` renders both legs in one card. No bare `(Outbound)`/`(Return)` placeholder rows.
- Latency Budget Pack governs total request-path latency, not just local provider timeouts.
- For long architecture references, read `artifacts/travel_concierge_product_north_star_v3.md`, `artifacts/travel_concierge_v4_travel_os_addendum.md`, `artifacts/ai_concierge_semantic_place_intelligence.md`, and `artifacts/ai_concierge_semantic_place_intelligence_v2_amendment.md` rather than copying them here.
- Runtime workflow guardrails: advisory `.claude/hooks/ai_os_advisory.py` reminds about contract / claim-safety / latency / SQL / env paths. No blocking hooks.

## Recent meaningful PRs

Keep this section small. Only entries that affect future work; replace older lines as they age out.

- 2026-05-14 — **Design Bible Addendum v1.1 (this PR).** New `docs/product/DESIGN_BIBLE_ADDENDUM_V1_1.md` — concise Stage 3.5 sharpening of Design Bible v1.0 (private atelier principle, Concierge search-bar grammar, trip-as-story model, future experience-lane IA, constraint-first feasibility UX). Adds emotional-architecture/UX-grammar guidance only; does not rewrite the Bible, does not expand Phase 0 scope, preserves all Stage 3 exit routing/provider guardrails. Docs only — no code, SQL, provider, or env changes.

- 2026-05-14 — **Stage 3 exit / status contract.** Stage 3 declared functionally exited. Canonical provider/search routing locked in `BUILD_QUEUE.md`. Wife-Wow design foundation added as next queue item in `BUILD_QUEUE.md` and `ROADMAP.md` (Stage 3.5). `HANDOFF.md` compacted and updated. No code, SQL, provider, or env changes.

- 2026-05-14 — **PR #370 — Google Hotels compare URL: timezone-safe date formatting + improved date context.** `buildHotelCompareUrl` now formats check-in/check-out dates in local time (not UTC), passes them to the Google Hotels URL. No behavior changes beyond date accuracy.

- 2026-05-14 — **PR #369 — Vertical-search architecture stabilization.** Explore Hotels/Attractions use canonical Google-Places-backed vertical search, not AI Concierge. Removed `allow_live_research` from `ConciergeSearchRequest` and all callers. New `POST /search/attractions` route + `SearchService.search_attraction_results`. `HotelExploreFlow` + `AttractionExploreFlow` rewritten to call `/search/hotels` and `/search/attractions`; no `callConciergeSearch`, no Tavily from default Explore. AI Concierge retains Tavily/live research when explicitly invoked (`ALLOW_LIVE_RESEARCH_CALLS`). No SQL, no env, no new providers.

- 2026-05-14 — **PR #368 — Round-trip add + saved-city resolution stabilization.** (A) "Add Round Trip" now adds one canonical scheduled flight item (`addRoundTripFlightToDay`). `ItineraryItemCard` renders both legs + Google Flights CTA in one card. (B) `CreateTripFromSavedModal` `initFromPrefill` no longer treats plain city text as a resolved chip; submit is blocked until user resolves via `CityAutocomplete`. Note: `allow_live_research` flag from this PR was superseded by PR #369 and fully removed.

- 2026-05-14 — **PR #367 — Hotel compare link-out + Create Trip from Saved autocomplete parity.** `HotelExploreFlow` gains "Compare prices" CTA → deterministic `google.com/travel/hotels` URL (Google Hotels, not Booking.com). `CreateTripFromSavedModal` uses `CityAutocomplete` for origin/destination (matching `TripBuilderForm`). No backend/SQL/env/provider changes.

- 2026-05-14 — **PR #366 — Flight-offer fingerprint dedupe.** Canonical Duffel offers now dedupe by `details.offer_fingerprint` (sha256 over stable fields), not title. 10 distinct round-trip offers → 10 API-visible rows. Backend only. No SQL, no env, no frontend changes.

- Earlier Stage 3 exit blockers (PRs #360–#365): canonical flight card rendering, round-trip dedupe, `is_round_trip` persistence, Saved-item Trip Ideas surfacing, create-with-search canonical flight seeding. All resolved. See `docs/product/DECISION_LOG.md` for durable records.

- Earlier Concierge / provider / save-flow work (Stage 2A, Flights v1, Provider Registry v1): folded into product source-of-truth docs. See `docs/product/DECISION_LOG.md` and `docs/ai/MISS_LEDGER.md`.

## Active invariants / safety packs to remember

Named packs in `docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md` (Travel section) own the rules. The packs themselves are the source of truth — do not paste their contents elsewhere:

- Google Places Addable Authority Pack
- Enrichment Evidence Only Pack
- Semantic Concierge Behavior Pack
- AI Concierge Card Contract Pack
- No Mock/Sample Visible Data Pack
- Latency Budget Pack
- Backend-only Scaffold Pack / No Visible Behavior Change Pack / Test Tier Pack (cross-cutting)

## Known risks / unresolved issues

- `saved_items` migration 005 must be applied to the Supabase project before Save is live in production. Migration is in `backend/db/migrations/005_saved_items.sql`.
- Hotels Slice 5A is discovery-only (`HotelDiscoveryCard`); do not add rates, prices, availability, or a fake hotel provider. Real hotel offers require a provider-backed Hotel Offer contract (deferred to Stage 2B or later).
- Flights v1 is **live and visible** (2026-05-13): Duffel (`LINK_OUT`, `production_allowed=True`) is trust-certified (`DUFFEL_SCHEDULE_TRUST_CERTIFIED=1`). Trust gate + route/date validation active. Slices default to `max_connections=0` (direct flights). `DUFFEL_DEBUG=false` (cert complete). **Google Flights link-out now supports one-way/round-trip and verified adult passenger count from real tfs fixtures**: `booking_link` is `SEARCH_REDIRECT` (Google Flights tfs= URL) for valid queries; falls back to UNAVAILABLE when URL cannot be built. Encoding verified against 5 real URL samples — field 2=2 for both trip types; round-trip = field 19=1 + two repeated legs; passenger count = repeated field_8=1 per adult. Frontend `FlightCard` shows "Search on Google Flights" — search redirect only, never booking. No OTA/booking URL ever generated. No Duffel orders. Skyscanner PENDING. Ignav DISABLED. Amadeus DISABLED.
- Saved-list foundation (Stage 3 v1) is live; `/saved` page, grouping, remove, and nav links all shipped.
- AI destination intelligence, road trip mode, deal/points intelligence, and Travel Watchtower are deferred to later stages.

## Next recommended step

**Wife-Wow design system foundation.** Stage 3 is functionally exited. Design tokens, premium surface language, shared components, and vertical result-card visual foundation are the next unlock. Strict no-behavior-change scope: no provider/search/API route/Tavily changes, no flight/hotel/saved-trip logic changes. After design foundation merges → Stage 4 AI destination intelligence entry contract.

Active env state: `DUFFEL_API_KEY` + `DUFFEL_FLIGHTS_ENABLED=1` + `DUFFEL_SCHEDULE_TRUST_CERTIFIED=1` + `DUFFEL_BOOKING_ENABLED=0`. Key server-side only; never `NEXT_PUBLIC_`. `IGNAV_FLIGHTS_ENABLED=0`.

## Handoff maintenance rule

- This file is current state only. It is not an append-only log.
- Keep under ~250–500 lines. If it grows past that, **compact before adding** — summarize older sections, do not extend them.
- Every meaningful PR may update this file, but by **replacing or summarizing**, never by appending.
- Move durable historical detail to `docs/ai/MISS_LEDGER.md` (workflow/process misses) or `docs/product/DECISION_LOG.md` (product decisions). Do not preserve old noise just because it exists.
- Do not create new archive files for routine PRs. An archive is justified only when current-state value is being replaced and the original detail is still useful elsewhere.
- Run `python scripts/repo_hygiene_audit.py` before opening cleanup-style PRs and after any major phase. The audit is report-only and flags handoff bloat, banned legacy paths, and uncollected/obsolete tests. See `docs/ai/REPO_HYGIENE.md`.
- `CLAUDE.md`, `docs/ai/AI_REPO_OPERATING_SYSTEM.md`, and `docs/ai/PROMPT_LIBRARY.md` enforce this rule.
