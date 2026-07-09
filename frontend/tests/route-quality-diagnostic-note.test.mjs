/**
 * Route Quality Diagnostic note — read-only frontend surface for the PR #526
 * backend diagnostic endpoint.
 *
 * Verifies:
 * 1.  fetchRouteQualityDiagnostic is exported from api.ts and only GETs.
 * 2.  fetchRouteQualityDiagnostic targets the route-quality-diagnostic endpoint.
 * 3.  RouteQualityDiagnosticNote is defined and rendered in ItineraryDayColumn.
 * 4.  The diagnostic fetch is not called inside any useEffect (no auto-fetch
 *     on render, day switch, or itinerary refresh).
 * 5.  The diagnostic fetch is only wired to an onClick handler.
 * 6.  Disabled/insufficient-stops/missing-coordinates/ready copy all render.
 * 7.  Excluded flights/hotels note renders when excludedStops is non-empty.
 * 8.  Ready-state copy never implies travel times were estimated.
 * 9.  No mutation/write call exists in the note (no PATCH/POST/DELETE).
 * 10. No route-estimate helper is imported/called from the note.
 * 11. CheckRoutePanel is not resurrected.
 * 12. Types are exported from types/index.ts.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const apiSrc = readFileSync(new URL("../src/lib/api.ts", import.meta.url), "utf8");
const dayColumnSrc = readFileSync(
  new URL("../src/components/trips/ItineraryDayColumn.tsx", import.meta.url),
  "utf8",
);
const typesSrc = readFileSync(new URL("../src/types/index.ts", import.meta.url), "utf8");

// ---------------------------------------------------------------------------
// 1-2. fetchRouteQualityDiagnostic — GET only, correct endpoint
// ---------------------------------------------------------------------------

test("fetchRouteQualityDiagnostic is exported from api.ts", () => {
  assert.match(
    apiSrc,
    /export async function fetchRouteQualityDiagnostic/,
    "fetchRouteQualityDiagnostic must be exported from api.ts",
  );
});

test("fetchRouteQualityDiagnostic targets the route-quality-diagnostic endpoint and only GETs", () => {
  const fnMatch = apiSrc.match(/export async function fetchRouteQualityDiagnostic[\s\S]{0,400}/);
  assert.ok(fnMatch, "function must exist");
  assert.match(fnMatch[0], /route-quality-diagnostic/, "must target the diagnostic endpoint");
  assert.doesNotMatch(fnMatch[0], /method.*["'](POST|PATCH|PUT|DELETE)["']/i, "must not use a write method");
});

// ---------------------------------------------------------------------------
// 3. Component defined and rendered
// ---------------------------------------------------------------------------

test("RouteQualityDiagnosticNote component is defined in ItineraryDayColumn", () => {
  assert.match(
    dayColumnSrc,
    /function RouteQualityDiagnosticNote/,
    "RouteQualityDiagnosticNote must be defined",
  );
});

test("RouteQualityDiagnosticNote is rendered in the expanded day body", () => {
  assert.match(
    dayColumnSrc,
    /<RouteQualityDiagnosticNote\s/,
    "RouteQualityDiagnosticNote must be used in JSX",
  );
});

// ---------------------------------------------------------------------------
// 4-5. Fetch only happens from an explicit click, never a useEffect
// ---------------------------------------------------------------------------

test("fetchRouteQualityDiagnostic is never called inside a useEffect", () => {
  const useEffectBodies = [...dayColumnSrc.matchAll(/useEffect\s*\(\s*\(\)\s*=>\s*\{([\s\S]{0,1200}?)\}\s*,/g)]
    .map((m) => m[1] ?? "");
  const calledInEffect = useEffectBodies.some((body) => /fetchRouteQualityDiagnostic/.test(body));
  assert.equal(calledInEffect, false, "fetchRouteQualityDiagnostic must not be called from a useEffect");
});

test("fetchRouteQualityDiagnostic is only invoked from a click handler", () => {
  const componentMatch = dayColumnSrc.match(/function RouteQualityDiagnosticNote[\s\S]*?\n\}\n/);
  assert.ok(componentMatch, "RouteQualityDiagnosticNote must exist");
  const src = componentMatch[0];
  assert.match(src, /const handleCheck = async \(\) => \{[\s\S]*?fetchRouteQualityDiagnostic/, "fetch must live in handleCheck");
  assert.match(src, /onClick=\{handleCheck\}/, "button must call handleCheck onClick");
});

// ---------------------------------------------------------------------------
// 6-8. Deterministic, honest copy states
// ---------------------------------------------------------------------------

test("disabled state renders honest copy", () => {
  assert.match(
    dayColumnSrc,
    /Route readiness review isn't turned on for this trip yet\./,
    "disabled copy must render",
  );
});

test("insufficient_stops state renders honest copy", () => {
  assert.match(
    dayColumnSrc,
    /eligible stop.*found\. Add more stops with locations to review route order\./,
    "insufficient_stops copy must render",
  );
});

test("missing_coordinates state renders honest copy", () => {
  assert.match(
    dayColumnSrc,
    /stops have location data\. Add locations before route planning\./,
    "missing_coordinates copy must render",
  );
});

test("ready state renders honest copy without implying route times were estimated", () => {
  assert.match(
    dayColumnSrc,
    /This day is ready for route review\./,
    "ready copy must render",
  );
  const fnMatch = dayColumnSrc.match(/function describeRouteQualityDiagnostic[\s\S]{0,1600}/);
  assert.ok(fnMatch, "describeRouteQualityDiagnostic must exist");
  assert.match(
    fnMatch[0],
    /No route travel-time data is available yet; no travel times are estimated here\./,
    "ready/missing_coordinates copy must disclaim travel-time estimation",
  );
});

// ---------------------------------------------------------------------------
// 7. Excluded flights/hotels note
// ---------------------------------------------------------------------------

test("excluded stops note references flights/hotels exclusion", () => {
  assert.match(
    dayColumnSrc,
    /function describeExcludedStops/,
    "describeExcludedStops must exist",
  );
  assert.match(
    dayColumnSrc,
    /excluded from route planning v1\./,
    "excluded stops copy must render",
  );
});

// ---------------------------------------------------------------------------
// 9. No mutation/write calls in the note
// ---------------------------------------------------------------------------

test("RouteQualityDiagnosticNote performs no mutation/write calls", () => {
  const componentMatch = dayColumnSrc.match(/function RouteQualityDiagnosticNote[\s\S]*?\n\}\n/);
  assert.ok(componentMatch);
  assert.doesNotMatch(
    componentMatch[0],
    /updateItem|deleteItem|createItem|updateItemTimeline|method:\s*["'](POST|PATCH|PUT|DELETE)["']/,
    "no write/mutation call must exist in the diagnostic note",
  );
});

// ---------------------------------------------------------------------------
// 10. No route-estimate helper imported/called from the note
// ---------------------------------------------------------------------------

test("RouteQualityDiagnosticNote does not call callRouteEstimate", () => {
  const componentMatch = dayColumnSrc.match(/function RouteQualityDiagnosticNote[\s\S]*?\n\}\n/);
  assert.ok(componentMatch);
  assert.doesNotMatch(
    componentMatch[0],
    /callRouteEstimate/,
    "diagnostic note must not call the route-estimate helper",
  );
});

// ---------------------------------------------------------------------------
// 11. CheckRoutePanel not resurrected
// ---------------------------------------------------------------------------

test("CheckRoutePanel is not resurrected", () => {
  assert.doesNotMatch(dayColumnSrc, /function CheckRoutePanel/, "CheckRoutePanel must not return");
  assert.doesNotMatch(dayColumnSrc, /<CheckRoutePanel\b/, "CheckRoutePanel must not be rendered");
});

// ---------------------------------------------------------------------------
// 12. Types exported
// ---------------------------------------------------------------------------

test("RouteQualityDiagnosticResponse is exported from types/index.ts", () => {
  assert.match(
    typesSrc,
    /export interface RouteQualityDiagnosticResponse/,
    "RouteQualityDiagnosticResponse must be exported",
  );
});

test("DiagnosticStopSummary and ExcludedStopSummary are exported from types/index.ts", () => {
  assert.match(typesSrc, /export interface DiagnosticStopSummary/, "DiagnosticStopSummary must be exported");
  assert.match(typesSrc, /export interface ExcludedStopSummary/, "ExcludedStopSummary must be exported");
});
