// Flights Provider Scaffold — fail-closed + frontend contract tests.
//
// These are source-content contract tests (same pattern as
// fail-closed-flights-hotels.test.mjs).  They guard:
//
//   1. FlightExploreFlow shows polished unavailable state (no mock cards).
//   2. No NEXT_PUBLIC_ env var name appears for flight provider keys.
//   3. FlightItineraryOffer TypeScript interface has required contract fields.
//   4. Provider key names are server-side only (not in any NEXT_PUBLIC_ block).
//   5. FlightExploreFlow deferred state copy remains intact.

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

function readFile(relPath) {
  return readFileSync(path.join(root, relPath), 'utf8');
}

const flightFlow = readSrc('components/explore/FlightExploreFlow.tsx');
const exploreTypes = readSrc('components/explore/types.ts');

// ---------------------------------------------------------------------------
// 1. FlightExploreFlow: polished unavailable state, no mock flight cards
// ---------------------------------------------------------------------------

test('FlightExploreFlow: has deferred/unavailable state container', () => {
  assert.match(
    flightFlow,
    /data-testid="flight-deferred-state"/,
    'Expected flight-deferred-state test id',
  );
});

test('FlightExploreFlow: shows coming-soon copy (not mock/fake cards)', () => {
  assert.match(
    flightFlow,
    /live flight search/i,
    'Expected "live flight search" copy indicating deferred state',
  );
});

test('FlightExploreFlow: does not render any hard-coded price strings', () => {
  // No "$" or "USD" hard-coded flight prices in the component
  assert.doesNotMatch(
    flightFlow,
    /\$\d+|\bUSD\b.*\d/,
    'FlightExploreFlow must not contain hard-coded price amounts',
  );
});

test('FlightExploreFlow: does not reference book.example.com', () => {
  assert.doesNotMatch(
    flightFlow,
    /book\.example\.com/i,
    'FlightExploreFlow must not contain mock booking URL',
  );
});

test('FlightExploreFlow: does not render mock flight rows', () => {
  // The component must not contain source="mock" or source="demo" strings
  assert.doesNotMatch(
    flightFlow,
    /source\s*=\s*["']mock["']/,
    'FlightExploreFlow must not contain mock source rows',
  );
  assert.doesNotMatch(
    flightFlow,
    /source\s*=\s*["']demo["']/,
    'FlightExploreFlow must not contain demo source rows',
  );
});

// ---------------------------------------------------------------------------
// 2–4. Provider keys are server-side only: no NEXT_PUBLIC_ flight key names
// ---------------------------------------------------------------------------

test('FlightExploreFlow: does not reference NEXT_PUBLIC_ flight provider keys', () => {
  assert.doesNotMatch(
    flightFlow,
    /NEXT_PUBLIC_SKYSCANNER/,
    'SKYSCANNER_API_KEY must not be exposed as a NEXT_PUBLIC_ variable',
  );
  assert.doesNotMatch(
    flightFlow,
    /NEXT_PUBLIC_IGNAV/,
    'IGNAV_API_KEY must not be exposed as a NEXT_PUBLIC_ variable',
  );
});

test('exploreTypes: no NEXT_PUBLIC_ flight provider key references', () => {
  assert.doesNotMatch(
    exploreTypes,
    /NEXT_PUBLIC_SKYSCANNER|NEXT_PUBLIC_IGNAV|NEXT_PUBLIC_DUFFEL/,
    'Provider keys must not appear with NEXT_PUBLIC_ prefix in types.ts',
  );
});

// ---------------------------------------------------------------------------
// 5. FlightItineraryOffer TypeScript interface has required contract fields
// ---------------------------------------------------------------------------

test('exploreTypes: FlightItineraryOffer interface exists', () => {
  assert.match(
    exploreTypes,
    /interface FlightItineraryOffer/,
    'Expected FlightItineraryOffer interface in types.ts',
  );
});

test('exploreTypes: FlightItineraryOffer has provider field', () => {
  assert.match(
    exploreTypes,
    /provider:\s*string/,
    'FlightItineraryOffer must have provider field',
  );
});

test('exploreTypes: FlightItineraryOffer has fetchedAt field', () => {
  assert.match(
    exploreTypes,
    /fetchedAt:\s*string/,
    'FlightItineraryOffer must have fetchedAt field (ISO 8601 UTC)',
  );
});

test('exploreTypes: FlightItineraryOffer has liveCachedStatus field', () => {
  assert.match(
    exploreTypes,
    /liveCachedStatus:\s*LiveCachedStatus/,
    'FlightItineraryOffer must have liveCachedStatus field',
  );
});

test('exploreTypes: FlightItineraryOffer has tripType field', () => {
  assert.match(
    exploreTypes,
    /tripType:\s*TripType/,
    'FlightItineraryOffer must have tripType field',
  );
});

test('exploreTypes: FlightItineraryOffer has outboundLeg field', () => {
  assert.match(
    exploreTypes,
    /outboundLeg:\s*FlightOfferLeg/,
    'FlightItineraryOffer must have outboundLeg field',
  );
});

test('exploreTypes: FlightItineraryOffer has price field as FlightPrice', () => {
  assert.match(
    exploreTypes,
    /price:\s*FlightPrice/,
    'FlightItineraryOffer must have price field of type FlightPrice',
  );
});

test('exploreTypes: FlightItineraryOffer has bookingLink field', () => {
  assert.match(
    exploreTypes,
    /bookingLink:\s*FlightBookingLink/,
    'FlightItineraryOffer must have bookingLink field',
  );
});

test('exploreTypes: FlightItineraryOffer kind discriminant is flight_offer', () => {
  assert.match(
    exploreTypes,
    /kind:\s*["']flight_offer["']/,
    'FlightItineraryOffer must have kind: "flight_offer" discriminant',
  );
});

test('exploreTypes: LiveCachedStatus has live and cached values', () => {
  assert.match(exploreTypes, /"live"/, 'LiveCachedStatus must include "live"');
  assert.match(exploreTypes, /"cached"/, 'LiveCachedStatus must include "cached"');
});

test('exploreTypes: BookingLinkType has all required values', () => {
  assert.match(exploreTypes, /"airline_direct"/, 'BookingLinkType must include airline_direct');
  assert.match(exploreTypes, /"ota"/, 'BookingLinkType must include ota');
  assert.match(exploreTypes, /"provider_deeplink"/, 'BookingLinkType must include provider_deeplink');
  assert.match(exploreTypes, /"unavailable"/, 'BookingLinkType must include unavailable');
});

test('exploreTypes: FlightSegment interface exists with required fields', () => {
  assert.match(exploreTypes, /interface FlightSegment/, 'FlightSegment interface must exist');
  assert.match(exploreTypes, /flightNumber:\s*string/, 'FlightSegment must have flightNumber');
  assert.match(exploreTypes, /durationMinutes:\s*number/, 'FlightSegment must have durationMinutes');
});

test('exploreTypes: FlightOfferLeg interface exists', () => {
  assert.match(
    exploreTypes,
    /interface FlightOfferLeg/,
    'FlightOfferLeg interface must exist',
  );
});

test('exploreTypes: FlightPrice has totalAmount and currency', () => {
  assert.match(exploreTypes, /interface FlightPrice/, 'FlightPrice interface must exist');
  assert.match(exploreTypes, /currency:\s*string/, 'FlightPrice must have currency field');
  assert.match(exploreTypes, /totalAmount:\s*number/, 'FlightPrice must have totalAmount field');
});

// ---------------------------------------------------------------------------
// 6. No visible booking UI added by this scaffold
// ---------------------------------------------------------------------------

test('FlightExploreFlow: no booking button or checkout CTA', () => {
  assert.doesNotMatch(
    flightFlow,
    /Book Now|Checkout|Purchase Ticket|Complete Booking/i,
    'FlightExploreFlow must not contain booking/checkout CTA copy',
  );
});

test('FlightExploreFlow: no points/award prices shown', () => {
  assert.doesNotMatch(
    flightFlow,
    /\d+\s*(pts|points|miles|award)/i,
    'FlightExploreFlow must not display points/award prices',
  );
});
