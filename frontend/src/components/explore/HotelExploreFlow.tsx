"use client";

/**
 * Hotels vertical — canonical vertical search.
 *
 * HotelExploreFlow calls the canonical /search/hotels endpoint
 * (searchHotelsExplore), the same Google-Places-backed hotel search service
 * used by /trips/create-with-search seeding.  Explore Hotels is a pure
 * provider-backed discovery surface — it does not depend on the AI Concierge
 * search route and spends no paid research credits.
 *
 * Discovery-only lodging cards: Google Places verified hotels, no rates,
 * no prices, no availability.  Compare prices CTA (v1): deterministic Google
 * Hotels search link-out only — no in-app rates, no OTA booking.
 */

import { useState } from "react";
import { MapPin, Calendar, Users, Building2, Hotel, Star, ExternalLink, Search, Loader2, AlertCircle } from "lucide-react";

/**
 * Build a deterministic Google Hotels comparison search URL.
 * External search link-out only — no price, rate, or availability data.
 */
function buildHotelCompareUrl({
  hotelName,
  destination,
  checkIn,
  checkOut,
  guests,
}: {
  hotelName: string;
  destination: string;
  checkIn?: string;
  checkOut?: string;
  guests?: number;
}): string {
  const qParts = [hotelName, destination];
  if (checkIn) qParts.push(new Date(checkIn).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }));
  if (checkOut) qParts.push(`to ${new Date(checkOut).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}`);
  if (guests && guests > 0) qParts.push(`${guests} guest${guests !== 1 ? 's' : ''}`);
  const q = encodeURIComponent(qParts.join(' '));
  let url = `https://www.google.com/travel/hotels?q=${q}`;
  if (checkIn) url += `&checkin=${encodeURIComponent(checkIn)}`;
  if (checkOut) url += `&checkout=${encodeURIComponent(checkOut)}`;
  if (guests && guests > 0) url += `&adults=${guests}`;
  return url;
}
import { searchHotelsExplore } from "@/lib/api";
import type { ExploreHotelResult } from "@/lib/api";
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
  const [results, setResults] = useState<ExploreHotelResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [lastForm, setLastForm] = useState<HotelFormValues | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const dest = form.destination.trim();
    if (!dest) return;

    setLoading(true);
    setError(null);
    setSearched(true);
    setLastForm({ ...form });
    setResults(null);

    try {
      // Canonical vertical search: Google-Places-backed /search/hotels.
      const res = await searchHotelsExplore(
        dest,
        form.checkIn || undefined,
        form.checkOut || undefined,
        form.guests,
      );
      setResults(res);
      if (res.length === 0) {
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

  function buildContext(h: ExploreHotelResult): ExploreResultContext {
    const dest = lastForm?.destination ?? form.destination.trim();
    // Future-ready compare link: Google Hotels search link-out only, no price fields.
    const compareLink = buildHotelCompareUrl({
      hotelName: h.name,
      destination: dest,
      checkIn: lastForm?.checkIn || undefined,
      checkOut: lastForm?.checkOut || undefined,
      guests: lastForm?.guests,
    });
    // Normalize saved-item display snapshot: discovery fields only, no price/rate/booking.
    const savedPayload: Record<string, unknown> = {
      type: "hotel",
      name: h.name,
      source: h.source,
      rating: h.rating,
      address: h.address,
      mapsLink: h.googleMapsUri,
      googleMapsUri: h.googleMapsUri,
      providerPlaceId: h.googlePlaceId,
      // Search context preserved for future provider-backed offer hydration
      destination: dest,
      checkIn: lastForm?.checkIn || undefined,
      checkOut: lastForm?.checkOut || undefined,
      guests: lastForm?.guests,
      // Compare link metadata (external search link-out only; no price/rate data)
      compareLink,
    };
    return {
      vertical: "hotels",
      destination: dest,
      dates: { checkIn: lastForm?.checkIn || undefined, checkOut: lastForm?.checkOut || undefined },
      guests: lastForm?.guests,
      location:
        h.lat != null && h.lng != null ? { lat: h.lat, lng: h.lng } : undefined,
      providerIdentity: h.googlePlaceId ?? undefined,
      originalPayload: savedPayload,
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
            <HotelCard key={h.id + i} hotel={h} context={buildContext(h)} />
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
  hotel: ExploreHotelResult;
  context: ExploreResultContext;
}) {
  // compareLink is stored by buildContext in originalPayload — external search link-out only.
  const compareLink = (context.originalPayload as Record<string, unknown>).compareLink as string | undefined;

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
                {h.name}
              </h3>
              <p className="text-xs text-cream-500 mt-0.5 truncate">
                {h.address || "Hotel"}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {h.googleMapsUri && (
                <a
                  href={h.googleMapsUri}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1.5 rounded-lg bg-white/[.05] hover:bg-white/[.10] text-cream-400 transition"
                  aria-label={`View ${h.name} on Google Maps`}
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3 mt-2 flex-wrap">
            {h.rating != null && (
              <span className="flex items-center gap-0.5 text-xs text-amber-400 font-medium">
                <Star className="w-3 h-3 fill-amber-400" />
                {h.rating.toFixed(1)}
              </span>
            )}
          </div>

          {compareLink && (
            <div className="mt-2">
              <a
                href={compareLink}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-violet-500/10 hover:bg-violet-500/20 text-violet-300 hover:text-violet-200 text-xs transition"
                aria-label={`Compare prices for ${h.name}`}
                data-testid="hotel-compare-cta"
              >
                <Search className="w-3 h-3" />
                Compare prices
              </a>
            </div>
          )}

          <ResultActionSheet context={context} />
        </div>
      </div>
    </div>
  );
}
