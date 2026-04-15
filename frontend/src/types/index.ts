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

// ─── Itinerary ────────────────────────────────────────────────────────────────

export type ItemType = "flight" | "hotel" | "activity" | "transit" | "meal" | "note";

export interface ItineraryItem {
  id: string;
  dayId: string;
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
