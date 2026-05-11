"use client";

import { useState } from "react";
import { Search, MapPin, Star, ExternalLink, Utensils, Loader2, AlertCircle } from "lucide-react";
import { searchRestaurants } from "@/lib/api";
import type { RestaurantSearchResult } from "@/types";
import type { ExploreResultContext } from "./types";

interface Props {
  onResultSelect?: (ctx: ExploreResultContext) => void;
}

export function RestaurantExploreFlow({ onResultSelect }: Props) {
  const [destination, setDestination] = useState("");
  const [cuisine, setCuisine] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<RestaurantSearchResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [lastDestination, setLastDestination] = useState("");

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const dest = destination.trim();
    if (!dest) return;

    setLoading(true);
    setError(null);
    setSearched(true);
    setLastDestination(dest);

    try {
      const envelope = await searchRestaurants(dest);
      setResults(envelope.restaurants);
      if (envelope.terminalNoResults) {
        setError("No restaurants found for this destination. Try a different area.");
      }
    } catch {
      setError("Search failed. Please try again.");
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  function buildContext(r: RestaurantSearchResult): ExploreResultContext {
    return {
      vertical: "restaurants",
      destination: lastDestination,
      location: r.lat != null && r.lng != null ? { lat: r.lat, lng: r.lng } : undefined,
      providerIdentity: r.providerPlaceId ?? r.placeId,
      originalPayload: r,
    };
  }

  return (
    <div className="space-y-6">
      {/* Search form */}
      <form onSubmit={handleSearch} className="space-y-3">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cream-500 pointer-events-none" />
            <input
              type="text"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              placeholder="City or area (e.g. Paris, Marais district)"
              className="input pl-9 w-full"
              aria-label="Destination"
              required
            />
          </div>
          <div className="relative w-40 shrink-0">
            <Utensils className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cream-500 pointer-events-none" />
            <input
              type="text"
              value={cuisine}
              onChange={(e) => setCuisine(e.target.value)}
              placeholder="Cuisine (optional)"
              className="input pl-9 w-full"
              aria-label="Cuisine or vibe"
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
        <div className="space-y-3" aria-label="Loading restaurants">
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

      {/* Empty state after search */}
      {!loading && searched && results !== null && results.length === 0 && !error && (
        <div className="text-center py-10 text-cream-500 text-sm">
          No verified restaurants found for <span className="text-cream-300 font-medium">{lastDestination}</span>.
          Try a broader area or different city name.
        </div>
      )}

      {/* Results */}
      {!loading && results && results.length > 0 && (
        <div className="space-y-3" data-testid="restaurant-results">
          <p className="text-xs text-cream-500 font-medium uppercase tracking-wider px-1">
            {results.length} restaurant{results.length !== 1 ? "s" : ""} in {lastDestination}
          </p>
          {results.map((r) => (
            <RestaurantCard
              key={r.id}
              restaurant={r}
              onSelect={onResultSelect ? () => onResultSelect(buildContext(r)) : undefined}
            />
          ))}
        </div>
      )}

      {/* Idle prompt */}
      {!searched && !loading && (
        <div className="text-center py-10 text-cream-500 text-sm">
          Enter a city or area to discover top-rated restaurants.
        </div>
      )}
    </div>
  );
}

function RestaurantCard({
  restaurant: r,
  onSelect,
}: {
  restaurant: RestaurantSearchResult;
  onSelect?: () => void;
}) {
  const priceStr = r.priceLevel != null ? "$".repeat(Math.min(r.priceLevel, 4)) : null;

  return (
    <div className="card card-lift p-4">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center shrink-0">
          <Utensils className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-cream-100 leading-tight truncate">
                {r.name}
              </h3>
              <p className="text-xs text-cream-500 mt-0.5 truncate">
                {r.cuisine}{r.address ? ` · ${r.address}` : ""}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {r.googleMapsUri && (
                <a
                  href={r.googleMapsUri}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1.5 rounded-lg bg-white/[.05] hover:bg-white/[.10] text-cream-400 transition"
                  aria-label={`View ${r.name} on Google Maps`}
                  onClick={(e) => e.stopPropagation()}
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
              {onSelect && (
                <button
                  onClick={onSelect}
                  className="px-3 py-1.5 rounded-lg bg-brand-500/20 text-brand-300 text-xs font-medium hover:bg-brand-500/30 transition"
                  aria-label={`Select ${r.name}`}
                >
                  Select
                </button>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3 mt-2 flex-wrap">
            {r.rating != null && (
              <span className="flex items-center gap-0.5 text-xs text-amber-400 font-medium">
                <Star className="w-3 h-3 fill-amber-400" />
                {r.rating.toFixed(1)}
                {r.numReviews != null && (
                  <span className="text-cream-600 font-normal ml-0.5">
                    ({r.numReviews.toLocaleString()})
                  </span>
                )}
              </span>
            )}
            {priceStr && (
              <span className="text-xs text-cream-400 font-medium">{priceStr}</span>
            )}
            {r.tags && r.tags.length > 0 && (
              <div className="flex gap-1 flex-wrap">
                {r.tags.slice(0, 3).map((tag) => (
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
        </div>
      </div>
    </div>
  );
}
