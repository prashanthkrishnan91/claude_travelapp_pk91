"use client";

/**
 * ResultActionSheet — Stage 3 exit cleanup
 *
 * Shared action surface for Explore result cards. Save/Unsave is wired here.
 * Adding to or creating a trip happens from Saved (`/saved`), not directly
 * from Explore. The expanded section shows accurate guidance and (after save)
 * a link to manage the item in Saved.
 */

import { useState } from "react";
import Link from "next/link";
import { Bookmark, BookmarkCheck, PlusCircle, Loader2, ChevronDown, ChevronUp, ArrowRight } from "lucide-react";
import { saveItem, deleteSavedItem } from "@/lib/api";
import type { SavedItemCreate, SavedItem } from "@/types";
import type { ExploreResultContext } from "./types";

export interface ResultActionSheetProps {
  context: ExploreResultContext;
  /** Initial saved state if the caller already knows the saved item */
  initialSavedItem?: SavedItem | null;
}

type ActionState = "idle" | "saving" | "saved" | "error";

/** Map ExploreVertical (plural) → SavedItemVertical (singular). */
const VERTICAL_MAP: Record<string, SavedItemCreate["vertical"]> = {
  restaurants: "restaurant",
  attractions: "attraction",
  hotels: "hotel",
  flights: "flight",
};

/**
 * Build a SavedItemCreate payload from an ExploreResultContext.
 * Keeps vertical-specific context in search_context without mixing hotel/flight fields.
 */
function buildSavePayload(ctx: ExploreResultContext): SavedItemCreate {
  const payload = ctx.originalPayload as Record<string, unknown>;
  const savedVertical = VERTICAL_MAP[ctx.vertical] ?? "restaurant";

  const displayName =
    (payload["name"] as string | undefined) ??
    (payload["title"] as string | undefined) ??
    ctx.destination;

  const displaySnapshot: Record<string, unknown> = {
    name: displayName,
    destination: ctx.destination,
    ...( payload["rating"] !== undefined && { rating: payload["rating"] }),
    ...( payload["cuisine"] !== undefined && { cuisine: payload["cuisine"] }),
    ...( payload["category"] !== undefined && { category: payload["category"] }),
    ...( payload["priceLevel"] !== undefined && { priceLevel: payload["priceLevel"] }),
    ...( payload["address"] !== undefined && { address: payload["address"] }),
    ...( payload["tags"] !== undefined && { tags: payload["tags"] }),
    ...( payload["googleMapsUri"] !== undefined && { googleMapsUri: payload["googleMapsUri"] }),
    // Real routeable metadata from the provider — never geocoded or fabricated.
    // ctx.location carries lat/lng set by the Explore adapter; only written when
    // both are finite numbers (Number.isFinite rejects NaN, Infinity, and non-numbers)
    // so extractItineraryCoordinates can recover them on the Saved → Trip path.
    ...(Number.isFinite(ctx.location?.lat) && Number.isFinite(ctx.location?.lng) && {
      lat: ctx.location!.lat,
      lng: ctx.location!.lng,
    }),
    ...(typeof ctx.providerIdentity === "string" && ctx.providerIdentity && {
      providerPlaceId: ctx.providerIdentity,
    }),
  };

  let searchContext: Record<string, unknown> = { destination: ctx.destination };

  if (ctx.vertical === "hotels") {
    searchContext = {
      destination: ctx.destination,
      ...(ctx.dates?.checkIn && { checkIn: ctx.dates.checkIn }),
      ...(ctx.dates?.checkOut && { checkOut: ctx.dates.checkOut }),
      ...(ctx.guests !== undefined && { guests: ctx.guests }),
      ...(ctx.rooms !== undefined && { rooms: ctx.rooms }),
    };
  } else if (ctx.vertical === "flights") {
    searchContext = {
      origin: ctx.origin,
      destination: ctx.destination,
      ...(ctx.dates?.departure && { departureDate: ctx.dates.departure }),
      ...(ctx.dates?.returnDate && { returnDate: ctx.dates.returnDate }),
      ...(ctx.passengers !== undefined && { passengers: ctx.passengers }),
      ...(ctx.cabinClass && { cabinClass: ctx.cabinClass }),
    };
  }

  const provenance: Record<string, unknown> = {
    source: "explore_shell",
    vertical: ctx.vertical,
    savedAt: new Date().toISOString(),
  };

  const provider = ctx.providerIdentity ? "google_places" : undefined;
  const providerPlaceId = ctx.providerIdentity ?? undefined;

  return {
    vertical: savedVertical,
    displayName,
    provider,
    providerPlaceId,
    displaySnapshot,
    searchContext,
    provenance,
  };
}

export function ResultActionSheet({ context, initialSavedItem }: ResultActionSheetProps) {
  const [actionState, setActionState] = useState<ActionState>(
    initialSavedItem ? "saved" : "idle"
  );
  const [savedItemId, setSavedItemId] = useState<string | null>(
    initialSavedItem?.id ?? null
  );
  const [expanded, setExpanded] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  async function handleSave() {
    if (actionState === "saving") return;
    setActionState("saving");
    setErrorMsg(null);
    try {
      const payload = buildSavePayload(context);
      const saved = await saveItem(payload);
      setSavedItemId(saved.id);
      setActionState("saved");
    } catch {
      setActionState("error");
      setErrorMsg("Save failed. Please try again.");
    }
  }

  async function handleUnsave() {
    if (!savedItemId || actionState === "saving") return;
    setActionState("saving");
    setErrorMsg(null);
    try {
      await deleteSavedItem(savedItemId);
      setSavedItemId(null);
      setActionState("idle");
    } catch {
      setActionState("error");
      setErrorMsg("Could not remove saved item. Please try again.");
    }
  }

  const isSaved = actionState === "saved";
  const isLoading = actionState === "saving";

  return (
    <div data-testid="result-action-sheet">
      {/* Compact trigger row */}
      <div className="flex items-center gap-2">
        {/* Save / Unsave */}
        <button
          type="button"
          onClick={isSaved ? handleUnsave : handleSave}
          disabled={isLoading}
          aria-label={isSaved ? "Remove from saved" : "Save"}
          className={[
            "flex items-center gap-1.5 px-3 py-1.5 min-h-[44px] rounded-lg text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2",
            isSaved
              ? "text-ds-accent hover:text-ds-accent-muted"
              : "bg-ds-carbon text-ds-text-tertiary hover:bg-ds-pen-stroke hover:text-ds-text-secondary",
            isLoading ? "opacity-60 cursor-not-allowed" : "",
          ].join(" ")}
          style={isSaved ? { backgroundColor: "var(--ds-accent-subtle)" } : undefined}
          data-testid="save-action-btn"
        >
          {isLoading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : isSaved ? (
            <BookmarkCheck className="w-3.5 h-3.5" />
          ) : (
            <Bookmark className="w-3.5 h-3.5" />
          )}
          {isSaved ? "Saved" : "Save"}
        </button>

        {/* More actions toggle */}
        <button
          type="button"
          onClick={() => setExpanded((v: boolean) => !v)}
          aria-label={expanded ? "Hide actions" : "More actions"}
          className="flex items-center gap-1 px-2 py-1.5 min-h-[44px] rounded-lg text-xs text-ds-text-tertiary bg-ds-carbon hover:bg-ds-pen-stroke hover:text-ds-text-secondary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
          data-testid="more-actions-toggle"
        >
          <PlusCircle className="w-3.5 h-3.5" />
          More
          {expanded ? (
            <ChevronUp className="w-3 h-3" />
          ) : (
            <ChevronDown className="w-3 h-3" />
          )}
        </button>
      </div>

      {/* Expanded guidance — Add/Create happen from Saved, not Explore */}
      {expanded && (
        <div className="mt-2 flex flex-col gap-1.5" data-testid="trip-actions-guidance">
          {isSaved ? (
            <Link
              href="/saved"
              className="flex items-center gap-2 px-3 py-2 min-h-[44px] rounded-lg text-xs text-ds-text-secondary bg-ds-carbon hover:bg-ds-pen-stroke transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
              aria-label="Manage in Saved"
              data-testid="manage-in-saved-link"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              Manage in Saved
              <ArrowRight className="w-3.5 h-3.5 ml-auto" />
            </Link>
          ) : (
            <p
              className="px-3 py-2 rounded-lg text-xs text-ds-text-tertiary bg-ds-midnight leading-snug"
              data-testid="save-first-hint"
            >
              Save first to add or create a trip from Saved.
            </p>
          )}
        </div>
      )}

      {/* Error feedback */}
      {actionState === "error" && errorMsg && (
        <p className="mt-1.5 text-xs text-ds-warning" data-testid="action-error">
          {errorMsg}
        </p>
      )}
    </div>
  );
}
