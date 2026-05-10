import type { Trip, TripStatus } from "@/types";

const PLANNING_STATUSES: ReadonlySet<TripStatus> = new Set(["draft", "researching", "planned", "booked"]);

function isoToday(today?: Date): string {
  return (today ?? new Date()).toISOString().slice(0, 10);
}

export function getDisplayTripStatus(trip: Trip, today?: Date): TripStatus {
  const now = isoToday(today);
  if (trip.endDate && trip.endDate < now && PLANNING_STATUSES.has(trip.status)) {
    return "completed";
  }
  return trip.status;
}

export function getTripStatusGroup(trip: Trip, today?: Date): "Active" | "Past" {
  const status = getDisplayTripStatus(trip, today);
  return status === "completed" || status === "archived" ? "Past" : "Active";
}
