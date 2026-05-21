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
  /** Short mobile-only cue (full description stays on desktop). */
  cue: string;
  icon: React.ElementType;
}

const VERTICALS: VerticalMeta[] = [
  {
    id: "flights",
    label: "Flights",
    description: "Search live flights by route and dates with a Google Flights link-out",
    cue: "Live routes",
    icon: Plane,
  },
  {
    id: "hotels",
    label: "Hotels",
    description: "Discover Google-verified hotels at any destination",
    cue: "Verified stays",
    icon: Hotel,
  },
  {
    id: "restaurants",
    label: "Restaurants",
    description: "Discover top-rated restaurants anywhere in the world",
    cue: "Dining ideas",
    icon: Utensils,
  },
  {
    id: "attractions",
    label: "Attractions",
    description: "Explore must-see sights and local experiences",
    cue: "Places to see",
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

// Vertical mood lines for the banner. Identity/mood only — never the typed
// destination (destination state stays inside each flow; no lifted controller).
const VERTICAL_MOODS: Record<ExploreVertical, string> = {
  flights: "Live routes · Google Flights link-out",
  hotels: "Google-verified stays · no rates shown",
  restaurants: "Top-rated, verified tables",
  attractions: "Must-see sights and local experiences",
};

/**
 * The Observatory meridian band — a wide horizon viewing slit. Shared,
 * purely presentational; reused as the landing hero and (compact variant)
 * as the per-vertical mood banner.
 */
function ObsMeridian({
  banner = false,
  hero = false,
  children,
}: {
  banner?: boolean;
  hero?: boolean;
  children: React.ReactNode;
}) {
  const cls = [
    "obs-meridian",
    banner ? "obs-meridian--banner" : "",
    hero ? "obs-meridian--hero" : "",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls}>
      <div className="obs-meridian-scene" aria-hidden="true" />
      <div className="obs-meridian-bloom" aria-hidden="true" />
      <div className="obs-meridian-grain" aria-hidden="true" />
      <div className="obs-meridian-horizon" aria-hidden="true" />
      <div className="obs-meridian-vignette" aria-hidden="true" />
      <div className="obs-meridian-copy">{children}</div>
    </div>
  );
}

export function ExploreShell() {
  const [active, setActive] = useState<ExploreVertical | null>(null);

  if (active) {
    return (
      <div className="obs-field">
        <div className="obs-room folio-cinema-lounge" data-testid="explore-vertical-flow">
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

        {/* Vertical mood banner — identity/mood only, no destination */}
        <ObsMeridian banner>
          <header>
            <p className="obs-meridian-eyebrow">{VERTICAL_OVERLINES[active]}</p>
            <h2 className="obs-meridian-title">{VERTICAL_TITLES[active]}</h2>
          </header>
          <p className="obs-meridian-foot">{VERTICAL_MOODS[active]}</p>
        </ObsMeridian>

        {/* Search instrument section — the vertical's own production flow */}
        <section
          className="folio-cinema-card rounded-xl overflow-hidden"
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
      </div>
    );
  }

  return (
    <div className="obs-field">
      <div className="obs-room folio-cinema-lounge" data-testid="explore-home">
        {/* Observatory meridian hero — transportive mood surface */}
        <ObsMeridian hero>
          <header data-testid="explore-lounge-header">
            <p className="obs-meridian-eyebrow">Curated Discovery</p>
            <h1 className="obs-meridian-title">Discover</h1>
          </header>
          <p className="obs-meridian-foot">
            Browse flights, hotels, restaurants, and attractions.
          </p>
        </ObsMeridian>
        <div className="editorial-section-rule" aria-hidden="true" />

        {/* Curated browse deck — choose what to browse first.
            2×2 on mobile, 4-up on desktop; clearly named, no clipping. */}
        <p className="obs-deck-label">Choose what to browse</p>
        <div
          className="obs-deck grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-4"
          data-testid="explore-vertical-grid"
        >
          {VERTICALS.map((v) => (
            <VerticalCard key={v.id} meta={v} onSelect={() => setActive(v.id)} />
          ))}
        </div>
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
      className="obs-vert-card min-h-[44px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
      aria-label={`Explore ${meta.label}`}
      data-testid={`vertical-card-${meta.id}`}
    >
      <span className="obs-vert-glyph" aria-hidden="true">
        <Icon className="w-[18px] h-[18px]" />
      </span>
      <div className="min-w-0">
        <p className="obs-vert-over">{VERTICAL_OVERLINES[meta.id]}</p>
        <h3 className="obs-vert-name">{meta.label}</h3>
        <p className="obs-vert-desc">{meta.description}</p>
        <p className="obs-vert-cue">{meta.cue}</p>
      </div>
      <span className="obs-vert-go" aria-hidden="true">
        {meta.id === "flights" ? "Search" : "Browse"} &rarr;
      </span>
    </button>
  );
}
