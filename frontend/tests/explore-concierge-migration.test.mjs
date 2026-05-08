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
  assert.match(apiClient, /if \(addability !== "addable"\) return null;/, 'Adapter drops cards unless addability is exactly "addable"');
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

// ── Blocker 2 follow-up: addability must be present and equal to "addable" ──

test('Adapter requires display.addability === "addable" (missing addability returns null)', () => {
  // The adapter must require the canonical display contract; a Concierge
  // card with no display block has not been normalized through the v1B/PR-287
  // seam and must not surface in Explore even if a provider id is present.
  assert.match(apiClient, /if \(addability !== "addable"\) return null;/, 'Adapter strictly requires addability === "addable"');
  assert.doesNotMatch(apiClient, /if \(addability && addability !== "addable"\) return null;/, 'Soft check (allowing missing addability) must not exist');
});

// ── Blocker 1 follow-up: snapshot canonical-identity guard ───────────────────

test('api.ts exports isCanonicalSnapshotAttraction with the v1B identity rules', () => {
  assert.match(apiClient, /export function isCanonicalSnapshotAttraction\(/, 'Snapshot guard helper must be exported');
  // Identity rules: reject mock-shaped ids and require a Google-Maps / place_id URL.
  assert.match(apiClient, /id\.startsWith\("mock-"\)/, 'Snapshot guard rejects mock- prefixed ids');
  assert.match(apiClient, /id\.startsWith\("attr-"\)/, 'Snapshot guard rejects legacy attr- prefixed ids');
  assert.match(apiClient, /url\.includes\("google\.com\/maps"\)/, 'Snapshot guard accepts googleMapsUri-shaped urls');
  assert.match(apiClient, /url\.includes\("place_id:"\)/, 'Snapshot guard accepts place_id deep-link urls');
});

test('TripBuilder Explore filters snapshot attractions through the canonical guard before reuse', () => {
  // The snapshot may contain rows minted by the legacy mock-backed
  // /search/attractions surface before this migration.  TripBuilder must
  // discard non-canonical rows and trigger a canonical refetch.
  assert.match(tripBuilder, /isCanonicalSnapshotAttraction/, 'TripBuilder imports and uses the snapshot guard');
  assert.match(tripBuilder, /safeSnapshotAttractions/, 'TripBuilder uses a filtered safeSnapshotAttractions list');
  assert.match(tripBuilder, /allSnapshotAttractionsCanonical/, 'TripBuilder tracks whether the entire snapshot attractions list is canonical');
  // Health gate forces refetch when any snapshot row fails the guard.
  assert.match(
    tripBuilder,
    /hasHealthyAttractions\s*=\s*\n?\s*snapshot != null\s*\n?\s*&&\s*allSnapshotAttractionsCanonical/,
    'hasHealthyAttractions requires every snapshot attraction to be canonical',
  );
  // Refetch path uses the canonical helper, not raw snapshot.
  assert.match(tripBuilder, /shouldFetchAttractions \? searchAttractionsViaConcierge\(tripId, destination\) : Promise\.resolve\(safeSnapshotAttractions\)/, 'Non-fetch branch falls back to the filtered safe list');
  // Restaurants must remain reusable independently — guard is attractions-only.
  assert.match(tripBuilder, /shouldFetchRestaurants \? searchRestaurants\(destination\)/, 'Restaurant snapshot reuse is not changed by the v1B guard');
});

// ── Behavioral parity for the snapshot guard ─────────────────────────────────
// The guard logic is small and pure; we re-implement it here from the same
// rules and verify both shapes (legacy mock vs. canonical Google identity).

function isCanonicalSnapshotAttractionRef(a) {
  if (!a) return false;
  const id = typeof a.id === 'string' ? a.id : '';
  if (!id || id.startsWith('mock-') || id.startsWith('attr-')) return false;
  const url = typeof a.bookingUrl === 'string' ? a.bookingUrl : '';
  if (!url) return false;
  return url.includes('google.com/maps') || url.includes('place_id:');
}

test('Snapshot guard rejects legacy mock-shaped attraction rows (forces canonical refetch)', () => {
  const legacyMockShaped = {
    id: 'mock-attraction-1',
    name: 'Mock Park',
    bookingUrl: 'https://example.com/booking/mock-1',
  };
  const legacyAttrShaped = {
    id: 'attr-12345',
    name: 'Old Attraction',
    bookingUrl: '',
  };
  const noBookingUrl = {
    id: 'ChIJN1t_tDeuEmsRUsoyG83frY4',
    name: 'Place w/o Maps URL',
    bookingUrl: '',
  };
  assert.equal(isCanonicalSnapshotAttractionRef(legacyMockShaped), false, 'mock- prefixed id must be rejected');
  assert.equal(isCanonicalSnapshotAttractionRef(legacyAttrShaped), false, 'attr- prefixed legacy id must be rejected');
  assert.equal(isCanonicalSnapshotAttractionRef(noBookingUrl), false, 'Missing Google Maps URL must be rejected');
});

test('Snapshot guard accepts canonical attraction rows minted by the v1B adapter (reusable)', () => {
  const googleMapsUriShaped = {
    id: 'ChIJN1t_tDeuEmsRUsoyG83frY4',
    name: 'Verified Park',
    bookingUrl: 'https://www.google.com/maps/place/?q=place_id:ChIJN1t_tDeuEmsRUsoyG83frY4',
  };
  const placeIdDeepLink = {
    id: 'ChIJExample',
    name: 'Verified Museum',
    bookingUrl: 'https://maps.google.com/?cid=12345&place_id:ChIJExample',
  };
  assert.equal(isCanonicalSnapshotAttractionRef(googleMapsUriShaped), true, 'Google Maps URL row must be reusable');
  assert.equal(isCanonicalSnapshotAttractionRef(placeIdDeepLink), true, 'place_id deep link row must be reusable');
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
