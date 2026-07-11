"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { ItineraryItem, ReorderProposal } from "@/types";
import { applyRouteReorderProposal } from "@/lib/api";

// ─── ReorderProposalPreview ────────────────────────────────────────────────
// Explicit user-approved reorder-proposal apply contract (AI Route Planning
// v1 PR C), reused by the AI route-planning suggestion surfaced from
// "Plan My Day". Renders only when a `proposal` is supplied. Nothing here
// writes until the user explicitly clicks "Apply this order" — cancel/
// dismiss writes nothing.

export function ReorderProposalPreview({
  tripId,
  dayId,
  items,
  proposal,
  onApplied,
}: {
  tripId: string;
  dayId: string;
  items: ItineraryItem[];
  proposal: ReorderProposal | null;
  onApplied?: (order: string[]) => void;
}) {
  const [dismissed, setDismissed] = useState(false);
  const [applying, setApplying] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    setDismissed(false);
    setApplying(false);
    setErrorMessage(null);
  }, [proposal]);

  if (!proposal || dismissed) return null;

  const titleFor = (itemId: string) =>
    items.find((item) => item.id === itemId)?.title ?? "Untitled stop";

  // Display order (e.g. canonical Morning/Afternoon/Evening/Unscheduled
  // section order) is shown when supplied, so the preview always matches
  // the visible itinerary — but apply always sends currentOrder/
  // proposedOrder (raw position order), never these.
  const displayedCurrentOrder = proposal.currentDisplayOrder ?? proposal.currentOrder;
  const displayedProposedOrder = proposal.proposedDisplayOrder ?? proposal.proposedOrder;

  const handleCancel = () => {
    if (applying) return;
    setDismissed(true);
  };

  const handleConfirm = async () => {
    if (applying) return;
    setApplying(true);
    setErrorMessage(null);
    try {
      const result = await applyRouteReorderProposal(
        tripId,
        dayId,
        proposal.currentOrder,
        proposal.proposedOrder
      );
      if (result.status === "applied") {
        onApplied?.(result.order);
        setDismissed(true);
      } else {
        setErrorMessage(result.message || "This order couldn't be applied. Nothing changed.");
      }
    } catch {
      setErrorMessage("This order couldn't be applied. Nothing changed.");
    } finally {
      setApplying(false);
    }
  };

  return (
    <div
      data-testid="reorder-proposal-preview"
      className="flex flex-col gap-2 px-2.5 py-2 rounded-lg bg-ds-linen border border-ds-hairline mt-1"
    >
      <p className="text-[10px] text-ds-folio-ink-mist leading-tight">
        Nothing changes until you confirm. This only reorders the stops shown below.
      </p>
      {proposal.rationale && (
        <p data-testid="reorder-proposal-rationale" className="text-[11px] text-ds-folio-ink leading-snug">
          {proposal.rationale}
        </p>
      )}
      <div className="grid grid-cols-2 gap-2">
        <div data-testid="reorder-proposal-current">
          <p className="text-[10px] font-medium text-ds-folio-ink">Current order</p>
          <ol className="text-[10px] text-ds-folio-ink-mist list-decimal list-inside">
            {displayedCurrentOrder.map((itemId) => (
              <li key={itemId}>{titleFor(itemId)}</li>
            ))}
          </ol>
        </div>
        <div data-testid="reorder-proposal-proposed">
          <p className="text-[10px] font-medium text-ds-folio-ink">Proposed order</p>
          <ol className="text-[10px] text-ds-folio-ink-mist list-decimal list-inside">
            {displayedProposedOrder.map((itemId) => (
              <li key={itemId}>{titleFor(itemId)}</li>
            ))}
          </ol>
        </div>
      </div>
      {errorMessage && (
        <p className="text-[10px] text-ds-marine-ink" data-testid="reorder-proposal-error">
          {errorMessage}
        </p>
      )}
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={handleCancel}
          disabled={applying}
          data-testid="reorder-proposal-cancel"
          className="px-2 py-1 rounded-md text-[10px] font-medium text-ds-folio-ink-mist hover:text-ds-folio-ink border border-ds-hairline disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleConfirm}
          disabled={applying}
          data-testid="reorder-proposal-confirm"
          className="flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-medium text-white bg-ds-marine-ink disabled:opacity-50"
        >
          {applying && <Loader2 className="w-3 h-3 animate-spin" />}
          Apply this order
        </button>
      </div>
    </div>
  );
}
