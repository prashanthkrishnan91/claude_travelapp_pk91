/**
 * Canonical trip-item metadata contract for routeable place-like items.
 *
 * Travel hints, map links, address display, category labels, and ratings on
 * an itinerary card should not depend on whether the item entered the trip
 * from Concierge, Build/Add-to-Day, Ideas placement, Saved, or Explore. Once
 * a routeable place-like row becomes an itinerary item, the same canonical
 * fields drive its card UX wherever the source data supports them.
 *
 * Contract:
 *   - Reads camelCase first, then snake_case fallback (legacy persisted rows).
 *   - Also accepts widely-used alternate coordinate keys (`latitude`/`longitude`,
 *     nested `coordinates.{lat,lng}`, `geo.{lat,lng}`, `location.{lat,lng}`).
 *   - Only forwards fields that are present and non-null on the source.
 *   - Never fabricates coordinates, place ids, ratings, or map links.
 *   - Never geocodes — pure local mapping; no provider calls.
 *   - Returned object is safe to spread into a write-side `details` payload;
 *     `toSnake` on the api boundary will re-snake the camelCase keys.
 */
export const ROUTEABLE_METADATA_KEYS = [
  "lat",
  "lng",
  "address",
  "formattedAddress",
  "placeId",
  "providerPlaceId",
  "googleMapsUri",
  "mapsLink",
  "category",
  "type",
  "rating",
  "numReviews",
  "priceLevel",
  "openingHours",
  "bookingUrl",
  "cuisine",
  "city",
  "location",
  "name",
  "description",
  "tags",
  "aiScore",
] as const;

type RouteableKey = (typeof ROUTEABLE_METADATA_KEYS)[number];

function readCamelOrSnake(
  source: Record<string, unknown>,
  camel: string,
  snake: string,
): unknown {
  const c = source[camel];
  if (c !== undefined && c !== null) return c;
  const s = source[snake];
  if (s !== undefined && s !== null) return s;
  return undefined;
}

const CAMEL_TO_SNAKE: Record<RouteableKey, string> = {
  lat: "lat",
  lng: "lng",
  address: "address",
  formattedAddress: "formatted_address",
  placeId: "place_id",
  providerPlaceId: "provider_place_id",
  googleMapsUri: "google_maps_uri",
  mapsLink: "maps_link",
  category: "category",
  type: "type",
  rating: "rating",
  numReviews: "num_reviews",
  priceLevel: "price_level",
  openingHours: "opening_hours",
  bookingUrl: "booking_url",
  cuisine: "cuisine",
  city: "city",
  location: "location",
  name: "name",
  description: "description",
  tags: "tags",
  aiScore: "ai_score",
};

const LAT_RANGE: readonly [number, number] = [-90, 90];
const LNG_RANGE: readonly [number, number] = [-180, 180];

/**
 * Read a finite number within [low, high], or undefined. Rejects booleans,
 * non-numeric values, NaN/Infinity, and out-of-range values — a coordinate
 * that fails this check must count as missing, never as located. Mirrors the
 * backend port in `route_quality_diagnostic.py::_read_number` so the two
 * "canonical coordinate" definitions never disagree on what counts as valid.
 */
function readNumber(value: unknown, range?: readonly [number, number]): number | undefined {
  if (typeof value !== "number" || !Number.isFinite(value)) return undefined;
  if (range && (value < range[0] || value > range[1])) return undefined;
  return value;
}

/**
 * Resolve a real numeric latitude from any common provider key.
 * Order: top-level `lat`/`latitude`, then nested `coordinates`/`geo`/`location`
 * (when those are objects carrying `{lat,lng}` or `{latitude,longitude}`).
 * Returns undefined when no real number is found, or when the value is out of
 * the valid Earth latitude range — never geocodes, never treats junk as real.
 */
export function readCanonicalLat(
  source: Record<string, unknown> | null | undefined,
): number | undefined {
  if (!source) return undefined;
  const direct = readNumber(source.lat, LAT_RANGE) ?? readNumber(source.latitude, LAT_RANGE);
  if (direct !== undefined) return direct;
  for (const k of ["coordinates", "geo", "location", "coords", "position"]) {
    const nested = source[k];
    if (nested && typeof nested === "object") {
      const n = nested as Record<string, unknown>;
      const v = readNumber(n.lat, LAT_RANGE) ?? readNumber(n.latitude, LAT_RANGE);
      if (v !== undefined) return v;
    }
  }
  return undefined;
}

/** See `readCanonicalLat` — same contract for longitude. */
export function readCanonicalLng(
  source: Record<string, unknown> | null | undefined,
): number | undefined {
  if (!source) return undefined;
  const direct =
    readNumber(source.lng, LNG_RANGE) ??
    readNumber(source.longitude, LNG_RANGE) ??
    readNumber(source.lon, LNG_RANGE);
  if (direct !== undefined) return direct;
  for (const k of ["coordinates", "geo", "location", "coords", "position"]) {
    const nested = source[k];
    if (nested && typeof nested === "object") {
      const n = nested as Record<string, unknown>;
      const v =
        readNumber(n.lng, LNG_RANGE) ??
        readNumber(n.longitude, LNG_RANGE) ??
        readNumber(n.lon, LNG_RANGE);
      if (v !== undefined) return v;
    }
  }
  return undefined;
}

/**
 * Extract routeable canonical metadata from any source `details`-like blob.
 * Returns a flat object containing only the routeable keys that the source
 * actually carries — never fabricates a missing field. Coordinates are
 * normalized to canonical `lat`/`lng` even when the source used alternate
 * keys (`latitude`/`longitude` or nested `coordinates.lat`/`geo.lat`...).
 */
export function extractRouteableTripItemMetadata(
  source: Record<string, unknown> | null | undefined,
): Record<string, unknown> {
  if (!source) return {};
  const out: Record<string, unknown> = {};
  for (const key of ROUTEABLE_METADATA_KEYS) {
    if (key === "lat" || key === "lng") continue;
    const value = readCamelOrSnake(source, key, CAMEL_TO_SNAKE[key]);
    if (value !== undefined && value !== null) {
      out[key] = value;
    }
  }
  // Coordinates: read from any common key shape; canonicalize to lat/lng.
  const lat = readCanonicalLat(source);
  const lng = readCanonicalLng(source);
  if (lat !== undefined && lng !== undefined) {
    out.lat = lat;
    out.lng = lng;
  }
  return out;
}

/**
 * True only when both lat and lng are resolvable as real finite numbers
 * (under any canonical or alternate key). Used to decide whether a card is
 * travel-hint-eligible without guessing.
 */
export function hasRouteableCoordinates(
  source: Record<string, unknown> | null | undefined,
): boolean {
  if (!source) return false;
  return readCanonicalLat(source) !== undefined && readCanonicalLng(source) !== undefined;
}
