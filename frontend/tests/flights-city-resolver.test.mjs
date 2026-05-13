/**
 * Flights city resolver — CityAutocomplete wiring in FlightExploreFlow.
 *
 * Structural tests verifying:
 * 1. FlightExploreFlow imports CityAutocomplete and AirportSelection.
 * 2. FlightExploreRequest in api.ts carries originAirports? / destinationAirports?.
 * 3. searchFlightsExplore sends origin_airports/destination_airports when multiple airports.
 * 4. Form validates by selection-not-null (no raw IATA validateIata guard).
 * 5. Multi-airport passthrough: airports[0] is primary; full array sent when > 1.
 * 6. Duffel search scope: multi-airport arrays do NOT expand Duffel slices (documented).
 * 7. Safety invariants: no booking/OTA/Ignav behavior; server-side key only.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const flightFlow = readFileSync(
  new URL('../src/components/explore/FlightExploreFlow.tsx', import.meta.url), 'utf8');

const apiTs = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url), 'utf8');

const duffelProvider = readFileSync(
  new URL('../../backend/app/services/flights_provider_duffel.py', import.meta.url), 'utf8');

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

test('searchFlightsExplore sends origin_airports when length > 1', () => {
  // The guard must be length > 1, not unconditional, so single airports stay primary-only
  assert.match(apiTs, /originAirports.*length.*1|length.*1.*originAirports/s);
  assert.match(apiTs, /origin_airports/);
});

test('searchFlightsExplore sends destination_airports when length > 1', () => {
  assert.match(apiTs, /destinationAirports.*length.*1|length.*1.*destinationAirports/s);
  assert.match(apiTs, /destination_airports/);
});

test('searchFlightsExplore always sends single origin field', () => {
  // Primary single IATA is always sent regardless of multi-airport arrays
  assert.match(apiTs, /origin:\s*req\.origin/);
  assert.match(apiTs, /destination:\s*req\.destination/);
});

// ── 3. Form validation ────────────────────────────────────────────────────────

test('FlightExploreFlow checks form.origin null-guard', () => {
  assert.match(flightFlow, /!form\.origin/);
  assert.match(flightFlow, /!form\.destination/);
});

test('submit button disabled when origin or destination null', () => {
  assert.match(flightFlow, /disabled=\{isLoading \|\| !form\.origin \|\| !form\.destination/);
});

// ── 4. Multi-airport passthrough to API ──────────────────────────────────────

test('FlightExploreFlow derives primary IATA from airports[0]', () => {
  assert.match(flightFlow, /airports\[0\]/);
});

test('FlightExploreFlow sends originAirports only when multiple airports selected', () => {
  // Guard: airports.length > 1 before setting originAirports
  assert.match(flightFlow, /airports\.length > 1/);
  assert.match(flightFlow, /originAirports/);
  assert.match(flightFlow, /destinationAirports/);
});

test('FlightExploreFlow maps all airports to uppercase before API call', () => {
  assert.match(flightFlow, /toUpperCase\(\)/);
});

// ── 5. Duffel search scope (primary-airport-only) ─────────────────────────────

test('Duffel provider documents city-group scope limitation in _build_slices', () => {
  // The comment must be present to prevent accidental cross-product expansion
  assert.match(duffelProvider, /Duffel search.*primary.*airport|primary.*airport.*Duffel search/si);
});

test('Duffel provider does not expand origin_airports into multi-slice calls', () => {
  // _build_slices uses req.origin, not req.origin_airports or req.all_origins
  const buildSlicesSection = duffelProvider.match(/_build_slices[\s\S]*?return slices/)?.[0] ?? '';
  assert.ok(buildSlicesSection.length > 0, '_build_slices section not found');
  assert.doesNotMatch(buildSlicesSection, /all_origins|origin_airports/);
});

// ── 6. Safety invariants ──────────────────────────────────────────────────────

test('FlightExploreFlow safety comment documents server-side key', () => {
  assert.match(flightFlow, /server-side/i);
});

test('FlightExploreFlow uses search_redirect not booking link', () => {
  assert.match(flightFlow, /search_redirect/i);
  assert.doesNotMatch(flightFlow, /duffel.*book|book.*duffel/i);
});

test('Duffel provider documents no orders created', () => {
  assert.match(duffelProvider, /never creates.*orders|orders.*never/i);
});
