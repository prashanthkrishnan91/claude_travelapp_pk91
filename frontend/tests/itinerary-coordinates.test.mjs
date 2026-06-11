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
const actionSheet = readFileSync(
  new URL("../src/components/explore/ResultActionSheet.tsx", import.meta.url),
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

// ── Explore → Saved routeable metadata gap closure (upstream handoff audit) ───

test("buildSavePayload writes lat/lng from ctx.location into displaySnapshot", () => {
  // After the gap fix, ctx.location?.lat and ctx.location?.lng must appear in the
  // displaySnapshot block so extractItineraryCoordinates can recover them on the
  // Saved → Trip path. This closes the honest missing_location fallback.
  const snapshotStart = actionSheet.indexOf("const displaySnapshot");
  const snapshotEnd = actionSheet.indexOf("let searchContext", snapshotStart);
  const snapshotBlock = actionSheet.slice(snapshotStart, snapshotEnd);
  assert.ok(
    snapshotBlock.includes("ctx.location?.lat") || snapshotBlock.includes("ctx.location.lat"),
    "lat not written from ctx.location into displaySnapshot"
  );
  assert.ok(
    snapshotBlock.includes("ctx.location?.lng") || snapshotBlock.includes("ctx.location.lng"),
    "lng not written from ctx.location into displaySnapshot"
  );
});

test("buildSavePayload guards lat/lng with Number.isFinite — rejects NaN, Infinity, and non-numbers", () => {
  const snapshotStart = actionSheet.indexOf("const displaySnapshot");
  const snapshotEnd = actionSheet.indexOf("let searchContext", snapshotStart);
  const snapshotBlock = actionSheet.slice(snapshotStart, snapshotEnd);
  // Number.isFinite is the strictest guard: rejects NaN, Infinity, -Infinity, undefined
  assert.ok(
    snapshotBlock.includes("Number.isFinite"),
    "lat/lng guard must use Number.isFinite (typeof guard is not sufficient — it passes NaN and Infinity)"
  );
  // Must gate both lat and lng
  const isFiniteCount = (snapshotBlock.match(/Number\.isFinite/g) || []).length;
  assert.ok(isFiniteCount >= 2, `Number.isFinite must guard both lat and lng — found ${isFiniteCount} call(s)`);
});

test("buildSavePayload writes providerPlaceId into displaySnapshot for place identity persistence", () => {
  const snapshotStart = actionSheet.indexOf("const displaySnapshot");
  const snapshotEnd = actionSheet.indexOf("let searchContext", snapshotStart);
  const snapshotBlock = actionSheet.slice(snapshotStart, snapshotEnd);
  assert.ok(
    snapshotBlock.includes("providerPlaceId"),
    "providerPlaceId not written into displaySnapshot"
  );
});

test("addSavedItemToTrip forwards item.providerPlaceId as fallback when snapshot lacks it", () => {
  const start = api.indexOf("export async function addSavedItemToTrip");
  const end = api.indexOf("async function seedSavedFlightAsItineraryItem");
  const block = api.slice(start, end);
  assert.match(block, /item\.providerPlaceId/);
  assert.match(block, /details\.providerPlaceId/);
  // Must prefer snapshot value over top-level field
  assert.match(block, /snap\["providerPlaceId"\]/);
});

test("addSavedItemToTrip writes both providerPlaceId (camelCase) and provider_place_id (snake_case) for canonical metadata", () => {
  const start = api.indexOf("export async function addSavedItemToTrip");
  const end = api.indexOf("async function seedSavedFlightAsItineraryItem");
  const block = api.slice(start, end);
  assert.match(block, /details\.providerPlaceId = resolvedProviderPlaceId/);
  assert.match(block, /details\.provider_place_id = resolvedProviderPlaceId/);
  // Both must be written in the same guarded block
  const guardIdx = block.indexOf("if (resolvedProviderPlaceId)");
  const guardBlock = block.slice(guardIdx, guardIdx + 200);
  assert.ok(
    guardBlock.includes("providerPlaceId") && guardBlock.includes("provider_place_id"),
    "both camelCase and snake_case providerPlaceId must be written in the same guard block"
  );
});

test("addSavedItemToTrip without lat/lng in snapshot does not fabricate coordinates", () => {
  const start = api.indexOf("export async function addSavedItemToTrip");
  const end = api.indexOf("async function seedSavedFlightAsItineraryItem");
  const block = api.slice(start, end);
  // coordinates are only set inside the savedCoords guard
  assert.match(block, /if \(savedCoords\) \{/);
  // no unconditional lat/lng assignment outside the guard
  const guardedBlock = block.replace(/if \(savedCoords\) \{[\s\S]*?\}/m, "");
  assert.doesNotMatch(guardedBlock, /details\.lat = /);
  assert.doesNotMatch(guardedBlock, /details\.lng = /);
});

test("no fake coordinates, place IDs, or travel times introduced in either file", () => {
  const actionSheetCode = actionSheet.replace(/\/\/.*$/gm, "").replace(/\/\*[\s\S]*?\*\//g, "");
  assert.doesNotMatch(actionSheetCode, /geocode|Nominatim|fabricat|goldenSpread|Math\.random/i);
  const addBlock = (() => {
    const start = api.indexOf("export async function addSavedItemToTrip");
    const end = api.indexOf("async function seedSavedFlightAsItineraryItem");
    return api.slice(start, end).replace(/\/\/.*$/gm, "");
  })();
  assert.doesNotMatch(addBlock, /geocode|Nominatim|fabricat|goldenSpread|Math\.random/i);
});
