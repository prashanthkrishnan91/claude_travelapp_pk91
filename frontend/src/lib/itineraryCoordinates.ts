// Journey Desk v2B — itinerary coordinate contract.
//
// Single, honest normalizer for real geographic coordinates carried by source
// data (search results, saved snapshots, Google geometry). It NEVER infers,
// geocodes, or fabricates: it only reads coordinates that already exist, in a
// few known shapes, and validates them. The read side (MapFoldOut, and a future
// v2C pin renderer) calls this so even loosely-persisted coords are gated.
//
// No network. No index/destination/address/maps-URL inference. No goldenSpread.

export interface ItineraryCoordinates {
  lat: number;
  lng: number;
}

function toFiniteNumber(value: unknown): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed === "") return null;
    const n = Number(trimmed);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function validPair(lat: number | null, lng: number | null): ItineraryCoordinates | null {
  if (lat === null || lng === null) return null;
  // Valid Earth ranges only.
  if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return null;
  // (0, 0) is the canonical "null island" placeholder — reject it.
  if (lat === 0 && lng === 0) return null;
  return { lat, lng };
}

/**
 * Extract real coordinates from a source object, or null. Accepts only these
 * real shapes (first valid pair wins):
 *   - { lat, lng }
 *   - { latitude, longitude }
 *   - { location: { lat, lng } | { latitude, longitude } }
 *   - { geometry: { location: { lat, lng } | { latitude, longitude } } }  (Google)
 * Numbers or safely-parseable numeric strings only; finite and in range.
 */
export function extractItineraryCoordinates(source: unknown): ItineraryCoordinates | null {
  if (!source || typeof source !== "object") return null;
  const s = source as Record<string, unknown>;

  const candidates: Array<[unknown, unknown]> = [
    [s.lat, s.lng],
    [s.latitude, s.longitude],
  ];

  // `location` may be a plain string (e.g. a city name) — only an object qualifies.
  const loc = s.location;
  if (loc && typeof loc === "object") {
    const l = loc as Record<string, unknown>;
    candidates.push([l.lat, l.lng], [l.latitude, l.longitude]);
  }

  const geom = s.geometry;
  if (geom && typeof geom === "object") {
    const gl = (geom as Record<string, unknown>).location;
    if (gl && typeof gl === "object") {
      const g = gl as Record<string, unknown>;
      candidates.push([g.lat, g.lng], [g.latitude, g.longitude]);
    }
  }

  for (const [rawLat, rawLng] of candidates) {
    const pair = validPair(toFiniteNumber(rawLat), toFiniteNumber(rawLng));
    if (pair) return pair;
  }
  return null;
}
