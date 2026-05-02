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
