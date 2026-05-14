/**
 * Runtime fixture tests for canonical round-trip flight bucketing.
 *
 * Unlike the regex-only checks in trip-candidates-contract.test.mjs, this test
 * loads the actual `buildTripCandidateBuckets` function from
 * `frontend/src/lib/tripCandidates.ts` (with `--experimental-strip-types`),
 * stubs the `@/lib/api` alias, and runs canonical FlightItineraryOffer-shaped
 * fixtures through it to prove:
 *
 *   1. trip_type="round_trip" + return_leg → bucketed in roundTripFlights
 *   2. trip_type="one_way" + no return_leg → bucketed in flights
 *   3. is_round_trip:true → bucketed in roundTripFlights
 *   4. Multiple distinct round-trip offers survive dedupe
 *   5. After toCamel (tripType, returnLeg, isRoundTrip), behaviour identical
 *
 * Requires Node 22+ for native TypeScript stripping.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

// ─── Build a loadable module from tripCandidates.ts ────────────────────────────
//
// The source imports `@/lib/api` (a Next.js path alias) which Node cannot resolve
// natively. We rewrite that import to a relative stub and write to a temp .ts
// file so Node --experimental-strip-types can load it directly.

const srcPath = new URL('../src/lib/tripCandidates.ts', import.meta.url);
const src = readFileSync(srcPath, 'utf8');

const stubDir = mkdtempSync(path.join(tmpdir(), 'tripcand-'));
const stubApiPath = path.join(stubDir, 'api-stub.ts');
writeFileSync(stubApiPath, `
export function computeExploreAttractionScore(_r: number, _n: number, _c?: string): number {
  return 0;
}
export function computeExploreRestaurantScore(_r: number, _n: number, _p: number, _s?: number): number {
  return 0;
}
`);

// Strip multi-line `import type { ... } from "@/types";` entirely (Node's
// type-stripper removes it but the source spec "@/types" can't resolve).
const noTypes = src.replace(
  /import\s+type\s+\{[\s\S]*?\}\s+from\s+["']@\/types["']\s*;?/g,
  '',
);
const finalSrc = noTypes.replace(
  /from\s+["']@\/lib\/api["']/g,
  `from ${JSON.stringify(stubApiPath)}`,
);

const candPath = path.join(stubDir, 'tripCandidates.ts');
writeFileSync(candPath, finalSrc);

const mod = await import(pathToFileURL(candPath).href);
const { buildTripCandidateBuckets } = mod;

// ─── Canonical-shaped fixtures (post-toCamel — keys are camelCase) ────────────

// All canonical fixtures carry `kind: "flight_offer"` and `sourceKind:
// "creation_seed"` (set by backend _offer_to_flight_item). These markers
// signal the frontend selector that the persisted item id IS the offer
// identity — no further reconstructive dedupe should run.

function camelRoundTripOffer({
  id,
  dep = '2026-05-13T10:00:00Z',
  flightNo = 'DL100',
  rtFlightNo = 'DL101',
  rtDep = '2026-05-20T10:00:00Z',
  cashPrice = 850,
  currency = 'USD',
  cabinClass = 'economy',
}) {
  return {
    id,
    itemType: 'flight',
    title: `Delta ${flightNo}`,
    dayId: null,
    details: {
      kind: 'flight_offer',
      provider: 'duffel_flights',
      source: 'duffel_flights',
      sourceKind: 'creation_seed',
      tripType: 'round_trip',
      isRoundTrip: true,
      airline: 'Delta',
      flightNumber: flightNo,
      origin: 'BOS',
      destination: 'SEA',
      departureTime: dep,
      cashPrice,
      currency,
      cabinClass,
      outboundLeg: {
        origin: 'BOS', destination: 'SEA',
        departureTime: dep, arrivalTime: '2026-05-13T14:00:00Z',
        segments: [{ airline: 'Delta', flightNumber: flightNo, origin: 'BOS', destination: 'SEA', departureTime: dep }],
      },
      returnLeg: {
        origin: 'SEA', destination: 'BOS',
        departureTime: rtDep, arrivalTime: '2026-05-20T18:00:00Z',
        segments: [{ airline: 'Delta', flightNumber: rtFlightNo, origin: 'SEA', destination: 'BOS', departureTime: rtDep }],
      },
    },
  };
}

function snakeRoundTripOffer({ id }) {
  return {
    id,
    itemType: 'flight',
    title: 'Snake RT',
    dayId: null,
    details: {
      kind: 'flight_offer',
      provider: 'duffel_flights',
      source: 'duffel_flights',
      source_kind: 'creation_seed',
      trip_type: 'round_trip',
      is_round_trip: true,
      outbound_leg: {
        origin: 'BOS', destination: 'SEA',
        departure_time: '2026-05-13T10:00:00Z',
        segments: [{ airline: 'United', flight_number: 'UA200', origin: 'BOS', destination: 'SEA', departure_time: '2026-05-13T10:00:00Z' }],
      },
      return_leg: {
        origin: 'SEA', destination: 'BOS',
        departure_time: '2026-05-20T10:00:00Z',
        segments: [{ airline: 'United', flight_number: 'UA201', origin: 'SEA', destination: 'BOS', departure_time: '2026-05-20T10:00:00Z' }],
      },
    },
  };
}

function oneWayOffer({ id, flightNo = 'AA300' }) {
  return {
    id,
    itemType: 'flight',
    title: `American ${flightNo}`,
    dayId: null,
    details: {
      kind: 'flight_offer',
      provider: 'duffel_flights',
      source: 'duffel_flights',
      sourceKind: 'creation_seed',
      tripType: 'one_way',
      isRoundTrip: false,
      airline: 'American',
      flightNumber: flightNo,
      origin: 'BOS',
      destination: 'SEA',
      departureTime: '2026-05-13T10:00:00Z',
    },
  };
}

// ─── Tests ─────────────────────────────────────────────────────────────────────

test('runtime: canonical round-trip row goes to roundTripFlights bucket, not flights', () => {
  const buckets = buildTripCandidateBuckets([
    camelRoundTripOffer({ id: 'rt-1' }),
  ]);
  assert.equal(buckets.roundTripFlights.length, 1, 'round-trip bucket must have the row');
  assert.equal(buckets.flights.length, 0, 'one-way bucket must NOT receive a round-trip row');
});

test('runtime: snake_case canonical round-trip row also buckets correctly', () => {
  const buckets = buildTripCandidateBuckets([
    snakeRoundTripOffer({ id: 'rt-snake' }),
  ]);
  assert.equal(buckets.roundTripFlights.length, 1);
  assert.equal(buckets.flights.length, 0);
});

test('runtime: returnLeg-only (no tripType/isRoundTrip) also buckets as round-trip', () => {
  const row = {
    id: 'rt-leg-only',
    itemType: 'flight',
    title: 'Leg only',
    dayId: null,
    details: {
      outboundLeg: {
        origin: 'BOS', destination: 'SEA',
        departureTime: '2026-05-13T10:00:00Z',
        segments: [{ airline: 'JetBlue', flightNumber: 'B6400', origin: 'BOS', destination: 'SEA', departureTime: '2026-05-13T10:00:00Z' }],
      },
      returnLeg: {
        origin: 'SEA', destination: 'BOS',
        departureTime: '2026-05-20T10:00:00Z',
        segments: [{ airline: 'JetBlue', flightNumber: 'B6401', origin: 'SEA', destination: 'BOS', departureTime: '2026-05-20T10:00:00Z' }],
      },
    },
  };
  const buckets = buildTripCandidateBuckets([row]);
  assert.equal(buckets.roundTripFlights.length, 1);
  assert.equal(buckets.flights.length, 0);
});

test('runtime: pure one-way row goes to flights bucket', () => {
  const buckets = buildTripCandidateBuckets([oneWayOffer({ id: 'ow-1' })]);
  assert.equal(buckets.flights.length, 1);
  assert.equal(buckets.roundTripFlights.length, 0);
});

test('runtime: mixed round-trip + one-way bucket correctly side by side', () => {
  const buckets = buildTripCandidateBuckets([
    camelRoundTripOffer({ id: 'rt-1' }),
    oneWayOffer({ id: 'ow-1' }),
    snakeRoundTripOffer({ id: 'rt-snake' }),
  ]);
  assert.equal(buckets.roundTripFlights.length, 2);
  assert.equal(buckets.flights.length, 1);
});

test('runtime: multiple distinct round-trip offers survive dedupe', () => {
  const buckets = buildTripCandidateBuckets([
    camelRoundTripOffer({ id: 'rt-1', flightNo: 'DL100', dep: '2026-05-13T08:00:00Z' }),
    camelRoundTripOffer({ id: 'rt-2', flightNo: 'DL200', dep: '2026-05-13T12:00:00Z' }),
    camelRoundTripOffer({ id: 'rt-3', flightNo: 'DL300', dep: '2026-05-13T17:00:00Z' }),
  ]);
  assert.equal(buckets.roundTripFlights.length, 3, 'distinct round-trip offers must not collapse to 1');
});

test('runtime: round-trip rows assigned to a day are excluded from candidate buckets', () => {
  const row = camelRoundTripOffer({ id: 'rt-assigned' });
  row.dayId = 'some-uuid-1234';
  const buckets = buildTripCandidateBuckets([row]);
  assert.equal(buckets.roundTripFlights.length, 0);
  assert.equal(buckets.flights.length, 0);
});

// ─── Canonical-flight-offer no-dedupe contract (Stage 3 exit) ────────────────
//
// Canonical provider-backed persisted flight offers (kind="flight_offer" /
// sourceKind="creation_seed" / provider+tripType) carry the offer identity
// IN the persisted item id. Backend create-with-search has already chosen
// which offers to persist; the frontend MUST NOT re-collapse them by
// reconstructed fields. Every persisted canonical row is its own card.
// Production evidence: 10 persisted round-trip offers → must be 10 cards.

test('runtime: 10 canonical persisted round-trip offers (same pair, same price) show 10 cards', () => {
  // Same flight pair, same cash price, same currency, same cabin — only the
  // persisted item id differs. With the canonical-offer contract all 10 must
  // remain visible.
  const offers = [];
  for (let i = 0; i < 10; i++) {
    offers.push(camelRoundTripOffer({
      id: `canonical-rt-${i}`,
      flightNo: 'DL100', rtFlightNo: 'DL101',
      cashPrice: 850, currency: 'USD', cabinClass: 'economy',
    }));
  }
  const buckets = buildTripCandidateBuckets(offers);
  assert.equal(buckets.roundTripFlights.length, 10,
    `Expected 10 canonical round-trip cards, got ${buckets.roundTripFlights.length}`);
  assert.equal(buckets.flights.length, 0);
});

test('runtime: 10 canonical persisted one-way offers all remain visible', () => {
  const offers = [];
  for (let i = 0; i < 10; i++) {
    offers.push(oneWayOffer({ id: `canonical-ow-${i}` }));
  }
  const buckets = buildTripCandidateBuckets(offers);
  assert.equal(buckets.flights.length, 10, 'all 10 canonical one-way offers must remain visible');
  assert.equal(buckets.roundTripFlights.length, 0);
});

test('runtime: canonical round-trip with sourceKind="creation_seed" only (no kind) still no-dedupe', () => {
  const mk = (id) => ({
    id,
    itemType: 'flight',
    title: 'Delta DL100',
    dayId: null,
    details: {
      sourceKind: 'creation_seed',
      tripType: 'round_trip',
      isRoundTrip: true,
      returnLeg: {
        origin: 'SEA', destination: 'BOS',
        departureTime: '2026-05-20T10:00:00Z',
        segments: [{ airline: 'Delta', flightNumber: 'DL101', departureTime: '2026-05-20T10:00:00Z' }],
      },
      outboundLeg: {
        origin: 'BOS', destination: 'SEA',
        departureTime: '2026-05-13T10:00:00Z',
        segments: [{ airline: 'Delta', flightNumber: 'DL100', departureTime: '2026-05-13T10:00:00Z' }],
      },
      cashPrice: 850, currency: 'USD', cabinClass: 'economy',
    },
  });
  const buckets = buildTripCandidateBuckets([mk('a'), mk('b'), mk('c')]);
  assert.equal(buckets.roundTripFlights.length, 3,
    'creation_seed canonical rows must not collapse even when other fields match');
});

test('runtime: legacy exact-duplicate rows (no canonical provenance) still collapse', () => {
  // No kind, no sourceKind, no provider/source — pre-canonical legacy rows
  // continue to use the identity+fare dedupe key so old fixtures collapse.
  const mkLegacy = (id) => ({
    id,
    itemType: 'flight',
    title: 'Legacy Delta',
    dayId: null,
    details: {
      tripType: 'round_trip',
      isRoundTrip: true,
      outboundLeg: {
        origin: 'BOS', destination: 'SEA',
        departureTime: '2026-05-13T10:00:00Z',
        segments: [{ airline: 'Delta', flightNumber: 'DL100', departureTime: '2026-05-13T10:00:00Z' }],
      },
      returnLeg: {
        origin: 'SEA', destination: 'BOS',
        departureTime: '2026-05-20T10:00:00Z',
        segments: [{ airline: 'Delta', flightNumber: 'DL101', departureTime: '2026-05-20T10:00:00Z' }],
      },
      cashPrice: 850, currency: 'USD', cabinClass: 'economy',
    },
  });
  const buckets = buildTripCandidateBuckets([mkLegacy('a'), mkLegacy('b'), mkLegacy('c')]);
  assert.equal(buckets.roundTripFlights.length, 1,
    'legacy exact-duplicate rows without canonical provenance must still collapse');
});

test('runtime: legacy one-way exact duplicates (no canonical provenance) still collapse', () => {
  const mkLegacy = (id) => ({
    id,
    itemType: 'flight',
    title: 'Legacy AA',
    dayId: null,
    details: {
      tripType: 'one_way', isRoundTrip: false,
      airline: 'American', flightNumber: 'AA300',
      origin: 'BOS', destination: 'SEA',
      departureTime: '2026-05-13T10:00:00Z',
      cashPrice: 320, currency: 'USD', cabinClass: 'economy',
    },
  });
  const buckets = buildTripCandidateBuckets([mkLegacy('a'), mkLegacy('b'), mkLegacy('c')]);
  assert.equal(buckets.flights.length, 1, 'legacy one-way duplicates must still collapse');
});
