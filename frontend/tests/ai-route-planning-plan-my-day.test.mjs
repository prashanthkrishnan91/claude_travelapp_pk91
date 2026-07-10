/**
 * AI Route Planning v1 — real user flow, triggered from the existing
 * "Plan My Day" button (docs/ai/AI_ROUTE_PLANNING_V1_ADR.md).
 *
 * Verifies:
 * 1.  generateRouteReorderProposal is exported from api.ts and only POSTs
 *     to the reorder-proposal generate endpoint.
 * 2.  handlePlanDay (the Plan My Day click handler) calls
 *     generateRouteReorderProposal — proposal generation is reachable only
 *     from that explicit user action.
 * 3.  generateRouteReorderProposal is never called inside a useEffect in
 *     TripBuilder.tsx or ItineraryDayColumn.tsx — no generation on render,
 *     day switch, or refresh.
 * 4.  The generate call is gated on the day already having ≥2 routeable
 *     stops (getRouteableStopsForEstimate + length >= 2), not fired blindly.
 * 5.  No new permanent itinerary-column button was added for this feature —
 *     ItineraryDayColumn.tsx gains no reference to the generate helper.
 * 6.  DayPlanModal (the existing Plan My Day result surface) is the only
 *     place the route-suggestion section renders — no new modal/page/panel
 *     component was introduced.
 * 7.  Applying a suggestion refreshes the day's local item order and clears
 *     the proposal; it is wired through the existing onApplied callback.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const apiSrc = readFileSync(new URL("../src/lib/api.ts", import.meta.url), "utf8");
const tripBuilderSrc = readFileSync(
  new URL("../src/components/trips/TripBuilder.tsx", import.meta.url),
  "utf8",
);
const dayColumnSrc = readFileSync(
  new URL("../src/components/trips/ItineraryDayColumn.tsx", import.meta.url),
  "utf8",
);
const dayPlanModalSrc = readFileSync(
  new URL("../src/components/trips/DayPlanModal.tsx", import.meta.url),
  "utf8",
);

function useEffectBodies(src) {
  return [...src.matchAll(/useEffect\s*\(\s*\(\)\s*=>\s*\{([\s\S]{0,2000}?)\}\s*,/g)].map(
    (m) => m[1] ?? "",
  );
}

// ---------------------------------------------------------------------------
// 1. generateRouteReorderProposal — POST only, correct endpoint
// ---------------------------------------------------------------------------

test("generateRouteReorderProposal is exported from api.ts", () => {
  assert.match(
    apiSrc,
    /export async function generateRouteReorderProposal/,
    "generateRouteReorderProposal must be exported from api.ts",
  );
});

test("generateRouteReorderProposal targets the generate endpoint and POSTs", () => {
  const fnMatch = apiSrc.match(/export async function generateRouteReorderProposal[\s\S]{0,600}/);
  assert.ok(fnMatch, "function must exist");
  assert.match(fnMatch[0], /route-reorder-proposal\/generate/, "must target the generate endpoint");
  assert.match(fnMatch[0], /method:\s*["']POST["']/, "must use POST");
});

// ---------------------------------------------------------------------------
// 2. Only reachable from the explicit Plan My Day handler
// ---------------------------------------------------------------------------

test("handlePlanDay calls generateRouteReorderProposal", () => {
  const fnMatch = tripBuilderSrc.match(
    /const handlePlanDay = useCallback\(async \(dayId[\s\S]*?\n  \}, \[[^\]]*\]\);/,
  );
  assert.ok(fnMatch, "handlePlanDay must exist");
  assert.match(fnMatch[0], /generateRouteReorderProposal\(/, "handlePlanDay must call generateRouteReorderProposal");
});

// ---------------------------------------------------------------------------
// 3. No generation on render / day switch / refresh
// ---------------------------------------------------------------------------

test("generateRouteReorderProposal is never called inside a useEffect in TripBuilder", () => {
  const calledInEffect = useEffectBodies(tripBuilderSrc).some((body) =>
    /generateRouteReorderProposal/.test(body),
  );
  assert.equal(calledInEffect, false, "must not be called from a useEffect in TripBuilder");
});

test("generateRouteReorderProposal is never called inside a useEffect in ItineraryDayColumn", () => {
  const calledInEffect = useEffectBodies(dayColumnSrc).some((body) =>
    /generateRouteReorderProposal/.test(body),
  );
  assert.equal(calledInEffect, false, "must not be called from a useEffect in ItineraryDayColumn");
});

test("generateRouteReorderProposal does not appear in ItineraryDayColumn at all", () => {
  assert.doesNotMatch(
    dayColumnSrc,
    /generateRouteReorderProposal/,
    "generation must only be wired through the Plan My Day handler in TripBuilder, not the day column",
  );
});

// ---------------------------------------------------------------------------
// 4. Gated on >= 2 routeable stops already in the day
// ---------------------------------------------------------------------------

test("handlePlanDay gates generation on routableStops.length >= 2", () => {
  const fnMatch = tripBuilderSrc.match(
    /const handlePlanDay = useCallback\(async \(dayId[\s\S]*?\n  \}, \[[^\]]*\]\);/,
  );
  assert.match(fnMatch[0], /getRouteableStopsForEstimate\(/, "must compute routeable stops for the target day");
  assert.match(fnMatch[0], /routableStops\.length >= 2/, "must gate generation on at least 2 routeable stops");
});

// ---------------------------------------------------------------------------
// 5. No new permanent itinerary-column button for this feature
// ---------------------------------------------------------------------------

test("ItineraryDayColumn does not gain a new button referencing route-reorder generation", () => {
  assert.doesNotMatch(dayColumnSrc, /generateRouteReorderProposal/);
  assert.doesNotMatch(dayColumnSrc, /RouteSuggestionSection/);
});

// ---------------------------------------------------------------------------
// 6. Only the existing Plan My Day result surface (DayPlanModal) hosts it
// ---------------------------------------------------------------------------

test("DayPlanModal renders the route-suggestion section, no separate modal/page component exists", () => {
  assert.match(dayPlanModalSrc, /function RouteSuggestionSection/, "route suggestion section must live in DayPlanModal");
  assert.match(dayPlanModalSrc, /<RouteSuggestionSection\s/, "must be rendered inside the existing Plan My Day modal");
});

test("no new page/dashboard/map component was introduced for route planning", () => {
  assert.doesNotMatch(dayPlanModalSrc, /function \w*(Dashboard|RoutePage|RouteMap)\w*/);
});

// ---------------------------------------------------------------------------
// 7. Applying refreshes local order via the existing onApplied callback
// ---------------------------------------------------------------------------

test("handleRouteProposalApplied reorders the day's items and clears the proposal", () => {
  const fnMatch = tripBuilderSrc.match(
    /const handleRouteProposalApplied = useCallback\(\(order[\s\S]*?\n  \}, \[[^\]]*\]\);/,
  );
  assert.ok(fnMatch, "handleRouteProposalApplied must exist");
  assert.match(fnMatch[0], /setDays\(/, "must update local day state");
  assert.match(fnMatch[0], /setRouteReorderProposal\(null\)/, "must clear the proposal after applying");
});

test("DayPlanModal wires onRouteProposalApplied through to the shared preview's onApplied", () => {
  assert.match(tripBuilderSrc, /onRouteProposalApplied=\{handleRouteProposalApplied\}/);
  assert.match(dayPlanModalSrc, /onApplied=\{onApplied\}/);
});
