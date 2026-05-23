"use client";

import { useEffect, useMemo, useState } from "react";
import { MapPin, ExternalLink, X } from "lucide-react";
import type { ItineraryDay, ItineraryItem } from "@/types";
import { extractItineraryCoordinates } from "@/lib/itineraryCoordinates";
import { TripLensMap, type TripLensPin } from "@/components/trips/TripLensMap";

// ── Honest map-readiness (v2C) ─────────────────────────────────────────────────
//
// v2B established a strict coordinate contract: `extractItineraryCoordinates`
// reads only real lat/lng already present in a placed item's `details` (Google
// geometry, saved snapshot, explore add) and rejects out-of-range / null-island
// values. v2C plots a pin for every placed item that returns valid coordinates —
// nothing else. Positions are never network-resolved, never index-spread, and
// never inferred from an address, city, destination, or Maps URL.
//
// Items that have no real coordinates but DO carry a real Google Maps URL stay
// in the honest "Map links" list below the map. Items with neither are omitted.

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

const kindOf = (item: ItineraryItem): string => KIND_LABEL[item.itemType] ?? "Item";

interface LinkRow {
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
// Journey Desk Map Fold-Out — Trip Lens only. Mobile bottom sheet ↔ desktop
// right-docked drawer, mirroring the Ideas Tray. v2C plots real pins (validated
// coordinates only) inside the drawer and keeps the honest link list below; no
// fabricated coordinates, routes, or counts. Day/Idea views are deferred (v2D).

export function MapFoldOut({ open, onClose, days }: MapFoldOutProps) {
  const [selectedPinId, setSelectedPinId] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  // Trip lens, in day → position order:
  //   pins     = placed items with VALIDATED real coordinates (these plot)
  //   linkRows = placed items without coordinates but with a real Maps URL
  const { pins, linkRows } = useMemo(() => {
    const pinList: TripLensPin[] = [];
    const links: LinkRow[] = [];
    let order = 0;
    for (const day of days) {
      for (const item of day.items ?? []) {
        const coords = extractItineraryCoordinates(det(item));
        if (coords) {
          order += 1;
          pinList.push({
            id: item.id,
            lat: coords.lat,
            lng: coords.lng,
            title: item.title,
            kind: kindOf(item),
            dayNumber: day.dayNumber,
            time: timeLabelOf(item),
            order,
            // Real link: the item's own Maps URL, else a real ?q=lat,lng link.
            mapsUrl: mapsUrlOf(item) ?? `https://www.google.com/maps?q=${coords.lat},${coords.lng}`,
          });
        } else {
          const mapsUrl = mapsUrlOf(item);
          if (mapsUrl) links.push({ item, dayNumber: day.dayNumber, mapsUrl });
        }
      }
    }
    return { pins: pinList, linkRows: links };
  }, [days]);

  if (!open) return null;

  const hasPins = pins.length > 0;
  const hasLinks = linkRows.length > 0;

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
              {/* Single lens — Trip. Day/Idea views are deferred to v2D. */}
              Trip lens
            </p>
          </div>
          <div className="flex flex-col items-end gap-1 flex-shrink-0 text-right">
            <span data-testid="map-mapped-count" className="text-[11px] text-ds-folio-ink-mist">
              {pins.length} mapped
            </span>
            {hasLinks ? (
              <span data-testid="map-links-count" className="text-[11px] text-ds-folio-ink-mist">
                {linkRows.length} map link{linkRows.length === 1 ? "" : "s"}
              </span>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close trip map"
            className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg text-ds-folio-ink-mist hover:text-ds-folio-ink hover:bg-ds-linen transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 flex-shrink-0"
          >
            <X className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>

        {/* Real pin map — only when validated coordinates exist (capped so the
            list stays reachable on mobile; a panel, never the whole drawer). */}
        {hasPins ? (
          <div className="flex-shrink-0 px-5 pt-3" data-testid="journey-desk-trip-map">
            <TripLensMap pins={pins} selectedId={selectedPinId} onSelect={setSelectedPinId} />
          </div>
        ) : null}

        {/* Honest list: link-only rows (no real coordinates) below the map. */}
        <div className="flex-1 overflow-y-auto px-5 py-3 space-y-2">
          {!hasPins && !hasLinks ? (
            <p className="py-6 text-center text-sm text-ds-folio-ink-mist" data-testid="map-empty-state">
              No real coordinates saved yet. Map links are available for saved places that include
              Google&nbsp;Maps URLs.
            </p>
          ) : null}

          {hasLinks ? (
            <>
              <p className="px-1 pt-1 text-[11px] font-medium uppercase tracking-wide text-ds-folio-ink-mist">
                Map links
              </p>
              {linkRows.map(({ item, dayNumber, mapsUrl }) => {
                const time = timeLabelOf(item);
                const kind = kindOf(item);
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
              })}
            </>
          ) : null}
        </div>

        <p className="px-5 py-2.5 border-t border-ds-hairline text-[11px] italic text-ds-folio-ink-mist">
          {hasPins
            ? "Pins are placed from saved coordinates only. Map links open in Google Maps."
            : "Opens in Google Maps. A plotted map needs saved coordinates."}
        </p>
      </section>
    </div>
  );
}
