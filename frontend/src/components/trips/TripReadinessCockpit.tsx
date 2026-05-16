"use client";

import Link from "next/link";
import {
  CalendarDays,
  Plane,
  Hotel,
  Utensils,
  MapPin,
  Sparkles,
  Zap,
  BookOpen,
} from "lucide-react";
import type { Trip, ItineraryDay, ItineraryItem } from "@/types";

// ── Props ────────────────────────────────────────────────────────────────────

export interface TripReadinessCockpitProps {
  trip: Trip;
  itineraryDays: ItineraryDay[];
  onOpenConcierge: () => void;
  onOpenOptimize: () => void;
  onOpenEdit: () => void;
}

// ── Derived readiness ────────────────────────────────────────────────────────

interface ReadinessData {
  hasDates: boolean;
  totalDays: number;
  activeDayCount: number;
  totalItems: number;
  hasFlights: boolean;
  hasHotel: boolean;
  hasDining: boolean;
  hasActivities: boolean;
}

function deriveReadiness(trip: Trip, days: ItineraryDay[]): ReadinessData {
  const allItems: ItineraryItem[] = days.flatMap((d) => d.items ?? []);
  const activeDays = days.filter((d) => (d.items ?? []).length > 0);
  return {
    hasDates: !!(trip.startDate && trip.endDate),
    totalDays: days.length,
    activeDayCount: activeDays.length,
    totalItems: allItems.length,
    hasFlights: allItems.some((i) => i.itemType === "flight"),
    hasHotel: allItems.some((i) => i.itemType === "hotel"),
    hasDining: allItems.some((i) => i.itemType === "meal"),
    hasActivities: allItems.some((i) => i.itemType === "activity"),
  };
}

// ── Shared button class ───────────────────────────────────────────────────────

const ACTION_BTN =
  "inline-flex items-center gap-1.5 px-3 py-2 min-h-[44px] rounded-lg text-xs font-medium transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2";

const PRIMARY_BTN = `${ACTION_BTN} bg-ds-accent text-ds-text-inverse hover:opacity-90`;
const GHOST_BTN = `${ACTION_BTN} border border-ds-pen-stroke text-ds-text-secondary hover:bg-ds-carbon`;

// ── Main component ────────────────────────────────────────────────────────────

export function TripReadinessCockpit({
  trip,
  itineraryDays,
  onOpenConcierge,
  onOpenOptimize,
  onOpenEdit,
}: TripReadinessCockpitProps) {
  const r = deriveReadiness(trip, itineraryDays);

  // ── Signal definitions ──────────────────────────────────────────────────────

  const signals = [
    {
      key: "flights",
      label: "Flights",
      icon: <Plane className="w-3.5 h-3.5" aria-hidden="true" />,
      present: r.hasFlights,
      presentCopy: "Looks like flights are in the plan",
      missingCopy: "Still needs a flight",
    },
    {
      key: "hotel",
      label: "Stay",
      icon: <Hotel className="w-3.5 h-3.5" aria-hidden="true" />,
      present: r.hasHotel,
      presentCopy: "A place to stay is set",
      missingCopy: "Still needs somewhere to stay",
    },
    {
      key: "dining",
      label: "Dining",
      icon: <Utensils className="w-3.5 h-3.5" aria-hidden="true" />,
      present: r.hasDining,
      presentCopy: "Some dining is on the plan",
      missingCopy: "No dining added yet",
    },
    {
      key: "activities",
      label: "Activities",
      icon: <MapPin className="w-3.5 h-3.5" aria-hidden="true" />,
      present: r.hasActivities,
      presentCopy: "Activities are on the schedule",
      missingCopy: "No activities planned yet",
    },
  ] as const;

  const coveredCount = signals.filter((s) => s.present).length;

  // ── Headline copy ────────────────────────────────────────────────────────────

  function getHeadline(): string {
    if (!r.hasDates) return "Start by adding your travel dates";
    if (r.totalItems === 0) return "Ready to start planning";
    if (coveredCount === signals.length) return "Your trip is looking well-planned";
    if (coveredCount >= 2) return "Good progress — a few gaps to fill";
    return "Building out your itinerary";
  }

  // ── Next best action ─────────────────────────────────────────────────────────
  // Priority: dates → flights → hotel → empty days → all good

  let nextStepDescription: string;
  let primaryAction: React.ReactNode;
  let secondaryAction: React.ReactNode | null = null;

  if (!r.hasDates) {
    nextStepDescription = "Add travel dates to unlock full day-by-day planning.";
    primaryAction = (
      <button onClick={onOpenEdit} className={PRIMARY_BTN}>
        <CalendarDays className="w-3.5 h-3.5" aria-hidden="true" />
        Add Dates
      </button>
    );
  } else if (!r.hasFlights) {
    nextStepDescription = "Locking in flights is usually the best place to start.";
    primaryAction = (
      <button onClick={onOpenOptimize} className={PRIMARY_BTN}>
        <Zap className="w-3.5 h-3.5" aria-hidden="true" />
        Find Flights
      </button>
    );
    secondaryAction = (
      <button onClick={onOpenConcierge} className={GHOST_BTN}>
        <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
        Ask Concierge
      </button>
    );
  } else if (!r.hasHotel) {
    nextStepDescription = "Flights are set. Finding a place to stay is the natural next step.";
    primaryAction = (
      <button onClick={onOpenConcierge} className={PRIMARY_BTN}>
        <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
        Ask Concierge
      </button>
    );
    secondaryAction = (
      <Link href="/explore" className={GHOST_BTN}>
        Explore Hotels
      </Link>
    );
  } else if (r.totalDays > 0 && r.activeDayCount < r.totalDays) {
    const emptyDays = r.totalDays - r.activeDayCount;
    nextStepDescription = `${emptyDays} day${emptyDays === 1 ? "" : "s"} still need plans. Your Concierge can suggest what fits.`;
    primaryAction = (
      <button onClick={onOpenConcierge} className={PRIMARY_BTN}>
        <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
        Plan with Concierge
      </button>
    );
    secondaryAction = (
      <Link href="/explore" className={GHOST_BTN}>
        Explore Nearby
      </Link>
    );
  } else {
    nextStepDescription =
      "Your trip is looking well-planned. The Concierge can help add finishing touches.";
    primaryAction = (
      <button onClick={onOpenConcierge} className={PRIMARY_BTN}>
        <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
        Review with Concierge
      </button>
    );
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <section
      aria-labelledby="trip-readiness-heading"
      data-testid="trip-readiness-cockpit"
      className="mb-6 rounded-2xl border border-ds-pen-stroke bg-ds-onyx shadow-[var(--ds-elevation-2)] overflow-hidden"
    >
      {/* ── Header: advisor note — no score/KPI indicator ──────────────────── */}
      <div className="px-5 pt-4 pb-3 border-b border-ds-pen-stroke">
        <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-text-tertiary">
          Concierge Notes
        </p>
        <h2
          id="trip-readiness-heading"
          className="mt-0.5 text-sm font-semibold text-ds-text leading-snug"
        >
          {getHeadline()}
        </h2>
      </div>

      {/* ── Day coverage: compact pills, no dashboard-grid header ─────────── */}
      {r.totalDays > 0 && (
        <div
          className="px-5 py-3 border-b border-ds-pen-stroke"
          data-testid="day-coverage-strip"
        >
          <div className="flex items-center flex-wrap gap-2">
            <div
              role="list"
              aria-label="Day coverage"
              className="flex items-center flex-wrap gap-1.5"
            >
              {itineraryDays.map((day) => {
                const hasItems = (day.items ?? []).length > 0;
                return (
                  <span
                    key={day.id}
                    role="listitem"
                    aria-label={`Day ${day.dayNumber}: ${hasItems ? "has plans" : "no plans yet"}`}
                    className={[
                      "inline-flex items-center justify-center w-7 h-7 rounded-full text-[10px] font-semibold select-none",
                      hasItems
                        ? "bg-ds-accent text-ds-text-inverse"
                        : "border border-ds-pen-stroke text-ds-text-tertiary",
                    ].join(" ")}
                  >
                    {day.dayNumber}
                  </span>
                );
              })}
            </div>
            <span className="text-xs text-ds-text-tertiary">
              {r.activeDayCount === r.totalDays
                ? "All days covered"
                : r.activeDayCount === 0
                ? "No days planned yet"
                : `${r.activeDayCount} of ${r.totalDays} days planned`}
            </span>
          </div>
        </div>
      )}

      {/* ── Signal observations — advisor note style, 2×2 grid ───────────── */}
      <div
        className="grid grid-cols-2 gap-x-4 gap-y-3 px-5 py-4 sm:grid-cols-4"
        data-testid="readiness-signals"
      >
        {signals.map((signal) => (
          <div
            key={signal.key}
            data-testid={`readiness-signal-${signal.key}`}
            className="flex items-center gap-2.5"
          >
            <span
              aria-hidden="true"
              className={[
                "flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center",
                signal.present
                  ? "text-ds-accent"
                  : "border border-ds-pen-stroke text-ds-text-tertiary",
              ].join(" ")}
              style={signal.present ? { backgroundColor: "var(--ds-accent-subtle)" } : undefined}
            >
              {signal.icon}
            </span>
            <p className="text-xs text-ds-text-secondary leading-snug">
              {signal.present ? signal.presentCopy : signal.missingCopy}
            </p>
          </div>
        ))}
      </div>

      {/* ── Advisor recommendation — advisor prose, flows naturally ─────── */}
      <div
        className="px-5 pb-4 pt-3 border-t border-ds-pen-stroke bg-ds-carbon"
        data-testid="next-action-area"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm italic text-ds-text-secondary leading-snug max-w-prose">
            {nextStepDescription}
          </p>
          <div className="flex items-center gap-2 flex-shrink-0 flex-wrap">
            {secondaryAction}
            {primaryAction}
          </div>
        </div>
      </div>

      {/* ── Planning tools — subtle, no section label ─────────────────────── */}
      <div
        className="px-5 py-3 border-t border-ds-pen-stroke flex items-center gap-4 flex-wrap"
        data-testid="planning-tools-strip"
      >
        <Link
          href="/explore"
          className="inline-flex items-center gap-1 text-xs text-ds-text-secondary hover:text-ds-text transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2 rounded"
        >
          <MapPin className="w-3.5 h-3.5 text-ds-accent" aria-hidden="true" />
          Explore
        </Link>
        <Link
          href="/saved"
          className="inline-flex items-center gap-1 text-xs text-ds-text-secondary hover:text-ds-text transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2 rounded"
        >
          <BookOpen className="w-3.5 h-3.5 text-ds-accent" aria-hidden="true" />
          Saved Ideas
        </Link>
        <button
          onClick={onOpenConcierge}
          aria-label="Open AI Concierge panel"
          className="inline-flex items-center gap-1 text-xs text-ds-text-secondary hover:text-ds-text transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2 rounded"
        >
          <Sparkles className="w-3.5 h-3.5 text-ds-accent" aria-hidden="true" />
          AI Concierge
        </button>
      </div>
    </section>
  );
}
