/**
 * Flights city resolver — CityAutocomplete wiring in FlightExploreFlow.
 *
 * Structural tests verifying:
 * 1. FlightExploreFlow imports CityAutocomplete and AirportSelection.
 * 2. FlightExploreRequest in api.ts carries originAirports? / destinationAirports?.
 * 3. searchFlightsExplore passes origin_airports when multiple airports present.
 * 4. Form validates by selection-not-null (no raw IATA validateIata guard).
 * 5. Safety invariants: no booking link, server-side key only.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const flightFlow = readFileSync(
  new URL('../src/components/explore/FlightExploreFlow.tsx', import.meta.url), 'utf8');

const apiTs = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url), 'utf8');

// ── 1. CityAutocomplete integration ──────────────────────────────────────────

test('FlightExploreFlow imports CityAutocomplete', () => {
  assert.match(flightFlow, /CityAutocomplete/);
});

test('FlightExploreFlow imports AirportSelection type', () => {
  assert.match(flightFlow, /AirportSelection/);
});

test('FlightExploreFlow uses AirportSelection|null for origin and destination', () => {
  assert.match(flightFlow, /AirportSelection\s*\|\s*null/);
});

test('FlightExploreFlow does not use raw IATA validateIata guard', () => {
  assert.doesNotMatch(flightFlow, /validateIata/);
});

test('FlightExploreFlow does not use maxLength=3 raw IATA input', () => {
  assert.doesNotMatch(flightFlow, /maxLength=\{3\}/);
});

// ── 2. FlightExploreRequest multi-airport fields ──────────────────────────────

test('FlightExploreRequest has originAirports optional field', () => {
  assert.match(apiTs, /originAirports\??\s*:/);
});

test('FlightExploreRequest has destinationAirports optional field', () => {
  assert.match(apiTs, /destinationAirports\??\s*:/);
});

test('searchFlightsExplore passes origin_airports when multiple', () => {
  assert.match(apiTs, /origin_airports/);
});

test('searchFlightsExplore passes destination_airports when multiple', () => {
  assert.match(apiTs, /destination_airports/);
});

// ── 3. Form validation ────────────────────────────────────────────────────────

test('FlightExploreFlow checks form.origin null-guard (not IATA string check)', () => {
  assert.match(flightFlow, /!form\.origin/);
  assert.match(flightFlow, /!form\.destination/);
});

// ── 4. Multi-airport passthrough to API ──────────────────────────────────────

test('FlightExploreFlow passes originAirports when multiple airports selected', () => {
  assert.match(flightFlow, /originAirports/);
  assert.match(flightFlow, /destinationAirports/);
});

test('FlightExploreFlow derives primary IATA from airports[0]', () => {
  assert.match(flightFlow, /airports\[0\]/);
});

// ── 5. Safety invariants ──────────────────────────────────────────────────────

test('FlightExploreFlow safety comment documents server-side key', () => {
  assert.match(flightFlow, /server-side/i);
});

test('FlightExploreFlow uses search_redirect not booking link', () => {
  assert.match(flightFlow, /search_redirect/i);
  assert.doesNotMatch(flightFlow, /duffel.*book|book.*duffel/i);
});
