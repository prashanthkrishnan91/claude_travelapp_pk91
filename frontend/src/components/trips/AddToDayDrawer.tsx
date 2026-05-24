"use client";

import { useEffect } from "react";
import { Plane, Hotel, UtensilsCrossed, MapPin, X } from "lucide-react";
import type { ItineraryDay } from "@/types";

export type AddToDayVertical = "flight" | "hotel" | "restaurant" | "attraction";

export interface AddToDayDrawerProps {
  open: boolean;
  onClose: () => void;
  day: ItineraryDay | null;
  /** Called when user picks a vertical — routes to the Build panel with day pre-selected. */
  onSelectVertical: (vertical: AddToDayVertical) => void;
}

const VERTICALS: { vertical: AddToDayVertical; label: string; subLabel: string; Icon: typeof Plane; testId: string }[] = [
  { vertical: "flight",     label: "Flight",        subLabel: "Search & add flights",   Icon: Plane,            testId: "add-to-day-flight"     },
  { vertical: "hotel",      label: "Stay",          subLabel: "Find a hotel or stay",   Icon: Hotel,            testId: "add-to-day-hotel"      },
  { vertical: "restaurant", label: "Dining",        subLabel: "Restaurants & cafes",    Icon: UtensilsCrossed,  testId: "add-to-day-dining"     },
  { vertical: "attraction", label: "Things to do",  subLabel: "Attractions & places",   Icon: MapPin,           testId: "add-to-day-attraction" },
];

// ── AddToDayDrawer ─────────────────────────────────────────────────────────────
//
// A focused bottom sheet (mobile) / right drawer (desktop) that lets the user
// pick a vertical to add to a specific day. Selecting a vertical hands off to
// the existing Build panel with the chosen day pre-selected — no new search or
// provider logic is introduced here.

export function AddToDayDrawer({ open, onClose, day, onSelectVertical }: AddToDayDrawerProps) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open || !day) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex justify-end"
      role="dialog"
      aria-modal="true"
      aria-label={`Add to Day ${day.dayNumber}`}
      data-testid="add-to-day-drawer"
    >
      {/* Scrim */}
      <button
        type="button"
        aria-label="Close add-to-day drawer"
        onClick={onClose}
        className="absolute inset-0 bg-black/40"
      />

      {/* Sheet (mobile bottom) / drawer (desktop right) — matches IdeasTray pattern */}
      <section
        className="journey-desk-tray jd-tray-enter absolute inset-x-0 bottom-0 rounded-t-2xl flex flex-col lg:inset-y-0 lg:right-0 lg:left-auto lg:bottom-auto lg:h-full lg:max-h-none lg:w-[380px] lg:rounded-t-none lg:rounded-l-2xl"
        aria-label={`Add something to Day ${day.dayNumber}`}
      >
        {/* Mobile grab handle */}
        <div className="lg:hidden flex justify-center pt-2.5" aria-hidden="true">
          <span className="h-1 w-9 rounded-full bg-ds-hairline" />
        </div>

        {/* Header */}
        <div className="flex items-start justify-between gap-3 px-5 pt-3 pb-4 border-b border-ds-hairline">
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-ds-accent mb-0.5">
              Day {day.dayNumber}
            </p>
            <h2 className="font-serif text-xl font-semibold text-ds-folio-ink leading-tight">
              Add to this day
            </h2>
            <p className="mt-0.5 text-xs italic text-ds-folio-ink-mist">
              Choose what you&apos;d like to plan — the day stays selected.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex-shrink-0 p-1.5 rounded-lg hover:bg-ds-linen text-ds-folio-ink-mist hover:text-ds-folio-ink transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 min-h-[44px] min-w-[44px] flex items-center justify-center mt-0.5"
          >
            <X className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>

        {/* Vertical targets — large, mobile-safe */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          <ul className="flex flex-col gap-2">
            {VERTICALS.map(({ vertical, label, subLabel, Icon, testId }) => (
              <li key={vertical}>
                <button
                  type="button"
                  data-testid={testId}
                  onClick={() => onSelectVertical(vertical)}
                  className="jd-vertical-target w-full flex items-center gap-4 px-4 py-3.5 min-h-[60px] text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2"
                >
                  <span className="flex-shrink-0 flex items-center justify-center w-9 h-9 rounded-xl bg-ds-linen border border-ds-hairline text-ds-folio-ink-soft">
                    <Icon className="w-4 h-4" aria-hidden="true" />
                  </span>
                  <span className="min-w-0">
                    <span className="block font-serif text-base font-semibold text-ds-folio-ink leading-tight">
                      {label}
                    </span>
                    <span className="block text-xs text-ds-folio-ink-mist mt-0.5">
                      {subLabel}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
