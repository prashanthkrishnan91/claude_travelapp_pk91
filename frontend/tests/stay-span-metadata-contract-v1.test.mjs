/**
 * Stay-span + reservation metadata contract v1 — source-scan contract tests.
 *
 * Guards the invariants from this slice:
 *
 *  1. Hotel card reads canonical checkIn/checkOut keys first (after toCamel normalization).
 *  2. Hotel card retains tolerant fallbacks: check_in, check_out, check_in_date, check_out_date, checkInDate, checkOutDate.
 *  3. formatClock handles plain HH:mm time strings (reservation/entry times).
 *  4. Meal card renders "Reservation · {time}" label when reservationTime present.
 *  5. Activity card renders "Entry · {time}" label when entryTime present.
 *  6. Missing metadata renders nothing (hasAny guards include reservationTime/entryTime).
 *  7. Hotel editor inputs are type="date" (check-in, check-out).
 *  8. Meal editor input is type="time" (reservation).
 *  9. Activity editor input is type="time" (entry).
 * 10. Save path calls updateItemMetadata (not updateItemTimeline or dayPart).
 * 11. updateItemMetadata merges details and calls updateItem.
 * 12. Empty values delete/omit metadata keys (no stale key after clear).
 * 13. Unrelated detail keys preserved (spread current details).
 * 14. timeLabel/dayPart not reused for reservation/entry fixed facts.
 * 15. Brief remains read-only (no updateItemMetadata call added).
 * 16. AddToDayDrawer/Build/search files untouched by this slice.
 * 17. api.ts item 5 skip stated: addHotelToTrip does not invent check-in/out dates.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const itemCard = readFileSync(
  new URL("../src/components/trips/ItineraryItemCard.tsx", import.meta.url),
  "utf8",
);
const apiSrc = readFileSync(
  new URL("../src/lib/api.ts", import.meta.url),
  "utf8",
);
const brief = readFileSync(
  new URL("../src/components/trips/TripBrief.tsx", import.meta.url),
  "utf8",
);
const addToDayDrawer = readFileSync(
  new URL("../src/components/trips/AddToDayDrawer.tsx", import.meta.url),
  "utf8",
);
const tripBuilder = readFileSync(
  new URL("../src/components/trips/TripBuilder.tsx", import.meta.url),
  "utf8",
);

// ── 1. Hotel card: canonical checkIn/checkOut keys read first ─────────────────

test("ItineraryItemCard hotel block reads d.checkIn as first-priority key", () => {
  const hotelIdx = itemCard.indexOf('item.itemType === "hotel"');
  assert.ok(hotelIdx >= 0, "hotel block must exist");
  const hotelBlock = itemCard.slice(hotelIdx, hotelIdx + 600);
  assert.match(hotelBlock, /d\.checkIn/, "hotel block must read d.checkIn (canonical camelCase key)");
});

test("ItineraryItemCard hotel block reads d.checkOut as first-priority key", () => {
  const hotelIdx = itemCard.indexOf('item.itemType === "hotel"');
  const hotelBlock = itemCard.slice(hotelIdx, hotelIdx + 600);
  assert.match(hotelBlock, /d\.checkOut/, "hotel block must read d.checkOut (canonical camelCase key)");
});

test("ItineraryItemCard hotel block: checkIn canonical key appears before fallbacks in the chain", () => {
  const hotelIdx = itemCard.indexOf('item.itemType === "hotel"');
  const hotelBlock = itemCard.slice(hotelIdx, hotelIdx + 600);
  const camelIdx = hotelBlock.indexOf("d.checkIn");
  const snakeIdx = hotelBlock.indexOf("d.check_in");
  assert.ok(camelIdx >= 0, "d.checkIn must exist");
  assert.ok(snakeIdx >= 0, "d.check_in must exist");
  assert.ok(camelIdx < snakeIdx, "d.checkIn must appear before d.check_in in the fallback chain");
});

// ── 2. Hotel card: tolerant fallbacks retained ────────────────────────────────

test("ItineraryItemCard hotel block still reads d.check_in as fallback", () => {
  assert.match(itemCard, /d\.check_in\b/, "hotel block must still read d.check_in fallback");
});

test("ItineraryItemCard hotel block still reads d.check_out as fallback", () => {
  assert.match(itemCard, /d\.check_out\b/, "hotel block must still read d.check_out fallback");
});

test("ItineraryItemCard hotel block retains check_in_date fallback", () => {
  assert.match(itemCard, /d\.check_in_date/, "hotel block must retain d.check_in_date fallback");
});

test("ItineraryItemCard hotel block retains checkInDate fallback", () => {
  assert.match(itemCard, /d\.checkInDate/, "hotel block must retain d.checkInDate fallback");
});

// ── 3. formatClock handles plain HH:mm ───────────────────────────────────────

test("formatClock has a plain HH:mm regex handler for reservation/entry times", () => {
  assert.match(
    itemCard,
    /const plain = value\.match/,
    "formatClock must have a plain HH:mm match for reservation/entry times",
  );
});

test("formatClock handles plain time — pattern and conversion block present", () => {
  // Verify both the regex and the 12h conversion appear together for the plain case
  assert.match(itemCard, /plain/, "formatClock must have a 'plain' variable for HH:mm handling");
  // The conversion math appears for the plain branch
  const plainIdx = itemCard.indexOf("const plain = value.match");
  assert.ok(plainIdx >= 0, "plain match must be declared in formatClock");
  const plainBlock = itemCard.slice(plainIdx, plainIdx + 300);
  assert.match(plainBlock, /hour24.*Number.*plain/, "plain branch must convert hour to number");
  assert.match(plainBlock, /hour12/, "plain branch must compute 12-hour clock");
  assert.match(plainBlock, /ampm/, "plain branch must compute AM/PM");
});

// ── 4. Meal card: Reservation · {time} label ─────────────────────────────────

test("ItineraryItemCard meal block reads d.reservationTime", () => {
  // Use the JSX render block (not the handler which also contains "meal")
  const mealIdx = itemCard.indexOf('item.itemType === "meal" && (() => {');
  assert.ok(mealIdx >= 0, "meal JSX render block must exist");
  const mealBlock = itemCard.slice(mealIdx, mealIdx + 3000);
  assert.match(mealBlock, /reservationTime/, "meal block must read d.reservationTime");
});

test("ItineraryItemCard meal block renders 'Reservation ·' fixed-fact label", () => {
  const mealIdx = itemCard.indexOf('item.itemType === "meal" && (() => {');
  const mealBlock = itemCard.slice(mealIdx, mealIdx + 3000);
  assert.match(mealBlock, /Reservation\s*·/, "meal block must render 'Reservation ·' label");
});

test("ItineraryItemCard meal block has meal-reservation-fact testid", () => {
  assert.match(itemCard, /data-testid="meal-reservation-fact"/, "meal block must have meal-reservation-fact testid");
});

// ── 5. Activity card: Entry · {time} label ───────────────────────────────────

test("ItineraryItemCard activity block reads d.entryTime", () => {
  // Use the JSX render block (not the handler which also contains "activity")
  const actIdx = itemCard.indexOf('item.itemType === "activity" && (() => {');
  assert.ok(actIdx >= 0, "activity JSX render block must exist");
  const actBlock = itemCard.slice(actIdx, actIdx + 4000);
  assert.match(actBlock, /entryTime/, "activity block must read d.entryTime");
});

test("ItineraryItemCard activity block renders 'Entry ·' fixed-fact label", () => {
  const actIdx = itemCard.indexOf('item.itemType === "activity" && (() => {');
  const actBlock = itemCard.slice(actIdx, actIdx + 4000);
  assert.match(actBlock, /Entry\s*·/, "activity block must render 'Entry ·' label");
});

test("ItineraryItemCard activity block has activity-entry-fact testid", () => {
  assert.match(itemCard, /data-testid="activity-entry-fact"/, "activity block must have activity-entry-fact testid");
});

// ── 6. Missing metadata renders nothing (hasAny guards updated) ───────────────

test("ItineraryItemCard meal hasAny guard includes formattedReservation", () => {
  const mealIdx = itemCard.indexOf('item.itemType === "meal" && (() => {');
  const mealBlock = itemCard.slice(mealIdx, mealIdx + 3000);
  assert.match(
    mealBlock,
    /formattedReservation/,
    "meal hasAny guard must include formattedReservation so block renders when only reservation exists",
  );
});

test("ItineraryItemCard activity hasAny guard includes formattedEntryTime", () => {
  const actIdx = itemCard.indexOf('item.itemType === "activity" && (() => {');
  const actBlock = itemCard.slice(actIdx, actIdx + 4000);
  assert.match(
    actBlock,
    /formattedEntryTime/,
    "activity hasAny guard must include formattedEntryTime so block renders when only entry exists",
  );
});

// ── 7. Hotel editor: date inputs ─────────────────────────────────────────────

test("ItineraryItemCard hotel meta editor has check-in date input", () => {
  assert.match(
    itemCard,
    /data-testid="itinerary-meta-check-in"/,
    "hotel editor must have itinerary-meta-check-in testid",
  );
});

test("ItineraryItemCard hotel meta editor check-in input is type date", () => {
  const idx = itemCard.indexOf('data-testid="itinerary-meta-check-in"');
  assert.ok(idx >= 0, "check-in input must exist");
  // Look in a window around the testid for type="date"
  const ctx = itemCard.slice(Math.max(0, idx - 300), idx + 50);
  assert.match(ctx, /type="date"/, "check-in input must be type=date");
});

test("ItineraryItemCard hotel meta editor has check-out date input", () => {
  assert.match(
    itemCard,
    /data-testid="itinerary-meta-check-out"/,
    "hotel editor must have itinerary-meta-check-out testid",
  );
});

test("ItineraryItemCard hotel meta editor check-out input is type date", () => {
  const idx = itemCard.indexOf('data-testid="itinerary-meta-check-out"');
  assert.ok(idx >= 0, "check-out input must exist");
  const ctx = itemCard.slice(Math.max(0, idx - 300), idx + 50);
  assert.match(ctx, /type="date"/, "check-out input must be type=date");
});

// ── 8. Meal editor: time input ───────────────────────────────────────────────

test("ItineraryItemCard meal meta editor has reservation-time input", () => {
  assert.match(
    itemCard,
    /data-testid="itinerary-meta-reservation-time"/,
    "meal editor must have itinerary-meta-reservation-time testid",
  );
});

test("ItineraryItemCard meal meta editor reservation input is type time", () => {
  const idx = itemCard.indexOf('data-testid="itinerary-meta-reservation-time"');
  assert.ok(idx >= 0, "reservation-time input must exist");
  const ctx = itemCard.slice(Math.max(0, idx - 300), idx + 50);
  assert.match(ctx, /type="time"/, "reservation-time input must be type=time");
});

// ── 9. Activity editor: time input ───────────────────────────────────────────

test("ItineraryItemCard activity meta editor has entry-time input", () => {
  assert.match(
    itemCard,
    /data-testid="itinerary-meta-entry-time"/,
    "activity editor must have itinerary-meta-entry-time testid",
  );
});

test("ItineraryItemCard activity meta editor entry input is type time", () => {
  const idx = itemCard.indexOf('data-testid="itinerary-meta-entry-time"');
  assert.ok(idx >= 0, "entry-time input must exist");
  const ctx = itemCard.slice(Math.max(0, idx - 300), idx + 50);
  assert.match(ctx, /type="time"/, "entry-time input must be type=time");
});

// ── 10. Save path calls updateItemMetadata ───────────────────────────────────

test("ItineraryItemCard imports updateItemMetadata from api", () => {
  assert.match(
    itemCard,
    /import\s*\{[^}]*updateItemMetadata[^}]*\}\s*from\s*["']@\/lib\/api["']/,
    "ItineraryItemCard must import updateItemMetadata from @/lib/api",
  );
});

test("ItineraryItemCard handleSaveMetadata calls updateItemMetadata", () => {
  assert.match(
    itemCard,
    /handleSaveMetadata[\s\S]{0,1500}updateItemMetadata/,
    "handleSaveMetadata must call updateItemMetadata",
  );
});

test("ItineraryItemCard meta editor save button has itinerary-meta-save testid", () => {
  assert.match(
    itemCard,
    /data-testid="itinerary-meta-save"/,
    "meta editor save button must have itinerary-meta-save testid",
  );
});

test("ItineraryItemCard handleSaveMetadata passes item.id and currentDetails to updateItemMetadata", () => {
  const idx = itemCard.indexOf("handleSaveMetadata");
  const fnBlock = itemCard.slice(idx, idx + 1000);
  assert.match(fnBlock, /updateItemMetadata\(item\.id/, "must call updateItemMetadata with item.id");
  assert.match(fnBlock, /currentDetails/, "must pass currentDetails to updateItemMetadata");
});

// ── 11. updateItemMetadata in api.ts: merges and calls updateItem ─────────────

test("api.ts exports updateItemMetadata", () => {
  assert.match(
    apiSrc,
    /export async function updateItemMetadata\(/,
    "api.ts must export updateItemMetadata",
  );
});

test("updateItemMetadata spreads currentDetails to preserve unrelated keys", () => {
  const fnIdx = apiSrc.indexOf("export async function updateItemMetadata(");
  assert.ok(fnIdx >= 0, "updateItemMetadata must exist");
  const fnBlock = apiSrc.slice(fnIdx, fnIdx + 800);
  assert.match(fnBlock, /\.\.\.\s*currentDetails/, "updateItemMetadata must spread currentDetails");
});

test("updateItemMetadata calls updateItem", () => {
  const fnIdx = apiSrc.indexOf("export async function updateItemMetadata(");
  const fnBlock = apiSrc.slice(fnIdx, fnIdx + 1200);
  assert.match(fnBlock, /return updateItem\(/, "updateItemMetadata must call updateItem");
});

test("updateItemMetadata patch type includes checkIn and checkOut", () => {
  const fnIdx = apiSrc.indexOf("export async function updateItemMetadata(");
  const fnBlock = apiSrc.slice(fnIdx, fnIdx + 300);
  assert.match(fnBlock, /checkIn\?.*string|checkIn.*string/, "patch must include checkIn");
  assert.match(fnBlock, /checkOut\?.*string|checkOut.*string/, "patch must include checkOut");
});

test("updateItemMetadata patch type includes reservationTime and entryTime", () => {
  const fnIdx = apiSrc.indexOf("export async function updateItemMetadata(");
  const fnBlock = apiSrc.slice(fnIdx, fnIdx + 300);
  assert.match(fnBlock, /reservationTime/, "patch must include reservationTime");
  assert.match(fnBlock, /entryTime/, "patch must include entryTime");
});

// ── 12. Empty values delete metadata keys ────────────────────────────────────

test("updateItemMetadata deletes checkIn when value is empty/falsy", () => {
  const fnIdx = apiSrc.indexOf("export async function updateItemMetadata(");
  const fnBlock = apiSrc.slice(fnIdx, fnIdx + 800);
  assert.match(fnBlock, /delete merged\.checkIn/, "must delete merged.checkIn when empty");
});

test("updateItemMetadata deletes checkOut when value is empty/falsy", () => {
  const fnIdx = apiSrc.indexOf("export async function updateItemMetadata(");
  const fnBlock = apiSrc.slice(fnIdx, fnIdx + 800);
  assert.match(fnBlock, /delete merged\.checkOut/, "must delete merged.checkOut when empty");
});

test("updateItemMetadata deletes reservationTime when value is empty", () => {
  const fnIdx = apiSrc.indexOf("export async function updateItemMetadata(");
  const fnBlock = apiSrc.slice(fnIdx, fnIdx + 1200);
  assert.match(fnBlock, /delete merged\.reservationTime/, "must delete merged.reservationTime when empty");
});

test("updateItemMetadata deletes entryTime when value is empty", () => {
  const fnIdx = apiSrc.indexOf("export async function updateItemMetadata(");
  const fnBlock = apiSrc.slice(fnIdx, fnIdx + 1200);
  assert.match(fnBlock, /delete merged\.entryTime/, "must delete merged.entryTime when empty");
});

test("handleSaveMetadata passes empty string as undefined (falsy) so updateItemMetadata clears the key", () => {
  const idx = itemCard.indexOf("handleSaveMetadata");
  const fnBlock = itemCard.slice(idx, idx + 1000);
  // Empty inputs produce undefined via `|| undefined`, which updateItemMetadata treats as a clear signal
  assert.match(
    fnBlock,
    /\|\|\s*undefined/,
    "handleSaveMetadata must coerce empty string to undefined so empty fields clear the metadata key",
  );
});

// ── 13. Unrelated detail keys preserved ──────────────────────────────────────

test("updateItemMetadata spreads all currentDetails before applying patch", () => {
  const fnIdx = apiSrc.indexOf("export async function updateItemMetadata(");
  const fnBlock = apiSrc.slice(fnIdx, fnIdx + 800);
  // The spread must come before conditional deletes so all other keys survive
  const spreadIdx = fnBlock.indexOf("...currentDetails");
  const deleteIdx = fnBlock.indexOf("delete merged");
  assert.ok(spreadIdx >= 0, "must spread currentDetails");
  assert.ok(deleteIdx >= 0, "must have delete merged calls");
  assert.ok(spreadIdx < deleteIdx, "spread must come before delete operations");
});

// ── 14. timeLabel/dayPart not reused for reservation/entry facts ──────────────

test("ItineraryItemCard reservation display does not use dayPart or timeLabel", () => {
  const mealIdx = itemCard.indexOf('item.itemType === "meal" && (() => {');
  assert.ok(mealIdx >= 0, "meal JSX render block must exist");
  const mealBlock = itemCard.slice(mealIdx, mealIdx + 3000);
  // The formattedReservation path must NOT read dayPart or timeLabel
  const reservationIdx = mealBlock.indexOf("formattedReservation");
  assert.ok(reservationIdx >= 0, "formattedReservation must exist in meal block");
  // Check the reservation rendering context doesn't use dayPart
  const renderCtx = mealBlock.slice(reservationIdx, reservationIdx + 200);
  assert.doesNotMatch(renderCtx, /dayPart/, "reservation display must not reuse dayPart");
  assert.doesNotMatch(renderCtx, /timeLabel/, "reservation display must not reuse timeLabel");
});

test("ItineraryItemCard entry time display does not use dayPart or timeLabel", () => {
  const actIdx = itemCard.indexOf('item.itemType === "activity" && (() => {');
  assert.ok(actIdx >= 0, "activity JSX render block must exist");
  const actBlock = itemCard.slice(actIdx, actIdx + 4000);
  const entryIdx = actBlock.indexOf("formattedEntryTime");
  assert.ok(entryIdx >= 0, "formattedEntryTime must exist in activity block");
  const renderCtx = actBlock.slice(entryIdx, entryIdx + 200);
  assert.doesNotMatch(renderCtx, /dayPart/, "entry time display must not reuse dayPart");
  assert.doesNotMatch(renderCtx, /timeLabel/, "entry time display must not reuse timeLabel");
});

test("updateItemMetadata does not set dayPart or timeLabel", () => {
  const fnIdx = apiSrc.indexOf("export async function updateItemMetadata(");
  const fnBlock = apiSrc.slice(fnIdx, fnIdx + 800);
  assert.doesNotMatch(fnBlock, /dayPart/, "updateItemMetadata must not touch dayPart");
  assert.doesNotMatch(fnBlock, /timeLabel/, "updateItemMetadata must not touch timeLabel");
});

// ── 15. Brief remains read-only ───────────────────────────────────────────────

test("TripBrief has no updateItemMetadata call (read-only)", () => {
  assert.doesNotMatch(
    brief,
    /updateItemMetadata/,
    "TripBrief must not call updateItemMetadata — it remains read-only",
  );
});

test("TripBrief has no metaEditorOpen or meta editor state (read-only)", () => {
  assert.doesNotMatch(
    brief,
    /metaEditorOpen|handleOpenMetaEditor|handleSaveMetadata/,
    "TripBrief must remain read-only — no metadata editor state or handlers",
  );
});

// ── 16. AddToDayDrawer / Build / search files untouched ──────────────────────

test("AddToDayDrawer is untouched by this slice (no metadata editor added)", () => {
  assert.doesNotMatch(
    addToDayDrawer,
    /updateItemMetadata|metaEditorOpen|reservationTime|entryTime/,
    "AddToDayDrawer must not be changed by this slice",
  );
});

test("TripBuilder is untouched by the metadata editor (no metadata editor state in TripBuilder)", () => {
  assert.doesNotMatch(
    tripBuilder,
    /metaEditorOpen|handleSaveMetadata/,
    "TripBuilder must not contain metadata editor state — editor lives in ItineraryItemCard only",
  );
});

// ── 17. addHotelToTrip does not invent check-in/out dates ────────────────────

test("addHotelToTrip in api.ts does not write checkIn or check_in dates (no invented dates)", () => {
  const fnIdx = apiSrc.indexOf("export async function addHotelToTrip(");
  assert.ok(fnIdx >= 0, "addHotelToTrip must exist");
  const fnEnd = apiSrc.indexOf("\nexport ", fnIdx + 1);
  const fnBlock = apiSrc.slice(fnIdx, fnEnd > fnIdx ? fnEnd : fnIdx + 800);
  assert.doesNotMatch(
    fnBlock,
    /checkIn\s*:|check_in\s*:|checkOut\s*:|check_out\s*:/,
    "addHotelToTrip must not write check-in/out dates — ResearchResult carries no typed date field and dates cannot be invented",
  );
});

// ── Overflow menu entries exist for hotel / meal / activity ──────────────────

test("ItineraryItemCard desktop overflow has itinerary-item-edit-metadata entry", () => {
  assert.match(
    itemCard,
    /data-testid="itinerary-item-edit-metadata"/,
    "desktop overflow must have itinerary-item-edit-metadata entry",
  );
});

test("ItineraryItemCard mobile overflow has itinerary-item-mobile-edit-metadata entry", () => {
  assert.match(
    itemCard,
    /data-testid="itinerary-item-mobile-edit-metadata"/,
    "mobile overflow must have itinerary-item-mobile-edit-metadata entry",
  );
});

test("ItineraryItemCard edit metadata menu entry labels hotel as 'Edit stay dates'", () => {
  assert.match(
    itemCard,
    /Edit stay dates/,
    "metadata menu entry must label hotel action as 'Edit stay dates'",
  );
});

test("ItineraryItemCard edit metadata menu entry labels meal as 'Edit reservation'", () => {
  assert.match(
    itemCard,
    /Edit reservation/,
    "metadata menu entry must label meal action as 'Edit reservation'",
  );
});

test("ItineraryItemCard edit metadata menu entry labels activity as 'Edit entry time'", () => {
  assert.match(
    itemCard,
    /Edit entry time/,
    "metadata menu entry must label activity action as 'Edit entry time'",
  );
});

// ── handleOpenMetaEditor closes timeline editor ───────────────────────────────

test("handleOpenMetaEditor sets timelineOpen to false before opening meta editor", () => {
  const idx = itemCard.indexOf("handleOpenMetaEditor");
  assert.ok(idx >= 0, "handleOpenMetaEditor must exist");
  const fnBlock = itemCard.slice(idx, idx + 600);
  assert.match(
    fnBlock,
    /setTimelineOpen\(false\)/,
    "handleOpenMetaEditor must close the timeline editor",
  );
});

// ── handleOpenTimeline closes meta editor ─────────────────────────────────────

test("handleOpenTimeline sets metaEditorOpen to false before opening timeline", () => {
  const idx = itemCard.indexOf("const handleOpenTimeline");
  assert.ok(idx >= 0, "handleOpenTimeline must exist");
  const fnBlock = itemCard.slice(idx, idx + 300);
  assert.match(
    fnBlock,
    /setMetaEditorOpen\(false\)/,
    "handleOpenTimeline must close the metadata editor",
  );
});
