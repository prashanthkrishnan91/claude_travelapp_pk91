// Hotels Product Contract v1 — discovery-only safety contract.
//
// Source-content contract tests (same pattern as
// fail-closed-flights-hotels.test.mjs).  These guard that:
//
//   1. searchHotels() preserves the Hotels v1 discovery/has-real-rate
//      markers in ResearchResult.metadata so callers can refuse to use
//      Google Places lodging discovery rows as priced inputs.
//   2. mapHotelToResult() suppresses fake "$0/night" priceDisplay strings
//      for discovery-only rows (no fabricated rate copy).
//   3. OptimizeTripModal switches to provider_unavailable when no hotel
//      row has a real rate, and never calls optimizeTrip() with
//      discovery-only rows.

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const apiClient = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url),
  'utf8',
);
const optimizeModal = readFileSync(
  new URL('../src/components/trips/OptimizeTripModal.tsx', import.meta.url),
  'utf8',
);

test('api.ts: RawHotelResult exposes Hotels v1 discovery markers', () => {
  assert.match(
    apiClient,
    /offerKind\?:\s*string/,
    'RawHotelResult must surface offerKind from the backend response.',
  );
  assert.match(
    apiClient,
    /hasRealRate\?:\s*boolean/,
    'RawHotelResult must surface hasRealRate from the backend response.',
  );
  assert.match(
    apiClient,
    /source\?:\s*string/,
    'RawHotelResult must surface the backend source attribution.',
  );
});

test('api.ts: mapHotelToResult propagates discovery markers into metadata', () => {
  assert.match(
    apiClient,
    /metadata:\s*\{[\s\S]*?offerKind:\s*h\.offerKind/,
    'metadata.offerKind must be propagated for downstream consumers.',
  );
  assert.match(
    apiClient,
    /hasRealRate,/,
    'metadata.hasRealRate must be propagated for downstream consumers.',
  );
});

test('api.ts: discovery-only rows never show $0/night priceDisplay', () => {
  // The mapper must only build the "$X/night" string when the row
  // carries a real rate AND a positive nightly price.  Otherwise a
  // Google Places discovery row would render "$0/night" — which would
  // be a fabricated nightly rate from the user's perspective.
  assert.match(
    apiClient,
    /const showsRate = hasRealRate && typeof h\.pricePerNight === "number" && h\.pricePerNight > 0;/,
    'mapHotelToResult must gate priceDisplay on hasRealRate AND positive pricePerNight.',
  );
  assert.match(
    apiClient,
    /priceDisplay:\s*showsRate\s*\?\s*`\$\$\{h\.pricePerNight\}\/night`\s*:\s*undefined/,
    'priceDisplay must be undefined when the row is discovery-only or has no rate.',
  );
});

test('OptimizeTripModal: refuses to call optimizeTrip when no hotel has a real rate', () => {
  assert.match(
    optimizeModal,
    /hotelHasRealRate/,
    'Expected a hotelHasRealRate helper to gate priced package inputs.',
  );
  assert.match(
    optimizeModal,
    /anyHotelHasRealRate\(rawHotels\)/,
    'Expected the modal to check anyHotelHasRealRate(rawHotels) before optimizing.',
  );
  // Provider-unavailable branch must precede optimizeTrip() — no
  // discovery-only rows can reach the optimizer.
  const checkIdx = optimizeModal.indexOf('anyHotelHasRealRate(rawHotels)');
  const optimizeCallIdx = optimizeModal.indexOf('await optimizeTrip(');
  assert.ok(checkIdx > 0, 'anyHotelHasRealRate gate must be present.');
  assert.ok(optimizeCallIdx > 0, 'optimizeTrip() call must be present.');
  assert.ok(
    checkIdx < optimizeCallIdx,
    'anyHotelHasRealRate gate must run before optimizeTrip() so discovery-only rows cannot reach the optimizer.',
  );
});

test('OptimizeTripModal: filters discovery-only rows out of the optimizer input', () => {
  // Even on a mixed batch (some priced, some discovery), only the
  // priced rows feed into ``hotels`` — otherwise $0/night discovery
  // rows could mix into the ranked packages.
  assert.match(
    optimizeModal,
    /pricedHotels\s*=\s*rawHotels\.filter\(hotelHasRealRate\)/,
    'Expected pricedHotels = rawHotels.filter(hotelHasRealRate) to drop discovery-only rows.',
  );
  assert.match(
    optimizeModal,
    /pricedHotels\.slice\(0, 10\)\.map/,
    'Expected the optimizer input to be built from pricedHotels, not rawHotels.',
  );
});

test('OptimizeTripModal: hotelHasRealRate requires both flag and positive nightly rate', () => {
  // Belt-and-braces: the helper must require BOTH metadata.hasRealRate === true
  // AND a positive pricePerNight.  Either one alone is insufficient — a backend
  // with a stale wire model could send hasRealRate=true with ppn=0, or vice
  // versa.  Both checks together prevent fabricated $0/night packages.
  assert.match(
    optimizeModal,
    /meta\.hasRealRate === true/,
    'hotelHasRealRate must check metadata.hasRealRate === true.',
  );
  assert.match(
    optimizeModal,
    /typeof ppn === "number"\s*&&\s*ppn\s*>\s*0/,
    'hotelHasRealRate must require a positive pricePerNight.',
  );
});
