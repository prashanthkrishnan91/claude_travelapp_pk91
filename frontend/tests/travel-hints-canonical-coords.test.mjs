/**
 * Travel Hints — canonical coordinate access contract tests.
 *
 * Verifies:
 * 1. travelHints imports readCanonicalLat and readCanonicalLng.
 * 2. Direct lat/lng details fields still resolve (backward-compat).
 * 3. latitude/longitude alias fields resolve via canonical readers.
 * 4. Nested coordinate shapes (coordinates.lat/lng) resolve via canonical readers.
 * 5. Missing/invalid coordinates still produce missing_location.
 * 6. No route optimization, reordering, or provider calls were added.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const travelHintsSrc = readFileSync(
  new URL("../src/lib/travelHints.ts", import.meta.url),
  "utf8",
);

const metadataSrc = readFileSync(
  new URL("../src/lib/tripItemMetadata.ts", import.meta.url),
  "utf8",
);

// ---------------------------------------------------------------------------
// 1. Import of canonical readers
// ---------------------------------------------------------------------------

test("travelHints imports readCanonicalLat from tripItemMetadata", () => {
  assert.match(
    travelHintsSrc,
    /import[^;]*readCanonicalLat[^;]*from.*tripItemMetadata/,
    "travelHints must import readCanonicalLat from tripItemMetadata",
  );
});

test("travelHints imports readCanonicalLng from tripItemMetadata", () => {
  assert.match(
    travelHintsSrc,
    /import[^;]*readCanonicalLng[^;]*from.*tripItemMetadata/,
    "travelHints must import readCanonicalLng from tripItemMetadata",
  );
});

test("travelHints uses readCanonicalLat in computeAdjacentHints", () => {
  assert.match(
    travelHintsSrc,
    /readCanonicalLat\(/,
    "readCanonicalLat must be called in travelHints",
  );
});

test("travelHints uses readCanonicalLng in computeAdjacentHints", () => {
  assert.match(
    travelHintsSrc,
    /readCanonicalLng\(/,
    "readCanonicalLng must be called in travelHints",
  );
});

// ---------------------------------------------------------------------------
// 2. Direct lat/lng still works — canonical reader handles it
// ---------------------------------------------------------------------------

test("readCanonicalLat resolves direct source.lat (backward compat)", () => {
  assert.match(
    metadataSrc,
    /readNumber\(source\.lat,/,
    "readCanonicalLat must try source.lat first",
  );
});

test("readCanonicalLng resolves direct source.lng (backward compat)", () => {
  assert.match(
    metadataSrc,
    /readNumber\(source\.lng,/,
    "readCanonicalLng must try source.lng first",
  );
});

// ---------------------------------------------------------------------------
// 3. latitude/longitude alias fields work
// ---------------------------------------------------------------------------

test("readCanonicalLat resolves source.latitude alias", () => {
  assert.match(
    metadataSrc,
    /readNumber\(source\.latitude,/,
    "readCanonicalLat must try source.latitude as alias",
  );
});

test("readCanonicalLng resolves source.longitude alias", () => {
  assert.match(
    metadataSrc,
    /readNumber\(source\.longitude,/,
    "readCanonicalLng must try source.longitude as alias",
  );
});

// ---------------------------------------------------------------------------
// 4. Nested coordinate shape works (e.g. coordinates.lat / coordinates.lng)
// ---------------------------------------------------------------------------

test("readCanonicalLat checks nested coordinates object", () => {
  assert.match(
    metadataSrc,
    /"coordinates"/,
    "readCanonicalLat must check nested coordinates key",
  );
});

test("readCanonicalLng checks nested coordinates object", () => {
  assert.match(
    metadataSrc,
    /"coordinates"/,
    "readCanonicalLng must check nested coordinates key",
  );
});

test("canonical readers also check nested geo/location/coords/position", () => {
  for (const k of ["geo", "location", "coords", "position"]) {
    assert.match(
      metadataSrc,
      new RegExp(`"${k}"`),
      `canonical readers must check nested key '${k}'`,
    );
  }
});

// ---------------------------------------------------------------------------
// 5. Missing/invalid coordinates still produce missing_location
// ---------------------------------------------------------------------------

test("travelHints still has missing_location branch", () => {
  assert.match(
    travelHintsSrc,
    /missing_location/,
    "missing_location kind must remain in travelHints",
  );
});

test("missing-location null-check uses == null (catches undefined from canonical readers)", () => {
  assert.match(
    travelHintsSrc,
    /lat1 == null \|\| lng1 == null \|\| lat2 == null \|\| lng2 == null/,
    "null guard must use == null so undefined from canonical readers also triggers fallback",
  );
});

test("missing-location fallback copy is preserved", () => {
  assert.match(
    travelHintsSrc,
    /Add location details to improve travel hints\./,
    "fallback label copy must remain unchanged",
  );
});

test("readCanonical returns undefined (not 0) when source has no coords", () => {
  assert.doesNotMatch(
    metadataSrc,
    /lat:\s*0\b|lng:\s*0\b/,
    "canonical readers must not default to 0",
  );
  assert.match(
    metadataSrc,
    /Number\.isFinite\(value\)/,
    "canonical readers must require a real finite number",
  );
});

// ---------------------------------------------------------------------------
// 6. No route optimization, reordering, or provider calls added
// ---------------------------------------------------------------------------

test("travelHints does not reference route optimization or RouteReadinessStatus", () => {
  assert.doesNotMatch(
    travelHintsSrc,
    /RouteReadinessStatus|optimizeRoute|routeOptimiz/,
    "travelHints must not include route-optimization concepts",
  );
});

test("travelHints does not reorder items", () => {
  assert.doesNotMatch(
    travelHintsSrc,
    /reorder|sort\(|\.sort\b/,
    "travelHints must not reorder or sort items",
  );
});

test("travelHints does not make provider or network calls", () => {
  assert.doesNotMatch(
    travelHintsSrc,
    /fetch\(|await fetch|http\.get|https\.get|DirectionsAPI|DistanceMatrix|RoutesAPI/i,
    "travelHints must remain a pure local computation — no provider calls",
  );
});

test("travelHints does not geocode", () => {
  assert.doesNotMatch(
    travelHintsSrc,
    /geocod/i,
    "travelHints must not geocode",
  );
});
