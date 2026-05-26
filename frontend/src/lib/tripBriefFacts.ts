import type { ItineraryDay } from "@/types";
import { readHotelCheckIn, readHotelCheckOut } from "./hotelStaySpans";

export type ScheduledFactType =
  | "flight"
  | "hotel-checkin"
  | "hotel-checkout"
  | "hotel-stay"
  | "meal-reservation"
  | "activity-entry";

export interface ScheduledFact {
  type: ScheduledFactType;
  label: string;
  title: string;
  dayNumber: number;
  date: string | null;
  time: string | null;
  sortKey: string;
}

/** Formats a plain HH:mm or ISO datetime string to "H:MM AM/PM". Returns null if unparseable. */
export function formatBriefTime(raw: unknown): string | null {
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

function makeSortKey(dayNumber: number, time: string | null): string {
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

/**
 * Derives fixed scheduled facts from itinerary days.
 *
 * Pure, deterministic, no side effects. Facts are sorted chronologically by
 * day number then time (items without a specific time sort last within their day).
 *
 * - Flights: always included as placed facts.
 * - Hotels: check-in and check-out facts when dates exist; simple stay anchor otherwise.
 * - Meals: included only when details.reservationTime is present.
 * - Activities: included only when details.entryTime is present.
 *
 * Uses readHotelCheckIn/readHotelCheckOut from hotelStaySpans.ts to avoid
 * duplicating the camelCase-first fallback chain.
 */
export function deriveTripBriefFacts(days: ItineraryDay[]): ScheduledFact[] {
  const facts: ScheduledFact[] = [];
  const emittedHotelKeys = new Set<string>();

  for (const day of days) {
    for (const item of day.items ?? []) {
      const d = (item.details ?? {}) as Record<string, unknown>;

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

// ── Grouped summary ───────────────────────────────────────────────────────────

export interface FlightSummaryRow {
  title: string;
  dayNumber: number;
  date: string | null;
  time: string | null;
}

export interface StaySummaryRow {
  title: string;
  checkInDay: number | null;
  checkInDate: string | null;
  checkOutDay: number | null;
  checkOutDate: string | null;
}

export interface TripBriefSummary {
  flights: FlightSummaryRow[];
  stays: StaySummaryRow[];
  reservationCount: number;
  entryCount: number;
  allFacts: ScheduledFact[];
}

/**
 * Derives a compact grouped summary for the Brief UI:
 * - flights: one row per placed flight
 * - stays: one range row per hotel (check-in + check-out combined)
 * - reservationCount / entryCount: scalar counts for timed plans
 * - allFacts: full chronological list for the disclosure panel
 */
export function deriveTripBriefSummary(days: ItineraryDay[]): TripBriefSummary {
  const allFacts = deriveTripBriefFacts(days);

  const flights: FlightSummaryRow[] = allFacts
    .filter((f) => f.type === "flight")
    .map((f) => ({ title: f.title, dayNumber: f.dayNumber, date: f.date, time: f.time }));

  // Build one StaySummaryRow per unique stay identity (title::checkIn::checkOut).
  // Iterating days directly (not allFacts) so two same-name hotels with different
  // dates get distinct rows — keying by title alone would collapse them.
  const stayMap = new Map<string, StaySummaryRow>();
  const emittedStayKeys = new Set<string>();
  for (const day of days) {
    for (const item of day.items ?? []) {
      if (item.itemType !== "hotel") continue;
      const d = (item.details ?? {}) as Record<string, unknown>;
      const checkIn = readHotelCheckIn(d);
      const checkOut = readHotelCheckOut(d);
      const stayKey = `${item.title}::${checkIn ?? ""}::${checkOut ?? ""}`;
      if (emittedStayKeys.has(stayKey)) continue;
      emittedStayKeys.add(stayKey);
      const checkInDay = checkIn ? (days.find((d2) => d2.date === checkIn) ?? day).dayNumber : null;
      const checkOutDay = checkOut ? (days.find((d2) => d2.date === checkOut) ?? day).dayNumber : null;
      stayMap.set(stayKey, {
        title: item.title,
        checkInDay,
        checkInDate: checkIn ?? null,
        checkOutDay,
        checkOutDate: checkOut ?? null,
      });
    }
  }
  const stays = Array.from(stayMap.values());

  const reservationCount = allFacts.filter((f) => f.type === "meal-reservation").length;
  const entryCount = allFacts.filter((f) => f.type === "activity-entry").length;

  return { flights, stays, reservationCount, entryCount, allFacts };
}
