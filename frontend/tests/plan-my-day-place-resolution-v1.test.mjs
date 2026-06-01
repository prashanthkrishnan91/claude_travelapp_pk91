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
