/**
 * Journey Desk v2A — Map Fold-Out, Trip Lens only.
 *
 * Audit finding: placed itinerary items carry Google Maps URLs / addresses, not
 * a durable per-item coordinate contract (only some hotels persist real lat/lng).
 * So v2A does NOT plot pins — it opens an honest "Where the trip lives" fold-out
 * listing only map-ready placed items, each opening a REAL Google Maps URL (the
 * item's own link, or ?q=lat,lng built from real coords). No fake pins/coords/
 * routes/distances/counts. Day/Idea lenses are deferred to v2B.
 *
 * Source-scan contract tests (no DOM/browser in this environment).
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const map = readFileSync(
  new URL("../src/components/trips/MapFoldOut.tsx", import.meta.url),
  "utf8",
);
const dayboard = readFileSync(
  new URL("../src/components/trips/Dayboard.tsx", import.meta.url),
  "utf8",
);
const page = readFileSync(
  new URL("../src/app/trips/[id]/page.tsx", import.meta.url),
  "utf8",
);

// ── Fold-out shell ──────────────────────────────────────────────────────────

test("map fold-out is a modal dialog drawer with a stable testid", () => {
  assert.match(map, /data-testid="journey-desk-map"/);
  assert.match(map, /role="dialog"/);
  assert.match(map, /aria-modal="true"/);
});

test("fold-out is a bottom sheet on mobile / right drawer on desktop (reuses tray shell + reduced-motion)", () => {
  assert.match(map, /journey-desk-tray jd-tray-enter/);
  assert.match(map, /bottom-0/);
  assert.match(map, /lg:right-0/);
});

test("fold-out closes on Escape and close control", () => {
  assert.match(map, /e\.key === "Escape"/);
  assert.match(map, /aria-label="Close trip map"/);
});

test("header reads 'Where the trip lives' with a real map-ready count", () => {
  assert.match(map, /Where the trip lives/);
  assert.match(map, /data-testid="map-ready-count"/);
  assert.match(map, /\{rows\.length\} map-ready place\{rows\.length === 1 \? "" : "s"\}/);
});

// ── Trip Lens only (Day / Idea lenses deferred) ───────────────────────────────

test("only the Trip lens ships — no Day or Idea lens", () => {
  assert.match(map, /Trip lens/);
  assert.doesNotMatch(map, /Day lens|Idea lens|Day Lens|Idea Lens/);
});

// ── Honest map-readiness — real links only, no fake plotting ──────────────────

test("map-ready URL comes from a real link or real coordinates only", () => {
  assert.match(map, /x\.maps_link as string/);
  assert.match(map, /x\.googleMapsUri as string/);
  assert.match(map, /x\.source_url as string/);
  // real coords -> a real Google Maps q-link (never a fabricated position)
  assert.match(map, /typeof lat === "number" && typeof lng === "number"/);
  assert.match(map, /https:\/\/www\.google\.com\/maps\?q=\$\{lat\},\$\{lng\}/);
});

test("items without a real map link are omitted (no placeholders)", () => {
  assert.match(map, /if \(mapsUrl\) rows\.push/);
  assert.match(map, /return null;/);
});

test("rows open the real Maps URL in a new tab", () => {
  assert.match(map, /data-testid="map-ready-row"/);
  assert.match(map, /href=\{mapsUrl\}/);
  assert.match(map, /target="_blank"/);
});

test("no fake pins, coordinates, routes, distances, geocoding, or heatmap", () => {
  assert.doesNotMatch(map, /leaflet|Leaflet|geocode|goldenSpread|heatLayer|Nominatim/);
  assert.doesNotMatch(map, /distance|route line|polyline|drawRoute/i);
});

test("honest footer explains a plotted map needs saved coordinates", () => {
  assert.match(map, /saved coordinates/);
});

// ── Single quiet entry point ──────────────────────────────────────────────────

test("the Dayboard exposes a single quiet 'Trip map' entry point", () => {
  assert.match(dayboard, /data-testid="journey-desk-trip-map-link"/);
  assert.match(dayboard, /Trip map/);
  assert.match(dayboard, /onOpenMap &&/);
});

// ── Page integration ──────────────────────────────────────────────────────────

test("page wires the map fold-out from the Dayboard 'Trip map' link", () => {
  assert.match(page, /import \{ MapFoldOut \} from "@\/components\/trips\/MapFoldOut"/);
  assert.match(page, /const \[mapOpen,\s*setMapOpen\]\s*=\s*useState\(false\)/);
  assert.match(page, /onOpenMap=\{\(\) => setMapOpen\(true\)\}/);
  assert.match(page, /<MapFoldOut[\s\S]{0,120}open=\{mapOpen\}/);
});

test("v1A–v1D surfaces are not regressed", () => {
  assert.match(page, /data-testid="trip-chapter-cover"/);
  assert.match(page, /<TripBrief/);
  assert.match(page, /<Dayboard/);
  assert.match(page, /<ExpandedDayPanel/);
  assert.match(page, /<IdeasTray/);
});

test("MapFoldOut does not import or reuse the discovery TripMapView (separate, honest surface)", () => {
  assert.doesNotMatch(map, /TripMapView/);
});
