"use client";

/**
 * Flights vertical — structured input + deferred state.
 *
 * POST /search/flights requires IATA codes + dates and is classified
 * mock-backed (BLOCK_LEGACY_PRODUCT_MOCK) in Product Surface Pruning v1A.
 * A real provider (Duffel/Amadeus) is needed before this vertical can
 * execute. The form collects origin, destination, dates, passengers, and
 * cabin class so the full context is action-ready for Slice 2.
 */

import { useState } from "react";
import { Plane, Calendar, Users, ArrowRight, Construction } from "lucide-react";
import type { ExploreResultContext } from "./types";

interface FlightFormValues {
  origin: string;
  destination: string;
  departure: string;
  returnDate: string;
  passengers: number;
  cabinClass: "economy" | "premium_economy" | "business" | "first";
}

export function FlightExploreFlow() {
  const [form, setForm] = useState<FlightFormValues>({
    origin: "",
    destination: "",
    departure: "",
    returnDate: "",
    passengers: 1,
    cabinClass: "economy",
  });
  const [submitted, setSubmitted] = useState(false);
  const [savedCtx, setSavedCtx] = useState<ExploreResultContext | null>(null);
  const [originError, setOriginError] = useState("");
  const [destError, setDestError] = useState("");

  function validateIata(code: string): boolean {
    return /^[A-Za-z]{3}$/.test(code.trim());
  }

  function set(field: keyof FlightFormValues, value: string | number) {
    setSubmitted(false);
    if (field === "origin") setOriginError("");
    if (field === "destination") setDestError("");
    setForm((f) => ({ ...f, [field]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
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

    const ctx: ExploreResultContext = {
      vertical: "flights",
      destination: form.destination.trim().toUpperCase(),
      origin: form.origin.trim().toUpperCase(),
      dates: {
        departure: form.departure || undefined,
        returnDate: form.returnDate || undefined,
      },
      passengers: form.passengers,
      cabinClass: form.cabinClass,
      originalPayload: {
        origin: form.origin.trim().toUpperCase(),
        destination: form.destination.trim().toUpperCase(),
        departure: form.departure,
        returnDate: form.returnDate,
        passengers: form.passengers,
        cabinClass: form.cabinClass,
      },
    };
    setSavedCtx(ctx);
    setSubmitted(true);
  }

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Origin / Destination */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="relative">
              <Plane className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cream-500 pointer-events-none rotate-45" />
              <input
                type="text"
                value={form.origin}
                onChange={(e) => set("origin", e.target.value.toUpperCase())}
                placeholder="Origin — JFK"
                maxLength={3}
                className={`input pl-9 w-full uppercase tracking-widest ${originError ? "border-rose-500/60" : ""}`}
                aria-label="Origin airport code"
                required
              />
            </div>
            {originError && <p className="text-xs text-rose-400 mt-1">{originError}</p>}
          </div>
          <div>
            <div className="relative">
              <ArrowRight className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cream-500 pointer-events-none" />
              <input
                type="text"
                value={form.destination}
                onChange={(e) => set("destination", e.target.value.toUpperCase())}
                placeholder="Destination — CDG"
                maxLength={3}
                className={`input pl-9 w-full uppercase tracking-widest ${destError ? "border-rose-500/60" : ""}`}
                aria-label="Destination airport code"
                required
              />
            </div>
            {destError && <p className="text-xs text-rose-400 mt-1">{destError}</p>}
          </div>
        </div>

        {/* Dates */}
        <div className="grid grid-cols-2 gap-3">
          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cream-500 pointer-events-none" />
            <input
              type="date"
              value={form.departure}
              onChange={(e) => set("departure", e.target.value)}
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
              onChange={(e) => set("returnDate", e.target.value)}
              min={form.departure || undefined}
              className="input pl-9 w-full"
              aria-label="Return date (optional)"
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
              onChange={(e) => set("passengers", Math.max(1, parseInt(e.target.value) || 1))}
              min={1}
              max={9}
              className="input pl-9 w-full"
              aria-label="Number of passengers"
            />
          </div>
          <select
            value={form.cabinClass}
            onChange={(e) => set("cabinClass", e.target.value)}
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
          disabled={!form.origin.trim() || !form.destination.trim() || !form.departure}
          className="btn-primary w-full flex items-center justify-center gap-2"
        >
          <Plane className="w-4 h-4" />
          Search Flights
        </button>
      </form>

      {submitted && savedCtx ? (
        <DeferredState ctx={savedCtx} />
      ) : (
        <div className="text-center py-8 text-cream-500 text-sm">
          Enter origin and destination airport codes to search flights.
        </div>
      )}
    </div>
  );
}

function DeferredState({ ctx }: { ctx: ExploreResultContext }) {
  const route = ctx.origin && ctx.destination ? `${ctx.origin} → ${ctx.destination}` : ctx.destination;
  return (
    <div
      className="rounded-2xl border border-sky-500/20 bg-sky-500/5 p-6 text-center space-y-3"
      data-testid="flight-deferred-state"
      role="status"
      aria-live="polite"
    >
      <div className="flex justify-center">
        <div className="w-12 h-12 rounded-full bg-sky-500/10 text-sky-400 flex items-center justify-center">
          <Construction className="w-6 h-6" />
        </div>
      </div>
      <div>
        <p className="text-cream-200 font-semibold text-sm">Live flight search coming soon</p>
        <p className="text-cream-500 text-xs mt-1">
          We&apos;re connecting to real flight providers for{" "}
          <span className="text-cream-300">{route}</span>
          {ctx.dates?.departure ? ` on ${ctx.dates.departure}` : ""}
          {ctx.passengers ? `, ${ctx.passengers} passenger${ctx.passengers !== 1 ? "s" : ""}` : ""}{" "}
          ({ctx.cabinClass?.replace("_", " ")}).
        </p>
      </div>
      <p className="text-xs text-cream-600">
        Live flight search arrives in a future Explore update.
      </p>
    </div>
  );
}
