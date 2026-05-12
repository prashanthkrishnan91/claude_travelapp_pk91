/**
 * Saved → Trip Conversion — Stage 3 v2
 *
 * Focused structural tests verifying:
 * 1.  addSavedItemToTrip is exported from api.ts.
 * 2.  It posts to existing POST /itinerary/items (not day-scoped helpers).
 * 3.  It does NOT reuse createItem or addHotelToDay.
 * 4.  It guards against flights (unsupported vertical throws).
 * 5.  Hotel conversion mapping carries no rates, prices, or booking fields.
 * 6.  SavedShell imports addSavedItemToTrip and fetchTrips.
 * 7.  SavedShell has add-to-trip-btn (data-testid).
 * 8.  SavedShell has trip-picker (data-testid).
 * 9.  SavedShell has add-to-trip-success (data-testid).
 * 10. SavedShell has add-to-trip-error (data-testid).
 * 11. Flights vertical is excluded from trip conversion (canAddToTrip guard).
 * 12. No new /search/* calls or provider imports introduced.
 * 13. No TripBuilder or tripCandidates imports.
 * 14. Existing Stage 3 v1 tests still satisfied: remove, loading, empty, error.
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

const apiTs      = read('src/lib/api.ts');
const savedShell = read('src/components/saved/SavedShell.tsx');

// ── 1–3. addSavedItemToTrip in api.ts ────────────────────────────────────────

test('api.ts exports addSavedItemToTrip', () => {
  assert.ok(
    apiTs.includes('export async function addSavedItemToTrip'),
    'addSavedItemToTrip must be exported from api.ts'
  );
});

test('addSavedItemToTrip posts to /itinerary/items (not day-scoped path)', () => {
  const fnStart = apiTs.indexOf('export async function addSavedItemToTrip');
  const fnBody  = apiTs.slice(fnStart, fnStart + 2500);
  assert.ok(fnBody.includes('"/itinerary/items"'), 'must post to /itinerary/items');
  assert.ok(!fnBody.includes('`/itinerary/${'), 'must NOT use day-scoped route pattern');
});

test('addSavedItemToTrip does not delegate to createItem', () => {
  const fnStart = apiTs.indexOf('export async function addSavedItemToTrip');
  const fnBody  = apiTs.slice(fnStart, fnStart + 2500);
  assert.ok(!fnBody.includes('createItem('), 'must not call day-scoped createItem');
});

test('addSavedItemToTrip does not delegate to addHotelToDay', () => {
  const fnStart = apiTs.indexOf('export async function addSavedItemToTrip');
  const fnBody  = apiTs.slice(fnStart, fnStart + 2500);
  assert.ok(!fnBody.includes('addHotelToDay('), 'must not call addHotelToDay');
});

// ── 4. Flights guard ──────────────────────────────────────────────────────────

test('addSavedItemToTrip throws for unsupported verticals (e.g. flight)', () => {
  const fnStart = apiTs.indexOf('export async function addSavedItemToTrip');
  const fnBody  = apiTs.slice(fnStart, fnStart + 2500);
  assert.ok(fnBody.includes('throw new Error'), 'must throw for unsupported vertical');
  assert.ok(fnBody.includes('not supported'), 'error message must say not supported');
});

// ── 5. Hotel details — no rates/prices/booking ────────────────────────────────

test('addSavedItemToTrip hotel branch includes checkIn/checkOut/guests', () => {
  const fnStart = apiTs.indexOf('export async function addSavedItemToTrip');
  const fnBody  = apiTs.slice(fnStart, fnStart + 2500);
  assert.ok(fnBody.includes('checkIn'), 'hotel branch must include checkIn');
  assert.ok(fnBody.includes('checkOut'), 'hotel branch must include checkOut');
  assert.ok(fnBody.includes('guests'), 'hotel branch must include guests');
});

test('addSavedItemToTrip hotel branch does not include price_per_night', () => {
  const fnStart = apiTs.indexOf('export async function addSavedItemToTrip');
  const fnBody  = apiTs.slice(fnStart, fnStart + 2500);
  assert.ok(!fnBody.includes('price_per_night'), 'must not include price_per_night');
  assert.ok(!fnBody.includes('booking_url'), 'must not include booking_url');
  assert.ok(!fnBody.includes('totalPrice'), 'must not include totalPrice');
});

test('addSavedItemToTrip sets day_id to null / omits day_id (unscheduled candidate)', () => {
  const fnStart = apiTs.indexOf('export async function addSavedItemToTrip');
  const fnBody  = apiTs.slice(fnStart, fnStart + 2500);
  // day_id must not appear in the payload construction (we omit it for unscheduled)
  assert.ok(
    !fnBody.includes("day_id:") || fnBody.includes("day_id: null"),
    'day_id must be omitted or null (unscheduled candidate)'
  );
});

test('addSavedItemToTrip includes source:"saved_item" provenance in details', () => {
  const fnStart = apiTs.indexOf('export async function addSavedItemToTrip');
  const fnBody  = apiTs.slice(fnStart, fnStart + 2500);
  assert.ok(fnBody.includes('source'), 'details must include source provenance');
  assert.ok(fnBody.includes('savedItemId'), 'details must include savedItemId provenance');
});

// ── 6. SavedShell imports ─────────────────────────────────────────────────────

test('SavedShell imports addSavedItemToTrip', () => {
  assert.ok(savedShell.includes('addSavedItemToTrip'), 'SavedShell must import addSavedItemToTrip');
});

test('SavedShell imports fetchTrips', () => {
  assert.ok(savedShell.includes('fetchTrips'), 'SavedShell must import fetchTrips');
});

test('SavedShell loads trips in parallel with saved items', () => {
  assert.ok(
    savedShell.includes('Promise.all') && savedShell.includes('fetchTrips'),
    'SavedShell must load trips in parallel with saved items'
  );
});

// ── 7–10. Add-to-trip UI testids ──────────────────────────────────────────────

test('SavedShell has add-to-trip-btn (data-testid)', () => {
  assert.ok(savedShell.includes('add-to-trip-btn'), 'must have add-to-trip-btn testid');
});

test('SavedShell has trip-picker (data-testid)', () => {
  assert.ok(savedShell.includes('trip-picker'), 'must have trip-picker testid');
});

test('SavedShell has add-to-trip-success (data-testid)', () => {
  assert.ok(savedShell.includes('add-to-trip-success'), 'must have add-to-trip-success testid');
});

test('SavedShell has add-to-trip-error (data-testid)', () => {
  assert.ok(savedShell.includes('add-to-trip-error'), 'must have add-to-trip-error testid');
});

// ── 11. Flights guard in SavedShell ──────────────────────────────────────────

test('SavedShell guards flights vertical from Add to Trip (canAddToTrip)', () => {
  assert.ok(
    savedShell.includes('canAddToTrip') || savedShell.includes('"flight"'),
    'SavedShell must guard flights from Add to Trip'
  );
  assert.ok(
    savedShell.includes('!== "flight"') || savedShell.includes("!== 'flight'"),
    'flight vertical must be excluded from add-to-trip'
  );
});

// ── 12. No provider calls / search routes ────────────────────────────────────

test('SavedShell does not call any /search/* routes', () => {
  assert.ok(!savedShell.includes('/search/'), 'must not call any /search/* routes');
});

test('SavedShell does not import callConciergeSearch or searchRestaurants', () => {
  assert.ok(!savedShell.includes('callConciergeSearch'), 'must not import callConciergeSearch');
  assert.ok(!savedShell.includes('searchRestaurants'), 'must not import searchRestaurants');
});

// ── 13. Forbidden scope ───────────────────────────────────────────────────────

test('SavedShell does not import TripBuilder', () => {
  assert.ok(!savedShell.includes('TripBuilder'), 'must not import TripBuilder');
});

test('SavedShell does not import tripCandidates', () => {
  assert.ok(!savedShell.includes('tripCandidates'), 'must not import tripCandidates');
});

// ── 14. Stage 3 v1 invariants still hold ─────────────────────────────────────

test('SavedShell still has remove-saved-btn', () => {
  assert.ok(savedShell.includes('remove-saved-btn'), 'remove button must still exist');
});

test('SavedShell still has saved-loading state', () => {
  assert.ok(savedShell.includes('saved-loading'), 'loading state must still exist');
});

test('SavedShell still has saved-empty state with /explore link', () => {
  assert.ok(savedShell.includes('saved-empty'), 'empty state must still exist');
  const emptyIdx = savedShell.indexOf('saved-empty');
  const slice = savedShell.slice(emptyIdx, emptyIdx + 800);
  assert.ok(slice.includes('/explore'), 'empty state must still link to /explore');
});

test('SavedShell still has saved-error state', () => {
  assert.ok(savedShell.includes('saved-error'), 'error state must still exist');
});
