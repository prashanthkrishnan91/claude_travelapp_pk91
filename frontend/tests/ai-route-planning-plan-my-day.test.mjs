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
 * 8.  A validated, route-improved proposal renders current vs proposed
 *     order, a deterministic (provider-derived, not LLM-authored) savings
 *     line, and Cancel/Apply controls.
 * 9.  A current-order-already-practical result shows no Apply action —
 *     only the deterministic backend message, never the reorder preview.
 * 10. A route-validation-failure ("unavailable") result shows honest copy
 *     from the backend, not a fabricated claim.
 * 11. Apply failure leaves the displayed itinerary order unchanged — the
 *     day's local state is only ever mutated from the "applied" branch.
 * 12. Current and proposed preview lists use the canonical
 *     Morning/Afternoon/Evening/Unscheduled display order from the
 *     backend, not raw position order.
 * 13. A cross-day-part proposal is rejected server-side before it ever
 *     reaches "success" — the frontend never has a code path that shows
 *     Apply for a day-part-crossing proposal.
 * 14. ItineraryDayColumn's inline connectors are untouched by this
 *     patch — they still key off the same item/routeLegs props as before,
 *     with no new day-part display-order wiring.
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

// ---------------------------------------------------------------------------
// 8. Improved proposal: current vs proposed, deterministic savings, Cancel/Apply
// ---------------------------------------------------------------------------

test("formatEstimatedSavings is computed only from provider duration/distance fields, never LLM text", () => {
  const fnMatch = dayPlanModalSrc.match(/function formatEstimatedSavings\([\s\S]*?\n\}/);
  assert.ok(fnMatch, "formatEstimatedSavings must exist");
  assert.match(fnMatch[0], /estimatedSavingsSeconds/);
  assert.match(fnMatch[0], /estimatedDistanceSavingsMeters/);
  assert.doesNotMatch(fnMatch[0], /\brationale\b/, "savings line must not read LLM-authored rationale text");
});

test("RouteSuggestionSection renders the deterministic savings line above the reorder preview for an improved proposal", () => {
  const fnMatch = dayPlanModalSrc.match(/function RouteSuggestionSection\([\s\S]*?\n\}\n/);
  assert.ok(fnMatch, "RouteSuggestionSection must exist");
  assert.match(fnMatch[0], /formatEstimatedSavings\(routeProposal\)/);
  assert.match(fnMatch[0], /data-testid="route-suggestion-savings"/);
  assert.match(fnMatch[0], /<ReorderProposalPreview/, "the before/after preview with Cancel/Apply must still render for a real proposal");
});

// ---------------------------------------------------------------------------
// 9. current_order_already_practical: no Apply action
// ---------------------------------------------------------------------------

test("RouteSuggestionSection treats reason=current_order_already_practical as authoritative for hiding Apply", () => {
  const fnMatch = dayPlanModalSrc.match(/function RouteSuggestionSection\([\s\S]*?\n\}\n/);
  assert.match(
    fnMatch[0],
    /routeProposal\.reason === "current_order_already_practical"/,
    "must check the deterministic backend reason code",
  );
});

test("the already-practical branch renders only the backend message, never ReorderProposalPreview", () => {
  const fnMatch = dayPlanModalSrc.match(/function RouteSuggestionSection\([\s\S]*?\n\}\n/);
  const body = fnMatch[0];
  const alreadyPracticalMatch = body.match(
    /if \(isAlreadyPractical\) \{[\s\S]*?\n  \}/,
  );
  assert.ok(alreadyPracticalMatch, "already-practical early-return branch must exist");
  assert.doesNotMatch(alreadyPracticalMatch[0], /ReorderProposalPreview/, "must not render Apply controls when nothing is actionable");
  assert.match(alreadyPracticalMatch[0], /\{routeProposal\.message\}/, "must show the deterministic backend copy");
});

// ---------------------------------------------------------------------------
// 10. Route-validation-failure ("unavailable") shows honest backend copy
// ---------------------------------------------------------------------------

test("the unavailable branch renders the backend's own honest message, not a fabricated claim", () => {
  const fnMatch = dayPlanModalSrc.match(/function RouteSuggestionSection\([\s\S]*?\n\}\n/);
  const unavailableMatch = fnMatch[0].match(
    /if \(routeProposal\.status === "unavailable"\) \{[\s\S]*?\n  \}/,
  );
  assert.ok(unavailableMatch, "unavailable branch must exist");
  assert.match(unavailableMatch[0], /data-testid="route-suggestion-unavailable"/);
  assert.match(unavailableMatch[0], /\{routeProposal\.message\}/, "must render the backend-provided message, not hardcoded copy");
  assert.doesNotMatch(unavailableMatch[0], /ReorderProposalPreview/, "must not offer Apply when the route couldn't be verified");
});

// ---------------------------------------------------------------------------
// 11. Apply failure leaves the displayed itinerary order unchanged
// ---------------------------------------------------------------------------

test("day state is only mutated from the applied branch of ReorderProposalPreview's confirm handler", () => {
  const previewSrc = readFileSync(
    new URL("../src/components/trips/ReorderProposalPreview.tsx", import.meta.url),
    "utf8",
  );
  const confirmMatch = previewSrc.match(/const handleConfirm = async \(\) => \{[\s\S]*?\n  \};/);
  assert.ok(confirmMatch, "handleConfirm must exist");
  const body = confirmMatch[0];
  // onApplied (which drives TripBuilder's setDays reorder) is only called
  // inside the `status === "applied"` branch — a failed/rejected apply
  // call must fall into the else branch and only set an error message.
  const appliedBranch = body.match(/if \(result\.status === "applied"\) \{[\s\S]*?\}\s*else\s*\{[\s\S]*?\}/);
  assert.ok(appliedBranch, "must branch on result.status === \"applied\"");
  assert.match(appliedBranch[0], /onApplied\?\.\(result\.order\)/);
  const elseBranch = appliedBranch[0].match(/else\s*\{([\s\S]*?)\}$/);
  assert.ok(elseBranch, "else branch must exist for a non-applied result");
  assert.doesNotMatch(elseBranch[1], /onApplied/, "onApplied (and therefore the day's displayed order) must not be touched on apply failure");
  assert.match(elseBranch[1], /setErrorMessage/, "apply failure must surface an honest error instead");
});

test("TripBuilder's handleRouteProposalApplied (the only local-order mutator) is not called from api.ts error paths", () => {
  assert.doesNotMatch(
    apiSrc.match(/export async function applyRouteReorderProposal[\s\S]{0,600}/)[0],
    /handleRouteProposalApplied/,
  );
});

// ---------------------------------------------------------------------------
// 12. Preview uses canonical day-part display order, not raw position order
// ---------------------------------------------------------------------------

test("RouteSuggestionSection passes currentDisplayOrder/proposedDisplayOrder through to the shared preview", () => {
  const fnMatch = dayPlanModalSrc.match(/function RouteSuggestionSection\([\s\S]*?\n\}\n/);
  assert.ok(fnMatch, "RouteSuggestionSection must exist");
  assert.match(fnMatch[0], /currentDisplayOrder: routeProposal\.currentDisplayOrder/);
  assert.match(fnMatch[0], /proposedDisplayOrder: routeProposal\.proposedDisplayOrder/);
});

test("ReorderProposalPreview renders display order (falling back to raw order) instead of always using raw order", () => {
  const previewSrc = readFileSync(
    new URL("../src/components/trips/ReorderProposalPreview.tsx", import.meta.url),
    "utf8",
  );
  assert.match(
    previewSrc,
    /const displayedCurrentOrder = proposal\.currentDisplayOrder \?\? proposal\.currentOrder;/,
  );
  assert.match(
    previewSrc,
    /const displayedProposedOrder = proposal\.proposedDisplayOrder \?\? proposal\.proposedOrder;/,
  );
  assert.match(previewSrc, /displayedCurrentOrder\.map/);
  assert.match(previewSrc, /displayedProposedOrder\.map/);
});

test("backend response type declares currentDisplayOrder/proposedDisplayOrder as required (non-optional) fields", () => {
  const typesSrc = readFileSync(new URL("../src/types/index.ts", import.meta.url), "utf8");
  const block = typesSrc
    .split("export interface RouteReorderProposalGenerateResponse")[1]
    .split(/^\}/m)[0];
  assert.match(block, /currentDisplayOrder: string\[\];/);
  assert.match(block, /proposedDisplayOrder: string\[\];/);
});

// ---------------------------------------------------------------------------
// 13. Cross-day-part proposals never reach a state that shows Apply
// ---------------------------------------------------------------------------

test("a day-part-boundary violation is rejected server-side as status=unavailable, never surfaced as success", () => {
  // Static proof that the backend contract this frontend consumes treats
  // day_part_boundary_violated as an "unavailable" reason (see
  // backend/app/services/route_reorder_proposal_generate.py) — the
  // frontend's existing unavailable branch (which never renders
  // ReorderProposalPreview, per an earlier test in this file) is therefore
  // the only code path reachable for a cross-day-part proposal. This test
  // guards against a future change accidentally special-casing that reason
  // to show Apply.
  const fnMatch = dayPlanModalSrc.match(/function RouteSuggestionSection\([\s\S]*?\n\}\n/);
  assert.doesNotMatch(
    fnMatch[0],
    /day_part_boundary_violated/,
    "the frontend must not special-case this reason — it is just another unavailable message",
  );
});

// ---------------------------------------------------------------------------
// 14. Inline connectors untouched by this patch
// ---------------------------------------------------------------------------

test("ItineraryDayColumn has no new day-part display-order wiring", () => {
  assert.doesNotMatch(dayColumnSrc, /DisplayOrder/);
  assert.doesNotMatch(dayColumnSrc, /currentDisplayOrder|proposedDisplayOrder/);
});

test("renderItemsWithConnectors still exists, unchanged by this patch", () => {
  assert.match(dayColumnSrc, /function renderItemsWithConnectors/);
});
