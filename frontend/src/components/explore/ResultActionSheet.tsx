"use client";

/**
 * ResultActionSheet — Stage 2A Slice 2
 *
 * Shared action surface for Explore result cards: Save, Add to Trip, Create Trip.
 * Works without a trip context. Save is wired; Add to Trip and Create Trip are
 * present but deferred (disabled with clear copy) until trip-picker and modal
 * wiring lands in a follow-up slice.
 */

import { useState } from "react";
import { Bookmark, BookmarkCheck, PlusCircle, Loader2, ChevronDown, ChevronUp } from "lucide-react";
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
    ...( payload["priceLevel"] !== undefined && { priceLevel: payload["priceLevel"] }),
    ...( payload["address"] !== undefined && { address: payload["address"] }),
    ...( payload["tags"] !== undefined && { tags: payload["tags"] }),
    ...( payload["googleMapsUri"] !== undefined && { googleMapsUri: payload["googleMapsUri"] }),
  };

  let searchContext: Record<string, unknown> = { destination: ctx.destination };

  if (ctx.vertical === "hotels") {
    searchContext = {
      destination: ctx.destination,
      ...(ctx.dates?.checkIn && { checkIn: ctx.dates.checkIn }),
      ...(ctx.dates?.checkOut && { checkOut: ctx.dates.checkOut }),
      ...(ctx.guests !== undefined && { guests: ctx.guests }),
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
    <div className="mt-2" data-testid="result-action-sheet">
      {/* Compact trigger row */}
      <div className="flex items-center gap-2">
        {/* Save / Unsave */}
        <button
          onClick={isSaved ? handleUnsave : handleSave}
          disabled={isLoading}
          aria-label={isSaved ? "Remove from saved" : "Save"}
          className={[
            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition",
            isSaved
              ? "bg-amber-500/15 text-amber-400 hover:bg-amber-500/25"
              : "bg-white/[.06] text-cream-400 hover:bg-white/[.10]",
            isLoading ? "opacity-60 cursor-not-allowed" : "",
          ].join(" ")}
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
          onClick={() => setExpanded((v: boolean) => !v)}
          aria-label={expanded ? "Hide actions" : "More actions"}
          className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs text-cream-500 bg-white/[.04] hover:bg-white/[.08] transition"
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

      {/* Expanded deferred actions */}
      {expanded && (
        <div className="mt-2 flex flex-col gap-1.5" data-testid="deferred-actions">
          <button
            disabled
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-cream-600 bg-white/[.03] cursor-not-allowed"
            aria-label="Add to Trip — coming soon"
            data-testid="add-to-trip-btn"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            Add to Trip
            <span className="ml-auto text-[10px] text-cream-700 font-medium uppercase tracking-wide">
              Coming soon
            </span>
          </button>
          <button
            disabled
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-cream-600 bg-white/[.03] cursor-not-allowed"
            aria-label="Create Trip — coming soon"
            data-testid="create-trip-btn"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            Create Trip
            <span className="ml-auto text-[10px] text-cream-700 font-medium uppercase tracking-wide">
              Coming soon
            </span>
          </button>
        </div>
      )}

      {/* Error feedback */}
      {actionState === "error" && errorMsg && (
        <p className="mt-1.5 text-xs text-rose-400" data-testid="action-error">
          {errorMsg}
        </p>
      )}
    </div>
  );
}
