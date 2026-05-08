# Legacy Flights/Hotels Strategy v1 — Audit & Migration Plan

> **Status update (2026-05-08): Fail-Closed UX v1 (Option A) IMPLEMENTED** — see PR on branch `claude/fail-closed-ux-flights-hotels-XBsgp`. `/trips/create-with-search` now fails closed with `HTTP 503 {code: "provider_unavailable"}` on **both** the empty-results path and the non-empty mock-row path (`source ∈ {mock,demo,fixture}` or any `book.example.com` booking URL — covers flights, hotels, round-trip pair legs, and option deep-links). No trip, no itinerary days, no itinerary items are persisted on either branch. `TripBuilderForm` shows honest provider-unavailable copy and offers a `createTrip()` blank-trip fallback. `OptimizeTripModal` no longer says "Try adjusting your dates"; it surfaces honest provider-unavailable copy and additionally refuses to surface mock-derived rows for selection (URL-host signal — `source` is not on the FE wire format). New tests: `backend/tests/test_create_with_search_fail_closed.py` (10 cases) and `frontend/tests/fail-closed-flights-hotels.test.mjs`. **Next step: select a provider (Option C flights and/or Option D hotels) for a future provider-integration PR — implementation, not strategy work, is now the gating concern.**

Date: 2026-05-08
Severity: **Level 2** (architecture audit / spec). No live mock leakage was discovered in canonical Concierge addable flows, but mock-derived flight/hotel rows **can still be persisted into itinerary items** when `BLOCK_LEGACY_PRODUCT_MOCK` is off — see §5 risk table. No production behavior change in this PR. No SQL. No new providers. No new LLM calls. No UI redesign.
Branch: `claude/audit-flights-hotels-strategy-KoptK`

> Companion to `docs/ai/PRODUCT_SURFACE_AUDIT.md` (post-PR #290 cleanup audit). This document is the deeper deferred analysis for the **flights/hotels** surfaces that the cleanup audit explicitly punted to a "real-provider strategy PR."

## 0. Product capability vs. implementation

This strategy explicitly distinguishes:

1. **Product capability we want to preserve.**
   - Round-trip flights: search outbound + return options, display a paired round-trip recommendation, allow adding outbound flight to Day 1, add return flight to the final day, persist into the itinerary once provider-backed or user-entered.
   - Hotels: search and display hotel options, allow adding a hotel stay, persist into trip-level lodging once provider-backed or user-entered.
2. **Current mock-backed implementation to retire or fail-close.** `_mock_flights`, `_mock_hotels`, `_mock_round_trip_flights` and the routes/callers below.
3. **Future canonical/provider-backed implementation path.** §6.
4. **Interim UX behavior when no real provider is available.** §7 (selected next PR).

We are **not** recommending permanent deletion of the flights or hotels product concept. Routes and frontend entry points may be retired only if and when a safer fail-closed UX or a canonical provider replacement lands.

## 1. Backend route inventory

| Route | Handler | Status | Producer | Mock-leak risk (flag off) | Persistence risk |
|---|---|---|---|---|---|
| `POST /search/flights` | `backend/app/routes/search.py:99` `search_flights()` | Guarded mock — live | `SearchService.search_flights` → `_mock_flights` (`backend/app/services/search.py:897,925`) | Emits realistic mock rows + fake `book.example.com` booking URLs | None directly; persisted only via `OptimizeTripModal.handleSelect` and `/trips/create-with-search` |
| `POST /search/round-trip-flights` | `backend/app/routes/search.py:129` `search_round_trip_flights()` | Guarded mock — server-side only | `SearchService.search_round_trip_flights` (`backend/app/services/search.py:972`) calls `search_flights` twice | Indirect (via `_mock_flights`) | Persisted indirectly only through `/trips/create-with-search` (round-trip pair selection currently unused on persistence path) |
| `POST /search/hotels` | `backend/app/routes/search.py:157` `search_hotels()` | Guarded mock — live | `SearchService.search_hotels` (`backend/app/services/search.py:1014`) → `_mock_hotels` | Emits realistic mock rows + fake `book.example.com` URLs | Same as flights |
| `POST /trips/create-with-search` | `backend/app/routes/trips.py:409` `create_trip_with_search()` | **Mixed** — calls `_mock_flights` + `_mock_hotels` + `_mock_round_trip_flights` server-side, persists scored top-10 flight/hotel rows into `itinerary_items` | Transitive via `_mock_*` (each honors `BLOCK_LEGACY_PRODUCT_MOCK`) | **Highest-blast-radius mock-derived persistence path in the repo today.** Trip is created unconditionally even when both arrays are empty. |
| `POST /optimize/trip` | `backend/app/routes/optimize.py` | Canonical scorer | n/a | None (operates on caller-supplied data) | None |

Route quarantine seams in `backend/app/routes/search.py:77-82` (`LEGACY_PRODUCT_MOCK_ROUTES`) and `backend/app/services/search.py:76-190` (`_legacy_product_mock_blocked`, `_LEGACY_MOCK_DEPENDENT_NAMESPACES`, `_suppress_legacy_mock_cache`).

`_mock_flights` definition: `backend/app/services/search.py:313`. `_mock_hotels`: `backend/app/services/search.py:406`. Both gated at top by `_legacy_product_mock_blocked()` and re-marked by `_mark_legacy_product_mock(...)` at `backend/app/services/search.py:868-869`. `LEGACY_PRODUCT_MOCK_FUNCTIONS` is now `{flights, hotels, restaurants}`.

## 2. Frontend caller inventory

| File | Calls | Surface | Status | Mock-leak risk (flag off) | Addability/persistence risk |
|---|---|---|---|---|---|
| `frontend/src/components/trips/OptimizeTripModal.tsx:19-23,109-115,181-184` | `searchFlights`, `searchHotels`, then `optimizeTrip`, then `addOptimizedFlightToDay` + `addOptimizedHotelToTrip` on accept | Mock-backed (guarded) | Live, last live mock product UI | Yes — flight/hotel options rendered with mock airlines, flight numbers, prices, and fake booking URLs | Persists on accept into `itinerary_items` (one flight to Day 1 + one trip-level hotel) |
| `frontend/src/components/trips/TripBuilderForm.tsx:48-62` | `createTripWithSearch` (dynamic import) | Mock-backed via backend | Live | Indirect (server orchestrates `_mock_flights`/`_mock_hotels`) | High — creates a new trip and persists top-10 flights + top-10 hotels with fake booking URLs |
| `frontend/src/lib/api.ts:178` `createTripWithSearch()` | `POST /trips/create-with-search` | API wrapper | Live | Indirect | n/a (wrapper) |
| `frontend/src/lib/api.ts:540` `searchFlights()` | `POST /search/flights` | API wrapper | Live | Indirect | n/a (wrapper) |
| `frontend/src/lib/api.ts:636` `searchHotels()` | `POST /search/hotels` | API wrapper | Live | Indirect | n/a (wrapper) |
| `frontend/src/lib/api.ts:1301` `addOptimizedFlightToDay()` | `POST /trips/{id}/days/{dayId}/itinerary-items` | Persistence | Live | None directly (caller-supplied data) | Persists whatever the caller hands in — currently mock-derived from `OptimizeTripModal` |
| `frontend/src/lib/api.ts:1333` `addOptimizedHotelToTrip()` | `POST /trips/{id}/itinerary-items` | Persistence | Live | None directly | Same — persists mock-derived hotel from `OptimizeTripModal` |

No other live frontend caller of flights/hotels was found. `searchRoundTripFlights` has no frontend wrapper or caller (server-only via `/trips/create-with-search`).

## 3. Reference classification (audit-required)

| Token | File:line | Class |
|---|---|---|
| `/search/flights` | `backend/app/routes/search.py:14,77,98` | live runtime (guarded) |
| `/search/flights` | `frontend/src/lib/api.ts:533,577` | live runtime wrapper |
| `/search/flights` | `backend/tests/test_product_surface_pruning_v1a.py:302,403` | test guard |
| `/search/flights` | `docs/ai/PRODUCT_SURFACE_AUDIT.md`, `docs/ai/HANDOFF.md`, `docs/ai/progress_log.md` | doc/handoff |
| `/search/hotels` | `backend/app/routes/search.py:19,79,156` | live runtime (guarded) |
| `/search/hotels` | `frontend/src/lib/api.ts:633,644` | live runtime wrapper |
| `/search/hotels` | `backend/tests/test_product_surface_pruning_v1a.py:304,405` | test guard |
| `/search/round-trip-flights` | `backend/app/routes/search.py:17,78,128` | guarded runtime (server-only) |
| `/search/round-trip-flights` | `backend/tests/test_product_surface_pruning_v1a.py` | test guard |
| `/trips/create-with-search` | `backend/app/routes/trips.py:409` | live runtime (persistence path) |
| `/trips/create-with-search` | `frontend/src/lib/api.ts:178` | live runtime wrapper |
| `createTripWithSearch` | `frontend/src/lib/api.ts:178`; `frontend/src/components/trips/TripBuilderForm.tsx:48-62` | live runtime |
| `OptimizeTripModal` | `frontend/src/components/trips/OptimizeTripModal.tsx` | live runtime |
| `searchFlights` | `frontend/src/lib/api.ts:540`; `frontend/src/components/trips/OptimizeTripModal.tsx:19,110` | live runtime |
| `searchHotels` | `frontend/src/lib/api.ts:636`; `frontend/src/components/trips/OptimizeTripModal.tsx:20,111` | live runtime |
| `searchRoundTripFlights` | (no frontend wrapper) | stale-removed (server-only via `/search/round-trip-flights`) |
| `_mock_flights` | `backend/app/services/search.py:313,868,879,925,954` | guarded runtime |
| `_mock_flights` | `backend/tests/test_product_surface_pruning_v1a.py:153,212` | test guard |
| `_mock_hotels` | `backend/app/services/search.py:406,869,880,1027` | guarded runtime |
| `_mock_hotels` | `backend/tests/test_product_surface_pruning_v1a.py:140,212` | test guard |
| `BLOCK_LEGACY_PRODUCT_MOCK` | `backend/app/services/search.py:76,85` and route docstrings; `backend/tests/test_product_surface_pruning_v1a.py` | live runtime gate |
| `addOptimizedFlightToDay` | `frontend/src/lib/api.ts:1301`; `frontend/src/components/trips/OptimizeTripModal.tsx:22,182` | live runtime persistence |
| `addOptimizedHotelToTrip` | `frontend/src/lib/api.ts:1333`; `frontend/src/components/trips/OptimizeTripModal.tsx:23,183` | live runtime persistence |

## 4. Current behavior matrix

| Scenario | `/search/flights`, `/search/hotels`, `/search/round-trip-flights` | `OptimizeTripModal` | `/trips/create-with-search` | `TripBuilderForm` |
|---|---|---|---|---|
| **Flag unset (`BLOCK_LEGACY_PRODUCT_MOCK` off)** | Returns mock rows with fake `book.example.com` URLs and synthesized airline/hotel names; cached in `research_cache` with `source="mock"` (1h TTL) | Renders mock options; on accept persists 1 mock flight + 1 mock hotel into the trip | Creates the trip and **persists top-10 mock flights + top-10 mock hotels** as itinerary items (`backend/app/routes/trips.py:504-580`), each with the fake booking URL embedded in `details.booking_url` and `details.booking_options[]` | Calls create-with-search; navigates to `/trips/{id}` with mock-derived items already persisted |
| **Flag on (`BLOCK_LEGACY_PRODUCT_MOCK=1`)** | `_mock_flights` / `_mock_hotels` short-circuit to `[]`. Emits `[legacy_product_mock.blocked]` telemetry. New cache writes skipped (`backend/app/services/search.py:926,955,1028`) | Throws `"No flights found …"` or `"No hotels found …"` (`OptimizeTripModal.tsx:114-115`); no items persisted | Per-search `try/except` swallows; `flights=[]`, `hotels=[]`, `round_trip_pairs=[]`. **Trip is still created** unconditionally (line 488). No itinerary items added. Returns `TripWithResults` with empty arrays | Calls succeed; trip exists with **blank itinerary** and the user is navigated to it |
| **Cached mock rows present, flag flipped on mid-flight** | `_suppress_legacy_mock_cache(namespace, cached)` (`backend/app/services/search.py:161,917,945,1018`) drops rows whose `source != "google_places"`. No leak path | Same as flag-on column | Same as flag-on column | Same |
| **Empty results (no mock, no provider)** | Returns `[]`. Clients see `[]` | Same fail-closed throw | Trip is created with empty itinerary (same hole as flag-on) | Same — trip exists, blank itinerary |

Key honest finding: **`/trips/create-with-search` creates a trip even when no flight/hotel data is available.** This is a UX hole independent of the mock vs. provider question — a "create trip from search" flow that produces empty itineraries on every flag-on or empty-result path is misleading.

## 5. Risk table

| Risk | Severity | Where | Notes |
|---|---|---|---|
| Mock-leak (live, flag off) | High | `_mock_flights`, `_mock_hotels`, both `/search/{flights,hotels,round-trip-flights}` routes, `/trips/create-with-search`, `OptimizeTripModal` | Default deployment with flag off ships fake airlines, fake flight numbers, and fake `book.example.com` URLs to users. |
| Persistence — fake booking URLs in `itinerary_items.details.booking_url` and `details.booking_options[]` | High | `backend/app/routes/trips.py:535-540,572-581`; `OptimizeTripModal.handleSelect` via `addOptimizedFlightToDay`/`addOptimizedHotelToTrip` | Stale rows persist forever in user trips even after a real provider lands; flag-on does not retroactively clean them up. |
| UX breakage when flag on | Medium | `OptimizeTripModal.tsx:114-115` (good: throws clear message); `/trips/create-with-search` (bad: creates an empty trip silently) | OptimizeTripModal degrades acceptably; create-with-search currently creates an honest-but-confusing empty itinerary. |
| Cache leak across flag flip | Low (already mitigated) | `_suppress_legacy_mock_cache` (`backend/app/services/search.py:161-190`) | Dual-layer guard (helper-level + cache-side). Tests cover this in `test_product_surface_pruning_v1a.py` (cache-leak tests at lines 613, 632). |
| Provider integration | High (future) | New provider would need credentials, schema, rate-limit budget, and canonical card normalization | Out of scope for this PR. |
| Test coverage drift — new mock callers | Medium | `test_only_known_frontend_files_reference_legacy_search` in `backend/tests/test_product_surface_pruning_v1a.py` is the live drift guard | Must be extended if/when `OptimizeTripModal` or `TripBuilderForm` are renamed/migrated. |
| AI scoring of mock rows | Medium | `_compute_flight_ai_score` / `_compute_hotel_ai_score` in `backend/app/routes/trips.py:472-481` | Scores meaningless data; harmless if rows never reach a user but compounds the persistence risk above. |

## 6. Provider strategy options

### Option A — Fail-Closed UX v1 (recommended)
- Make `BLOCK_LEGACY_PRODUCT_MOCK=1` the default for production.
- `/search/flights`, `/search/hotels`, `/search/round-trip-flights` keep returning `[]`.
- `OptimizeTripModal` already degrades to a clear error (no further work needed).
- `/trips/create-with-search` is changed to **fail closed**: refuse to create a trip when flights+hotels both empty, OR create the trip with an explicit "lodging/flights coming soon — provider integration pending" empty-state in the UI.
- Pros: zero new providers, zero new LLM calls, zero schema changes, removes the live mock-leak path entirely.
- Cons: temporary loss of the "one-click trip from search" demo.

### Option B — Provider Readiness Scaffold v1
- Add a typed `FlightProvider` / `HotelProvider` interface with one no-op implementation (`NullProvider` returning `[]`) wired behind feature flags. No live provider call.
- Move `_mock_flights` / `_mock_hotels` into `tests/fixtures/` only; runtime imports forbidden.
- Pros: cleanly separates capability from implementation; ready to slot a real provider in later.
- Cons: ~2x lines of churn vs. Option A; no immediate UX improvement.

### Option C — Flights Provider Integration v1 (Amadeus or similar)
- Real flight provider, live API, normalization to `FlightResult`, caching, rate-limit budget, eval.
- Pros: restores capability.
- Cons: far out of scope for an audit PR; needs API keys, provider eval, contract tests, latency gate, and a dedicated PR per provider.

### Option D — Hotels Provider Integration v1
- Same as C for hotels (Google Places lodging is a possibility but not a price/availability source; affiliate booking sites have policy/legal review costs).
- Cons: same as C, plus uncertain viable provider.

### Option E — Delete/disable mock-backed `OptimizeTripModal` + `/trips/create-with-search` until canonical provider exists
- Hardest fail-closed: remove the entry points so users never see the partial flow.
- Pros: zero ambiguity.
- Cons: deletes a user-facing capability with no replacement; violates the project requirement "prefer disable/fail closed over delete the product concept."

### Hybrid
- Option A now → Option B in the next PR → Option C/D when a vetted provider is selected.

## 7. Recommended next implementation PR

**Pick: Option A — Fail-Closed UX v1 for `OptimizeTripModal` + `/trips/create-with-search`.**

Why this is safer than the alternatives:

- Eliminates the only remaining live mock-leak path (`/search/{flights,hotels,round-trip-flights}` → `OptimizeTripModal` / `create-with-search`) **without** requiring a provider, credentials, LLM, or schema change.
- Closes the "create-empty-trip" UX hole that exists regardless of flag state.
- Preserves the product capability — routes, models, frontend wrappers, and persistence paths remain so a future provider PR can swap implementations under the same contracts.
- Avoids Option B's interface-design churn before we know which provider will land.
- Avoids Options C/D's provider-eval scope creep.
- Avoids Option E's destruction of a user-facing capability with no replacement.

Acceptance criteria for the next PR (Fail-Closed UX v1):

1. Flip the production default for `BLOCK_LEGACY_PRODUCT_MOCK` to **on** (in deploy config / docs only — no code default change unless explicitly approved). Document the rollout.
2. `/trips/create-with-search` returns HTTP 503/422 (or a 200 with `flights=[], hotels=[], round_trip_pairs=[], status="provider_unavailable"`) **without creating a trip** when both `flights` and `hotels` come back empty under the flag.
3. Frontend `TripBuilderForm` shows an honest "Flights & hotels are not yet provider-backed — create a blank trip and add items manually" empty-state and links to a manual trip create flow.
4. `OptimizeTripModal` already fails closed; tighten its error copy to say "provider integration pending" rather than "Try adjusting your dates" (which is misleading under flag-on).
5. Add backend test: `test_create_with_search_does_not_create_trip_when_provider_unavailable`.
6. Add frontend test: `OptimizeTripModal` displays the new copy under the flag-on path.
7. No change to `/ai/concierge`, `/ai/concierge/search`, AIConciergePanel, or canonical Google-Places restaurant flow.
8. No SQL, no new providers, no new LLM calls.
9. Update `docs/ai/HANDOFF.md` and `docs/ai/PRODUCT_SURFACE_AUDIT.md`.

## 8. Non-goals (explicit)

- No Amadeus / Google Flights / Booking.com / Skyscanner / Kayak / Expedia integration in this PR.
- No new API keys or environment requirements.
- No new LLM calls.
- No new SQL or schema changes.
- No redesign of `OptimizeTripModal`, `TripBuilderForm`, or `TripBuilder`.
- No deletion of `/search/flights`, `/search/hotels`, `/search/round-trip-flights`, `/trips/create-with-search`, `_mock_flights`, or `_mock_hotels` in this PR — these stay quarantined and will move with the chosen next PR.
- No changes to `AIConciergePanel`, `/ai/concierge`, `/ai/concierge/search`, or the canonical display contract.
- No replacement mock fixtures created.
- No conversion of mock-backed flight/hotel data into canonical production cards.
- No cleanup of historical mock-derived rows already persisted into `itinerary_items` (separate cleanup PR if/when needed).

## 9. Self-audit — acceptance-criteria → evidence map

| Acceptance criterion | Evidence in this PR |
|---|---|
| 1. Repo has a clear Legacy Flights/Hotels Strategy artifact | This file: `docs/ai/LEGACY_FLIGHTS_HOTELS_STRATEGY.md` |
| 2. Every remaining flights/hotels mock-backed route and caller inventoried | §1 (routes), §2 (frontend), §3 (token-by-token) |
| 3. Current behavior with `BLOCK_LEGACY_PRODUCT_MOCK` on/off explained | §4 behavior matrix rows 1–2 |
| 4. Cache behavior and persistence risk explained | §4 row 3, §5 rows 1–2, with `backend/app/services/search.py:161,917,945,1018` and `backend/app/routes/trips.py:504-580` citations |
| 5. Names safest next implementation PR and explains why | §7 (Option A) and "Why this is safer" paragraph |
| 6. Explicitly rejects unsafe shortcuts (fake booking links, mock-derived persisted cards) | §5 (Persistence row), §6 (Option E), §8 |
| 7. Any added tests are contract-focused, not brittle snapshots | No new tests added in this PR — existing contract tests in `backend/tests/test_product_surface_pruning_v1a.py` already cover the flag-on, cache-leak, and caller-registry contracts. Test additions deferred to the Fail-Closed UX v1 PR. |
| 8. No SQL, no provider expansion, no LLM calls | §0, §6, §8 |
| 9. Docs/handoff/progress lightly updated | `docs/ai/HANDOFF.md` and `docs/ai/progress_log.md` updated in this PR |
| 10. PR summary includes severity, risks, files changed, audit findings, selected next PR, tests, SQL/UI/provider answers | See PR summary in the PR body |

## 10. Tests run for this audit

This PR is doc-only; no production code changes. Tests run as evidence:

- `backend/tests/test_product_surface_pruning_v1a.py` — existing flag-on/cache-leak/caller-registry guards still pass on base.
- `backend/tests/test_cost_guardrails.py` — no change.
- `frontend/tests/explore-concierge-migration.test.mjs`, `frontend/tests/explore-hydration.test.mjs` — no change.

If full suites have unrelated failures on base, those are documented in `docs/ai/HANDOFF.md` rather than re-litigated here.
