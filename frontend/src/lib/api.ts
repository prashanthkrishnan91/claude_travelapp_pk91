/**
 * API client for the Travel Concierge backend.
 *
 * - All responses are transformed from snake_case → camelCase.
 * - All request bodies are transformed from camelCase → snake_case.
 * - Auth via Supabase JWT: Authorization: Bearer <access_token>
 */

import type {
  Trip,
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

// ─── Flight Search ────────────────────────────────────────────────────────────

export async function searchFlights(
  origin: string,
  destination: string,
  departureDate: string
): Promise<FlightSearchResult[]> {
  const normalizedOrigin = origin.trim().toUpperCase();
  const normalizedDestination = destination.trim().toUpperCase();

  if (!/^[A-Z]{3}$/.test(normalizedOrigin)) {
    throw new Error(`Invalid origin: "${origin}" — must be a 3-letter IATA code (e.g. JFK)`);
  }
  if (!/^[A-Z]{3}$/.test(normalizedDestination)) {
    throw new Error(`Invalid destination: "${destination}" — must be a 3-letter IATA code (e.g. LAX)`);
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(departureDate)) {
    throw new Error(`Invalid departure_date: "${departureDate}" — must be YYYY-MM-DD`);
  }

  const payload = {
    origin: normalizedOrigin,
    destination: normalizedDestination,
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

function mapAttractionToResult(a: RawAttractionResult): ResearchResult {
  return {
    id: a.id,
    category: "activity" as ResearchCategory,
    title: a.name,
    description: a.description,
    location: a.location || a.address,
    duration: a.durationMinutes
      ? `${Math.round((a.durationMinutes / 60) * 10) / 10}h`
      : undefined,
    priceDisplay: a.price ? `$${a.price}/person` : undefined,
    rating: a.rating,
    tags: [a.category].filter(Boolean),
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

/** Fetch attractions/activities for a location. */
export async function searchAttractions(
  location: string,
  date?: string
): Promise<ResearchResult[]> {
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

// ─── Compare ─────────────────────────────────────────────────────────────────

export async function compareItems(items: CompareItemInput[]): Promise<CompareResult[]> {
  const payload = toSnake({ items });
  const response = await apiFetch<{ results: CompareResult[] }>("/compare", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.results;
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
