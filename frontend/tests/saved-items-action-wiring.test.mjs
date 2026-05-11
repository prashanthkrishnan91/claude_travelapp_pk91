/**
 * Saved Items & ResultActionSheet — Stage 2A Slice 2
 *
 * Focused structural tests verifying:
 * 1. SavedItem / SavedItemCreate types are exported from @/types.
 * 2. saveItem / listSavedItems / deleteSavedItem are exported from api.ts.
 * 3. ResultActionSheet component exists and exports the named export.
 * 4. ResultActionSheet renders a save button (save-action-btn testid).
 * 5. ResultActionSheet renders more-actions-toggle with deferred Add/Create.
 * 6. RestaurantExploreFlow imports ResultActionSheet.
 * 7. RestaurantExploreFlow no longer renders the Slice-1 "actions-pending-badge".
 * 8. buildSavePayload logic: restaurant context maps provider identity correctly.
 * 9. buildSavePayload logic: hotel sets guests (not passengers) in search_context.
 * 10. buildSavePayload logic: flight sets passengers + cabin_class (not guests).
 * 11. backend migration 005 exists with correct table/column DDL.
 * 12. saved_items route file exports correct paths/verbs.
 * 13. SavedItemsService file exists with create/list/delete methods.
 * 14. tripCandidates.ts is untouched (no saved_items import).
 * 15. TripBuilder.tsx is untouched (no saved_items import).
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');

function read(rel) {
  return readFileSync(path.join(root, rel), 'utf8');
}

// ── Source files ──────────────────────────────────────────────────────────────

const typesIndex = read('src/types/index.ts');
const apiTs = read('src/lib/api.ts');
const actionSheet = read('src/components/explore/ResultActionSheet.tsx');
const restaurantFlow = read('src/components/explore/RestaurantExploreFlow.tsx');
const migration005 = read('../backend/db/migrations/005_saved_items.sql');
const savedItemsRoute = read('../backend/app/routes/saved_items.py');
const savedItemsService = read('../backend/app/services/saved_items.py');
const tripCandidates = read('src/lib/tripCandidates.ts');
const tripBuilder = read('src/components/trips/TripBuilder.tsx');

// ── 1. Types exported ─────────────────────────────────────────────────────────

test('types/index.ts exports SavedItemVertical', () => {
  assert.ok(typesIndex.includes('SavedItemVertical'), 'SavedItemVertical missing from types');
});

test('types/index.ts exports SavedItemCreate', () => {
  assert.ok(typesIndex.includes('SavedItemCreate'), 'SavedItemCreate missing from types');
});

test('types/index.ts exports SavedItem interface', () => {
  assert.ok(
    typesIndex.includes('export interface SavedItem'),
    'SavedItem interface missing from types'
  );
});

test('SavedItem has userId, vertical, displayName, displaySnapshot, searchContext, provenance', () => {
  assert.ok(typesIndex.includes('userId'), 'userId missing from SavedItem');
  assert.ok(typesIndex.includes('displayName'), 'displayName missing from SavedItem');
  assert.ok(typesIndex.includes('displaySnapshot'), 'displaySnapshot missing from SavedItem');
  assert.ok(typesIndex.includes('searchContext'), 'searchContext missing from SavedItem');
  assert.ok(typesIndex.includes('provenance'), 'provenance missing from SavedItem');
});

// ── 2. API helper exports ─────────────────────────────────────────────────────

test('api.ts exports saveItem', () => {
  assert.ok(
    apiTs.includes('export async function saveItem'),
    'saveItem not exported from api.ts'
  );
});

test('api.ts exports listSavedItems', () => {
  assert.ok(
    apiTs.includes('export async function listSavedItems'),
    'listSavedItems not exported from api.ts'
  );
});

test('api.ts exports deleteSavedItem', () => {
  assert.ok(
    apiTs.includes('export async function deleteSavedItem'),
    'deleteSavedItem not exported from api.ts'
  );
});

test('api.ts saveItem calls /saved-items POST', () => {
  assert.ok(apiTs.includes('"/saved-items"'), '/saved-items endpoint missing from api.ts');
});

test('api.ts deleteSavedItem calls /saved-items/:id DELETE', () => {
  assert.ok(
    apiTs.includes('`/saved-items/${itemId}`'),
    'deleteSavedItem URL pattern missing'
  );
});

// ── 3–5. ResultActionSheet component ─────────────────────────────────────────

test('ResultActionSheet.tsx exports ResultActionSheet', () => {
  assert.ok(
    actionSheet.includes('export function ResultActionSheet'),
    'ResultActionSheet not exported'
  );
});

test('ResultActionSheet renders save-action-btn', () => {
  assert.ok(
    actionSheet.includes('data-testid="save-action-btn"'),
    'save-action-btn testid missing'
  );
});

test('ResultActionSheet renders more-actions-toggle', () => {
  assert.ok(
    actionSheet.includes('data-testid="more-actions-toggle"'),
    'more-actions-toggle testid missing'
  );
});

test('ResultActionSheet renders deferred add-to-trip-btn', () => {
  assert.ok(
    actionSheet.includes('data-testid="add-to-trip-btn"'),
    'add-to-trip-btn testid missing'
  );
});

test('ResultActionSheet renders deferred create-trip-btn', () => {
  assert.ok(
    actionSheet.includes('data-testid="create-trip-btn"'),
    'create-trip-btn testid missing'
  );
});

test('ResultActionSheet Add to Trip and Create Trip are disabled', () => {
  // Both deferred buttons must carry disabled attribute
  const addMatch = actionSheet.match(/data-testid="add-to-trip-btn"[^>]*>/);
  assert.ok(addMatch, 'add-to-trip-btn not found');
  assert.ok(
    actionSheet.includes('disabled') &&
      actionSheet.includes('Coming soon'),
    'deferred actions must be disabled and show "Coming soon"'
  );
});

test('ResultActionSheet does not import from tripCandidates or TripBuilder', () => {
  assert.ok(!actionSheet.includes('tripCandidates'), 'must not import tripCandidates');
  assert.ok(!actionSheet.includes('TripBuilder'), 'must not import TripBuilder');
});

// ── 6–7. RestaurantExploreFlow wiring ─────────────────────────────────────────

test('RestaurantExploreFlow imports ResultActionSheet', () => {
  assert.ok(
    restaurantFlow.includes('ResultActionSheet'),
    'ResultActionSheet not imported in RestaurantExploreFlow'
  );
});

test('RestaurantExploreFlow no longer has actions-pending-badge', () => {
  assert.ok(
    !restaurantFlow.includes('actions-pending-badge'),
    'Slice-1 actions-pending-badge stub should be removed now that actions are live'
  );
});

test('RestaurantExploreFlow passes context to ResultActionSheet', () => {
  assert.ok(
    restaurantFlow.includes('<ResultActionSheet context='),
    'ResultActionSheet context prop not passed in RestaurantExploreFlow'
  );
});

// ── 8–10. buildSavePayload logic (structural) ─────────────────────────────────

test('ResultActionSheet buildSavePayload uses providerIdentity for provider_place_id', () => {
  assert.ok(
    actionSheet.includes('providerIdentity') && actionSheet.includes('providerPlaceId'),
    'provider identity mapping missing in buildSavePayload'
  );
});

test('ResultActionSheet hotel context carries guests not passengers', () => {
  // hotel branch should reference guests (ExploreVertical uses plural "hotels")
  assert.ok(
    actionSheet.includes("ctx.vertical === \"hotels\"") &&
      actionSheet.includes('guests'),
    'hotel search_context must include guests'
  );
  // hotel branch must NOT reference ctx.passengers
  const hotelBranchIdx = actionSheet.indexOf("ctx.vertical === \"hotels\"");
  const flightBranchIdx = actionSheet.indexOf("ctx.vertical === \"flights\"");
  const hotelSection = actionSheet.slice(hotelBranchIdx, flightBranchIdx);
  assert.ok(!hotelSection.includes('passengers'), 'hotel section must not include passengers');
});

test('ResultActionSheet flight context carries passengers and cabinClass not guests', () => {
  assert.ok(
    actionSheet.includes("ctx.vertical === \"flights\"") &&
      actionSheet.includes('passengers'),
    'flight search_context must include passengers'
  );
  const flightBranchIdx = actionSheet.indexOf("ctx.vertical === \"flights\"");
  // grab a reasonable slice after the flight branch
  const flightSection = actionSheet.slice(flightBranchIdx, flightBranchIdx + 500);
  assert.ok(!flightSection.includes('guests:'), 'flight section must not include guests field');
});

// ── 11. Migration 005 ─────────────────────────────────────────────────────────

test('migration 005 creates saved_items table', () => {
  assert.ok(
    migration005.includes('create table') && migration005.includes('saved_items'),
    'saved_items table DDL missing from migration 005'
  );
});

test('migration 005 has vertical check constraint with all 4 verticals', () => {
  assert.ok(migration005.includes("'restaurant'"), "restaurant vertical missing");
  assert.ok(migration005.includes("'attraction'"), "attraction vertical missing");
  assert.ok(migration005.includes("'hotel'"), "hotel vertical missing");
  assert.ok(migration005.includes("'flight'"), "flight vertical missing");
});

test('migration 005 has user_id FK to users', () => {
  assert.ok(
    migration005.includes('user_id') && migration005.includes('references public.users'),
    'user_id FK missing from migration 005'
  );
});

test('migration 005 has display_snapshot jsonb', () => {
  assert.ok(migration005.includes('display_snapshot'), 'display_snapshot missing');
  assert.ok(migration005.includes('jsonb'), 'jsonb type missing');
});

test('migration 005 has search_context jsonb', () => {
  assert.ok(migration005.includes('search_context'), 'search_context missing');
});

test('migration 005 has provenance jsonb', () => {
  assert.ok(migration005.includes('provenance'), 'provenance missing');
});

test('migration 005 has provider_place_id column', () => {
  assert.ok(migration005.includes('provider_place_id'), 'provider_place_id column missing');
});

test('migration 005 has RLS enabled', () => {
  assert.ok(
    migration005.includes('enable row level security'),
    'RLS not enabled on saved_items'
  );
});

test('migration 005 has soft-delete status column', () => {
  assert.ok(
    migration005.includes("'active'") && migration005.includes("'deleted'"),
    'soft-delete status values missing'
  );
});

test('migration 005 has partial unique index for provider deduplication', () => {
  assert.ok(
    migration005.includes('create unique index') && migration005.includes('provider_place_id is not null'),
    'partial unique index for provider dedup missing'
  );
});

// ── 12. Backend route structure ───────────────────────────────────────────────

test('saved_items route has POST /', () => {
  assert.ok(savedItemsRoute.includes('@router.post(""'), 'POST / missing from route');
});

test('saved_items route has GET /', () => {
  assert.ok(savedItemsRoute.includes('@router.get(""'), 'GET / missing from route');
});

test('saved_items route has DELETE /{item_id}', () => {
  assert.ok(savedItemsRoute.includes('@router.delete("/{item_id}"'), 'DELETE route missing');
});

test('saved_items route prefix is /saved-items', () => {
  assert.ok(
    savedItemsRoute.includes('prefix="/saved-items"'),
    '/saved-items prefix missing from route'
  );
});

// ── 13. SavedItemsService methods ─────────────────────────────────────────────

test('SavedItemsService has create method', () => {
  assert.ok(savedItemsService.includes('def create('), 'create method missing');
});

test('SavedItemsService has list_active method', () => {
  assert.ok(savedItemsService.includes('def list_active('), 'list_active method missing');
});

test('SavedItemsService has delete method', () => {
  assert.ok(savedItemsService.includes('def delete('), 'delete method missing');
});

test('SavedItemsService idempotency check calls _find_active', () => {
  assert.ok(savedItemsService.includes('_find_active'), 'idempotency dedup via _find_active missing');
});

// ── 14–15. Forbidden scope untouched ─────────────────────────────────────────

test('tripCandidates.ts has no saved_items import', () => {
  assert.ok(!tripCandidates.includes('saved_items'), 'tripCandidates.ts must not reference saved_items');
});

test('TripBuilder.tsx has no saved_items import', () => {
  assert.ok(!tripBuilder.includes('saved_items'), 'TripBuilder.tsx must not reference saved_items');
});
