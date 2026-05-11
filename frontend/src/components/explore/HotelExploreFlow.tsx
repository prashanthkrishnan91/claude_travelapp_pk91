"use client";

/**
 * Hotels vertical — structured input + deferred state.
 *
 * POST /search/hotels is classified mock-backed (BLOCK_LEGACY_PRODUCT_MOCK)
 * in Product Surface Pruning v1A. A real hotel provider is needed before this
 * vertical can execute. The form collects destination + dates + guests so the
 * context is ready for Slice 2 / future execution.
 */

import { useState } from "react";
import { MapPin, Calendar, Users, Hotel, Construction } from "lucide-react";
import type { ExploreResultContext } from "./types";

interface HotelFormValues {
  destination: string;
  checkIn: string;
  checkOut: string;
  guests: number;
}

interface Props {
  /** Called when user confirms the form — carries action-ready context for Slice 2. */
  onDeferred?: (ctx: ExploreResultContext) => void;
}

export function HotelExploreFlow({ onDeferred }: Props) {
  const [form, setForm] = useState<HotelFormValues>({
    destination: "",
    checkIn: "",
    checkOut: "",
    guests: 2,
  });
  const [submitted, setSubmitted] = useState(false);
  const [savedCtx, setSavedCtx] = useState<ExploreResultContext | null>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.destination.trim()) return;
    const ctx: ExploreResultContext = {
      vertical: "hotels",
      destination: form.destination.trim(),
      dates: { checkIn: form.checkIn || undefined, checkOut: form.checkOut || undefined },
      guests: form.guests,
      originalPayload: {
        destination: form.destination.trim(),
        checkIn: form.checkIn,
        checkOut: form.checkOut,
        guests: form.guests,
      },
    };
    setSavedCtx(ctx);
    setSubmitted(true);
    onDeferred?.(ctx);
  }

  function set(field: keyof HotelFormValues, value: string | number) {
    setSubmitted(false);
    setForm((f) => ({ ...f, [field]: value }));
  }

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="relative">
          <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cream-500 pointer-events-none" />
          <input
            type="text"
            value={form.destination}
            onChange={(e) => set("destination", e.target.value)}
            placeholder="Destination city (e.g. Barcelona)"
            className="input pl-9 w-full"
            aria-label="Destination"
            required
          />
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cream-500 pointer-events-none" />
            <input
              type="date"
              value={form.checkIn}
              onChange={(e) => set("checkIn", e.target.value)}
              className="input pl-9 w-full"
              aria-label="Check-in date"
            />
          </div>
          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cream-500 pointer-events-none" />
            <input
              type="date"
              value={form.checkOut}
              onChange={(e) => set("checkOut", e.target.value)}
              min={form.checkIn || undefined}
              className="input pl-9 w-full"
              aria-label="Check-out date"
            />
          </div>
          <div className="relative">
            <Users className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cream-500 pointer-events-none" />
            <input
              type="number"
              value={form.guests}
              onChange={(e) => set("guests", Math.max(1, parseInt(e.target.value) || 1))}
              min={1}
              max={20}
              className="input pl-9 w-full"
              aria-label="Number of guests"
            />
          </div>
        </div>
        <button
          type="submit"
          disabled={!form.destination.trim()}
          className="btn-primary w-full flex items-center justify-center gap-2"
        >
          <Hotel className="w-4 h-4" />
          Search Hotels
        </button>
      </form>

      {submitted && savedCtx ? (
        <DeferredState ctx={savedCtx} />
      ) : (
        <div className="text-center py-8 text-cream-500 text-sm">
          Enter your destination and dates to search hotels.
        </div>
      )}
    </div>
  );
}

function DeferredState({ ctx }: { ctx: ExploreResultContext }) {
  const dateStr =
    ctx.dates?.checkIn && ctx.dates?.checkOut
      ? `${ctx.dates.checkIn} – ${ctx.dates.checkOut}`
      : ctx.dates?.checkIn ?? null;

  return (
    <div
      className="rounded-2xl border border-violet-500/20 bg-violet-500/5 p-6 text-center space-y-3"
      data-testid="hotel-deferred-state"
      role="status"
      aria-live="polite"
    >
      <div className="flex justify-center">
        <div className="w-12 h-12 rounded-full bg-violet-500/10 text-violet-400 flex items-center justify-center">
          <Construction className="w-6 h-6" />
        </div>
      </div>
      <div>
        <p className="text-cream-200 font-semibold text-sm">Live hotel search coming soon</p>
        <p className="text-cream-500 text-xs mt-1">
          We&apos;re connecting to real hotel providers for{" "}
          <span className="text-cream-300">{ctx.destination}</span>
          {dateStr ? ` (${dateStr})` : ""}
          {ctx.guests ? `, ${ctx.guests} guest${ctx.guests !== 1 ? "s" : ""}` : ""}.
        </p>
      </div>
      <p className="text-xs text-cream-600">
        Live hotel search arrives in a future Explore update.
      </p>
    </div>
  );
}
