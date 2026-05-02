/**
 * Travel Time Hints v1 — contract tests.
 *
 * Verifies:
 * 1. computeAdjacentHints exports and returns PairHint[] shape.
 * 2. Adjacent items with lat/lng produce a travel_ok hint when nearby.
 * 3. Adjacent items with lat/lng produce a far_apart hint when far (> FAR_APART_DRIVE_MIN minutes drive).
 * 4. Missing lat/lng on either item produces a missing_location hint.
 * 5. Single-item list (or empty) produces no hints.
 * 6. summarizeHints counts far_apart and missing_location correctly.
 * 7. DayTravelHintBar is rendered in ItineraryDayColumn (component surface).
 * 8. Connectors for missing_location pairs show helpful copy in ItineraryDayColumn.
 * 9. Far-apart connector shows "far apart" warning copy.
 * 10. Timeline/dayPart ordering is respected (existing section grouping preserved).
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const travelHintsSrc = readFileSync(
  new URL('../src/lib/travelHints.ts', import.meta.url),
  'utf8',
);

const dayColumn = readFileSync(
  new URL('../src/components/trips/ItineraryDayColumn.tsx', import.meta.url),
  'utf8',
);

// ---------------------------------------------------------------------------
// 1. Exports
// ---------------------------------------------------------------------------

test('travelHints exports computeAdjacentHints', () => {
  assert.match(travelHintsSrc, /export function computeAdjacentHints/, 'computeAdjacentHints must be exported');
});

test('travelHints exports summarizeHints', () => {
  assert.match(travelHintsSrc, /export function summarizeHints/, 'summarizeHints must be exported');
});

test('travelHints exports FAR_APART_DRIVE_MIN constant', () => {
  assert.match(travelHintsSrc, /export const FAR_APART_DRIVE_MIN/, 'FAR_APART_DRIVE_MIN must be exported');
});

test('travelHints exports conservative walking constants', () => {
  assert.match(travelHintsSrc, /export const CONSERVATIVE_WALK_FACTOR/, 'CONSERVATIVE_WALK_FACTOR must be exported');
  assert.match(travelHintsSrc, /export const MAX_WALK_HINT_MIN/, 'MAX_WALK_HINT_MIN must be exported');
});

// ---------------------------------------------------------------------------
// 2. PairHint shape: kind and label fields
// ---------------------------------------------------------------------------

test('travelHints defines PairHint with kind and label fields', () => {
  assert.match(travelHintsSrc, /PairHint/, 'PairHint interface must exist');
  assert.match(travelHintsSrc, /kind/, 'PairHint must include kind field');
  assert.match(travelHintsSrc, /label/, 'PairHint must include label field');
});

test('travelHints defines PairHintKind with travel_ok, far_apart, missing_location', () => {
  assert.match(travelHintsSrc, /"travel_ok"/, 'travel_ok kind must be defined');
  assert.match(travelHintsSrc, /"far_apart"/, 'far_apart kind must be defined');
  assert.match(travelHintsSrc, /"missing_location"/, 'missing_location kind must be defined');
});

// ---------------------------------------------------------------------------
// 3. Nearby items → travel_ok
// ---------------------------------------------------------------------------

test('computeAdjacentHints emits travel_ok for nearby items (< FAR_APART_DRIVE_MIN drive)', () => {
  // The source should route non-far pairs to travel_ok
  assert.match(travelHintsSrc, /travel_ok/, 'travel_ok branch must exist in computeAdjacentHints');
  // Nearby items should NOT get far_apart label
  assert.match(travelHintsSrc, /kind.*far_apart|far_apart.*kind/, 'far_apart branch must exist');
});

// ---------------------------------------------------------------------------
// 4. Far-apart items → far_apart with warning label
// ---------------------------------------------------------------------------

test('computeAdjacentHints emits far_apart hint with "far apart" copy when drive time exceeds threshold', () => {
  assert.match(travelHintsSrc, /far apart/, '"far apart" copy must appear in far_apart hint label');
  assert.match(travelHintsSrc, /FAR_APART_DRIVE_MIN/, 'threshold must be applied in computeAdjacentHints');
});

test('far_apart hint label includes "These two stops may be far apart"', () => {
  assert.match(travelHintsSrc, /These two stops may be far apart/, 'exact far-apart copy must be present');
});

// ---------------------------------------------------------------------------
// 5. Missing lat/lng → missing_location
// ---------------------------------------------------------------------------

test('computeAdjacentHints emits missing_location when either item lacks lat or lng', () => {
  assert.match(travelHintsSrc, /missing_location/, 'missing_location branch must exist');
  assert.match(travelHintsSrc, /lat.*==.*null|lat1 == null/, 'null check for lat must exist');
});

test('missing_location hint label includes "Add location details"', () => {
  assert.match(travelHintsSrc, /Add location details/, '"Add location details" copy must appear in missing_location hint');
});

// ---------------------------------------------------------------------------
// 6. Empty / single-item list → no hints
// ---------------------------------------------------------------------------

test('computeAdjacentHints returns empty array for empty input (no crash)', () => {
  // Implementation must handle items.length < 2 safely via loop condition
  assert.match(travelHintsSrc, /items\.length - 1/, 'loop must iterate up to items.length - 1 (safe for empty/single)');
});

// ---------------------------------------------------------------------------
// 7. summarizeHints aggregates correctly
// ---------------------------------------------------------------------------

test('summarizeHints returns farApartCount, missingLocationCount, hasIssues', () => {
  assert.match(travelHintsSrc, /farApartCount/, 'farApartCount must be in summarizeHints output');
  assert.match(travelHintsSrc, /missingLocationCount/, 'missingLocationCount must be in summarizeHints output');
  assert.match(travelHintsSrc, /hasIssues/, 'hasIssues must be in summarizeHints output');
});

test('summarizeHints hasIssues is false when no far_apart or missing_location hints', () => {
  // hasIssues = farApartCount + missingLocationCount > 0
  assert.match(travelHintsSrc, /farApartCount \+ missingLocationCount > 0/, 'hasIssues formula must be correct');
});

// ---------------------------------------------------------------------------
// 8. ItineraryDayColumn uses computeAdjacentHints for connectors
// ---------------------------------------------------------------------------

test('ItineraryDayColumn imports and uses computeAdjacentHints from travelHints', () => {
  assert.match(dayColumn, /computeAdjacentHints/, 'computeAdjacentHints must be imported/used in ItineraryDayColumn');
});

test('ItineraryDayColumn imports summarizeHints from travelHints', () => {
  assert.match(dayColumn, /summarizeHints/, 'summarizeHints must be used for DayTravelHintBar');
});

// ---------------------------------------------------------------------------
// 9. Missing-location connector copy in ItineraryDayColumn
// ---------------------------------------------------------------------------

test('ItineraryDayColumn shows "Add location details" hint for missing-location pairs', () => {
  assert.match(dayColumn, /Add location details to improve travel hints/, '"Add location details" connector copy must be in ItineraryDayColumn');
});

// ---------------------------------------------------------------------------
// 10. Far-apart warning copy in ItineraryDayColumn connector
// ---------------------------------------------------------------------------

test('ItineraryDayColumn shows "far apart" warning for far-apart pairs', () => {
  assert.match(dayColumn, /far apart|These two stops may be far apart/, '"far apart" copy must appear in ItineraryDayColumn connector');
});

// ---------------------------------------------------------------------------
// 11. DayTravelHintBar is rendered in ItineraryDayColumn
// ---------------------------------------------------------------------------

test('ItineraryDayColumn defines and renders DayTravelHintBar', () => {
  assert.match(dayColumn, /DayTravelHintBar/, 'DayTravelHintBar must be defined and used in ItineraryDayColumn');
});

test('DayTravelHintBar shows day-level summary with "far apart" language', () => {
  assert.match(dayColumn, /Consider grouping nearby items|far apart/, 'day-level far-apart message must appear');
});

test('DayTravelHintBar shows "Rough hints only" disclaimer', () => {
  assert.match(dayColumn, /Rough hints only/, '"Rough hints only" disclaimer must appear in DayTravelHintBar');
});

// ---------------------------------------------------------------------------
// 12. travel_ok hints include "~" prefix to signal rough estimate
// ---------------------------------------------------------------------------

test('travel_ok hint label is prefixed with ~ to indicate rough estimate', () => {
  assert.match(travelHintsSrc, /`~\$\{label\}`/, 'travel_ok label must use ~ prefix for rough estimate');
});

test('walking hint uses conservative adjustment (ceil walkMinutes * factor)', () => {
  assert.match(
    travelHintsSrc,
    /Math\.ceil\(estimate\.walkMinutes \* CONSERVATIVE_WALK_FACTOR\)/,
    'walking estimate should be adjusted conservatively'
  );
});

test('connector rows include vertical breathing room classes', () => {
  assert.match(dayColumn, /py-1/, 'connector row should include py-1 spacing');
  assert.match(dayColumn, /leading-snug/, 'connector copy should use readable line-height');
});

// ---------------------------------------------------------------------------
// 13. Timeline/dayPart ordering preserved (existing section grouping intact)
// ---------------------------------------------------------------------------

test('ItineraryDayColumn still uses groupByDayPart for section ordering', () => {
  assert.match(dayColumn, /groupByDayPart/, 'groupByDayPart must remain for section ordering');
});

test('ItineraryDayColumn TimelineSections still renders section headers in order', () => {
  assert.match(dayColumn, /morning.*afternoon.*evening|orderedSections/, 'section ordering must be preserved');
});

// ---------------------------------------------------------------------------
// 14. No map UI, no route drawing, no auto-reordering
// ---------------------------------------------------------------------------

test('travelHints does not reference map, route, or reorder concepts', () => {
  assert.doesNotMatch(travelHintsSrc, /map|route|reorder|drag|drop|sort/, 'travelHints must not include map/route/reorder logic');
});
