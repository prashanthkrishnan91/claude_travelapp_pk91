"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Bookmark, ChevronDown, Loader2, X } from "lucide-react";
import { fetchTripIdeas, assignIdeaToDay, deleteItem, updateIdeaMeta } from "@/lib/api";
import type { ItineraryDay, ItineraryItem } from "@/types";

interface Props {
  tripId: string;
  days: ItineraryDay[];
  refreshKey?: number;
  onIdeaAssigned?: () => void;
}

const STATUS_OPTIONS = [
  { value: "must_do", label: "Must-do", activeClass: "bg-emerald-400/15 text-emerald-300 ring-emerald-400/40" },
  { value: "maybe",   label: "Maybe",   activeClass: "bg-amber-200/15 text-amber-200 ring-amber-300/40" },
  { value: "skipped", label: "Skip",    activeClass: "bg-slate-600/40 text-slate-400 ring-slate-500/40" },
] as const;

type IdeaStatus = "must_do" | "maybe" | "skipped";

function getIdeaStatus(item: ItineraryItem): IdeaStatus {
  const d = (item.details ?? {}) as Record<string, unknown>;
  const s = (d.ideaStatus ?? d.idea_status) as string | undefined;
  if (s === "must_do" || s === "maybe" || s === "skipped") return s;
  return "maybe";
}

function getIdeaNote(item: ItineraryItem): string {
  const d = (item.details ?? {}) as Record<string, unknown>;
  return ((d.userNote ?? d.user_note) as string | undefined) ?? "";
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
  onUpdate,
  assigning,
  removing,
}: {
  item: ItineraryItem;
  days: ItineraryDay[];
  onAssign: (dayId: string) => void;
  onRemove: () => void;
  onUpdate: (patch: { ideaStatus?: string; userNote?: string }) => Promise<void>;
  assigning: boolean;
  removing: boolean;
}) {
  const [selectedDay, setSelectedDay] = useState(days[0]?.id ?? "");
  const [savingMeta, setSavingMeta] = useState(false);
  const [status, setStatus] = useState<IdeaStatus>(getIdeaStatus(item));
  const [note, setNote] = useState(getIdeaNote(item));
  const [noteOpen, setNoteOpen] = useState(() => !!getIdeaNote(item));
  const noteTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const rating = ideaRating(item);

  async function handleStatusChange(newStatus: IdeaStatus) {
    if (newStatus === status || savingMeta) return;
    setStatus(newStatus);
    setSavingMeta(true);
    try {
      await onUpdate({ ideaStatus: newStatus });
    } finally {
      setSavingMeta(false);
    }
  }

  function handleNoteChange(val: string) {
    setNote(val);
    if (noteTimerRef.current) clearTimeout(noteTimerRef.current);
    noteTimerRef.current = setTimeout(() => {
      setSavingMeta(true);
      onUpdate({ userNote: val }).finally(() => setSavingMeta(false));
    }, 800);
  }

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
        <div className="flex items-center gap-1">
          {savingMeta && <Loader2 className="h-3 w-3 animate-spin text-slate-500" />}
          <button
            onClick={onRemove}
            disabled={removing}
            title="Remove from trip ideas"
            className="flex-shrink-0 rounded p-1 text-slate-500 hover:bg-slate-800 hover:text-slate-300 transition"
          >
            {removing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <X className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Priority / status row */}
      <div className="mt-2 flex items-center gap-1">
        {STATUS_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => handleStatusChange(opt.value)}
            disabled={savingMeta}
            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ring-1 transition ${
              status === opt.value
                ? opt.activeClass
                : "text-slate-500 ring-slate-600/40 hover:text-slate-300 hover:ring-slate-500/60"
            }`}
          >
            {opt.label}
          </button>
        ))}
        <button
          onClick={() => setNoteOpen((v) => !v)}
          className="ml-auto text-[10px] text-slate-500 hover:text-slate-300 transition"
        >
          {note ? "note ✎" : "+ note"}
        </button>
      </div>

      {/* Inline note textarea */}
      {noteOpen && (
        <textarea
          value={note}
          onChange={(e) => handleNoteChange(e.target.value)}
          placeholder="Add a note…"
          rows={2}
          className="mt-1.5 w-full resize-none rounded-lg border border-slate-600 bg-slate-800 px-2 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-amber-300/50"
        />
      )}

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
  const [showSkipped, setShowSkipped] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const all = await fetchTripIdeas(tripId);
    const conciergeIdeas = all.filter(
      (it) => {
        const details = (it.details ?? {}) as Record<string, unknown>;
        return details.sourceKind === "concierge_idea" || details.source_kind === "concierge_idea";
      },
    );
    setIdeas(conciergeIdeas);
    setLoading(false);
  }, [tripId]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  // Auto-expand when ideas arrive so users see them immediately
  useEffect(() => {
    if (ideas.length > 0) setOpen(true);
  }, [ideas.length]);

  const visibleIdeas = ideas.filter((it) => showSkipped || getIdeaStatus(it) !== "skipped");
  const skippedCount = ideas.filter((it) => getIdeaStatus(it) === "skipped").length;

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

  async function handleUpdate(itemId: string, patch: { ideaStatus?: string; userNote?: string }) {
    const idea = ideas.find((it) => it.id === itemId);
    if (!idea) return;
    const currentDetails = (idea.details ?? {}) as Record<string, unknown>;
    setIdeas((prev) =>
      prev.map((it) =>
        it.id === itemId ? { ...it, details: { ...it.details, ...patch } } : it
      )
    );
    try {
      await updateIdeaMeta(itemId, currentDetails, patch);
    } catch (err) {
      console.error("[trip-ideas] update meta failed", err);
      void load();
    }
  }

  return (
    <div className="rounded-2xl border border-amber-200/15 bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 shadow-sm">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-3.5 py-3 text-left"
      >
        <div className="flex items-center gap-2">
          <Bookmark className="h-3.5 w-3.5 text-amber-200/70" />
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-slate-100">Trip Ideas</span>
            <span className="text-[10px] text-slate-400">Saved from AI Concierge · add to a day when ready</span>
          </div>
          {visibleIdeas.length > 0 && (
            <span className="rounded-full bg-amber-200/15 px-1.5 py-0.5 text-[10px] font-semibold text-amber-200">
              {visibleIdeas.length}
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
            <p className="py-2 text-xs text-slate-400">Save recommendations from AI Concierge and schedule them later.</p>
          ) : (
            <div className="space-y-2">
              {visibleIdeas.map((idea) => (
                <IdeaCard
                  key={idea.id}
                  item={idea}
                  days={days}
                  assigning={assigningId === idea.id}
                  removing={removingId === idea.id}
                  onAssign={(dayId) => handleAssign(idea.id, dayId)}
                  onRemove={() => handleRemove(idea.id)}
                  onUpdate={(patch) => handleUpdate(idea.id, patch)}
                />
              ))}
              {skippedCount > 0 && (
                <button
                  onClick={() => setShowSkipped((v) => !v)}
                  className="w-full pt-1 text-center text-[10px] text-slate-500 hover:text-slate-300 transition"
                >
                  {showSkipped
                    ? `Hide ${skippedCount} skipped`
                    : `${skippedCount} skipped · show`}
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
