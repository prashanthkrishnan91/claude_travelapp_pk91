// Flights v1 — Ignav live search contract tests.
//
// Source-content structural tests (no React renderer needed).
// Guard:
//   1. FlightExploreFlow calls /explore/flights (not legacy /search/flights).
//   2. FlightExploreFlow renders live results state (data-testid="flight-results-list").
//   3. FlightExploreFlow renders unavailable state (data-testid="flight-unavailable-state").
//   4. FlightExploreFlow renders empty state (data-testid="flight-empty-state").
//   5. FlightExploreFlow renders error state (data-testid="flight-error-state").
//   6. FlightCard renders price from provider (no hard-coded prices).
//   7. FlightCard renders live status badge (data-testid="flight-live-status").
//   8. FlightCard renders booking link (data-testid="flight-book-link").
//   9. No NEXT_PUBLIC_ env var name appears for provider keys.
//  10. No mock/placeholder prices in FlightExploreFlow source.
//  11. No points prices or points fields in FlightCard source.
//  12. Booking link uses target="_blank" rel="noopener noreferrer" (safe external link).
//  13. ResultActionSheet is imported and used for Save.
//  14. searchFlightsExplore is imported (canonical API helper).
//  15. api.ts: searchFlightsExplore calls /explore/flights, not /search/flights.
//  16. api.ts: searchFlightsExplore does NOT embed any API key value.
//  17. FlightItineraryOffer TS interface has all required v1 fields.
//  18. FlightExploreFlow has search button with data-testid.
//  19. FlightExploreFlow has loading state during search.
//  20. api.ts: FlightExploreResponse type exists with status and offers fields.

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');

function readSrc(relPath) {
  return readFileSync(path.join(root, 'src', relPath), 'utf8');
}

const flightFlow = readSrc('components/explore/FlightExploreFlow.tsx');
const exploreTypes = readSrc('components/explore/types.ts');
const apiTs = readSrc('lib/api.ts');

// ---------------------------------------------------------------------------
// 1. Calls canonical /explore/flights endpoint
// ---------------------------------------------------------------------------

test('FlightExploreFlow: imports searchFlightsExplore (not legacy searchFlights)', () => {
  assert.match(
    flightFlow,
    /import.*searchFlightsExplore.*from.*@\/lib\/api/,
    'Must import searchFlightsExplore from api',
  );
  assert.doesNotMatch(
    flightFlow,
    /searchFlights\b(?!Explore)/,
    'Must not call legacy searchFlights (only searchFlightsExplore)',
  );
});

test('api.ts: searchFlightsExplore posts to /explore/flights', () => {
  assert.match(
    apiTs,
    /\/explore\/flights/,
    'searchFlightsExplore must target /explore/flights',
  );
});

test('api.ts: searchFlightsExplore does not use legacy /search/flights', () => {
  // Find the searchFlightsExplore function body and ensure it doesn't reference legacy route
  const fnStart = apiTs.indexOf('export async function searchFlightsExplore');
  const fnEnd = apiTs.indexOf('\nexport ', fnStart + 1);
  const fnBody = apiTs.slice(fnStart, fnEnd > fnStart ? fnEnd : undefined);
  assert.doesNotMatch(fnBody, /\/search\/flights/, 'searchFlightsExplore must not call legacy /search/flights');
});

// ---------------------------------------------------------------------------
// 2–5. State containers
// ---------------------------------------------------------------------------

test('FlightExploreFlow: has live results list container', () => {
  assert.match(
    flightFlow,
    /data-testid="flight-results-list"/,
    'Expected flight-results-list test id for live results',
  );
});

test('FlightExploreFlow: has unavailable state container', () => {
  assert.match(
    flightFlow,
    /data-testid="flight-unavailable-state"/,
    'Expected flight-unavailable-state test id',
  );
});

test('FlightExploreFlow: has empty state container', () => {
  assert.match(
    flightFlow,
    /data-testid="flight-empty-state"/,
    'Expected flight-empty-state test id',
  );
});

test('FlightExploreFlow: has error state container', () => {
  assert.match(
    flightFlow,
    /data-testid="flight-error-state"/,
    'Expected flight-error-state test id',
  );
});

// ---------------------------------------------------------------------------
// 6. No hard-coded prices
// ---------------------------------------------------------------------------

test('FlightExploreFlow: does not render hard-coded price strings', () => {
  // Prices must come from provider; no literal "$499" or "USD 399" in JSX
  assert.doesNotMatch(
    flightFlow,
    />\$\d{2,}|>\s*USD\s+\d|"USD\s+\d/,
    'FlightExploreFlow must not contain hard-coded price values',
  );
});

// ---------------------------------------------------------------------------
// 7–8. FlightCard fields
// ---------------------------------------------------------------------------

test('FlightCard: renders live-cached status badge', () => {
  assert.match(
    flightFlow,
    /data-testid="flight-live-status"/,
    'Expected flight-live-status badge in FlightCard',
  );
});

test('FlightCard: renders booking link anchor', () => {
  assert.match(
    flightFlow,
    /data-testid="flight-book-link"/,
    'Expected flight-book-link anchor in FlightCard',
  );
});

test('FlightCard: renders airline name', () => {
  assert.match(
    flightFlow,
    /data-testid="flight-airline"/,
    'Expected flight-airline testid in FlightCard',
  );
});

test('FlightCard: renders cash price', () => {
  assert.match(
    flightFlow,
    /data-testid="flight-price"/,
    'Expected flight-price testid in FlightCard',
  );
});

// ---------------------------------------------------------------------------
// 9. No NEXT_PUBLIC_ key exposure
// ---------------------------------------------------------------------------

test('FlightExploreFlow: no NEXT_PUBLIC_ flight provider key references', () => {
  assert.doesNotMatch(
    flightFlow,
    /NEXT_PUBLIC_IGNAV|NEXT_PUBLIC_SKYSCANNER|NEXT_PUBLIC_.*API_KEY/i,
    'Provider API keys must never appear as NEXT_PUBLIC_ in frontend code',
  );
});

test('api.ts: no NEXT_PUBLIC_ ignav key reference in searchFlightsExplore', () => {
  assert.doesNotMatch(
    apiTs,
    /NEXT_PUBLIC_IGNAV/i,
    'IGNAV_API_KEY must not be exposed via NEXT_PUBLIC_',
  );
});

// ---------------------------------------------------------------------------
// 11. No points prices
// ---------------------------------------------------------------------------

test('FlightExploreFlow: no points price fields rendered', () => {
  assert.doesNotMatch(
    flightFlow,
    /points_cost|pointsCost|points_estimate|pointsEstimate|cpp\b|awardPrice|points.*price/i,
    'FlightExploreFlow must never render points prices (separately gated)',
  );
});

test('FlightExploreFlow: no booking language beyond link-out', () => {
  assert.doesNotMatch(
    flightFlow,
    /checkout|ticketing|PNR|payment|purchase now/i,
    'FlightExploreFlow must not contain booking/checkout language',
  );
});

// ---------------------------------------------------------------------------
// 12. Safe external link
// ---------------------------------------------------------------------------

test('FlightCard: booking link has rel="noopener noreferrer"', () => {
  assert.match(
    flightFlow,
    /rel="noopener noreferrer"/,
    'External booking link must have rel="noopener noreferrer"',
  );
});

test('FlightCard: booking link has target="_blank"', () => {
  assert.match(
    flightFlow,
    /target="_blank"/,
    'External booking link must open in new tab',
  );
});

// ---------------------------------------------------------------------------
// 13. ResultActionSheet for Save
// ---------------------------------------------------------------------------

test('FlightExploreFlow: imports and renders ResultActionSheet', () => {
  assert.match(
    flightFlow,
    /import.*ResultActionSheet.*from.*ResultActionSheet/,
    'Must import ResultActionSheet for Save action',
  );
  assert.match(
    flightFlow,
    /<ResultActionSheet/,
    'Must render ResultActionSheet on flight cards',
  );
});

// ---------------------------------------------------------------------------
// 18–19. Search form UX
// ---------------------------------------------------------------------------

test('FlightExploreFlow: search button has data-testid', () => {
  assert.match(
    flightFlow,
    /data-testid="flight-search-btn"/,
    'Search button must have flight-search-btn testid',
  );
});

test('FlightExploreFlow: has loading spinner during search', () => {
  assert.match(
    flightFlow,
    /Searching|animate-spin/,
    'Must show loading indicator while search is in progress',
  );
});

// ---------------------------------------------------------------------------
// 20. FlightExploreResponse type in api.ts
// ---------------------------------------------------------------------------

test('api.ts: FlightExploreResponse type exists with status field', () => {
  assert.match(
    apiTs,
    /FlightExploreResponse/,
    'FlightExploreResponse type must be defined',
  );
  assert.match(
    apiTs,
    /status.*FlightExploreStatus|FlightExploreStatus.*ok.*empty.*unavailable.*error/,
    'FlightExploreStatus must include ok, empty, unavailable, error values',
  );
});

test('api.ts: FlightExploreResponse includes offers array', () => {
  const typeSection = apiTs.slice(
    apiTs.indexOf('FlightExploreResponse'),
    apiTs.indexOf('FlightExploreResponse') + 500,
  );
  assert.match(typeSection, /offers/, 'FlightExploreResponse must have offers field');
});

// ---------------------------------------------------------------------------
// 17. FlightItineraryOffer interface fields
// ---------------------------------------------------------------------------

test('types.ts: FlightItineraryOffer has required v1 fields', () => {
  const required = [
    'provider',
    'fetchedAt',
    'liveCachedStatus',
    'tripType',
    'origin',
    'destination',
    'departureDate',
    'passengers',
    'cabinClass',
    'outboundLeg',
    'price',
    'bookingLink',
  ];
  for (const field of required) {
    assert.match(
      exploreTypes,
      new RegExp(`\\b${field}\\b`),
      `FlightItineraryOffer must have field: ${field}`,
    );
  }
});

test('types.ts: FlightItineraryOffer has kind discriminant', () => {
  assert.match(
    exploreTypes,
    /kind.*flight_offer/,
    'FlightItineraryOffer must have kind: "flight_offer" discriminant',
  );
});

test('types.ts: FlightItineraryOffer has NO points fields', () => {
  const offerSection = exploreTypes.slice(
    exploreTypes.indexOf('FlightItineraryOffer'),
    exploreTypes.indexOf('}', exploreTypes.indexOf('FlightItineraryOffer')) + 1,
  );
  assert.doesNotMatch(
    offerSection,
    /points_cost|pointsCost|points_estimate|cpp\b/,
    'FlightItineraryOffer interface must not have points fields',
  );
});
