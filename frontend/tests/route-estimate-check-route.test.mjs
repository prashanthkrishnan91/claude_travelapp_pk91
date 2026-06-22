/**
 * Route Planning UX simplification — inline Google Routes connectors (PR #515).
 *
 * Verifies:
 * 1.  callRouteEstimate is exported from api.ts.
 * 2.  callRouteEstimate only POSTs — never GETs.
 * 3.  callRouteEstimate targets the route-estimate endpoint.
 * 4.  getRouteableStopsForEstimate is exported from travelHints.ts.
 * 5.  getRouteableStopsForEstimate filters to activity/meal only.
 * 6.  getRouteableStopsForEstimate excludes items without coordinates.
 * 7.  getRouteableStopsForEstimate preserves order.
 * 8.  "Check route" button (check-route-btn testid) no longer present.
 * 9.  CheckRoutePanel component no longer rendered in ItineraryDayColumn.
 * 10. callRouteEstimate is called inside a useEffect (auto-fetch per day).
 * 11. callRouteEstimate is NOT called when fewer than 2 routable stops.
 * 12. Inline connector uses Google Routes leg data when available (drive label).
 * 13. Google Routes result is labelled "drive", never "walk".
 * 14. No GOOGLE_ROUTES_API_KEY in frontend source.
 * 15. No optimize/reorder/map-route behavior introduced.
 * 16. RouteEstimateResponse, RouteEstimateLeg, RouteableStopPayload types exported.
 * 17. RouteReadinessStatus still present and intact (regression guard).
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const apiSrc = readFileSync(
  new URL("../src/lib/api.ts", import.meta.url),
  "utf8",
);

const travelHintsSrc = readFileSync(
  new URL("../src/lib/travelHints.ts", import.meta.url),
  "utf8",
);

const dayColumnSrc = readFileSync(
  new URL("../src/components/trips/ItineraryDayColumn.tsx", import.meta.url),
  "utf8",
);

const typesSrc = readFileSync(
  new URL("../src/types/index.ts", import.meta.url),
  "utf8",
);

// Glob all frontend src files for key safety checks
import { readdirSync, statSync } from "node:fs";
import { join } from "node:path";

function walkFiles(dir) {
  const results = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) results.push(...walkFiles(full));
    else if (entry.name.endsWith(".ts") || entry.name.endsWith(".tsx")) results.push(full);
  }
  return results;
}

const frontendSrcFiles = walkFiles(new URL("../src", import.meta.url).pathname);
const allFrontendSrc = frontendSrcFiles.map((f) => readFileSync(f, "utf8")).join("\n");

// ---------------------------------------------------------------------------
// 1. callRouteEstimate exported from api.ts
// ---------------------------------------------------------------------------

test("callRouteEstimate is exported from api.ts", () => {
  assert.match(
    apiSrc,
    /export async function callRouteEstimate/,
    "callRouteEstimate must be exported from api.ts",
  );
});

// ---------------------------------------------------------------------------
// 2. callRouteEstimate uses POST, not GET
// ---------------------------------------------------------------------------

test("callRouteEstimate uses POST method", () => {
  const fnMatch = apiSrc.match(/export async function callRouteEstimate[\s\S]{0,600}/);
  assert.ok(fnMatch, "callRouteEstimate must exist");
  assert.match(fnMatch[0], /method.*"POST"|"POST".*method/, "callRouteEstimate must POST");
  assert.doesNotMatch(fnMatch[0], /method.*"GET"|"GET".*method/, "callRouteEstimate must not GET");
});

// ---------------------------------------------------------------------------
// 3. callRouteEstimate targets the route-estimate endpoint
// ---------------------------------------------------------------------------

test("callRouteEstimate targets the route-estimate endpoint", () => {
  const fnMatch = apiSrc.match(/export async function callRouteEstimate[\s\S]{0,600}/);
  assert.ok(fnMatch);
  assert.match(fnMatch[0], /route-estimate/, "callRouteEstimate must target the route-estimate path");
});

// ---------------------------------------------------------------------------
// 4. getRouteableStopsForEstimate exported from travelHints.ts
// ---------------------------------------------------------------------------

test("getRouteableStopsForEstimate is exported from travelHints.ts", () => {
  assert.match(
    travelHintsSrc,
    /export function getRouteableStopsForEstimate/,
    "getRouteableStopsForEstimate must be exported from travelHints",
  );
});

// ---------------------------------------------------------------------------
// 5. getRouteableStopsForEstimate filters to activity/meal
// ---------------------------------------------------------------------------

test('getRouteableStopsForEstimate filters to "activity" item type', () => {
  const fnMatch = travelHintsSrc.match(/export function getRouteableStopsForEstimate[\s\S]{0,600}/);
  assert.ok(fnMatch, "function must exist");
  assert.match(fnMatch[0], /"activity"/, 'must filter for "activity"');
});

test('getRouteableStopsForEstimate filters to "meal" item type', () => {
  const fnMatch = travelHintsSrc.match(/export function getRouteableStopsForEstimate[\s\S]{0,600}/);
  assert.ok(fnMatch);
  assert.match(fnMatch[0], /"meal"/, 'must filter for "meal"');
});

test("getRouteableStopsForEstimate does not include flight or hotel", () => {
  const fnMatch = travelHintsSrc.match(/export function getRouteableStopsForEstimate[\s\S]{0,600}/);
  assert.ok(fnMatch);
  assert.doesNotMatch(fnMatch[0], /"flight"/, "flight must not appear in routeable stop filter");
  assert.doesNotMatch(fnMatch[0], /"hotel"/, "hotel must not appear in routeable stop filter");
});

// ---------------------------------------------------------------------------
// 6. getRouteableStopsForEstimate excludes missing-coord items
// ---------------------------------------------------------------------------

test("getRouteableStopsForEstimate uses hasRouteableCoordinates to gate stops", () => {
  const fnMatch = travelHintsSrc.match(/export function getRouteableStopsForEstimate[\s\S]{0,600}/);
  assert.ok(fnMatch);
  assert.match(
    fnMatch[0],
    /hasRouteableCoordinates/,
    "must gate on hasRouteableCoordinates",
  );
});

// ---------------------------------------------------------------------------
// 7. getRouteableStopsForEstimate preserves order (no sort)
// ---------------------------------------------------------------------------

test("getRouteableStopsForEstimate does not sort or reorder stops", () => {
  const fnMatch = travelHintsSrc.match(/export function getRouteableStopsForEstimate[\s\S]{0,600}/);
  assert.ok(fnMatch);
  assert.doesNotMatch(fnMatch[0], /\.sort\(/, "must not reorder stops");
});

// ---------------------------------------------------------------------------
// 8. "Check route" button no longer present
// ---------------------------------------------------------------------------

test('"check-route-btn" testid no longer present in ItineraryDayColumn', () => {
  assert.doesNotMatch(
    dayColumnSrc,
    /data-testid="check-route-btn"/,
    '"check-route-btn" testid must be removed — separate Check route button is gone',
  );
});

test('"check-route-idle" testid no longer present in ItineraryDayColumn', () => {
  assert.doesNotMatch(
    dayColumnSrc,
    /data-testid="check-route-idle"/,
    '"check-route-idle" testid must be removed',
  );
});

// ---------------------------------------------------------------------------
// 9. CheckRoutePanel no longer rendered
// ---------------------------------------------------------------------------

test("CheckRoutePanel component no longer defined in ItineraryDayColumn", () => {
  assert.doesNotMatch(
    dayColumnSrc,
    /function CheckRoutePanel/,
    "CheckRoutePanel component must be removed",
  );
});

test("CheckRoutePanel no longer used in ItineraryDayColumn JSX", () => {
  assert.doesNotMatch(
    dayColumnSrc,
    /<CheckRoutePanel\b/,
    "CheckRoutePanel must not be rendered",
  );
});

// ---------------------------------------------------------------------------
// 10. callRouteEstimate is called inside a useEffect (auto-fetch)
// ---------------------------------------------------------------------------

test("callRouteEstimate is called inside a useEffect in ItineraryDayColumn", () => {
  // Find useEffect blocks and check that at least one calls callRouteEstimate
  const useEffectBodies = [...dayColumnSrc.matchAll(/useEffect\s*\(\s*\(\)\s*=>\s*\{([\s\S]{0,800}?)\}\s*,/g)]
    .map((m) => m[1] ?? "");
  assert.ok(useEffectBodies.length > 0, "at least one useEffect must exist");
  const hasRouteEstimateCall = useEffectBodies.some((body) =>
    /callRouteEstimate/.test(body)
  );
  assert.ok(hasRouteEstimateCall, "callRouteEstimate must be called inside a useEffect for auto-fetch");
});

// ---------------------------------------------------------------------------
// 11. callRouteEstimate NOT called when fewer than 2 routable stops
// ---------------------------------------------------------------------------

test("route-estimate effect guards on routableStops.length < 2", () => {
  // The useEffect body that contains callRouteEstimate must also guard on length < 2
  const useEffectBodies = [...dayColumnSrc.matchAll(/useEffect\s*\(\s*\(\)\s*=>\s*\{([\s\S]{0,800}?)\}\s*,/g)]
    .map((m) => m[1] ?? "");
  const routeEffect = useEffectBodies.find((body) => /callRouteEstimate/.test(body));
  assert.ok(routeEffect, "must find useEffect containing callRouteEstimate");
  assert.match(
    routeEffect,
    /routableStops\.length\s*<\s*2/,
    "useEffect must guard on routableStops.length < 2 before calling callRouteEstimate",
  );
});

// ---------------------------------------------------------------------------
// 12. Inline connector uses Google Routes leg data
// ---------------------------------------------------------------------------

test("renderItemsWithConnectors accepts routeLegs parameter", () => {
  const fnMatch = dayColumnSrc.match(/function renderItemsWithConnectors[\s\S]{0,800}/);
  assert.ok(fnMatch, "renderItemsWithConnectors must exist");
  assert.match(
    fnMatch[0],
    /routeLegs/,
    "renderItemsWithConnectors must accept routeLegs parameter",
  );
});

test("inline connector uses fromItemId / toItemId to match Google leg", () => {
  const fnMatch = dayColumnSrc.match(/function renderItemsWithConnectors[\s\S]{0,4000}/);
  assert.ok(fnMatch, "renderItemsWithConnectors must exist");
  assert.match(
    fnMatch[0],
    /fromItemId|toItemId/,
    "connector must match Google leg by fromItemId/toItemId",
  );
});

test("inline connector renders drive label from Google Routes leg", () => {
  const fnMatch = dayColumnSrc.match(/function renderItemsWithConnectors[\s\S]{0,4000}/);
  assert.ok(fnMatch);
  // When a Google leg is used, it should show "min drive"
  assert.match(
    fnMatch[0],
    /min drive/,
    'Google Routes connector must label timing as "min drive"',
  );
});

test('inline connector uses data-testid="route-connector-google" for Google leg', () => {
  assert.match(
    dayColumnSrc,
    /data-testid="route-connector-google"/,
    'Google Routes connector must use data-testid="route-connector-google"',
  );
});

// ---------------------------------------------------------------------------
// 13. Google Routes result is labelled "drive", not "walk"
// ---------------------------------------------------------------------------

test("Google Routes connector does not produce a walk label", () => {
  // Find the block that renders the Google leg connector
  const googleLegBlock = dayColumnSrc.match(/googleLeg[\s\S]{0,500}min drive/);
  assert.ok(googleLegBlock, "must find Google leg connector block");
  assert.doesNotMatch(
    googleLegBlock[0],
    /min walk/,
    "Google Routes adapter is DRIVE — connector must never say 'min walk'",
  );
});

// ---------------------------------------------------------------------------
// 14. GOOGLE_ROUTES_API_KEY not in frontend source
// ---------------------------------------------------------------------------

test("GOOGLE_ROUTES_API_KEY is not referenced anywhere in frontend source", () => {
  assert.doesNotMatch(
    allFrontendSrc,
    /GOOGLE_ROUTES_API_KEY/,
    "GOOGLE_ROUTES_API_KEY must never appear in frontend source",
  );
});

// ---------------------------------------------------------------------------
// 15. No optimize/reorder/map-route behavior
// ---------------------------------------------------------------------------

test("ItineraryDayColumn does not reference route optimization or reordering", () => {
  assert.doesNotMatch(
    dayColumnSrc,
    /OptimizeDay|Optimize Day|optimizeRoute|reorder|routeMatrix|DirectionsAPI|DistanceMatrix/i,
    "must not introduce optimize/reorder/matrix behavior",
  );
});

test("api.ts callRouteEstimate does not reference optimize or matrix endpoints", () => {
  const fnMatch = apiSrc.match(/export async function callRouteEstimate[\s\S]{0,600}/);
  assert.ok(fnMatch);
  assert.doesNotMatch(
    fnMatch[0],
    /optimizeWaypoints|computeRouteMatrix|matrix|reorder/i,
    "callRouteEstimate must only call route-estimate, not matrix or optimize",
  );
});

// ---------------------------------------------------------------------------
// 16. Route estimate types exported from types/index.ts
// ---------------------------------------------------------------------------

test("RouteEstimateResponse is exported from types/index.ts", () => {
  assert.match(
    typesSrc,
    /export interface RouteEstimateResponse/,
    "RouteEstimateResponse must be exported from types",
  );
});

test("RouteEstimateLeg is exported from types/index.ts", () => {
  assert.match(
    typesSrc,
    /export interface RouteEstimateLeg/,
    "RouteEstimateLeg must be exported from types",
  );
});

test("RouteableStopPayload is exported from types/index.ts", () => {
  assert.match(
    typesSrc,
    /export interface RouteableStopPayload/,
    "RouteableStopPayload must be exported from types",
  );
});

// ---------------------------------------------------------------------------
// 17. RouteReadinessStatus still present and intact (regression guard)
// ---------------------------------------------------------------------------

test("RouteReadinessStatus still defined in ItineraryDayColumn (regression guard)", () => {
  assert.match(
    dayColumnSrc,
    /function RouteReadinessStatus/,
    "RouteReadinessStatus must still be present",
  );
});

test('RouteReadinessStatus still uses data-testid="route-readiness-status" (regression guard)', () => {
  assert.match(
    dayColumnSrc,
    /data-testid="route-readiness-status"/,
    "route-readiness-status testid must remain intact",
  );
});

test("computeRouteReadiness still imported in ItineraryDayColumn (regression guard)", () => {
  assert.match(
    dayColumnSrc,
    /import[^;]*computeRouteReadiness[^;]*from.*travelHints/,
    "computeRouteReadiness import must remain intact",
  );
});

test("routeLegs state is passed to TimelineSections (regression guard)", () => {
  const usage = dayColumnSrc.match(/<TimelineSections[\s\S]{0,600}/);
  assert.ok(usage, "TimelineSections usage must be present");
  assert.match(usage[0], /routeLegs/, "TimelineSections must receive routeLegs prop");
});
