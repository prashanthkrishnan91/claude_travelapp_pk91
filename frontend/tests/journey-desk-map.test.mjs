/**
 * Journey Desk v2C — Map Fold-Out, real Trip Lens pin map.
 *
 * v2A shipped an honest map-ready list (no pins). v2B added a strict coordinate
 * contract (`extractItineraryCoordinates`). v2C plots REAL pins for placed items
 * whose `details` already carry validated coordinates, and keeps the honest
 * "Map links" list for coordinate-less items that still have a real Maps URL.
 *
 * Hard contract: pins come ONLY from `extractItineraryCoordinates`; the map
 * never geocodes, spreads by index (goldenSpread), uses a heatmap, or falls back
 * to a destination/city center. Map center/bounds derive from real pins only.
 * Trip lens only (no Day/Idea lens). v1A–v1D / v2A / v2B contracts preserved.
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
const lensMap = readFileSync(
  new URL("../src/components/trips/TripLensMap.tsx", import.meta.url),
  "utf8",
);
const css = readFileSync(
  new URL("../src/app/globals.css", import.meta.url),
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

test("header reads 'Where the trip lives' with honest Mapped + Map-links counts", () => {
  assert.match(map, /Where the trip lives/);
  // Real coordinate pins vs real links without coordinates — separate counts,
  // scoped to the active lens.
  assert.match(map, /data-testid="map-mapped-count"/);
  assert.match(map, /\{activePins\.length\} mapped/);
  assert.match(map, /data-testid="map-links-count"/);
  assert.match(map, /\{activeLinks\.length\} map link\{activeLinks\.length === 1 \? "" : "s"\}/);
});

// ── Visual Itinerary Map v1A — Trip / Day / Ideas lenses ──────────────────────

test("all three lenses ship — Trip, Day, Ideas", () => {
  assert.match(map, /type Lens = "trip" \| "day" \| "ideas";/);
  assert.match(map, /data-testid={`map-lens-\$\{tab\.key\}`}/);
  assert.match(map, /key: "trip", label: "Trip"/);
  assert.match(map, /key: "day", label: "Day"/);
  assert.match(map, /key: "ideas", label: "Ideas"/);
});

// ── Real pin eligibility — validated coordinates only ─────────────────────────

test("pin eligibility uses ONLY extractItineraryCoordinates (no inference)", () => {
  assert.match(map, /import \{ extractItineraryCoordinates \} from "@\/lib\/itineraryCoordinates"/);
  // A pin is built only when the normalizer returns coordinates.
  assert.match(map, /const coords = extractItineraryCoordinates\(det\(item\)\);/);
  assert.match(map, /if \(coords\) \{[\s\S]*?pins\.push/);
});

test("a real pin carries the placed-order number, day, time, kind and a real Maps URL", () => {
  assert.match(map, /order \+= 1;/);
  assert.match(map, /lat: coords\.lat,/);
  assert.match(map, /lng: coords\.lng,/);
  assert.match(map, /dayNumber: day\.dayNumber,/);
  // mapsUrl = the item's own link, else a real ?q=lat,lng link (never fabricated)
  assert.match(map, /mapsUrl: mapsUrlOf\(item\) \?\? `https:\/\/www\.google\.com\/maps\?q=\$\{coords\.lat\},\$\{coords\.lng\}`/);
});

test("map-ready link rows come from a real explicit link or real coordinates (v2B q-link)", () => {
  assert.match(map, /x\.maps_link as string/);
  assert.match(map, /x\.googleMapsUri as string/);
  assert.match(map, /x\.source_url as string/);
  assert.match(map, /const coords = extractItineraryCoordinates\(x\)/);
  assert.match(map, /https:\/\/www\.google\.com\/maps\?q=\$\{coords\.lat\},\$\{coords\.lng\}/);
});

test("coordinate-less items go to the link list; items with neither are omitted", () => {
  assert.match(map, /if \(mapsUrl\) linkRows\.push/);
  assert.match(map, /return null;/);
});

// ── Zero coordinates → no plotted map ─────────────────────────────────────────

test("the pin map renders only when validated coordinates exist", () => {
  assert.match(map, /const hasPins = activePins\.length > 0;/);
  assert.match(map, /\{hasPins \?[\s\S]*?<TripLensMap pins=\{activePins\}/);
});

test("zero-coordinate, zero-link trips show the honest empty state, never a fake map", () => {
  assert.match(map, /data-testid="map-empty-state"/);
  assert.match(map, /No real coordinates saved yet\./);
});

// ── The pin map fabricates nothing ────────────────────────────────────────────

test("the pin map plots real coordinates with Leaflet — no geocode/goldenSpread/heatmap/Nominatim/destination fallback", () => {
  // Leaflet is allowed (real plotting); fabrication is not.
  assert.match(lensMap, /import\("leaflet"\)/);
  assert.match(lensMap, /L\.marker\(\[pin\.lat, pin\.lng\]/);
  assert.doesNotMatch(lensMap, /geocode|Nominatim|goldenSpread|heatLayer|computeWeight/);
  assert.doesNotMatch(lensMap, /distance|polyline|drawRoute|route line|nearby/i);
  // No destination/city/index/address-based positioning anywhere.
  assert.doesNotMatch(lensMap, /destination|\bcity\b|index|\baddress\b/i);
});

test("map center/bounds derive from real pin coordinates only", () => {
  assert.match(lensMap, /const latlngs: \[number, number\]\[\] = \[\];/);
  assert.match(lensMap, /latlngs\.push\(\[pin\.lat, pin\.lng\]\)/);
  assert.match(lensMap, /map\.setView\(latlngs\[0\], 14\)/);
  assert.match(lensMap, /map\.fitBounds\(latlngs/);
});

test("MapFoldOut itself contains no plotting library or fabrication primitives", () => {
  assert.doesNotMatch(map, /leaflet|Leaflet|geocode|goldenSpread|heatLayer|Nominatim/);
  assert.doesNotMatch(map, /distance|route line|polyline|drawRoute/i);
});

// ── Honest link list preserved (v2A behavior) ─────────────────────────────────

test("link rows still open a real Maps URL in a new tab", () => {
  assert.match(map, /data-testid="map-ready-row"/);
  assert.match(map, /href=\{mapsUrl\}/);
  assert.match(map, /target="_blank"/);
});

test("honest footer explains pins come from saved coordinates only", () => {
  assert.match(map, /saved coordinates/);
});

// ── Premium "folded atlas" surface (visual patch — real pins unchanged) ──────

test("the map sits inside a warm atlas frame with a Trip-lens caption", () => {
  assert.match(map, /jd-atlas-frame/);
  assert.match(map, /jd-atlas-caption/);
  assert.match(css, /\.jd-atlas-frame\s*\{/);
  assert.match(css, /\.jd-atlas-caption\s*\{/);
});

test("OSM tiles get a scoped muted/warm filter (legibility kept, not raw default)", () => {
  assert.match(css, /\.jd-trip-map \.leaflet-tile-pane\s*\{[\s\S]*?filter:/);
  assert.match(css, /saturate\(0\.78\)/);
});

test("Leaflet zoom controls are restyled to paper with a marine hover", () => {
  assert.match(css, /\.jd-trip-map \.leaflet-control-zoom a\s*\{/);
  assert.match(css, /\.jd-trip-map \.leaflet-control-zoom a:hover\s*\{[\s\S]*?--ds-marine-ink/);
});

test("attribution is restyled but NOT hidden", () => {
  assert.match(css, /\.jd-trip-map \.leaflet-control-attribution\s*\{/);
  // Never suppress attribution.
  assert.doesNotMatch(css, /\.leaflet-control-attribution[\s\S]{0,80}display:\s*none/);
});

test("pins are brass-rimmed marine stamps with a selected state (reduced-motion safe)", () => {
  assert.match(css, /\.jd-trip-pin\s*\{[\s\S]*?--ds-marine-ink/);
  assert.match(css, /\.jd-trip-pin\s*\{[\s\S]*?--ds-ember-brass/);
  assert.match(css, /\.jd-trip-pin-wrap--selected/);
  assert.match(css, /prefers-reduced-motion: reduce[\s\S]*?\.jd-trip-pin-wrap--selected \.jd-trip-pin \{ transform: none/);
});

test("TripLensMap toggles the selected stamp class via the public marker element", () => {
  assert.match(lensMap, /marker\.getElement\(\)/);
  assert.match(lensMap, /classList\.toggle\("jd-trip-pin-wrap--selected"/);
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

test("the real pin map does not reuse the discovery TripMapView (separate, honest surface)", () => {
  assert.doesNotMatch(map, /TripMapView/);
  assert.doesNotMatch(lensMap, /TripMapView/);
});
