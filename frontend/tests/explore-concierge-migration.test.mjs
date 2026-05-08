// Product Surface Migration v1B — TripBuilder Explore canonical migration.
//
// Asserts that:
//   1. TripBuilder.tsx no longer calls the legacy mock-backed
//      /search/attractions, /search/clusters, /search/best-area routes
//      (or their typed wrappers `searchAttractions`, `searchClusters`,
//      `fetchBestArea`, `planClusterDay`).
//   2. TripBuilder.tsx routes Explore attraction discovery through the
//      canonical /ai/concierge/search surface via
//      `searchAttractionsViaConcierge(tripId, destination)`.
//   3. The api.ts adapter `mapUnifiedAttractionToResult(...)` preserves the
//      fields needed by the existing Add to Day / Save / Maps handlers
//      (id, name, address, location, rating, numReviews, aiScore, tags,
//      bookingUrl, lat, lng) and gates on canonical Google verification +
//      `display.addability === "addable"` so non-addable / unverified
//      Concierge cards never surface in Explore.
//   4. The legacy mock-backed wrappers and types have been removed from
//      api.ts (no `export async function searchAttractions`,
//      `searchClusters`, `fetchBestArea`, `planClusterDay`).
//   5. The grouped/Areas view and BestAreaCard have been removed from
//      TripBuilder.tsx so partial-mock cluster / best-area data cannot
//      reappear in user-facing Explore.

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

test('TripBuilder Explore no longer references the legacy mock-backed product routes', () => {
  // No direct route references.
  assert.doesNotMatch(tripBuilder, /['"]\/search\/attractions['"]/, 'No /search/attractions string literal');
  assert.doesNotMatch(tripBuilder, /['"]\/search\/clusters['"]/, 'No /search/clusters string literal');
  assert.doesNotMatch(tripBuilder, /['"]\/search\/best-area['"]/, 'No /search/best-area string literal');
  // No typed wrappers either.
  assert.doesNotMatch(tripBuilder, /\bsearchAttractions\(/, 'No call to legacy searchAttractions');
  assert.doesNotMatch(tripBuilder, /\bsearchClusters\(/, 'No call to legacy searchClusters');
  assert.doesNotMatch(tripBuilder, /\bfetchBestArea\(/, 'No call to legacy fetchBestArea');
  assert.doesNotMatch(tripBuilder, /\bplanClusterDay\(/, 'No call to legacy planClusterDay');
});

test('TripBuilder Explore routes attraction discovery through the canonical AI Concierge surface', () => {
  assert.match(apiClient, /export async function searchAttractionsViaConcierge\(/, 'api.ts exports searchAttractionsViaConcierge');
  assert.match(tripBuilder, /searchAttractionsViaConcierge\b/, 'TripBuilder imports the canonical helper');
  assert.match(tripBuilder, /searchAttractionsViaConcierge\(tripId, destination\)/, 'TripBuilder calls the canonical helper with tripId + destination');
});

test('Canonical helper goes through /ai/concierge/search and is gated on addability + provider id', () => {
  assert.match(apiClient, /callConciergeSearch\(tripId, `Top attractions in \$\{dest\}`\)/, 'searchAttractionsViaConcierge delegates to callConciergeSearch');
  assert.match(apiClient, /["']\/ai\/concierge\/search["']/, 'The canonical /ai/concierge/search route is the only Concierge search seam');
  // Fail-closed gates.
  assert.match(apiClient, /addability && addability !== "addable"/, 'Adapter drops cards whose addability is not "addable"');
  assert.match(apiClient, /if \(!providerPlaceId\) return null;/, 'Adapter drops cards without a Google Places provider id');
});

test('Canonical adapter preserves fields needed by Add to Day / Save / Maps', () => {
  // The fields below must appear in the returned object so the existing
  // addAttractionToDay / addAttractionToTrip / Maps handlers keep working
  // without a schema change to the persisted itinerary item.
  const requiredKeys = [
    'id:',
    'name,',
    'category:',
    'description,',
    'location:',
    'address,',
    'rating,',
    'numReviews,',
    'aiScore:',
    'tags:',
    'bookingUrl: mapsUri',
    'lat:',
    'lng:',
  ];
  for (const key of requiredKeys) {
    assert.ok(apiClient.includes(key), `Adapter must include "${key}" — needed for downstream handlers`);
  }
  // Maps URI must come from googleVerification when present, falling back to
  // a deterministic place_id deep link.
  assert.match(apiClient, /gv\?\.googleMapsUri/, 'Adapter sources mapsUri from googleVerification.googleMapsUri first');
  assert.match(apiClient, /place_id:\$\{encodeURIComponent\(providerPlaceId\)\}/, 'Adapter falls back to a place_id-based Google Maps deep link');
});

test('Legacy mock-backed wrappers have been removed from api.ts', () => {
  assert.doesNotMatch(apiClient, /export async function searchAttractions\b/, 'searchAttractions wrapper removed');
  assert.doesNotMatch(apiClient, /export async function searchClusters\b/, 'searchClusters wrapper removed');
  assert.doesNotMatch(apiClient, /export async function fetchBestArea\b/, 'fetchBestArea wrapper removed');
  assert.doesNotMatch(apiClient, /export async function planClusterDay\b/, 'planClusterDay wrapper removed');
  assert.doesNotMatch(apiClient, /["']\/search\/attractions["']/, 'No /search/attractions literal in api.ts');
  assert.doesNotMatch(apiClient, /["']\/search\/clusters["']/, 'No /search/clusters literal in api.ts');
  assert.doesNotMatch(apiClient, /["']\/search\/best-area["']/, 'No /search/best-area literal in api.ts');
});

test('Grouped / Areas view and BestAreaCard are removed so partial-mock data cannot resurface', () => {
  assert.doesNotMatch(tripBuilder, /viewMode === "grouped"/, 'Grouped view branch removed');
  assert.doesNotMatch(tripBuilder, /setViewMode\("grouped"\)/, 'Grouped view button removed');
  assert.doesNotMatch(tripBuilder, /function BestAreaCard/, 'BestAreaCard component removed');
  assert.doesNotMatch(tripBuilder, /<BestAreaCard\b/, 'BestAreaCard render removed');
  // TripMapView must still work, but `bestArea` is no longer hydrated from a
  // mock-backed source — the prop is intentionally null.
  assert.match(tripBuilder, /bestArea=\{null\}/, 'TripMapView is passed bestArea={null} (fail closed)');
});
