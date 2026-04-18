/** Client-side travel time estimation using haversine distance. */

export interface TravelEstimate {
  distanceKm: number;
  walkMinutes: number;
  driveMinutes: number;
}

function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.asin(Math.sqrt(Math.max(0, Math.min(1, a))));
}

export function estimateTravel(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number,
): TravelEstimate {
  const distKm = haversineKm(lat1, lng1, lat2, lng2);
  return {
    distanceKm: Math.round(distKm * 10) / 10,
    walkMinutes: Math.max(1, Math.round((distKm / 5) * 60)),   // 5 km/h
    driveMinutes: Math.max(1, Math.round((distKm / 30) * 60)), // 30 km/h city
  };
}

/** Returns the preferred label and mode: walk if ≤20 min, otherwise drive. */
export function formatTravelBadge(est: TravelEstimate): { label: string; mode: "walk" | "drive" } {
  if (est.walkMinutes <= 20) {
    return { label: `${est.walkMinutes} min walk`, mode: "walk" };
  }
  return { label: `${est.driveMinutes} min drive`, mode: "drive" };
}

export function sumRoute(estimates: TravelEstimate[]): { totalKm: number; totalDriveMin: number } {
  const totalKm = Math.round(estimates.reduce((s, e) => s + e.distanceKm, 0) * 10) / 10;
  const totalDriveMin = estimates.reduce((s, e) => s + e.driveMinutes, 0);
  return { totalKm, totalDriveMin };
}
