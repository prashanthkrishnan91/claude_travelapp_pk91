// One-way flight add-to-itinerary correctness contract.
//
// Source-content contract tests (same pattern as fail-closed-flights-hotels.test.mjs).
// Guards that:
//   1. addOneWayFlightToDay exists in api.ts and sends startTime/endTime/details.
//   2. handleAddCandidateToItinerary branches on itemType === "flight" and calls addOneWayFlightToDay.
//   3. Round-trip path adds ONE canonical item via addRoundTripFlightToDay.
//   4. No book.example.com / fake booking URL in addOneWayFlightToDay.
//   5. No _mock_flights call in the one-way add path.
//   6. One-way cards display a "One-way" indicator distinct from round-trip cards.
//   7. Round-trip button copy is "Add Round Trip" (not ambiguous "Add Both Flights").

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const apiSrc = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url),
  'utf8',
);
const tripBuilder = readFileSync(
  new URL('../src/components/trips/TripBuilder.tsx', import.meta.url),
  'utf8',
);

// ── api.ts contract ───────────────────────────────────────────────────────────

test('api.ts: addOneWayFlightToDay is exported', () => {
  assert.match(
    apiSrc,
    /export async function addOneWayFlightToDay\b/,
    'Expected addOneWayFlightToDay to be exported from api.ts',
  );
});

test('api.ts: addOneWayFlightToDay sends startTime from departure_time', () => {
  // The function must include startTime in its payload (preserves schedule)
  assert.match(
    apiSrc,
    /startTime:\s*depTime/,
    'addOneWayFlightToDay must map depTime → startTime in the POST payload',
  );
});

test('api.ts: addOneWayFlightToDay sends endTime from arrival_time', () => {
  assert.match(
    apiSrc,
    /endTime:\s*arrTime/,
    'addOneWayFlightToDay must map arrTime → endTime in the POST payload',
  );
});

test('api.ts: addOneWayFlightToDay spreads full details into payload', () => {
  assert.match(
    apiSrc,
    /details:\s*\{[^}]*\.\.\.\s*d\s*\}/,
    'addOneWayFlightToDay must spread item.details into stored details so flight info is persisted',
  );
});

test('api.ts: addOneWayFlightToDay does not contain book.example.com', () => {
  // Slice out just the addOneWayFlightToDay function body
  const fnStart = apiSrc.indexOf('export async function addOneWayFlightToDay');
  const fnEnd   = apiSrc.indexOf('\nexport async function', fnStart + 1);
  const fnBody  = apiSrc.slice(fnStart, fnEnd === -1 ? undefined : fnEnd);
  assert.doesNotMatch(
    fnBody,
    /book\.example\.com/,
    'addOneWayFlightToDay must not reference fake booking host',
  );
});

test('api.ts: addOneWayFlightToDay does not call _mock_flights', () => {
  const fnStart = apiSrc.indexOf('export async function addOneWayFlightToDay');
  const fnEnd   = apiSrc.indexOf('\nexport async function', fnStart + 1);
  const fnBody  = apiSrc.slice(fnStart, fnEnd === -1 ? undefined : fnEnd);
  assert.doesNotMatch(
    fnBody,
    /_mock_flights/,
    'addOneWayFlightToDay must not call _mock_flights',
  );
});

test('api.ts: addRoundTripFlightToDay adds ONE item preserving canonical details', () => {
  assert.match(
    apiSrc,
    /export async function addRoundTripFlightToDay\b/,
    'addRoundTripFlightToDay must exist for canonical round-trip add',
  );
  const fnStart = apiSrc.indexOf('export async function addRoundTripFlightToDay');
  const fnEnd   = apiSrc.indexOf('\nexport ', fnStart + 1);
  const fnBody  = apiSrc.slice(fnStart, fnEnd === -1 ? undefined : fnEnd);
  // Single item, full details spread — no bare "(Outbound)"/"(Return)" titles.
  assert.match(fnBody, /details:\s*\{\s*\.\.\.\s*d\s*\}/, 'must spread full canonical details');
  assert.ok(!fnBody.includes('(Outbound)'), 'must not build "(Outbound)" placeholder title');
  assert.ok(!fnBody.includes('(Return)'), 'must not build "(Return)" placeholder title');
});

test('api.ts: old split round-trip leg helpers are removed', () => {
  assert.ok(
    !apiSrc.includes('addRoundTripOutboundToDay'),
    'addRoundTripOutboundToDay must be removed — produced placeholder-only rows',
  );
  assert.ok(
    !apiSrc.includes('addRoundTripReturnToDay'),
    'addRoundTripReturnToDay must be removed — produced placeholder-only rows',
  );
});

// ── TripBuilder.tsx contract ──────────────────────────────────────────────────

test('TripBuilder: imports addOneWayFlightToDay from api', () => {
  assert.match(
    tripBuilder,
    /addOneWayFlightToDay/,
    'TripBuilder must import addOneWayFlightToDay',
  );
});

test('TripBuilder: handleAddCandidateToItinerary branches on itemType === "flight"', () => {
  assert.match(
    tripBuilder,
    /item\.itemType\s*===\s*"flight"/,
    'handleAddCandidateToItinerary must branch on itemType === "flight" to use addOneWayFlightToDay',
  );
});

test('TripBuilder: handleAddCandidateToItinerary calls addOneWayFlightToDay for flights', () => {
  assert.match(
    tripBuilder,
    /addOneWayFlightToDay\s*\(\s*tripId/,
    'handleAddCandidateToItinerary must call addOneWayFlightToDay(tripId, ...) for flight items',
  );
});

test('TripBuilder: round-trip add uses addRoundTripFlightToDay (single canonical item)', () => {
  assert.match(
    tripBuilder,
    /addRoundTripFlightToDay\s*\(\s*\n?\s*tripId/,
    'handleAddRoundTripToItinerary must call addRoundTripFlightToDay(tripId, ...)',
  );
});

test('TripBuilder: round-trip add no longer uses split leg helpers', () => {
  assert.ok(
    !tripBuilder.includes('addRoundTripOutboundToDay'),
    'TripBuilder must not reference removed addRoundTripOutboundToDay',
  );
  assert.ok(
    !tripBuilder.includes('addRoundTripReturnToDay'),
    'TripBuilder must not reference removed addRoundTripReturnToDay',
  );
});

test('TripBuilder: one-way card shows "One-way" indicator', () => {
  assert.match(
    tripBuilder,
    /One-way/,
    'FlightCandidateCard must display a One-way indicator to distinguish from round-trip cards',
  );
});

test('TripBuilder: round-trip card button says "Add Round Trip"', () => {
  assert.match(
    tripBuilder,
    /Add Round Trip/,
    'RoundTripFlightCard add button must say "Add Round Trip" for clarity',
  );
});

test('TripBuilder: one-way add button does not say "Add Both"', () => {
  // FlightCandidateCard button should say "Add" not "Add Both"
  assert.doesNotMatch(
    tripBuilder,
    /Add Both Flights/,
    'One-way card must not say "Add Both Flights" — only round-trip uses that copy',
  );
});
