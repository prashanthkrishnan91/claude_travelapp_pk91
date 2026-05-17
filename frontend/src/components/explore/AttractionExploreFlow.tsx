"use client";

/**
 * Attractions vertical — canonical vertical search.
 *
 * AttractionExploreFlow calls the canonical /search/attractions endpoint
 * (searchAttractionsExplore), backed by Google Places Text Search only — the
 * same provider-backed attractions search used by /trips/create-with-search
 * seeding.  Explore Attractions is a pure provider-backed discovery surface:
 * it does not depend on the AI Concierge search route and uses no paid
 * research providers.
 */

import { useState } from "react";
import { Search, MapPin, Tag, Star, ExternalLink, Landmark, Loader2, AlertCircle } from "lucide-react";
import { searchAttractionsExplore } from "@/lib/api";
import type { ExploreAttractionResult } from "@/lib/api";
import type { ExploreResultContext } from "./types";
import { ResultActionSheet } from "./ResultActionSheet";
import { Card } from "@/components/ui/Card";
import { TrustStrip } from "@/components/ui/TrustStrip";

export function AttractionExploreFlow() {
  const [destination, setDestination] = useState("");
  const [interest, setInterest] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<ExploreAttractionResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [lastDestination, setLastDestination] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const dest = destination.trim();
    if (!dest) return;

    setLoading(true);
    setError(null);
    setSearched(true);
    setLastDestination(dest);
    setResults(null);

    try {
      // Canonical vertical search: Google-Places-backed /search/attractions.
      const res = await searchAttractionsExplore(dest, interest.trim() || undefined);
      setResults(res);
      if (res.length === 0) {
        setError("No attractions found for this destination. Try a different area or interest.");
      }
    } catch {
      setError("Search failed. Please try again.");
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  function buildContext(a: ExploreAttractionResult): ExploreResultContext {
    const savedPayload: Record<string, unknown> = {
      type: "attraction",
      name: a.name,
      source: a.source,
      category: a.category,
      rating: a.rating,
      address: a.address,
      tags: a.tags,
      mapsLink: a.googleMapsUri,
      googleMapsUri: a.googleMapsUri,
      providerPlaceId: a.googlePlaceId,
      destination: lastDestination,
    };
    return {
      vertical: "attractions",
      destination: lastDestination,
      location:
        a.lat != null && a.lng != null ? { lat: a.lat, lng: a.lng } : undefined,
      providerIdentity: a.googlePlaceId ?? undefined,
      originalPayload: savedPayload,
    };
  }

  return (
    <div className="space-y-6">
      {/* Search form */}
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ds-text-tertiary pointer-events-none" />
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
            <Tag className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ds-text-tertiary pointer-events-none" />
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
        <div className="flex items-start gap-2 p-3 rounded-xl border text-sm text-ds-warning border-ds-warning/20 bg-ds-warning/10">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-3" aria-label="Loading attractions">
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
          No verified attractions found for{" "}
          <span className="text-ds-text font-medium">{lastDestination}</span>.
          Try a broader area or different interest.
        </div>
      )}

      {/* Results */}
      {!loading && results && results.length > 0 && (
        <div className="space-y-3" data-testid="attraction-results">
          <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-text-tertiary px-1" data-testid="explore-results-header">
            {results.length} attraction{results.length !== 1 ? "s" : ""} in {lastDestination}
          </p>
          {results.map((a, i) => (
            <AttractionCard key={a.id + i} attraction={a} context={buildContext(a)} />
          ))}
        </div>
      )}

      {/* Idle prompt */}
      {!searched && !loading && (
        <div className="text-center py-10 text-ds-text-tertiary text-sm">
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
  attraction: ExploreAttractionResult;
  context: ExploreResultContext;
}) {
  return (
    <Card tone="dark" as="article" className="card-lift" style={{ padding: "var(--ds-space-5)" }}>
      <Card.Identity>
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 text-ds-accent"
          style={{ backgroundColor: "var(--ds-accent-subtle)" }}
          aria-hidden="true"
        >
          <Landmark className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-ds-text leading-tight truncate">
                {a.name}
              </h3>
              <p className="text-xs text-ds-text-tertiary mt-0.5 truncate">
                {a.category}{a.address ? ` · ${a.address}` : ""}
              </p>
            </div>
            {a.googleMapsUri && (
              <a
                href={a.googleMapsUri}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1.5 rounded-lg bg-ds-carbon hover:bg-ds-pen-stroke text-ds-text-tertiary hover:text-ds-text-secondary transition-colors shrink-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                aria-label={`View ${a.name} on Google Maps`}
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
        </div>
      </Card.Identity>

      {a.googlePlaceId && (
        <Card.Trust className="mt-2">
          <TrustStrip sourceCount={1} />
        </Card.Trust>
      )}

      <Card.Meta className="mt-2">
        {a.rating != null && (
          <span className="flex items-center gap-0.5 text-xs text-ds-accent font-medium">
            <Star className="w-3 h-3 fill-current" />
            {a.rating.toFixed(1)}
            {a.reviewCount != null && (
              <span className="text-ds-text-tertiary font-normal ml-0.5">
                ({a.reviewCount.toLocaleString()})
              </span>
            )}
          </span>
        )}
        {a.tags && a.tags.length > 0 &&
          a.tags.slice(0, 3).map((tag) => (
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
