/**
 * Map System v1B — shared marker + popup visual polish.
 *
 * PR #474 unified the basemap (MapTiler central registry + shared
 * `lib/mapProvider.ts`). v1B makes the Explore/Build discovery map
 * (`TripMapView`) wear the same Private Travel Atelier / Journey Desk language:
 * a warm paper popup, a restrained marine/brass marker family, and a
 * marine-ink "Add to Trip" CTA — replacing the generic white card, bright-blue
 * CTA, and blue/orange SaaS dots. Visual-only: no behavior, no data, no
 * provider/config changes. Journey Desk's no-fake-pin contract is preserved.
 *
 * Source-scan contract tests (no DOM/browser in this environment).
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const tripMap = readFileSync(
  new URL("../src/components/trips/TripMapView.tsx", import.meta.url),
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

// ── Popup: warm paper Atelier, not a generic white card ───────────────────────

test("the discovery popup uses the shared warm-paper Atelier shell", () => {
  assert.match(tripMap, /className="atlas-map-popup/);
  assert.match(css, /\.atlas-map-popup\s*\{[\s\S]*?var\(--ds-warm-paper\)/);
  // Brass-hairline + paper elevation (matches the Journey Desk popup language).
  assert.match(css, /\.atlas-map-popup\s*\{[\s\S]*?--ds-ember-brass[\s\S]*?--ds-paper-elevation-2/);
  // No leftover generic white card / slate chrome on the popup container.
  assert.doesNotMatch(tripMap, /bg-white rounded-xl shadow-xl border border-slate-200/);
});

test("the popup title is serif and facts use muted folio tokens", () => {
  assert.match(tripMap, /font-serif text-sm font-semibold text-ds-folio-ink/);
  assert.match(tripMap, /text-ds-folio-ink-mist/);
  // Tags are calm paper chips, not bright blue/orange utility pills.
  assert.match(tripMap, /className="atlas-map-popup-chip"/);
  assert.doesNotMatch(tripMap, /bg-blue-100 text-blue-700/);
  assert.doesNotMatch(tripMap, /bg-orange-100 text-orange-700/);
});

// ── CTA: marine Atelier primary, not bright SaaS blue ─────────────────────────

test("the Add to Trip CTA uses the marine Atelier primary, not bright sky blue", () => {
  assert.match(tripMap, /Add to Trip/);
  assert.match(tripMap, /bg-ds-marine-ink hover:bg-ds-marine-soft text-ds-paper/);
  assert.doesNotMatch(tripMap, /bg-sky-600 hover:bg-sky-500 text-white/);
});

test("Add to Trip behavior is unchanged (still calls handleAddFromPopup)", () => {
  assert.match(tripMap, /onClick=\{handleAddFromPopup\}/);
  assert.match(tripMap, /disabled=\{addingId !== null\}/);
});

// ── Markers: shared premium family, not generic blue/orange dots ──────────────

test("markers use the shared atlas marker family (marine / ember), not inline blue/orange dots", () => {
  assert.match(tripMap, /class="atlas-map-marker-dot atlas-map-marker-dot--\$\{variant\}"/);
  assert.match(tripMap, /className: "atlas-map-marker"/);
  assert.match(tripMap, /makeIcon\("attraction"\)/);
  assert.match(tripMap, /makeIcon\("restaurant"\)/);
  // The old hardcoded SaaS dot colors are gone.
  assert.doesNotMatch(tripMap, /#2563eb/);
  assert.doesNotMatch(tripMap, /#ea580c/);
});

test("the marker family is defined with marine/brass tokens + a reduced-motion-safe active state", () => {
  assert.match(css, /\.atlas-map-marker-dot--attraction\s*\{[\s\S]*?--ds-marine-ink/);
  assert.match(css, /\.atlas-map-marker-dot--restaurant\s*\{[\s\S]*?--ds-ember-brass/);
  assert.match(css, /\.atlas-map-marker--active \.atlas-map-marker-dot\s*\{[\s\S]*?--ds-ember-brass/);
  assert.match(css, /prefers-reduced-motion: reduce[\s\S]*?\.atlas-map-marker--active \.atlas-map-marker-dot \{ transform: none/);
});

test("the active marker class is toggled via the public marker element (visual only)", () => {
  assert.match(tripMap, /classList\.toggle\("atlas-map-marker--active"/);
  // panTo behavior preserved.
  assert.match(tripMap, /panTo\(marker\.getLatLng\(\)/);
});

// ── Provider/config + attribution preserved (PR #474 contract) ────────────────

test("both surfaces still consume the shared map provider config", () => {
  assert.match(tripMap, /const tiles = getMapProvider\(\);/);
  assert.match(lensMap, /const tiles = getMapProvider\(\);/);
});

test("attribution is still restyled, never hidden, for both map scopes", () => {
  assert.match(css, /\.atlas-map-surface \.leaflet-control-attribution,/);
  assert.doesNotMatch(
    css,
    /\.atlas-map-surface \.leaflet-control-attribution[\s\S]{0,80}display:\s*none/,
  );
});

// ── Discovery data semantics + Journey Desk no-fake contract unchanged ────────

test("discovery data logic is untouched (goldenSpread/heatmap/geocode still present)", () => {
  assert.match(tripMap, /goldenSpread/);
  assert.match(tripMap, /heatLayer/);
  assert.match(tripMap, /geocodeCity/);
});

test("Journey Desk Trip Lens map still fabricates nothing", () => {
  assert.doesNotMatch(lensMap, /geocode|Nominatim|goldenSpread|heatLayer|computeWeight/);
  assert.match(lensMap, /L\.marker\(\[pin\.lat, pin\.lng\]/);
});
