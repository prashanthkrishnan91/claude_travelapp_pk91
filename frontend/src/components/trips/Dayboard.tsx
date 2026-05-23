"use client";

import type { ItineraryDay } from "@/types";

// ── Props ────────────────────────────────────────────────────────────────────

export interface DayboardProps {
  days: ItineraryDay[];
  /** Open the day in the itinerary workspace. */
  onSelectDay: (day: ItineraryDay) => void;
}

// Timezone-safe display ("Thu, Nov 12") — mirrors ItineraryDayColumn.formatDate
// so a date never shifts a day under the user's local zone.
function formatDayDate(dateStr?: string): string {
  if (!dateStr) return "";
  const [year, month, day] = dateStr.split("-").map(Number);
  if (!year || !month || !day) return "";
  const d = new Date(Date.UTC(year, month - 1, day));
  if (isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

// ── Component ──────────────────────────────────────────────────────────────────
//
// The collapsed Dayboard: one calm card per day giving the 10-second read —
// day numeral, date, a real where-line when present, and what is placed vs.
// still being decided. Tapping a day opens it in the itinerary workspace.
// No weather, no fabricated counts (blueprint §5 / §8).

export function Dayboard({ days, onSelectDay }: DayboardProps) {
  if (days.length === 0) return null;

  const activeDays = days.filter((d) => (d.items ?? []).length > 0).length;

  return (
    <section data-testid="journey-desk-dayboard" aria-label="Dayboard" className="mb-6">
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-ds-accent">
          Dayboard
        </p>
        <span className="text-xs text-ds-folio-ink-mist">
          {activeDays === days.length
            ? "All days planned"
            : `${activeDays} of ${days.length} days planned`}
        </span>
      </div>

      <ul className="flex flex-col gap-2">
        {days.map((day) => {
          const itemCount = (day.items ?? []).length;
          const stillDeciding = itemCount === 0;
          const whereLine = day.title || day.summary || "";
          const dateLabel = formatDayDate(day.date);
          return (
            <li key={day.id}>
              <button
                type="button"
                data-testid="journey-desk-day-card"
                onClick={() => onSelectDay(day)}
                aria-label={`Day ${day.dayNumber}${dateLabel ? `, ${dateLabel}` : ""}: ${
                  stillDeciding ? "still deciding" : `${itemCount} placed`
                }`}
                className="jd-day-card w-full flex items-center gap-3.5 px-3.5 py-2.5 min-h-[52px] text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2"
              >
                {/* Day numeral — the editorial anchor */}
                <span
                  aria-hidden="true"
                  className="flex-shrink-0 font-serif italic text-2xl sm:text-3xl leading-none text-ds-folio-ink/90 w-8 sm:w-9 text-center"
                >
                  {day.dayNumber}
                </span>

                <span className="flex-1 min-w-0">
                  {dateLabel && (
                    <span className="block text-sm font-semibold text-ds-folio-ink leading-tight">
                      {dateLabel}
                    </span>
                  )}
                  {whereLine && (
                    <span className="block mt-0.5 text-xs italic text-ds-folio-ink-mist truncate">
                      {whereLine}
                    </span>
                  )}
                </span>

                {/* Placement read — calm brass dot when still deciding */}
                <span className="flex-shrink-0 inline-flex items-center gap-2 text-xs text-ds-folio-ink-mist">
                  {stillDeciding ? (
                    <>
                      <span className="jd-decide-dot" aria-hidden="true" />
                      <span className="italic">Still deciding</span>
                    </>
                  ) : (
                    <span>{itemCount} placed</span>
                  )}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
