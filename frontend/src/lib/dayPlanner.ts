/**
 * Smart Day Timeline AI Planning — client-side deterministic planner.
 *
 * Used as the primary fallback when the backend AI path is unavailable or
 * fails. Applies simple common-sense rules based on item title, category,
 * cuisine, and itemType to suggest dayPart / timeLabel metadata.
 *
 * Rules (in priority order):
 *   1. Preserve explicit details.dayPart if already set.
 *   2. Flights and hotels → unscheduled (conservative).
 *   3. Title/category keyword match → morning | afternoon | evening.
 *   4. itemType == "meal" with no specific match → afternoon (Lunch).
 *   5. itemType == "activity" with no match → morning.
 *   6. Default → unscheduled.
 */

import type { ItineraryItem } from "@/types";

export type DayPart = "morning" | "afternoon" | "evening" | "unscheduled";

export interface DayPlannerSuggestion {
  itemId: string;
  dayPart: DayPart;
  timeLabel?: string;
}

const MORNING_PAT =
  /breakfast|brunch|coffee|cafe|caf[eé]|bakery|patisserie|boulangerie|morning tour|sunrise/i;

const EVENING_PAT =
  /dinner|supper|cocktail|nightlife|nightclub|\bbar\b|speakeasy|jazz\s+club|wine\s+bar|rooftop\s+bar|evening|night\s+market/i;

const LUNCH_PAT = /\blunch\b|midday|noon/i;

function _morningLabel(text: string): string | undefined {
  if (/breakfast|brunch/i.test(text)) return "Breakfast";
  if (/coffee|cafe|caf[eé]|bakery/i.test(text)) return "Morning coffee";
  return undefined;
}

function _eveningLabel(text: string): string | undefined {
  if (/dinner|supper/i.test(text)) return "Dinner";
  if (/cocktail|\bbar\b|speakeasy|wine\s+bar/i.test(text)) return "Evening drinks";
  if (/nightlife|nightclub|jazz\s+club/i.test(text)) return "Night out";
  return undefined;
}

export function suggestTimelineFallback(
  items: ItineraryItem[]
): DayPlannerSuggestion[] {
  return items.map((item) => {
    const d = (item.details ?? {}) as Record<string, unknown>;

    // Preserve explicitly set dayPart (from prior manual control saves)
    const explicit = d.dayPart as string | undefined;
    if (
      explicit === "morning" ||
      explicit === "afternoon" ||
      explicit === "evening"
    ) {
      return {
        itemId: item.id,
        dayPart: explicit,
        timeLabel: (d.timeLabel as string | undefined) || undefined,
      };
    }

    // Flights and hotels: leave unscheduled, avoid guessing
    if (item.itemType === "flight" || item.itemType === "hotel") {
      return { itemId: item.id, dayPart: "unscheduled" };
    }

    const searchText = [
      item.title,
      d.category as string,
      d.type as string,
      d.cuisine as string,
      d.notes as string,
    ]
      .filter(Boolean)
      .join(" ");

    if (MORNING_PAT.test(searchText)) {
      return {
        itemId: item.id,
        dayPart: "morning",
        timeLabel: _morningLabel(searchText),
      };
    }

    if (EVENING_PAT.test(searchText)) {
      return {
        itemId: item.id,
        dayPart: "evening",
        timeLabel: _eveningLabel(searchText),
      };
    }

    if (LUNCH_PAT.test(searchText)) {
      return { itemId: item.id, dayPart: "afternoon", timeLabel: "Lunch" };
    }

    // Generic meal items default to afternoon lunch slot
    if (item.itemType === "meal") {
      return { itemId: item.id, dayPart: "afternoon", timeLabel: "Lunch" };
    }

    // Generic activities default to morning
    if (item.itemType === "activity") {
      return { itemId: item.id, dayPart: "morning" };
    }

    return { itemId: item.id, dayPart: "unscheduled" };
  });
}
