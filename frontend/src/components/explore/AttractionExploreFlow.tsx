"use client";

/**
 * Attractions vertical — live via tripless AI Concierge (Stage 2A Slice 4).
 *
 * Calls callConciergeSearch(null, query, undefined, destination) — no trip_id
 * required (Slice 3 made the Concierge trip-optional). Returns
 * UnifiedAttractionResult cards verified by Google Places.
 */

import { useState } from "react";
import { Search, MapPin, Tag, Star, ExternalLink, Landmark, Loader2, AlertCircle } from "lucide-react";
import { callConciergeSearch } from "@/lib/api";
import type { UnifiedAttractionResult } from "@/lib/api";
import type { ExploreResultContext } from "./types";
import { ResultActionSheet } from "./ResultActionSheet";

export function AttractionExploreFlow() {
  const [destination, setDestination] = useState("");
  const [interest, setInterest] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<UnifiedAttractionResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [lastDestination, setLastDestination] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const dest = destination.trim();
    if (!dest) return;

    const query = interest.trim()
      ? `${interest.trim()} in ${dest}`
      : `top attractions in ${dest}`;

    setLoading(true);
    setError(null);
    setSearched(true);
    setLastDestination(dest);
    setResults(null);

    try {
      const res = await callConciergeSearch(null, query, undefined, dest);
      setResults(res.attractions);
      if (res.attractions.length === 0) {
        setError("No attractions found for this destination. Try a different area or interest.");
      }
    } catch {
      setError("Search failed. Please try again.");
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  function buildContext(a: UnifiedAttractionResult): ExploreResultContext {
    const gv = a.googleVerification;
    return {
      vertical: "attractions",
      destination: lastDestination,
      location:
        gv?.lat != null && gv?.lng != null ? { lat: gv.lat, lng: gv.lng } : undefined,
      providerIdentity: gv?.providerPlaceId ?? undefined,
      originalPayload: a as unknown as Record<string, unknown>,
    };
  }

  return (
    <div className="space-y-6">
      {/* Search form */}
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cream-500 pointer-events-none" />
            <input
              type="text"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              placeholder="City or area (e.g. Tokyo, Shinjuku)"
              className="input pl-9 w-full"
              aria-label="Destination"
              required
            />
          </div>
          <div className="relative w-44 shrink-0">
            <Tag className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cream-500 pointer-events-none" />
            <input
              type="text"
              value={interest}
              onChange={(e) => setInterest(e.target.value)}
              placeholder="Interest (optional)"
              className="input pl-9 w-full"
              aria-label="Interest or category"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !destination.trim()}
            className="btn-primary flex items-center gap-2 shrink-0"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            Search
          </button>
        </div>
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
        <div className="space-y-3" aria-label="Loading attractions">
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
          No verified attractions found for{" "}
          <span className="text-cream-300 font-medium">{lastDestination}</span>.
          Try a broader area or different interest.
        </div>
      )}

      {/* Results */}
      {!loading && results && results.length > 0 && (
        <div className="space-y-3" data-testid="attraction-results">
          <p className="text-xs text-cream-500 font-medium uppercase tracking-wider px-1">
            {results.length} attraction{results.length !== 1 ? "s" : ""} in {lastDestination}
          </p>
          {results.map((a, i) => (
            <AttractionCard key={a.name + i} attraction={a} context={buildContext(a)} />
          ))}
        </div>
      )}

      {/* Idle prompt */}
      {!searched && !loading && (
        <div className="text-center py-10 text-cream-500 text-sm">
          Enter a city or area to find top attractions.
        </div>
      )}
    </div>
  );
}

function AttractionCard({
  attraction: a,
  context,
}: {
  attraction: UnifiedAttractionResult;
  context: ExploreResultContext;
}) {
  const displayName = a.display?.displayName ?? a.name;
  const displayWhy = a.display?.displayWhy ?? a.supportingDetails?.whyPick ?? null;
  const address = a.address ?? a.supportingDetails?.address ?? null;

  return (
    <div className="card card-lift p-4">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center shrink-0">
          <Landmark className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-cream-100 leading-tight truncate">
                {displayName}
              </h3>
              <p className="text-xs text-cream-500 mt-0.5 truncate">
                {a.category}{address ? ` · ${address}` : ""}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {a.mapsLink && (
                <a
                  href={a.mapsLink}
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
            {a.rating != null && (
              <span className="flex items-center gap-0.5 text-xs text-amber-400 font-medium">
                <Star className="w-3 h-3 fill-amber-400" />
                {a.rating.toFixed(1)}
                {a.reviewCount != null && (
                  <span className="text-cream-600 font-normal ml-0.5">
                    ({a.reviewCount.toLocaleString()})
                  </span>
                )}
              </span>
            )}
            {a.tags && a.tags.length > 0 && (
              <div className="flex gap-1 flex-wrap">
                {a.tags.slice(0, 3).map((tag) => (
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
