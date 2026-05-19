"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Map,
  Sparkles,
  PlusCircle,
  ArrowRight,
} from "lucide-react";
import { TripStatusBadge } from "@/components/ui/TripStatusBadge";
import {
  fetchDashboardSummary,
  fetchTrips,
  type DashboardSummary,
} from "@/lib/api";
import { getDisplayTripStatus, getTripStatusGroup } from "@/lib/tripStatus";
import {
  FolioPanel,
  FolioScene,
  FolioReveal,
  FolioRouteThread,
  FolioLivingCanvas,
  FolioAtelierHero,
  FolioCtaGlide,
  FolioJourneyCover,
  FolioJourneyUnfurl,
  FolioShelfSpread,
} from "@/components/ui/Folio";
import {
  WorldAtmosphere,
  WorldGlassSurface,
  WorldMist,
  WorldRoomSwitcher,
  WorldScenery,
  WorldWayfinder,
} from "@/components/ui/World";
import {
  pickWorldFromDestination,
  worldStyleVars,
  type LocationData,
} from "@/lib/worldData";
import type { Trip } from "@/types";

// ── Helpers ────────────────────────────────────────────────────────────────────

function getTimeGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function formatDateRange(start?: string, end?: string) {
  if (!start) return "Dates TBD";
  const fmt = (d: string) =>
    new Date(d).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  return end ? `${fmt(start)} – ${fmt(end)}` : fmt(start);
}

function formatDateRangeShort(start?: string, end?: string) {
  if (!start) return "Dates to be decided";
  const fmt = (d: string) =>
    new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  return end ? `${fmt(start)} – ${fmt(end)}` : fmt(start);
}

function getFolioCode(trip: Trip): string {
  // 3-letter folio serial derived from the destination, not fabricated data.
  const letters = (trip.destination || trip.title || "TRP")
    .toUpperCase()
    .replace(/[^A-Z]/g, "");
  return (letters.slice(0, 3) || "TRP").padEnd(3, "·");
}

const STATUS_PRIORITY: Record<string, number> = {
  researching: 0,
  planned: 1,
  booked: 2,
  draft: 3,
};

function pickContinuePlanning(trips: Trip[]): Trip | null {
  const active = trips.filter((t) => getTripStatusGroup(t) === "Active");
  if (!active.length) return null;
  return active.sort(
    (a, b) =>
      (STATUS_PRIORITY[a.status] ?? 99) - (STATUS_PRIORITY[b.status] ?? 99),
  )[0];
}

// ── Overline role ────────────────────────────────────────────────────────────

function Overline({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <p
      className={`text-[10px] font-semibold uppercase tracking-[0.1em] ${
        className ?? "text-ds-folio-ink-mist"
      }`}
    >
      {children}
    </p>
  );
}

// ── Atelier greeting (editorial hero spread) ─────────────────────────────────

function AtelierGreeting({
  tripCount,
}: {
  tripCount: number;
}) {
  const greeting = getTimeGreeting();
  const shelfLine =
    tripCount > 0
      ? `Your canvas is set. ${tripCount} journey${
          tripCount !== 1 ? "s" : ""
        } breathing on your shelf.`
      : "Your canvas is set. Begin where the light falls.";
  return (
    <header
      data-testid="atelier-greeting"
      className="folio-reveal"
    >
      <WorldGlassSurface
        tone="paper"
        className="world-hero-greeting px-7 py-8 md:px-10 md:py-10"
      >
        <FolioAtelierHero>
          <div className="folio-issue-eyebrow">Private Travel Concierge</div>
          <h1 className="folio-display mt-3 text-balance">
            {greeting},{" "}
            <span className="italic text-ds-folio-ink-soft">planner.</span>
          </h1>
          <p className="folio-editorial-sub mt-2 max-w-xl">{shelfLine}</p>
          <div className="mapline-rule mt-5" aria-hidden="true" />
        </FolioAtelierHero>
      </WorldGlassSurface>
    </header>
  );
}

// ── Primary concierge instrument (atelier invitation) ────────────────────────

function ConciergeEntry() {
  return (
    <section aria-label="AI Concierge" data-testid="concierge-entry">
      <FolioPanel
        className="folio-invitation-panel folio-atelier-invitation relative h-full p-7 md:p-10 lg:p-12"
        data-testid="concierge-advisor-desk"
      >
        <div className="folio-card-accent" aria-hidden="true" />
        <div className="relative z-10 flex flex-col h-full">
          <Overline className="text-ds-folio-ink-mist tracking-[0.28em]">
            01 · Dedicated System
          </Overline>
          <h2 className="folio-heading mt-4 max-w-md text-balance">
            Your private concierge.
          </h2>
          <p className="folio-caption mt-3 max-w-sm leading-relaxed">
            Bespoke dining, boutique architecture, and quiet local scenery —
            curated instantly for your aesthetic.
          </p>

          <div className="mt-8 md:mt-10">
            <FolioCtaGlide>
              <Link
                href="/concierge"
                className="btn-marine min-h-[44px] inline-flex items-center gap-3 px-6"
              >
                <span>Open Concierge</span>
                <span className="folio-cta-arrow" aria-hidden="true">
                  <ArrowRight className="w-4 h-4" />
                </span>
              </Link>
            </FolioCtaGlide>
          </div>
        </div>
      </FolioPanel>
    </section>
  );
}

// ── Continue planning (active journey folio object) ──────────────────────────

function ContinuePlanningStrip({ trip }: { trip: Trip }) {
  const folioCode = getFolioCode(trip);
  const dateLine = formatDateRangeShort(trip.startDate, trip.endDate);
  const longDateLine = formatDateRange(trip.startDate, trip.endDate);
  return (
    <section
      aria-label="Continue planning"
      data-testid="atelier-continue-planning"
    >
      {/* paper-world surface: folio-paper-card layered with folio-journey-entry and folio-active-journey-object on the article below. */}
      <div className="flex items-center justify-between mb-4 px-1">
        <Overline className="text-ds-folio-ink-mist">Continue planning</Overline>
        <p className="folio-serial">
          {folioCode} · {trip.status.toUpperCase()}
        </p>
      </div>

      <Link
        href={`/trips/${trip.id}`}
        className="block min-h-[44px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2 rounded-[28px]"
        aria-label={`Open ${trip.title} folio`}
      >
        <article className="folio-paper-card folio-journey-entry folio-active-journey-object">
          <FolioJourneyCover>
            <span className="folio-journey-stamp">{dateLine}</span>
          </FolioJourneyCover>

          <div className="p-6 md:p-7">
            <div className="flex items-center gap-2 mb-2">
              <TripStatusBadge status={getDisplayTripStatus(trip)} />
              <span className="text-[10px] tracking-[0.22em] uppercase font-medium text-ds-ember-brass">
                · {trip.destination?.split(",")[0] ?? "Folio"}
              </span>
            </div>

            <h3 className="folio-card-title text-balance text-[1.6rem] leading-tight">
              {trip.title}
            </h3>
            <p className="folio-caption mt-1 italic">
              {trip.destination || "Destination to be decided."}
            </p>

            <FolioJourneyUnfurl>
              <div className="border-t border-ds-hairline pt-4 mt-2">
                <FolioRouteThread className="mb-3" />
                <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-[11px] font-light text-ds-folio-ink-soft">
                  <div>
                    <p className="folio-serial">Dates</p>
                    <p className="mt-0.5">{longDateLine}</p>
                  </div>
                  <div>
                    <p className="folio-serial">Party</p>
                    <p className="mt-0.5">
                      {trip.travelers} traveler
                      {trip.travelers !== 1 ? "s" : ""}
                    </p>
                  </div>
                </div>
              </div>
            </FolioJourneyUnfurl>

            <div className="mt-6 flex items-center justify-between text-xs uppercase tracking-[0.18em] font-medium text-ds-folio-ink-mist">
              <span>Open folio</span>
              <FolioCtaGlide>
                <span className="folio-cta-arrow" aria-hidden="true">
                  <ArrowRight className="w-4 h-4 text-ds-folio-ink-soft" />
                </span>
              </FolioCtaGlide>
            </div>
          </div>
        </article>
      </Link>
    </section>
  );
}

// ── Journey shelf teaser (scrapbook spread) ──────────────────────────────────

function JourneyShelfTeaser({ count }: { count: number }) {
  return (
    <section aria-label="Your travel shelf" data-testid="journey-shelf-teaser">
      {/* paper-world surface: folio-paper-card layered with folio-shelf-spread on the shelf link below. */}
      <div className="flex items-center justify-between mb-4 px-1">
        <Overline className="text-ds-folio-ink-mist">Your travel shelf</Overline>
        <div className="flex items-center gap-4">
          <Link
            href="/trips/new"
            className="flex items-center gap-1.5 text-xs font-medium text-ds-accent hover:text-ds-accent-muted transition min-h-[44px]"
            data-testid="home-new-trip-action"
          >
            <PlusCircle className="w-3.5 h-3.5" aria-hidden="true" />
            New
          </Link>
          <Link
            href="/trips"
            className="text-xs text-ds-accent hover:text-ds-accent-muted font-medium transition flex items-center gap-1 min-h-[44px]"
          >
            View all <ArrowRight className="w-3 h-3" aria-hidden="true" />
          </Link>
        </div>
      </div>
      <Link
        href="/trips"
        className="block focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2 rounded-[20px]"
        aria-label="Open your travel shelf"
      >
        <FolioShelfSpread className="folio-paper-card">
          <p className="folio-serial mb-3">
            YOUR ARCHIVE · {count} {count !== 1 ? "ENTRIES" : "ENTRY"}
          </p>
          <p className="folio-card-title mb-1">
            {count} journey{count !== 1 ? "s" : ""} in the folio.
          </p>
          <div className="flex items-end justify-between mt-2">
            <p className="folio-caption italic">
              Open the shelf and turn the page.
            </p>
            <FolioCtaGlide>
              <span className="folio-cta-arrow" aria-hidden="true">
                <ArrowRight className="w-4 h-4 text-ds-folio-ink-mist" />
              </span>
            </FolioCtaGlide>
          </div>
        </FolioShelfSpread>
      </Link>
    </section>
  );
}

// ── Empty atelier state ──────────────────────────────────────────────────────

function EmptyAtelierHome() {
  return (
    <section
      aria-label="Start your first journey"
      data-testid="atelier-empty-state"
      className="space-y-6"
    >
      <div className="text-center py-10 px-4">
        <div
          className="flex items-center justify-center w-16 h-16 rounded-2xl bg-ds-accent-subtle text-ds-accent mx-auto mb-5"
          aria-hidden="true"
        >
          <Map className="w-8 h-8" />
        </div>
        <h2 className="folio-heading mb-2 text-ds-folio-ink">
          Your travel shelf is empty.
        </h2>
        <p className="folio-caption max-w-sm mx-auto italic text-ds-folio-ink-mist">
          Plan your first journey, or ask the concierge to imagine where to go.
        </p>
      </div>
      <div className="flex flex-col sm:flex-row gap-3">
        <FolioCtaGlide className="flex-1">
          <Link
            href="/trips/new"
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-ds-accent text-ds-text-inverse text-sm font-semibold hover:opacity-90 transition-opacity min-h-[48px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
            data-testid="home-new-trip-action"
          >
            <PlusCircle className="w-4 h-4" aria-hidden="true" />
            Plan a Journey
            <span className="folio-cta-arrow" aria-hidden="true">
              <ArrowRight className="w-4 h-4" />
            </span>
          </Link>
        </FolioCtaGlide>
        <Link
          href="/concierge"
          className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl border border-ds-hairline bg-ds-linen text-ds-folio-ink-soft text-sm font-medium hover:bg-ds-bone hover:text-ds-folio-ink transition-all min-h-[48px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
        >
          <Sparkles className="w-4 h-4" aria-hidden="true" />
          Open Concierge
        </Link>
      </div>
    </section>
  );
}

// ── Rooms strip (world-driven portals) ───────────────────────────────────────
//
// Replaces the old 2-tile Explore/Saved artifact stack with a 4-room portal
// row. Each portal carries its own atmosphere preview — concierge feels like
// a private salon, explore like an observatory, planning like a drafting
// atelier, saved like a scrapbook library. Scenery does orientation work;
// labels are quiet.

function AtelierPlanningStrip({ world }: { world: LocationData }) {
  return (
    <section aria-label="Rooms in this house" data-testid="atelier-planning-strip">
      <div className="editorial-section-rule" aria-hidden="true" />
      <div className="flex items-center justify-between mb-4 px-1">
        <p className="text-[10px] block font-semibold uppercase tracking-[0.1em] text-ds-folio-ink-mist">Discovery tools</p>
        <p className="folio-serial italic text-ds-folio-ink-mist">
          {/* Quieter, optional secondary anchor — not primary orientation;
              scenery does the orientation work above. The previous "PORTLAND
              · MISTY FOREST…" overline that sat at the top has been removed. */}
          <span className="folio-serial">
            {world.location} · {world.archetype ?? "atelier"}
          </span>
          <span className="folio-caption sr-only">{world.mood}</span>
        </p>
      </div>
      <p className="folio-caption italic text-ds-folio-ink-mist mb-5 max-w-md px-1">
        Step through a door. Each room keeps the house intact.
      </p>
      <WorldRoomSwitcher world={world} />
    </section>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export function DashboardClient() {
  const [summary, setSummary] = useState<DashboardSummary>({
    tripCount: 0,
    cardCount: 0,
    itineraryCount: 0,
  });
  const [trips, setTrips] = useState<Trip[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const [summaryData, tripsData] = await Promise.all([
        fetchDashboardSummary(),
        fetchTrips(),
      ]);
      setSummary(summaryData);
      setTrips(tripsData);
      setLoading(false);
    }
    load();
  }, []);

  if (loading) {
    return (
      <div
        className="space-y-6"
        aria-busy="true"
        aria-label="Loading your atelier"
      >
        <div className="space-y-2">
          <div className="h-3 w-28 bg-ds-hairline rounded animate-pulse" />
          <div className="h-7 w-44 bg-ds-hairline rounded animate-pulse" />
          <div className="h-4 w-36 bg-ds-hairline rounded animate-pulse" />
        </div>
        <div className="h-36 bg-ds-linen border border-ds-hairline rounded-lg animate-pulse" />
        <div className="h-24 bg-ds-linen border border-ds-hairline rounded-lg animate-pulse" />
      </div>
    );
  }

  const continuePlanning = pickContinuePlanning(trips);
  const hasTrips = trips.length > 0;
  const hasContinue = hasTrips && continuePlanning;

  // ── Invisible Interface: pick the current world from the active trip's
  //    destination, falling back to the Atelier (house) world. The result
  //    drives every --world-* CSS variable on the canvas below.
  const world = pickWorldFromDestination(continuePlanning?.destination);

  return (
    <FolioScene
      className="atelier-transition editorial-scene world-canvas world-scenery-host"
      data-testid="atelier-home"
      data-world-location={world.location}
      style={worldStyleVars(world)}
    >
      {/* Full-bleed destination scenery — the first thing the eye sees.
          Painted CSS scenery + optional photographic mood asset + a
          legibility overlay. Aria-hidden; it is environment, not text. */}
      <WorldScenery
        height="tall"
        imageAlt={world.visualLayer.imageAlt}
      />
      <WorldMist />
      <WorldAtmosphere />
      <FolioLivingCanvas>
        <div className="space-y-10 md:space-y-14 pb-8 relative">
          <AtelierGreeting tripCount={summary.tripCount} />

          {/* Asymmetric editorial spread: concierge invitation (lg:7) +
              active journey object (lg:5, offset down). On mobile they stack. */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-start">
            <FolioReveal stagger={2} className="lg:col-span-7">
              <ConciergeEntry />
            </FolioReveal>
            {hasContinue ? (
              <FolioReveal
                stagger={3}
                className="lg:col-span-5 lg:mt-12"
              >
                <ContinuePlanningStrip trip={continuePlanning!} />
              </FolioReveal>
            ) : (
              <FolioReveal
                stagger={3}
                className="lg:col-span-5 lg:mt-12"
              >
                <EmptyAtelierHome />
              </FolioReveal>
            )}
          </div>

          {/* Lower spread: scrapbook shelf (lg:7) + room portals
              (lg:5, slightly raised). Mobile stacks. */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-start">
            {hasTrips && (
              <FolioReveal stagger={4} className="lg:col-span-7">
                <JourneyShelfTeaser count={summary.tripCount} />
              </FolioReveal>
            )}
            <FolioReveal
              stagger={4}
              className={
                hasTrips ? "lg:col-span-5 lg:-mt-4" : "lg:col-span-12"
              }
            >
              <AtelierPlanningStrip world={world} />
            </FolioReveal>
          </div>

          {/* Quiet, secondary editorial signature — the location is now
              implied by the scenery; this anchor is here only for visitors
              who want to confirm the world they're in. Tiny and faded. */}
          <footer className="pt-2 pb-1 px-1 opacity-80">
            <WorldWayfinder world={world} className="world-wayfinder-quiet" />
          </footer>
        </div>
      </FolioLivingCanvas>
    </FolioScene>
  );
}
