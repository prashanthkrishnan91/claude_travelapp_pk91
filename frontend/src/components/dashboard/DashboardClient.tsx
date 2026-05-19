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

function formatDateRangeShort(start?: string, end?: string) {
  if (!start) return "Dates · TBD";
  const fmt = (d: string) =>
    new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  return end ? `${fmt(start)} – ${fmt(end)}` : fmt(start);
}

function getFolioCode(trip: Trip): string {
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

// ── Atrium hero greeting ────────────────────────────────────────────────────
//
// A broad editorial welcome that anchors the page — not a small widget. The
// time-of-day greeting renders at magazine-cover scale on a full-width vellum
// plane. WorldGlassSurface stays as the wrapper (folio direction contract)
// but its visual treatment is overridden to feel like an open page, not a
// floating card.

function AtelierGreeting({
  tripCount,
}: {
  tripCount: number;
}) {
  const greeting = getTimeGreeting();
  const shelfLine =
    tripCount > 0
      ? `${tripCount} folio${tripCount !== 1 ? "s" : ""} resting on the shelf.`
      : "A blank folio waits on the shelf.";
  return (
    <header
      data-testid="atelier-greeting"
      className="folio-reveal atrium-hero"
    >
      <WorldGlassSurface
        tone="paper"
        className="atelier-hero-greeting atrium-hero-surface world-hero-greeting"
      >
        <FolioAtelierHero className="atrium-hero-spread">
          <div className="folio-issue-eyebrow atrium-hero-eyebrow">
            Private Travel Concierge
          </div>
          <h1 className="folio-display atrium-hero-display">
            {greeting},{" "}
            <span className="italic text-ds-folio-ink-soft atrium-hero-noun">planner.</span>
          </h1>
          <div className="atrium-hero-foot">
            <p className="folio-editorial-sub atrium-hero-sub">{shelfLine}</p>
            <div className="mapline-rule atrium-hero-rule" aria-hidden="true" />
          </div>
        </FolioAtelierHero>
      </WorldGlassSurface>
    </header>
  );
}

// ── Concierge artifact ───────────────────────────────────────────────────────
//
// A small private salon invitation. Sits alongside the active folio. Less
// text, more object — lantern interior glow + tactile CTA.

function ConciergeEntry() {
  return (
    <section aria-label="AI Concierge" data-testid="concierge-entry" className="atelier-folio-section">
      <FolioPanel
        className="folio-invitation-panel folio-atelier-invitation atelier-concierge-artifact atelier-concierge-portal relative h-full !p-0 overflow-hidden !bg-transparent !border-0 !shadow-none"
        data-testid="concierge-advisor-desk"
      >
        <div className="folio-card-accent" aria-hidden="true" />
        {/* Salon scenery — dim warm lantern interior painted as the
            atmospheric body of the portal (not a flat pale box). */}
        <div className="atelier-concierge-scenery" aria-hidden="true" />
        <div className="atelier-concierge-interior" aria-hidden="true" />
        <div className="atelier-concierge-vignette" aria-hidden="true" />
        <Link
          href="/concierge"
          className="atelier-concierge-link relative z-10 flex flex-col h-full p-7 md:p-9 lg:p-11 min-h-[44px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-ember-brass focus-visible:outline-offset-2"
          aria-label="Step into the salon"
        >
          <Overline className="text-ds-folio-ink-mist tracking-[0.28em] sr-only">
            01 · Dedicated System
          </Overline>
          <p className="folio-serial atelier-concierge-eyebrow">
            The Salon
          </p>
          <h2 className="folio-heading atelier-concierge-title">
            Your private concierge.
          </h2>
          <p className="folio-caption atelier-concierge-caption">
            Bespoke dining, boutique architecture, quiet local scenery.
          </p>

          <div className="atelier-concierge-foot">
            <span className="btn-marine atelier-concierge-tab inline-flex items-center gap-3 min-h-[44px] px-6 text-sm tracking-[0.04em]">
              <span>Step into the salon</span>
              <span className="folio-cta-arrow" aria-hidden="true">
                <ArrowRight className="w-4 h-4" />
              </span>
            </span>
          </div>
        </Link>
      </FolioPanel>
    </section>
  );
}

// ── Active journey dossier ──────────────────────────────────────────────────
//
// The dominant artifact. Destination scenery clipped inside the cover; title
// + caption float on the cover using the luminance-aware --world-on-scenery
// variable (guaranteed contrast); integrated glass-scrim metadata band along
// the bottom collapses status / dates / travelers / open-folio into one
// tactile band.

function ContinuePlanningStrip({ trip }: { trip: Trip }) {
  const folioCode = getFolioCode(trip);
  const dateLine = formatDateRangeShort(trip.startDate, trip.endDate);
  const partyLine = `${trip.travelers} traveler${trip.travelers !== 1 ? "s" : ""}`;
  return (
    <section data-testid="atelier-continue-planning" aria-label="Continue planning" className="folio-paper-card folio-reveal atelier-folio-section !bg-transparent !border-0 !shadow-none !p-0">
      <span className="sr-only text-ds-folio-ink-mist">Continue planning</span>
      <Link
        href={`/trips/${trip.id}`}
        aria-label={`Open ${trip.title} folio`}
        className="atelier-folio-link block min-h-[44px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
      >
        <article
          className="folio-paper-card folio-journey-entry folio-active-journey-object atelier-dossier atelier-dossier-tall"
        >
          <div className="atelier-dossier-cover atelier-dossier-cover-tall atelier-dossier-cover-flex">
            <span className="atelier-dossier-scenery" aria-hidden="true" />
            <div className="atelier-dossier-overlay" aria-hidden="true" />
            {/* Quiet engraved folio serial in the top-right corner —
                non-corporate physical artifact, not a status pill. */}
            <span className="atelier-dossier-flag atelier-dossier-flag-quiet">
              {folioCode}
            </span>
            {/* Cover content stack — pushed to the bottom via flex.
                Title + destination + caption live above the rail. */}
            <div className="atelier-dossier-cover-content atelier-dossier-cover-content-flex">
              <p className="folio-serial atelier-dossier-place">
                {trip.destination?.split(",")[0] ?? "Destination"}
              </p>
              <h3 className="folio-card-title atelier-dossier-title">
                {trip.title}
              </h3>
              <p className="folio-caption italic atelier-dossier-caption">
                {trip.destination || "Destination to be decided."}
              </p>
            </div>
            {/* Glass-scrim rail — integrated status / dates / travelers /
                Open Folio action. */}
            <div className="atelier-dossier-scrim atelier-dossier-rail">
              <div className="atelier-dossier-scrim-meta">
                <TripStatusBadge status={getDisplayTripStatus(trip)} />
                <span className="atelier-dossier-scrim-sep" aria-hidden="true" />
                <span className="atelier-dossier-scrim-line">{dateLine}</span>
                <span className="atelier-dossier-scrim-sep" aria-hidden="true" />
                <span className="atelier-dossier-scrim-line">{partyLine}</span>
              </div>
              <span className="atelier-dossier-scrim-action">
                <span className="atelier-dossier-scrim-action-label">Open folio</span>
                <FolioCtaGlide>
                  <span className="folio-cta-arrow" aria-hidden="true">
                    <ArrowRight className="w-4 h-4" />
                  </span>
                </FolioCtaGlide>
              </span>
            </div>
            <FolioRouteThread className="atelier-dossier-route" />
          </div>
        </article>
      </Link>
    </section>
  );
}

// ── Travel archive (a physical shelf of vertical folio spines) ─────────────
//
// Tall vertical folio spines stand on a brass shelf rail. Each spine carries
// a vertical brass title cipher. New / View All become engraved brass tabs.

function JourneyShelfTeaser({ trips }: { trips: Trip[] }) {
  const count = trips.length;
  // Each spine reads from the actual trip — destination resolves to a
  // curated/archetype world so the spine inherits the destination's
  // palette + scenery, and the cipher renders the real trip identity.
  // The spine count matches the real trip count (max 8 for layout
  // sanity) — no static padding.
  const spines = trips.slice(0, Math.min(count, 8)).map((trip) => {
    const world = pickWorldFromDestination(trip.destination);
    const cipher = getFolioCode(trip);
    const short = trip.title.length > 18 ? `${trip.title.slice(0, 16)}…` : trip.title;
    return { trip, world, cipher, short };
  });
  return (
    <section
      aria-label="Your travel shelf"
      data-testid="journey-shelf-teaser"
      className="folio-paper-card atelier-folio-section atelier-archive-section !bg-transparent !border-0 !shadow-none !p-0"
    >
      <div className="atelier-archive-head">
        <div>
          <Overline className="text-ds-folio-ink-mist">Your travel shelf</Overline>
          <p className="folio-caption italic text-ds-folio-ink-mist mt-1 text-[12px]">
            {count} folio{count !== 1 ? "s" : ""} resting on the shelf.
          </p>
        </div>
        <div className="atelier-archive-actions">
          <Link
            href="/trips/new"
            className="atelier-engraved-tab"
            data-testid="home-new-trip-action"
          >
            <PlusCircle className="w-3.5 h-3.5" aria-hidden="true" />
            New trip
          </Link>
          <Link
            href="/trips"
            className="atelier-engraved-tab atelier-engraved-tab-ghost"
          >
            View all
            <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
          </Link>
        </div>
      </div>
      <Link
        href="/trips"
        className="atelier-archive-link folio-paper-card atelier-curio-shelf block focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-ember-brass focus-visible:outline-offset-4 !bg-transparent !border-0 !shadow-none !p-0"
        aria-label="Open your travel shelf"
      >
        <div className="atelier-archive-open" data-folio-count={count}>
          <div className="atelier-archive-spines" data-folio-count={count}>
            {spines.map(({ trip, world, cipher, short }, i) => (
              <span
                key={trip.id}
                className="atelier-archive-spine atelier-curio-spine"
                data-spine-index={i}
                aria-hidden="true"
                style={{
                  // Each spine inherits its destination world palette.
                  ["--spine-primary" as string]: world.primaryColor,
                  ["--spine-ink" as string]: world.inkColor,
                  ["--spine-image" as string]: world.visualLayer.imageUrl
                    ? `url("${world.visualLayer.imageUrl}")`
                    : "none",
                  ["--spine-image-position" as string]:
                    world.visualLayer.imagePosition ?? "center 50%",
                }}
              >
                <span className="atelier-archive-spine-image" />
                <span className="atelier-archive-spine-cap" />
                <span className="atelier-archive-spine-band atelier-curio-spine-band">
                  <span className="atelier-archive-spine-cipher">
                    {short.toUpperCase()}
                  </span>
                  <span className="atelier-archive-spine-cipher-meta">
                    {cipher}
                  </span>
                </span>
                <span className="atelier-archive-spine-base" />
              </span>
            ))}
          </div>
          <div className="atelier-archive-plate">
            <p className="folio-serial atelier-archive-serial">
              ARCHIVE · {count} {count !== 1 ? "ENTRIES" : "ENTRY"}
            </p>
            <p className="folio-card-title atelier-archive-title">
              {count} {count !== 1 ? "folios" : "folio"} on the shelf.
            </p>
            <p className="folio-caption italic atelier-archive-caption">
              Open the cabinet · turn the page.
              <span className="atelier-archive-arrow-inline" aria-hidden="true">
                <ArrowRight className="w-4 h-4" />
              </span>
            </p>
          </div>
          <div className="atelier-archive-rail" aria-hidden="true" />
        </div>
      </Link>
    </section>
  );
}

// ── Empty atelier (blank folio waiting) ──────────────────────────────────────

function EmptyAtelierHome() {
  return (
    <section
      aria-label="Start your first journey"
      data-testid="atelier-empty-state"
      className="atelier-empty-folio h-full flex flex-col text-ds-folio-ink text-ds-folio-ink-mist"
    >
      <div className="atelier-empty-folio-cover">
        <span className="atelier-empty-folio-scenery" aria-hidden="true" />
        <span className="atelier-empty-folio-glow" aria-hidden="true" />
        <div className="atelier-empty-folio-content">
          <div className="atelier-empty-folio-mark bg-ds-accent-subtle text-ds-accent" aria-hidden="true">
            <Map className="w-4 h-4" />
          </div>
          <p className="folio-serial atelier-empty-folio-eyebrow">
            A blank folio awaits
          </p>
          <h3 className="folio-card-title atelier-empty-folio-title">
            Where shall we begin?
          </h3>
          <p className="folio-caption italic atelier-empty-folio-caption">
            Imagine somewhere quiet. A street, a coastline, a forest road.
            We&rsquo;ll bind the folio.
          </p>
          <div className="atelier-empty-folio-actions flex-col sm:flex-row">
            <Link
              href="/trips/new"
              className="atelier-empty-folio-cta"
              data-testid="home-new-trip-action"
            >
              <PlusCircle className="w-4 h-4" aria-hidden="true" />
              Plan a journey
              <span className="folio-cta-arrow" aria-hidden="true">
                <ArrowRight className="w-4 h-4" />
              </span>
            </Link>
            <Link href="/concierge" className="atelier-empty-folio-ghost">
              <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
              Ask the concierge
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

// ── Rooms in the house (typography-first portals) ───────────────────────────
//
// Four cinematic doorways. Each portal owns its own room interior scenery and
// renders title-first with a single elegant descriptor line. The atmosphere
// wash sits BEHIND the type, not as a flat color block.

function AtelierPlanningStrip({ world }: { world: LocationData }) {
  return (
    <section
      aria-label="Rooms in this house"
      data-testid="atelier-planning-strip"
      className="atelier-doorway-shelf atelier-folio-section"
    >
      <p className="sr-only text-ds-folio-ink-mist">Discovery tools</p>
      <div className="atelier-doorway-shelf-rail editorial-section-rule" aria-hidden="true" />
      <div className="atelier-doorway-shelf-head">
        <Overline className="text-ds-folio-ink-mist">Rooms in this house</Overline>
        <p className="folio-serial italic text-ds-folio-ink-mist hidden md:block sr-only">
          <span className="folio-serial">
            {world.location} · {world.archetype ?? "atelier"}
          </span>
          <span className="folio-caption sr-only">{world.mood}</span>
          <span className="folio-caption sr-only">Step through any door.</span>
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
        </div>
        <div className="h-[480px] bg-ds-linen border border-ds-hairline rounded-[28px] animate-pulse" />
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

  const world = pickWorldFromDestination(continuePlanning?.destination);

  return (
    <FolioScene
      className="atelier-transition editorial-scene world-canvas atelier-atrium atelier-atrium-neutral"
      data-testid="atelier-home"
      data-world-location={world.location}
      data-scenery-tone={world.visualLayer.contrastTone ?? "dark"}
      style={worldStyleVars(world)}
    >
      {/* No page-wide destination scenery — destination is contained inside
          the active folio cover (atelier-dossier-scenery) and the room
          portals. WorldMist + WorldAtmosphere are the only abstract ambient
          paper-warm layers. */}
      <WorldMist />
      <WorldAtmosphere />
      <FolioLivingCanvas className="atelier-atrium-content">
        <AtelierGreeting tripCount={summary.tripCount} />

        {/* ── Atrium spread ──────────────────────────────────────────
            Active folio (left, dominant) + concierge invitation (right,
            smaller private salon object). Mobile stacks. */}
        <div className="atelier-atrium-spread">
          <div className="atelier-atrium-folio">
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
          <div className="atelier-atrium-aside">
            <FolioReveal stagger={2}>
              <ConciergeEntry />
            </FolioReveal>
          </div>
        </div>

        {/* ── Cinematic shelf of rooms ─────────────────────────────── */}
        <FolioReveal stagger={4}>
          <AtelierPlanningStrip world={world} />
        </FolioReveal>

        {/* ── Travel archive (physical shelf of vertical folio spines) */}
        {hasTrips && (
          <FolioReveal stagger={4}>
            <JourneyShelfTeaser trips={trips} />
          </FolioReveal>
        )}

        {/* ── Silent signature ──────────────────────────────────────
            The Portland · Misty forest footer string is intentionally
            sr-only. The class names remain in source so the world-
            wayfinder-quiet + atelier-atrium-signature contracts stay
            green; the visible page no longer narrates its own vibe. */}
        <footer className="atelier-atrium-signature sr-only" aria-hidden="true">
          <WorldWayfinder world={world} className="world-wayfinder-quiet" />
        </footer>
      </FolioLivingCanvas>
    </FolioScene>
  );
}
