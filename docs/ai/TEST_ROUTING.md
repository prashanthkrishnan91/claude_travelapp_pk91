# TEST_ROUTING — Travel Concierge

## Purpose
Prevent routine PRs from running the full backend suite (~2,600 tests) while preserving critical regression gates from PR #287–#299.

**Default rule:** Claude/Codex should **not** run `pytest tests/` for ordinary PRs. Use the lowest sufficient tier.

## Tier model

### Tier 0 — Changed-file adjacent (default)
Use for docs-only, isolated backend tests, or isolated frontend changes.

- Run tests directly tied to changed modules/files.
- Add one adjacent contract test if the changed file is in a shared mapper/contract surface.

### Tier 1 — Product contract/regression bundle
Use for Concierge/provider/search/product-surface work.

Canonical bundles (run only relevant bundles):

#### AI Concierge card contract bundle
- `cd backend && pytest tests/test_concierge_card_contract.py tests/test_concierge_display_contract.py tests/test_explore_snapshot.py`
- `cd frontend && node --test tests/concierge-renderers.test.mjs tests/explore-concierge-migration.test.mjs`

#### Flights provider bundle
- `cd backend && pytest tests/test_flights_product_contract_v1.py tests/test_amadeus_flight_provider.py tests/test_search_flights_provider_wiring.py`

#### Hotels provider bundle
- `cd backend && pytest tests/test_hotels_product_contract_v1.py tests/test_google_places_hotel_provider.py tests/test_search_hotels_provider_wiring.py`
- `cd frontend && node --test tests/hotels-discovery-only.test.mjs`

#### Mock/fail-closed safety bundle
- `cd backend && pytest tests/test_product_surface_pruning_v1a.py tests/test_create_with_search_fail_closed.py tests/test_search_flights_provider_wiring.py tests/test_search_hotels_provider_wiring.py`
- `cd frontend && node --test tests/fail-closed-flights-hotels.test.mjs tests/hotels-discovery-only.test.mjs`

#### OptimizeTripModal fail-closed bundle
- `cd frontend && node --test tests/fail-closed-flights-hotels.test.mjs tests/hotels-discovery-only.test.mjs`

#### TripBuilder / add-to-trip bundle
- `cd frontend && node --test tests/fail-closed-flights-hotels.test.mjs tests/explore-hydration.test.mjs`
- `cd backend && pytest tests/test_create_with_search_fail_closed.py`

### Tier 2 — Broader smoke (still targeted)
Use when touching shared routes/services/models/api mappers across multiple product surfaces.

- `cd backend && pytest tests/test_product_surface_pruning_v1a.py tests/test_create_with_search_fail_closed.py tests/test_flights_product_contract_v1.py tests/test_search_flights_provider_wiring.py tests/test_hotels_product_contract_v1.py tests/test_search_hotels_provider_wiring.py tests/test_concierge_card_contract.py tests/test_concierge_display_contract.py`
- `cd frontend && node --test tests/concierge-renderers.test.mjs tests/fail-closed-flights-hotels.test.mjs tests/hotels-discovery-only.test.mjs`

### Tier 3 — Full backend suite (`pytest tests/`)
Allowed only for:
- release checkpoints,
- shared infrastructure changes,
- test infrastructure changes,
- broad model/schema changes,
- suspicious targeted-test failures needing broad confirmation,
- explicit merge-gate request.

If Tier 3 is used, PR summary must include the explicit reason.

## Required PR evidence
Every PR summary must state:
1. **Test tier used**
2. **Why this tier was sufficient**
3. Whether full suite was skipped; if skipped, list targeted bundles used instead
4. If full suite was run, the high-risk reason

## Critical invariants that must remain covered
Do not merge without targeted coverage for:
- canonical AI Concierge card contract
- no mock-backed product rows
- no `book.example.com` persistence path
- flights/hotels provider fail-closed behavior
- no live `_mock_flights` / `_mock_hotels` route calls
- discovery-only hotels excluded from priced OptimizeTripModal inputs
- outbound flight Day 1 / return flight final-day behavior
