import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const tripBuilder = readFileSync(
  new URL('../src/components/trips/TripBuilder.tsx', import.meta.url),
  'utf8',
);
const apiClient = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url),
  'utf8',
);

test('TripBuilder waits for auth session before loading attractions/restaurants', () => {
  assert.match(tripBuilder, /authSessionReady/, 'authSessionReady state must exist to gate hydration');
  assert.match(tripBuilder, /supabase\.auth\.getSession\(\)/, 'TripBuilder must check current session on mount');
  assert.match(tripBuilder, /onAuthStateChange/, 'TripBuilder must subscribe to auth changes');
  assert.match(tripBuilder, /if \(!destination \|\| !authSessionReady\) return;/, 'Explore loaders must bail when auth is not ready');
});

test('TripBuilder hydration mapper preserves attraction and restaurant score fields from persisted snake_case/camelCase details', () => {
  assert.match(tripBuilder, /function normalizeExploreScore\(details: Record<string, unknown>\)/, 'TripBuilder should centralize explore score normalization');
  assert.match(tripBuilder, /if \(typeof details\.ai_score === "number"\) return details\.ai_score;/, 'Persisted ai_score should map into aiScore');
  assert.match(tripBuilder, /if \(typeof details\.score === "number"\) return details\.score;/, 'Persisted fallback score should map into aiScore');
  assert.match(tripBuilder, /typeof details\.num_reviews === "number" \? details\.num_reviews/, 'Persisted num_reviews should map for card details');
});

test('API search mappers preserve attraction and restaurant score fields from snake_case/camelCase/score payloads', () => {
  assert.match(apiClient, /typeof a\.ai_score === "number"/, 'Attractions mapper should support ai_score from backend payload');
  assert.match(apiClient, /typeof a\.score === "number"/, 'Attractions mapper should support legacy score field');
  assert.match(apiClient, /typeof r\.ai_score === "number"/, 'Restaurants mapper should support ai_score from backend payload');
  assert.match(apiClient, /typeof r\.score === "number"/, 'Restaurants mapper should support legacy score field');
});

test('TripBuilder existing-trip hydration still refreshes via provider search path', () => {
  assert.match(tripBuilder, /searchAttractions\(destination\)/, 'Attractions should be refreshed from provider-backed search path');
  assert.match(tripBuilder, /searchRestaurants\(destination\)/, 'Restaurants should be refreshed from provider-backed search path');
  assert.doesNotMatch(tripBuilder, /if \(candidateAttractions\.length > 0\) return;/, 'Existing in-memory candidates must not short-circuit provider hydration');
  assert.doesNotMatch(tripBuilder, /if \(candidateRestaurants\.length > 0\) return;/, 'Existing in-memory candidates must not short-circuit provider hydration');
});

test('TripBuilder does not render misleading score or Top Pick for zero/absent score', () => {
  assert.match(tripBuilder, /if \(typeof score !== "number" \|\| !Number\.isFinite\(score\) \|\| score <= 0\) return null;/, 'Score badge must be hidden for missing or zero score');
  assert.match(tripBuilder, /isTopPick=\{attractionSort === "ai" && idx < top20 && \(attraction\.aiScore \?\? 0\) > 0\}/, 'Attraction Top Pick requires positive score');
  assert.match(tripBuilder, /isTopPick=\{restaurantSort === "ai" && idx < top20 && \(restaurant\.aiScore \?\? 0\) > 0\}/, 'Restaurant Top Pick requires positive score');
});
