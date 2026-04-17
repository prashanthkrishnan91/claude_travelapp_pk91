// ─── Trip ────────────────────────────────────────────────────────────────────

export type TripStatus =
  | "draft"
  | "researching"
  | "planned"
  | "booked"
  | "completed"
  | "archived";

export interface Trip {
  id: string;
  title: string;
  destination: string;
  origin?: string;
  startDate?: string;   // ISO date string
  endDate?: string;
  travelers: number;
  budgetCash?: number;
  budgetCurrency: string;
  status: TripStatus;
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

// ─── Trip Context ─────────────────────────────────────────────────────────────

export interface TripContext {
  city: string;
  temp?: number;
  condition?: string;
  vibe: string;
  dateRange?: string;
}

// ─── Booking ──────────────────────────────────────────────────────────────────

export interface BookingOption {
  /** Provider identifier, e.g. "booking_com", "chase_portal", "viator" */
  provider: string;
  /** Deep-link URL to complete the booking */
  url: string;
}

// ─── Itinerary ────────────────────────────────────────────────────────────────

export type ItemType = "flight" | "hotel" | "activity" | "transit" | "meal" | "note";

export interface ItineraryItem {
  id: string;
  dayId?: string;
  tripId: string;
  itemType: ItemType;
  title: string;
  description?: string;
  location?: string;
  startTime?: string;
  endTime?: string;
  cashPrice?: number;
  cashCurrency?: string;
  pointsPrice?: number;
  pointsCardKey?: string;
  bestOption?: "cash" | "points";
  position: number;
  details?: {
    bookingOptions?: BookingOption[];
    [key: string]: unknown;
  };
}

export interface ItineraryDay {
  id: string;
  tripId: string;
  dayNumber: number;
  date?: string;
  title?: string;
  summary?: string;
  items: ItineraryItem[];
}

// ─── Travel Card ─────────────────────────────────────────────────────────────

export interface TravelCard {
  id: string;
  cardKey: string;
  displayName: string;
  issuer: string;
  pointsBalance: number;
  pointValueCpp?: number;
  isPrimary: boolean;
}

// ─── Dashboard Stats ─────────────────────────────────────────────────────────

export interface DashboardStats {
  totalTrips: number;
  upcomingTrips: number;
  totalCards: number;
  totalPoints: number;
}

// ─── Flight Search ────────────────────────────────────────────────────────────

export interface FlightSearchResult {
  id: string;
  airline: string;
  flightNumber: string;
  origin: string;
  destination: string;
  departureTime: string;
  arrivalTime: string;
  durationMinutes: number;
  stops: number;
  cabinClass: string;
  price: number;
  pointsEstimate: number;
  pointsCost: number;
  cpp: number;
  recommendationTag: string;
  rating?: number;
  bookingUrl: string;
  bookingOptions?: BookingOption[];
  aiScore?: number;
  decision?: string;
  tags?: string[];
  savingsVsBest?: number;
  explanation?: string;
}

// ─── Round-Trip Flight Pair ───────────────────────────────────────────────────

export interface RoundTripFlightPair {
  id: string;
  outbound: FlightSearchResult;
  returnFlight: FlightSearchResult;
  totalPrice: number;
  totalPoints: number;
  combinedCpp: number;
  totalDurationMinutes: number;
}

// ─── Research Results (Trip Builder left panel) ───────────────────────────────

export type ResearchCategory = "flight" | "hotel" | "activity" | "meal" | "transit" | "note";

export interface ResearchResult {
  id: string;
  category: ResearchCategory;
  title: string;
  description?: string;
  location?: string;
  duration?: string;
  priceDisplay?: string;
  rating?: number;
  tags?: string[];
  bookingUrl?: string;
  bookingOptions?: BookingOption[];
  metadata?: Record<string, unknown>;
}

// ─── Restaurant Search Result ─────────────────────────────────────────────────

export interface RestaurantSearchResult {
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
  tags: string[];
  bookingUrl?: string;
  bookingOptions?: BookingOption[];
  lat?: number;
  lng?: number;
}

// ─── Attraction Search Result ─────────────────────────────────────────────────

export interface AttractionSearchResult {
  id: string;
  name: string;
  category: string;
  description: string;
  location: string;
  address: string;
  rating?: number;
  numReviews?: number;
  price?: number;
  priceLevel?: number;
  openingHours?: string;
  durationMinutes?: number;
  aiScore?: number;
  tags: string[];
  bookingUrl?: string;
  bookingOptions?: BookingOption[];
  lat?: number;
  lng?: number;
}

// ─── Proximity Cluster ────────────────────────────────────────────────────────

export interface PlaceInCluster {
  id: string;
  name: string;
  placeType: "attraction" | "restaurant";
  category: string;
  address: string;
  rating?: number;
  aiScore?: number;
  tags: string[];
  lat: number;
  lng: number;
  bookingUrl: string;
  bookingOptions?: BookingOption[];
}

export interface LocationCluster {
  clusterId: string;
  areaName: string;
  label: string;
  centerLat: number;
  centerLng: number;
  places: PlaceInCluster[];
}

// ─── Day Plan ─────────────────────────────────────────────────────────────────

export interface DayPlan {
  tripId: string;
  dayNumber: number;
  destination: string;
  attractions: AttractionSearchResult[];
  lunch: RestaurantSearchResult;
  dinner: RestaurantSearchResult;
}

// ─── Compare ──────────────────────────────────────────────────────────────────

export interface CompareItemInput {
  id: string;
  name: string;
  itemType: string;
  cashPrice: number;
  pointsCost: number;
  rating?: number;
  layovers?: number;
}

export interface CompareResult {
  id: string;
  name: string;
  type: string;
  price: number;
  points: number;
  cpp: number | null;
  valueScore: number;
  tags: string[];
  recommendationReason: string;
}

// ─── Deals Feed ───────────────────────────────────────────────────────────────

export interface DealItem {
  itemId: string;
  title: string;
  description: string;
  valueScore: number;
  tags: string[];
}

// ─── Trip Builder Form ────────────────────────────────────────────────────────

export interface TripBuilderFormData {
  title: string;
  destination: string;
  origin: string;
  startDate: string;
  endDate: string;
  travelers: number;
  budgetCash: string;
  budgetCurrency: string;
  notes: string;
}
