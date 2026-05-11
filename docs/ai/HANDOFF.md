# HANDOFF — Current Repo State

Last updated: 2026-05-11

## Purpose

This file is **current operational state**, not a historical log. It is meant to be loaded into context every session, so it must stay compact. Do not append PR-by-PR history. When something changes, replace or summarize the affected section instead of adding new entries.

## Current product stage

- Roadmap stage: **Stage 2 — Open app before trip exists.** Stage 1 is GREEN. Stage 2A contract is defined in `docs/product/STAGE_2A_CONTRACT.md`. See `docs/product/ROADMAP.md`.
- Active build queue item: **Stage 2A Slice 3 — Trip-Optional AI Concierge.** Slice 2 shipped.
- Current north-star reminder: Discover → Search → Save → Plan → Optimize → Watch. The app must be useful before a trip exists. Wife-wow goal applies. See `docs/product/NORTH_STAR.md`.

## Current architecture / runtime state

- OS v4 is the canonical operating system. No v4.2 or v5 labels.
- Google Places is canonical for addable cards. Yelp / Foursquare / editorial are enrichment / evidence only and cannot mint addable cards.
- AI Concierge card field contract is the source of truth (`display.displayWhy`, `supportingDetails.whyPick`, top-level `whyPick`).
- Latency Budget Pack governs total request-path latency, not just local provider timeouts.
- For long architecture references, read `artifacts/travel_concierge_product_north_star_v3.md`, `artifacts/travel_concierge_v4_travel_os_addendum.md`, `artifacts/ai_concierge_semantic_place_intelligence.md`, and `artifacts/ai_concierge_semantic_place_intelligence_v2_amendment.md` rather than copying them here.
- Runtime workflow guardrails: advisory `.claude/hooks/ai_os_advisory.py` reminds about contract / claim-safety / latency / SQL / env paths. No blocking hooks.

## Recent meaningful PRs

Keep this section small. Only entries that affect future work; replace older lines as they age out.

- 2026-05-11 — **Stage 2A Slice 2 — Unified Result Actions v1 + saved_items foundation.** Migration 005 adds `saved_items` table (user-scoped, vertical enum: restaurant|attraction|hotel|flight, provider identity, display_snapshot JSONB, search_context JSONB, provenance JSONB, soft-delete, RLS, partial unique index for provider dedup). Backend: `SavedItemsService` + `/saved-items` route (POST/GET/DELETE). Frontend: `SavedItem` + `SavedItemCreate` types, `saveItem`/`listSavedItems`/`deleteSavedItem` API helpers, `ResultActionSheet` component (Save live; Add to Trip / Create Trip deferred with clear UX). Wired into `RestaurantExploreFlow` result cards. 13 backend tests, 42 frontend tests pass. No changes to `TripBuilder`, `TripIdeasPanel`, or `tripCandidates.ts`.
- 2026-05-11 — **Stage 2A Slice 1 — Global Explore Shell v1.** `/explore` route + `ExploreShell` component with 4-vertical entry grid (Flights, Hotels, Restaurants, Attractions). Restaurants execute via real `searchRestaurants` (Google Places, no trip_id). Attractions/Hotels/Flights show structured forms + polished deferred states (routes mock-backed or deleted — documented in source). "Explore" link added to Sidebar and MobileNav. `ExploreResultContext` type carries full Slice-2 action-ready payload (vertical, destination, dates, origin, guests, passengers, providerIdentity, originalPayload). 43 new tests in `global-explore-shell.test.mjs`; 518 total pass. No SQL migration. No changes to `TripBuilder`, `tripCandidates.ts`, or AI Concierge behavior.
- 2026-05-11 — **Trip Workspace Finalized Itinerary Card Experience v1 (Level 2).** Two gaps fixed: (a) hotel add-to-day data loss — `handleAddCandidateToItinerary` called `createItem` for hotels, stripping all details (stars, rating, amenities, area_label, proximity_label); new `addHotelToDay` in `api.ts` preserves the full `item.details` payload; TripBuilder uses it; (b) display layer gaps — `ItineraryItemCard` now has vertical-specific sections for `activity` (rating ★, category, tags, maps link) and `meal` (cuisine, rating ★, price level $/$$/$$, tags); hotel section enhanced with stars (★★★★★), area badges (In Best Area / Close to Best Area), proximity label, and amenities/tags pills alongside existing check-in/check-out/rating. Flight schedule display (origin→dest, dep/arr times, outbound/return leg badge) unchanged. 48 tests in `frontend/tests/itinerary-card-finalized-display.test.mjs` (includes payload-level field-mapping and handler-routing proofs added in correction commit); 144 total frontend tests pass across 9 bundles. No SQL migration. No live providers.
- 2026-05-10 — **Level 3 Trip Data Contract Rescue.** Persisted ACTIVITY/MEAL rows were not surfacing in the Attractions/Restaurants panels because the frontend still hydrated those panels from the legacy `trips.metadata.explore_snapshot` cache, which was empty after fresh creation and then triggered a slow AI Concierge "Top attractions in <city>" fallback that wrote `[]` back, locking the UI at 0. Simultaneously, all 39 creation-seed candidates were being dumped into Trip Ideas. Fixes: (a) `itinerary_items` (day_id IS NULL) is now the single canonical source of truth — new `frontend/src/lib/tripCandidates.ts` selector groups persisted rows into flights / round-trip / hotels / attractions / restaurants with stable dedupe + on-the-fly aiScore enrichment; (b) `TripBuilder` reads all four verticals from this selector via one `fetchTripItems` call; (c) snapshot demoted to a deprecated empty-bucket fallback — `mergePersistedWithSnapshot` cannot override non-empty persisted buckets; (d) backend `list_unscheduled_items` re-scoped to `source_kind == "concierge_idea"` so Trip Ideas holds only the user's explicit shortlist; (e) `TripIdeasPanel` groups by vertical with a per-vertical visible cap + Show more/less; (f) concierge `_save_message` and `_persist_request_log_task` quietly drop FK 23503 from a deleted trip (INFO, not WARNING). Obsolete callers (`searchAttractionsViaConcierge`, `isCanonicalSnapshotAttraction`) and the tests pinning the snapshot-first hydration internals were removed; replacement coverage lives in `frontend/tests/trip-candidates-contract.test.mjs`, `frontend/tests/trip-ideas-grouping.test.mjs`, and `backend/tests/test_concierge_deleted_trip_lifecycle.py`. No SQL migration. No live providers.
- 2026-05-10 — **PR #318** — Level 2: unified four-vertical trip seeding reliability. Fixed: (1) flights=0 bug — airport cross-product blew 15s Duffel budget; now uses primary airport only; (2) hotels not immediately visible — Supabase `RemoteProtocolError` silently swallowed; added `supabase_retry.py` + WARNING-level logging; (3) attractions=0 — no creation-time seeding; added `SearchService.search_attractions` (Google Places, fail-closed); (4) restaurants=0 — same; `search_restaurants` now called concurrently. `create_with_search` runs 5 concurrent workers (was 3), returns `seeding_status` dict per vertical. 121 tests pass. No SQL migration.
- 2026-05-10 — project source/test/docs hygiene PR. Deleted orphan `ai/` root scaffolding package, `scripts/design_bible/` PDF generator, and the orphan `artifacts/Travel_Concierge_Design_Bible.pdf` it produced. Removed dead `PRODUCT_SURFACE_AUDIT.md` / `progress_log.md` references in `docs/ai/LEGACY_FLIGHTS_HOTELS_STRATEGY.md`. Added report-only `scripts/repo_hygiene_audit.py` + `docs/ai/REPO_HYGIENE.md`. No product behavior change.
- 2026-05-10 — workflow architecture hygiene (claude-flow stack, ~37 stale/duplicate workflow assets, cross-AI-tool configs removed). Canonical anchors: `.claude/skills/`, `docs/ai/TEST_ROUTING.md`, `docs/ai/PROMPT_LIBRARY.md`, `.github/pull_request_template.md`, `docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md`.
- Earlier Concierge / provider / save-flow work has been folded into product source-of-truth docs and is no longer tracked PR-by-PR here. See `docs/product/DECISION_LOG.md` and `docs/ai/MISS_LEDGER.md` for durable records.

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
- AI Concierge (`callConcierge`, `callConciergeSearch`) currently requires a `tripId`. Slice 3 must make this optional.
- Attractions vertical is deferred: `/search/attractions` was removed (v1C), and `searchAttractionsViaConcierge` requires a tripId. Slice 3 unblocks this.
- Hotels vertical is deferred: `/search/hotels` is mock-backed (BLOCK_LEGACY_PRODUCT_MOCK). Needs a real provider.
- Flights vertical is deferred: `/search/flights` is mock-backed. Needs Duffel/Amadeus real provider.
- Saved-list foundation (Stage 3 root object) not built; ideas still need a non-trip home.
- AI destination intelligence, road trip mode, deal/points intelligence, and Travel Watchtower are deferred to later stages.

## Next recommended step

Implement Stage 2A Slice 3 — Trip-Optional AI Concierge. Backend: `callConcierge`/`callConciergeSearch` accept optional `trip_id`; when null, skip trip-context hydration and return place cards only. Frontend: `callConcierge`/`callConciergeSearch` in `api.ts` accept optional `tripId`. No change to existing trip-bound Concierge behavior. This unblocks the Attractions vertical in the Explore shell.

## Handoff maintenance rule

- This file is current state only. It is not an append-only log.
- Keep under ~250–500 lines. If it grows past that, **compact before adding** — summarize older sections, do not extend them.
- Every meaningful PR may update this file, but by **replacing or summarizing**, never by appending.
- Move durable historical detail to `docs/ai/MISS_LEDGER.md` (workflow/process misses) or `docs/product/DECISION_LOG.md` (product decisions). Do not preserve old noise just because it exists.
- Do not create new archive files for routine PRs. An archive is justified only when current-state value is being replaced and the original detail is still useful elsewhere.
- Run `python scripts/repo_hygiene_audit.py` before opening cleanup-style PRs and after any major phase. The audit is report-only and flags handoff bloat, banned legacy paths, and uncollected/obsolete tests. See `docs/ai/REPO_HYGIENE.md`.
- `CLAUDE.md`, `docs/ai/AI_REPO_OPERATING_SYSTEM.md`, and `docs/ai/PROMPT_LIBRARY.md` enforce this rule.
