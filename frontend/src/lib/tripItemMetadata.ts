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
 *   - Only forwards fields that are present and non-null on the source.
 *   - Never fabricates coordinates, place ids, ratings, or map links.
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

/**
 * Extract routeable canonical metadata from any source `details`-like blob.
 * Returns a flat object containing only the routeable keys that the source
 * actually carries — never fabricates a missing field.
 */
export function extractRouteableTripItemMetadata(
  source: Record<string, unknown> | null | undefined,
): Record<string, unknown> {
  if (!source) return {};
  const out: Record<string, unknown> = {};
  for (const key of ROUTEABLE_METADATA_KEYS) {
    const value = readCamelOrSnake(source, key, CAMEL_TO_SNAKE[key]);
    if (value !== undefined && value !== null) {
      out[key] = value;
    }
  }
  return out;
}

/**
 * True only when both lat and lng are real numbers on the source details.
 * Used to decide whether a card is travel-hint-eligible without guessing.
 */
export function hasRouteableCoordinates(
  source: Record<string, unknown> | null | undefined,
): boolean {
  if (!source) return false;
  const lat = readCamelOrSnake(source, "lat", "lat");
  const lng = readCamelOrSnake(source, "lng", "lng");
  return typeof lat === "number" && Number.isFinite(lat)
    && typeof lng === "number" && Number.isFinite(lng);
}
