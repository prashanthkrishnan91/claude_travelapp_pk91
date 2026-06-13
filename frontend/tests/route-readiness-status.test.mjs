/**
 * Route Readiness Status — display-only day-level coordinate coverage indicator.
 *
 * Verifies:
 * 1.  activity/meal with canonical coords are counted as location-ready (withCoords++).
 * 2.  activity/meal without coords are counted as missing.
 * 3.  flight/hotel are excluded from routeable stop counts.
 * 4.  status is hidden when fewer than 2 routeable stops exist.
 * 5.  status is hidden when all routeable stops have coords.
 * 6.  status appears when at least one routeable stop is missing coords.
 * 7.  no Optimize Day, route optimization, provider calls, geocoding, or route
 *     sequencing were added.
 * 8.  PR #504 canonical coordinate access (hasRouteableCoordinates) remains intact.
 * 9.  PR #506 flight/hotel skip behavior remains intact.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const travelHintsSrc = readFileSync(
  new URL("../src/lib/travelHints.ts", import.meta.url),
  "utf8",
);

const dayColumnSrc = readFileSync(
  new URL("../src/components/trips/ItineraryDayColumn.tsx", import.meta.url),
  "utf8",
);

// ---------------------------------------------------------------------------
// 1. computeRouteReadiness is exported from travelHints
// ---------------------------------------------------------------------------

test("computeRouteReadiness is exported from travelHints", () => {
  assert.match(
    travelHintsSrc,
    /export function computeRouteReadiness/,
    "computeRouteReadiness must be an exported function in travelHints",
  );
});

// ---------------------------------------------------------------------------
// 2. Routeable stop filter: only activity and meal
// ---------------------------------------------------------------------------

test('computeRouteReadiness filters to "activity" items only (not flight/hotel)', () => {
  assert.match(
    travelHintsSrc,
    /itemType.*===.*"activity"|"activity".*===.*itemType/,
    'computeRouteReadiness must filter by itemType === "activity"',
  );
});

test('computeRouteReadiness filters to "meal" items only (not flight/hotel)', () => {
  assert.match(
    travelHintsSrc,
    /itemType.*===.*"meal"|"meal".*===.*itemType/,
    'computeRouteReadiness must filter by itemType === "meal"',
  );
});

test("computeRouteReadiness filter excludes flight and hotel (no itemType check for them in routeable)", () => {
  // The routeable filter must only include activity/meal, not flight or hotel
  const readinessFn = travelHintsSrc.match(
    /export function computeRouteReadiness[\s\S]{0,800}/,
  );
  assert.ok(readinessFn, "computeRouteReadiness function must exist");
  const fnBody = readinessFn[0];
  // Must include activity and meal in the filter
  assert.match(fnBody, /"activity"/, 'routeable filter must include "activity"');
  assert.match(fnBody, /"meal"/, 'routeable filter must include "meal"');
  // Must not include flight or hotel in the routeable filter
  assert.doesNotMatch(
    fnBody,
    /"flight".*routeable|routeable.*"flight"/,
    "flight must not be in routeable filter",
  );
  assert.doesNotMatch(
    fnBody,
    /"hotel".*routeable|routeable.*"hotel"/,
    "hotel must not be in routeable filter",
  );
});

// ---------------------------------------------------------------------------
// 3. Canonical coordinate check: hasRouteableCoordinates
// ---------------------------------------------------------------------------

test("travelHints imports hasRouteableCoordinates from tripItemMetadata", () => {
  assert.match(
    travelHintsSrc,
    /import[^;]*hasRouteableCoordinates[^;]*from.*tripItemMetadata/,
    "travelHints must import hasRouteableCoordinates from tripItemMetadata",
  );
});

test("computeRouteReadiness uses hasRouteableCoordinates to check coords", () => {
  assert.match(
    travelHintsSrc,
    /hasRouteableCoordinates\(/,
    "computeRouteReadiness must call hasRouteableCoordinates",
  );
});

// ---------------------------------------------------------------------------
// 4. Hide when fewer than 2 routeable stops
// ---------------------------------------------------------------------------

test("computeRouteReadiness returns null when fewer than 2 eligible stops", () => {
  assert.match(
    travelHintsSrc,
    /eligible\.length\s*<\s*2/,
    "computeRouteReadiness must return null when fewer than 2 eligible stops",
  );
  // Confirm the null guard is actually a return null
  assert.match(
    travelHintsSrc,
    /eligible\.length\s*<\s*2[\s\S]{0,30}return null/,
    "null guard for < 2 eligible stops must return null",
  );
});

// ---------------------------------------------------------------------------
// 5. Hide when all eligible stops have coordinates
// ---------------------------------------------------------------------------

test("computeRouteReadiness returns null when all eligible stops have coords", () => {
  assert.match(
    travelHintsSrc,
    /withCoords\s*===\s*eligible\.length/,
    "computeRouteReadiness must return null when withCoords equals total",
  );
  assert.match(
    travelHintsSrc,
    /withCoords\s*===\s*eligible\.length[\s\S]{0,30}return null/,
    "all-coords guard must return null",
  );
});

// ---------------------------------------------------------------------------
// 6. Returns { total, withCoords } when some coords are missing
// ---------------------------------------------------------------------------

test("computeRouteReadiness returns total and withCoords when some coords missing", () => {
  assert.match(
    travelHintsSrc,
    /return\s*\{\s*total[\s\S]{0,40}withCoords|return\s*\{\s*withCoords[\s\S]{0,40}total/,
    "computeRouteReadiness must return { total, withCoords } object",
  );
});

// ---------------------------------------------------------------------------
// 7. RouteReadinessStatus component present in ItineraryDayColumn
// ---------------------------------------------------------------------------

test("RouteReadinessStatus component is defined in ItineraryDayColumn", () => {
  assert.match(
    dayColumnSrc,
    /function RouteReadinessStatus/,
    "RouteReadinessStatus function must be defined in ItineraryDayColumn",
  );
});

test("RouteReadinessStatus has data-testid route-readiness-status", () => {
  assert.match(
    dayColumnSrc,
    /data-testid="route-readiness-status"/,
    'RouteReadinessStatus must use data-testid="route-readiness-status"',
  );
});

test("RouteReadinessStatus renders honest copy: stops have location data", () => {
  assert.match(
    dayColumnSrc,
    /stops have location data/,
    'RouteReadinessStatus must say "stops have location data"',
  );
});

test("RouteReadinessStatus renders helper copy: Add locations before route planning", () => {
  assert.match(
    dayColumnSrc,
    /Add locations before route planning/,
    'RouteReadinessStatus must say "Add locations before route planning"',
  );
});

test("ItineraryDayColumn imports computeRouteReadiness from travelHints", () => {
  assert.match(
    dayColumnSrc,
    /import[^;]*computeRouteReadiness[^;]*from.*travelHints/,
    "ItineraryDayColumn must import computeRouteReadiness from travelHints",
  );
});

test("RouteReadinessStatus is rendered in the expanded body", () => {
  assert.match(
    dayColumnSrc,
    /<RouteReadinessStatus\s/,
    "RouteReadinessStatus must be used in ItineraryDayColumn JSX",
  );
});

// ---------------------------------------------------------------------------
// 8. No Optimize Day, route optimization, provider calls, geocoding, or sequencing
// ---------------------------------------------------------------------------

test("travelHints does not reference route optimization or Optimize Day", () => {
  assert.doesNotMatch(
    travelHintsSrc,
    /OptimizeDay|Optimize Day|optimizeRoute|routeOptimiz|RouteOptimiz/,
    "no route-optimization concepts in travelHints",
  );
});

test("RouteReadinessStatus does not reference Optimize Day button or route optimization", () => {
  const componentMatch = dayColumnSrc.match(
    /function RouteReadinessStatus[\s\S]{0,600}/,
  );
  assert.ok(componentMatch, "RouteReadinessStatus must exist");
  const componentSrc = componentMatch[0];
  assert.doesNotMatch(
    componentSrc,
    /Optimize|optimizeRoute|DirectionsAPI|DistanceMatrix|RoutesAPI|geocod/i,
    "RouteReadinessStatus must not reference optimization, directions, or geocoding",
  );
});

test("travelHints computeRouteReadiness does not call geocoding or external provider APIs", () => {
  const readinessFn = travelHintsSrc.match(
    /export function computeRouteReadiness[\s\S]{0,600}/,
  );
  assert.ok(readinessFn, "computeRouteReadiness must exist");
  assert.doesNotMatch(
    readinessFn[0],
    /fetch\(|await fetch|DirectionsAPI|DistanceMatrix|RoutesAPI|geocod/i,
    "computeRouteReadiness must be pure local computation",
  );
});

test("travelHints does not reorder items", () => {
  assert.doesNotMatch(
    travelHintsSrc,
    /reorder|\.sort\b/,
    "travelHints must not reorder or sort items",
  );
});

// ---------------------------------------------------------------------------
// 9. PR #504 — canonical coordinate access remains intact
// ---------------------------------------------------------------------------

test("travelHints still imports readCanonicalLat from tripItemMetadata (PR #504 intact)", () => {
  assert.match(
    travelHintsSrc,
    /import[^;]*readCanonicalLat[^;]*from.*tripItemMetadata/,
    "readCanonicalLat import must remain (PR #504)",
  );
});

test("travelHints still imports readCanonicalLng from tripItemMetadata (PR #504 intact)", () => {
  assert.match(
    travelHintsSrc,
    /import[^;]*readCanonicalLng[^;]*from.*tripItemMetadata/,
    "readCanonicalLng import must remain (PR #504)",
  );
});

test("travelHints still calls readCanonicalLat and readCanonicalLng in computeAdjacentHints (PR #504 intact)", () => {
  assert.match(
    travelHintsSrc,
    /readCanonicalLat\(/,
    "readCanonicalLat must still be called (PR #504)",
  );
  assert.match(
    travelHintsSrc,
    /readCanonicalLng\(/,
    "readCanonicalLng must still be called (PR #504)",
  );
});

// ---------------------------------------------------------------------------
// 10. PR #506 — flight/hotel skip behavior remains intact
// ---------------------------------------------------------------------------

test('travelHints still emits skip kind for flight/hotel pairs (PR #506 intact)', () => {
  assert.match(
    travelHintsSrc,
    /kind.*:.*"skip"|"skip".*:.*kind/,
    'skip kind must still be emitted for flight/hotel pairs (PR #506)',
  );
});

test('travelHints still gates "flight" itemType to skip (PR #506 intact)', () => {
  assert.match(
    travelHintsSrc,
    /itemType.*===.*"flight"|"flight".*===.*itemType/,
    'flight gate must remain in computeAdjacentHints (PR #506)',
  );
});

test('travelHints still gates "hotel" itemType to skip (PR #506 intact)', () => {
  assert.match(
    travelHintsSrc,
    /itemType.*===.*"hotel"|"hotel".*===.*itemType/,
    'hotel gate must remain in computeAdjacentHints (PR #506)',
  );
});

test("summarizeHints does not count skip hints as issues (PR #506 intact)", () => {
  assert.doesNotMatch(
    travelHintsSrc,
    /filter.*"skip"|"skip".*filter/,
    "summarizeHints must not filter/count skip hints (PR #506)",
  );
});
