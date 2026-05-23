"use client";

import { Plane, Hotel, Check, ArrowRight } from "lucide-react";
import type { Trip, ItineraryDay, ItineraryItem } from "@/types";

// ── Props ────────────────────────────────────────────────────────────────────

export interface TripBriefProps {
  trip: Trip;
  days: ItineraryDay[];
  /** Unassigned Trip Ideas (candidates not yet placed into a day). */
  ideas: ItineraryItem[];
  /** Open the placement surface (Ideas Tray / Ideas workspace on mobile). */
  onReview: () => void;
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

  // Fixed line — the strongest anchor already placed. Shown only when present.
  const fixed = hasFlight
    ? { label: "Flights", value: firstFlight!.title }
    : hasHotel
      ? { label: "Stay", value: firstHotel!.title }
      : null;

  // Pending line — the first missing anchor. One line only; omitted when both set.
  const pending = !hasFlight
    ? { label: "Flights", Icon: Plane }
    : !hasHotel
      ? { label: "Stay", Icon: Hotel }
      : null;

  return (
    <section
      data-testid="journey-desk-brief"
      aria-label="Trip brief"
      className="mb-6 journey-desk-brief"
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

      <div className="px-5 pb-4">
        {/* Fixed — what is already set */}
        {fixed && (
          <div data-testid="jd-brief-fixed" className="jd-brief-row flex items-center gap-2.5 py-2.5">
            <Check className="w-3.5 h-3.5 flex-shrink-0 text-ds-trust" aria-hidden="true" />
            <span className="text-sm text-ds-folio-ink">
              <span className="font-semibold">{fixed.label}</span>
              <span className="text-ds-folio-ink-soft"> · {fixed.value}</span>
            </span>
          </div>
        )}

        {/* Pending — the next anchor still to choose */}
        {pending && (
          <div
            data-testid="jd-brief-pending"
            className="jd-brief-row flex items-center justify-between gap-3 py-2.5"
          >
            <span className="inline-flex items-center gap-2.5 text-sm text-ds-folio-ink">
              <pending.Icon className="w-3.5 h-3.5 flex-shrink-0 text-ds-folio-ink-mist" aria-hidden="true" />
              <span>
                <span className="font-semibold">{pending.label}</span>
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
        )}

        {/* Summary — what still needs deciding (real Trip Ideas count) */}
        <div
          data-testid="jd-brief-decide"
          className="jd-brief-row flex items-center justify-between gap-3 py-2.5"
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
            <span className="text-sm italic text-ds-folio-ink-mist">
              {placedCount > 0 ? "Everything saved is placed" : "Nothing to decide yet"}
            </span>
          )}
        </div>
      </div>
    </section>
  );
}
