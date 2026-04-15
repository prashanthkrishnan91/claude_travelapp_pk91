/**
 * API client for the Travel Concierge backend.
 *
 * - All responses are transformed from snake_case → camelCase.
 * - All request bodies are transformed from camelCase → snake_case.
 * - Auth is a placeholder X-User-ID header until Supabase Auth is wired up.
 */

import type {
  Trip,
  ItineraryDay,
  ItineraryItem,
  ItemType,
  TravelCard,
  ResearchResult,
  ResearchCategory,
  TripBuilderFormData,
  CompareItemInput,
  CompareResult,
  BookingOption,
} from "@/types";

// ─── Config ──────────────────────────────────────────────────────────────────

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Placeholder user ID until real auth exists. */
export const DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001";

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

  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-User-ID": DEFAULT_USER_ID,
      ...(options.headers as Record<string, string>),
    },
    // Don't cache on the server so data is always fresh
    cache: "no-store",
  });

  if (res.status === 204) return null as T;

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      // ignore parse errors
    }
    throw new Error(`API error: ${detail}`);
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
    userId: DEFAULT_USER_ID,
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

// ─── Travel Cards ─────────────────────────────────────────────────────────────

export async function fetchCards(): Promise<TravelCard[]> {
  try {
    return await apiFetch<TravelCard[]>("/cards");
  } catch {
    return [];
  }
}
