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

// ── Vertical config ───────────────────────────────────────────────────────────

const VERTICAL_CONFIG = [
  {
    key: "restaurant" as SavedItemVertical,
    label: "Restaurants",
    icon: Utensils,
    iconBg: "bg-amber-500/10",
    iconColor: "text-amber-400",
  },
  {
    key: "attraction" as SavedItemVertical,
    label: "Attractions",
    icon: Landmark,
    iconBg: "bg-blue-500/10",
    iconColor: "text-blue-400",
  },
  {
    key: "hotel" as SavedItemVertical,
    label: "Hotels",
    icon: Building2,
    iconBg: "bg-violet-500/10",
    iconColor: "text-violet-400",
  },
  {
    key: "flight" as SavedItemVertical,
    label: "Flights",
    icon: Plane,
    iconBg: "bg-sky-500/10",
    iconColor: "text-sky-400",
  },
] as const;

type VerticalCfg = (typeof VERTICAL_CONFIG)[number];

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

  const { icon: Icon, iconBg, iconColor } = vertConfig;

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
    <div className="card card-lift p-4" data-testid="saved-item-card">
      <div className="flex items-start gap-3">
        {/* Vertical icon */}
        <div
          className={`w-10 h-10 rounded-xl ${iconBg} ${iconColor} flex items-center justify-center shrink-0`}
        >
          <Icon className="w-5 h-5" />
        </div>

        <div className="flex-1 min-w-0">
          {/* Name + action row */}
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-cream-100 leading-tight truncate">
                {name}
              </h3>
              {subtitle && (
                <p className="text-xs text-cream-500 mt-0.5 truncate">{subtitle}</p>
              )}
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              {googleMapsUri && (
                <a
                  href={googleMapsUri}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1.5 rounded-lg bg-white/[.05] hover:bg-white/[.10] text-cream-400 transition"
                  aria-label={`View ${name} on Google Maps`}
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
              <button
                onClick={handleRemove}
                disabled={removing}
                aria-label={`Remove ${name} from saved`}
                className="p-1.5 rounded-lg bg-white/[.04] hover:bg-rose-500/10 text-cream-600 hover:text-rose-400 transition disabled:opacity-50"
                data-testid="remove-saved-btn"
              >
                {removing ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Trash2 className="w-3.5 h-3.5" />
                )}
              </button>
            </div>
          </div>

          {/* Rating + price + tags */}
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            {rating != null && (
              <span
                className="flex items-center gap-0.5 text-xs text-amber-400 font-medium"
                data-testid="saved-card-rating"
              >
                <Star className="w-3 h-3 fill-amber-400" />
                {rating.toFixed(1)}
              </span>
            )}
            {priceStr && (
              <span className="text-xs text-cream-400 font-medium">{priceStr}</span>
            )}
            {tagList.length > 0 && (
              <div className="flex gap-1 flex-wrap">
                {tagList.slice(0, 3).map((tag) => (
                  <span
                    key={tag}
                    className="px-1.5 py-0.5 text-[10px] rounded-full bg-white/[.06] text-cream-400"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Hotel: dates + guests from search context — discovery only, no rates */}
          {item.vertical === "hotel" && (checkIn || checkOut || guests != null) && (
            <div
              className="flex items-center gap-3 mt-1.5 flex-wrap"
              data-testid="hotel-search-context"
            >
              {(checkIn || checkOut) && (
                <span className="flex items-center gap-1 text-xs text-cream-500">
                  <Calendar className="w-3 h-3" />
                  {[checkIn, checkOut].filter(Boolean).join(" → ")}
                </span>
              )}
              {guests != null && (
                <span className="flex items-center gap-1 text-xs text-cream-500">
                  <Users className="w-3 h-3" />
                  {guests} {guests === 1 ? "guest" : "guests"}
                </span>
              )}
            </div>
          )}

          {/* Saved date */}
          <p className="text-[10px] text-cream-700 mt-2">Saved {savedDate}</p>

          {/* Create Trip — all verticals (Stage 3 v3) */}
          <div className="mt-2" data-testid="create-trip-section">
            <button
              onClick={() => onCreateTrip(item)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-brand-500/10 text-brand-300 hover:bg-brand-500/20 transition"
              data-testid="create-trip-btn"
            >
              <Sparkles className="w-3.5 h-3.5" />
              Create Trip
            </button>
          </div>

          {/* Add to Trip */}
          {canAddToTrip && (
            <div className="mt-2" data-testid="add-to-trip-section">
              {addState === "idle" && (
                <button
                  onClick={() => setAddState("picking")}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white/[.06] text-cream-400 hover:bg-white/[.10] transition"
                  data-testid="add-to-trip-btn"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  Add to Trip
                </button>
              )}

              {addState === "picking" && (
                <div className="space-y-1" data-testid="trip-picker">
                  {trips.length === 0 ? (
                    <p className="text-xs text-cream-500 py-1">
                      No trips yet.{" "}
                      <Link href="/trips/new" className="text-brand-400 hover:underline">
                        Create one
                      </Link>
                    </p>
                  ) : (
                    <>
                      <p className="text-[10px] text-cream-600 uppercase tracking-wide">
                        Choose a trip
                      </p>
                      {trips.map((trip) => (
                        <button
                          key={trip.id}
                          onClick={() => handleAddToTrip(trip)}
                          className="w-full text-left px-3 py-1.5 rounded-lg text-xs text-cream-300 bg-white/[.05] hover:bg-white/[.10] transition truncate"
                          data-testid="trip-picker-option"
                        >
                          {trip.title} · {trip.destination}
                        </button>
                      ))}
                    </>
                  )}
                  <button
                    onClick={() => setAddState("idle")}
                    className="text-[10px] text-cream-600 hover:text-cream-400 transition"
                  >
                    Cancel
                  </button>
                </div>
              )}

              {addState === "adding" && (
                <div className="flex items-center gap-1.5 text-xs text-cream-500 py-1">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Adding to trip…
                </div>
              )}

              {addState === "added" && (
                <div className="space-y-1">
                  <div
                    className="flex items-center gap-1.5 text-xs text-brand-400"
                    data-testid="add-to-trip-success"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Added to {addedToTripName}
                  </div>
                  <button
                    onClick={() => setAddState("idle")}
                    className="text-[10px] text-cream-600 hover:text-cream-400 transition"
                  >
                    Add to another trip
                  </button>
                </div>
              )}

              {addState === "error" && (
                <div className="space-y-1">
                  <p className="text-xs text-rose-400" data-testid="add-to-trip-error">
                    {addError}
                  </p>
                  <button
                    onClick={() => setAddState("idle")}
                    className="text-[10px] text-cream-500 hover:text-cream-300 transition"
                  >
                    Try again
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Remove error */}
          {removeError && (
            <p className="text-xs text-rose-400 mt-1" data-testid="remove-error">
              {removeError}
            </p>
          )}
        </div>
      </div>
    </div>
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

  const { icon: Icon, iconColor, label, key } = config;

  return (
    <section data-testid={`saved-group-${key}`}>
      <div className="flex items-center gap-2 mb-3">
        <Icon className={`w-4 h-4 ${iconColor}`} />
        <h2 className="text-sm font-semibold text-cream-200 uppercase tracking-wide">
          {label}
        </h2>
        <span className="text-xs text-cream-600 font-medium">{items.length}</span>
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
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-8" data-testid="saved-shell">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-brand-500/10 text-brand-400 flex items-center justify-center">
          <Bookmark className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-cream-100">Saved Ideas</h1>
          <p className="text-xs text-cream-500">Your pre-trip inspiration board.</p>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div
          className="flex items-center justify-center py-16 text-cream-500"
          data-testid="saved-loading"
        >
          <Loader2 className="w-6 h-6 animate-spin mr-2" />
          <span className="text-sm">Loading your saved ideas…</span>
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div
          className="flex flex-col items-center gap-3 py-12 text-center"
          data-testid="saved-error"
        >
          <AlertCircle className="w-8 h-8 text-rose-400" />
          <p className="text-sm text-cream-400">{error}</p>
          <button
            onClick={load}
            className="px-4 py-2 rounded-lg bg-white/[.06] text-cream-300 text-sm hover:bg-white/[.10] transition"
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
          <div className="w-14 h-14 rounded-2xl bg-brand-500/10 text-brand-400 flex items-center justify-center">
            <Bookmark className="w-7 h-7" />
          </div>
          <div>
            <p className="text-base font-semibold text-cream-200">Nothing saved yet</p>
            <p className="text-sm text-cream-500 mt-1">
              Explore restaurants, attractions, and hotels — then save the ones that inspire you.
            </p>
          </div>
          <Link
            href="/explore"
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-500 text-dark-50 text-sm font-medium hover:bg-brand-600 transition"
            data-testid="saved-empty-explore-link"
          >
            <Compass className="w-4 h-4" />
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
