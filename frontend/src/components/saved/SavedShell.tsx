"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Bookmark,
  Utensils,
  Landmark,
  Building2,
  Plane,
  Trash2,
  ExternalLink,
  Star,
  Compass,
  Loader2,
  AlertCircle,
  Calendar,
  Users,
  PlusCircle,
  CheckCircle2,
  Sparkles,
} from "lucide-react";
import { listSavedItems, deleteSavedItem, fetchTrips, addSavedItemToTrip } from "@/lib/api";
import type { SavedItem, SavedItemVertical, Trip } from "@/types";
import { CreateTripFromSavedModal } from "./CreateTripFromSavedModal";
import { Card } from "@/components/ui/Card";

// ── Vertical config ───────────────────────────────────────────────────────────

const VERTICAL_CONFIG = [
  { key: "restaurant" as SavedItemVertical, label: "Restaurants", icon: Utensils },
  { key: "attraction" as SavedItemVertical, label: "Attractions", icon: Landmark },
  { key: "hotel" as SavedItemVertical, label: "Hotels", icon: Building2 },
  { key: "flight" as SavedItemVertical, label: "Flights", icon: Plane },
] as const;

type VerticalCfg = (typeof VERTICAL_CONFIG)[number];

// Overline type labels for scrapbook idea identity (§8C TYPE_LABELS pattern)
const TYPE_OVERLINES: Record<SavedItemVertical, string> = {
  restaurant: "Restaurant",
  attraction: "Attraction",
  hotel: "Hotel",
  flight: "Flight",
};

// ── Snapshot / context field helpers ─────────────────────────────────────────

function snapStr(item: SavedItem, key: string): string | null {
  const v = item.displaySnapshot[key];
  return typeof v === "string" && v ? v : null;
}

function snapNum(item: SavedItem, key: string): number | null {
  const v = item.displaySnapshot[key];
  return typeof v === "number" ? v : null;
}

function snapTags(item: SavedItem): string[] {
  const v = item.displaySnapshot["tags"];
  return Array.isArray(v) ? (v as string[]) : [];
}

function ctxStr(item: SavedItem, key: string): string | null {
  const v = item.searchContext[key];
  return typeof v === "string" && v ? v : null;
}

function ctxNum(item: SavedItem, key: string): number | null {
  const v = item.searchContext[key];
  return typeof v === "number" ? v : null;
}

function formatSavedDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

// ── Add-to-Trip state ─────────────────────────────────────────────────────────

type AddState = "idle" | "picking" | "adding" | "added" | "error";

// ── Saved Item Card ───────────────────────────────────────────────────────────

function SavedItemCard({
  item,
  vertConfig,
  trips,
  onRemove,
  onCreateTrip,
}: {
  item: SavedItem;
  vertConfig: VerticalCfg;
  trips: Trip[];
  onRemove: (id: string) => void;
  onCreateTrip: (item: SavedItem) => void;
}) {
  const [removing, setRemoving] = useState(false);
  const [removeError, setRemoveError] = useState<string | null>(null);
  const [addState, setAddState] = useState<AddState>("idle");
  const [addedToTripName, setAddedToTripName] = useState<string | null>(null);
  const [addError, setAddError] = useState<string | null>(null);

  const { icon: Icon } = vertConfig;

  const name = snapStr(item, "name") ?? item.displayName;
  const destination = snapStr(item, "destination") ?? ctxStr(item, "destination");
  const address = snapStr(item, "address");
  const rating = snapNum(item, "rating");
  const googleMapsUri = snapStr(item, "googleMapsUri");
  const tagList = snapTags(item);

  // Restaurant-specific
  const cuisine = item.vertical === "restaurant" ? snapStr(item, "cuisine") : null;
  const priceLevel = item.vertical === "restaurant" ? snapNum(item, "priceLevel") : null;
  const priceStr = priceLevel != null ? "$".repeat(Math.min(priceLevel, 4)) : null;

  // Hotel search context — discovery only, no rates or booking fields
  const checkIn = item.vertical === "hotel" ? ctxStr(item, "checkIn") : null;
  const checkOut = item.vertical === "hotel" ? ctxStr(item, "checkOut") : null;
  const guests = item.vertical === "hotel" ? ctxNum(item, "guests") : null;

  const savedDate = formatSavedDate(item.createdAt);

  // Flights are not yet supported for trip conversion
  const canAddToTrip = item.vertical !== "flight";

  // Secondary line: cuisine + address, or destination fallback
  const subtitle =
    [cuisine, address].filter(Boolean).join(" · ") || destination || null;

  async function handleRemove() {
    if (removing) return;
    setRemoving(true);
    setRemoveError(null);
    try {
      await deleteSavedItem(item.id);
      onRemove(item.id);
    } catch {
      setRemoving(false);
      setRemoveError("Could not remove. Please try again.");
    }
  }

  async function handleAddToTrip(trip: Trip) {
    setAddState("adding");
    setAddError(null);
    try {
      await addSavedItemToTrip(trip.id, item);
      setAddedToTripName(trip.title);
      setAddState("added");
    } catch {
      setAddState("error");
      setAddError("Could not add to trip. Please try again.");
    }
  }

  return (
    <article
      className="saved-folio-card card-lift p-3"
      data-testid="saved-item-card"
    >
      <Card.Identity>
        {/* Vertical icon — uniform warm accent treatment */}
        <div
          aria-hidden="true"
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
          style={{ backgroundColor: "var(--ds-accent-subtle)" }}
        >
          <Icon className="w-4 h-4 text-ds-accent" />
        </div>

        <div className="flex-1 min-w-0">
          {/* Type overline + action cluster */}
          <div className="flex items-center justify-between gap-2 mb-0.5">
            <p
              className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-accent-muted"
              data-testid="saved-item-type-overline"
            >
              {TYPE_OVERLINES[item.vertical]}
            </p>
            <div className="flex items-center gap-0.5 shrink-0">
              {googleMapsUri && (
                <a
                  href={googleMapsUri}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="min-w-[44px] min-h-[44px] flex items-center justify-center rounded-md text-ds-slate hover:text-ds-accent-muted transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                  aria-label={`View ${name} on Google Maps`}
                >
                  <ExternalLink className="w-3 h-3" aria-hidden="true" />
                </a>
              )}
              <button
                type="button"
                onClick={handleRemove}
                disabled={removing}
                aria-label={`Remove ${name} from saved`}
                className="min-w-[44px] min-h-[44px] flex items-center justify-center rounded-md text-ds-slate hover:text-ds-warning transition-colors disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                data-testid="remove-saved-btn"
              >
                {removing ? (
                  <Loader2 className="w-3 h-3 animate-spin" aria-hidden="true" />
                ) : (
                  <Trash2 className="w-3 h-3" aria-hidden="true" />
                )}
              </button>
            </div>
          </div>

          {/* Name + subtitle */}
          <h3
            className="text-sm font-semibold text-ds-text leading-tight truncate"
            data-testid="saved-item-name"
          >
            {name}
          </h3>
          {subtitle && (
            <p className="text-xs text-ds-slate mt-0.5 truncate">{subtitle}</p>
          )}

          {/* Rating + price + tags */}
          {(rating != null || priceStr || tagList.length > 0) && (
            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
              {rating != null && (
                <span
                  className="flex items-center gap-0.5 text-xs text-ds-text font-medium"
                  data-testid="saved-card-rating"
                >
                  <Star className="w-3 h-3 text-ds-accent fill-current" aria-hidden="true" />
                  {rating.toFixed(1)}
                </span>
              )}
              {priceStr && (
                <span className="text-xs text-ds-slate font-medium">{priceStr}</span>
              )}
              {tagList.length > 0 && (
                <div className="flex gap-1 flex-wrap">
                  {tagList.slice(0, 3).map((tag) => (
                    <span
                      key={tag}
                      className="px-1.5 py-0.5 text-[10px] rounded-full border border-ds-hairline text-ds-slate"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Hotel: dates + guests from search context — discovery only, no rates */}
          {item.vertical === "hotel" && (checkIn || checkOut || guests != null) && (
            <div
              className="flex items-center gap-3 mt-1.5 flex-wrap"
              data-testid="hotel-search-context"
            >
              {(checkIn || checkOut) && (
                <span className="flex items-center gap-1 text-xs text-ds-slate">
                  <Calendar className="w-3 h-3" aria-hidden="true" />
                  {[checkIn, checkOut].filter(Boolean).join(" → ")}
                </span>
              )}
              {guests != null && (
                <span className="flex items-center gap-1 text-xs text-ds-slate">
                  <Users className="w-3 h-3" aria-hidden="true" />
                  {guests} {guests === 1 ? "guest" : "guests"}
                </span>
              )}
            </div>
          )}

          {/* Saved date */}
          <p className="text-[10px] text-ds-slate opacity-50 mt-1.5">Saved {savedDate}</p>

          {/* Planning bridge — compact horizontal action row */}
          <div
            className="mt-2 pt-2 border-t border-ds-hairline/40"
            data-testid="saved-planning-bridge"
          >
            <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-slate mb-1.5">
              Plan with this
            </p>

            {/* Idle: compact horizontal pill row */}
            <div className="flex items-center gap-1.5 flex-wrap">
              {/* Create Trip — all verticals */}
              <div data-testid="create-trip-section">
                <button
                  type="button"
                  onClick={() => onCreateTrip(item)}
                  className="min-h-[44px] flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium bg-ds-accent-subtle text-ds-accent border border-ds-accent/20 hover:opacity-90 transition-opacity focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                  data-testid="create-trip-btn"
                >
                  <Sparkles className="w-3 h-3 text-ds-accent" aria-hidden="true" />
                  Create Trip
                </button>
              </div>

              {/* Add to Trip — non-flight verticals, idle state only shows pill */}
              {canAddToTrip && addState === "idle" && (
                <div data-testid="add-to-trip-section">
                  <button
                    type="button"
                    onClick={() => setAddState("picking")}
                    className="min-h-[44px] flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium border border-ds-pen-stroke text-ds-text-secondary hover:border-ds-accent/40 hover:text-ds-accent transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent"
                    data-testid="add-to-trip-btn"
                  >
                    <PlusCircle className="w-3 h-3" aria-hidden="true" />
                    Add to Trip
                  </button>
                </div>
              )}
            </div>

            {/* Add to Trip — non-idle states */}
            {canAddToTrip && addState !== "idle" && (
              <div data-testid="add-to-trip-section" className="mt-1.5">
                {addState === "picking" && (
                  <div className="space-y-1" data-testid="trip-picker">
                    {trips.length === 0 ? (
                      <p className="text-xs text-ds-slate py-1">
                        No trips yet.{" "}
                        <Link
                          href="/trips/new"
                          className="text-ds-text underline hover:opacity-70 transition-opacity"
                        >
                          Create one
                        </Link>
                      </p>
                    ) : (
                      <>
                        <p className="text-[10px] text-ds-slate uppercase tracking-[0.1em]">
                          Choose a trip
                        </p>
                        {trips.map((trip) => (
                          <button
                            type="button"
                            key={trip.id}
                            onClick={() => handleAddToTrip(trip)}
                            className="min-h-[44px] w-full text-left px-3 py-1.5 rounded-lg text-xs text-ds-text bg-ds-carbon border border-ds-pen-stroke hover:bg-ds-onyx transition-colors truncate focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                            data-testid="trip-picker-option"
                          >
                            {trip.title} · {trip.destination}
                          </button>
                        ))}
                      </>
                    )}
                    <button
                      type="button"
                      onClick={() => setAddState("idle")}
                      className="min-h-[44px] flex items-center text-[10px] text-ds-slate hover:text-ds-text transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                )}

                {addState === "adding" && (
                  <div className="flex items-center gap-1.5 text-xs text-ds-slate py-1">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                    Adding to trip…
                  </div>
                )}

                {addState === "added" && (
                  <div className="space-y-1">
                    <div
                      className="flex items-center gap-1.5 text-xs text-ds-text"
                      data-testid="add-to-trip-success"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 text-ds-trust" aria-hidden="true" />
                      Added to {addedToTripName}
                    </div>
                    <button
                      type="button"
                      onClick={() => setAddState("idle")}
                      className="min-h-[44px] flex items-center text-[10px] text-ds-slate hover:text-ds-text transition-colors"
                    >
                      Add to another trip
                    </button>
                  </div>
                )}

                {addState === "error" && (
                  <div className="space-y-1">
                    <p className="text-xs text-ds-warning" data-testid="add-to-trip-error">
                      {addError}
                    </p>
                    <button
                      type="button"
                      onClick={() => setAddState("idle")}
                      className="min-h-[44px] flex items-center text-[10px] text-ds-slate hover:text-ds-text transition-colors"
                    >
                      Try again
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Remove error */}
          {removeError && (
            <p className="text-xs text-ds-warning mt-1" data-testid="remove-error">
              {removeError}
            </p>
          )}
        </div>
      </Card.Identity>
    </article>
  );
}

// ── Vertical group ─────────────────────────────────────────────────────────────

function VerticalGroup({
  config,
  items,
  trips,
  onRemove,
  onCreateTrip,
}: {
  config: VerticalCfg;
  items: SavedItem[];
  trips: Trip[];
  onRemove: (id: string) => void;
  onCreateTrip: (item: SavedItem) => void;
}) {
  if (items.length === 0) return null;

  const { label, key, icon: SectionIcon } = config;

  return (
    <section data-testid={`saved-section-${key}`} aria-label={`${label} ideas`}>
      {/* Editorial scrapbook section header — icon + label + count */}
      <div className="flex items-center gap-2 mb-3 pb-2 border-b border-ds-hairline">
        <div aria-hidden="true" className="w-5 h-5 flex items-center justify-center shrink-0">
          <SectionIcon className="w-3.5 h-3.5 text-ds-accent-muted" />
        </div>
        <p
          className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-accent-muted flex-1"
          data-testid={`saved-section-label-${key}`}
        >
          {label}
        </p>
        <span className="text-[10px] text-ds-text-secondary font-medium tabular-nums">
          {items.length}
        </span>
      </div>
      {/* Two-column grid on desktop — single column on mobile */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {items.map((item) => (
          <SavedItemCard
            key={item.id}
            item={item}
            vertConfig={config}
            trips={trips}
            onRemove={onRemove}
            onCreateTrip={onCreateTrip}
          />
        ))}
      </div>
    </section>
  );
}

// ── SavedShell ─────────────────────────────────────────────────────────────────

export function SavedShell() {
  const router = useRouter();
  const [items, setItems] = useState<SavedItem[]>([]);
  const [trips, setTrips] = useState<Trip[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createTripFor, setCreateTripFor] = useState<SavedItem | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, tripList] = await Promise.all([listSavedItems(), fetchTrips()]);
      setItems(data.filter((i) => i.status === "active"));
      setTrips(tripList);
    } catch {
      setError("Could not load saved ideas. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleRemove = useCallback((id: string) => {
    setItems((prev) => prev.filter((i) => i.id !== id));
  }, []);

  const handleCreateTrip = useCallback((item: SavedItem) => {
    setCreateTripFor(item);
  }, []);

  const grouped = VERTICAL_CONFIG.map((cfg) => ({
    config: cfg,
    items: items.filter((i) => i.vertical === cfg.key),
  }));

  const hasAny = items.length > 0;

  return (
    <div
      className="max-w-2xl lg:max-w-4xl mx-auto saved-clipping-desk atelier-transition py-6 px-4 sm:px-6"
      data-testid="saved-shell"
    >
      {/* Folio header — dark integrated shelf label, no cream slab */}
      <div className="saved-folio-header pt-4 pb-3 px-1 mb-6">
        <header data-testid="saved-scrapbook-header">
          <div className="flex items-start gap-3">
            <div
              aria-hidden="true"
              className="w-9 h-9 rounded-xl flex items-center justify-center bg-ds-accent-subtle shrink-0 mt-0.5"
            >
              <Bookmark className="w-4 h-4 text-ds-accent-muted" />
            </div>
            <div className="flex-1 min-w-0">
              <p
                className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-accent"
                data-testid="saved-scrapbook-overline"
              >
                Your Travel Scrapbook
              </p>
              <h1
                className="text-xl font-bold text-ds-text leading-tight"
                data-testid="saved-scrapbook-heading"
              >
                Saved Ideas
              </h1>
              {!loading && !error && hasAny && (
                <p className="text-xs text-ds-slate mt-0.5" data-testid="saved-scrapbook-count">
                  {items.length} {items.length === 1 ? "idea" : "ideas"} in your collection
                </p>
              )}
            </div>
          </div>
          {/* Editorial section rule below the scrapbook header */}
          <div className="editorial-section-rule mt-4" aria-hidden="true" />
        </header>
      </div>

      {/* Content zone — cards float as clippings on the dark atelier surface */}

      {/* Loading */}
      {loading && (
        <div
          data-testid="saved-loading"
          className="flex items-center justify-center py-16 text-ds-text-secondary"
        >
          <Loader2 className="w-6 h-6 animate-spin mr-2" aria-hidden="true" />
          <span className="text-sm">Loading your saved ideas…</span>
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div
          className="flex flex-col items-center gap-3 py-12 text-center"
          data-testid="saved-error"
        >
          <AlertCircle className="w-8 h-8 text-ds-warning" aria-hidden="true" />
          <p className="text-sm text-ds-text-secondary">{error}</p>
          <button
            type="button"
            onClick={load}
            className="min-h-[44px] px-4 py-2 rounded-lg bg-ds-carbon border border-ds-pen-stroke text-ds-text text-sm hover:bg-ds-onyx transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
          >
            Try again
          </button>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && !hasAny && (
        <div
          className="flex flex-col items-center gap-4 py-16 text-center"
          data-testid="saved-empty"
        >
          <div
            className="w-14 h-14 rounded-2xl bg-ds-bone flex items-center justify-center"
            aria-hidden="true"
          >
            <Bookmark className="w-7 h-7 text-ds-accent" />
          </div>
          <div>
            <p className="text-base font-semibold text-ds-text">Nothing saved yet</p>
            <p className="text-sm text-ds-text-secondary mt-1">
              Explore restaurants, attractions, and hotels — then save the ones that inspire you.
            </p>
          </div>
          <Link
            href="/explore"
            className="min-h-[44px] flex items-center gap-2 px-5 py-2.5 rounded-xl bg-ds-carbon border border-ds-pen-stroke text-ds-text text-sm font-medium hover:bg-ds-onyx transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
            data-testid="saved-empty-explore-link"
          >
            <Compass className="w-4 h-4" aria-hidden="true" />
            Start Exploring
          </Link>
        </div>
      )}

      {/* Grouped verticals */}
      {!loading && !error && hasAny && (
        <div className="space-y-8">
          {grouped.map(({ config, items: groupItems }) => (
            <VerticalGroup
              key={config.key}
              config={config}
              items={groupItems}
              trips={trips}
              onRemove={handleRemove}
              onCreateTrip={handleCreateTrip}
            />
          ))}
        </div>
      )}

      {createTripFor && (
        <CreateTripFromSavedModal
          item={createTripFor}
          onClose={() => setCreateTripFor(null)}
          onCreated={(trip) => {
            setCreateTripFor(null);
            router.push(`/trips/${trip.id}`);
          }}
        />
      )}
    </div>
  );
}
