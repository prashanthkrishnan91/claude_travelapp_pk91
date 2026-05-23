"use client";

import { useEffect } from "react";
import { MapPin, ExternalLink, X } from "lucide-react";
import type { ItineraryDay, ItineraryItem } from "@/types";
import { extractItineraryCoordinates } from "@/lib/itineraryCoordinates";

// ── Honest map-readiness ──────────────────────────────────────────────────────
//
// v2A audit: placed itinerary items reliably carry Google Maps URLs / addresses,
// but NOT coordinates (only some hotels persist real lat/lng). There is no
// durable per-item coordinate contract, so we do NOT plot a pin map (that would
// fabricate positions). Instead we list the items that have a *real* map link —
// the item's own Maps URL, or a real `?q=lat,lng` link built from real coords.
// Items with neither are omitted (no placeholders, no fake pins/routes).

type Details = Record<string, unknown>;
const det = (item: ItineraryItem): Details => (item.details ?? {}) as Details;

function mapsUrlOf(item: ItineraryItem): string | null {
  const x = det(item);
  const link =
    (x.maps_link as string | undefined) ??
    (x.mapsLink as string | undefined) ??
    (x.googleMapsUri as string | undefined) ??
    (x.google_maps_uri as string | undefined) ??
    (x.source_url as string | undefined);
  if (typeof link === "string" && /^https?:\/\//.test(link)) return link;
  // Validate persisted coordinates on read (single gate for every write path):
  // rejects out-of-range / null-island values before building a real q-link.
  const coords = extractItineraryCoordinates(x);
  if (coords) return `https://www.google.com/maps?q=${coords.lat},${coords.lng}`;
  return null;
}

function timeLabelOf(item: ItineraryItem): string | null {
  const raw = item.startTime;
  if (typeof raw === "string" && raw.trim()) {
    const iso = raw.match(/T(\d{2}:\d{2})/);
    if (iso) return iso[1];
    const hhmm = raw.match(/^(\d{1,2}:\d{2})/);
    if (hhmm) return hhmm[1];
  }
  const tl = det(item).timeLabel;
  return typeof tl === "string" && tl.trim() ? tl.trim() : null;
}

const KIND_LABEL: Record<string, string> = {
  hotel: "Hotel",
  flight: "Flight",
  meal: "Dining",
  activity: "Place",
  transit: "Transit",
  note: "Note",
};

interface MapReadyRow {
  item: ItineraryItem;
  dayNumber: number;
  mapsUrl: string;
}

// ── Props ─────────────────────────────────────────────────────────────────────

export interface MapFoldOutProps {
  open: boolean;
  onClose: () => void;
  days: ItineraryDay[];
}

// ── Component ──────────────────────────────────────────────────────────────────
//
// Journey Desk Map Fold-Out — Trip Lens only (v2A). Mobile bottom sheet ↔ desktop
// right-docked drawer, mirroring the Ideas Tray. Honest map-ready list; no pins,
// no fabricated coordinates/routes/distances/counts. Day/Idea lenses are deferred.

export function MapFoldOut({ open, onClose, days }: MapFoldOutProps) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  // Trip lens: every placed item that has a real map affordance, in day → position order.
  const rows: MapReadyRow[] = [];
  for (const day of days) {
    for (const item of day.items ?? []) {
      const mapsUrl = mapsUrlOf(item);
      if (mapsUrl) rows.push({ item, dayNumber: day.dayNumber, mapsUrl });
    }
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex justify-end"
      role="dialog"
      aria-modal="true"
      aria-label="Trip map"
      data-testid="journey-desk-map"
    >
      <button type="button" aria-label="Close trip map" onClick={onClose} className="absolute inset-0 bg-black/40" />

      <section
        className="journey-desk-tray jd-tray-enter absolute inset-x-0 bottom-0 max-h-[88vh] rounded-t-2xl flex flex-col lg:inset-y-0 lg:right-0 lg:left-auto lg:bottom-auto lg:h-full lg:max-h-none lg:w-[400px] lg:rounded-t-none lg:rounded-l-2xl"
        aria-label="Where the trip lives"
      >
        <div className="lg:hidden flex justify-center pt-2.5" aria-hidden="true">
          <span className="h-1 w-9 rounded-full bg-ds-hairline" />
        </div>

        {/* Header */}
        <div className="flex items-start justify-between gap-3 px-5 pt-3 pb-3 border-b border-ds-hairline">
          <div className="min-w-0">
            <h2 className="font-serif text-xl font-semibold text-ds-folio-ink leading-tight">Where the trip lives</h2>
            <p className="mt-0.5 inline-flex items-center gap-1.5 text-xs text-ds-folio-ink-mist">
              <MapPin className="w-3 h-3 text-ds-accent" aria-hidden="true" />
              {/* Single lens in v2A — Trip. Day/Idea lenses are deferred to v2B. */}
              Trip lens
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span data-testid="map-ready-count" className="text-[11px] text-ds-folio-ink-mist">
              {rows.length} map-ready place{rows.length === 1 ? "" : "s"}
            </span>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close trip map"
              className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg text-ds-folio-ink-mist hover:text-ds-folio-ink hover:bg-ds-linen transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2"
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Honest map-ready list — no plotted pins (no per-item coordinate contract) */}
        <div className="flex-1 overflow-y-auto px-5 py-3 space-y-2">
          {rows.length === 0 ? (
            <p className="py-6 text-center text-sm text-ds-folio-ink-mist">
              No map-ready places yet. Placed items with a Google&nbsp;Maps link will appear here.
            </p>
          ) : (
            rows.map(({ item, dayNumber, mapsUrl }) => {
              const time = timeLabelOf(item);
              const kind = KIND_LABEL[item.itemType] ?? "Item";
              return (
                <a
                  key={item.id}
                  href={mapsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="map-ready-row"
                  className="jd-day-item flex items-center gap-3 p-3 hover:border-ds-marine-ink/40 transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2"
                >
                  <span className="flex-shrink-0 inline-flex items-center justify-center w-7 h-7 rounded-full bg-ds-linen text-[10px] font-semibold text-ds-folio-ink-mist" aria-hidden="true">
                    {dayNumber}
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className="block font-serif text-sm font-semibold text-ds-folio-ink leading-snug truncate">
                      {item.title}
                    </span>
                    <span className="block text-[11px] text-ds-folio-ink-mist">
                      Day {dayNumber}
                      {time ? ` · ${time}` : ""} · {kind}
                    </span>
                  </span>
                  <ExternalLink className="w-3.5 h-3.5 flex-shrink-0 text-ds-folio-ink-mist" aria-hidden="true" />
                </a>
              );
            })
          )}
        </div>

        <p className="px-5 py-2.5 border-t border-ds-hairline text-[11px] italic text-ds-folio-ink-mist">
          Opens in Google Maps. A plotted map needs saved coordinates — coming later.
        </p>
      </section>
    </div>
  );
}
