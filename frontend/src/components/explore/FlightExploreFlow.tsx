"use client";

/**
 * Flights vertical — live Ignav-backed search (Flights v1).
 *
 * Calls POST /explore/flights when the form is submitted.
 * Renders compact flight cards when offers are returned.
 * Falls back to polished unavailable/error states when provider is off or errors.
 *
 * Safety invariants:
 * - No mock/placeholder flight data ever rendered.
 * - Cash price only from provider (never estimated).
 * - No points prices (separately gated track).
 * - IGNAV_API_KEY is server-side only; no NEXT_PUBLIC_ key exposure.
 */

import { useState } from "react";
import {
  Plane,
  Calendar,
  Users,
  ArrowRight,
  Construction,
  ExternalLink,
  Clock,
  AlertCircle,
} from "lucide-react";
import { searchFlightsExplore } from "@/lib/api";
import type { FlightExploreRequest, FlightExploreResponse } from "@/lib/api";
import type { FlightItineraryOffer, ExploreResultContext } from "./types";
import { ResultActionSheet } from "./ResultActionSheet";

// ---------------------------------------------------------------------------
// Form types
// ---------------------------------------------------------------------------

interface FlightFormValues {
  origin: string;
  destination: string;
  departure: string;
  returnDate: string;
  passengers: number;
  cabinClass: "economy" | "premium_economy" | "business" | "first";
}

type SearchState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "results"; response: FlightExploreResponse }
  | { kind: "error"; message: string };

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTime(isoStr: string): string {
  if (!isoStr) return "--:--";
  try {
    // Prefer parsing as UTC; strip trailing Z for display
    const d = new Date(isoStr);
    return d.toUTCString().slice(17, 22); // "HH:MM"
  } catch {
    return isoStr.slice(11, 16);
  }
}

function formatDuration(minutes: number): string {
  if (!minutes) return "--";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function formatPrice(currency: string, amount: number): string {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${currency} ${amount.toFixed(0)}`;
  }
}

function cabinLabel(cabin: string): string {
  return cabin.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function buildFlightContext(
  offer: FlightItineraryOffer,
  formValues: FlightFormValues
): ExploreResultContext {
  const label =
    `${offer.origin} → ${offer.destination}` +
    (offer.tripType === "round_trip" ? " (round-trip)" : "");

  return {
    vertical: "flights",
    destination: offer.destination,
    origin: offer.origin,
    dates: {
      departure: offer.departureDate,
      returnDate: offer.returnDate ?? undefined,
    },
    passengers: offer.passengers,
    cabinClass: offer.cabinClass,
    originalPayload: {
      // Flight offer fields for saved-item display snapshot
      name: label,
      origin: offer.origin,
      destination: offer.destination,
      departureDate: offer.departureDate,
      returnDate: offer.returnDate ?? undefined,
      tripType: offer.tripType,
      passengers: offer.passengers,
      cabinClass: offer.cabinClass,
      price: offer.price,
      bookingLink: offer.bookingLink,
      provider: offer.provider,
      liveCachedStatus: offer.liveCachedStatus,
      fetchedAt: offer.fetchedAt,
      outboundLeg: offer.outboundLeg,
      returnLeg: offer.returnLeg ?? undefined,
    },
  };
}

// ---------------------------------------------------------------------------
// FlightCard
// ---------------------------------------------------------------------------

function FlightCard({
  offer,
  formValues,
}: {
  offer: FlightItineraryOffer;
  formValues: FlightFormValues;
}) {
  const ob = offer.outboundLeg;
  const ret = offer.returnLeg;
  const airline =
    ob.segments[0]?.airline ?? "Unknown airline";
  const flightNumbers = ob.segments.map((s) => s.flightNumber).join(", ");
  const hasBookingLink =
    offer.bookingLink.linkType !== "unavailable" && offer.bookingLink.url;
  const context = buildFlightContext(offer, formValues);

  return (
    <div
      className="rounded-2xl border border-white/[.08] bg-white/[.03] p-4 space-y-3"
      data-testid="flight-card"
    >
      {/* Header row: airline + price */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <Plane className="w-3.5 h-3.5 text-sky-400 shrink-0" />
            <span
              className="text-sm font-semibold text-cream-100 truncate"
              data-testid="flight-airline"
            >
              {airline}
            </span>
            <span className="text-xs text-cream-600">{flightNumbers}</span>
          </div>
          <p className="text-xs text-cream-500 mt-0.5">
            {cabinLabel(offer.cabinClass)} ·{" "}
            {offer.passengers} pax
          </p>
        </div>
        <div className="text-right shrink-0">
          <p
            className="text-base font-bold text-cream-100"
            data-testid="flight-price"
          >
            {formatPrice(offer.price.currency, offer.price.totalAmount)}
          </p>
          <p className="text-[10px] text-cream-600 uppercase tracking-wide">
            {offer.price.taxesFeesIncluded === true
              ? "taxes incl."
              : offer.price.taxesFeesIncluded === false
              ? "+ taxes"
              : "total"}
          </p>
        </div>
      </div>

      {/* Outbound leg */}
      <LegRow leg={ob} label={offer.tripType === "round_trip" ? "Outbound" : undefined} />

      {/* Return leg (round-trip only) */}
      {ret && <LegRow leg={ret} label="Return" />}

      {/* Live status badge + booking CTA */}
      <div className="flex items-center justify-between pt-1 border-t border-white/[.05]">
        <span
          className={[
            "text-[10px] font-medium px-2 py-0.5 rounded-full uppercase tracking-wide",
            offer.liveCachedStatus === "live"
              ? "bg-emerald-500/10 text-emerald-400"
              : "bg-amber-500/10 text-amber-400",
          ].join(" ")}
          data-testid="flight-live-status"
        >
          {offer.liveCachedStatus}
        </span>

        {hasBookingLink ? (
          <a
            href={offer.bookingLink.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-500/15 text-sky-300 text-xs font-medium hover:bg-sky-500/25 transition"
            data-testid="flight-book-link"
            aria-label={`Book flight on ${offer.bookingLink.providerName}`}
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Book
          </a>
        ) : (
          <span className="text-xs text-cream-700 italic">
            Booking link unavailable
          </span>
        )}
      </div>

      {/* Save action */}
      <ResultActionSheet context={context} />
    </div>
  );
}

function LegRow({
  leg,
  label,
}: {
  leg: FlightItineraryOffer["outboundLeg"];
  label?: string;
}) {
  return (
    <div className="space-y-1">
      {label && (
        <p className="text-[10px] uppercase tracking-wide text-cream-600 font-medium">
          {label}
        </p>
      )}
      <div className="flex items-center gap-2 text-sm">
        <span className="font-semibold text-cream-100 w-11 shrink-0">
          {formatTime(leg.departureTime)}
        </span>
        <span className="text-cream-500 font-medium">{leg.origin}</span>
        <ArrowRight className="w-3 h-3 text-cream-600 shrink-0" />
        <span className="text-cream-500 font-medium">{leg.destination}</span>
        <span className="font-semibold text-cream-100">
          {formatTime(leg.arrivalTime)}
        </span>
      </div>
      <div className="flex items-center gap-3 text-xs text-cream-600">
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {formatDuration(leg.durationMinutes)}
        </span>
        <span>
          {leg.stops === 0
            ? "Non-stop"
            : leg.stops === 1
            ? "1 stop"
            : `${leg.stops} stops`}
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Unavailable / error states
// ---------------------------------------------------------------------------

function UnavailableState() {
  return (
    <div
      className="rounded-2xl border border-sky-500/20 bg-sky-500/5 p-6 text-center space-y-3"
      data-testid="flight-unavailable-state"
      role="status"
      aria-live="polite"
    >
      <div className="flex justify-center">
        <div className="w-12 h-12 rounded-full bg-sky-500/10 text-sky-400 flex items-center justify-center">
          <Construction className="w-6 h-6" />
        </div>
      </div>
      <div>
        <p className="text-cream-200 font-semibold text-sm">
          Flight search unavailable
        </p>
        <p className="text-cream-500 text-xs mt-1">
          Live flight search is not available at the moment. Please try again
          later.
        </p>
      </div>
    </div>
  );
}

function EmptyState({
  origin,
  destination,
}: {
  origin: string;
  destination: string;
}) {
  return (
    <div
      className="rounded-2xl border border-white/[.06] bg-white/[.02] p-6 text-center space-y-2"
      data-testid="flight-empty-state"
      role="status"
    >
      <Plane className="w-8 h-8 text-cream-600 mx-auto" />
      <p className="text-cream-300 text-sm font-medium">No flights found</p>
      <p className="text-cream-600 text-xs">
        No available flights for {origin} → {destination}. Try different dates
        or airports.
      </p>
    </div>
  );
}

function ErrorState({ message }: { message?: string }) {
  return (
    <div
      className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-5 flex items-start gap-3"
      data-testid="flight-error-state"
      role="alert"
    >
      <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
      <div>
        <p className="text-sm font-medium text-rose-300">Search failed</p>
        <p className="text-xs text-cream-500 mt-0.5">
          {message ?? "Could not complete flight search. Please try again."}
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function FlightExploreFlow() {
  const [form, setForm] = useState<FlightFormValues>({
    origin: "",
    destination: "",
    departure: "",
    returnDate: "",
    passengers: 1,
    cabinClass: "economy",
  });
  const [searchState, setSearchState] = useState<SearchState>({ kind: "idle" });
  const [originError, setOriginError] = useState("");
  const [destError, setDestError] = useState("");

  function validateIata(code: string): boolean {
    return /^[A-Za-z]{3}$/.test(code.trim());
  }

  function setField(field: keyof FlightFormValues, value: string | number) {
    if (field === "origin") setOriginError("");
    if (field === "destination") setDestError("");
    setSearchState({ kind: "idle" });
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    let valid = true;
    if (!validateIata(form.origin)) {
      setOriginError("Enter a 3-letter IATA code (e.g. JFK)");
      valid = false;
    }
    if (!validateIata(form.destination)) {
      setDestError("Enter a 3-letter IATA code (e.g. CDG)");
      valid = false;
    }
    if (!valid || !form.departure) return;

    setSearchState({ kind: "loading" });

    const req: FlightExploreRequest = {
      origin: form.origin.trim().toUpperCase(),
      destination: form.destination.trim().toUpperCase(),
      departureDate: form.departure,
      passengers: form.passengers,
      cabinClass: form.cabinClass,
    };
    if (form.returnDate) {
      req.returnDate = form.returnDate;
    }

    try {
      const response = await searchFlightsExplore(req);
      setSearchState({ kind: "results", response });
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Unexpected error during search";
      setSearchState({ kind: "error", message: msg });
    }
  }

  const isLoading = searchState.kind === "loading";

  return (
    <div className="space-y-6">
      {/* Search form */}
      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Origin / Destination */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="relative">
              <Plane className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cream-500 pointer-events-none rotate-45" />
              <input
                type="text"
                value={form.origin}
                onChange={(e) => setField("origin", e.target.value.toUpperCase())}
                placeholder="Origin — JFK"
                maxLength={3}
                className={`input pl-9 w-full uppercase tracking-widest ${originError ? "border-rose-500/60" : ""}`}
                aria-label="Origin airport code"
                required
              />
            </div>
            {originError && (
              <p className="text-xs text-rose-400 mt-1">{originError}</p>
            )}
          </div>
          <div>
            <div className="relative">
              <ArrowRight className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cream-500 pointer-events-none" />
              <input
                type="text"
                value={form.destination}
                onChange={(e) =>
                  setField("destination", e.target.value.toUpperCase())
                }
                placeholder="Destination — CDG"
                maxLength={3}
                className={`input pl-9 w-full uppercase tracking-widest ${destError ? "border-rose-500/60" : ""}`}
                aria-label="Destination airport code"
                required
              />
            </div>
            {destError && (
              <p className="text-xs text-rose-400 mt-1">{destError}</p>
            )}
          </div>
        </div>

        {/* Dates */}
        <div className="grid grid-cols-2 gap-3">
          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cream-500 pointer-events-none" />
            <input
              type="date"
              value={form.departure}
              onChange={(e) => setField("departure", e.target.value)}
              className="input pl-9 w-full"
              aria-label="Departure date"
              required
            />
          </div>
          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cream-500 pointer-events-none" />
            <input
              type="date"
              value={form.returnDate}
              onChange={(e) => setField("returnDate", e.target.value)}
              min={form.departure || undefined}
              className="input pl-9 w-full"
              aria-label="Return date (optional — leave blank for one-way)"
            />
          </div>
        </div>

        {/* Passengers + Cabin */}
        <div className="grid grid-cols-2 gap-3">
          <div className="relative">
            <Users className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cream-500 pointer-events-none" />
            <input
              type="number"
              value={form.passengers}
              onChange={(e) =>
                setField("passengers", Math.max(1, parseInt(e.target.value) || 1))
              }
              min={1}
              max={9}
              className="input pl-9 w-full"
              aria-label="Number of passengers"
            />
          </div>
          <select
            value={form.cabinClass}
            onChange={(e) => setField("cabinClass", e.target.value)}
            className="input w-full"
            aria-label="Cabin class"
          >
            <option value="economy">Economy</option>
            <option value="premium_economy">Premium Economy</option>
            <option value="business">Business</option>
            <option value="first">First</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={
            isLoading ||
            !form.origin.trim() ||
            !form.destination.trim() ||
            !form.departure
          }
          className="btn-primary w-full flex items-center justify-center gap-2"
          data-testid="flight-search-btn"
        >
          {isLoading ? (
            <>
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Searching…
            </>
          ) : (
            <>
              <Plane className="w-4 h-4" />
              Search Flights
            </>
          )}
        </button>
      </form>

      {/* Results area */}
      {searchState.kind === "idle" && (
        <div className="text-center py-8 text-cream-500 text-sm">
          Enter origin and destination airport codes to search flights.
        </div>
      )}

      {searchState.kind === "results" &&
        (() => {
          const { response } = searchState;
          if (response.status === "ok" && response.offers.length > 0) {
            return (
              <div
                className="space-y-4"
                data-testid="flight-results-list"
              >
                <p className="text-xs text-cream-500">
                  {response.offers.length} flight
                  {response.offers.length !== 1 ? "s" : ""} found · prices from
                  live provider
                </p>
                {response.offers.map((offer, i) => (
                  <FlightCard
                    key={`${offer.provider}-${offer.fetchedAt}-${i}`}
                    offer={offer}
                    formValues={form}
                  />
                ))}
              </div>
            );
          }
          if (response.status === "empty") {
            return (
              <EmptyState
                origin={form.origin.toUpperCase()}
                destination={form.destination.toUpperCase()}
              />
            );
          }
          if (
            response.status === "unavailable" ||
            response.status === "error"
          ) {
            return <UnavailableState />;
          }
          return null;
        })()}

      {searchState.kind === "error" && (
        <ErrorState message={searchState.message} />
      )}
    </div>
  );
}
