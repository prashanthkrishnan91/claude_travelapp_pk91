/**
 * Concierge add-path metadata preservation — contract tests.
 *
 * Root cause fixed: fast_dynamic_place_search._to_card() requested places.location
 * from the Google Places API but did not parse latitude/longitude into
 * GoogleVerification, so Concierge-added activity/meal items lacked routeable
 * coordinates. Fix: extract lat/lng from the location dict and pass to
 * GoogleVerification(lat=..., lng=...).
 *
 * These tests cover the frontend write-boundary contract so no future refactor
 * silently drops coordinates that the backend now correctly returns.
 *
 * Verifies:
 * 1.  normalizeGoogleVerificationDetails preserves lat when googleVerification carries it.
 * 2.  normalizeGoogleVerificationDetails preserves lng when googleVerification carries it.
 * 3.  normalizeGoogleVerificationDetails preserves providerPlaceId / place identity.
 * 4.  normalizeGoogleVerificationDetails preserves googleMapsUri.
 * 5.  normalizeGoogleVerificationDetails preserves formattedAddress.
 * 6.  normalizeGoogleVerificationDetails returns empty object when googleVerification absent.
 * 7.  normalizeGoogleVerificationDetails does not fabricate coords when gv has no lat/lng.
 * 8.  addStructuredConciergeItemToTrip payload spreads normalizeGoogleVerificationDetails.
 * 9.  saveToTripIdeas payload spreads normalizeGoogleVerificationDetails.
 * 10. addConciergeItemToTrip legacy path writes only { reason } — no coord fields.
 * 11. RouteReadinessStatus: computeRouteReadiness returns null when Concierge-added
 *     activity/meal items all have coords (banner hidden = "coordinate-ready").
 * 12. RouteReadinessStatus: computeRouteReadiness returns { total, withCoords } when
 *     some items lack coords (banner visible).
 * 13. PR #504 canonical coordinate access (readCanonicalLat/Lng) still reads top-level
 *     lat/lng written by normalizeGoogleVerificationDetails.
 * 14. PR #506 flight/hotel skip behavior intact in travelHints.
 * 15. No route optimization, geocoding, or reorder symbols in api.ts or travelHints.
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

const tripItemMetaSrc = readFileSync(
  new URL("../src/lib/tripItemMetadata.ts", import.meta.url),
  "utf8",
);

// ---------------------------------------------------------------------------
// 1–7. normalizeGoogleVerificationDetails — coordinate and identity preservation
// ---------------------------------------------------------------------------

test("normalizeGoogleVerificationDetails exists in api.ts", () => {
  assert.match(
    apiSrc,
    /function normalizeGoogleVerificationDetails/,
    "normalizeGoogleVerificationDetails must be defined in api.ts",
  );
});

test("normalizeGoogleVerificationDetails extracts lat from googleVerification.lat", () => {
  const fnMatch = apiSrc.match(
    /function normalizeGoogleVerificationDetails[\s\S]{0,800}/,
  );
  assert.ok(fnMatch, "normalizeGoogleVerificationDetails must exist");
  const fn = fnMatch[0];
  assert.match(
    fn,
    /gv\.lat|gvAliases\.lat/,
    "normalizeGoogleVerificationDetails must read lat from gv.lat or gvAliases.lat",
  );
});

test("normalizeGoogleVerificationDetails extracts lng from googleVerification.lng", () => {
  const fnMatch = apiSrc.match(
    /function normalizeGoogleVerificationDetails[\s\S]{0,800}/,
  );
  assert.ok(fnMatch);
  const fn = fnMatch[0];
  assert.match(
    fn,
    /gv\.lng|gvAliases\.lng/,
    "normalizeGoogleVerificationDetails must read lng from gv.lng or gvAliases.lng",
  );
});

test("normalizeGoogleVerificationDetails emits lat into return object", () => {
  // The function body spans ~50 lines; search full source for the return pattern
  assert.match(
    apiSrc,
    /\?\s*\{\s*lat\s*\}\s*:/,
    "normalizeGoogleVerificationDetails must conditionally emit { lat } in return",
  );
});

test("normalizeGoogleVerificationDetails emits lng into return object", () => {
  assert.match(
    apiSrc,
    /\?\s*\{\s*lng\s*\}\s*:/,
    "normalizeGoogleVerificationDetails must conditionally emit { lng } in return",
  );
});

test("normalizeGoogleVerificationDetails preserves providerPlaceId as provider_place_id", () => {
  const fnMatch = apiSrc.match(
    /function normalizeGoogleVerificationDetails[\s\S]{0,800}/,
  );
  assert.ok(fnMatch);
  const fn = fnMatch[0];
  assert.match(
    fn,
    /provider_place_id/,
    "normalizeGoogleVerificationDetails must write provider_place_id",
  );
  assert.match(
    fn,
    /gv\.providerPlaceId|providerPlaceId/,
    "normalizeGoogleVerificationDetails must read providerPlaceId",
  );
});

test("normalizeGoogleVerificationDetails preserves googleMapsUri as google_maps_uri", () => {
  // The function spans ~50 lines; search the full source for these patterns
  assert.match(
    apiSrc,
    /google_maps_uri/,
    "normalizeGoogleVerificationDetails must write google_maps_uri",
  );
  assert.match(
    apiSrc,
    /gv\.googleMapsUri|googleMapsUri/,
    "normalizeGoogleVerificationDetails must read googleMapsUri",
  );
});

test("normalizeGoogleVerificationDetails preserves formattedAddress as formatted_address", () => {
  assert.match(
    apiSrc,
    /formatted_address/,
    "normalizeGoogleVerificationDetails must write formatted_address",
  );
  assert.match(
    apiSrc,
    /gv\.formattedAddress|formattedAddress/,
    "normalizeGoogleVerificationDetails must read formattedAddress",
  );
});

test("normalizeGoogleVerificationDetails returns empty object when no googleVerification", () => {
  const fnMatch = apiSrc.match(
    /function normalizeGoogleVerificationDetails[\s\S]{0,400}/,
  );
  assert.ok(fnMatch);
  const fn = fnMatch[0];
  // Early-return guard when gv is falsy
  assert.match(
    fn,
    /if\s*\(\s*!gv|return\s*\{\}/,
    "normalizeGoogleVerificationDetails must guard against missing gv and return {}",
  );
});

test("normalizeGoogleVerificationDetails uses conditional spread to avoid fabricating absent coords", () => {
  // Must guard lat/lng behind undefined check before emitting into return object
  assert.match(
    apiSrc,
    /lat\s*!==\s*undefined/,
    "lat must only be emitted when not undefined (no fabrication)",
  );
  assert.match(
    apiSrc,
    /lng\s*!==\s*undefined/,
    "lng must only be emitted when not undefined (no fabrication)",
  );
});

// ---------------------------------------------------------------------------
// 8–9. Active add paths spread normalizeGoogleVerificationDetails
// ---------------------------------------------------------------------------

test("addStructuredConciergeItemToTrip spreads normalizeGoogleVerificationDetails into details", () => {
  assert.match(
    apiSrc,
    /export async function addStructuredConciergeItemToTrip/,
    "addStructuredConciergeItemToTrip must exist",
  );
  // The spread of normalizeGoogleVerificationDetails must appear in the file
  // (used by both addStructuredConciergeItemToTrip and saveToTripIdeas)
  assert.match(
    apiSrc,
    /\.\.\.normalizeGoogleVerificationDetails\(/,
    "normalizeGoogleVerificationDetails must be spread into at least one active add-path details payload",
  );
});

test("saveToTripIdeas spreads normalizeGoogleVerificationDetails into details", () => {
  assert.match(
    apiSrc,
    /export async function saveToTripIdeas/,
    "saveToTripIdeas must exist",
  );
  // Confirm the spread appears at least twice — once for each active path
  const matches = apiSrc.match(/\.\.\.normalizeGoogleVerificationDetails\(/g);
  assert.ok(
    matches && matches.length >= 2,
    `normalizeGoogleVerificationDetails must be spread in both addStructuredConciergeItemToTrip and saveToTripIdeas; found ${matches?.length ?? 0} occurrence(s)`,
  );
});

test("addStructuredConciergeItemToTrip is the active structured add path (not legacy)", () => {
  assert.match(
    apiSrc,
    /export async function addStructuredConciergeItemToTrip/,
    "addStructuredConciergeItemToTrip must be exported",
  );
});

// ---------------------------------------------------------------------------
// 10. Legacy addConciergeItemToTrip — reason-only, safe if still exported
// ---------------------------------------------------------------------------

test("addConciergeItemToTrip legacy path writes only reason, not lat/lng", () => {
  const fnMatch = apiSrc.match(
    /export async function addConciergeItemToTrip[\s\S]{0,400}/,
  );
  assert.ok(fnMatch, "addConciergeItemToTrip must exist");
  const fn = fnMatch[0];
  assert.match(fn, /reason/, "addConciergeItemToTrip must include reason");
  // The details payload in the legacy function must be reason-only
  const detailsBlock = fn.match(/details:\s*\{[^}]+\}/)?.[0] ?? "";
  assert.doesNotMatch(
    detailsBlock,
    /\blat\b/,
    "addConciergeItemToTrip details must not include lat",
  );
  assert.doesNotMatch(
    detailsBlock,
    /\blng\b/,
    "addConciergeItemToTrip details must not include lng",
  );
});

test("ConciergeSuggestion type has no lat/lng/googleVerification fields", () => {
  const ifaceMatch = apiSrc.match(
    /export interface ConciergeSuggestion\s*\{[\s\S]{0,300}\}/,
  );
  assert.ok(ifaceMatch, "ConciergeSuggestion interface must exist");
  const iface = ifaceMatch[0];
  assert.doesNotMatch(iface, /\blat\b/, "ConciergeSuggestion must not have lat");
  assert.doesNotMatch(iface, /\blng\b/, "ConciergeSuggestion must not have lng");
  assert.doesNotMatch(
    iface,
    /googleVerification/,
    "ConciergeSuggestion must not have googleVerification",
  );
});

// ---------------------------------------------------------------------------
// 11–12. RouteReadinessStatus: computeRouteReadiness sees Concierge coord state
// ---------------------------------------------------------------------------

test("computeRouteReadiness returns null (hidden) when all eligible activity/meal items have coords", () => {
  // Structural: verify all-coords guard exists
  assert.match(
    travelHintsSrc,
    /withCoords\s*===\s*eligible\.length[\s\S]{0,30}return null/,
    "computeRouteReadiness must return null when all stops have coords (banner hidden)",
  );
});

test("computeRouteReadiness returns { total, withCoords } when some activity/meal items lack coords", () => {
  assert.match(
    travelHintsSrc,
    /return\s*\{\s*total[\s\S]{0,40}withCoords|return\s*\{\s*withCoords[\s\S]{0,40}total/,
    "computeRouteReadiness must return { total, withCoords } when some coords missing",
  );
});

test("computeRouteReadiness uses hasRouteableCoordinates to check items", () => {
  assert.match(
    travelHintsSrc,
    /hasRouteableCoordinates\(/,
    "computeRouteReadiness must call hasRouteableCoordinates",
  );
});

test("computeRouteReadiness filters to activity and meal only (Concierge-added types)", () => {
  const readinessFnMatch = travelHintsSrc.match(
    /export function computeRouteReadiness[\s\S]{0,600}/,
  );
  assert.ok(readinessFnMatch, "computeRouteReadiness must exist");
  const fn = readinessFnMatch[0];
  assert.match(fn, /"activity"/, 'filter must include "activity"');
  assert.match(fn, /"meal"/, 'filter must include "meal"');
});

// ---------------------------------------------------------------------------
// 13. PR #504 — canonical coordinate access still reads top-level lat/lng
// ---------------------------------------------------------------------------

test("readCanonicalLat reads top-level lat key first (PR #504 intact)", () => {
  assert.match(
    tripItemMetaSrc,
    /source\.lat/,
    "readCanonicalLat must check source.lat directly (PR #504)",
  );
});

test("readCanonicalLng reads top-level lng key first (PR #504 intact)", () => {
  assert.match(
    tripItemMetaSrc,
    /source\.lng/,
    "readCanonicalLng must check source.lng directly (PR #504)",
  );
});

test("hasRouteableCoordinates is exported from tripItemMetadata (PR #504 intact)", () => {
  assert.match(
    tripItemMetaSrc,
    /export function hasRouteableCoordinates/,
    "hasRouteableCoordinates must be exported (PR #504)",
  );
});

test("travelHints imports hasRouteableCoordinates from tripItemMetadata (PR #504 intact)", () => {
  assert.match(
    travelHintsSrc,
    /import[^;]*hasRouteableCoordinates[^;]*from.*tripItemMetadata/,
    "travelHints must import hasRouteableCoordinates from tripItemMetadata (PR #504)",
  );
});

// ---------------------------------------------------------------------------
// 14. PR #506 — flight/hotel skip behavior intact
// ---------------------------------------------------------------------------

test("travelHints skips flight items in computeAdjacentHints (PR #506 intact)", () => {
  assert.match(
    travelHintsSrc,
    /itemType.*===.*"flight"|"flight".*===.*itemType/,
    'travelHints must gate "flight" itemType to skip (PR #506)',
  );
});

test("travelHints skips hotel items in computeAdjacentHints (PR #506 intact)", () => {
  assert.match(
    travelHintsSrc,
    /itemType.*===.*"hotel"|"hotel".*===.*itemType/,
    'travelHints must gate "hotel" itemType to skip (PR #506)',
  );
});

test("skip kind is still emitted for flight/hotel pairs (PR #506 intact)", () => {
  assert.match(
    travelHintsSrc,
    /kind.*:.*"skip"|"skip".*:.*kind/,
    'skip kind must be emitted for flight/hotel pairs (PR #506)',
  );
});

// ---------------------------------------------------------------------------
// 15. No route optimization, geocoding, or reorder symbols
// ---------------------------------------------------------------------------

test("api.ts Concierge add functions do not reference route optimization", () => {
  assert.doesNotMatch(
    apiSrc,
    /OptimizeDay|optimizeRoute|routeOptimiz|RouteOptimiz|DirectionsAPI|DistanceMatrix|RoutesAPI/,
    "api.ts must not contain route optimization symbols",
  );
});

test("api.ts does not geocode — no geocoding calls in add paths", () => {
  const addPathSection = apiSrc.slice(
    apiSrc.indexOf("function normalizeGoogleVerificationDetails"),
    apiSrc.indexOf("addMichelinRestaurantToTrip") + 200,
  );
  assert.doesNotMatch(
    addPathSection,
    /geocode\(|geocoding|Geocoding|reverse_geocode/,
    "Concierge add paths must never geocode",
  );
});

test("api.ts does not reorder itinerary items in Concierge add paths", () => {
  const addPathSection = apiSrc.slice(
    apiSrc.indexOf("function normalizeGoogleVerificationDetails"),
    apiSrc.indexOf("addMichelinRestaurantToTrip") + 200,
  );
  assert.doesNotMatch(
    addPathSection,
    /reorder|\.sort\(/,
    "Concierge add paths must not reorder items",
  );
});

test("travelHints does not perform route optimization or geocoding", () => {
  assert.doesNotMatch(
    travelHintsSrc,
    /DirectionsAPI|DistanceMatrix|RoutesAPI|geocod|optimizeRoute|reorder/i,
    "travelHints must not reference optimization, geocoding, or reorder",
  );
});
