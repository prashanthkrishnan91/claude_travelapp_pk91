/**
 * Canonical trip candidate selector — Level 3 Trip Data Contract Rescue.
 *
 * Single source of truth for grouping persisted ``ItineraryItem`` rows
 * (returned by ``GET /trips/{id}/items``) into the four product verticals
 * the TripBuilder UI renders.
 *
 * Why this exists: prior to this module, flights/hotels were read from
 * ``itinerary_items`` while attractions/restaurants were read from the
 * legacy ``trips.metadata.explore_snapshot`` cache, which meant that
 * ``/trips/create-with-search`` could persist 8 ACTIVITY rows + 8 MEAL rows
 * and the Attractions/Restaurants panels still rendered 0 — the snapshot
 * had not been populated yet and the AI Concierge "Top attractions in Tokyo"
 * fallback would then write an empty snapshot, locking in the zero state.
 *
 * Contract:
 *   - ``item_type`` is the primary discriminator (flight/hotel/activity/meal).
 *   - Round-trip flights are split off via ``details.isRoundTrip``.
 *   - ``details.sourceKind`` is *not* used to gate visibility — every
 *     persisted vertical row is a candidate regardless of provenance.
 *   - Items are de-duped by a stable identity key per vertical.
 *
 * Notes (BACKWARDS COMPAT):
 *   ``ItineraryItem.details`` arrives camelCased by ``toCamel`` in api.ts,
 *   but pre-migration rows persisted before the rename still carry snake_case
 *   keys (e.g. ``num_reviews``, ``google_maps_uri``, ``is_round_trip``,
 *   ``return_flight``).  Every access in this module reads camelCase first
 *   then falls back to snake_case so old rows continue to display.
 */

import type {
  AttractionSearchResult,
  ItineraryItem,
  RestaurantSearchResult,
} from "@/types";
import {
  computeExploreAttractionScore,
  computeExploreRestaurantScore,
} from "@/lib/api";

export interface TripCandidateBuckets {
  flights: ItineraryItem[];
  roundTripFlights: ItineraryItem[];
  hotels: ItineraryItem[];
  attractions: AttractionSearchResult[];
  restaurants: RestaurantSearchResult[];
  /** Total counts before any visible-display cap is applied. */
  totals: {
    flights: number;
    roundTripFlights: number;
    hotels: number;
    attractions: number;
    restaurants: number;
  };
}

const EMPTY: TripCandidateBuckets = {
  flights: [],
  roundTripFlights: [],
  hotels: [],
  attractions: [],
  restaurants: [],
  totals: { flights: 0, roundTripFlights: 0, hotels: 0, attractions: 0, restaurants: 0 },
};

function getDetail<T = unknown>(item: ItineraryItem, ...keys: string[]): T | undefined {
  const d = (item.details ?? {}) as Record<string, unknown>;
  for (const k of keys) {
    if (d[k] !== undefined && d[k] !== null) return d[k] as T;
  }
  return undefined;
}

function isDayAssigned(item: ItineraryItem): boolean {
  // Treat null-like legacy sentinels as unscheduled candidates.
  const raw = item.dayId;
  if (raw == null) return false;
  if (typeof raw === "string") {
    const normalized = raw.trim().toLowerCase();
    if (normalized === "" || normalized === "null" || normalized === "undefined") {
      return false;
    }
  }
  return true;
}

function isRoundTripFlight(item: ItineraryItem): boolean {
  const d = (item.details ?? {}) as Record<string, unknown>;
  // Legacy boolean flags
  if (d.isRoundTrip != null) return Boolean(d.isRoundTrip);
  if (d.is_round_trip != null) return Boolean(d.is_round_trip);
  // Canonical: trip_type field (snake_case stored, camelCase after toCamel)
  if (d.tripType === "round_trip" || d.trip_type === "round_trip") return true;
  // Canonical: return_leg present and non-null (outbound+return pair)
  if (d.returnLeg != null || d.return_leg != null) return true;
  return false;
}

/** AI score from persisted details, falling back to 0. */
function flightScore(item: ItineraryItem): number {
  const v = getDetail<number>(item, "aiScore", "ai_score");
  return typeof v === "number" ? v : 0;
}

function hotelScore(item: ItineraryItem): number {
  const v = getDetail<number>(item, "aiScore", "ai_score");
  return typeof v === "number" ? v : 0;
}

function flightDedupeKey(item: ItineraryItem): string {
  const d = (item.details ?? {}) as Record<string, unknown>;
  if (isRoundTripFlight(item)) {
    // Canonical: key on first-segment airline+flightNumber+departureTime for each leg.
    // Route/date alone is not sufficient — many Duffel offers share origin+dest+date.
    const ob     = (d.outboundLeg ?? d.outbound_leg ?? d.outbound) as Record<string, unknown> | undefined;
    const rt     = (d.returnLeg  ?? d.return_leg  ?? d.returnFlight ?? d.return_flight) as Record<string, unknown> | undefined;
    const obSegs = (ob?.segments as Array<Record<string, unknown>>) ?? [];
    const rtSegs = (rt?.segments as Array<Record<string, unknown>>) ?? [];
    const obSeg0 = obSegs[0] as Record<string, unknown> | undefined;
    const rtSeg0 = rtSegs[0] as Record<string, unknown> | undefined;
    const obAirline = (obSeg0?.airline as string)                                                     || (d.airline as string)        || "";
    const obFlight  = ((obSeg0?.flightNumber ?? obSeg0?.flight_number) as string)                     || ((d.flightNumber ?? d.flight_number) as string) || "";
    const obDep     = ((ob?.departureTime   ?? ob?.departure_time)   as string)                       || ((d.departureTime  ?? d.departure_time)  as string) || "";
    const rtAirline = (rtSeg0?.airline as string)      || "";
    const rtFlight  = ((rtSeg0?.flightNumber ?? rtSeg0?.flight_number) as string) || "";
    const rtDep     = ((rt?.departureTime   ?? rt?.departure_time)   as string)   || "";
    if (obFlight || obDep) {
      return `rt:${obAirline}:${obFlight}:${obDep}:${rtAirline}:${rtFlight}:${rtDep}`;
    }
    // Legacy fallback: pairId or item id
    return `rt:${(d.pairId ?? d.pair_id ?? item.id) as string}`;
  }
  const num     = (d.flightNumber ?? d.flight_number) as string | undefined;
  const airline = d.airline as string | undefined;
  const dep     = (d.departureTime ?? d.departure_time) as string | undefined;
  return `ow:${airline ?? ""}:${num ?? item.title}:${dep ?? ""}`;
}

function hotelDedupeKey(item: ItineraryItem): string {
  const d = (item.details ?? {}) as Record<string, unknown>;
  const name = (d.name as string | undefined) ?? item.title;
  return `hotel:${name.trim().toLowerCase()}`;
}

function activityDedupeKey(name: string, placeId: string | undefined): string {
  if (placeId) return `act:place:${placeId}`;
  return `act:name:${name.trim().toLowerCase()}`;
}

function mealDedupeKey(name: string, placeId: string | undefined): string {
  if (placeId) return `meal:place:${placeId}`;
  return `meal:name:${name.trim().toLowerCase()}`;
}

function itemToAttraction(item: ItineraryItem): AttractionSearchResult {
  const d = (item.details ?? {}) as Record<string, unknown>;
  const name = (d.name as string | undefined) ?? item.title;
  const placeId =
    (d.placeId as string | undefined) ??
    (d.place_id as string | undefined) ??
    undefined;
  const address =
    (d.address as string | undefined) ?? item.location ?? "";
  const rating = typeof d.rating === "number" ? (d.rating as number) : undefined;
  const numReviews =
    typeof d.numReviews === "number"
      ? (d.numReviews as number)
      : typeof d.num_reviews === "number"
        ? (d.num_reviews as number)
        : undefined;
  const category =
    (d.category as string | undefined) ??
    ((Array.isArray(d.types) && (d.types as string[])[0]) || "attraction");
  const storedScore =
    typeof d.aiScore === "number" && (d.aiScore as number) > 0
      ? (d.aiScore as number)
      : typeof d.ai_score === "number" && (d.ai_score as number) > 0
        ? (d.ai_score as number)
        : undefined;
  const computedScore =
    storedScore == null && rating != null && numReviews != null && numReviews > 0
      ? computeExploreAttractionScore(rating, numReviews, category)
      : undefined;
  const aiScore = storedScore ?? (computedScore && computedScore > 0 ? computedScore : undefined);
  const mapsUri =
    (d.googleMapsUri as string | undefined) ??
    (d.google_maps_uri as string | undefined) ??
    undefined;
  const bookingUrl =
    (d.bookingUrl as string | undefined) ??
    (d.booking_url as string | undefined) ??
    mapsUri ??
    (placeId ? `https://www.google.com/maps/place/?q=place_id:${encodeURIComponent(placeId)}` : undefined);
  return {
    id: placeId ?? item.id,
    name,
    category,
    description: (d.description as string | undefined) ?? "",
    location: (d.location as string | undefined) ?? item.location ?? "",
    address,
    rating,
    numReviews,
    priceLevel:
      typeof d.priceLevel === "number"
        ? (d.priceLevel as number)
        : typeof d.price_level === "number"
          ? (d.price_level as number)
          : undefined,
    openingHours:
      (d.openingHours as string | undefined) ??
      (d.opening_hours as string | undefined),
    durationMinutes:
      typeof d.durationMinutes === "number"
        ? (d.durationMinutes as number)
        : typeof d.duration_minutes === "number"
          ? (d.duration_minutes as number)
          : undefined,
    aiScore,
    tags: Array.isArray(d.tags) ? (d.tags as string[]) : [],
    bookingUrl,
    lat: typeof d.lat === "number" ? (d.lat as number) : undefined,
    lng: typeof d.lng === "number" ? (d.lng as number) : undefined,
  };
}

function itemToRestaurant(item: ItineraryItem): RestaurantSearchResult {
  const d = (item.details ?? {}) as Record<string, unknown>;
  const name = (d.name as string | undefined) ?? item.title;
  const placeId =
    (d.placeId as string | undefined) ??
    (d.place_id as string | undefined) ??
    undefined;
  const address =
    (d.address as string | undefined) ?? item.location ?? "";
  const rating = typeof d.rating === "number" ? (d.rating as number) : undefined;
  const numReviews =
    typeof d.numReviews === "number"
      ? (d.numReviews as number)
      : typeof d.num_reviews === "number"
        ? (d.num_reviews as number)
        : undefined;
  const priceLevel =
    typeof d.priceLevel === "number"
      ? (d.priceLevel as number)
      : typeof d.price_level === "number"
        ? (d.price_level as number)
        : undefined;
  const storedScore =
    typeof d.aiScore === "number" && (d.aiScore as number) > 0
      ? (d.aiScore as number)
      : typeof d.ai_score === "number" && (d.ai_score as number) > 0
        ? (d.ai_score as number)
        : undefined;
  const sentiment = typeof d.sentiment === "number" ? (d.sentiment as number) : undefined;
  const computedScore =
    storedScore == null && rating != null && numReviews != null && numReviews > 0
      ? computeExploreRestaurantScore(rating, numReviews, priceLevel ?? 2, sentiment)
      : undefined;
  const aiScore = storedScore ?? (computedScore && computedScore > 0 ? computedScore : undefined);
  const mapsUri =
    (d.googleMapsUri as string | undefined) ??
    (d.google_maps_uri as string | undefined) ??
    undefined;
  return {
    id: placeId ?? item.id,
    name,
    cuisine: (d.cuisine as string | undefined) ?? "Restaurant",
    location: (d.location as string | undefined) ?? item.location ?? "",
    address,
    rating,
    numReviews,
    priceLevel,
    openingHours:
      (d.openingHours as string | undefined) ??
      (d.opening_hours as string | undefined),
    aiScore,
    sentiment,
    tags: Array.isArray(d.tags) ? (d.tags as string[]) : [],
    bookingUrl:
      (d.bookingUrl as string | undefined) ??
      (d.booking_url as string | undefined),
    lat: typeof d.lat === "number" ? (d.lat as number) : undefined,
    lng: typeof d.lng === "number" ? (d.lng as number) : undefined,
    providerPlaceId: placeId,
    googleMapsUri: mapsUri,
    placeId,
  };
}

/**
 * Bucket persisted ItineraryItem rows into the four candidate verticals
 * + a separate round-trip flight bucket.  Skips rows assigned to a day
 * (those belong to the right-pane itinerary, not the left-pane candidates).
 */
export function buildTripCandidateBuckets(items: ItineraryItem[]): TripCandidateBuckets {
  if (!Array.isArray(items) || items.length === 0) return { ...EMPTY };

  const flights: ItineraryItem[] = [];
  const roundTripFlights: ItineraryItem[] = [];
  const hotels: ItineraryItem[] = [];
  const attractions: AttractionSearchResult[] = [];
  const restaurants: RestaurantSearchResult[] = [];

  const seenFlight = new Set<string>();
  const seenHotel = new Set<string>();
  const seenAttraction = new Set<string>();
  const seenRestaurant = new Set<string>();

  for (const item of items) {
    // Candidates are trip-level rows (day_id = null).  Day-assigned items
    // are already rendered in the right-pane itinerary timeline.
    if (isDayAssigned(item)) continue;

    switch (item.itemType) {
      case "flight": {
        const key = flightDedupeKey(item);
        if (seenFlight.has(key)) continue;
        seenFlight.add(key);
        if (isRoundTripFlight(item)) roundTripFlights.push(item);
        else flights.push(item);
        break;
      }
      case "hotel": {
        const key = hotelDedupeKey(item);
        if (seenHotel.has(key)) continue;
        seenHotel.add(key);
        hotels.push(item);
        break;
      }
      case "activity": {
        const att = itemToAttraction(item);
        const key = activityDedupeKey(att.name, att.id);
        if (seenAttraction.has(key)) continue;
        seenAttraction.add(key);
        attractions.push(att);
        break;
      }
      case "meal": {
        const rest = itemToRestaurant(item);
        const key = mealDedupeKey(rest.name, rest.id);
        if (seenRestaurant.has(key)) continue;
        seenRestaurant.add(key);
        restaurants.push(rest);
        break;
      }
      default:
        // transit / note — not a candidate vertical
        break;
    }
  }

  flights.sort((a, b) => flightScore(b) - flightScore(a));
  roundTripFlights.sort((a, b) => flightScore(b) - flightScore(a));
  hotels.sort((a, b) => hotelScore(b) - hotelScore(a));
  attractions.sort((a, b) => (b.aiScore ?? 0) - (a.aiScore ?? 0));
  restaurants.sort((a, b) => (b.aiScore ?? 0) - (a.aiScore ?? 0));

  return {
    flights,
    roundTripFlights,
    hotels,
    attractions,
    restaurants,
    totals: {
      flights: flights.length,
      roundTripFlights: roundTripFlights.length,
      hotels: hotels.length,
      attractions: attractions.length,
      restaurants: restaurants.length,
    },
  };
}

/**
 * Merge Explore snapshot attractions/restaurants with persisted candidates.
 *
 * Precedence rule (Level 3 contract rescue):
 *   1. If persisted candidates exist for a vertical, they win.  An empty
 *      Explore snapshot CANNOT zero out persisted ACTIVITY/MEAL candidates.
 *   2. If persisted candidates are empty AND the snapshot has rows, fall
 *      back to the snapshot.  This preserves backwards compatibility for
 *      trips created before ``/trips/create-with-search`` seeded all four
 *      verticals.
 */
export function mergePersistedWithSnapshot(
  persisted: TripCandidateBuckets,
  snapshot: { attractions: AttractionSearchResult[]; restaurants: RestaurantSearchResult[] } | null,
): TripCandidateBuckets {
  if (!snapshot) return persisted;
  const attractions =
    persisted.attractions.length > 0 ? persisted.attractions : snapshot.attractions;
  const restaurants =
    persisted.restaurants.length > 0 ? persisted.restaurants : snapshot.restaurants;
  return {
    ...persisted,
    attractions,
    restaurants,
    totals: {
      ...persisted.totals,
      attractions: attractions.length,
      restaurants: restaurants.length,
    },
  };
}
