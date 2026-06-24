"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Plane,
  Hotel,
  ArrowRight,
  Utensils,
  Clock,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import type { Trip, ItineraryDay, ItineraryItem } from "@/types";
import { AtelierBackdrop } from "@/components/atmosphere/AtelierBackdrop";
import {
  deriveTripBriefSummary,
  type StaySummaryRow,
  type ScheduledFactType,
} from "@/lib/tripBriefFacts";

// ── Props ────────────────────────────────────────────────────────────────────

export interface TripBriefProps {
  trip: Trip;
  days: ItineraryDay[];
  /** Unassigned Trip Ideas (candidates not yet placed into a day). */
  ideas: ItineraryItem[];
  /** Open the placement surface (Ideas Tray / Ideas workspace on mobile). */
  onReview: () => void;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatStayRange(s: StaySummaryRow): string {
  if (s.checkInDay !== null && s.checkOutDay !== null)
    return `Day ${s.checkInDay} → Day ${s.checkOutDay}`;
  if (s.checkInDay !== null) return `From Day ${s.checkInDay}`;
  if (s.checkOutDay !== null) return `To Day ${s.checkOutDay}`;
  return "Stay";
}

function FactIcon({ type }: { type: ScheduledFactType }) {
  const cls = "w-3.5 h-3.5 flex-shrink-0 text-ds-folio-ink-mist";
  if (type === "flight") return <Plane className={cls} aria-hidden="true" />;
  if (type === "meal-reservation") return <Utensils className={cls} aria-hidden="true" />;
  if (type === "activity-entry") return <Clock className={cls} aria-hidden="true" />;
  return <Hotel className={cls} aria-hidden="true" />;
}

function factLabel(type: ScheduledFactType): string {
  if (type === "flight") return "Flight";
  if (type === "hotel-checkin") return "Check in";
  if (type === "hotel-checkout") return "Check out";
  if (type === "hotel-stay") return "Stay";
  if (type === "meal-reservation") return "Reservation";
  return "Entry";
}

// ── Component ──────────────────────────────────────────────────────────────────
//
// The Brief is the calm, at-a-glance answer that opens Journey Desk: where the
// trip is, what is already fixed, and what still needs choosing. Every value is
// derived from real trip / itinerary / Trip Ideas data — never fabricated.

export function TripBrief({ days, ideas, onReview }: TripBriefProps) {
  const [detailsOpen, setDetailsOpen] = useState(false);

  const placedItems: ItineraryItem[] = days.flatMap((d) => d.items ?? []);
  const placedCount = placedItems.length;
  const ideasCount = ideas.length;
  const totalCandidates = placedCount + ideasCount;

  const firstFlight = placedItems.find((i) => i.itemType === "flight");
  const firstHotel = placedItems.find((i) => i.itemType === "hotel");
  const hasFlight = !!firstFlight;
  const hasHotel = !!firstHotel;

  const { flights, stays, reservationCount, entryCount, allFacts } =
    deriveTripBriefSummary(days);

  const timedLabel = [
    reservationCount > 0
      ? `${reservationCount} ${reservationCount === 1 ? "reservation" : "reservations"}`
      : "",
    entryCount > 0
      ? `${entryCount} ${entryCount === 1 ? "entry time" : "entry times"}`
      : "",
  ]
    .filter(Boolean)
    .join(" · ");

  const nextTimed = allFacts.find(
    (f) => f.type === "meal-reservation" || f.type === "activity-entry",
  );

  // Pending lines — essential anchors still missing. Honest, never faked.
  const pendingLines: { label: string; Icon: typeof Plane }[] = [];
  if (!hasFlight) pendingLines.push({ label: "Flights", Icon: Plane });
  if (!hasHotel) pendingLines.push({ label: "Stay", Icon: Hotel });

  return (
    <section
      data-testid="journey-desk-brief"
      aria-label="Trip brief"
      className="relative isolate overflow-hidden mb-4 sm:mb-6 journey-desk-brief"
    >
      {/* Atmospheric Background System v1 — brief-texture, the lightest role,
          rendered through the shared component (absolute mode) so the Brief is
          centrally managed like every other surface. Content sits above it. */}
      <AtelierBackdrop role="brief-texture" mode="absolute" />

      <div className="relative z-10">
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
        {/* Flights section */}
        {flights.length > 0 && (
          <div data-testid="jd-brief-section-flights">
            {flights.map((f, i) => (
              <div
                key={`flight-${i}`}
                data-testid="jd-brief-flight-row"
                className="jd-brief-row flex items-center gap-2.5 py-2"
              >
                <Plane
                  className="w-3.5 h-3.5 flex-shrink-0 text-ds-folio-ink-mist"
                  aria-hidden="true"
                />
                <span className="text-sm text-ds-folio-ink flex-1 min-w-0 truncate">
                  {f.title}
                </span>
                <span className="text-xs text-ds-folio-ink-mist flex-shrink-0 ml-auto pl-2">
                  {f.time ? `Day ${f.dayNumber} · ${f.time}` : `Day ${f.dayNumber}`}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Stays section */}
        {stays.length > 0 && (
          <div data-testid="jd-brief-section-stays">
            {stays.map((s, i) => (
              <div
                key={`stay-${i}`}
                data-testid="jd-brief-stay-row"
                className="jd-brief-row flex items-center gap-2.5 py-2"
              >
                <Hotel
                  className="w-3.5 h-3.5 flex-shrink-0 text-ds-folio-ink-mist"
                  aria-hidden="true"
                />
                <span className="text-sm text-ds-folio-ink flex-1 min-w-0 truncate">
                  {s.title}
                </span>
                <span className="text-xs text-ds-folio-ink-mist flex-shrink-0 ml-auto pl-2">
                  {formatStayRange(s)}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Timed plans section */}
        {(reservationCount > 0 || entryCount > 0) && (
          <div data-testid="jd-brief-section-timed">
            <div
              data-testid="jd-brief-timed-summary"
              className="jd-brief-row flex items-center gap-2.5 py-2"
            >
              <Utensils
                className="w-3.5 h-3.5 flex-shrink-0 text-ds-folio-ink-mist"
                aria-hidden="true"
              />
              <span className="text-sm text-ds-folio-ink">{timedLabel}</span>
            </div>
            {nextTimed && (
              <div
                data-testid="jd-brief-next-timed"
                className="pl-7 text-xs text-ds-folio-ink-mist pb-1"
              >
                {`Next: ${nextTimed.title}${nextTimed.time ? ` · Day ${nextTimed.dayNumber} · ${nextTimed.time}` : ""}`}
              </div>
            )}
          </div>
        )}

        {/* Disclosure toggle — expands full chronological fact list */}
        {allFacts.length > 0 && (
          <>
            <button
              type="button"
              data-testid="jd-brief-view-details"
              onClick={() => setDetailsOpen((o) => !o)}
              aria-expanded={detailsOpen}
              className="inline-flex items-center gap-1 text-xs text-ds-folio-ink-mist hover:text-ds-folio-ink transition-colors duration-[120ms] py-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 rounded"
            >
              {detailsOpen ? "Hide details" : "View all fixed details"}
              {detailsOpen ? (
                <ChevronUp className="w-3.5 h-3.5" aria-hidden="true" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5" aria-hidden="true" />
              )}
            </button>
            {detailsOpen && (
              <div data-testid="jd-brief-details-list" className="mt-1">
                {allFacts.map((fact, i) => (
                  <div
                    key={`detail-${i}`}
                    data-testid="jd-brief-detail-item"
                    className="flex items-center gap-2.5 py-1.5 text-xs text-ds-folio-ink-soft"
                  >
                    <FactIcon type={fact.type} />
                    <span className="flex-1 min-w-0 truncate">
                      <span className="font-medium">{factLabel(fact.type)}</span>
                      <span className="text-ds-folio-ink-mist"> · {fact.title}</span>
                    </span>
                    {(fact.time ?? fact.date) && (
                      <span className="flex-shrink-0 ml-auto pl-2 text-ds-folio-ink-mist">
                        {fact.time
                          ? `Day ${fact.dayNumber} · ${fact.time}`
                          : `Day ${fact.dayNumber}`}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* Pending — essential anchors still to choose (one line each) */}
        {pendingLines.map((line) => (
          <div
            key={line.label}
            data-testid="jd-brief-pending"
            className="jd-brief-row flex items-center justify-between gap-3 py-2"
          >
            <span className="inline-flex items-center gap-2.5 text-sm text-ds-folio-ink">
              <line.Icon
                className="w-3.5 h-3.5 flex-shrink-0 text-ds-folio-ink-mist"
                aria-hidden="true"
              />
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
      </div>
    </section>
  );
}
