/**
 * Map System v1 — MapTiler provider registry + shared map visual system.
 *
 * Backend `provider_registry.py` centrally registers `maptiler_maps` (role
 * MAP_TILE, visual basemap only). The frontend resolves which tile provider
 * every map surface renders through ONE shared config (`lib/mapProvider.ts`):
 * MapTiler when a public key is configured, else the OpenStreetMap public-tile
 * fallback. Both the Journey Desk Trip Lens map (TripLensMap) and the
 * Explore/Build discovery map (TripMapView) consume that config — neither
 * hardcodes a tile URL anymore — and both share the warm muted atlas Leaflet
 * skin (.jd-trip-map + .atlas-map-surface).
 *
 * Source-scan contract tests (no DOM/browser in this environment).
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const provider = readFileSync(
  new URL("../src/lib/mapProvider.ts", import.meta.url),
  "utf8",
);
const lensMap = readFileSync(
  new URL("../src/components/trips/TripLensMap.tsx", import.meta.url),
  "utf8",
);
const tripMap = readFileSync(
  new URL("../src/components/trips/TripMapView.tsx", import.meta.url),
  "utf8",
);
const css = readFileSync(
  new URL("../src/app/globals.css", import.meta.url),
  "utf8",
);

// ── Shared config: single source of truth ─────────────────────────────────────

test("a single shared map provider config exposes the tile contract", () => {
  assert.match(provider, /export function getMapProvider\(\): MapProviderConfig/);
  assert.match(provider, /id:\s*MapProviderId/);
  assert.match(provider, /tileUrl:\s*string/);
  assert.match(provider, /attribution:\s*string/);
  assert.match(provider, /configured:\s*boolean/);
  assert.match(provider, /styleName:\s*string/);
});

test("MapTiler is preferred when its public key is configured", () => {
  assert.match(provider, /process\.env\.NEXT_PUBLIC_MAPTILER_KEY/);
  assert.match(provider, /process\.env\.NEXT_PUBLIC_MAP_PROVIDER/);
  // MapTiler tile URL is built from the public key.
  assert.match(provider, /api\.maptiler\.com\/maps\/[a-z-]+\/\{z\}\/\{x\}\/\{y\}\.png\?key=\$\{key\}/);
  assert.match(provider, /id:\s*"maptiler"/);
  assert.match(provider, /configured:\s*true/);
});

test("OpenStreetMap public tiles remain the honest fallback (key absent)", () => {
  assert.match(provider, /tile\.openstreetmap\.org\/\{z\}\/\{x\}\/\{y\}\.png/);
  assert.match(provider, /id:\s*"osm"/);
  assert.match(provider, /configured:\s*false/);
});

test("the key is public/browser-only — no server secret in the config", () => {
  // Only the NEXT_PUBLIC_ key is read; no bare/server MAPTILER_KEY.
  assert.doesNotMatch(provider, /process\.env\.MAPTILER_KEY\b/);
  assert.doesNotMatch(provider, /process\.env\.MAPTILER_SECRET/);
});

test("attribution is always provided for whichever provider is active", () => {
  assert.match(provider, /maptiler\.com\/copyright/);
  assert.match(provider, /openstreetmap\.org\/copyright/);
});

// ── Both map surfaces consume the shared config (no hardcoded tile URLs) ───────

test("TripLensMap (Journey Desk) uses the shared map provider config", () => {
  assert.match(lensMap, /import \{ getMapProvider \} from "@\/lib\/mapProvider"/);
  assert.match(lensMap, /const tiles = getMapProvider\(\);/);
  assert.match(lensMap, /L\.tileLayer\(tiles\.tileUrl, \{/);
  // No separately hardcoded tile URL remains.
  assert.doesNotMatch(lensMap, /tile\.openstreetmap\.org/);
  assert.doesNotMatch(lensMap, /api\.maptiler\.com/);
});

test("TripMapView (Explore/Build discovery) uses the shared map provider config", () => {
  assert.match(tripMap, /import \{ getMapProvider \} from "@\/lib\/mapProvider"/);
  assert.match(tripMap, /const tiles = getMapProvider\(\);/);
  assert.match(tripMap, /L\.tileLayer\(tiles\.tileUrl, \{/);
  assert.doesNotMatch(tripMap, /tile\.openstreetmap\.org/);
  assert.doesNotMatch(tripMap, /api\.maptiler\.com/);
});

// ── Shared visual system across both surfaces ─────────────────────────────────

test("the discovery map opts into the shared atlas skin scope", () => {
  assert.match(tripMap, /className="atlas-map-surface/);
});

test("both map scopes share the warm muted tile filter", () => {
  // One shared rule covers .atlas-map-surface and .jd-trip-map tile panes.
  assert.match(
    css,
    /\.atlas-map-surface \.leaflet-tile-pane,\s*\n\s*\.jd-trip-map \.leaflet-tile-pane\s*\{[\s\S]*?filter:\s*saturate\(0\.78\)/,
  );
});

test("both map scopes share paper-styled zoom controls with a marine hover", () => {
  assert.match(css, /\.atlas-map-surface \.leaflet-control-zoom a,/);
  assert.match(
    css,
    /\.atlas-map-surface \.leaflet-control-zoom a:hover,[\s\S]*?--ds-marine-ink/,
  );
});

test("attribution is restyled for both scopes but never hidden", () => {
  assert.match(css, /\.atlas-map-surface \.leaflet-control-attribution,/);
  assert.doesNotMatch(
    css,
    /\.atlas-map-surface \.leaflet-control-attribution[\s\S]{0,80}display:\s*none/,
  );
});

// ── Discovery semantics are NOT changed by this slice ─────────────────────────

test("discovery map keeps its own data behavior (heatmap/geocode/markers untouched)", () => {
  // These are the discovery map's data semantics — present and unchanged.
  assert.match(tripMap, /goldenSpread/);
  assert.match(tripMap, /heatLayer/);
  assert.match(tripMap, /geocodeCity/);
});

test("Journey Desk Trip Lens map still fabricates nothing (no discovery primitives)", () => {
  assert.doesNotMatch(lensMap, /geocode|Nominatim|goldenSpread|heatLayer|computeWeight/);
  assert.match(lensMap, /L\.marker\(\[pin\.lat, pin\.lng\]/);
});
