"use client";

import { useState, useMemo, type FormEvent } from "react";
import { Loader2, X, AlertCircle } from "lucide-react";
import { CityAutocomplete } from "@/components/ui/CityAutocomplete";
import type { AirportSelection } from "@/components/ui/CityAutocomplete";
import { createTripFromSavedItem } from "@/lib/api";
import type { SavedItem, Trip, TripBuilderFormData } from "@/types";

// ── Prefill helpers (pure, deterministic) ─────────────────────────────────────

function ctxStr(item: SavedItem, key: string): string {
  const v = item.searchContext[key];
  return typeof v === "string" && v ? v : "";
}

function ctxNum(item: SavedItem, key: string): number | null {
  const v = item.searchContext[key];
  return typeof v === "number" ? v : null;
}

function snapStr(item: SavedItem, key: string): string {
  const v = item.displaySnapshot[key];
  return typeof v === "string" && v ? v : "";
}

export interface TripPrefill {
  title: string;
  destination: string;
  origin: string;
  startDate: string;
  endDate: string;
  travelers: number;
}

/**
 * Build prefilled trip form values from a saved item per Stage 3 v3 contract.
 * Trusted sources: searchContext and displaySnapshot only. No fabrication.
 */
export function buildTripPrefillFromSavedItem(item: SavedItem): TripPrefill {
  const v = item.vertical;

  if (v === "flight") {
    const origin = ctxStr(item, "origin");
    const destination = ctxStr(item, "destination");
    const dep = ctxStr(item, "departureDate");
    const ret = ctxStr(item, "returnDate");
    const pax = ctxNum(item, "passengers");
    const title =
      origin && destination
        ? `${origin} → ${destination}`
        : destination
          ? `${destination} trip`
          : "";
    return {
      title,
      destination,
      origin,
      startDate: dep,
      // round-trip: returnDate; one-way: default endDate to departureDate
      endDate: ret || dep,
      travelers: pax ?? 1,
    };
  }

  if (v === "hotel") {
    const destination = ctxStr(item, "destination");
    const ci = ctxStr(item, "checkIn");
    const co = ctxStr(item, "checkOut");
    // if either date is missing, BOTH stay blank
    const bothDates = ci && co;
    const guests = ctxNum(item, "guests");
    return {
      title: destination ? `${destination} trip` : "",
      destination,
      origin: "",
      startDate: bothDates ? ci : "",
      endDate: bothDates ? co : "",
      travelers: guests ?? 1,
    };
  }

  // restaurant / attraction — destination from searchContext OR displaySnapshot
  const destination = ctxStr(item, "destination") || snapStr(item, "destination");
  const name = snapStr(item, "name") || item.displayName;
  return {
    title: destination ? `${destination} trip` : name ? `${name} trip` : "",
    destination,
    origin: "",
    startDate: "",
    endDate: "",
    travelers: 1,
  };
}

// ── Modal ─────────────────────────────────────────────────────────────────────

type SubmitState = "idle" | "submitting" | "error";

export function CreateTripFromSavedModal({
  item,
  onClose,
  onCreated,
}: {
  item: SavedItem;
  onClose: () => void;
  onCreated: (trip: Trip) => void;
}) {
  const prefill = useMemo(() => buildTripPrefillFromSavedItem(item), [item]);

  const [title, setTitle] = useState(prefill.title);
  // Airport autocomplete selections — resolved chips with city/country/IATA airports.
  const [originSel, setOriginSel] = useState<AirportSelection | null>(null);
  const [destSel, setDestSel] = useState<AirportSelection | null>(null);
  const [startDate, setStartDate] = useState(prefill.startDate);
  const [endDate, setEndDate] = useState(prefill.endDate);
  const [travelers, setTravelers] = useState<number>(prefill.travelers);

  // Derive string values used in formData and canSubmit gate.
  const origin = originSel?.city ?? "";
  const destination = destSel?.city ?? "";

  const [state, setState] = useState<SubmitState>("idle");
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    title.trim().length > 0 &&
    origin.trim().length > 0 &&
    destination.trim().length > 0 &&
    startDate.length > 0 &&
    endDate.length > 0 &&
    travelers >= 1 &&
    state !== "submitting";

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    if (endDate < startDate) {
      setError("End date must be on or after start date.");
      setState("error");
      return;
    }

    setState("submitting");
    setError(null);

    const formData: TripBuilderFormData = {
      title: title.trim(),
      destination: destination.trim(),
      origin: origin.trim(),
      startDate,
      endDate,
      travelers,
      budgetCash: "",
      budgetCurrency: "USD",
      notes: "",
    };

    try {
      const trip = await createTripFromSavedItem({
        savedItem: item,
        formData,
        originAirports: originSel?.airports,
        destinationAirports: destSel?.airports,
      });
      onCreated(trip);
    } catch {
      setState("error");
      setError("Could not create trip. Please try again.");
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
      data-testid="create-trip-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-trip-title"
    >
      <div className="w-full max-w-md rounded-2xl bg-dark-100 border border-white/[.08] p-5 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h2
              id="create-trip-title"
              className="text-base font-semibold text-cream-100"
            >
              Create a new trip
            </h2>
            <p className="text-xs text-cream-500 mt-0.5">
              Prefilled from your saved {item.vertical}. Edit anything before saving.
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={state === "submitting"}
            aria-label="Close"
            className="p-1.5 rounded-lg bg-white/[.04] hover:bg-white/[.10] text-cream-500 transition disabled:opacity-50"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3" data-testid="create-trip-form">
          <div>
            <label className="block text-[10px] uppercase tracking-wide text-cream-500 mb-1">
              Trip title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-lg bg-white/[.04] border border-white/[.06] text-sm text-cream-100 focus:outline-none focus:border-brand-400"
              data-testid="ct-title"
            />
          </div>

          <div>
            <label className="block text-[10px] uppercase tracking-wide text-cream-500 mb-1">
              Origin
            </label>
            <div data-testid="ct-origin">
              <CityAutocomplete
                placeholder="City you're flying from"
                value={originSel}
                onChange={setOriginSel}
              />
            </div>
          </div>

          <div>
            <label className="block text-[10px] uppercase tracking-wide text-cream-500 mb-1">
              Destination
            </label>
            <div data-testid="ct-destination">
              <CityAutocomplete
                placeholder="Destination city"
                value={destSel}
                onChange={setDestSel}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] uppercase tracking-wide text-cream-500 mb-1">
                Start date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
                className="w-full px-3 py-2 rounded-lg bg-white/[.04] border border-white/[.06] text-sm text-cream-100 focus:outline-none focus:border-brand-400"
                data-testid="ct-start-date"
              />
            </div>
            <div>
              <label className="block text-[10px] uppercase tracking-wide text-cream-500 mb-1">
                End date
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
                className="w-full px-3 py-2 rounded-lg bg-white/[.04] border border-white/[.06] text-sm text-cream-100 focus:outline-none focus:border-brand-400"
                data-testid="ct-end-date"
              />
            </div>
          </div>

          <div>
            <label className="block text-[10px] uppercase tracking-wide text-cream-500 mb-1">
              Travelers
            </label>
            <input
              type="number"
              min={1}
              value={travelers}
              onChange={(e) => setTravelers(Math.max(1, Number(e.target.value) || 1))}
              className="w-full px-3 py-2 rounded-lg bg-white/[.04] border border-white/[.06] text-sm text-cream-100 focus:outline-none focus:border-brand-400"
              data-testid="ct-travelers"
            />
          </div>

          {state === "error" && error && (
            <div
              className="flex items-start gap-2 px-3 py-2 rounded-lg bg-rose-500/10 text-rose-300 text-xs"
              data-testid="ct-error"
            >
              <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              disabled={state === "submitting"}
              className="px-3 py-2 rounded-lg text-xs text-cream-400 hover:text-cream-200 transition disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canSubmit}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-500 text-dark-50 text-xs font-medium hover:bg-brand-600 transition disabled:opacity-50"
              data-testid="ct-submit"
            >
              {state === "submitting" ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Creating trip…
                </>
              ) : (
                "Create trip"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
