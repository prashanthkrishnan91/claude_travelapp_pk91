"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Bookmark, ChevronDown, Loader2, Plane, Hotel, Sparkles, UtensilsCrossed, Search, X } from "lucide-react";
import { fetchTripIdeas, assignIdeaToDay, deleteItem, updateIdeaMeta } from "@/lib/api";
import type { ItemType, ItineraryDay, ItineraryItem } from "@/types";
import { FolioButton, FolioCard, FolioChip, FolioPanel } from "@/components/ui/Folio";

// Default visible items per vertical before "Show more" — keeps the panel
// usable when a user accumulates many saved ideas. See Level 3 Trip Data
// Contract Rescue (Trip Ideas must not flat-dump 39+ cards).
const DEFAULT_VISIBLE_PER_VERTICAL = 3;

interface VerticalGroup {
  key: ItemType;
  label: string;
  icon: ReactNode;
  items: ItineraryItem[];
}

function groupIdeasByVertical(ideas: ItineraryItem[]): VerticalGroup[] {
  const buckets: Record<string, ItineraryItem[]> = {
    activity: [],
    meal: [],
    hotel: [],
    flight: [],
  };
  for (const idea of ideas) {
    const t = idea.itemType;
    if (t === "activity" || t === "meal" || t === "hotel" || t === "flight") {
      buckets[t].push(idea);
    }
  }
  const groups: VerticalGroup[] = [
    { key: "activity", label: "Attractions", icon: <Sparkles className="h-3 w-3 text-ds-accent" />,       items: buckets.activity },
    { key: "meal",     label: "Restaurants", icon: <UtensilsCrossed className="h-3 w-3 text-ds-accent" />, items: buckets.meal     },
    { key: "hotel",    label: "Hotels",      icon: <Hotel className="h-3 w-3 text-ds-accent" />,           items: buckets.hotel    },
    { key: "flight",   label: "Flights",     icon: <Plane className="h-3 w-3 text-ds-accent" />,           items: buckets.flight   },
  ];
  return groups.filter((g) => g.items.length > 0);
}

interface Props {
  tripId: string;
  days: ItineraryDay[];
  refreshKey?: number;
  onIdeaAssigned?: () => void;
}

const STATUS_OPTIONS = [
  { value: "must_do", label: "Must-do", activeClass: "text-ds-trust-verified ring-ds-trust-verified/40" },
  { value: "maybe",   label: "Maybe",   activeClass: "text-ds-caution ring-ds-caution/40" },
  { value: "skipped", label: "Skip",    activeClass: "text-ds-folio-ink-soft ring-ds-folio-ink-soft/40 bg-ds-bone" },
] as const;

type IdeaStatus = "must_do" | "maybe" | "skipped";

// "active" = all non-skipped (default view); other values filter to that status only
export type StatusFilter = "active" | "must_do" | "maybe" | "skipped";
export type SortOption = "priority" | "recently_saved" | "name" | "category";

export const STATUS_FILTER_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "active",  label: "All" },
  { value: "must_do", label: "Must-do" },
  { value: "maybe",   label: "Maybe" },
  { value: "skipped", label: "Skip" },
];

export const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "priority",       label: "Priority" },
  { value: "recently_saved", label: "Recently saved" },
  { value: "name",           label: "Name" },
  { value: "category",       label: "Category" },
];

const PRIORITY_ORDER: Record<IdeaStatus, number> = {
  must_do: 0,
  maybe: 1,
  skipped: 2,
};

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

export function filterByStatus(ideas: ItineraryItem[], filter: StatusFilter): ItineraryItem[] {
  if (filter === "active") return ideas.filter((it) => getIdeaStatus(it) !== "skipped");
  return ideas.filter((it) => getIdeaStatus(it) === filter);
}

export function searchIdeas(ideas: ItineraryItem[], query: string): ItineraryItem[] {
  const q = query.toLowerCase().trim();
  if (!q) return ideas;
  return ideas.filter((idea) => {
    const details = (idea.details ?? {}) as Record<string, unknown>;
    const note = ((details.userNote ?? details.user_note) as string | undefined) ?? "";
    const address = (details.address as string | undefined) ?? "";
    const category = ideaCategory(idea).toLowerCase();
    return (
      idea.title.toLowerCase().includes(q) ||
      (idea.location ?? "").toLowerCase().includes(q) ||
      address.toLowerCase().includes(q) ||
      note.toLowerCase().includes(q) ||
      category.includes(q)
    );
  });
}

export function sortIdeas(ideas: ItineraryItem[], sortBy: SortOption): ItineraryItem[] {
  const sorted = [...ideas];
  switch (sortBy) {
    case "priority":
      return sorted.sort((a, b) => PRIORITY_ORDER[getIdeaStatus(a)] - PRIORITY_ORDER[getIdeaStatus(b)]);
    case "recently_saved":
      return sorted.sort((a, b) => {
        const ta = a.createdAt;
        const tb = b.createdAt;
        if (!ta && !tb) return 0;
        if (!ta) return 1;
        if (!tb) return -1;
        return tb.localeCompare(ta);
      });
    case "name":
      return sorted.sort((a, b) => a.title.localeCompare(b.title));
    case "category":
      return sorted.sort((a, b) => ideaCategory(a).localeCompare(ideaCategory(b)));
    default:
      return sorted;
  }
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
    <FolioCard className="folio-paper-item p-3" data-testid="trip-idea-card">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-ds-folio-ink">{item.title}</p>
          <p className="mt-0.5 text-[11px] uppercase tracking-[0.08em] text-ds-folio-ink-mist">{ideaCategory(item)}</p>
          {rating && <p className="mt-0.5 text-xs text-ds-folio-ink-mist">{rating}</p>}
          {item.location && item.location !== item.title && (
            <p className="mt-0.5 text-[11px] text-ds-folio-ink-mist">{item.location}</p>
          )}
        </div>
        <div className="flex items-center gap-1">
          {savingMeta && <Loader2 className="h-3 w-3 animate-spin text-ds-folio-ink-mist" />}
          <button
            type="button"
            onClick={onRemove}
            disabled={removing}
            title="Remove from trip ideas"
            className="flex-shrink-0 min-w-[44px] min-h-[44px] flex items-center justify-center rounded text-ds-folio-ink-mist hover:bg-ds-linen hover:text-ds-folio-ink transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
          >
            {removing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <X className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Priority / status row */}
      <div className="mt-2 flex items-center gap-1">
        {STATUS_OPTIONS.map((opt) => (
          <button
            type="button"
            key={opt.value}
            onClick={() => handleStatusChange(opt.value)}
            disabled={savingMeta}
            className="group min-h-[44px] flex items-center justify-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
          >
            <span
              className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ring-1 transition ${
                status === opt.value
                  ? opt.activeClass
                  : "text-ds-folio-ink-soft ring-ds-hairline group-hover:text-ds-folio-ink group-hover:ring-ds-folio-ink-mist"
              }`}
              style={status === opt.value && opt.value !== "skipped"
                ? { backgroundColor: "var(--ds-accent-subtle)" }
                : undefined}
            >
              {opt.label}
            </span>
          </button>
        ))}
        <button
          type="button"
          onClick={() => setNoteOpen((v) => !v)}
          className="ml-auto min-h-[44px] min-w-[44px] flex items-center justify-center px-1 text-[10px] text-ds-folio-ink-mist hover:text-ds-folio-ink transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
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
          className="mt-1.5 w-full resize-none rounded-lg border border-ds-hairline bg-ds-bone px-2 py-1.5 text-xs text-ds-folio-ink placeholder-ds-folio-ink-mist focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
        />
      )}

      {days.length > 0 && (
        <div className="mt-2.5 flex items-center gap-1.5">
          <select
            value={selectedDay}
            onChange={(e) => setSelectedDay(e.target.value)}
            disabled={assigning}
            className="flex-1 min-h-[44px] rounded-lg border border-ds-hairline bg-ds-bone px-2 py-1.5 text-xs text-ds-folio-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
          >
            {days.map((day) => (
              <option key={day.id} value={day.id}>
                Day {day.dayNumber}{day.date ? ` · ${day.date}` : ""}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => onAssign(selectedDay)}
            disabled={assigning || !selectedDay}
            className="flex-shrink-0 min-h-[44px] inline-flex items-center justify-center rounded-lg px-2.5 text-xs font-medium text-ds-accent ring-1 ring-ds-accent/40 hover:ring-ds-accent transition disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
            style={{ backgroundColor: "var(--ds-accent-subtle)" }}
          >
            {assigning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Add to Day"}
          </button>
        </div>
      )}
    </FolioCard>
  );
}

export function TripIdeasPanel({ tripId, days, refreshKey, onIdeaAssigned }: Props) {
  const [ideas, setIdeas] = useState<ItineraryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [assigningId, setAssigningId] = useState<string | null>(null);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [open, setOpen] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("active");
  const [sortBy, setSortBy] = useState<SortOption>("priority");
  const [expandedGroups, setExpandedGroups] = useState<Partial<Record<ItemType, boolean>>>({});

  const load = useCallback(async () => {
    setLoading(true);
    const all = await fetchTripIdeas(tripId);
    setIdeas(all);
    setLoading(false);
  }, [tripId]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  // Auto-expand when ideas arrive so users see them immediately
  useEffect(() => {
    if (ideas.length > 0) setOpen(true);
  }, [ideas.length]);

  // Badge shows active (non-skipped) count regardless of current filter
  const activeCount = ideas.filter((it) => getIdeaStatus(it) !== "skipped").length;

  const filteredAndSorted = useMemo(() => {
    let result = filterByStatus(ideas, statusFilter);
    result = searchIdeas(result, searchQuery);
    result = sortIdeas(result, sortBy);
    return result;
  }, [ideas, statusFilter, searchQuery, sortBy]);

  const hasActiveFilters =
    statusFilter !== "active" || searchQuery.trim().length > 0 || sortBy !== "priority";

  function handleReset() {
    setSearchQuery("");
    setStatusFilter("active");
    setSortBy("priority");
  }

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
    <FolioPanel data-testid="trip-ideas-panel-root">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-3.5 py-3 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2 rounded-2xl"
      >
        <div className="flex items-center gap-2">
          <Bookmark className="h-3.5 w-3.5 text-ds-accent" />
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-ds-folio-ink">Trip Ideas</span>
            <span className="text-[10px] text-ds-folio-ink-mist">Saved from AI Concierge · add to a day when ready</span>
          </div>
          {activeCount > 0 && (
            <span className="rounded-full px-1.5 py-0.5 text-[10px] font-semibold text-ds-accent border border-ds-hairline"
              style={{ backgroundColor: "var(--ds-accent-subtle)" }}>
              {activeCount}
            </span>
          )}
        </div>
        <ChevronDown className={`h-4 w-4 text-ds-folio-ink-mist transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="border-t border-ds-hairline px-3.5 pb-3.5 pt-3">
          {loading ? (
            <div className="flex items-center gap-2 py-2 text-xs text-ds-folio-ink-mist">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Loading ideas…
            </div>
          ) : ideas.length === 0 ? (
            <p className="py-2 text-xs text-ds-folio-ink-mist">Save recommendations from AI Concierge and schedule them later.</p>
          ) : (
            <>
              {/* Compact filter / search / sort controls */}
              <div className="mb-3 space-y-2">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ds-folio-ink-mist" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search ideas…"
                    aria-label="Search trip ideas"
                    className="w-full rounded-lg border border-ds-hairline bg-ds-bone py-1.5 pl-7 pr-2 text-xs text-ds-folio-ink placeholder-ds-folio-ink-mist focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                  />
                </div>
                <div className="flex flex-wrap items-center gap-1">
                  {STATUS_FILTER_OPTIONS.map((opt) => (
                    <button
                      type="button"
                      key={opt.value}
                      onClick={() => setStatusFilter(opt.value)}
                      aria-pressed={statusFilter === opt.value}
                      className="group min-h-[44px] flex items-center justify-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                    >
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-medium ring-1 transition ${
                          statusFilter === opt.value
                            ? "text-ds-accent ring-ds-accent/40"
                            : "text-ds-folio-ink-mist ring-ds-hairline group-hover:text-ds-folio-ink group-hover:ring-ds-accent/30"
                        }`}
                        style={statusFilter === opt.value ? { backgroundColor: "var(--ds-accent-subtle)" } : undefined}
                      >
                        {opt.label}
                      </span>
                    </button>
                  ))}
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as SortOption)}
                    aria-label="Sort ideas"
                    className="ml-auto min-h-[44px] rounded-lg border border-ds-hairline bg-ds-bone px-2 py-1 text-[10px] text-ds-folio-ink-mist focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                  >
                    {SORT_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                  {hasActiveFilters && (
                    <button
                      type="button"
                      onClick={handleReset}
                      aria-label="Reset filters"
                      className="min-h-[44px] min-w-[44px] flex items-center justify-center px-1 text-[10px] text-ds-folio-ink-mist hover:text-ds-folio-ink transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                    >
                      Clear ×
                    </button>
                  )}
                </div>
              </div>

              {filteredAndSorted.length === 0 ? (
                <p className="py-2 text-xs text-ds-folio-ink-mist">No ideas match your current filters.</p>
              ) : (
                <div className="space-y-3">
                  {groupIdeasByVertical(filteredAndSorted).map((group) => {
                    const expanded = expandedGroups[group.key] ?? false;
                    const visible = expanded
                      ? group.items
                      : group.items.slice(0, DEFAULT_VISIBLE_PER_VERTICAL);
                    const overflow = group.items.length - visible.length;
                    return (
                      <div key={group.key} data-vertical={group.key}>
                        <div className="mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-ds-folio-ink-mist">
                          {group.icon}
                          {group.label}
                          <span className="text-ds-folio-ink-mist opacity-70">({group.items.length})</span>
                        </div>
                        <div className="space-y-2">
                          {visible.map((idea) => (
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
                        </div>
                        {overflow > 0 && (
                          <FolioButton
                            variant="secondary"
                            onClick={() => setExpandedGroups((prev) => ({ ...prev, [group.key]: true }))}
                            className="mt-1.5 w-full justify-center text-[10px]"
                          >
                            Show {overflow} more
                          </FolioButton>
                        )}
                        {expanded && group.items.length > DEFAULT_VISIBLE_PER_VERTICAL && (
                          <FolioButton
                            variant="secondary"
                            onClick={() => setExpandedGroups((prev) => ({ ...prev, [group.key]: false }))}
                            className="mt-1.5 w-full justify-center text-[10px]"
                          >
                            Show less
                          </FolioButton>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </FolioPanel>
  );
}
