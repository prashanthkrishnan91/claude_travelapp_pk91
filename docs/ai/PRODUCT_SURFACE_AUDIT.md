# Product Surface Audit — Post-PR #290

Date: 2026-05-08
Severity: Level 2 (architecture audit / spec). No live mock leakage into AIConciergePanel addable cards or Add-to-Day / Save / Maps flows was discovered, so no Level 3 escalation.
Type: Decision artifact. No production behavior change. No SQL. No new providers. No new LLM calls. No UI change.

This document is the post-cleanup audit that follows PRs #287 (canonical display contract), #288 (legacy mock quarantine + caller registry), #289 (TripBuilder Explore migration to canonical `/ai/concierge/search`), and #290 (frontend fallback ladder removal).

It maps every remaining product-surface route, every important frontend caller, the production status of each surface, and recommends the next single focused PR.

## 1. Assumptions

- PR #287 landed: AIConciergePanel addable cards must satisfy the canonical display contract — `display.addability === "addable"`, `display.displayName`, `display.displayCategory`, `googleVerification.providerPlaceId`. Confirmed at `frontend/src/components/trips/AIConciergePanel.tsx:319,519-526,1284-1307`.
- PR #288 landed: `BLOCK_LEGACY_PRODUCT_MOCK` env flag short-circuits every `_mock_*` helper in `backend/app/services/search.py` and suppresses mock-source cache rows in `_LEGACY_MOCK_DEPENDENT_NAMESPACES`. Confirmed at `backend/app/services/search.py:84-190`.
- PR #289 landed: TripBuilder Explore now calls `searchAttractionsViaConcierge(tripId, destination)` → `/ai/concierge/search`. Grouped/Areas view + Best Area card removed (fail-closed). Confirmed at `frontend/src/components/trips/TripBuilder.tsx:71-80,1367-1368`.
- PR #290 landed: Top-level fallback ladders removed from AIConciergePanel; canonical display contract enforced on the addable path.
- Legacy caller registry test `backend/tests/test_product_surface_pruning_v1a.py::test_only_known_frontend_files_reference_legacy_search` is the live drift guard for any new `/search/*` mock caller.

## 2. Backend route inventory

| Route | Backend producer | Status | Mock-leak risk | Addability risk | Notes |
|---|---|---|---|---|---|
| `POST /ai/concierge` | `backend/app/routes/ai.py:699` | Canonical | None | High (intentionally) — addable cards | Goes through `display_contract.py` normalizer at the response boundary. |
| `POST /ai/concierge/search` | `backend/app/routes/ai.py:745` | Canonical | None | High (intentionally) — addable cards | Same display contract seam. Sole canonical attractions surface for TripBuilder Explore. |
| `POST /ai/concierge/debug-trace` | `backend/app/routes/ai.py:822` | Canonical (diagnostic) | None | None | Diagnostic only; never renders cards. |
| `GET /ai/concierge/{trip_id}/messages` | `backend/app/routes/ai.py:895` | Canonical | None | None | Conversation history. |
| `DELETE /ai/concierge/cache` | `backend/app/routes/ai.py:901` | Canonical (admin) | None | None | Cache flush. |
| `POST /search/restaurants` | `backend/app/routes/search.py:198` → `SearchService.search_restaurants` (Google Places) | Canonical | None (Google-Places-backed; fail-closed when key missing) | Medium — TripBuilder Explore renders restaurant cards with Add-to-Day / Maps | Listed in `CANONICAL_PRODUCT_ROUTES`. Excluded from `_LEGACY_MOCK_DEPENDENT_NAMESPACES`. |
| `POST /search/attractions` | `backend/app/routes/search.py:176` → `_mock_attractions` | Guarded mock — orphaned | Guarded (`BLOCK_LEGACY_PRODUCT_MOCK` + cache suppression) | None at runtime — no live frontend caller post PR #289 | Frontend caller removed in PR #289. Backend route + service still present; quarantine enforced. Candidate for v1C deletion if no consumer is added. |
| `POST /search/clusters` | `backend/app/routes/search.py:221` → `SearchService.search_clusters` (partial mock via `_mock_attractions`) | Guarded mock — orphaned | Guarded; cluster shape derives from `_mock_attractions` | None at runtime — UI removed in PR #289 | No frontend caller. Strong deletion candidate. |
| `POST /search/best-area` | `backend/app/routes/search.py:244` → `SearchService.get_best_area` (partial mock) | Guarded mock — orphaned | Guarded | None at runtime — UI removed in PR #289 | No frontend caller. Strong deletion candidate. |
| `POST /search/flights` | `backend/app/routes/search.py:96` → `_mock_flights` | Guarded mock — live | Guarded; emits `[legacy_product_mock.emitted]` telemetry while flag off | Medium — `OptimizeTripModal` renders flight options, persists via `addOptimizedFlightToDay` | Sole live mock-backed user-facing surface today. |
| `POST /search/round-trip-flights` | `backend/app/routes/search.py:126` → `_mock_round_trip_flights` | Guarded mock — server-side | Guarded | Indirect — only invoked from `POST /trips/create-with-search` (`backend/app/routes/trips.py:454`) | No direct frontend caller. |
| `POST /search/hotels` | `backend/app/routes/search.py:154` → `_mock_hotels` | Guarded mock — live | Guarded | Medium — `OptimizeTripModal` renders hotel options, persists via `addOptimizedHotelToTrip` | Same risk class as `/search/flights`. |
| `POST /trips/create-with-search` | `backend/app/routes/trips.py:409` | Mixed — calls `_mock_flights` + `_mock_hotels` + `_mock_round_trip_flights` server-side | Guarded transitively (each underlying `_mock_*` honors `BLOCK_LEGACY_PRODUCT_MOCK`); failure mode is empty arrays not fabricated rows | High — persists scored flight/hotel rows into the new trip when flag is off | Trip-creation entry point used by `TripBuilderForm`. |
| `POST /optimize/trip` | `backend/app/routes/optimize.py:11` | Canonical (optimization scoring; does not synthesize new product cards) | None | None | Operates on already-persisted itinerary items. |

Routes outside the product-card scope (`/cards`, `/deals`, `/itinerary`, `/plan`, `/resolve`, `/dashboard`, `/value`, `/compare`, `/context`, `/travel`, `/ai/timeline/suggest`) are not on the audit surface — they do not synthesize Add-to-Day place cards from mock fixtures.

## 3. Frontend caller inventory

| File | Calls | Surface | Status post PR #290 | Mock-leak risk | Addability risk |
|---|---|---|---|---|---|
| `frontend/src/components/trips/AIConciergePanel.tsx` | `/ai/concierge`, `/ai/concierge/search` (via `lib/api.ts`) | Canonical | Live, contract-enforced | None | Yes — addable cards. Display contract gates fail-closed on missing `display.*` / `providerPlaceId`. |
| `frontend/src/components/trips/TripBuilder.tsx` | `searchAttractionsViaConcierge` (→ `/ai/concierge/search`) and `searchRestaurants` (→ `/search/restaurants`) | Canonical | Live | None — both canonical | Yes — addable attractions (Google-Places-verified) and restaurants. |
| `frontend/src/components/trips/OptimizeTripModal.tsx` | `searchFlights`, `searchHotels` | Mock-backed (guarded) | Live | Guarded; emits when flag off | Yes — flight + hotel options persisted to itinerary. **Last live mock product surface.** |
| `frontend/src/components/trips/TripBuilderForm.tsx` | `createTripWithSearch` → `/trips/create-with-search` | Mixed (transitively mock-backed) | Live | Guarded | Yes — persists scored flight/hotel rows at trip creation. |
| `frontend/src/components/concierge/ConciergeResponse.tsx` | none (presentational; consumes a `ConciergeResponse` payload it does not fetch) | Non-live | **Not wired into any live `app/` route or page.** Only consumer is its own story file. | None at runtime; no fetch | Low — `PlaceRecommendationsView`'s "Add to Trip" button has no `onClick` handler (`PlaceRecommendationsView.tsx:69-71`). It is a static demo button. |
| `frontend/src/components/concierge/PlaceRecommendationsView.tsx` | none | Non-live (story/demo) | Same as above | None at runtime | Same as above. Looser fallback logic noted in task brief is contained because this view is not on the live AIConciergePanel path. |
| `frontend/src/components/concierge/PlaceRecommendationsView.stories.tsx` | none | Story-only | Storybook only | Possible if ever wired to real data; today it is demo-only | None at runtime. Watch-list candidate for v1C non-live cleanup. |
| `frontend/tests/explore-concierge-migration.test.mjs` | none (asserts non-presence of legacy tokens via `assert.doesNotMatch`) | Test-only | Live | None | None |
| `frontend/tests/explore-hydration.test.mjs` | none | Test-only | Live | None | None |
| `frontend/src/lib/api.ts` | exports `searchFlights`, `searchHotels`, `searchRestaurants`, `searchAttractionsViaConcierge`, `callConciergeSearch`, `createTripWithSearch`, ... | Mixed | Live | Guarded for the legacy wrappers; canonical for the rest | Helper layer; routes addability/leak risk to the consuming component. |

The only frontend files still referencing legacy `/search/*` mock-backed tokens (per the v1A registry test) are `lib/api.ts`, `OptimizeTripModal.tsx`, `tests/explore-hydration.test.mjs`, and `tests/explore-concierge-migration.test.mjs`. All other prior callers were removed in PR #289.

## 4. Surface classification summary

- Canonical, production-safe (live, addable allowed): `/ai/concierge`, `/ai/concierge/search`, `/search/restaurants`.
- Canonical, production-safe (live, non-card): `/optimize/trip`, `/ai/concierge/{trip_id}/messages`, `/ai/concierge/debug-trace`, `/ai/concierge/cache`.
- Mock-backed but blocked/guarded, live: `/search/flights`, `/search/hotels` (via `OptimizeTripModal`); `/search/round-trip-flights` (server-side via `/trips/create-with-search`); `/trips/create-with-search` (mixed).
- Mock-backed and orphaned (guarded, no live caller): `/search/attractions`, `/search/clusters`, `/search/best-area`. Backend code still loaded; no production consumer.
- Non-live / story-only: `frontend/src/components/concierge/ConciergeResponse.tsx`, `PlaceRecommendationsView.tsx`, `PlaceRecommendationsView.stories.tsx`. Effectively dead frontend code from the live-routing perspective.
- Quarantined / dead: none yet — orphan routes above are still loaded; deletion is the next decision point.

## 5. Risk ratings

| Surface | Mock-leak risk | Addability risk | Cache leak risk | Composite |
|---|---|---|---|---|
| `/ai/concierge*` | none | high (intended) | none (own cache, canonical) | Low — contract-enforced |
| `/search/restaurants` | none | medium (intended) | guarded (own stale-mock eviction) | Low |
| `/search/flights` + `/search/hotels` (via OptimizeTripModal) | guarded | medium | guarded by `_suppress_legacy_mock_cache` | Medium — last live mock surface |
| `/trips/create-with-search` | guarded | high (persists at trip creation) | guarded (transitive) | Medium |
| `/search/round-trip-flights` | guarded | indirect | guarded | Medium |
| `/search/attractions` | guarded; orphan | none at runtime | guarded | Low — but dead-code risk |
| `/search/clusters`, `/search/best-area` | guarded; orphan | none at runtime | guarded | Low — but dead-code risk |
| `ConciergeResponse` / `PlaceRecommendationsView` (non-live) | none today | none at runtime (no `onClick`) | none | Low — fallback-leak watch-list |

## 6. Recommended next PR

**Selected: Candidate A — Product Surface Cleanup v1C, *deletion variant*.**

Concretely the next focused PR should:

1. Delete the orphaned backend route handlers `/search/attractions`, `/search/clusters`, `/search/best-area` from `backend/app/routes/search.py`.
2. Delete the corresponding `SearchService.search_attractions` / `search_clusters` / `get_best_area` methods and `_mock_attractions` from `backend/app/services/search.py` (along with the `attractions` namespace from `_LEGACY_MOCK_DEPENDENT_NAMESPACES` and any cluster/best-area helpers and models that become unreachable).
3. Delete the corresponding Pydantic models from `backend/app/models/search.py` that become unreachable.
4. Update `LEGACY_PRODUCT_MOCK_DEPENDENT_ROUTES`, `LEGACY_PRODUCT_MOCK_FUNCTIONS`, and `backend/tests/test_product_surface_pruning_v1a.py` registries to drop the now-deleted entries (the stale-entry guard test will force the update).
5. Add a small backend test that asserts the deleted route paths are no longer registered on the FastAPI app.

### Why A over B/C/D

- **B (legacy flights/hotels strategy)** touches the *only* live mock product surface, depends on a real-provider decision (Amadeus / Google Flights) that is explicitly out of audit scope, and would either be a multi-week migration or an irreversible UX removal. Doing A first shrinks the audit surface so that B can be scoped purely against `OptimizeTripModal` + `/trips/create-with-search` without the orphan-route noise.
- **C (non-live surface cleanup)** is real but lower risk — `PlaceRecommendationsView`'s "Add to Trip" button has no `onClick` handler today (verified at `PlaceRecommendationsView.tsx:69-71`), and `ConciergeResponse` is not imported by any `app/` page. The watch-list is captured here; doing A first removes the bigger orphan footprint.
- **D (test consolidation)** is cleanup, not a leakage-risk closer. It is fine to defer.
- **A is reversible, additive-test, single-PR scope** and completes the architectural promise of PR #289 (which fail-closed-removed the UI but left the backend orphans loaded).

### Variant alternative if v1C cannot be deletion-only

If a stakeholder still wants grouped/Areas / Best Area in the UI, then v1C must instead be a *canonical rebuild* over verified Concierge attractions (`/ai/concierge/search`) + `/search/restaurants`. That is a strictly larger PR and must not reuse the deleted `_mock_attractions` fixture. Default to the deletion variant unless explicitly directed otherwise.

## 7. Recommended deletion / quarantine candidates

- Delete: `/search/attractions`, `/search/clusters`, `/search/best-area` route handlers and underlying `SearchService` methods + `_mock_attractions` fixture + cluster/best-area pydantic models that become unreachable.
- Quarantine watch-list (not delete yet — they are story/demo surfaces and benign today): `frontend/src/components/concierge/ConciergeResponse.tsx`, `PlaceRecommendationsView.tsx`, `PlaceRecommendationsView.stories.tsx`. Add an explicit comment block stating they are non-live and must not be wired to real data without a v1C-style review. Consider a small frontend test that asserts no `app/` page imports `ConciergeResponse`.
- Defer: `/search/flights`, `/search/hotels`, `/search/round-trip-flights`, `/trips/create-with-search`. Quarantine remains the right state until B ships.

## 8. Recommended canonical rebuild candidates

- Long-term: real flights / hotels provider (or a Concierge-backed itinerary scaffold that does not synthesize new mock-shaped rows). Owner of strategy PR.
- Optional: canonical clustering / Best Area over verified Concierge attractions + `/search/restaurants`. Only if there is product demand; otherwise the deletion variant of A is final.

## 9. Explicit non-goals of this audit

- No implementation of canonical clustering or Best Area.
- No flights/hotels provider integration.
- No new providers, no new LLM calls, no SQL.
- No re-enabling of grouped/Areas or Best Area in the UI.
- No loosening of the AIConciergePanel canonical display contract.
- No restoration of broad top-level fallback ladders.
- No conversion of mock-backed data into addable production cards.
- No exposure of internal diagnostics to end users.

## 10. Self-audit — acceptance criterion → artifact

| Criterion | Where satisfied |
|---|---|
| 1. Repo has post-PR #290 audit artifact | This file (`docs/ai/PRODUCT_SURFACE_AUDIT.md`). |
| 2. Names every remaining legacy/mock/canonical route + every important frontend caller | §2 route inventory and §3 frontend caller inventory. |
| 3. Identifies which surfaces can affect Add to Day / Save / Maps / itinerary | §3 "Addability risk" column, §5 composite ratings. |
| 4. Distinguishes canonical / guarded / quarantined / non-live | §4 surface classification summary. |
| 5. Chooses one next PR with reasoning | §6 (Candidate A, deletion variant) with explicit comparison to B/C/D. |
| 6. Tests are contract-focused, not brittle string snapshots | No new tests in this PR; the existing caller-registry test in `backend/tests/test_product_surface_pruning_v1a.py` already covers the invariants this audit relies on. |
| 7. Add to Day / Save / Maps / itinerary preserved | No code change in this PR. |
| 8. No SQL, no provider expansion, no new LLM calls | None added. |
| 9. PR summary present | See pull request body. |

## 11. PR summary (for the pull request body)

- Severity: Level 2 (audit/spec).
- Root risk: orphaned mock-backed `/search/{attractions,clusters,best-area}` route handlers remain loaded after PR #289 removed their UI consumers; `OptimizeTripModal` + `/trips/create-with-search` remain the only live mock-backed product surface.
- Files changed: `docs/ai/PRODUCT_SURFACE_AUDIT.md` (new), `docs/ai/HANDOFF.md` (entry added), `progress_log.md` (entry added).
- Audit findings: see §2–§5.
- Selected next PR: Candidate A — Product Surface Cleanup v1C (deletion variant of orphaned `/search/{attractions,clusters,best-area}` and their service methods + `_mock_attractions`).
- Tests run: none added; existing `backend/tests/test_product_surface_pruning_v1a.py` invariants remain authoritative for the caller registry.
- Supabase SQL required: No.
- UI changes: No.
- New providers / LLM calls: No.
- Risks / limitations: this is a decision artifact only; orphan routes remain loaded until v1C ships. The non-live `ConciergeResponse` / `PlaceRecommendationsView` story surfaces are placed on a watch-list rather than deleted in this PR.
- Self-audit result: §10 maps each acceptance criterion to its artifact.
