/**
 * Route Planning v1 PR E — itinerary coordinate parity hardening.
 *
 * Root cause: two gaps in the canonical coordinate contract could let an
 * upstream place with real coordinates lose them (or let a bad coordinate be
 * treated as real) once it became an itinerary item.
 *
 * Bug 1 — TripBuilder's "research result" add path (`handleAddResult`, wired
 * to the left-panel `SearchResultCard` "+" action) called `createItem`
 * without a `details` payload at all, silently dropping every routeable
 * field (lat/lng/placeId/category/...) carried in `ResearchResult.metadata`
 * (e.g. `mapHotelToResult` in api.ts writes real `metadata.lat`/`metadata.lng`).
 * Fixed by extracting `extractRouteableTripItemMetadata(result.metadata)`
 * and passing it through as `details`, the same canonical write boundary
 * already used by `handleAddAttractionToItinerary`/`handleAddRestaurantToItinerary`/
 * `handlePlanAddAttraction`/`handlePlanAddRestaurant`.
 *
 * Bug 2 — `readCanonicalLat`/`readCanonicalLng` (the frontend canonical
 * coordinate readers used by `hasRouteableCoordinates`, `getRouteableStopsForEstimate`,
 * `RouteReadinessStatus`, `DayFlowReview`, and inline connectors) accepted any
 * finite number, including out-of-range values (e.g. lat=999). The backend
 * route-quality-diagnostic port (`route_quality_diagnostic.py::_read_number`)
 * already rejected out-of-range values — so a bad coordinate could read as
 * "routeable" on the frontend while the backend diagnostic honestly reported
 * it missing. Fixed by adding the same [-90,90]/[-180,180] range check to the
 * frontend readers, so both "canonical" definitions agree.
 *
 * No coordinate fabrication, no geocoding, no new provider/LLM/route-estimate
 * call site, no reorder-proposal wiring, no itinerary mutation beyond normal
 * add-item behavior.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const apiSrc = readFileSync(new URL("../src/lib/api.ts", import.meta.url), "utf8");
const tripBuilderSrc = readFileSync(
  new URL("../src/components/trips/TripBuilder.tsx", import.meta.url),
  "utf8",
);
const metadataSrc = readFileSync(
  new URL("../src/lib/tripItemMetadata.ts", import.meta.url),
  "utf8",
);
const travelHintsSrc = readFileSync(
  new URL("../src/lib/travelHints.ts", import.meta.url),
  "utf8",
);

// ---------------------------------------------------------------------------
// 1-2. Plan My Day / Concierge add preserve canonical coordinates (already
// wired pre-PR-E; guarded here so this PR cannot regress them).
// ---------------------------------------------------------------------------

test("Plan My Day (handlePlanAddAttraction) still builds additionalDetails via extractRouteableTripItemMetadata", () => {
  const fnMatch = tripBuilderSrc.match(
    /const handlePlanAddAttraction[\s\S]{0,1200}/,
  );
  assert.ok(fnMatch, "handlePlanAddAttraction must exist");
  assert.match(
    fnMatch[0],
    /extractRouteableTripItemMetadata\(/,
    "handlePlanAddAttraction must extract canonical routeable metadata",
  );
  assert.match(
    fnMatch[0],
    /addAttractionToDay\(tripId, dayPlanTargetDayId, attraction, additionalDetails\)/,
    "handlePlanAddAttraction must pass additionalDetails into addAttractionToDay",
  );
});

test("Concierge structured add (addStructuredConciergeItemToTrip) still spreads normalizeGoogleVerificationDetails", () => {
  assert.match(
    apiSrc,
    /export async function addStructuredConciergeItemToTrip[\s\S]{0,2000}\.\.\.normalizeGoogleVerificationDetails\(/,
    "addStructuredConciergeItemToTrip must spread normalizeGoogleVerificationDetails into details",
  );
});

// ---------------------------------------------------------------------------
// 3. Saved item add preserves canonical coordinates (already wired; guarded).
// ---------------------------------------------------------------------------

test("addSavedItemToTrip still extracts real coordinates via extractItineraryCoordinates", () => {
  const fnMatch = apiSrc.match(/export async function addSavedItemToTrip[\s\S]{0,1800}/);
  assert.ok(fnMatch, "addSavedItemToTrip must exist");
  assert.match(
    fnMatch[0],
    /extractItineraryCoordinates\(snap\)/,
    "addSavedItemToTrip must extract coordinates from the saved snapshot",
  );
  assert.match(
    fnMatch[0],
    /details\.lat = savedCoords\.lat/,
    "addSavedItemToTrip must write lat onto details when coordinates resolve",
  );
});

// ---------------------------------------------------------------------------
// 4. Explore/search/card add (research-result "+") — the bug fixed in this PR.
// ---------------------------------------------------------------------------

test("handleAddResult now builds additionalDetails from result.metadata via extractRouteableTripItemMetadata", () => {
  const fnMatch = tripBuilderSrc.match(/const handleAddResult = useCallback[\s\S]{0,1100}/);
  assert.ok(fnMatch, "handleAddResult must exist");
  const fn = fnMatch[0];
  assert.match(
    fn,
    /extractRouteableTripItemMetadata\(\s*\(result\.metadata \?\? \{\}\)/,
    "handleAddResult must extract canonical routeable metadata from result.metadata",
  );
  assert.match(
    fn,
    /createItem\(tripId, targetDay\.id, \{[\s\S]{0,300}details: additionalDetails/,
    "handleAddResult must pass the extracted metadata into createItem as details",
  );
});

test("createItem accepts an optional canonical details payload (write boundary already exists)", () => {
  assert.match(
    apiSrc,
    /export async function createItem\(/,
    "createItem must exist",
  );
  const fnMatch = apiSrc.match(/export async function createItem\([\s\S]{0,900}/);
  assert.match(
    fnMatch[0],
    /details\?: Record<string, unknown>/,
    "createItem must accept an optional details payload",
  );
});

test("mapHotelToResult (a live ResearchResult producer) carries real lat/lng in metadata", () => {
  const fnMatch = apiSrc.match(/function mapHotelToResult[\s\S]{0,1000}/);
  assert.ok(fnMatch, "mapHotelToResult must exist");
  assert.match(fnMatch[0], /lat: h\.lat/, "mapHotelToResult must forward h.lat into metadata");
  assert.match(fnMatch[0], /lng: h\.lng/, "mapHotelToResult must forward h.lng into metadata");
});

// ---------------------------------------------------------------------------
// 5-6. getRouteableStopsForEstimate / RouteReadinessStatus see newly added
// items as routeable via the shared canonical helpers (structural guard —
// behavior already covered by route-estimate-check-route.test.mjs and
// route-readiness-status.test.mjs; this just proves createItem's `details`
// output shape is exactly what those readers expect).
// ---------------------------------------------------------------------------

test("getRouteableStopsForEstimate reads coordinates via readCanonicalLat/readCanonicalLng (same helpers createItem's details feed)", () => {
  assert.match(
    travelHintsSrc,
    /getRouteableStopsForEstimate[\s\S]{0,600}readCanonicalLat\(d\)/,
    "getRouteableStopsForEstimate must resolve lat via readCanonicalLat",
  );
  assert.match(
    travelHintsSrc,
    /getRouteableStopsForEstimate[\s\S]{0,600}readCanonicalLng\(d\)/,
    "getRouteableStopsForEstimate must resolve lng via readCanonicalLng",
  );
});

// ---------------------------------------------------------------------------
// 7. Address-only items (no lat/lng) remain non-routeable.
// ---------------------------------------------------------------------------

test("hasRouteableCoordinates requires both lat and lng to resolve — address alone is insufficient", () => {
  const fnMatch = metadataSrc.match(/export function hasRouteableCoordinates[\s\S]{0,300}/);
  assert.ok(fnMatch, "hasRouteableCoordinates must exist");
  assert.match(
    fnMatch[0],
    /readCanonicalLat\(source\) !== undefined && readCanonicalLng\(source\) !== undefined/,
    "hasRouteableCoordinates must require both lat and lng, never infer from address",
  );
});

test("extractRouteableTripItemMetadata only emits lat/lng together, never a bare address as a coordinate", () => {
  const fnMatch = metadataSrc.match(/export function extractRouteableTripItemMetadata[\s\S]{0,900}/);
  assert.ok(fnMatch, "extractRouteableTripItemMetadata must exist");
  assert.match(
    fnMatch[0],
    /if \(lat !== undefined && lng !== undefined\)/,
    "extractRouteableTripItemMetadata must gate lat/lng emission on both resolving",
  );
});

// ---------------------------------------------------------------------------
// 8. Invalid lat/lng (out-of-range, non-finite, non-numeric) rejected
// consistently — the second bug fixed in this PR.
// ---------------------------------------------------------------------------

test("readNumber rejects non-finite and non-numeric values (unchanged contract)", () => {
  const fnMatch = metadataSrc.match(/function readNumber\([\s\S]{0,300}/);
  assert.ok(fnMatch, "readNumber must exist");
  assert.match(
    fnMatch[0],
    /typeof value !== "number" \|\| !Number\.isFinite\(value\)/,
    "readNumber must reject non-numeric and non-finite (NaN/Infinity) values",
  );
});

test("readNumber now also rejects out-of-range values when a range is supplied", () => {
  const fnMatch = metadataSrc.match(/function readNumber\([\s\S]{0,400}/);
  assert.ok(fnMatch, "readNumber must exist");
  assert.match(
    fnMatch[0],
    /range && \(value < range\[0\] \|\| value > range\[1\]\)/,
    "readNumber must reject values outside the supplied [low, high] range",
  );
});

test("readCanonicalLat validates against LAT_RANGE ([-90, 90]) — mirrors backend route_quality_diagnostic.py", () => {
  assert.match(metadataSrc, /const LAT_RANGE: readonly \[number, number\] = \[-90, 90\];/);
  const fnMatch = metadataSrc.match(/export function readCanonicalLat[\s\S]{0,700}/);
  assert.ok(fnMatch);
  assert.match(fnMatch[0], /readNumber\(source\.lat, LAT_RANGE\)/);
});

test("readCanonicalLng validates against LNG_RANGE ([-180, 180]) — mirrors backend route_quality_diagnostic.py", () => {
  assert.match(metadataSrc, /const LNG_RANGE: readonly \[number, number\] = \[-180, 180\];/);
  const fnMatch = metadataSrc.match(/export function readCanonicalLng[\s\S]{0,700}/);
  assert.ok(fnMatch);
  assert.match(fnMatch[0], /readNumber\(source\.lng, LNG_RANGE\)/);
});

test("booleans can never satisfy readNumber (typeof guard, not just Number.isFinite)", () => {
  const fnMatch = metadataSrc.match(/function readNumber\([\s\S]{0,300}/);
  assert.ok(fnMatch);
  assert.match(
    fnMatch[0],
    /typeof value !== "number"/,
    "readNumber must type-check before range/finiteness checks so bool/string junk is rejected",
  );
});

// ---------------------------------------------------------------------------
// 9. No new provider/LLM/route-estimate/reorder-proposal call sites were
// introduced by this hardening.
// ---------------------------------------------------------------------------

test("tripItemMetadata.ts contains no provider/LLM/geocoding symbols", () => {
  assert.doesNotMatch(
    metadataSrc,
    /anthropic|openai|google_routes|geocode\(|Geocoding\(|callRouteEstimate|applyRouteReorderProposal|ReorderProposalPreview|CheckRoutePanel/i,
    "tripItemMetadata.ts must remain a pure local mapper — no provider/LLM/route-estimate/reorder symbols",
  );
});

test("handleAddResult fix does not introduce a route-estimate, reorder-proposal, or provider call", () => {
  const fnMatch = tripBuilderSrc.match(/const handleAddResult = useCallback[\s\S]{0,900}/);
  assert.ok(fnMatch);
  assert.doesNotMatch(
    fnMatch[0],
    /callRouteEstimate|applyRouteReorderProposal|ReorderProposalPreview|geocode/i,
    "handleAddResult must only extract already-present metadata — no new call sites",
  );
});
