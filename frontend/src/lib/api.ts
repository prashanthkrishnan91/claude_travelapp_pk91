/**
 * API client for the Travel Concierge backend.
 *
 * - All responses are transformed from snake_case → camelCase.
 * - All request bodies are transformed from camelCase → snake_case.
 * - Auth via Supabase JWT: Authorization: Bearer <access_token>
 */

import type {
  Trip,
  TripContext,
  ItineraryDay,
  ItineraryItem,
  ItemType,
  TravelCard,
  DealItem,
  ResearchResult,
  ResearchCategory,
  TripBuilderFormData,
  CompareItemInput,
  CompareResult,
  BookingOption,
  FlightSearchResult,
  AttractionSearchResult,
  RestaurantSearchResult,
  DayPlan,
  OptimizeFlightInput,
  OptimizeHotelInput,
  TripOptimizationResponse,
  SavedItem,
  SavedItemCreate,
} from "@/types";
import { supabase } from "./supabase";
import { normalizeConciergeResponse } from "./concierge/types";
import {
  addDaysToIsoDate,
  computeExpectedTripDayCount,
  expectedDayNumbers,
  missingDayNumbers,
  normalizeIsoDate,
} from "./tripDays";

// ─── Config ──────────────────────────────────────────────────────────────────

/** Direct connection to FastAPI backend — no proxy, no rewrites. */
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";


async function getAuthHeader(): Promise<Record<string, string>> {
  const { data: { session } } = await supabase.auth.getSession();


  if (!session) {
    throw new Error("[auth] No active session — request blocked. User must be signed in.");
  }

  const token = session.access_token;
  if (!token) {
    console.error("[auth] Session exists but access_token is null/undefined — request blocked.");
    throw new Error("[auth] Missing access_token in session.");
  }


  const header = { Authorization: `Bearer ${token}` };
  return header;
}

// ─── Case transformers ────────────────────────────────────────────────────────

function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, ch) => ch.toUpperCase());
}

function camelToSnake(str: string): string {
  return str.replace(/[A-Z]/g, (ch) => `_${ch.toLowerCase()}`);
}

function transformKeys(obj: unknown, transform: (k: string) => string): unknown {
  if (Array.isArray(obj)) {
    return obj.map((item) => transformKeys(item, transform));
  }
  if (obj !== null && typeof obj === "object") {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([k, v]) => [
        transform(k),
        transformKeys(v, transform),
      ])
    );
  }
  return obj;
}

const toCamel = <T>(data: unknown): T =>
  transformKeys(data, snakeToCamel) as T;

const toSnake = <T>(data: unknown): T =>
  transformKeys(data, camelToSnake) as T;

// ─── Base fetcher ─────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_URL}${path}`;


  const authHeader = await getAuthHeader();

  const finalHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...authHeader,
    ...(options.headers as Record<string, string>),
  };


  const res = await fetch(url, {
    ...options,
    headers: finalHeaders,
    // Don't cache on the server so data is always fresh
    cache: "no-store",
  });


  if (res.status === 204) return null as T;

  if (!res.ok) {
    let detail: unknown = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      // ignore parse errors
    }
    // Structured errors (e.g. {code, message}) are surfaced as ApiError so
    // callers can branch on the code without string-matching.
    if (detail && typeof detail === "object") {
      const obj = detail as { code?: string; message?: string };
      const err = new Error(obj.message ?? `API error: ${res.status}`) as Error & {
        status?: number;
        code?: string;
        detail?: unknown;
      };
      err.status = res.status;
      err.code = obj.code;
      err.detail = detail;
      throw err;
    }
    const err = new Error(`API error: ${detail}`) as Error & {
      status?: number;
    };
    err.status = res.status;
    throw err;
  }

  const json = await res.json();
  return toCamel<T>(json);
}

// ─── Trips ────────────────────────────────────────────────────────────────────

export async function fetchTrips(): Promise<Trip[]> {
  try {
    return await apiFetch<Trip[]>("/trips");
  } catch {
    return [];
  }
}

export async function fetchTrip(id: string): Promise<Trip | null> {
  try {
    return await apiFetch<Trip>(`/trips/${id}`);
  } catch {
    return null;
  }
}

export async function createTrip(formData: TripBuilderFormData): Promise<Trip> {
  const payload = toSnake({
    title: formData.title,
    destination: formData.destination,
    origin: formData.origin || null,
    startDate: formData.startDate || null,
    endDate: formData.endDate || null,
    travelers: formData.travelers,
    budgetCash: formData.budgetCash ? Number(formData.budgetCash) : null,
    budgetCurrency: formData.budgetCurrency,
    notes: formData.notes || null,
    status: "draft",
  });

  return apiFetch<Trip>("/trips", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function createTripWithSearch(data: {
  originCity: string;
  originAirports: string[];
  destinationCity: string;
  destinationAirports: string[];
  startDate: string;
  endDate: string;
}): Promise<Trip> {
  const payload = {
    origin_city: data.originCity,
    origin_airports: data.originAirports,
    destination_city: data.destinationCity,
    destination_airports: data.destinationAirports,
    start_date: data.startDate,
    end_date: data.endDate,
  };
  return apiFetch<Trip>("/trips/create-with-search", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateTrip(
  id: string,
  patch: Partial<Trip>
): Promise<Trip> {
  const payload = toSnake(patch);
  return apiFetch<Trip>(`/trips/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteTrip(id: string): Promise<void> {
  await apiFetch<void>(`/trips/${id}`, { method: "DELETE" });
}

export async function fetchTripContext(tripId: string): Promise<TripContext | null> {
  try {
    return await apiFetch<TripContext>(`/context/trip/${tripId}`);
  } catch {
    return null;
  }
}

// ─── Itinerary ────────────────────────────────────────────────────────────────

/** Fetch all days for a trip, each with their items. */
export async function fetchItinerary(tripId: string): Promise<ItineraryDay[]> {
  try {
    const days = (await apiFetch<ItineraryDay[]>(`/itinerary/${tripId}/days`))
      .sort((a, b) => a.dayNumber - b.dayNumber);

    // Fetch items for every day in parallel
    const daysWithItems = await Promise.all(
      days.map(async (day) => {
        try {
          const items = await apiFetch<ItineraryItem[]>(
            `/itinerary/${tripId}/days/${day.id}/items`
          );
          return { ...day, items };
        } catch {
          return { ...day, items: [] };
        }
      })
    );

    return daysWithItems;
  } catch {
    return [];
  }
}

export async function ensureTripDays(
  tripId: string,
  startDate?: string,
  endDate?: string
): Promise<ItineraryDay[]> {
  const canonicalStart = normalizeIsoDate(startDate);
  const canonicalEnd = normalizeIsoDate(endDate);
  if (!canonicalStart || !canonicalEnd) return fetchItinerary(tripId);

  const expectedCount = computeExpectedTripDayCount(canonicalStart, canonicalEnd);
  if (expectedCount <= 0 || expectedCount > 90) return fetchItinerary(tripId);

  const days = await fetchItinerary(tripId);
  const expectedNumbers = expectedDayNumbers(canonicalStart, canonicalEnd);
  const actualNumbers = days.map((d) => d.dayNumber);
  const missingNumbers = missingDayNumbers(expectedNumbers, actualNumbers);

  for (const dayNumber of missingNumbers) {
    const date = addDaysToIsoDate(canonicalStart, dayNumber - 1);
    try {
      await createDay(tripId, { dayNumber, title: `Day ${dayNumber}`, date });
    } catch {
      // backend uniqueness/idempotency keeps this safe under concurrent callers
    }
  }

  for (const day of days) {
    if (!expectedNumbers.includes(day.dayNumber)) continue;
    const expectedDate = addDaysToIsoDate(canonicalStart, day.dayNumber - 1);
    if (normalizeIsoDate(day.date) === expectedDate) continue;
    try {
      await apiFetch<ItineraryDay>(`/itinerary/${tripId}/days/${day.id}`, {
        method: "PATCH",
        body: JSON.stringify(
          toSnake({
            date: expectedDate,
            title: day.title ?? `Day ${day.dayNumber}`,
          })
        ),
      });
    } catch {
      // fallback: server-side reconciliation still runs on trip updates
    }
  }

  return fetchItinerary(tripId);
}

export async function createDay(
  tripId: string,
  data: { dayNumber: number; title?: string; date?: string }
): Promise<ItineraryDay> {
  const payload = toSnake({ ...data, tripId });
  const day = await apiFetch<ItineraryDay>(`/itinerary/${tripId}/days`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return { ...day, items: [] };
}

export async function deleteDay(tripId: string, dayId: string): Promise<void> {
  await apiFetch<void>(`/itinerary/${tripId}/days/${dayId}`, {
    method: "DELETE",
  });
}

export async function createItem(
  tripId: string,
  dayId: string,
  data: {
    itemType: ItemType;
    title: string;
    description?: string;
    location?: string;
    position: number;
    bookingOptions?: BookingOption[];
  }
): Promise<ItineraryItem> {
  const { bookingOptions, ...rest } = data;
  const payload = toSnake({
    ...rest,
    tripId,
    dayId,
    ...(bookingOptions?.length ? { details: { bookingOptions } } : {}),
  });
  return apiFetch<ItineraryItem>(
    `/itinerary/${tripId}/days/${dayId}/items`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function fetchBookingLinks(itemId: string): Promise<BookingOption[]> {
  try {
    return await apiFetch<BookingOption[]>(`/itinerary/items/${itemId}/booking-links`);
  } catch {
    return [];
  }
}

export async function updateItem(
  itemId: string,
  patch: Partial<ItineraryItem>
): Promise<ItineraryItem> {
  const payload = toSnake(patch);
  return apiFetch<ItineraryItem>(`/itinerary/items/${itemId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteItem(itemId: string): Promise<void> {
  await apiFetch<void>(`/itinerary/items/${itemId}`, { method: "DELETE" });
}

export async function fetchTripItems(tripId: string): Promise<ItineraryItem[]> {
  try {
    return await apiFetch<ItineraryItem[]>(`/trips/${tripId}/items`);
  } catch {
    return [];
  }
}

export async function addFlightToTrip(
  tripId: string,
  flight: FlightSearchResult
): Promise<ItineraryItem> {
  const payload = toSnake({
    tripId,
    itemType: "flight",
    title: `${flight.airline} ${flight.flightNumber}`,
    startTime: flight.departureTime,
    endTime: flight.arrivalTime,
    cashPrice: flight.price,
    pointsPrice: flight.pointsCost,
    cppValue: flight.cpp,
    details: {
      airline: flight.airline,
      flightNumber: flight.flightNumber,
      origin: flight.origin,
      destination: flight.destination,
      departureTime: flight.departureTime,
      arrivalTime: flight.arrivalTime,
      durationMinutes: flight.durationMinutes,
      stops: flight.stops,
      cabinClass: flight.cabinClass,
      price: flight.price,
      pointsCost: flight.pointsCost,
      cpp: flight.cpp,
    },
  });
  return apiFetch<ItineraryItem>("/itinerary/items", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function addRoundTripOutboundToDay(
  tripId: string,
  dayId: string,
  outbound: Record<string, unknown>,
  position: number
): Promise<ItineraryItem> {
  // Leg data arrives camelCase (after toCamel transform); fall back to snake_case for old data
  const flightNum  = (outbound.flightNumber  ?? outbound.flight_number)  as string | undefined;
  const depTime    = (outbound.departureTime ?? outbound.departure_time) as string | undefined;
  const arrTime    = (outbound.arrivalTime   ?? outbound.arrival_time)   as string | undefined;
  const pointsCost = (outbound.pointsCost    ?? outbound.points_cost)    as number | undefined;
  const payload = toSnake({
    tripId,
    dayId,
    itemType: "flight",
    title: `${outbound.airline ?? ""} ${flightNum ?? ""} (Outbound)`.trim(),
    startTime: depTime,
    endTime: arrTime,
    cashPrice: outbound.price,
    pointsPrice: pointsCost,
    cppValue: outbound.cpp,
    position,
    details: { ...outbound, leg: "outbound" },
  });
  return apiFetch<ItineraryItem>("/itinerary/items", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function addRoundTripReturnToDay(
  tripId: string,
  dayId: string,
  returnFlight: Record<string, unknown>,
  position: number
): Promise<ItineraryItem> {
  // Leg data arrives camelCase (after toCamel transform); fall back to snake_case for old data
  const flightNum  = (returnFlight.flightNumber  ?? returnFlight.flight_number)  as string | undefined;
  const depTime    = (returnFlight.departureTime ?? returnFlight.departure_time) as string | undefined;
  const arrTime    = (returnFlight.arrivalTime   ?? returnFlight.arrival_time)   as string | undefined;
  const pointsCost = (returnFlight.pointsCost    ?? returnFlight.points_cost)    as number | undefined;
  const payload = toSnake({
    tripId,
    dayId,
    itemType: "flight",
    title: `${returnFlight.airline ?? ""} ${flightNum ?? ""} (Return)`.trim(),
    startTime: depTime,
    endTime: arrTime,
    cashPrice: returnFlight.price,
    pointsPrice: pointsCost,
    cppValue: returnFlight.cpp,
    position,
    details: { ...returnFlight, leg: "return" },
  });
  return apiFetch<ItineraryItem>("/itinerary/items", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function addOneWayFlightToDay(
  tripId: string,
  dayId: string,
  item: ItineraryItem,
  position: number
): Promise<ItineraryItem> {
  const d = (item.details ?? {}) as Record<string, unknown>;
  const flightNum  = ((d.flightNumber  ?? d.flight_number)  as string | undefined) ?? "";
  const airline    = (d.airline as string | undefined) ?? "";
  const depTime    = (d.departureTime ?? d.departure_time) as string | undefined;
  const arrTime    = (d.arrivalTime   ?? d.arrival_time)   as string | undefined;
  const pointsCost = ((d.pointsCost   ?? d.points_cost)    as number | undefined) ?? item.pointsPrice;
  const price      = (d.price as number | undefined) ?? item.cashPrice;
  const cpp        = (d.cpp as number | undefined);
  const payload = toSnake({
    tripId,
    dayId,
    itemType: "flight",
    title: `${airline} ${flightNum}`.trim() || item.title,
    startTime: depTime,
    endTime: arrTime,
    cashPrice: price,
    pointsPrice: pointsCost,
    cppValue: cpp,
    position,
    details: { ...d },
  });
  return apiFetch<ItineraryItem>("/itinerary/items", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Add a hotel candidate to a specific itinerary day, preserving all stored details. */
export async function addHotelToDay(
  tripId: string,
  dayId: string,
  item: ItineraryItem,
  position: number
): Promise<ItineraryItem> {
  const d = (item.details ?? {}) as Record<string, unknown>;
  const payload = {
    trip_id: tripId,
    day_id: dayId,
    item_type: "hotel",
    title: item.title,
    location: item.location ?? undefined,
    position,
    details: { ...d },
  };
  return apiFetch<ItineraryItem>("/itinerary/items", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function addHotelToTrip(
  tripId: string,
  hotel: ResearchResult
): Promise<ItineraryItem> {
  const meta = (hotel.metadata ?? {}) as Record<string, unknown>;
  const pricePerNight = typeof meta.pricePerNight === "number" ? meta.pricePerNight : null;
  const details: Record<string, unknown> = {
    name: hotel.title,
    location: hotel.location ?? null,
    price_per_night: pricePerNight,
    rating: hotel.rating ?? null,
    amenities: Array.isArray(meta.amenities) ? meta.amenities : [],
    stars: typeof meta.stars === "number" ? meta.stars : null,
    booking_url: hotel.bookingUrl ?? null,
    lat: typeof meta.lat === "number" ? meta.lat : null,
    lng: typeof meta.lng === "number" ? meta.lng : null,
    location_score: typeof meta.locationScore === "number" ? meta.locationScore : null,
    proximity_label: typeof meta.proximityLabel === "string" ? meta.proximityLabel : null,
    area_label: typeof meta.areaLabel === "string" ? meta.areaLabel : null,
  };
  // Remove null entries to keep metadata flat and clean
  const cleanDetails = Object.fromEntries(
    Object.entries(details).filter(([, v]) => v !== null)
  );
  const payload: Record<string, unknown> = {
    trip_id: tripId,
    item_type: "hotel",
    title: hotel.title,
  };
  if (hotel.location) payload.location = hotel.location;
  if (pricePerNight !== null) payload.cash_price = pricePerNight;
  if (Object.keys(cleanDetails).length > 0) payload.details = cleanDetails;

  console.log("[addHotelToTrip] payload:", JSON.stringify(payload));
  return apiFetch<ItineraryItem>("/itinerary/items", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ─── Airport Resolver ────────────────────────────────────────────────────────

export interface AirportMatch {
  city: string;
  country: string;
  airports: string[];
}

export interface AirportResolveResponse {
  matches: AirportMatch[];
}

export async function resolveAirports(query: string): Promise<AirportResolveResponse> {
  return apiFetch<AirportResolveResponse>("/resolve/airports", {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}

// ─── Flight Search ────────────────────────────────────────────────────────────

/**
 * Product Surface Pruning v1A — legacy mock-backed product route.
 * Calls `POST /search/flights`, which is currently fed by
 * `_mock_flights` in the backend `SearchService`.  The
 * `BLOCK_LEGACY_PRODUCT_MOCK` env flag will short-circuit the backend to an
 * empty list; do **not** add new callers of this function.  The v1B
 * migration plan (see `docs/ai/HANDOFF.md`) replaces this with a real
 * provider or routes the call through the canonical AI Concierge surface.
 */
export async function searchFlights(
  origin: string | string[],
  destination: string | string[],
  departureDate: string
): Promise<FlightSearchResult[]> {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(departureDate)) {
    throw new Error(`Invalid departure_date: "${departureDate}" — must be YYYY-MM-DD`);
  }

  const originCodes = (Array.isArray(origin) ? origin : [origin.trim().toUpperCase()]).map((c) => c.trim().toUpperCase());
  const destCodes = (Array.isArray(destination) ? destination : [destination.trim().toUpperCase()]).map((c) => c.trim().toUpperCase());

  for (const code of [...originCodes, ...destCodes]) {
    if (!/^[A-Z]{3}$/.test(code)) {
      throw new Error(`Invalid airport code: "${code}" — must be a 3-letter IATA code`);
    }
  }

  const payload =
    originCodes.length === 1 && destCodes.length === 1
      ? {
          origin: originCodes[0],
          destination: destCodes[0],
          departure_date: departureDate,
          passengers: 1,
          cabin_class: "economy",
        }
      : {
          origin_airports: originCodes,
          destination_airports: destCodes,
          departure_date: departureDate,
          passengers: 1,
          cabin_class: "economy",
        };

  console.log("[searchFlights] payload:", JSON.stringify(payload));

  return apiFetch<FlightSearchResult[]>("/search/flights", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ─── Explore Flights (canonical live provider) ───────────────────────────────

export interface FlightExploreRequest {
  origin: string;
  destination: string;
  departureDate: string;      // YYYY-MM-DD
  returnDate?: string;        // YYYY-MM-DD; omit for one-way
  passengers: number;
  cabinClass: "economy" | "premium_economy" | "business" | "first";
  originAirports?: string[];        // multi-airport city group; city-group token used when > 1
  destinationAirports?: string[];   // multi-airport city group; city-group token used when > 1
}

export type FlightExploreStatus = "ok" | "empty" | "unavailable" | "error";

export interface FlightExploreResponse {
  status: FlightExploreStatus;
  offers: import("@/components/explore/types").FlightItineraryOffer[];
  reason?: string | null;
}

/**
 * Live flight search via POST /explore/flights (canonical provider-neutral route).
 *
 * Returns { status, offers } where status drives the UI state:
 * - "ok"          → render flight cards
 * - "empty"       → no results found
 * - "unavailable" → provider not configured (polished unavailable state)
 * - "error"       → provider error (polished error state)
 *
 * Provider key (IGNAV_API_KEY) is server-side only; never exposed to the frontend.
 */
export async function searchFlightsExplore(
  req: FlightExploreRequest
): Promise<FlightExploreResponse> {
  const body: Record<string, unknown> = {
    origin: req.origin.trim().toUpperCase(),
    destination: req.destination.trim().toUpperCase(),
    departure_date: req.departureDate,
    passengers: req.passengers,
    cabin_class: req.cabinClass,
  };
  if (req.returnDate) {
    body["return_date"] = req.returnDate;
  }
  if (req.originAirports && req.originAirports.length > 1) {
    body["origin_airports"] = req.originAirports.map((c) => c.toUpperCase());
  }
  if (req.destinationAirports && req.destinationAirports.length > 1) {
    body["destination_airports"] = req.destinationAirports.map((c) => c.toUpperCase());
  }
  return apiFetch<FlightExploreResponse>("/explore/flights", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ─── Search / Research ────────────────────────────────────────────────────────

interface RawHotelResult {
  id: string;
  name: string;
  pricePerNight: number;
  rating?: number;
  location: string;
  amenities: string[];
  stars?: number;
  bookingUrl?: string;
  bookingOptions?: BookingOption[];
  lat?: number;
  lng?: number;
  locationScore?: number;
  proximityLabel?: string;
  areaLabel?: string;
  distanceToBestArea?: number;
  // Hotels Product Contract v1 surface markers.
  source?: string;
  offerKind?: string; // "discovery" | "bookable_offer"
  hasRealRate?: boolean;
}

function mapHotelToResult(h: RawHotelResult): ResearchResult {
  // Discovery-only rows (e.g. Google Places lodging) carry no real
  // nightly rate.  Suppress fake ``$0/night`` strings so the UI never
  // shows fabricated pricing copy.
  const hasRealRate = h.hasRealRate === true;
  const showsRate = hasRealRate && typeof h.pricePerNight === "number" && h.pricePerNight > 0;
  return {
    id: h.id,
    category: "hotel" as ResearchCategory,
    title: h.name,
    location: h.location,
    duration: "Per night",
    priceDisplay: showsRate ? `$${h.pricePerNight}/night` : undefined,
    rating: h.rating,
    tags: (h.amenities ?? []).slice(0, 3),
    bookingUrl: h.bookingUrl,
    bookingOptions: h.bookingOptions,
    metadata: {
      pricePerNight: h.pricePerNight,
      amenities: h.amenities ?? [],
      stars: h.stars,
      lat: h.lat,
      lng: h.lng,
      locationScore: h.locationScore,
      proximityLabel: h.proximityLabel,
      areaLabel: h.areaLabel,
      distanceToBestArea: h.distanceToBestArea,
      source: h.source,
      offerKind: h.offerKind,
      hasRealRate,
    },
  };
}

/**
 * Fetch hotels for a destination and date range.
 *
 * Product Surface Pruning v1A — legacy mock-backed product route.  Calls
 * `POST /search/hotels`, fed by `_mock_hotels`.  Honors the
 * `BLOCK_LEGACY_PRODUCT_MOCK` env flag.  Do not add new callers.
 */
export async function searchHotels(
  location: string,
  checkIn: string,
  checkOut: string,
  guests: number
): Promise<ResearchResult[]> {
  try {
    const payload = toSnake({ location, checkIn, checkOut, guests });
    const results = await apiFetch<RawHotelResult[]>("/search/hotels", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return results.map(mapHotelToResult);
  } catch {
    return [];
  }
}

interface RawRestaurantResult {
  id: string;
  name: string;
  cuisine: string;
  location: string;
  address: string;
  rating?: number;
  numReviews?: number;
  price?: number;
  priceLevel?: number;
  openingHours?: string;
  aiScore?: number;
  ai_score?: number;
  score?: number;
  sentiment?: number;
  tags?: string[];
  bookingUrl?: string;
  bookingOptions?: BookingOption[];
  provider_place_id?: string;
  providerPlaceId?: string;
  google_place_id?: string;
  googlePlaceId?: string;
  google_maps_uri?: string;
  googleMapsUri?: string;
  place_id?: string;
  placeId?: string;
  formatted_address?: string;
  formattedAddress?: string;
  user_ratings_total?: number;
  userRatingsTotal?: number;
  review_count?: number;
  reviewCount?: number;
  source?: string;
  source_status?: string;
  sourceStatus?: string;
  cache_status?: string;
  cacheStatus?: string;
  verification_status?: string;
  verificationStatus?: string;
}

function extractVerifiedRestaurantIdentity(r: RawRestaurantResult): {
  providerPlaceId?: string;
  googleMapsUri?: string;
  placeId?: string;
} {
  const providerPlaceId = typeof r.providerPlaceId === "string" ? r.providerPlaceId : typeof r.provider_place_id === "string" ? r.provider_place_id : undefined;
  const googlePlaceId = typeof r.googlePlaceId === "string" ? r.googlePlaceId : typeof r.google_place_id === "string" ? r.google_place_id : undefined;
  const googleMapsUri = typeof r.googleMapsUri === "string" ? r.googleMapsUri : typeof r.google_maps_uri === "string" ? r.google_maps_uri : undefined;
  const placeId = typeof r.placeId === "string" ? r.placeId : typeof r.place_id === "string" ? r.place_id : undefined;
  return { providerPlaceId: providerPlaceId ?? googlePlaceId, googleMapsUri, placeId: placeId ?? googlePlaceId };
}

function mapRestaurantToResult(r: RawRestaurantResult): RestaurantSearchResult {
  const normalizedAiScore =
    typeof r.aiScore === "number"
      ? r.aiScore
      : typeof r.ai_score === "number"
        ? r.ai_score
        : typeof r.score === "number"
          ? r.score
          : undefined;
  const identity = extractVerifiedRestaurantIdentity(r);
  return {
    id: r.id,
    name: r.name,
    cuisine: r.cuisine,
    location: r.location,
    address: typeof r.address === "string" && r.address.trim().length > 0
      ? r.address
      : typeof r.formattedAddress === "string"
        ? r.formattedAddress
        : typeof r.formatted_address === "string"
          ? r.formatted_address
          : "",
    rating: r.rating,
    numReviews: typeof r.numReviews === "number"
      ? r.numReviews
      : typeof r.reviewCount === "number"
        ? r.reviewCount
        : typeof r.review_count === "number"
          ? r.review_count
          : typeof r.userRatingsTotal === "number"
            ? r.userRatingsTotal
            : typeof r.user_ratings_total === "number"
              ? r.user_ratings_total
              : undefined,
    price: r.price,
    priceLevel: r.priceLevel,
    openingHours: r.openingHours,
    aiScore: normalizedAiScore,
    sentiment: r.sentiment,
    tags: r.tags ?? [],
    bookingUrl: r.bookingUrl,
    bookingOptions: r.bookingOptions,
    providerPlaceId: identity.providerPlaceId,
    googleMapsUri: identity.googleMapsUri,
    placeId: identity.placeId,
  };
}

/** Fetch restaurants and dining options for a location, sorted by AI score DESC. */
export interface RestaurantSearchEnvelope {
  restaurants: RestaurantSearchResult[];
  sourceStatus: string;
  cacheStatus: string;
  terminalNoResults: boolean;
}

export async function searchRestaurants(
  location: string,
  date?: string
): Promise<RestaurantSearchEnvelope> {
  try {
    const payload = toSnake({ location, date: date ?? null });
    const results = await apiFetch<RawRestaurantResult[]>("/search/restaurants", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    // Safety net: reject mock/demo/fallback restaurants before the verified filter.
    // source="mock" or providerPlaceId starting with "mock-" indicates backend mock data.
    const nonMockRaw = results.filter((r) => r.source !== "mock");
    const mapped = nonMockRaw.map(mapRestaurantToResult);
    const verified = mapped.filter((r) => {
      const pId = r.providerPlaceId ?? "";
      return !pId.startsWith("mock-") && Boolean(r.googleMapsUri || r.providerPlaceId || r.placeId);
    });
    const sourceStatus = String((results[0] as RawRestaurantResult | undefined)?.source_status ?? "ok");
    const cacheStatus = String((results[0] as RawRestaurantResult | undefined)?.cache_status ?? "unknown");
    const terminalNoResults = verified.length === 0 && sourceStatus === "terminal_no_results";
    console.info("[explore_restaurants_mapper] input=%d drop_mock=%d mapped=%d drop_unverified=%d source_status=%s cache_status=%s", results.length, results.length-nonMockRaw.length, mapped.length, mapped.length-verified.length, sourceStatus, cacheStatus);
    return { restaurants: verified, sourceStatus, cacheStatus, terminalNoResults };
  } catch {
    return { restaurants: [], sourceStatus: "error", cacheStatus: "bypass", terminalNoResults: false };
  }
}

// ─── Explore candidate snapshots ─────────────────────────────────────────────

export interface ExploreSnapshot {
  destination: string;
  createdAt: string;
  attractions: AttractionSearchResult[];
  restaurants: RestaurantSearchResult[];
  restaurantStatus?: string;
}

/**
 * Deterministic attraction score mirroring backend _compute_attraction_ai_score.
 * Used to enrich stale snapshot candidates that have rating/numReviews but no aiScore.
 */
export function computeExploreAttractionScore(
  rating: number,
  numReviews: number,
  category: string
): number {
  const ratingScore = (rating / 5.0) * 100;
  const reviewScore = Math.min(100.0, (Math.log1p(numReviews) / Math.log1p(500_000)) * 100);
  const popularity = ratingScore * 0.6 + reviewScore * 0.4;
  const uniquenessBonus = category === "hidden_gems" || category === "local_favorites" ? 8.0 : 0.0;
  const raw = popularity * 0.9 + uniquenessBonus * 0.1;
  return Math.round(Math.min(100.0, Math.max(0.0, raw)) * 10) / 10;
}

/**
 * Deterministic restaurant score mirroring backend _compute_restaurant_ai_score.
 * Used to enrich stale snapshot candidates that have rating/numReviews but no aiScore.
 */
export function computeExploreRestaurantScore(
  rating: number,
  numReviews: number,
  priceLevel: number,
  sentiment?: number
): number {
  const ratingScore = (rating / 5.0) * 100;
  const reviewScore = Math.min(100.0, (Math.log1p(numReviews) / Math.log1p(500_000)) * 100);
  const priceValue = Math.max(0.0, ((4 - priceLevel) / 4.0) * 100);
  let raw: number;
  if (sentiment != null) {
    raw = ratingScore * 0.4 + reviewScore * 0.3 + priceValue * 0.15 + sentiment * 100 * 0.15;
  } else {
    raw = ratingScore * 0.45 + reviewScore * 0.35 + priceValue * 0.2;
  }
  return Math.round(Math.min(100.0, Math.max(0.0, raw)) * 10) / 10;
}

/**
 * Fetch the persisted Explore candidate snapshot for a trip.
 * Returns null when no snapshot exists or on network/auth failure.
 * Snapshot is keyed per-trip in trips.metadata.explore_snapshot.
 * Enriches stale candidates (ai_score=null) with deterministic scoring when rating data is present.
 */
export async function fetchExploreSnapshot(tripId: string): Promise<ExploreSnapshot | null> {
  try {
    const data = await apiFetch<Record<string, unknown> | null>(`/trips/${tripId}/explore-snapshot`);
    if (!data) return null;
    const rawAttractions = Array.isArray(data.attractions) ? (data.attractions as Record<string, unknown>[]) : [];
    const rawRestaurants = Array.isArray(data.restaurants) ? (data.restaurants as Record<string, unknown>[]) : [];
    if (rawAttractions.length === 0 && rawRestaurants.length === 0) return null;
    const attractions: AttractionSearchResult[] = rawAttractions.map((a) => {
      const storedScore =
        typeof a.aiScore === "number" && a.aiScore > 0
          ? a.aiScore
          : typeof a.ai_score === "number" && a.ai_score > 0
            ? a.ai_score
            : typeof a.score === "number" && a.score > 0
              ? a.score
          : undefined;
      const computedScore =
        storedScore == null &&
        typeof a.rating === "number" &&
        typeof (a.numReviews ?? a.num_reviews) === "number" &&
        Number(a.numReviews ?? a.num_reviews) > 0
          ? computeExploreAttractionScore(a.rating, Number(a.numReviews ?? a.num_reviews), String(a.category ?? ""))
          : undefined;
      const aiScore = storedScore ?? (computedScore != null && computedScore > 0 ? computedScore : undefined);
      return {
        id: String(a.id ?? ""),
        name: String(a.name ?? ""),
        category: String(a.category ?? "attraction"),
        description: String(a.description ?? ""),
        location: String(a.location ?? ""),
        address: String(a.address ?? ""),
        rating: typeof a.rating === "number" ? a.rating : undefined,
        numReviews: typeof a.numReviews === "number" ? a.numReviews : typeof a.num_reviews === "number" ? a.num_reviews : undefined,
        priceLevel: typeof a.priceLevel === "number" ? a.priceLevel : typeof a.price_level === "number" ? a.price_level : undefined,
        openingHours: typeof a.openingHours === "string" ? a.openingHours : typeof a.opening_hours === "string" ? a.opening_hours : undefined,
        durationMinutes: typeof a.durationMinutes === "number" ? a.durationMinutes : typeof a.duration_minutes === "number" ? a.duration_minutes : undefined,
        aiScore,
        tags: Array.isArray(a.tags) ? (a.tags as string[]) : [],
        bookingUrl: typeof a.bookingUrl === "string" ? a.bookingUrl : typeof a.booking_url === "string" ? a.booking_url : undefined,
        lat: typeof a.lat === "number" ? a.lat : undefined,
        lng: typeof a.lng === "number" ? a.lng : undefined,
      };
    });
    const restaurants = rawRestaurants.map((r): RestaurantSearchResult | null => {
      const storedScore =
        typeof r.aiScore === "number" && r.aiScore > 0
          ? r.aiScore
          : typeof r.ai_score === "number" && r.ai_score > 0
            ? r.ai_score
            : typeof r.score === "number" && r.score > 0
              ? r.score
          : undefined;
      const sentiment = typeof r.sentiment === "number" ? r.sentiment : undefined;
      const computedScore =
        storedScore == null &&
        typeof r.rating === "number" &&
        typeof (r.numReviews ?? r.num_reviews) === "number" &&
        Number(r.numReviews ?? r.num_reviews) > 0
          ? computeExploreRestaurantScore(
              r.rating,
              Number(r.numReviews ?? r.num_reviews),
              typeof r.priceLevel === "number" ? r.priceLevel : 2,
              sentiment
            )
          : undefined;
      const aiScore = storedScore ?? (computedScore != null && computedScore > 0 ? computedScore : undefined);
      const providerPlaceId =
        typeof r.providerPlaceId === "string" ? r.providerPlaceId :
        typeof r.provider_place_id === "string" ? r.provider_place_id :
        typeof r.googlePlaceId === "string" ? r.googlePlaceId :
        typeof r.google_place_id === "string" ? r.google_place_id : undefined;
      const googleMapsUri = typeof r.googleMapsUri === "string" ? r.googleMapsUri : typeof r.google_maps_uri === "string" ? r.google_maps_uri : undefined;
      const placeId =
        typeof r.placeId === "string" ? r.placeId :
        typeof r.place_id === "string" ? r.place_id :
        typeof r.googlePlaceId === "string" ? r.googlePlaceId :
        typeof r.google_place_id === "string" ? r.google_place_id : undefined;
      // Quarantine: stale mock snapshot entries have providerPlaceId starting with "mock-".
      // These must not hydrate into visible restaurant cards.
      const isMockEntry =
        (typeof providerPlaceId === "string" && providerPlaceId.startsWith("mock-")) ||
        (typeof r.source === "string" && r.source === "mock");
      if (isMockEntry) return null;
      if (!googleMapsUri && !providerPlaceId && !placeId) return null;
      return {
        id: String(r.id ?? ""),
        name: String(r.name ?? ""),
        cuisine: String(r.cuisine ?? "Restaurant"),
        location: String(r.location ?? ""),
        address:
          typeof r.address === "string" && r.address.trim().length > 0
            ? r.address
            : String(r.formattedAddress ?? r.formatted_address ?? ""),
        rating: typeof r.rating === "number" ? r.rating : undefined,
        numReviews:
          typeof r.numReviews === "number" ? r.numReviews :
          typeof r.num_reviews === "number" ? r.num_reviews :
          typeof r.reviewCount === "number" ? r.reviewCount :
          typeof r.review_count === "number" ? r.review_count :
          typeof r.userRatingsTotal === "number" ? r.userRatingsTotal :
          typeof r.user_ratings_total === "number" ? r.user_ratings_total : undefined,
        priceLevel: typeof r.priceLevel === "number" ? r.priceLevel : typeof r.price_level === "number" ? r.price_level : undefined,
        openingHours: typeof r.openingHours === "string" ? r.openingHours : typeof r.opening_hours === "string" ? r.opening_hours : undefined,
        aiScore,
        sentiment,
        tags: Array.isArray(r.tags) ? (r.tags as string[]) : [],
        bookingUrl: typeof r.bookingUrl === "string" ? r.bookingUrl : typeof r.booking_url === "string" ? r.booking_url : undefined,
        lat: typeof r.lat === "number" ? r.lat : undefined,
        lng: typeof r.lng === "number" ? r.lng : undefined,
        providerPlaceId,
        googleMapsUri,
        placeId,
      };
    }).filter((r): r is RestaurantSearchResult => r !== null);
    return {
      destination: String(data.destination ?? ""),
      createdAt: String(data.createdAt ?? ""),
      attractions,
      restaurants,
      restaurantStatus: String(data.restaurant_status ?? "unknown"),
    };
  } catch {
    return null;
  }
}

/**
 * Persist scored Explore candidates for a trip.
 * Snapshot is stored in trips.metadata.explore_snapshot.
 * Enriches candidates missing aiScore using deterministic scoring before saving.
 * Failure is non-fatal — next load will call provider search again.
 */
export async function saveExploreSnapshot(
  tripId: string,
  snapshot: { destination: string; attractions: AttractionSearchResult[]; restaurants: RestaurantSearchResult[]; restaurantStatus?: string }
): Promise<void> {
  try {
    const body = {
      destination: snapshot.destination,
      created_at: new Date().toISOString(),
      attractions: snapshot.attractions.map((a) => {
        let aiScore = a.aiScore != null && a.aiScore > 0 ? a.aiScore : null;
        if (aiScore == null && a.rating != null && a.numReviews != null && a.numReviews > 0) {
          const computed = computeExploreAttractionScore(a.rating, a.numReviews, a.category ?? "");
          aiScore = computed > 0 ? computed : null;
        }
        return {
          id: a.id,
          name: a.name,
          category: a.category,
          description: a.description ?? "",
          location: a.location,
          address: a.address,
          rating: a.rating ?? null,
          num_reviews: a.numReviews ?? null,
          price_level: a.priceLevel ?? null,
          opening_hours: a.openingHours ?? null,
          duration_minutes: a.durationMinutes ?? null,
          ai_score: aiScore,
          tags: a.tags ?? [],
          booking_url: a.bookingUrl ?? null,
          lat: a.lat ?? null,
          lng: a.lng ?? null,
        };
      }),
      restaurant_status: snapshot.restaurantStatus ?? "unknown",
      restaurants: snapshot.restaurants
        .filter((r) => !r.providerPlaceId?.startsWith("mock-"))
        .map((r) => {
        let aiScore = r.aiScore != null && r.aiScore > 0 ? r.aiScore : null;
        if (aiScore == null && r.rating != null && r.numReviews != null && r.numReviews > 0) {
          const computed = computeExploreRestaurantScore(
            r.rating,
            r.numReviews,
            r.priceLevel ?? 2,
            r.sentiment
          );
          aiScore = computed > 0 ? computed : null;
        }
        return {
          id: r.id,
          name: r.name,
          cuisine: r.cuisine,
          location: r.location,
          address: r.address,
          rating: r.rating ?? null,
          num_reviews: r.numReviews ?? null,
          price_level: r.priceLevel ?? null,
          opening_hours: r.openingHours ?? null,
          ai_score: aiScore,
          sentiment: r.sentiment ?? null,
          tags: r.tags ?? [],
          booking_url: r.bookingUrl ?? null,
          lat: r.lat ?? null,
          lng: r.lng ?? null,
          provider_place_id: r.providerPlaceId ?? r.placeId ?? null,
          google_maps_uri: r.googleMapsUri ?? null,
          place_id: r.placeId ?? null,
        };
      }),
    };
    await apiFetch(`/trips/${tripId}/explore-snapshot`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  } catch {
    // Non-fatal: next load will call provider search again
  }
}

/** Add a restaurant to the itinerary as a trip-level meal item. */
export async function addRestaurantToTrip(
  tripId: string,
  restaurant: RestaurantSearchResult
): Promise<ItineraryItem> {
  const payload = {
    trip_id: tripId,
    item_type: "meal",
    title: restaurant.name,
    location: restaurant.address || restaurant.location,
    details: {
      name: restaurant.name,
      cuisine: restaurant.cuisine,
      location: restaurant.location,
      address: restaurant.address,
      rating: restaurant.rating ?? null,
      num_reviews: restaurant.numReviews ?? null,
      ai_score: restaurant.aiScore ?? null,
      tags: restaurant.tags,
      price_level: restaurant.priceLevel ?? null,
      opening_hours: restaurant.openingHours ?? null,
      booking_url: restaurant.bookingUrl ?? null,
      lat: restaurant.lat ?? null,
      lng: restaurant.lng ?? null,
    },
  };
  return apiFetch<ItineraryItem>("/itinerary/items", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Fetch a smart day plan (2–3 attractions + lunch + dinner) for a specific trip day. */
export async function fetchDayPlan(tripId: string, dayNumber: number): Promise<DayPlan> {
  const payload = toSnake({ tripId, dayNumber });
  return apiFetch<DayPlan>("/plan/day", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Add an attraction to a specific itinerary day with full metadata. */
export async function addAttractionToDay(
  tripId: string,
  dayId: string,
  attraction: AttractionSearchResult
): Promise<ItineraryItem> {
  const payload = {
    trip_id: tripId,
    day_id: dayId,
    item_type: "activity",
    title: attraction.name,
    location: attraction.address || attraction.location,
    details: {
      name: attraction.name,
      location: attraction.location,
      address: attraction.address,
      rating: attraction.rating ?? null,
      num_reviews: attraction.numReviews ?? null,
      ai_score: attraction.aiScore ?? null,
      tags: attraction.tags,
      category: attraction.category,
      description: attraction.description,
      opening_hours: attraction.openingHours ?? null,
      price_level: attraction.priceLevel ?? null,
      booking_url: attraction.bookingUrl ?? null,
      lat: attraction.lat ?? null,
      lng: attraction.lng ?? null,
    },
  };
  return apiFetch<ItineraryItem>("/itinerary/items", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Add a restaurant to a specific itinerary day with full metadata. */
export async function addRestaurantToDay(
  tripId: string,
  dayId: string,
  restaurant: RestaurantSearchResult
): Promise<ItineraryItem> {
  const payload = {
    trip_id: tripId,
    day_id: dayId,
    item_type: "meal",
    title: restaurant.name,
    location: restaurant.address || restaurant.location,
    details: {
      name: restaurant.name,
      cuisine: restaurant.cuisine,
      location: restaurant.location,
      address: restaurant.address,
      rating: restaurant.rating ?? null,
      num_reviews: restaurant.numReviews ?? null,
      ai_score: restaurant.aiScore ?? null,
      tags: restaurant.tags,
      price_level: restaurant.priceLevel ?? null,
      opening_hours: restaurant.openingHours ?? null,
      booking_url: restaurant.bookingUrl ?? null,
      lat: restaurant.lat ?? null,
      lng: restaurant.lng ?? null,
    },
  };
  return apiFetch<ItineraryItem>("/itinerary/items", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Add an attraction to the itinerary as a trip-level activity item. */
export async function addAttractionToTrip(
  tripId: string,
  attraction: AttractionSearchResult
): Promise<ItineraryItem> {
  const payload = {
    trip_id: tripId,
    item_type: "activity",
    title: attraction.name,
    location: attraction.address || attraction.location,
    details: {
      name: attraction.name,
      location: attraction.location,
      address: attraction.address,
      rating: attraction.rating ?? null,
      num_reviews: attraction.numReviews ?? null,
      ai_score: attraction.aiScore ?? null,
      tags: attraction.tags,
      category: attraction.category,
      description: attraction.description,
      opening_hours: attraction.openingHours ?? null,
      price_level: attraction.priceLevel ?? null,
      booking_url: attraction.bookingUrl ?? null,
      lat: attraction.lat ?? null,
      lng: attraction.lng ?? null,
    },
  };
  return apiFetch<ItineraryItem>("/itinerary/items", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ─── Compare ─────────────────────────────────────────────────────────────────

export async function compareItems(items: CompareItemInput[]): Promise<CompareResult[]> {
  const payload = toSnake({ items });
  const response = await apiFetch<{ results: CompareResult[] }>("/compare", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.results;
}

// ─── Dashboard Summary ────────────────────────────────────────────────────────

export interface DashboardSummary {
  tripCount: number;
  cardCount: number;
  itineraryCount: number;
}

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  try {
    const data = await apiFetch<DashboardSummary>("/dashboard/summary");
    console.log("[dashboard] summary response:", data);
    return data;
  } catch (err) {
    console.error("[dashboard] failed to fetch summary:", err);
    return { tripCount: 0, cardCount: 0, itineraryCount: 0 };
  }
}

// ─── Deals Feed ───────────────────────────────────────────────────────────────

export async function fetchDealsFeed(): Promise<DealItem[]> {
  try {
    const response = await apiFetch<{ deals: DealItem[] }>("/deals");
    return response.deals;
  } catch {
    return [];
  }
}

// ─── Travel Cards ─────────────────────────────────────────────────────────────

export async function fetchCards(): Promise<TravelCard[]> {
  try {
    return await apiFetch<TravelCard[]>("/cards");
  } catch {
    return [];
  }
}

export interface CreateCardData {
  cardKey: string;
  displayName: string;
  issuer: string;
  pointsBalance?: number;
  pointValueCpp?: number;
  isPrimary?: boolean;
}

export async function createCard(data: CreateCardData): Promise<TravelCard> {
  const payload = toSnake({
    ...data,
    currency: "USD",
    pointsBalance: data.pointsBalance ?? 0,
    isPrimary: data.isPrimary ?? false,
  });
  return apiFetch<TravelCard>("/cards", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface UpdateCardData {
  displayName?: string;
  issuer?: string;
  pointsBalance?: number;
  pointValueCpp?: number;
  isPrimary?: boolean;
}

export async function updateCard(cardId: string, data: UpdateCardData): Promise<TravelCard> {
  const payload = toSnake(data);
  return apiFetch<TravelCard>(`/cards/${cardId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

// ─── Trip Optimization ────────────────────────────────────────────────────────

export async function optimizeTrip(
  flights: OptimizeFlightInput[],
  hotels: OptimizeHotelInput[]
): Promise<TripOptimizationResponse> {
  const payload = toSnake({ flights, hotels });
  return apiFetch<TripOptimizationResponse>("/optimize/trip", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function addOptimizedFlightToDay(
  tripId: string,
  dayId: string,
  flight: OptimizeFlightInput
): Promise<ItineraryItem> {
  const payload = toSnake({
    tripId,
    dayId,
    itemType: "flight" as ItemType,
    title: `${flight.airline} ${flight.flightNumber}`,
    cashPrice: flight.price,
    pointsPrice: flight.pointsCost,
    position: 0,
    details: {
      airline: flight.airline,
      flightNumber: flight.flightNumber,
      durationMinutes: flight.durationMinutes,
      stops: flight.stops,
      cabinClass: flight.cabinClass,
      price: flight.price,
      pointsCost: flight.pointsCost,
      cpp: flight.cpp,
      decision: flight.decision,
      tags: flight.tags,
    },
  });
  return apiFetch<ItineraryItem>(`/itinerary/${tripId}/days/${dayId}/items`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function addOptimizedHotelToTrip(
  tripId: string,
  hotel: OptimizeHotelInput
): Promise<ItineraryItem> {
  const payload: Record<string, unknown> = {
    trip_id: tripId,
    item_type: "hotel",
    title: hotel.name,
    cash_price: hotel.pricePerNight,
    ...(hotel.pointsEstimate > 0 ? { points_price: hotel.pointsEstimate } : {}),
    details: {
      name: hotel.name,
      price: hotel.price,
      price_per_night: hotel.pricePerNight,
      nights: hotel.nights,
      rating: hotel.rating ?? null,
      stars: hotel.stars ?? null,
      location_score: hotel.locationScore ?? null,
      area_label: hotel.areaLabel ?? null,
    },
  };
  return apiFetch<ItineraryItem>("/itinerary/items", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ─── AI Concierge ─────────────────────────────────────────────────────────────

export interface ConciergeDisplayFields {
  displayName: string;
  displayCategory: string;
  displayMetaLine?: string | null;
  displayWhy: string;
  displaySourceSummary?: string | null;
  displayBadges: string[];
  addability: "addable" | "research_only" | "closed";
  /** Google-backed price display string ("$$", "$10–20", "Free"). Null when unavailable. */
  displayPrice?: string | null;
  /** True only when displayWhy was produced by the LLM/evidence-grounded path and passed the
   *  claim-safety reviewer. Frontend must NOT render a Concierge Note block when false/absent. */
  displayWhyValidated?: boolean | null;
}

export interface ConciergeSuggestion {
  type: "attraction" | "restaurant";
  name: string;
  reason: string;
}

export interface ConciergeResult {
  response: string;
  suggestions: ConciergeSuggestion[];
}

export type SourceConfidence = "high" | "medium" | "low" | "unknown";

export interface SourceEvidence {
  sourceTitle?: string | null;
  sourceUrl?: string | null;
  sourceDomain?: string | null;
  sourceRank?: number | null;
  sourceReason?: string | null;
  sourceEvidence?: string | null;
  sourceCategory?: string | null;
  neighborhoodHint?: string | null;
  mentionCount?: number;
}

export interface VenueEnrichment {
  yelpRating?: number;
  yelpReviewCount?: number;
  yelpReviewExcerpts?: string[];
  foursquareCategories?: string[];
  foursquareTags?: string[];
  foursquarePopularity?: number;
}

export interface GoogleVerification {
  provider: "google_places";
  providerPlaceId?: string | null;
  name?: string | null;
  formattedAddress?: string | null;
  lat?: number | null;
  lng?: number | null;
  businessStatus?: string | null;
  googleMapsUri?: string | null;
  websiteUri?: string | null;
  rating?: number | null;
  userRatingCount?: number | null;
  types?: string[];
  confidence?: SourceConfidence;
  score?: number;
  reason?: string | null;
  failureReason?: string | null;
}

export interface UnifiedRestaurantResult {
  type: "verified_place";
  name: string;
  source: string;
  michelinStatus?: string;
  cuisine: string;
  neighborhood?: string;
  rating?: number;
  reviewCount?: number;
  summary?: string;
  bookingLink?: string;
  mapsLink?: string;
  sourceUrl?: string;
  lastVerifiedAt?: string;
  confidence?: SourceConfidence;
  aiScore?: number;
  tags: string[];
  verifiedPlace?: boolean | null;
  verificationTier?: "primary" | "secondary" | null;
  googleVerification?: GoogleVerification | null;
  sourceEvidence?: SourceEvidence | null;
  evidence?: string[];
  bestForTags?: string[];
  evidenceCount?: number;
  sourceBadges?: string[];
  enrichment?: VenueEnrichment | null;
  primaryReason?: string | null;
  supportingDetails?: {
    rating?: string | null;
    reviewCount?: number | null;
    address?: string | null;
    editorialMentions?: number | null;
    tags?: string[];
    metaLine?: string | null;
    whyPick?: string | null;
    conciergeNote?: string | null;
    categoryLabel?: string | null;
    /** Google priceLevel enum (e.g. "PRICE_LEVEL_MODERATE"). Use displayPrice for UI. */
    priceLevel?: string | null;
    /** Google PriceRange object {startPrice, endPrice}. Use displayPrice for UI. */
    priceRange?: Record<string, unknown> | null;
  } | null;
  display?: ConciergeDisplayFields | null;
}

export interface UnifiedAttractionResult {
  type: "verified_place";
  name: string;
  source: string;
  category: string;
  description?: string;
  neighborhood?: string;
  rating?: number;
  reviewCount?: number;
  address?: string;
  mapsLink?: string;
  sourceUrl?: string;
  lastVerifiedAt?: string;
  confidence?: SourceConfidence;
  aiScore?: number;
  tags: string[];
  verifiedPlace?: boolean | null;
  verificationTier?: "primary" | "secondary" | null;
  googleVerification?: GoogleVerification | null;
  sourceEvidence?: SourceEvidence | null;
  evidence?: string[];
  bestForTags?: string[];
  evidenceCount?: number;
  sourceBadges?: string[];
  enrichment?: VenueEnrichment | null;
  primaryReason?: string | null;
  supportingDetails?: {
    rating?: string | null;
    reviewCount?: number | null;
    address?: string | null;
    editorialMentions?: number | null;
    tags?: string[];
    metaLine?: string | null;
    whyPick?: string | null;
    conciergeNote?: string | null;
    categoryLabel?: string | null;
    /** Google priceLevel enum (e.g. "PRICE_LEVEL_MODERATE"). Use displayPrice for UI. */
    priceLevel?: string | null;
    /** Google PriceRange object {startPrice, endPrice}. Use displayPrice for UI. */
    priceRange?: Record<string, unknown> | null;
  } | null;
  display?: ConciergeDisplayFields | null;
}

export interface UnifiedHotelResult {
  type: "verified_place";
  name: string;
  source: string;
  areaLabel?: string;
  stars?: number;
  rating?: number;
  pricePerNight?: number;
  mapsLink?: string;
  bookingUrl?: string;
  sourceUrl?: string;
  lastVerifiedAt?: string;
  confidence?: SourceConfidence;
  reason?: string;
  aiScore?: number;
  tags: string[];
  verifiedPlace?: boolean | null;
  verificationTier?: "primary" | "secondary" | null;
  googleVerification?: GoogleVerification | null;
  sourceEvidence?: SourceEvidence | null;
  evidence?: string[];
  bestForTags?: string[];
  evidenceCount?: number;
  sourceBadges?: string[];
  enrichment?: VenueEnrichment | null;
  primaryReason?: string | null;
  supportingDetails?: {
    rating?: string | null;
    reviewCount?: number | null;
    address?: string | null;
    editorialMentions?: number | null;
    tags?: string[];
    metaLine?: string | null;
    whyPick?: string | null;
    conciergeNote?: string | null;
    categoryLabel?: string | null;
    /** Google priceLevel enum (e.g. "PRICE_LEVEL_MODERATE"). Use displayPrice for UI. */
    priceLevel?: string | null;
    /** Google PriceRange object {startPrice, endPrice}. Use displayPrice for UI. */
    priceRange?: Record<string, unknown> | null;
  } | null;
  display?: ConciergeDisplayFields | null;
}

export interface UnifiedAreaComparisonResult {
  area: string;
  vibe: string;
  bestFor: string;
  pros: string[];
  cons: string[];
  logistics: string;
  valueSignal: string;
  recommendation: string;
  sourceUrl?: string;
  lastVerifiedAt?: string;
}

export interface UnifiedResearchSourceResult {
  type: "research_source";
  title: string;
  source: string;
  sourceType: "article_listicle_blog_directory" | "neighborhood_area" | "generic_info_source";
  summary?: string;
  sourceUrl?: string;
  neighborhood?: string;
  lastVerifiedAt?: string;
  confidence?: SourceConfidence;
  tripAddable: boolean;
  venuesDiscovered?: number;
}

export interface ConciergeSearchResult {
  response: string;
  intent: string;
  retrievalUsed: boolean;
  sourceStatus: string;
  cached?: boolean;
  liveProvider?: string | null;
  restaurants: UnifiedRestaurantResult[];
  attractions: UnifiedAttractionResult[];
  hotels: UnifiedHotelResult[];
  researchSources: UnifiedResearchSourceResult[];
  areas: string[];
  areaComparisons: UnifiedAreaComparisonResult[];
  suggestions: ConciergeSuggestion[];
  sources: string[];
  warnings: string[];
}

export interface ConciergeMessage {
  id: string;
  tripId: string;
  clientMessageId?: string | null;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  structuredResults?: ConciergeSearchResult | null;
  createdAt: string;
}

export async function callConcierge(
  tripId: string | null,
  userQuery: string,
  destination?: string
): Promise<ConciergeResult> {
  return apiFetch<ConciergeResult>("/ai/concierge", {
    method: "POST",
    body: JSON.stringify({
      ...(tripId ? { trip_id: tripId } : {}),
      ...(destination ? { destination } : {}),
      user_query: userQuery,
    }),
  });
}

export async function callConciergeSearch(
  tripId: string | null,
  userQuery: string,
  clientMessageId?: string,
  destination?: string
): Promise<ConciergeSearchResult> {
  const raw = await apiFetch<unknown>("/ai/concierge/search", {
    method: "POST",
    body: JSON.stringify({
      ...(tripId ? { trip_id: tripId } : {}),
      ...(destination ? { destination } : {}),
      user_query: userQuery,
      ...(clientMessageId ? { client_message_id: clientMessageId } : {}),
    }),
  });
  const normalized = normalizeConciergeResponse(raw);
  if (normalized.responseType !== "place_recommendations") {
    return {
      response: normalized.responseType === "trip_advice" ? normalized.response : normalized.message,
      intent: "",
      retrievalUsed: false,
      sourceStatus: "none",
      restaurants: [],
      attractions: [],
      hotels: [],
      researchSources: [],
      areas: [],
      areaComparisons: [],
      suggestions: [],
      sources: [],
      warnings: [],
    };
  }
  return {
    response: normalized.response,
    intent: normalized.intent,
    retrievalUsed: normalized.retrievalUsed,
    sourceStatus: normalized.sourceStatus,
    cached: normalized.cached,
    liveProvider: normalized.liveProvider,
    restaurants: normalized.restaurants as UnifiedRestaurantResult[],
    attractions: normalized.attractions as UnifiedAttractionResult[],
    hotels: normalized.hotels as UnifiedHotelResult[],
    researchSources: normalized.researchSources as UnifiedResearchSourceResult[],
    areas: normalized.areas,
    areaComparisons: normalized.areaComparisons as UnifiedAreaComparisonResult[],
    suggestions: normalized.suggestions,
    sources: normalized.sources,
    warnings: normalized.warnings,
  };
}

export async function fetchConciergeMessages(tripId: string): Promise<ConciergeMessage[]> {
  return apiFetch<ConciergeMessage[]>(`/ai/concierge/${tripId}/messages`);
}

// ─── Product Surface Migration v1B — TripBuilder Explore canonical adapter ──
//
// The legacy /search/attractions surface was mock-backed (see PR #288).  v1B
// migrates the TripBuilder Explore attraction list onto the canonical
// /ai/concierge/search response, which is Google-Places-verified and goes
// through the display contract.  The adapter below converts a single
// canonical UnifiedAttractionResult into the existing AttractionSearchResult
// shape so downstream Add to Day / Save / Maps handlers keep working without
// changing the persisted itinerary-item schema.
//
// Fail-closed rules:
//   1. Drop cards whose `display.addability` is anything other than "addable"
//      (research_only / closed must never become user-facing Explore cards).
//   2. Drop cards without a Google Places provider id — TripBuilder Explore is
//      a place-discovery surface, so the canonical identity must be present
//      for Maps and Save flows to work safely.
export function mapUnifiedAttractionToResult(
  u: UnifiedAttractionResult
): AttractionSearchResult | null {
  const addability = u.display?.addability;
  // v1B requires the canonical display contract: missing addability means
  // the card never went through the display normalizer (PR #287) and must
  // not surface in user-facing Explore.  Only `"addable"` passes.
  if (addability !== "addable") return null;
  const gv = u.googleVerification ?? null;
  const providerPlaceId = gv?.providerPlaceId ?? undefined;
  if (!providerPlaceId) return null;

  const name = (u.display?.displayName && u.display.displayName.trim().length > 0)
    ? u.display.displayName
    : u.name;
  const address = (gv?.formattedAddress && gv.formattedAddress.trim().length > 0)
    ? gv.formattedAddress
    : (u.address ?? "");
  const mapsUri = gv?.googleMapsUri
    ?? u.mapsLink
    ?? `https://www.google.com/maps/place/?q=place_id:${encodeURIComponent(providerPlaceId)}`;
  const rating = typeof gv?.rating === "number" ? gv.rating : (typeof u.rating === "number" ? u.rating : undefined);
  const numReviews = typeof gv?.userRatingCount === "number"
    ? gv.userRatingCount
    : (typeof u.reviewCount === "number" ? u.reviewCount : undefined);
  const description = (u.description && u.description.trim().length > 0)
    ? u.description
    : (u.display?.displayWhy ?? u.primaryReason ?? "");

  const category = u.display?.displayCategory || u.category || "attraction";

  // Normalize ai_score to 0-100.  The concierge pipeline computes it on a
  // ~0-8 scale (Bayesian 5-star base + category/relevance bonuses).  When
  // rating + review data is present, use the same deterministic 0-100 formula
  // as the snapshot-load path for consistency.  Otherwise linearly scale the
  // raw score (max ~8) into 0-100.
  const rawAiScore = typeof u.aiScore === "number" ? u.aiScore : undefined;
  const aiScore: number | undefined =
    rating != null && numReviews != null && numReviews > 0
      ? computeExploreAttractionScore(rating, numReviews, category)
      : rawAiScore != null && rawAiScore > 0 && rawAiScore <= 10
        ? Math.round(Math.min(100, rawAiScore * (100 / 8.0)) * 10) / 10
        : rawAiScore;

  return {
    id: providerPlaceId,
    name,
    category,
    description,
    location: u.neighborhood ?? "",
    address,
    rating,
    numReviews,
    aiScore,
    tags: Array.isArray(u.tags) ? u.tags : [],
    bookingUrl: mapsUri,
    lat: typeof gv?.lat === "number" ? gv.lat : undefined,
    lng: typeof gv?.lng === "number" ? gv.lng : undefined,
  };
}

// Removed (Level 3 Trip Data Contract Rescue):
//   - isCanonicalSnapshotAttraction
//   - searchAttractionsViaConcierge
// These powered the legacy snapshot-first Explore hydration in TripBuilder,
// which competed with the canonical persisted-itinerary_items source of
// truth and caused new trips to render 0 attractions/restaurants while
// triggering a slow AI Concierge "Top attractions in <city>" search.
// Attractions/restaurants are now read from persisted ACTIVITY/MEAL rows
// via buildTripCandidateBuckets (frontend/src/lib/tripCandidates.ts).

// [DEV-ONLY] Debug trace for the AI Concierge pipeline
export interface ConciergeDebugTrace {
  summary: {
    rawProviderCandidateCount: number;
    extractedCandidateCount: number;
    googleDirectCandidateCount: number;
    mergedCandidateCount: number;
    dedupedCandidateCount: number;
    rawCandidateCount: number;
    googleMatchedCount: number;
    acceptedOperationalCount: number;
    rejectedCountByReason: Record<string, number>;
    finalAddableCount: number;
    researchOnlyCount: number;
    whyPickSourceDistribution: Record<string, number>;
  };
  parsedIntent: string;
  searchQueries: string[];
  rawCandidates: string[];
  dedupedCandidates: string[];
  googleVerification: Record<string, unknown>;
  rejectionReasons: unknown[];
  finalAddableCards: unknown[];
  finalDisplayPayload: unknown;
  cacheStatus: { hit: boolean; key: string | null };
}

export async function callConciergeDebugTrace(
  userQuery: string,
  location: string,
  limit = 10
): Promise<ConciergeDebugTrace> {
  return apiFetch<ConciergeDebugTrace>("/ai/concierge/debug-trace", {
    method: "POST",
    body: JSON.stringify({ user_query: userQuery, location, limit }),
  });
}

export async function clearConciergeCache(
  tripId: string,
  destination?: string | null
): Promise<void> {
  await apiFetch<void>("/ai/concierge/cache", {
    method: "DELETE",
    body: JSON.stringify({
      trip_id: tripId,
      ...(destination ? { destination } : {}),
    }),
  });
}

type ConciergeStructuredItem = UnifiedRestaurantResult | UnifiedAttractionResult | UnifiedHotelResult;

export type ConciergeItemKind = "restaurant" | "attraction" | "hotel";

function normalizeGoogleVerificationDetails(item: ConciergeStructuredItem): Record<string, unknown> {
  const gv = item.googleVerification;
  if (!gv || typeof gv !== "object") return {};
  const gvAliases = gv as unknown as {
    lat?: number | null;
    lng?: number | null;
    provider_place_id?: string | null;
    formatted_address?: string | null;
    google_maps_uri?: string | null;
  };

  const getNonEmpty = <T>(...values: Array<T | null | undefined | "">): T | undefined => {
    for (const value of values) {
      if (value !== null && value !== undefined && value !== "") return value as T;
    }
    return undefined;
  };

  const lat = getNonEmpty<number>(
    gv.lat,
    gvAliases.lat
  );
  const lng = getNonEmpty<number>(
    gv.lng,
    gvAliases.lng
  );
  const providerPlaceId = getNonEmpty<string>(
    gv.providerPlaceId ?? undefined,
    gvAliases.provider_place_id ?? undefined
  );
  const formattedAddress = getNonEmpty<string>(
    gv.formattedAddress ?? undefined,
    gvAliases.formatted_address ?? undefined
  );
  const googleMapsUri = getNonEmpty<string>(
    gv.googleMapsUri ?? undefined,
    gvAliases.google_maps_uri ?? undefined
  );

  return {
    ...(lat !== undefined ? { lat } : {}),
    ...(lng !== undefined ? { lng } : {}),
    ...(providerPlaceId ? { provider_place_id: providerPlaceId } : {}),
    ...(formattedAddress ? { formatted_address: formattedAddress } : {}),
    ...(googleMapsUri ? { google_maps_uri: googleMapsUri } : {}),
  };
}

export async function addStructuredConciergeItemToTrip(
  tripId: string,
  item: ConciergeStructuredItem,
  kind: ConciergeItemKind,
  opts?: { dayId?: string; reason?: string }
): Promise<ItineraryItem> {
  const cityOrArea = "neighborhood" in item ? item.neighborhood : ("areaLabel" in item ? item.areaLabel : undefined);
  const reviewCount = "reviewCount" in item ? (item.reviewCount ?? null) : null;
  const category = kind === "restaurant"
    ? "restaurant"
    : kind === "hotel"
      ? "hotel"
      : ("category" in item ? item.category : "activity");
  const payload = {
    trip_id: tripId,
    ...(opts?.dayId ? { day_id: opts.dayId } : {}),
    item_type: kind === "restaurant" ? "meal" : kind === "hotel" ? "hotel" : "activity",
    title: item.name,
    location: cityOrArea || item.name,
    details: {
      name: item.name,
      category,
      type: category,
      city: cityOrArea ?? null,
      location: cityOrArea ?? null,
      address: "address" in item ? (item.address ?? null) : null,
      rating: item.rating ?? null,
      review_count: reviewCount,
      review_count_text: reviewCount != null ? `${reviewCount}` : null,
      source: item.source ?? null,
      source_url: "mapsLink" in item ? (item.mapsLink ?? null) : null,
      maps_link: "mapsLink" in item ? (item.mapsLink ?? null) : null,
      booking_url: "bookingLink" in item ? (item.bookingLink ?? null) : null,
      notes: opts?.reason ?? ("summary" in item ? (item.summary ?? null) : ("description" in item ? (item.description ?? null) : null)),
      reason: opts?.reason ?? null,
      estimated_price_tag: "pricePerNight" in item && item.pricePerNight != null ? `$${Math.round(item.pricePerNight)}/night` : null,
      value_tag: "pricePerNight" in item && item.pricePerNight != null ? `$${Math.round(item.pricePerNight)}/night` : null,
      tags: item.tags ?? [],
      ...normalizeGoogleVerificationDetails(item),
    },
  };
  return apiFetch<ItineraryItem>("/itinerary/items", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchTripIdeas(tripId: string): Promise<ItineraryItem[]> {
  try {
    return await apiFetch<ItineraryItem[]>(`/trips/${tripId}/ideas`);
  } catch {
    return [];
  }
}

export async function saveToTripIdeas(
  tripId: string,
  item: ConciergeStructuredItem,
  kind: ConciergeItemKind,
  reason?: string,
): Promise<ItineraryItem> {
  const cityOrArea = "neighborhood" in item ? item.neighborhood : ("areaLabel" in item ? item.areaLabel : undefined);
  const reviewCount = "reviewCount" in item ? (item.reviewCount ?? null) : null;
  const category = kind === "restaurant"
    ? "restaurant"
    : kind === "hotel"
      ? "hotel"
      : ("category" in item ? item.category : "activity");
  const payload = {
    trip_id: tripId,
    item_type: kind === "restaurant" ? "meal" : kind === "hotel" ? "hotel" : "activity",
    title: item.name,
    location: cityOrArea || item.name,
    details: {
      name: item.name,
      category,
      type: category,
      city: cityOrArea ?? null,
      location: cityOrArea ?? null,
      address: "address" in item ? (item.address ?? null) : null,
      rating: item.rating ?? null,
      review_count: reviewCount,
      review_count_text: reviewCount != null ? `${reviewCount}` : null,
      source: item.source ?? null,
      source_url: "mapsLink" in item ? (item.mapsLink ?? null) : null,
      maps_link: "mapsLink" in item ? (item.mapsLink ?? null) : null,
      booking_url: "bookingLink" in item ? (item.bookingLink ?? null) : null,
      notes: reason ?? ("summary" in item ? (item.summary ?? null) : ("description" in item ? (item.description ?? null) : null)),
      reason: reason ?? null,
      tags: item.tags ?? [],
      source_kind: "concierge_idea",
      idea_status: "maybe",
      ...normalizeGoogleVerificationDetails(item),
    },
  };
  return apiFetch<ItineraryItem>("/itinerary/items", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateIdeaMeta(
  itemId: string,
  currentDetails: Record<string, unknown>,
  patch: { ideaStatus?: string; userNote?: string }
): Promise<ItineraryItem> {
  const merged = { ...currentDetails, ...patch };
  return updateItem(itemId, { details: merged as ItineraryItem["details"] });
}

export async function updateItemTimeline(
  itemId: string,
  currentDetails: Record<string, unknown>,
  patch: { dayPart: string; timeLabel?: string }
): Promise<ItineraryItem> {
  const merged: Record<string, unknown> = { ...currentDetails, dayPart: patch.dayPart };
  if (patch.timeLabel) {
    merged.timeLabel = patch.timeLabel;
  } else {
    delete merged.timeLabel;
  }
  return updateItem(itemId, { details: merged as ItineraryItem["details"] });
}

// ─── Smart Day Timeline AI Planning ──────────────────────────────────────────

export interface TimelineSuggestion {
  itemId: string;
  dayPart: "morning" | "afternoon" | "evening" | "unscheduled";
  timeLabel?: string;
}

/**
 * Ask the backend AI planner to suggest dayPart/timeLabel for a list of
 * itinerary items. Falls back to the client-side deterministic planner when
 * the backend is unreachable or the AI key is not configured.
 *
 * Preserves all other item fields — only dayPart and timeLabel are suggested.
 * Callers must still apply suggestions via updateItemTimeline.
 */
export async function suggestDayTimeline(
  items: ItineraryItem[]
): Promise<TimelineSuggestion[]> {
  const payload = {
    items: items.map((item) => ({
      id: item.id,
      title: item.title,
      item_type: item.itemType,
      details: (item.details ?? {}) as Record<string, unknown>,
    })),
  };

  try {
    const result = await apiFetch<{ suggestions: TimelineSuggestion[] }>(
      "/ai/timeline/suggest",
      { method: "POST", body: JSON.stringify(payload) }
    );
    return result.suggestions;
  } catch {
    // Client-side deterministic fallback — always works in local/dev/test
    const { suggestTimelineFallback } = await import("./dayPlanner");
    return suggestTimelineFallback(items);
  }
}

export async function assignIdeaToDay(itemId: string, dayId: string): Promise<ItineraryItem> {
  return apiFetch<ItineraryItem>(`/itinerary/items/${itemId}`, {
    method: "PATCH",
    body: JSON.stringify({ day_id: dayId }),
  });
}

export async function moveIdeaToTripIdeas(itemId: string): Promise<ItineraryItem> {
  return apiFetch<ItineraryItem>(`/itinerary/items/${itemId}`, {
    method: "PATCH",
    body: JSON.stringify({ day_id: null }),
  });
}

export async function addConciergeItemToTrip(
  tripId: string,
  suggestion: ConciergeSuggestion
): Promise<ItineraryItem> {
  const payload = {
    trip_id: tripId,
    item_type: suggestion.type === "restaurant" ? "meal" : "activity",
    title: suggestion.name,
    details: { reason: suggestion.reason },
  };
  return apiFetch<ItineraryItem>("/itinerary/items", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function addMichelinRestaurantToTrip(
  tripId: string,
  restaurant: UnifiedRestaurantResult
): Promise<ItineraryItem> {
  const payload = {
    trip_id: tripId,
    item_type: "meal",
    title: restaurant.name,
    location: restaurant.neighborhood || restaurant.name,
    details: {
      name: restaurant.name,
      cuisine: restaurant.cuisine,
      neighborhood: restaurant.neighborhood ?? null,
      rating: restaurant.rating ?? null,
      num_reviews: restaurant.reviewCount ?? null,
      michelin_status: restaurant.michelinStatus ?? null,
      source: restaurant.source,
      summary: restaurant.summary ?? null,
      ai_score: restaurant.aiScore ?? null,
      tags: restaurant.tags,
      booking_url: restaurant.bookingLink ?? null,
      maps_link: restaurant.mapsLink ?? null,
    },
  };
  return apiFetch<ItineraryItem>("/itinerary/items", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ─── Saved Items (Stage 2A Slice 2) ──────────────────────────────────────────

export async function saveItem(payload: SavedItemCreate): Promise<SavedItem> {
  return apiFetch<SavedItem>("/saved-items", {
    method: "POST",
    body: JSON.stringify(toSnake(payload)),
  });
}

export async function listSavedItems(vertical?: string): Promise<SavedItem[]> {
  const qs = vertical ? `?vertical=${encodeURIComponent(vertical)}` : "";
  return apiFetch<SavedItem[]>(`/saved-items${qs}`);
}

export async function deleteSavedItem(itemId: string): Promise<void> {
  await apiFetch<void>(`/saved-items/${itemId}`, { method: "DELETE" });
}

// ─── Saved → Trip Conversion (Stage 3 v2) ────────────────────────────────────

const SAVED_VERTICAL_TO_ITEM_TYPE: Record<string, string> = {
  restaurant: "meal",
  attraction: "activity",
  hotel: "hotel",
};

/**
 * Promote a saved idea into an unscheduled itinerary candidate on an existing trip.
 * Posts directly to POST /itinerary/items with day_id omitted (null = unscheduled).
 * Hotel details carry discovery context only — no rates, prices, or booking fields.
 * Flights are not supported; callers must guard on item.vertical !== "flight".
 */
export async function addSavedItemToTrip(
  tripId: string,
  item: SavedItem
): Promise<ItineraryItem> {
  const itemType = SAVED_VERTICAL_TO_ITEM_TYPE[item.vertical];
  if (!itemType) {
    throw new Error(`Vertical "${item.vertical}" is not supported for trip conversion.`);
  }

  const snap = item.displaySnapshot;
  const ctx = item.searchContext;

  const title =
    (typeof snap["name"] === "string" && snap["name"] ? snap["name"] : null) ??
    item.displayName;

  const location: string | undefined =
    (typeof snap["address"] === "string" && snap["address"] ? snap["address"] : undefined) ??
    (typeof snap["destination"] === "string" && snap["destination"] ? snap["destination"] : undefined) ??
    (typeof ctx["destination"] === "string" && ctx["destination"] ? ctx["destination"] : undefined);

  const details: Record<string, unknown> = {
    name: title,
    source: "saved_item",
    savedItemId: item.id,
  };

  if (typeof snap["address"] === "string" && snap["address"]) details.address = snap["address"];
  if (typeof snap["rating"] === "number") details.rating = snap["rating"];
  if (Array.isArray(snap["tags"]) && (snap["tags"] as unknown[]).length) details.tags = snap["tags"];
  if (typeof snap["googleMapsUri"] === "string" && snap["googleMapsUri"]) details.googleMapsUri = snap["googleMapsUri"];

  if (item.vertical === "restaurant") {
    if (typeof snap["cuisine"] === "string" && snap["cuisine"]) details.cuisine = snap["cuisine"];
    if (typeof snap["priceLevel"] === "number") details.priceLevel = snap["priceLevel"];
  }

  if (item.vertical === "hotel") {
    if (typeof ctx["checkIn"] === "string" && ctx["checkIn"]) details.checkIn = ctx["checkIn"];
    if (typeof ctx["checkOut"] === "string" && ctx["checkOut"]) details.checkOut = ctx["checkOut"];
    if (typeof ctx["guests"] === "number") details.guests = ctx["guests"];
  }

  const payload: Record<string, unknown> = {
    trip_id: tripId,
    item_type: itemType,
    title,
    details,
    position: 0,
  };
  if (location) payload.location = location;

  return apiFetch<ItineraryItem>("/itinerary/items", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
