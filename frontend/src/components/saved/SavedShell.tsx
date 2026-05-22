"use client";

import { useState, useEffect, useCallback, useMemo, type CSSProperties } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Bookmark,
  Utensils,
  Landmark,
  Building2,
  Plane,
  Trash2,
  MapPin,
  Compass,
  Loader2,
  AlertCircle,
  Calendar,
  Users,
  PlusCircle,
  CheckCircle2,
  Sparkles,
  Check,
  GitCompare,
  X,
} from "lucide-react";
import { listSavedItems, deleteSavedItem, fetchTrips, addSavedItemToTrip } from "@/lib/api";
import type { SavedItem, SavedItemVertical, Trip } from "@/types";
import { CreateTripFromSavedModal } from "./CreateTripFromSavedModal";

// ── Vertical config ───────────────────────────────────────────────────────────

const VERTICAL_CONFIG = [
  { key: "restaurant" as SavedItemVertical, label: "Restaurants", icon: Utensils },
  { key: "attraction" as SavedItemVertical, label: "Attractions", icon: Landmark },
  { key: "hotel" as SavedItemVertical, label: "Hotels", icon: Building2 },
  { key: "flight" as SavedItemVertical, label: "Flights", icon: Plane },
] as const;

type VerticalCfg = (typeof VERTICAL_CONFIG)[number];

const CONFIG_BY_KEY: Record<SavedItemVertical, VerticalCfg> = {
  restaurant: VERTICAL_CONFIG[0],
  attraction: VERTICAL_CONFIG[1],
  hotel: VERTICAL_CONFIG[2],
  flight: VERTICAL_CONFIG[3],
};

// Overline type labels for dossier card identity (§8C TYPE_LABELS pattern)
const TYPE_OVERLINES: Record<SavedItemVertical, string> = {
  restaurant: "Restaurant",
  attraction: "Attraction",
  hotel: "Hotel",
  flight: "Flight",
};

// Place verticals can be compared and added to an existing trip; flights cannot.
const PLACE_VERTICALS: SavedItemVertical[] = ["restaurant", "attraction", "hotel"];
const COMPARE_MAX = 4;

// Grouping modes. "day" is intentionally absent — saved items are not assigned
// to trip days until they are added to a trip, so there is no real day data to
// group by. We surface it as a disabled control rather than fabricate buckets.
type GroupMode = "recent" | "city" | "category";

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

// Source provenance → honest origin label. Only the two real sources are
// labelled; anything else (legacy rows) is omitted rather than guessed.
function sourceLabel(item: SavedItem): string | null {
  const s = item.provenance?.["source"];
  if (s === "outside_concierge") return "From Concierge";
  if (s === "explore_shell") return "From Explore";
  return null;
}

// "Saved context" is the real search query the user typed when the item was
// saved (concierge rows carry searchContext.query). Never fabricated; omitted
// when no query was recorded. Surfaced under the "Saved context" label.
function whyItMattered(item: SavedItem): string | null {
  return ctxStr(item, "query");
}

function cityOf(item: SavedItem): string {
  return snapStr(item, "destination") ?? ctxStr(item, "destination") ?? "Elsewhere";
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

// ── Planning bridge (Add to Trip / Create Trip state machine) ─────────────────

function PlanningBridge({
  item,
  trips,
  canAddToTrip,
  onCreateTrip,
}: {
  item: SavedItem;
  trips: Trip[];
  canAddToTrip: boolean;
  onCreateTrip: (item: SavedItem) => void;
}) {
  const [addState, setAddState] = useState<AddState>("idle");
  const [addedToTripName, setAddedToTripName] = useState<string | null>(null);
  const [addError, setAddError] = useState<string | null>(null);

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
    <div className="folio-dossier-actions" data-testid="saved-planning-bridge">
      <p className="folio-muted-overline">Plan with this</p>

      {/* Idle: Add to Trip is the primary CTA; Create Trip is the ghost path. */}
      <div className="folio-action-row">
        {/* Add to Trip — primary, non-flight verticals only */}
        {canAddToTrip && addState === "idle" && (
          <div data-testid="add-to-trip-section" className="contents">
            <button
              type="button"
              onClick={() => setAddState("picking")}
              className="folio-btn-primary min-h-[44px]"
              data-testid="add-to-trip-btn"
            >
              <PlusCircle className="w-3.5 h-3.5" aria-hidden="true" />
              Add to Trip
            </button>
          </div>
        )}

        {/* Create Trip — all verticals (the only planning path for flights) */}
        <div data-testid="create-trip-section" className="contents">
          <button
            type="button"
            onClick={() => onCreateTrip(item)}
            className="folio-btn-ghost min-h-[44px]"
            data-testid="create-trip-btn"
          >
            <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
            Create Trip
          </button>
        </div>
      </div>

      {/* Add to Trip — non-idle states */}
      {canAddToTrip && addState !== "idle" && (
        <div data-testid="add-to-trip-section" className="mt-2">
          {addState === "picking" && (
            <div className="space-y-1" data-testid="trip-picker">
              {trips.length === 0 ? (
                <p className="text-xs text-ds-folio-ink-mist py-1">
                  No trips yet.{" "}
                  <Link
                    href="/trips/new"
                    className="text-ds-marine-ink underline hover:opacity-70 transition-opacity"
                  >
                    Create one
                  </Link>
                </p>
              ) : (
                <>
                  <p className="folio-muted-overline">Choose a trip</p>
                  {trips.map((trip) => (
                    <button
                      type="button"
                      key={trip.id}
                      onClick={() => handleAddToTrip(trip)}
                      className="min-h-[44px] w-full text-left px-3 py-1.5 rounded-lg text-xs text-ds-folio-ink bg-ds-bone border border-ds-hairline hover:border-ds-marine-ink transition-colors truncate focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2"
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
                className="min-h-[44px] flex items-center text-[10px] text-ds-folio-ink-mist hover:text-ds-folio-ink transition-colors"
              >
                Cancel
              </button>
            </div>
          )}

          {addState === "adding" && (
            <div className="flex items-center gap-1.5 text-xs text-ds-folio-ink-mist py-1">
              <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
              Adding to trip…
            </div>
          )}

          {addState === "added" && (
            <div className="space-y-1">
              <div
                className="flex items-center gap-1.5 text-xs text-ds-folio-ink"
                data-testid="add-to-trip-success"
              >
                <CheckCircle2 className="w-3.5 h-3.5 text-ds-trust-verified" aria-hidden="true" />
                Added to {addedToTripName}
              </div>
              <button
                type="button"
                onClick={() => setAddState("idle")}
                className="min-h-[44px] flex items-center text-[10px] text-ds-folio-ink-mist hover:text-ds-folio-ink transition-colors"
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
                className="min-h-[44px] flex items-center text-[10px] text-ds-folio-ink-mist hover:text-ds-folio-ink transition-colors"
              >
                Try again
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Place dossier card (restaurant / attraction / hotel) ──────────────────────

function PlaceDossierCard({
  item,
  trips,
  picked,
  compareFull,
  onTogglePick,
  onRemove,
  onCreateTrip,
}: {
  item: SavedItem;
  trips: Trip[];
  picked: boolean;
  compareFull: boolean;
  onTogglePick: (id: string) => void;
  onRemove: (id: string) => void;
  onCreateTrip: (item: SavedItem) => void;
}) {
  const [removing, setRemoving] = useState(false);
  const [removeError, setRemoveError] = useState<string | null>(null);

  const cfg = CONFIG_BY_KEY[item.vertical];
  const { icon: Icon } = cfg;

  const name = snapStr(item, "name") ?? item.displayName;
  const address = snapStr(item, "address");
  const destination = snapStr(item, "destination") ?? ctxStr(item, "destination");
  const rating = snapNum(item, "rating");
  const googleMapsUri = snapStr(item, "googleMapsUri");
  const tagList = snapTags(item);
  const source = sourceLabel(item);
  const why = whyItMattered(item);

  const cuisine = item.vertical === "restaurant" ? snapStr(item, "cuisine") : null;
  const priceLevel = item.vertical === "restaurant" ? snapNum(item, "priceLevel") : null;
  const priceStr = priceLevel != null ? "$".repeat(Math.min(priceLevel, 4)) : null;

  const checkIn = item.vertical === "hotel" ? ctxStr(item, "checkIn") : null;
  const checkOut = item.vertical === "hotel" ? ctxStr(item, "checkOut") : null;
  const guests = item.vertical === "hotel" ? ctxNum(item, "guests") : null;

  const savedDate = formatSavedDate(item.createdAt);
  const where = address ?? destination;

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

  return (
    <article
      className="folio-dossier-card"
      data-testid="saved-item-card"
      data-picked={picked ? "true" : "false"}
    >
      <>
        {/* Typeset plate — no fabricated photo. Carries the category glyph, a
            vertical source spine tab, and (when selected) an in-compare flag.
            The only compare *control* is the bottom action-row icon. */}
        <div className="folio-dossier-plate" aria-hidden="true">
          {source && <span className="folio-source-tab">{source}</span>}
          <Icon className="folio-plate-glyph" />
          {picked && (
            <span className="folio-compare-flag">
              <Check className="w-3 h-3" aria-hidden="true" />
              In compare
            </span>
          )}
        </div>

        <div className="folio-dossier-body">
          <p
            className="folio-type-overline"
            data-testid="saved-item-type-overline"
          >
            {TYPE_OVERLINES[item.vertical]}
          </p>

          <h3 className="folio-dossier-name" data-testid="saved-item-name">
            {name}
          </h3>

          {where && (
            <p className="folio-dossier-where">
              <MapPin className="w-3 h-3 shrink-0" aria-hidden="true" />
              <span className="truncate">
                {[cuisine, where].filter(Boolean).join(" · ")}
              </span>
            </p>
          )}

          {/* Saved context — the real saved search query; omitted when absent.
              (Source — From Concierge / From Explore — is shown on the plate's
              spine tab.) Never an invented note. */}
          {why && (
            <p className="folio-dossier-why" data-testid="saved-item-why">
              <span className="folio-why-label">Saved context</span>
              {why}
            </p>
          )}

          {/* Real provider facts — rating / price / tags. Omitted when missing. */}
          {(rating != null || priceStr || tagList.length > 0) && (
            <div className="flex items-center gap-2 flex-wrap">
              {rating != null && (
                <span
                  className="flex items-center gap-0.5 text-xs text-ds-folio-ink font-medium"
                  data-testid="saved-card-rating"
                >
                  <span className="text-ds-sandstone-gold" aria-hidden="true">★</span>
                  {rating.toFixed(1)}
                </span>
              )}
              {priceStr && (
                <span className="text-xs text-ds-folio-ink-mist font-medium">{priceStr}</span>
              )}
              {tagList.length > 0 && (
                <div className="flex gap-1 flex-wrap">
                  {tagList.slice(0, 3).map((tag) => (
                    <span key={tag} className="folio-tag-chip">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Hotel: dates + guests from search context — discovery only, no rates */}
          {item.vertical === "hotel" && (checkIn || checkOut || guests != null) && (
            <div className="flex items-center gap-3 flex-wrap" data-testid="hotel-search-context">
              {(checkIn || checkOut) && (
                <span className="flex items-center gap-1 text-xs text-ds-folio-ink-mist">
                  <Calendar className="w-3 h-3" aria-hidden="true" />
                  {[checkIn, checkOut].filter(Boolean).join(" → ")}
                </span>
              )}
              {guests != null && (
                <span className="flex items-center gap-1 text-xs text-ds-folio-ink-mist">
                  <Users className="w-3 h-3" aria-hidden="true" />
                  {guests} {guests === 1 ? "guest" : "guests"}
                </span>
              )}
            </div>
          )}

          <p className="folio-saved-date">Saved {savedDate}</p>

          <PlanningBridge
            item={item}
            trips={trips}
            canAddToTrip
            onCreateTrip={onCreateTrip}
          />

          {/* Secondary icon actions: Map, Compare, Remove */}
          <div className="folio-icon-row">
            {googleMapsUri && (
              <a
                href={googleMapsUri}
                target="_blank"
                rel="noopener noreferrer"
                className="folio-icon-btn min-w-[44px] min-h-[44px]"
                aria-label={`View ${name} on Google Maps`}
              >
                <MapPin className="w-4 h-4" aria-hidden="true" />
              </a>
            )}
            <button
              type="button"
              onClick={() => onTogglePick(item.id)}
              disabled={compareFull && !picked}
              aria-pressed={picked}
              aria-label={picked ? `Remove ${name} from compare` : `Compare ${name}`}
              className="folio-icon-btn folio-compare-toggle min-w-[44px] min-h-[44px]"
              data-picked={picked ? "true" : "false"}
              data-testid="compare-icon-btn"
            >
              {picked ? (
                <Check className="w-4 h-4" aria-hidden="true" />
              ) : (
                <GitCompare className="w-4 h-4" aria-hidden="true" />
              )}
            </button>
            <button
              type="button"
              onClick={handleRemove}
              disabled={removing}
              aria-label={`Remove ${name} from saved`}
              className="folio-icon-btn folio-icon-danger min-w-[44px] min-h-[44px]"
              data-testid="remove-saved-btn"
            >
              {removing ? (
                <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
              ) : (
                <Trash2 className="w-4 h-4" aria-hidden="true" />
              )}
            </button>
          </div>

          {removeError && (
            <p className="text-xs text-ds-warning mt-1" data-testid="remove-error">
              {removeError}
            </p>
          )}
        </div>
      </>
    </article>
  );
}

// ── Dedicated flight card (boarding-pass layout, no plate spine) ──────────────

function FlightCard({
  item,
  onRemove,
  onCreateTrip,
}: {
  item: SavedItem;
  onRemove: (id: string) => void;
  onCreateTrip: (item: SavedItem) => void;
}) {
  const [removing, setRemoving] = useState(false);
  const [removeError, setRemoveError] = useState<string | null>(null);

  const name = snapStr(item, "name") ?? item.displayName;
  const origin = ctxStr(item, "origin");
  const destination = ctxStr(item, "destination") ?? snapStr(item, "destination");
  const departureDate = ctxStr(item, "departureDate");
  const returnDate = ctxStr(item, "returnDate");
  const cabin = ctxStr(item, "cabinClass");
  const passengers = ctxNum(item, "passengers");
  const source = sourceLabel(item);
  const savedDate = formatSavedDate(item.createdAt);

  const dateLine = [departureDate, returnDate].filter(Boolean).join(" → ");
  const detailLine = [
    cabin,
    passengers != null ? `${passengers} ${passengers === 1 ? "traveller" : "travellers"}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

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

  return (
    <article
      className="folio-flight-card"
      data-testid="saved-item-card"
      data-flight-card="true"
    >
      <>
        {/* Full-width route band — codes never crop, wrap, or fight a source rail */}
        <div className="folio-flight-band" data-testid="flight-route-band">
          <span className="folio-flight-ap">{origin ?? "—"}</span>
          <span className="folio-flight-path" aria-hidden="true">
            <Plane className="w-3.5 h-3.5" />
          </span>
          <span className="folio-flight-ap">{destination ?? "—"}</span>
        </div>

        <div className="folio-dossier-body">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="folio-type-overline" data-testid="saved-item-type-overline">
              {TYPE_OVERLINES.flight}
            </p>
            {source && <span className="folio-source-chip">{source}</span>}
          </div>

          <h3 className="folio-dossier-name" data-testid="saved-item-name">
            {name}
          </h3>

          {dateLine && (
            <p className="folio-dossier-where">
              <Calendar className="w-3 h-3 shrink-0" aria-hidden="true" />
              <span className="truncate">{dateLine}</span>
            </p>
          )}
          {detailLine && <p className="folio-saved-date">{detailLine}</p>}

          <p className="folio-saved-date">Saved {savedDate}</p>

          {/* Flights are not addable to an existing trip and have no map; their
              real planning path is Create Trip. No Compare for flights. */}
          <div className="folio-dossier-actions" data-testid="saved-planning-bridge">
            <p className="folio-muted-overline">Plan with this</p>
            <div className="folio-action-row">
              <div data-testid="create-trip-section" className="contents">
                <button
                  type="button"
                  onClick={() => onCreateTrip(item)}
                  className="folio-btn-primary min-h-[44px]"
                  data-testid="create-trip-btn"
                >
                  <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
                  Create Trip
                </button>
              </div>
              <button
                type="button"
                onClick={handleRemove}
                disabled={removing}
                aria-label={`Remove ${name} from saved`}
                className="folio-icon-btn folio-icon-danger min-w-[44px] min-h-[44px]"
                data-testid="remove-saved-btn"
              >
                {removing ? (
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                ) : (
                  <Trash2 className="w-4 h-4" aria-hidden="true" />
                )}
              </button>
            </div>
          </div>

          {removeError && (
            <p className="text-xs text-ds-warning mt-1" data-testid="remove-error">
              {removeError}
            </p>
          )}
        </div>
      </>
    </article>
  );
}

// ── Card dispatcher ───────────────────────────────────────────────────────────

function SavedItemCard(props: {
  item: SavedItem;
  trips: Trip[];
  picked: boolean;
  compareFull: boolean;
  onTogglePick: (id: string) => void;
  onRemove: (id: string) => void;
  onCreateTrip: (item: SavedItem) => void;
}) {
  // Flights are not addable to an existing trip (no leg-splitting from Saved),
  // so they use the dedicated boarding-pass card whose only planning path is
  // Create Trip. Place verticals can be added to a trip.
  const canAddToTrip = props.item.vertical !== "flight";
  if (!canAddToTrip) {
    return (
      <FlightCard item={props.item} onRemove={props.onRemove} onCreateTrip={props.onCreateTrip} />
    );
  }
  return <PlaceDossierCard {...props} />;
}

// ── Compare tray + sheet ──────────────────────────────────────────────────────

function CompareTray({
  items,
  onOpen,
  onRemove,
}: {
  items: SavedItem[];
  onOpen: () => void;
  onRemove: (id: string) => void;
}) {
  if (items.length === 0) return null;
  const ready = items.length >= 2;
  return (
    <div className="folio-compare-tray" data-testid="compare-tray" role="region" aria-label="Compare shortlist">
      <span className="folio-compare-label">Compare</span>
      <div className="folio-compare-thumbs">
        {items.map((it) => {
          const cfg = CONFIG_BY_KEY[it.vertical];
          const Icon = cfg.icon;
          return (
            <span key={it.id} className="folio-compare-thumb">
              <Icon className="w-4 h-4" aria-hidden="true" />
              <button
                type="button"
                className="folio-compare-thumb-x"
                aria-label={`Remove ${snapStr(it, "name") ?? it.displayName} from compare`}
                onClick={() => onRemove(it.id)}
              >
                <X className="w-3 h-3" aria-hidden="true" />
              </button>
            </span>
          );
        })}
        {items.length < 2 && <span className="folio-compare-thumb folio-compare-thumb-empty" aria-hidden="true" />}
      </div>
      <button
        type="button"
        className="folio-btn-primary folio-compare-open"
        disabled={!ready}
        onClick={onOpen}
        data-testid="compare-open-btn"
      >
        {ready ? `Compare ${items.length}` : "Pick 2+"}
      </button>
    </div>
  );
}

function CompareSheet({
  items,
  onClose,
}: {
  items: SavedItem[];
  onClose: () => void;
}) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="folio-compare-scrim"
      data-testid="compare-sheet"
      role="dialog"
      aria-modal="true"
      aria-label="Compare saved places"
      onClick={onClose}
    >
      <div
        className="folio-compare-sheet"
        style={{ "--cols": String(items.length) } as CSSProperties}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="folio-compare-sheet-head">
          <div>
            <p className="folio-muted-overline">Side by side</p>
            <h2 className="folio-dossier-name">Your shortlist</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="folio-icon-btn"
            aria-label="Close compare"
            data-testid="compare-close-btn"
          >
            <X className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
        <p className="folio-saved-date">Only the facts you saved — nothing invented.</p>

        <div className="folio-compare-grid">
          {items.map((it) => {
            const cfg = CONFIG_BY_KEY[it.vertical];
            const Icon = cfg.icon;
            const name = snapStr(it, "name") ?? it.displayName;
            const where = snapStr(it, "address") ?? snapStr(it, "destination") ?? ctxStr(it, "destination");
            const rating = snapNum(it, "rating");
            const source = sourceLabel(it);
            const savedQuery = whyItMattered(it);
            return (
              <div key={it.id} className="folio-compare-col" data-testid="compare-col">
                <div className="folio-compare-col-plate" aria-hidden="true">
                  <Icon className="folio-plate-glyph" />
                </div>
                <div className="folio-compare-col-body">
                  <p className="folio-type-overline">{TYPE_OVERLINES[it.vertical]}</p>
                  <h3 className="folio-dossier-name">{name}</h3>
                  {where && (
                    <div className="folio-compare-row">
                      <span className="folio-compare-row-k">Where</span>
                      {where}
                    </div>
                  )}
                  {/* Two honest saved datapoints: provenance source, and the
                      saved search query. Each shown only when present; never an
                      invented note. */}
                  {source && (
                    <div className="folio-compare-row" data-testid="compare-source">
                      <span className="folio-compare-row-k">Source</span>
                      {source}
                    </div>
                  )}
                  {savedQuery && (
                    <div className="folio-compare-row" data-testid="compare-note">
                      <span className="folio-compare-row-k">Saved context</span>
                      {savedQuery}
                    </div>
                  )}
                  {rating != null && (
                    <div className="folio-compare-row">
                      <span className="folio-compare-row-k">Rating</span>
                      {rating.toFixed(1)} ★
                    </div>
                  )}
                  <div className="folio-compare-row">
                    <span className="folio-compare-row-k">Saved</span>
                    {formatSavedDate(it.createdAt)}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── Group section ─────────────────────────────────────────────────────────────

function GroupSection({
  label,
  testKey,
  items,
  trips,
  compareIds,
  compareFull,
  onTogglePick,
  onRemove,
  onCreateTrip,
}: {
  label: string | null;
  testKey: string;
  items: SavedItem[];
  trips: Trip[];
  compareIds: Set<string>;
  compareFull: boolean;
  onTogglePick: (id: string) => void;
  onRemove: (id: string) => void;
  onCreateTrip: (item: SavedItem) => void;
}) {
  if (items.length === 0) return null;
  return (
    <section data-testid={`saved-section-${testKey}`} aria-label={label ? `${label}` : "Saved"}>
      {label && (
        <div className="folio-group-head">
          <p
            className="folio-group-label"
            data-testid={`saved-section-label-${testKey}`}
          >
            {label}
          </p>
          <span className="folio-group-line" aria-hidden="true" />
          <span className="folio-group-count tabular-nums">{items.length}</span>
        </div>
      )}
      <div className="folio-card-grid">
        {items.map((item) => (
          <SavedItemCard
            key={item.id}
            item={item}
            trips={trips}
            picked={compareIds.has(item.id)}
            compareFull={compareFull}
            onTogglePick={onTogglePick}
            onRemove={onRemove}
            onCreateTrip={onCreateTrip}
          />
        ))}
      </div>
    </section>
  );
}

// ── Canonical view pipeline ───────────────────────────────────────────────────

type VisibleGroup = { label: string | null; key: string; items: SavedItem[] };

/**
 * visibleGroups = applyGrouping(applyFilter(allSavedItems, activeFilter), activeGroup)
 *
 * The visible collection is ALWAYS derived fresh from the full saved-items
 * array — filter first, then group. It never reads from a previously filtered
 * or grouped result, so switching filter/group can never leave stale remnants
 * and no refresh is ever required to reset state.
 */
function buildVisibleGroups(
  all: SavedItem[],
  activeCat: "all" | SavedItemVertical,
  groupMode: GroupMode,
): VisibleGroup[] {
  const filtered = activeCat === "all" ? all : all.filter((i) => i.vertical === activeCat);

  if (groupMode === "category") {
    return VERTICAL_CONFIG.map((cfg) => ({
      label: cfg.label,
      key: cfg.key as string,
      items: filtered.filter((i) => i.vertical === cfg.key),
    })).filter((g) => g.items.length > 0);
  }

  if (groupMode === "city") {
    const byCity = new Map<string, SavedItem[]>();
    for (const it of filtered) {
      const city = cityOf(it);
      if (!byCity.has(city)) byCity.set(city, []);
      byCity.get(city)!.push(it);
    }
    return Array.from(byCity.entries())
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([city, list]) => ({
        label: city,
        key: city.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
        items: list,
      }));
  }

  // recent — newest first, single ungrouped section
  const sorted = [...filtered].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
  return [{ label: null, key: "recent", items: sorted }];
}

// ── SavedShell ─────────────────────────────────────────────────────────────────

export function SavedShell() {
  const router = useRouter();
  const [items, setItems] = useState<SavedItem[]>([]);
  const [trips, setTrips] = useState<Trip[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createTripFor, setCreateTripFor] = useState<SavedItem | null>(null);

  const [activeCat, setActiveCat] = useState<"all" | SavedItemVertical>("all");
  const [groupMode, setGroupMode] = useState<GroupMode>("recent");
  const [compareIds, setCompareIds] = useState<Set<string>>(new Set());
  const [compareOpen, setCompareOpen] = useState(false);

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
    setCompareIds((prev) => {
      if (!prev.has(id)) return prev;
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }, []);

  const handleCreateTrip = useCallback((item: SavedItem) => {
    setCreateTripFor(item);
  }, []);

  const compareFull = compareIds.size >= COMPARE_MAX;

  const handleTogglePick = useCallback(
    (id: string) => {
      setCompareIds((prev) => {
        const next = new Set(prev);
        if (next.has(id)) {
          next.delete(id);
        } else {
          // Places only, capped at COMPARE_MAX.
          const item = items.find((i) => i.id === id);
          if (!item || !PLACE_VERTICALS.includes(item.vertical)) return prev;
          if (next.size >= COMPARE_MAX) return prev;
          next.add(id);
        }
        return next;
      });
    },
    [items],
  );

  // Category counts from the full active set (not the filtered view).
  const counts = useMemo(() => {
    const c: Record<string, number> = { all: items.length };
    for (const cfg of VERTICAL_CONFIG) c[cfg.key] = 0;
    for (const it of items) c[it.vertical] = (c[it.vertical] ?? 0) + 1;
    return c;
  }, [items]);

  // Canonical: derive the visible groups fresh from the full `items` array on
  // every filter/group change (filter → group). No intermediate state is reused.
  const visibleGroups = useMemo(
    () => buildVisibleGroups(items, activeCat, groupMode),
    [items, activeCat, groupMode],
  );

  const compareItems = useMemo(
    () => items.filter((i) => compareIds.has(i.id)),
    [items, compareIds],
  );

  const hasAny = items.length > 0;

  const GROUP_OPTIONS: { key: GroupMode | "day"; label: string; disabled?: boolean }[] = [
    { key: "recent", label: "Recent" },
    { key: "city", label: "City" },
    { key: "category", label: "Category" },
    // Day has no real backing data for saved (unassigned to trip days).
    { key: "day", label: "Day", disabled: true },
  ];

  return (
    <div className="folio-private-desk" data-testid="saved-shell" data-folio-world="paper">
      <div className="folio-private-folio">
        <span className="folio-private-meridian" aria-hidden="true" />

        <div className="folio-private-grid">
          {/* Left leaf — header + filters + grouping (the rail on desktop) */}
          <div className="folio-private-rail">
            <header data-testid="saved-scrapbook-header" className="folio-private-head">
              <p
                className="folio-private-eyebrow"
                data-testid="saved-scrapbook-overline"
              >
                Private Folio
              </p>
              <h1
                className="folio-private-title"
                data-testid="saved-scrapbook-heading"
              >
                Places you&rsquo;ve kept
              </h1>
              {!loading && !error && hasAny && (
                <p
                  className="folio-private-sub"
                  data-testid="saved-scrapbook-count"
                >
                  {items.length} {items.length === 1 ? "idea" : "ideas"} in your collection
                </p>
              )}
            </header>

            {!loading && !error && hasAny && (
              <>
                <div className="folio-rail-block">
                  <p className="folio-muted-overline folio-rail-label">Collection</p>
                  <div className="folio-cat-chips" role="group" aria-label="Filter by category">
                    <button
                      type="button"
                      className="folio-cat-chip"
                      data-active={activeCat === "all"}
                      onClick={() => setActiveCat("all")}
                      data-testid="saved-cat-all"
                    >
                      All <span className="folio-cat-count">{counts.all}</span>
                    </button>
                    {VERTICAL_CONFIG.map((cfg) => {
                      const Icon = cfg.icon;
                      const n = counts[cfg.key] ?? 0;
                      if (n === 0) return null;
                      return (
                        <button
                          type="button"
                          key={cfg.key}
                          className="folio-cat-chip"
                          data-active={activeCat === cfg.key}
                          onClick={() => setActiveCat(cfg.key)}
                          data-testid={`saved-cat-${cfg.key}`}
                        >
                          <Icon className="w-3.5 h-3.5" aria-hidden="true" />
                          {cfg.label} <span className="folio-cat-count">{n}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="folio-rail-block">
                  <p className="folio-muted-overline folio-rail-label">Group</p>
                  <div className="folio-group-seg" role="group" aria-label="Group saved items">
                    {GROUP_OPTIONS.map((opt) => (
                      <button
                        type="button"
                        key={opt.key}
                        className="folio-group-seg-btn"
                        data-on={!opt.disabled && groupMode === opt.key}
                        disabled={opt.disabled}
                        aria-disabled={opt.disabled}
                        title={opt.disabled ? "Available once items are placed in a trip" : undefined}
                        onClick={() => !opt.disabled && setGroupMode(opt.key as GroupMode)}
                        data-testid={`saved-group-${opt.key}`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Right leaf — the collection canvas */}
          <div className="folio-private-canvas">
            {loading && (
              <div
                data-testid="saved-loading"
                className="flex items-center justify-center py-16 text-ds-folio-ink-mist"
              >
                <Loader2 className="w-6 h-6 animate-spin mr-2" aria-hidden="true" />
                <span className="text-sm">Loading your saved ideas…</span>
              </div>
            )}

            {!loading && error && (
              <div
                className="flex flex-col items-center gap-3 py-12 text-center"
                data-testid="saved-error"
              >
                <AlertCircle className="w-8 h-8 text-ds-warning" aria-hidden="true" />
                <p className="text-sm text-ds-folio-ink-soft">{error}</p>
                <button
                  type="button"
                  onClick={load}
                  className="folio-btn-ghost min-h-[44px]"
                >
                  Try again
                </button>
              </div>
            )}

            {!loading && !error && !hasAny && (
              <div className="flex flex-col items-center gap-3 py-16 text-center" data-testid="saved-empty">
                <Bookmark className="w-10 h-10 text-ds-sandstone-gold" aria-hidden="true" />
                <p className="text-base font-semibold text-ds-folio-ink">Nothing saved yet</p>
                <Link href="/explore" className="folio-btn-primary min-h-[44px]" data-testid="saved-empty-explore-link">
                  <Compass className="w-4 h-4" aria-hidden="true" />
                  Start Exploring
                </Link>
                <p className="text-sm text-ds-folio-ink-soft max-w-xs">
                  Explore restaurants, attractions, and hotels — then keep the ones that inspire you.
                </p>
              </div>
            )}

            {!loading && !error && hasAny && (
              <div className="folio-collection">
                {visibleGroups.map((g) => (
                  <GroupSection
                    key={`${activeCat}:${groupMode}:${g.key}`}
                    label={g.label}
                    testKey={g.key}
                    items={g.items}
                    trips={trips}
                    compareIds={compareIds}
                    compareFull={compareFull}
                    onTogglePick={handleTogglePick}
                    onRemove={handleRemove}
                    onCreateTrip={handleCreateTrip}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <CompareTray
        items={compareItems}
        onOpen={() => setCompareOpen(true)}
        onRemove={handleTogglePick}
      />

      {compareOpen && compareItems.length >= 2 && (
        <CompareSheet items={compareItems} onClose={() => setCompareOpen(false)} />
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
