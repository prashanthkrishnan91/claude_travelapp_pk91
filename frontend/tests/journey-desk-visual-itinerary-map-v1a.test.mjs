/**
 * Visual Itinerary Map v1A — Day Lens + Ideas Lens + map-based add-to-day.
 *
 * Builds on the v2C real Trip Lens pin map. Adds a restrained Trip / Day / Ideas
 * lens switcher inside the Map Fold-Out:
 *   - Trip Lens  : all placed map-ready items (unchanged behavior).
 *   - Day Lens   : the selected day's placed map-ready items only.
 *   - Ideas Lens : unplaced Trip Ideas with validated real coordinates, with a
 *                  durable day-level "Add to Day…" action.
 *
 * Hard contract (carried from v2B/v2C): every pin on every lens comes ONLY from
 * `extractItineraryCoordinates`. No geocoding, no goldenSpread, no index/city/
 * destination/address inference, no fabricated coordinates, no fabricated slot
 * labels (placement is day-level only — there is no durable slot persistence).
 *
 * Source-scan contract tests (no DOM/browser in this environment).
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const map = readFileSync(new URL("../src/components/trips/MapFoldOut.tsx", import.meta.url), "utf8");
const lensMap = readFileSync(new URL("../src/components/trips/TripLensMap.tsx", import.meta.url), "utf8");
const css = readFileSync(new URL("../src/app/globals.css", import.meta.url), "utf8");
const page = readFileSync(new URL("../src/app/trips/[id]/page.tsx", import.meta.url), "utf8");
const api = readFileSync(new URL("../src/lib/api.ts", import.meta.url), "utf8");

// ── Lens switcher ─────────────────────────────────────────────────────────────

test("lens switcher renders Trip / Day / Ideas with honest counts", () => {
  assert.match(map, /role="tablist"/);
  assert.match(map, /data-testid={`map-lens-\$\{tab\.key\}`}/);
  assert.match(map, /key: "trip", label: "Trip"/);
  assert.match(map, /key: "day", label: "Day"/);
  assert.match(map, /key: "ideas", label: "Ideas"/);
  // Counts are derived from the real pin arrays for each lens.
  assert.match(map, /label: "Trip", count: trip\.pins\.length/);
  assert.match(map, /label: "Day", count: day\.pins\.length/);
  assert.match(map, /label: "Ideas", count: ideaPins\.length/);
});

test("the active lens drives which pins and links render", () => {
  assert.match(map, /const activePins = lens === "trip" \? trip\.pins : lens === "day" \? day\.pins : ideaPins;/);
  assert.match(map, /const activeLinks = lens === "trip" \? trip\.linkRows : lens === "day" \? day\.linkRows : \[\];/);
});

// ── Day Lens — filters placed pins to one real day ────────────────────────────

test("Day Lens defaults to the selected Dayboard day, else the first trip day", () => {
  assert.match(map, /days\.find\(\(d\) => d\.id === selectedDayId\) \?\? days\[0\] \?\? null/);
  // The day pins come from buildPlaced over just that one day.
  assert.match(map, /buildPlaced\(dayLensDay \? \[dayLensDay\] : \[\]\)/);
});

test("Day Lens offers day chips that re-select the day (synced to the page)", () => {
  assert.match(map, /data-testid="map-day-chips"/);
  assert.match(map, /data-testid={`map-day-chip-\$\{d\.dayNumber\}`}/);
  assert.match(map, /onSelectDay\?\.\(d\.id\)/);
});

test("Day Lens empty state is honest and offers Add from Ideas (no fake nearby/route)", () => {
  assert.match(map, /No map-ready places planned for this day yet\./);
  assert.match(map, /data-testid="map-add-from-ideas"/);
  assert.match(map, /Add from Ideas/);
  assert.doesNotMatch(map, /nearby|optimi[sz]e|route/i);
});

// ── Ideas Lens — only unplaced ideas with validated coordinates ───────────────

test("Ideas Lens plots ONLY ideas with validated coordinates as idea pins", () => {
  // Same normalizer gate as placed pins.
  assert.match(map, /for \(const item of ideas\) \{[\s\S]*?const coords = extractItineraryCoordinates\(det\(item\)\);/);
  assert.match(map, /if \(coords\) \{[\s\S]*?variant: "idea",/);
  // Coordinate-less ideas only become link rows when a real Maps URL exists.
  assert.match(map, /else if \(mapsUrlOf\(item\)\) \{[\s\S]*?linkItems\.push\(item\)/);
});

test("idea pins carry a real saved note (when present) and a real Maps URL only", () => {
  assert.match(map, /note: userNoteOf\(item\) \|\| null,/);
  assert.match(map, /mapsUrl: mapsUrlOf\(item\) \?\? `https:\/\/www\.google\.com\/maps\?q=\$\{coords\.lat\},\$\{coords\.lng\}`/);
});

test("ideas with neither coordinates nor a real Maps URL are omitted (never faked)", () => {
  // No catch-all push of every idea — only coords or real-URL ideas surface.
  assert.doesNotMatch(map, /ideas\.forEach[\s\S]*?pins\.push/);
  assert.match(map, /data-testid="map-ideas-no-pins"/);
});

// ── Add to Day — durable day-level assignment, no fabricated slot ─────────────

test("Add to Day uses the durable day-level assignment and follows the idea into its day", () => {
  assert.match(map, /data-testid="map-idea-add-to-day"/);
  // assignFromIdeas awaits the real assignment, then selects + shows that day.
  assert.match(map, /async function assignFromIdeas\(itemId: string, dayId: string\) \{\s*await onAssign\(itemId, dayId\);/);
  assert.match(map, /onSelectDay\?\.\(dayId\);/);
  assert.match(map, /setLens\("day"\);/);
});

test("Add to Day is day-level only — no fabricated Dinner/Morning/Evening slot label", () => {
  assert.match(map, /Add to which day/);
  assert.doesNotMatch(map, /Dinner|Breakfast|Lunch|Morning|Afternoon|Evening/);
});

test("assignIdeaToDay only PATCHes day_id — server keeps details (coords survive)", () => {
  assert.match(api, /export async function assignIdeaToDay\(itemId: string, dayId: string\)/);
  assert.match(api, /assignIdeaToDay[\s\S]*?body: JSON\.stringify\(\{ day_id: dayId \}\)/);
});

// ── Only durable Ideas actions are exposed ────────────────────────────────────

test("Ideas Lens exposes only durable actions — Keep as Maybe (updateIdeaMeta) + Remove (deleteItem)", () => {
  // Keep as Maybe maps to the existing ideaStatus write.
  assert.match(map, /onUpdateMeta\(item\.id, det\(item\), \{ ideaStatus: "maybe" \}\)/);
  assert.match(map, /Keep as Maybe/);
  // Remove maps to the existing delete.
  assert.match(map, /onRemove\(item\.id\)/);
  assert.match(map, /Remove/);
});

// ── No fabrication anywhere in the Journey Desk map files ──────────────────────

test("no geocode / Nominatim / goldenSpread / fake-coordinate strings in the map files", () => {
  for (const src of [map, lensMap]) {
    assert.doesNotMatch(src, /geocode|Nominatim|goldenSpread|heatLayer|computeWeight/);
    assert.doesNotMatch(src, /drawRoute|polyline|route line|optimi[sz]e/i);
  }
  // MapFoldOut delegates plotting to TripLensMap (no Leaflet in the fold-out).
  assert.doesNotMatch(map, /leaflet|Leaflet/);
});

// ── Idea pin marker — same family, visually distinct ──────────────────────────

test("TripLensMap renders a distinct idea marker for the idea variant", () => {
  assert.match(lensMap, /variant\?: "planned" \| "idea";/);
  assert.match(lensMap, /pin\.variant === "idea"[\s\S]*?jd-idea-pin/);
  // Planned stamp keeps its numbered marker.
  assert.match(lensMap, /<span class="jd-trip-pin">\$\{escapeHtml\(String\(pin\.order\)\)\}<\/span>/);
});

test("idea marker CSS is the brass family, visually distinct, reduced-motion safe", () => {
  assert.match(css, /\.jd-idea-pin\s*\{[\s\S]*?--ds-ember-brass/);
  assert.match(css, /\.jd-trip-pin-wrap--selected \.jd-idea-pin/);
  assert.match(css, /prefers-reduced-motion: reduce[\s\S]*?\.jd-trip-pin-wrap--selected \.jd-idea-pin \{ transform: none/);
});

test("lens switcher CSS uses ds tokens (marine/brass), reduced-motion safe — no SaaS color", () => {
  assert.match(css, /\.jd-lens-tab\s*\{/);
  assert.match(css, /\.jd-lens-tab--active\s*\{[\s\S]*?--ds-marine-ink/);
  assert.match(css, /prefers-reduced-motion: reduce[\s\S]*?\.jd-lens-tab \{ transition: none/);
  assert.doesNotMatch(css, /\.jd-lens-tab[\s\S]{0,200}#[0-9a-fA-F]{6}/);
});

// ── Page wiring — real durable handlers + refresh after assignment ────────────

test("page wires the new MapFoldOut props to the existing durable handlers", () => {
  assert.match(page, /<MapFoldOut[\s\S]*?ideas=\{tripIdeas\}/);
  assert.match(page, /<MapFoldOut[\s\S]*?selectedDayId=\{selectedDayId\}/);
  assert.match(page, /<MapFoldOut[\s\S]*?onSelectDay=\{\(dayId\) => setSelectedDayId\(dayId\)\}/);
  assert.match(page, /<MapFoldOut[\s\S]*?onAssign=\{handleIdeaAssign\}/);
  assert.match(page, /<MapFoldOut[\s\S]*?onUpdateMeta=\{handleIdeaMeta\}/);
  assert.match(page, /<MapFoldOut[\s\S]*?onRemove=\{handleIdeaRemove\}/);
});

test("assignment refreshes days + ideas counts (existing handler re-fetches both)", () => {
  // handleIdeaAssign re-derives days and re-fetches ideas, so all lens counts
  // (Trip / Day / Ideas) and the Brief/Dayboard update after a placement.
  assert.match(page, /async function handleIdeaAssign\(itemId: string, dayId: string\) \{[\s\S]*?await assignIdeaToDay\(itemId, dayId\);[\s\S]*?setItineraryDays\(days\);[\s\S]*?refreshIdeas\(\);/);
});
