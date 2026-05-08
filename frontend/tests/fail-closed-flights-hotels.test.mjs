// Fail-Closed UX v1 — flights/hotels copy contract.
//
// These are source-content contract tests (same pattern as
// concierge-renderers.test.mjs / explore-concierge-migration.test.mjs) — they
// guard the user-visible copy strings, not the runtime behavior, since the
// repo does not yet wire React Testing Library for these components.
//
// Contract:
//   1. TripBuilderForm shows honest provider-unavailable copy and offers a
//      manual blank-trip path on backend 503/provider_unavailable failure.
//   2. OptimizeTripModal shows honest provider-unavailable copy instead of
//      the old "Try adjusting your dates" message when flights/hotels
//      search returns empty.
//   3. apiFetch surfaces structured `{code, message}` error details so
//      callers can branch on `code === "provider_unavailable"`.

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const tripBuilder = readFileSync(
  new URL('../src/components/trips/TripBuilderForm.tsx', import.meta.url),
  'utf8',
);
const optimizeModal = readFileSync(
  new URL('../src/components/trips/OptimizeTripModal.tsx', import.meta.url),
  'utf8',
);
const apiClient = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url),
  'utf8',
);

test('TripBuilderForm: shows honest provider-unavailable copy', () => {
  assert.match(
    tripBuilder,
    /provider-backed search is not enabled yet/i,
    'Expected provider-unavailable copy referencing provider-backed search.',
  );
  assert.match(
    tripBuilder,
    /create a blank trip and add items manually/i,
    'Expected manual blank-trip CTA copy.',
  );
});

test('TripBuilderForm: branches on provider_unavailable / 503 from backend', () => {
  assert.match(
    tripBuilder,
    /code\s*===\s*"provider_unavailable"/,
    'Expected explicit branch on backend code === "provider_unavailable".',
  );
  assert.match(
    tripBuilder,
    /status\s*===\s*503/,
    'Expected explicit branch on HTTP 503.',
  );
});

test('TripBuilderForm: keeps manual trip creation available via createTrip()', () => {
  assert.match(
    tripBuilder,
    /createTrip\b/,
    'Expected manual trip creation to call createTrip() so users are not stuck.',
  );
});

test('OptimizeTripModal: removed misleading "Try adjusting your dates" copy', () => {
  assert.doesNotMatch(
    optimizeModal,
    /Try adjusting your dates/,
    'OptimizeTripModal must not blame dates when provider-backed search is unavailable.',
  );
});

test('OptimizeTripModal: shows honest provider-unavailable copy', () => {
  assert.match(
    optimizeModal,
    /Provider-backed flight and hotel search is not enabled yet/i,
    'Expected honest provider-unavailable body copy.',
  );
  assert.match(
    optimizeModal,
    /You can still build the trip manually/i,
    'Expected guidance that the user can still build the trip manually.',
  );
  assert.match(
    optimizeModal,
    /provider_unavailable/,
    'Expected a "provider_unavailable" phase distinct from generic error.',
  );
});

test('OptimizeTripModal: refuses to surface rows with mock book.example.com booking URLs', () => {
  // Even when /search/flights or /search/hotels returns *non-empty* rows
  // (BLOCK_LEGACY_PRODUCT_MOCK off), the modal must detect mock-derived
  // booking URLs and switch to provider_unavailable instead of letting
  // the user click "Select This Plan" — otherwise mock rows leak into
  // /trips/{id}/days/{dayId}/itinerary-items via addOptimizedFlightToDay
  // / addOptimizedHotelToTrip.
  assert.match(
    optimizeModal,
    /book\.example\.com/,
    'Expected the mock host sentinel to appear in the client guard.',
  );
  assert.match(
    optimizeModal,
    /anyMockDerivedFlights/,
    'Expected a mock-flight detection helper used before phase=results.',
  );
  assert.match(
    optimizeModal,
    /anyMockDerivedHotels/,
    'Expected a mock-hotel detection helper used before phase=results.',
  );
});

test('apiFetch: surfaces structured {code, message} error details', () => {
  assert.match(
    apiClient,
    /err\.code\s*=\s*obj\.code/,
    'apiFetch must attach structured error code so callers can branch on it.',
  );
  assert.match(
    apiClient,
    /err\.status\s*=\s*res\.status/,
    'apiFetch must attach HTTP status so callers can branch on 503.',
  );
});
