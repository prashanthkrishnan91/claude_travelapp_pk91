/**
 * Hotel Explore Live — Stage 2A Slice 5C
 *
 * Focused structural tests verifying the Hotels vertical is wired as
 * discovery-only lodging cards via the tripless AI Concierge:
 *
 * 1. callConciergeSearch is the search path — no mock/legacy routes.
 * 2. Discovery-only contract: no price, rate, booking, or availability fields rendered.
 * 3. Search context (destination, dates, guests) preserved in ExploreResultContext.
 * 4. HotelCard renders name, stars, rating, address/area, why note, maps link, ResultActionSheet.
 * 5. No DeferredState / "coming soon" copy remains.
 * 6. Google Places providerPlaceId extracted as providerIdentity.
 * 7. No fake hotel provider, no mock rows, no /search/hotels route.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const hotelFlow = readFileSync(
  new URL('../src/components/explore/HotelExploreFlow.tsx', import.meta.url), 'utf8');

// ── 1. Live search path ────────────────────────────────────────────────────

test('HotelExploreFlow imports and calls callConciergeSearch', () => {
  assert.match(hotelFlow, /import.*callConciergeSearch.*from.*api/);
  assert.match(hotelFlow, /callConciergeSearch\(null,/);
});

test('HotelExploreFlow passes null tripId (tripless Concierge pattern)', () => {
  assert.match(hotelFlow, /callConciergeSearch\(null,\s*query/);
});

test('HotelExploreFlow reads res.hotels from Concierge response', () => {
  assert.match(hotelFlow, /res\.hotels/);
});

test('HotelExploreFlow imports UnifiedHotelResult type from api', () => {
  assert.match(hotelFlow, /UnifiedHotelResult/);
  assert.match(hotelFlow, /from.*@\/lib\/api/);
});

// ── 2. Discovery-only contract — no price/rate/booking fields rendered ─────

test('HotelExploreFlow does not render pricePerNight', () => {
  assert.doesNotMatch(hotelFlow, /pricePerNight/);
});

test('HotelExploreFlow does not render bookingUrl', () => {
  assert.doesNotMatch(hotelFlow, /bookingUrl/);
});

test('HotelExploreFlow does not render totalPrice or currency fields', () => {
  assert.doesNotMatch(hotelFlow, /totalPrice/);
  assert.doesNotMatch(hotelFlow, /\.currency/);
});

test('HotelExploreFlow does not render availability or cancellation claims', () => {
  assert.doesNotMatch(hotelFlow, /isAvailable/);
  assert.doesNotMatch(hotelFlow, /cancellation/i);
});

test('HotelExploreFlow does not show "book now" or "best deal" copy', () => {
  assert.doesNotMatch(hotelFlow, /book now/i);
  assert.doesNotMatch(hotelFlow, /best deal/i);
});

// ── 3. Search context preserved in ExploreResultContext ──────────────────

test('HotelExploreFlow sets vertical: "hotels" in ExploreResultContext', () => {
  assert.match(hotelFlow, /vertical: "hotels"/);
});

test('HotelExploreFlow preserves checkIn and checkOut in dates context', () => {
  assert.match(hotelFlow, /dates: \{ checkIn/);
  assert.match(hotelFlow, /checkOut/);
});

test('HotelExploreFlow preserves guests count in ExploreResultContext', () => {
  assert.match(hotelFlow, /guests: lastForm/);
});

test('HotelExploreFlow extracts providerPlaceId as providerIdentity', () => {
  assert.match(hotelFlow, /providerPlaceId/);
  assert.match(hotelFlow, /providerIdentity/);
});

// ── 4. HotelCard content ─────────────────────────────────────────────────

test('HotelCard renders stars field', () => {
  assert.match(hotelFlow, /h\.stars/);
  assert.match(hotelFlow, /★/);
});

test('HotelCard renders rating with Star icon', () => {
  assert.match(hotelFlow, /h\.rating/);
  assert.match(hotelFlow, /Star/);
});

test('HotelCard renders areaLabel or address', () => {
  assert.match(hotelFlow, /areaLabel/);
  assert.match(hotelFlow, /address/);
});

test('HotelCard renders displayWhy / whyPick note', () => {
  assert.match(hotelFlow, /displayWhy/);
  assert.match(hotelFlow, /whyPick/);
});

test('HotelCard renders Google Maps external link when mapsLink present', () => {
  assert.match(hotelFlow, /h\.mapsLink/);
  assert.match(hotelFlow, /ExternalLink/);
});

test('HotelCard wires ResultActionSheet', () => {
  assert.match(hotelFlow, /import.*ResultActionSheet/);
  assert.match(hotelFlow, /<ResultActionSheet/);
});

test('HotelCard renders hotel-results testid on result list', () => {
  assert.match(hotelFlow, /data-testid="hotel-results"/);
});

// ── 5. No deferred-state remnants ────────────────────────────────────────

test('HotelExploreFlow does not contain deferred-state testid', () => {
  assert.doesNotMatch(hotelFlow, /hotel-deferred-state/);
});

test('HotelExploreFlow does not contain "coming soon" copy', () => {
  assert.doesNotMatch(hotelFlow, /coming soon/i);
});

test('HotelExploreFlow does not import Construction icon (deferred UI)', () => {
  assert.doesNotMatch(hotelFlow, /Construction/);
});

// ── 6. No fake/mock provider ─────────────────────────────────────────────

test('HotelExploreFlow does not reference /search/hotels route', () => {
  assert.doesNotMatch(hotelFlow, /\/search\/hotels/);
});

test('HotelExploreFlow does not reference searchHotels function', () => {
  assert.doesNotMatch(hotelFlow, /searchHotels/);
});

test('HotelExploreFlow does not reference Duffel or booking providers', () => {
  assert.doesNotMatch(hotelFlow, /[Dd]uffel/);
  assert.doesNotMatch(hotelFlow, /[Bb]ooking\.com/);
});

// ── 7. originalPayload normalization for saved-item display snapshots ─────

test('buildContext savedPayload includes normalized address from supportingDetails', () => {
  assert.match(hotelFlow, /address: h\.supportingDetails/);
});

test('buildContext savedPayload includes googleMapsUri normalized from mapsLink', () => {
  assert.match(hotelFlow, /googleMapsUri: h\.mapsLink/);
});

test('buildContext savedPayload preserves mapsLink field', () => {
  assert.match(hotelFlow, /mapsLink: h\.mapsLink/);
});

test('buildContext savedPayload includes search context fields destination, checkIn, checkOut, guests', () => {
  assert.match(hotelFlow, /destination: dest/);
  assert.match(hotelFlow, /checkIn: lastForm/);
  assert.match(hotelFlow, /checkOut: lastForm/);
  assert.match(hotelFlow, /guests: lastForm/);
});

test('buildContext savedPayload does not assign pricePerNight or bookingUrl', () => {
  assert.doesNotMatch(hotelFlow, /pricePerNight\s*:/);
  assert.doesNotMatch(hotelFlow, /bookingUrl\s*:/);
});

test('buildContext savedPayload does not assign totalPrice, currency, isAvailable, or cancellation', () => {
  assert.doesNotMatch(hotelFlow, /totalPrice\s*:/);
  assert.doesNotMatch(hotelFlow, /currency\s*:/);
  assert.doesNotMatch(hotelFlow, /isAvailable\s*:/);
  assert.doesNotMatch(hotelFlow, /cancellation\s*:/);
});
