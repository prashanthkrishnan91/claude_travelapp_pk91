/**
 * Journey Desk route-diagnostics cleanup — removes the debug-feeling
 * "Route readiness review" / "Day flow review" affordances from the normal
 * itinerary day UI. Inline route connectors are the actual user-facing
 * product surface for route information; these panels duplicated it.
 *
 * Verifies:
 * 1.  RouteQualityDiagnosticNote is not defined or rendered in ItineraryDayColumn.
 * 2.  DayFlowReview is not defined or rendered in ItineraryDayColumn.
 * 3.  The "Check route readiness" / "Review day flow" affordances and their
 *     testids no longer exist.
 * 4.  fetchRouteQualityDiagnostic is no longer imported/used in the column
 *     (endpoint itself in api.ts is untouched).
 * 5.  Inline route connectors (renderItemsWithConnectors, route-connector-*
 *     testids) still render.
 * 6.  callRouteEstimate call site and its useEffect guard remain unchanged.
 * 7.  RouteReadinessStatus (compact missing-coordinate status) still renders.
 * 8.  No new panel/drawer/modal/debug component was introduced.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const dayColumnSrc = readFileSync(
  new URL("../src/components/trips/ItineraryDayColumn.tsx", import.meta.url),
  "utf8",
);

// ---------------------------------------------------------------------------
// 1-2. Debug components fully removed
// ---------------------------------------------------------------------------

test("RouteQualityDiagnosticNote is not defined in ItineraryDayColumn", () => {
  assert.doesNotMatch(
    dayColumnSrc,
    /function RouteQualityDiagnosticNote/,
    "RouteQualityDiagnosticNote must be removed",
  );
});

test("RouteQualityDiagnosticNote is not rendered in ItineraryDayColumn", () => {
  assert.doesNotMatch(
    dayColumnSrc,
    /<RouteQualityDiagnosticNote\b/,
    "RouteQualityDiagnosticNote must not be rendered",
  );
});

test("DayFlowReview is not defined in ItineraryDayColumn", () => {
  assert.doesNotMatch(
    dayColumnSrc,
    /function DayFlowReview/,
    "DayFlowReview must be removed",
  );
});

test("DayFlowReview is not rendered in ItineraryDayColumn", () => {
  assert.doesNotMatch(
    dayColumnSrc,
    /<DayFlowReview\b/,
    "DayFlowReview must not be rendered",
  );
});

// ---------------------------------------------------------------------------
// 3. Visible debug affordances and testids gone
// ---------------------------------------------------------------------------

test("'Check route readiness' button copy is gone", () => {
  assert.doesNotMatch(dayColumnSrc, /Check route readiness/, "button copy must be removed");
});

test("'Review day flow' button copy is gone", () => {
  assert.doesNotMatch(dayColumnSrc, /Review day flow/, "button copy must be removed");
});

test("route-quality-diagnostic and day-flow-review testids are gone", () => {
  assert.doesNotMatch(dayColumnSrc, /data-testid="route-quality-diagnostic/, "diagnostic testids must be removed");
  assert.doesNotMatch(dayColumnSrc, /data-testid="day-flow-review/, "day-flow-review testids must be removed");
});

// ---------------------------------------------------------------------------
// 4. fetchRouteQualityDiagnostic no longer imported/used here
// ---------------------------------------------------------------------------

test("fetchRouteQualityDiagnostic is no longer imported in ItineraryDayColumn", () => {
  assert.doesNotMatch(
    dayColumnSrc,
    /fetchRouteQualityDiagnostic/,
    "the diagnostic fetch helper must no longer be referenced from the day column",
  );
});

// ---------------------------------------------------------------------------
// 5. Inline route connectors still render
// ---------------------------------------------------------------------------

test("renderItemsWithConnectors still exists and builds inline connectors", () => {
  assert.match(
    dayColumnSrc,
    /function renderItemsWithConnectors/,
    "inline connector renderer must remain",
  );
});

test("route-connector-google and route-connector-unavailable testids still render", () => {
  assert.match(dayColumnSrc, /data-testid="route-connector-google"/, "google leg connector must remain");
  assert.match(dayColumnSrc, /data-testid="route-connector-unavailable"/, "unavailable connector must remain");
});

// ---------------------------------------------------------------------------
// 6. callRouteEstimate call site unchanged
// ---------------------------------------------------------------------------

test("callRouteEstimate is still called inside a useEffect guarded on routableStops.length < 2", () => {
  const useEffectBodies = [...dayColumnSrc.matchAll(/useEffect\s*\(\s*\(\)\s*=>\s*\{([\s\S]{0,900}?)\}\s*,/g)]
    .map((m) => m[1] ?? "");
  const routeEffect = useEffectBodies.find((body) => /callRouteEstimate/.test(body));
  assert.ok(routeEffect, "must find useEffect containing callRouteEstimate");
  assert.match(
    routeEffect,
    /routableStops\.length\s*<\s*2/,
    "route-estimate effect guard must remain unchanged",
  );
});

test("callRouteEstimate import remains", () => {
  assert.match(dayColumnSrc, /import[^;]*callRouteEstimate[^;]*from "@\/lib\/api"/, "callRouteEstimate import must remain");
});

// ---------------------------------------------------------------------------
// 7. Compact missing-coordinate status still renders
// ---------------------------------------------------------------------------

test("RouteReadinessStatus is still defined and rendered", () => {
  assert.match(dayColumnSrc, /function RouteReadinessStatus/, "RouteReadinessStatus must remain");
  assert.match(dayColumnSrc, /<RouteReadinessStatus\s/, "RouteReadinessStatus must still be rendered");
});

// ---------------------------------------------------------------------------
// 8. No new panel/drawer/modal/debug surface introduced
// ---------------------------------------------------------------------------

test("no new panel/drawer/modal/debug component was introduced", () => {
  assert.doesNotMatch(
    dayColumnSrc,
    /function \w*(Diagnostic|Drawer|Modal|Debug)\w*/,
    "no new panel/drawer/modal/debug component must be introduced",
  );
});
