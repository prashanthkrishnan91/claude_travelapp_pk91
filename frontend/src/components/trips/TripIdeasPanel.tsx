"use client";

import { useCallback, useEffect, useState } from "react";
import { Bookmark, ChevronDown, Loader2, X } from "lucide-react";
import { fetchTripIdeas, assignIdeaToDay, deleteItem } from "@/lib/api";
import type { ItineraryDay, ItineraryItem } from "@/types";

interface Props {
  tripId: string;
  days: ItineraryDay[];
  refreshKey?: number;
  onIdeaAssigned?: () => void;
}

function ideaCategory(item: ItineraryItem): string {
  const details = (item.details ?? {}) as Record<string, unknown>;
  const cat = (details.category as string | undefined) ?? (details.type as string | undefined);
  if (cat) return cat.charAt(0).toUpperCase() + cat.slice(1);
  if (item.itemType === "meal") return "Restaurant";
  if (item.itemType === "hotel") return "Hotel";
  if (item.itemType === "activity") return "Attraction";
  return "Idea";
}

function ideaRating(item: ItineraryItem): string | null {
  const details = (item.details ?? {}) as Record<string, unknown>;
  const r = details.rating as number | null | undefined;
  const rc = details.review_count as number | null | undefined;
  if (!r) return null;
  return rc ? `★ ${r.toFixed(1)} (${Number(rc).toLocaleString()} reviews)` : `★ ${r.toFixed(1)}`;
}

function IdeaCard({
  item,
  days,
  onAssign,
  onRemove,
  assigning,
  removing,
}: {
  item: ItineraryItem;
  days: ItineraryDay[];
  onAssign: (dayId: string) => void;
  onRemove: () => void;
  assigning: boolean;
  removing: boolean;
}) {
  const [selectedDay, setSelectedDay] = useState(days[0]?.id ?? "");
  const rating = ideaRating(item);

  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900/50 p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-slate-100">{item.title}</p>
          <p className="mt-0.5 text-[11px] uppercase tracking-[0.08em] text-slate-400">{ideaCategory(item)}</p>
          {rating && <p className="mt-0.5 text-xs text-slate-300">{rating}</p>}
          {item.location && item.location !== item.title && (
            <p className="mt-0.5 text-[11px] text-slate-400">{item.location}</p>
          )}
        </div>
        <button
          onClick={onRemove}
          disabled={removing}
          title="Remove from trip ideas"
          className="flex-shrink-0 rounded p-1 text-slate-500 hover:bg-slate-800 hover:text-slate-300 transition"
        >
          {removing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <X className="h-3.5 w-3.5" />}
        </button>
      </div>

      {days.length > 0 && (
        <div className="mt-2.5 flex items-center gap-1.5">
          <select
            value={selectedDay}
            onChange={(e) => setSelectedDay(e.target.value)}
            disabled={assigning}
            className="flex-1 rounded-lg border border-slate-600 bg-slate-800 px-2 py-1.5 text-xs text-slate-100 focus:outline-none focus:ring-1 focus:ring-amber-300/50"
          >
            {days.map((day) => (
              <option key={day.id} value={day.id}>
                Day {day.dayNumber}{day.date ? ` · ${day.date}` : ""}
              </option>
            ))}
          </select>
          <button
            onClick={() => onAssign(selectedDay)}
            disabled={assigning || !selectedDay}
            className="flex-shrink-0 rounded-lg bg-amber-200/15 px-2.5 py-1.5 text-xs font-medium text-amber-100 ring-1 ring-amber-300/40 hover:bg-amber-200/25 transition disabled:opacity-50"
          >
            {assigning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Add to Day"}
          </button>
        </div>
      )}
    </div>
  );
}

export function TripIdeasPanel({ tripId, days, refreshKey, onIdeaAssigned }: Props) {
  const [ideas, setIdeas] = useState<ItineraryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [assigningId, setAssigningId] = useState<string | null>(null);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [open, setOpen] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const all = await fetchTripIdeas(tripId);
    const conciergeIdeas = all.filter(
      (it) => (it.details as Record<string, unknown>)?.source_kind === "concierge_idea",
    );
    setIdeas(conciergeIdeas);
    setLoading(false);
  }, [tripId]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  async function handleAssign(itemId: string, dayId: string) {
    setAssigningId(itemId);
    try {
      await assignIdeaToDay(itemId, dayId);
      setIdeas((prev) => prev.filter((it) => it.id !== itemId));
      onIdeaAssigned?.();
    } catch (err) {
      console.error("[trip-ideas] assign failed", err);
    } finally {
      setAssigningId(null);
    }
  }

  async function handleRemove(itemId: string) {
    setRemovingId(itemId);
    try {
      await deleteItem(itemId);
      setIdeas((prev) => prev.filter((it) => it.id !== itemId));
    } catch (err) {
      console.error("[trip-ideas] remove failed", err);
    } finally {
      setRemovingId(null);
    }
  }

  if (!loading && ideas.length === 0) return null;

  return (
    <div className="rounded-2xl border border-amber-200/15 bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 shadow-sm">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-3.5 py-3 text-left"
      >
        <div className="flex items-center gap-2">
          <Bookmark className="h-3.5 w-3.5 text-amber-200/70" />
          <span className="text-sm font-semibold text-slate-100">Trip Ideas</span>
          {ideas.length > 0 && (
            <span className="rounded-full bg-amber-200/15 px-1.5 py-0.5 text-[10px] font-semibold text-amber-200">
              {ideas.length}
            </span>
          )}
        </div>
        <ChevronDown className={`h-4 w-4 text-slate-400 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="border-t border-slate-700/60 px-3.5 pb-3.5 pt-3">
          {loading ? (
            <div className="flex items-center gap-2 py-2 text-xs text-slate-400">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Loading ideas…
            </div>
          ) : ideas.length === 0 ? (
            <p className="py-2 text-xs text-slate-400">No saved ideas yet. Use Save on any concierge result.</p>
          ) : (
            <div className="space-y-2">
              {ideas.map((idea) => (
                <IdeaCard
                  key={idea.id}
                  item={idea}
                  days={days}
                  assigning={assigningId === idea.id}
                  removing={removingId === idea.id}
                  onAssign={(dayId) => handleAssign(idea.id, dayId)}
                  onRemove={() => handleRemove(idea.id)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
