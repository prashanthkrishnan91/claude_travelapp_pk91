import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const apiTs = readFileSync(new URL('../src/lib/api.ts', import.meta.url), 'utf8');

test('restaurant mapper accepts google_place_id aliases as verified identity', () => {
  assert.match(apiTs, /google_place_id\?: string/);
  assert.match(apiTs, /googlePlaceId\?: string/);
  assert.match(apiTs, /providerPlaceId:\s*providerPlaceId \?\? googlePlaceId/);
  assert.match(apiTs, /placeId:\s*placeId \?\? googlePlaceId/);
});

test('restaurant mapper preserves verified google fields through snapshot hydration aliases', () => {
  assert.match(apiTs, /formatted_address\?: string/);
  assert.match(apiTs, /user_ratings_total\?: number/);
  assert.match(apiTs, /review_count\?: number/);
  assert.match(apiTs, /r\.formattedAddress \?\? r\.formatted_address/);
  assert.match(apiTs, /r\.userRatingsTotal/);
  assert.match(apiTs, /r\.user_ratings_total/);
});

test('explore restaurant trust gate still requires verified place identity fields', () => {
  assert.match(apiTs, /\.filter\(\(r\) => Boolean\(r\.googleMapsUri \|\| r\.providerPlaceId \|\| r\.placeId\)\)/);
  assert.match(apiTs, /if \(!googleMapsUri && !providerPlaceId && !placeId\) return null/);
});
