"use client";

/**
 * Hotels vertical — live discovery via tripless AI Concierge (Stage 2A Slice 5C).
 *
 * Discovery-only lodging cards: Google Places verified hotels, no rates,
 * no prices, no availability. Search context (destination, dates, guests)
 * is preserved in ExploreResultContext for a future provider-backed offer.
 *
 * Calls callConciergeSearch(null, query, undefined, destination) — no trip_id
 * required (Slice 3 made the Concierge trip-optional). Returns
 * UnifiedHotelResult cards verified by Google Places.
 */

import { useState } from "react";
import { MapPin, Calendar, Users, Building2, Hotel, Star, ExternalLink, Loader2, AlertCircle } from "lucide-react";
import { callConciergeSearch } from "@/lib/api";
import type { UnifiedHotelResult } from "@/lib/api";
import type { ExploreResultContext } from "./types";
import { ResultActionSheet } from "./ResultActionSheet";

interface HotelFormValues {
  destination: string;
  checkIn: string;
  checkOut: string;
  guests: number;
}

export function HotelExploreFlow() {
  const [form, setForm] = useState<HotelFormValues>({
    destination: "",
    checkIn: "",
    checkOut: "",
    guests: 2,
  });
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<UnifiedHotelResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [lastForm, setLastForm] = useState<HotelFormValues | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const dest = form.destination.trim();
    if (!dest) return;

    const query = `hotels in ${dest}`;

    setLoading(true);
    setError(null);
    setSearched(true);
    setLastForm({ ...form });
    setResults(null);

    try {
      const res = await callConciergeSearch(null, query, undefined, dest);
      setResults(res.hotels);
      if (res.hotels.length === 0) {
        setError("No hotels found for this destination. Try a different area.");
      }
    } catch {
      setError("Search failed. Please try again.");
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  function set(field: keyof HotelFormValues, value: string | number) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function buildContext(h: UnifiedHotelResult): ExploreResultContext {
    const gv = h.googleVerification;
    return {
      vertical: "hotels",
      destination: lastForm?.destination ?? form.destination.trim(),
      dates: { checkIn: lastForm?.checkIn || undefined, checkOut: lastForm?.checkOut || undefined },
      guests: lastForm?.guests,
      location:
        gv?.lat != null && gv?.lng != null ? { lat: gv.lat, lng: gv.lng } : undefined,
      providerIdentity: gv?.providerPlaceId ?? undefined,
      originalPayload: h as unknown as Record<string, unknown>,
    };
  }

  return (
    <div className="space-y-6">
      {/* Search form */}
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
          disabled={loading || !form.destination.trim()}
          className="btn-primary w-full flex items-center justify-center gap-2"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Hotel className="w-4 h-4" />
          )}
          {loading ? "Searching…" : "Search Hotels"}
        </button>
      </form>

      {/* Error state */}
      {error && !loading && (
        <div className="flex items-start gap-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-3" aria-label="Loading hotels">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card p-4 animate-pulse">
              <div className="flex gap-3">
                <div className="w-10 h-10 rounded-xl bg-white/[.06] shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-white/[.06] rounded w-3/4" />
                  <div className="h-3 bg-white/[.06] rounded w-1/2" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && searched && results !== null && results.length === 0 && !error && (
        <div className="text-center py-10 text-cream-500 text-sm">
          No verified hotels found for{" "}
          <span className="text-cream-300 font-medium">{lastForm?.destination}</span>.
          Try a broader area.
        </div>
      )}

      {/* Results */}
      {!loading && results && results.length > 0 && (
        <div className="space-y-3" data-testid="hotel-results">
          <p className="text-xs text-cream-500 font-medium uppercase tracking-wider px-1">
            {results.length} hotel{results.length !== 1 ? "s" : ""} in {lastForm?.destination}
          </p>
          {results.map((h, i) => (
            <HotelCard key={h.name + i} hotel={h} context={buildContext(h)} />
          ))}
        </div>
      )}

      {/* Idle prompt */}
      {!searched && !loading && (
        <div className="text-center py-8 text-cream-500 text-sm">
          Enter your destination to find places to stay.
        </div>
      )}
    </div>
  );
}

function HotelCard({
  hotel: h,
  context,
}: {
  hotel: UnifiedHotelResult;
  context: ExploreResultContext;
}) {
  const displayName = h.display?.displayName ?? h.name;
  const displayWhy = h.display?.displayWhy ?? h.supportingDetails?.whyPick ?? null;
  const address = h.supportingDetails?.address ?? null;
  const areaLabel = h.areaLabel ?? null;

  return (
    <div className="card card-lift p-4">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl bg-violet-500/10 text-violet-400 flex items-center justify-center shrink-0">
          <Building2 className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-cream-100 leading-tight truncate">
                {displayName}
              </h3>
              <p className="text-xs text-cream-500 mt-0.5 truncate">
                {areaLabel ?? address ?? "Hotel"}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {h.mapsLink && (
                <a
                  href={h.mapsLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1.5 rounded-lg bg-white/[.05] hover:bg-white/[.10] text-cream-400 transition"
                  aria-label={`View ${displayName} on Google Maps`}
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3 mt-2 flex-wrap">
            {h.stars != null && h.stars > 0 && (
              <span className="text-xs text-amber-300 font-medium" aria-label={`${h.stars} stars`}>
                {"★".repeat(Math.min(h.stars, 5))}
              </span>
            )}
            {h.rating != null && (
              <span className="flex items-center gap-0.5 text-xs text-amber-400 font-medium">
                <Star className="w-3 h-3 fill-amber-400" />
                {h.rating.toFixed(1)}
              </span>
            )}
            {h.tags && h.tags.length > 0 && (
              <div className="flex gap-1 flex-wrap">
                {h.tags.slice(0, 3).map((tag) => (
                  <span
                    key={tag}
                    className="px-1.5 py-0.5 text-[10px] rounded-full bg-white/[.06] text-cream-400"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>

          {displayWhy && (
            <p className="text-xs text-cream-400 mt-2 leading-relaxed line-clamp-2">
              {displayWhy}
            </p>
          )}

          <ResultActionSheet context={context} />
        </div>
      </div>
    </div>
  );
}
