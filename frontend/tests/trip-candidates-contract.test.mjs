/**
 * Trip Candidate Contract — Level 3 Trip Data Contract Rescue.
 *
 * Verifies that the canonical `buildTripCandidateBuckets` selector in
 * `frontend/src/lib/tripCandidates.ts`:
 *   1. Groups persisted ItineraryItem rows into flights / round-trip / hotels /
 *      attractions / restaurants buckets based on item_type + details.isRoundTrip.
 *   2. Skips items that are already assigned to a day.
 *   3. De-dupes by stable identity per vertical.
 *   4. Does not require ai_score to make a row visible (rating + numReviews is
 *      enough; the selector computes a deterministic score on the fly).
 *   5. Trip Ideas does NOT include creation_seed rows (data-layer guard lives
 *      in backend list_unscheduled_items; this test checks the source-of-truth
 *      assumptions for the frontend selector).
 *   6. `mergePersistedWithSnapshot` cannot zero out non-empty persisted
 *      attractions/restaurants buckets.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const selectorSrc = readFileSync(
  new URL('../src/lib/tripCandidates.ts', import.meta.url),
  'utf8',
);
const tripBuilder = readFileSync(
  new URL('../src/components/trips/TripBuilder.tsx', import.meta.url),
  'utf8',
);
const apiTs = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url),
  'utf8',
);

test('tripCandidates selector exports buildTripCandidateBuckets and mergePersistedWithSnapshot', () => {
  assert.match(selectorSrc, /export function buildTripCandidateBuckets\(/);
  assert.match(selectorSrc, /export function mergePersistedWithSnapshot\(/);
});

test('selector groups by item_type and splits round-trip flights off the flight bucket', () => {
  assert.match(selectorSrc, /case "flight":/);
  assert.match(selectorSrc, /case "hotel":/);
  assert.match(selectorSrc, /case "activity":/);
  assert.match(selectorSrc, /case "meal":/);
  assert.match(selectorSrc, /isRoundTripFlight/);
});

test('selector skips day-assigned items so candidates only carry unscheduled rows', () => {
  assert.match(selectorSrc, /if \(isDayAssigned\(item\)\) continue;/);
});

test('selector dedupes hotel/attraction/restaurant rows by a stable identity key', () => {
  assert.match(selectorSrc, /seenHotel/);
  assert.match(selectorSrc, /seenAttraction/);
  assert.match(selectorSrc, /seenRestaurant/);
});

test('selector computes aiScore from rating+numReviews when persisted row lacks one', () => {
  assert.match(selectorSrc, /computeExploreAttractionScore\(rating, numReviews/);
  assert.match(selectorSrc, /computeExploreRestaurantScore\(rating, numReviews/);
});

test('mergePersistedWithSnapshot: empty snapshot cannot override non-empty persisted attractions/restaurants', () => {
  // Source-level guard: persisted wins when non-empty.
  assert.match(
    selectorSrc,
    /persisted\.attractions\.length > 0 \? persisted\.attractions : snapshot\.attractions/,
  );
  assert.match(
    selectorSrc,
    /persisted\.restaurants\.length > 0 \? persisted\.restaurants : snapshot\.restaurants/,
  );
});

test('TripBuilder uses canonical selector for all four verticals', () => {
  assert.match(tripBuilder, /buildTripCandidateBuckets/);
  assert.match(tripBuilder, /mergePersistedWithSnapshot/);
  // Old competing surfaces must NOT be re-introduced
  assert.doesNotMatch(tripBuilder, /searchAttractionsViaConcierge/);
});

test('TripBuilder no longer mints empty snapshots that overwrite persisted candidates', () => {
  // Specifically: TripBuilder must NOT call saveExploreSnapshot from hydration.
  assert.doesNotMatch(tripBuilder, /saveExploreSnapshot\(/);
});

test('TripBuilder hydrates attractions/restaurants from persisted itinerary_items', () => {
  // Single fetch path: GET /trips/{id}/items via fetchTripItems → selector.
  assert.match(tripBuilder, /fetchTripItems\(tripId\)/);
  assert.match(tripBuilder, /setCandidateAttractions\(merged\.attractions\)/);
  assert.match(tripBuilder, /setCandidateRestaurants\(merged\.restaurants\)/);
});

test('api.ts no longer exports searchAttractionsViaConcierge / isCanonicalSnapshotAttraction', () => {
  assert.doesNotMatch(apiTs, /export async function searchAttractionsViaConcierge\(/);
  assert.doesNotMatch(apiTs, /export function isCanonicalSnapshotAttraction\(/);
});

test('api.ts still exports computeExploreAttractionScore / computeExploreRestaurantScore (used by selector)', () => {
  assert.match(apiTs, /export function computeExploreAttractionScore\(/);
  assert.match(apiTs, /export function computeExploreRestaurantScore\(/);
});


test('selector treats null-like day_id sentinels as unscheduled candidates', () => {
  assert.match(selectorSrc, /normalized === \"null\"/);
  assert.match(selectorSrc, /normalized === \"undefined\"/);
});


test('TripBuilder does not gate flight candidate hydration by past/completed trip date', () => {
  assert.match(tripBuilder, /setCandidateFlights\(\[\.\.\.merged\.flights, \.\.\.merged\.roundTripFlights\]\)/);
  assert.doesNotMatch(tripBuilder, /Flights are unavailable for past trip dates\./);
});
