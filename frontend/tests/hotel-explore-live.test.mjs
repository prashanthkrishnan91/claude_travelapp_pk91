/**
 * Hotel Explore — canonical vertical search architecture.
 *
 * Structural tests proving Explore Hotels uses the canonical
 * /search/hotels Google Places endpoint (searchHotelsExplore) and does NOT
 * go through the AI Concierge route:
 *
 * 1. searchHotelsExplore is the search path — /search/hotels, not Concierge.
 * 2. No callConciergeSearch import/call, no /ai/concierge/search reference.
 * 3. Discovery-only contract: no price, rate, booking, or availability fields.
 * 4. No Tavily / live-research / concierge-note rendering.
 * 5. HotelCard renders name, rating, address, maps link, ResultActionSheet.
 * 6. Compare prices CTA preserved (PR #367 Google Hotels link-out).
 * 7. Google Places place id flows through as providerIdentity.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const hotelFlow = readFileSync(
  new URL('../src/components/explore/HotelExploreFlow.tsx', import.meta.url), 'utf8');
const apiClient = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url), 'utf8');

// ── 1. Canonical vertical-search path ──────────────────────────────────────

test('HotelExploreFlow imports and calls searchHotelsExplore', () => {
  assert.match(hotelFlow, /import\s*\{\s*searchHotelsExplore\s*\}\s*from\s*"@\/lib\/api"/);
  assert.match(hotelFlow, /searchHotelsExplore\(/);
});

test('HotelExploreFlow imports ExploreHotelResult type from api', () => {
  assert.match(hotelFlow, /ExploreHotelResult/);
});

test('searchHotelsExplore helper exists in api.ts and hits /search/hotels', () => {
  assert.match(apiClient, /export async function searchHotelsExplore\(/);
  const start = apiClient.indexOf('export async function searchHotelsExplore(');
  const slice = apiClient.slice(start, start + 1200);
  assert.match(slice, /"\/search\/hotels"/);
  assert.doesNotMatch(slice, /concierge/i);
});

// ── 2. No AI Concierge dependency ──────────────────────────────────────────

test('HotelExploreFlow does not import or call callConciergeSearch', () => {
  assert.doesNotMatch(hotelFlow, /callConciergeSearch/);
});

test('HotelExploreFlow does not reference /ai/concierge/search', () => {
  assert.doesNotMatch(hotelFlow, /\/ai\/concierge\/search/);
});

test('HotelExploreFlow does not reference allowLiveResearch / live research / Tavily', () => {
  assert.doesNotMatch(hotelFlow, /allowLiveResearch/);
  assert.doesNotMatch(hotelFlow, /live.?research/i);
  assert.doesNotMatch(hotelFlow, /tavily/i);
});

// ── 3. Discovery-only contract — no price/rate/booking fields ──────────────

test('HotelExploreFlow does not render pricePerNight / bookingUrl', () => {
  assert.doesNotMatch(hotelFlow, /pricePerNight/);
  assert.doesNotMatch(hotelFlow, /bookingUrl/);
});

test('HotelExploreFlow does not render totalPrice, currency, availability claims', () => {
  assert.doesNotMatch(hotelFlow, /totalPrice/);
  assert.doesNotMatch(hotelFlow, /\.currency/);
  assert.doesNotMatch(hotelFlow, /isAvailable/);
  assert.doesNotMatch(hotelFlow, /cancellation/i);
});

test('HotelExploreFlow does not show "book now" or "best deal" copy', () => {
  assert.doesNotMatch(hotelFlow, /book now/i);
  assert.doesNotMatch(hotelFlow, /best deal/i);
});

// ── 4. No concierge / LLM note rendering ───────────────────────────────────

test('HotelCard does not render concierge / displayWhy / whyPick notes', () => {
  assert.doesNotMatch(hotelFlow, /displayWhy/);
  assert.doesNotMatch(hotelFlow, /whyPick/);
  assert.doesNotMatch(hotelFlow, /conciergeNote/);
});

// ── 5. Search context preserved in ExploreResultContext ────────────────────

test('HotelExploreFlow sets vertical: "hotels" in ExploreResultContext', () => {
  assert.match(hotelFlow, /vertical: "hotels"/);
});

test('HotelExploreFlow preserves checkIn/checkOut/guests in context', () => {
  assert.match(hotelFlow, /dates: \{ checkIn/);
  assert.match(hotelFlow, /checkOut/);
  assert.match(hotelFlow, /guests: lastForm/);
});

test('HotelExploreFlow flows Google Places place id as providerIdentity', () => {
  assert.match(hotelFlow, /providerIdentity: h\.googlePlaceId/);
});

// ── 6. HotelCard content ───────────────────────────────────────────────────

test('HotelCard renders rating with Star icon', () => {
  assert.match(hotelFlow, /h\.rating/);
  assert.match(hotelFlow, /Star/);
});

test('HotelCard renders address line', () => {
  assert.match(hotelFlow, /h\.address/);
});

test('HotelCard renders Google Maps external link', () => {
  assert.match(hotelFlow, /h\.googleMapsUri/);
  assert.match(hotelFlow, /ExternalLink/);
});

test('HotelCard wires ResultActionSheet (Save / More actions)', () => {
  assert.match(hotelFlow, /import.*ResultActionSheet/);
  assert.match(hotelFlow, /<ResultActionSheet/);
});

test('HotelExploreFlow renders hotel-results testid on result list', () => {
  assert.match(hotelFlow, /data-testid="hotel-results"/);
});

// ── 7. Compare prices CTA preserved (PR #367) ──────────────────────────────

test('HotelCard renders a Compare prices CTA (labeled link-out)', () => {
  assert.match(hotelFlow, /Compare prices/);
  assert.match(hotelFlow, /data-testid="hotel-compare-cta"/);
});

test('Hotel compare CTA is an external link (target=_blank, rel=noopener)', () => {
  assert.match(hotelFlow, /target="_blank"/);
  assert.match(hotelFlow, /rel="noopener noreferrer"/);
});

test('buildHotelCompareUrl utility targets Google Hotels search URL', () => {
  assert.match(hotelFlow, /function buildHotelCompareUrl/);
  assert.match(hotelFlow, /google\.com\/travel\/hotels/);
  assert.doesNotMatch(hotelFlow, /expedia\.com/i);
  assert.doesNotMatch(hotelFlow, /booking\.com/i);
  assert.doesNotMatch(hotelFlow, /trivago\.com/i);
});

test('buildHotelCompareUrl uses encodeURIComponent for deterministic encoding', () => {
  assert.match(hotelFlow, /encodeURIComponent/);
});

test('buildHotelCompareUrl uses adults= param (not guests=) for structured Google Hotels handoff', () => {
  assert.match(hotelFlow, /adults=\$\{guests\}/);
  assert.doesNotMatch(hotelFlow, /guests=\$\{guests\}/);
});

test('buildHotelCompareUrl q fallback includes dates and guest count context', () => {
  // q is built from qParts including checkIn, checkOut, and guests text
  assert.match(hotelFlow, /qParts\.push.*guest/);
  assert.match(hotelFlow, /qParts\.push.*to /);
});

test('buildContext savedPayload includes compareLink metadata', () => {
  assert.match(hotelFlow, /compareLink/);
});

test('Hotel compare CTA renders with Search icon (not a booking icon)', () => {
  assert.match(hotelFlow, /Search.*className/);
  assert.doesNotMatch(hotelFlow, /ShoppingCart/);
  assert.doesNotMatch(hotelFlow, /CreditCard/);
});
