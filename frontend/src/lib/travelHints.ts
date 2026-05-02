/** Client-side travel time hints for adjacent itinerary stops. */

import { estimateTravel, TravelEstimate } from "./travelTime";

export type PairHintKind = "travel_ok" | "far_apart" | "missing_location";

export interface PairHint {
  itemAId: string;
  itemBId: string;
  kind: PairHintKind;
  /** Human-readable copy — always safe to display. */
  label: string;
  estimate?: TravelEstimate;
}

/** Drive time above which stops are considered potentially far apart — rough threshold, not precise routing. */
export const FAR_APART_DRIVE_MIN = 30;
/** Multiplier applied to straight-line walking estimates to avoid optimistic hints in dense city grids. */
export const CONSERVATIVE_WALK_FACTOR = 1.35;
/** Prefer walk hints only when the conservative estimate remains reasonably short. */
export const MAX_WALK_HINT_MIN = 35;

interface HintableItem {
  id: string;
  details?: Record<string, unknown> | null;
}

/**
 * Returns one PairHint per adjacent pair in the given ordered list.
 * Returns [] when items has fewer than two entries.
 */
export function computeAdjacentHints(items: HintableItem[]): PairHint[] {
  const hints: PairHint[] = [];
  for (let i = 0; i < items.length - 1; i++) {
    const a = items[i];
    const b = items[i + 1];
    const da = (a.details ?? {}) as Record<string, unknown>;
    const db = (b.details ?? {}) as Record<string, unknown>;
    const lat1 = da.lat as number | null | undefined;
    const lng1 = da.lng as number | null | undefined;
    const lat2 = db.lat as number | null | undefined;
    const lng2 = db.lng as number | null | undefined;

    if (lat1 == null || lng1 == null || lat2 == null || lng2 == null) {
      hints.push({
        itemAId: a.id,
        itemBId: b.id,
        kind: "missing_location",
        label: "Add location details to improve travel hints.",
      });
      continue;
    }

    const estimate = estimateTravel(lat1, lng1, lat2, lng2);
    const conservativeWalkMin = Math.max(1, Math.ceil(estimate.walkMinutes * CONSERVATIVE_WALK_FACTOR));
    const mode: "walk" | "drive" = conservativeWalkMin <= MAX_WALK_HINT_MIN ? "walk" : "drive";

    if (estimate.driveMinutes > FAR_APART_DRIVE_MIN) {
      hints.push({
        itemAId: a.id,
        itemBId: b.id,
        kind: "far_apart",
        label: "These two stops may be far apart.",
        estimate: { ...estimate, walkMinutes: conservativeWalkMin },
      });
    } else {
      const walkAdjustedEstimate = { ...estimate, walkMinutes: conservativeWalkMin };
      const label =
        mode === "walk"
          ? `${walkAdjustedEstimate.walkMinutes} min walk`
          : `${walkAdjustedEstimate.driveMinutes} min drive`;
      hints.push({
        itemAId: a.id,
        itemBId: b.id,
        kind: "travel_ok",
        label: `~${label}`,
        estimate: walkAdjustedEstimate,
      });
    }
  }
  return hints;
}

/** Aggregates hints to identify day-level issues. */
export function summarizeHints(hints: PairHint[]): {
  farApartCount: number;
  missingLocationCount: number;
  hasIssues: boolean;
} {
  const farApartCount = hints.filter((h) => h.kind === "far_apart").length;
  const missingLocationCount = hints.filter((h) => h.kind === "missing_location").length;
  return {
    farApartCount,
    missingLocationCount,
    hasIssues: farApartCount + missingLocationCount > 0,
  };
}
