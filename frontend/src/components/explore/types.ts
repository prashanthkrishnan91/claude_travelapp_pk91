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

// ---------------------------------------------------------------------------
// Flight domain types — normalized offer contract (Flights v1 scaffold)
// ---------------------------------------------------------------------------

/**
 * How fresh the flight price is.
 * Adapters MUST set this on every FlightItineraryOffer.
 */
export type LiveCachedStatus = "live" | "cached";

/**
 * Classification of the booking deep-link destination.
 * "search_redirect" links to a third-party search page (e.g. Google Flights) — search only, not booking.
 * "unavailable" means no bookable or searchable link exists for this offer.
 */
export type BookingLinkType = "airline_direct" | "ota" | "provider_deeplink" | "search_redirect" | "unavailable";

export type TripType = "one_way" | "round_trip";

/** One non-stop hop within a journey leg. All fields are provider-sourced. */
export interface FlightSegment {
  airline: string;
  flightNumber: string;
  origin: string;          // IATA
  destination: string;     // IATA
  departureTime: string;   // ISO 8601 UTC
  arrivalTime: string;     // ISO 8601 UTC
  durationMinutes: number;
  aircraftType?: string;
  cabinClass?: string;
}

/** One outbound or return journey, containing one or more segments. */
export interface FlightOfferLeg {
  origin: string;          // IATA
  destination: string;     // IATA
  departureTime: string;   // ISO 8601 UTC
  arrivalTime: string;     // ISO 8601 UTC
  durationMinutes: number;
  stops: number;
  segments: FlightSegment[];
}

/**
 * Cash price from a live provider.
 * NEVER fabricated, estimated, or inferred.
 */
export interface FlightPrice {
  currency: string;        // ISO 4217
  totalAmount: number;     // > 0; total for all passengers
  perPassengerAmount?: number;
  taxesFeesIncluded?: boolean | null;
}

/**
 * External deep-link to complete the booking.
 * When link_type is "unavailable", url is empty.
 * Placeholder/mock URLs are explicitly forbidden.
 */
export interface FlightBookingLink {
  url: string;
  linkType: BookingLinkType;
  providerName: string;    // e.g. "skyscanner_flights"
}

/**
 * Normalized flight offer from an approved provider adapter.
 *
 * This type is NEVER populated by disabled/scaffold adapters.
 * A disabled provider returns no flight cards — the FlightExploreFlow
 * remains in its polished "unavailable" state.
 *
 * Cash price (FlightPrice) is only present when sourced from a live
 * provider; points/award prices are a separate future track.
 */
export interface FlightItineraryOffer {
  kind: "flight_offer";
  provider: string;                    // registry ID, e.g. "skyscanner_flights"
  fetchedAt: string;                   // ISO 8601 UTC
  liveCachedStatus: LiveCachedStatus;
  tripType: TripType;
  origin: string;                      // IATA
  destination: string;                 // IATA
  departureDate: string;               // YYYY-MM-DD
  returnDate?: string;                 // YYYY-MM-DD; undefined for one-way
  passengers: number;
  cabinClass: string;
  outboundLeg: FlightOfferLeg;
  returnLeg?: FlightOfferLeg;          // undefined for one-way
  price: FlightPrice;
  bookingLink: FlightBookingLink;
  aiScore?: number;                    // 0–1 optional AI ranking
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
