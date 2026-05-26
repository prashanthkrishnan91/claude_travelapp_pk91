import type { ItineraryDay, ItineraryItem } from "@/types";

export type StayMarkerKind = "staying" | "checkout";

export interface StayMarker {
  kind: StayMarkerKind;
  hotelTitle: string;
  itemId: string;
}

export interface DayHotelDisplay {
  suppressedHotelItemIds: Set<string>;
  stayMarkers: StayMarker[];
}

function parseHotelDate(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  const s = raw.trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
  const [y, m, d] = s.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  if (isNaN(dt.getTime())) return null;
  return s;
}

export function readHotelCheckIn(d: Record<string, unknown>): string | null {
  return parseHotelDate(d.checkIn ?? d.check_in ?? d.check_in_date ?? d.checkInDate);
}

export function readHotelCheckOut(d: Record<string, unknown>): string | null {
  return parseHotelDate(d.checkOut ?? d.check_out ?? d.check_out_date ?? d.checkOutDate);
}

interface HotelSpan {
  checkIn: string;
  checkOut: string;
  hotelTitle: string;
  itemId: string;
  physicalDayId: string;
  physicalDayDate: string | null;
  position: number;
}

export function deriveHotelStayDisplay(
  displayDays: Array<ItineraryDay & { date?: string }>
): Map<string, DayHotelDisplay> {
  const result = new Map<string, DayHotelDisplay>();

  for (const day of displayDays) {
    result.set(day.id, { suppressedHotelItemIds: new Set(), stayMarkers: [] });
  }

  const spans: HotelSpan[] = [];
  for (const day of displayDays) {
    for (const item of day.items) {
      if (item.itemType !== "hotel") continue;
      const d = (item.details ?? {}) as Record<string, unknown>;
      const checkIn = readHotelCheckIn(d);
      const checkOut = readHotelCheckOut(d);
      if (!checkIn || !checkOut || checkIn >= checkOut) continue;
      spans.push({
        checkIn,
        checkOut,
        hotelTitle: item.title,
        itemId: item.id,
        physicalDayId: day.id,
        physicalDayDate: day.date ?? null,
        position: item.position,
      });
    }
  }

  const byCheckIn = new Map<string, HotelSpan[]>();
  for (const span of spans) {
    const arr = byCheckIn.get(span.checkIn) ?? [];
    arr.push(span);
    byCheckIn.set(span.checkIn, arr);
  }

  for (const [, group] of byCheckIn) {
    const onCheckInDay = group.filter((s) => s.physicalDayDate === s.checkIn);
    const canonical =
      onCheckInDay.length > 0
        ? onCheckInDay.reduce((a, b) => (a.position <= b.position ? a : b))
        : group.reduce((a, b) => (a.position <= b.position ? a : b));

    for (const span of group) {
      if (span.itemId !== canonical.itemId) {
        const dayDisplay = result.get(span.physicalDayId);
        if (dayDisplay) dayDisplay.suppressedHotelItemIds.add(span.itemId);
      }
    }

    for (const day of displayDays) {
      if (!day.date || day.id === canonical.physicalDayId) continue;
      const dayDate = day.date;
      if (dayDate > canonical.checkIn && dayDate < canonical.checkOut) {
        result.get(day.id)?.stayMarkers.push({
          kind: "staying",
          hotelTitle: canonical.hotelTitle,
          itemId: canonical.itemId,
        });
      } else if (dayDate === canonical.checkOut) {
        result.get(day.id)?.stayMarkers.push({
          kind: "checkout",
          hotelTitle: canonical.hotelTitle,
          itemId: canonical.itemId,
        });
      }
    }
  }

  return result;
}
