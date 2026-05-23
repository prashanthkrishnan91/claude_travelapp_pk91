"use client";

import { Sparkles, Star } from "lucide-react";
import type { ItineraryDay, ItineraryItem } from "@/types";
import { groupJourneyDeskDay } from "@/lib/dayParts";

// ── Honest readers (same detail keys as the Ideas Tray / legacy tab) ──────────

type Details = Record<string, unknown>;
const det = (item: ItineraryItem): Details => (item.details ?? {}) as Details;

function userNoteOf(item: ItineraryItem): string {
  const x = det(item);
  return ((x.userNote ?? x.user_note) as string | undefined)?.trim() ?? "";
}
function reasonOf(item: ItineraryItem): string {
  const x = det(item);
  return ((x.reason as string | undefined) ?? "")?.trim() ?? "";
}
function ratingOf(item: ItineraryItem): string | null {
  const r = det(item).rating as number | null | undefined;
  return typeof r === "number" && r ? r.toFixed(1) : null;
}
function mapsUrlOf(item: ItineraryItem): string | null {
  const x = det(item);
  const u =
    (x.maps_link as string | undefined) ??
    (x.mapsLink as string | undefined) ??
    (x.googleMapsUri as string | undefined) ??
    (x.google_maps_uri as string | undefined) ??
    (x.source_url as string | undefined);
  return typeof u === "string" && /^https?:\/\//.test(u) ? u : null;
}
function bookingUrlOf(item: ItineraryItem): string | null {
  const x = det(item);
  const u =
    (x.booking_url as string | undefined) ??
    (x.bookingUrl as string | undefined) ??
    (x.googleFlightsSearchUrl as string | undefined) ??
    (x.google_flights_search_url as string | undefined);
  return typeof u === "string" && /^https?:\/\//.test(u) ? u : null;
}

// Real clock time only — never invented.
function timeLabelOf(item: ItineraryItem): string | null {
  const raw = item.startTime;
  if (typeof raw !== "string" || !raw.trim()) {
    const tl = det(item).timeLabel;
    return typeof tl === "string" && tl.trim() ? tl.trim() : null;
  }
  const iso = raw.match(/T(\d{2}:\d{2})/);
  if (iso) return iso[1];
  const hhmm = raw.match(/^(\d{1,2}:\d{2})/);
  if (hhmm) return hhmm[1];
  return null;
}

function formatDayDate(dateStr?: string): string {
  if (!dateStr) return "";
  const [y, m, d] = dateStr.split("-").map(Number);
  if (!y || !m || !d) return "";
  const date = new Date(Date.UTC(y, m - 1, d));
  if (isNaN(date.getTime())) return "";
  return date.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", timeZone: "UTC" });
}

// ── Props ─────────────────────────────────────────────────────────────────────

export interface ExpandedDayPanelProps {
  day: ItineraryDay;
  /** Count of unplaced Trip Ideas (trip-level, for the decision strip). */
  ideasCount: number;
  /** Opens the v1B Ideas Tray (day-level placement). */
  onAddFromIdeas: () => void;
  /** Quiet fallback to the legacy Itinerary tab for fuller editing/reordering. */
  onEditInItinerary?: () => void;
}

// ── Component ──────────────────────────────────────────────────────────────────
//
// The expanded day: a calm paper workspace for the selected Dayboard day. Items
// are grouped into Morning / Afternoon / Evening / Logistics (+ honest "Anytime"
// for untimed items) using the durable classifier — no fabricated slots. The
// decision strip summarizes open decisions honestly and opens the Ideas Tray.
// Read-only except for that existing tray placement flow.

export function ExpandedDayPanel({ day, ideasCount, onAddFromIdeas, onEditInItinerary }: ExpandedDayPanelProps) {
  const groups = groupJourneyDeskDay(day.items ?? []);
  const hasItems = (day.items ?? []).length > 0;
  const whereLine = day.title || day.summary || "";
  const dateLabel = formatDayDate(day.date);

  // Honest decision-strip summary. The idea count is TRIP-level (the whole tray),
  // not day-specific — the copy says so plainly rather than implying a day filter.
  const ideaPhrase = `${ideasCount} trip idea${ideasCount === 1 ? "" : "s"} still in the tray`;
  let decision: string;
  if (!hasItems && ideasCount > 0) decision = `Nothing placed in this day yet · ${ideaPhrase}`;
  else if (!hasItems) decision = "Nothing placed in this day yet";
  else if (ideasCount > 0) decision = ideaPhrase;
  else decision = "No open decisions";
  const showAddFromIdeas = ideasCount > 0;

  return (
    <section
      data-testid="journey-desk-expanded-day"
      aria-label={`Day ${day.dayNumber} detail`}
      className="mb-4 sm:mb-6 journey-desk-day"
    >
      {/* Header */}
      <div className="px-5 pt-4 pb-3">
        <div className="flex items-start justify-between gap-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-ds-accent">
            Day {day.dayNumber}
          </p>
          {onEditInItinerary && (
            <button
              type="button"
              data-testid="jd-day-edit-in-itinerary"
              onClick={onEditInItinerary}
              className="flex-shrink-0 text-xs font-medium text-ds-folio-ink-soft hover:text-ds-marine-ink transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 rounded"
            >
              Edit in Itinerary
            </button>
          )}
        </div>
        <h2 className="mt-0.5 font-serif text-xl font-semibold text-ds-folio-ink leading-tight">
          {dateLabel || `Day ${day.dayNumber}`}
        </h2>
        {whereLine && (
          <p className="mt-1 text-sm italic text-ds-folio-ink-mist leading-snug">{whereLine}</p>
        )}
      </div>

      {/* Decision strip — calm brass dot, never an alert */}
      <div data-testid="jd-decision-strip" className="jd-decision-strip mx-5 mb-3 flex items-center gap-3 px-3.5 py-2.5">
        <span className="jd-decide-dot flex-shrink-0" aria-hidden="true" />
        <span className="flex-1 text-sm italic text-ds-folio-ink-soft leading-snug">{decision}</span>
        {showAddFromIdeas && (
          <button
            type="button"
            data-testid="jd-decision-add-from-ideas"
            onClick={onAddFromIdeas}
            className="flex-shrink-0 text-xs font-medium text-ds-folio-ink-soft hover:text-ds-marine-ink transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 rounded"
          >
            Add from Ideas Tray
          </button>
        )}
      </div>

      {/* Grouped placed items — only non-empty sections (silent empties) */}
      <div className="px-5 pb-4 space-y-4">
        {groups.length === 0 ? (
          <p className="text-sm text-ds-folio-ink-mist italic">No plans placed in this day yet.</p>
        ) : (
          groups.map((group) => (
            <div key={group.key} data-testid="jd-day-section" data-section={group.key}>
              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-ds-folio-ink-mist">
                {group.label}
              </p>
              <ul className="flex flex-col gap-2">
                {group.items.map((item) => (
                  <ExpandedDayItemCard key={item.id} item={item} />
                ))}
              </ul>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

// ── Read-only placed-item card ────────────────────────────────────────────────

function ExpandedDayItemCard({ item }: { item: ItineraryItem }) {
  const note = userNoteOf(item);
  const reason = reasonOf(item);
  const rating = ratingOf(item);
  const time = timeLabelOf(item);
  const mapsUrl = mapsUrlOf(item);
  const bookingUrl = bookingUrlOf(item);
  const location = item.location && item.location !== item.title ? item.location : "";

  const LINK =
    "text-xs font-medium text-ds-folio-ink-soft hover:text-ds-marine-ink transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 rounded";

  return (
    <li className="jd-day-item p-3" data-testid="jd-day-item">
      <div className="flex items-baseline gap-2.5">
        {time && (
          <span className="flex-shrink-0 font-serif italic text-sm text-ds-folio-ink-mist tabular-nums">{time}</span>
        )}
        <h4 className="font-serif text-sm font-semibold text-ds-folio-ink leading-snug">{item.title}</h4>
      </div>

      {(rating || location) && (
        <p className="mt-0.5 inline-flex items-center gap-2 text-xs text-ds-folio-ink-mist">
          {rating && (
            <span className="inline-flex items-center gap-0.5">
              <Star className="w-3 h-3 text-ds-accent" aria-hidden="true" />
              {rating}
            </span>
          )}
          {location && <span className="truncate">{location}</span>}
        </p>
      )}

      {/* Note hierarchy — private marginalia, then a distinct concierge reason */}
      {note && (
        <p
          data-testid="jd-day-item-note"
          className="jd-note-private mt-1.5 font-serif italic text-sm text-ds-folio-ink line-clamp-1"
        >
          {note}
        </p>
      )}
      {reason && reason !== note && (
        <p className="mt-1 inline-flex items-center gap-1.5 text-xs text-ds-folio-ink-mist line-clamp-1">
          <Sparkles className="w-3 h-3 flex-shrink-0 text-ds-accent" aria-hidden="true" />
          {reason}
        </p>
      )}

      {/* Contextual secondary links — only where real */}
      {(mapsUrl || (item.itemType === "flight" && bookingUrl)) && (
        <div className="mt-2 flex items-center gap-4">
          {mapsUrl && (
            <a href={mapsUrl} target="_blank" rel="noopener noreferrer" className={LINK}>
              Map
            </a>
          )}
          {item.itemType === "flight" && bookingUrl && (
            <a href={bookingUrl} target="_blank" rel="noopener noreferrer" className={LINK}>
              Google Flights
            </a>
          )}
        </div>
      )}
    </li>
  );
}
