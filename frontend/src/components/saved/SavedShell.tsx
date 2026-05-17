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
    <Card tone="paper" as="article" className="card-lift p-4" data-testid="saved-item-card">
      <Card.Identity>
        {/* Vertical icon — uniform warm accent treatment */}
        <div
          aria-hidden="true"
          className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 mt-0.5"
          style={{ backgroundColor: "var(--ds-accent-subtle)" }}
        >
          <Icon className="w-5 h-5 text-ds-accent" />
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
                  className="min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg bg-ds-bone hover:bg-ds-linen text-ds-slate transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                  aria-label={`View ${name} on Google Maps`}
                >
                  <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
                </a>
              )}
              <button
                onClick={handleRemove}
                disabled={removing}
                aria-label={`Remove ${name} from saved`}
                className="min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg bg-ds-bone hover:bg-ds-hairline text-ds-slate hover:text-ds-warning transition-colors disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                data-testid="remove-saved-btn"
              >
                {removing ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                ) : (
                  <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
                )}
              </button>
            </div>
          </div>

          {/* Name + subtitle */}
          <h3
            className="text-sm font-semibold text-ds-text-inverse leading-tight truncate"
            data-testid="saved-item-name"
          >
            {name}
          </h3>
          {subtitle && (
            <p className="text-xs text-ds-slate mt-0.5 truncate">{subtitle}</p>
          )}

          {/* Rating + price + tags */}
          {(rating != null || priceStr || tagList.length > 0) && (
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              {rating != null && (
                <span
                  className="flex items-center gap-0.5 text-xs text-ds-text-inverse font-medium"
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
          <p className="text-[10px] text-ds-slate opacity-60 mt-2">Saved {savedDate}</p>

          {/* Planning bridge — Create Trip + Add to Trip */}
          <div
            className="mt-3 pt-2.5 border-t border-ds-hairline/60"
            data-testid="saved-planning-bridge"
          >
            <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-slate mb-2">
              Plan with this
            </p>

            {/* Create Trip — all verticals */}
            <div className="mb-1.5" data-testid="create-trip-section">
              <button
                onClick={() => onCreateTrip(item)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-ds-bone text-ds-text-inverse hover:bg-ds-linen transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                data-testid="create-trip-btn"
              >
                <Sparkles className="w-3.5 h-3.5 text-ds-accent" aria-hidden="true" />
                Create Trip
              </button>
            </div>

            {/* Add to Trip — non-flight verticals */}
            {canAddToTrip && (
              <div data-testid="add-to-trip-section">
                {addState === "idle" && (
                  <button
                    onClick={() => setAddState("picking")}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-ds-bone text-ds-text-inverse hover:bg-ds-linen transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                    data-testid="add-to-trip-btn"
                  >
                    <PlusCircle className="w-3.5 h-3.5 text-ds-slate" aria-hidden="true" />
                    Add to Trip
                  </button>
                )}

                {addState === "picking" && (
                  <div className="space-y-1" data-testid="trip-picker">
                    {trips.length === 0 ? (
                      <p className="text-xs text-ds-slate py-1">
                        No trips yet.{" "}
                        <Link
                          href="/trips/new"
                          className="text-ds-text-inverse underline hover:opacity-70 transition-opacity"
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
                            key={trip.id}
                            onClick={() => handleAddToTrip(trip)}
                            className="w-full text-left px-3 py-1.5 rounded-lg text-xs text-ds-text-inverse bg-ds-bone hover:bg-ds-linen transition-colors truncate focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                            data-testid="trip-picker-option"
                          >
                            {trip.title} · {trip.destination}
                          </button>
                        ))}
                      </>
                    )}
                    <button
                      onClick={() => setAddState("idle")}
                      className="text-[10px] text-ds-slate hover:text-ds-text-inverse transition-colors"
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
                      className="flex items-center gap-1.5 text-xs text-ds-text-inverse"
                      data-testid="add-to-trip-success"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 text-ds-trust" aria-hidden="true" />
                      Added to {addedToTripName}
                    </div>
                    <button
                      onClick={() => setAddState("idle")}
                      className="text-[10px] text-ds-slate hover:text-ds-text-inverse transition-colors"
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
                      onClick={() => setAddState("idle")}
                      className="text-[10px] text-ds-slate hover:text-ds-text-inverse transition-colors"
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
    </Card>
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

  const { label, key } = config;

  return (
    <section data-testid={`saved-section-${key}`} aria-label={`${label} ideas`}>
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-ds-hairline">
        <p
          className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-accent-muted"
          data-testid={`saved-section-label-${key}`}
        >
          {label}
        </p>
        <span className="text-[10px] text-ds-slate font-medium">{items.length}</span>
      </div>
      <div className="space-y-3">
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
    /* Warm-paper scrapbook surface — linen album on midnight ink shell (§9) */
    <div
      className="max-w-2xl mx-auto bg-ds-linen rounded-2xl px-6 py-6 space-y-8"
      data-testid="saved-shell"
    >
      {/* Scrapbook editorial header */}
      <header data-testid="saved-scrapbook-header">
        <div className="flex items-start gap-3">
          <div
            aria-hidden="true"
            className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 mt-0.5"
            style={{ backgroundColor: "var(--ds-accent-subtle)" }}
          >
            <Bookmark className="w-5 h-5 text-ds-accent" />
          </div>
          <div>
            <p
              className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-accent"
              data-testid="saved-scrapbook-overline"
            >
              Your Travel Scrapbook
            </p>
            <h1
              className="text-xl font-bold text-ds-text-inverse leading-tight"
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
      </header>

      {/* Loading */}
      {loading && (
        <div
          className="flex items-center justify-center py-16 text-ds-slate"
          data-testid="saved-loading"
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
          <p className="text-sm text-ds-slate">{error}</p>
          <button
            onClick={load}
            className="px-4 py-2 rounded-lg bg-ds-bone text-ds-text-inverse text-sm hover:bg-ds-hairline transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
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
            <p className="text-base font-semibold text-ds-text-inverse">Nothing saved yet</p>
            <p className="text-sm text-ds-slate mt-1">
              Explore restaurants, attractions, and hotels — then save the ones that inspire you.
            </p>
          </div>
          <Link
            href="/explore"
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-ds-bone text-ds-text-inverse text-sm font-medium hover:bg-ds-hairline transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
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
