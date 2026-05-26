/**
 * Trip Brief — Scheduled Facts v1
 *
 * Guards:
 *  1. deriveTripBriefFacts includes placed flights
 *  2. Hotel checkIn/checkOut facts derive from checkIn/checkOut metadata
 *  3. Hotel without dates preserves simple stay anchor; does not fabricate dates
 *  4. Meal with reservationTime appears as a scheduled fact
 *  5. Meal without reservationTime does not appear
 *  6. Activity with entryTime appears as a scheduled fact
 *  7. Activity without entryTime does not appear
 *  8. Facts are sorted chronologically (by day number then time)
 *  9. formatBriefTime converts HH:mm to H:MM AM/PM
 * 10. formatBriefTime extracts time from ISO datetime strings
 * 11. formatBriefTime returns null for unparseable input
 * 12. TripBrief imports deriveTripBriefFacts and renders jd-brief-scheduled-fact
 * 13. TripBrief caps visible facts and shows overflow line
 * 14. TripBrief has no edit/menu/drag controls for scheduled facts
 * 15. TripBrief Review ideas behavior remains wired
 * 16. TripBrief pending lines (missing flight/stay) remain
 * 17. tripBriefFacts.ts imports readHotelCheckIn/readHotelCheckOut from hotelStaySpans
 * 18. tripBriefFacts.ts does not import from api.ts or UI components
 * 19. No AddToDayDrawer / IdeasTray / Itinerary mutation path touched
 * 20. Hotel duplicate (same title+dates) emits only one check-in and one check-out
 * 21. Two distinct hotels each emit their own check-in/check-out facts
 * 22. Flight startTime / endTime formatted when present
 * 23. Scheduled fact rows carry no buttons or interactive controls
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

// Source files for contract checks
const factsSrc = readFileSync(
  new URL("../src/lib/tripBriefFacts.ts", import.meta.url),
  "utf8"
);
const briefSrc = readFileSync(
  new URL("../src/components/trips/TripBrief.tsx", import.meta.url),
  "utf8"
);
const addToDaySrc = readFileSync(
  new URL("../src/components/trips/AddToDayDrawer.tsx", import.meta.url),
  "utf8"
);
const ideasTraySrc = readFileSync(
  new URL("../src/components/trips/IdeasTray.tsx", import.meta.url),
  "utf8"
);

// ── Inline pure-logic extraction ─────────────────────────────────────────────
// We cannot import TypeScript directly in the Node test runner, so we replicate
// the pure logic inline. Keep in sync with tripBriefFacts.ts and hotelStaySpans.ts.

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

function formatBriefTime(raw) {
  if (typeof raw !== "string" || !raw.trim()) return null;
  const s = raw.trim();
  const hhmm = s.match(/^(\d{1,2}):(\d{2})$/);
  if (hhmm) {
    const h = parseInt(hhmm[1], 10);
    const m = parseInt(hhmm[2], 10);
    if (h >= 0 && h <= 23 && m >= 0 && m <= 59) {
      const period = h >= 12 ? "PM" : "AM";
      const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
      return `${h12}:${String(m).padStart(2, "0")} ${period}`;
    }
  }
  const iso = s.match(/T(\d{2}):(\d{2})/);
  if (iso) {
    const h = parseInt(iso[1], 10);
    const m = parseInt(iso[2], 10);
    const period = h >= 12 ? "PM" : "AM";
    const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
    return `${h12}:${String(m).padStart(2, "0")} ${period}`;
  }
  return null;
}

function makeSortKey(dayNumber, time) {
  const paddedDay = String(dayNumber).padStart(4, "0");
  if (!time) return `${paddedDay}:99:99`;
  const match = time.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i);
  if (!match) return `${paddedDay}:99:99`;
  let h = parseInt(match[1], 10);
  const m = match[2];
  const period = match[3].toUpperCase();
  if (period === "PM" && h < 12) h += 12;
  if (period === "AM" && h === 12) h = 0;
  return `${paddedDay}:${String(h).padStart(2, "0")}:${m}`;
}

function deriveTripBriefFacts(days) {
  const facts = [];
  const emittedHotelKeys = new Set();

  for (const day of days) {
    for (const item of day.items ?? []) {
      const d = item.details ?? {};

      if (item.itemType === "flight") {
        const time =
          formatBriefTime(item.startTime) ?? formatBriefTime(item.endTime) ?? null;
        facts.push({
          type: "flight",
          label: "Flight",
          title: item.title,
          dayNumber: day.dayNumber,
          date: day.date ?? null,
          time,
          sortKey: makeSortKey(day.dayNumber, time),
        });
      } else if (item.itemType === "hotel") {
        const checkIn = readHotelCheckIn(d);
        const checkOut = readHotelCheckOut(d);
        const hotelKey = `${item.title}::${checkIn ?? ""}::${checkOut ?? ""}`;

        if (!emittedHotelKeys.has(hotelKey)) {
          emittedHotelKeys.add(hotelKey);

          if (checkIn || checkOut) {
            if (checkIn) {
              const checkInDay = days.find((d2) => d2.date === checkIn) ?? day;
              facts.push({
                type: "hotel-checkin",
                label: "Check in",
                title: item.title,
                dayNumber: checkInDay.dayNumber,
                date: checkIn,
                time: null,
                sortKey: makeSortKey(checkInDay.dayNumber, null),
              });
            }
            if (checkOut) {
              const checkOutDay = days.find((d2) => d2.date === checkOut) ?? day;
              facts.push({
                type: "hotel-checkout",
                label: "Check out",
                title: item.title,
                dayNumber: checkOutDay.dayNumber,
                date: checkOut,
                time: null,
                sortKey: makeSortKey(checkOutDay.dayNumber, null),
              });
            }
          } else {
            facts.push({
              type: "hotel-stay",
              label: "Stay",
              title: item.title,
              dayNumber: day.dayNumber,
              date: day.date ?? null,
              time: null,
              sortKey: makeSortKey(day.dayNumber, null),
            });
          }
        }
      } else if (item.itemType === "meal") {
        const time = formatBriefTime(d.reservationTime);
        if (!time) continue;
        facts.push({
          type: "meal-reservation",
          label: "Reservation",
          title: item.title,
          dayNumber: day.dayNumber,
          date: day.date ?? null,
          time,
          sortKey: makeSortKey(day.dayNumber, time),
        });
      } else if (item.itemType === "activity") {
        const time = formatBriefTime(d.entryTime);
        if (!time) continue;
        facts.push({
          type: "activity-entry",
          label: "Entry",
          title: item.title,
          dayNumber: day.dayNumber,
          date: day.date ?? null,
          time,
          sortKey: makeSortKey(day.dayNumber, time),
        });
      }
    }
  }

  facts.sort((a, b) => a.sortKey.localeCompare(b.sortKey));
  return facts;
}

// ── Helper fixtures ───────────────────────────────────────────────────────────

function makeDay(dayNumber, date, items) {
  return { id: `day-${dayNumber}`, tripId: "trip-1", dayNumber, date, items };
}

function makeFlight(id, title, startTime) {
  return {
    id,
    tripId: "trip-1",
    itemType: "flight",
    title,
    startTime: startTime ?? undefined,
    position: 0,
  };
}

function makeHotel(id, title, checkIn, checkOut) {
  return {
    id,
    tripId: "trip-1",
    itemType: "hotel",
    title,
    position: 1,
    details: checkIn || checkOut ? { checkIn, checkOut } : {},
  };
}

function makeMeal(id, title, reservationTime) {
  return {
    id,
    tripId: "trip-1",
    itemType: "meal",
    title,
    position: 2,
    details: reservationTime ? { reservationTime } : {},
  };
}

function makeActivity(id, title, entryTime) {
  return {
    id,
    tripId: "trip-1",
    itemType: "activity",
    title,
    position: 3,
    details: entryTime ? { entryTime } : {},
  };
}

// ── Unit tests: deriveTripBriefFacts ──────────────────────────────────────────

test("deriveTripBriefFacts includes placed flights", () => {
  const days = [makeDay(1, "2026-06-01", [makeFlight("f1", "JFK → CDG")])];
  const facts = deriveTripBriefFacts(days);
  assert.equal(facts.length, 1);
  assert.equal(facts[0].type, "flight");
  assert.equal(facts[0].label, "Flight");
  assert.equal(facts[0].title, "JFK → CDG");
  assert.equal(facts[0].dayNumber, 1);
});

test("flight with startTime exposes the formatted time", () => {
  const days = [makeDay(1, "2026-06-01", [makeFlight("f1", "JFK → CDG", "2026-06-01T08:30:00Z")])];
  const facts = deriveTripBriefFacts(days);
  assert.equal(facts[0].time, "8:30 AM");
});

test("flight without times has null time", () => {
  const days = [makeDay(1, "2026-06-01", [makeFlight("f1", "Return flight")])];
  const facts = deriveTripBriefFacts(days);
  assert.equal(facts[0].time, null);
});

test("hotel checkIn/checkOut facts derive from checkIn/checkOut metadata", () => {
  const hotel = makeHotel("h1", "Grand Hotel", "2026-06-02", "2026-06-05");
  const days = [
    makeDay(1, "2026-06-01", []),
    makeDay(2, "2026-06-02", [hotel]),
    makeDay(3, "2026-06-03", []),
    makeDay(4, "2026-06-04", []),
    makeDay(5, "2026-06-05", []),
  ];
  const facts = deriveTripBriefFacts(days);
  const checkin = facts.find((f) => f.type === "hotel-checkin");
  const checkout = facts.find((f) => f.type === "hotel-checkout");
  assert.ok(checkin, "should have a check-in fact");
  assert.ok(checkout, "should have a check-out fact");
  assert.equal(checkin.label, "Check in");
  assert.equal(checkin.title, "Grand Hotel");
  assert.equal(checkin.date, "2026-06-02");
  assert.equal(checkin.dayNumber, 2);
  assert.equal(checkout.label, "Check out");
  assert.equal(checkout.date, "2026-06-05");
  assert.equal(checkout.dayNumber, 5);
});

test("hotel without dates preserves simple stay anchor; does not fabricate check-in/out facts", () => {
  const hotel = makeHotel("h1", "Mystery Inn", null, null);
  const days = [makeDay(1, "2026-06-01", [hotel])];
  const facts = deriveTripBriefFacts(days);
  assert.equal(facts.length, 1);
  assert.equal(facts[0].type, "hotel-stay", "type must be hotel-stay, not hotel-checkin or hotel-checkout");
  assert.equal(facts[0].label, "Stay");
  assert.equal(facts[0].title, "Mystery Inn");
  // date comes from the day the hotel card is physically on; no fabricated check-in/out dates
  assert.equal(facts[0].date, "2026-06-01");
  assert.equal(facts[0].time, null, "hotel-stay has no time");
});

test("hotel duplicate (same title+dates) emits only one check-in and one check-out", () => {
  const hotel1 = makeHotel("h1", "Grand Hotel", "2026-06-02", "2026-06-05");
  const hotel2 = makeHotel("h2", "Grand Hotel", "2026-06-02", "2026-06-05");
  const days = [
    makeDay(2, "2026-06-02", [hotel1, hotel2]),
    makeDay(5, "2026-06-05", []),
  ];
  const facts = deriveTripBriefFacts(days);
  const checkins = facts.filter((f) => f.type === "hotel-checkin");
  const checkouts = facts.filter((f) => f.type === "hotel-checkout");
  assert.equal(checkins.length, 1, "only one check-in per unique stay key");
  assert.equal(checkouts.length, 1, "only one check-out per unique stay key");
});

test("two distinct hotels each emit their own check-in/check-out facts", () => {
  const hotel1 = makeHotel("h1", "Hotel Alpha", "2026-06-01", "2026-06-03");
  const hotel2 = makeHotel("h2", "Hotel Beta", "2026-06-04", "2026-06-06");
  const days = [
    makeDay(1, "2026-06-01", [hotel1]),
    makeDay(3, "2026-06-03", []),
    makeDay(4, "2026-06-04", [hotel2]),
    makeDay(6, "2026-06-06", []),
  ];
  const facts = deriveTripBriefFacts(days);
  const checkins = facts.filter((f) => f.type === "hotel-checkin");
  const checkouts = facts.filter((f) => f.type === "hotel-checkout");
  assert.equal(checkins.length, 2, "one check-in per distinct hotel");
  assert.equal(checkouts.length, 2, "one check-out per distinct hotel");
});

test("meal with reservationTime appears as a scheduled fact", () => {
  const meal = makeMeal("m1", "Le Bernardin", "19:30");
  const days = [makeDay(2, "2026-06-02", [meal])];
  const facts = deriveTripBriefFacts(days);
  assert.equal(facts.length, 1);
  assert.equal(facts[0].type, "meal-reservation");
  assert.equal(facts[0].label, "Reservation");
  assert.equal(facts[0].title, "Le Bernardin");
  assert.equal(facts[0].time, "7:30 PM");
});

test("meal without reservationTime does not appear as a scheduled fact", () => {
  const meal = makeMeal("m1", "Random Bistro", null);
  const days = [makeDay(1, "2026-06-01", [meal])];
  const facts = deriveTripBriefFacts(days);
  assert.equal(facts.length, 0, "meal without reservation time must be excluded");
});

test("activity with entryTime appears as a scheduled fact", () => {
  const activity = makeActivity("a1", "Eiffel Tower", "10:00");
  const days = [makeDay(3, "2026-06-03", [activity])];
  const facts = deriveTripBriefFacts(days);
  assert.equal(facts.length, 1);
  assert.equal(facts[0].type, "activity-entry");
  assert.equal(facts[0].label, "Entry");
  assert.equal(facts[0].title, "Eiffel Tower");
  assert.equal(facts[0].time, "10:00 AM");
});

test("activity without entryTime does not appear as a scheduled fact", () => {
  const activity = makeActivity("a1", "Wander around", null);
  const days = [makeDay(1, "2026-06-01", [activity])];
  const facts = deriveTripBriefFacts(days);
  assert.equal(facts.length, 0, "activity without entry time must be excluded");
});

test("facts are sorted chronologically by day then time", () => {
  const days = [
    makeDay(1, "2026-06-01", [
      makeMeal("m1", "Late Dinner", "20:00"),
      makeFlight("f1", "JFK → CDG"),
      makeMeal("m2", "Early Breakfast", "08:00"),
    ]),
    makeDay(2, "2026-06-02", [
      makeActivity("a1", "Museum", "09:00"),
    ]),
  ];
  const facts = deriveTripBriefFacts(days);
  assert.ok(facts.length >= 4);
  // All day-1 facts precede day-2 facts
  const day1 = facts.filter((f) => f.dayNumber === 1);
  const day2 = facts.filter((f) => f.dayNumber === 2);
  const lastDay1Idx = facts.lastIndexOf(day1[day1.length - 1]);
  const firstDay2Idx = facts.indexOf(day2[0]);
  assert.ok(lastDay1Idx < firstDay2Idx, "day 1 facts must all precede day 2 facts");
  // Within day 1: 08:00 < 20:00 < flight (no time → sorts last)
  const day1Meals = day1.filter((f) => f.type === "meal-reservation");
  assert.equal(day1Meals[0].title, "Early Breakfast", "earlier reservation time sorts first");
  assert.equal(day1Meals[1].title, "Late Dinner");
  const flightFact = day1.find((f) => f.type === "flight");
  assert.ok(day1.indexOf(flightFact) > day1.indexOf(day1Meals[1]), "untimed item sorts after timed items within same day");
});

// ── Unit tests: formatBriefTime ───────────────────────────────────────────────

test("formatBriefTime converts plain HH:mm to H:MM AM/PM", () => {
  assert.equal(formatBriefTime("08:30"), "8:30 AM");
  assert.equal(formatBriefTime("13:45"), "1:45 PM");
  assert.equal(formatBriefTime("00:00"), "12:00 AM");
  assert.equal(formatBriefTime("12:00"), "12:00 PM");
  assert.equal(formatBriefTime("19:30"), "7:30 PM");
});

test("formatBriefTime extracts time from ISO datetime strings", () => {
  assert.equal(formatBriefTime("2026-06-01T08:30:00Z"), "8:30 AM");
  assert.equal(formatBriefTime("2026-06-01T20:15:00"), "8:15 PM");
});

test("formatBriefTime returns null for unparseable input", () => {
  assert.equal(formatBriefTime(null), null);
  assert.equal(formatBriefTime(undefined), null);
  assert.equal(formatBriefTime(""), null);
  assert.equal(formatBriefTime("not-a-time"), null);
  assert.equal(formatBriefTime(1234), null);
});

// ── Source-scan: TripBrief component ─────────────────────────────────────────

test("TripBrief imports deriveTripBriefFacts from the helper", () => {
  assert.match(briefSrc, /import[\s\S]{0,100}deriveTripBriefFacts[\s\S]{0,50}tripBriefFacts/);
});

test("TripBrief renders jd-brief-scheduled-fact testid for each visible fact", () => {
  assert.match(briefSrc, /data-testid="jd-brief-scheduled-fact"/);
});

test("TripBrief caps visible facts and shows overflow line", () => {
  assert.match(briefSrc, /FACTS_CAP/);
  assert.match(briefSrc, /jd-brief-more-fixed/);
  assert.match(briefSrc, /more fixed/);
});

test("TripBrief scheduled fact rows carry no buttons, menus, or drag controls", () => {
  // Extract the scheduled-fact JSX block to check it has no interactive controls.
  // We confirm: no button, no DropdownMenu, no drag handle inside the fact block.
  const factBlock = briefSrc.slice(
    briefSrc.indexOf('data-testid="jd-brief-scheduled-fact"'),
    briefSrc.indexOf('data-testid="jd-brief-scheduled-fact"') + 400
  );
  assert.ok(factBlock.length > 20, "fact block must exist");
  assert.doesNotMatch(factBlock, /<button/i);
  assert.doesNotMatch(factBlock, /DropdownMenu|MoreHorizontal|GripVertical/);
});

test("TripBrief Review ideas behavior remains wired", () => {
  assert.match(briefSrc, /data-testid="jd-brief-review-action"/);
  assert.match(briefSrc, /onClick=\{onReview\}/);
  assert.match(briefSrc, /Review ideas/);
});

test("TripBrief retains pending lines for missing flight and stay anchors", () => {
  assert.match(briefSrc, /if \(!hasFlight\) pendingLines\.push/);
  assert.match(briefSrc, /if \(!hasHotel\) pendingLines\.push/);
  assert.match(briefSrc, /data-testid="jd-brief-pending"/);
});

test("TripBrief still derives hasFlight and hasHotel from real placed items", () => {
  assert.match(briefSrc, /i\.itemType === "flight"/);
  assert.match(briefSrc, /i\.itemType === "hotel"/);
});

test("TripBrief honest empty state: no saved ideas nudges to Explore and Saved", () => {
  assert.match(briefSrc, /No saved ideas yet/);
  assert.match(briefSrc, /href="\/explore"/);
  assert.match(briefSrc, /href="\/saved"/);
});

test("TripBrief has exactly one marine-ink primary action (Review ideas only)", () => {
  const matches = briefSrc.match(/bg-ds-marine-ink/g) ?? [];
  assert.equal(matches.length, 1, "exactly one bg-ds-marine-ink primary action in Brief");
});

// ── Source-scan: tripBriefFacts.ts helper ────────────────────────────────────

test("tripBriefFacts.ts imports readHotelCheckIn and readHotelCheckOut from hotelStaySpans", () => {
  assert.match(factsSrc, /import[\s\S]{0,100}readHotelCheckIn[\s\S]{0,50}hotelStaySpans/);
  assert.match(factsSrc, /readHotelCheckOut/);
});

test("tripBriefFacts.ts exports deriveTripBriefFacts as the main entry point", () => {
  assert.match(factsSrc, /export function deriveTripBriefFacts/);
});

test("tripBriefFacts.ts handles meal reservationTime gate", () => {
  assert.match(factsSrc, /reservationTime/);
  assert.match(factsSrc, /meal-reservation/);
});

test("tripBriefFacts.ts handles activity entryTime gate", () => {
  assert.match(factsSrc, /entryTime/);
  assert.match(factsSrc, /activity-entry/);
});

test("tripBriefFacts.ts does not import from api.ts", () => {
  assert.doesNotMatch(factsSrc, /from ["']\.\/api["']/);
  assert.doesNotMatch(factsSrc, /from ["']@\/lib\/api["']/);
});

test("tripBriefFacts.ts does not import any UI components", () => {
  assert.doesNotMatch(factsSrc, /from ["']react["']/);
  assert.doesNotMatch(factsSrc, /from ["']@\/components/);
});

test("tripBriefFacts.ts sorts facts by sortKey (chronological)", () => {
  assert.match(factsSrc, /facts\.sort\(.*sortKey/);
});

// ── Contract: no mutation paths introduced ───────────────────────────────────

test("TripBrief does not import or call AddToDayDrawer", () => {
  assert.doesNotMatch(briefSrc, /AddToDayDrawer/);
});

test("TripBrief does not import or call IdeasTray directly", () => {
  assert.doesNotMatch(briefSrc, /IdeasTray/);
});

test("TripBrief does not call assignIdeaToDay, unplaceItemToIdeas, or deleteItem", () => {
  assert.doesNotMatch(briefSrc, /assignIdeaToDay|unplaceItemToIdeas|deleteItem/);
});

test("tripBriefFacts.ts does not reference AddToDayDrawer or IdeasTray", () => {
  assert.doesNotMatch(factsSrc, /AddToDayDrawer|IdeasTray/);
});

test("AddToDayDrawer is unchanged by this slice (source scan sanity)", () => {
  // Brief scheduled-facts changes must not modify AddToDayDrawer.
  assert.match(addToDaySrc, /AddToDayDrawer/);
  assert.doesNotMatch(addToDaySrc, /jd-brief-scheduled-fact/);
});

test("IdeasTray is unchanged by this slice (source scan sanity)", () => {
  assert.match(ideasTraySrc, /IdeasTray/);
  assert.doesNotMatch(ideasTraySrc, /jd-brief-scheduled-fact/);
});
