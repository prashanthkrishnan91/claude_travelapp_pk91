"use client";

import { useState } from "react";
import { Search, MapPin, Star, ExternalLink, Utensils, Loader2, AlertCircle } from "lucide-react";
import { searchRestaurants } from "@/lib/api";
import type { RestaurantSearchResult } from "@/types";
import type { ExploreResultContext } from "./types";
import { ResultActionSheet } from "./ResultActionSheet";
import { Card } from "@/components/ui/Card";
import { TrustStrip } from "@/components/ui/TrustStrip";

export function RestaurantExploreFlow() {
  const [destination, setDestination] = useState("");
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
      {/* Search form — cuisine/vibe filter is a Slice 2+ feature once
          searchRestaurants supports a query parameter */}
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
        <div className="flex items-start gap-2 p-3 rounded-xl border text-sm text-ds-warning border-ds-warning/20 bg-ds-warning/10">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-3" aria-label="Loading restaurants">
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

      {/* Empty state after search */}
      {!loading && searched && results !== null && results.length === 0 && !error && (
        <div className="text-center py-10 text-ds-text-tertiary text-sm">
          No verified restaurants found for <span className="text-ds-text font-medium">{lastDestination}</span>.
          Try a broader area or different city name.
        </div>
      )}

      {/* Results */}
      {!loading && results && results.length > 0 && (
        <div className="space-y-3" data-testid="restaurant-results">
          <p className="text-xs text-ds-text-tertiary font-medium uppercase tracking-wider px-1">
            {results.length} restaurant{results.length !== 1 ? "s" : ""} in {lastDestination}
          </p>
          {results.map((r) => (
            <RestaurantCard key={r.id} restaurant={r} context={buildContext(r)} />
          ))}
        </div>
      )}

      {/* Idle prompt */}
      {!searched && !loading && (
        <div className="text-center py-10 text-ds-text-tertiary text-sm">
          Enter a city or area to discover top-rated restaurants.
        </div>
      )}
    </div>
  );
}

function RestaurantCard({
  restaurant: r,
  context,
}: {
  restaurant: RestaurantSearchResult;
  context: ExploreResultContext;
}) {
  const priceStr = r.priceLevel != null ? "$".repeat(Math.min(r.priceLevel, 4)) : null;
  const hasPlaceSource = !!(r.providerPlaceId || r.placeId);

  return (
    <Card tone="dark" as="article" className="card-lift" style={{ padding: "var(--ds-space-5)" }}>
      <Card.Identity>
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 text-ds-accent"
          style={{ backgroundColor: "var(--ds-accent-subtle)" }}
          aria-hidden="true"
        >
          <Utensils className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-ds-text leading-tight truncate">
                {r.name}
              </h3>
              <p className="text-xs text-ds-text-tertiary mt-0.5 truncate">
                {r.cuisine}{r.address ? ` · ${r.address}` : ""}
              </p>
            </div>
            {r.googleMapsUri && (
              <a
                href={r.googleMapsUri}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1.5 rounded-lg bg-ds-carbon hover:bg-ds-pen-stroke text-ds-text-tertiary hover:text-ds-text-secondary transition-colors shrink-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                aria-label={`View ${r.name} on Google Maps`}
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
        </div>
      </Card.Identity>

      {hasPlaceSource && (
        <Card.Trust className="mt-2">
          <TrustStrip sourceCount={1} />
        </Card.Trust>
      )}

      <Card.Meta className="mt-2">
        {r.rating != null && (
          <span className="flex items-center gap-0.5 text-xs text-ds-accent font-medium">
            <Star className="w-3 h-3 fill-current" />
            {r.rating.toFixed(1)}
            {r.numReviews != null && (
              <span className="text-ds-text-tertiary font-normal ml-0.5">
                ({r.numReviews.toLocaleString()})
              </span>
            )}
          </span>
        )}
        {priceStr && (
          <span className="text-xs text-ds-text-secondary font-medium">{priceStr}</span>
        )}
        {r.tags && r.tags.length > 0 &&
          r.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-1.5 py-0.5 text-[10px] rounded-sm border border-ds-pen-stroke text-ds-text-tertiary"
            >
              {tag}
            </span>
          ))}
      </Card.Meta>

      <Card.Actions className="mt-3">
        <ResultActionSheet context={context} />
      </Card.Actions>
    </Card>
  );
}
