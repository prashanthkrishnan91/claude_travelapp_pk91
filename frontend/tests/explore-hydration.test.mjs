import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const tripBuilder = readFileSync(
  new URL('../src/components/trips/TripBuilder.tsx', import.meta.url),
  'utf8',
);

test('TripBuilder waits for auth session before loading attractions/restaurants', () => {
  assert.match(tripBuilder, /authSessionReady/, 'authSessionReady state must exist to gate hydration');
  assert.match(tripBuilder, /supabase\.auth\.getSession\(\)/, 'TripBuilder must check current session on mount');
  assert.match(tripBuilder, /onAuthStateChange/, 'TripBuilder must subscribe to auth changes');
  assert.match(tripBuilder, /if \(!destination \|\| !authSessionReady\) return;/, 'Explore loaders must bail when auth is not ready');
});

test('TripBuilder hydrates attraction/restaurant candidates from persisted trip-level itinerary items first', () => {
  assert.match(tripBuilder, /filter\(\(i\) => i\.itemType === "activity" && !i\.dayId\)/, 'Must read trip-level activity items before provider search');
  assert.match(tripBuilder, /filter\(\(i\) => i\.itemType === "meal" && !i\.dayId\)/, 'Must read trip-level meal items before provider search');
  assert.match(tripBuilder, /setCandidateAttractions\(persistedAttractions\)/, 'Persisted attractions must be mapped into rendered candidateAttractions state');
  assert.match(tripBuilder, /setCandidateRestaurants\(persistedRestaurants\)/, 'Persisted restaurants must be mapped into rendered candidateRestaurants state');
});

test('TripBuilder avoids duplicate provider-backed attraction/restaurant calls for same trip+destination', () => {
  assert.match(tripBuilder, /attractionsHydrationKeyRef/, 'Attractions hydration key cache must exist');
  assert.match(tripBuilder, /restaurantsHydrationKeyRef/, 'Restaurants hydration key cache must exist');
  assert.match(tripBuilder, /if \(candidateAttractions\.length > 0\) return;/, 'Must skip attractions provider call when already hydrated');
  assert.match(tripBuilder, /if \(candidateRestaurants\.length > 0\) return;/, 'Must skip restaurants provider call when already hydrated');
});
