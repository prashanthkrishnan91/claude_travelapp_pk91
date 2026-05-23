import type { ItineraryItem } from "@/types";

// Journey Desk day-part classification.
//
// This mirrors the durable, honest classifier used by ItineraryDayColumn
// (`getItemDayPart`) so the Journey Desk expanded day groups items the same way
// the itinerary does — never fabricating a time. It reads only real signals:
//   1. an explicit persisted `details.dayPart` (written by updateItemTimeline),
//   2. a keyword in `details.timeLabel`,
//   3. a real hour parsed from `startTime` / flight departure fields.
// When no real signal exists the item stays `unscheduled` (shown as "Anytime").
//
// It is duplicated rather than imported because itinerary-timeline tests pin the
// classifier source inside ItineraryDayColumn; a later slice can consolidate.

export type DayPart = "morning" | "afternoon" | "evening" | "unscheduled";

export function getItemDayPart(item: ItineraryItem): DayPart {
  const d = (item.details ?? {}) as Record<string, unknown>;

  const explicit = d.dayPart as string | undefined;
  if (explicit === "morning" || explicit === "afternoon" || explicit === "evening") return explicit;
  if (explicit === "unscheduled") return "unscheduled";

  const label = ((d.timeLabel as string | undefined) ?? "").toLowerCase();
  if (label.includes("morning")) return "morning";
  if (label.includes("afternoon")) return "afternoon";
  if (label.includes("evening") || label.includes("night")) return "evening";

  const parseHour = (raw: unknown): number | null => {
    if (typeof raw !== "string" || raw.trim().length === 0) return null;
    const input = raw.trim();
    const isoMatch = input.match(/T(\d{2}):/);
    if (isoMatch) return Number(isoMatch[1]);
    const hhMM = input.match(/^(\d{1,2}):\d{2}/);
    if (hhMM) return Number(hhMM[1]);
    const parsed = new Date(input);
    return isNaN(parsed.getTime()) ? null : parsed.getHours();
  };

  const flightDetails = item.itemType === "flight" ? d : null;
  const hour =
    parseHour(item.startTime) ??
    parseHour(flightDetails?.departureTime) ??
    parseHour(flightDetails?.departure_time) ??
    parseHour(flightDetails?.departureDateTime) ??
    parseHour(flightDetails?.departure_datetime);

  const normalizedHour =
    typeof hour === "number" && Number.isFinite(hour) && hour >= 0 && hour <= 23 ? hour : null;

  if (normalizedHour !== null) {
    if (normalizedHour >= 0 && normalizedHour < 12) return "morning";
    if (normalizedHour >= 12 && normalizedHour < 17) return "afternoon";
    if (normalizedHour >= 17) return "evening";
  }

  return "unscheduled";
}

// Journey Desk expanded-day sections: Morning / Afternoon / Evening / Logistics,
// plus an honest "Anytime" bucket for untimed, non-logistics items.
export type JourneyDeskSection = "morning" | "afternoon" | "evening" | "logistics" | "anytime";

const LOGISTICS_TYPES = new Set(["flight", "hotel", "transit"]);

export function classifyJourneyDeskSection(item: ItineraryItem): JourneyDeskSection {
  if (LOGISTICS_TYPES.has(item.itemType)) return "logistics";
  const part = getItemDayPart(item);
  return part === "unscheduled" ? "anytime" : part;
}

export interface JourneyDeskGroup {
  key: JourneyDeskSection;
  label: string;
  items: ItineraryItem[];
}

const SECTION_ORDER: { key: JourneyDeskSection; label: string }[] = [
  { key: "morning", label: "Morning" },
  { key: "afternoon", label: "Afternoon" },
  { key: "evening", label: "Evening" },
  { key: "logistics", label: "Logistics" },
  { key: "anytime", label: "Anytime" },
];

export function groupJourneyDeskDay(items: ItineraryItem[]): JourneyDeskGroup[] {
  const buckets: Record<JourneyDeskSection, ItineraryItem[]> = {
    morning: [],
    afternoon: [],
    evening: [],
    logistics: [],
    anytime: [],
  };
  for (const item of items) buckets[classifyJourneyDeskSection(item)].push(item);
  return SECTION_ORDER.filter((s) => buckets[s.key].length > 0).map((s) => ({
    key: s.key,
    label: s.label,
    items: buckets[s.key],
  }));
}
