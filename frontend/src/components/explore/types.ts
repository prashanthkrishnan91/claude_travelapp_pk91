/**
 * Shared types for the Global Explore Shell (Stage 2A Slice 1).
 * ExploreResultContext is the action-ready payload each result card carries
 * so Slice 2 (ResultActionSheet) can wire Save / Add to Trip / Create Trip
 * without re-fetching anything.
 */

import type { RestaurantSearchResult, AttractionSearchResult } from "@/types";

// ---------------------------------------------------------------------------
// Hotel domain types — discovery vs offer (Hotels Product Contract v1)
// ---------------------------------------------------------------------------

/**
 * Hotel discovery card — a verified lodging entity from Google Places.
 * Has NO rates, prices, or availability claims.
 * Use for HotelExploreFlow / HotelDiscoveryCard rendering (Slice 5A).
 */
export interface HotelDiscoveryCard {
  kind: "hotel_discovery";
  placeId: string;
  name: string;
  /** Search context — preserved for future provider-backed offer hydration */
  destination: string;
  checkIn?: string;
  checkOut?: string;
  guests?: number;
  rooms?: number;
  /** Place metadata */
  rating?: number;
  address?: string;
  googleMapsUrl?: string;
  tags?: string[];
}

/**
 * Hotel offer from a real rates provider (Slice 5C+, Duffel Stays or similar).
 * NEVER populated by discovery-only adapters (Google Places).
 * Every field carrying price/availability data must come from a live provider.
 *
 * Do not render totalPrice, currency, or cancellationSummary from a
 * HotelDiscoveryCard — use HotelOffer only.
 */
export interface HotelOffer {
  kind: "hotel_offer";
  provider: string;                   // e.g. "duffel_stays"
  providerPropertyId: string;
  providerOfferId?: string;
  /** Search context */
  destination: string;
  checkIn: string;
  checkOut: string;
  guests: number;
  rooms: number;
  /** Price — provider-verified only, never invented */
  currency: string;                   // ISO 4217
  totalPrice: number;
  taxesFeesIncluded: boolean | null;  // null = unknown
  /** Booking */
  cancellationSummary?: string;
  bookingUrl?: string;
  /** Freshness + trust */
  rateFetchedAt: string;              // ISO 8601 UTC
  providerDisclaimer: string;         // must be surfaced to the user in UI
  /** Availability */
  isAvailable: boolean;
  errorReason?: string;
}

export type ExploreVertical = "flights" | "hotels" | "restaurants" | "attractions";

export interface ExploreResultContext {
  vertical: ExploreVertical;
  destination: string;
  /** Lat/lng when available from the provider */
  location?: { lat?: number; lng?: number };
  /** Hotel/flight date context */
  dates?: {
    checkIn?: string;
    checkOut?: string;
    departure?: string;
    returnDate?: string;
  };
  /** Flight origin airport code */
  origin?: string;
  /** Hotel guest count */
  guests?: number;
  /** Hotel room count */
  rooms?: number;
  /** Flight passenger count */
  passengers?: number;
  /** Cabin class for flights */
  cabinClass?: string;
  /** Provider-assigned place identity (Google Place ID etc.) */
  providerIdentity?: string;
  /** Original provider payload — typed per vertical */
  originalPayload: RestaurantSearchResult | AttractionSearchResult | Record<string, unknown>;
}
