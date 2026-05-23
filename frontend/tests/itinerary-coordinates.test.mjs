/**
 * Journey Desk v2B — Map Coordinate Contract foundation.
 *
 * A single normalizer (lib/itineraryCoordinates.ts) extracts ONLY real
 * coordinates that already exist in source data, with strict validation. It
 * never geocodes, infers, or fabricates. The Saved -> Trip path now persists
 * real coordinates from the saved snapshot; the read side (MapFoldOut) validates
 * every persisted coordinate through the same normalizer. No SQL/schema change
 * (details JSON carries coordinates). No plotted pins yet (v2C).
 *
 * Source-scan contract tests (no TS runtime / browser in this environment).
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const util = readFileSync(
  new URL("../src/lib/itineraryCoordinates.ts", import.meta.url),
  "utf8",
);
const api = readFileSync(
  new URL("../src/lib/api.ts", import.meta.url),
  "utf8",
);
const map = readFileSync(
  new URL("../src/components/trips/MapFoldOut.tsx", import.meta.url),
  "utf8",
);

// ── Utility: strict validation, real shapes only ─────────────────────────────

test("utility exports a single coordinate extractor", () => {
  assert.match(util, /export function extractItineraryCoordinates\(source: unknown\)/);
});

test("coordinates are range-validated (lat -90..90, lng -180..180)", () => {
  assert.match(util, /lat < -90 \|\| lat > 90 \|\| lng < -180 \|\| lng > 180/);
});

test("the (0, 0) null-island placeholder is rejected", () => {
  assert.match(util, /lat === 0 && lng === 0/);
});

test("numeric strings are safely parsed; non-finite/empty rejected", () => {
  assert.match(util, /Number\(trimmed\)/);
  assert.match(util, /Number\.isFinite/);
});

test("accepts only real coordinate shapes (lat/lng, latitude/longitude, location.*, geometry.location)", () => {
  assert.match(util, /\[s\.lat, s\.lng\]/);
  assert.match(util, /\[s\.latitude, s\.longitude\]/);
  assert.match(util, /s\.location/);
  assert.match(util, /s\.geometry/);
  assert.match(util, /\.location/);
});

test("utility does NOT geocode, fabricate, or index-spread coordinates", () => {
  // Strip comments so we assert on real code, not the explanatory header.
  const code = util.replace(/\/\/.*$/gm, "").replace(/\/\*[\s\S]*?\*\//g, "");
  assert.doesNotMatch(code, /fetch\(|geocode|Nominatim|goldenSpread|spread\(|Math\.(sin|cos|random)/i);
  assert.doesNotMatch(code, /destination|address|\bcity\b|maps_link/i);
});

// ── Saved -> Trip persists real coordinates (the audited gap) ─────────────────

test("addSavedItemToTrip persists real coordinates from the saved snapshot only", () => {
  const start = api.indexOf("export async function addSavedItemToTrip");
  const end = api.indexOf("async function seedSavedFlightAsItineraryItem");
  assert.ok(start !== -1 && end > start, "addSavedItemToTrip block must exist");
  const block = api.slice(start, end);
  assert.match(block, /const savedCoords = extractItineraryCoordinates\(snap\)/);
  assert.match(block, /details\.lat = savedCoords\.lat/);
  assert.match(block, /details\.lng = savedCoords\.lng/);
  assert.match(block, /coordinateSource = "saved_item"/);
  // gated — only set when real coordinates exist
  assert.match(block, /if \(savedCoords\) \{/);
  // note carryover preserved
  assert.match(block, /details\.userNote = item\.note/);
});

test("api imports the shared coordinate normalizer", () => {
  assert.match(api, /import \{ extractItineraryCoordinates \} from "\.\/itineraryCoordinates"/);
});

// ── Trip Ideas assignment preserves details (coords survive) ──────────────────

test("assignIdeaToDay only patches day_id — it never strips item details/coordinates", () => {
  const start = api.indexOf("export async function assignIdeaToDay");
  const block = api.slice(start, start + 260);
  assert.match(block, /body: JSON\.stringify\(\{ day_id: dayId \}\)/);
  assert.doesNotMatch(block, /lat|lng|details/);
});

// ── Existing paths still persist coordinates (regression) ─────────────────────

test("Explore place + concierge paths still carry real coordinates", () => {
  assert.match(api, /lat: restaurant\.lat \?\? null/);
  assert.match(api, /lat: attraction\.lat \?\? null/);
  // concierge/Trip-Ideas path persists googleVerification coords
  assert.match(api, /\.\.\.\(lat !== undefined \? \{ lat \} : \{\}\)/);
});

// ── Read side validates every persisted coordinate ────────────────────────────

test("MapFoldOut validates persisted coordinates through the normalizer", () => {
  assert.match(map, /import \{ extractItineraryCoordinates \} from "@\/lib\/itineraryCoordinates"/);
  assert.match(map, /const coords = extractItineraryCoordinates\(x\)/);
  assert.match(map, /maps\?q=\$\{coords\.lat\},\$\{coords\.lng\}/);
});

// ── No plotted pins / no SQL in this slice ────────────────────────────────────

test("v2B introduces no plotted pin map and no fabricated positions", () => {
  assert.doesNotMatch(map, /leaflet|Leaflet|goldenSpread|heatLayer|drawMarker|L\.marker/);
});
