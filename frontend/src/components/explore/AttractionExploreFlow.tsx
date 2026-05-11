"use client";

/**
 * Attractions vertical — deferred state.
 *
 * The only attractions route that exists, `/search/attractions`, was removed
 * in Product Surface Pruning v1C. The remaining path,
 * `searchAttractionsViaConcierge`, requires a `tripId` (Stage 2A Slice 3
 * makes the AI Concierge trip-optional). Until then this vertical collects
 * the user's destination + interest and returns a polished deferred state.
 */

import { useState } from "react";
import { MapPin, Tag, Construction } from "lucide-react";

export function AttractionExploreFlow() {
  const [destination, setDestination] = useState("");
  const [interest, setInterest] = useState("");
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (destination.trim()) setSubmitted(true);
  }

  return (
    <div className="space-y-6">
      {/* Input form */}
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
            disabled={!destination.trim()}
            className="btn-primary shrink-0"
          >
            Search
          </button>
        </div>
      </form>

      {/* Deferred state */}
      {submitted ? (
        <DeferredState destination={destination.trim()} interest={interest.trim()} />
      ) : (
        <div className="text-center py-10 text-cream-500 text-sm">
          Enter a city or area to find top attractions.
        </div>
      )}
    </div>
  );
}

function DeferredState({ destination, interest }: { destination: string; interest: string }) {
  return (
    <div
      className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-6 text-center space-y-3"
      data-testid="attraction-deferred-state"
      role="status"
      aria-live="polite"
    >
      <div className="flex justify-center">
        <div className="w-12 h-12 rounded-full bg-amber-500/10 text-amber-400 flex items-center justify-center">
          <Construction className="w-6 h-6" />
        </div>
      </div>
      <div>
        <p className="text-cream-200 font-semibold text-sm">
          Attractions search coming soon
        </p>
        <p className="text-cream-500 text-xs mt-1">
          We&apos;re building a trip-optional attractions route for{" "}
          <span className="text-cream-300">{destination}</span>
          {interest ? ` (${interest})` : ""}. This will be powered by the AI Concierge in the next update.
        </p>
      </div>
      <p className="text-xs text-cream-600">
        Full attraction search arrives in the next Explore update.
      </p>
    </div>
  );
}
