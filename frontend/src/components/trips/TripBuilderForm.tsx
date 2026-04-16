"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Sparkles, Loader2, CheckCircle2, Plane, Hotel, Star, BarChart2, MapPin } from "lucide-react";
import { CityAutocomplete } from "@/components/ui/CityAutocomplete";
import type { AirportSelection } from "@/components/ui/CityAutocomplete";

// ─── Step loader labels ───────────────────────────────────────────────────────

const CREATION_STEPS = [
  { icon: MapPin,     label: "Resolving airports…"   },
  { icon: Plane,      label: "Searching flights…"    },
  { icon: Hotel,      label: "Searching hotels…"     },
  { icon: BarChart2,  label: "Ranking results…"      },
  { icon: Star,       label: "Building your trip…"   },
];

// ─── Main component ───────────────────────────────────────────────────────────

export function TripBuilderForm() {
  const router = useRouter();

  const [originSel,  setOriginSel]  = useState<AirportSelection | null>(null);
  const [destSel,    setDestSel]    = useState<AirportSelection | null>(null);
  const [startDate,  setStartDate]  = useState("");
  const [endDate,    setEndDate]    = useState("");
  const [creating,   setCreating]   = useState(false);
  const [stepIndex,  setStepIndex]  = useState(0);
  const [error,      setError]      = useState<string | null>(null);

  const canSubmit = !!originSel && !!destSel && !!startDate && !!endDate;

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;

    setCreating(true);
    setError(null);
    setStepIndex(0);

    // Advance the step indicator while waiting for the backend
    const interval = setInterval(() => {
      setStepIndex((s) => Math.min(s + 1, CREATION_STEPS.length - 1));
    }, 900);

    try {
      const { createTripWithSearch } = await import("@/lib/api");
      const trip = await createTripWithSearch({
        originCity:          originSel!.city,
        originAirports:      originSel!.airports,
        destinationCity:     destSel!.city,
        destinationAirports: destSel!.airports,
        startDate,
        endDate,
      });
      clearInterval(interval);
      router.push(`/trips/${trip.id}`);
    } catch (err) {
      clearInterval(interval);
      setError(err instanceof Error ? err.message : "Failed to create trip. Please try again.");
      setCreating(false);
      setStepIndex(0);
    }
  }

  // ── Step loader view ────────────────────────────────────────────────────────
  if (creating) {
    return (
      <div className="max-w-md">
        <div className="card p-8 text-center">
          <div className="w-14 h-14 rounded-2xl bg-sky-50 flex items-center justify-center mx-auto mb-5">
            <Sparkles className="w-7 h-7 text-sky-500 animate-pulse" />
          </div>
          <h2 className="text-lg font-bold text-slate-900 mb-1">Your AI concierge is working</h2>
          <p className="text-sm text-slate-500 mb-7">Finding the best flights and hotels for your trip…</p>

          <div className="space-y-3 text-left">
            {CREATION_STEPS.map((step, i) => {
              const done    = i < stepIndex;
              const active  = i === stepIndex;
              const pending = i > stepIndex;
              const Icon    = step.icon;
              return (
                <div
                  key={i}
                  className={`flex items-center gap-3 text-sm transition-opacity ${pending ? "opacity-30" : "opacity-100"}`}
                >
                  {done ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                  ) : active ? (
                    <Loader2 className="w-4 h-4 text-sky-500 animate-spin flex-shrink-0" />
                  ) : (
                    <Icon className="w-4 h-4 text-slate-300 flex-shrink-0" />
                  )}
                  <span className={done ? "text-slate-500" : active ? "text-slate-900 font-medium" : "text-slate-400"}>
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // ── Form view ───────────────────────────────────────────────────────────────
  return (
    <div className="max-w-lg">
      <form onSubmit={handleCreate} className="card p-6 sm:p-8 space-y-5">
        <div>
          <label className="label">Flying from</label>
          <CityAutocomplete
            placeholder="Origin city — e.g. New York, London…"
            value={originSel}
            onChange={setOriginSel}
          />
          {originSel && originSel.airports.length > 1 && (
            <p className="mt-1 text-xs text-sky-600 flex items-center gap-1">
              <Plane className="w-3 h-3" />
              {originSel.airports.length} airports: {originSel.airports.join(", ")}
            </p>
          )}
        </div>

        <div>
          <label className="label">Flying to</label>
          <CityAutocomplete
            placeholder="Destination city — e.g. Tokyo, Paris…"
            value={destSel}
            onChange={setDestSel}
          />
          {destSel && destSel.airports.length > 1 && (
            <p className="mt-1 text-xs text-sky-600 flex items-center gap-1">
              <Plane className="w-3 h-3" />
              {destSel.airports.length} airports: {destSel.airports.join(", ")}
            </p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label" htmlFor="start-date">Departure date</label>
            <input
              id="start-date"
              type="date"
              className="input"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="label" htmlFor="end-date">Return date</label>
            <input
              id="end-date"
              type="date"
              className="input"
              value={endDate}
              min={startDate}
              onChange={(e) => setEndDate(e.target.value)}
              required
            />
          </div>
        </div>

        {startDate && endDate && (
          <div className="rounded-xl bg-sky-50 border border-sky-100 px-4 py-2.5 text-sm text-sky-700">
            <span className="font-medium">Trip length: </span>
            {Math.max(1, Math.ceil(
              (new Date(endDate).getTime() - new Date(startDate).getTime()) / (1000 * 60 * 60 * 24)
            ))}{" "}
            nights
          </div>
        )}

        {error && (
          <div className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <button
          type="submit"
          className="btn-primary w-full"
          disabled={!canSubmit}
        >
          <Sparkles className="w-4 h-4" />
          Create Trip
        </button>

        <p className="text-xs text-slate-400 text-center">
          Your AI concierge will automatically find and rank the best flights and hotels.
        </p>
      </form>
    </div>
  );
}
