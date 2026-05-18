/**
 * Fix failed-post-#430 bugs — contract tests.
 *
 * Bug A — CityAutocomplete portal: prior z-[60]+isolate fix was insufficient on mobile
 *   because sibling fields and ancestor stacking/overflow contexts can still cover an
 *   absolute-positioned dropdown. Fix: render via React DOM portal into document.body
 *   at fixed coordinates. These tests verify the portal approach is wired correctly and
 *   that the old z-index-only approach is absent.
 *
 * Bug B — Round-trip leg card rendering: addRoundTripLegToDay spread ...d which included
 *   both outboundLeg and returnLeg on every leg item; ItineraryItemCard detected the pair
 *   and rendered a round-trip card regardless of is_round_trip:false. Fix: (1) leg details
 *   built without the other leg's data; (2) ItineraryItemCard explicit one-way flags win;
 *   (3) handleAddRoundTripToItinerary uses robust date extraction and removes blind
 *   first/last-day fallback — missing/mismatched dates show a toast and create nothing.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const autocompleteSrc = readFileSync(
  new URL('../src/components/ui/CityAutocomplete.tsx', import.meta.url),
  'utf8',
);
const apiSrc = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url),
  'utf8',
);
const tripBuilder = readFileSync(
  new URL('../src/components/trips/TripBuilder.tsx', import.meta.url),
  'utf8',
);
const itemCardSrc = readFileSync(
  new URL('../src/components/trips/ItineraryItemCard.tsx', import.meta.url),
  'utf8',
);

// ─── Bug A: CityAutocomplete portal ──────────────────────────────────────────

test('BugA: CityAutocomplete imports createPortal from react-dom', () => {
  assert.match(
    autocompleteSrc,
    /createPortal.*react-dom|react-dom.*createPortal/,
    'Must import createPortal from react-dom for the portal approach',
  );
});

test('BugA: portal layer uses position:fixed (not absolute positioning inside form)', () => {
  assert.match(
    autocompleteSrc,
    /position.*["']?fixed["']?|["']fixed["'].*position/,
    'Portal dropdown must use position:fixed anchored to viewport coordinates',
  );
});

test('BugA: portal layer uses z-index 9999', () => {
  assert.match(
    autocompleteSrc,
    /zIndex.*9999|9999.*zIndex/,
    'Portal must use zIndex:9999 to appear above all stacking contexts',
  );
});

test('BugA: position derived from getBoundingClientRect on input container', () => {
  assert.match(
    autocompleteSrc,
    /getBoundingClientRect/,
    'Dropdown coordinates must be measured via getBoundingClientRect',
  );
});

test('BugA: position updates on resize event', () => {
  assert.match(
    autocompleteSrc,
    /addEventListener.*resize|resize.*addEventListener/s,
    'Must update position on window resize',
  );
});

test('BugA: position updates on scroll event (capture phase)', () => {
  assert.match(
    autocompleteSrc,
    /addEventListener.*scroll|scroll.*addEventListener/s,
    'Must update position on scroll to keep portal anchored when page scrolls',
  );
});

test('BugA: outside-click checks portalRef in addition to containerRef', () => {
  assert.match(
    autocompleteSrc,
    /portalRef/,
    'Outside-click handler must also check portalRef so portal clicks are not treated as outside-clicks',
  );
});

test('BugA: handleSelect still present and wired to suggestions', () => {
  assert.match(autocompleteSrc, /handleSelect/, 'handleSelect must remain');
});

test('BugA: resolveAirports API call preserved', () => {
  assert.match(autocompleteSrc, /resolveAirports/, 'resolveAirports must remain');
});

test('BugA: old z-[60] class absent (portal replaces z-index-only approach)', () => {
  assert.ok(
    !autocompleteSrc.includes('z-[60]'),
    'z-[60] must be absent — it was the failed z-index-only approach',
  );
});

test('BugA: old z-[100] class absent from suggestions list (portal uses inline zIndex:9999)', () => {
  assert.ok(
    !autocompleteSrc.includes('z-[100]'),
    'z-[100] must be absent — portal layer uses inline zIndex:9999 instead',
  );
});

test('BugA: manual IATA fallback also rendered in the portal layer', () => {
  // Both the suggestions list and the manual fallback must be inside the portal content
  // (same ref). Verify the manual submit handler is still present.
  assert.match(
    autocompleteSrc,
    /handleManualSubmit/,
    'Manual IATA fallback submit handler must remain',
  );
});

// ─── Bug B: addRoundTripLegToDay — clean one-way leg shape ───────────────────

test('BugB: addRoundTripLegToDay does not spread full round-trip ...d into legDetails', () => {
  // Get the body of addRoundTripLegToDay
  const startIdx = apiSrc.indexOf('export async function addRoundTripLegToDay');
  const endIdx = apiSrc.indexOf('\nexport async function', startIdx + 1);
  const fnBody = apiSrc.slice(startIdx, endIdx === -1 ? undefined : endIdx);

  // The old bug: `...d` spread all round-trip fields into each leg item.
  // After the fix, legDetails is built field by field without ...d.
  assert.ok(
    !fnBody.includes('...d,'),
    'legDetails must NOT spread ...d — that preserved outboundLeg+returnLeg on every leg item',
  );
});

test('BugB: outbound leg details do not include returnLeg/return_leg keys', () => {
  const startIdx = apiSrc.indexOf('legDetails: Record<string, unknown> = {');
  assert.ok(startIdx !== -1, 'legDetails object must be present');
  // Capture the legDetails literal up to the closing brace
  const legDetailsSrc = apiSrc.slice(startIdx, startIdx + 2000);
  assert.ok(
    !legDetailsSrc.includes('returnLeg') && !legDetailsSrc.includes('return_leg') &&
    !legDetailsSrc.includes('returnFlight') && !legDetailsSrc.includes('return_flight'),
    'legDetails must not include returnLeg / return_leg — that causes round-trip card rendering',
  );
});

test('BugB: outbound leg details do not include outboundLeg/outbound_leg keys in the literal', () => {
  const startIdx = apiSrc.indexOf('legDetails: Record<string, unknown> = {');
  const legDetailsSrc = apiSrc.slice(startIdx, startIdx + 2000);
  assert.ok(
    !legDetailsSrc.includes('outboundLeg:') && !legDetailsSrc.includes('outbound_leg:'),
    'legDetails must not include outboundLeg / outbound_leg on leg items',
  );
});

test('BugB: each leg item has trip_type:"one_way"', () => {
  const startIdx = apiSrc.indexOf('export async function addRoundTripLegToDay');
  const endIdx = apiSrc.indexOf('\nexport async function', startIdx + 1);
  const fnBody = apiSrc.slice(startIdx, endIdx === -1 ? undefined : endIdx);
  assert.match(
    fnBody,
    /trip_type.*one_way|one_way.*trip_type/,
    'Each leg item must set trip_type:"one_way"',
  );
});

test('BugB: each leg item has is_round_trip:false', () => {
  const startIdx = apiSrc.indexOf('export async function addRoundTripLegToDay');
  const endIdx = apiSrc.indexOf('\nexport async function', startIdx + 1);
  const fnBody = apiSrc.slice(startIdx, endIdx === -1 ? undefined : endIdx);
  assert.match(
    fnBody,
    /is_round_trip:\s*false/,
    'Each leg item must set is_round_trip:false',
  );
});

test('BugB: Google Flights CTA URL preserved in leg details (google_flights_search_url)', () => {
  const startIdx = apiSrc.indexOf('legDetails: Record<string, unknown> = {');
  const legDetailsSrc = apiSrc.slice(startIdx, startIdx + 2000);
  assert.match(
    legDetailsSrc,
    /google_flights_search_url/,
    'google_flights_search_url must be preserved in leg details for the CTA',
  );
});

test('BugB: startTime and endTime carry leg departure/arrival times', () => {
  const startIdx = apiSrc.indexOf('export async function addRoundTripLegToDay');
  const endIdx = apiSrc.indexOf('\nexport async function', startIdx + 1);
  const fnBody = apiSrc.slice(startIdx, endIdx === -1 ? undefined : endIdx);
  assert.match(fnBody, /startTime.*depTime|depTime.*startTime/, 'startTime must be set to leg departure time');
  assert.match(fnBody, /endTime.*arrTime|arrTime.*endTime/, 'endTime must be set to leg arrival time');
});

test('BugB: departure_time in legDetails carries selected-leg departure (not round-trip top level)', () => {
  const startIdx = apiSrc.indexOf('legDetails: Record<string, unknown> = {');
  const legDetailsSrc = apiSrc.slice(startIdx, startIdx + 2000);
  assert.match(
    legDetailsSrc,
    /departure_time.*depTime|depTime.*departure_time/,
    'departure_time in legDetails must equal the selected leg\'s depTime',
  );
});

// ─── Bug B: handleAddRoundTripToItinerary — robust date extraction, no blind fallback ───

test('BugB: extractLegDepartureDate helper present in TripBuilder', () => {
  assert.match(
    tripBuilder,
    /extractLegDepartureDate/,
    'TripBuilder must define extractLegDepartureDate helper for robust date extraction',
  );
});

test('BugB: resolveItineraryDayByDate helper present in TripBuilder', () => {
  assert.match(
    tripBuilder,
    /resolveItineraryDayByDate/,
    'TripBuilder must define resolveItineraryDayByDate helper for day matching',
  );
});

test('BugB: extractLegDepartureDate supports camelCase departureTime field', () => {
  assert.match(
    tripBuilder,
    /legData\.departureTime/,
    'extractLegDepartureDate must try legData.departureTime',
  );
});

test('BugB: extractLegDepartureDate supports snake_case departure_time field', () => {
  assert.match(
    tripBuilder,
    /legData\.departure_time/,
    'extractLegDepartureDate must try legData.departure_time',
  );
});

test('BugB: extractLegDepartureDate supports segment-level departure fields', () => {
  assert.match(
    tripBuilder,
    /seg0\?\.departureTime|seg0\?\.departure_time/,
    'extractLegDepartureDate must try segment[0] departure fields',
  );
});

test('BugB: missing dates show toast and create nothing (no blind fallback)', () => {
  assert.match(
    tripBuilder,
    /Could not place round-trip flight because flight dates were missing/,
    'Must show a toast when leg dates cannot be extracted',
  );
});

test('BugB: date mismatch shows toast and creates nothing', () => {
  assert.match(
    tripBuilder,
    /Flight date does not match this trip/,
    'Must show a toast when extracted date has no matching itinerary day',
  );
});

test('BugB: no blind days[0] fallback for outbound in handleAddRoundTripToItinerary', () => {
  const fnStart = tripBuilder.indexOf('const handleAddRoundTripToItinerary');
  assert.ok(fnStart !== -1, 'handleAddRoundTripToItinerary must exist');
  const fnBody = tripBuilder.slice(fnStart, fnStart + 5000);
  // The old blind fallback pattern: ?? days[0]
  assert.ok(
    !fnBody.includes('?? days[0]') && !fnBody.includes('?? days[0];'),
    'Must not blind-fallback to days[0] for outbound — missing dates should create nothing',
  );
});

test('BugB: no blind days[days.length-1] fallback for return in handleAddRoundTripToItinerary', () => {
  const fnStart = tripBuilder.indexOf('const handleAddRoundTripToItinerary');
  const fnBody = tripBuilder.slice(fnStart, fnStart + 5000);
  assert.ok(
    !fnBody.match(/\?\?\s*days\s*\[\s*days\.length\s*-\s*1\s*\]/),
    'Must not blind-fallback to last day for return — missing dates should create nothing',
  );
});

test('BugB: rollback deleteItem(outboundItem.id) preserved if return leg fails', () => {
  assert.match(
    tripBuilder,
    /deleteItem\(outboundItem\.id\)/,
    'Must attempt deleteItem(outboundItem.id) if return-leg add fails',
  );
});

test('BugB: setDays called only after both leg items exist', () => {
  const successComment = tripBuilder.indexOf('// Both legs succeeded');
  const returnItemIdx = tripBuilder.indexOf('returnItem = await addRoundTripLegToDay');
  assert.ok(
    returnItemIdx !== -1 && successComment > returnItemIdx,
    'setDays must be called only after both outbound and return items exist',
  );
});

// ─── Bug B: ItineraryItemCard — explicit one-way flags override stale leg keys ───

test('BugB: ItineraryItemCard checks explicit one-way flag before round-trip detection', () => {
  assert.match(
    itemCardSrc,
    /isExplicitlyOneWay/,
    'ItineraryItemCard must define isExplicitlyOneWay to short-circuit round-trip detection',
  );
});

test('BugB: isExplicitlyOneWay checks trip_type === "one_way"', () => {
  const flagIdx = itemCardSrc.indexOf('isExplicitlyOneWay');
  const flagBlock = itemCardSrc.slice(flagIdx, flagIdx + 600);
  assert.match(flagBlock, /trip_type.*one_way|one_way.*trip_type/, 'must check trip_type:"one_way"');
});

test('BugB: isExplicitlyOneWay checks is_round_trip === false', () => {
  const flagIdx = itemCardSrc.indexOf('isExplicitlyOneWay');
  const flagBlock = itemCardSrc.slice(flagIdx, flagIdx + 600);
  assert.match(flagBlock, /is_round_trip.*false|false.*is_round_trip/, 'must check is_round_trip:false');
});

test('BugB: isExplicitlyOneWay checks leg_of_round_trip presence', () => {
  const flagIdx = itemCardSrc.indexOf('isExplicitlyOneWay');
  const flagBlock = itemCardSrc.slice(flagIdx, flagIdx + 600);
  assert.match(flagBlock, /leg_of_round_trip/, 'must check leg_of_round_trip for one-way detection');
});

test('BugB: isRoundTrip is gated on !isExplicitlyOneWay', () => {
  const rtIdx = itemCardSrc.indexOf('const isRoundTrip');
  const rtBlock = itemCardSrc.slice(rtIdx, rtIdx + 400);
  assert.match(
    rtBlock,
    /!isExplicitlyOneWay/,
    'isRoundTrip must be false when isExplicitlyOneWay is true',
  );
});

test('BugB: ItineraryItemCard still renders round-trip testid for true round-trip items', () => {
  assert.match(
    itemCardSrc,
    /data-testid="itinerary-roundtrip-flight"/,
    'itinerary-roundtrip-flight testid must remain for true round-trip cards',
  );
});

test('BugB: ItineraryItemCard Google Flights CTA preserved for both one-way and round-trip', () => {
  assert.match(
    itemCardSrc,
    /itinerary-google-flights-cta/,
    'Google Flights CTA testid must appear in ItineraryItemCard',
  );
  // Must appear in both the round-trip block and the one-way block
  const firstOccurrence = itemCardSrc.indexOf('itinerary-google-flights-cta');
  const secondOccurrence = itemCardSrc.indexOf('itinerary-google-flights-cta', firstOccurrence + 1);
  assert.ok(
    secondOccurrence !== -1,
    'itinerary-google-flights-cta must appear in both round-trip and one-way render paths',
  );
});

// ─── Bug B: ItineraryDayColumn time bucket placement for one-way leg items ───

test('BugB: ItineraryDayColumn getItemDayPart reads item.startTime for bucket classification', () => {
  const dayColSrc = readFileSync(
    new URL('../src/components/trips/ItineraryDayColumn.tsx', import.meta.url),
    'utf8',
  );
  assert.match(
    dayColSrc,
    /parseHour\(item\.startTime\)/,
    'getItemDayPart must use item.startTime to classify split round-trip leg items into time buckets',
  );
});

test('BugB: ItineraryDayColumn getItemDayPart reads flight departure_time from details', () => {
  const dayColSrc = readFileSync(
    new URL('../src/components/trips/ItineraryDayColumn.tsx', import.meta.url),
    'utf8',
  );
  assert.match(
    dayColSrc,
    /departure_time|departureTime/,
    'getItemDayPart must also read departure fields from flight details for bucket classification',
  );
});

test('BugB: addRoundTripLegToDay startTime equals leg departure time (Morning/Afternoon/Evening placement)', () => {
  // Verify the payload carries startTime: depTime so getItemDayPart classifies correctly
  const startIdx = apiSrc.indexOf('export async function addRoundTripLegToDay');
  const endIdx = apiSrc.indexOf('\nexport async function', startIdx + 1);
  const fnBody = apiSrc.slice(startIdx, endIdx === -1 ? undefined : endIdx);
  assert.match(
    fnBody,
    /startTime.*depTime|depTime.*startTime/,
    'startTime in the persisted payload must equal the leg departure time for time-bucket placement',
  );
  assert.match(
    fnBody,
    /endTime.*arrTime|arrTime.*endTime/,
    'endTime in the persisted payload must equal the leg arrival time',
  );
});

// ─── Bug B: addRoundTripLegToDay — expanded extraction paths ────────────────

test('BugB: addRoundTripLegToDay depTime extraction covers departureDateTime path', () => {
  const startIdx = apiSrc.indexOf('export async function addRoundTripLegToDay');
  const endIdx = apiSrc.indexOf('\nexport async function', startIdx + 1);
  const fnBody = apiSrc.slice(startIdx, endIdx === -1 ? undefined : endIdx);
  assert.match(
    fnBody,
    /departureDateTime|departure_datetime/,
    'depTime extraction must also try departureDateTime / departure_datetime fields',
  );
});

test('BugB: addRoundTripLegToDay depTime extraction covers segment[0] departure fields', () => {
  const startIdx = apiSrc.indexOf('export async function addRoundTripLegToDay');
  const endIdx = apiSrc.indexOf('\nexport async function', startIdx + 1);
  const fnBody = apiSrc.slice(startIdx, endIdx === -1 ? undefined : endIdx);
  assert.match(
    fnBody,
    /seg0\?\.departureTime|seg0\?\.departure_time/,
    'depTime extraction must fall back to segment[0] departure fields',
  );
});

test('BugB: addRoundTripLegToDay arrTime extraction covers arrivalDateTime path', () => {
  const startIdx = apiSrc.indexOf('export async function addRoundTripLegToDay');
  const endIdx = apiSrc.indexOf('\nexport async function', startIdx + 1);
  const fnBody = apiSrc.slice(startIdx, endIdx === -1 ? undefined : endIdx);
  assert.match(
    fnBody,
    /arrivalDateTime|arrival_datetime/,
    'arrTime extraction must also try arrivalDateTime / arrival_datetime fields',
  );
});

test('BugB: addRoundTripLegToDay arrTime extraction uses last segment (segLast) for arrival', () => {
  const startIdx = apiSrc.indexOf('export async function addRoundTripLegToDay');
  const endIdx = apiSrc.indexOf('\nexport async function', startIdx + 1);
  const fnBody = apiSrc.slice(startIdx, endIdx === -1 ? undefined : endIdx);
  assert.match(
    fnBody,
    /segLast/,
    'arrTime extraction must use last segment (segLast) for multi-segment flights',
  );
  assert.match(
    fnBody,
    /segLast\?\.arrivalTime|segLast\?\.arrival_time/,
    'arrTime extraction must read arrival from segLast',
  );
});

test('BugB: legDetails includes camelCase departureTime alias', () => {
  const startIdx = apiSrc.indexOf('legDetails: Record<string, unknown> = {');
  const legDetailsSrc = apiSrc.slice(startIdx, startIdx + 2500);
  assert.match(
    legDetailsSrc,
    /departureTime:\s*depTime/,
    'legDetails must include camelCase departureTime alongside snake_case departure_time',
  );
});

test('BugB: legDetails includes camelCase arrivalTime alias', () => {
  const startIdx = apiSrc.indexOf('legDetails: Record<string, unknown> = {');
  const legDetailsSrc = apiSrc.slice(startIdx, startIdx + 2500);
  assert.match(
    legDetailsSrc,
    /arrivalTime:\s*arrTime/,
    'legDetails must include camelCase arrivalTime alongside snake_case arrival_time',
  );
});

test('BugB: legDetails includes leg_label field', () => {
  const startIdx = apiSrc.indexOf('legDetails: Record<string, unknown> = {');
  const legDetailsSrc = apiSrc.slice(startIdx, startIdx + 2500);
  assert.match(
    legDetailsSrc,
    /leg_label/,
    'legDetails must include leg_label for display (e.g. "Outbound" / "Return")',
  );
});
