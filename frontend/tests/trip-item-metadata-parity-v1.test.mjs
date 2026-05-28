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
  assert.match(metadataSrc, /Number\.isFinite\(lat\)/, "lat must be checked with Number.isFinite");
  assert.match(metadataSrc, /Number\.isFinite\(lng\)/, "lng must be checked with Number.isFinite");
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
  assert.doesNotMatch(
    metadataSrc,
    /geocode|geocoding|fetch\(|fetch `/i,
    "extractor must be a pure local mapper — no provider/geocoding calls",
  );
});
