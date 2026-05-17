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

// ── Airport selection helpers ─────────────────────────────────────────────────

/**
 * Convert a prefill string into an initial CityAutocomplete state.
 * - 3-letter IATA codes (e.g. "SEA") → a resolved AirportSelection
 *   (airports: [code]); `query` stays blank.
 * - Plain city strings (e.g. "boise") → NOT a resolved selection. The string
 *   is returned as `query` so it stays visible and editable, but `selection`
 *   is null so submit stays blocked until the user picks a real city/airport.
 * - Empty string → both null/blank.
 */
function initFromPrefill(prefillStr: string): {
  selection: AirportSelection | null;
  query: string;
} {
  const trimmed = prefillStr.trim();
  if (!trimmed) return { selection: null, query: "" };
  const upper = trimmed.toUpperCase();
  if (/^[A-Z]{3}$/.test(upper)) {
    return { selection: { city: upper, country: "", airports: [upper] }, query: "" };
  }
  // Plain (non-IATA) prefill: visible/editable text, but unresolved.
  return { selection: null, query: trimmed };
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
  // Airport autocomplete state — initialized from prefill via initFromPrefill.
  // IATA prefills (e.g. "SEA") start as a resolved chip with airports:[code].
  // Plain city prefills (e.g. "boise") start UNRESOLVED — the text is seeded
  // into CityAutocomplete's input (visible/editable) but selection is null,
  // so submit stays blocked until the user picks a real city/airport.
  const originInit = useMemo(() => initFromPrefill(prefill.origin), [prefill.origin]);
  const destInit = useMemo(() => initFromPrefill(prefill.destination), [prefill.destination]);
  const [originSel, setOriginSel] = useState<AirportSelection | null>(originInit.selection);
  const [destSel, setDestSel] = useState<AirportSelection | null>(destInit.selection);
  const [startDate, setStartDate] = useState(prefill.startDate);
  const [endDate, setEndDate] = useState(prefill.endDate);
  const [travelers, setTravelers] = useState<number>(prefill.travelers);

  // Derive string values used in formData and canSubmit gate.
  const origin = originSel?.city ?? "";
  const destination = destSel?.city ?? "";

  // A selection counts as resolved only when it carries IATA airport codes —
  // a plain city string is never treated as a completed airport chip.
  const originResolved = !!originSel && originSel.airports.length > 0;
  const destResolved = !!destSel && destSel.airports.length > 0;
  const airportsUnresolved = !originResolved || !destResolved;

  const [state, setState] = useState<SubmitState>("idle");
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    title.trim().length > 0 &&
    originResolved &&
    destResolved &&
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
        // Only forward airport arrays when there are resolved IATA codes.
        // Plain city prefill chips have airports:[] — do not pass them.
        originAirports: originSel?.airports?.length ? originSel.airports : undefined,
        destinationAirports: destSel?.airports?.length ? destSel.airports : undefined,
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
      <div className="w-full max-w-md rounded-2xl bg-ds-onyx border border-ds-pen-stroke p-5 space-y-4 shadow-[var(--ds-elevation-4)]">
        <div className="flex items-start justify-between">
          <div>
            <h2
              id="create-trip-title"
              className="text-base font-semibold text-ds-text"
            >
              Create a new trip
            </h2>
            <p className="text-xs text-ds-text-tertiary mt-0.5">
              Prefilled from your saved {item.vertical}. Edit anything before saving.
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={state === "submitting"}
            aria-label="Close"
            className="min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg bg-ds-carbon hover:bg-ds-pen-stroke text-ds-text-tertiary transition-colors disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
          >
            <X className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3" data-testid="create-trip-form">
          <div>
            <label className="block text-[10px] uppercase tracking-[0.1em] text-ds-text-tertiary mb-1">
              Trip title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-lg bg-ds-carbon border border-ds-pen-stroke text-sm text-ds-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
              data-testid="ct-title"
            />
          </div>

          <div>
            <label className="block text-[10px] uppercase tracking-[0.1em] text-ds-text-tertiary mb-1">
              Origin
            </label>
            <div data-testid="ct-origin">
              <CityAutocomplete
                placeholder="City you're flying from"
                value={originSel}
                onChange={setOriginSel}
                initialQuery={originInit.query}
              />
            </div>
          </div>

          <div>
            <label className="block text-[10px] uppercase tracking-[0.1em] text-ds-text-tertiary mb-1">
              Destination
            </label>
            <div data-testid="ct-destination">
              <CityAutocomplete
                placeholder="Destination city"
                value={destSel}
                onChange={setDestSel}
                initialQuery={destInit.query}
              />
            </div>
          </div>

          {airportsUnresolved && (
            <p
              className="text-[11px] text-ds-caution"
              data-testid="ct-unresolved-hint"
            >
              Select a city/airport from suggestions before creating the trip.
            </p>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] uppercase tracking-[0.1em] text-ds-text-tertiary mb-1">
                Start date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
                className="w-full px-3 py-2 rounded-lg bg-ds-carbon border border-ds-pen-stroke text-sm text-ds-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                data-testid="ct-start-date"
              />
            </div>
            <div>
              <label className="block text-[10px] uppercase tracking-[0.1em] text-ds-text-tertiary mb-1">
                End date
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
                className="w-full px-3 py-2 rounded-lg bg-ds-carbon border border-ds-pen-stroke text-sm text-ds-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                data-testid="ct-end-date"
              />
            </div>
          </div>

          <div>
            <label className="block text-[10px] uppercase tracking-[0.1em] text-ds-text-tertiary mb-1">
              Travelers
            </label>
            <input
              type="number"
              min={1}
              value={travelers}
              onChange={(e) => setTravelers(Math.max(1, Number(e.target.value) || 1))}
              className="w-full px-3 py-2 rounded-lg bg-ds-carbon border border-ds-pen-stroke text-sm text-ds-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
              data-testid="ct-travelers"
            />
          </div>

          {state === "error" && error && (
            <div
              className="flex items-start gap-2 px-3 py-2 rounded-lg bg-ds-carbon text-ds-warning text-xs"
              data-testid="ct-error"
            >
              <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" aria-hidden="true" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              disabled={state === "submitting"}
              className="min-h-[44px] px-3 py-2 rounded-lg text-xs text-ds-text-tertiary hover:text-ds-text transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canSubmit}
              className="min-h-[44px] flex items-center gap-2 px-4 py-2 rounded-lg bg-ds-accent text-ds-text-inverse text-xs font-medium hover:bg-ds-accent-muted transition-colors disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
              data-testid="ct-submit"
            >
              {state === "submitting" ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
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
