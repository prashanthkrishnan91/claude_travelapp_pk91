/**
 * Route Planning v1 PR F — route-estimate inline connector validation/hardening.
 *
 * Audits and hardens the existing auto-fetch route-estimate call site in
 * ItineraryDayColumn (introduced in PR #515/#519). No new call site, no AI/LLM,
 * no reorder-proposal wiring, no route panel/drawer/modal/map — the inline
 * connector remains the only route UI.
 *
 * Verifies:
 * 1.  callRouteEstimate is not invoked when routableStops.length < 2 (guard present).
 * 2.  callRouteEstimate is invoked only once the guard passes (>= 2 stops).
 * 3.  getRouteableStopsForEstimate excludes flight/hotel/note/transit item types.
 * 4.  getRouteableStopsForEstimate gates on hasRouteableCoordinates (rejects invalid/out-of-range coords).
 * 5.  routeLegs are cleared synchronously at the start of every effect run (stop-signature change),
 *     so a still-in-flight refetch can never leave a previous, now-stale leg on screen.
 * 6.  routeLegs are only ever set from a "success" response with non-empty estimates —
 *     disabled/not_configured/provider_error/thrown-error responses never populate routeLegs.
 * 7.  routableStopsKey encodes stop order, so reordering (same stop set, different order)
 *     changes the effect dependency and triggers a refetch; connector matching is by
 *     fromItemId/toItemId pair, not index, so mapping self-corrects after reorder.
 * 8.  No new route-estimate call site was added — callRouteEstimate has exactly one call site.
 * 9.  No LLM/reorder-apply/CheckRoutePanel/"Optimize Day" language near the route-estimate effect.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const apiSrc = readFileSync(new URL("../src/lib/api.ts", import.meta.url), "utf8");
const travelHintsSrc = readFileSync(new URL("../src/lib/travelHints.ts", import.meta.url), "utf8");
const dayColumnSrc = readFileSync(
  new URL("../src/components/trips/ItineraryDayColumn.tsx", import.meta.url),
  "utf8",
);

function findRouteEstimateEffect(src) {
  const bodies = [...src.matchAll(/useEffect\s*\(\s*\(\)\s*=>\s*\{([\s\S]{0,1200}?)\n  \}, \[/g)].map(
    (m) => m[1] ?? "",
  );
  return bodies.find((body) => /callRouteEstimate/.test(body));
}

// ---------------------------------------------------------------------------
// 1 & 2. Guard: not called below 2 stops, called once guard passes
// ---------------------------------------------------------------------------

test("route-estimate effect returns before calling callRouteEstimate when routableStops.length < 2", () => {
  const effect = findRouteEstimateEffect(dayColumnSrc);
  assert.ok(effect, "must find the route-estimate useEffect");
  const guardMatch = effect.match(/if\s*\(\s*routableStops\.length\s*<\s*2\s*\)\s*\{([\s\S]{0,200}?)\}/);
  assert.ok(guardMatch, "must find the length < 2 guard block");
  assert.match(guardMatch[1], /return/, "guard block must return before reaching callRouteEstimate");
  assert.doesNotMatch(guardMatch[1], /callRouteEstimate/, "callRouteEstimate must not be inside the < 2 guard block");
});

test("callRouteEstimate call in the effect is textually after the length < 2 guard", () => {
  const effect = findRouteEstimateEffect(dayColumnSrc);
  assert.ok(effect);
  const guardIndex = effect.search(/routableStops\.length\s*<\s*2/);
  const callIndex = effect.indexOf("callRouteEstimate(");
  assert.ok(guardIndex >= 0 && callIndex >= 0);
  assert.ok(callIndex > guardIndex, "callRouteEstimate must execute after the guard check, not before");
});

// ---------------------------------------------------------------------------
// 3. Excludes flight/hotel/note/transit
// ---------------------------------------------------------------------------

test("getRouteableStopsForEstimate whitelist excludes flight, hotel, note, and transit", () => {
  const fnMatch = travelHintsSrc.match(/export function getRouteableStopsForEstimate[\s\S]{0,600}/);
  assert.ok(fnMatch);
  assert.match(fnMatch[0], /itemType === "activity" \|\| item\.itemType === "meal"/);
  for (const banned of ["flight", "hotel", "note", "transit"]) {
    assert.doesNotMatch(
      fnMatch[0],
      new RegExp(`"${banned}"`),
      `${banned} must not appear in the routeable stop whitelist`,
    );
  }
});

// ---------------------------------------------------------------------------
// 4. Invalid / out-of-range coordinates excluded via hasRouteableCoordinates
// ---------------------------------------------------------------------------

test("getRouteableStopsForEstimate gates on hasRouteableCoordinates before mapping a stop", () => {
  const fnMatch = travelHintsSrc.match(/export function getRouteableStopsForEstimate[\s\S]{0,600}/);
  assert.ok(fnMatch);
  const filterIndex = fnMatch[0].indexOf("hasRouteableCoordinates");
  const mapIndex = fnMatch[0].indexOf(".map(");
  assert.ok(filterIndex >= 0 && mapIndex >= 0);
  assert.ok(filterIndex < mapIndex, "coordinate gate must run before the payload is constructed");
});

test("readCanonicalLat/readCanonicalLng range-check coordinates (out-of-range rejected)", () => {
  const tripItemMetaSrc = readFileSync(
    new URL("../src/lib/tripItemMetadata.ts", import.meta.url),
    "utf8",
  );
  assert.match(tripItemMetaSrc, /-90/, "lat lower bound must be enforced");
  assert.match(tripItemMetaSrc, /90/, "lat upper bound must be enforced");
  assert.match(tripItemMetaSrc, /-180/, "lng lower bound must be enforced");
  assert.match(tripItemMetaSrc, /180/, "lng upper bound must be enforced");
});

// ---------------------------------------------------------------------------
// 5. routeLegs cleared synchronously at the start of every effect run
// ---------------------------------------------------------------------------

test("route-estimate effect clears routeLegs synchronously before the < 2 guard and before fetching", () => {
  const effect = findRouteEstimateEffect(dayColumnSrc);
  assert.ok(effect);
  const clearIndex = effect.indexOf("setRouteLegs([])");
  const guardIndex = effect.search(/routableStops\.length\s*<\s*2/);
  const fetchIndex = effect.indexOf("callRouteEstimate(");
  assert.ok(clearIndex >= 0, "effect must clear routeLegs synchronously");
  assert.ok(
    clearIndex < guardIndex && clearIndex < fetchIndex,
    "routeLegs must be cleared before the guard check and before any fetch is issued, " +
      "so a previous (now-stale) leg is never left on screen during an in-flight refetch",
  );
});

// ---------------------------------------------------------------------------
// 6. routeLegs only ever set from a genuine non-empty success response
// ---------------------------------------------------------------------------

test("routeLegs is only set to response.estimates when status is success and estimates non-empty", () => {
  const effect = findRouteEstimateEffect(dayColumnSrc);
  assert.ok(effect);
  assert.match(
    effect,
    /response\.status === "success" && response\.estimates\.length > 0/,
    "must require both a success status and non-empty estimates before setting routeLegs",
  );
});

test("route-estimate effect clears routeLegs in the else branch (disabled/not_configured/provider_error)", () => {
  const effect = findRouteEstimateEffect(dayColumnSrc);
  assert.ok(effect);
  const thenBlock = effect.match(/\.then\(\(response\)\s*=>\s*\{([\s\S]{0,400}?)\}\)/);
  assert.ok(thenBlock, "must find the .then handler");
  assert.match(thenBlock[1], /else\s*\{\s*setRouteLegs\(\[\]\);?\s*\}/, "non-success statuses must clear routeLegs");
});

test("route-estimate effect clears routeLegs on a thrown/rejected request (catch handler)", () => {
  const effect = findRouteEstimateEffect(dayColumnSrc);
  assert.ok(effect);
  const catchBlock = effect.match(/\.catch\(\(\)\s*=>\s*\{([\s\S]{0,200}?)\}\)/);
  assert.ok(catchBlock, "must find the .catch handler");
  assert.match(catchBlock[1], /setRouteLegs\(\[\]\)/, "catch handler must clear routeLegs, never leave stale data");
});

// ---------------------------------------------------------------------------
// 7. routableStopsKey encodes order; connector matches by id pair, not index
// ---------------------------------------------------------------------------

test("routableStopsKey is derived from stop id + coordinates in array order (join, no sort)", () => {
  assert.match(
    dayColumnSrc,
    /const routableStopsKey = routableStops\.map\(\(s\) => `\$\{s\.itemId\}:\$\{s\.lat\},\$\{s\.lng\}`\)\.join\("\|"\)/,
  );
});

test("route-estimate effect depends on routableStopsKey (re-fires when order/coords/set changes)", () => {
  const depsMatch = dayColumnSrc.match(/\}, \[routableStopsKey, day\.tripId, day\.id\]\)/);
  assert.ok(depsMatch, "effect dependency array must include routableStopsKey");
});

test("inline connector matches a Google leg by exact fromItemId/toItemId pair, not array index", () => {
  const fnMatch = dayColumnSrc.match(/function renderItemsWithConnectors[\s\S]{0,4000}/);
  assert.ok(fnMatch);
  assert.match(
    fnMatch[0],
    /leg\.fromItemId === item\.id && leg\.toItemId === nextItem\.id/,
    "connector lookup must match on the exact adjacent id pair so stale legs from a prior order never apply to the wrong pair",
  );
});

// ---------------------------------------------------------------------------
// 8. No new route-estimate call site was added
// ---------------------------------------------------------------------------

test("callRouteEstimate has exactly one call site in ItineraryDayColumn", () => {
  const matches = [...dayColumnSrc.matchAll(/callRouteEstimate\(/g)];
  assert.equal(matches.length, 1, "callRouteEstimate must be called from exactly one place");
});

test("no route-estimate fetch exists outside a useEffect in ItineraryDayColumn", () => {
  const effect = findRouteEstimateEffect(dayColumnSrc);
  assert.ok(effect, "the sole callRouteEstimate call must live inside a useEffect");
});

// ---------------------------------------------------------------------------
// 9. No AI/LLM/reorder/CheckRoutePanel/"Optimize Day" language near the effect
// ---------------------------------------------------------------------------

test("route-estimate effect region contains no LLM/AI/reorder/optimize/panel language", () => {
  const effectStart = dayColumnSrc.indexOf("const routableStops = useMemo(");
  const effectRegion = dayColumnSrc.slice(effectStart, effectStart + 2000);
  assert.doesNotMatch(
    effectRegion,
    /anthropic|openai|\bllm\b|applyRouteReorderProposal|ReorderProposalPreview|CheckRoutePanel|Optimize Day|geocode/i,
    "route-estimate effect region must stay free of banned scope",
  );
});

test("no LLM/provider symbols anywhere in api.ts callRouteEstimate helper", () => {
  // Bounded to the function body itself (up to its closing brace) so this
  // doesn't bleed into an unrelated neighboring function's doc comment.
  const fnMatch = apiSrc.match(/export async function callRouteEstimate[\s\S]{0,600}?\n\}/);
  assert.ok(fnMatch);
  assert.doesNotMatch(fnMatch[0], /anthropic|openai|\bllm\b/i);
});
