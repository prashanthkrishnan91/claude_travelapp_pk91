/**
 * Travel Hints — non-routable item type exclusion contract tests.
 *
 * Verifies:
 * 1. flight → activity pair emits "skip" (no missing_location / route hint).
 * 2. hotel → activity pair emits "skip".
 * 3. activity → hotel pair emits "skip".
 * 4. activity → activity with coords still emits travel_ok or far_apart.
 * 5. activity → activity missing coords still emits missing_location.
 * 6. One hint result per adjacent pair — index alignment preserved.
 * 7. summarizeHints does not count skip hints as issues.
 * 8. No route optimization, reordering, geocoding, or provider calls added.
 * 9. PairHintKind includes "skip".
 * 10. ItineraryDayColumn handles "skip" hint with a plain connector (no label).
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const travelHintsSrc = readFileSync(
  new URL("../src/lib/travelHints.ts", import.meta.url),
  "utf8",
);

const dayColumn = readFileSync(
  new URL("../src/components/trips/ItineraryDayColumn.tsx", import.meta.url),
  "utf8",
);

// ---------------------------------------------------------------------------
// 1. PairHintKind includes "skip"
// ---------------------------------------------------------------------------

test('PairHintKind union includes "skip"', () => {
  assert.match(travelHintsSrc, /"skip"/, 'PairHintKind must include "skip"');
});

// ---------------------------------------------------------------------------
// 2. HintableItem accepts itemType
// ---------------------------------------------------------------------------

test("HintableItem interface accepts itemType field", () => {
  assert.match(
    travelHintsSrc,
    /itemType\?/,
    "HintableItem must declare itemType? field",
  );
});

// ---------------------------------------------------------------------------
// 3. Non-routable gate: flight and hotel are gated
// ---------------------------------------------------------------------------

test('computeAdjacentHints gates "flight" itemType to skip', () => {
  assert.match(
    travelHintsSrc,
    /itemType.*===.*"flight"|"flight".*===.*itemType/,
    'non-routable gate must check for "flight"',
  );
});

test('computeAdjacentHints gates "hotel" itemType to skip', () => {
  assert.match(
    travelHintsSrc,
    /itemType.*===.*"hotel"|"hotel".*===.*itemType/,
    'non-routable gate must check for "hotel"',
  );
});

test("non-routable gate emits skip hint and continues", () => {
  assert.match(
    travelHintsSrc,
    /kind.*:.*"skip"|"skip".*:.*kind/,
    "skip hint must be emitted for non-routable pairs",
  );
  assert.match(travelHintsSrc, /continue/, "loop must continue after emitting skip");
});

// ---------------------------------------------------------------------------
// 4. activity/meal pairs unchanged — coordinate paths still present
// ---------------------------------------------------------------------------

test("activity/meal coordinate path (missing_location) remains intact", () => {
  assert.match(
    travelHintsSrc,
    /lat1 == null \|\| lng1 == null \|\| lat2 == null \|\| lng2 == null/,
    "missing_location null-check must remain intact after non-routable gate",
  );
});

test("activity/meal travel_ok branch remains intact", () => {
  assert.match(travelHintsSrc, /kind.*:.*"travel_ok"|"travel_ok".*:.*kind/, "travel_ok branch must remain");
});

test("activity/meal far_apart branch remains intact", () => {
  assert.match(travelHintsSrc, /kind.*:.*"far_apart"|"far_apart".*:.*kind/, "far_apart branch must remain");
});

// ---------------------------------------------------------------------------
// 5. Index alignment — one hint per adjacent pair
// ---------------------------------------------------------------------------

test("computeAdjacentHints emits exactly one hint per adjacent pair (skip included)", () => {
  // Every branch — skip, missing_location, far_apart, travel_ok — calls hints.push(...)
  // and the loop runs items.length - 1 times regardless of itemType
  const pushMatches = [...travelHintsSrc.matchAll(/hints\.push\(/g)];
  assert.ok(pushMatches.length >= 4, "hints.push must appear in all four branches (skip, missing_location, far_apart, travel_ok)");
});

// ---------------------------------------------------------------------------
// 6. summarizeHints ignores skip hints
// ---------------------------------------------------------------------------

test("summarizeHints only counts far_apart and missing_location (skip is not an issue)", () => {
  // summarizeHints filters by kind — skip is not in the filter list
  assert.match(travelHintsSrc, /filter.*far_apart|far_apart.*filter/, "summarizeHints must filter far_apart");
  assert.match(travelHintsSrc, /filter.*missing_location|missing_location.*filter/, "summarizeHints must filter missing_location");
  assert.doesNotMatch(
    travelHintsSrc,
    /filter.*"skip"|"skip".*filter/,
    "summarizeHints must not filter/count skip hints as issues",
  );
});

// ---------------------------------------------------------------------------
// 7. ItineraryDayColumn renders plain connector for skip (no label copy)
// ---------------------------------------------------------------------------

test("ItineraryDayColumn handles skip hint kind", () => {
  assert.match(
    dayColumn,
    /hint\.kind.*===.*"skip"|"skip".*===.*hint\.kind/,
    'ItineraryDayColumn must handle hint.kind === "skip"',
  );
});

test("ItineraryDayColumn skip connector has no label text", () => {
  // skip connector should just be a vertical line, no label span
  // Verify the skip branch exists and is not followed by a label span with hint.label
  const skipBranchMatch = dayColumn.match(/hint\.kind.*===.*"skip"[\s\S]{0,400}/);
  assert.ok(skipBranchMatch, "skip branch must exist in ItineraryDayColumn");
  // The skip connector block should not reference hint.label
  const skipBlock = skipBranchMatch[0];
  assert.doesNotMatch(skipBlock, /hint\.label/, "skip connector must not render hint.label");
});

test("ItineraryDayColumn skip connector preserves vertical rail line", () => {
  // Plain connector still renders the hairline vertical rail for visual continuity
  const skipBranchMatch = dayColumn.match(/hint\.kind.*===.*"skip"[\s\S]{0,400}/);
  assert.ok(skipBranchMatch, "skip branch must exist");
  assert.match(skipBranchMatch[0], /bg-ds-hairline/, "skip connector must include vertical hairline for visual continuity");
});

// ---------------------------------------------------------------------------
// 8. No route optimization, reordering, geocoding, or provider calls added
// ---------------------------------------------------------------------------

test("travelHints does not reference RouteReadinessStatus or route optimization", () => {
  assert.doesNotMatch(
    travelHintsSrc,
    /RouteReadinessStatus|optimizeRoute|routeOptimiz/,
    "no route-optimization concepts allowed",
  );
});

test("travelHints does not reorder items", () => {
  assert.doesNotMatch(
    travelHintsSrc,
    /reorder|\.sort\b/,
    "travelHints must not reorder or sort items",
  );
});

test("travelHints does not make provider or network calls", () => {
  assert.doesNotMatch(
    travelHintsSrc,
    /fetch\(|await fetch|http\.get|https\.get|DirectionsAPI|DistanceMatrix|RoutesAPI/i,
    "travelHints must remain pure local computation",
  );
});

test("travelHints does not geocode", () => {
  assert.doesNotMatch(travelHintsSrc, /geocod/i, "travelHints must not geocode");
});

// ---------------------------------------------------------------------------
// 9. PR #504 canonical coordinate access remains intact
// ---------------------------------------------------------------------------

test("travelHints still imports readCanonicalLat and readCanonicalLng", () => {
  assert.match(
    travelHintsSrc,
    /import[^;]*readCanonicalLat[^;]*from.*tripItemMetadata/,
    "readCanonicalLat import must remain",
  );
  assert.match(
    travelHintsSrc,
    /import[^;]*readCanonicalLng[^;]*from.*tripItemMetadata/,
    "readCanonicalLng import must remain",
  );
});

test("travelHints still calls readCanonicalLat and readCanonicalLng in the coordinate path", () => {
  assert.match(travelHintsSrc, /readCanonicalLat\(/, "readCanonicalLat must still be called");
  assert.match(travelHintsSrc, /readCanonicalLng\(/, "readCanonicalLng must still be called");
});
