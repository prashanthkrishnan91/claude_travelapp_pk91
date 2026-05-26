/**
 * Hotel Stay Span v1 — unit + contract tests.
 *
 * Guards:
 *  1. hotelStaySpans helper derives intermediate "staying" markers
 *  2. hotelStaySpans helper derives checkout marker on checkout day
 *  3. Same-day check-in/out produces no markers
 *  4. Overlap boundary: checkout Hotel A + check-in Hotel B same day
 *  5. Invalid/missing dates fail closed (no markers, no suppression)
 *  6. Duplicate records prefer item physically on check-in day
 *  7. Derived markers are read-only — hotelStaySpans imports nothing from api
 *  8. ItineraryDayColumn accepts stayMarkers and suppressedHotelItemIds props (source contract)
 *  9. TripBuilder derives hotelStayDisplayMap from displayDays (source contract)
 * 10. TripBuilder passes stayMarkers and suppressedHotelItemIds to ItineraryDayColumn (source contract)
 * 11. Hotel metadata save patches dayId on move (api.ts updateItemMetadata accepts newDayId)
 * 12. No create/delete calls in hotelStaySpans
 * 13. readHotelCheckIn reads canonical camelCase key first
 * 14. readHotelCheckOut reads canonical camelCase key first
 * 15. Fallback keys accepted: check_in, check_in_date, checkInDate, check_out, check_out_date, checkOutDate
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

// Source files for contract checks
const spansSrc = readFileSync(
  new URL("../src/lib/hotelStaySpans.ts", import.meta.url),
  "utf8"
);
const apiSrc = readFileSync(
  new URL("../src/lib/api.ts", import.meta.url),
  "utf8"
);
const dayColSrc = readFileSync(
  new URL("../src/components/trips/ItineraryDayColumn.tsx", import.meta.url),
  "utf8"
);
const tripBuilderSrc = readFileSync(
  new URL("../src/components/trips/TripBuilder.tsx", import.meta.url),
  "utf8"
);

// ── Inline pure-logic extraction for unit testing ────────────────────────────
// We cannot import TypeScript directly in Node test runner, so we replicate
// the pure logic inline. These must stay in sync with hotelStaySpans.ts.

function parseHotelDate(raw) {
  if (typeof raw !== "string") return null;
  const s = raw.trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
  const [y, m, d] = s.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  if (isNaN(dt.getTime())) return null;
  return s;
}

function readHotelCheckIn(d) {
  return parseHotelDate(d.checkIn ?? d.check_in ?? d.check_in_date ?? d.checkInDate);
}

function readHotelCheckOut(d) {
  return parseHotelDate(d.checkOut ?? d.check_out ?? d.check_out_date ?? d.checkOutDate);
}

function hotelIdentityKey(d, title, location) {
  const placeId =
    (typeof d.placeId === "string" && d.placeId) ||
    (typeof d.place_id === "string" && d.place_id) ||
    (typeof d.googlePlaceId === "string" && d.googlePlaceId) ||
    (typeof d.google_place_id === "string" && d.google_place_id) ||
    (typeof d.googleMapsUri === "string" && d.googleMapsUri) ||
    (typeof d.google_maps_uri === "string" && d.google_maps_uri);
  if (placeId) return placeId;
  return `${title.toLowerCase().trim()}::${typeof location === "string" ? location.toLowerCase().trim() : ""}`;
}

function deriveHotelStayDisplay(displayDays) {
  const result = new Map();
  for (const day of displayDays) {
    result.set(day.id, { suppressedHotelItemIds: new Set(), stayMarkers: [] });
  }
  const spans = [];
  for (const day of displayDays) {
    for (const item of day.items) {
      if (item.itemType !== "hotel") continue;
      const d = item.details ?? {};
      const checkIn = readHotelCheckIn(d);
      const checkOut = readHotelCheckOut(d);
      if (!checkIn || !checkOut || checkIn >= checkOut) continue;
      spans.push({
        checkIn, checkOut,
        hotelTitle: item.title,
        itemId: item.id,
        physicalDayId: day.id,
        physicalDayDate: day.date ?? null,
        position: item.position,
        stayKey: `${hotelIdentityKey(d, item.title, item.location)}::${checkIn}::${checkOut}`,
      });
    }
  }
  const byStayKey = new Map();
  for (const span of spans) {
    const arr = byStayKey.get(span.stayKey) ?? [];
    arr.push(span);
    byStayKey.set(span.stayKey, arr);
  }
  for (const [, group] of byStayKey) {
    const onCheckInDay = group.filter((s) => s.physicalDayDate === s.checkIn);
    const canonical = onCheckInDay.length > 0
      ? onCheckInDay.reduce((a, b) => a.position <= b.position ? a : b)
      : group.reduce((a, b) => a.position <= b.position ? a : b);
    for (const span of group) {
      if (span.itemId !== canonical.itemId) {
        result.get(span.physicalDayId)?.suppressedHotelItemIds.add(span.itemId);
      }
    }
    for (const day of displayDays) {
      if (!day.date || day.id === canonical.physicalDayId) continue;
      const dayDate = day.date;
      if (dayDate > canonical.checkIn && dayDate < canonical.checkOut) {
        result.get(day.id)?.stayMarkers.push({ kind: "staying", hotelTitle: canonical.hotelTitle, itemId: canonical.itemId });
      } else if (dayDate === canonical.checkOut) {
        result.get(day.id)?.stayMarkers.push({ kind: "checkout", hotelTitle: canonical.hotelTitle, itemId: canonical.itemId });
      }
    }
  }
  return result;
}

// ── Helper to build a simple displayDays structure ──────────────────────────

function makeDay(id, date, items = []) {
  return { id, date, dayNumber: 1, title: `Day`, items };
}

function makeHotelItem(id, checkIn, checkOut, position = 0, title, location) {
  return {
    id,
    itemType: "hotel",
    title: title ?? `Hotel-${id}`,
    location: location ?? null,
    position,
    details: { checkIn, checkOut },
  };
}

function makeHotelItemWithPlaceId(id, checkIn, checkOut, placeId, position = 0) {
  return {
    id,
    itemType: "hotel",
    title: `Hotel-${id}`,
    location: null,
    position,
    details: { checkIn, checkOut, placeId },
  };
}

// ── 1. Intermediate staying markers ──────────────────────────────────────────

test("deriveHotelStayDisplay produces staying markers on intermediate days", () => {
  const days = [
    makeDay("d1", "2025-06-01", [makeHotelItem("h1", "2025-06-01", "2025-06-04")]),
    makeDay("d2", "2025-06-02"),
    makeDay("d3", "2025-06-03"),
    makeDay("d4", "2025-06-04"),
  ];
  const map = deriveHotelStayDisplay(days);
  assert.equal(map.get("d2")?.stayMarkers.length, 1, "Day 2 must have one staying marker");
  assert.equal(map.get("d2")?.stayMarkers[0].kind, "staying");
  assert.equal(map.get("d3")?.stayMarkers.length, 1, "Day 3 must have one staying marker");
  assert.equal(map.get("d3")?.stayMarkers[0].kind, "staying");
  assert.equal(map.get("d1")?.stayMarkers.length, 0, "Check-in day gets no marker (full card)");
});

// ── 2. Checkout marker ────────────────────────────────────────────────────────

test("deriveHotelStayDisplay produces checkout marker on checkout day", () => {
  const days = [
    makeDay("d1", "2025-06-01", [makeHotelItem("h1", "2025-06-01", "2025-06-04")]),
    makeDay("d2", "2025-06-02"),
    makeDay("d3", "2025-06-03"),
    makeDay("d4", "2025-06-04"),
  ];
  const map = deriveHotelStayDisplay(days);
  assert.equal(map.get("d4")?.stayMarkers.length, 1, "Checkout day must have one marker");
  assert.equal(map.get("d4")?.stayMarkers[0].kind, "checkout");
  assert.equal(map.get("d4")?.stayMarkers[0].hotelTitle, "Hotel-h1");
});

// ── 3. Same-day check-in/out: no markers ─────────────────────────────────────

test("same-day check-in and check-out produces no markers (full card only)", () => {
  const days = [
    makeDay("d1", "2025-06-01", [makeHotelItem("h1", "2025-06-01", "2025-06-01")]),
    makeDay("d2", "2025-06-02"),
  ];
  const map = deriveHotelStayDisplay(days);
  assert.equal(map.get("d1")?.stayMarkers.length, 0);
  assert.equal(map.get("d2")?.stayMarkers.length, 0);
  assert.equal(map.get("d1")?.suppressedHotelItemIds.size, 0);
});

// ── 4. Overlap boundary: Hotel A checkout + Hotel B check-in same day ─────────

test("checkout/checkin overlap on same day: checkout marker for A, staying for B (if applicable)", () => {
  const days = [
    makeDay("d1", "2025-06-01", [makeHotelItem("hA", "2025-06-01", "2025-06-03")]),
    makeDay("d2", "2025-06-02"),
    makeDay("d3", "2025-06-03", [makeHotelItem("hB", "2025-06-03", "2025-06-05")]),
    makeDay("d4", "2025-06-04"),
    makeDay("d5", "2025-06-05"),
  ];
  const map = deriveHotelStayDisplay(days);
  // Day 3: checkout for A, no marker for B (it's on checkIn day = physicalDayId)
  const d3markers = map.get("d3")?.stayMarkers ?? [];
  assert.ok(d3markers.some((m) => m.kind === "checkout" && m.itemId === "hA"), "Day 3 must have checkout for Hotel A");
  assert.equal(map.get("d4")?.stayMarkers.length, 1, "Day 4 has staying marker for B");
  assert.equal(map.get("d4")?.stayMarkers[0].kind, "staying");
  assert.equal(map.get("d5")?.stayMarkers.length, 1, "Day 5 has checkout marker for B");
  assert.equal(map.get("d5")?.stayMarkers[0].kind, "checkout");
});

// ── 5. Invalid/missing dates fail closed ─────────────────────────────────────

test("hotel with no checkIn/checkOut produces no markers or suppressions", () => {
  const days = [
    makeDay("d1", "2025-06-01", [{ id: "h1", itemType: "hotel", title: "Hotel-h1", position: 0, details: {} }]),
    makeDay("d2", "2025-06-02"),
  ];
  const map = deriveHotelStayDisplay(days);
  assert.equal(map.get("d1")?.stayMarkers.length, 0);
  assert.equal(map.get("d2")?.stayMarkers.length, 0);
  assert.equal(map.get("d1")?.suppressedHotelItemIds.size, 0);
});

test("hotel with invalid date string produces no markers", () => {
  const days = [
    makeDay("d1", "2025-06-01", [{ id: "h1", itemType: "hotel", title: "H", position: 0, details: { checkIn: "not-a-date", checkOut: "2025-06-05" } }]),
    makeDay("d2", "2025-06-02"),
  ];
  const map = deriveHotelStayDisplay(days);
  assert.equal(map.get("d2")?.stayMarkers.length, 0);
});

// ── 6. Duplicate records prefer check-in-day item ────────────────────────────

test("duplicate hotel records with same checkIn prefer item physically on checkIn day", () => {
  // Same hotel (same title + location) placed on two different days — simulate accidental duplicate
  // h1 is on Day 2 (not checkIn day), h2 is on Day 1 (the checkIn day)
  const days = [
    makeDay("d1", "2025-06-01", [makeHotelItem("h2", "2025-06-01", "2025-06-04", 0, "Hilton Tokyo", "Tokyo")]),
    makeDay("d2", "2025-06-02", [makeHotelItem("h1", "2025-06-01", "2025-06-04", 0, "Hilton Tokyo", "Tokyo")]),
    makeDay("d3", "2025-06-03"),
    makeDay("d4", "2025-06-04"),
  ];
  const map = deriveHotelStayDisplay(days);
  // h1 (on Day2, not checkIn day) is suppressed; h2 (on checkIn Day1) is canonical
  assert.ok(map.get("d2")?.suppressedHotelItemIds.has("h1"), "h1 on non-checkIn day must be suppressed");
  assert.ok(!map.get("d1")?.suppressedHotelItemIds.has("h2"), "h2 on checkIn day must not be suppressed");
});

// ── 7. hotelStaySpans imports nothing from api ────────────────────────────────

test("hotelStaySpans.ts has no import from @/lib/api (pure helper, no side effects)", () => {
  assert.doesNotMatch(spansSrc, /@\/lib\/api/, "hotelStaySpans must not import from api");
  assert.doesNotMatch(spansSrc, /updateItem|deleteItem|createItem/, "hotelStaySpans must not call any API function");
});

// ── 8. ItineraryDayColumn accepts new props (source contract) ─────────────────

test("ItineraryDayColumn props interface includes stayMarkers", () => {
  assert.match(dayColSrc, /stayMarkers/, "ItineraryDayColumn must accept stayMarkers prop");
});

test("ItineraryDayColumn props interface includes suppressedHotelItemIds", () => {
  assert.match(dayColSrc, /suppressedHotelItemIds/, "ItineraryDayColumn must accept suppressedHotelItemIds prop");
});

test("ItineraryDayColumn props interface includes onSaveHotelDates", () => {
  assert.match(dayColSrc, /onSaveHotelDates/, "ItineraryDayColumn must accept onSaveHotelDates prop");
});

test("ItineraryDayColumn renders stay-markers testid when stayMarkers present", () => {
  assert.match(dayColSrc, /data-testid="stay-markers"/, "ItineraryDayColumn must render stay-markers container");
});

test("ItineraryDayColumn renders dynamic stay-marker testid using marker.kind", () => {
  assert.match(dayColSrc, /stay-marker.*marker\.kind|marker\.kind.*stay-marker/, "ItineraryDayColumn must render dynamic stay-marker-{kind} testid");
});

test("ItineraryDayColumn renders checkout/staying labels in stay markers", () => {
  assert.match(dayColSrc, /Check out.*hotelTitle|hotelTitle.*Check out/, "ItineraryDayColumn must render 'Check out · {hotelTitle}'");
  assert.match(dayColSrc, /Staying at.*hotelTitle|hotelTitle.*Staying at/, "ItineraryDayColumn must render 'Staying at {hotelTitle}'");
});

test("ItineraryDayColumn uses Hotel icon from lucide-react for stay markers", () => {
  assert.match(dayColSrc, /Hotel/, "ItineraryDayColumn must import and use Hotel icon for stay markers");
});

test("ItineraryDayColumn filters suppressedHotelItemIds from visibleItems", () => {
  assert.match(dayColSrc, /suppressedHotelItemIds/, "ItineraryDayColumn must filter suppressed hotel item ids from visibleItems");
});

// ── 9. TripBuilder derives hotelStayDisplayMap ────────────────────────────────

test("TripBuilder imports deriveHotelStayDisplay from hotelStaySpans", () => {
  assert.match(
    tripBuilderSrc,
    /import.*deriveHotelStayDisplay.*from.*hotelStaySpans/,
    "TripBuilder must import deriveHotelStayDisplay"
  );
});

test("TripBuilder computes hotelStayDisplayMap with useMemo", () => {
  assert.match(tripBuilderSrc, /hotelStayDisplayMap/, "TripBuilder must compute hotelStayDisplayMap");
  assert.match(tripBuilderSrc, /deriveHotelStayDisplay\(displayDays\)/, "TripBuilder must pass displayDays to deriveHotelStayDisplay");
});

// ── 10. TripBuilder passes new props to ItineraryDayColumn ───────────────────

test("TripBuilder passes stayMarkers to ItineraryDayColumn", () => {
  assert.match(tripBuilderSrc, /stayMarkers=/, "TripBuilder must pass stayMarkers prop to ItineraryDayColumn");
});

test("TripBuilder passes suppressedHotelItemIds to ItineraryDayColumn", () => {
  assert.match(tripBuilderSrc, /suppressedHotelItemIds=/, "TripBuilder must pass suppressedHotelItemIds prop to ItineraryDayColumn");
});

test("TripBuilder passes onSaveHotelDates to ItineraryDayColumn", () => {
  assert.match(tripBuilderSrc, /onSaveHotelDates=\{handleSaveHotelDates\}/, "TripBuilder must pass onSaveHotelDates to ItineraryDayColumn");
});

// ── 11. api.ts updateItemMetadata accepts optional newDayId ──────────────────

test("updateItemMetadata signature accepts optional newDayId parameter", () => {
  const fnIdx = apiSrc.indexOf("export async function updateItemMetadata(");
  assert.ok(fnIdx >= 0, "updateItemMetadata must exist");
  const fnSig = apiSrc.slice(fnIdx, fnIdx + 300);
  assert.match(fnSig, /newDayId\?/, "updateItemMetadata must accept optional newDayId parameter");
});

test("updateItemMetadata passes dayId to updateItem when newDayId is provided", () => {
  const fnIdx = apiSrc.indexOf("export async function updateItemMetadata(");
  const fnBlock = apiSrc.slice(fnIdx, fnIdx + 1500);
  assert.match(fnBlock, /dayId.*newDayId|newDayId.*dayId/, "updateItemMetadata must use newDayId as dayId when provided");
});

// ── 12. No create/delete in hotelStaySpans ───────────────────────────────────

test("hotelStaySpans.ts does not call createItem or deleteItem", () => {
  assert.doesNotMatch(spansSrc, /createItem|deleteItem/, "hotelStaySpans must not create or delete items");
});

// ── 13. readHotelCheckIn canonical key priority ───────────────────────────────

test("readHotelCheckIn reads d.checkIn as first priority", () => {
  const result = readHotelCheckIn({ checkIn: "2025-06-01", check_in: "2025-06-02" });
  assert.equal(result, "2025-06-01", "checkIn must take priority over check_in");
});

test("readHotelCheckIn falls back to check_in", () => {
  const result = readHotelCheckIn({ check_in: "2025-06-01" });
  assert.equal(result, "2025-06-01");
});

test("readHotelCheckIn falls back to check_in_date", () => {
  const result = readHotelCheckIn({ check_in_date: "2025-06-01" });
  assert.equal(result, "2025-06-01");
});

test("readHotelCheckIn falls back to checkInDate", () => {
  const result = readHotelCheckIn({ checkInDate: "2025-06-01" });
  assert.equal(result, "2025-06-01");
});

// ── 14. readHotelCheckOut canonical key priority ──────────────────────────────

test("readHotelCheckOut reads d.checkOut as first priority", () => {
  const result = readHotelCheckOut({ checkOut: "2025-06-05", check_out: "2025-06-06" });
  assert.equal(result, "2025-06-05");
});

test("readHotelCheckOut falls back to check_out", () => {
  const result = readHotelCheckOut({ check_out: "2025-06-05" });
  assert.equal(result, "2025-06-05");
});

test("readHotelCheckOut falls back to check_out_date", () => {
  const result = readHotelCheckOut({ check_out_date: "2025-06-05" });
  assert.equal(result, "2025-06-05");
});

test("readHotelCheckOut falls back to checkOutDate", () => {
  const result = readHotelCheckOut({ checkOutDate: "2025-06-05" });
  assert.equal(result, "2025-06-05");
});

// ── 15. UTC-safe date parsing ─────────────────────────────────────────────────

test("parseHotelDate rejects non-YYYY-MM-DD strings", () => {
  assert.equal(readHotelCheckIn({ checkIn: "June 1 2025" }), null);
  assert.equal(readHotelCheckIn({ checkIn: "2025/06/01" }), null);
  assert.equal(readHotelCheckIn({ checkIn: "" }), null);
  assert.equal(readHotelCheckIn({ checkIn: null }), null);
});

test("parseHotelDate accepts valid YYYY-MM-DD string", () => {
  assert.equal(readHotelCheckIn({ checkIn: "2025-06-01" }), "2025-06-01");
});

// ── hotelStaySpans.ts source contracts ───────────────────────────────────────

test("hotelStaySpans.ts exports readHotelCheckIn", () => {
  assert.match(spansSrc, /export function readHotelCheckIn/, "hotelStaySpans must export readHotelCheckIn");
});

test("hotelStaySpans.ts exports readHotelCheckOut", () => {
  assert.match(spansSrc, /export function readHotelCheckOut/, "hotelStaySpans must export readHotelCheckOut");
});

test("hotelStaySpans.ts exports deriveHotelStayDisplay", () => {
  assert.match(spansSrc, /export function deriveHotelStayDisplay/, "hotelStaySpans must export deriveHotelStayDisplay");
});

test("hotelStaySpans.ts exports StayMarker type", () => {
  assert.match(spansSrc, /export.*StayMarker/, "hotelStaySpans must export StayMarker type");
});

test("hotelStaySpans.ts exports DayHotelDisplay type", () => {
  assert.match(spansSrc, /export.*DayHotelDisplay/, "hotelStaySpans must export DayHotelDisplay type");
});

test("hotelStaySpans.ts uses UTC-safe date parsing (Date.UTC)", () => {
  assert.match(spansSrc, /Date\.UTC/, "hotelStaySpans must use Date.UTC for UTC-safe date parsing");
});

test("hotelStaySpans.ts groups by stayKey not checkIn (regression guard)", () => {
  assert.match(spansSrc, /byStayKey/, "hotelStaySpans must group by stayKey to avoid cross-hotel suppression");
  assert.doesNotMatch(spansSrc, /byCheckIn/, "hotelStaySpans must not group by checkIn alone");
});

test("TripBuilder handleSaveHotelDates resolves newDayId from displayDays", () => {
  assert.match(
    tripBuilderSrc,
    /handleSaveHotelDates[\s\S]{0,2000}displayDays\.find/,
    "handleSaveHotelDates must resolve newDayId by searching displayDays"
  );
});

test("TripBuilder handleSaveHotelDates calls updateItemMetadata", () => {
  assert.match(
    tripBuilderSrc,
    /handleSaveHotelDates[\s\S]{0,2000}updateItemMetadata/,
    "handleSaveHotelDates must call updateItemMetadata"
  );
});

test("TripBuilder imports updateItemMetadata from api", () => {
  assert.match(
    tripBuilderSrc,
    /updateItemMetadata/,
    "TripBuilder must import and use updateItemMetadata"
  );
});

// ── 16. Different hotels with same checkIn/checkOut are NOT suppressed ────────

test("two different hotels (by title) with same checkIn/checkOut are both visible", () => {
  // Both hotels check in and check out on the same dates but have different titles
  const days = [
    makeDay("d1", "2025-07-01", [
      makeHotelItem("hA", "2025-07-01", "2025-07-04", 0, "Grand Hyatt", "Tokyo"),
      makeHotelItem("hB", "2025-07-01", "2025-07-04", 1, "Mandarin Oriental", "Tokyo"),
    ]),
    makeDay("d2", "2025-07-02"),
    makeDay("d3", "2025-07-03"),
    makeDay("d4", "2025-07-04"),
  ];
  const map = deriveHotelStayDisplay(days);
  // Neither hotel should be suppressed — they have different titles so different stayKeys
  assert.ok(!map.get("d1")?.suppressedHotelItemIds.has("hA"), "Hotel A must not be suppressed");
  assert.ok(!map.get("d1")?.suppressedHotelItemIds.has("hB"), "Hotel B must not be suppressed");
});

test("two different hotels with same checkIn/checkOut but different placeIds are both visible", () => {
  const days = [
    makeDay("d1", "2025-07-01", [
      makeHotelItemWithPlaceId("hA", "2025-07-01", "2025-07-04", "place-001"),
      makeHotelItemWithPlaceId("hB", "2025-07-01", "2025-07-04", "place-002"),
    ]),
    makeDay("d2", "2025-07-02"),
  ];
  const map = deriveHotelStayDisplay(days);
  assert.ok(!map.get("d1")?.suppressedHotelItemIds.has("hA"), "Hotel A (place-001) must not be suppressed");
  assert.ok(!map.get("d1")?.suppressedHotelItemIds.has("hB"), "Hotel B (place-002) must not be suppressed");
});

test("true duplicate — same hotel (same title+location, same dates) on two days: non-checkIn copy suppressed", () => {
  // Same logical hotel placed on two different days (data error / copy-paste)
  const days = [
    makeDay("d1", "2025-07-01", [makeHotelItem("hA", "2025-07-01", "2025-07-04", 0, "Grand Hyatt", "Tokyo")]),
    makeDay("d2", "2025-07-02", [makeHotelItem("hB", "2025-07-01", "2025-07-04", 0, "Grand Hyatt", "Tokyo")]),
    makeDay("d3", "2025-07-03"),
    makeDay("d4", "2025-07-04"),
  ];
  const map = deriveHotelStayDisplay(days);
  // hB is on Day 2 (not the checkIn day), same hotel → must be suppressed
  assert.ok(map.get("d2")?.suppressedHotelItemIds.has("hB"), "True duplicate on non-checkIn day must be suppressed");
  assert.ok(!map.get("d1")?.suppressedHotelItemIds.has("hA"), "Canonical (on checkIn day) must not be suppressed");
});

test("true duplicate — same placeId, same dates on two days: non-checkIn copy suppressed", () => {
  const days = [
    makeDay("d1", "2025-07-01", [makeHotelItemWithPlaceId("hA", "2025-07-01", "2025-07-04", "place-abc")]),
    makeDay("d2", "2025-07-02", [makeHotelItemWithPlaceId("hB", "2025-07-01", "2025-07-04", "place-abc")]),
    makeDay("d3", "2025-07-03"),
  ];
  const map = deriveHotelStayDisplay(days);
  assert.ok(map.get("d2")?.suppressedHotelItemIds.has("hB"), "Same placeId duplicate must be suppressed");
  assert.ok(!map.get("d1")?.suppressedHotelItemIds.has("hA"), "Canonical must not be suppressed");
});

// ── 17. TripBuilder Build-add date seeding contracts ─────────────────────────

test("TripBuilder imports readHotelCheckOut from hotelStaySpans for Build-add checkout fallback", () => {
  assert.match(
    tripBuilderSrc,
    /import.*readHotelCheckOut.*from.*hotelStaySpans/,
    "TripBuilder must import readHotelCheckOut for Build-add checkout fallback"
  );
});

test("TripBuilder Build-add seeds hotel checkIn from targetDay.date (not candidate placeholder)", () => {
  assert.match(
    tripBuilderSrc,
    /targetDay\.date/,
    "handleAddCandidateToItinerary must seed checkIn from targetDay.date"
  );
});

test("TripBuilder Build-add uses displayDays.findIndex for next-day checkout default", () => {
  assert.match(
    tripBuilderSrc,
    /displayDays\.findIndex/,
    "handleAddCandidateToItinerary must use displayDays.findIndex to find next day for checkout"
  );
});

test("TripBuilder Build-add builds seededDetails stripping all old date keys", () => {
  assert.match(
    tripBuilderSrc,
    /seededDetails/,
    "handleAddCandidateToItinerary must build seededDetails stripping old date keys"
  );
});

test("TripBuilder handleAddCandidateToItinerary uses resolvedDay for hotel state update", () => {
  assert.match(
    tripBuilderSrc,
    /resolvedDay/,
    "handleAddCandidateToItinerary must use resolvedDay to anchor hotel to correct day"
  );
});

// ── 18. Build hotel date seeding (inline pure logic) ─────────────────────────

function seedHotelDetailsForAdd(rawDetails, targetDayDate, nextDayDate) {
  const checkIn = targetDayDate;
  let checkOut;
  if (nextDayDate) {
    checkOut = nextDayDate;
  } else {
    const existingCheckOut = readHotelCheckOut(rawDetails);
    if (existingCheckOut && checkIn && existingCheckOut > checkIn) {
      checkOut = existingCheckOut;
    }
  }
  const seededDetails = Object.fromEntries(
    Object.entries(rawDetails).filter(
      ([k]) => !["checkIn","checkOut","check_in","check_in_date","checkInDate",
                 "check_out","check_out_date","checkOutDate"].includes(k)
    )
  );
  if (checkIn) seededDetails.checkIn = checkIn;
  if (checkOut) seededDetails.checkOut = checkOut;
  return seededDetails;
}

test("Build-add seeds checkIn to target day date, ignoring candidate placeholder", () => {
  // Candidate has full-trip placeholder dates (Day 1 to last day)
  const raw = { checkIn: "2025-07-01", checkOut: "2025-07-15", rating: 4.5, stars: 5 };
  const result = seedHotelDetailsForAdd(raw, "2025-07-03", "2025-07-04");
  assert.equal(result.checkIn, "2025-07-03", "checkIn must be the target day's date, not candidate's");
  assert.equal(result.checkOut, "2025-07-04", "checkOut must be the next trip day");
});

test("Build-add preserves unrelated hotel details (rating, stars, amenities, coordinates)", () => {
  const raw = { checkIn: "2025-07-01", checkOut: "2025-07-15", rating: 4.5, stars: 5, amenities: ["pool"], lat: 35.6 };
  const result = seedHotelDetailsForAdd(raw, "2025-07-03", "2025-07-04");
  assert.equal(result.rating, 4.5);
  assert.equal(result.stars, 5);
  assert.deepEqual(result.amenities, ["pool"]);
  assert.equal(result.lat, 35.6);
});

test("Build-add strips all conflicting snake/fallback date keys", () => {
  const raw = { check_in: "2025-07-01", check_in_date: "2025-07-01", checkInDate: "2025-07-01",
                check_out: "2025-07-15", check_out_date: "2025-07-15", checkOutDate: "2025-07-15", rating: 4.0 };
  const result = seedHotelDetailsForAdd(raw, "2025-07-03", "2025-07-04");
  assert.equal(result.check_in, undefined);
  assert.equal(result.check_in_date, undefined);
  assert.equal(result.checkInDate, undefined);
  assert.equal(result.check_out, undefined);
  assert.equal(result.check_out_date, undefined);
  assert.equal(result.checkOutDate, undefined);
  assert.equal(result.checkIn, "2025-07-03");
  assert.equal(result.checkOut, "2025-07-04");
});

test("Build-add checkout defaults to next trip day when available", () => {
  const raw = { rating: 4.0 };
  const result = seedHotelDetailsForAdd(raw, "2025-07-10", "2025-07-11");
  assert.equal(result.checkOut, "2025-07-11");
});

test("Build-add checkout falls back to valid existing checkOut when no next day", () => {
  const raw = { checkOut: "2025-07-20", rating: 4.0 };
  const result = seedHotelDetailsForAdd(raw, "2025-07-10", null);
  assert.equal(result.checkOut, "2025-07-20", "valid existing checkOut preserved when after new checkIn");
});

test("Build-add omits checkOut when no next day and existing checkOut predates new checkIn", () => {
  // Stale checkout (trip-start placeholder) is before the chosen checkIn
  const raw = { checkOut: "2025-07-05" };
  const result = seedHotelDetailsForAdd(raw, "2025-07-10", null);
  assert.equal(result.checkOut, undefined, "stale checkOut before new checkIn must be omitted");
});

test("Build-add omits checkIn when targetDay has no date (undated trip, fail-closed)", () => {
  const raw = { checkIn: "2025-07-01", rating: 4.0 };
  const result = seedHotelDetailsForAdd(raw, undefined, "2025-07-02");
  assert.equal(result.checkIn, undefined, "checkIn not seeded when targetDay has no date");
});
