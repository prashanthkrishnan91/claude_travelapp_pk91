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

const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];
// Parse YYYY-MM-DD by splitting to avoid timezone shifts from new Date(isoDate)
function formatIsoDateForDisplay(iso: string): string | undefined {
  const parts = iso.split('-');
  if (parts.length !== 3) return undefined;
  const month = parseInt(parts[1], 10);
  const day = parseInt(parts[2], 10);
  const year = parseInt(parts[0], 10);
  if (!month || !day || !year || month < 1 || month > 12) return undefined;
  return `${MONTHS[month - 1]} ${day} ${year}`;
}

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
  const checkInDisplay = checkIn ? formatIsoDateForDisplay(checkIn) : undefined;
  const checkOutDisplay = checkOut ? formatIsoDateForDisplay(checkOut) : undefined;
  if (checkInDisplay) qParts.push(checkInDisplay);
  if (checkOutDisplay) qParts.push(`to ${checkOutDisplay}`);
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
import { Card } from "@/components/ui/Card";
import { TrustStrip } from "@/components/ui/TrustStrip";

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
          <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ds-text-tertiary pointer-events-none" />
          <input
            type="text"
            value={form.destination}
            onChange={(e) => set("destination", e.target.value)}
            placeholder="Destination city"
            className="input pl-9 w-full"
            aria-label="Destination"
            required
          />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ds-text-tertiary pointer-events-none" />
            <input
              type="date"
              value={form.checkIn}
              onChange={(e) => set("checkIn", e.target.value)}
              className="input pl-9 w-full"
              aria-label="Check-in date"
            />
          </div>
          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ds-text-tertiary pointer-events-none" />
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
            <Users className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ds-text-tertiary pointer-events-none" />
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
        <div className="flex items-start gap-2 p-3 rounded-xl border text-sm text-ds-warning border-ds-warning/20 bg-ds-warning/10">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-3" aria-label="Loading hotels">
          {[1, 2, 3].map((i) => (
            <Card tone="dark" key={i} className="animate-pulse" style={{ padding: "var(--ds-space-5)" }}>
              <div className="flex gap-3">
                <div className="w-10 h-10 rounded-xl bg-ds-pen-stroke shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-ds-pen-stroke rounded w-3/4" />
                  <div className="h-3 bg-ds-pen-stroke rounded w-1/2" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && searched && results !== null && results.length === 0 && !error && (
        <div className="text-center py-10 text-ds-text-tertiary text-sm">
          No verified hotels found for{" "}
          <span className="text-ds-text font-medium">{lastForm?.destination}</span>.
          Try a broader area.
        </div>
      )}

      {/* Results */}
      {!loading && results && results.length > 0 && (
        <div className="space-y-3" data-testid="hotel-results">
          <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-text-tertiary px-1" data-testid="explore-results-header">
            {results.length} hotel{results.length !== 1 ? "s" : ""} in {lastForm?.destination}
          </p>
          {results.map((h, i) => (
            <HotelCard key={h.id + i} hotel={h} context={buildContext(h)} />
          ))}
        </div>
      )}

      {/* Idle prompt */}
      {!searched && !loading && (
        <div className="text-center py-8 text-ds-text-tertiary text-sm">
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
    <Card tone="dark" as="article" className="card-lift" style={{ padding: "var(--ds-space-5)" }}>
      <Card.Identity>
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 text-ds-accent"
          style={{ backgroundColor: "var(--ds-accent-subtle)" }}
          aria-hidden="true"
        >
          <Building2 className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-ds-text leading-tight truncate">
                {h.name}
              </h3>
              <p className="text-xs text-ds-text-tertiary mt-0.5 truncate">
                {h.address || "Hotel"}
              </p>
            </div>
            {h.googleMapsUri && (
              <a
                href={h.googleMapsUri}
                target="_blank"
                rel="noopener noreferrer"
                className="min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg bg-ds-carbon hover:bg-ds-pen-stroke text-ds-text-tertiary hover:text-ds-text-secondary transition-colors shrink-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                aria-label={`View ${h.name} on Google Maps`}
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
        </div>
      </Card.Identity>

      {h.googlePlaceId && (
        <Card.Trust className="mt-2">
          <TrustStrip sourceCount={1} />
        </Card.Trust>
      )}

      <Card.Meta className="mt-2">
        {h.rating != null && (
          <span className="flex items-center gap-0.5 text-xs text-ds-accent font-medium">
            <Star className="w-3 h-3 fill-current" />
            {h.rating.toFixed(1)}
          </span>
        )}
      </Card.Meta>

      {compareLink && (
        <div className="mt-2">
          <a
            href={compareLink}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 min-h-[44px] rounded-lg text-ds-accent text-xs transition-colors hover:text-ds-accent-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
            style={{ backgroundColor: "var(--ds-accent-subtle)" }}
            aria-label={`Compare prices for ${h.name}`}
            data-testid="hotel-compare-cta"
          >
            <Search className="w-3 h-3" />
            Compare prices
          </a>
        </div>
      )}

      <Card.Actions className="mt-3">
        <ResultActionSheet context={context} />
      </Card.Actions>
    </Card>
  );
}
