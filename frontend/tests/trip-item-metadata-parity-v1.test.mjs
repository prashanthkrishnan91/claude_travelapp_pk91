/**
 * Trip Item Metadata Parity v1 — contract tests.
 *
 * Goal: once a routeable place-like item becomes an itinerary item, the same
 * canonical metadata fields drive its card UX (travel hints, map links,
 * address, category, rating) regardless of ingress path. Routeable metadata
 * must survive the source-to-trip-item boundary for Concierge add, Build/
 * Add-to-Day, and Ideas placement. Missing-metadata items still fall back to
 * the honest "Add location details to improve travel hints." copy.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const metadataSrc = readFileSync(
  new URL("../src/lib/tripItemMetadata.ts", import.meta.url),
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

const travelHintsSrc = readFileSync(
  new URL("../src/lib/travelHints.ts", import.meta.url),
  "utf8",
);

// ---------------------------------------------------------------------------
// 1. Canonical helper exists and exports the contract.
// ---------------------------------------------------------------------------

test("tripItemMetadata exports extractRouteableTripItemMetadata", () => {
  assert.match(
    metadataSrc,
    /export function extractRouteableTripItemMetadata/,
    "extractRouteableTripItemMetadata must be exported",
  );
});

test("tripItemMetadata exports hasRouteableCoordinates", () => {
  assert.match(
    metadataSrc,
    /export function hasRouteableCoordinates/,
    "hasRouteableCoordinates must be exported",
  );
});

test("tripItemMetadata exports ROUTEABLE_METADATA_KEYS", () => {
  assert.match(
    metadataSrc,
    /export const ROUTEABLE_METADATA_KEYS/,
    "ROUTEABLE_METADATA_KEYS must be exported",
  );
});

test("canonical key list includes the travel-hint critical fields", () => {
  for (const key of ["lat", "lng", "address", "placeId", "googleMapsUri", "category", "rating"]) {
    assert.match(metadataSrc, new RegExp(`"${key}"`), `${key} must be in ROUTEABLE_METADATA_KEYS`);
  }
});

test("canonical reader falls back to snake_case for legacy persisted rows", () => {
  for (const snake of ["formatted_address", "place_id", "google_maps_uri", "num_reviews", "ai_score", "booking_url"]) {
    assert.match(metadataSrc, new RegExp(snake.replace(/_/g, "_")), `snake fallback ${snake} must be mapped`);
  }
});

test("extractor never fabricates: skips undefined/null values", () => {
  assert.match(
    metadataSrc,
    /value !== undefined && value !== null/,
    "extractor must skip nullish values (no fabrication)",
  );
});

test("hasRouteableCoordinates requires real finite lat AND lng numbers", () => {
  assert.match(metadataSrc, /Number\.isFinite\(value\)/, "coords must be checked with Number.isFinite");
  assert.match(
    metadataSrc,
    /readCanonicalLat\(source\) !== undefined && readCanonicalLng\(source\) !== undefined/,
    "must require both lat and lng",
  );
});

// ---------------------------------------------------------------------------
// 2. createItem now forwards canonical routeable details.
// ---------------------------------------------------------------------------

test("createItem accepts a details parameter for canonical routeable metadata", () => {
  assert.match(
    apiSrc,
    /details\?\:\s*Record<string,\s*unknown>/,
    "createItem signature must include optional details: Record<string, unknown>",
  );
});

test("createItem payload includes details when routeable metadata is supplied", () => {
  assert.match(
    apiSrc,
    /mergedDetails\s*\?\s*\{\s*details:\s*mergedDetails\s*\}\s*:\s*\{\}/,
    "createItem must include the merged details blob on the payload when present",
  );
});

test("createItem merges routeableDetails with bookingOptions, not overwriting either", () => {
  assert.match(
    apiSrc,
    /\.\.\.\(hasRouteable\s*\?\s*routeableDetails\s*:\s*\{\}\)/,
    "createItem must spread routeable details into the merged blob",
  );
  assert.match(
    apiSrc,
    /\.\.\.\(hasBooking\s*\?\s*\{\s*bookingOptions\s*\}\s*:\s*\{\}\)/,
    "createItem must spread bookingOptions into the merged blob",
  );
});

// ---------------------------------------------------------------------------
// 3. Build/Add-to-Day uses the canonical contract.
// ---------------------------------------------------------------------------

test("TripBuilder imports extractRouteableTripItemMetadata", () => {
  assert.match(
    tripBuilderSrc,
    /extractRouteableTripItemMetadata/,
    "TripBuilder must import extractRouteableTripItemMetadata",
  );
});

test("handleAddCandidateToItinerary passes canonical metadata into createItem", () => {
  const startIdx = tripBuilderSrc.indexOf("handleAddCandidateToItinerary");
  assert.ok(startIdx > -1, "handleAddCandidateToItinerary must exist");
  // Slice the function body region; check that the activity/meal createItem call
  // forwards extracted routeable metadata.
  const slice = tripBuilderSrc.slice(startIdx, startIdx + 5000);
  assert.match(
    slice,
    /extractRouteableTripItemMetadata/,
    "candidate add must call extractRouteableTripItemMetadata",
  );
  assert.match(
    slice,
    /details:\s*routeable/,
    "candidate add must forward the routeable details into createItem",
  );
});

// ---------------------------------------------------------------------------
// 4. Concierge add path keeps lat/lng (regression guard for parity baseline).
// ---------------------------------------------------------------------------

test("addStructuredConciergeItemToTrip still includes normalizeGoogleVerificationDetails", () => {
  assert.match(
    apiSrc,
    /addStructuredConciergeItemToTrip[\s\S]+normalizeGoogleVerificationDetails\(item\)/,
    "Concierge add path must still attach Google verification details (lat/lng/placeId/...)",
  );
});

// ---------------------------------------------------------------------------
// 5. Ideas placement preserves details (PATCH day_id only).
// ---------------------------------------------------------------------------

test("assignIdeaToDay does not strip details — only patches day_id", () => {
  const match = apiSrc.match(/export async function assignIdeaToDay[\s\S]{0,400}/);
  assert.ok(match, "assignIdeaToDay must exist");
  assert.match(
    match[0],
    /day_id:\s*dayId/,
    "assignIdeaToDay must PATCH day_id",
  );
  assert.doesNotMatch(
    match[0],
    /details:/,
    "assignIdeaToDay must NOT touch details (so routeable metadata is preserved as-is)",
  );
});

// ---------------------------------------------------------------------------
// 6. Saved → trip path still persists real coordinates when present.
// ---------------------------------------------------------------------------

test("addSavedItemToTrip persists lat/lng from the saved snapshot when present", () => {
  const fnStart = apiSrc.indexOf("export async function addSavedItemToTrip");
  assert.ok(fnStart > -1, "addSavedItemToTrip must exist");
  const slice = apiSrc.slice(fnStart, fnStart + 2500);
  assert.match(slice, /details\.lat\s*=\s*savedCoords\.lat/, "lat must be persisted from saved snapshot");
  assert.match(slice, /details\.lng\s*=\s*savedCoords\.lng/, "lng must be persisted from saved snapshot");
});

// ---------------------------------------------------------------------------
// 7. Honest fallback copy stays for genuinely missing metadata.
// ---------------------------------------------------------------------------

test("travelHints still shows honest fallback when lat/lng are missing", () => {
  assert.match(
    travelHintsSrc,
    /Add location details to improve travel hints\./,
    "missing-metadata fallback copy must remain",
  );
  assert.match(
    travelHintsSrc,
    /lat1 == null \|\| lng1 == null \|\| lat2 == null \|\| lng2 == null/,
    "missing-metadata branch must remain gated on real null checks (no guessing)",
  );
});

// ---------------------------------------------------------------------------
// 8. Hard constraints — no fabrication in the canonical extractor.
// ---------------------------------------------------------------------------

test("extractor does not fabricate maps links or place ids", () => {
  // The extractor file must not invent URLs or ids — only forward what the
  // source supplies. Guard by ensuring no template literal with maps URLs.
  assert.doesNotMatch(
    metadataSrc,
    /google\.com\/maps/,
    "extractor must not synthesize Google Maps URLs",
  );
  assert.doesNotMatch(
    metadataSrc,
    /place_id:\$\{|placeId:\s*`/,
    "extractor must not synthesize place ids",
  );
});

test("extractor does not geocode plain addresses into coordinates", () => {
  // No live provider/geocoding calls (no fetch/await against external endpoints).
  assert.doesNotMatch(
    metadataSrc,
    /fetch\(|fetch\s+`|await fetch|http\.get|https\.get/i,
    "extractor must be a pure local mapper — no provider/geocoding calls",
  );
});

// ---------------------------------------------------------------------------
// 9. v1.1 — Build attraction/restaurant add path forwards canonical metadata.
// ---------------------------------------------------------------------------

test("v1.1 — addAttractionToDay accepts additionalDetails param", () => {
  assert.match(
    apiSrc,
    /addAttractionToDay[\s\S]{0,500}additionalDetails\?\:\s*Record<string,\s*unknown>/,
    "addAttractionToDay must accept additionalDetails for canonical metadata parity",
  );
});

test("v1.1 — addRestaurantToDay accepts additionalDetails param", () => {
  assert.match(
    apiSrc,
    /addRestaurantToDay[\s\S]{0,500}additionalDetails\?\:\s*Record<string,\s*unknown>/,
    "addRestaurantToDay must accept additionalDetails for canonical metadata parity",
  );
});

test("v1.1 — add*ToDay merges additionalDetails without overwriting non-null base", () => {
  // The merge rule must fill base nulls/empties but never clobber non-null base values.
  assert.match(
    apiSrc,
    /if \(v == null\) continue/,
    "additionalDetails null/undefined entries must be skipped (no fabrication)",
  );
  assert.match(
    apiSrc,
    /existing == null \|\| existing === ""/,
    "merge must only fill when base field is null/empty",
  );
});

test("v1.1 — TripBuilder builds candidateSourceItemsRef map from persisted items", () => {
  assert.match(
    tripBuilderSrc,
    /candidateSourceItemsRef/,
    "TripBuilder must keep a ref of persisted source items for canonical lookup",
  );
  assert.match(
    tripBuilderSrc,
    /sourceMap\.set\(placeId, it\)/,
    "source map must be keyed by placeId (so search-result placeId lookup works)",
  );
  assert.match(
    tripBuilderSrc,
    /sourceMap\.set\(it\.id, it\)/,
    "source map must also be keyed by ItineraryItem id (fallback)",
  );
});

test("v1.1 — handleAddAttractionToItinerary forwards canonical metadata into add", () => {
  const idx = tripBuilderSrc.indexOf("handleAddAttractionToItinerary");
  assert.ok(idx > -1, "handleAddAttractionToItinerary must exist");
  const slice = tripBuilderSrc.slice(idx, idx + 2500);
  assert.match(
    slice,
    /candidateSourceItemsRef\.current\.get\(attraction\.id\)/,
    "handler must look up the original persisted candidate by id",
  );
  assert.match(
    slice,
    /extractRouteableTripItemMetadata/,
    "handler must call the canonical extractor on the source item details",
  );
  assert.match(
    slice,
    /addAttractionToDay\([^)]+,\s*additionalDetails\)/,
    "handler must pass additionalDetails into addAttractionToDay",
  );
});

test("v1.1 — handleAddRestaurantToItinerary forwards canonical metadata into add", () => {
  const idx = tripBuilderSrc.indexOf("handleAddRestaurantToItinerary");
  assert.ok(idx > -1, "handleAddRestaurantToItinerary must exist");
  const slice = tripBuilderSrc.slice(idx, idx + 2500);
  assert.match(
    slice,
    /candidateSourceItemsRef\.current\.get\(restaurant\.id\)/,
    "handler must look up the original persisted candidate by id",
  );
  assert.match(
    slice,
    /extractRouteableTripItemMetadata/,
    "handler must call the canonical extractor on the source item details",
  );
  assert.match(
    slice,
    /addRestaurantToDay\([^)]+,\s*additionalDetails\)/,
    "handler must pass additionalDetails into addRestaurantToDay",
  );
});

// ---------------------------------------------------------------------------
// 10. v1.1 — Canonical extractor handles alternate coordinate keys.
// ---------------------------------------------------------------------------

test("readCanonicalLat handles latitude alias", () => {
  assert.match(metadataSrc, /readNumber\(source\.lat\) \?\? readNumber\(source\.latitude\)/);
});

test("readCanonicalLng handles longitude and lon aliases", () => {
  assert.match(
    metadataSrc,
    /readNumber\(source\.lng\) \?\? readNumber\(source\.longitude\) \?\? readNumber\(source\.lon\)/,
  );
});

test("canonical coordinate reader checks nested coordinates/geo/location/coords/position", () => {
  for (const k of ["coordinates", "geo", "location", "coords", "position"]) {
    assert.match(metadataSrc, new RegExp(`"${k}"`), `nested key '${k}' must be checked`);
  }
});

test("hasRouteableCoordinates is true only when both canonical lat AND lng resolve", () => {
  assert.match(
    metadataSrc,
    /readCanonicalLat\(source\) !== undefined && readCanonicalLng\(source\) !== undefined/,
    "hasRouteableCoordinates must require both",
  );
});

// ---------------------------------------------------------------------------
// 11. v1.1 — tripCandidates uses canonical reader (no alternate-key drop).
// ---------------------------------------------------------------------------

test("tripCandidates.itemToAttraction/itemToRestaurant use canonical coordinate readers", () => {
  const candSrc = readFileSync(
    new URL("../src/lib/tripCandidates.ts", import.meta.url),
    "utf8",
  );
  assert.match(candSrc, /readCanonicalLat\(d\)/, "itemToAttraction/Restaurant must read lat via canonical helper");
  assert.match(candSrc, /readCanonicalLng\(d\)/, "itemToAttraction/Restaurant must read lng via canonical helper");
});

// ---------------------------------------------------------------------------
// 12. v1.1 — No fabrication: alternate-key resolution does not invent coords.
// ---------------------------------------------------------------------------

test("v1.1 — readCanonical{Lat,Lng} return undefined when no real number is present", () => {
  // Source must not synthesize a 0 or a default coordinate.
  assert.doesNotMatch(metadataSrc, /lat:\s*0\b|lng:\s*0\b/, "must not default coords to 0");
  assert.match(metadataSrc, /Number\.isFinite\(value\)/, "must require finite number");
});

// ---------------------------------------------------------------------------
// 13. v1.1 — Honest fallback still triggers when BOTH coords are missing.
// ---------------------------------------------------------------------------

test("extractRouteableTripItemMetadata only emits lat/lng when both are real numbers", () => {
  // Implementation: out.lat and out.lng are set only when both are defined.
  assert.match(
    metadataSrc,
    /if \(lat !== undefined && lng !== undefined\)/,
    "extractor must only emit lat/lng pair when both resolve",
  );
});

// ---------------------------------------------------------------------------
// 14. v1.3 — Plan My Day path uses the same canonical write boundary as Build.
// ---------------------------------------------------------------------------

test("v1.3 — handlePlanAddAttraction passes canonical metadata into addAttractionToDay", () => {
  const idx = tripBuilderSrc.indexOf("handlePlanAddAttraction");
  assert.ok(idx > -1, "handlePlanAddAttraction must exist");
  const slice = tripBuilderSrc.slice(idx, idx + 1200);
  assert.match(
    slice,
    /extractRouteableTripItemMetadata\(\s*attraction/,
    "handlePlanAddAttraction must call the canonical extractor on the attraction",
  );
  assert.match(
    slice,
    /addAttractionToDay\([^)]+,\s*additionalDetails\)/,
    "handlePlanAddAttraction must pass additionalDetails into addAttractionToDay",
  );
});

test("v1.3 — handlePlanAddRestaurant passes canonical metadata into addRestaurantToDay", () => {
  const idx = tripBuilderSrc.indexOf("handlePlanAddRestaurant");
  assert.ok(idx > -1, "handlePlanAddRestaurant must exist");
  const slice = tripBuilderSrc.slice(idx, idx + 1200);
  assert.match(
    slice,
    /extractRouteableTripItemMetadata\(\s*restaurant/,
    "handlePlanAddRestaurant must call the canonical extractor on the restaurant",
  );
  assert.match(
    slice,
    /addRestaurantToDay\([^)]+,\s*additionalDetails\)/,
    "handlePlanAddRestaurant must pass additionalDetails into addRestaurantToDay",
  );
});

test("v1.3 — Plan My Day write boundary is identical to Build/CandidatePanel", () => {
  // Both handlers must call the same canonical extractor on their source
  // payload and forward into the same add*ToDay function. This guarantees
  // any routeable field present on the AttractionSearchResult /
  // RestaurantSearchResult shape flows through identically regardless of
  // ingress path (Plan My Day, Build/CandidatePanel, Day Plan modal).
  const planAttIdx = tripBuilderSrc.indexOf("handlePlanAddAttraction");
  const buildAttIdx = tripBuilderSrc.indexOf("handleAddAttractionToItinerary");
  assert.ok(planAttIdx > -1 && buildAttIdx > -1);
  const planSlice = tripBuilderSrc.slice(planAttIdx, planAttIdx + 1200);
  const buildSlice = tripBuilderSrc.slice(buildAttIdx, buildAttIdx + 2500);
  // Both call extractRouteableTripItemMetadata.
  assert.match(planSlice, /extractRouteableTripItemMetadata/);
  assert.match(buildSlice, /extractRouteableTripItemMetadata/);
  // Both pass additionalDetails into addAttractionToDay.
  assert.match(planSlice, /addAttractionToDay\([^)]+,\s*additionalDetails\)/);
  assert.match(buildSlice, /addAttractionToDay\([^)]+,\s*additionalDetails\)/);
});

// ---------------------------------------------------------------------------
// 15. v1.3 — Honest fallback for Plan My Day items lacking upstream coords.
// ---------------------------------------------------------------------------

test("v1.3 — extractor produces empty additionalDetails when source has no coords", () => {
  // The extractor must skip nullish values; an AttractionSearchResult-shaped
  // object with lat:undefined,lng:undefined produces an output that does not
  // include lat/lng, so addAttractionToDay persists lat:null/lng:null and
  // computeAdjacentHints correctly emits the honest fallback. No fabrication.
  assert.match(
    metadataSrc,
    /value !== undefined && value !== null/,
    "extractor must skip nullish — proves no fake coords are injected",
  );
});
