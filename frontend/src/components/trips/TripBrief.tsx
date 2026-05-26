"use client";

import Link from "next/link";
import { Plane, Hotel, ArrowRight, Utensils, Clock } from "lucide-react";
import type { Trip, ItineraryDay, ItineraryItem } from "@/types";
import {
  deriveTripBriefFacts,
  type ScheduledFactType,
} from "@/lib/tripBriefFacts";

// Maximum scheduled facts shown before "+ N more fixed" overflow line.
const FACTS_CAP = 5;

// ── Props ────────────────────────────────────────────────────────────────────

export interface TripBriefProps {
  trip: Trip;
  days: ItineraryDay[];
  /** Unassigned Trip Ideas (candidates not yet placed into a day). */
  ideas: ItineraryItem[];
  /** Open the placement surface (Ideas Tray / Ideas workspace on mobile). */
  onReview: () => void;
}

// ── Icon per scheduled fact type ─────────────────────────────────────────────

function FactIcon({ type }: { type: ScheduledFactType }) {
  const cls = "w-3.5 h-3.5 flex-shrink-0 text-ds-folio-ink-mist";
  if (type === "flight") return <Plane className={cls} aria-hidden="true" />;
  if (type === "meal-reservation") return <Utensils className={cls} aria-hidden="true" />;
  if (type === "activity-entry") return <Clock className={cls} aria-hidden="true" />;
  return <Hotel className={cls} aria-hidden="true" />;
}

// ── Component ──────────────────────────────────────────────────────────────────
//
// The Brief is the calm, at-a-glance answer that opens Journey Desk: where the
// trip is, what is already fixed, and what still needs choosing. Every value is
// derived from real trip / itinerary / Trip Ideas data — never fabricated.
// "Anchors" and "Open Decisions" are merged into these few lines (blueprint §5).

export function TripBrief({ days, ideas, onReview }: TripBriefProps) {
  const placedItems: ItineraryItem[] = days.flatMap((d) => d.items ?? []);
  const placedCount = placedItems.length;
  const ideasCount = ideas.length;
  const totalCandidates = placedCount + ideasCount;

  const firstFlight = placedItems.find((i) => i.itemType === "flight");
  const firstHotel = placedItems.find((i) => i.itemType === "hotel");
  const hasFlight = !!firstFlight;
  const hasHotel = !!firstHotel;

  // Scheduled facts — fixed anchors derived from real placed data.
  const allFacts = deriveTripBriefFacts(days);
  const visibleFacts = allFacts.slice(0, FACTS_CAP);
  const hiddenFactsCount = allFacts.length - visibleFacts.length;

  // Pending lines — essential anchors still missing. Honest, never faked.
  const pendingLines: { label: string; Icon: typeof Plane }[] = [];
  if (!hasFlight) pendingLines.push({ label: "Flights", Icon: Plane });
  if (!hasHotel) pendingLines.push({ label: "Stay", Icon: Hotel });

  return (
    <section
      data-testid="journey-desk-brief"
      aria-label="Trip brief"
      className="mb-4 sm:mb-6 journey-desk-brief"
    >
      {/* Header — overline + real placed progress */}
      <div className="flex items-baseline justify-between gap-3 px-5 pt-4 pb-2">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-ds-accent">
          The Brief
        </p>
        {totalCandidates > 0 && (
          <span data-testid="jd-brief-progress" className="text-xs text-ds-folio-ink-mist">
            {placedCount} of {totalCandidates} placed
          </span>
        )}
      </div>

      <div className="px-5 pb-3.5">
        {/* Scheduled facts — read-only fixed trip anchors */}
        {visibleFacts.map((fact, i) => (
          <div
            key={`${fact.type}-${fact.title}-${i}`}
            data-testid="jd-brief-scheduled-fact"
            className="jd-brief-row flex items-center gap-2.5 py-2"
          >
            <FactIcon type={fact.type} />
            <span className="text-sm text-ds-folio-ink flex-1 min-w-0 truncate">
              <span className="font-semibold">{fact.label}</span>
              <span className="text-ds-folio-ink-soft"> · {fact.title}</span>
            </span>
            {(fact.time ?? fact.date) && (
              <span className="text-xs text-ds-folio-ink-mist flex-shrink-0 ml-auto pl-2">
                {fact.time
                  ? `Day ${fact.dayNumber} · ${fact.time}`
                  : `Day ${fact.dayNumber}`}
              </span>
            )}
          </div>
        ))}
        {hiddenFactsCount > 0 && (
          <p
            data-testid="jd-brief-more-fixed"
            className="text-xs text-ds-folio-ink-mist py-1 pl-7"
          >
            + {hiddenFactsCount} more fixed
          </p>
        )}

        {/* Pending — essential anchors still to choose (one line each) */}
        {pendingLines.map((line) => (
          <div
            key={line.label}
            data-testid="jd-brief-pending"
            className="jd-brief-row flex items-center justify-between gap-3 py-2"
          >
            <span className="inline-flex items-center gap-2.5 text-sm text-ds-folio-ink">
              <line.Icon className="w-3.5 h-3.5 flex-shrink-0 text-ds-folio-ink-mist" aria-hidden="true" />
              <span>
                <span className="font-semibold">{line.label}</span>
                <span className="text-ds-folio-ink-soft"> · still to choose</span>
              </span>
            </span>
            <button
              type="button"
              onClick={onReview}
              className="text-xs font-medium text-ds-folio-ink-soft hover:text-ds-marine-ink transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 rounded"
            >
              Choose
            </button>
          </div>
        ))}

        {/* Decide — real Trip Ideas count, or an honest "no ideas yet" nudge */}
        <div
          data-testid="jd-brief-decide"
          className="jd-brief-row flex items-center justify-between gap-3 py-2"
        >
          {ideasCount > 0 ? (
            <>
              <span className="text-sm text-ds-folio-ink">
                <span className="font-semibold">{ideasCount}</span>
                <span className="text-ds-folio-ink-soft">
                  {" "}still to decide
                </span>
              </span>
              <button
                type="button"
                data-testid="jd-brief-review-action"
                onClick={onReview}
                className="inline-flex items-center gap-1.5 px-3 py-2 min-h-[44px] rounded-lg text-xs font-medium bg-ds-marine-ink text-ds-paper hover:bg-ds-marine-soft transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2"
              >
                Review ideas
                <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
              </button>
            </>
          ) : (
            <span className="inline-flex items-center flex-wrap gap-x-1.5 gap-y-0.5 text-sm text-ds-folio-ink-soft">
              <span className="italic text-ds-folio-ink-mist">No saved ideas yet —</span>
              <span>
                start from{" "}
                <Link
                  href="/explore"
                  className="font-medium text-ds-folio-ink-soft hover:text-ds-marine-ink underline decoration-ds-hairline underline-offset-2 transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 rounded"
                >
                  Explore
                </Link>{" "}
                or{" "}
                <Link
                  href="/saved"
                  className="font-medium text-ds-folio-ink-soft hover:text-ds-marine-ink underline decoration-ds-hairline underline-offset-2 transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 rounded"
                >
                  Saved
                </Link>
              </span>
            </span>
          )}
        </div>
      </div>
    </section>
  );
}
