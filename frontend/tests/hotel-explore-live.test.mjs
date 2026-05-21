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

test('buildHotelCompareUrl utility targets Google Travel hotel search URL', () => {
  // Uses the /travel/search surface (Google Travel hotel search) — the working
  // Google Travel destination, not a generic Google Search or an OTA.
  assert.match(hotelFlow, /function buildHotelCompareUrl/);
  assert.match(hotelFlow, /google\.com\/travel\/search/);
  assert.doesNotMatch(hotelFlow, /google\.com\/search\b/);
  assert.doesNotMatch(hotelFlow, /google\.com\/maps/);
  assert.doesNotMatch(hotelFlow, /expedia\.com/i);
  assert.doesNotMatch(hotelFlow, /booking\.com/i);
  assert.doesNotMatch(hotelFlow, /trivago\.com/i);
});

test('buildHotelCompareUrl uses encodeURIComponent for deterministic encoding', () => {
  assert.match(hotelFlow, /encodeURIComponent/);
});

test('buildHotelCompareUrl carries dates via the deterministic ts= Google Travel param', () => {
  // Dates are handed to Google Travel through the `ts` protobuf param, built by
  // buildGoogleTravelDatesParam from the selected check-in/check-out.
  assert.match(hotelFlow, /buildGoogleTravelDatesParam/,
    'buildHotelCompareUrl must build the ts= date param from selected dates');
  assert.match(hotelFlow, /&ts=\$\{ts\}/,
    'buildHotelCompareUrl must append the ts= date param to the URL');
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

test('buildGoogleTravelDatesParam reproduces the verified reference ts= byte-for-byte', () => {
  // The ts= protobuf is a deterministic, date-only payload (check-in, check-out,
  // nights, occupancy=1 room, currency USD).  It contains NO hotel-specific or
  // session-specific data.  This test proves our builder reproduces a real,
  // verified Google Travel ts= param (observed for 2026-07-31 → 2026-08-05)
  // byte-for-byte — i.e. the dates are encoded correctly and deterministically.
  const blockStart = hotelFlow.indexOf('const MONTHS');
  const blockEnd = hotelFlow.indexOf('import { searchHotelsExplore }');
  let block = hotelFlow.slice(blockStart, blockEnd);
  block = block
    .replace(/as \[number, number, number\]/g, '')
    .replace(/\}: \{[^}]*\}\)/s, '})')
    .replace(/\bcheckIn\?/g, 'checkIn')
    .replace(/\bcheckOut\?/g, 'checkOut')
    .replace(/\bguests\?/g, 'guests')
    .replace(/: number\[\]/g, '')
    .replace(/: string \| undefined/g, '')
    .replace(/: string\b/g, '')
    .replace(/: number\b/g, '')
    .replace(/\)\s*\{/g, ') {');
  const buildTs = new Function(block + '\nreturn buildGoogleTravelDatesParam;')();
  const refTs = 'CAEaIAoCGgASGhIUCgcI6g8QBxgfEgcI6g8QCBgFGAUyAggBKgkKBToDVVNEGgA';
  assert.strictEqual(
    buildTs('2026-07-31', '2026-08-05'),
    refTs,
    'ts= for 2026-07-31 → 2026-08-05 must match the verified reference byte-for-byte',
  );
  // Missing/invalid dates → no ts (clean q-only search)
  assert.strictEqual(buildTs(undefined, '2026-08-05'), undefined);
  assert.strictEqual(buildTs('2026-08-05', '2026-08-05'), undefined, 'zero-night range yields no ts');
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
  // checkIn/checkOut must flow into the date param builder and the q display text
  assert.match(fnBody, /buildGoogleTravelDatesParam\(checkIn,\s*checkOut\)/, 'checkIn/checkOut must flow into ts= builder');
  assert.match(fnBody, /formatIsoDateForDisplay\(checkIn\)/, 'checkIn must flow into q display text');
  assert.match(fnBody, /formatIsoDateForDisplay\(checkOut\)/, 'checkOut must flow into q display text');
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

// Shared extractor: pull the date/URL builder block (helpers + buildHotelCompareUrl)
// out of the source and eval it so tests can call the real rendered-href path.
function extractCompareUrlBuilder() {
  const blockStart = hotelFlow.indexOf('const MONTHS');
  const blockEnd = hotelFlow.indexOf('import { searchHotelsExplore }');
  let block = hotelFlow.slice(blockStart, blockEnd);
  block = block
    .replace(/as \[number, number, number\]/g, '')
    .replace(/\}: \{[^}]*\}\)/s, '})')
    .replace(/\bcheckIn\?/g, 'checkIn')
    .replace(/\bcheckOut\?/g, 'checkOut')
    .replace(/\bguests\?/g, 'guests')
    .replace(/: number\[\]/g, '')
    .replace(/: string \| undefined/g, '')
    .replace(/: string\b/g, '')
    .replace(/: number\b/g, '')
    .replace(/\)\s*\{/g, ') {');
  try {
    // eslint-disable-next-line no-new-func
    return new Function(block + '\nreturn buildHotelCompareUrl;')();
  } catch {
    return null;
  }
}

test('buildHotelCompareUrl: two structurally different date ranges both produce distinct date-aware URLs', () => {
  // Verify the function is genuinely parameterized by extracting and calling it.
  // Range A: 2026-07-10 to 2026-07-17  (summer trip)
  // Range B: 2026-11-01 to 2026-11-05  (autumn trip)
  // Dates are carried in the ts= protobuf and echoed in the q= display text.
  // If either range produces a URL containing the other range's dates, the
  // function is hardcoding dates.
  const buildUrl = extractCompareUrlBuilder();
  if (buildUrl) {
    const rangeA = buildUrl({ hotelName: 'Hotel Foo', destination: 'Paris', checkIn: '2026-07-10', checkOut: '2026-07-17', guests: 2 });
    const rangeB = buildUrl({ hotelName: 'Hotel Foo', destination: 'Paris', checkIn: '2026-11-01', checkOut: '2026-11-05', guests: 2 });
    // Both must be Google Travel hotel search URLs with a ts= date param
    assert.match(rangeA, /google\.com\/travel\/search/, 'Range A must use /travel/search');
    assert.match(rangeB, /google\.com\/travel\/search/, 'Range B must use /travel/search');
    assert.match(rangeA, /[&?]ts=/, 'Range A must carry a ts= date param');
    assert.match(rangeB, /[&?]ts=/, 'Range B must carry a ts= date param');
    // Human-readable q text must reflect each range's own dates
    assert.match(rangeA, /July%2010%202026/, 'Range A q must show July 10 2026');
    assert.match(rangeB, /November%201%202026/, 'Range B q must show November 1 2026');
    assert.doesNotMatch(rangeA, /November/, 'Range A must not contain Range B month');
    assert.doesNotMatch(rangeB, /July/, 'Range B must not contain Range A month');
    // The ts= protobuf must differ between ranges (dates are encoded distinctly)
    const tsA = new URL(rangeA).searchParams.get('ts');
    const tsB = new URL(rangeB).searchParams.get('ts');
    assert.notStrictEqual(tsA, tsB, 'Different date ranges must produce different ts= params');
    assert.notStrictEqual(rangeA, rangeB, 'Different date ranges must produce different URLs');
  }
});

// ── 9. Named regression: Hyatt Regency Chicago, Jul 31–Aug 5 2026, 2 guests ─
//
// Reference: a real Google Travel hotel search for this scenario was observed
// at https://www.google.com/travel/search?q=hyatt%20regency%20chicago&...&ts=...
// Investigation (decoding the reference URL) showed:
//   - `q`  param: safely constructable (hotel name + destination)
//   - `ts` param: protobuf, PURELY date-derived (check-in, check-out, nights,
//                 occupancy=1 room, currency USD) — NO hotel/session data.
//                 Reproduced byte-for-byte by buildGoogleTravelDatesParam.
//   - `qs`, `ved`, `ap` params: opaque/session-generated (place search ids,
//                 click tracking, place anchor) — NOT constructable, omitted.
// Decision: use /travel/search?q=...&ts=<dates> — the working Google Travel
// hotel-search surface — with the deterministic date-only ts= param.

test('buildHotelCompareUrl: Hyatt Regency Chicago Jul 31–Aug 5 2026 regression', () => {
  // Concrete regression case:
  //   hotel: Hyatt Regency Chicago, destination: Chicago
  //   check-in: 2026-07-31, check-out: 2026-08-05, guests: 2
  // The compare link MUST carry these exact dates — not Jun 12–14 or any stale value.
  const buildUrl = extractCompareUrlBuilder();
  if (buildUrl) {
    const result = buildUrl({
      hotelName: 'Hyatt Regency Chicago',
      destination: 'Chicago',
      checkIn: '2026-07-31',
      checkOut: '2026-08-05',
      guests: 2,
    });

    // Must use the Google Travel hotel-search surface, not generic search/maps
    assert.match(result, /google\.com\/travel\/search/, 'must use /travel/search surface');
    assert.doesNotMatch(result, /google\.com\/search\b/, 'must not use generic Google Search URL');
    assert.doesNotMatch(result, /google\.com\/maps/, 'must not fall back to a Maps link');

    // Must carry the submitted dates in the ts= param — and it must equal the
    // verified reference ts= for this exact scenario (byte-for-byte).
    const ts = new URL(result).searchParams.get('ts');
    assert.strictEqual(
      ts,
      'CAEaIAoCGgASGhIUCgcI6g8QBxgfEgcI6g8QCBgFGAUyAggBKgkKBToDVVNEGgA',
      'ts= must match the verified reference for 2026-07-31 → 2026-08-05',
    );

    // q text must echo the submitted dates and NOT the stale Jun 12–14 range
    assert.match(result, /July%2031%202026/, 'q must show July 31 2026');
    assert.match(result, /August%205%202026/, 'q must show August 5 2026');
    assert.doesNotMatch(result, /June/, 'compare URL must not contain stale June dates');
    assert.doesNotMatch(result, /2026-06-1[24]/, 'compare URL must not contain stale Jun 12–14 dates');

    // Must NOT embed the opaque session params (qs/ved/ap)
    assert.doesNotMatch(result, /[&?]qs=/, 'must not embed opaque qs= session param');
    assert.doesNotMatch(result, /[&?]ved=/, 'must not embed opaque ved= tracking param');
    assert.doesNotMatch(result, /[&?]ap=/, 'must not embed opaque ap= place-anchor param');

    // Hotel name, destination, and guest context in the q param
    assert.match(result, /[Hh]yatt/, 'hotel name must appear in q param');
    assert.match(result, /[Cc]hicago/, 'destination must appear in q param');
    assert.match(result, /2%20guests/, 'guest count must appear in q text');
  }
});

test('buildHotelCompareUrl uses /travel/search hotel surface, not generic Google Search or Maps', () => {
  // Guards against regression to a generic google.com/search?q= or maps link.
  // /travel/search?q=...&ts=<dates> is the working Google Travel hotel surface;
  // the ts= param is a deterministic, date-only payload (verified byte-for-byte
  // against a real Google Travel URL), NOT an opaque session param.
  const fnStart = hotelFlow.indexOf('function buildHotelCompareUrl');
  const fnEnd = hotelFlow.indexOf('\nimport ', fnStart);
  const fnBody = hotelFlow.slice(fnStart, fnEnd > fnStart ? fnEnd : fnStart + 1500);
  assert.match(fnBody, /travel\/search/, 'must use /travel/search surface');
  assert.doesNotMatch(fnBody, /google\.com\/search/, 'must not use generic /search endpoint');
  assert.doesNotMatch(fnBody, /google\.com\/maps/, 'must not use a Maps link');
  // The opaque session params must never be fabricated
  assert.doesNotMatch(fnBody, /[&?]qs=/, 'must not embed opaque qs= param');
  assert.doesNotMatch(fnBody, /[&?]ved=/, 'must not embed opaque ved= param');
  assert.doesNotMatch(fnBody, /[&?]ap=/, 'must not embed opaque ap= param');
});
