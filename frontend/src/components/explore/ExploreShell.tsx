"use client";

import { useState } from "react";
import { Plane, Hotel, Utensils, MapPin, ArrowLeft } from "lucide-react";
import { RestaurantExploreFlow } from "./RestaurantExploreFlow";
import { AttractionExploreFlow } from "./AttractionExploreFlow";
import { HotelExploreFlow } from "./HotelExploreFlow";
import { FlightExploreFlow } from "./FlightExploreFlow";
import type { ExploreVertical } from "./types";

interface VerticalMeta {
  id: ExploreVertical;
  label: string;
  description: string;
  icon: React.ElementType;
}

const VERTICALS: VerticalMeta[] = [
  {
    id: "flights",
    label: "Flights",
    description: "Search live flights by route and dates with a Google Flights link-out",
    icon: Plane,
  },
  {
    id: "hotels",
    label: "Hotels",
    description: "Discover Google-verified hotels at any destination",
    icon: Hotel,
  },
  {
    id: "restaurants",
    label: "Restaurants",
    description: "Discover top-rated restaurants anywhere in the world",
    icon: Utensils,
  },
  {
    id: "attractions",
    label: "Attractions",
    description: "Explore must-see sights and local experiences",
    icon: MapPin,
  },
];

const VERTICAL_TITLES: Record<ExploreVertical, string> = {
  flights: "Flights",
  hotels: "Hotels",
  restaurants: "Restaurants",
  attractions: "Attractions",
};

const VERTICAL_OVERLINES: Record<ExploreVertical, string> = {
  flights: "Search",
  hotels: "Stays",
  restaurants: "Dining",
  attractions: "Experiences",
};

export function ExploreShell() {
  const [active, setActive] = useState<ExploreVertical | null>(null);

  if (active) {
    return (
      <div className="space-y-6 editorial-scene" data-testid="explore-vertical-flow">
        {/* Editorial breadcrumb */}
        <div className="flex items-center gap-3" data-testid="explore-lounge-breadcrumb">
          <button
            type="button"
            onClick={() => setActive(null)}
            className="flex items-center gap-1.5 min-h-[44px] text-sm text-ds-text-tertiary hover:text-ds-text transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
            aria-label="Back to Explore"
          >
            <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            Explore
          </button>
          <span className="text-ds-pen-stroke" aria-hidden="true">/</span>
          <h2 className="text-sm font-semibold text-ds-text">
            {VERTICAL_TITLES[active]}
          </h2>
        </div>

        {/* Search instrument section */}
        <section
          className="rounded-xl border border-ds-pen-stroke bg-ds-onyx boutique-instrument overflow-hidden"
          data-testid={`${active}-flow`}
          aria-label={`${VERTICAL_TITLES[active]} search`}
        >
          <div className="folio-cover-tab" aria-hidden="true" />
          <div className="p-4 sm:p-6">
          <div className="mb-5" data-testid="explore-instrument-header">
            <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-accent">
              {VERTICAL_OVERLINES[active]}
            </p>
            <h3 className="text-base font-semibold text-ds-text mt-0.5">
              {VERTICAL_TITLES[active]}
            </h3>
          </div>
          {active === "restaurants" && <RestaurantExploreFlow />}
          {active === "attractions" && <AttractionExploreFlow />}
          {active === "hotels" && <HotelExploreFlow />}
          {active === "flights" && <FlightExploreFlow />}
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-8 editorial-scene" data-testid="explore-home">
      {/* Editorial lounge header */}
      <header data-testid="explore-lounge-header">
        <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-accent mb-1">
          Curated Discovery
        </p>
        <h1 className="text-2xl font-bold text-ds-text">Discover</h1>
        <p className="text-sm text-ds-text-tertiary mt-1 leading-snug">
          Flights, hotels, restaurants, and attractions — verified, no trip required.
        </p>
      </header>
      <div className="editorial-section-rule" aria-hidden="true" />

      {/* Discovery trays */}
      <div
        className="grid grid-cols-1 sm:grid-cols-2 gap-4"
        data-testid="explore-vertical-grid"
      >
        {VERTICALS.map((v) => (
          <VerticalCard key={v.id} meta={v} onSelect={() => setActive(v.id)} />
        ))}
      </div>
    </div>
  );
}

function VerticalCard({
  meta,
  onSelect,
}: {
  meta: VerticalMeta;
  onSelect: () => void;
}) {
  const Icon = meta.icon;
  return (
    <button
      type="button"
      onClick={onSelect}
      className="rounded-xl border border-ds-pen-stroke bg-ds-onyx card-lift p-5 text-left flex items-start gap-4 w-full min-h-[44px] transition-colors atelier-surface-depth boutique-folio focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
      aria-label={`Explore ${meta.label}`}
      data-testid={`vertical-card-${meta.id}`}
    >
      <div
        className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0 text-ds-accent"
        style={{ backgroundColor: "var(--ds-accent-subtle)" }}
        aria-hidden="true"
      >
        <Icon className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-text-tertiary mb-0.5">
          {VERTICAL_OVERLINES[meta.id]}
        </p>
        <h3 className="text-sm font-semibold text-ds-text leading-tight">
          {meta.label}
        </h3>
        <p className="text-xs text-ds-text-tertiary mt-1 leading-snug">
          {meta.description}
        </p>
      </div>
    </button>
  );
}
