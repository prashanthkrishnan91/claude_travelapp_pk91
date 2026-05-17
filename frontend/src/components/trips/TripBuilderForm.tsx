"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Sparkles, Loader2, CheckCircle2, Plane, Hotel, Star, BarChart2, MapPin } from "lucide-react";
import { CityAutocomplete } from "@/components/ui/CityAutocomplete";
import type { AirportSelection } from "@/components/ui/CityAutocomplete";

type ProviderUnavailableState = {
  kind: "provider_unavailable";
  message: string;
};

const PROVIDER_UNAVAILABLE_COPY =
  "Flights and hotels are temporarily unavailable because provider-backed search is not enabled yet. You can still create a blank trip and add items manually.";

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
  const [providerUnavailable, setProviderUnavailable] = useState<ProviderUnavailableState | null>(null);
  const [creatingBlank, setCreatingBlank] = useState(false);

  const canSubmit = !!originSel && !!destSel && !!startDate && !!endDate;

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;

    setCreating(true);
    setError(null);
    setProviderUnavailable(null);
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
      const apiErr = err as Error & { code?: string; status?: number };
      if (apiErr?.code === "provider_unavailable" || apiErr?.status === 503) {
        setProviderUnavailable({
          kind: "provider_unavailable",
          message: apiErr?.message || PROVIDER_UNAVAILABLE_COPY,
        });
      } else {
        setError(err instanceof Error ? err.message : "Failed to create trip. Please try again.");
      }
      setCreating(false);
      setStepIndex(0);
    }
  }

  async function handleCreateBlankTrip() {
    if (!destSel || !startDate || !endDate) return;
    setCreatingBlank(true);
    try {
      const { createTrip } = await import("@/lib/api");
      const trip = await createTrip({
        title: `${destSel.city} Trip`,
        destination: destSel.city,
        origin: originSel?.city ?? "",
        startDate,
        endDate,
        travelers: 1,
        budgetCash: "",
        budgetCurrency: "USD",
        notes: "",
      });
      router.push(`/trips/${trip.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create a blank trip.");
      setCreatingBlank(false);
    }
  }

  // ── Step loader view ────────────────────────────────────────────────────────
  if (creating) {
    return (
      <div className="w-full max-w-md atelier-transition" data-testid="new-trip-loading-state">
        <div className="rounded-xl border border-ds-pen-stroke bg-ds-onyx p-8 text-center boutique-instrument">
          <div className="w-14 h-14 rounded-2xl bg-ds-accent-subtle flex items-center justify-center mx-auto mb-5">
            <Sparkles className="w-7 h-7 text-ds-accent animate-pulse" />
          </div>
          <h2 className="text-lg font-semibold text-ds-text mb-1">Your AI concierge is working</h2>
          <p className="text-sm text-ds-text-tertiary mb-7">Finding the best flights and hotels for your trip…</p>

          <div className="space-y-3 text-left" data-testid="new-trip-step-loader">
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
                    <CheckCircle2 className="w-4 h-4 text-ds-trust flex-shrink-0" />
                  ) : active ? (
                    <Loader2 className="w-4 h-4 text-ds-accent animate-spin flex-shrink-0" />
                  ) : (
                    <Icon className="w-4 h-4 text-ds-pen-stroke flex-shrink-0" />
                  )}
                  <span className={done ? "text-ds-text-tertiary" : active ? "text-ds-text font-medium" : "text-ds-text-tertiary opacity-60"}>
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
    <div className="w-full max-w-lg atelier-transition editorial-scene" data-testid="new-trip-form-container">
      <form onSubmit={handleCreate} className="rounded-xl border border-ds-pen-stroke bg-ds-onyx p-6 sm:p-8 space-y-5 boutique-folio advisor-desk-panel" data-testid="new-trip-builder-form">
        <div>
          <label className="label">Flying from</label>
          <CityAutocomplete
            placeholder="Origin city — e.g. New York, London…"
            value={originSel}
            onChange={setOriginSel}
          />
          {originSel && originSel.airports.length > 1 && (
            <p className="mt-1 text-xs text-ds-accent flex items-center gap-1">
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
            <p className="mt-1 text-xs text-ds-accent flex items-center gap-1">
              <Plane className="w-3 h-3" />
              {destSel.airports.length} airports: {destSel.airports.join(", ")}
            </p>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
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
          <div className="rounded-xl border border-ds-pen-stroke bg-ds-carbon px-4 py-2.5 text-sm text-ds-text-secondary" data-testid="trip-length-info">
            <span className="font-medium text-ds-text">Trip length: </span>
            {Math.max(1, Math.ceil(
              (new Date(endDate).getTime() - new Date(startDate).getTime()) / (1000 * 60 * 60 * 24)
            ))}{" "}
            nights
          </div>
        )}

        {providerUnavailable && (
          <div
            role="alert"
            data-testid="trip-builder-provider-unavailable"
            className="rounded-xl border border-ds-caution/20 px-4 py-3 text-sm space-y-2"
            style={{ background: "color-mix(in srgb, var(--ds-caution) 8%, transparent)" }}
          >
            <p className="font-semibold text-ds-caution">Flights &amp; hotels search is temporarily unavailable</p>
            <p className="text-ds-text-tertiary">{PROVIDER_UNAVAILABLE_COPY}</p>
            <button
              type="button"
              onClick={handleCreateBlankTrip}
              disabled={creatingBlank || !destSel || !startDate || !endDate}
              className="inline-flex items-center gap-1.5 text-ds-accent underline underline-offset-2 hover:text-ds-accent-muted disabled:opacity-50 disabled:no-underline"
            >
              {creatingBlank ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Creating blank trip…
                </>
              ) : (
                "Create a blank trip and add items manually"
              )}
            </button>
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="rounded-xl border border-ds-warning/30 px-4 py-3 text-sm text-ds-warning"
            style={{ background: "color-mix(in srgb, var(--ds-warning) 8%, transparent)" }}
          >
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

        <p className="text-xs text-ds-text-tertiary text-center">
          Your AI concierge will automatically find and rank the best flights and hotels.
        </p>
      </form>
    </div>
  );
}
