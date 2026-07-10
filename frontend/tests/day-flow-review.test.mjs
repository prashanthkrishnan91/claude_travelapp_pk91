/**
 * DayFlowReview — deterministic, read-only "Review day flow" surface
 * (AI Route Planning v1 PR D). Uses only already-loaded frontend data
 * (visibleItems + existing routeLegs). No LLM call, no reorder-proposal
 * source, no provider/route-estimate call, no itinerary mutation.
 *
 * Verifies:
 * 1.  DayFlowReview is defined and rendered near the route readiness area.
 * 2.  Review is triggered only by explicit click; never auto-opens on render.
 * 3.  No callRouteEstimate call/import inside the new component.
 * 4.  No applyRouteReorderProposal call/import inside the new component.
 * 5.  No LLM/provider/generator symbols in the new component.
 * 6.  CheckRoutePanel is not resurrected.
 * 7.  No "Optimize Day" / auto-reorder language.
 * 8.  Missing-coordinate state renders honest copy.
 * 9.  Route-data-unavailable state renders honest copy.
 * 10. Excluded-stop-type copy renders only the types actually present (never
 *     a fixed "Hotels and flights" claim when the day has neither, or only
 *     one, of those types).
 * 11. Longest-leg/current-order summary renders using provided legs only.
 * 12. No fabricated total when route legs are incomplete/absent.
 * 13. Readiness gate uses located/routable stop count, not just eligible count.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const dayColumnSrc = readFileSync(
  new URL("../src/components/trips/ItineraryDayColumn.tsx", import.meta.url),
  "utf8",
);

function componentSrc() {
  const match = dayColumnSrc.match(/function DayFlowReview[\s\S]*?\n\}\n/);
  assert.ok(match, "DayFlowReview must be defined");
  return match[0];
}

// ---------------------------------------------------------------------------
// 1. Component defined and rendered near route readiness area
// ---------------------------------------------------------------------------

test("DayFlowReview component is defined in ItineraryDayColumn", () => {
  assert.match(dayColumnSrc, /function DayFlowReview/, "DayFlowReview must be defined");
});

test("DayFlowReview is rendered directly after RouteQualityDiagnosticNote", () => {
  assert.match(
    dayColumnSrc,
    /<RouteQualityDiagnosticNote\s[^>]*\/>\s*\n\s*<DayFlowReview\s/,
    "DayFlowReview must render immediately after RouteQualityDiagnosticNote",
  );
});

test("DayFlowReview button reads 'Review day flow'", () => {
  assert.match(componentSrc(), /Review day flow/, "button copy must read 'Review day flow'");
});

// ---------------------------------------------------------------------------
// 2. Click-only trigger, never auto-opens
// ---------------------------------------------------------------------------

test("DayFlowReview defaults to collapsed (expanded state starts false)", () => {
  assert.match(
    componentSrc(),
    /useState\(false\)/,
    "expanded state must default to false",
  );
});

test("DayFlowReview has no useEffect that auto-expands", () => {
  assert.doesNotMatch(
    componentSrc(),
    /useEffect/,
    "DayFlowReview must not use useEffect to auto-expand",
  );
});

test("DayFlowReview only expands via an explicit onClick handler", () => {
  assert.match(
    componentSrc(),
    /onClick=\{\(\) => setExpanded\(true\)\}/,
    "expansion must be wired to an explicit onClick",
  );
});

// ---------------------------------------------------------------------------
// 3-6. Banned symbols inside the new component
// ---------------------------------------------------------------------------

test("DayFlowReview does not call or import callRouteEstimate", () => {
  assert.doesNotMatch(componentSrc(), /callRouteEstimate/, "must not reference callRouteEstimate");
});

test("DayFlowReview does not call or import applyRouteReorderProposal", () => {
  assert.doesNotMatch(componentSrc(), /applyRouteReorderProposal/, "must not reference applyRouteReorderProposal");
});

test("DayFlowReview has no LLM/provider/generator symbols", () => {
  assert.doesNotMatch(
    componentSrc(),
    /anthropic|openai|\bllm\b|generateProposal|suggestDayTimeline/i,
    "must not reference any LLM/provider/generator symbol",
  );
});

test("DayFlowReview does not resurrect CheckRoutePanel", () => {
  assert.doesNotMatch(componentSrc(), /CheckRoutePanel/, "must not reference CheckRoutePanel");
  assert.doesNotMatch(dayColumnSrc, /function CheckRoutePanel/, "CheckRoutePanel must not exist anywhere");
});

test("DayFlowReview performs no fetch/write calls", () => {
  assert.doesNotMatch(
    componentSrc(),
    /fetch\(|method:\s*["'](POST|PATCH|PUT|DELETE)["']|updateItem|deleteItem|createItem/,
    "must be a pure client-side computation with no network/write calls",
  );
});

// ---------------------------------------------------------------------------
// 7. No "Optimize Day" / auto-reorder language
// ---------------------------------------------------------------------------

test("DayFlowReview never uses Optimize Day or auto-reorder language", () => {
  assert.doesNotMatch(
    componentSrc(),
    /Optimize Day|optimizeRoute|auto-reorder|autoReorder/i,
    "must not imply optimization or automatic reordering",
  );
});

// ---------------------------------------------------------------------------
// 8-10. Honest copy states
// ---------------------------------------------------------------------------

test("DayFlowReview renders honest missing-coordinate copy", () => {
  assert.match(componentSrc(), /Add locations before route planning\./, "missing-coordinate copy must render");
  assert.match(componentSrc(), /Missing coordinates:/, "must list which stops are missing coordinates");
});

test("DayFlowReview renders honest route-data-unavailable copy", () => {
  assert.match(
    componentSrc(),
    /No travel-time review is available yet\./,
    "unavailable-state copy must render",
  );
  assert.match(
    componentSrc(),
    /This review uses the route details already shown between stops\./,
    "review must disclose it only uses already-shown route details",
  );
});

test("DayFlowReview renders excluded flights/hotels copy when both are present", () => {
  const fnMatch = dayColumnSrc.match(/function describeExcludedStopTypes[\s\S]{0,700}/);
  assert.ok(fnMatch, "describeExcludedStopTypes must exist");
  assert.match(
    componentSrc(),
    /describeExcludedStopTypes\(flow\.excludedStopTypes\)/,
    "excluded copy must be conditioned on excluded stop types actually present",
  );
});

test("describeExcludedStopTypes names only hotel when only hotel is present", () => {
  assert.match(
    dayColumnSrc,
    /EXCLUDED_STOP_TYPE_LABELS[\s\S]{0,200}hotel:\s*"Hotels"/,
    "hotel label must exist",
  );
  // Single-type join path must not force in "flights" text
  const fnMatch = dayColumnSrc.match(/function describeExcludedStopTypes[\s\S]{0,700}/);
  assert.ok(fnMatch);
  assert.match(fnMatch[0], /labels\.length === 1\s*\n?\s*\?\s*labels\[0\]/, "single-type case must render only that type's label");
});

test("describeExcludedStopTypes does not hardcode 'Hotels and flights' as the only possible output", () => {
  // The old hardcoded literal must be gone from the component body — copy
  // must now be derived from describeExcludedStopTypes for every case.
  assert.doesNotMatch(
    componentSrc(),
    /<p>Hotels and flights are excluded from route planning v1\.<\/p>/,
    "must not hardcode a fixed excluded-types claim in JSX",
  );
});

test("describeExcludedStopTypes renders singular 'Transit is excluded' for transit-only", () => {
  const fnMatch = dayColumnSrc.match(/function describeExcludedStopTypes[\s\S]{0,700}/);
  assert.ok(fnMatch, "describeExcludedStopTypes must exist");
  assert.match(
    fnMatch[0],
    /excludedStopTypes\[0\] === "transit" \? "is" : "are"/,
    "transit-only case must use singular verb form",
  );
});

test("describeExcludedStopTypes renders 'Notes are excluded' for note-only", () => {
  assert.match(
    dayColumnSrc,
    /EXCLUDED_STOP_TYPE_LABELS[\s\S]{0,200}note:\s*"Notes"/,
    "note label must exist so a note-only day reads 'Notes are excluded from route planning v1.'",
  );
});

test("excludedStopTypes is computed as a filtered array, not a single boolean", () => {
  assert.match(
    dayColumnSrc,
    /excludedStopTypes:\s*string\[\]/,
    "DayFlowSummary must carry excludedStopTypes as an array, not a boolean flag",
  );
  assert.doesNotMatch(
    dayColumnSrc,
    /hasExcludedStopTypes/,
    "the old boolean hasExcludedStopTypes must be fully replaced",
  );
});

// ---------------------------------------------------------------------------
// 11-12. Leg summary uses only provided data; no fabricated totals
// ---------------------------------------------------------------------------

test("DayFlowReview summarizes leg count and longest leg from provided routeLegs only", () => {
  const src = componentSrc();
  assert.match(src, /legSummary\.legCount/, "must render the count of visible route legs");
  assert.match(src, /legSummary\.longestLeg/, "must render the longest available leg when present");
  assert.match(src, /durationSeconds/, "longest leg must be derived from leg's own duration field");
});

test("DayFlowReview renders current-order summary from routable stop titles only", () => {
  assert.match(
    componentSrc(),
    /Current order:/,
    "must render a current-order summary using only existing stop titles",
  );
  assert.match(
    dayColumnSrc,
    /function summarizeDayFlowLegs[\s\S]{0,1200}/,
    "summarizeDayFlowLegs must exist",
  );
});

test("DayFlowReview does not fabricate a total travel time", () => {
  assert.doesNotMatch(
    componentSrc(),
    /totalDuration|totalDistance|sum\(|reduce\(\s*\([^)]*\)\s*=>\s*[^,]*\+\s*leg\.durationSeconds\s*,\s*0\s*\)/,
    "must not compute or render a fabricated total across legs",
  );
});

test("DayFlowReview reports unavailable state when routeLegs is empty or absent", () => {
  const fnMatch = dayColumnSrc.match(/function summarizeDayFlowLegs[\s\S]{0,600}/);
  assert.ok(fnMatch, "summarizeDayFlowLegs must exist");
  assert.match(
    fnMatch[0],
    /!routeLegs \|\| routeLegs\.length === 0/,
    "must treat missing/empty routeLegs as unavailable",
  );
  assert.match(fnMatch[0], /available:\s*false/, "must report available: false when no legs exist");
});

// ---------------------------------------------------------------------------
// Uses existing helpers only — no new provider/route computation introduced
// ---------------------------------------------------------------------------

test("DayFlowReview reuses getRouteableStopsForEstimate rather than reimplementing coordinate checks", () => {
  assert.match(
    dayColumnSrc,
    /function summarizeDayFlow\(items: ItineraryItem\[\]\)[\s\S]{0,400}getRouteableStopsForEstimate/,
    "summarizeDayFlow must reuse getRouteableStopsForEstimate",
  );
});

test("DayFlowReview does not import any new provider/route-estimate helper", () => {
  assert.doesNotMatch(
    dayColumnSrc,
    /import[^;]*generateReorderProposal[^;]*;/,
    "no new proposal-generation import must be added",
  );
});

// ---------------------------------------------------------------------------
// 13. Readiness gate uses located/routable count, not just eligible count
// ---------------------------------------------------------------------------

test("summarizeDayFlow reports locatedCount from getRouteableStopsForEstimate, not just eligible count", () => {
  const fnMatch = dayColumnSrc.match(/function summarizeDayFlow\(items: ItineraryItem\[\]\)[\s\S]{0,600}/);
  assert.ok(fnMatch, "summarizeDayFlow must exist");
  assert.match(
    fnMatch[0],
    /locatedCount:\s*located\.length/,
    "summarizeDayFlow must return locatedCount derived from the routable stops list",
  );
});

test("DayFlowReview gates the 'not enough located stops' copy on locatedCount, not eligibleCount", () => {
  assert.match(
    componentSrc(),
    /flow\.locatedCount < 2/,
    "the not-enough-located-stops gate must use flow.locatedCount",
  );
  assert.doesNotMatch(
    componentSrc(),
    /flow\.eligibleCount/,
    "the old eligibleCount-based gate must be fully replaced",
  );
});

test("DayFlowReview shows a non-misleading message for exactly one located stop with no missing coordinates", () => {
  assert.match(
    componentSrc(),
    /Add another located activity or meal before route planning\./,
    "must render the one-located-stop copy instead of implying missing coordinates",
  );
});

test("missing-coordinate copy takes priority over the not-enough-located-stops copy when both could apply", () => {
  const src = componentSrc();
  const missingIdx = src.indexOf("flow.missingCoordinateTitles.length > 0 ?");
  const locatedIdx = src.indexOf("flow.locatedCount < 2 && <p>Add another located");
  assert.ok(missingIdx !== -1, "missing-coordinate branch must exist");
  assert.ok(locatedIdx !== -1, "not-enough-located-stops branch must exist");
  assert.ok(missingIdx < locatedIdx, "missing-coordinate branch must be checked first");
});
