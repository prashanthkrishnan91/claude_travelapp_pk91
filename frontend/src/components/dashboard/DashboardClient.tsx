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
import { FolioPanel } from "@/components/ui/Folio";
import type { Trip } from "@/types";

// ── Helpers ────────────────────────────────────────────────────────────────────

function getTimeGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning.";
  if (hour < 18) return "Good afternoon.";
  return "Good evening.";
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

// ── Overline type role ────────────────────────────────────────────────────────

function Overline({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <p className={`text-[10px] font-semibold uppercase tracking-[0.1em] ${className ?? "text-ds-folio-ink-mist"}`}>
      {children}
    </p>
  );
}

// ── Atelier greeting ──────────────────────────────────────────────────────────

function AtelierGreeting({ tripCount }: { tripCount: number }) {
  const greeting = getTimeGreeting();
  return (
    <header data-testid="atelier-greeting">
      <div className="folio-issue-eyebrow">Private Travel Concierge</div>
      <h1 className="folio-display mt-2">
        {greeting}
      </h1>
      <p className="folio-editorial-sub mt-1 mb-3">
        Your private travel edition.
      </p>
      <p className="text-[11px] tracking-[0.06em] text-ds-folio-ink-mist">
        {tripCount > 0
          ? `${tripCount} trip${tripCount !== 1 ? "s" : ""} on your shelf.`
          : "Plan, discover, and refine — at your own pace."}
      </p>
      <div className="mapline-rule mt-4" aria-hidden="true" />
    </header>
  );
}

// ── Primary concierge instrument ──────────────────────────────────────────────

function ConciergeEntry() {
  return (
    <section aria-label="AI Concierge" data-testid="concierge-entry">
      <FolioPanel data-testid="concierge-advisor-desk">
        <div className="folio-card-accent" aria-hidden="true" />
        <div className="px-6 pt-5 pb-4 border-b border-ds-hairline">
          <Overline className="text-ds-folio-ink-mist">Private Travel Concierge</Overline>
          <h2 className="folio-heading mt-2">
            Your private concierge.
          </h2>
        </div>
        <div className="px-6 py-6">
          <p className="folio-caption mb-6">
            Restaurants, hotels, and hidden gems — prepared privately for you.
          </p>
          <Link
            href="/concierge"
            className="btn-marine min-h-[44px] w-full"
          >
            Open Concierge
            <ArrowRight className="w-4 h-4" aria-hidden="true" />
          </Link>
        </div>
      </FolioPanel>
    </section>
  );
}

// ── Continue planning ─────────────────────────────────────────────────────────

function ContinuePlanningStrip({ trip }: { trip: Trip }) {
  return (
    <section
      aria-label="Continue planning"
      data-testid="atelier-continue-planning"
    >
      <Overline className="text-ds-folio-ink-mist">Continue planning</Overline>
      <article className="folio-paper-card mt-3 p-5">
        <div className="flex items-start gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-2">
              <TripStatusBadge status={getDisplayTripStatus(trip)} />
              <p className="folio-serial">{trip.status.toUpperCase()} · FOLIO</p>
            </div>
            <h3 className="folio-card-title mb-0.5">
              {trip.title}
            </h3>
            <p className="folio-caption truncate">
              {trip.destination}
            </p>
            <p className="folio-serial mt-2">
              {formatDateRange(trip.startDate, trip.endDate)}
              {trip.travelers > 1 && ` · ${trip.travelers} travelers`}
            </p>
          </div>
          <Link
            href={`/trips/${trip.id}`}
            className="shrink-0 inline-flex items-center gap-1.5 text-xs font-semibold text-ds-accent hover:text-ds-accent-muted transition min-h-[44px] self-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
          >
            Open <ArrowRight className="w-3 h-3" aria-hidden="true" />
          </Link>
        </div>
      </article>
    </section>
  );
}

// ── Journey shelf teaser ──────────────────────────────────────────────────────

function JourneyShelfTeaser({ count }: { count: number }) {
  return (
    <section
      aria-label="Your travel shelf"
      data-testid="journey-shelf-teaser"
    >
      <div className="flex items-center justify-between mb-3">
        <Overline className="text-ds-folio-ink-mist">Your travel shelf</Overline>
        <div className="flex items-center gap-3">
          <Link
            href="/trips/new"
            className="flex items-center gap-1 text-xs font-medium text-ds-accent hover:text-ds-accent-muted transition min-h-[44px]"
            data-testid="home-new-trip-action"
          >
            <PlusCircle className="w-3 h-3" aria-hidden="true" />
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
        className="folio-paper-card block p-5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
      >
        <p className="folio-serial mb-2">
          YOUR ARCHIVE · {count} {count !== 1 ? "ENTRIES" : "ENTRY"}
        </p>
        <p className="text-sm font-medium text-ds-folio-ink mb-1">
          {count} trip{count !== 1 ? "s" : ""} in the archive
        </p>
        <div className="flex items-end justify-between">
          <p className="folio-caption">
            Browse your full journey collection.
          </p>
          <ArrowRight
            className="w-4 h-4 text-ds-folio-ink-mist shrink-0 ml-3"
            aria-hidden="true"
          />
        </div>
      </Link>
    </section>
  );
}

// ── Empty atelier state ───────────────────────────────────────────────────────

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
        <h2 className="text-xl font-semibold text-ds-folio-ink mb-2">
          Your travel shelf is empty.
        </h2>
        <p className="text-sm text-ds-folio-ink-mist max-w-sm mx-auto leading-relaxed">
          Plan your first trip, or ask the concierge to help you discover where
          to go.
        </p>
      </div>
      <div className="flex flex-col sm:flex-row gap-3">
        <Link
          href="/trips/new"
          className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-ds-accent text-ds-text-inverse text-sm font-semibold hover:opacity-90 transition-opacity min-h-[44px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
          data-testid="home-new-trip-action"
        >
          <PlusCircle className="w-4 h-4" aria-hidden="true" />
          Plan a Trip
        </Link>
        <Link
          href="/concierge"
          className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl border border-ds-hairline bg-ds-linen text-ds-folio-ink-soft text-sm font-medium hover:bg-ds-bone hover:text-ds-folio-ink transition-all min-h-[44px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
        >
          <Sparkles className="w-4 h-4" aria-hidden="true" />
          Open Concierge
        </Link>
      </div>
    </section>
  );
}

// ── Discovery tools strip ─────────────────────────────────────────────────────

function AtelierPlanningStrip() {
  return (
    <section
      aria-label="Discovery tools"
      data-testid="atelier-planning-strip"
    >
      <div className="editorial-section-rule" aria-hidden="true" />
      <Overline className="text-ds-folio-ink-mist">Discovery tools</Overline>
      <div className="grid grid-cols-2 gap-3 mt-3">
        <Link
          href="/explore"
          className="folio-paper-card group flex flex-col gap-2 p-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
        >
          <p className="folio-serial">01 · EXPLORE</p>
          <p className="text-sm font-medium text-ds-folio-ink group-hover:text-ds-accent transition truncate">
            Explore
          </p>
          <p className="folio-caption truncate">
            Hotels, dining &amp; more
          </p>
        </Link>
        <Link
          href="/saved"
          className="folio-paper-card group flex flex-col gap-2 p-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
        >
          <p className="folio-serial">02 · SAVED</p>
          <p className="text-sm font-medium text-ds-folio-ink group-hover:text-ds-accent transition truncate">
            Saved Ideas
          </p>
          <p className="folio-caption truncate">
            Your travel scrapbook
          </p>
        </Link>
      </div>
    </section>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

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

  return (
    <div className="space-y-8 atelier-transition editorial-scene" data-testid="atelier-home">
      <AtelierGreeting tripCount={summary.tripCount} />
      <ConciergeEntry />
      {hasTrips && continuePlanning && (
        <ContinuePlanningStrip trip={continuePlanning} />
      )}
      {hasTrips ? (
        <JourneyShelfTeaser count={summary.tripCount} />
      ) : (
        <EmptyAtelierHome />
      )}
      <AtelierPlanningStrip />
    </div>
  );
}
