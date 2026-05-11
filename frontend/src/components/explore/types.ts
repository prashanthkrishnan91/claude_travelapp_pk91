/**
 * Shared types for the Global Explore Shell (Stage 2A Slice 1).
 * ExploreResultContext is the action-ready payload each result card carries
 * so Slice 2 (ResultActionSheet) can wire Save / Add to Trip / Create Trip
 * without re-fetching anything.
 */

import type { RestaurantSearchResult, AttractionSearchResult } from "@/types";

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
  /** Flight passenger count */
  passengers?: number;
  /** Cabin class for flights */
  cabinClass?: string;
  /** Provider-assigned place identity (Google Place ID etc.) */
  providerIdentity?: string;
  /** Original provider payload — typed per vertical */
  originalPayload: RestaurantSearchResult | AttractionSearchResult | Record<string, unknown>;
}
