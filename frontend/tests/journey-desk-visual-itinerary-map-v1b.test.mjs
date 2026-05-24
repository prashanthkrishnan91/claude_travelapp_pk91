/**
 * Visual Itinerary Map v1B — safe map management + planned pin actions.
 *
 * v1A added Trip / Day / Ideas lenses + add-to-day from the map. v1B makes the
 * map feel safe and useful as a planning surface:
 *   - planned pins/list rows get useful, real-field cards with SAFE actions
 *   - actions are gated to durable existing writes ONLY:
 *       Move to Day…    → assignIdeaToDay (PATCH day_id; details preserved)
 *       Remove from day → moveIdeaToTripIdeas (PATCH day_id:null; NON-destructive)
 *       Remove from trip → deleteItem (DELETE; two-step confirm guard)
 *   - destructive deletes (trip item + idea) require an inline confirm
 *   - NO hide/show UI (no durable preference/status contract exists)
 *   - lightweight pin<->card selection sync
 *
 * Hard contract (carried from v2B/v2C/v1A): every pin comes ONLY from
 * extractItineraryCoordinates; no geocoding/goldenSpread/index/destination
 * inference; no fabricated coordinates or slot labels.
 *
 * Source-scan contract tests (no DOM/browser in this environment).
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const map = readFileSync(new URL("../src/components/trips/MapFoldOut.tsx", import.meta.url), "utf8");
const lensMap = readFileSync(new URL("../src/components/trips/TripLensMap.tsx", import.meta.url), "utf8");
const page = readFileSync(new URL("../src/app/trips/[id]/page.tsx", import.meta.url), "utf8");
const api = readFileSync(new URL("../src/lib/api.ts", import.meta.url), "utf8");

// ── Planned item cards in Trip / Day lenses ───────────────────────────────────

test("planned pins render a useful planned-item card (real fields only)", () => {
  assert.match(map, /data-testid="map-planned-card"/);
  // buildPlaced now also returns cards alongside pins (same coordinate gate).
  assert.match(map, /cards\.push\(\{ item, dayNumber: day\.dayNumber, mapsUrl \}\)/);
  assert.match(map, /const activeCards = lens === "trip" \? trip\.cards : lens === "day" \? day\.cards : \[\];/);
});

test("planned cards build from the same validated coordinate gate as pins", () => {
  assert.match(map, /const coords = extractItineraryCoordinates\(det\(item\)\);/);
  assert.match(map, /if \(coords\) \{[\s\S]*?cards\.push/);
});

// ── Actions gated to durable writes only ──────────────────────────────────────

test("Move uses the durable day-level write (assignIdeaToDay via onMoveToDay=onAssign)", () => {
  assert.match(map, /data-testid="map-planned-move"/);
  assert.match(map, /onMoveToDay\(item\.id, d\.id\)/);
  // Move only renders when there is somewhere else to move to.
  assert.match(map, /const otherDays = days\.filter\(\(d\) => d\.id !== item\.dayId\);/);
  assert.match(map, /const canMove = otherDays\.length > 0;/);
  assert.match(map, /\{canMove && !pickDay &&/);
});

test("Move never fabricates a slot/dayPart label", () => {
  assert.match(map, /Move to which day/);
  assert.doesNotMatch(map, /Dinner|Breakfast|Lunch|Morning|Afternoon|Evening/);
});

// ── Premium hybrid action pattern: Map + Move chips · More kebab ──────────────

test("planned card shows at most Map + Move chips and a kebab More button (not 4 text links)", () => {
  // Labeled icon chips for the two primary affordances.
  assert.match(map, /<MapIcon className="w-3\.5 h-3\.5"[\s\S]*?Map\s*<\/a>/);
  assert.match(map, /<CalendarDays className="w-3\.5 h-3\.5"[\s\S]*?Move\s*<\/button>/);
  // Icon-only kebab opens the overflow menu (aria-labelled for a11y).
  assert.match(map, /data-testid="map-planned-more"/);
  assert.match(map, /aria-haspopup="menu"/);
  assert.match(map, /<MoreHorizontal className="w-4 h-4"/);
  assert.match(map, /aria-label="More actions"/);
});

test("destructive + unplace actions live in the overflow menu, never side by side in the row", () => {
  assert.match(map, /data-testid="map-planned-more-menu"/);
  // The unplace + remove controls are inside the menu, not the always-visible row.
  assert.match(map, /role="menu"[\s\S]*?data-testid="map-planned-unplace"/);
  assert.match(map, /role="menu"[\s\S]*?data-testid="map-planned-remove"/);
});

test("Back to Ideas = durable unplace (moveIdeaToTripIdeas), explicit text (place-like only), not a delete", () => {
  assert.match(map, /data-testid="map-planned-unplace"/);
  assert.match(map, /onUnplace\(item\.id\)/);
  // Renamed: never "remove" wording for the non-destructive unplace.
  assert.match(map, /Back to Ideas/);
  assert.doesNotMatch(map, /Remove from day/);
  // Place-like items get Back to Ideas; anchors get Manage in Itinerary instead.
  assert.match(map, /const isAnchor = item\.itemType !== "meal" && item\.itemType !== "activity";/);
  assert.match(map, /\{isAnchor \?[\s\S]*?map-planned-manage-itinerary[\s\S]*?map-planned-unplace/);
  // Wired to the day_id:null PATCH, which preserves details.
  assert.match(page, /async function handleItemUnplace\(itemId: string\) \{\s*await moveIdeaToTripIdeas\(itemId\);/);
  assert.match(api, /export async function moveIdeaToTripIdeas\(itemId: string\)[\s\S]*?body: JSON\.stringify\(\{ day_id: null \}\)/);
});

test("flight/hotel/logistics anchors offer Manage in Itinerary (text), wired to the legacy tab", () => {
  assert.match(map, /data-testid="map-planned-manage-itinerary"/);
  assert.match(map, /Manage in Itinerary/);
  assert.match(map, /onManageItinerary\(\)/);
  assert.match(page, /onManageItinerary=\{\(\) => \{[\s\S]*?setActiveMobileWorkspace\("itinerary"\)/);
});

// ── Destructive remove requires confirmation ──────────────────────────────────

test("planned 'Remove from trip' is a permanent delete protected by a two-step confirm", () => {
  assert.match(map, /data-testid="map-planned-remove"/);
  assert.match(map, /Remove from trip/);
  // First tap arms confirm; only the confirm button calls the durable delete.
  assert.match(map, /onClick=\{\(\) => setConfirmRemove\(true\)\}/);
  assert.match(map, /data-testid="map-planned-remove-confirm"/);
  assert.match(map, /Confirm remove from trip/);
});

test("idea 'Remove idea' is a permanent delete protected by a two-step confirm", () => {
  assert.match(map, /data-testid="map-idea-remove"/);
  assert.match(map, /Remove idea/);
  assert.match(map, /data-testid="map-idea-remove-confirm"/);
  assert.match(map, /Confirm remove idea/);
  // The confirm action calls the durable delete.
  assert.match(map, /onRemove\(item\.id\)/);
});

test("destructive confirm uses the restrained warning tone, not a bright red alert", () => {
  assert.match(map, /text-ds-warning/);
  assert.doesNotMatch(map, /bg-red-|text-red-|#ff0000|bg-rose-/i);
});

// ── No hide/show UI (no durable preference contract) ──────────────────────────

test("no hide/show map-pin UI ships (no durable preference/status contract exists)", () => {
  // Note: aria-hidden is allowed (a11y); we forbid hide/show-pin *feature* surface.
  assert.doesNotMatch(map, /hide from map|show on map|hide\/show|hideFromMap|pinVisible|togglePin|hidePin|show pin|hide pin/i);
});

test("no 'remove from map' wording (Remove only deletes or unplaces — never fake-hides)", () => {
  assert.doesNotMatch(map, /remove from map/i);
});

// ── Selection / list sync ─────────────────────────────────────────────────────

test("selecting a card selects the pin, and a selected card scrolls into view", () => {
  // Card click drives the shared selectedPinId (which opens the pin popup).
  assert.match(map, /onClick=\{\(\) => onSelect\(item\.id\)\}/);
  assert.match(map, /selected \? "ring-2 ring-ds-marine-ink\/50" : ""/);
  // Lightweight: bring the selected card into view (nearest, no heavy animation).
  assert.match(map, /if \(selected && ref\.current\) ref\.current\.scrollIntoView\(\{ block: "nearest" \}\)/);
});

test("the map still drives selection back to cards via onSelect=setSelectedPinId", () => {
  assert.match(map, /<TripLensMap pins=\{activePins\} selectedId=\{selectedPinId\} onSelect=\{setSelectedPinId\}/);
  assert.match(lensMap, /marker\.on\("click", \(\) => onSelect\?\.\(pin\.id\)\)/);
});

// ── Empty / needs-location clarity ────────────────────────────────────────────

test("Day Lens empty state offers Add from Ideas only when ideas exist", () => {
  assert.match(map, /No map-ready places planned for this day yet\./);
  assert.match(map, /\{isDay && ideasExist \?/);
  assert.match(map, /data-testid="map-add-from-ideas"/);
});

test("Ideas Lens needs-location list explains those ideas can open in Maps but not plot yet", () => {
  assert.match(map, /data-testid="map-needs-location-note"/);
  assert.match(map, /can open in Google Maps but don&apos;t have coordinates to plot yet/);
  // No suggestion of geocoding / auto-placement.
  assert.doesNotMatch(map, /geocode|auto-?place|find coordinates|look up/i);
});

// ── No fabrication anywhere in the Journey Desk map files ──────────────────────

test("no geocode / Nominatim / goldenSpread / fake-coordinate strings in the map files", () => {
  for (const src of [map, lensMap]) {
    assert.doesNotMatch(src, /geocode|Nominatim|goldenSpread|heatLayer|computeWeight/);
    assert.doesNotMatch(src, /drawRoute|polyline|route line|optimi[sz]e/i);
  }
  assert.doesNotMatch(map, /leaflet|Leaflet/);
  // TripLensMap still positions pins from real coords only.
  assert.doesNotMatch(lensMap, /destination|\bcity\b|index|\baddress\b/i);
});

// ── Page wiring — new durable unplace handler + refresh ───────────────────────

test("page wires onUnplace to the durable moveIdeaToTripIdeas handler", () => {
  assert.match(page, /import \{[\s\S]*?moveIdeaToTripIdeas,[\s\S]*?\} from/);
  assert.match(page, /<MapFoldOut[\s\S]*?onUnplace=\{handleItemUnplace\}/);
});

test("unplace + delete both refresh days and ideas so all counts stay coherent", () => {
  assert.match(page, /async function refreshDaysAndIdeas\(\) \{[\s\S]*?setItineraryDays\(days\);[\s\S]*?refreshIdeas\(\);/);
  assert.match(page, /async function handleItemUnplace\(itemId: string\) \{[\s\S]*?await refreshDaysAndIdeas\(\);/);
  assert.match(page, /async function handleIdeaRemove\(itemId: string\) \{[\s\S]*?await deleteItem\(itemId\);[\s\S]*?await refreshDaysAndIdeas\(\);/);
});

// ── v1A behavior preserved ────────────────────────────────────────────────────

test("v1A lenses + add-to-day are preserved", () => {
  assert.match(map, /data-testid="map-lens-trip"|map-lens-\$\{tab\.key\}/);
  assert.match(map, /async function assignFromIdeas\(itemId: string, dayId: string\) \{\s*await onAssign\(itemId, dayId\);/);
  assert.match(map, /setLens\("day"\);/);
  assert.match(map, /data-testid="map-idea-add-to-day"/);
});
