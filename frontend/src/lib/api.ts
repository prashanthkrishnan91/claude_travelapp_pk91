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
  LocationCluster,
  PlaceInCluster,
  BestAreaRecommendation,
  DayPlan,
} from "@/types";
import { supabase } from "./supabase";

// ─── Config ──────────────────────────────────────────────────────────────────

/** Direct connection to FastAPI backend — no proxy, no rewrites. */
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

console.log("API URL:", process.env.NEXT_PUBLIC_API_URL);

async function getAuthHeader(): Promise<Record<string, string>> {
  const { data: { session } } = await supabase.auth.getSession();

  console.log("[auth] session:", session);

  if (!session) {
    throw new Error("[auth] No active session — request blocked. User must be signed in.");
  }

  const token = session.access_token;
  if (!token) {
    console.error("[auth] Session exists but access_token is null/undefined — request blocked.");
    throw new Error("[auth] Missing access_token in session.");
  }

  console.log("[auth] access_token:", token.slice(0, 20) + "…");

  const header = { Authorization: `Bearer ${token}` };
  console.log("[auth] Authorization header attached:", header.Authorization.slice(0, 30) + "…");
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

  console.log(`[apiFetch] → ${options.method ?? "GET"} ${url}`);
  if (options.body) {
    console.log(`[apiFetch] body:`, options.body);
  }

  const authHeader = await getAuthHeader();

  const finalHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...authHeader,
    ...(options.headers as Record<string, string>),
  };

  console.log("[apiFetch] final request headers:", finalHeaders);

  const res = await fetch(url, {
    ...options,
    headers: finalHeaders,
    // Don't cache on the server so data is always fresh
    cache: "no-store",
  });

  console.log(`[apiFetch] ← ${res.status} ${res.statusText} (${url})`);

  if (res.status === 204) return null as T;

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      console.error(`[apiFetch] error body:`, body);
      detail = body?.detail ?? detail;
    } catch {
      // ignore parse errors
    }
    throw new Error(`API error: ${detail}`);
  }

  const json = await res.json();
  console.log(`[apiFetch] response body:`, json);
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
    const days = await apiFetch<ItineraryDay[]>(`/itinerary/${tripId}/days`);

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
  const payload = toSnake({
    tripId,
    dayId,
    itemType: "flight",
    title: `${outbound.airline ?? ""} ${outbound.flight_number ?? ""} (Outbound)`.trim(),
    startTime: outbound.departure_time,
    endTime: outbound.arrival_time,
    cashPrice: outbound.price,
    pointsPrice: outbound.points_cost,
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
  const payload = toSnake({
    tripId,
    dayId,
    itemType: "flight",
    title: `${returnFlight.airline ?? ""} ${returnFlight.flight_number ?? ""} (Return)`.trim(),
    startTime: returnFlight.departure_time,
    endTime: returnFlight.arrival_time,
    cashPrice: returnFlight.price,
    pointsPrice: returnFlight.points_cost,
    cppValue: returnFlight.cpp,
    position,
    details: { ...returnFlight, leg: "return" },
  });
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

// ─── Search / Research ────────────────────────────────────────────────────────

interface RawAttractionResult {
  id: string;
  name: string;
  category: string;
  description: string;
  durationMinutes?: number;
  price?: number;
  rating?: number;
  location: string;
  address: string;
  bookingUrl?: string;
  bookingOptions?: BookingOption[];
  aiScore?: number;
  tags?: string[];
  numReviews?: number;
  openingHours?: string;
  priceLevel?: number;
}

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
}

function mapAttractionToResult(a: RawAttractionResult): AttractionSearchResult {
  return {
    id: a.id,
    name: a.name,
    category: a.category,
    description: a.description,
    location: a.location,
    address: a.address,
    rating: a.rating,
    numReviews: a.numReviews,
    price: a.price,
    priceLevel: a.priceLevel,
    openingHours: a.openingHours,
    durationMinutes: a.durationMinutes,
    aiScore: a.aiScore,
    tags: a.tags ?? [],
    bookingUrl: a.bookingUrl,
    bookingOptions: a.bookingOptions,
  };
}

function mapHotelToResult(h: RawHotelResult): ResearchResult {
  return {
    id: h.id,
    category: "hotel" as ResearchCategory,
    title: h.name,
    location: h.location,
    duration: "Per night",
    priceDisplay: h.pricePerNight ? `$${h.pricePerNight}/night` : undefined,
    rating: h.rating,
    tags: (h.amenities ?? []).slice(0, 3),
    bookingUrl: h.bookingUrl,
    bookingOptions: h.bookingOptions,
    metadata: {
      pricePerNight: h.pricePerNight,
      amenities: h.amenities ?? [],
      stars: h.stars,
    },
  };
}

/** Fetch hotels for a destination and date range. */
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

/** Fetch attractions/activities for a location, sorted by AI score DESC. */
export async function searchAttractions(
  location: string,
  date?: string
): Promise<AttractionSearchResult[]> {
  try {
    const payload = toSnake({ location, date: date ?? null });
    const results = await apiFetch<RawAttractionResult[]>(
      "/search/attractions",
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    );
    return results.map(mapAttractionToResult);
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
  sentiment?: number;
  tags?: string[];
  bookingUrl?: string;
  bookingOptions?: BookingOption[];
}

function mapRestaurantToResult(r: RawRestaurantResult): RestaurantSearchResult {
  return {
    id: r.id,
    name: r.name,
    cuisine: r.cuisine,
    location: r.location,
    address: r.address,
    rating: r.rating,
    numReviews: r.numReviews,
    price: r.price,
    priceLevel: r.priceLevel,
    openingHours: r.openingHours,
    aiScore: r.aiScore,
    sentiment: r.sentiment,
    tags: r.tags ?? [],
    bookingUrl: r.bookingUrl,
    bookingOptions: r.bookingOptions,
  };
}

/** Fetch restaurants and dining options for a location, sorted by AI score DESC. */
export async function searchRestaurants(
  location: string,
  date?: string
): Promise<RestaurantSearchResult[]> {
  try {
    const payload = toSnake({ location, date: date ?? null });
    const results = await apiFetch<RawRestaurantResult[]>("/search/restaurants", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return results.map(mapRestaurantToResult);
  } catch {
    return [];
  }
}

/** Fetch attractions and restaurants grouped into proximity clusters. */
export async function searchClusters(
  location: string,
  radiusKm: number = 1.5
): Promise<LocationCluster[]> {
  try {
    const payload = { location, radius_km: radiusKm };
    const raw = await apiFetch<Record<string, unknown>[]>("/search/clusters", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return raw.map((c) => ({
      clusterId: c.cluster_id as string,
      areaName: c.area_name as string,
      label: c.label as string,
      centerLat: c.center_lat as number,
      centerLng: c.center_lng as number,
      places: (c.places as Record<string, unknown>[]).map(
        (p): PlaceInCluster => ({
          id: p.id as string,
          name: p.name as string,
          placeType: p.place_type as "attraction" | "restaurant",
          category: p.category as string,
          address: p.address as string,
          rating: p.rating as number | undefined,
          aiScore: p.ai_score as number | undefined,
          tags: (p.tags as string[]) ?? [],
          lat: p.lat as number,
          lng: p.lng as number,
          bookingUrl: p.booking_url as string,
          bookingOptions: p.booking_options as BookingOption[] | undefined,
        })
      ),
    }));
  } catch {
    return [];
  }
}

/** Fetch the best area recommendation for a destination. */
export async function fetchBestArea(
  location: string,
  radiusKm: number = 1.5
): Promise<BestAreaRecommendation | null> {
  try {
    const payload = { location, radius_km: radiusKm };
    const raw = await apiFetch<Record<string, unknown> | null>("/search/best-area", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (!raw) return null;
    return {
      areaName: raw.area_name as string,
      reason: raw.reason as string,
      score: raw.score as number,
      centerLat: raw.center_lat as number,
      centerLng: raw.center_lng as number,
      radiusKm: raw.radius_km as number,
      clusterId: raw.cluster_id as string,
    };
  } catch {
    return null;
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
