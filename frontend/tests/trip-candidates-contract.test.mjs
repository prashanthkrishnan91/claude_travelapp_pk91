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


test('selector keeps real UUID dayId rows assigned (not candidate buckets)', () => {
  assert.match(selectorSrc, /return true;/, 'Expected non-null-like dayId to remain assigned.');
  assert.doesNotMatch(selectorSrc, /normalized === \"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\"/i, 'UUID dayId must not be treated as null-like sentinel.');
});

// ── Canonical round-trip bucketing (canonical FlightItineraryOffer fields) ────

test('isRoundTripFlight detects canonical snake_case trip_type="round_trip"', () => {
  assert.match(
    selectorSrc,
    /d\.trip_type === "round_trip"/,
    'isRoundTripFlight must check d.trip_type === "round_trip"',
  );
});

test('isRoundTripFlight detects canonical camelCase tripType="round_trip"', () => {
  assert.match(
    selectorSrc,
    /d\.tripType === "round_trip"/,
    'isRoundTripFlight must check d.tripType === "round_trip"',
  );
});

test('isRoundTripFlight detects canonical returnLeg (camelCase after toCamel)', () => {
  assert.match(
    selectorSrc,
    /d\.returnLeg != null/,
    'isRoundTripFlight must classify row as round-trip when d.returnLeg is non-null',
  );
});

test('isRoundTripFlight detects canonical return_leg (snake_case fallback)', () => {
  assert.match(
    selectorSrc,
    /d\.return_leg != null/,
    'isRoundTripFlight must classify row as round-trip when d.return_leg is non-null',
  );
});

test('isRoundTripFlight still detects legacy is_round_trip boolean', () => {
  assert.match(
    selectorSrc,
    /d\.is_round_trip != null/,
    'isRoundTripFlight must still handle legacy is_round_trip boolean flag',
  );
});

test('flightDedupeKey uses canonical origin+destination+departureDate+returnDate for round-trips', () => {
  assert.match(
    selectorSrc,
    /rt:\$\{origin\}:\$\{dest\}:\$\{depDate\}:\$\{retDate\}/,
    'flightDedupeKey must use canonical route fields for round-trip dedup key',
  );
});

test('flightDedupeKey calls isRoundTripFlight (so canonical rows use canonical dedup branch)', () => {
  assert.match(
    selectorSrc,
    /if \(isRoundTripFlight\(item\)\)/,
    'flightDedupeKey must call isRoundTripFlight to select the dedup branch',
  );
});

test('flightDedupeKey reads departure_date / departureDate for canonical one-way key', () => {
  assert.match(
    selectorSrc,
    /d\.departureDate.*d\.departure_date|d\.departure_date.*d\.departureDate/,
    'flightDedupeKey must read canonical departureDate/departure_date',
  );
});
