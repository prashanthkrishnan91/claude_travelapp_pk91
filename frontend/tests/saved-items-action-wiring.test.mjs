/**
 * Saved Items & ResultActionSheet — Stage 2A Slice 2 (patched)
 *
 * Focused structural tests verifying:
 * 1. SavedItem / SavedItemCreate types are exported from @/types.
 * 2. SavedItemCreate and SavedItem include providerItemId (flight/non-place identity).
 * 3. saveItem / listSavedItems / deleteSavedItem are exported from api.ts.
 * 4. ResultActionSheet component exists and exports the named export.
 * 5. ResultActionSheet renders save-action-btn and deferred Add/Create actions.
 * 6. RestaurantExploreFlow imports ResultActionSheet; no Slice-1 stub.
 * 7. buildSavePayload: hotel sets guests + rooms (not passengers); flight sets passengers (not guests).
 * 8. ExploreResultContext includes rooms field.
 * 9. backend migration 005: provider_item_id column + item_identity unique index.
 * 10. migration 005: place_identity index still present.
 * 11. saved_items route uses SavedItemVertical type for vertical query param.
 * 12. SavedItemsService has create/list_active/delete + both _find_by_place/_find_by_item.
 * 13. tripCandidates.ts and TripBuilder.tsx are untouched.
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
const exploreTypes = read('src/components/explore/types.ts');
const restaurantFlow = read('src/components/explore/RestaurantExploreFlow.tsx');
const migration005 = read('../backend/db/migrations/005_saved_items.sql');
const savedItemsRoute = read('../backend/app/routes/saved_items.py');
const savedItemsService = read('../backend/app/services/saved_items.py');
const savedItemsModel = read('../backend/app/models/saved_items.py');
const tripCandidates = read('src/lib/tripCandidates.ts');
const tripBuilder = read('src/components/trips/TripBuilder.tsx');

// ── 1. Core type exports ──────────────────────────────────────────────────────

test('types/index.ts exports SavedItemVertical', () => {
  assert.ok(typesIndex.includes('SavedItemVertical'), 'SavedItemVertical missing');
});

test('types/index.ts exports SavedItemCreate', () => {
  assert.ok(typesIndex.includes('SavedItemCreate'), 'SavedItemCreate missing');
});

test('types/index.ts exports SavedItem interface', () => {
  assert.ok(typesIndex.includes('export interface SavedItem'), 'SavedItem interface missing');
});

test('SavedItem has core identity fields', () => {
  assert.ok(typesIndex.includes('userId'), 'userId missing');
  assert.ok(typesIndex.includes('displayName'), 'displayName missing');
  assert.ok(typesIndex.includes('displaySnapshot'), 'displaySnapshot missing');
  assert.ok(typesIndex.includes('searchContext'), 'searchContext missing');
  assert.ok(typesIndex.includes('provenance'), 'provenance missing');
});

// ── 2. providerItemId in types ────────────────────────────────────────────────

test('SavedItemCreate has providerItemId (flight/non-place identity)', () => {
  assert.ok(typesIndex.includes('providerItemId'), 'providerItemId missing from SavedItemCreate/SavedItem');
});

test('SavedItem has providerItemId', () => {
  const savedItemBlock = typesIndex.slice(typesIndex.indexOf('export interface SavedItem'));
  assert.ok(savedItemBlock.includes('providerItemId'), 'providerItemId missing from SavedItem interface');
});

// ── 3. API helper exports ─────────────────────────────────────────────────────

test('api.ts exports saveItem', () => {
  assert.ok(apiTs.includes('export async function saveItem'), 'saveItem missing from api.ts');
});

test('api.ts exports listSavedItems', () => {
  assert.ok(apiTs.includes('export async function listSavedItems'), 'listSavedItems missing');
});

test('api.ts exports deleteSavedItem', () => {
  assert.ok(apiTs.includes('export async function deleteSavedItem'), 'deleteSavedItem missing');
});

test('api.ts saveItem calls /saved-items POST', () => {
  assert.ok(apiTs.includes('"/saved-items"'), '/saved-items endpoint missing');
});

test('api.ts deleteSavedItem uses item id in URL', () => {
  assert.ok(apiTs.includes('`/saved-items/${itemId}`'), 'deleteSavedItem URL pattern missing');
});

// ── 4–5. ResultActionSheet structure ─────────────────────────────────────────

test('ResultActionSheet exports ResultActionSheet', () => {
  assert.ok(actionSheet.includes('export function ResultActionSheet'), 'ResultActionSheet not exported');
});

test('ResultActionSheet renders save-action-btn', () => {
  assert.ok(actionSheet.includes('data-testid="save-action-btn"'), 'save-action-btn missing');
});

test('ResultActionSheet renders more-actions-toggle', () => {
  assert.ok(actionSheet.includes('data-testid="more-actions-toggle"'), 'more-actions-toggle missing');
});

test('ResultActionSheet no longer renders deferred add-to-trip-btn', () => {
  assert.ok(!actionSheet.includes('data-testid="add-to-trip-btn"'), 'stale add-to-trip-btn must be removed');
});

test('ResultActionSheet no longer renders deferred create-trip-btn', () => {
  assert.ok(!actionSheet.includes('data-testid="create-trip-btn"'), 'stale create-trip-btn must be removed');
});

test('ResultActionSheet does not render "Coming soon" copy', () => {
  assert.ok(!actionSheet.includes('Coming soon'), 'stale Coming soon copy must be removed');
});

test('ResultActionSheet exposes save-first guidance and Manage-in-Saved link', () => {
  assert.ok(actionSheet.includes('data-testid="save-first-hint"'), 'save-first-hint missing');
  assert.ok(actionSheet.includes('data-testid="manage-in-saved-link"'), 'manage-in-saved-link missing');
  assert.ok(actionSheet.includes('href="/saved"'), 'Manage link must point to /saved');
});

test('ResultActionSheet does not import tripCandidates or TripBuilder', () => {
  assert.ok(!actionSheet.includes('tripCandidates'), 'must not import tripCandidates');
  assert.ok(!actionSheet.includes('TripBuilder'), 'must not import TripBuilder');
});

// ── 6. RestaurantExploreFlow wiring ──────────────────────────────────────────

test('RestaurantExploreFlow imports ResultActionSheet', () => {
  assert.ok(restaurantFlow.includes('ResultActionSheet'), 'ResultActionSheet not in RestaurantExploreFlow');
});

test('RestaurantExploreFlow no longer has actions-pending-badge', () => {
  assert.ok(!restaurantFlow.includes('actions-pending-badge'), 'Slice-1 stub must be removed');
});

test('RestaurantExploreFlow passes context to ResultActionSheet', () => {
  assert.ok(restaurantFlow.includes('<ResultActionSheet context='), 'context prop not passed');
});

// ── 7. hotel/flight search_context separation ─────────────────────────────────

test('ResultActionSheet hotel branch uses "hotels" vertical and includes guests', () => {
  assert.ok(
    actionSheet.includes('ctx.vertical === "hotels"') && actionSheet.includes('guests'),
    'hotel branch must check hotels vertical and include guests'
  );
});

test('ResultActionSheet hotel branch includes rooms', () => {
  const hotelIdx = actionSheet.indexOf('ctx.vertical === "hotels"');
  const flightIdx = actionSheet.indexOf('ctx.vertical === "flights"');
  const hotelSection = actionSheet.slice(hotelIdx, flightIdx);
  assert.ok(hotelSection.includes('rooms'), 'hotel section must include rooms');
  assert.ok(!hotelSection.includes('passengers'), 'hotel section must not include passengers');
});

test('ResultActionSheet flight branch uses "flights" vertical and includes passengers', () => {
  assert.ok(
    actionSheet.includes('ctx.vertical === "flights"') && actionSheet.includes('passengers'),
    'flight branch must check flights vertical and include passengers'
  );
});

test('ResultActionSheet flight branch does not include guests', () => {
  const flightIdx = actionSheet.indexOf('ctx.vertical === "flights"');
  const flightSection = actionSheet.slice(flightIdx, flightIdx + 600);
  assert.ok(!flightSection.includes('guests:'), 'flight section must not include guests field');
});

// ── 8. ExploreResultContext rooms field ───────────────────────────────────────

test('ExploreResultContext has rooms field', () => {
  assert.ok(exploreTypes.includes('rooms'), 'rooms field missing from ExploreResultContext');
});

test('ExploreResultContext rooms is separate from passengers', () => {
  assert.ok(
    exploreTypes.includes('guests') && exploreTypes.includes('rooms') && exploreTypes.includes('passengers'),
    'guests, rooms, and passengers must all be distinct fields'
  );
});

// ── 9–10. Migration 005 schema ────────────────────────────────────────────────

test('migration 005 creates saved_items table', () => {
  assert.ok(migration005.includes('create table') && migration005.includes('saved_items'), 'table DDL missing');
});

test('migration 005 has all 4 verticals', () => {
  assert.ok(migration005.includes("'restaurant'"), 'restaurant missing');
  assert.ok(migration005.includes("'attraction'"), 'attraction missing');
  assert.ok(migration005.includes("'hotel'"), 'hotel missing');
  assert.ok(migration005.includes("'flight'"), 'flight missing');
});

test('migration 005 has provider_place_id column', () => {
  assert.ok(migration005.includes('provider_place_id'), 'provider_place_id column missing');
});

test('migration 005 has provider_item_id column', () => {
  assert.ok(migration005.includes('provider_item_id'), 'provider_item_id column missing — flight identity needs this');
});

test('migration 005 has place-based unique index (saved_items_place_identity_uq)', () => {
  assert.ok(
    migration005.includes('saved_items_place_identity_uq'),
    'place identity unique index missing'
  );
});

test('migration 005 has item-based unique index (saved_items_item_identity_uq)', () => {
  assert.ok(
    migration005.includes('saved_items_item_identity_uq'),
    'item identity unique index missing — flights need a non-place dedup path'
  );
});

test('migration 005 has user_id FK', () => {
  assert.ok(migration005.includes('user_id') && migration005.includes('references public.users'), 'user_id FK missing');
});

test('migration 005 has display_snapshot jsonb', () => {
  assert.ok(migration005.includes('display_snapshot') && migration005.includes('jsonb'), 'display_snapshot jsonb missing');
});

test('migration 005 has search_context jsonb', () => {
  assert.ok(migration005.includes('search_context'), 'search_context missing');
});

test('migration 005 has provenance jsonb', () => {
  assert.ok(migration005.includes('provenance'), 'provenance missing');
});

test('migration 005 has RLS enabled', () => {
  assert.ok(migration005.includes('enable row level security'), 'RLS not enabled');
});

test('migration 005 has soft-delete status', () => {
  assert.ok(migration005.includes("'active'") && migration005.includes("'deleted'"), 'soft-delete status missing');
});

// ── 11. Route type safety ─────────────────────────────────────────────────────

test('saved_items route has POST /', () => {
  assert.ok(savedItemsRoute.includes('@router.post(""'), 'POST / missing');
});

test('saved_items route has GET /', () => {
  assert.ok(savedItemsRoute.includes('@router.get(""'), 'GET / missing');
});

test('saved_items route has DELETE /{item_id}', () => {
  assert.ok(savedItemsRoute.includes('@router.delete("/{item_id}"'), 'DELETE route missing');
});

test('saved_items route uses SavedItemVertical type for vertical query param', () => {
  assert.ok(
    savedItemsRoute.includes('SavedItemVertical'),
    'vertical query param must use SavedItemVertical type, not Optional[str]'
  );
});

// ── 12. SavedItemsService methods ─────────────────────────────────────────────

test('SavedItemsService has create method', () => {
  assert.ok(savedItemsService.includes('def create('), 'create method missing');
});

test('SavedItemsService has list_active method', () => {
  assert.ok(savedItemsService.includes('def list_active('), 'list_active method missing');
});

test('SavedItemsService has delete method', () => {
  assert.ok(savedItemsService.includes('def delete('), 'delete method missing');
});

test('SavedItemsService has _find_by_place for Google Places dedup', () => {
  assert.ok(savedItemsService.includes('_find_by_place'), '_find_by_place missing');
});

test('SavedItemsService has _find_by_item for flight/non-place dedup', () => {
  assert.ok(savedItemsService.includes('_find_by_item'), '_find_by_item missing — flight dedup needs this');
});

test('Pydantic model uses Field(default_factory=dict) not mutable defaults', () => {
  assert.ok(
    savedItemsModel.includes('Field(default_factory=dict)'),
    'mutable dict defaults must use Field(default_factory=dict)'
  );
});

// ── 14. Explore → Saved routeable metadata gap (upstream-to-trip handoff audit) ─

test('buildSavePayload writes lat from ctx.location into displaySnapshot', () => {
  const snapshotStart = actionSheet.indexOf('const displaySnapshot');
  const snapshotEnd = actionSheet.indexOf('let searchContext', snapshotStart);
  const snapshotBlock = actionSheet.slice(snapshotStart, snapshotEnd);
  assert.ok(
    snapshotBlock.includes('ctx.location?.lat') || snapshotBlock.includes('ctx.location.lat'),
    'lat from ctx.location not written into displaySnapshot'
  );
});

test('buildSavePayload writes lng from ctx.location into displaySnapshot', () => {
  const snapshotStart = actionSheet.indexOf('const displaySnapshot');
  const snapshotEnd = actionSheet.indexOf('let searchContext', snapshotStart);
  const snapshotBlock = actionSheet.slice(snapshotStart, snapshotEnd);
  assert.ok(
    snapshotBlock.includes('ctx.location?.lng') || snapshotBlock.includes('ctx.location.lng'),
    'lng from ctx.location not written into displaySnapshot'
  );
});

test('buildSavePayload writes providerPlaceId (from ctx.providerIdentity) into displaySnapshot', () => {
  const snapshotStart = actionSheet.indexOf('const displaySnapshot');
  const snapshotEnd = actionSheet.indexOf('let searchContext', snapshotStart);
  const snapshotBlock = actionSheet.slice(snapshotStart, snapshotEnd);
  assert.ok(
    snapshotBlock.includes('providerPlaceId'),
    'providerPlaceId not written into displaySnapshot'
  );
});

test('buildSavePayload providerPlaceId is gated on non-empty string — empty/undefined providerIdentity not written', () => {
  const snapshotStart = actionSheet.indexOf('const displaySnapshot');
  const snapshotEnd = actionSheet.indexOf('let searchContext', snapshotStart);
  const snapshotBlock = actionSheet.slice(snapshotStart, snapshotEnd);
  // Guard must check both type and truthiness (non-empty string)
  assert.ok(
    snapshotBlock.includes('typeof ctx.providerIdentity === "string"') &&
    snapshotBlock.includes('ctx.providerIdentity'),
    'providerPlaceId must be gated on typeof string && truthy (non-empty)'
  );
});

test('buildSavePayload lat/lng are gated — not written when ctx.location is absent', () => {
  // Guard must be a type check, not an unconditional spread
  const snapshotStart = actionSheet.indexOf('const displaySnapshot');
  const snapshotEnd = actionSheet.indexOf('let searchContext', snapshotStart);
  const snapshotBlock = actionSheet.slice(snapshotStart, snapshotEnd);
  assert.ok(
    snapshotBlock.includes('typeof ctx.location') || snapshotBlock.includes('ctx.location?.lat'),
    'lat/lng must be conditionally written — guard missing'
  );
});

// ── 13. Forbidden scope ───────────────────────────────────────────────────────

test('tripCandidates.ts has no saved_items reference', () => {
  assert.ok(!tripCandidates.includes('saved_items'), 'tripCandidates.ts must not reference saved_items');
});

test('TripBuilder.tsx has no saved_items reference', () => {
  assert.ok(!tripBuilder.includes('saved_items'), 'TripBuilder.tsx must not reference saved_items');
});
