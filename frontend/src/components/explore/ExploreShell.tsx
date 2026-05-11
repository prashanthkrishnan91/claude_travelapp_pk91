"use client";

import { useState } from "react";
import { Plane, Hotel, Utensils, MapPin, ArrowLeft } from "lucide-react";
import { RestaurantExploreFlow } from "./RestaurantExploreFlow";
import { AttractionExploreFlow } from "./AttractionExploreFlow";
import { HotelExploreFlow } from "./HotelExploreFlow";
import { FlightExploreFlow } from "./FlightExploreFlow";
import type { ExploreVertical, ExploreResultContext } from "./types";

interface VerticalMeta {
  id: ExploreVertical;
  label: string;
  description: string;
  icon: React.ElementType;
  iconBg: string;
  iconColor: string;
  badge?: string;
}

const VERTICALS: VerticalMeta[] = [
  {
    id: "flights",
    label: "Flights",
    description: "Search one-way or round-trip flights by route and dates",
    icon: Plane,
    iconBg: "bg-sky-500/10",
    iconColor: "text-sky-400",
    badge: "Coming soon",
  },
  {
    id: "hotels",
    label: "Hotels",
    description: "Find hotels at any destination for your travel dates",
    icon: Hotel,
    iconBg: "bg-violet-500/10",
    iconColor: "text-violet-400",
    badge: "Coming soon",
  },
  {
    id: "restaurants",
    label: "Restaurants",
    description: "Discover top-rated restaurants anywhere in the world",
    icon: Utensils,
    iconBg: "bg-amber-500/10",
    iconColor: "text-amber-400",
  },
  {
    id: "attractions",
    label: "Attractions",
    description: "Explore must-see sights and local experiences",
    icon: MapPin,
    iconBg: "bg-emerald-500/10",
    iconColor: "text-emerald-400",
    badge: "Coming soon",
  },
];

const VERTICAL_TITLES: Record<ExploreVertical, string> = {
  flights: "Search Flights",
  hotels: "Search Hotels",
  restaurants: "Discover Restaurants",
  attractions: "Explore Attractions",
};

export function ExploreShell() {
  const [active, setActive] = useState<ExploreVertical | null>(null);

  function handleSelect(ctx: ExploreResultContext) {
    // Slice 2 will wire ResultActionSheet here.
    // For now the context is available but no action is taken.
    console.info("[ExploreShell] result selected:", ctx.vertical, ctx.destination);
  }

  if (active) {
    return (
      <div className="space-y-6" data-testid="explore-vertical-flow">
        {/* Back nav */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setActive(null)}
            className="flex items-center gap-1.5 text-sm text-cream-400 hover:text-cream-200 transition"
            aria-label="Back to Explore"
          >
            <ArrowLeft className="w-4 h-4" />
            Explore
          </button>
          <span className="text-cream-600">/</span>
          <h2 className="text-sm font-semibold text-cream-200">
            {VERTICAL_TITLES[active]}
          </h2>
        </div>

        {/* Active vertical flow */}
        <div className="card p-6" data-testid={`${active}-flow`}>
          {active === "restaurants" && (
            <RestaurantExploreFlow onResultSelect={handleSelect} />
          )}
          {active === "attractions" && <AttractionExploreFlow />}
          {active === "hotels" && <HotelExploreFlow onDeferred={handleSelect} />}
          {active === "flights" && <FlightExploreFlow onDeferred={handleSelect} />}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8" data-testid="explore-home">
      <div>
        <h1 className="text-2xl font-bold text-cream-100">Explore</h1>
        <p className="text-sm text-cream-500 mt-1">
          Discover flights, hotels, restaurants, and attractions — no trip required.
        </p>
      </div>

      {/* Vertical entry grid */}
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
      onClick={onSelect}
      className="card card-lift p-5 text-left flex items-start gap-4 group transition"
      aria-label={`Explore ${meta.label}`}
      data-testid={`vertical-card-${meta.id}`}
    >
      <div
        className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${meta.iconBg} ${meta.iconColor} group-hover:scale-105 transition-transform`}
      >
        <Icon className="w-6 h-6" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="text-base font-semibold text-cream-100">{meta.label}</h3>
          {meta.badge && (
            <span className="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-white/[.07] text-cream-500">
              {meta.badge}
            </span>
          )}
        </div>
        <p className="text-sm text-cream-500 mt-0.5 leading-snug">{meta.description}</p>
      </div>
    </button>
  );
}
