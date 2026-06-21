/**
 * Plan My Day Place Resolution v1 — contract tests.
 *
 * Goal (follow-up to PR #499): before Plan My Day writes place-like
 * recommendations into the itinerary, they are resolved into the same canonical
 * routeable trip-item metadata contract used by Build/Concierge whenever
 * possible. When the existing Google Places resolution succeeds upstream, a
 * Plan My Day-added place carries lat/lng + placeId + googleMapsUri and becomes
 * route-hint eligible with the same fields as Build/Concierge. When resolution
 * fails, the placed item keeps the honest "Add location details" fallback —
 * no fabricated coordinates or place ids.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const typesSrc = readFileSync(
  new URL("../src/types/index.ts", import.meta.url),
  "utf8",
);
const apiSrc = readFileSync(
  new URL("../src/lib/api.ts", import.meta.url),
  "utf8",
);
const tripBuilderSrc = readFileSync(
  new URL("../src/components/trips/TripBuilder.tsx", import.meta.url),
  "utf8",
);
const metadataSrc = readFileSync(
  new URL("../src/lib/tripItemMetadata.ts", import.meta.url),
  "utf8",
);

// ---------------------------------------------------------------------------
// 1. AttractionSearchResult carries canonical place identity (parity with
//    RestaurantSearchResult), so resolved day-plan attractions persist it.
// ---------------------------------------------------------------------------

test("AttractionSearchResult declares placeId / googleMapsUri identity", () => {
  const block = typesSrc.split("export interface AttractionSearchResult")[1]
    .split("export interface")[0];
  assert.match(block, /placeId\?: string/);
  assert.match(block, /googleMapsUri\?: string/);
  assert.match(block, /providerPlaceId\?: string/);
});

test("RestaurantSearchResult still carries place identity (regression)", () => {
  const block = typesSrc.split("export interface RestaurantSearchResult")[1]
    .split("export interface")[0];
  assert.match(block, /placeId\?: string/);
  assert.match(block, /googleMapsUri\?: string/);
});

// ---------------------------------------------------------------------------
// 2. addAttractionToDay / addRestaurantToDay persist canonical place identity.
// ---------------------------------------------------------------------------

test("addAttractionToDay persists place_id + google_maps_uri from source", () => {
  const block = apiSrc.split("export async function addAttractionToDay")[1]
    .split("export async function")[0];
  assert.match(block, /place_id: attraction\.placeId \?\? null/);
  assert.match(block, /google_maps_uri: attraction\.googleMapsUri \?\? null/);
});

test("addRestaurantToDay persists place_id + google_maps_uri from source", () => {
  const block = apiSrc.split("export async function addRestaurantToDay")[1]
    .split("export async function")[0];
  assert.match(block, /place_id: restaurant\.placeId \?\? null/);
  assert.match(block, /google_maps_uri: restaurant\.googleMapsUri \?\? null/);
});

// ---------------------------------------------------------------------------
// 3. Plan My Day handlers route through the canonical extractor (same write
//    boundary as Build/Concierge) — a resolved item uses the same fields.
// ---------------------------------------------------------------------------

test("Plan My Day attraction handler uses extractRouteableTripItemMetadata", () => {
  const block = tripBuilderSrc.split("handlePlanAddAttraction")[1]
    .split("handlePlanAddRestaurant")[0];
  assert.match(block, /extractRouteableTripItemMetadata\(/);
  assert.match(block, /addAttractionToDay\(/);
});

test("Plan My Day restaurant handler uses extractRouteableTripItemMetadata", () => {
  const block = tripBuilderSrc.split("handlePlanAddRestaurant")[1]
    .split("handleAddResult")[0];
  assert.match(block, /extractRouteableTripItemMetadata\(/);
  assert.match(block, /addRestaurantToDay\(/);
});

// ---------------------------------------------------------------------------
// 4. The canonical extractor forwards placeId / googleMapsUri / coords — so a
//    resolved Plan My Day item is route-hint eligible with the same fields as
//    Build/Concierge.
// ---------------------------------------------------------------------------

test("ROUTEABLE_METADATA_KEYS includes placeId + googleMapsUri + coords", () => {
  const block = metadataSrc.split("ROUTEABLE_METADATA_KEYS")[1].split("] as const")[0];
  for (const key of ["placeId", "googleMapsUri", "lat", "lng"]) {
    assert.match(block, new RegExp(`"${key}"`), `extractor must forward ${key}`);
  }
});

// ---------------------------------------------------------------------------
// 5. Regression: Build/Add-to-Day path (#499) still recovers richer metadata
//    from the persisted candidate source row via candidateSourceItemsRef.
// ---------------------------------------------------------------------------

test("Build/Add-to-Day still reads candidateSourceItemsRef (PR #499 contract)", () => {
  assert.match(
    tripBuilderSrc,
    /candidateSourceItemsRef\.current\.get\(attraction\.id\)/,
    "Build attraction handler must still recover the persisted source row",
  );
});

// ---------------------------------------------------------------------------
// 6. No fabrication: extractor never invents coordinates or place ids.
// ---------------------------------------------------------------------------

test("extractor never geocodes / fabricates (no network, comment contract)", () => {
  assert.match(metadataSrc, /Never fabricates/i);
  assert.match(metadataSrc, /Never geocodes/i);
  assert.doesNotMatch(metadataSrc, /fetch\(|geocode\(|axios/);
});

test("addAttraction/addRestaurant only persist identity when present (?? null)", () => {
  // Honest fallback: when the source lacks identity, null is written — never
  // a fabricated place id or coordinate.
  assert.match(apiSrc, /place_id: attraction\.placeId \?\? null/);
  assert.match(apiSrc, /place_id: restaurant\.placeId \?\? null/);
});

// ---------------------------------------------------------------------------
// 7. Coordinate pass-through — lat/lng persist when present.
//    Acceptance criteria: "Plan My Day attraction with lat/lng persists
//    canonical coords" / "Plan My Day restaurant/meal with lat/lng persists
//    canonical coords".
// ---------------------------------------------------------------------------

test("addAttractionToDay writes attraction.lat ?? null into baseDetails.lat", () => {
  // When the Plan My Day upstream response carries lat (from Google Places
  // resolution or bulk search), addAttractionToDay reads attraction.lat
  // directly. ?? null ensures: real number passes through; absent → null.
  const block = apiSrc.split("export async function addAttractionToDay")[1]
    .split("export async function")[0];
  assert.match(block, /lat: attraction\.lat \?\? null/);
});

test("addAttractionToDay writes attraction.lng ?? null into baseDetails.lng", () => {
  const block = apiSrc.split("export async function addAttractionToDay")[1]
    .split("export async function")[0];
  assert.match(block, /lng: attraction\.lng \?\? null/);
});

test("addRestaurantToDay writes restaurant.lat ?? null into baseDetails.lat", () => {
  const block = apiSrc.split("export async function addRestaurantToDay")[1]
    .split("export async function")[0];
  assert.match(block, /lat: restaurant\.lat \?\? null/);
});

test("addRestaurantToDay writes restaurant.lng ?? null into baseDetails.lng", () => {
  const block = apiSrc.split("export async function addRestaurantToDay")[1]
    .split("export async function")[0];
  assert.match(block, /lng: restaurant\.lng \?\? null/);
});

// ---------------------------------------------------------------------------
// 8. Honest fallback — ?? null, not ?? 0 / not geocoded.
//    Acceptance criteria: "Plan My Day does not fabricate coordinates when
//    none exist" / "Missing-coord upstream result remains honest fallback".
// ---------------------------------------------------------------------------

test("addAttractionToDay lat/lng fallback is null — no fabricated zeros or geocoding", () => {
  const block = apiSrc.split("export async function addAttractionToDay")[1]
    .split("export async function")[0];
  assert.match(block, /lat: attraction\.lat \?\? null/);
  assert.doesNotMatch(block, /lat: attraction\.lat \?\? 0\b/);
  assert.doesNotMatch(block, /geocode/i);
});

test("addRestaurantToDay lat/lng fallback is null — no fabricated zeros or geocoding", () => {
  const block = apiSrc.split("export async function addRestaurantToDay")[1]
    .split("export async function")[0];
  assert.match(block, /lat: restaurant\.lat \?\? null/);
  assert.doesNotMatch(block, /lat: restaurant\.lat \?\? 0\b/);
  assert.doesNotMatch(block, /geocode/i);
});

// ---------------------------------------------------------------------------
// 9. gp- prefix safety — placeId (not id) is used for place_id persistence.
//    Acceptance criteria: "gp- prefixed place id does not cause metadata
//    recovery failure if a canonical source item exists".
//
//    search_attraction_results stamps id="gp-{place_id}" but place_id="{place_id}"
//    separately. addAttractionToDay must persist the clean placeId field, not
//    the gp-prefixed id — so the persisted place_id stays usable for map links
//    and route readiness without the "gp-" prefix leaking.
// ---------------------------------------------------------------------------

test("addAttractionToDay uses attraction.placeId (not attraction.id) for place_id — gp-prefix safe", () => {
  const block = apiSrc.split("export async function addAttractionToDay")[1]
    .split("export async function")[0];
  assert.match(block, /place_id: attraction\.placeId \?\? null/);
  assert.doesNotMatch(block, /place_id: attraction\.id/);
});

test("addRestaurantToDay uses restaurant.placeId (not restaurant.id) for place_id — gp-prefix safe", () => {
  const block = apiSrc.split("export async function addRestaurantToDay")[1]
    .split("export async function")[0];
  assert.match(block, /place_id: restaurant\.placeId \?\? null/);
  assert.doesNotMatch(block, /place_id: restaurant\.id/);
});

// ---------------------------------------------------------------------------
// 10. Build / Concierge / Saved / Ideas regression.
//     Acceptance criteria: "Existing working add paths are regression-protected".
// ---------------------------------------------------------------------------

test("Concierge add: addStructuredConciergeItemToTrip still uses normalizeGoogleVerificationDetails", () => {
  // Regression guard: the Concierge add path spreads lat/lng/placeId from
  // googleVerification via this helper. Plan My Day changes must not disturb it.
  const block = apiSrc.split("export async function addStructuredConciergeItemToTrip")[1]
    .split("export async function")[0];
  assert.match(block, /normalizeGoogleVerificationDetails\(item\)/);
});

test("Ideas path: saveToTripIdeas still uses normalizeGoogleVerificationDetails", () => {
  const block = apiSrc.split("export async function saveToTripIdeas")[1]
    .split("export async function")[0];
  assert.match(block, /normalizeGoogleVerificationDetails\(item\)/);
});

test("Saved path: addSavedItemToTrip still persists lat/lng from snapshot coordinates", () => {
  const fnStart = apiSrc.indexOf("export async function addSavedItemToTrip");
  assert.ok(fnStart > -1, "addSavedItemToTrip must exist");
  const slice = apiSrc.slice(fnStart, fnStart + 2500);
  assert.match(slice, /details\.lat\s*=\s*savedCoords\.lat/);
  assert.match(slice, /details\.lng\s*=\s*savedCoords\.lng/);
});

test("Build path: handlePlanAddAttraction does NOT read candidateSourceItemsRef (v1.4 revert guard)", () => {
  // Regression guard: Plan My Day handler must NOT recover coords from
  // candidateSourceItemsRef (reverted in v1.4 to protect Build regression).
  // Plan My Day relies on upstream server-side resolution, not the local cache.
  const planBlock = tripBuilderSrc.split("handlePlanAddAttraction")[1]
    .split("handlePlanAddRestaurant")[0];
  assert.doesNotMatch(
    planBlock,
    /candidateSourceItemsRef/,
    "handlePlanAddAttraction must NOT read candidateSourceItemsRef (v1.4 revert contract)",
  );
});
