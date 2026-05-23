"use client";

import { useEffect, useState } from "react";
import { Hotel, Plane, UtensilsCrossed, MapPin, Sparkles, Star, X, Loader2 } from "lucide-react";
import type { ItineraryDay, ItineraryItem } from "@/types";

// ── Honest readers — every value comes from real Trip Ideas data ──────────────

type Details = Record<string, unknown>;
const d = (item: ItineraryItem): Details => (item.details ?? {}) as Details;

function userNoteOf(item: ItineraryItem): string {
  const x = d(item);
  return ((x.userNote ?? x.user_note) as string | undefined)?.trim() ?? "";
}
function reasonOf(item: ItineraryItem): string {
  const x = d(item);
  return ((x.reason as string | undefined) ?? "")?.trim() ?? "";
}
function mapsUrlOf(item: ItineraryItem): string | null {
  const x = d(item);
  const u =
    (x.maps_link as string | undefined) ??
    (x.mapsLink as string | undefined) ??
    (x.googleMapsUri as string | undefined) ??
    (x.google_maps_uri as string | undefined) ??
    (x.source_url as string | undefined);
  return typeof u === "string" && /^https?:\/\//.test(u) ? u : null;
}
function bookingUrlOf(item: ItineraryItem): string | null {
  const x = d(item);
  const u =
    (x.booking_url as string | undefined) ??
    (x.bookingUrl as string | undefined) ??
    (x.googleFlightsSearchUrl as string | undefined) ??
    (x.google_flights_search_url as string | undefined);
  return typeof u === "string" && /^https?:\/\//.test(u) ? u : null;
}
function ratingOf(item: ItineraryItem): string | null {
  const x = d(item);
  const r = x.rating as number | null | undefined;
  if (!r || typeof r !== "number") return null;
  const rc = x.review_count as number | null | undefined;
  return rc ? `${r.toFixed(1)} (${Number(rc).toLocaleString()})` : r.toFixed(1);
}

const KIND_META: Record<string, { label: string; Icon: typeof Hotel }> = {
  hotel:    { label: "Hotel",  Icon: Hotel },
  flight:   { label: "Flight", Icon: Plane },
  meal:     { label: "Dining", Icon: UtensilsCrossed },
  activity: { label: "Place",  Icon: MapPin },
};

const KIND_CHIPS: { key: string; label: string }[] = [
  { key: "all",      label: "All" },
  { key: "hotel",    label: "Hotels" },
  { key: "flight",   label: "Flights" },
  { key: "meal",     label: "Dining" },
  { key: "activity", label: "Places" },
];

// ── Props ─────────────────────────────────────────────────────────────────────

export interface IdeasTrayProps {
  open: boolean;
  onClose: () => void;
  days: ItineraryDay[];
  /** Unassigned Trip Ideas (candidates). */
  ideas: ItineraryItem[];
  /** Durable day-level placement write. */
  onAssign: (itemId: string, dayId: string) => Promise<void>;
  /** Durable status/note write (updateIdeaMeta). */
  onUpdateMeta: (
    itemId: string,
    currentDetails: Record<string, unknown>,
    patch: { ideaStatus?: string; userNote?: string },
  ) => Promise<void>;
  onRemove: (itemId: string) => Promise<void>;
}

// ── Tray ────────────────────────────────────────────────────────────────────
//
// The Ideas Tray exists to *place* candidates, not to list them. Mobile = bottom
// sheet; desktop = right-docked drawer (the responsive adaptation of the v2
// prototype's right rail — a permanent rail would fight the existing TripBuilder
// columns, so v1B docks a drawer instead). Every action maps to a real durable
// write; placement is day-level only (no fabricated slot like "· Dinner").

export function IdeasTray({ open, onClose, days, ideas, onAssign, onUpdateMeta, onRemove }: IdeasTrayProps) {
  const [filter, setFilter] = useState<string>("all");
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const countFor = (key: string) =>
    key === "all" ? ideas.length : ideas.filter((i) => i.itemType === key).length;
  const visible = filter === "all" ? ideas : ideas.filter((i) => i.itemType === filter);

  async function run(itemId: string, fn: () => Promise<void>) {
    setBusyId(itemId);
    try {
      await fn();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex justify-end"
      role="dialog"
      aria-modal="true"
      aria-label="Ideas tray"
      data-testid="journey-desk-ideas-tray"
    >
      {/* Scrim */}
      <button
        type="button"
        aria-label="Close ideas tray"
        onClick={onClose}
        className="absolute inset-0 bg-black/40"
      />

      {/* Sheet (mobile bottom) / drawer (desktop right) */}
      <section
        className="journey-desk-tray jd-tray-enter absolute inset-x-0 bottom-0 max-h-[88vh] rounded-t-2xl flex flex-col lg:inset-y-0 lg:right-0 lg:left-auto lg:bottom-auto lg:h-full lg:max-h-none lg:w-[400px] lg:rounded-t-none lg:rounded-l-2xl"
        aria-label="Place an idea into the trip"
      >
        {/* Mobile grab handle */}
        <div className="lg:hidden flex justify-center pt-2.5" aria-hidden="true">
          <span className="h-1 w-9 rounded-full bg-ds-hairline" />
        </div>

        {/* Header */}
        <div className="flex items-start justify-between gap-3 px-5 pt-3 pb-3 border-b border-ds-hairline">
          <div className="min-w-0">
            <h2 className="font-serif text-xl font-semibold text-ds-folio-ink leading-tight">Place one in.</h2>
            <p className="mt-0.5 text-xs italic text-ds-folio-ink-mist">
              From your Private Folio.
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span data-testid="ideas-tray-count" className="text-[11px] text-ds-folio-ink-mist">
              {ideas.length} {ideas.length === 1 ? "candidate" : "candidates"}
            </span>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close ideas tray"
              className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg text-ds-folio-ink-mist hover:text-ds-folio-ink hover:bg-ds-linen transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2"
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Filter chips by kind — counts from real data */}
        <div className="flex items-center gap-1.5 overflow-x-auto px-5 py-2.5 border-b border-ds-hairline">
          {KIND_CHIPS.map((chip) => {
            const n = countFor(chip.key);
            if (chip.key !== "all" && n === 0) return null;
            const active = filter === chip.key;
            return (
              <button
                key={chip.key}
                type="button"
                onClick={() => setFilter(chip.key)}
                aria-pressed={active}
                data-testid={`ideas-tray-filter-${chip.key}`}
                className={`flex-shrink-0 rounded-full px-3 py-1.5 text-xs font-medium border transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 ${
                  active
                    ? "border-ds-marine-ink text-ds-marine-ink bg-ds-marine-ink/5"
                    : "border-ds-hairline text-ds-folio-ink-soft hover:text-ds-folio-ink"
                }`}
              >
                {chip.label} <span className="opacity-60">{n}</span>
              </button>
            );
          })}
        </div>

        {/* Candidate list */}
        <div className="flex-1 overflow-y-auto px-5 py-3 space-y-2.5">
          {visible.length === 0 ? (
            <p className="py-6 text-center text-sm text-ds-folio-ink-mist">No candidates in this filter.</p>
          ) : (
            visible.map((item) => (
              <IdeasTrayCard
                key={item.id}
                item={item}
                days={days}
                busy={busyId === item.id}
                onAssign={(dayId) => run(item.id, () => onAssign(item.id, dayId))}
                onKeepMaybe={() => run(item.id, () => onUpdateMeta(item.id, d(item), { ideaStatus: "maybe" }))}
                onRemove={() => run(item.id, () => onRemove(item.id))}
              />
            ))
          )}
        </div>
      </section>
    </div>
  );
}

// ── Card — placement-first, one bold primary action ───────────────────────────

function IdeasTrayCard({
  item,
  days,
  busy,
  onAssign,
  onKeepMaybe,
  onRemove,
}: {
  item: ItineraryItem;
  days: ItineraryDay[];
  busy: boolean;
  onAssign: (dayId: string) => void;
  onKeepMaybe: () => void;
  onRemove: () => void;
}) {
  const [pickDay, setPickDay] = useState(false);
  const kind = KIND_META[item.itemType] ?? { label: "Idea", Icon: Sparkles };
  const KindIcon = kind.Icon;
  const note = userNoteOf(item);
  const reason = reasonOf(item);
  const rating = ratingOf(item);
  const mapsUrl = mapsUrlOf(item);
  const bookingUrl = bookingUrlOf(item);
  const location = item.location && item.location !== item.title ? item.location : "";
  const dayAssignable = days.length > 0;

  const SECONDARY_LINK =
    "text-xs font-medium text-ds-folio-ink-soft hover:text-ds-marine-ink transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 rounded";

  return (
    <article className="jd-tray-card p-3.5" data-testid="ideas-tray-card" data-kind={item.itemType}>
      {/* Kind overline */}
      <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-ds-folio-ink-mist">
        <KindIcon className="w-3 h-3 text-ds-accent" aria-hidden="true" />
        {kind.label}
      </div>

      {/* Title */}
      <h3 className="mt-1 font-serif text-base font-semibold text-ds-folio-ink leading-snug">{item.title}</h3>

      {/* Provider facts — real metadata only */}
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
          data-testid="ideas-tray-note-private"
          className="jd-note-private mt-2 font-serif italic text-sm text-ds-folio-ink line-clamp-1"
        >
          {note}
        </p>
      )}
      {reason && reason !== note && (
        <p
          data-testid="ideas-tray-note-concierge"
          className="mt-1.5 inline-flex items-center gap-1.5 text-xs text-ds-folio-ink-mist line-clamp-1"
        >
          <Sparkles className="w-3 h-3 flex-shrink-0 text-ds-accent" aria-hidden="true" />
          {reason}
        </p>
      )}

      {/* Primary action — placement-first, honest (day-level only) */}
      <div className="mt-3">
        {dayAssignable ? (
          pickDay ? (
            <div data-testid="ideas-tray-day-picker" className="rounded-lg border border-ds-hairline p-2">
              <p className="px-1 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-ds-folio-ink-mist">
                Add to which day
              </p>
              <div className="flex flex-col gap-1">
                {days.map((day) => (
                  <button
                    key={day.id}
                    type="button"
                    disabled={busy}
                    onClick={() => onAssign(day.id)}
                    className="flex items-center justify-between gap-2 min-h-[44px] rounded-md px-2.5 text-left text-sm text-ds-folio-ink ring-1 ring-ds-marine-ink/30 hover:ring-ds-marine-ink hover:text-ds-marine-ink transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 disabled:opacity-50"
                  >
                    <span className="font-medium">Day {day.dayNumber}</span>
                    {day.date && <span className="text-xs text-ds-folio-ink-mist">{day.date}</span>}
                  </button>
                ))}
              </div>
              <button type="button" onClick={() => setPickDay(false)} className={`${SECONDARY_LINK} mt-1.5 px-1`}>
                Cancel
              </button>
            </div>
          ) : (
            <button
              type="button"
              data-testid="ideas-tray-primary-action"
              onClick={() => setPickDay(true)}
              disabled={busy}
              className="w-full inline-flex items-center justify-center gap-1.5 min-h-[44px] rounded-lg text-sm font-medium bg-ds-marine-ink text-ds-paper hover:bg-ds-marine-soft transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 disabled:opacity-50"
            >
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : "Add to Day…"}
            </button>
          )
        ) : (
          <button
            type="button"
            data-testid="ideas-tray-primary-action"
            onClick={onKeepMaybe}
            disabled={busy}
            className="w-full inline-flex items-center justify-center gap-1.5 min-h-[44px] rounded-lg text-sm font-medium bg-ds-marine-ink text-ds-paper hover:bg-ds-marine-soft transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 disabled:opacity-50"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : "Keep as Maybe"}
          </button>
        )}
      </div>

      {/* Secondary actions — quiet text links, contextual to real data */}
      <div className="mt-2.5 flex items-center flex-wrap gap-x-4 gap-y-1">
        {mapsUrl && (
          <a href={mapsUrl} target="_blank" rel="noopener noreferrer" className={SECONDARY_LINK}>
            Map
          </a>
        )}
        {item.itemType === "flight" && bookingUrl && (
          <a href={bookingUrl} target="_blank" rel="noopener noreferrer" className={SECONDARY_LINK}>
            Google Flights
          </a>
        )}
        {dayAssignable && (
          <button type="button" onClick={onKeepMaybe} disabled={busy} className={SECONDARY_LINK}>
            Keep as Maybe
          </button>
        )}
        <button type="button" onClick={onRemove} disabled={busy} className={`${SECONDARY_LINK} ml-auto`}>
          Remove
        </button>
      </div>
    </article>
  );
}
