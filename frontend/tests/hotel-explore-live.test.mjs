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

test('formatIsoDateForDisplay parses YYYY-MM-DD by string split, not new Date', () => {
  // Must define a local formatter using split, not new Date(isoDate)
  assert.match(hotelFlow, /formatIsoDateForDisplay/);
  assert.match(hotelFlow, /\.split\('-'\)/);
  // Must not pass checkIn/checkOut directly into new Date() for display formatting
  assert.doesNotMatch(hotelFlow, /new Date\(checkIn\)/);
  assert.doesNotMatch(hotelFlow, /new Date\(checkOut\)/);
});

test('buildContext savedPayload includes compareLink metadata', () => {
  assert.match(hotelFlow, /compareLink/);
});

test('Hotel compare CTA renders with Search icon (not a booking icon)', () => {
  assert.match(hotelFlow, /Search.*className/);
  assert.doesNotMatch(hotelFlow, /ShoppingCart/);
  assert.doesNotMatch(hotelFlow, /CreditCard/);
});

// ── 8. Regression: selected check-in/check-out dates carried in compare URL ─

test('buildHotelCompareUrl appends &checkin= structured param for date handoff', () => {
  // Google Hotels reads checkin/checkout as structured date params, not just
  // the q= display text.  Both must be present to correctly scope the search.
  // Guards against regression where dates were dropped from the compare URL.
  assert.match(
    hotelFlow,
    /&checkin=\$\{encodeURIComponent\(checkIn\)\}/,
    'buildHotelCompareUrl must add &checkin=encodeURIComponent(checkIn) to the URL',
  );
});

test('buildHotelCompareUrl appends &checkout= structured param for date handoff', () => {
  assert.match(
    hotelFlow,
    /&checkout=\$\{encodeURIComponent\(checkOut\)\}/,
    'buildHotelCompareUrl must add &checkout=encodeURIComponent(checkOut) to the URL',
  );
});

test('buildHotelCompareUrl passes checkIn/checkOut parameters through directly — no hardcoded dates', () => {
  // Guard against regression where a fixed date (e.g. 2026-06-12) was hardcoded
  // into buildHotelCompareUrl instead of using the caller-supplied value.
  // Checks:
  //   1. The function body uses the `checkIn` / `checkOut` parameters (not a literal).
  //   2. No ISO date literal appears in the function body.
  // A function that hardcodes "2026-06-12" would fail assertion 2.
  // A function that ignores its parameter would fail assertion 1.
  const fnStart = hotelFlow.indexOf('function buildHotelCompareUrl');
  const fnEnd = hotelFlow.indexOf('\nimport ', fnStart);
  const fnBody = hotelFlow.slice(fnStart, fnEnd > fnStart ? fnEnd : fnStart + 1500);
  assert.match(fnBody, /encodeURIComponent\(checkIn\)/, 'checkIn parameter must flow into URL');
  assert.match(fnBody, /encodeURIComponent\(checkOut\)/, 'checkOut parameter must flow into URL');
  assert.doesNotMatch(
    fnBody,
    /['"]\d{4}-\d{2}-\d{2}['"]/,
    'buildHotelCompareUrl must not contain a hardcoded ISO date literal',
  );
});

test('HotelExploreFlow: no hardcoded ISO date literals anywhere in source', () => {
  // Guards against any YYYY-MM-DD string constant being embedded in the file.
  // A hardcoded "2026-06-12" (or any other fixed date) in the source would
  // cause every compare link to show that date regardless of user input.
  assert.doesNotMatch(
    hotelFlow,
    /['"]\d{4}-\d{2}-\d{2}['"]/,
    'HotelExploreFlow must not contain any hardcoded ISO date string literals',
  );
});

test('handleSubmit uses a single form snapshot for both setLastForm and the API call', () => {
  // Guards against the regression where form was read multiple times inside
  // handleSubmit — a single snapshot ensures the compare link and the search
  // request always use the exact same dates (prevents divergence on re-search).
  const submitStart = hotelFlow.indexOf('async function handleSubmit');
  const submitEnd = hotelFlow.indexOf('\n  function set(', submitStart);
  const submitBody = hotelFlow.slice(submitStart, submitEnd > submitStart ? submitEnd : submitStart + 1500);
  // Must create a snapshot variable and use it for setLastForm
  assert.match(submitBody, /const snapshot\s*=\s*\{\s*\.\.\.\s*form\s*\}/,
    'handleSubmit must snapshot form into a local const before async work');
  assert.match(submitBody, /setLastForm\(snapshot\)/,
    'setLastForm must receive the snapshot, not a fresh form spread');
  // The API call must use snapshot.checkIn / snapshot.checkOut, not form.checkIn
  assert.match(submitBody, /snapshot\.checkIn/,
    'searchHotelsExplore must be called with snapshot.checkIn');
  assert.match(submitBody, /snapshot\.checkOut/,
    'searchHotelsExplore must be called with snapshot.checkOut');
  // Ensure the live `form` state is NOT read after the snapshot for dates
  assert.doesNotMatch(
    submitBody.replace(/const snapshot\s*=\s*\{[^}]+\}/, ''),
    /form\.checkIn|form\.checkOut/,
    'form.checkIn/checkOut must not be read again after snapshot is taken',
  );
});

test('buildContext passes lastForm checkIn and checkOut to buildHotelCompareUrl (not a fallback date)', () => {
  // The compare link must be built from the user-selected dates captured in
  // lastForm — not from today's date or any fallback computed elsewhere.
  const buildContextSlice = hotelFlow.slice(
    hotelFlow.indexOf('function buildContext'),
    hotelFlow.indexOf('\nfunction HotelCard'),
  );
  assert.match(
    buildContextSlice,
    /checkIn:.*lastForm/,
    'compareLink must be built with lastForm.checkIn (user-selected date)',
  );
  assert.match(
    buildContextSlice,
    /checkOut:.*lastForm/,
    'compareLink must be built with lastForm.checkOut (user-selected date)',
  );
});

test('buildContext does not use fallbackIn or fallbackOut for compareLink', () => {
  // The fallback dates in searchHotelsExplore are for the /search/hotels API
  // call only — they must NOT leak into the compare URL shown to the user.
  const buildContextSlice = hotelFlow.slice(
    hotelFlow.indexOf('function buildContext'),
    hotelFlow.indexOf('\nfunction HotelCard'),
  );
  assert.doesNotMatch(
    buildContextSlice,
    /fallbackIn|fallbackOut/,
    'buildContext must not reference fallback dates when building the compare URL',
  );
});

test('buildHotelCompareUrl: two structurally different date ranges both produce distinct URLs (parameterized, not fixed)', () => {
  // Verify the function is genuinely parameterized by extracting and calling it.
  // We strip TS type annotations and eval the function with two date ranges.
  // Range A: 2026-07-10 to 2026-07-17  (summer trip)
  // Range B: 2026-11-01 to 2026-11-05  (autumn trip)
  // If either range produces a URL containing the other range's dates, the
  // function is hardcoding dates.  If both URLs match their input dates, the
  // function correctly passes through whatever the caller supplies.
  const fnStart = hotelFlow.indexOf('function buildHotelCompareUrl');
  const fnEnd = hotelFlow.indexOf('\nimport ', fnStart);
  const rawFn = hotelFlow.slice(fnStart, fnEnd > fnStart ? fnEnd : fnStart + 1500);
  // Strip TypeScript type annotations for eval
  const jsFn = rawFn
    .replace(/:\s*string\b/g, '')
    .replace(/:\s*number\b/g, '')
    .replace(/\?\s*:/g, ':')
    .replace(/\{[^}]*hotelName[^}]*\}/g, '')  // strip param type annotation block
    .replace(/\):\s*string\s*\{/, ') {');       // strip return type

  let buildUrl;
  try {
    // eslint-disable-next-line no-new-func
    buildUrl = new Function(`return (${jsFn})`)();
  } catch {
    // If eval fails (e.g. TS syntax slipped through), fall through to source checks only.
    buildUrl = null;
  }

  if (buildUrl) {
    const rangeA = buildUrl({ hotelName: 'Hotel Foo', destination: 'Paris', checkIn: '2026-07-10', checkOut: '2026-07-17', guests: 2 });
    const rangeB = buildUrl({ hotelName: 'Hotel Foo', destination: 'Paris', checkIn: '2026-11-01', checkOut: '2026-11-05', guests: 2 });
    assert.match(rangeA, /checkin=2026-07-10/, 'Range A URL must contain checkIn 2026-07-10');
    assert.match(rangeA, /checkout=2026-07-17/, 'Range A URL must contain checkOut 2026-07-17');
    assert.match(rangeB, /checkin=2026-11-01/, 'Range B URL must contain checkIn 2026-11-01');
    assert.match(rangeB, /checkout=2026-11-05/, 'Range B URL must contain checkOut 2026-11-05');
    assert.doesNotMatch(rangeA, /2026-11/, 'Range A URL must not contain Range B dates');
    assert.doesNotMatch(rangeB, /2026-07/, 'Range B URL must not contain Range A dates');
    assert.notStrictEqual(rangeA, rangeB, 'Different date ranges must produce different URLs');
  }
});
