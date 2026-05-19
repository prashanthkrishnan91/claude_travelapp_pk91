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
//
// The greeting is the first piece of writing on the page. It floats as a
// translucent paper-glass panel directly on the destination scenery, so
// the world reads through its edges. No big SaaS dashboard header — it
// reads like the opening page of a private travel issue.

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
        className="atelier-hero-greeting world-hero-greeting"
      >
        <FolioAtelierHero>
          <div className="folio-issue-eyebrow">Private Travel Concierge</div>
          <h1 className="folio-display mt-4 text-balance text-[2.6rem] leading-[1.04] md:text-[3.4rem] lg:text-[4.2rem]">
            {greeting},{" "}
            <span className="italic text-ds-folio-ink-soft">planner.</span>
          </h1>
          <p className="folio-editorial-sub mt-3 max-w-xl text-[1.0625rem] md:text-[1.125rem] leading-relaxed">
            {shelfLine}
          </p>
          <div className="mapline-rule mt-6" aria-hidden="true" />
        </FolioAtelierHero>
      </WorldGlassSurface>
    </header>
  );
}

// ── Concierge threshold (the private salon doorway) ──────────────────────────
//
// A full-width, cinematic threshold into the concierge salon. The right
// half is painted as the salon interior — brass-warm lantern light, deep
// velvet shadow — so the user can see the room they're about to enter
// before reading a word.

function ConciergeEntry() {
  return (
    <section aria-label="AI Concierge" data-testid="concierge-entry">
      <FolioPanel
        className="folio-invitation-panel folio-atelier-invitation atelier-concierge-threshold relative h-full !p-0 overflow-hidden"
        data-testid="concierge-advisor-desk"
      >
        <div className="folio-card-accent" aria-hidden="true" />
        <div className="relative z-10 flex flex-col lg:flex-row items-stretch h-full">
          <div className="flex-1 flex flex-col justify-center p-7 md:p-10 lg:p-14 lg:max-w-[58%]">
            <Overline className="text-ds-folio-ink-mist tracking-[0.28em]">
              01 · Dedicated System
            </Overline>
            <h2 className="folio-heading mt-4 max-w-md text-balance text-[2rem] md:text-[2.4rem] lg:text-[2.8rem] leading-[1.08]">
              Your private concierge.
            </h2>
            <p className="folio-caption mt-3 max-w-md text-[1rem] leading-relaxed">
              Bespoke dining, boutique architecture, and quiet local scenery —
              curated instantly for your aesthetic.
            </p>

            <div className="mt-8">
              <FolioCtaGlide>
                <Link
                  href="/concierge"
                  className="btn-marine min-h-[44px] inline-flex items-center gap-3 px-7 text-sm tracking-[0.04em]"
                >
                  <span>Step into the salon</span>
                  <span className="folio-cta-arrow" aria-hidden="true">
                    <ArrowRight className="w-4 h-4" />
                  </span>
                </Link>
              </FolioCtaGlide>
            </div>
          </div>
          {/* Salon interior — visible doorway preview on desktop, peeks
              through the bottom on mobile (handled by ::before/::after). */}
          <div
            aria-hidden="true"
            className="hidden lg:flex flex-1 items-end justify-end p-12"
          >
            <span className="text-[10px] tracking-[0.3em] uppercase font-semibold text-ds-paper/70">
              the private salon
            </span>
          </div>
        </div>
      </FolioPanel>
    </section>
  );
}

// ── Active journey dossier (folio object, not a card) ────────────────────────
//
// The active trip becomes a physical dossier: a tactile portfolio object
// with the destination scenery clipped INSIDE its cover, a brass date
// plate, a folded folio-serial flag, and a brass binding seam at the
// right edge that glows when you hover. No floating orphan labels.

function ContinuePlanningStrip({ trip }: { trip: Trip }) {
  const folioCode = getFolioCode(trip);
  const dateLine = formatDateRangeShort(trip.startDate, trip.endDate);
  const longDateLine = formatDateRange(trip.startDate, trip.endDate);
  return (
    <section data-testid="atelier-continue-planning" aria-label="Continue planning" className="folio-paper-card folio-reveal !bg-transparent !border-0 !shadow-none !p-0">
      <p className="folio-serial mb-3 text-ds-folio-ink-mist">Continue planning</p>
      <Link
        href={`/trips/${trip.id}`}
        aria-label={`Open ${trip.title} folio`}
        className="block min-h-[44px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2 rounded-[28px]"
      >
        <article
          className="folio-paper-card folio-journey-entry folio-active-journey-object atelier-dossier"
        >
          <div className="atelier-dossier-cover">
            <span className="atelier-dossier-scenery" aria-hidden="true" />
            <span className="atelier-dossier-plate">{dateLine}</span>
            <span className="atelier-dossier-flag">
              {folioCode} · {trip.status.toUpperCase()}
            </span>
          </div>

          <div className="atelier-dossier-body">
            <div className="flex items-center gap-2 mb-1">
              <TripStatusBadge status={getDisplayTripStatus(trip)} />
              <span className="text-[10px] tracking-[0.22em] uppercase font-medium text-ds-ember-brass">
                · {trip.destination?.split(",")[0] ?? "Folio"}
              </span>
            </div>

            <h3 className="folio-card-title text-balance text-[1.8rem] md:text-[2rem] leading-[1.05]">
              {trip.title}
            </h3>
            <p className="folio-caption italic mt-1">
              {trip.destination || "Destination to be decided."}
            </p>

            <FolioRouteThread className="atelier-dossier-route" />

            <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-[11px] font-light text-ds-folio-ink-soft mt-1">
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

            <div className="atelier-dossier-footer">
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

// ── Travel shelf (curio cabinet) ─────────────────────────────────────────────
//
// A physical shelf, not a SaaS card. Three book spines fan behind the
// primary plate so the user feels the volume of their archive.

function JourneyShelfTeaser({ count }: { count: number }) {
  return (
    <section
      aria-label="Your travel shelf"
      data-testid="journey-shelf-teaser"
      className="folio-paper-card !bg-transparent !border-0 !shadow-none !p-0"
    >
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
        className="block focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2 rounded-[28px]"
        aria-label="Open your travel shelf"
      >
        <div className="atelier-curio-shelf folio-paper-card">
          {/* Three book spines fan behind the primary plate. */}
          <span className="atelier-curio-spines" aria-hidden="true">
            <span className="atelier-curio-spine" />
            <span className="atelier-curio-spine" />
            <span className="atelier-curio-spine" />
          </span>
          <div className="atelier-curio-plate">
            <p className="folio-serial mb-3">
              YOUR ARCHIVE · {count} {count !== 1 ? "ENTRIES" : "ENTRY"}
            </p>
            <p className="folio-card-title text-[1.6rem] md:text-[1.8rem] leading-[1.1] mb-1">
              {count} journey{count !== 1 ? "s" : ""} on the shelf.
            </p>
            <div className="flex items-end justify-between mt-3">
              <p className="folio-caption italic max-w-md">
                Open the cabinet and turn the page.
              </p>
              <FolioCtaGlide>
                <span className="folio-cta-arrow" aria-hidden="true">
                  <ArrowRight className="w-4 h-4 text-ds-folio-ink-mist" />
                </span>
              </FolioCtaGlide>
            </div>
          </div>
        </div>
      </Link>
    </section>
  );
}

// ── Empty atelier state ──────────────────────────────────────────────────────
//
// First-run state. Reads as the empty page of a freshly opened folio —
// quiet, inviting, not a "no data" empty state.

function EmptyAtelierHome() {
  return (
    <section
      aria-label="Start your first journey"
      data-testid="atelier-empty-state"
      className="atelier-dossier text-ds-folio-ink text-ds-folio-ink-mist h-full flex flex-col"
    >
      <div className="atelier-dossier-cover" aria-hidden="true">
        <span className="atelier-dossier-scenery" />
        <span className="atelier-dossier-flag">
          TRP · WAITING
        </span>
      </div>
      <div className="atelier-dossier-body flex-1 flex flex-col justify-center">
        <div
          className="flex items-center justify-center w-12 h-12 rounded-2xl bg-ds-accent-subtle text-ds-accent mb-4"
          aria-hidden="true"
        >
          <Map className="w-6 h-6" />
        </div>
        <h3 className="folio-card-title text-ds-folio-ink text-[1.6rem] md:text-[1.8rem] leading-[1.05]">
          A blank folio, waiting.
        </h3>
        <p className="folio-caption italic text-ds-folio-ink-mist mt-1 mb-5 max-w-sm">
          Plan your first journey, or ask the concierge to imagine where to go.
        </p>
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
            Ask Concierge
          </Link>
        </div>
      </div>
    </section>
  );
}

// ── Rooms in the house (the doorway shelf) ───────────────────────────────────
//
// Four tall doorways arranged in a cinematic shelf. Each portal owns its
// own room interior (concierge=salon, explore=observatory, planning=
// drafting atelier, saved=scrapbook library) so the four read as four
// distinct boutique rooms. Tiny brass plaques carry the labels; the
// scenery is the orientation.

function AtelierPlanningStrip({ world }: { world: LocationData }) {
  return (
    <section
      aria-label="Rooms in this house"
      data-testid="atelier-planning-strip"
      className="atelier-doorway-shelf"
    >
      <p className="sr-only text-ds-folio-ink-mist">Discovery tools</p>
      <div className="editorial-section-rule" aria-hidden="true" />
      <div className="flex items-end justify-between mb-5 px-1 gap-6">
        <div>
          <p className="folio-serial text-ds-folio-ink-mist mb-1">
            CHAPTER · ROOMS IN THIS HOUSE
          </p>
          <h2 className="folio-heading text-[1.6rem] md:text-[1.9rem] leading-[1.1] max-w-xl">
            Four doorways. One private house.
          </h2>
          <p className="folio-caption italic text-ds-folio-ink-mist mt-2 max-w-md">
            Step through any door — each room keeps the house intact.
          </p>
        </div>
        <p className="folio-serial italic text-ds-folio-ink-mist hidden md:block whitespace-nowrap">
          <span className="folio-serial">
            {world.location} · {world.archetype ?? "atelier"}
          </span>
          <span className="folio-caption sr-only">{world.mood}</span>
        </p>
      </div>
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
        className="atelier-atrium-content"
        aria-busy="true"
        aria-label="Loading your atelier"
      >
        <div className="space-y-3 mt-6">
          <div className="h-3 w-28 bg-ds-hairline rounded animate-pulse" />
          <div className="h-12 w-80 max-w-full bg-ds-hairline rounded animate-pulse" />
          <div className="h-4 w-60 max-w-full bg-ds-hairline rounded animate-pulse" />
        </div>
        <div className="h-72 bg-ds-linen border border-ds-hairline rounded-[28px] animate-pulse" />
        <div className="h-36 bg-ds-linen border border-ds-hairline rounded-[28px] animate-pulse" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="h-72 bg-ds-linen border border-ds-hairline rounded-[26px] animate-pulse" />
          <div className="h-72 bg-ds-linen border border-ds-hairline rounded-[26px] animate-pulse" />
          <div className="h-72 bg-ds-linen border border-ds-hairline rounded-[26px] animate-pulse" />
          <div className="h-72 bg-ds-linen border border-ds-hairline rounded-[26px] animate-pulse" />
        </div>
      </div>
    );
  }

  const continuePlanning = pickContinuePlanning(trips);
  const hasTrips = trips.length > 0;
  const hasContinue = hasTrips && continuePlanning;

  // The active trip's destination drives the entire page world. When there
  // is no active trip, the Atelier (house) world is the foyer.
  const world = pickWorldFromDestination(continuePlanning?.destination);

  return (
    <FolioScene
      className="atelier-transition editorial-scene world-canvas world-scenery-host atelier-atrium"
      data-testid="atelier-home"
      data-world-location={world.location}
      style={worldStyleVars(world)}
    >
      {/* Full-bleed destination scenery — the first thing the eye sees.
          Extends edge-to-edge of the main area because the home page
          opts out of the AppShell max-w-7xl container. */}
      <WorldScenery
        height="tall"
        imageAlt={world.visualLayer.imageAlt}
      />
      <WorldMist />
      <WorldAtmosphere />
      <FolioLivingCanvas className="atelier-atrium-content">
        {/* ── Hero spread ────────────────────────────────────────────
            Greeting at left (translucent paper-glass), active trip
            dossier at right (folio object). The scenery lives behind
            them; the user feels the destination before reading. */}
        <div className="atelier-atrium-hero">
          <AtelierGreeting tripCount={summary.tripCount} />
          {hasContinue ? (
            <FolioReveal stagger={3}>
              <ContinuePlanningStrip trip={continuePlanning!} />
            </FolioReveal>
          ) : (
            <FolioReveal stagger={3}>
              <EmptyAtelierHome />
            </FolioReveal>
          )}
        </div>

        {/* ── Concierge threshold ────────────────────────────────────
            Full-width doorway into the private salon. The right edge
            paints the room you'd step into. */}
        <FolioReveal stagger={2}>
          <ConciergeEntry />
        </FolioReveal>

        {/* ── Four rooms ──────────────────────────────────────────────
            The cinematic shelf — four tall doorways into Concierge,
            Explore, Planning, Saved. Each portal carries its own
            atmospheric interior. */}
        <FolioReveal stagger={4}>
          <AtelierPlanningStrip world={world} />
        </FolioReveal>

        {/* ── Travel shelf ───────────────────────────────────────────
            Only when trips exist — a curio cabinet of the archive. */}
        {hasTrips && (
          <FolioReveal stagger={4}>
            <JourneyShelfTeaser count={summary.tripCount} />
          </FolioReveal>
        )}

        {/* ── Quiet signature ───────────────────────────────────────
            Tiny editorial location anchor at the bottom of the page,
            never the primary orientation. */}
        <footer className="atelier-atrium-signature">
          <WorldWayfinder world={world} className="world-wayfinder-quiet" />
        </footer>
      </FolioLivingCanvas>
    </FolioScene>
  );
}
