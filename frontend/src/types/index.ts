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

// ─── Rewards Intelligence ─────────────────────────────────────────────────────

export interface RewardsBreakdown {
  earnRate?: string;
  opportunityCost?: string;
  transferPartner?: string;
}

export interface BestCardRecommendation {
  cardKey: string;
  displayName: string;
  earnRate: number;
  expectedPoints: number;
  expectedValueUsd: number;
}

export interface RewardsIntelligence {
  decision: "points" | "cash";
  cpp: number;
  adjustedCpp: number;
  effectiveCost: number;
  effectiveCurrency?: string;
  explanation: string;
  breakdown?: RewardsBreakdown;
  bestCard?: BestCardRecommendation;
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
  rewardsIntelligence?: RewardsIntelligence;
  position: number;
  createdAt?: string;
  updatedAt?: string;
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

// ─── Route Estimate ───────────────────────────────────────────────────────────

export interface RouteableStopPayload {
  itemId: string;
  title: string;
  itemType: string;
  lat: number;
  lng: number;
  placeId?: string;
  providerPlaceId?: string;
}

export interface RouteEstimateLeg {
  fromItemId: string;
  toItemId: string;
  distanceMeters: number;
  durationSeconds: number;
  provider: string;
  orderIndex: number;
}

export interface RouteEstimateResponse {
  status: "disabled" | "not_configured" | "success" | "provider_error";
  reason: string;
  message: string;
  provider: string;
  estimates: RouteEstimateLeg[];
  metadata: Record<string, unknown>;
}

// ─── Route Quality Diagnostic (read-only, PR #526) ───────────────────────────

export type RouteQualityDiagnosticStatus =
  | "ready"
  | "insufficient_stops"
  | "missing_coordinates"
  | "disabled";

export interface DiagnosticStopSummary {
  itemId: string;
  title: string;
  itemType: string;
  position: number;
  lat?: number;
  lng?: number;
  category?: string;
}

export interface ExcludedStopSummary {
  itemId: string;
  title: string;
  itemType: string;
  reason: string;
}

export interface RouteQualityDiagnosticResponse {
  status: RouteQualityDiagnosticStatus;
  eligibleStopCount: number;
  locatedStopCount: number;
  missingCoordinateCount: number;
  eligibleStops: DiagnosticStopSummary[];
  missingCoordinateStops: DiagnosticStopSummary[];
  excludedStops: ExcludedStopSummary[];
  routeDataStatus: "unavailable";
  warnings: string[];
  safeForAi: boolean;
  aiBlockers: string[];
}

// ─── Reorder Proposal (explicit user-confirmed apply, PR C) ──────────────────
// No AI/LLM generates this proposal in this PR — it is only the shape the
// apply contract validates and writes on explicit user confirmation.

export interface ReorderProposal {
  /** Raw position-order item IDs — what applyRouteReorderProposal always sends. */
  currentOrder: string[];
  proposedOrder: string[];
  /**
   * Display-only ordering (e.g. canonical Morning/Afternoon/Evening/
   * Unscheduled section order matching ItineraryDayColumn). When present,
   * the preview renders these instead of currentOrder/proposedOrder — but
   * apply always uses currentOrder/proposedOrder, never these.
   */
  currentDisplayOrder?: string[];
  proposedDisplayOrder?: string[];
  /** Short plain-English reason for the suggested change, if any. */
  rationale?: string;
  moveReasons?: Record<string, string>;
}

export type RouteReorderApplyStatus = "disabled" | "rejected" | "applied";

export interface RouteReorderApplyResponse {
  status: RouteReorderApplyStatus;
  reason: string;
  message: string;
  dayId: string;
  order: string[];
}

// ─── Route Reorder Proposal — AI generation (AI Route Planning v1) ───────────
// Triggered only by an explicit "Plan My Day" click. Read-only — generation
// never writes; applying a proposal reuses RouteReorderApplyResponse above.

export type RouteReorderProposalGenerateStatus = "disabled" | "unavailable" | "success";

export interface RouteReorderProposalGenerateResponse {
  status: RouteReorderProposalGenerateStatus;
  /** Machine-readable cause, e.g. "proposal_generated", "current_order_already_practical". */
  reason: string;
  message: string;
  dayId: string;
  /** Raw position-order item IDs — the shape the existing apply endpoint (#528) requires. */
  currentOrder: string[];
  proposedOrder: string[];
  /**
   * Display-only ordering: every day item bucketed into the same canonical
   * Morning/Afternoon/Evening/Unscheduled sections ItineraryDayColumn
   * renders. The preview must render these, not currentOrder/proposedOrder,
   * so what's shown always matches the visible itinerary.
   */
  currentDisplayOrder: string[];
  proposedDisplayOrder: string[];
  rationale: string;
  moveReasons: Record<string, string>;
  /** Provider-derived (Google Routes) evidence — never LLM-authored. Null when no route comparison was made. */
  currentDurationSeconds?: number | null;
  proposedDurationSeconds?: number | null;
  estimatedSavingsSeconds?: number | null;
  currentDistanceMeters?: number | null;
  proposedDistanceMeters?: number | null;
  estimatedDistanceSavingsMeters?: number | null;
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
  providerPlaceId?: string;
  googleMapsUri?: string;
  placeId?: string;
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
  // Plan My Day Place Resolution v1: canonical Google place identity (parity
  // with RestaurantSearchResult) so day-plan-accepted attractions persist the
  // same routeable metadata as Build/Concierge items.
  providerPlaceId?: string;
  googleMapsUri?: string;
  placeId?: string;
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
  counts: { attractions: number; restaurants: number };
  avgDistance: string;
}

// ─── Best Area Recommendation ─────────────────────────────────────────────────

export interface BestAreaRecommendation {
  areaName: string;
  reason: string;
  score: number;
  centerLat: number;
  centerLng: number;
  radiusKm: number;
  clusterId: string;
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

// ─── Trip Optimization ────────────────────────────────────────────────────────

export interface OptimizeFlightInput {
  id: string;
  airline: string;
  flightNumber: string;
  price: number;
  pointsCost: number;
  cpp: number;
  durationMinutes: number;
  stops: number;
  cabinClass: string;
  rating?: number;
  decision: string;
  tags: string[];
  explanation: string;
}

export interface OptimizeHotelInput {
  id: string;
  name: string;
  price: number;
  pricePerNight: number;
  nights: number;
  pointsEstimate: number;
  rating?: number;
  stars?: number;
  locationScore?: number;
  areaLabel?: string;
  tags: string[];
  explanation: string;
}

export interface TripOption {
  rank: number;
  flight: OptimizeFlightInput;
  hotel: OptimizeHotelInput;
  totalCost: number;
  totalPoints: number;
  flightScore: number;
  hotelScore: number;
  rewardsEfficiency: number;
  totalValueScore: number;
  summary: string;
}

export interface TripOptimizationResponse {
  bestOptions: TripOption[];
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

// ─── Saved Items (Stage 2A Slice 2) ──────────────────────────────────────────

export type SavedItemVertical = "restaurant" | "attraction" | "hotel" | "flight";
export type SavedItemStatus = "active" | "deleted";

export interface SavedItemCreate {
  vertical: SavedItemVertical;
  displayName: string;
  provider?: string;
  /** Google Place ID — restaurants, attractions, hotels */
  providerPlaceId?: string;
  /** Generic offer / itinerary / entity identity — flights, non-place providers */
  providerItemId?: string;
  displaySnapshot?: Record<string, unknown>;
  searchContext?: Record<string, unknown>;
  provenance?: Record<string, unknown>;
}

export interface SavedItem {
  id: string;
  userId: string;
  vertical: SavedItemVertical;
  displayName: string;
  provider?: string;
  providerPlaceId?: string;
  providerItemId?: string;
  displaySnapshot: Record<string, unknown>;
  searchContext: Record<string, unknown>;
  provenance: Record<string, unknown>;
  /** Persisted user note ("great rooftop", "near hotel", etc.). Null when unset. */
  note?: string | null;
  status: SavedItemStatus;
  createdAt: string;
  updatedAt: string;
}
