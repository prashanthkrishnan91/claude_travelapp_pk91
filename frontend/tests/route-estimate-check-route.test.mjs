/**
 * Route Planning v1 — "Check route" button (PR #514).
 *
 * Verifies:
 * 1.  callRouteEstimate is exported from api.ts.
 * 2.  callRouteEstimate only POSTs — never GETs; no auto-call on import.
 * 3.  getRouteableStopsForEstimate is exported from travelHints.ts.
 * 4.  getRouteableStopsForEstimate filters to activity/meal only.
 * 5.  getRouteableStopsForEstimate excludes items without coordinates.
 * 6.  getRouteableStopsForEstimate preserves order.
 * 7.  CheckRoutePanel uses data-testid="check-route-btn" for the idle button.
 * 8.  CheckRoutePanel is rendered in the expanded body (ItineraryDayColumn).
 * 9.  No route-estimate call on page load or day switch (no useEffect calling it).
 * 10. No optimize/reorder/map-route/caching behavior introduced.
 * 11. GOOGLE_ROUTES_API_KEY not referenced in frontend source.
 * 12. RouteEstimateResponse, RouteEstimateLeg types exported from types/index.ts.
 * 13. Success display shows "Route estimate" and "estimated only" labels.
 * 14. Error state uses data-testid="check-route-error".
 * 15. Loading state uses data-testid="check-route-loading".
 * 16. Disabled/non-configured backend responses handled via response.message.
 * 17. Existing RouteReadinessStatus tests still pass (regression guard).
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

test("callRouteEstimate targets the route-estimate endpoint", () => {
  const fnMatch = apiSrc.match(/export async function callRouteEstimate[\s\S]{0,600}/);
  assert.ok(fnMatch);
  assert.match(fnMatch[0], /route-estimate/, "callRouteEstimate must target the route-estimate path");
});

// ---------------------------------------------------------------------------
// 3. getRouteableStopsForEstimate exported from travelHints.ts
// ---------------------------------------------------------------------------

test("getRouteableStopsForEstimate is exported from travelHints.ts", () => {
  assert.match(
    travelHintsSrc,
    /export function getRouteableStopsForEstimate/,
    "getRouteableStopsForEstimate must be exported from travelHints",
  );
});

// ---------------------------------------------------------------------------
// 4. getRouteableStopsForEstimate filters to activity/meal
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
// 5. getRouteableStopsForEstimate excludes missing-coord items
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
// 6. getRouteableStopsForEstimate preserves order (no sort)
// ---------------------------------------------------------------------------

test("getRouteableStopsForEstimate does not sort or reorder stops", () => {
  const fnMatch = travelHintsSrc.match(/export function getRouteableStopsForEstimate[\s\S]{0,600}/);
  assert.ok(fnMatch);
  assert.doesNotMatch(fnMatch[0], /\.sort\(/, "must not reorder stops");
});

// ---------------------------------------------------------------------------
// 7. CheckRoutePanel idle button testid
// ---------------------------------------------------------------------------

test('CheckRoutePanel uses data-testid="check-route-btn" for the idle button', () => {
  assert.match(
    dayColumnSrc,
    /data-testid="check-route-btn"/,
    'CheckRoutePanel must have data-testid="check-route-btn"',
  );
});

// ---------------------------------------------------------------------------
// 8. CheckRoutePanel rendered in ItineraryDayColumn expanded body
// ---------------------------------------------------------------------------

test("CheckRoutePanel is rendered in ItineraryDayColumn JSX", () => {
  assert.match(
    dayColumnSrc,
    /<CheckRoutePanel\b/,
    "CheckRoutePanel must be used in ItineraryDayColumn",
  );
});

test("CheckRoutePanel receives tripId and dayId props", () => {
  const usage = dayColumnSrc.match(/<CheckRoutePanel[\s\S]{0,200}/);
  assert.ok(usage, "CheckRoutePanel usage must be present");
  assert.match(usage[0], /tripId/, "CheckRoutePanel must receive tripId");
  assert.match(usage[0], /dayId/, "CheckRoutePanel must receive dayId");
});

// ---------------------------------------------------------------------------
// 9. No automatic route-estimate call on load or day switch
// ---------------------------------------------------------------------------

test("callRouteEstimate is not called inside any useEffect in ItineraryDayColumn", () => {
  // Extract the inner callback body of each useEffect block (content between => { and }) up to 200 chars)
  // to avoid greedy matching spilling into adjacent handler code.
  const useEffectBodies = [...dayColumnSrc.matchAll(/useEffect\s*\(\s*\(\)\s*=>\s*\{([^}]{0,200})\}/g)]
    .map((m) => m[1] ?? "");
  // There must be at least one useEffect (the state-reset one)
  assert.ok(useEffectBodies.length > 0, "at least one useEffect must exist");
  for (const body of useEffectBodies) {
    assert.doesNotMatch(
      body,
      /callRouteEstimate/,
      "callRouteEstimate must not be called inside a useEffect callback body (no auto-trigger)",
    );
  }
});

test("callRouteEstimate is not called at module level or on render in ItineraryDayColumn", () => {
  // The only callRouteEstimate call should be inside the handleCheckRoute async function
  const allCalls = [...dayColumnSrc.matchAll(/callRouteEstimate/g)];
  // Should appear: 1 import + 1 call inside handler = 2 occurrences
  assert.ok(allCalls.length >= 1, "callRouteEstimate must appear at least once (import or call)");
  // The call site must be inside an async arrow or function (not top-level JSX or useEffect)
  const handlerMatch = dayColumnSrc.match(/handleCheckRoute[\s\S]{0,400}callRouteEstimate/);
  assert.ok(handlerMatch, "callRouteEstimate must be inside handleCheckRoute handler");
});

// ---------------------------------------------------------------------------
// 10. No optimize/reorder/map-route/caching behavior
// ---------------------------------------------------------------------------

test("CheckRoutePanel does not reference route optimization or reordering", () => {
  const panelMatch = dayColumnSrc.match(/function CheckRoutePanel[\s\S]{0,3000}/);
  assert.ok(panelMatch, "CheckRoutePanel must exist");
  assert.doesNotMatch(
    panelMatch[0],
    /OptimizeDay|Optimize Day|optimizeRoute|reorder|routeMatrix|DirectionsAPI|DistanceMatrix/i,
    "CheckRoutePanel must not introduce optimize/reorder/matrix behavior",
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
// 11. GOOGLE_ROUTES_API_KEY not in frontend source
// ---------------------------------------------------------------------------

test("GOOGLE_ROUTES_API_KEY is not referenced anywhere in frontend source", () => {
  assert.doesNotMatch(
    allFrontendSrc,
    /GOOGLE_ROUTES_API_KEY/,
    "GOOGLE_ROUTES_API_KEY must never appear in frontend source",
  );
});

// ---------------------------------------------------------------------------
// 12. Route estimate types exported from types/index.ts
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
// 13. Success display copy
// ---------------------------------------------------------------------------

test('CheckRoutePanel success display includes "Route estimate" label', () => {
  assert.match(
    dayColumnSrc,
    /Route estimate/,
    'success panel must say "Route estimate"',
  );
});

test('CheckRoutePanel success display includes "estimated" qualifier', () => {
  assert.match(
    dayColumnSrc,
    /estimated only|estimated\b/i,
    'success panel must label results as estimated',
  );
});

// ---------------------------------------------------------------------------
// 14. Error state testid
// ---------------------------------------------------------------------------

test('CheckRoutePanel uses data-testid="check-route-error" for error state', () => {
  assert.match(
    dayColumnSrc,
    /data-testid="check-route-error"/,
    'error state must use data-testid="check-route-error"',
  );
});

// ---------------------------------------------------------------------------
// 15. Loading state testid
// ---------------------------------------------------------------------------

test('CheckRoutePanel uses data-testid="check-route-loading" for loading state', () => {
  assert.match(
    dayColumnSrc,
    /data-testid="check-route-loading"/,
    'loading state must use data-testid="check-route-loading"',
  );
});

// ---------------------------------------------------------------------------
// 16. Backend non-success statuses use response.message (safe copy)
// ---------------------------------------------------------------------------

test("CheckRoutePanel uses response.message for non-success backend status", () => {
  const panelMatch = dayColumnSrc.match(/function CheckRoutePanel[\s\S]{0,3000}/);
  assert.ok(panelMatch);
  assert.match(
    panelMatch[0],
    /response\.message/,
    "non-success statuses must surface response.message (safe copy from backend)",
  );
});

test("CheckRoutePanel does not expose provider internals in error copy", () => {
  const panelMatch = dayColumnSrc.match(/function CheckRoutePanel[\s\S]{0,3000}/);
  assert.ok(panelMatch);
  assert.doesNotMatch(
    panelMatch[0],
    /GOOGLE_ROUTES|google_routes_adapter|provider_error|not_configured/,
    "CheckRoutePanel must not expose internal status codes or provider names in UI copy",
  );
});

// ---------------------------------------------------------------------------
// 17. Regression guard — RouteReadinessStatus still present and intact
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

test("CheckRoutePanel is rendered after RouteReadinessStatus (correct placement)", () => {
  const readinessPos = dayColumnSrc.indexOf("<RouteReadinessStatus");
  const checkRoutePos = dayColumnSrc.indexOf("<CheckRoutePanel");
  assert.ok(readinessPos !== -1, "RouteReadinessStatus must be present");
  assert.ok(checkRoutePos !== -1, "CheckRoutePanel must be present");
  assert.ok(
    checkRoutePos > readinessPos,
    "CheckRoutePanel must appear after RouteReadinessStatus in JSX",
  );
});
