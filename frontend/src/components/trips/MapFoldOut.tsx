"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { MapPin, Map as MapIcon, CalendarDays, MoreHorizontal, ExternalLink, X, Sparkles, Star, Loader2 } from "lucide-react";
import type { ItineraryDay, ItineraryItem } from "@/types";
import { extractItineraryCoordinates } from "@/lib/itineraryCoordinates";
import { TripLensMap, type TripLensPin } from "@/components/trips/TripLensMap";

// ── Honest map-readiness (v2C) + Visual Itinerary Map v1A/v1B ──────────────────
//
// v2B established a strict coordinate contract: `extractItineraryCoordinates`
// reads only real lat/lng already present in an item's `details` (Google
// geometry, saved snapshot, explore add) and rejects out-of-range / null-island
// values. Every pin on every lens is built from that normalizer — nothing else.
// Positions are never network-resolved, never index-spread, and never inferred
// from an address, city, destination, or Maps URL.
//
//   Trip Lens  — all placed map-ready items.
//   Day Lens   — the selected day's placed map-ready items only.
//   Ideas Lens — unplaced Trip Ideas with real coordinates (distinct markers).
//
// v1B adds safe planned-item actions backed ONLY by durable existing writes,
// behind a premium hybrid row (Map + Move chips · More kebab overflow):
//   Move            → onAssign (PATCH day_id; details preserved)
//   Back to Ideas   → onUnplace (PATCH day_id:null → back to Trip Ideas; preserved)
//   Remove from trip → onRemove (DELETE; two-step confirm guard)
// Destructive deletes (trip + idea) are protected by an inline confirm. There is
// no durable pin-visibility preference contract, so no such toggle UI is rendered
// (deferred to v1C until a real preference/status field exists).

type Details = Record<string, unknown>;
const det = (item: ItineraryItem): Details => (item.details ?? {}) as Details;

type Lens = "trip" | "day" | "ideas";

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

function userNoteOf(item: ItineraryItem): string {
  const x = det(item);
  return ((x.userNote ?? x.user_note) as string | undefined)?.trim() ?? "";
}
function reasonOf(item: ItineraryItem): string {
  return ((det(item).reason as string | undefined) ?? "")?.trim() ?? "";
}
function ratingOf(item: ItineraryItem): string | null {
  const r = det(item).rating as number | null | undefined;
  if (!r || typeof r !== "number") return null;
  const rc = det(item).review_count as number | null | undefined;
  return rc ? `${r.toFixed(1)} (${Number(rc).toLocaleString()})` : r.toFixed(1);
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
interface PlacedCard {
  item: ItineraryItem;
  dayNumber: number;
  mapsUrl: string;
}

// Build placed pins + planned cards + link rows for a set of days (Trip = all,
// Day = one). Pins and cards share the same validated-coordinate gate.
function buildPlaced(days: ItineraryDay[]): {
  pins: TripLensPin[];
  cards: PlacedCard[];
  linkRows: LinkRow[];
} {
  const pins: TripLensPin[] = [];
  const cards: PlacedCard[] = [];
  const linkRows: LinkRow[] = [];
  let order = 0;
  for (const day of days) {
    for (const item of day.items ?? []) {
      const coords = extractItineraryCoordinates(det(item));
      if (coords) {
        order += 1;
        const mapsUrl = mapsUrlOf(item) ?? `https://www.google.com/maps?q=${coords.lat},${coords.lng}`;
        pins.push({
          id: item.id,
          lat: coords.lat,
          lng: coords.lng,
          title: item.title,
          kind: kindOf(item),
          dayNumber: day.dayNumber,
          time: timeLabelOf(item),
          order,
          variant: "planned",
          mapsUrl,
        });
        cards.push({ item, dayNumber: day.dayNumber, mapsUrl });
      } else {
        const mapsUrl = mapsUrlOf(item);
        if (mapsUrl) linkRows.push({ item, dayNumber: day.dayNumber, mapsUrl });
      }
    }
  }
  return { pins, cards, linkRows };
}

// ── Props ─────────────────────────────────────────────────────────────────────

export interface MapFoldOutProps {
  open: boolean;
  onClose: () => void;
  days: ItineraryDay[];
  /** Unplaced Trip Ideas (candidates) — same source the Ideas Tray reads. */
  ideas: ItineraryItem[];
  /** Currently selected Dayboard day (drives the Day Lens default). */
  selectedDayId?: string | null;
  /** Sync the selected day back to the page (keeps Dayboard/Expanded Day coherent). */
  onSelectDay?: (dayId: string) => void;
  /** Durable day-level assignment (assignIdeaToDay) — also powers Move to Day. */
  onAssign: (itemId: string, dayId: string) => Promise<void>;
  /** Durable status write (updateIdeaMeta) — used for "Keep as Maybe". */
  onUpdateMeta: (
    itemId: string,
    currentDetails: Record<string, unknown>,
    patch: { ideaStatus?: string; userNote?: string },
  ) => Promise<void>;
  /** Durable delete (deleteItem) — used for "Remove from trip" / "Remove idea". */
  onRemove: (itemId: string) => Promise<void>;
  /** Durable unplace (moveIdeaToTripIdeas → day_id:null) — "Back to Ideas". */
  onUnplace: (itemId: string) => Promise<void>;
  /** Open the legacy Ideas workspace for fuller management. */
  onManage: () => void;
  /** Open the legacy Itinerary workspace (for flight/hotel/logistics anchors). */
  onManageItinerary: () => void;
}

// ── Component ──────────────────────────────────────────────────────────────────

export function MapFoldOut({
  open,
  onClose,
  days,
  ideas,
  selectedDayId,
  onSelectDay,
  onAssign,
  onUpdateMeta,
  onRemove,
  onUnplace,
  onManage,
  onManageItinerary,
}: MapFoldOutProps) {
  const [lens, setLens] = useState<Lens>("trip");
  const [selectedPinId, setSelectedPinId] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  // The Day Lens shows one day: the page's selected day, else the first trip day.
  const dayLensDay = useMemo(
    () => days.find((d) => d.id === selectedDayId) ?? days[0] ?? null,
    [days, selectedDayId],
  );

  const trip = useMemo(() => buildPlaced(days), [days]);
  const day = useMemo(() => buildPlaced(dayLensDay ? [dayLensDay] : []), [dayLensDay]);

  // Ideas Lens: unplaced ideas with validated coordinates plot as distinct idea
  // pins; coordinate-less ideas with a real Maps URL fall to a needs-location
  // link list; ideas with neither are omitted (they remain in the Ideas Tray).
  const { ideaPins, ideaLinkItems } = useMemo(() => {
    const pins: TripLensPin[] = [];
    const linkItems: ItineraryItem[] = [];
    for (const item of ideas) {
      const coords = extractItineraryCoordinates(det(item));
      if (coords) {
        pins.push({
          id: item.id,
          lat: coords.lat,
          lng: coords.lng,
          title: item.title,
          kind: kindOf(item),
          dayNumber: 0,
          time: null,
          order: 0,
          variant: "idea",
          note: userNoteOf(item) || null,
          mapsUrl: mapsUrlOf(item) ?? `https://www.google.com/maps?q=${coords.lat},${coords.lng}`,
        });
      } else if (mapsUrlOf(item)) {
        linkItems.push(item);
      }
    }
    return { ideaPins: pins, ideaLinkItems: linkItems };
  }, [ideas]);

  // After a successful assignment, follow the idea into its day so the user sees
  // it land: select that day and switch to the Day Lens.
  async function assignFromIdeas(itemId: string, dayId: string) {
    await onAssign(itemId, dayId);
    onSelectDay?.(dayId);
    setSelectedPinId(null);
    setLens("day");
  }

  if (!open) return null;

  const activePins = lens === "trip" ? trip.pins : lens === "day" ? day.pins : ideaPins;
  const activeCards = lens === "trip" ? trip.cards : lens === "day" ? day.cards : [];
  const activeLinks = lens === "trip" ? trip.linkRows : lens === "day" ? day.linkRows : [];
  const hasPins = activePins.length > 0;

  const LENS_TABS: { key: Lens; label: string; count: number }[] = [
    { key: "trip", label: "Trip", count: trip.pins.length },
    { key: "day", label: "Day", count: day.pins.length },
    { key: "ideas", label: "Ideas", count: ideaPins.length },
  ];

  const lensCaption = lens === "trip" ? "Trip lens" : lens === "day" ? "Day lens" : "Ideas lens";

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
              {lensCaption}
            </p>
          </div>
          <div className="flex flex-col items-end gap-1 flex-shrink-0 text-right">
            <span data-testid="map-mapped-count" className="text-[11px] text-ds-folio-ink-mist">
              {activePins.length} mapped
            </span>
            {activeLinks.length > 0 ? (
              <span data-testid="map-links-count" className="text-[11px] text-ds-folio-ink-mist">
                {activeLinks.length} map link{activeLinks.length === 1 ? "" : "s"}
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

        {/* Lens switcher — Trip / Day / Ideas, honest counts */}
        <div className="jd-lens-switch px-5 py-2.5 border-b border-ds-hairline" role="tablist" aria-label="Map lens">
          {LENS_TABS.map((tab) => {
            const active = lens === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                role="tab"
                aria-selected={active}
                data-testid={`map-lens-${tab.key}`}
                onClick={() => {
                  setLens(tab.key);
                  setSelectedPinId(null);
                }}
                className={`jd-lens-tab ${active ? "jd-lens-tab--active" : ""}`}
              >
                {tab.label}
                <span className="jd-lens-tab-count">{tab.count}</span>
              </button>
            );
          })}
        </div>

        {/* Day chips — only on the Day Lens, only when there are real days */}
        {lens === "day" && days.length > 0 ? (
          <div className="flex items-center gap-1.5 overflow-x-auto px-5 py-2.5 border-b border-ds-hairline" data-testid="map-day-chips">
            {days.map((d) => {
              const active = dayLensDay?.id === d.id;
              return (
                <button
                  key={d.id}
                  type="button"
                  onClick={() => {
                    onSelectDay?.(d.id);
                    setSelectedPinId(null);
                  }}
                  aria-pressed={active}
                  data-testid={`map-day-chip-${d.dayNumber}`}
                  className={`flex-shrink-0 rounded-full px-3 py-1.5 text-xs font-medium border transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 ${
                    active
                      ? "border-ds-marine-ink text-ds-marine-ink bg-ds-marine-ink/5"
                      : "border-ds-hairline text-ds-folio-ink-soft hover:text-ds-folio-ink"
                  }`}
                >
                  Day {d.dayNumber}
                </button>
              );
            })}
          </div>
        ) : null}

        {/* Real pin map — only when validated coordinates exist for this lens. */}
        {hasPins ? (
          <div className="flex-shrink-0 px-5 pt-3" data-testid="journey-desk-trip-map">
            <div className="jd-atlas-frame">
              <span className="jd-atlas-caption" aria-hidden="true">
                <MapPin className="w-3 h-3" />
                {lensCaption}
              </span>
              <TripLensMap pins={activePins} selectedId={selectedPinId} onSelect={setSelectedPinId} />
            </div>
          </div>
        ) : null}

        {/* Body — per-lens list below the map */}
        <div className="flex-1 overflow-y-auto px-5 py-3 space-y-2">
          {lens === "ideas" ? (
            <IdeasLensBody
              ideas={ideas}
              ideaPinIds={ideaPins.map((p) => p.id)}
              ideaLinkItems={ideaLinkItems}
              days={days}
              selectedPinId={selectedPinId}
              onSelect={setSelectedPinId}
              onAssign={assignFromIdeas}
              onKeepMaybe={(item) => onUpdateMeta(item.id, det(item), { ideaStatus: "maybe" })}
              onRemove={onRemove}
              onManage={onManage}
            />
          ) : (
            <PlannedLensBody
              hasPins={hasPins}
              cards={activeCards}
              linkRows={activeLinks}
              isDay={lens === "day"}
              days={days}
              ideasExist={ideas.length > 0}
              selectedPinId={selectedPinId}
              onSelect={setSelectedPinId}
              onMoveToDay={onAssign}
              onUnplace={onUnplace}
              onRemove={onRemove}
              onManageItinerary={onManageItinerary}
              onAddFromIdeas={() => {
                setLens("ideas");
                setSelectedPinId(null);
              }}
            />
          )}
        </div>

        <p className="px-5 py-2.5 border-t border-ds-hairline text-[11px] italic text-ds-folio-ink-mist">
          {lens === "ideas"
            ? "Idea pins are unplaced saved places with real coordinates. Add to Day places them in your plan."
            : hasPins
              ? "Pins are placed from saved coordinates only. Map links open in Google Maps."
              : "Opens in Google Maps. A plotted map needs saved coordinates."}
        </p>
      </section>
    </div>
  );
}

// ── Planned lens body (Trip / Day) — planned cards + honest link rows ──────────

function PlannedLensBody({
  hasPins,
  cards,
  linkRows,
  isDay,
  days,
  ideasExist,
  selectedPinId,
  onSelect,
  onMoveToDay,
  onUnplace,
  onRemove,
  onManageItinerary,
  onAddFromIdeas,
}: {
  hasPins: boolean;
  cards: PlacedCard[];
  linkRows: LinkRow[];
  isDay: boolean;
  days: ItineraryDay[];
  ideasExist: boolean;
  selectedPinId: string | null;
  onSelect: (id: string) => void;
  onMoveToDay: (itemId: string, dayId: string) => Promise<void>;
  onUnplace: (itemId: string) => Promise<void>;
  onRemove: (itemId: string) => Promise<void>;
  onManageItinerary: () => void;
  onAddFromIdeas: () => void;
}) {
  const hasLinks = linkRows.length > 0;
  const hasCards = cards.length > 0;
  return (
    <>
      {!hasPins && !hasLinks ? (
        <div className="py-6 text-center" data-testid="map-empty-state">
          <p className="text-sm text-ds-folio-ink-mist">
            {isDay
              ? "No map-ready places planned for this day yet."
              : "No real coordinates saved yet. Map links are available for saved places that include Google Maps URLs."}
          </p>
          {isDay && ideasExist ? (
            <button
              type="button"
              data-testid="map-add-from-ideas"
              onClick={onAddFromIdeas}
              className="mt-3 inline-flex items-center justify-center gap-1.5 min-h-[44px] rounded-lg px-4 text-sm font-medium bg-ds-marine-ink text-ds-paper hover:bg-ds-marine-soft transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2"
            >
              Add from Ideas
            </button>
          ) : null}
        </div>
      ) : null}

      {hasCards ? (
        <>
          <p className="px-1 pt-1 text-[11px] font-medium uppercase tracking-wide text-ds-folio-ink-mist">
            On the map
          </p>
          {cards.map((card) => (
            <PlannedItemCard
              key={card.item.id}
              card={card}
              days={days}
              selected={selectedPinId === card.item.id}
              onSelect={onSelect}
              onMoveToDay={onMoveToDay}
              onUnplace={onUnplace}
              onRemove={onRemove}
              onManageItinerary={onManageItinerary}
            />
          ))}
        </>
      ) : null}

      {hasLinks ? (
        <>
          <p className="px-1 pt-3 text-[11px] font-medium uppercase tracking-wide text-ds-folio-ink-mist">Map links</p>
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
    </>
  );
}

// ── Planned item card — useful real fields + safe durable actions ──────────────

function PlannedItemCard({
  card,
  days,
  selected,
  onSelect,
  onMoveToDay,
  onUnplace,
  onRemove,
  onManageItinerary,
}: {
  card: PlacedCard;
  days: ItineraryDay[];
  selected: boolean;
  onSelect: (id: string) => void;
  onMoveToDay: (itemId: string, dayId: string) => Promise<void>;
  onUnplace: (itemId: string) => Promise<void>;
  onRemove: (itemId: string) => Promise<void>;
  onManageItinerary: () => void;
}) {
  const { item, dayNumber, mapsUrl } = card;
  const ref = useRef<HTMLElement>(null);
  const [busy, setBusy] = useState(false);
  const [pickDay, setPickDay] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);
  // Restaurants/places carry a meaningful "Back to Ideas" (durable unplace);
  // flight/hotel/logistics anchors instead point to the fuller Itinerary editor.
  const isAnchor = item.itemType !== "meal" && item.itemType !== "activity";

  // Lightweight selection sync: when this card becomes the selected pin, bring it
  // into view (no heavy animation — instant nearest scroll).
  useEffect(() => {
    if (selected && ref.current) ref.current.scrollIntoView({ block: "nearest" });
  }, [selected]);

  const note = userNoteOf(item);
  const reason = reasonOf(item);
  const rating = ratingOf(item);
  const time = timeLabelOf(item);
  const location = item.location && item.location !== item.title ? item.location : "";
  // Day-level move only when there is somewhere else to move to.
  const otherDays = days.filter((d) => d.id !== item.dayId);
  const canMove = otherDays.length > 0;

  const LINK =
    "text-xs font-medium text-ds-folio-ink-soft hover:text-ds-marine-ink transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 rounded";
  // Premium labeled chip (icon + short label) — thumb-friendly tap target.
  const ACTION_CHIP =
    "inline-flex items-center gap-1.5 min-h-[40px] px-2.5 rounded-md text-xs font-medium text-ds-folio-ink-soft hover:text-ds-marine-ink hover:bg-ds-linen transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2";
  // Overflow-menu row — explicit text labels (never icon-only for consequence).
  const MENU_ITEM =
    "w-full flex items-center min-h-[40px] px-2.5 rounded-md text-left text-sm font-medium text-ds-folio-ink hover:bg-ds-linen transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 disabled:opacity-50";

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  }

  return (
    <article
      ref={ref}
      data-testid="map-planned-card"
      data-kind={item.itemType}
      onClick={() => onSelect(item.id)}
      className={`jd-tray-card p-3.5 cursor-pointer ${selected ? "ring-2 ring-ds-marine-ink/50" : ""}`}
    >
      <div className="flex items-baseline gap-2.5">
        {time && (
          <span className="flex-shrink-0 font-serif italic text-sm text-ds-folio-ink-mist tabular-nums">{time}</span>
        )}
        <h3 className="font-serif text-base font-semibold text-ds-folio-ink leading-snug">{item.title}</h3>
      </div>
      <p className="mt-0.5 text-[11px] text-ds-folio-ink-mist">
        Day {dayNumber} · {kindOf(item)}
      </p>

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

      {note && (
        <p
          data-testid="map-planned-note-private"
          className="jd-note-private mt-2 font-serif italic text-sm text-ds-folio-ink line-clamp-1"
        >
          {note}
        </p>
      )}
      {reason && reason !== note && (
        <p className="mt-1.5 inline-flex items-center gap-1.5 text-xs text-ds-folio-ink-mist line-clamp-1">
          <Sparkles className="w-3 h-3 flex-shrink-0 text-ds-accent" aria-hidden="true" />
          {reason}
        </p>
      )}

      {/* Move to Day… — durable day-level move (assignIdeaToDay), no slot label */}
      {pickDay ? (
        <div
          data-testid="map-planned-day-picker"
          className="mt-3 rounded-lg border border-ds-hairline p-2"
          onClick={(e) => e.stopPropagation()}
        >
          <p className="px-1 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-ds-folio-ink-mist">
            Move to which day
          </p>
          <div className="flex flex-col gap-1">
            {otherDays.map((d) => (
              <button
                key={d.id}
                type="button"
                disabled={busy}
                onClick={() => run(() => onMoveToDay(item.id, d.id)).then(() => setPickDay(false))}
                className="flex items-center justify-between gap-2 min-h-[44px] rounded-md px-2.5 text-left text-sm text-ds-folio-ink ring-1 ring-ds-marine-ink/30 hover:ring-ds-marine-ink hover:text-ds-marine-ink transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 disabled:opacity-50"
              >
                <span className="font-medium">Day {d.dayNumber}</span>
                {d.date && <span className="text-xs text-ds-folio-ink-mist">{d.date}</span>}
              </button>
            ))}
          </div>
          <button type="button" onClick={() => setPickDay(false)} className={`${LINK} mt-1.5 px-1`}>
            Cancel
          </button>
        </div>
      ) : null}

      {/* Premium hybrid action row: Map + Move (icon + short label) · More (kebab) */}
      <div className="mt-2.5 flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
        {mapsUrl && (
          <a href={mapsUrl} target="_blank" rel="noopener noreferrer" className={ACTION_CHIP}>
            <MapIcon className="w-3.5 h-3.5" aria-hidden="true" />
            Map
          </a>
        )}
        {canMove && !pickDay && (
          <button type="button" data-testid="map-planned-move" onClick={() => setPickDay(true)} disabled={busy} className={ACTION_CHIP}>
            <CalendarDays className="w-3.5 h-3.5" aria-hidden="true" />
            Move
          </button>
        )}

        <div className="relative ml-auto">
          <button
            type="button"
            data-testid="map-planned-more"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            aria-label="More actions"
            onClick={() => {
              setMenuOpen((v) => !v);
              setConfirmRemove(false);
            }}
            disabled={busy}
            className="inline-flex items-center justify-center min-h-[40px] min-w-[40px] rounded-md text-ds-folio-ink-soft hover:text-ds-folio-ink hover:bg-ds-linen transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 disabled:opacity-50"
          >
            <MoreHorizontal className="w-4 h-4" aria-hidden="true" />
          </button>

          {menuOpen ? (
            <>
              {/* Lightweight tap-away to close (no portal/animation). */}
              <button
                type="button"
                aria-hidden="true"
                tabIndex={-1}
                onClick={() => setMenuOpen(false)}
                className="fixed inset-0 z-10 cursor-default"
              />
              <div
                role="menu"
                data-testid="map-planned-more-menu"
                className="absolute right-0 top-full z-20 mt-1 min-w-[190px] rounded-lg border border-ds-hairline bg-ds-paper p-1 shadow-[var(--ds-paper-elevation-2)]"
              >
                {confirmRemove ? (
                  <div className="p-2" data-testid="map-planned-remove-confirm">
                    <p className="px-1 pb-2 text-xs text-ds-folio-ink-soft leading-snug">
                      Remove this from the trip permanently?
                    </p>
                    <button
                      type="button"
                      onClick={() => run(() => onRemove(item.id))}
                      disabled={busy}
                      className="w-full inline-flex items-center justify-center gap-1.5 min-h-[40px] rounded-md text-sm font-semibold text-ds-warning ring-1 ring-ds-warning/40 hover:bg-ds-warning/10 transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-warning focus-visible:outline-offset-2 disabled:opacity-50"
                    >
                      {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Confirm remove from trip"}
                    </button>
                    <button type="button" onClick={() => setConfirmRemove(false)} disabled={busy} className={`${MENU_ITEM} mt-1 justify-center`}>
                      Cancel
                    </button>
                  </div>
                ) : (
                  <>
                    {isAnchor ? (
                      <button
                        type="button"
                        role="menuitem"
                        data-testid="map-planned-manage-itinerary"
                        onClick={() => {
                          setMenuOpen(false);
                          onManageItinerary();
                        }}
                        className={MENU_ITEM}
                      >
                        Manage in Itinerary
                      </button>
                    ) : (
                      <button
                        type="button"
                        role="menuitem"
                        data-testid="map-planned-unplace"
                        onClick={() => run(() => onUnplace(item.id)).then(() => setMenuOpen(false))}
                        disabled={busy}
                        className={MENU_ITEM}
                        title="Move this back to your Ideas tray (keeps all its details)"
                      >
                        Back to Ideas
                      </button>
                    )}
                    {/* Remove from trip = permanent delete, explicit text + two-step confirm. */}
                    <button
                      type="button"
                      role="menuitem"
                      data-testid="map-planned-remove"
                      onClick={() => setConfirmRemove(true)}
                      disabled={busy}
                      className={`${MENU_ITEM} text-ds-warning`}
                    >
                      Remove from trip…
                    </button>
                  </>
                )}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </article>
  );
}

// ── Ideas lens body — durable Add to Day / Keep as Maybe / Remove (guarded) ────

function IdeasLensBody({
  ideas,
  ideaPinIds,
  ideaLinkItems,
  days,
  selectedPinId,
  onSelect,
  onAssign,
  onKeepMaybe,
  onRemove,
  onManage,
}: {
  ideas: ItineraryItem[];
  ideaPinIds: string[];
  ideaLinkItems: ItineraryItem[];
  days: ItineraryDay[];
  selectedPinId: string | null;
  onSelect: (id: string) => void;
  onAssign: (itemId: string, dayId: string) => Promise<void>;
  onKeepMaybe: (item: ItineraryItem) => Promise<void>;
  onRemove: (itemId: string) => Promise<void>;
  onManage: () => void;
}) {
  const mapped = ideas.filter((i) => ideaPinIds.includes(i.id));

  if (ideas.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-ds-folio-ink-mist" data-testid="map-empty-state">
        No saved ideas yet. Save places from Explore or your Folio to plan them on the map.
      </p>
    );
  }

  return (
    <>
      {mapped.length > 0 ? (
        <>
          <p className="px-1 pt-1 text-[11px] font-medium uppercase tracking-wide text-ds-folio-ink-mist">
            On the map
          </p>
          {mapped.map((item) => (
            <IdeaLensCard
              key={item.id}
              item={item}
              days={days}
              selected={selectedPinId === item.id}
              onSelect={onSelect}
              onAssign={onAssign}
              onKeepMaybe={onKeepMaybe}
              onRemove={onRemove}
              onManage={onManage}
            />
          ))}
        </>
      ) : (
        <p className="py-4 text-center text-sm text-ds-folio-ink-mist" data-testid="map-ideas-no-pins">
          No saved ideas have map coordinates yet.
        </p>
      )}

      {/* Needs-location: real ideas without coordinates but with a real Maps URL. */}
      {ideaLinkItems.length > 0 ? (
        <>
          <p className="px-1 pt-3 text-[11px] font-medium uppercase tracking-wide text-ds-folio-ink-mist">
            Needs location
          </p>
          <p className="px-1 pb-1 text-[11px] italic text-ds-folio-ink-mist" data-testid="map-needs-location-note">
            These saved ideas can open in Google Maps but don&apos;t have coordinates to plot yet.
          </p>
          {ideaLinkItems.map((item) => {
            const url = mapsUrlOf(item)!;
            return (
              <a
                key={item.id}
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                data-testid="map-idea-link-row"
                className="jd-day-item flex items-center gap-3 p-3 hover:border-ds-marine-ink/40 transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2"
              >
                <span className="flex-1 min-w-0">
                  <span className="block font-serif text-sm font-semibold text-ds-folio-ink leading-snug truncate">
                    {item.title}
                  </span>
                  <span className="block text-[11px] text-ds-folio-ink-mist">{kindOf(item)}</span>
                </span>
                <ExternalLink className="w-3.5 h-3.5 flex-shrink-0 text-ds-folio-ink-mist" aria-hidden="true" />
              </a>
            );
          })}
        </>
      ) : null}
    </>
  );
}

function IdeaLensCard({
  item,
  days,
  selected,
  onSelect,
  onAssign,
  onKeepMaybe,
  onRemove,
  onManage,
}: {
  item: ItineraryItem;
  days: ItineraryDay[];
  selected: boolean;
  onSelect: (id: string) => void;
  onAssign: (itemId: string, dayId: string) => Promise<void>;
  onKeepMaybe: (item: ItineraryItem) => Promise<void>;
  onRemove: (itemId: string) => Promise<void>;
  onManage: () => void;
}) {
  const ref = useRef<HTMLElement>(null);
  const [pickDay, setPickDay] = useState(false);
  const [busy, setBusy] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);

  useEffect(() => {
    if (selected && ref.current) ref.current.scrollIntoView({ block: "nearest" });
  }, [selected]);

  const note = userNoteOf(item);
  const reason = reasonOf(item);
  const rating = ratingOf(item);
  const mapsUrl = mapsUrlOf(item);
  const location = item.location && item.location !== item.title ? item.location : "";
  const dayAssignable = days.length > 0;

  const SECONDARY_LINK =
    "text-xs font-medium text-ds-folio-ink-soft hover:text-ds-marine-ink transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 rounded";

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  }

  return (
    <article
      ref={ref}
      data-testid="map-idea-card"
      data-kind={item.itemType}
      onClick={() => onSelect(item.id)}
      className={`jd-tray-card p-3.5 cursor-pointer ${selected ? "ring-2 ring-ds-marine-ink/50" : ""}`}
    >
      <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-ds-folio-ink-mist">
        <MapPin className="w-3 h-3 text-ds-accent" aria-hidden="true" />
        {kindOf(item)}
      </div>

      <h3 className="mt-1 font-serif text-base font-semibold text-ds-folio-ink leading-snug">{item.title}</h3>

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

      {note && (
        <p
          data-testid="map-idea-note-private"
          className="jd-note-private mt-2 font-serif italic text-sm text-ds-folio-ink line-clamp-1"
        >
          {note}
        </p>
      )}
      {reason && reason !== note && (
        <p className="mt-1.5 inline-flex items-center gap-1.5 text-xs text-ds-folio-ink-mist line-clamp-1">
          <Sparkles className="w-3 h-3 flex-shrink-0 text-ds-accent" aria-hidden="true" />
          {reason}
        </p>
      )}

      {/* Primary action — durable, day-level only (no fabricated slot) */}
      <div className="mt-3" onClick={(e) => e.stopPropagation()}>
        {dayAssignable ? (
          pickDay ? (
            <div data-testid="map-idea-day-picker" className="rounded-lg border border-ds-hairline p-2">
              <p className="px-1 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-ds-folio-ink-mist">
                Add to which day
              </p>
              <div className="flex flex-col gap-1">
                {days.map((d) => (
                  <button
                    key={d.id}
                    type="button"
                    disabled={busy}
                    onClick={() => run(() => onAssign(item.id, d.id))}
                    className="flex items-center justify-between gap-2 min-h-[44px] rounded-md px-2.5 text-left text-sm text-ds-folio-ink ring-1 ring-ds-marine-ink/30 hover:ring-ds-marine-ink hover:text-ds-marine-ink transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 disabled:opacity-50"
                  >
                    <span className="font-medium">Day {d.dayNumber}</span>
                    {d.date && <span className="text-xs text-ds-folio-ink-mist">{d.date}</span>}
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
              data-testid="map-idea-add-to-day"
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
            data-testid="map-idea-add-to-day"
            onClick={() => run(() => onKeepMaybe(item))}
            disabled={busy}
            className="w-full inline-flex items-center justify-center gap-1.5 min-h-[44px] rounded-lg text-sm font-medium bg-ds-marine-ink text-ds-paper hover:bg-ds-marine-soft transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 disabled:opacity-50"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : "Keep as Maybe"}
          </button>
        )}
      </div>

      {/* Secondary actions — quiet, contextual to real durable behavior only */}
      <div className="mt-2.5 flex items-center flex-wrap gap-x-4 gap-y-1" onClick={(e) => e.stopPropagation()}>
        {mapsUrl && (
          <a href={mapsUrl} target="_blank" rel="noopener noreferrer" className={SECONDARY_LINK}>
            Map
          </a>
        )}
        {dayAssignable && (
          <button type="button" onClick={() => run(() => onKeepMaybe(item))} disabled={busy} className={SECONDARY_LINK}>
            Keep as Maybe
          </button>
        )}
        <button type="button" onClick={onManage} className={SECONDARY_LINK}>
          {note ? "Edit note in Ideas" : "Manage in Ideas"}
        </button>
        {/* Remove idea = permanent delete, two-step confirm guard. */}
        {confirmRemove ? (
          <span className="ml-auto inline-flex items-center gap-3" data-testid="map-idea-remove-confirm">
            <button
              type="button"
              onClick={() => run(() => onRemove(item.id))}
              disabled={busy}
              className="text-xs font-semibold text-ds-warning hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-warning focus-visible:outline-offset-2 rounded"
            >
              {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Confirm remove idea"}
            </button>
            <button type="button" onClick={() => setConfirmRemove(false)} disabled={busy} className={SECONDARY_LINK}>
              Cancel
            </button>
          </span>
        ) : (
          <button
            type="button"
            data-testid="map-idea-remove"
            onClick={() => setConfirmRemove(true)}
            disabled={busy}
            className={`${SECONDARY_LINK} ml-auto`}
          >
            Remove idea
          </button>
        )}
      </div>
    </article>
  );
}
