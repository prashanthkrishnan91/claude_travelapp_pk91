"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Map,
  Sparkles,
  BookmarkCheck,
  Compass,
  PlusCircle,
  ArrowRight,
  Calendar,
  Users,
  MapPin,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { TripStatusBadge } from "@/components/ui/TripStatusBadge";
import {
  fetchDashboardSummary,
  fetchTrips,
  type DashboardSummary,
} from "@/lib/api";
import { getDisplayTripStatus, getTripStatusGroup } from "@/lib/tripStatus";
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

function Overline({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-text-tertiary">
      {children}
    </p>
  );
}

// ── Atelier greeting ──────────────────────────────────────────────────────────

function AtelierGreeting({ tripCount }: { tripCount: number }) {
  const greeting = getTimeGreeting();
  return (
    <header data-testid="atelier-greeting">
      <Overline>Private Travel Concierge</Overline>
      <h1 className="text-2xl font-semibold text-ds-text mt-2 mb-1">
        {greeting}
      </h1>
      <p className="text-sm text-ds-text-tertiary">
        {tripCount > 0
          ? `${tripCount} trip${tripCount !== 1 ? "s" : ""} on your shelf.`
          : "Your private travel atelier. Plan, discover, and refine."}
      </p>
      {/* Editorial mapline — route-motif accent below the greeting */}
      <div className="mapline-rule mt-4" aria-hidden="true" />
    </header>
  );
}

// ── Primary concierge instrument ──────────────────────────────────────────────

function ConciergeEntry() {
  return (
    <section aria-label="AI Concierge" data-testid="concierge-entry">
      {/* advisor-desk-panel: visible 2-zone desk composition (brass rule + warm glow) */}
      <div className="advisor-desk-panel boutique-instrument" data-testid="concierge-advisor-desk">
        {/* Desk header zone — warmer/darker band with stamp mark */}
        <div className="concierge-desk-header px-6 pt-5 pb-4">
          <div className="flex items-center gap-3">
            <div
              className="atelier-stamp shrink-0"
              aria-hidden="true"
            >
              AI
            </div>
            <div className="flex-1 min-w-0">
              <Overline>Private Travel Concierge</Overline>
              <h2 className="text-base font-semibold text-ds-text mt-0.5 leading-snug">
                AI Travel Concierge
              </h2>
            </div>
            <div
              className="flex items-center justify-center w-9 h-9 rounded-xl bg-ds-accent-subtle text-ds-accent shrink-0"
              aria-hidden="true"
            >
              <Sparkles className="w-4 h-4" />
            </div>
          </div>
        </div>
        {/* Desk body — description and primary CTA */}
        <div className="px-6 py-5">
          <p className="text-sm text-ds-text-secondary leading-relaxed mb-4">
            Ask for restaurants, hotels, or activities — anywhere. Your
            private concierge, ready when you are.
          </p>
          <Link
            href="/concierge"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-ds-accent text-ds-text-inverse text-sm font-semibold hover:opacity-90 transition-opacity min-h-[44px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
          >
            Open Concierge
            <ArrowRight className="w-4 h-4" aria-hidden="true" />
          </Link>
        </div>
      </div>
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
      <Overline>Continue planning</Overline>
      <Card
        as="article"
        tone="dark"
        className="mt-3 p-5 hover:border-ds-accent/40 transition-colors duration-200 atelier-surface-depth"
      >
        <div className="flex items-start gap-4">
          <div
            className="flex items-center justify-center w-10 h-10 rounded-xl bg-ds-accent-subtle text-ds-accent shrink-0"
            aria-hidden="true"
          >
            <MapPin className="w-4 h-4" />
          </div>
          <div className="flex-1 min-w-0">
            <TripStatusBadge status={getDisplayTripStatus(trip)} />
            <h3 className="text-sm font-semibold text-ds-text mt-1.5 mb-0.5">
              {trip.title}
            </h3>
            <p className="text-xs text-ds-text-secondary truncate">
              {trip.destination}
            </p>
            <p className="text-xs text-ds-text-tertiary mt-1 flex items-center gap-1.5 flex-wrap">
              <Calendar className="w-3 h-3" aria-hidden="true" />
              {formatDateRange(trip.startDate, trip.endDate)}
              {trip.travelers > 1 && (
                <>
                  {" "}
                  ·{" "}
                  <Users className="w-3 h-3" aria-hidden="true" />
                  {trip.travelers} travelers
                </>
              )}
            </p>
          </div>
          <Link
            href={`/trips/${trip.id}`}
            className="shrink-0 inline-flex items-center gap-1.5 text-xs font-semibold text-ds-accent hover:text-ds-accent-muted transition min-h-[44px] self-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
          >
            Open <ArrowRight className="w-3 h-3" aria-hidden="true" />
          </Link>
        </div>
      </Card>
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
        <Overline>Your travel shelf</Overline>
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
        className="flex items-center gap-3 p-4 rounded-xl border border-ds-pen-stroke bg-ds-onyx hover:border-ds-accent/40 transition-all duration-200 atelier-surface-depth focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
      >
        <div
          className="flex items-center justify-center w-9 h-9 rounded-lg bg-ds-accent-subtle text-ds-accent shrink-0"
          aria-hidden="true"
        >
          <Map className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-ds-text">
            {count} trip{count !== 1 ? "s" : ""} planned
          </p>
          <p className="text-xs text-ds-text-tertiary">
            Browse your full journey shelf
          </p>
        </div>
        <ArrowRight
          className="w-4 h-4 text-ds-text-tertiary shrink-0"
          aria-hidden="true"
        />
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
        <h2 className="text-xl font-semibold text-ds-text mb-2">
          Your travel shelf is empty.
        </h2>
        <p className="text-sm text-ds-text-tertiary max-w-sm mx-auto leading-relaxed">
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
          className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl border border-ds-pen-stroke bg-ds-carbon text-ds-text text-sm font-medium hover:border-ds-accent/40 hover:text-ds-accent transition-all min-h-[44px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
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
      <Overline>Discovery tools</Overline>
      <div className="grid grid-cols-2 gap-3 mt-3">
        <Link
          href="/explore"
          className="group flex items-center gap-3 p-4 rounded-xl border border-ds-pen-stroke bg-ds-onyx hover:border-ds-accent/40 transition-all duration-200 atelier-surface-depth focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
        >
          <span
            className="flex items-center justify-center w-8 h-8 rounded-lg bg-ds-accent-subtle text-ds-accent shrink-0"
            aria-hidden="true"
          >
            <Compass className="w-4 h-4" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-medium text-ds-text group-hover:text-ds-accent transition truncate">
              Explore
            </p>
            <p className="text-xs text-ds-text-tertiary truncate">
              Hotels, dining &amp; more
            </p>
          </div>
        </Link>
        <Link
          href="/saved"
          className="group flex items-center gap-3 p-4 rounded-xl border border-ds-pen-stroke bg-ds-onyx hover:border-ds-accent/40 transition-all duration-200 atelier-surface-depth focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
        >
          <span
            className="flex items-center justify-center w-8 h-8 rounded-lg bg-ds-accent-subtle text-ds-accent shrink-0"
            aria-hidden="true"
          >
            <BookmarkCheck className="w-4 h-4" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-medium text-ds-text group-hover:text-ds-accent transition truncate">
              Saved Ideas
            </p>
            <p className="text-xs text-ds-text-tertiary truncate">
              Your travel scrapbook
            </p>
          </div>
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
          <div className="h-3 w-28 bg-ds-pen-stroke rounded animate-pulse" />
          <div className="h-7 w-44 bg-ds-pen-stroke rounded animate-pulse" />
          <div className="h-4 w-36 bg-ds-pen-stroke rounded animate-pulse" />
        </div>
        <div className="h-36 bg-ds-onyx border border-ds-pen-stroke rounded-lg animate-pulse" />
        <div className="h-24 bg-ds-onyx border border-ds-pen-stroke rounded-lg animate-pulse" />
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
